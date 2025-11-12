from datetime import datetime

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
class Candidate:
    __tablename__ = 'candidatos'

    id: Mapped[int] = mapped_column(init=False, primary_key=True, nullable=False)
    username: Mapped[str] = mapped_column(nullable=False, unique=True)
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
class Election:
    __tablename__ = 'eleições'
    id: Mapped[int] = mapped_column(init=False, primary_key=True, nullable=False)
    title: Mapped[str] = mapped_column(nullable=False)


@table_registry.mapped_as_dataclass
# Tabela de relação de Candidato x Eleição
class Election_Candidate:
    __tablename__ = 'eleicao_candidato'

    id: Mapped[int] = mapped_column(init=False, primary_key=True, nullable=False)
    fk_election: Mapped[int] = mapped_column(ForeignKey('eleições.id'))
    fk_candidate: Mapped[int] = mapped_column(ForeignKey('candidatos.id'))


@table_registry.mapped_as_dataclass
# Tabela de relação de Voto x Eleição
class Vote_Election:
    __tablename__ = 'votos'

    id: Mapped[int] = mapped_column(init=False, primary_key=True, nullable=False)
    fk_user: Mapped[int] = mapped_column(ForeignKey('usuarios.id'))
    fk_election_candidate: Mapped[int] = mapped_column(ForeignKey('eleicao_candidato.id'))
    encrypted_vote: Mapped[str] = mapped_column(nullable=False)  # Voto criptografado (valor "1")
    created_at: Mapped[datetime] = mapped_column(
        init=False, nullable=False, server_default=func.now()
    )


@table_registry.mapped_as_dataclass
# Tabela para armazenar o registro criptografado de cada eleição
class Election_Tally:
    __tablename__ = 'registro_eleicao'

    id: Mapped[int] = mapped_column(init=False, primary_key=True, nullable=False)
    fk_election: Mapped[int] = mapped_column(ForeignKey('eleições.id'), unique=True)
    encrypted_tally: Mapped[str] = mapped_column(nullable=False)
    total_candidates: Mapped[int] = mapped_column(nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        init=False,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
