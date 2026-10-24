import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User
from src.security import get_password_hash
from src.settings import Settings

logger = logging.getLogger('uvicorn.error')


async def ensure_admin(session: AsyncSession, settings: Settings):
    """
    Garante que o administrador definido no .env exista.
    Se já houver um usuário com o ADMIN_EMAIL, ele é promovido a administrador;
    caso contrário, é criado com ADMIN_USERNAME e ADMIN_PASSWORD.
    A senha de um usuário existente nunca é alterada.
    """
    if not settings.ADMIN_EMAIL:
        logger.warning('ADMIN_EMAIL não definido: nenhum administrador configurado')
        return

    db_user = await session.scalar(select(User).where(User.email == settings.ADMIN_EMAIL))

    if db_user:
        if not db_user.is_admin:
            db_user.is_admin = True
            await session.commit()
        return

    if not settings.ADMIN_USERNAME or not settings.ADMIN_PASSWORD:
        logger.warning(
            'Defina ADMIN_USERNAME e ADMIN_PASSWORD para criar o administrador'
        )
        return

    username_taken = await session.scalar(
        select(User).where(User.username == settings.ADMIN_USERNAME)
    )
    if username_taken:
        logger.warning(
            'ADMIN_USERNAME "%s" já pertence a outro usuário', settings.ADMIN_USERNAME
        )
        return

    session.add(
        User(
            username=settings.ADMIN_USERNAME,
            password=get_password_hash(settings.ADMIN_PASSWORD),
            email=settings.ADMIN_EMAIL,
            is_admin=True,
        )
    )
    await session.commit()
