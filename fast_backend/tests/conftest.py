from contextlib import contextmanager
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from src.app import app
from src.models import table_registry


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def session():
    """
    Configura e limpa um banco de dados de teste
    para cada teste que o solicita,
    assegurando que cada teste seja isolado
    e tenha seu próprio ambiente limpo para trabalhar.
    """
    engine = create_engine('sqlite:///:memory:')  # cria uma sessão em memória
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
