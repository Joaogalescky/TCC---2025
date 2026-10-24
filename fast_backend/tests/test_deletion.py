from http import HTTPStatus

from tests.test_elections import _open_with_candidate


def _token(client, user):
    return client.post(
        '/auth/token',
        data={'username': user.email, 'password': user.clean_password},
    ).json()['access_token']


def _vote(client, election, candidate, token):
    return client.post(
        f'/vote/election/{election.id}',
        headers={'Authorization': f'Bearer {token}'},
        json={'candidate_id': candidate.id},
    )


# Usuários


def test_delete_user_without_participation_is_physical(client, user, token):
    response = client.delete(
        f'/users/{user.id}', headers={'Authorization': f'Bearer {token}'}
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'message': 'User deleted'}
    assert client.get(f'/users/{user.id}').status_code == HTTPStatus.NOT_FOUND


def test_delete_voter_is_logical(client, election, candidate, user, admin_token):
    _open_with_candidate(client, election, candidate, admin_token)
    token = _token(client, user)
    _vote(client, election, candidate, token)

    response = client.delete(
        f'/users/{user.id}', headers={'Authorization': f'Bearer {token}'}
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'message': 'User deactivated'}
    assert client.get(f'/users/{user.id}').json()['is_deleted'] is True


def test_deleted_user_cannot_login_or_use_old_token(
    client, election, candidate, user, admin_token
):
    _open_with_candidate(client, election, candidate, admin_token)
    token = _token(client, user)
    _vote(client, election, candidate, token)
    client.delete(f'/users/{user.id}', headers={'Authorization': f'Bearer {token}'})

    login = client.post(
        '/auth/token',
        data={'username': user.email, 'password': user.clean_password},
    )
    me = client.get('/users/me', headers={'Authorization': f'Bearer {token}'})

    assert login.status_code == HTTPStatus.UNAUTHORIZED
    assert login.json() == {'detail': 'Account deleted'}
    assert me.status_code == HTTPStatus.UNAUTHORIZED


