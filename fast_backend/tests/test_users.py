from http import HTTPStatus

from src.schemas import UserPublic
from src.security import create_access_token


def test_create_user(client):
    response = client.post(
        '/users',
        json={
            'username': 'test',
            'password': 'test',
            'email': 'test@test.com',
            'statusVotacao': True,
        },
    )

    assert response.status_code == HTTPStatus.CREATED
    assert response.json() == {
        'username': 'test',
        'email': 'test@test.com',
        'statusVotacao': True,
        'id': 1,
    }


def test_create_user_should_return_conflict_username(client, user):
    response = client.post(
        '/users',
        json={
            'username': user.username,
            'password': 'test',
            'email': 'test@test.com',
            'statusVotacao': True,
        },
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {'detail': 'Username already exists'}


def test_create_user_should_return_conflict_email(client, user):
    response = client.post(
        '/users',
        json={
            'username': 'test',
            'password': 'test',
            'email': user.email,
            'statusVotacao': True,
        },
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {'detail': 'Email already exists'}


def test_create_user_should_return_bad_request(client):
    response = client.post(
        '/users',
        json={
            'username': 'test',
            'password': 'test',
            'statusVotacao': True,
        },
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.json()['detail'][0]['msg'] == 'Field required'
    assert response.json()['detail'][0]['loc'][-1] == 'email'


def test_get_users(client):
    response = client.get('/users')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'users': []}


def test_get_users_with_users(client, user):
    user_schema = UserPublic.model_validate(user).model_dump()
    response = client.get('/users')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'users': [user_schema]}


def test_get_user_by_id(client, user):
    user_schema = UserPublic.model_validate(user).model_dump()
    response = client.get(f'/users/{user.id}')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == user_schema


def test_get_user_by_id_should_return_not_found(client):
    response = client.get('/users/-1')

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'User not found'}


def test_update_user(client, user, token):
    response = client.put(
        f'/users/{user.id}',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'username': 'test2',
            'password': 'test2',
            'email': 'test2@test.com',
            'statusVotacao': False,
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        'username': 'test2',
        'email': 'test2@test.com',
        'statusVotacao': False,
        'id': user.id,
    }


def test_update_integrity_error(client, user, other_user, token):
    response_update = client.put(
        f'/users/{user.id}',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'username': other_user.username,
            'password': 'newtest3',
            'email': 'newtest3@test.com',
            'statusVotacao': True,
        },
    )

    assert response_update.status_code == HTTPStatus.CONFLICT
    assert response_update.json() == {'detail': 'Username or Email already exists'}


def test_update_user_with_wrong_user(client, other_user, token):
    response = client.put(
        f'/users/{other_user.id}',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'username': 'bob',
            'password': 'mynewpassword',
            'email': 'bob@example.com',
            'statusVotacao': False,
        },
    )
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.json() == {'detail': 'Not enough permissions'}


def test_parcial_update_user(client, user, token):
    response = client.patch(
        f'/users/{user.id}',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'username': 'test4',
            'password': 'test4',
            'email': 'test4@test.com',
            'statusVotacao': True,
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        'username': 'test4',
        'email': 'test4@test.com',
        'statusVotacao': True,
        'id': user.id,
    }


def test_parcial_update_user_integrity_error(client, user, token):
    client.post(
        '/users/',
        json={
            'username': 'test5',
            'password': 'test5',
            'email': 'test5@test.com',
            'statusVotacao': False,
        },
    )
    response_update = client.patch(
        f'/users/{user.id}',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'username': 'test5',
            'password': 'newtest5',
            'email': 'test5@test.com',
            'statusVotacao': True,
        },
    )

    assert response_update.status_code == HTTPStatus.CONFLICT
    assert response_update.json() == {'detail': 'Username or Email already exists'}


def test_parcial_update_user_with_wrong_user(client, other_user, token):
    response = client.patch(
        f'/users/{other_user.id}',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'username': 'bob',
            'password': 'mynewpassword',
            'email': 'bob@example.com',
            'statusVotacao': False,
        },
    )
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.json() == {'detail': 'Not enough permissions'}


def test_delete_user(client, user, token):
    response = client.delete(
        f'/users/{user.id}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'message': 'User deleted'}


def test_delete_user_with_wrong_user(client, other_user, token):
    response = client.delete(
        f'/users/{other_user.id}',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.json() == {'detail': 'Not enough permissions'}


def test_get_current_user_not_found(client):
    data = {'no-email': 'test'}
    token = create_access_token(data)

    response = client.delete(
        '/users/1',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json() == {'detail': 'Could not validate credentials'}


def test_get_current_user_does_not_exist(client):
    data = {'sub': 'test@test'}
    token = create_access_token(data)

    response = client.delete(
        '/users/1',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json() == {'detail': 'Could not validate credentials'}
