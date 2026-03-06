"""Utilitários de autenticação: hash de senha e controle de sessão Streamlit."""
import bcrypt
import streamlit as st
from database.connection import get_session
from models import Usuario, TipoUsuario


def hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()


def verificar_senha(senha: str, senha_hash: str) -> bool:
    return bcrypt.checkpw(senha.encode(), senha_hash.encode())


def autenticar(email: str, senha: str) -> Usuario | None:
    """Retorna o Usuario se credenciais válidas, None caso contrário."""
    session = get_session()
    try:
        usuario = session.query(Usuario).filter_by(email=email.strip(), ativo=True).first()
        if usuario and verificar_senha(senha, usuario.senha_hash):
            # Carrega relacionamentos necessários enquanto a sessão está aberta
            _ = usuario.gerencia
            _ = usuario.coordenacao
            session.expunge(usuario)
            return usuario
        return None
    finally:
        session.close()


def usuario_logado() -> Usuario | None:
    """Retorna o usuário da sessão ou None."""
    return st.session_state.get("usuario")


def require_auth():
    """Para a execução da página se o usuário não estiver logado."""
    if not usuario_logado():
        st.error("Você precisa estar logado para acessar esta página.")
        st.stop()


def require_gestor():
    """Para a execução se o usuário não for gestor."""
    require_auth()
    u = usuario_logado()
    if u and u.tipo != TipoUsuario.gestor:
        st.error("Acesso restrito a gestores.")
        st.stop()


def fazer_logout():
    st.session_state.pop("usuario", None)
