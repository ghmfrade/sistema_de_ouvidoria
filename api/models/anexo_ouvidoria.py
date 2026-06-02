from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class AnexoOuvidoria(Base):
    __tablename__ = "anexos_ouvidoria"

    id: Mapped[int] = mapped_column(primary_key=True)
    ouvidoria_id: Mapped[int] = mapped_column(ForeignKey("ouvidorias.id"), nullable=False)
    nome_arquivo: Mapped[str] = mapped_column(String(300), nullable=False)
    nome_storage: Mapped[str] = mapped_column(String(300), nullable=False)
    tipo_mime: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tamanho: Mapped[int | None] = mapped_column(Integer, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    enviado_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)

    ouvidoria: Mapped["Ouvidoria"] = relationship(back_populates="anexos")
    enviado_por: Mapped["Usuario"] = relationship(foreign_keys=[enviado_por_id])

    def __repr__(self) -> str:
        return f"<AnexoOuvidoria {self.nome_arquivo} ouvidoria={self.ouvidoria_id}>"
