from http import HTTPStatus

from src.schemas import UserPublic


def test_root_return_hello_world(client):
    response = client.get('/')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'message': 'Ola Mundo!'}


def test_create_user(client):
    response = client.post(
        '/users/',
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


def test_create_user_should_return_bad_request(client):
    response = client.post(
        '/users/',
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
    response = client.get('/users/')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'users': []}


def test_get_users_with_users(client, user):
    user_schema = UserPublic.model_validate(user).model_dump()
    response = client.get('/users/')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'users': [user_schema]}


def test_get_user_by_id(client):
    response = client.get('/users/1')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        'username': 'testeusuario',
        'email': 'usuario@teste.com',
        'statusVotacao': True,
        'id': 1,
    }


def test_get_user_by_id_should_return_not_found(client):
    response = client.get('/users/-1')

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'User not found'}


def test_update_user(client):
    response = client.put(
        '/users/1',
        json={
            'username': 'testeusuario2',
            'password': 'senha',
            'email': 'usuario2@teste.com',
            'statusVotacao': False,
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        'username': 'testeusuario2',
        'email': 'usuario2@teste.com',
        'statusVotacao': False,
        'id': 1,
    }


def test_update_user_should_return_not_found(client):
    response = client.put(
        '/users/-1',
        json={
            'username': 'teste_usuario_inexistente',
            'password': 'senha',
            'email': 'usuario_inexistente@teste.com',
            'statusVotacao': False,
        },
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'User not found'}


def test_delete_user(client):
    response = client.delete(
        '/users/1',
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'message': 'User deleted'}


def test_delete_user_should_return_not_found(client):
    response = client.delete(
        'users/-1',
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'User not found'}
