"""Substitui utils/loaders_catalog.py — consome a API via HTTP."""
import streamlit as st
from api.client.base import get


@st.cache_data(ttl=300)
def carregar_municipios() -> list[str]:
    return [m["nome"] for m in get("/catalogo/municipios")]


def carregar_categorias() -> list[tuple[int, str]]:
    return [(c["id"], c["nome"]) for c in get("/catalogo/categorias") if c["ativo"]]


def carregar_subcategorias(categoria_id: int) -> list[tuple[int, str]]:
    data = get(f"/catalogo/categorias/{categoria_id}/subcategorias")
    return [(s["id"], s["nome"]) for s in data if s["ativo"]]


def carregar_todas_gerencias() -> list[tuple[int, str]]:
    return [(g["id"], g["nome"]) for g in get("/catalogo/gerencias")]


def carregar_gerencias_ativas() -> list[tuple[int, str]]:
    return [(g["id"], g["nome"]) for g in get("/catalogo/gerencias") if g["ativo"]]


def carregar_coordenacoes(gerencia_id: int | None = None) -> list[tuple[int, str]]:
    params = {"gerencia_id": gerencia_id} if gerencia_id else None
    return [(c["id"], c["nome"]) for c in get("/catalogo/coordenacoes", params=params)]


@st.cache_data(ttl=300)
def carregar_regioes_metropolitanas() -> list[str]:
    return get("/catalogo/regioes-metropolitanas")


def carregar_tecnicos_disponiveis() -> list[tuple[int, str]]:
    return [(t["id"], t["nome"]) for t in get("/catalogo/tecnicos")]
