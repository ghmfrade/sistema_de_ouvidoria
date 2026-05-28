"""Cliente HTTP base para chamadas à API FastAPI.

Uso nas pages Streamlit:
    from api.client.base import get, post, patch, delete, ApiError
"""
import os
from typing import Any

import httpx
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_BASE = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")
API_PUBLIC_URL = os.environ.get("API_PUBLIC_URL", API_BASE)
_TIMEOUT = 20.0


class ApiError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"API {status_code}: {detail}")


def _token() -> str:
    sess = st.session_state.get("api_session")
    if not sess or "token" not in sess:
        st.session_state.pop("api_session", None)
        st.rerun()
    return sess["token"]


def _headers() -> dict:
    return {"Authorization": f"Bearer {_token()}"}


def _raise_if_error(r: httpx.Response) -> None:
    if not r.is_success:
        if r.status_code == 401:
            # Token expirado ou inválido — limpa sessão e volta para o login
            st.session_state.pop("api_session", None)
            st.rerun()
        try:
            detail = r.json().get("detail", r.text)
        except Exception:
            detail = r.text
        raise ApiError(r.status_code, detail)


def _raise_if_error_public(r: httpx.Response) -> None:
    """Versão de _raise_if_error para endpoints públicos (sem token).

    Não faz st.rerun() em 401, pois credenciais inválidas devem retornar
    uma exceção com mensagem para o caller tratar (ex: login inválido).
    """
    if not r.is_success:
        try:
            detail = r.json().get("detail", r.text)
        except Exception:
            detail = r.text
        raise ApiError(r.status_code, detail)


def post_public(path: str, json: dict | None = None) -> Any:
    """POST sem token — usado apenas para endpoints públicos como /auth/login."""
    r = httpx.post(f"{API_BASE}{path}", json=json, timeout=_TIMEOUT)
    _raise_if_error_public(r)
    return r.json()


def get(path: str, params: dict | None = None) -> Any:
    r = httpx.get(f"{API_BASE}{path}", headers=_headers(), params=params, timeout=_TIMEOUT)
    _raise_if_error(r)
    return r.json()


def post(path: str, json: dict | None = None, **kwargs) -> Any:
    r = httpx.post(f"{API_BASE}{path}", headers=_headers(), json=json, timeout=_TIMEOUT, **kwargs)
    _raise_if_error(r)
    return r.json()


def patch(path: str, json: dict | None = None) -> Any:
    r = httpx.patch(f"{API_BASE}{path}", headers=_headers(), json=json, timeout=_TIMEOUT)
    _raise_if_error(r)
    return r.json()


def delete(path: str) -> Any:
    r = httpx.delete(f"{API_BASE}{path}", headers=_headers(), timeout=_TIMEOUT)
    _raise_if_error(r)
    return r.json()


def post_file(path: str, file_bytes: bytes, filename: str, content_type: str) -> Any:
    r = httpx.post(
        f"{API_BASE}{path}",
        headers=_headers(),
        files={"arquivo": (filename, file_bytes, content_type)},
        timeout=60.0,
    )
    _raise_if_error(r)
    return r.json()
