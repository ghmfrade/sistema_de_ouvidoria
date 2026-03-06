from datetime import date, datetime
from sqlalchemy import Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class RespostaTecnica(Base):
    __tablename__ = "respostas_tecnicas"

    id: Mapped[int] = mapped_column(primary_key=True)
    ouvidoria_id: Mapped[int] = mapped_column(ForeignKey("ouvidorias.id"), nullable=False)
    tecnico_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    numero_sei_resposta: Mapped[str | None] = mapped_column(String(100), nullable=True)
    data_resposta: Mapped[date] = mapped_column(Date, nullable=False)
    texto_resposta: Mapped[str] = mapped_column(Text, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    ouvidoria: Mapped["Ouvidoria"] = relationship(back_populates="respostas")  # noqa: F821
    tecnico: Mapped["Usuario"] = relationship(foreign_keys=[tecnico_id])  # noqa: F821

    def __repr__(self) -> str:
        return f"<RespostaTecnica ouvidoria={self.ouvidoria_id} tecnico={self.tecnico_id}>"
