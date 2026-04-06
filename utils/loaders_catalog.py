"""Loaders de dados de catálogo: municípios, categorias, subcategorias, gerências, coordenações."""

import streamlit as st

from repositories.catalog_repo import (
    get_categorias,
    get_coordenacoes,
    get_gerencias,
    get_subcategorias,
    get_todas_permissionarias,
)
from repositories.municipios_repo import get_municipios_sp


@st.cache_data(ttl=300)
def carregar_municipios():
    """Lista de nomes de municípios de SP ordenados."""
    return [m["nome"] for m in get_municipios_sp()]


def carregar_categorias():
    """Categorias ativas para selectbox: [(id, nome)]."""
    return [(c["id"], c["nome"]) for c in get_categorias() if c["ativo"]]


def carregar_subcategorias(categoria_id: int):
    """Subcategorias ativas de uma categoria para selectbox: [(id, nome)]."""
    return [(sc["id"], sc["nome"]) for sc in get_subcategorias(categoria_id) if sc["ativo"]]


def carregar_todas_gerencias():
    """Todas as gerências para selectbox: [(id, nome)]."""
    return [(g["id"], g["nome"]) for g in get_gerencias()]


def carregar_gerencias_ativas():
    """Gerências ativas para selectbox: [(id, nome)]."""
    return [(g["id"], g["nome"]) for g in get_gerencias() if g["ativo"]]


def carregar_coordenacoes(gerencia_id=None):
    """Coordenações para selectbox, opcionalmente filtradas por gerência: [(id, nome)]."""
    return [(c["id"], c["nome"]) for c in get_coordenacoes(gerencia_id)]


def carregar_todas_permissionarias():
    """Todas as permissionárias para selectbox: [(id, nome)]."""
    return [(p["id"], p["nome"]) for p in get_todas_permissionarias()]
