"""
Regras de voto, lotes, decifragem e apuração.

Fluxo: cada voto é um vetor 1-hot cifrado, somado ao total da eleição
(caminho 1) e guardado no lote aberto. Ao completar LOTE_TAMANHO votos, ou ao
encerrar a eleição, o lote é fechado: seus votos são somados do zero num
subtotal (caminho 2), os comprovantes entram na cadeia de hashes e os votos
individuais são apagados. A apuração só publica o resultado se os dois
caminhos baterem.
"""

import asyncio
import hashlib
import json
import uuid
import weakref
from contextlib import asynccontextmanager
from http import HTTPStatus

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.crypto_service import crypto_service
from src.database import begin_immediate
from src.models import (
    HASH_LENGTH,
    Election,
    Election_Candidate,
    Election_Tally,
    ElectionStatus,
    Lot_Subtotal,
    Participation,
    Receipt,
    User,
    Vote_Election,
)
from src.settings import Settings

settings = Settings()

GENESIS_HASH = '0' * HASH_LENGTH

# Um lock por event loop (os testes criam um loop por teste)
_locks: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()


def _election_lock() -> asyncio.Lock:
    loop = asyncio.get_running_loop()
    lock = _locks.get(loop)
    if lock is None:
        lock = _locks[loop] = asyncio.Lock()
    return lock


@asynccontextmanager
async def serialized_transaction(session: AsyncSession):
    """
    Transação serializada para tudo que altera o total cifrado: um asyncio.Lock
    (o backend roda com 1 worker) mais BEGIN IMMEDIATE no SQLite. Em qualquer
    erro, desfaz tudo.
    """
    async with _election_lock():
        await begin_immediate(session)
        try:
            yield
        except BaseException:
            await session.rollback()
            raise


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def lot_hash(
    previous_hash: str,
    numero_lote: int,
    qtd_votos: int,
    receipt_hashes: list[str],
    encrypted_subtotal: bytes,
) -> str:
    """Elo da cadeia: liga o lote ao anterior, aos comprovantes e ao subtotal"""
    parts = [
        'TCC-LOTE-v1',
        previous_hash,
        str(numero_lote),
        str(qtd_votos),
        ','.join(sorted(receipt_hashes)),
        sha256_hex(encrypted_subtotal),
    ]
    return sha256_hex('|'.join(parts).encode())


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=HTTPStatus.CONFLICT, detail=detail)


async def get_tally(session: AsyncSession, election_id: int) -> Election_Tally | None:
    return await session.scalar(
        select(Election_Tally).where(Election_Tally.fk_election == election_id)
    )


async def has_votes(session: AsyncSession, election_id: int) -> bool:
    participation = await session.scalar(
        select(Participation).where(Participation.fk_election == election_id)
    )
    return participation is not None


# Abertura


async def initialize_election(session: AsyncSession, election: Election):
    """Ao abrir: fixa a posição de cada candidato e cria o total cifrado zero"""
    links = (
        await session.scalars(
            select(Election_Candidate)
            .where(Election_Candidate.fk_election == election.id)
            .order_by(Election_Candidate.id)
        )
    ).all()
    for position, link in enumerate(links):
        link.posicao = position

    total_candidates = len(links)
    session.add(
        Election_Tally(
            fk_election=election.id,
            encrypted_tally=crypto_service.serialize(
                crypto_service.zero(total_candidates)
            ),
            total_candidates=total_candidates,
        )
    )


# Voto


