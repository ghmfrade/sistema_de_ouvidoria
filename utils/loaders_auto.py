"""Loaders de autos de linha, cidades, permissionarias e regioes metropolitanas."""

import streamlit as st
from sqlalchemy import exists
from sqlalchemy.orm import aliased

from database.connection import get_session
from models import AutoLinha, Municipio, ParadaAutoLinha, Permissionaria, TipoServico

@st.cache_data(ttl=300)
def carregar_cidades_por_tipo(tipo_servico: str):
    """Retorna cidades de origem via nome IBGE, filtradas pelo tipo de servico.
    Fretamento: todos os municipios SP. Regular: apenas cidades com paradas ativas."""
    session = get_session()
    try:
        if "Fretamento" in tipo_servico:
            rows = session.query(Municipio.nome).filter_by(estado="SP").order_by(Municipio.nome).all()
            return [r[0] for r in rows]
        q = (
            session.query(Municipio.nome)
            .join(ParadaAutoLinha, ParadaAutoLinha.municipio_id == Municipio.id)
            .join(AutoLinha, AutoLinha.id == ParadaAutoLinha.auto_id)
            .filter(AutoLinha.tipo == tipo_servico, AutoLinha.ativo == True)
        )
        return sorted({r[0] for r in q.distinct().all() if r[0]})
    finally:
        session.close()


@st.cache_data(ttl=300)
def carregar_cidades(tipo_servico: str, perm_id: int | None = None, regiao: str | None = None):
    """Retorna cidades via nome IBGE para busca por trecho, com filtros opcionais."""
    session = get_session()
    try:
        q = (
            session.query(Municipio.nome)
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
        session.close()


def carregar_cidades_destino(tipo_servico: str, nome_origem: str,
                             perm_id: int | None = None, regiao: str | None = None):
    """Retorna cidades alcancaveis a partir da origem (via linhas que passam pela origem).
    Fretamento: todos os municipios SP (sem filtro). Regular: filtra por linhas em comum."""
    session = get_session()
    try:
        if "Fretamento" in tipo_servico:
            rows = session.query(Municipio.nome).filter_by(estado="SP").order_by(Municipio.nome).all()
            return [r[0] for r in rows if r[0] != nome_origem]

        mun_id_orig = session.query(Municipio.id).filter_by(nome=nome_origem).scalar()
        if not mun_id_orig:
            return []

        ParadaOrig = aliased(ParadaAutoLinha)
        q = (
            session.query(Municipio.nome)
            .join(ParadaAutoLinha, ParadaAutoLinha.municipio_id == Municipio.id)
            .join(AutoLinha, AutoLinha.id == ParadaAutoLinha.auto_id)
            .filter(
                AutoLinha.tipo == tipo_servico,
                AutoLinha.ativo == True,
                Municipio.id != mun_id_orig,
                exists().where(
                    (ParadaOrig.auto_id == AutoLinha.id) &
                    (ParadaOrig.municipio_id == mun_id_orig)
                ),
            )
        )
        if perm_id is not None:
            q = q.filter(AutoLinha.permissionaria_id == perm_id)
        if regiao is not None:
            q = q.filter(AutoLinha.regiao_metropolitana == regiao)
        return sorted({r[0] for r in q.distinct().all() if r[0]})
    finally:
        session.close()


@st.cache_data(ttl=300)
def carregar_todos_autos(tipo_servico: str, perm_id: int | None = None, regiao: str | None = None):
    """Retorna todos os autos filtrados: (id, numero, cidade_ini, cidade_fim, empresa)."""
    session = get_session()
    try:
        q = session.query(AutoLinha).filter(AutoLinha.tipo == tipo_servico, AutoLinha.ativo == True)
        if perm_id is not None:
            q = q.filter(AutoLinha.permissionaria_id == perm_id)
        if regiao is not None:
            q = q.filter(AutoLinha.regiao_metropolitana == regiao)
        autos = q.order_by(AutoLinha.numero).all()
        return [(a.id, a.numero, a.cidade_inicial or "", a.cidade_final or "",
                 a.permissionaria.nome if a.permissionaria else "") for a in autos]
    finally:
        session.close()


@st.cache_data(ttl=300)
def carregar_permissionarias(tipo_servico: str, regiao: str | None = None):
    """Retorna permissionarias que possuem autos do tipo informado: [(id, nome)]."""
    session = get_session()
    try:
        q = (
            session.query(Permissionaria)
            .join(AutoLinha, AutoLinha.permissionaria_id == Permissionaria.id)
            .filter(AutoLinha.tipo == tipo_servico, AutoLinha.ativo == True)
        )
        if regiao is not None:
            q = q.filter(AutoLinha.regiao_metropolitana == regiao)
        perms = q.distinct().order_by(Permissionaria.nome).all()
        return [(p.id, p.nome) for p in perms]
    finally:
        session.close()


@st.cache_data(ttl=300)
def carregar_regioes_metropolitanas():
    """Retorna lista de regioes metropolitanas distintas."""
    session = get_session()
    try:
        rows = (
            session.query(AutoLinha.regiao_metropolitana)
            .filter(AutoLinha.tipo == TipoServico.REGULAR_METROPOLITANO.value, AutoLinha.ativo == True)
            .filter(AutoLinha.regiao_metropolitana.isnot(None))
            .distinct()
            .all()
        )
        return sorted({r[0].strip() for r in rows if r[0]})
    finally:
        session.close()


def buscar_autos_por_trecho(tipo_servico: str, cidade_a: str, cidade_b: str,
                            perm_id: int | None = None, regiao: str | None = None):
    """Retorna autos que tem paradas em AMBAS as cidades (filtro por municipio_id)."""
    session = get_session()
    try:
        q = session.query(AutoLinha).filter(AutoLinha.tipo == tipo_servico, AutoLinha.ativo == True)
        if perm_id is not None:
            q = q.filter(AutoLinha.permissionaria_id == perm_id)
        if regiao is not None:
            q = q.filter(AutoLinha.regiao_metropolitana == regiao)
        if cidade_a:
            mun_id_a = session.query(Municipio.id).filter_by(nome=cidade_a).scalar()
            if mun_id_a:
                q = q.filter(exists().where(
                    (ParadaAutoLinha.auto_id == AutoLinha.id) &
                    (ParadaAutoLinha.municipio_id == mun_id_a)
                ))
        if cidade_b:
            mun_id_b = session.query(Municipio.id).filter_by(nome=cidade_b).scalar()
            if mun_id_b:
                q = q.filter(exists().where(
                    (ParadaAutoLinha.auto_id == AutoLinha.id) &
                    (ParadaAutoLinha.municipio_id == mun_id_b)
                ))
        autos = q.order_by(AutoLinha.numero).all()
        return [(a.id, a.numero, a.cidade_inicial or "", a.cidade_final or "",
                 a.permissionaria.nome if a.permissionaria else "") for a in autos]
    finally:
        session.close()
