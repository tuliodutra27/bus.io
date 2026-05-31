import enum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db import Base


class Regime(str, enum.Enum):
    admin = "admin"   # administrativo (seg-qui 07-17, sex 07-16)
    turno = "turno"   # turno (07-19 ou 19-07, todos os dias)


class TipoOnibus(str, enum.Enum):
    admin = "admin"   # ônibus grande, 50 assentos
    micro = "micro"   # micro-ônibus de turno, 30 assentos


class TipoExcecao(str, enum.Enum):
    hora_extra = "hora_extra"
    ausencia = "ausencia"
    eventual = "eventual"


class StatusSolicitacao(str, enum.Enum):
    pendente = "pendente"
    aprovada = "aprovada"
    recusada = "recusada"


class Rota(Base):
    __tablename__ = "rotas"

    id = Column(Integer, primary_key=True)
    nome = Column(String(120), nullable=False)
    cidade = Column(String(120), nullable=False)
    bairros = Column(Text, nullable=True)      # bairros atendidos, separados por ";"
    horarios = Column(String(120), nullable=True)

    onibus = relationship("Onibus", back_populates="rota")
    colaboradores = relationship("Colaborador", back_populates="rota")

    def bairros_lista(self):
        if not self.bairros:
            return []
        return [b.strip() for b in self.bairros.split(";") if b.strip()]


class Onibus(Base):
    __tablename__ = "onibus"

    id = Column(Integer, primary_key=True)
    identificador = Column(String(40), nullable=False, unique=True)
    tipo = Column(Enum(TipoOnibus), nullable=False)
    capacidade = Column(Integer, nullable=False)
    rota_id = Column(Integer, ForeignKey("rotas.id"), nullable=True)
    ativo = Column(Boolean, default=True, nullable=False)
    # exemplo=True -> ônibus presente apenas para exibição (sem roster real no MVP)
    exemplo = Column(Boolean, default=False, nullable=False)

    rota = relationship("Rota", back_populates="onibus")
    assentos = relationship(
        "Assento", back_populates="onibus", cascade="all, delete-orphan"
    )


class Assento(Base):
    __tablename__ = "assentos"
    __table_args__ = (UniqueConstraint("onibus_id", "numero", name="uq_assento_onibus_numero"),)

    id = Column(Integer, primary_key=True)
    onibus_id = Column(Integer, ForeignKey("onibus.id"), nullable=False)
    numero = Column(Integer, nullable=False)
    fila = Column(Integer, nullable=False)
    coluna = Column(Integer, nullable=False)   # 1..4 (1,2 = esquerda | 3,4 = direita)
    lado = Column(String(10), nullable=False)  # "esq" | "dir"

    onibus = relationship("Onibus", back_populates="assentos")
    alocacao = relationship(
        "AlocacaoFixa", back_populates="assento", uselist=False,
        cascade="all, delete-orphan",
    )


class Colaborador(Base):
    __tablename__ = "colaboradores"

    id = Column(Integer, primary_key=True)
    nome = Column(String(160), nullable=False)
    matricula = Column(String(40), nullable=False, unique=True)
    setor = Column(String(120), nullable=True)
    telefone = Column(String(40), nullable=True)
    regime = Column(Enum(Regime), nullable=False)
    cidade = Column(String(120), nullable=False)
    bairro = Column(String(120), nullable=True)
    rota_id = Column(Integer, ForeignKey("rotas.id"), nullable=True)

    rota = relationship("Rota", back_populates="colaboradores")


class AlocacaoFixa(Base):
    """Roster permanente: assento que o colaborador ocupa no dia a dia."""

    __tablename__ = "alocacoes_fixas"

    id = Column(Integer, primary_key=True)
    assento_id = Column(Integer, ForeignKey("assentos.id"), nullable=False, unique=True)
    colaborador_id = Column(Integer, ForeignKey("colaboradores.id"), nullable=False)

    assento = relationship("Assento", back_populates="alocacao")
    colaborador = relationship("Colaborador")


class ExcecaoData(Base):
    """Ocupação pontual em uma data (hora extra, ausência ou eventual)."""

    __tablename__ = "excecoes_data"
    __table_args__ = (
        UniqueConstraint("data", "assento_id", name="uq_excecao_data_assento"),
    )

    id = Column(Integer, primary_key=True)
    data = Column(Date, nullable=False)
    assento_id = Column(Integer, ForeignKey("assentos.id"), nullable=False)
    colaborador_id = Column(Integer, ForeignKey("colaboradores.id"), nullable=True)
    tipo = Column(Enum(TipoExcecao), nullable=False)

    assento = relationship("Assento")
    colaborador = relationship("Colaborador")


class SolicitacaoHoraExtra(Base):
    """Registro/histórico da solicitação de hora extra."""

    __tablename__ = "solicitacoes_hora_extra"

    id = Column(Integer, primary_key=True)
    colaborador_id = Column(Integer, ForeignKey("colaboradores.id"), nullable=False)
    data = Column(Date, nullable=False)
    onibus_turno_id = Column(Integer, ForeignKey("onibus.id"), nullable=True)
    assento_id = Column(Integer, ForeignKey("assentos.id"), nullable=True)
    status = Column(Enum(StatusSolicitacao), default=StatusSolicitacao.pendente, nullable=False)

    colaborador = relationship("Colaborador")
    onibus_turno = relationship("Onibus")
    assento = relationship("Assento")
