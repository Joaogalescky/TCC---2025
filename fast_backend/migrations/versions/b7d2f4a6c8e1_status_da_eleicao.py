"""status da eleicao

Adiciona 'status' em 'eleicoes': open (aberta), closed (encerrada) ou
tallied (apurada). Eleições existentes continuam abertas.

Revision ID: b7d2f4a6c8e1
Revises: a3c1e5f7b9d2
Create Date: 2026-10-23 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7d2f4a6c8e1'
down_revision: Union[str, Sequence[str], None] = 'a3c1e5f7b9d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('eleicoes') as batch_op:
        batch_op.add_column(sa.Column('status', sa.String(), server_default='open', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('eleicoes') as batch_op:
        batch_op.drop_column('status')
