"""exclusao logica

Adiciona 'deleted_at' em 'usuarios' para a exclusão lógica de quem já
participou de eleições. Eleições canceladas usam o novo valor 'cancelled'
na coluna 'status', que já existe.

Revision ID: d5f9b2e4a7c3
Revises: c4e8a1d3f6b9
Create Date: 2026-10-24 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5f9b2e4a7c3'
down_revision: Union[str, Sequence[str], None] = 'c4e8a1d3f6b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('usuarios') as batch_op:
        batch_op.add_column(sa.Column('deleted_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Eleições canceladas voltam a encerradas, último status válido antes desta versão
    op.execute("UPDATE eleicoes SET status = 'closed' WHERE status = 'cancelled'")
    with op.batch_alter_table('usuarios') as batch_op:
        batch_op.drop_column('deleted_at')
