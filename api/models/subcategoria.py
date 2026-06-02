from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class Subcategoria(Base):
    __tablename__ = "subcategorias"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    categoria_id: Mapped[int] = mapped_column(ForeignKey("categorias.id"), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    categoria: Mapped["Categoria"] = relationship(back_populates="subcategorias")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Subcategoria {self.nome} cat={self.categoria_id}>"
