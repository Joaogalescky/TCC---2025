from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from .settings import Settings

engine = create_async_engine(Settings().DATABASE_URL)


@event.listens_for(engine.sync_engine, 'connect')
def _sqlite_pragmas(dbapi_connection, connection_record):
    # Sobrescreve com zeros o conteúdo apagado (votos de lotes já fechados),
    # para que não possa ser recuperado das páginas livres do arquivo
    if engine.dialect.name != 'sqlite':
        return
    cursor = dbapi_connection.cursor()
    cursor.execute('PRAGMA secure_delete = ON')
    cursor.close()


async def get_session():
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session


async def begin_immediate(session: AsyncSession):
    """
    Abre uma transação de escrita exclusiva no SQLite (BEGIN IMMEDIATE):
    outra transação que tente escrever espera esta terminar, evitando que
    dois votos leiam o mesmo total cifrado (lost update).
    """
    conn = await session.connection()
    if conn.dialect.name != 'sqlite':
        return
    raw = await conn.get_raw_connection()
    if not raw.driver_connection.in_transaction:
        await conn.exec_driver_sql('BEGIN IMMEDIATE')
