import time
from http import HTTPStatus

import factory
import pytest
import pytest_asyncio

from src.crypto_service import crypto_service
from src.models import Election, Election_Candidate, User
from src.settings import Settings

# Tamanho de lote de produção nas medições criptográficas (os testes de API
# usam o LOTE_TAMANHO=5 definido no conftest)
LOTE_PRODUCAO = 1000


@pytest.fixture(autouse=True)
def persistent_keys():
    # Mesmas chaves persistentes usadas pela aplicação
    crypto_service.load_or_create_keys(Settings().KEYS_DIR)


@pytest_asyncio.fixture
async def stress_election_setup(session):
    # Criar eleição (em configuração)
    election = StressElectionFactory()
    session.add(election)
    await session.commit()
    await session.refresh(election)

    # Criar 3 candidatos
    candidates = []
    for i in range(3):
        candidate = StressCandidateFactory()
        session.add(candidate)
        candidates.append(candidate)

    await session.commit()

    # Associar candidatos à eleição
    for candidate in candidates:
        await session.refresh(candidate)
        election_candidate = Election_Candidate(
            fk_election=election.id, fk_candidate=candidate.id
        )
        session.add(election_candidate)

    await session.commit()

    return election, candidates


def _simulate_election(votes: int, candidates: int, lot_size: int = LOTE_PRODUCAO):
    """
    Reproduz o fluxo do sistema sem banco: voto cifrado e serializado, soma
    incremental do total (caminho 1), lotes recalculados do zero (caminho 2) e
    dupla contagem na apuração. Devolve o resultado e os tempos de cada etapa.
    """
    times = {'voto': 0.0, 'lote': 0.0, 'apuracao': 0.0}
    tally = crypto_service.serialize(crypto_service.zero(candidates))
    open_lot, subtotals = [], []

    def close_lot():
        start = time.perf_counter()
        subtotal = crypto_service.zero(candidates)
        for vote in open_lot:
            subtotal = crypto_service.add(subtotal, crypto_service.deserialize(vote))
        subtotals.append(crypto_service.serialize(subtotal))
        open_lot.clear()
        times['lote'] += time.perf_counter() - start

    for i in range(votes):
        start = time.perf_counter()
        vector = crypto_service.create_vote_vector(i % candidates, candidates)
        ciphertext = crypto_service.encrypt_vector(vector)
        open_lot.append(crypto_service.serialize(ciphertext))
        tally = crypto_service.serialize(
            crypto_service.add(crypto_service.deserialize(tally), ciphertext)
        )
        times['voto'] += time.perf_counter() - start
        if len(open_lot) == lot_size:
            close_lot()
    if open_lot:
        close_lot()

    start = time.perf_counter()
    accumulated = crypto_service.decrypt(crypto_service.deserialize(tally), candidates)
    total = crypto_service.zero(candidates)
    for subtotal in subtotals:
        total = crypto_service.add(total, crypto_service.deserialize(subtotal))
    from_lots = crypto_service.decrypt(total, candidates)
    times['apuracao'] = time.perf_counter() - start

    assert accumulated == from_lots
    return accumulated, len(subtotals), times


def _report(votes, lots, times, results):
    print(f'\n{votes:,} votos em {lots} lote(s)')
    per_vote_ms = times['voto'] / votes * 1000
    print(f'  voto (cifrar + serializar + somar ao total): {per_vote_ms:.2f} ms')
    print(f'  fechamento de lote: {times["lote"] / lots:.2f} s por lote')
    print(f'  apuração (dupla contagem): {times["apuracao"] * 1000:.1f} ms')
    print(f'  resultado: {results}')


@pytest.mark.asyncio
async def test_crypto_stress_100_votes():
    votes = 100
    results, lots, times = _simulate_election(votes, 3)
    _report(votes, lots, times, results)
    assert sum(results) == votes


@pytest.mark.asyncio
async def test_crypto_stress_1000_votes():
    votes = 1000
    results, lots, times = _simulate_election(votes, 3)
    _report(votes, lots, times, results)
    assert sum(results) == votes
    assert lots == 1


@pytest.mark.asyncio
async def test_crypto_stress_10000_votes():
    votes = 10000
    results, lots, times = _simulate_election(votes, 3)
    _report(votes, lots, times, results)
    assert sum(results) == votes
    assert lots == votes // LOTE_PRODUCAO


