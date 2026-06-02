from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class Gerencia(Base):
    __tablename__ = "gerencias"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    coordenacoes: Mapped[list["Coordenacao"]] = relationship(back_populates="gerencia")  # noqa: F821
    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="gerencia")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Gerencia {self.nome}>"
