from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class AutoLinha(Base):
    __tablename__ = "autos_linha"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    itinerario: Mapped[str | None] = mapped_column(Text, nullable=True)
    cidade_inicial: Mapped[str | None] = mapped_column(String(200), nullable=True)
    cidade_final: Mapped[str | None] = mapped_column(String(200), nullable=True)
    permissionaria_id: Mapped[int | None] = mapped_column(ForeignKey("permissionarias.id"), nullable=True)

    permissionaria: Mapped["Permissionaria | None"] = relationship(back_populates="autos")  # noqa: F821
    paradas: Mapped[list["ParadaAutoLinha"]] = relationship(  # noqa: F821
        back_populates="auto", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<AutoLinha {self.numero}>"
