"""Loaders de dados de catalogo: municipios, categorias, subcategorias, gerencias ativas."""

import streamlit as st

from database.connection import get_session
from models import Categoria, Gerencia, Municipio, Subcategoria


@st.cache_data(ttl=300)
def carregar_municipios():
    """Retorna lista de municipios de SP ordenados por nome."""
    session = get_session()
    try:
        munis = session.query(Municipio).filter_by(estado="SP").order_by(Municipio.nome).all()
        return [m.nome for m in munis]
    finally:
        session.close()


def carregar_categorias():
    """Retorna categorias ativas: [(id, nome)]."""
    session = get_session()
    try:
        cats = session.query(Categoria).filter_by(ativo=True).order_by(Categoria.nome).all()
        return [(c.id, c.nome) for c in cats]
    finally:
        session.close()


def carregar_subcategorias(categoria_id: int):
    """Retorna subcategorias ativas de uma categoria: [(id, nome)]."""
    session = get_session()
    try:
        subcats = (
            session.query(Subcategoria)
            .filter_by(categoria_id=categoria_id, ativo=True)
            .order_by(Subcategoria.nome)
            .all()
        )
        return [(sc.id, sc.nome) for sc in subcats]
    finally:
        session.close()


def carregar_gerencias_ativas():
    """Retorna gerencias ativas: [(id, nome)]."""
    s = get_session()
    try:
        return [(g.id, g.nome) for g in s.query(Gerencia).filter_by(ativo=True).order_by(Gerencia.nome).all()]
    finally:
        s.close()
