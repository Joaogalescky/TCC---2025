from http import HTTPStatus

from fastapi import FastAPI

from src.routers import auth, candidate, election, users
from src.schemas import Message

app = FastAPI()


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(candidate.router)
app.include_router(election.router)


@app.get('/', status_code=HTTPStatus.OK, response_model=Message)
async def read_root():
    return {'message': 'Ola Mundo!'}
