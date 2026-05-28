"""protocolo_bigint

Revision ID: g7h5i3j1k209
Revises: a2b3c4d5e6f7
Create Date: 2026-05-28 12:00:00.000000

Alteracoes cobertas:
- ouvidorias: converte protocolo de VARCHAR(50) para BIGINT
- Remove o sufixo '.0' residual de valores inseridos via pandas/importação
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g7h5i3j1k209'
down_revision: Union[str, Sequence[str], None] = 'a2b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Limpa valores "123.0" residuais antes de converter o tipo
    op.execute(
        "UPDATE ouvidorias SET protocolo = SPLIT_PART(protocolo, '.', 1) WHERE protocolo LIKE '%.%'"
    )
    # Converte VARCHAR(50) → BIGINT; USING faz o cast implícito
    op.execute(
        "ALTER TABLE ouvidorias ALTER COLUMN protocolo TYPE BIGINT USING protocolo::BIGINT"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE ouvidorias ALTER COLUMN protocolo TYPE VARCHAR(50) USING protocolo::VARCHAR"
    )
