import enum

from sqlalchemy import Boolean, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class TipoServico(str, enum.Enum):
    REGULAR_INTERMUNICIPAL = "Regular – Intermunicipal"
    REGULAR_METROPOLITANO = "Regular – Metropolitano"
    FRETAMENTO_INTERMUNICIPAL = "Fretamento Intermunicipal"
    FRETAMENTO_METROPOLITANO = "Fretamento Metropolitano"


class AutoLinha(Base):
    __tablename__ = "autos_linha"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[str] = mapped_column(String(50), nullable=False)
    tipo: Mapped[TipoServico] = mapped_column(
        Enum(TipoServico, values_callable=lambda x: [e.value for e in x]),
        default=TipoServico.REGULAR_INTERMUNICIPAL,
        server_default=TipoServico.REGULAR_INTERMUNICIPAL.value,
        nullable=False,
    )
    itinerario: Mapped[str | None] = mapped_column(Text, nullable=True)
    cidade_inicial: Mapped[str | None] = mapped_column(String(200), nullable=True)
    cidade_final: Mapped[str | None] = mapped_column(String(200), nullable=True)
    permissionaria_id: Mapped[int | None] = mapped_column(ForeignKey("permissionarias.id"), nullable=True)

    # Campos específicos de linhas metropolitanas
    regiao_metropolitana: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sub_regiao: Mapped[str | None] = mapped_column(String(100), nullable=True)
    nome_fantasia: Mapped[str | None] = mapped_column(String(200), nullable=True)
    denominacao_a: Mapped[str | None] = mapped_column(String(300), nullable=True)
    denominacao_b: Mapped[str | None] = mapped_column(String(300), nullable=True)
    via: Mapped[str | None] = mapped_column(String(200), nullable=True)
    servico: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)

    permissionaria: Mapped["Permissionaria | None"] = relationship(back_populates="autos")  # noqa: F821
    paradas: Mapped[list["ParadaAutoLinha"]] = relationship(  # noqa: F821
        back_populates="auto", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index(
            "uix_auto_numero_tipo_rm",
            numero, tipo, func.coalesce(regiao_metropolitana, ""),
            unique=True,
        ),
    )

    def __repr__(self) -> str:
        return f"<AutoLinha {self.numero} tipo={self.tipo.value}>"
