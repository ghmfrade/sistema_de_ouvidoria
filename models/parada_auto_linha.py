from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class ParadaAutoLinha(Base):
    __tablename__ = "paradas_auto_linha"

    id: Mapped[int] = mapped_column(primary_key=True)
    auto_id: Mapped[int] = mapped_column(ForeignKey("autos_linha.id"), nullable=False)
    cidade: Mapped[str] = mapped_column(String(200), nullable=False, index=True)

    auto: Mapped["AutoLinha"] = relationship(back_populates="paradas")  # noqa: F821

    def __repr__(self) -> str:
        return f"<ParadaAutoLinha auto_id={self.auto_id} cidade={self.cidade!r}>"
