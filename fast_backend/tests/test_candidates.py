from http import HTTPStatus

import factory
import pytest_asyncio

from src.models import Candidate
from src.schemas import CandidatePublic


def test_create_candidate(client):
    response = client.post(
        '/candidates',
        json={'username': 'test_candidate'},
    )

    assert response.status_code == HTTPStatus.CREATED
    assert response.json() == {
        'id': 1,
        'username': 'test_candidate',
    }


def test_create_candidate_should_return_conflict_username(client, candidate):
    response = client.post(
        '/candidates',
        json={'username': candidate.username},
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {'detail': 'Username already exist'}


def test_get_candidates(client):
    response = client.get('/candidates')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'candidates': []}


def test_get_candidates_with_candidates(client, candidate):
    candidate_schema = CandidatePublic.model_validate(candidate).model_dump()
    response = client.get('/candidates')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'candidates': [candidate_schema]}


def test_get_candidate_by_id(client, candidate):
    candidate_schema = CandidatePublic.model_validate(candidate).model_dump()
    response = client.get(f'/candidates/{candidate.id}')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == candidate_schema


def test_get_candidate_by_id_should_return_not_found(client):
    response = client.get('/candidates/-1')

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Candidate not found'}


def test_update_candidate(client, candidate):
    response = client.put(
        f'/candidates/{candidate.id}',
        json={'username': 'updated_candidate'},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        'id': candidate.id,
        'username': 'updated_candidate',
    }


def test_update_candidate_should_return_not_found(client):
    response = client.put(
        '/candidates/-1',
        json={'username': 'updated_candidate'},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Candidate not found'}


def test_update_candidate_integrity_error(client, candidate, other_candidate):
    response = client.put(
        f'/candidates/{candidate.id}',
        json={'username': other_candidate.username},
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {'detail': 'Username already exist'}


def test_delete_candidate(client, candidate):
    response = client.delete(f'/candidates/{candidate.id}')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'message': 'Candidate deleted'}


def test_delete_candidate_should_return_not_found(client):
    response = client.delete('/candidates/-1')

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Candidate not found'}


class CandidateFactory(factory.Factory):
    class Meta:
        model = Candidate

    username = factory.Sequence(lambda n: f'candidate{n}')


@pytest_asyncio.fixture
async def candidate(session):
    candidate = CandidateFactory()
    session.add(candidate)
    await session.commit()
    await session.refresh(candidate)
    return candidate


@pytest_asyncio.fixture
async def other_candidate(session):
    candidate = CandidateFactory()
    session.add(candidate)
    await session.commit()
    await session.refresh(candidate)
    return candidate
