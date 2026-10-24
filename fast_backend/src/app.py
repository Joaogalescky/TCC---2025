import logging
from contextlib import asynccontextmanager
from http import HTTPStatus

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.admin import ensure_admin
from src.crypto_service import crypto_service
from src.database import get_session
from src.routers import auth, candidates, elections, events, users, vote
from src.schemas import Message
from src.settings import Settings


def _hide_vote_routes(record: logging.LogRecord) -> bool:
    """
    Tira do access log as rotas /vote/*: o log guardaria o IP e o horário de
    cada voto e o comprovante consultado (que fica no caminho da URL)
    """
    path = record.args[2] if isinstance(record.args, tuple) and record.args else ''
    return not str(path).startswith('/vote/')


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    access_logger = logging.getLogger('uvicorn.access')
    if _hide_vote_routes not in access_logger.filters:
        access_logger.addFilter(_hide_vote_routes)

    # Contexto e chaves do OpenFHE: carregados de KEYS_DIR ou gerados na 1ª vez
    crypto_service.load_or_create_keys(settings.KEYS_DIR)

    # Respeita o override de sessão usado nos testes
    session_provider = app.dependency_overrides.get(get_session, get_session)
    async for session in session_provider():
        await ensure_admin(session, settings)
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        'http://localhost:5173',
        'http://localhost:3000',
        'http://frontend:3000',
    ],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(candidates.router)
app.include_router(elections.router)
app.include_router(vote.router)
app.include_router(events.router)


@app.get('/', status_code=HTTPStatus.OK, response_model=Message)
async def read_root():
    return {'message': 'Ola Mundo!'}


@app.get('/health', status_code=HTTPStatus.OK)
async def health_check():
    return {'status': 'healthy'}
