"""initial_schema

Revision ID: 05df12ff552c
Revises: 
Create Date: 2026-03-06 09:43:46.032046

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '05df12ff552c'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Cria todas as tabelas do schema inicial."""
    op.execute("CREATE SCHEMA IF NOT EXISTS ouvidoria")
    op.execute("CREATE TYPE tipousuario AS ENUM ('gestor', 'tecnico')")
    op.execute("""
        CREATE TYPE statusouvidoria AS ENUM (
            'Aguardando ações',
            'Aguardando resposta da permissionária',
            'Em análise técnica',
            'Retorno técnico',
            'Concluído'
        )
    """)
    op.execute("""
        CREATE TABLE permissionarias (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(200) NOT NULL UNIQUE
        )
    """)
    op.execute("""
        CREATE TABLE gerencias (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(200) NOT NULL UNIQUE
        )
    """)
    op.execute("""
        CREATE TABLE categorias (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(200) NOT NULL UNIQUE,
            descricao TEXT,
            ativo BOOLEAN NOT NULL DEFAULT TRUE
        )
    """)
    op.execute("""
        CREATE TABLE coordenacoes (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(200) NOT NULL,
            gerencia_id INTEGER NOT NULL REFERENCES gerencias(id)
        )
    """)
    op.execute("""
        CREATE TABLE autos_linha (
            id SERIAL PRIMARY KEY,
            numero VARCHAR(50) NOT NULL UNIQUE,
            itinerario TEXT,
            cidade_inicial VARCHAR(200),
            cidade_final VARCHAR(200),
            permissionaria_id INTEGER REFERENCES permissionarias(id)
        )
    """)
    op.execute("""
        CREATE TABLE usuarios (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(200) NOT NULL,
            email VARCHAR(200) NOT NULL UNIQUE,
            senha_hash VARCHAR(200) NOT NULL,
            tipo tipousuario NOT NULL,
            gerencia_id INTEGER REFERENCES gerencias(id),
            coordenacao_id INTEGER REFERENCES coordenacoes(id),
            ativo BOOLEAN NOT NULL DEFAULT TRUE
        )
    """)
    op.execute("""
        CREATE TABLE ouvidorias (
            id SERIAL PRIMARY KEY,
            numero_sei VARCHAR(100) NOT NULL,
            prazo DATE NOT NULL,
            status statusouvidoria NOT NULL DEFAULT 'Aguardando ações',
            criado_por_id INTEGER NOT NULL REFERENCES usuarios(id),
            criado_em TIMESTAMP NOT NULL DEFAULT now(),
            atualizado_em TIMESTAMP NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE TABLE reclamacoes (
            id SERIAL PRIMARY KEY,
            ouvidoria_id INTEGER NOT NULL REFERENCES ouvidorias(id),
            numero_item INTEGER NOT NULL,
            categoria_id INTEGER REFERENCES categorias(id),
            local_embarque VARCHAR(200),
            local_desembarque VARCHAR(200),
            descricao TEXT,
            criado_em TIMESTAMP NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE TABLE respostas_tecnicas (
            id SERIAL PRIMARY KEY,
            ouvidoria_id INTEGER NOT NULL REFERENCES ouvidorias(id),
            tecnico_id INTEGER NOT NULL REFERENCES usuarios(id),
            numero_sei_resposta VARCHAR(100),
            data_resposta DATE NOT NULL,
            texto_resposta TEXT NOT NULL,
            criado_em TIMESTAMP NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE TABLE paradas_auto_linha (
            id SERIAL PRIMARY KEY,
            auto_id INTEGER NOT NULL REFERENCES autos_linha(id),
            cidade VARCHAR(200) NOT NULL
        )
    """)
    op.execute("CREATE INDEX ix_paradas_auto_linha_cidade ON paradas_auto_linha (cidade)")
    op.execute("""
        CREATE TABLE ouvidoria_tecnicos (
            ouvidoria_id INTEGER NOT NULL REFERENCES ouvidorias(id),
            tecnico_id INTEGER NOT NULL REFERENCES usuarios(id),
            respondido BOOLEAN NOT NULL DEFAULT FALSE,
            respondido_em TIMESTAMP,
            PRIMARY KEY (ouvidoria_id, tecnico_id)
        )
    """)
    op.execute("""
        CREATE TABLE reclamacao_autos (
            reclamacao_id INTEGER NOT NULL REFERENCES reclamacoes(id),
            auto_id INTEGER NOT NULL REFERENCES autos_linha(id),
            pontuacao NUMERIC(10, 4) NOT NULL,
            PRIMARY KEY (reclamacao_id, auto_id)
        )
    """)


def downgrade() -> None:
    """Remove todas as tabelas do schema inicial."""
    op.drop_table("reclamacao_autos")
    op.drop_table("ouvidoria_tecnicos")
    op.drop_index("ix_paradas_auto_linha_cidade", table_name="paradas_auto_linha")
    op.drop_table("paradas_auto_linha")
    op.drop_table("respostas_tecnicas")
    op.drop_table("reclamacoes")
    op.drop_table("ouvidorias")
    op.drop_table("usuarios")
    op.drop_table("autos_linha")
    op.drop_table("coordenacoes")
    op.drop_table("categorias")
    op.drop_table("gerencias")
    op.drop_table("permissionarias")
    sa.Enum(name="statusouvidoria").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="tipousuario").drop(op.get_bind(), checkfirst=True)
    op.execute("DROP SCHEMA IF EXISTS ouvidoria")
