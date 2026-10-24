"""eleicao em configuracao

Novas eleições passam a nascer com status 'draft' (em configuração): o
administrador vincula os candidatos e depois abre a votação ('open').
Eleições existentes mantêm o status atual.

Revision ID: c4e8a1d3f6b9
Revises: b7d2f4a6c8e1
Create Date: 2026-10-24 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4e8a1d3f6b9'
down_revision: Union[str, Sequence[str], None] = 'b7d2f4a6c8e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('eleicoes') as batch_op:
        batch_op.alter_column('status', existing_type=sa.String(), server_default='draft')


def downgrade() -> None:
    """Downgrade schema."""
    # Eleições em configuração voltam a ser abertas, status que existia antes
    op.execute("UPDATE eleicoes SET status = 'open' WHERE status = 'draft'")
    with op.batch_alter_table('eleicoes') as batch_op:
        batch_op.alter_column('status', existing_type=sa.String(), server_default='open')