def test_deleted_user_email_stays_reserved(
    client, election, candidate, user, admin_token
):
    _open_with_candidate(client, election, candidate, admin_token)
    token = _token(client, user)
    _vote(client, election, candidate, token)
    client.delete(f'/users/{user.id}', headers={'Authorization': f'Bearer {token}'})

    response = client.post(
        '/users',
        json={
            'username': 'novo_nome',
            'email': user.email,
            'password': 'testtest',
            'statusVotacao': False,
        },
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {'detail': 'Email already exists'}


def test_admin_can_delete_user(client, user, admin_token):
    response = client.delete(
        f'/users/{user.id}', headers={'Authorization': f'Bearer {admin_token}'}
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'message': 'User deleted'}


def test_admin_account_cannot_be_deleted(client, admin, admin_token):
    response = client.delete(
        f'/users/{admin.id}', headers={'Authorization': f'Bearer {admin_token}'}
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {'detail': 'Admin account cannot be deleted'}


def test_delete_user_twice_should_return_conflict(
    client, election, candidate, user, admin_token
):
    _open_with_candidate(client, election, candidate, admin_token)
    _vote(client, election, candidate, _token(client, user))
    headers = {'Authorization': f'Bearer {admin_token}'}
    client.delete(f'/users/{user.id}', headers=headers)

    response = client.delete(f'/users/{user.id}', headers=headers)

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {'detail': 'User already deleted'}


def test_reactivate_user(client, election, candidate, user, admin_token):
    _open_with_candidate(client, election, candidate, admin_token)
    _vote(client, election, candidate, _token(client, user))
    headers = {'Authorization': f'Bearer {admin_token}'}
    client.delete(f'/users/{user.id}', headers=headers)

    response = client.post(f'/users/{user.id}/reactivate', headers=headers)

    assert response.status_code == HTTPStatus.OK
    assert response.json()['is_deleted'] is False
    assert _token(client, user)


def test_reactivate_active_user_should_return_conflict(client, user, admin_token):
    response = client.post(
        f'/users/{user.id}/reactivate',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {'detail': 'User is not deleted'}


def test_reactivate_should_require_admin(client, user, token):
    response = client.post(
        f'/users/{user.id}/reactivate',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN


# Candidatos


def test_delete_candidate_linked_only_to_draft_is_physical(
    client, election, candidate, admin_token
):
    headers = {'Authorization': f'Bearer {admin_token}'}
    client.post(f'/elections/{election.id}/candidates/{candidate.id}', headers=headers)

    response = client.delete(f'/users/{candidate.id}', headers=headers)

    assert response.json() == {'message': 'User deleted'}
    assert client.get(f'/elections/{election.id}/candidates').json()['candidates'] == []


def test_deleted_candidate_stays_on_ballot_and_receives_votes(
    client, election, candidate, user, admin_token
):
    headers = _open_with_candidate(client, election, candidate, admin_token)

    response = client.delete(f'/users/{candidate.id}', headers=headers)
    assert response.json() == {'message': 'User deactivated'}

    ballot = client.get(f'/elections/{election.id}/candidates').json()['candidates']
    assert {
        'id': candidate.id,
        'username': candidate.username,
        'is_deleted': True,
    } in ballot

    assert _vote(client, election, candidate, _token(client, user)).status_code == (
        HTTPStatus.CREATED
    )

    client.post(f'/elections/{election.id}/close', headers=headers)
    results = client.post(f'/elections/{election.id}/tally', headers=headers).json()
    assert {
        'id': candidate.id,
        'username': candidate.username,
        'is_deleted': True,
        'votes': 1,
    } in results['candidates']


def test_deleted_candidate_is_not_available_for_new_elections(
    client, election, candidate, admin_token
):
    headers = _open_with_candidate(client, election, candidate, admin_token)
    client.delete(f'/users/{candidate.id}', headers=headers)
    new_election = client.post(
        '/elections', headers=headers, json={'title': 'Nova'}
    ).json()

    listing = client.get('/candidates').json()['candidates']
    link = client.post(
        f'/elections/{new_election["id"]}/candidates/{candidate.id}', headers=headers
    )

    assert candidate.id not in [c['id'] for c in listing]
    assert link.status_code == HTTPStatus.NOT_FOUND


def test_set_candidate_on_deleted_user_should_return_conflict(
    client, election, candidate, admin_token
):
    headers = _open_with_candidate(client, election, candidate, admin_token)
    client.delete(f'/users/{candidate.id}', headers=headers)

    response = client.patch(
        f'/users/{candidate.id}/candidate',
        headers=headers,
        json={'is_candidate': False},
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {'detail': 'User is deleted'}


# Eleições


def test_delete_election_with_votes_should_return_conflict(
    client, election, candidate, admin_token
):
    headers = _open_with_candidate(client, election, candidate, admin_token)
    _vote(client, election, candidate, admin_token)

    response = client.delete(f'/elections/{election.id}', headers=headers)

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {'detail': 'Election has votes, cancel it instead'}


def test_delete_election_removes_links(client, election, candidate, admin_token):
    """Sem restos: uma nova eleição com o mesmo id não herda candidatos."""
    headers = {'Authorization': f'Bearer {admin_token}'}
    client.post(f'/elections/{election.id}/candidates/{candidate.id}', headers=headers)
    client.delete(f'/elections/{election.id}', headers=headers)

    new_election = client.post(
        '/elections', headers=headers, json={'title': 'Nova'}
    ).json()
    response = client.get(f'/elections/{new_election["id"]}/candidates')

    assert new_election['id'] == election.id
    assert response.json()['candidates'] == []


def test_has_votes_flag(client, election, candidate, admin_token):
    _open_with_candidate(client, election, candidate, admin_token)
    assert client.get(f'/elections/{election.id}').json()['has_votes'] is False

    _vote(client, election, candidate, admin_token)

    assert client.get(f'/elections/{election.id}').json()['has_votes'] is True


def test_cancel_election(client, election, candidate, admin_token):
    headers = _open_with_candidate(client, election, candidate, admin_token)
    _vote(client, election, candidate, admin_token)

    response = client.post(f'/elections/{election.id}/cancel', headers=headers)

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        'id': election.id,
        'title': election.title,
        'status': 'cancelled',
        'has_votes': True,
    }


def test_cancelled_election_keeps_history_and_blocks_actions(
    client, election, candidate, user, admin_token
):
    headers = _open_with_candidate(client, election, candidate, admin_token)
    _vote(client, election, candidate, admin_token)
    client.post(f'/elections/{election.id}/cancel', headers=headers)

    assert _vote(client, election, candidate, _token(client, user)).status_code == (
        HTTPStatus.CONFLICT
    )
    for action in ('open', 'close', 'tally'):
        response = client.post(f'/elections/{election.id}/{action}', headers=headers)
        assert response.status_code == HTTPStatus.CONFLICT
    assert client.get(f'/vote/results/{election.id}').status_code == HTTPStatus.CONFLICT
    assert client.delete(f'/elections/{election.id}', headers=headers).status_code == (
        HTTPStatus.CONFLICT
    )
    assert len(client.get(f'/elections/{election.id}/candidates').json()['candidates'])


def test_cancel_draft_or_tallied_election_should_return_conflict(
    client, election, candidate, admin_token
):
    headers = {'Authorization': f'Bearer {admin_token}'}
    detail = {'detail': 'Only open or closed elections can be cancelled'}

    response = client.post(f'/elections/{election.id}/cancel', headers=headers)
    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == detail

    _open_with_candidate(client, election, candidate, admin_token)
    client.post(f'/elections/{election.id}/close', headers=headers)
    client.post(f'/elections/{election.id}/tally', headers=headers)

    response = client.post(f'/elections/{election.id}/cancel', headers=headers)
    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == detail


def test_cancel_should_require_admin(client, election, token):
    response = client.post(
        f'/elections/{election.id}/cancel',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
