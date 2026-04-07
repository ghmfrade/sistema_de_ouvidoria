"""
Seed para criar usuários padrão (admin).

Uso:
    python database/seed_usuarios.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import db_session
from models import Usuario, TipoUsuario
import auth


def criar_admin():
    """Cria usuário gestor admin padrão."""
    email = "admin@artesp.sp.gov.br"
    senha = "admin123"

    with db_session() as session:
        existe = session.query(Usuario).filter_by(email=email).first()
        if existe:
            print(f"  Usuario {email} ja existe — nenhuma acao necessaria.")
            return

        usuario = Usuario(
            nome="Administrador",
            email=email,
            senha_hash=auth.hash_senha(senha),
            tipo=TipoUsuario.gestor,
            ativo=True,
        )
        session.add(usuario)

    print(f"  Usuario gestor criado: {email}")


if __name__ == "__main__":
    print("Criando usuarios padrao...")
    criar_admin()
    print("Concluido.")
