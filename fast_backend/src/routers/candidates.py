from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.models import User
from src.schemas import CandidateList, CandidatePublic, FilterPage

# Candidatos são usuários marcados pelo administrador (PATCH /users/{id}/candidate)
router = APIRouter(prefix='/candidates', tags=['candidates'])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.get('/', status_code=HTTPStatus.OK, response_model=CandidateList)
async def get_candidates(
    session: Session, filter_candidates: Annotated[FilterPage, Query()]
):
    query = await session.scalars(
        select(User)
        .where(User.is_candidate, User.deleted_at.is_(None))
        .offset(filter_candidates.offset)
        .limit(filter_candidates.limit)
    )
    candidates = query.all()
    return {'candidates': candidates}


@router.get('/{candidate_id}', status_code=HTTPStatus.OK, response_model=CandidatePublic)
async def get_candidate_by_id(candidate_id: int, session: Session):
    db_candidate = await session.scalar(
        select(User).where(
            User.id == candidate_id, User.is_candidate, User.deleted_at.is_(None)
        )
    )
    if not db_candidate:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='Candidate not found'
        )
    return db_candidate
