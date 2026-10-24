"""Votos persistentes por lote (LOTE_TAMANHO=5 e LOTE_MINIMO_DECIFRAR=2 nos testes)"""

import asyncio
import hashlib
from http import HTTPStatus

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from src import voting
from src.app import app
from src.crypto_service import crypto_service
from src.database import get_session
from src.models import (
    HASH_LENGTH,
    Election,
    Election_Tally,
    Lot_Subtotal,
    Participation,
    Receipt,
    User,
    Vote_Election,
    table_registry,
)
from src.security import create_access_token, get_password_hash
from src.settings import Settings
from tests.test_elections import _create_candidate

LOT_SIZE = 5


def _admin_headers(admin_token):
    return {'Authorization': f'Bearer {admin_token}'}


def _setup_election(client, election, admin_token, candidates=2):
    """Cria e vincula candidatos, abre a votação e devolve os ids na ordem da cédula"""
    headers = _admin_headers(admin_token)
    ids = [
        _create_candidate(client, headers, f'cand_{election.id}_{i}')
        for i in range(candidates)
    ]
    for candidate_id in ids:
        client.post(
            f'/elections/{election.id}/candidates/{candidate_id}', headers=headers
        )
    response = client.post(f'/elections/{election.id}/open', headers=headers)
    assert response.status_code == HTTPStatus.OK
    return ids


def _voter_tokens(client, quantity, prefix='eleitor'):
    tokens = []
    for i in range(quantity):
        email = f'{prefix}{i}@test.com'
        client.post(
            '/users',
            json={
                'username': f'{prefix}{i}',
                'email': email,
                'password': 'testtest',
                'statusVotacao': False,
            },
        )
        tokens.append(create_access_token(data={'sub': email}))
    return tokens


def _vote(client, election_id, candidate_id, token):
    return client.post(
        f'/vote/election/{election_id}',
        headers={'Authorization': f'Bearer {token}'},
        json={'candidate_id': candidate_id},
    )


def _close_and_tally(client, election_id, admin_token):
    headers = _admin_headers(admin_token)
    client.post(f'/elections/{election_id}/close', headers=headers)
    return client.post(f'/elections/{election_id}/tally', headers=headers)


async def _count(session, model, election_id):
    session.expire_all()
    return await session.scalar(
        select(func.count()).select_from(model).where(model.fk_election == election_id)
    )


# 1 e 2: modelo de dados


@pytest.mark.asyncio
async def test_vote_stores_only_bytes_and_receipt(client, session, election, admin_token):
    candidates = _setup_election(client, election, admin_token)
    (token,) = _voter_tokens(client, 1)

    response = _vote(client, election.id, candidates[0], token)

    assert response.status_code == HTTPStatus.CREATED
    receipt = response.json()['receipt']
    assert len(receipt) == HASH_LENGTH
    assert int(receipt, 16) >= 0
    assert 'vote_id' not in response.json()

    vote = await session.scalar(select(Vote_Election))
    assert isinstance(vote.encrypted_vote, bytes)
    assert hashlib.sha256(vote.encrypted_vote).hexdigest() == receipt
    assert await _count(session, Participation, election.id) == 1

    columns = {
        row[1] for row in (await session.execute(text('PRAGMA table_info(votos)'))).all()
    }
    assert columns == {'id', 'fk_election', 'encrypted_vote', 'receipt_hash'}


@pytest.mark.asyncio
async def test_vote_tables_are_without_rowid(session):
    for table in ('votos', 'participacoes', 'comprovantes'):
        sql = await session.scalar(
            text('SELECT sql FROM sqlite_master WHERE name = :name'), {'name': table}
        )
        assert 'WITHOUT ROWID' in sql, table


# 3: voto duplo


def test_double_vote_should_return_conflict(client, election, admin_token):
    candidates = _setup_election(client, election, admin_token)
    (token,) = _voter_tokens(client, 1)
    _vote(client, election.id, candidates[0], token)

    response = _vote(client, election.id, candidates[1], token)

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {'detail': 'User already voted in this election'}


# 4 e 5: fechamento de lote


@pytest.mark.asyncio
async def test_fifth_vote_closes_lot(client, session, election, admin_token):
    candidates = _setup_election(client, election, admin_token)
    tokens = _voter_tokens(client, LOT_SIZE)

    for i, token in enumerate(tokens):
        assert _vote(client, election.id, candidates[i % 2], token).status_code == (
            HTTPStatus.CREATED
        )

    lot = await session.scalar(select(Lot_Subtotal))
    assert lot.numero_lote == 1
    assert lot.qtd_votos == LOT_SIZE
    assert await _count(session, Receipt, election.id) == LOT_SIZE
    assert await _count(session, Vote_Election, election.id) == 0


@pytest.mark.asyncio
async def test_close_election_closes_partial_lot(client, session, election, admin_token):
    candidates = _setup_election(client, election, admin_token)
    partial = LOT_SIZE - 2
    for token in _voter_tokens(client, partial):
        _vote(client, election.id, candidates[0], token)

    client.post(f'/elections/{election.id}/close', headers=_admin_headers(admin_token))

    lot = await session.scalar(select(Lot_Subtotal))
    assert lot.qtd_votos == partial
    assert await _count(session, Vote_Election, election.id) == 0


