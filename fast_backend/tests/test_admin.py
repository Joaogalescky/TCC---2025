import pytest
from pydantic import ValidationError
from sqlalchemy import select

from src.admin import ensure_admin
from src.models import User
from src.settings import Settings


def admin_settings(**kwargs):
    return Settings(
        ADMIN_USERNAME='admin',
        ADMIN_EMAIL='admin@test.com',
        ADMIN_PASSWORD='admin123',
        **kwargs,
    )


@pytest.mark.asyncio
async def test_ensure_admin_creates_admin(session):
    await ensure_admin(session, admin_settings())

    admin = await session.scalar(select(User).where(User.email == 'admin@test.com'))

    assert admin.is_admin is True
    assert admin.is_candidate is False


@pytest.mark.asyncio
async def test_ensure_admin_promotes_existing_user(session, user):
    await ensure_admin(
        session,
        Settings(ADMIN_EMAIL=user.email, ADMIN_USERNAME=None, ADMIN_PASSWORD=None),
    )
    db_user = await session.scalar(select(User).where(User.id == user.id))

    assert db_user.is_admin is True


@pytest.mark.asyncio
async def test_ensure_admin_is_idempotent(session):
    await ensure_admin(session, admin_settings())
    await ensure_admin(session, admin_settings())

    admins = await session.scalars(select(User).where(User.is_admin))

    assert len(admins.all()) == 1


@pytest.mark.asyncio
async def test_ensure_admin_without_email_does_nothing(session):
    await ensure_admin(session, Settings(ADMIN_EMAIL=None))

    users = await session.scalars(select(User))

    assert users.all() == []


@pytest.mark.asyncio
async def test_ensure_admin_skips_when_username_taken(session, user):
    await ensure_admin(
        session,
        Settings(
            ADMIN_USERNAME=user.username,
            ADMIN_EMAIL='admin@test.com',
            ADMIN_PASSWORD='admin123',
        ),
    )

    admin = await session.scalar(select(User).where(User.email == 'admin@test.com'))

    assert admin is None


def test_admin_can_login(client, admin):
    response = client.post(
        '/auth/token',
        data={'username': admin.email, 'password': admin.clean_password},
    )
    me = client.get(
        '/users/me',
        headers={'Authorization': f'Bearer {response.json()["access_token"]}'},
    )

    assert me.json()['is_admin'] is True


def test_settings_should_reject_invalid_admin_email():
    with pytest.raises(ValidationError):
        Settings(ADMIN_EMAIL='admin@eleicao.local')