async def cast_vote(
    session: AsyncSession, election_id: int, user: User, candidate_id: int
) -> str:
    """Registra o voto e devolve o comprovante (SHA-256 do voto cifrado)"""
    async with serialized_transaction(session):
        election = await session.scalar(
            select(Election).where(Election.id == election_id)
        )
        if not election:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND, detail='Election not found'
            )
        if election.status != ElectionStatus.OPEN:
            raise _conflict('Election is not open for voting')

        link = await session.scalar(
            select(Election_Candidate).where(
                Election_Candidate.fk_election == election_id,
                Election_Candidate.fk_candidate == candidate_id,
            )
        )
        if not link:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Candidate not found in this election',
            )

        already_voted = await session.scalar(
            select(Participation).where(
                Participation.fk_user == user.id,
                Participation.fk_election == election_id,
            )
        )
        if already_voted:
            raise _conflict('User already voted in this election')

        tally = await get_tally(session, election_id)
        if tally is None or link.posicao is None:
            raise _conflict('Election was not initialized for voting')

        vector = crypto_service.create_vote_vector(link.posicao, tally.total_candidates)
        ciphertext = crypto_service.encrypt_vector(vector)

        # Prova ZK simulada: validada no momento do voto e não gravada
        zk_proof = crypto_service.generate_zk_proof(vector, ciphertext)
        if not crypto_service.verify_zk_proof(zk_proof, tally.total_candidates):
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST, detail='Invalid ZK proof for vote'
            )

        encrypted_vote = crypto_service.serialize(ciphertext)
        receipt = sha256_hex(encrypted_vote)

        session.add(Participation(fk_user=user.id, fk_election=election_id))
        session.add(
            Vote_Election(
                id=str(uuid.uuid4()),
                fk_election=election_id,
                encrypted_vote=encrypted_vote,
                receipt_hash=receipt,
            )
        )

        # Caminho 1: soma incremental, voto a voto
        total = crypto_service.add(
            crypto_service.deserialize(tally.encrypted_tally), ciphertext
        )
        tally.encrypted_tally = crypto_service.serialize(total)
        tally.total_votos += 1

        user.statusVotacao = True
        await session.flush()

        open_votes = await session.scalar(
            select(func.count())
            .select_from(Vote_Election)
            .where(Vote_Election.fk_election == election_id)
        )
        if open_votes >= settings.LOTE_TAMANHO:
            await close_lot(session, tally)

        await session.commit()

    return receipt


# Lotes


async def close_lot(session: AsyncSession, tally: Election_Tally) -> int | None:
    """Fecha o lote aberto; devolve o número do lote ou None se estava vazio"""
    votes = (
        await session.scalars(
            select(Vote_Election).where(Vote_Election.fk_election == tally.fk_election)
        )
    ).all()
    if not votes:
        return None

    # Caminho 2: soma recalculada do zero, lendo os votos do banco
    subtotal = crypto_service.zero(tally.total_candidates)
    for vote in votes:
        subtotal = crypto_service.add(
            subtotal, crypto_service.deserialize(vote.encrypted_vote)
        )
    encrypted_subtotal = crypto_service.serialize(subtotal)

    numero_lote = tally.lotes_fechados + 1
    receipt_hashes = sorted(vote.receipt_hash for vote in votes)
    hash_lote = lot_hash(
        tally.hash_ultimo_lote,
        numero_lote,
        len(votes),
        receipt_hashes,
        encrypted_subtotal,
    )

    session.add(
        Lot_Subtotal(
            fk_election=tally.fk_election,
            numero_lote=numero_lote,
            qtd_votos=len(votes),
            encrypted_subtotal=encrypted_subtotal,
            hash_lote=hash_lote,
        )
    )
    session.add_all([
        Receipt(
            receipt_hash=receipt_hash,
            fk_election=tally.fk_election,
            numero_lote=numero_lote,
        )
        for receipt_hash in receipt_hashes
    ])
    tally.lotes_fechados = numero_lote
    tally.hash_ultimo_lote = hash_lote

    await session.execute(
        delete(Vote_Election).where(Vote_Election.fk_election == tally.fk_election)
    )
    return numero_lote


async def close_open_lot(session: AsyncSession, election_id: int):
    """Fechamento final: nenhum voto individual fica no banco"""
    tally = await get_tally(session, election_id)
    if tally is not None:
        await close_lot(session, tally)


