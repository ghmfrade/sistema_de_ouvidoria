import enum
from datetime import date, datetime
from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class StatusOuvidoria(str, enum.Enum):
    AGUARDANDO_ACOES = "Aguardando ações"
    AGUARDANDO_PERMISSIONARIA = "Aguardando resposta da permissionária"
    EM_ANALISE_TECNICA = "Em análise técnica"
    RETORNO_TECNICO = "Retorno técnico"
    CONCLUIDO = "Concluído"


class Ouvidoria(Base):
    __tablename__ = "ouvidorias"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero_sei: Mapped[str] = mapped_column(String(100), nullable=False)
    prazo: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[StatusOuvidoria] = mapped_column(
        Enum(StatusOuvidoria, values_callable=lambda x: [e.value for e in x]),
        default=StatusOuvidoria.AGUARDANDO_ACOES,
        nullable=False,
    )
    criado_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    criado_por: Mapped["Usuario"] = relationship(foreign_keys=[criado_por_id])  # noqa: F821
    reclamacoes: Mapped[list["Reclamacao"]] = relationship(  # noqa: F821
        back_populates="ouvidoria", cascade="all, delete-orphan", order_by="Reclamacao.numero_item"
    )
    atribuicoes: Mapped[list["OuvidoriaTecnico"]] = relationship(  # noqa: F821
        "OuvidoriaTecnico",
        foreign_keys="OuvidoriaTecnico.ouvidoria_id",
        cascade="all, delete-orphan",
    )
    respostas: Mapped[list["RespostaTecnica"]] = relationship(  # noqa: F821
        back_populates="ouvidoria", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Ouvidoria SEI={self.numero_sei} status={self.status}>"
