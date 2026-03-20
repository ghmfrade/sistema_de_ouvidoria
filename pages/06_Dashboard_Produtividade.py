"""Dashboard de Produtividade – volume, status, prazos e desempenho de técnicos."""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import altair as alt
from datetime import date, timedelta
from sqlalchemy import text

import auth
from auth import usuario_logado
from database.connection import get_session
from models import Gerencia, StatusOuvidoria

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

    def _gerencias_ativas():
        s = get_session()
        try:
            return [(g.id, g.nome) for g in s.query(Gerencia).filter_by(ativo=True).order_by(Gerencia.nome).all()]
        finally:
            s.close()

    ger_opcoes = [("", "Todas")] + _gerencias_ativas()
    ger_sel_label = st.selectbox("Gerência", [n for _, n in ger_opcoes], key="prod_ger")
    ger_sel_id = next((gid for gid, n in ger_opcoes if n == ger_sel_label), "")

    status_opcoes = [s.value for s in StatusOuvidoria]
    status_sel = st.multiselect("Status", status_opcoes, default=status_opcoes, key="prod_status")

st.title("📊 Dashboard de Produtividade")

if data_ini > data_fim:
    st.error("A data inicial deve ser anterior à data final.")
    st.stop()

# ── Helpers de query ─────────────────────────────────────────────────────────
def _exec(sql, params=None):
    s = get_session()
    try:
        rows = s.execute(text(sql), params or {}).fetchall()
        return rows
    finally:
        s.close()


# filtro de gerência: restringe via JOIN com ouvidoria_tecnicos → usuarios
_ger_join = """
    JOIN ouvidoria_tecnicos ot ON ot.ouvidoria_id = o.id
    JOIN usuarios u ON u.id = ot.tecnico_id
""" if ger_sel_id else ""
_ger_where = "AND u.gerencia_id = :ger_id" if ger_sel_id else ""

status_list = status_sel if status_sel else status_opcoes
_status_where = "AND o.status::text = ANY(:statuses)"

base_params = {
    "ini": data_ini,
    "fim": data_fim,
    "ger_id": ger_sel_id or None,
    "statuses": status_list,
}

# ── KPIs ─────────────────────────────────────────────────────────────────────
kpi_sql = f"""
    SELECT
        COUNT(DISTINCT o.id) AS total,
        COUNT(DISTINCT o.id) FILTER (WHERE o.status::text = 'Concluído') AS concluidas,
        COUNT(DISTINCT o.id) FILTER (WHERE o.prazo < CURRENT_DATE AND o.status::text <> 'Concluído') AS vencidas
    FROM ouvidorias o
    {_ger_join}
    WHERE o.criado_em::date BETWEEN :ini AND :fim
    {_ger_where}
    {_status_where}
"""
kpi_row = _exec(kpi_sql, base_params)
total, concluidas, vencidas = (kpi_row[0] if kpi_row else (0, 0, 0))

tempo_sql = f"""
    SELECT AVG((rt.data_resposta - o.criado_em::date)) AS media_dias
    FROM respostas_tecnicas rt
    JOIN ouvidorias o ON o.id = rt.ouvidoria_id
    {_ger_join}
    WHERE o.criado_em::date BETWEEN :ini AND :fim
    {_ger_where}
    {_status_where}
"""
tempo_row = _exec(tempo_sql, base_params)
media_dias = round(float(tempo_row[0][0]), 1) if tempo_row and tempo_row[0][0] else None

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total de Ouvidorias", total)
c2.metric("Concluídas", concluidas)
c3.metric("Vencidas", vencidas, delta=None)
c4.metric("Tempo Médio de Resposta", f"{media_dias} dias" if media_dias else "–")

st.divider()

# ── Gráfico 1 — Volume por mês ────────────────────────────────────────────────
st.subheader("Volume por Mês")
vol_sql = f"""
    SELECT TO_CHAR(DATE_TRUNC('month', o.criado_em), 'YYYY-MM') AS mes,
           COUNT(DISTINCT o.id) AS total
    FROM ouvidorias o
    {_ger_join}
    WHERE o.criado_em::date BETWEEN :ini AND :fim
    {_ger_where}
    {_status_where}
    GROUP BY mes ORDER BY mes
"""
vol_rows = _exec(vol_sql, base_params)
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
status_sql = f"""
    SELECT o.status, COUNT(DISTINCT o.id) AS total
    FROM ouvidorias o
    {_ger_join}
    WHERE o.criado_em::date BETWEEN :ini AND :fim
    {_ger_where}
    {_status_where}
    GROUP BY o.status ORDER BY total DESC
"""
status_rows = _exec(status_sql, base_params)
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
    venc_sql = """
        SELECT c.nome AS coordenacao, COUNT(DISTINCT o.id) AS total
        FROM ouvidorias o
        JOIN ouvidoria_tecnicos ot ON ot.ouvidoria_id = o.id
        JOIN usuarios usr ON usr.id = ot.tecnico_id
        JOIN coordenacoes c ON c.id = usr.coordenacao_id
        WHERE o.prazo < CURRENT_DATE
          AND o.status::text <> 'Concluído'
          AND o.criado_em::date BETWEEN :ini AND :fim
        GROUP BY c.nome ORDER BY total DESC
        LIMIT 15
    """
    venc_rows = _exec(venc_sql, {"ini": data_ini, "fim": data_fim})
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
    resp_sql = f"""
        SELECT usr.nome AS tecnico,
               AVG((rt.data_resposta - o.criado_em::date)) AS media_dias
        FROM respostas_tecnicas rt
        JOIN ouvidorias o ON o.id = rt.ouvidoria_id
        JOIN usuarios usr ON usr.id = rt.tecnico_id
        WHERE o.criado_em::date BETWEEN :ini AND :fim
        GROUP BY usr.nome ORDER BY media_dias DESC
        LIMIT 15
    """
    resp_rows = _exec(resp_sql, {"ini": data_ini, "fim": data_fim})
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
rank_sql = f"""
    SELECT c.nome AS coordenacao, COUNT(DISTINCT o.id) AS total
    FROM ouvidorias o
    JOIN ouvidoria_tecnicos ot ON ot.ouvidoria_id = o.id
    JOIN usuarios usr ON usr.id = ot.tecnico_id
    JOIN coordenacoes c ON c.id = usr.coordenacao_id
    WHERE o.criado_em::date BETWEEN :ini AND :fim
    {_ger_where}
    {_status_where}
    GROUP BY c.nome ORDER BY total DESC
    LIMIT 15
"""
rank_rows = _exec(rank_sql, base_params)
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
