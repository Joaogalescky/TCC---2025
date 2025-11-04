from contextlib import contextmanager
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.app import app
from src.database import get_session
from src.models import User, table_registry
from src.security import get_password_hash


@pytest.fixture
def client(session):
    def get_session_override():
        return session

    with TestClient(app) as client:
        app.dependency_overrides[get_session] = get_session_override
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def session():
    """
    Configura e limpa um banco de dados de teste
    para cada teste que o solicita,
    assegurando que cada teste seja isolado
    e tenha seu próprio ambiente limpo para trabalhar.
    """
    engine = create_engine(
        'sqlite:///:memory:',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )  # cria uma sessão em memória
    table_registry.metadata.create_all(engine)

    with Session(engine) as session:  # cria uma sessão para os teste
        yield session  # fornece uma instância para teste

    table_registry.metadata.drop_all(engine)  # apaga as tabelas


@contextmanager
def _mock_db_time(*, model, time=datetime(2025, 1, 1)):
    """
    Gerenciador de contexto.
    Toda vezes que um registro de model for inserido no banco de dados,
    se ele tiver o campo created_at, por padrão, o campo será cadastrado
    com a sua data pré-fixada.
    Facilita a manutenção dos testes que precisam da comparação de data,
    pois será determinística.
    """

    def fake_time_hook(mapper, connection, target):
        if hasattr(target, 'created_at'):
            target.created_at = time
        if hasattr(target, 'updated_at'):
            target.updated_at = time

    event.listen(model, 'before_insert', fake_time_hook)

    yield time

    event.remove(model, 'before_insert', fake_time_hook)


@pytest.fixture
def mock_db_time():
    return _mock_db_time


@pytest.fixture
def user(session):
    password = 'senha'
    user = User(
        username='testeusuario',
        password=get_password_hash(password),
        email='usuario@teste.com',
        statusVotacao=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    user.clean_password = password

    return user


@pytest.fixture
def token(client, user):
    response = client.post(
        '/auth/token',
        data={
            'username': user.email,
            'password': user.clean_password,
        },
    )
    return response.json()['access_token']
