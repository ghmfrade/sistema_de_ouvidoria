"""Dashboard de Qualidade / Fiscalizacao - autos, permissionarias, categorias e cidades."""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import altair as alt
from datetime import date, timedelta

import auth
from auth import usuario_logado
from utils import (
    carregar_categorias,
    carregar_gerencias_ativas,
    carregar_todas_permissionarias,
    query_categorias_pizza,
    query_cidades,
    query_empresas_pontuacao,
    query_evolucao_mensal,
    query_heatmap_cat_empresa,
    query_kpis_qualidade,
    query_sla,
    query_tabela_analitica,
    query_tendencia_empresa,
    query_top_autos_pontuacao,
    query_top_categoria,
    query_top_permissionaria,
    to_excel,
)
from components import reduz_margem_side_bar, reduz_margem_topo_page

st.set_page_config(page_title="Dashboard Qualidade", page_icon="🔎", layout="wide")
st.markdown('<style>[data-testid="stSidebar"]{width:220px!important;min-width:220px!important;}</style>', unsafe_allow_html=True)
auth.require_gestor()

u = usuario_logado()

reduz_margem_topo_page()

# ── Sidebar ──────────────────────────────────────────────────────────────────
reduz_margem_side_bar()
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
    st.markdown("### Filtros")

    ger_list = carregar_gerencias_ativas()
    cat_list_all = carregar_categorias()
    perm_list = carregar_todas_permissionarias()

    periodo_opcoes = {
        "Ultimos 3 meses": 90,
        "Ultimos 6 meses": 180,
        "Ultimo ano": 365,
        "Ultimos 2 anos": 730,
        "Personalizado": 0,
    }
    periodo_sel = st.selectbox("Periodo", list(periodo_opcoes.keys()), index=2, key="qual_periodo")

    hoje = date.today()
    if periodo_sel == "Personalizado":
        data_ini = st.date_input("De", value=hoje - timedelta(days=365), key="qual_ini")
        data_fim = st.date_input("Ate", value=hoje, key="qual_fim")
    else:
        dias = periodo_opcoes[periodo_sel]
        data_ini = hoje - timedelta(days=dias)
        data_fim = hoje

    st.divider()

    ger_opcoes = ["Todas"] + [n for _, n in ger_list]
    ger_sel = st.selectbox("Gerencia", ger_opcoes, key="qual_ger")
    ger_id = next((gid for gid, n in ger_list if n == ger_sel), None)

    cat_nomes = [n for _, n in cat_list_all]
    cat_sel = st.multiselect("Categorias", cat_nomes, default=cat_nomes, key="qual_cat")

    perm_opcoes = ["Todas"] + [n for _, n in perm_list]
    perm_sel = st.selectbox("Permissionaria", perm_opcoes, key="qual_perm")
    perm_id = next((pid for pid, n in perm_list if n == perm_sel), None)

    st.divider()
    tipo_servico_opcoes = ["Todos", "Regular – Intermunicipal", "Regular – Metropolitano", "Fretamento Intermunicipal", "Fretamento Metropolitano"]
    tipo_servico_sel = st.selectbox("Tipo de Servico", tipo_servico_opcoes, key="qual_tipo_srv")

    top_n = st.slider("Top N autos", min_value=10, max_value=50, value=20, step=5, key="qual_topn")

# ── Titulo ────────────────────────────────────────────────────────────────────
st.title("🔎 Dashboard de Qualidade e Fiscalizacao")
st.caption(f"Periodo: **{data_ini.strftime('%d/%m/%Y')}** a **{data_fim.strftime('%d/%m/%Y')}**")

if data_ini > data_fim:
    st.error("A data inicial deve ser anterior a data final.")
    st.stop()

# ── Parametros comuns ─────────────────────────────────────────────────────────
_cat_list = cat_sel if cat_sel else cat_nomes
_tipo_srv = tipo_servico_sel if tipo_servico_sel != "Todos" else None

