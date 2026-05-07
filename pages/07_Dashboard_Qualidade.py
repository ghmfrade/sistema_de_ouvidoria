"""Dashboard de Qualidade / Fiscalizacao - autos, permissionarias, categorias e cidades."""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import altair as alt
from datetime import date, timedelta

import auth
from auth import usuario_logado
from api.client.catalogo_client import carregar_categorias, carregar_gerencias_ativas
from api.client.dashboard_client import (
    query_categorias_pizza, query_cidades, query_empresas_pontuacao,
    query_evolucao_mensal, query_heatmap_cat_empresa, query_kpis_qualidade,
    query_sla, query_tabela_analitica, query_tendencia_empresa,
    query_top_autos_pontuacao, query_top_categoria, query_top_permissionaria,
)
from utils import to_excel
from components import reduz_margem_side_bar, reduz_margem_topo_page

st.set_page_config(page_title="Dashboard Qualidade", page_icon="🔎", layout="wide")
st.markdown('<style>[data-testid="stSidebar"]{width:220px!important;min-width:220px!important;}</style>', unsafe_allow_html=True)
auth.require_gestor()

u = usuario_logado()
reduz_margem_topo_page()

# ── Sidebar ──────────────────────────────────────────────────────────────────
reduz_margem_side_bar()
with st.sidebar:
    st.markdown(f"**{u['nome']}**")
    st.caption("Gestor")
    st.divider()
    if st.button("← Ouvidorias", use_container_width=True):
        st.switch_page("pages/01_Ouvidorias.py")
    if st.button("Sair", use_container_width=True):
        auth.fazer_logout(); st.rerun()

    st.divider()
    st.markdown("### Filtros")

    ger_list = carregar_gerencias_ativas()
    cat_list_all = carregar_categorias()

    # Permissionárias: buscadas via endpoint de catálogo para todos os tipos
    from api.client.base import get
    _perms_raw = get("/catalogo/permissionarias", params={"tipo_servico": "Regular – Metropolitano"})
    perm_list = [(p["id"], p["nome"]) for p in _perms_raw]

    periodo_opcoes = {
        "Ultimos 3 meses": 90, "Ultimos 6 meses": 180,
        "Ultimo ano": 365, "Ultimos 2 anos": 730, "Personalizado": 0,
    }
    periodo_sel = st.selectbox("Periodo", list(periodo_opcoes.keys()), index=2, key="qual_periodo")
    hoje = date.today()
    if periodo_sel == "Personalizado":
        data_ini = st.date_input("De", value=hoje - timedelta(days=365), key="qual_ini")
        data_fim = st.date_input("Ate", value=hoje, key="qual_fim")
    else:
        data_ini = hoje - timedelta(days=periodo_opcoes[periodo_sel])
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
    tipo_servico_opcoes = ["Todos", "Regular – Intermunicipal", "Regular – Metropolitano",
                           "Fretamento Intermunicipal", "Fretamento Metropolitano"]
    tipo_servico_sel = st.selectbox("Tipo de Servico", tipo_servico_opcoes, key="qual_tipo_srv")
    top_n = st.slider("Top N autos", min_value=10, max_value=50, value=20, step=5, key="qual_topn")

# ── Titulo ────────────────────────────────────────────────────────────────────
st.title("🔎 Dashboard de Qualidade e Fiscalizacao")
st.caption(f"Periodo: **{data_ini.strftime('%d/%m/%Y')}** a **{data_fim.strftime('%d/%m/%Y')}**")

if data_ini > data_fim:
    st.error("A data inicial deve ser anterior a data final.")
    st.stop()

_cat_list = cat_sel if cat_sel else cat_nomes
_tipo_srv = tipo_servico_sel if tipo_servico_sel != "Todos" else None

# ── KPIs ──────────────────────────────────────────────────────────────────────
total_rec, pontuacao_total, autos_unicos = query_kpis_qualidade(data_ini, data_fim, ger_id, perm_id, _cat_list, _tipo_srv)
perm_top_nome, perm_top_pts = query_top_permissionaria(data_ini, data_fim, ger_id, perm_id, _cat_list, _tipo_srv)
cat_top = query_top_categoria(data_ini, data_fim, ger_id, _cat_list, _tipo_srv)
sla_total, sla_ok = query_sla(data_ini, data_fim, ger_id)
sla_pct = round((sla_ok / sla_total * 100), 1) if sla_total > 0 else 0

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Reclamacoes", total_rec)
k2.metric("Pontuacao Total", f"{pontuacao_total:.2f}" if pontuacao_total else "0.00")
k3.metric("Autos Reclamados", autos_unicos)
k4.metric("Categoria Top", cat_top or "–")
k5.metric("SLA no Prazo", f"{sla_pct}%")

