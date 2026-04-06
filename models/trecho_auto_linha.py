from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class TrechoAutoLinha(Base):
    __tablename__ = "trechos_auto_linha"

    id:             Mapped[int] = mapped_column(primary_key=True)
    auto_id:        Mapped[int] = mapped_column(ForeignKey("autos_linha.id", ondelete="CASCADE"), nullable=False, index=True)
    municipio_a_id: Mapped[int] = mapped_column(ForeignKey("municipios.id"), nullable=False, index=True)
    municipio_b_id: Mapped[int] = mapped_column(ForeignKey("municipios.id"), nullable=False, index=True)

    auto:        Mapped["AutoLinha"] = relationship(back_populates="trechos")  # noqa: F821
    municipio_a: Mapped["Municipio"] = relationship(foreign_keys=[municipio_a_id])  # noqa: F821
    municipio_b: Mapped["Municipio"] = relationship(foreign_keys=[municipio_b_id])  # noqa: F821

    __table_args__ = (
        UniqueConstraint("auto_id", "municipio_a_id", "municipio_b_id", name="uq_trecho"),
        CheckConstraint("municipio_a_id < municipio_b_id", name="ck_ordem"),
    )

    def __repr__(self) -> str:
        return f"<TrechoAutoLinha auto_id={self.auto_id} {self.municipio_a_id}↔{self.municipio_b_id}>"
