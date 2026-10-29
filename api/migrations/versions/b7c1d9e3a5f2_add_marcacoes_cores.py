"""add marcacoes por cor (ouvidoria_marcacoes e marcador_legendas)

Revision ID: b7c1d9e3a5f2
Revises: a2b3c4d5e6f7
Create Date: 2026-10-29
"""

revision = "b7c1d9e3a5f2"
down_revision = "a2b3c4d5e6f7"
branch_labels = None
depends_on = None

import sqlalchemy as sa
from alembic import op

_CORES = "('vermelho','laranja','amarelo','verde','azul','roxo','marrom')"


def upgrade() -> None:
    op.create_table(
        "ouvidoria_marcacoes",
        sa.Column("ouvidoria_id", sa.Integer(), sa.ForeignKey("ouvidorias.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("cor", sa.String(20), nullable=False),
        sa.Column("marcado_em", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(f"cor IN {_CORES}", name="ck_ouvidoria_marcacoes_cor"),
    )
    op.create_table(
        "marcador_legendas",
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("cor", sa.String(20), primary_key=True),
        sa.Column("rotulo", sa.String(40), nullable=False),
        sa.CheckConstraint(f"cor IN {_CORES}", name="ck_marcador_legendas_cor"),
    )


def downgrade() -> None:
    op.drop_table("marcador_legendas")
    op.drop_table("ouvidoria_marcacoes")
