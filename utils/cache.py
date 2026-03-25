"""Funções de cache compartilhadas entre páginas.

Centralizar aqui garante que a invalidação via .clear() funcione
corretamente, pois o Streamlit vincula o cache ao objeto função.
Cada página importa daqui em vez de definir cópias locais.
"""

import streamlit as st

from database.connection import get_session
from models import (
    AutoLinha,
    Categoria,
    Coordenacao,
    Gerencia,
    Municipio,
    ParadaAutoLinha,
    Permissionaria,
    Subcategoria,
    TipoServico,
    TipoUsuario,
    Usuario,
)


@st.cache_data(ttl=300)
def carregar_categorias():
    """Retorna [(id, nome)] de categorias ativas, ordenadas por nome."""
    s = get_session()
    try:
        cats = s.query(Categoria).filter_by(ativo=True).order_by(Categoria.nome).all()
        return [(c.id, c.nome) for c in cats]
    finally:
        s.close()


@st.cache_data(ttl=300)
def carregar_subcategorias(categoria_id: int):
    """Retorna [(id, nome)] de subcategorias ativas de uma categoria."""
    s = get_session()
    try:
        subs = (
            s.query(Subcategoria)
            .filter_by(categoria_id=categoria_id, ativo=True)
            .order_by(Subcategoria.nome)
            .all()
        )
        return [(sc.id, sc.nome) for sc in subs]
    finally:
        s.close()


@st.cache_data(ttl=300)
def carregar_municipios():
    """Retorna lista de nomes de municípios de SP, ordenada por nome."""
    s = get_session()
    try:
        munis = s.query(Municipio).filter_by(estado="SP").order_by(Municipio.nome).all()
        return [m.nome for m in munis]
    finally:
        s.close()


@st.cache_data(ttl=300)
def carregar_tecnicos_ativos():
    """Retorna [(id, nome)] de usuários técnicos ativos, ordenados por nome."""
    s = get_session()
    try:
        tecs = (
            s.query(Usuario)
            .filter_by(tipo=TipoUsuario.tecnico, ativo=True)
            .order_by(Usuario.nome)
            .all()
        )
        return [(t.id, t.nome) for t in tecs]
    finally:
        s.close()


@st.cache_data(ttl=300)
def carregar_gerencias():
    """Retorna [(id, nome)] de gerências ativas, ordenadas por nome."""
    s = get_session()
    try:
        gs = s.query(Gerencia).filter_by(ativo=True).order_by(Gerencia.nome).all()
        return [(g.id, g.nome) for g in gs]
    finally:
        s.close()


@st.cache_data(ttl=300)
def carregar_coordenacoes(gerencia_id: int | None = None):
    """Retorna [(id, nome)] de coordenações ativas, com filtro opcional por gerência."""
    s = get_session()
    try:
        q = s.query(Coordenacao).filter_by(ativo=True)
        if gerencia_id is not None:
            q = q.filter_by(gerencia_id=gerencia_id)
        cs = q.order_by(Coordenacao.nome).all()
        return [(c.id, c.nome) for c in cs]
    finally:
        s.close()


@st.cache_data(ttl=300)
def carregar_cidades_por_tipo(tipo_servico: str):
    """Retorna cidades de origem via nome IBGE, filtradas pelo tipo de serviço.
    Fretamento: todos os municípios SP. Regular: apenas cidades com paradas ativas."""
    s = get_session()
    try:
        if "Fretamento" in tipo_servico:
            rows = s.query(Municipio.nome).filter_by(estado="SP").order_by(Municipio.nome).all()
            return [r[0] for r in rows]
        q = (
            s.query(Municipio.nome)
            .join(ParadaAutoLinha, ParadaAutoLinha.municipio_id == Municipio.id)
            .join(AutoLinha, AutoLinha.id == ParadaAutoLinha.auto_id)
            .filter(AutoLinha.tipo == tipo_servico, AutoLinha.ativo == True)
        )
        return sorted({r[0] for r in q.distinct().all() if r[0]})
    finally:
        s.close()