if perm_top_nome and perm_top_nome != "–":
    st.info(f"**Empresa com maior pontuacao acumulada:** {perm_top_nome} ({perm_top_pts} pts)")

st.divider()

# ── Evolucao Mensal ───────────────────────────────────────────────────────────
st.subheader("Evolucao Mensal de Reclamacoes")
evo_rows = query_evolucao_mensal(data_ini, data_fim, ger_id, _cat_list, _tipo_srv)
if evo_rows:
    df_evo = pd.DataFrame(evo_rows, columns=["mes", "total"])
    line = (alt.Chart(df_evo).mark_area(
        line={"color": "#1f77b4"},
        color=alt.Gradient(gradient="linear",
            stops=[alt.GradientStop(color="#1f77b4", offset=1), alt.GradientStop(color="rgba(31,119,180,0.1)", offset=0)],
            x1=1, x2=1, y1=1, y2=0,
    )).encode(x=alt.X("mes:N", title="Mes", sort=None, axis=alt.Axis(labelAngle=-45)),
              y=alt.Y("total:Q", title="Reclamacoes"), tooltip=["mes", "total"]).properties(height=280))
    points = alt.Chart(df_evo).mark_circle(size=50, color="#1f77b4").encode(x="mes:N", y="total:Q", tooltip=["mes", "total"])
    st.altair_chart(line + points, use_container_width=True)
else:
    st.info("Sem dados no periodo.")

st.divider()
col1, col2 = st.columns(2)

with col1:
    st.subheader(f"Top {top_n} Autos por Pontuacao")
    autos_rows = query_top_autos_pontuacao(data_ini, data_fim, ger_id, perm_id, _cat_list, _tipo_srv, top_n)
    if autos_rows:
        df_autos = pd.DataFrame([(r[0], float(r[1]) if r[1] else 0) for r in autos_rows], columns=["auto", "pontuacao"])
        st.altair_chart(alt.Chart(df_autos).mark_bar(cornerRadiusEnd=4)
            .encode(y=alt.Y("auto:N", sort="-x", title="Auto de Linha"), x=alt.X("pontuacao:Q"),
                    tooltip=["auto", alt.Tooltip("pontuacao:Q", format=".4f")])
            .properties(height=max(300, top_n * 18)), use_container_width=True)
    else:
        st.info("Sem dados no periodo.")

with col2:
    st.subheader("Empresas por Pontuacao")
    perm_rows = query_empresas_pontuacao(data_ini, data_fim, ger_id, perm_id, _cat_list, _tipo_srv)
    if perm_rows:
        df_perm = pd.DataFrame([(r[0], float(r[1]) if r[1] else 0) for r in perm_rows], columns=["empresa", "pontuacao"])
        bars = alt.Chart(df_perm).mark_bar(cornerRadiusEnd=4, color="#e67e22").encode(
            y=alt.Y("empresa:N", sort="-x"), x=alt.X("pontuacao:Q"),
            tooltip=["empresa", alt.Tooltip("pontuacao:Q", format=".4f")])
        text_labels = bars.mark_text(align="left", dx=3, fontSize=11).encode(text=alt.Text("pontuacao:Q", format=".2f"))
        st.altair_chart((bars + text_labels).properties(height=max(300, len(df_perm) * 22)), use_container_width=True)
    else:
        st.info("Sem dados.")

st.divider()
col3, col4 = st.columns(2)

with col3:
    st.subheader("Reclamacoes por Categoria")
    cat_rows = query_categorias_pizza(data_ini, data_fim, ger_id, _cat_list, _tipo_srv)
    if cat_rows:
        df_cat = pd.DataFrame(cat_rows, columns=["categoria", "total"])
        total_cat = df_cat["total"].sum()
        df_cat["percentual"] = (df_cat["total"] / total_cat * 100).round(1)
        pie = (alt.Chart(df_cat).mark_arc(innerRadius=50, outerRadius=130, stroke="#fff", strokeWidth=2)
            .encode(theta=alt.Theta("total:Q", stack=True),
                    color=alt.Color("categoria:N", scale=alt.Scale(scheme="tableau10"),
                                    legend=alt.Legend(orient="bottom", columns=2)),
                    tooltip=["categoria", "total", alt.Tooltip("percentual:Q", format=".1f", title="%")])
            .properties(height=320, width=320))
        st.altair_chart(pie, use_container_width=True)
    else:
        st.info("Sem dados.")

