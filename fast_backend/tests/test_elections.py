from http import HTTPStatus

import factory
import pytest_asyncio

from src.models import Election
from src.schemas import ElectionPublic


def test_create_election(client, admin_token):
    response = client.post(
        '/elections',
        headers={'Authorization': f'Bearer {admin_token}'},
        json={'title': 'Test Election'},
    )

    assert response.status_code == HTTPStatus.CREATED
    assert response.json() == {
        'id': 1,
        'title': 'Test Election',
        'status': 'open',
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


def test_update_election(client, election, admin_token):
    response = client.put(
        f'/elections/{election.id}',
        headers={'Authorization': f'Bearer {admin_token}'},
        json={'title': 'Updated Election'},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        'id': election.id,
        'title': 'Updated Election',
        'status': 'open',
    }


def test_update_election_should_return_not_found(client, admin_token):
    response = client.put(
        '/elections/-1',
        headers={'Authorization': f'Bearer {admin_token}'},
        json={'title': 'Updated Election'},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Election not found'}


def test_delete_election(client, election, admin_token):
    response = client.delete(
        f'/elections/{election.id}',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'message': 'Election deleted'}


def test_delete_election_should_return_not_found(client, admin_token):
    response = client.delete(
        '/elections/-1',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Election not found'}


def test_create_election_should_require_admin(client, token):
    response = client.post(
        '/elections',
        headers={'Authorization': f'Bearer {token}'},
        json={'title': 'Test Election'},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.json() == {'detail': 'Not enough permissions'}


def test_create_election_should_require_login(client):
    response = client.post('/elections', json={'title': 'Test Election'})

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_add_candidate_to_election(client, election, candidate, admin_token):
    response = client.post(
        f'/elections/{election.id}/candidates/{candidate.id}',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response.status_code == HTTPStatus.CREATED
    assert response.json() == {
        'id': election.id,
        'title': election.title,
        'status': 'open',
        'candidates': [{'id': candidate.id, 'username': candidate.username}],
    }


def test_add_voter_to_election_should_return_not_found(
    client, election, user, admin_token
):
    response = client.post(
        f'/elections/{election.id}/candidates/{user.id}',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Candidate not found'}


def test_add_candidate_to_election_should_require_admin(
    client, election, candidate, token
):
    response = client.post(
        f'/elections/{election.id}/candidates/{candidate.id}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN


def test_remove_candidate_from_election(client, election, candidate, admin_token):
    headers = {'Authorization': f'Bearer {admin_token}'}
    client.post(f'/elections/{election.id}/candidates/{candidate.id}', headers=headers)

    response = client.delete(
        f'/elections/{election.id}/candidates/{candidate.id}', headers=headers
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json()['candidates'] == []


def test_remove_candidate_not_in_election_should_return_not_found(
    client, election, candidate, admin_token
):
    response = client.delete(
        f'/elections/{election.id}/candidates/{candidate.id}',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Candidate not found in this election'}


def test_unmark_candidate_linked_to_election_should_return_conflict(
    client, election, candidate, admin_token
):
    headers = {'Authorization': f'Bearer {admin_token}'}
    client.post(f'/elections/{election.id}/candidates/{candidate.id}', headers=headers)

    response = client.patch(
        f'/users/{candidate.id}/candidate',
        headers=headers,
        json={'is_candidate': False},
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {'detail': 'Candidate is linked to an election'}


def test_candidate_and_voter_can_vote(client, election, candidate, user, admin_token):
    """Candidato e eleitor possuem voto; o candidato pode votar em si mesmo."""
    client.post(
        f'/elections/{election.id}/candidates/{candidate.id}',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    for voter in (candidate, user):
        token = client.post(
            '/auth/token',
            data={'username': voter.email, 'password': voter.clean_password},
        ).json()['access_token']
        response = client.post(
            f'/vote/election/{election.id}',
            headers={'Authorization': f'Bearer {token}'},
            json={'candidate_id': candidate.id},
        )
        assert response.status_code == HTTPStatus.CREATED

    headers = {'Authorization': f'Bearer {admin_token}'}
    client.post(f'/elections/{election.id}/close', headers=headers)
    client.post(f'/elections/{election.id}/tally', headers=headers)

    response = client.get(f'/vote/results/{election.id}')
    assert response.json()['candidates'] == [
        {'id': candidate.id, 'username': candidate.username, 'votes': 2}
    ]


def test_remove_candidate_with_votes_should_return_conflict(
    client, election, candidate, admin_token
):
    headers = {'Authorization': f'Bearer {admin_token}'}
    client.post(f'/elections/{election.id}/candidates/{candidate.id}', headers=headers)
    client.post(
        f'/vote/election/{election.id}',
        headers=headers,
        json={'candidate_id': candidate.id},
    )

    response = client.delete(
        f'/elections/{election.id}/candidates/{candidate.id}', headers=headers
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {'detail': 'Candidate already has votes in this election'}


def _link_and_vote(client, election, candidate, admin_token):
    headers = {'Authorization': f'Bearer {admin_token}'}
    client.post(f'/elections/{election.id}/candidates/{candidate.id}', headers=headers)
    client.post(
        f'/vote/election/{election.id}',
        headers=headers,
        json={'candidate_id': candidate.id},
    )
    return headers


def test_close_election(client, election, admin_token):
    response = client.post(
        f'/elections/{election.id}/close',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        'id': election.id,
        'title': election.title,
        'status': 'closed',
    }


def test_close_election_should_require_admin(client, election, token):
    response = client.post(
        f'/elections/{election.id}/close',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN


def test_close_election_twice_should_return_conflict(client, election, admin_token):
    headers = {'Authorization': f'Bearer {admin_token}'}
    client.post(f'/elections/{election.id}/close', headers=headers)

    response = client.post(f'/elections/{election.id}/close', headers=headers)

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {'detail': 'Election is not open'}


def test_vote_in_closed_election_should_return_conflict(
    client, election, candidate, token, admin_token
):
    headers = {'Authorization': f'Bearer {admin_token}'}
    client.post(f'/elections/{election.id}/candidates/{candidate.id}', headers=headers)
    client.post(f'/elections/{election.id}/close', headers=headers)

    response = client.post(
        f'/vote/election/{election.id}',
        headers={'Authorization': f'Bearer {token}'},
        json={'candidate_id': candidate.id},
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {'detail': 'Election is not open for voting'}


def test_add_candidate_to_closed_election_should_return_conflict(
    client, election, candidate, admin_token
):
    headers = {'Authorization': f'Bearer {admin_token}'}
    client.post(f'/elections/{election.id}/close', headers=headers)

    response = client.post(
        f'/elections/{election.id}/candidates/{candidate.id}', headers=headers
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {'detail': 'Election is not open'}


def test_tally_election(client, election, candidate, admin_token):
    headers = _link_and_vote(client, election, candidate, admin_token)
    client.post(f'/elections/{election.id}/close', headers=headers)

    response = client.post(f'/elections/{election.id}/tally', headers=headers)

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        'election_id': election.id,
        'candidates': [{'id': candidate.id, 'username': candidate.username, 'votes': 1}],
        'total_votes': 1,
    }
    assert client.get(f'/elections/{election.id}').json()['status'] == 'tallied'


def test_tally_open_election_should_return_conflict(client, election, admin_token):
    response = client.post(
        f'/elections/{election.id}/tally',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {'detail': 'Election must be closed before tallying'}


def test_tally_twice_should_return_conflict(client, election, admin_token):
    headers = {'Authorization': f'Bearer {admin_token}'}
    client.post(f'/elections/{election.id}/close', headers=headers)
    client.post(f'/elections/{election.id}/tally', headers=headers)

    response = client.post(f'/elections/{election.id}/tally', headers=headers)

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {'detail': 'Election already tallied'}


def test_tally_should_require_admin(client, election, token, admin_token):
    client.post(
        f'/elections/{election.id}/close',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    response = client.post(
        f'/elections/{election.id}/tally',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN


def test_tally_election_without_votes(client, election, candidate, admin_token):
    headers = {'Authorization': f'Bearer {admin_token}'}
    client.post(f'/elections/{election.id}/candidates/{candidate.id}', headers=headers)
    client.post(f'/elections/{election.id}/close', headers=headers)

    response = client.post(f'/elections/{election.id}/tally', headers=headers)

    assert response.status_code == HTTPStatus.OK
    assert response.json()['total_votes'] == 0


def test_results_before_tally_should_return_conflict(
    client, election, candidate, admin_token
):
    headers = _link_and_vote(client, election, candidate, admin_token)

    for _ in ('open', 'closed'):
        response = client.get(f'/vote/results/{election.id}')
        assert response.status_code == HTTPStatus.CONFLICT
        assert response.json() == {'detail': 'Election has not been tallied yet'}
        client.post(f'/elections/{election.id}/close', headers=headers)


def test_results_after_tally_are_public(client, election, candidate, admin_token):
    headers = _link_and_vote(client, election, candidate, admin_token)
    client.post(f'/elections/{election.id}/close', headers=headers)
    client.post(f'/elections/{election.id}/tally', headers=headers)

    response = client.get(f'/vote/results/{election.id}')

    assert response.status_code == HTTPStatus.OK
    assert response.json()['total_votes'] == 1


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
