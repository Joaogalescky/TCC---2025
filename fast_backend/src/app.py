from http import HTTPStatus

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.routers import auth, candidates, elections, events, users, vote
from src.schemas import Message

app = FastAPI()

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
