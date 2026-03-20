from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class Coordenacao(Base):
    __tablename__ = "coordenacoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    gerencia_id: Mapped[int] = mapped_column(ForeignKey("gerencias.id"), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    gerencia: Mapped["Gerencia"] = relationship(back_populates="coordenacoes")  # noqa: F821
    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="coordenacao")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Coordenacao {self.nome}>"