# Decifragem


async def decrypt_lots(
    session: AsyncSession, tally: Election_Tally, lotes: set[int]
) -> list[int]:
    """
    Única função que decifra conjuntos de lotes. Um conjunto parcial só é
    decifrado se ele e o seu complemento tiverem pelo menos
    LOTE_MINIMO_DECIFRAR votos, para impedir o ataque por diferença (total
    menos um conjunto quase completo revelaria os votos restantes). Votos
    individuais nunca são decifrados.
    """
    subtotals = (
        await session.scalars(
            select(Lot_Subtotal).where(Lot_Subtotal.fk_election == tally.fk_election)
        )
    ).all()
    all_lots = {subtotal.numero_lote for subtotal in subtotals}
    if not lotes <= all_lots:
        raise _conflict('Unknown lot for this election')

    chosen = [s for s in subtotals if s.numero_lote in lotes]
    qtd = sum(s.qtd_votos for s in chosen)
    complement = tally.total_votos - qtd
    minimum = settings.LOTE_MINIMO_DECIFRAR

    is_full_result = lotes == all_lots and complement == 0
    if not is_full_result and (qtd < minimum or complement < minimum):
        raise _conflict('Decryption not allowed for this set of lots')

    total = crypto_service.zero(tally.total_candidates)
    for subtotal in chosen:
        total = crypto_service.add(
            total, crypto_service.deserialize(subtotal.encrypted_subtotal)
        )
    return crypto_service.decrypt(total, tally.total_candidates)


# Cadeia de hashes


async def verify_chain(session: AsyncSession, tally: Election_Tally) -> bool:
    """Recalcula a cadeia do lote 1 ao último, conferindo comprovantes e subtotais"""
    subtotals = (
        await session.scalars(
            select(Lot_Subtotal)
            .where(Lot_Subtotal.fk_election == tally.fk_election)
            .order_by(Lot_Subtotal.numero_lote)
        )
    ).all()

    previous = GENESIS_HASH
    for expected_number, subtotal in enumerate(subtotals, start=1):
        if subtotal.numero_lote != expected_number:
            return False
        receipt_hashes = await _lot_receipts(
            session, tally.fk_election, subtotal.numero_lote
        )
        if len(receipt_hashes) != subtotal.qtd_votos:
            return False
        recalculated = lot_hash(
            previous,
            subtotal.numero_lote,
            subtotal.qtd_votos,
            receipt_hashes,
            subtotal.encrypted_subtotal,
        )
        if recalculated != subtotal.hash_lote:
            return False
        previous = subtotal.hash_lote

    return previous == tally.hash_ultimo_lote and len(subtotals) == tally.lotes_fechados


async def _lot_receipts(
    session: AsyncSession, election_id: int, numero_lote: int
) -> list[str]:
    return list(
        (
            await session.scalars(
                select(Receipt.receipt_hash)
                .where(
                    Receipt.fk_election == election_id,
                    Receipt.numero_lote == numero_lote,
                )
                .order_by(Receipt.receipt_hash)
            )
        ).all()
    )


# Apuração


