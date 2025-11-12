from http import HTTPStatus

import factory
import pytest_asyncio

from src.models import Election
from src.schemas import ElectionPublic


def test_create_election(client):
    response = client.post(
        '/elections',
        json={'title': 'Test Election'},
    )

    assert response.status_code == HTTPStatus.CREATED
    assert response.json() == {
        'id': 1,
        'title': 'Test Election',
    }


def test_get_elections(client):
    response = client.get('/elections')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'elections': []}


def test_get_elections_with_elections(client, election):
    election_schema = ElectionPublic.model_validate(election).model_dump()
    response = client.get('/elections')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'elections': [election_schema]}


def test_get_election_by_id(client, election):
    election_schema = ElectionPublic.model_validate(election).model_dump()
    response = client.get(f'/elections/{election.id}')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == election_schema


def test_get_election_by_id_should_return_not_found(client):
    response = client.get('/elections/-1')

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Election not found'}


def test_update_election(client, election):
    response = client.put(
        f'/elections/{election.id}',
        json={'title': 'Updated Election'},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        'id': election.id,
        'title': 'Updated Election',
    }


def test_update_election_should_return_not_found(client):
    response = client.put(
        '/elections/-1',
        json={'title': 'Updated Election'},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Election not found'}


def test_delete_election(client, election):
    response = client.delete(f'/elections/{election.id}')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'message': 'Election deleted'}


def test_delete_election_should_return_not_found(client):
    response = client.delete('/elections/-1')

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Election not found'}


class ElectionFactory(factory.Factory):
    class Meta:
        model = Election

    title = factory.Sequence(lambda n: f'Election {n}')


@pytest_asyncio.fixture
async def election(session):
    election = ElectionFactory()
    session.add(election)
    await session.commit()
    await session.refresh(election)
    return election
