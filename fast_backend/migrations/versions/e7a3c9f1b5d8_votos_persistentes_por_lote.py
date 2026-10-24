"""votos persistentes por lote

Votos cifrados passam a ser gravados como bytes, agrupados em lotes com
subtotal cifrado e comprovante (hash) encadeado:
- eleicao_candidato ganha 'posicao' (posição no vetor 1-hot);
- votos é recriada sem eleitor, candidato ou horário (WITHOUT ROWID);
- registro_eleicao é recriada com total em bytes, contadores e cadeia de hashes;
- novas tabelas participacoes, subtotais_lote e comprovantes.

ATENÇÃO: exige banco limpo. Os votos antigos guardavam só um UUID de um cache
em memória e não podem ser recuperados; votos e registros existentes são
descartados. Eleições abertas ou encerradas criadas antes desta revisão não
podem receber votos nem ser apuradas. O downgrade também descarta os votos.

Revision ID: e7a3c9f1b5d8
Revises: d5f9b2e4a7c3
Create Date: 2026-10-25 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7a3c9f1b5d8'
down_revision: Union[str, Sequence[str], None] = 'd5f9b2e4a7c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('eleicao_candidato') as batch_op:
        batch_op.add_column(sa.Column('posicao', sa.Integer(), nullable=True))
        batch_op.create_unique_constraint(
            'uq_eleicao_candidato_posicao', ['fk_election', 'posicao']
        )

    op.drop_table('votos')
    op.create_table('votos',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('fk_election', sa.Integer(), nullable=False),
    sa.Column('encrypted_vote', sa.LargeBinary(), nullable=False),
    sa.Column('receipt_hash', sa.String(length=64), nullable=False),
    sa.ForeignKeyConstraint(['fk_election'], ['eleicoes.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('receipt_hash'),
    sqlite_with_rowid=False,
    )

    op.drop_table('registro_eleicao')
    op.create_table('registro_eleicao',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('fk_election', sa.Integer(), nullable=False),
    sa.Column('encrypted_tally', sa.LargeBinary(), nullable=False),
    sa.Column('total_candidates', sa.Integer(), nullable=False),
    sa.Column('total_votos', sa.Integer(), nullable=False),
    sa.Column('lotes_fechados', sa.Integer(), nullable=False),
    sa.Column('hash_ultimo_lote', sa.String(length=64), nullable=False),
    sa.Column('resultado_json', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['fk_election'], ['eleicoes.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('fk_election')
    )

    op.create_table('participacoes',
    sa.Column('fk_user', sa.Integer(), nullable=False),
    sa.Column('fk_election', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['fk_election'], ['eleicoes.id'], ),
    sa.ForeignKeyConstraint(['fk_user'], ['usuarios.id'], ),
    sa.PrimaryKeyConstraint('fk_user', 'fk_election'),
    sqlite_with_rowid=False,
    )

    op.create_table('subtotais_lote',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('fk_election', sa.Integer(), nullable=False),
    sa.Column('numero_lote', sa.Integer(), nullable=False),
    sa.Column('qtd_votos', sa.Integer(), nullable=False),
    sa.Column('encrypted_subtotal', sa.LargeBinary(), nullable=False),
    sa.Column('hash_lote', sa.String(length=64), nullable=False),
    sa.ForeignKeyConstraint(['fk_election'], ['eleicoes.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('fk_election', 'numero_lote', name='uq_subtotais_lote_numero')
    )

    op.create_table('comprovantes',
    sa.Column('receipt_hash', sa.String(length=64), nullable=False),
    sa.Column('fk_election', sa.Integer(), nullable=False),
    sa.Column('numero_lote', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['fk_election'], ['eleicoes.id'], ),
    sa.PrimaryKeyConstraint('receipt_hash'),
    sqlite_with_rowid=False,
    )


def downgrade() -> None:
    """Downgrade schema (descarta votos, lotes e comprovantes)."""
    op.drop_table('comprovantes')
    op.drop_table('subtotais_lote')
    op.drop_table('participacoes')

    op.drop_table('registro_eleicao')
    op.create_table('registro_eleicao',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('fk_election', sa.Integer(), nullable=False),
    sa.Column('encrypted_tally', sa.String(), nullable=False),
    sa.Column('total_candidates', sa.Integer(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['fk_election'], ['eleicoes.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('fk_election')
    )

    op.drop_table('votos')
    op.create_table('votos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('fk_user', sa.Integer(), nullable=False),
    sa.Column('fk_election_candidate', sa.Integer(), nullable=False),
    sa.Column('encrypted_vote', sa.String(), nullable=False),
    sa.Column('zk_proof', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['fk_election_candidate'], ['eleicao_candidato.id'], ),
    sa.ForeignKeyConstraint(['fk_user'], ['usuarios.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    with op.batch_alter_table('eleicao_candidato') as batch_op:
        batch_op.drop_constraint('uq_eleicao_candidato_posicao', type_='unique')
        batch_op.drop_column('posicao')