@st.cache_data(ttl=300)
def carregar_cidades(tipo_servico: str, perm_id: int | None = None, regiao: str | None = None):
    """Retorna cidades via nome IBGE para busca por trecho, com filtros opcionais."""
    s = get_session()
    try:
        q = (
            s.query(Municipio.nome)
            .join(ParadaAutoLinha, ParadaAutoLinha.municipio_id == Municipio.id)
            .join(AutoLinha, AutoLinha.id == ParadaAutoLinha.auto_id)
            .filter(AutoLinha.tipo == tipo_servico, AutoLinha.ativo == True)
        )
        if perm_id is not None:
            q = q.filter(AutoLinha.permissionaria_id == perm_id)
        if regiao is not None:
            q = q.filter(AutoLinha.regiao_metropolitana == regiao)
        return sorted({r[0] for r in q.distinct().all() if r[0]})
    finally:
        s.close()


@st.cache_data(ttl=300)
def carregar_todos_autos(tipo_servico: str, perm_id: int | None = None, regiao: str | None = None):
    """Retorna todos os autos filtrados: (id, numero, cidade_ini, cidade_fim, empresa)."""
    s = get_session()
    try:
        q = s.query(AutoLinha).filter(AutoLinha.tipo == tipo_servico, AutoLinha.ativo == True)
        if perm_id is not None:
            q = q.filter(AutoLinha.permissionaria_id == perm_id)
        if regiao is not None:
            q = q.filter(AutoLinha.regiao_metropolitana == regiao)
        autos = q.order_by(AutoLinha.numero).all()
        return [(a.id, a.numero, a.cidade_inicial or "", a.cidade_final or "",
                 a.permissionaria.nome if a.permissionaria else "") for a in autos]
    finally:
        s.close()


@st.cache_data(ttl=300)
def carregar_permissionarias(tipo_servico: str, regiao: str | None = None):
    """Retorna permissionárias que possuem autos do tipo informado."""
    s = get_session()
    try:
        q = (
            s.query(Permissionaria)
            .join(AutoLinha, AutoLinha.permissionaria_id == Permissionaria.id)
            .filter(AutoLinha.tipo == tipo_servico, AutoLinha.ativo == True)
        )
        if regiao is not None:
            q = q.filter(AutoLinha.regiao_metropolitana == regiao)
        perms = q.distinct().order_by(Permissionaria.nome).all()
        return [(p.id, p.nome) for p in perms]
    finally:
        s.close()


@st.cache_data(ttl=300)
def carregar_regioes_metropolitanas():
    """Retorna lista de regiões metropolitanas distintas."""
    s = get_session()
    try:
        rows = (
            s.query(AutoLinha.regiao_metropolitana)
            .filter(AutoLinha.tipo == TipoServico.REGULAR_METROPOLITANO.value, AutoLinha.ativo == True)
            .filter(AutoLinha.regiao_metropolitana.isnot(None))
            .distinct()
            .all()
        )
        return sorted({r[0].strip() for r in rows if r[0]})
    finally:
        s.close()


# ── Funções de invalidação ────────────────────────────────────────────────────

def invalidar_cache_categorias():
    """Invalida cache de categorias e subcategorias.
    Chamar após criar/editar/ativar/desativar categoria ou subcategoria no Admin.
    """
    carregar_categorias.clear()
    carregar_subcategorias.clear()


def invalidar_cache_usuarios():
    """Invalida cache de técnicos ativos.
    Chamar após criar/editar/ativar/desativar usuário no Admin.
    """
    carregar_tecnicos_ativos.clear()


def invalidar_cache_estrutura():
    """Invalida cache de gerências e coordenações.
    Chamar após criar/editar/ativar/desativar gerência ou coordenação no Admin.
    """
    carregar_gerencias.clear()
    carregar_coordenacoes.clear()
