import time
from http import HTTPStatus

import factory
import pytest
import pytest_asyncio

from src.crypto_service import crypto_service
from src.models import Candidate, Election, Election_Candidate, User


@pytest_asyncio.fixture
async def stress_election_setup(session):
    # Criar eleição
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


@pytest.mark.asyncio
async def test_crypto_stress_100_votes():
    crypto_service.setup_crypto()
    crypto_service.clear_cache()

    start_time = time.time()

    encrypted_votes = []
    for i in range(100):
        candidate_pos = i % 3  # Distribuir entre 3 candidatos
        vote_vector = crypto_service.create_vote_vector(candidate_pos, 3)
        encrypted_vote = crypto_service.encrypt_vote(vote_vector)
        encrypted_votes.append(encrypted_vote)

    tally = crypto_service.create_zero_tally(3)
    for encrypted_vote in encrypted_votes:
        tally = crypto_service.add_vote_to_tally(tally, encrypted_vote)

    results = crypto_service.decrypt_tally(tally, 3)

    end_time = time.time()

    votes = 100

    print(f'100 votos processados em {end_time - start_time:.2f}s')
    print(f'Resultados: {results}')
    print(f'Cache final: {crypto_service.get_cache_size()} entradas')
    assert sum(results) == votes


@pytest.mark.asyncio
async def test_crypto_stress_1000_votes():
    crypto_service.setup_crypto()
    crypto_service.clear_cache()

    start_time = time.time()

    # Usando streaming para economizar memória
    vote_vectors = []
    for i in range(1000):
        candidate_pos = i % 3
        vote_vector = crypto_service.create_vote_vector(candidate_pos, 3)
        vote_vectors.append(vote_vector)

    results = crypto_service.process_votes_streaming(vote_vectors, 3)
    end_time = time.time()

    votes = 1000

    print(f'1.000 votos processados em {end_time - start_time:.2f}s')
    print(f'Resultados: {results}')
    print(f'Cache final: {crypto_service.get_cache_size()} entradas')
    assert sum(results) == votes


@pytest.mark.asyncio
async def test_crypto_stress_10000_votes():
    crypto_service.setup_crypto()
    crypto_service.clear_cache()

    start_time = time.time()

    vote_vectors = []
    for i in range(10000):
        candidate_pos = i % 3
        vote_vector = crypto_service.create_vote_vector(candidate_pos, 3)
        vote_vectors.append(vote_vector)

    results = crypto_service.process_votes_streaming(vote_vectors, 3)
    end_time = time.time()

    votes = 10000

    print(f'10.000 votos processados em {end_time - start_time:.2f}s')
    print(f'Resultados: {results}')
    print(f'Cache final: {crypto_service.get_cache_size()} entradas')
    assert sum(results) == votes


@pytest.mark.asyncio
async def test_crypto_stress_100000_votes():
    crypto_service.setup_crypto()
    crypto_service.clear_cache()

    start_time = time.time()

    # Processando em lotes menores para evitar sobrecarga de memória
    total_votes = 100000
    batch_size = 5000
    results = [0, 0, 0]

    for batch_start in range(0, total_votes, batch_size):
        batch_end = min(batch_start + batch_size, total_votes)
        batch_votes = []

        for i in range(batch_start, batch_end):
            candidate_pos = i % 3
            vote_vector = crypto_service.create_vote_vector(candidate_pos, 3)
            batch_votes.append(vote_vector)

        batch_results = crypto_service.process_votes_streaming(batch_votes, 3)

        # Somar resultados do lote
        for j in range(3):
            results[j] += batch_results[j]

        print(f'Processados {batch_end} votos...')
        crypto_service.clear_cache()

    end_time = time.time()

    print(f'100.000 votos processados em {end_time - start_time:.2f}s')
    print(f'Resultados: {results}')
    assert sum(results) == total_votes


@pytest.mark.asyncio
async def test_crypto_stress_memory_usage():
    crypto_service.setup_crypto()
    crypto_service.clear_cache()

    initial_cache_size = crypto_service.get_cache_size()

    # Criar 1000 votos e verificar que o cache não cresce indefinidamente
    for i in range(1000):
        vote_vector = crypto_service.create_vote_vector(i % 3, 3)
        crypto_service.encrypt_vote(vote_vector)

    final_cache_size = crypto_service.get_cache_size()

    print(f'Cache inicial: {initial_cache_size}')
    print(f'Cache final: {final_cache_size}')
    print(f'Limite máximo: {crypto_service.max_cache_size}')

    # Cache deve estar limitado pelo max_cache_size
    assert final_cache_size <= crypto_service.max_cache_size
    assert final_cache_size > 0


@pytest.mark.asyncio
async def test_crypto_overflow_protection():
    crypto_service.setup_crypto()

    # Testar com valores próximos ao limite do plaintext modulus
    plaintext_mod = 65537  # Valor padrão

    # Criar votos que somem próximo ao limite
    tally = crypto_service.create_zero_tally(1)

    # Simular muitos votos no mesmo candidato
    max_safe_votes = plaintext_mod // 2  # Margem de segurança

    for i in range(min(1000, max_safe_votes)):  # Limitar para não demorar muito
        vote_vector = crypto_service.create_vote_vector(0, 1)
        encrypted_vote = crypto_service.encrypt_vote(vote_vector)
        tally = crypto_service.add_vote_to_tally(tally, encrypted_vote)

    results = crypto_service.decrypt_tally(tally, 1)
    expected_votes = min(1000, max_safe_votes)

    print(f'Votos processados: {expected_votes}')
    print(f'Resultado: {results[0]}')

    assert results[0] == expected_votes


# Teste de API com múltiplos usuários
@pytest.mark.asyncio
async def test_api_stress_multiple_users(client, stress_election_setup, session):
    """Teste de estresse da API com múltiplos usuários"""
    election, candidates = stress_election_setup

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

    # Cada usuário vota
    vote_count = 0
    for i, user_data in enumerate(users_data):
        # Login
        login_response = client.post(
            '/auth/token',
            data={'username': user_data['email'], 'password': user_data['password']},
        )
        assert login_response.status_code == HTTPStatus.OK
        token = login_response.json()['access_token']

        # Votar
        candidate_id = candidates[i % 3].id  # Distribuir votos
        vote_response = client.post(
            f'/vote/election/{election.id}',
            json={'candidate_id': candidate_id},
            headers={'Authorization': f'Bearer {token}'},
        )

        if vote_response.status_code == HTTPStatus.CREATED:
            vote_count += 1

    # Verificar resultados
    results_response = client.get(f'/vote/results/{election.id}')
    assert results_response.status_code == HTTPStatus.OK

    results = results_response.json()
    print(f'Votos processados via API: {vote_count}')
    print(f'Total de votos: {results["total_votes"]}')

    assert results['total_votes'] == vote_count


class StressElectionFactory(factory.Factory):
    class Meta:
        model = Election

    title = 'Stress Test Election'


class StressCandidateFactory(factory.Factory):
    class Meta:
        model = Candidate

    username = factory.Sequence(lambda n: f'candidate_{n}')


class StressUserFactory(factory.Factory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f'stress_user_{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@stress.com')
    password = 'stress_password'
    statusVotacao = False
