"""split denominacao_a intermunicipal into denominacao_a e denominacao_b

Revision ID: f6a4d3e2c1b0
Revises: e5f3c2a1b890
Create Date: 2026-04-23

"""
from alembic import op

revision = "f6a4d3e2c1b0"
down_revision = "e5f3c2a1b890"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE autos_linha
        SET
            denominacao_b = TRIM(SPLIT_PART(denominacao_a, ' - ', 2)),
            denominacao_a = TRIM(SPLIT_PART(denominacao_a, ' - ', 1))
        WHERE
            tipo = 'Regular – Intermunicipal'
            AND denominacao_b IS NULL
            AND denominacao_a IS NOT NULL
            AND denominacao_a LIKE '% - %'
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE autos_linha
        SET
            denominacao_a = denominacao_a || ' - ' || denominacao_b,
            denominacao_b = NULL
        WHERE
            tipo = 'Regular – Intermunicipal'
            AND denominacao_b IS NOT NULL
    """)
