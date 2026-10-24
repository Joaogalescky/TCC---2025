from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    ForeignKey,
    LargeBinary,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, registry

table_registry = registry()


@table_registry.mapped_as_dataclass
class User:
    __tablename__ = 'usuarios'

    id: Mapped[int] = mapped_column(init=False, primary_key=True, nullable=False)
    username: Mapped[str] = mapped_column(nullable=False, unique=True)
    password: Mapped[str] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(nullable=False, unique=True)
    statusVotacao: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text('0')
    )
    # Definido pelo administrador; quem não é candidato é eleitor (ambos votam)
    is_candidate: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text('0')
    )
    is_admin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text('0')
    )
    # Exclusão lógica: preenchido quando quem participou de eleições exclui a conta
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        init=False, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        init=False,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class ElectionStatus(StrEnum):
    # em configuração (candidatos) -> aberta (votação) -> encerrada -> apurada
    # aberta ou encerrada com votos podem ser canceladas (exclusão lógica)
    DRAFT = 'draft'
    OPEN = 'open'
    CLOSED = 'closed'
    TALLIED = 'tallied'
    CANCELLED = 'cancelled'


@table_registry.mapped_as_dataclass
class Election:
    __tablename__ = 'eleicoes'
    id: Mapped[int] = mapped_column(init=False, primary_key=True, nullable=False)
    title: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(
        nullable=False, default=ElectionStatus.DRAFT, server_default=ElectionStatus.DRAFT
    )
    created_at: Mapped[datetime] = mapped_column(
        init=False, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        init=False,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


# Privacidade do voto: nenhuma tabela ligada a votos guarda horário, ordem de
# chegada ou o eleitor. Em SQLite uma tabela comum tem um rowid implícito na
# ordem de inserção; por isso votos, participações e comprovantes são
# WITHOUT ROWID, com chave primária não sequencial.
WITHOUT_ROWID = {'sqlite_with_rowid': False}
HASH_LENGTH = 64  # SHA-256 em hexadecimal


@table_registry.mapped_as_dataclass
# Tabela de relação de Candidato (usuário com is_candidate) x Eleição
class Election_Candidate:
    __tablename__ = 'eleicao_candidato'
    __table_args__ = (
        UniqueConstraint('fk_election', 'posicao', name='uq_eleicao_candidato_posicao'),
    )

    id: Mapped[int] = mapped_column(init=False, primary_key=True, nullable=False)
    fk_election: Mapped[int] = mapped_column(ForeignKey('eleicoes.id'))
    fk_candidate: Mapped[int] = mapped_column(ForeignKey('usuarios.id'))
    # Posição no vetor 1-hot, atribuída ao abrir a eleição e fixa depois
    posicao: Mapped[int | None] = mapped_column(nullable=True, default=None)


@table_registry.mapped_as_dataclass
# Quem já votou: impede o voto duplo sem ligar a pessoa ao voto
class Participation:
    __tablename__ = 'participacoes'
    __table_args__ = WITHOUT_ROWID

    fk_user: Mapped[int] = mapped_column(ForeignKey('usuarios.id'), primary_key=True)
    fk_election: Mapped[int] = mapped_column(ForeignKey('eleicoes.id'), primary_key=True)


@table_registry.mapped_as_dataclass
# Votos do lote aberto; apagados quando o lote fecha
class Vote_Election:
    __tablename__ = 'votos'
    __table_args__ = WITHOUT_ROWID

    # UUID4 aleatório: não revela a ordem de chegada
    id: Mapped[str] = mapped_column(primary_key=True)
    fk_election: Mapped[int] = mapped_column(ForeignKey('eleicoes.id'))
    # Vetor 1-hot cifrado e serializado
    encrypted_vote: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    # Comprovante entregue ao eleitor: SHA-256 de encrypted_vote
    receipt_hash: Mapped[str] = mapped_column(
        String(HASH_LENGTH), unique=True, nullable=False
    )


@table_registry.mapped_as_dataclass
# Total cifrado de cada eleição, criado ao abrir a votação
class Election_Tally:
    __tablename__ = 'registro_eleicao'

    id: Mapped[int] = mapped_column(init=False, primary_key=True, nullable=False)
    fk_election: Mapped[int] = mapped_column(ForeignKey('eleicoes.id'), unique=True)
    # Soma incremental, voto a voto (caminho 1 da dupla contagem)
    encrypted_tally: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    total_candidates: Mapped[int] = mapped_column(nullable=False)
    # Quantidade de votantes, pública como em qualquer eleição
    total_votos: Mapped[int] = mapped_column(nullable=False, default=0)
    lotes_fechados: Mapped[int] = mapped_column(nullable=False, default=0)
    hash_ultimo_lote: Mapped[str] = mapped_column(
        String(HASH_LENGTH), nullable=False, default='0' * HASH_LENGTH
    )
    # Resultado decifrado, gravado na apuração
    resultado_json: Mapped[str | None] = mapped_column(nullable=True, default=None)


@table_registry.mapped_as_dataclass
# Subtotal cifrado de cada lote fechado
class Lot_Subtotal:
    __tablename__ = 'subtotais_lote'
    __table_args__ = (
        UniqueConstraint('fk_election', 'numero_lote', name='uq_subtotais_lote_numero'),
    )

    id: Mapped[int] = mapped_column(init=False, primary_key=True, nullable=False)
    fk_election: Mapped[int] = mapped_column(ForeignKey('eleicoes.id'))
    numero_lote: Mapped[int] = mapped_column(nullable=False)
    qtd_votos: Mapped[int] = mapped_column(nullable=False)
    # Soma recalculada do zero com os votos do lote (caminho 2)
    encrypted_subtotal: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    # Elo da cadeia de hashes entre os lotes
    hash_lote: Mapped[str] = mapped_column(String(HASH_LENGTH), nullable=False)


@table_registry.mapped_as_dataclass
# Comprovantes dos lotes fechados, sempre lidos ordenados pelo próprio hash
class Receipt:
    __tablename__ = 'comprovantes'
    __table_args__ = WITHOUT_ROWID

    receipt_hash: Mapped[str] = mapped_column(String(HASH_LENGTH), primary_key=True)
    fk_election: Mapped[int] = mapped_column(ForeignKey('eleicoes.id'))
    numero_lote: Mapped[int] = mapped_column(nullable=False)
