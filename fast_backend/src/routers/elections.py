from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.models import (
    Election,
    Election_Candidate,
    ElectionStatus,
    User,
    Vote_Election,
)
from src.routers.events import notify_election_change
from src.routers.vote import compute_results
from src.schemas import (
    CandidatePublic,
    ElectionList,
    ElectionPublic,
    ElectionResultsSchema,
    ElectionSchema,
    ElectionWithCandidates,
    FilterPage,
    Message,
)
from src.security import get_current_admin

router = APIRouter(prefix='/elections', tags=['elections'])
Session = Annotated[AsyncSession, Depends(get_session)]
CurrentAdmin = Annotated[User, Depends(get_current_admin)]


@router.post('/', status_code=HTTPStatus.CREATED, response_model=ElectionPublic)
async def create_election(
    election: ElectionSchema,
    session: Session,
    admin: CurrentAdmin,
):
    db_election = Election(title=election.title)
    session.add(db_election)
    await session.commit()
    await session.refresh(db_election)
    await notify_election_change()

    return db_election


@router.get('/', status_code=HTTPStatus.OK, response_model=ElectionList)
async def get_elections(
    session: Session,
    filter_elections: Annotated[FilterPage, Query()],
):
    query = await session.scalars(
        select(Election).offset(filter_elections.offset).limit(filter_elections.limit)
    )

    elections = query.all()
    return {'elections': elections}


@router.get('/{election_id}', status_code=HTTPStatus.OK, response_model=ElectionPublic)
async def get_election_by_id(election_id: int, session: Session):
    db_election = await session.scalar(select(Election).where(Election.id == election_id))
    if not db_election:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='Election not found')
    return db_election


@router.put('/{election_id}', status_code=HTTPStatus.OK, response_model=ElectionPublic)
async def update_election(
    election_id: int,
    election: ElectionSchema,
    session: Session,
    admin: CurrentAdmin,
):
    db_election = await session.scalar(select(Election).where(Election.id == election_id))
    if not db_election:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='Election not found')

    try:
        db_election.title = election.title
        await session.commit()
        await session.refresh(db_election)
        await notify_election_change()

        return db_election

    except IntegrityError:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Title already exist',
        )


@router.delete('/{election_id}', status_code=HTTPStatus.OK, response_model=Message)
async def delete_election(
    election_id: int,
    session: Session,
    admin: CurrentAdmin,
):
    db_election = await session.scalar(select(Election).where(Election.id == election_id))

    if not db_election:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='Election not found')

    # Eleição apurada é mantida como histórico
    if db_election.status == ElectionStatus.TALLIED:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Tallied elections cannot be deleted',
        )

    await session.delete(db_election)
    await session.commit()
    await notify_election_change()

    return {'message': 'Election deleted'}


@router.post(
    '/{election_id}/candidates/{candidate_id}',
    status_code=HTTPStatus.CREATED,
    response_model=ElectionWithCandidates,
)
async def add_candidate_to_election(
    election_id: int, candidate_id: int, session: Session, admin: CurrentAdmin
):
    election = await _get_open_election(election_id, session)

    # Após o primeiro voto a lista de candidatos não recebe novos nomes
    first_vote = await session.scalar(
        select(Vote_Election)
        .join(Election_Candidate)
        .where(Election_Candidate.fk_election == election_id)
    )
    if first_vote:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Election already has votes',
        )

    candidate = await session.scalar(
        select(User).where(User.id == candidate_id, User.is_candidate)
    )
    if not candidate:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='Candidate not found'
        )

    existing = await session.scalar(
        select(Election_Candidate).where(
            Election_Candidate.fk_election == election_id,
            Election_Candidate.fk_candidate == candidate_id,
        )
    )
    if existing:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Candidate already associated with this election',
        )

    db_election_candidate = Election_Candidate(
        fk_election=election_id, fk_candidate=candidate_id
    )
    session.add(db_election_candidate)
    await session.commit()
    await notify_election_change()

    return await _election_with_candidates(election, session)


@router.get(
    '/{election_id}/candidates',
    status_code=HTTPStatus.OK,
    response_model=ElectionWithCandidates,
)
async def get_election_with_candidates_by_id(election_id: int, session: Session):
    election = await session.scalar(select(Election).where(Election.id == election_id))
    if not election:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='Election not found')

    return await _election_with_candidates(election, session)


@router.delete(
    '/{election_id}/candidates/{candidate_id}',
    status_code=HTTPStatus.OK,
    response_model=ElectionWithCandidates,
)
async def remove_candidate_from_election(
    election_id: int, candidate_id: int, session: Session, admin: CurrentAdmin
):
    election = await _get_open_election(election_id, session)

    election_candidate = await session.scalar(
        select(Election_Candidate).where(
            Election_Candidate.fk_election == election_id,
            Election_Candidate.fk_candidate == candidate_id,
        )
    )
    if not election_candidate:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Candidate not found in this election',
        )

    # Remover o vínculo apagaria votos já registrados para o candidato
    has_votes = await session.scalar(
        select(Vote_Election).where(
            Vote_Election.fk_election_candidate == election_candidate.id
        )
    )
    if has_votes:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Candidate already has votes in this election',
        )

    await session.delete(election_candidate)
    await session.commit()
    await notify_election_change()

    return await _election_with_candidates(election, session)


@router.post(
    '/{election_id}/close', status_code=HTTPStatus.OK, response_model=ElectionPublic
)
async def close_election(election_id: int, session: Session, admin: CurrentAdmin):
    # Encerra a votação: a partir daqui nenhum voto novo é aceito
    election = await _get_open_election(election_id, session)

    election.status = ElectionStatus.CLOSED
    await session.commit()
    await session.refresh(election)
    await notify_election_change()

    return election


@router.post(
    '/{election_id}/tally',
    status_code=HTTPStatus.OK,
    response_model=ElectionResultsSchema,
)
async def tally_election(election_id: int, session: Session, admin: CurrentAdmin):
    # Apura (descriptografa a soma homomórfica) e publica o resultado
    election = await session.scalar(select(Election).where(Election.id == election_id))
    if not election:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='Election not found')

    if election.status == ElectionStatus.OPEN:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Election must be closed before tallying',
        )
    if election.status == ElectionStatus.TALLIED:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT, detail='Election already tallied'
        )

    results = await compute_results(election_id, session)

    election.status = ElectionStatus.TALLIED
    await session.commit()
    await notify_election_change()

    return results


async def _get_open_election(election_id: int, session: AsyncSession):
    election = await session.scalar(select(Election).where(Election.id == election_id))
    if not election:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='Election not found')

    if election.status != ElectionStatus.OPEN:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT, detail='Election is not open'
        )

    return election


async def _election_with_candidates(election: Election, session: AsyncSession):
    candidates_query = await session.scalars(
        select(User)
        .join(Election_Candidate, User.id == Election_Candidate.fk_candidate)
        .where(Election_Candidate.fk_election == election.id)
    )
    candidates = [
        CandidatePublic(id=c.id, username=c.username) for c in candidates_query.all()
    ]

    return ElectionWithCandidates(
        id=election.id,
        title=election.title,
        status=election.status,
        candidates=candidates,
    )
