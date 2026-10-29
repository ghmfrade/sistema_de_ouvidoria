import enum
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class CorMarcacao(str, enum.Enum):
    vermelho = "vermelho"
    laranja = "laranja"
    amarelo = "amarelo"
    verde = "verde"
    azul = "azul"
    roxo = "roxo"
    marrom = "marrom"


class OuvidoriaMarcacao(Base):
    """Cor que um login atribui a uma ouvidoria. Independente de ouvidoria_tecnicos."""
    __tablename__ = "ouvidoria_marcacoes"

    ouvidoria_id: Mapped[int] = mapped_column(
        ForeignKey("ouvidorias.id", ondelete="CASCADE"), primary_key=True
    )
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True
    )
    cor: Mapped[str] = mapped_column(String(20), nullable=False)
    marcado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class MarcadorLegenda(Base):
    """Nome (rótulo) que um login dá a cada cor da paleta."""
    __tablename__ = "marcador_legendas"

    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True
    )
    cor: Mapped[str] = mapped_column(String(20), primary_key=True)
    rotulo: Mapped[str] = mapped_column(String(40), nullable=False)
