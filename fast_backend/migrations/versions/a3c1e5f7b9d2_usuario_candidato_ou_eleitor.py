"""usuario candidato ou eleitor

Unifica candidatos e eleitores na tabela 'usuarios':
- adiciona 'is_candidate' e 'is_admin' em 'usuarios';
- 'eleicao_candidato.fk_candidate' passa a referenciar 'usuarios.id';
- remove a tabela 'candidatos'.

Os candidatos antigos não têm e-mail nem senha, então vínculos, votos e
registros de apuração existentes são apagados.

Revision ID: a3c1e5f7b9d2
Revises: 51ff67aac2d9
Create Date: 2026-10-23 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3c1e5f7b9d2'
down_revision: Union[str, Sequence[str], None] = '51ff67aac2d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _recreate_eleicao_candidato(candidate_table: str) -> None:
    op.drop_table('eleicao_candidato')
    op.create_table('eleicao_candidato',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('fk_election', sa.Integer(), nullable=False),
    sa.Column('fk_candidate', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['fk_candidate'], [f'{candidate_table}.id'], ),
    sa.ForeignKeyConstraint(['fk_election'], ['eleicoes.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def upgrade() -> None:
    """Upgrade schema."""
    op.execute('DELETE FROM votos')
    op.execute('DELETE FROM registro_eleicao')

    with op.batch_alter_table('usuarios') as batch_op:
        batch_op.add_column(sa.Column('is_candidate', sa.Boolean(), server_default=sa.text('0'), nullable=False))
        batch_op.add_column(sa.Column('is_admin', sa.Boolean(), server_default=sa.text('0'), nullable=False))

    _recreate_eleicao_candidato('usuarios')
    op.drop_table('candidatos')


def downgrade() -> None:
    """Downgrade schema."""
    op.execute('DELETE FROM votos')
    op.execute('DELETE FROM registro_eleicao')

    op.create_table('candidatos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('username')
    )
    _recreate_eleicao_candidato('candidatos')

    with op.batch_alter_table('usuarios') as batch_op:
        batch_op.drop_column('is_admin')
        batch_op.drop_column('is_candidate')
