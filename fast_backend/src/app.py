from http import HTTPStatus

from fastapi import FastAPI

from src.routers import auth, users
from src.schemas import Message

app = FastAPI()


app.include_router(auth.router)
app.include_router(users.router)


@app.get('/', status_code=HTTPStatus.OK, response_model=Message)
def read_root():
    return {'message': 'Ola Mundo!'}
