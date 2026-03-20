from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base
from .auto_linha import TipoServico


class Reclamacao(Base):
    __tablename__ = "reclamacoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    ouvidoria_id: Mapped[int] = mapped_column(ForeignKey("ouvidorias.id"), nullable=False)
    numero_item: Mapped[int] = mapped_column(Integer, nullable=False)
    categoria_id: Mapped[int | None] = mapped_column(ForeignKey("categorias.id"), nullable=True)
    subcategoria_id: Mapped[int | None] = mapped_column(ForeignKey("subcategorias.id"), nullable=True)
    tipo_servico: Mapped[TipoServico | None] = mapped_column(
        Enum(TipoServico, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    local_embarque: Mapped[str | None] = mapped_column(String(200), nullable=True)
    local_desembarque: Mapped[str | None] = mapped_column(String(200), nullable=True)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    empresa_fretamento: Mapped[str | None] = mapped_column(String(300), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    ouvidoria: Mapped["Ouvidoria"] = relationship(back_populates="reclamacoes")  # noqa: F821
    categoria: Mapped["Categoria | None"] = relationship(back_populates="reclamacoes")  # noqa: F821
    subcategoria: Mapped["Subcategoria | None"] = relationship()  # noqa: F821
    autos_vinculados: Mapped[list["ReclamacaoAuto"]] = relationship(  # noqa: F821
        "ReclamacaoAuto",
        foreign_keys="ReclamacaoAuto.reclamacao_id",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Reclamacao item={self.numero_item} ouvidoria={self.ouvidoria_id}>"
