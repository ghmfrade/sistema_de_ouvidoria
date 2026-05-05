"""Loaders de autos de linha, cidades, permissionárias e regiões metropolitanas."""

import streamlit as st

from repositories.autos_repo import (
    buscar_autos_por_trecho as _buscar_autos_por_trecho,
    get_autos_regioes_metropolitanas,
    get_municipios_destino,
    get_permissionarias,
    get_todos_autos,
)
from repositories.municipios_repo import (
    get_municipios_com_linhas,
    get_municipios_sp,
)
from repositories.types import AutoDict, MunicipioDict, PermissionariaDict


@st.cache_data(ttl=300)
def carregar_cidades_por_tipo(tipo_servico: str) -> list[str]:
    """Cidades de origem filtradas pelo tipo de serviço, ordenadas."""
    if "Fretamento" in tipo_servico:
        return [m["nome"] for m in get_municipios_sp()]
    return sorted([m["nome"] for m in get_municipios_com_linhas(tipo_servico) if m["nome"]])


@st.cache_data(ttl=300)
def carregar_cidades(tipo_servico: str, perm_id: int | None = None, regiao: str | None = None) -> list[str]:
    """Cidades para busca por trecho, ordenadas."""
    return sorted([m["nome"] for m in get_municipios_com_linhas(tipo_servico, perm_id, regiao) if m["nome"]])


def carregar_cidades_destino(tipo_servico: str, nome_origem: str,
                              perm_id: int | None = None, regiao: str | None = None) -> list[str]:
    """Cidades alcançáveis a partir da origem, ordenadas."""
    if "Fretamento" in tipo_servico:
        return [m["nome"] for m in get_municipios_sp() if m["nome"] != nome_origem]
    return sorted([m["nome"] for m in get_municipios_destino(tipo_servico, nome_origem, perm_id, regiao) if m["nome"]])


@st.cache_data(ttl=300)
def carregar_todos_autos(tipo_servico: str, perm_id: int | None = None, regiao: str | None = None) -> list[AutoDict]:
    """Todos os autos filtrados como AutoDict."""
    return get_todos_autos(tipo_servico, perm_id, regiao)


@st.cache_data(ttl=300)
def carregar_permissionarias(tipo_servico: str, regiao: str | None = None) -> list[PermissionariaDict]:
    """Permissionárias com autos do tipo informado."""
    return get_permissionarias(tipo_servico, regiao)


@st.cache_data(ttl=300)
def carregar_regioes_metropolitanas() -> list[str]:
    """Regiões metropolitanas distintas, ordenadas e limpas."""
    return sorted({r.strip() for r in get_autos_regioes_metropolitanas() if r})


def buscar_autos_por_trecho(tipo_servico: str, cidade_a: str, cidade_b: str,
                             perm_id: int | None = None, regiao: str | None = None) -> list[AutoDict]:
    """Autos que possuem paradas em AMBAS as cidades."""
    return _buscar_autos_por_trecho(tipo_servico, cidade_a, cidade_b, perm_id, regiao)
