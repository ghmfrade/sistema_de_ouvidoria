"""remove constraint unique de email na tabela usuarios

Revision ID: a2b3c4d5e6f7
Revises: f6a4d3e2c1b0
Create Date: 2026-05-27

Permite criar múltiplos usuários com o mesmo e-mail, desde que apenas
um deles esteja ativo por vez. A unicidade é garantida em camada de
aplicação (rota POST /admin/usuarios e PATCH .../toggle).
"""

revision = "a2b3c4d5e6f7"
down_revision = "f6a4d3e2c1b0"
branch_labels = None
depends_on = None

from alembic import op


def upgrade() -> None:
    op.execute(
        "ALTER TABLE usuarios DROP CONSTRAINT IF EXISTS usuarios_email_key"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE usuarios ADD CONSTRAINT usuarios_email_key UNIQUE (email)"
    )
