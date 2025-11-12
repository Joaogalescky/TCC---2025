from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.models import Candidate, Election, Election_Candidate
from src.schemas import (
    ElectionList,
    ElectionPublic,
    ElectionSchema,
    FilterPage,
    Message,
)

router = APIRouter(prefix='/elections', tags=['elections'])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.post('/', status_code=HTTPStatus.CREATED, response_model=ElectionPublic)
async def create_election(
    election: ElectionSchema,
    session: Session,
):
    db_election = Election(title=election.title)
    session.add(db_election)
    await session.commit()
    await session.refresh(db_election)

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
):
    db_election = await session.scalar(select(Election).where(Election.id == election_id))
    if not db_election:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='Election not found')

    try:
        db_election.title = election.title
        await session.commit()
        await session.refresh(db_election)

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
):
    db_election = await session.scalar(select(Election).where(Election.id == election_id))

    if not db_election:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='Election not found')

    await session.delete(db_election)
    await session.commit()

    return {'message': 'Election deleted'}


@router.post('/{election_id}/candidates/{candidate_id}', status_code=HTTPStatus.CREATED, response_model=Message)
async def add_candidate_to_election(election_id: int, candidate_id: int, session: Session):
    """Associa um candidato a uma eleição"""

    # Verificar se eleição existe
    election = await session.scalar(select(Election).where(Election.id == election_id))
    if not election:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='Election not found')

    # Verificar se candidato existe
    candidate = await session.scalar(select(Candidate).where(Candidate.id == candidate_id))
    if not candidate:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='Candidate not found')

    # Verificar se associação já existe
    existing = await session.scalar(
        select(Election_Candidate).where(
            Election_Candidate.fk_election == election_id,
            Election_Candidate.fk_candidate == candidate_id
        )
    )
    if existing:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Candidate already associated with this election'
        )

    # Criar associação
    election_candidate = Election_Candidate(
        fk_election=election_id,
        fk_candidate=candidate_id
    )
    session.add(election_candidate)
    await session.commit()

    return {'message': 'Candidate added to election'}
