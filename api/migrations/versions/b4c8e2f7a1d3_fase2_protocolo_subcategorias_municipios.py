"""fase2_protocolo_subcategorias_municipios_fretamento

Revision ID: b4c8e2f7a1d3
Revises: a3b7c9d1e2f4
Create Date: 2026-03-20 10:00:00.000000

Alteracoes cobertas:
- ouvidorias: remove numero_sei, adiciona protocolo, conteudo, prazo_permissionaria
- Nova tabela: subcategorias
- Nova tabela: municipios (IBGE)
- Nova tabela: anexos_ouvidoria
- Nova tabela: respostas_permissionaria
- reclamacoes: adiciona subcategoria_id, empresa_fretamento
- respostas_tecnicas: remove numero_sei_resposta
- Enum tiposervico: renomeia valores e adiciona fretamento
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4c8e2f7a1d3'
down_revision: Union[str, Sequence[str], None] = 'a3b7c9d1e2f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Enum tiposervico: renomear valores existentes e adicionar novos ──
    # Renomear 'Intermunicipal' → 'Regular – Intermunicipal'
    op.execute("ALTER TYPE tiposervico RENAME VALUE 'Intermunicipal' TO 'Regular – Intermunicipal'")
    # Renomear 'Metropolitano' → 'Regular – Metropolitano'
    op.execute("ALTER TYPE tiposervico RENAME VALUE 'Metropolitano' TO 'Regular – Metropolitano'")
    # Adicionar novos valores de fretamento
    op.execute("ALTER TYPE tiposervico ADD VALUE 'Fretamento Intermunicipal'")
    op.execute("ALTER TYPE tiposervico ADD VALUE 'Fretamento Metropolitano'")

    # ── 2. Tabela ouvidorias: remover numero_sei, adicionar protocolo/conteudo/prazo_perm ──
    op.execute("ALTER TABLE ouvidorias DROP COLUMN IF EXISTS numero_sei")
    op.execute("""
        ALTER TABLE ouvidorias
            ADD COLUMN protocolo VARCHAR(50) NOT NULL DEFAULT '',
            ADD COLUMN conteudo TEXT NOT NULL DEFAULT '',
            ADD COLUMN prazo_permissionaria DATE
    """)
    # Criar constraint unique para protocolo
    op.execute("ALTER TABLE ouvidorias ADD CONSTRAINT uq_ouvidorias_protocolo UNIQUE (protocolo)")
    # Remover defaults temporarios (usados apenas para nao quebrar registros existentes)
    op.execute("ALTER TABLE ouvidorias ALTER COLUMN protocolo DROP DEFAULT")
    op.execute("ALTER TABLE ouvidorias ALTER COLUMN conteudo DROP DEFAULT")

    # ── 3. Nova tabela: subcategorias ────────────────────────────────────────
    op.execute("""
        CREATE TABLE subcategorias (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(200) NOT NULL,
            categoria_id INTEGER NOT NULL REFERENCES categorias(id),
            ativo BOOLEAN NOT NULL DEFAULT TRUE
        )
    """)

    # ── 4. Nova tabela: municipios ───────────────────────────────────────────
    op.execute("""
        CREATE TABLE municipios (
            id SERIAL PRIMARY KEY,
            cod_ibge INTEGER NOT NULL UNIQUE,
            nome VARCHAR(200) NOT NULL,
            estado VARCHAR(2) NOT NULL,
            populacao INTEGER NOT NULL DEFAULT 0
        )
    """)

    # ── 5. Nova tabela: anexos_ouvidoria ─────────────────────────────────────
    op.execute("""
        CREATE TABLE anexos_ouvidoria (
            id SERIAL PRIMARY KEY,
            ouvidoria_id INTEGER NOT NULL REFERENCES ouvidorias(id),
            nome_arquivo VARCHAR(300) NOT NULL,
            nome_storage VARCHAR(300) NOT NULL,
            tipo_mime VARCHAR(100),
            tamanho INTEGER,
            criado_em TIMESTAMP NOT NULL DEFAULT now(),
            enviado_por_id INTEGER NOT NULL REFERENCES usuarios(id)
        )
    """)

    # ── 6. Nova tabela: respostas_permissionaria ─────────────────────────────
    op.execute("""
        CREATE TABLE respostas_permissionaria (
            id SERIAL PRIMARY KEY,
            ouvidoria_id INTEGER NOT NULL REFERENCES ouvidorias(id),
            conteudo TEXT NOT NULL,
            data_resposta DATE NOT NULL,
            criado_em TIMESTAMP NOT NULL DEFAULT now(),
            registrado_por_id INTEGER NOT NULL REFERENCES usuarios(id)
        )
    """)

    # ── 7. Tabela reclamacoes: adicionar subcategoria_id e empresa_fretamento ─
    op.execute("""
        ALTER TABLE reclamacoes
            ADD COLUMN subcategoria_id INTEGER REFERENCES subcategorias(id),
            ADD COLUMN empresa_fretamento VARCHAR(300)
    """)

    # ── 8. Tabela respostas_tecnicas: remover numero_sei_resposta ────────────
    op.execute("ALTER TABLE respostas_tecnicas DROP COLUMN IF EXISTS numero_sei_resposta")


def downgrade() -> None:
    # 8. Restaurar numero_sei_resposta
    op.execute("ALTER TABLE respostas_tecnicas ADD COLUMN numero_sei_resposta VARCHAR(100)")

    # 7. Remover colunas de reclamacoes
    op.execute("ALTER TABLE reclamacoes DROP COLUMN IF EXISTS empresa_fretamento")
    op.execute("ALTER TABLE reclamacoes DROP COLUMN IF EXISTS subcategoria_id")

    # 6. Remover respostas_permissionaria
    op.execute("DROP TABLE IF EXISTS respostas_permissionaria")

    # 5. Remover anexos_ouvidoria
    op.execute("DROP TABLE IF EXISTS anexos_ouvidoria")

    # 4. Remover municipios
    op.execute("DROP TABLE IF EXISTS municipios")

    # 3. Remover subcategorias
    op.execute("DROP TABLE IF EXISTS subcategorias")

    # 2. Restaurar ouvidorias
    op.execute("ALTER TABLE ouvidorias DROP CONSTRAINT IF EXISTS uq_ouvidorias_protocolo")
    op.execute("ALTER TABLE ouvidorias DROP COLUMN IF EXISTS prazo_permissionaria")
    op.execute("ALTER TABLE ouvidorias DROP COLUMN IF EXISTS conteudo")
    op.execute("ALTER TABLE ouvidorias DROP COLUMN IF EXISTS protocolo")
    op.execute("ALTER TABLE ouvidorias ADD COLUMN numero_sei VARCHAR(100) NOT NULL DEFAULT ''")
    op.execute("ALTER TABLE ouvidorias ALTER COLUMN numero_sei DROP DEFAULT")

    # 1. Reverter enum tiposervico (PostgreSQL nao suporta RENAME VALUE em downgrade
    # nem DROP VALUE — recriar o tipo seria necessario, mas isso envolve recriar colunas
    # dependentes. Em ambiente de producao, fazer manualmente.)
    # Nota: nao eh possivel remover valores de um enum no PostgreSQL sem recriar o tipo.
    # O downgrade do enum deve ser feito com DROP TYPE + CREATE TYPE + ALTER COLUMN
    # Deixamos como comentario pois envolve recriar todas as colunas dependentes.
    pass
