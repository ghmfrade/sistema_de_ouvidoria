"""
Seed para criar usuários padrão (admin).

Uso:
    python database/seed_usuarios.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import bcrypt

from api.database.connection import db_session
from api.models import Usuario, TipoUsuario, Gerencia


def _hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()


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
            senha_hash=_hash_senha(senha),
            tipo=TipoUsuario.gestor,
            ativo=True,
        )
        session.add(usuario)

    print(f"  Usuario gestor criado: {email}")


def criar_dados_legados():
    """Cria (ou verifica) o usuário técnico 'Dados Legados' para dados históricos."""
    with db_session() as session:
        existente = session.query(Usuario).filter(
            Usuario.nome.ilike("Dados Legados")
        ).first()
        if existente:
            print(f"  Usuario 'Dados Legados' ja existe (id={existente.id}).")
            return

        gplan = session.query(Gerencia).filter(
            Gerencia.nome.ilike("GPLAN")
        ).first()
        if gplan is None:
            raise RuntimeError("Gerência 'GPLAN' não encontrada — execute seed de gerências primeiro.")

        usuario = Usuario(
            nome="Dados Legados",
            email="dados_legados",
            senha_hash=_hash_senha("senha_legados@26"),
            tipo=TipoUsuario.tecnico,
            gerencia_id=gplan.id,
            coordenacao_id=None,
            ativo=True,
        )
        session.add(usuario)

    print("  Usuario tecnico 'Dados Legados' criado.")


if __name__ == "__main__":
    print("Criando usuarios padrao...")
    criar_admin()
    criar_dados_legados()
    print("Concluido.")
