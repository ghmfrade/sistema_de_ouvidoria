import enum
from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class TipoUsuario(str, enum.Enum):
    gestor = "gestor"
    tecnico = "tecnico"


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    tipo: Mapped[TipoUsuario] = mapped_column(Enum(TipoUsuario), nullable=False)
    gerencia_id: Mapped[int | None] = mapped_column(ForeignKey("gerencias.id"), nullable=True)
    coordenacao_id: Mapped[int | None] = mapped_column(ForeignKey("coordenacoes.id"), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    gerencia: Mapped["Gerencia | None"] = relationship(back_populates="usuarios")  # noqa: F821
    coordenacao: Mapped["Coordenacao | None"] = relationship(back_populates="usuarios")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Usuario {self.email} ({self.tipo})>"
