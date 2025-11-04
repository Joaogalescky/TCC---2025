from http import HTTPStatus

from src.schemas import UserPublic
from src.security import create_access_token


def test_create_user(client):
    response = client.post(
        '/users',
        json={
            'username': 'testeusuario',
            'password': 'teste123',
            'email': 'usuario@teste.com',
            'statusVotacao': True,
        },
    )

    assert response.status_code == HTTPStatus.CREATED
    assert response.json() == {
        'username': 'testeusuario',
        'email': 'usuario@teste.com',
        'statusVotacao': True,
        'id': 1,
    }


def test_create_user_should_return_conflict_username(client, user):
    response = client.post(
        '/users',
        json={
            'username': user.username,
            'password': 'segredo',
            'email': 'novo_usuario@teste.com',
            'statusVotacao': True,
        },
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {'detail': 'Username already exists'}


def test_create_user_should_return_conflict_email(client, user):
    response = client.post(
        '/users',
        json={
            'username': 'novo_usuario',
            'password': 'segredo',
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
            'username': 'testeusuario',
            'password': 'teste123',
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
            'username': 'testeusuario2',
            'password': 'nova_senha',
            'email': 'usuario2@teste.com',
            'statusVotacao': False,
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        'username': 'testeusuario2',
        'email': 'usuario2@teste.com',
        'statusVotacao': False,
        'id': user.id,
    }


def test_update_integrity_error(client, user, token):
    client.post(
        '/users/',
        json={
            'username': 'testeusuario3',
            'password': 'testeusuario3',
            'email': 'testeusuario3@teste.com',
            'statusVotacao': False,
        },
    )
    response_update = client.put(
        f'/users/{user.id}',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'username': 'testeusuario3',
            'password': 'nova_senha',
            'email': 'usuario2@teste.com',
            'statusVotacao': True,
        },
    )

    assert response_update.status_code == HTTPStatus.CONFLICT
    assert response_update.json() == {'detail': 'Username or Email already exists'}


def test_parcial_update_user(client, user, token):
    response = client.patch(
        f'/users/{user.id}',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'username': 'testeusuario2',
            'password': 'nova_senha',
            'email': 'novo_testeusuario2@teste.com',
            'statusVotacao': True,
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        'username': 'testeusuario2',
        'email': 'novo_testeusuario2@teste.com',
        'statusVotacao': True,
        'id': user.id,
    }


def test_parcial_update_user_integrity_error(client, user, token):
    client.post(
        '/users/',
        json={
            'username': 'testeusuario3',
            'password': 'testeusuario3',
            'email': 'testeusuario3@teste.com',
            'statusVotacao': False,
        },
    )
    response_update = client.patch(
        f'/users/{user.id}',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'username': 'testeusuario3',
            'password': 'nova_senha',
            'email': 'usuario2@teste.com',
            'statusVotacao': True,
        },
    )

    assert response_update.status_code == HTTPStatus.CONFLICT
    assert response_update.json() == {'detail': 'Username or Email already exists'}


def test_delete_user(client, user, token):
    response = client.delete(
        f'/users/{user.id}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'message': 'User deleted'}


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
