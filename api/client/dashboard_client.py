"""Substitui utils/loaders_dashboard.py — consome a API via HTTP."""
import streamlit as st
from api.client.base import get

_TTL = 120


def _params_base(data_ini, data_fim, ger_id=None, status_list=None) -> dict:
    p = {"data_ini": str(data_ini), "data_fim": str(data_fim)}
    if ger_id:
        p["ger_id"] = ger_id
    if status_list:
        p["status_ids"] = ",".join(status_list)
    return p


def _params_qual(data_ini, data_fim, ger_id=None, perm_id=None, cat_list=None, tipo_servico=None) -> dict:
    p = {"data_ini": str(data_ini), "data_fim": str(data_fim)}
    if ger_id:
        p["ger_id"] = ger_id
    if perm_id:
        p["perm_id"] = perm_id
    if cat_list:
        p["cat_ids"] = ",".join(str(c) for c in cat_list)
    if tipo_servico:
        p["tipo_servico"] = tipo_servico
    return p


# ── Produtividade ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=_TTL)
def query_kpis_produtividade(data_ini, data_fim, ger_id, status_list):
    d = get("/dashboard/produtividade/kpis", params=_params_base(data_ini, data_fim, ger_id, status_list))
    return (d["total"], d["concluidas"], d["vencidas"])


@st.cache_data(ttl=_TTL)
def query_tempo_medio_resposta(data_ini, data_fim, ger_id, status_list):
    d = get("/dashboard/produtividade/tempo-medio", params=_params_base(data_ini, data_fim, ger_id, status_list))
    return d["dias"]


@st.cache_data(ttl=_TTL)
def query_volume_por_mes(data_ini, data_fim, ger_id, status_list):
    rows = get("/dashboard/produtividade/volume-por-mes", params=_params_base(data_ini, data_fim, ger_id, status_list))
    return [(r["mes"], r["total"]) for r in rows]


@st.cache_data(ttl=_TTL)
def query_distribuicao_status(data_ini, data_fim, ger_id, status_list):
    rows = get("/dashboard/produtividade/distribuicao-status", params=_params_base(data_ini, data_fim, ger_id, status_list))
    return [(r["status"], r["total"]) for r in rows]


@st.cache_data(ttl=_TTL)
def query_vencidas_por_coordenacao(data_ini, data_fim):
    rows = get("/dashboard/produtividade/vencidas-por-coordenacao",
               params={"data_ini": str(data_ini), "data_fim": str(data_fim)})
    return [(r["coordenacao"], r["total"]) for r in rows]


@st.cache_data(ttl=_TTL)
def query_tempo_medio_por_tecnico(data_ini, data_fim):
    rows = get("/dashboard/produtividade/tempo-medio-por-tecnico",
               params={"data_ini": str(data_ini), "data_fim": str(data_fim)})
    return [(r["tecnico_nome"], r["dias_medios"]) for r in rows]


@st.cache_data(ttl=_TTL)
def query_ranking_coordenacoes(data_ini, data_fim, ger_id, status_list):
    rows = get("/dashboard/produtividade/ranking-coordenacoes",
               params=_params_base(data_ini, data_fim, ger_id, status_list))
    return [(r["coordenacao_nome"], r["metrica"]) for r in rows]


# ── Qualidade ─────────────────────────────────────────────────────────────────

@st.cache_data(ttl=_TTL)
def query_kpis_qualidade(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico):
    d = get("/dashboard/qualidade/kpis", params=_params_qual(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico))
    return (d["total_reclamacoes"], d["pontuacao"], d["autos_unicos"])


@st.cache_data(ttl=_TTL)
def query_top_permissionaria(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico):
    d = get("/dashboard/qualidade/top-permissionaria", params=_params_qual(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico))
    return (d["nome"], d["pontos"])


@st.cache_data(ttl=_TTL)
def query_top_categoria(data_ini, data_fim, ger_id, cat_list, tipo_servico):
    d = get("/dashboard/qualidade/top-categoria",
            params=_params_qual(data_ini, data_fim, ger_id, None, cat_list, tipo_servico))
    return d["categoria"]


@st.cache_data(ttl=_TTL)
def query_sla(data_ini, data_fim, ger_id):
    d = get("/dashboard/qualidade/sla",
            params={"data_ini": str(data_ini), "data_fim": str(data_fim), **({"ger_id": ger_id} if ger_id else {})})
    return (d["total"], d["dentro_prazo"])


@st.cache_data(ttl=_TTL)
def query_evolucao_mensal(data_ini, data_fim, ger_id, cat_list, tipo_servico):
    rows = get("/dashboard/qualidade/evolucao-mensal", params=_params_qual(data_ini, data_fim, ger_id, None, cat_list, tipo_servico))
    return [(r["mes"], r["total"]) for r in rows]


@st.cache_data(ttl=_TTL)
def query_top_autos_pontuacao(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico, top_n=20):
    p = _params_qual(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico)
    p["top_n"] = top_n
    rows = get("/dashboard/qualidade/top-autos", params=p)
    return [(r["auto_numero"], r["pontuacao"]) for r in rows]


@st.cache_data(ttl=_TTL)
def query_empresas_pontuacao(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico):
    rows = get("/dashboard/qualidade/empresas-pontuacao", params=_params_qual(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico))
    return [(r["empresa"], r["pontos"]) for r in rows]


@st.cache_data(ttl=_TTL)
def query_categorias_pizza(data_ini, data_fim, ger_id, cat_list, tipo_servico):
    rows = get("/dashboard/qualidade/categorias-pizza", params=_params_qual(data_ini, data_fim, ger_id, None, cat_list, tipo_servico))
    return [(r["categoria"], r["total"]) for r in rows]


@st.cache_data(ttl=_TTL)
def query_cidades(data_ini, data_fim, ger_id, tipo_servico, tipo_cidade="Ambos"):
    p = {"data_ini": str(data_ini), "data_fim": str(data_fim), "tipo_cidade": tipo_cidade}
    if ger_id:
        p["ger_id"] = ger_id
    if tipo_servico:
        p["tipo_servico"] = tipo_servico
    rows = get("/dashboard/qualidade/cidades", params=p)
    return [(r["cidade"], r["count"]) for r in rows]


@st.cache_data(ttl=_TTL)
def query_heatmap_cat_empresa(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico):
    rows = get("/dashboard/qualidade/heatmap-cat-empresa", params=_params_qual(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico))
    return [(r["categoria"], r["empresa"], r["count"]) for r in rows]


@st.cache_data(ttl=_TTL)
def query_tendencia_empresa(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico):
    rows = get("/dashboard/qualidade/tendencia-empresa", params=_params_qual(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico))
    return [(r["periodo"], r["empresa"], r["valor"]) for r in rows]


@st.cache_data(ttl=_TTL)
def query_tabela_analitica(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico):
    import pandas as pd
    rows = get("/dashboard/qualidade/tabela-analitica", params=_params_qual(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico))
    return pd.DataFrame(rows) if rows else pd.DataFrame()
