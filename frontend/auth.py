"""Autenticação via API FastAPI — sem acesso direto ao banco.

A sessão vive em st.session_state, que some com F5, nova aba ou restart do pod.
Para sobreviver a isso, o token também fica no cookie `souvi_token` e é trocado
por um token novo (/auth/refresh) quando a sessão do Streamlit começa vazia.

O cookie não é HttpOnly: o Streamlit não deixa a app definir cabeçalhos de
resposta, então ele é gravado via JS. Aceitável aqui porque o token expira por
inatividade e a API impõe um teto de horas desde o login.
"""
import json

import streamlit as st
import streamlit.components.v1 as components
from api.client.auth_client import login as _api_login, renovar as _api_renovar
from api.client.base import ApiError

_COOKIE = "souvi_token"
_COOKIE_MAX_AGE_S = 8 * 60 * 60  # o teto real é imposto pela API (JWT_MAX_SESSION_HOURS)


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


def _restaurar_do_cookie() -> None:
    """Recupera a sessão a partir do cookie, uma vez por sessão do Streamlit.

    `st.context.cookies` reflete o carregamento da página, então após um logout
    o cookie antigo ainda aparece aqui — por isso a flag `_cookie_testado`.
    """
    if st.session_state.get("_cookie_testado"):
        return
    st.session_state["_cookie_testado"] = True
    token = st.context.cookies.get(_COOKIE)
    if not token:
        return
    try:
        st.session_state["api_session"] = _api_renovar(token)
    except Exception:
        st.session_state["_limpar_cookie"] = True


def _sincronizar_cookie() -> None:
    """Grava ou apaga o cookie quando o token da sessão muda."""
    if st.session_state.pop("_limpar_cookie", False):
        st.session_state.pop("_token_cookie", None)
        valor, max_age = "", 0
    else:
        sess = st.session_state.get("api_session")
        token = sess.get("token") if sess else None
        if not token or token == st.session_state.get("_token_cookie"):
            return
        st.session_state["_token_cookie"] = token
        valor, max_age = token, _COOKIE_MAX_AGE_S

    # O iframe do componente tem allow-same-origin, então alcança o cookie da página.
    script = f"""<script>
    const doc = window.parent.document;
    const seguro = window.parent.location.protocol === "https:" ? "; Secure" : "";
    doc.cookie = {json.dumps(_COOKIE)} + "=" + {json.dumps(valor)}
        + "; Max-Age={max_age}; Path=/; SameSite=Strict" + seguro;
    </script>"""
    with st.sidebar:
        components.html(script, height=0)


def usuario_logado() -> dict | None:
    """Retorna os dados do usuário logado (dict) ou None."""
    if not st.session_state.get("api_session"):
        _restaurar_do_cookie()
    _sincronizar_cookie()
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
    st.session_state["_limpar_cookie"] = True
