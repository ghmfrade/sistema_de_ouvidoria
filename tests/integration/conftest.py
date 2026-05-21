"""Fixtures para testes de integração contra o servidor real.

Variáveis de ambiente necessárias no .env:
    TEST_SERVER_URL      URL base da API no servidor (ex: http://10.23.42.237:8000)
    TEST_SERVER_EMAIL    Email de um usuário gestor ativo no servidor
    TEST_SERVER_PASSWORD Senha desse usuário

Se TEST_SERVER_URL não estiver configurada, todos os testes são pulados.
Se as credenciais não estiverem configuradas, testes que precisam de token são pulados.
"""
import os
import pytest
import requests
from dotenv import load_dotenv

load_dotenv()

_TIMEOUT = 10

_SERVER_URL = os.getenv("TEST_SERVER_URL", "").rstrip("/")
_EMAIL      = os.getenv("TEST_SERVER_EMAIL", "")
_PASSWORD   = os.getenv("TEST_SERVER_PASSWORD", "")


@pytest.fixture(scope="session")
def base_url():
    if not _SERVER_URL:
        pytest.skip("TEST_SERVER_URL não configurada no .env")
    return _SERVER_URL


@pytest.fixture(scope="session")
def http(base_url):
    """requests.Session sem headers — para endpoints públicos ou testes de 401."""
    s = requests.Session()
    s.request = lambda method, url, **kw: requests.Session.request(
        s, method, url, timeout=kw.pop("timeout", _TIMEOUT), **kw
    )
    yield s


@pytest.fixture(scope="session")
def gestor_headers(base_url):
    if not _EMAIL or not _PASSWORD:
        pytest.skip("TEST_SERVER_EMAIL / TEST_SERVER_PASSWORD não configuradas no .env")
    r = requests.post(
        f"{base_url}/auth/login",
        json={"email": _EMAIL, "senha": _PASSWORD},
        timeout=_TIMEOUT,
    )
    if r.status_code != 200:
        pytest.skip(f"Login falhou ({r.status_code}): {r.text[:200]}")
    token = r.json()["token"]
    return {"Authorization": f"Bearer {token}"}