# ── KPIs ──────────────────────────────────────────────────────────────────────
total_rec, pontuacao_total, autos_unicos = query_kpis_qualidade(data_ini, data_fim, ger_id, perm_id, _cat_list, _tipo_srv)

perm_top_result = query_top_permissionaria(data_ini, data_fim, ger_id, perm_id, _cat_list, _tipo_srv)
perm_top_nome = perm_top_result[0] if perm_top_result else "–"
perm_top_pts = perm_top_result[1] if perm_top_result else 0

cat_top = query_top_categoria(data_ini, data_fim, ger_id, _cat_list, _tipo_srv)

sla_total, sla_ok = query_sla(data_ini, data_fim, ger_id)
sla_pct = round((sla_ok / sla_total * 100), 1) if sla_total > 0 else 0

# ── Display KPIs ──────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Reclamacoes", total_rec)
k2.metric("Pontuacao Total", f"{pontuacao_total:.2f}")
k3.metric("Autos Reclamados", autos_unicos)
k4.metric("Categoria Top", cat_top)
k5.metric("SLA no Prazo", f"{sla_pct}%")

if perm_top_nome != "–":
    st.info(f"**Empresa com maior pontuacao acumulada:** {perm_top_nome} ({perm_top_pts} pts)")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECAO 1 — Evolucao Temporal
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("Evolucao Mensal de Reclamacoes")
evo_rows = query_evolucao_mensal(data_ini, data_fim, ger_id, _cat_list, _tipo_srv)
if evo_rows:
    df_evo = pd.DataFrame(evo_rows, columns=["mes", "total"])
    line = (
        alt.Chart(df_evo)
        .mark_area(
            line={"color": "#1f77b4"},
            color=alt.Gradient(
                gradient="linear",
                stops=[
                    alt.GradientStop(color="#1f77b4", offset=1),
                    alt.GradientStop(color="rgba(31,119,180,0.1)", offset=0),
                ],
                x1=1, x2=1, y1=1, y2=0,
            ),
        )
        .encode(
            x=alt.X("mes:N", title="Mes", sort=None, axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("total:Q", title="Reclamacoes"),
            tooltip=["mes", "total"],
        )
        .properties(height=280)
    )
    points = (
        alt.Chart(df_evo)
        .mark_circle(size=50, color="#1f77b4")
        .encode(x="mes:N", y="total:Q", tooltip=["mes", "total"])
    )
    st.altair_chart(line + points, use_container_width=True)
else:
    st.info("Sem dados no periodo.")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECAO 2 — Autos e Empresas
# ══════════════════════════════════════════════════════════════════════════════
col1, col2 = st.columns(2)

# ── Top N Autos por Pontuacao ─────────────────────────────────────────────────
with col1:
    st.subheader(f"Top {top_n} Autos por Pontuacao")
    autos_rows = query_top_autos_pontuacao(data_ini, data_fim, ger_id, perm_id, _cat_list, _tipo_srv, top_n)
    if autos_rows:
        df_autos = pd.DataFrame(autos_rows, columns=["auto", "pontuacao", "empresa"])
        df_autos["pontuacao"] = df_autos["pontuacao"].astype(float).round(4)
        chart_autos = (
            alt.Chart(df_autos)
            .mark_bar(cornerRadiusEnd=4)
            .encode(
                y=alt.Y("auto:N", sort="-x", title="Auto de Linha"),
                x=alt.X("pontuacao:Q", title="Pontuacao"),
                color=alt.Color("empresa:N", title="Empresa", legend=alt.Legend(orient="bottom", columns=2)),
                tooltip=["auto", "empresa", alt.Tooltip("pontuacao:Q", format=".4f")],
            )
            .properties(height=max(300, top_n * 18))
        )
        st.altair_chart(chart_autos, use_container_width=True)
    else:
        st.info("Sem dados no periodo.")

# ── Empresas por Pontuacao ────────────────────────────────────────────────────
with col2:
    st.subheader("Empresas por Pontuacao")
    perm_rows = query_empresas_pontuacao(data_ini, data_fim, ger_id, perm_id, _cat_list, _tipo_srv)
    if perm_rows:
        df_perm = pd.DataFrame(perm_rows, columns=["empresa", "pontuacao", "reclamacoes"])
        df_perm["pontuacao"] = df_perm["pontuacao"].astype(float).round(4)
        bars = (
            alt.Chart(df_perm)
            .mark_bar(cornerRadiusEnd=4, color="#e67e22")
            .encode(
                y=alt.Y("empresa:N", sort="-x", title="Empresa"),
                x=alt.X("pontuacao:Q", title="Pontuacao"),
                tooltip=["empresa", alt.Tooltip("pontuacao:Q", format=".4f"), "reclamacoes"],
            )
        )
        text_labels = bars.mark_text(align="left", dx=3, fontSize=11).encode(
            text=alt.Text("pontuacao:Q", format=".2f")
        )
        st.altair_chart((bars + text_labels).properties(height=max(300, len(df_perm) * 22)), use_container_width=True)
    else:
        st.info("Sem dados.")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECAO 3 — Categorias (pizza) + Cidades
# ══════════════════════════════════════════════════════════════════════════════
col3, col4 = st.columns(2)

# ── Pizza de Categorias ───────────────────────────────────────────────────────
with col3:
    st.subheader("Reclamacoes por Categoria")
    cat_rows = query_categorias_pizza(data_ini, data_fim, ger_id, _cat_list, _tipo_srv)
    if cat_rows:
        df_cat = pd.DataFrame(cat_rows, columns=["categoria", "total"])
        total_cat = df_cat["total"].sum()
        df_cat["percentual"] = (df_cat["total"] / total_cat * 100).round(1)

        pie = (
            alt.Chart(df_cat)
            .mark_arc(innerRadius=50, outerRadius=130, stroke="#fff", strokeWidth=2)
            .encode(
                theta=alt.Theta("total:Q", stack=True),
                color=alt.Color(
                    "categoria:N",
                    title="Categoria",
                    scale=alt.Scale(scheme="tableau10"),
                    legend=alt.Legend(orient="bottom", columns=2),
                ),
                tooltip=[
                    "categoria",
                    "total",
                    alt.Tooltip("percentual:Q", format=".1f", title="%"),
                ],
            )
            .properties(height=320, width=320)
        )
        st.altair_chart(pie, use_container_width=True)
    else:
        st.info("Sem dados.")

# ── Cidades — com seletor embarque/desembarque ────────────────────────────────
with col4:
    st.subheader("Top 20 Cidades")
    tipo_cidade = st.radio(
        "Filtrar por:",
        ["Embarque", "Desembarque", "Ambos"],
        horizontal=True,
        key="tipo_cidade",
    )

    cid_rows = query_cidades(data_ini, data_fim, ger_id, _tipo_srv, tipo_cidade)
    if cid_rows:
        df_cid = pd.DataFrame(cid_rows, columns=["cidade", "total"])
        chart_cid = (
            alt.Chart(df_cid)
            .mark_bar(cornerRadiusEnd=4, color="#1abc9c")
            .encode(
                y=alt.Y("cidade:N", sort="-x", title="Cidade"),
                x=alt.X("total:Q", title="Ocorrencias"),
                tooltip=["cidade", "total"],
            )
            .properties(height=max(280, len(df_cid) * 18))
        )
        st.altair_chart(chart_cid, use_container_width=True)
    else:
        st.info("Sem dados de cidades.")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECAO 4 — Heatmap: Categoria x Empresa
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("Mapa de Calor: Categorias x Empresas")
st.caption("Identifica concentracao de reclamacoes por tipo e empresa — util para acoes direcionadas de fiscalizacao.")

heat_rows = query_heatmap_cat_empresa(data_ini, data_fim, ger_id, perm_id, _cat_list, _tipo_srv)
if heat_rows:
    df_heat = pd.DataFrame(heat_rows, columns=["empresa", "categoria", "total"])
    # Limitar a top 15 empresas por volume total
    top_empresas = df_heat.groupby("empresa")["total"].sum().nlargest(15).index.tolist()
    df_heat = df_heat[df_heat["empresa"].isin(top_empresas)]

    heatmap = (
        alt.Chart(df_heat)
        .mark_rect(cornerRadius=3)
        .encode(
            x=alt.X("categoria:N", title="Categoria", axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("empresa:N", title="Empresa", sort="-x"),
            color=alt.Color(
                "total:Q",
                title="Reclamacoes",
                scale=alt.Scale(scheme="orangered"),
                legend=alt.Legend(orient="right"),
            ),
            tooltip=["empresa", "categoria", "total"],
        )
        .properties(height=max(300, len(top_empresas) * 25))
    )
    text_heat = (
        alt.Chart(df_heat)
        .mark_text(fontSize=11, color="white", fontWeight="bold")
        .encode(
            x="categoria:N",
            y=alt.Y("empresa:N", sort="-x"),
            text="total:Q",
            opacity=alt.condition(alt.datum.total > 0, alt.value(1), alt.value(0)),
        )
    )
    st.altair_chart(heatmap + text_heat, use_container_width=True)
else:
    st.info("Sem dados para o heatmap.")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECAO 5 — Reclamacoes por mes por empresa (stacked area)
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("Tendencia Mensal por Empresa")
st.caption("Acompanhe como cada permissionaria evolui ao longo do tempo — identifique picos e tendencias.")

trend_rows = query_tendencia_empresa(data_ini, data_fim, ger_id, perm_id, _cat_list, _tipo_srv)
if trend_rows:
    df_trend = pd.DataFrame(trend_rows, columns=["mes", "empresa", "total"])
    # Limitar top 8 empresas
    top_emp_trend = df_trend.groupby("empresa")["total"].sum().nlargest(8).index.tolist()
    df_trend = df_trend[df_trend["empresa"].isin(top_emp_trend)]

    area_chart = (
        alt.Chart(df_trend)
        .mark_area(opacity=0.7, interpolate="monotone")
        .encode(
            x=alt.X("mes:N", title="Mes", sort=None, axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("total:Q", stack="zero", title="Reclamacoes"),
            color=alt.Color("empresa:N", title="Empresa", scale=alt.Scale(scheme="tableau10"),
                            legend=alt.Legend(orient="bottom", columns=2)),
            tooltip=["mes", "empresa", "total"],
        )
        .properties(height=350)
    )
    st.altair_chart(area_chart, use_container_width=True)
else:
    st.info("Sem dados para tendencia.")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECAO 6 — Tabela exportavel
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("Tabela Analitica de Autos")
st.caption("Detalhe completo dos autos de linha com pontuacao acumulada — exporte para Excel para relatorios.")

tabela_rows = query_tabela_analitica(data_ini, data_fim, ger_id, perm_id, _cat_list, _tipo_srv)
if tabela_rows:
    df_tabela = pd.DataFrame(tabela_rows, columns=[
        "Auto", "Tipo", "Itinerario", "Empresa", "Cidade Inicial", "Cidade Final", "Reclamacoes", "Pontuacao",
    ])
    st.dataframe(
        df_tabela,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Pontuacao": st.column_config.NumberColumn(format="%.4f"),
            "Reclamacoes": st.column_config.NumberColumn(format="%d"),
        },
    )

    c_dl1, c_dl2, _ = st.columns([1, 1, 3])
    c_dl1.download_button(
        label="Exportar Excel",
        data=to_excel(df_tabela),
        file_name=f"autos_pontuacao_{data_ini}_{data_fim}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )
else:
    st.info("Sem dados de autos no periodo.")
