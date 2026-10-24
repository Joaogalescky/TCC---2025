from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, ForeignKey, func, text
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
    created_at: Mapped[datetime] = mapped_column(
        init=False, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        init=False,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ElectionStatus(StrEnum):
    # aberta -> encerrada (sem novos votos) -> apurada (resultado publicado)
    OPEN = 'open'
    CLOSED = 'closed'
    TALLIED = 'tallied'


@table_registry.mapped_as_dataclass
class Election:
    __tablename__ = 'eleicoes'
    id: Mapped[int] = mapped_column(init=False, primary_key=True, nullable=False)
    title: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(
        nullable=False, default=ElectionStatus.OPEN, server_default=ElectionStatus.OPEN
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


@table_registry.mapped_as_dataclass
# Tabela de relação de Candidato (usuário com is_candidate) x Eleição
class Election_Candidate:
    __tablename__ = 'eleicao_candidato'

    id: Mapped[int] = mapped_column(init=False, primary_key=True, nullable=False)
    fk_election: Mapped[int] = mapped_column(ForeignKey('eleicoes.id'))
    fk_candidate: Mapped[int] = mapped_column(ForeignKey('usuarios.id'))


@table_registry.mapped_as_dataclass
# Tabela de relação de Voto x Eleição
class Vote_Election:
    __tablename__ = 'votos'

    id: Mapped[int] = mapped_column(init=False, primary_key=True, nullable=False)
    fk_user: Mapped[int] = mapped_column(ForeignKey('usuarios.id'))
    fk_election_candidate: Mapped[int] = mapped_column(ForeignKey('eleicao_candidato.id'))
    # Voto criptografado (valor "1")
    encrypted_vote: Mapped[str] = mapped_column(nullable=False)
    # Prova ZK de 1-hot
    zk_proof: Mapped[str] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        init=False, nullable=False, server_default=func.now()
    )


@table_registry.mapped_as_dataclass
# Tabela para armazenar o registro criptografado de cada eleição
class Election_Tally:
    __tablename__ = 'registro_eleicao'

    id: Mapped[int] = mapped_column(init=False, primary_key=True, nullable=False)
    fk_election: Mapped[int] = mapped_column(ForeignKey('eleicoes.id'), unique=True)
    encrypted_tally: Mapped[str] = mapped_column(nullable=False)
    total_candidates: Mapped[int] = mapped_column(nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        init=False,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
