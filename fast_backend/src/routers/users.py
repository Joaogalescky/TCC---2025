from datetime import datetime
from http import HTTPStatus
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, select
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
from src.schemas import (
    CandidateStatusSchema,
    FilterPage,
    Message,
    UserList,
    UserPublic,
    UserSchema,
)
from src.security import get_current_admin, get_current_user, get_password_hash

router = APIRouter(prefix='/users', tags=['users'])
Session = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentAdmin = Annotated[User, Depends(get_current_admin)]


@router.post('/', status_code=HTTPStatus.CREATED, response_model=UserPublic)
async def create_user(user: UserSchema, session: Session):
    db_user = await session.scalar(
        select(User).where((User.username == user.username) | (User.email == user.email))
    )

    if db_user:
        if db_user.username == user.username:
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='Username already exists',
            )
        elif db_user.email == user.email:
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='Email already exists',
            )

    hashed_password = get_password_hash(user.password)

    db_user = User(
        username=user.username,
        password=hashed_password,
        email=user.email,
        statusVotacao=user.statusVotacao,
    )
    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)

    return db_user


@router.get('/', status_code=HTTPStatus.OK, response_model=UserList)
async def get_users(session: Session, filter_users: Annotated[FilterPage, Query()]):
    query = await session.scalars(
        select(User).offset(filter_users.offset).limit(filter_users.limit)
    )
    users = query.all()
    return {'users': users}


@router.get('/me', status_code=HTTPStatus.OK, response_model=UserPublic)
async def get_me(current_user: CurrentUser):
    return current_user


@router.get('/{user_id}', status_code=HTTPStatus.OK, response_model=UserPublic)
async def get_user_by_id(user_id: int, session: Session):
    db_user = await session.scalar(select(User).where(User.id == user_id))
    if not db_user:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='User not found')
    return db_user


@router.patch(
    '/{user_id}/candidate', status_code=HTTPStatus.OK, response_model=UserPublic
)
async def set_candidate_status(
    user_id: int,
    status: CandidateStatusSchema,
    session: Session,
    admin: CurrentAdmin,
):
    db_user = await session.scalar(select(User).where(User.id == user_id))
    if not db_user:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='User not found')

    if db_user.is_deleted:
        raise HTTPException(status_code=HTTPStatus.CONFLICT, detail='User is deleted')

    if not status.is_candidate:
        linked = await session.scalar(
            select(Election_Candidate).where(Election_Candidate.fk_candidate == user_id)
        )
        if linked:
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='Candidate is linked to an election',
            )

    db_user.is_candidate = status.is_candidate
    await session.commit()
    await session.refresh(db_user)
    await notify_election_change()

    return db_user


@router.put('/{user_id}', status_code=HTTPStatus.OK, response_model=UserPublic)
async def update_user(
    user_id: int,
    user: UserSchema,
    session: Session,
    current_user: CurrentUser,
):
    if current_user.id != user_id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail='Not enough permissions'
        )

    try:
        current_user.username = user.username
        current_user.password = get_password_hash(user.password)
        current_user.email = user.email
        current_user.statusVotacao = user.statusVotacao
        await session.commit()
        await session.refresh(current_user)

        return current_user

    except IntegrityError:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Username or Email already exists',
        )


@router.patch('/{user_id}', status_code=HTTPStatus.OK, response_model=UserPublic)
async def update_user_partial(
    user_id: int,
    user: UserSchema,
    session: Session,
    current_user: CurrentUser,
):
    if current_user.id != user_id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail='Not enough permissions'
        )

    try:
        if user.username is not None:
            current_user.username = user.username
        if user.password is not None:
            current_user.password = get_password_hash(user.password)
        if user.email is not None:
            current_user.email = user.email
        if user.statusVotacao is not None:
            current_user.statusVotacao = user.statusVotacao
        await session.commit()
        await session.refresh(current_user)

        return current_user
    except IntegrityError:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Username or Email already exists',
        )


@router.delete('/{user_id}', status_code=HTTPStatus.OK, response_model=Message)
async def delete_user(
    user_id: int,
    session: Session,
    current_user: CurrentUser,
):
    # O próprio usuário ou o administrador podem excluir uma conta
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail='Not enough permissions'
        )

    db_user = await session.scalar(select(User).where(User.id == user_id))
    if not db_user:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='User not found')

    if db_user.is_admin:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT, detail='Admin account cannot be deleted'
        )
    if db_user.is_deleted:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT, detail='User already deleted'
        )

    # Vínculos com eleições em configuração não têm votos e podem ser removidos
    draft_elections = select(Election.id).where(Election.status == ElectionStatus.DRAFT)
    await session.execute(
        delete(Election_Candidate).where(
            Election_Candidate.fk_candidate == user_id,
            Election_Candidate.fk_election.in_(draft_elections),
        )
    )

    if await _has_participated(user_id, session):
        # Exclusão lógica: mantém votos, candidaturas e o e-mail reservado
        db_user.deleted_at = datetime.now(tz=ZoneInfo('UTC'))
        await session.commit()
        await notify_election_change()
        return {'message': 'User deactivated'}

    await session.delete(db_user)
    await session.commit()
    await notify_election_change()

    return {'message': 'User deleted'}


@router.post(
    '/{user_id}/reactivate', status_code=HTTPStatus.OK, response_model=UserPublic
)
async def reactivate_user(user_id: int, session: Session, admin: CurrentAdmin):
    db_user = await session.scalar(select(User).where(User.id == user_id))
    if not db_user:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='User not found')

    if not db_user.is_deleted:
        raise HTTPException(status_code=HTTPStatus.CONFLICT, detail='User is not deleted')

    db_user.deleted_at = None
    await session.commit()
    await session.refresh(db_user)
    await notify_election_change()

    return db_user


async def _has_participated(user_id: int, session: AsyncSession) -> bool:
    # Participou: votou em alguma eleição ou é candidato numa eleição já aberta
    voted = await session.scalar(
        select(Vote_Election).where(Vote_Election.fk_user == user_id)
    )
    if voted:
        return True

    candidacy = await session.scalar(
        select(Election_Candidate)
        .join(Election, Election.id == Election_Candidate.fk_election)
        .where(
            Election_Candidate.fk_candidate == user_id,
            Election.status != ElectionStatus.DRAFT,
        )
    )
    return candidacy is not None
