"""Smoke tests para endpoints de dashboard de produtividade.

Verifica que cada endpoint:
  1. Retorna HTTP 200
  2. Serializa JSON sem erros (Decimal, datetime, tipos não-serializáveis)
  3. Retorna o tipo esperado (list ou dict)

Não verifica paridade de dados — apenas que o endpoint não explode.
Técnico não tem acesso a dashboards (403 esperado).

Os endpoints de qualidade (v2) são cobertos por test_qualidade_v2.py.
"""
from datetime import date, timedelta

import pytest

DATA_INI = (date.today() - timedelta(days=365)).isoformat()
DATA_FIM = date.today().isoformat()
_BASE = {"data_ini": DATA_INI, "data_fim": DATA_FIM}


# (path, params_extras, tipo_esperado)
ENDPOINTS_PRODUTIVIDADE = [
    ("/dashboard/produtividade/kpis",                    {},                    dict),
    ("/dashboard/produtividade/tempo-medio",             {},                    dict),
    ("/dashboard/produtividade/volume-por-mes",          {},                    list),
    ("/dashboard/produtividade/distribuicao-status",     {},                    list),
    ("/dashboard/produtividade/vencidas-por-coordenacao",{},                    list),
    ("/dashboard/produtividade/tempo-medio-por-tecnico", {},                    list),
    ("/dashboard/produtividade/ranking-coordenacoes",    {},                    list),
]

ALL_ENDPOINTS = ENDPOINTS_PRODUTIVIDADE


@pytest.mark.parametrize(
    "path,extras,tipo",
    ALL_ENDPOINTS,
    ids=[e[0].split("/")[-1] for e in ALL_ENDPOINTS],
)
def test_dashboard_retorna_200_e_json_valido(client, headers_gestor, path, extras, tipo):
    """Endpoint responde 200 e devolve JSON serializável do tipo correto."""
    r = client.get(path, headers=headers_gestor, params={**_BASE, **extras})
    assert r.status_code == 200, f"{path} → HTTP {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert isinstance(data, tipo), (
        f"{path} esperava {tipo.__name__}, recebeu {type(data).__name__}"
    )


@pytest.mark.parametrize(
    "path",
    [e[0] for e in ALL_ENDPOINTS],
    ids=[e[0].split("/")[-1] for e in ALL_ENDPOINTS],
)
def test_dashboard_bloqueia_tecnico(client, headers_tecnico, path):
    """Técnico não tem acesso a nenhum endpoint de dashboard (403)."""
    r = client.get(path, headers=headers_tecnico, params=_BASE)
    assert r.status_code == 403, f"{path} deveria retornar 403 para técnico, retornou {r.status_code}"
