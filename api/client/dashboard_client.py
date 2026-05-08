"""Consome a API via HTTP — apenas produtividade (qualidade migrou para Dash/qualidade-v2)."""
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

