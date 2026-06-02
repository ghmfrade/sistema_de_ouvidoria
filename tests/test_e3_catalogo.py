"""Etapa 3 — paridade entre endpoints de catálogo/autos e repositórios atuais."""
import pytest
from api.repositories.catalog_repo import (
    get_categorias, get_subcategorias, get_gerencias,
    get_coordenacoes, get_tecnicos_ativos, get_todas_permissionarias,
)
from api.repositories.municipios_repo import get_municipios_sp, get_municipios_com_linhas
from api.repositories.autos_repo import get_todos_autos, get_permissionarias

TIPO_SERVICO = "Regular – Metropolitano"


# ── Catálogo ──────────────────────────────────────────────────────────────────

def test_paridade_categorias(client, headers_gestor):
    esperado = get_categorias()
    r = client.get("/catalogo/categorias", headers=headers_gestor)
    assert r.status_code == 200
    obtido = r.json()
    assert len(obtido) == len(esperado)
    assert {c["id"] for c in esperado} == {c["id"] for c in obtido}


def test_paridade_subcategorias(client, headers_gestor):
    cats = get_categorias()
    if not cats:
        pytest.skip("Sem categorias no banco")
    cat_id = cats[0]["id"]
    esperado = get_subcategorias(cat_id)
    r = client.get(f"/catalogo/categorias/{cat_id}/subcategorias", headers=headers_gestor)
    assert r.status_code == 200
    assert {s["id"] for s in esperado} == {s["id"] for s in r.json()}


def test_paridade_gerencias(client, headers_gestor):
    esperado = get_gerencias()
    r = client.get("/catalogo/gerencias", headers=headers_gestor)
    assert r.status_code == 200
    assert {g["id"] for g in esperado} == {g["id"] for g in r.json()}


def test_paridade_coordenacoes(client, headers_gestor):
    esperado = get_coordenacoes()
    r = client.get("/catalogo/coordenacoes", headers=headers_gestor)
    assert r.status_code == 200
    assert {c["id"] for c in esperado} == {c["id"] for c in r.json()}


def test_paridade_coordenacoes_filtradas(client, headers_gestor):
    gers = get_gerencias()
    if not gers:
        pytest.skip("Sem gerências no banco")
    ger_id = gers[0]["id"]
    esperado = get_coordenacoes(ger_id)
    r = client.get("/catalogo/coordenacoes", headers=headers_gestor,
                   params={"gerencia_id": ger_id})
    assert r.status_code == 200
    assert {c["id"] for c in esperado} == {c["id"] for c in r.json()}


def test_paridade_tecnicos(client, headers_gestor):
    esperado = get_tecnicos_ativos()
    r = client.get("/catalogo/tecnicos", headers=headers_gestor)
    assert r.status_code == 200
    # Os usuários de teste criados pelo conftest aparecem no banco;
    # verificamos apenas que os técnicos reais (anteriores) estão presentes
    ids_obtidos = {t["id"] for t in r.json()}
    for t in esperado:
        assert t["id"] in ids_obtidos


def test_paridade_permissionarias(client, headers_gestor):
    esperado = get_permissionarias(TIPO_SERVICO)
    r = client.get("/catalogo/permissionarias", headers=headers_gestor,
                   params={"tipo_servico": TIPO_SERVICO})
    assert r.status_code == 200
    assert {p["id"] for p in esperado} == {p["id"] for p in r.json()}


def test_paridade_municipios(client, headers_gestor):
    esperado = get_municipios_sp()
    r = client.get("/catalogo/municipios", headers=headers_gestor)
    assert r.status_code == 200
    assert len(r.json()) == len(esperado)


def test_paridade_municipios_com_linhas(client, headers_gestor):
    esperado = get_municipios_com_linhas(TIPO_SERVICO)
    r = client.get("/catalogo/municipios/com-linhas", headers=headers_gestor,
                   params={"tipo_servico": TIPO_SERVICO})
    assert r.status_code == 200
    assert {m["id"] for m in esperado} == {m["id"] for m in r.json()}


def test_regioes_metropolitanas(client, headers_gestor):
    r = client.get("/catalogo/regioes-metropolitanas", headers=headers_gestor)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ── Autos ─────────────────────────────────────────────────────────────────────

def test_paridade_autos(client, headers_gestor):
    esperado = get_todos_autos(TIPO_SERVICO)
    r = client.get("/autos", headers=headers_gestor,
                   params={"tipo_servico": TIPO_SERVICO})
    assert r.status_code == 200
    assert len(r.json()) == len(esperado)


def test_autos_por_trecho(client, headers_gestor):
    r = client.get("/autos/por-trecho", headers=headers_gestor, params={
        "tipo_servico": TIPO_SERVICO,
        "cidade_a": "São Paulo",
        "cidade_b": "Campinas",
    })
    assert r.status_code == 200
    assert isinstance(r.json(), list)