with col4:
    st.subheader("Top 20 Cidades")
    tipo_cidade = st.radio("Filtrar por:", ["Embarque", "Desembarque", "Ambos"], horizontal=True, key="tipo_cidade")
    cid_rows = query_cidades(data_ini, data_fim, ger_id, _tipo_srv, tipo_cidade)
    if cid_rows:
        df_cid = pd.DataFrame(cid_rows, columns=["cidade", "total"])
        st.altair_chart(alt.Chart(df_cid).mark_bar(cornerRadiusEnd=4, color="#1abc9c")
            .encode(y=alt.Y("cidade:N", sort="-x"), x=alt.X("total:Q"), tooltip=["cidade", "total"])
            .properties(height=max(280, len(df_cid) * 18)), use_container_width=True)
    else:
        st.info("Sem dados de cidades.")

st.divider()
st.subheader("Mapa de Calor: Categorias x Empresas")
heat_rows = query_heatmap_cat_empresa(data_ini, data_fim, ger_id, perm_id, _cat_list, _tipo_srv)
if heat_rows:
    df_heat = pd.DataFrame(heat_rows, columns=["empresa", "categoria", "count"])
    top_empresas = df_heat.groupby("empresa")["count"].sum().nlargest(15).index.tolist()
    df_heat = df_heat[df_heat["empresa"].isin(top_empresas)]
    heatmap = (alt.Chart(df_heat).mark_rect(cornerRadius=3)
        .encode(x=alt.X("categoria:N", axis=alt.Axis(labelAngle=-45)),
                y=alt.Y("empresa:N", sort="-x"),
                color=alt.Color("count:Q", scale=alt.Scale(scheme="orangered")),
                tooltip=["empresa", "categoria", "count"])
        .properties(height=max(300, len(top_empresas) * 25)))
    text_heat = (alt.Chart(df_heat).mark_text(fontSize=11, color="white", fontWeight="bold")
        .encode(x="categoria:N", y=alt.Y("empresa:N", sort="-x"), text="count:Q",
                opacity=alt.condition(alt.datum.count > 0, alt.value(1), alt.value(0))))
    st.altair_chart(heatmap + text_heat, use_container_width=True)
else:
    st.info("Sem dados para o heatmap.")

st.divider()
st.subheader("Tendencia Mensal por Empresa")
trend_rows = query_tendencia_empresa(data_ini, data_fim, ger_id, perm_id, _cat_list, _tipo_srv)
if trend_rows:
    df_trend = pd.DataFrame(trend_rows, columns=["mes", "empresa", "total"])
    top_emp_trend = df_trend.groupby("empresa")["total"].sum().nlargest(8).index.tolist()
    df_trend = df_trend[df_trend["empresa"].isin(top_emp_trend)]
    area_chart = (alt.Chart(df_trend).mark_area(opacity=0.7, interpolate="monotone")
        .encode(x=alt.X("mes:N", sort=None, axis=alt.Axis(labelAngle=-45)),
                y=alt.Y("total:Q", stack="zero"),
                color=alt.Color("empresa:N", scale=alt.Scale(scheme="tableau10"),
                                legend=alt.Legend(orient="bottom", columns=2)),
                tooltip=["mes", "empresa", "total"])
        .properties(height=350))
    st.altair_chart(area_chart, use_container_width=True)
else:
    st.info("Sem dados para tendencia.")

st.divider()
st.subheader("Tabela Analitica de Autos")
tabela_df = query_tabela_analitica(data_ini, data_fim, ger_id, perm_id, _cat_list, _tipo_srv)
if tabela_df is not None and not tabela_df.empty:
    st.dataframe(tabela_df, use_container_width=True, hide_index=True)
    c_dl1, _ = st.columns([1, 3])
    c_dl1.download_button(
        label="Exportar Excel",
        data=to_excel(tabela_df),
        file_name=f"autos_pontuacao_{data_ini}_{data_fim}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )
else:
    st.info("Sem dados de autos no periodo.")
