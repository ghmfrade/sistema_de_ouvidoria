"""Autenticação via API FastAPI — sem acesso direto ao banco."""
import streamlit as st
from api.client.auth_client import login as _api_login
from api.client.base import ApiError


def autenticar(email: str, senha: str) -> tuple[dict | None, str | None]:
    """Autentica via API. Retorna (dict com dados do usuário, erro) ou (None, mensagem de erro).

    Retorna:
        (dict, None) se autenticado com sucesso
        (None, mensagem de erro) se falhar
    """
    try:
        return _api_login(email, senha), None
    except ApiError as e:
        return None, e.detail


def usuario_logado() -> dict | None:
    """Retorna os dados do usuário logado (dict) ou None."""
    return st.session_state.get("api_session")


def require_auth():
    """Para a execução da página se o usuário não estiver logado."""
    if not usuario_logado():
        st.error("Você precisa estar logado para acessar esta página.")
        st.stop()


def require_gestor():
    """Para a execução se o usuário não for gestor."""
    require_auth()
    u = usuario_logado()
    if u and u.get("tipo") != "gestor":
        st.error("Acesso restrito a gestores.")
        st.stop()


def fazer_logout():
    st.session_state.pop("api_session", None)


def hash_senha(senha: str) -> str:
    """Mantido para compatibilidade com scripts de seed."""
    import bcrypt
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