async def tally_election(session: AsyncSession, election: Election) -> dict:
    """
    Dupla contagem: o total acumulado voto a voto precisa ser igual à soma dos
    subtotais dos lotes, as contagens precisam bater e a cadeia de hashes
    precisa estar íntegra. Se algo falhar, nada é publicado.
    """
    tally = await get_tally(session, election.id)
    if tally is None:
        raise _conflict('Election was not initialized for voting')

    open_votes = await session.scalar(
        select(func.count())
        .select_from(Vote_Election)
        .where(Vote_Election.fk_election == election.id)
    )
    if open_votes:
        raise _conflict('Election still has an open lot')

    try:
        accumulated = crypto_service.decrypt(
            crypto_service.deserialize(tally.encrypted_tally), tally.total_candidates
        )
        from_lots = await decrypt_lots(session, tally, await _all_lots(session, tally))
    except HTTPException:
        raise
    except Exception:
        raise _conflict('Tally verification failed: invalid ciphertext')

    if accumulated != from_lots:
        raise _conflict(
            'Tally verification failed: accumulated total differs from the sum of '
            'lot subtotals; audit the lots'
        )

    participations = await session.scalar(
        select(func.count())
        .select_from(Participation)
        .where(Participation.fk_election == election.id)
    )
    lot_votes = await session.scalar(
        select(func.coalesce(func.sum(Lot_Subtotal.qtd_votos), 0)).where(
            Lot_Subtotal.fk_election == election.id
        )
    )
    if not (sum(accumulated) == tally.total_votos == participations == lot_votes):
        raise _conflict('Tally verification failed: vote counts do not match')

    if not await verify_chain(session, tally):
        raise _conflict('Tally verification failed: lot hash chain is broken')

    links = (
        await session.scalars(
            select(Election_Candidate)
            .where(Election_Candidate.fk_election == election.id)
            .order_by(Election_Candidate.posicao)
        )
    ).all()
    candidates = []
    for link in links:
        candidate = await session.scalar(select(User).where(User.id == link.fk_candidate))
        candidates.append({
            'id': candidate.id,
            'username': candidate.username,
            'is_deleted': candidate.is_deleted,
            'votes': accumulated[link.posicao],
        })

    result = {'candidates': candidates, 'total_votes': sum(accumulated)}
    tally.resultado_json = json.dumps(result)
    return {'election_id': election.id, **result}


async def _all_lots(session: AsyncSession, tally: Election_Tally) -> set[int]:
    return set(
        (
            await session.scalars(
                select(Lot_Subtotal.numero_lote).where(
                    Lot_Subtotal.fk_election == tally.fk_election
                )
            )
        ).all()
    )


async def published_results(session: AsyncSession, election_id: int) -> dict:
    """Resultado gravado na apuração; só atualiza se a conta foi excluída depois"""
    tally = await get_tally(session, election_id)
    result = json.loads(tally.resultado_json)
    for candidate in result['candidates']:
        user = await session.scalar(select(User).where(User.id == candidate['id']))
        candidate['is_deleted'] = user.is_deleted if user else True
    return {'election_id': election_id, **result}


# Comprovantes e auditoria


async def receipt_status(session: AsyncSession, election_id: int, receipt: str):
    pending = await session.scalar(
        select(Vote_Election.id).where(
            Vote_Election.fk_election == election_id,
            Vote_Election.receipt_hash == receipt,
        )
    )
    if pending:
        return {'status': 'pending', 'lote': None}

    registered = await session.scalar(
        select(Receipt).where(
            Receipt.fk_election == election_id, Receipt.receipt_hash == receipt
        )
    )
    if registered:
        return {'status': 'registered', 'lote': registered.numero_lote}

    return None


async def audit_report(session: AsyncSession, election_id: int) -> dict:
    tally = await get_tally(session, election_id)
    if tally is None:
        return {
            'election_id': election_id,
            'total_votos': 0,
            'lots': [],
            'chain_valid': True,
        }

    subtotals = (
        await session.scalars(
            select(Lot_Subtotal)
            .where(Lot_Subtotal.fk_election == election_id)
            .order_by(Lot_Subtotal.numero_lote)
        )
    ).all()
    lots = [
        {
            'numero_lote': subtotal.numero_lote,
            'qtd_votos': subtotal.qtd_votos,
            'hash_lote': subtotal.hash_lote,
            'receipts': await _lot_receipts(session, election_id, subtotal.numero_lote),
        }
        for subtotal in subtotals
    ]
    return {
        'election_id': election_id,
        'total_votos': tally.total_votos,
        'lots': lots,
        'chain_valid': await verify_chain(session, tally),
    }
