"""Reestrutura trechos e permissionárias.

- Limpa dados de teste
- Remove paradas_auto_linha
- Adiciona cnpj e nome_fantasia em permissionarias
- Remove cidade_inicial e cidade_final de autos_linha
- Cria trechos_auto_linha com par ordenado (municipio_a_id < municipio_b_id)

Revision ID: c3f1a8e2d904
Revises: a1df29eaf9c5
Create Date: 2026-04-06
"""

from alembic import op
import sqlalchemy as sa

revision = "c3f1a8e2d904"
down_revision = "a1df29eaf9c5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Limpar dados de teste ──────────────────────────────────────────────
    op.execute("TRUNCATE TABLE reclamacao_autos RESTART IDENTITY CASCADE")
    op.execute("TRUNCATE TABLE paradas_auto_linha RESTART IDENTITY CASCADE")
    op.execute("TRUNCATE TABLE autos_linha RESTART IDENTITY CASCADE")
    op.execute("TRUNCATE TABLE permissionarias RESTART IDENTITY CASCADE")
    op.execute("TRUNCATE TABLE ouvidorias RESTART IDENTITY CASCADE")

    # ── 2. Remover tabela de paradas ──────────────────────────────────────────
    op.drop_table("paradas_auto_linha")

    # ── 3. Permissionárias: cnpj + nome_fantasia ──────────────────────────────
    op.add_column("permissionarias", sa.Column("cnpj", sa.String(20), nullable=False, server_default=""))
    op.add_column("permissionarias", sa.Column("nome_fantasia", sa.String(200), nullable=True))
    op.create_unique_constraint("uq_permissionarias_cnpj", "permissionarias", ["cnpj"])
    # Remover unique no nome (empresas podem ter nomes similares mas CNPJs distintos)
    op.drop_constraint("permissionarias_nome_key", "permissionarias", type_="unique")
    # Remover o server_default temporário
    op.alter_column("permissionarias", "cnpj", server_default=None)

    # ── 4. Autos: remover colunas de cidade ───────────────────────────────────
    op.drop_column("autos_linha", "cidade_inicial")
    op.drop_column("autos_linha", "cidade_final")

    # ── 5. Criar trechos_auto_linha ───────────────────────────────────────────
    op.create_table(
        "trechos_auto_linha",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("auto_id", sa.Integer(), sa.ForeignKey("autos_linha.id", ondelete="CASCADE"), nullable=False),
        sa.Column("municipio_a_id", sa.Integer(), sa.ForeignKey("municipios.id"), nullable=False),
        sa.Column("municipio_b_id", sa.Integer(), sa.ForeignKey("municipios.id"), nullable=False),
        sa.UniqueConstraint("auto_id", "municipio_a_id", "municipio_b_id", name="uq_trecho"),
        sa.CheckConstraint("municipio_a_id < municipio_b_id", name="ck_ordem"),
    )
    op.create_index("ix_trechos_auto",  "trechos_auto_linha", ["auto_id"])
    op.create_index("ix_trechos_mun_a", "trechos_auto_linha", ["municipio_a_id"])
    op.create_index("ix_trechos_mun_b", "trechos_auto_linha", ["municipio_b_id"])


def downgrade() -> None:
    op.drop_table("trechos_auto_linha")

    op.add_column("autos_linha", sa.Column("cidade_inicial", sa.String(200), nullable=True))
    op.add_column("autos_linha", sa.Column("cidade_final", sa.String(200), nullable=True))

    op.drop_constraint("uq_permissionarias_cnpj", "permissionarias", type_="unique")
    op.create_unique_constraint("permissionarias_nome_key", "permissionarias", ["nome"])
    op.drop_column("permissionarias", "nome_fantasia")
    op.drop_column("permissionarias", "cnpj")

    op.create_table(
        "paradas_auto_linha",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("auto_id", sa.Integer(), sa.ForeignKey("autos_linha.id"), nullable=False),
        sa.Column("cidade", sa.String(200), nullable=False),
        sa.Column("municipio_id", sa.Integer(), sa.ForeignKey("municipios.id", ondelete="SET NULL"), nullable=True),
    )
