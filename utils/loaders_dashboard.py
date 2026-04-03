"""Loaders dos dashboards: wrappers cacheados (ttl=120) sobre as queries de repositório."""

import streamlit as st

import repositories.dashboard.produtividade_repo as _prod
import repositories.dashboard.qualidade_repo as _qual

_TTL = 120

# ── Produtividade ──────────────────────────────────────────────────────────────


@st.cache_data(ttl=_TTL)
def query_kpis_produtividade(data_ini, data_fim, ger_id, status_list):
    return _prod.query_kpis_produtividade(data_ini, data_fim, ger_id, status_list)


@st.cache_data(ttl=_TTL)
def query_tempo_medio_resposta(data_ini, data_fim, ger_id, status_list):
    return _prod.query_tempo_medio_resposta(data_ini, data_fim, ger_id, status_list)


@st.cache_data(ttl=_TTL)
def query_volume_por_mes(data_ini, data_fim, ger_id, status_list):
    return _prod.query_volume_por_mes(data_ini, data_fim, ger_id, status_list)


@st.cache_data(ttl=_TTL)
def query_distribuicao_status(data_ini, data_fim, ger_id, status_list):
    return _prod.query_distribuicao_status(data_ini, data_fim, ger_id, status_list)


@st.cache_data(ttl=_TTL)
def query_vencidas_por_coordenacao(data_ini, data_fim):
    return _prod.query_vencidas_por_coordenacao(data_ini, data_fim)


@st.cache_data(ttl=_TTL)
def query_tempo_medio_por_tecnico(data_ini, data_fim):
    return _prod.query_tempo_medio_por_tecnico(data_ini, data_fim)


@st.cache_data(ttl=_TTL)
def query_ranking_coordenacoes(data_ini, data_fim, ger_id, status_list):
    return _prod.query_ranking_coordenacoes(data_ini, data_fim, ger_id, status_list)


# ── Qualidade ─────────────────────────────────────────────────────────────────


@st.cache_data(ttl=_TTL)
def query_kpis_qualidade(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico):
    return _qual.query_kpis_qualidade(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico)


@st.cache_data(ttl=_TTL)
def query_top_permissionaria(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico):
    return _qual.query_top_permissionaria(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico)


@st.cache_data(ttl=_TTL)
def query_top_categoria(data_ini, data_fim, ger_id, cat_list, tipo_servico):
    return _qual.query_top_categoria(data_ini, data_fim, ger_id, cat_list, tipo_servico)


@st.cache_data(ttl=_TTL)
def query_sla(data_ini, data_fim, ger_id):
    return _qual.query_sla(data_ini, data_fim, ger_id)


@st.cache_data(ttl=_TTL)
def query_evolucao_mensal(data_ini, data_fim, ger_id, cat_list, tipo_servico):
    return _qual.query_evolucao_mensal(data_ini, data_fim, ger_id, cat_list, tipo_servico)


@st.cache_data(ttl=_TTL)
def query_top_autos_pontuacao(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico, top_n=20):
    return _qual.query_top_autos_pontuacao(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico, top_n)


@st.cache_data(ttl=_TTL)
def query_empresas_pontuacao(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico):
    return _qual.query_empresas_pontuacao(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico)


@st.cache_data(ttl=_TTL)
def query_categorias_pizza(data_ini, data_fim, ger_id, cat_list, tipo_servico):
    return _qual.query_categorias_pizza(data_ini, data_fim, ger_id, cat_list, tipo_servico)


@st.cache_data(ttl=_TTL)
def query_cidades(data_ini, data_fim, ger_id, tipo_servico, tipo_cidade="Ambos"):
    return _qual.query_cidades(data_ini, data_fim, ger_id, tipo_servico, tipo_cidade)


@st.cache_data(ttl=_TTL)
def query_heatmap_cat_empresa(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico):
    return _qual.query_heatmap_cat_empresa(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico)


@st.cache_data(ttl=_TTL)
def query_tendencia_empresa(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico):
    return _qual.query_tendencia_empresa(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico)


@st.cache_data(ttl=_TTL)
def query_tabela_analitica(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico):
    return _qual.query_tabela_analitica(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico)
