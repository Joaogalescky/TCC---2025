from dataclasses import asdict

from sqlalchemy import Select

from src.models import User


def test_create_user(session, mock_db_time):
    """
    Adiciona um novo usuário ao banco de dados,
    faz commit das mudanças, e depois verifica se o usuário
    foi devidamente criado consultando-o pelo nome de usuário.
    Se o usuário foi criado corretamente, o teste passa.
    Caso contrário, o teste falha, indicando que há algo errado
    com nossa função de criação de usuário
    """
    with mock_db_time(model=User) as time:
        new_user = User(
            username='teste',
            password='teste',
            email='teste@email.com',
            statusVotacao=False,
        )
        session.add(new_user)  # adiciona o registro a sessão
        session.commit()  # realiza a inserção ao banco

    # busca o dado
    user = session.scalar(Select(User).where(User.username == 'teste'))

    assert asdict(user) == {
        'id': 1,
        'username': 'teste',
        'password': 'teste',
        'email': 'teste@email.com',
        'statusVotacao': False,
        'created_at': time,
        'updated_at': time,
    }

    assert user.username == 'teste'
