from http import HTTPStatus

from src.schemas import CandidatePublic


def test_get_candidates(client):
    response = client.get('/candidates')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'candidates': []}


def test_get_candidates_with_candidates(client, candidate):
    candidate_schema = CandidatePublic.model_validate(candidate).model_dump()
    response = client.get('/candidates')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'candidates': [candidate_schema]}


def test_get_candidates_should_not_list_voters(client, user):
    response = client.get('/candidates')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'candidates': []}


def test_get_candidate_by_id(client, candidate):
    candidate_schema = CandidatePublic.model_validate(candidate).model_dump()
    response = client.get(f'/candidates/{candidate.id}')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == candidate_schema


def test_get_candidate_by_id_should_return_not_found(client):
    response = client.get('/candidates/-1')

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Candidate not found'}


def test_get_candidate_by_id_of_voter_should_return_not_found(client, user):
    response = client.get(f'/candidates/{user.id}')

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Candidate not found'}


def test_admin_set_user_as_candidate(client, user, admin_token):
    response = client.patch(
        f'/users/{user.id}/candidate',
        headers={'Authorization': f'Bearer {admin_token}'},
        json={'is_candidate': True},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json()['is_candidate'] is True


def test_admin_set_candidate_as_voter(client, candidate, admin_token):
    response = client.patch(
        f'/users/{candidate.id}/candidate',
        headers={'Authorization': f'Bearer {admin_token}'},
        json={'is_candidate': False},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json()['is_candidate'] is False


def test_set_candidate_should_require_admin(client, user, token):
    response = client.patch(
        f'/users/{user.id}/candidate',
        headers={'Authorization': f'Bearer {token}'},
        json={'is_candidate': True},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.json() == {'detail': 'Not enough permissions'}


def test_set_candidate_should_return_not_found(client, admin_token):
    response = client.patch(
        '/users/-1/candidate',
        headers={'Authorization': f'Bearer {admin_token}'},
        json={'is_candidate': True},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'User not found'}
