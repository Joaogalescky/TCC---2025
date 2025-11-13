from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.crypto_service import crypto_service
from src.database import get_session
from src.models import (
    Candidate,
    Election,
    Election_Candidate,
    Election_Tally,
    User,
    Vote_Election,
)
from src.schemas import ElectionResultsSchema, VoteResponse, VoteSchema
from src.security import get_current_user

router = APIRouter(prefix='/vote', tags=['vote'])
Session = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post('/election/{election_id}',
    status_code=HTTPStatus.CREATED,
    response_model=VoteResponse
)
async def cast_vote(
    election_id: int,
    vote: VoteSchema,
    session: Session,
    current_user: CurrentUser
):
    election_candidate = await session.scalar(
        select(Election_Candidate).where(
            Election_Candidate.fk_election == election_id,
            Election_Candidate.fk_candidate == vote.candidate_id
        )
    )
    if not election_candidate:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Candidate not found in this election'
        )

    existing_vote = await session.scalar(
        select(Vote_Election)
        .join(
            Election_Candidate,
            Vote_Election.fk_election_candidate == Election_Candidate.id
            )
        .where(
            Vote_Election.fk_user == current_user.id,
            Election_Candidate.fk_election == election_id
        )
    )
    if existing_vote:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='User already voted in this election'
        )

    # Configurar criptografia se necessário
    if not crypto_service.cc:
        crypto_service.setup_crypto()

    # Encriptar o valor "1" (representa um voto)
    encrypted_vote = crypto_service.encrypt_vote([1])

    # Salvar voto criptografado
    db_vote = Vote_Election(
        fk_user=current_user.id,
        fk_election_candidate=election_candidate.id,
        encrypted_vote=encrypted_vote
    )
    session.add(db_vote)

    # Atualizar tally da eleição
    tally = await session.scalar(
        select(Election_Tally).where(Election_Tally.fk_election == election_id)
    )

    if not tally:
        # Obter total de candidatos para criar tally inicial
        candidates_count = await session.scalar(
            select(
                func.count(Election_Candidate.id))
                .where(
                    Election_Candidate.fk_election == election_id
                )
        )

        encrypted_tally = crypto_service.create_zero_tally(candidates_count)
        tally = Election_Tally(
            fk_election=election_id,
            encrypted_tally=encrypted_tally,
            total_candidates=candidates_count
        )
        session.add(tally)

    # Somar voto ao tally (soma homomórfica)
    tally.encrypted_tally = crypto_service.add_vote_to_tally(
        tally.encrypted_tally,
        encrypted_vote
    )

    current_user.statusVotacao = True
    await session.commit()
    await session.refresh(db_vote)

    return VoteResponse(message='Vote cast successfully', vote_id=db_vote.id)


@router.get('/results/{election_id}',
            status_code=HTTPStatus.OK,
            response_model=ElectionResultsSchema
)
async def get_election_results(election_id: int, session: Session):
    # Obtém os resultados descriptografados de uma eleição

    election = await session.scalar(select(Election).where(Election.id == election_id))
    if not election:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='Election not found')

    # Obter tally criptografado
    tally = await session.scalar(
        select(Election_Tally).where(Election_Tally.fk_election == election_id)
    )
    if not tally:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='No votes found for this election'
        )

    # Contar votos por candidato usando soma homomórfica
    election_candidates = await session.scalars(
        select(Election_Candidate).where(Election_Candidate.fk_election == election_id)
    )
    candidates_list = election_candidates.all()

    # Para cada candidato, somar todos os votos criptografados
    candidates_results = []
    total_votes = 0

    if not crypto_service.cc:
        crypto_service.setup_crypto()

    for ec in candidates_list:
        # Obter todos os votos para este candidato
        votes = await session.scalars(
            select(Vote_Election).where(Vote_Election.fk_election_candidate == ec.id)
        )
        votes_list = votes.all()

        # Somar homomorficamente todos os votos
        if votes_list:
            candidate_tally = votes_list[0].encrypted_vote
            for vote in votes_list[1:]:
                candidate_tally = crypto_service.add_vote_to_tally(
                    candidate_tally, vote.encrypted_vote
                )

            # Descriptografar o total para este candidato
            decrypted_votes = crypto_service.decrypt_tally(candidate_tally, 1)[0]
        else:
            decrypted_votes = 0

        candidate = await session.scalar(
            select(Candidate)
            .where(Candidate.id == ec.fk_candidate)
        )
        total_votes += decrypted_votes

        candidates_results.append({
            'id': candidate.id,
            'username': candidate.username,
            'votes': decrypted_votes
        })

    return ElectionResultsSchema(
        election_id=election_id,
        candidates=candidates_results,
        total_votes=total_votes
    )
