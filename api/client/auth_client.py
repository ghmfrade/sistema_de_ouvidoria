"""Client de autenticação — não usa token (é quem gera o token)."""
import httpx

from api.client.base import API_BASE, _TIMEOUT, _raise_if_error_public, post_public


def login(email: str, senha: str) -> dict:
    """Autentica e retorna dict com token + dados do usuário.

    Retorna: {"token", "expira_em", "usuario_id", "nome", "tipo", "gerencia_id",
              "gerencia_nome", "coordenacao_id", "coordenacao_nome"}
    """
    return post_public("/auth/login", json={"email": email, "senha": senha})


def renovar(token: str) -> dict:
    """Troca um token ainda válido por um novo. Mesmo retorno de login().

    Não passa por _raise_if_error: um 401 aqui deve virar ApiError para o
    caller decidir, e não um st.rerun() no meio da renovação.
    """
    r = httpx.post(
        f"{API_BASE}/auth/refresh",
        headers={"Authorization": f"Bearer {token}"},
        timeout=_TIMEOUT,
    )
    _raise_if_error_public(r)
    return r.json()
