"""Substitui utils/loaders_auto.py — consome a API via HTTP."""
import streamlit as st
from api.client.base import get


@st.cache_data(ttl=300)
def carregar_cidades_atendidas(
    tipo_servico: str,
    perm_id: int | None = None,
    regiao: str | None = None,
) -> list[str]:
    params = {"tipo_servico": tipo_servico}
    if perm_id:
        params["perm_id"] = perm_id
    if regiao:
        params["regiao"] = regiao
    data = get("/catalogo/municipios/com-linhas", params=params)
    return sorted({m["nome"] for m in data})


@st.cache_data(ttl=300)
def carregar_cidades_destino(
    tipo_servico: str,
    nome_origem: str,
    perm_id: int | None = None,
    regiao: str | None = None,
) -> list[str]:
    params = {"tipo_servico": tipo_servico, "nome_origem": nome_origem}
    if perm_id:
        params["perm_id"] = perm_id
    if regiao:
        params["regiao"] = regiao
    data = get("/catalogo/municipios/destinos", params=params)
    return sorted({m["nome"] for m in data})


@st.cache_data(ttl=300)
def carregar_todos_autos(
    tipo_servico: str,
    perm_id: int | None = None,
    regiao: str | None = None,
) -> list[dict]:
    params = {"tipo_servico": tipo_servico}
    if perm_id:
        params["perm_id"] = perm_id
    if regiao:
        params["regiao"] = regiao
    return get("/autos", params=params)


@st.cache_data(ttl=300)
def carregar_permissionarias(
    tipo_servico: str,
    regiao: str | None = None,
) -> list[dict]:
    params = {"tipo_servico": tipo_servico}
    if regiao:
        params["regiao"] = regiao
    return get("/catalogo/permissionarias", params=params)


def buscar_autos_por_trecho(
    tipo_servico: str,
    cidade_a: str,
    cidade_b: str,
    perm_id: int | None = None,
    regiao: str | None = None,
) -> list[dict]:
    params = {"tipo_servico": tipo_servico, "cidade_a": cidade_a, "cidade_b": cidade_b}
    if perm_id:
        params["perm_id"] = perm_id
    if regiao:
        params["regiao"] = regiao
    return get("/autos/por-trecho", params=params)
