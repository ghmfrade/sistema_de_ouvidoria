"""add tc to autos_linha

Revision ID: d4e2b1f9a703
Revises: c3f1a8e2d904
Create Date: 2026-04-06

tc = região tarifária do auto intermunicipal:
  1=Campinas, 2=Sorocaba, 3=Bauru, 4=Araraquara, 5=São Paulo
"""
from alembic import op
import sqlalchemy as sa

revision = "d4e2b1f9a703"
down_revision = "c3f1a8e2d904"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("autos_linha", sa.Column("tc", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("autos_linha", "tc")