def test_close_election_without_votes_creates_no_lot(client, election, admin_token):
    _setup_election(client, election, admin_token)

    response = _close_and_tally(client, election.id, admin_token)

    assert response.status_code == HTTPStatus.OK
    assert response.json()['total_votes'] == 0
    audit = client.get(f'/elections/{election.id}/audit').json()
    assert audit['lots'] == []


# 6 e 7: apuração


def test_tally_after_simulated_restart(client, election, admin_token):
    candidates = _setup_election(client, election, admin_token)
    expected = [4, 3]  # 7 votos: um lote fechado e um aberto
    choices = [0] * expected[0] + [1] * expected[1]
    for token, choice in zip(_voter_tokens(client, len(choices)), choices):
        _vote(client, election.id, candidates[choice], token)

    # Reinício: some todo o estado em memória e as chaves voltam de KEYS_DIR
    crypto_service.reset()
    crypto_service.load_or_create_keys(Settings().KEYS_DIR)

    response = _close_and_tally(client, election.id, admin_token)

    assert response.status_code == HTTPStatus.OK
    assert [c['votes'] for c in response.json()['candidates']] == expected


def test_tally_with_several_lots_and_candidates(client, election, admin_token):
    candidates = _setup_election(client, election, admin_token, candidates=3)
    expected = [6, 4, 2]  # 12 votos: lotes de 5, 5 e 2
    choices = [0] * expected[0] + [1] * expected[1] + [2] * expected[2]
    for token, choice in zip(_voter_tokens(client, len(choices)), choices):
        assert _vote(client, election.id, candidates[choice], token).status_code == (
            HTTPStatus.CREATED
        )

    response = _close_and_tally(client, election.id, admin_token)

    assert response.status_code == HTTPStatus.OK
    assert [c['votes'] for c in response.json()['candidates']] == expected
    assert response.json()['total_votes'] == sum(expected)
    audit = client.get(f'/elections/{election.id}/audit').json()
    assert [lot['qtd_votos'] for lot in audit['lots']] == [5, 5, 2]
    assert audit['chain_valid'] is True
    assert client.get(f'/vote/results/{election.id}').json() == response.json()


# 8 e 9: adulteração


async def _closed_election_with_votes(client, election, admin_token, votes=6):
    candidates = _setup_election(client, election, admin_token)
    for i, token in enumerate(_voter_tokens(client, votes)):
        _vote(client, election.id, candidates[i % 2], token)
    client.post(f'/elections/{election.id}/close', headers=_admin_headers(admin_token))


