"""Dashboard de Produtividade – volume, status, prazos e desempenho de técnicos."""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import altair as alt
from datetime import date, timedelta

import auth
from auth import usuario_logado
from models import StatusOuvidoria
from utils import (
    carregar_gerencias_ativas,
    query_distribuicao_status,
    query_kpis_produtividade,
    query_ranking_coordenacoes,
    query_tempo_medio_por_tecnico,
    query_tempo_medio_resposta,
    query_vencidas_por_coordenacao,
    query_volume_por_mes,
)

st.set_page_config(page_title="Dashboard Produtividade", page_icon="📊", layout="wide")
st.markdown('<style>[data-testid="stSidebar"]{width:220px!important;min-width:220px!important;}</style>', unsafe_allow_html=True)
auth.require_gestor()

u = usuario_logado()

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"**{u.nome}**")
    st.caption("Gestor")
    st.divider()
    if st.button("← Ouvidorias", use_container_width=True):
        st.switch_page("pages/01_Ouvidorias.py")
    if st.button("Sair", use_container_width=True):
        auth.fazer_logout()
        st.rerun()

    st.divider()
    st.markdown("#### Filtros")

    hoje = date.today()
    data_ini = st.date_input("De", value=hoje - timedelta(days=365), key="prod_ini")
    data_fim = st.date_input("Até", value=hoje, key="prod_fim")

    ger_opcoes = [("", "Todas")] + carregar_gerencias_ativas()
    ger_sel_label = st.selectbox("Gerência", [n for _, n in ger_opcoes], key="prod_ger")
    ger_sel_id = next((gid for gid, n in ger_opcoes if n == ger_sel_label), "")

    status_opcoes = [s.value for s in StatusOuvidoria]
    status_sel = st.multiselect("Status", status_opcoes, default=status_opcoes, key="prod_status")

st.title("📊 Dashboard de Produtividade")

if data_ini > data_fim:
    st.error("A data inicial deve ser anterior à data final.")
    st.stop()

status_list = status_sel if status_sel else status_opcoes

# ── KPIs ─────────────────────────────────────────────────────────────────────
total, concluidas, vencidas = query_kpis_produtividade(data_ini, data_fim, ger_sel_id, status_list)
media_dias = query_tempo_medio_resposta(data_ini, data_fim, ger_sel_id, status_list)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total de Ouvidorias", total)
c2.metric("Concluídas", concluidas)
c3.metric("Vencidas", vencidas, delta=None)
c4.metric("Tempo Médio de Resposta", f"{media_dias} dias" if media_dias else "–")

st.divider()

# ── Gráfico 1 — Volume por mês ────────────────────────────────────────────────
st.subheader("Volume por Mês")
vol_rows = query_volume_por_mes(data_ini, data_fim, ger_sel_id, status_list)
if vol_rows:
    df_vol = pd.DataFrame(vol_rows, columns=["mes", "total"])
    chart = (
        alt.Chart(df_vol)
        .mark_bar(color="#1f77b4")
        .encode(
            x=alt.X("mes:N", title="Mês", sort=None),
            y=alt.Y("total:Q", title="Ouvidorias"),
            tooltip=["mes", "total"],
        )
        .properties(height=300)
    )
    st.altair_chart(chart, use_container_width=True)
else:
    st.info("Sem dados no período selecionado.")

# ── Gráfico 2 — Distribuição por status ───────────────────────────────────────
st.subheader("Distribuição por Status")
status_rows = query_distribuicao_status(data_ini, data_fim, ger_sel_id, status_list)
if status_rows:
    df_st = pd.DataFrame(status_rows, columns=["status", "total"])
    cor_map = {
        "Aguardando ações": "#f0ad4e",
        "Aguardando resposta da permissionária": "#5bc0de",
        "Em análise técnica": "#9b59b6",
        "Retorno técnico": "#e74c3c",
        "Concluído": "#2ecc71",
    }
    df_st["cor"] = df_st["status"].map(cor_map).fillna("#aaa")
    chart_st = (
        alt.Chart(df_st)
        .mark_bar()
        .encode(
            y=alt.Y("status:N", sort="-x", title="Status"),
            x=alt.X("total:Q", title="Ouvidorias"),
            color=alt.Color("status:N", scale=alt.Scale(domain=list(cor_map.keys()), range=list(cor_map.values())), legend=None),
            tooltip=["status", "total"],
        )
        .properties(height=220)
    )
    st.altair_chart(chart_st, use_container_width=True)
else:
    st.info("Sem dados.")

col_left, col_right = st.columns(2)

# ── Gráfico 3 — Vencidas por coordenação ────────────────────────────────────
with col_left:
    st.subheader("Vencidas por Coordenação")
    venc_rows = query_vencidas_por_coordenacao(data_ini, data_fim)
    if venc_rows:
        df_venc = pd.DataFrame(venc_rows, columns=["coordenacao", "total"])
        chart_venc = (
            alt.Chart(df_venc)
            .mark_bar(color="#e74c3c")
            .encode(
                y=alt.Y("coordenacao:N", sort="-x", title="Coordenação"),
                x=alt.X("total:Q", title="Vencidas"),
                tooltip=["coordenacao", "total"],
            )
            .properties(height=300)
        )
        st.altair_chart(chart_venc, use_container_width=True)
    else:
        st.info("Nenhuma ouvidoria vencida no período.")

# ── Gráfico 4 — Tempo médio de resposta por técnico ─────────────────────────
with col_right:
    st.subheader("Tempo Médio de Resposta por Técnico")
    resp_rows = query_tempo_medio_por_tecnico(data_ini, data_fim)
    if resp_rows:
        df_resp = pd.DataFrame(resp_rows, columns=["tecnico", "media_dias"])
        df_resp["media_dias"] = df_resp["media_dias"].astype(float).round(1)
        chart_resp = (
            alt.Chart(df_resp)
            .mark_bar(color="#9b59b6")
            .encode(
                y=alt.Y("tecnico:N", sort="-x", title="Técnico"),
                x=alt.X("media_dias:Q", title="Dias (média)"),
                tooltip=["tecnico", alt.Tooltip("media_dias:Q", format=".1f")],
            )
            .properties(height=300)
        )
        st.altair_chart(chart_resp, use_container_width=True)
    else:
        st.info("Sem respostas registradas no período.")

# ── Gráfico 5 — Ranking de coordenações por volume ───────────────────────────
st.subheader("Ranking de Coordenações por Volume de Atendimento")
rank_rows = query_ranking_coordenacoes(data_ini, data_fim, ger_sel_id, status_list)
if rank_rows:
    df_rank = pd.DataFrame(rank_rows, columns=["coordenacao", "total"])
    chart_rank = (
        alt.Chart(df_rank)
        .mark_bar(color="#2ecc71")
        .encode(
            y=alt.Y("coordenacao:N", sort="-x", title="Coordenação"),
            x=alt.X("total:Q", title="Ouvidorias Atribuídas"),
            tooltip=["coordenacao", "total"],
        )
        .properties(height=300)
    )
    st.altair_chart(chart_rank, use_container_width=True)
else:
    st.info("Sem dados de coordenações no período.")
