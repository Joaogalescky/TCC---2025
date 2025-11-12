from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.models import Candidate
from src.schemas import (
    CandidateList,
    CandidatePublic,
    CandidateSchema,
    FilterPage,
    Message,
)

router = APIRouter(prefix='/candidates', tags=['candidates'])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.post('/', status_code=HTTPStatus.CREATED, response_model=CandidatePublic)
async def create_candidate(candidate: CandidateSchema, session: Session):

    db_candidate = await session.scalar(
        select(Candidate).where((Candidate.username == candidate.username))
    )

    if db_candidate:
        if db_candidate.username == candidate.username:
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='Username already exist',
            )

    db_candidate = Candidate(username=candidate.username)

    session.add(db_candidate)
    await session.commit()
    await session.refresh(db_candidate)

    return db_candidate


@router.get('/', status_code=HTTPStatus.OK, response_model=CandidateList)
async def get_candidates(
    session: Session, filter_candidates: Annotated[FilterPage, Query()]
):
    query = await session.scalars(
        select(Candidate).offset(filter_candidates.offset).limit(filter_candidates.limit)
    )
    candidates = query.all()
    return {'candidates': candidates}


@router.get('/{candidate_id}', status_code=HTTPStatus.OK, response_model=CandidatePublic)
async def get_candidate_by_id(candidate_id: int, session: Session):
    db_candidate = await session.scalar(
        select(Candidate).where(Candidate.id == candidate_id)
    )
    if not db_candidate:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='Candidate not found'
        )
    return db_candidate


@router.put('/{candidate_id}', status_code=HTTPStatus.OK, response_model=CandidatePublic)
async def update_candidate(
    candidate_id: int,
    candidate: CandidateSchema,
    session: Session,
):
    db_candidate = await session.scalar(
        select(Candidate).where(Candidate.id == candidate_id)
    )
    if not db_candidate:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='Candidate not found'
        )

    try:
        db_candidate.username = candidate.username
        await session.commit()
        await session.refresh(db_candidate)

        return db_candidate

    except IntegrityError:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Username already exist',
        )


@router.delete('/{candidate_id}', status_code=HTTPStatus.OK, response_model=Message)
async def delete_candidate(
    candidate_id: int,
    session: Session,
):
    db_candidate = await session.scalar(
        select(Candidate).where(Candidate.id == candidate_id)
    )
    if not db_candidate:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='Candidate not found'
        )

    await session.delete(db_candidate)
    await session.commit()

    return {'message': 'Candidate deleted'}