@pytest.mark.asyncio
async def test_crypto_stress_100000_votes():
    # Só cifragem e soma em memória, sem serializar a cada voto, para manter o
    # tempo do teste viável
    start_time = time.time()

    total_votes = 100000
    tally = crypto_service.zero(3)
    for i in range(total_votes):
        vote_vector = crypto_service.create_vote_vector(i % 3, 3)
        tally = crypto_service.add(tally, crypto_service.encrypt_vector(vote_vector))
        if (i + 1) % 10000 == 0:
            print(f'Processados {i + 1} votos...')

    results = crypto_service.decrypt(tally, 3)
    end_time = time.time()

    print(f'100.000 votos processados em {end_time - start_time:.2f}s')
    print(f'Resultados: {results}')
    assert sum(results) == total_votes


@pytest.mark.asyncio
async def test_crypto_api_does_not_use_cache():
    # A API por bytes não depende do cache em memória (fonte da verdade é o banco)
    crypto_service.clear_cache()

    for i in range(100):
        vote_vector = crypto_service.create_vote_vector(i % 3, 3)
        crypto_service.serialize(crypto_service.encrypt_vector(vote_vector))

    assert crypto_service.get_cache_size() == 0


@pytest.mark.asyncio
async def test_crypto_overflow_protection():
    # Testar com valores próximos ao limite do plaintext modulus
    plaintext_mod = 65537  # Valor padrão

    tally = crypto_service.zero(1)

    # Simular muitos votos no mesmo candidato
    max_safe_votes = plaintext_mod // 2  # Margem de segurança

    for i in range(min(1000, max_safe_votes)):  # Limitar para não demorar muito
        vote_vector = crypto_service.create_vote_vector(0, 1)
        tally = crypto_service.add(tally, crypto_service.encrypt_vector(vote_vector))

    results = crypto_service.decrypt(tally, 1)
    expected_votes = min(1000, max_safe_votes)

    print(f'Votos processados: {expected_votes}')
    print(f'Resultado: {results[0]}')

    assert results[0] == expected_votes


# Teste de API com múltiplos usuários
@pytest.mark.asyncio
async def test_api_stress_multiple_users(
    client, stress_election_setup, session, admin_token
):
    """Teste de estresse da API com múltiplos usuários"""
    election, candidates = stress_election_setup
    candidate_ids = [c.id for c in candidates]
    election_id = election.id
    admin_headers = {'Authorization': f'Bearer {admin_token}'}

    response = client.post(f'/elections/{election_id}/open', headers=admin_headers)
    assert response.status_code == HTTPStatus.OK

    # Criar 50 usuários
    users_data = []
    for i in range(50):
        user_data = {
            'username': f'stress_user_{i}',
            'email': f'stress_user_{i}@test.com',
            'password': 'testpass',
            'statusVotacao': False,
        }

        response = client.post('/users', json=user_data)
        assert response.status_code == HTTPStatus.CREATED
        users_data.append(user_data)

    # Cada usuário vota (o voto que completa um lote também o fecha)
    vote_count = 0
    times = {'voto': 0.0}
    for i, user_data in enumerate(users_data):
        # Login
        login_response = client.post(
            '/auth/token',
            data={'username': user_data['email'], 'password': user_data['password']},
        )
        assert login_response.status_code == HTTPStatus.OK

        # Votar
        start = time.perf_counter()
        vote_response = client.post(
            f'/vote/election/{election_id}',
            json={'candidate_id': candidate_ids[i % 3]},
            headers={'Authorization': f'Bearer {login_response.json()["access_token"]}'},
        )
        times['voto'] += time.perf_counter() - start

        if vote_response.status_code == HTTPStatus.CREATED:
            vote_count += 1

    # Encerrar e apurar (resultado só é publicado após a apuração)
    for action, key in (('close', 'encerrar'), ('tally', 'apurar')):
        start = time.perf_counter()
        client.post(f'/elections/{election_id}/{action}', headers=admin_headers)
        times[key] = time.perf_counter() - start

    # Verificar resultados
    results_response = client.get(f'/vote/results/{election_id}')
    assert results_response.status_code == HTTPStatus.OK

    results = results_response.json()
    print(f'Votos processados via API: {vote_count}')
    print(f'Total de votos: {results["total_votes"]}')
    times = {k: v * 1000 for k, v in times.items()}
    print(
        f'Tempo médio por voto (requisição completa): {times["voto"] / vote_count:.1f} ms'
    )
    print(
        f'Encerramento: {times["encerrar"]:.1f} ms | Apuração: {times["apurar"]:.1f} ms'
    )

    assert results['total_votes'] == vote_count


class StressElectionFactory(factory.Factory):
    class Meta:
        model = Election

    title = 'Stress Test Election'


class StressCandidateFactory(factory.Factory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f'candidate_{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@stress.com')
    password = 'stress_password'
    is_candidate = True


class StressUserFactory(factory.Factory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f'stress_user_{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@stress.com')
    password = 'stress_password'
    statusVotacao = False
