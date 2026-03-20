"""add_ativo_gerencia_coordenacao

Revision ID: de19d1b30b44
Revises: 05df12ff552c
Create Date: 2026-03-06 10:20:13.142355

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'de19d1b30b44'
down_revision: Union[str, Sequence[str], None] = '05df12ff552c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TABLE gerencias ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT TRUE")
    op.execute("ALTER TABLE coordenacoes ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT TRUE")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE coordenacoes DROP COLUMN IF EXISTS ativo")
    op.execute("ALTER TABLE gerencias DROP COLUMN IF EXISTS ativo")
