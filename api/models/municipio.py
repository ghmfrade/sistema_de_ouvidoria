from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class Municipio(Base):
    __tablename__ = "municipios"

    id: Mapped[int] = mapped_column(primary_key=True)
    cod_ibge: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    estado: Mapped[str] = mapped_column(String(2), nullable=False)
    populacao: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def __repr__(self) -> str:
        return f"<Municipio {self.nome}/{self.estado}>"
