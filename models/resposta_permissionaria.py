from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class RespostaPermissionaria(Base):
    __tablename__ = "respostas_permissionaria"

    id: Mapped[int] = mapped_column(primary_key=True)
    ouvidoria_id: Mapped[int] = mapped_column(ForeignKey("ouvidorias.id"), nullable=False)
    conteudo: Mapped[str] = mapped_column(Text, nullable=False)
    data_resposta: Mapped[date] = mapped_column(Date, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    registrado_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)

    ouvidoria: Mapped["Ouvidoria"] = relationship(back_populates="respostas_permissionaria")
    registrado_por: Mapped["Usuario"] = relationship(foreign_keys=[registrado_por_id])

    def __repr__(self) -> str:
        return f"<RespostaPermissionaria ouvidoria={self.ouvidoria_id} data={self.data_resposta}>"
