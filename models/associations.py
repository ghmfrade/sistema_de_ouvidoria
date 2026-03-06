from datetime import datetime
from decimal import Decimal
from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class OuvidoriaTecnico(Base):
    """Relação N:N entre Ouvidoria e Usuário técnico."""
    __tablename__ = "ouvidoria_tecnicos"

    ouvidoria_id: Mapped[int] = mapped_column(ForeignKey("ouvidorias.id"), primary_key=True)
    tecnico_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), primary_key=True)
    respondido: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    respondido_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ReclamacaoAuto(Base):
    """Relação N:N entre Reclamação e Auto de Linha com pontuação calculada."""
    __tablename__ = "reclamacao_autos"

    reclamacao_id: Mapped[int] = mapped_column(ForeignKey("reclamacoes.id"), primary_key=True)
    auto_id: Mapped[int] = mapped_column(ForeignKey("autos_linha.id"), primary_key=True)
    pontuacao: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
