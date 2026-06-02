"""add_tipo_servico_metropolitano

Revision ID: a3b7c9d1e2f4
Revises: de19d1b30b44
Create Date: 2026-03-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3b7c9d1e2f4'
down_revision: Union[str, Sequence[str], None] = 'de19d1b30b44'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adiciona suporte a linhas metropolitanas."""
    # 1. Criar enum tiposervico
    op.execute("CREATE TYPE tiposervico AS ENUM ('Intermunicipal', 'Metropolitano')")

    # 2. Adicionar colunas em autos_linha
    op.execute("""
        ALTER TABLE autos_linha
            ADD COLUMN tipo tiposervico NOT NULL DEFAULT 'Intermunicipal',
            ADD COLUMN regiao_metropolitana VARCHAR(100),
            ADD COLUMN sub_regiao VARCHAR(100),
            ADD COLUMN nome_fantasia VARCHAR(200),
            ADD COLUMN denominacao_a VARCHAR(300),
            ADD COLUMN denominacao_b VARCHAR(300),
            ADD COLUMN via VARCHAR(200),
            ADD COLUMN servico VARCHAR(100),
            ADD COLUMN ativo BOOLEAN NOT NULL DEFAULT TRUE
    """)

    # 3. Backfill registros existentes
    op.execute("UPDATE autos_linha SET tipo = 'Intermunicipal' WHERE tipo IS NULL")

    # 4. Trocar unique constraint do numero por unique index composto
    op.execute("ALTER TABLE autos_linha DROP CONSTRAINT IF EXISTS autos_linha_numero_key")
    op.execute("""
        CREATE UNIQUE INDEX uix_auto_numero_tipo_rm
        ON autos_linha (numero, tipo, COALESCE(regiao_metropolitana, ''))
    """)

    # 5. Adicionar tipo_servico em reclamacoes
    op.execute("""
        ALTER TABLE reclamacoes
            ADD COLUMN tipo_servico tiposervico
    """)


def downgrade() -> None:
    """Remove suporte a linhas metropolitanas."""
    # Remover coluna tipo_servico de reclamacoes
    op.execute("ALTER TABLE reclamacoes DROP COLUMN IF EXISTS tipo_servico")

    # Remover unique index composto
    op.execute("DROP INDEX IF EXISTS uix_auto_numero_tipo_rm")

    # Remover linhas metropolitanas antes de restaurar constraint original
    op.execute("DELETE FROM paradas_auto_linha WHERE auto_id IN (SELECT id FROM autos_linha WHERE tipo = 'Metropolitano')")
    op.execute("DELETE FROM reclamacao_autos WHERE auto_id IN (SELECT id FROM autos_linha WHERE tipo = 'Metropolitano')")
    op.execute("DELETE FROM autos_linha WHERE tipo = 'Metropolitano'")

    # Restaurar unique constraint original
    op.execute("ALTER TABLE autos_linha ADD CONSTRAINT autos_linha_numero_key UNIQUE (numero)")

    # Remover colunas metropolitanas
    op.execute("""
        ALTER TABLE autos_linha
            DROP COLUMN IF EXISTS tipo,
            DROP COLUMN IF EXISTS regiao_metropolitana,
            DROP COLUMN IF EXISTS sub_regiao,
            DROP COLUMN IF EXISTS nome_fantasia,
            DROP COLUMN IF EXISTS denominacao_a,
            DROP COLUMN IF EXISTS denominacao_b,
            DROP COLUMN IF EXISTS via,
            DROP COLUMN IF EXISTS servico,
            DROP COLUMN IF EXISTS ativo
    """)

    # Remover enum
    op.execute("DROP TYPE IF EXISTS tiposervico")
