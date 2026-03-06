from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class Permissionaria(Base):
    __tablename__ = "permissionarias"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)

    autos: Mapped[list["AutoLinha"]] = relationship(back_populates="permissionaria")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Permissionaria {self.nome}>"
