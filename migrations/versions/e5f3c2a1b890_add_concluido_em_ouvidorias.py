"""add concluido_em to ouvidorias

Revision ID: e5f3c2a1b890
Revises: d4e2b1f9a703
Create Date: 2026-04-10

"""
from alembic import op
import sqlalchemy as sa

revision = "e5f3c2a1b890"
down_revision = "d4e2b1f9a703"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ouvidorias", sa.Column("concluido_em", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("ouvidorias", "concluido_em")
