"""Smoke tests de integração — requisições HTTP reais ao servidor.

Verifica que cada endpoint:
  1. Está acessível (sem timeout / connection error)
  2. Retorna o HTTP status esperado
  3. Resposta é JSON válido

Não valida conteúdo — apenas que o servidor está respondendo corretamente.

Execução:
    pytest tests/integration/ -v
"""
from datetime import date, timedelta

import pytest

_DATA_INI = (date.today() - timedelta(days=365)).isoformat()
_DATA_FIM  = date.today().isoformat()
_BASE_PERIODO = {"data_ini": _DATA_INI, "data_fim": _DATA_FIM}

_TIMEOUT = 10


# ── Auth ──────────────────────────────────────────────────────────────────────

def test_login_retorna_token(base_url, gestor_headers):
    """Login com credenciais válidas retorna token."""
    import os, requests
    from dotenv import load_dotenv
    load_dotenv()
    r = requests.post(
        f"{base_url}/auth/login",
        json={"email": os.getenv("TEST_SERVER_EMAIL"), "senha": os.getenv("TEST_SERVER_PASSWORD")},
        timeout=_TIMEOUT,
    )
    assert r.status_code == 200, f"Login → {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert "token" in data
    assert isinstance(data["token"], str)
    assert len(data["token"]) > 10


def test_auth_me(base_url, http, gestor_headers):
    """GET /auth/me retorna dados do usuário logado."""
    r = http.get(f"{base_url}/auth/me", headers=gestor_headers)
    assert r.status_code == 200, f"/auth/me → {r.status_code}: {r.text[:200]}"
    assert isinstance(r.json(), dict)


# ── Catálogo ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("path,params", [
    ("/catalogo/categorias",    {}),
    ("/catalogo/gerencias",     {}),
    ("/catalogo/tecnicos",      {}),
    ("/catalogo/permissionarias", {"tipo_servico": "Regular – Intermunicipal"}),
])
def test_catalogo(base_url, http, gestor_headers, path, params):
    r = http.get(f"{base_url}{path}", headers=gestor_headers, params=params)
    assert r.status_code == 200, f"{path} → {r.status_code}: {r.text[:200]}"
    assert isinstance(r.json(), list)


# ── Ouvidorias ────────────────────────────────────────────────────────────────

def test_listar_ouvidorias(base_url, http, gestor_headers):
    r = http.get(f"{base_url}/ouvidorias", headers=gestor_headers)
    assert r.status_code == 200, f"/ouvidorias → {r.status_code}: {r.text[:200]}"
    assert isinstance(r.json(), list)


# ── Dashboard Produtividade ───────────────────────────────────────────────────

@pytest.mark.parametrize("path", [
    "/dashboard/produtividade/kpis",
    "/dashboard/produtividade/volume-por-mes",
    "/dashboard/produtividade/distribuicao-status",
    "/dashboard/produtividade/ranking-coordenacoes",
])
def test_dashboard_produtividade(base_url, http, gestor_headers, path):
    r = http.get(f"{base_url}{path}", headers=gestor_headers, params=_BASE_PERIODO)
    assert r.status_code == 200, f"{path} → {r.status_code}: {r.text[:200]}"
    assert r.json() is not None


# ── Dashboard Qualidade v2 (público) ─────────────────────────────────────────

def test_qualidade_anos_disponiveis(base_url, http):
    r = http.get(f"{base_url}/dashboard/qualidade-v2/anos-disponiveis")
    assert r.status_code == 200, f"anos-disponiveis → {r.status_code}: {r.text[:200]}"
    assert isinstance(r.json(), list)


@pytest.mark.parametrize("path", [
    "/dashboard/qualidade-v2/resumo",
    "/dashboard/qualidade-v2/evolucao-mensal",
    "/dashboard/qualidade-v2/assuntos-pizza",
    "/dashboard/qualidade-v2/empresas-pontuacao",
    "/dashboard/qualidade-v2/empresas-irregular",
])
def test_qualidade_com_ano(base_url, http, path):
    anos = http.get(f"{base_url}/dashboard/qualidade-v2/anos-disponiveis").json()
    if not anos:
        pytest.skip("Sem dados de qualidade no servidor")
    r = http.get(f"{base_url}{path}", params={"ano": anos[-1]})
    assert r.status_code == 200, f"{path} → {r.status_code}: {r.text[:200]}"
    assert r.json() is not None


# ── Proteção de rotas ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("path", [
    "/catalogo/categorias",
    "/ouvidorias",
    "/dashboard/produtividade/kpis",
])
def test_token_invalido_retorna_401(base_url, http, path):
    """Endpoints protegidos devem retornar 401 com token inválido."""
    params = _BASE_PERIODO if "produtividade" in path else {}
    r = http.get(f"{base_url}{path}", headers={"Authorization": "Bearer token_invalido"}, params=params)
    assert r.status_code == 401, f"{path} com token inválido → esperava 401, recebeu {r.status_code}"
