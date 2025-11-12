from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.models import Election
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


@router.get('/{election_id}', status_code=HTTPStatus.OK, response_model=ElectionSchema)
async def get_election_by_id(election_id: int, session: Session):
    db_election = await session.scalar(
        select(Election).where(Election.id == election_id)
    )
    if not db_election:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='Election not found'
        )
    return db_election


@router.put('/{election_id}', status_code=HTTPStatus.OK, response_model=ElectionSchema)
async def update_election(
    election_id: int,
    election: ElectionSchema,
    session: Session,
):
    db_election = await session.scalar(
        select(Election).where(Election.id == election_id)
    )
    if not db_election:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='Election not found'
        )

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
    db_election = await session.scalar(
        select(Election).where(Election.id == election_id)
    )

    if not db_election:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Election not found'
        )

    await session.delete(db_election)
    await session.commit()

    return {'message': 'Election deleted'}