@pytest.mark.asyncio
async def test_tampered_tally_is_refused(client, session, election, admin_token):
    await _closed_election_with_votes(client, election, admin_token)
    other = crypto_service.serialize(crypto_service.encrypt_vector([1, 0]))
    await session.execute(
        update(Election_Tally)
        .where(Election_Tally.fk_election == election.id)
        .values(encrypted_tally=other)
    )
    await session.commit()

    response = client.post(
        f'/elections/{election.id}/tally', headers=_admin_headers(admin_token)
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert 'accumulated total differs' in response.json()['detail']
    assert client.get(f'/elections/{election.id}').json()['status'] == 'closed'


@pytest.mark.asyncio
async def test_tampered_subtotal_is_refused(client, session, election, admin_token):
    await _closed_election_with_votes(client, election, admin_token)
    other = crypto_service.serialize(crypto_service.encrypt_vector([5, 0]))
    await session.execute(
        update(Lot_Subtotal)
        .where(Lot_Subtotal.fk_election == election.id, Lot_Subtotal.numero_lote == 1)
        .values(encrypted_subtotal=other)
    )
    await session.commit()

    response = client.post(
        f'/elections/{election.id}/tally', headers=_admin_headers(admin_token)
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert client.get(f'/elections/{election.id}').json()['status'] == 'closed'


@pytest.mark.asyncio
async def test_tampered_receipt_breaks_chain(client, session, election, admin_token):
    await _closed_election_with_votes(client, election, admin_token)
    receipt = await session.scalar(select(Receipt.receipt_hash).limit(1))
    await session.execute(
        update(Receipt)
        .where(Receipt.receipt_hash == receipt)
        .values(receipt_hash='f' * 64)
    )
    await session.commit()

    audit = client.get(f'/elections/{election.id}/audit').json()
    response = client.post(
        f'/elections/{election.id}/tally', headers=_admin_headers(admin_token)
    )

    assert audit['chain_valid'] is False
    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {
        'detail': 'Tally verification failed: lot hash chain is broken'
    }


@pytest.mark.asyncio
async def test_tampered_lot_hash_breaks_chain(client, session, election, admin_token):
    await _closed_election_with_votes(client, election, admin_token)
    await session.execute(
        update(Lot_Subtotal)
        .where(Lot_Subtotal.fk_election == election.id, Lot_Subtotal.numero_lote == 1)
        .values(hash_lote='0' * 64)
    )
    await session.commit()

    assert client.get(f'/elections/{election.id}/audit').json()['chain_valid'] is False
    response = client.post(
        f'/elections/{election.id}/tally', headers=_admin_headers(admin_token)
    )
    assert response.status_code == HTTPStatus.CONFLICT


# 10: regra de decifragem


@pytest.mark.asyncio
async def test_decrypt_lots_rule(client, session, election, admin_token):
    # 6 votos: lote 1 com 5 e lote 2 com 1 (mínimo de 2 nos testes)
    await _closed_election_with_votes(client, election, admin_token, votes=6)
    session.expire_all()
    tally = await voting.get_tally(session, election.id)

    with pytest.raises(HTTPException, match='not allowed'):
        await voting.decrypt_lots(session, tally, {2})  # conjunto com 1 voto
    with pytest.raises(HTTPException, match='not allowed'):
        await voting.decrypt_lots(session, tally, {1})  # complemento com 1 voto

    assert await voting.decrypt_lots(session, tally, {1, 2}) == [3, 3]


# 11: comprovante


def test_receipt_status(client, election, admin_token):
    candidates = _setup_election(client, election, admin_token)
    tokens = _voter_tokens(client, LOT_SIZE)
    receipt = _vote(client, election.id, candidates[0], tokens[0]).json()['receipt']

    pending = client.get(f'/vote/receipt/{election.id}/{receipt}')
    for token in tokens[1:]:
        _vote(client, election.id, candidates[1], token)
    registered = client.get(f'/vote/receipt/{election.id}/{receipt}')
    missing = client.get(f'/vote/receipt/{election.id}/{"a" * 64}')

    assert pending.json() == {'status': 'pending', 'lote': None}
    assert registered.json() == {'status': 'registered', 'lote': 1}
    assert missing.status_code == HTTPStatus.NOT_FOUND


def test_audit_lists_sorted_receipts_without_ciphertexts(client, election, admin_token):
    candidates = _setup_election(client, election, admin_token)
    for token in _voter_tokens(client, LOT_SIZE):
        _vote(client, election.id, candidates[0], token)

    audit = client.get(f'/elections/{election.id}/audit').json()

    (lot,) = audit['lots']
    assert lot['receipts'] == sorted(lot['receipts'])
    assert set(lot) == {'numero_lote', 'qtd_votos', 'hash_lote', 'receipts'}


# 12: concorrência


@pytest.mark.asyncio
async def test_concurrent_votes(tmp_path):
    """Votos simultâneos em banco de arquivo: nenhum voto pode sobrescrever outro"""
    crypto_service.load_or_create_keys(Settings().KEYS_DIR)
    engine = create_async_engine(f'sqlite+aiosqlite:///{tmp_path}/concorrencia.db')
    async with engine.begin() as conn:
        await conn.run_sync(table_registry.metadata.create_all)

    async def new_session():
        async with AsyncSession(engine, expire_on_commit=False) as session:
            yield session

    voters = 8
    async with AsyncSession(engine, expire_on_commit=False) as session:
        password = get_password_hash('x')
        admin = User(
            username='adm', email='adm@test.com', password=password, is_admin=True
        )
        cands = [
            User(
                username=f'c{i}',
                email=f'c{i}@test.com',
                password=password,
                is_candidate=True,
            )
            for i in range(2)
        ]
        users = [
            User(username=f'v{i}', email=f'v{i}@test.com', password=password)
            for i in range(voters)
        ]
        election = Election(title='Concorrência')
        session.add_all([admin, *cands, *users, election])
        await session.commit()
        ids = {'election': election.id, 'cands': [c.id for c in cands]}
        emails = [u.email for u in users]

    app.dependency_overrides[get_session] = new_session
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url='http://test'
        ) as ac:
            admin_headers = {
                'Authorization': f'Bearer {create_access_token({"sub": "adm@test.com"})}'
            }
            for cand in ids['cands']:
                await ac.post(
                    f'/elections/{ids["election"]}/candidates/{cand}',
                    headers=admin_headers,
                )
            await ac.post(f'/elections/{ids["election"]}/open', headers=admin_headers)

            responses = await asyncio.gather(
                *(
                    ac.post(
                        f'/vote/election/{ids["election"]}',
                        headers={
                            'Authorization': f'Bearer {create_access_token({"sub": e})}'
                        },
                        json={'candidate_id': ids['cands'][i % 2]},
                    )
                    for i, e in enumerate(emails)
                )
            )
            assert all(r.status_code == HTTPStatus.CREATED for r in responses)

            await ac.post(f'/elections/{ids["election"]}/close', headers=admin_headers)
            tally = await ac.post(
                f'/elections/{ids["election"]}/tally', headers=admin_headers
            )
    finally:
        app.dependency_overrides.clear()

    async with AsyncSession(engine) as session:
        total = await session.scalar(select(Election_Tally.total_votos))
    await engine.dispose()

    assert total == voters
    assert tally.status_code == HTTPStatus.OK
    assert [c['votes'] for c in tally.json()['candidates']] == [voters // 2] * 2
