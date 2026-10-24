from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src import voting
from src.database import get_session
from src.models import Election, ElectionStatus, User
from src.schemas import (
    ElectionResultsSchema,
    ReceiptStatus,
    VoteResponse,
    VoteSchema,
)
from src.security import get_current_user

router = APIRouter(prefix='/vote', tags=['vote'])
Session = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post(
    '/election/{election_id}', status_code=HTTPStatus.CREATED, response_model=VoteResponse
)
async def cast_vote(
    election_id: int, vote: VoteSchema, session: Session, current_user: CurrentUser
):
    # Não registrar o comprovante em log nem ligá-lo ao usuário
    receipt = await voting.cast_vote(
        session, election_id, current_user, vote.candidate_id
    )
    return VoteResponse(message='Vote cast successfully', receipt=receipt)


@router.get(
    '/results/{election_id}',
    status_code=HTTPStatus.OK,
    response_model=ElectionResultsSchema,
)
async def get_election_results(election_id: int, session: Session):
    # Resultado publicado na apuração; nada é decifrado aqui
    election = await session.scalar(select(Election).where(Election.id == election_id))
    if not election:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='Election not found')

    if election.status != ElectionStatus.TALLIED:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT, detail='Election has not been tallied yet'
        )

    return await voting.published_results(session, election_id)


@router.get(
    '/receipt/{election_id}/{receipt_hash}',
    status_code=HTTPStatus.OK,
    response_model=ReceiptStatus,
)
async def check_receipt(election_id: int, receipt_hash: str, session: Session):
    status = await voting.receipt_status(session, election_id, receipt_hash.lower())
    if status is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='Receipt not found')
    return status
