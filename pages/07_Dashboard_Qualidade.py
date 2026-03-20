"""Dashboard de Qualidade / Fiscalizacao - autos, permissionarias, categorias e cidades."""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import altair as alt
import math
from datetime import date, timedelta
from io import BytesIO
from sqlalchemy import text

import auth
from auth import usuario_logado
from database.connection import get_session
from models import Gerencia, Categoria, Permissionaria

st.set_page_config(page_title="Dashboard Qualidade", page_icon="🔎", layout="wide")
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
    st.markdown("### Filtros")

    def _load(model, filtro_ativo=True):
        s = get_session()
        try:
            q = s.query(model)
            if filtro_ativo and hasattr(model, "ativo"):
                q = q.filter_by(ativo=True)
            return q.order_by(model.nome).all()
        finally:
            s.close()

    st.markdown("**Periodo**")
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

    ger_list = _load(Gerencia)
    ger_opcoes = ["Todas"] + [g.nome for g in ger_list]
    ger_sel = st.selectbox("Gerencia", ger_opcoes, key="qual_ger")
    ger_id = next((g.id for g in ger_list if g.nome == ger_sel), None)

    cat_list = _load(Categoria)
    cat_nomes = [c.nome for c in cat_list]
    cat_sel = st.multiselect("Categorias", cat_nomes, default=cat_nomes, key="qual_cat")

    perm_list = _load(Permissionaria, filtro_ativo=False)
    perm_opcoes = ["Todas"] + [p.nome for p in perm_list]
    perm_sel = st.selectbox("Permissionaria", perm_opcoes, key="qual_perm")
    perm_id = next((p.id for p in perm_list if p.nome == perm_sel), None)

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

# ── Helpers ───────────────────────────────────────────────────────────────────
def _exec(sql, params=None):
    s = get_session()
    try:
        return s.execute(text(sql), params or {}).fetchall()
    finally:
        s.close()

_cat_list = cat_sel if cat_sel else cat_nomes
_ger_join = "JOIN usuarios usr ON usr.id = ot.tecnico_id" if ger_id else ""
_ger_where = "AND usr.gerencia_id = :ger_id" if ger_id else ""
_ger_ot = "JOIN ouvidoria_tecnicos ot ON ot.ouvidoria_id = o.id" if ger_id else ""
_tipo_srv_where = "AND al.tipo::text = :tipo_servico" if tipo_servico_sel != "Todos" else ""
_tipo_srv_rec_where = "AND r.tipo_servico::text = :tipo_servico" if tipo_servico_sel != "Todos" else ""

base_params = {
    "ini": data_ini,
    "fim": data_fim,
    "ger_id": ger_id,
    "perm_id": perm_id,
    "cats": _cat_list,
    "tipo_servico": tipo_servico_sel if tipo_servico_sel != "Todos" else None,
}

# ── KPIs ──────────────────────────────────────────────────────────────────────
kpi_sql = f"""
    SELECT
        COUNT(DISTINCT r.id) AS total_rec,
        COALESCE(SUM(ra.pontuacao), 0) AS pontuacao_total,
        COUNT(DISTINCT al.id) AS autos_unicos
    FROM reclamacoes r
    JOIN ouvidorias o ON o.id = r.ouvidoria_id
    LEFT JOIN reclamacao_autos ra ON ra.reclamacao_id = r.id
    LEFT JOIN autos_linha al ON al.id = ra.auto_id
    LEFT JOIN categorias cat ON cat.id = r.categoria_id
    {_ger_ot}
    {_ger_join}
    WHERE o.criado_em::date BETWEEN :ini AND :fim
    {_ger_where}
    {_tipo_srv_where}
    {"AND al.permissionaria_id = :perm_id" if perm_id else ""}
    {"AND cat.nome = ANY(:cats)" if cat_sel else ""}
"""
kpi_row = _exec(kpi_sql, base_params)
total_rec = int(kpi_row[0][0]) if kpi_row else 0
pontuacao_total = float(kpi_row[0][1]) if kpi_row else 0.0
autos_unicos = int(kpi_row[0][2]) if kpi_row else 0

# Empresa com maior pontuacao (nome completo)
perm_top_sql = f"""
    SELECT p.nome, ROUND(COALESCE(SUM(ra.pontuacao), 0)::numeric, 2) AS pts
    FROM reclamacao_autos ra
    JOIN autos_linha al ON al.id = ra.auto_id
    JOIN permissionarias p ON p.id = al.permissionaria_id
    JOIN reclamacoes r ON r.id = ra.reclamacao_id
    JOIN ouvidorias o ON o.id = r.ouvidoria_id
    LEFT JOIN categorias cat ON cat.id = r.categoria_id
    {_ger_ot}
    {_ger_join}
    WHERE o.criado_em::date BETWEEN :ini AND :fim
    {_ger_where}
    {_tipo_srv_where}
    {"AND al.permissionaria_id = :perm_id" if perm_id else ""}
    {"AND cat.nome = ANY(:cats)" if cat_sel else ""}
    GROUP BY p.nome ORDER BY pts DESC LIMIT 1
"""
perm_top_rows = _exec(perm_top_sql, base_params)
perm_top_nome = perm_top_rows[0][0] if perm_top_rows else "–"
perm_top_pts = float(perm_top_rows[0][1]) if perm_top_rows else 0

# Categoria mais reclamada
cat_top_sql = f"""
    SELECT cat.nome, COUNT(r.id) AS total
    FROM reclamacoes r
    JOIN ouvidorias o ON o.id = r.ouvidoria_id
    JOIN categorias cat ON cat.id = r.categoria_id
    {_ger_ot}
    {_ger_join}
    WHERE o.criado_em::date BETWEEN :ini AND :fim
    {_ger_where}
    {_tipo_srv_rec_where}
    {"AND cat.nome = ANY(:cats)" if cat_sel else ""}
    GROUP BY cat.nome ORDER BY total DESC LIMIT 1
"""
cat_top_rows = _exec(cat_top_sql, base_params)
cat_top = cat_top_rows[0][0] if cat_top_rows else "–"

# SLA — ouvidorias respondidas dentro do prazo
sla_sql = f"""
    SELECT
        COUNT(DISTINCT o.id) AS total,
        COUNT(DISTINCT o.id) FILTER (
            WHERE o.status::text = 'Concluido' AND o.atualizado_em::date <= o.prazo
        ) AS dentro_prazo
    FROM ouvidorias o
    {_ger_ot}
    {_ger_join}
    WHERE o.criado_em::date BETWEEN :ini AND :fim
    {_ger_where}
"""
sla_rows = _exec(sla_sql, base_params)
sla_total = int(sla_rows[0][0]) if sla_rows else 0
sla_ok = int(sla_rows[0][1]) if sla_rows else 0
sla_pct = round((sla_ok / sla_total * 100), 1) if sla_total > 0 else 0

# ── Display KPIs ──────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Reclamacoes", total_rec)
k2.metric("Pontuacao Total", f"{pontuacao_total:.2f}")
k3.metric("Autos Reclamados", autos_unicos)
k4.metric("Categoria Top", cat_top)
k5.metric("SLA no Prazo", f"{sla_pct}%")

# Empresa destaque em callout (nome completo, sem truncar)
if perm_top_nome != "–":
    st.info(f"**Empresa com maior pontuacao acumulada:** {perm_top_nome} ({perm_top_pts} pts)")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECAO 1 — Evolucao Temporal
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("Evolucao Mensal de Reclamacoes")
evo_sql = f"""
    SELECT TO_CHAR(DATE_TRUNC('month', o.criado_em), 'YYYY-MM') AS mes,
           COUNT(r.id) AS total
    FROM reclamacoes r
    JOIN ouvidorias o ON o.id = r.ouvidoria_id
    LEFT JOIN categorias cat ON cat.id = r.categoria_id
    {_ger_ot}
    {_ger_join}
    WHERE o.criado_em::date BETWEEN :ini AND :fim
    {_ger_where}
    {_tipo_srv_rec_where}
    {"AND cat.nome = ANY(:cats)" if cat_sel else ""}
    GROUP BY mes ORDER BY mes
"""
evo_rows = _exec(evo_sql, base_params)
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
    autos_sql = f"""
        SELECT al.numero, COALESCE(SUM(ra.pontuacao), 0) AS pts, p.nome AS empresa
        FROM reclamacao_autos ra
        JOIN autos_linha al ON al.id = ra.auto_id
        LEFT JOIN permissionarias p ON p.id = al.permissionaria_id
        JOIN reclamacoes r ON r.id = ra.reclamacao_id
        JOIN ouvidorias o ON o.id = r.ouvidoria_id
        LEFT JOIN categorias cat ON cat.id = r.categoria_id
        {_ger_ot}
        {_ger_join}
        WHERE o.criado_em::date BETWEEN :ini AND :fim
        {_ger_where}
        {_tipo_srv_where}
        {"AND al.permissionaria_id = :perm_id" if perm_id else ""}
        {"AND cat.nome = ANY(:cats)" if cat_sel else ""}
        GROUP BY al.numero, p.nome ORDER BY pts DESC LIMIT :topn
    """
    autos_rows = _exec(autos_sql, {**base_params, "topn": top_n})
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
    perm_sql = f"""
        SELECT p.nome AS empresa, COALESCE(SUM(ra.pontuacao), 0) AS pts,
               COUNT(DISTINCT r.id) AS num_reclamacoes
        FROM reclamacao_autos ra
        JOIN autos_linha al ON al.id = ra.auto_id
        JOIN permissionarias p ON p.id = al.permissionaria_id
        JOIN reclamacoes r ON r.id = ra.reclamacao_id
        JOIN ouvidorias o ON o.id = r.ouvidoria_id
        LEFT JOIN categorias cat ON cat.id = r.categoria_id
        {_ger_ot}
        {_ger_join}
        WHERE o.criado_em::date BETWEEN :ini AND :fim
        {_ger_where}
        {_tipo_srv_where}
        {"AND al.permissionaria_id = :perm_id" if perm_id else ""}
        {"AND cat.nome = ANY(:cats)" if cat_sel else ""}
        GROUP BY p.nome ORDER BY pts DESC LIMIT 20
    """
    perm_rows = _exec(perm_sql, base_params)
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
    cat_sql = f"""
        SELECT COALESCE(cat.nome, '(sem categoria)') AS categoria, COUNT(r.id) AS total
        FROM reclamacoes r
        JOIN ouvidorias o ON o.id = r.ouvidoria_id
        LEFT JOIN categorias cat ON cat.id = r.categoria_id
        {_ger_ot}
        {_ger_join}
        WHERE o.criado_em::date BETWEEN :ini AND :fim
        {_ger_where}
        {_tipo_srv_rec_where}
        {"AND cat.nome = ANY(:cats)" if cat_sel else ""}
        GROUP BY categoria ORDER BY total DESC
    """
    cat_rows = _exec(cat_sql, base_params)
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

    if tipo_cidade == "Embarque":
        cid_sql = f"""
            SELECT r.local_embarque AS cidade, COUNT(*) AS total
            FROM reclamacoes r
            JOIN ouvidorias o ON o.id = r.ouvidoria_id
            {_ger_ot}
            {_ger_join}
            WHERE o.criado_em::date BETWEEN :ini AND :fim
              AND r.local_embarque IS NOT NULL AND r.local_embarque <> ''
            {_ger_where}
            {_tipo_srv_rec_where}
            GROUP BY cidade ORDER BY total DESC LIMIT 20
        """
    elif tipo_cidade == "Desembarque":
        cid_sql = f"""
            SELECT r.local_desembarque AS cidade, COUNT(*) AS total
            FROM reclamacoes r
            JOIN ouvidorias o ON o.id = r.ouvidoria_id
            {_ger_ot}
            {_ger_join}
            WHERE o.criado_em::date BETWEEN :ini AND :fim
              AND r.local_desembarque IS NOT NULL AND r.local_desembarque <> ''
            {_ger_where}
            GROUP BY cidade ORDER BY total DESC LIMIT 20
        """
    else:
        cid_sql = f"""
            SELECT cidade, SUM(total) AS total FROM (
                SELECT r.local_embarque AS cidade, COUNT(*) AS total
                FROM reclamacoes r
                JOIN ouvidorias o ON o.id = r.ouvidoria_id
                {_ger_ot}
                {_ger_join}
                WHERE o.criado_em::date BETWEEN :ini AND :fim
                  AND r.local_embarque IS NOT NULL AND r.local_embarque <> ''
                {_ger_where}
                GROUP BY r.local_embarque
                UNION ALL
                SELECT r.local_desembarque AS cidade, COUNT(*) AS total
                FROM reclamacoes r
                JOIN ouvidorias o ON o.id = r.ouvidoria_id
                {_ger_ot}
                {_ger_join}
                WHERE o.criado_em::date BETWEEN :ini AND :fim
                  AND r.local_desembarque IS NOT NULL AND r.local_desembarque <> ''
                {_ger_where}
                {_tipo_srv_rec_where}
                GROUP BY r.local_desembarque
            ) sub
            GROUP BY cidade ORDER BY total DESC LIMIT 20
        """

    cid_rows = _exec(cid_sql, base_params)
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

heat_sql = f"""
    SELECT p.nome AS empresa, COALESCE(cat.nome, '(sem)') AS categoria, COUNT(r.id) AS total
    FROM reclamacoes r
    JOIN ouvidorias o ON o.id = r.ouvidoria_id
    JOIN reclamacao_autos ra ON ra.reclamacao_id = r.id
    JOIN autos_linha al ON al.id = ra.auto_id
    JOIN permissionarias p ON p.id = al.permissionaria_id
    LEFT JOIN categorias cat ON cat.id = r.categoria_id
    {_ger_ot}
    {_ger_join}
    WHERE o.criado_em::date BETWEEN :ini AND :fim
    {_ger_where}
    {_tipo_srv_where}
    {"AND al.permissionaria_id = :perm_id" if perm_id else ""}
    {"AND cat.nome = ANY(:cats)" if cat_sel else ""}
    GROUP BY p.nome, categoria ORDER BY total DESC
"""
heat_rows = _exec(heat_sql, base_params)
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

trend_sql = f"""
    SELECT TO_CHAR(DATE_TRUNC('month', o.criado_em), 'YYYY-MM') AS mes,
           p.nome AS empresa,
           COUNT(r.id) AS total
    FROM reclamacoes r
    JOIN ouvidorias o ON o.id = r.ouvidoria_id
    JOIN reclamacao_autos ra ON ra.reclamacao_id = r.id
    JOIN autos_linha al ON al.id = ra.auto_id
    JOIN permissionarias p ON p.id = al.permissionaria_id
    LEFT JOIN categorias cat ON cat.id = r.categoria_id
    {_ger_ot}
    {_ger_join}
    WHERE o.criado_em::date BETWEEN :ini AND :fim
    {_ger_where}
    {_tipo_srv_where}
    {"AND al.permissionaria_id = :perm_id" if perm_id else ""}
    {"AND cat.nome = ANY(:cats)" if cat_sel else ""}
    GROUP BY mes, p.nome ORDER BY mes
"""
trend_rows = _exec(trend_sql, base_params)
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

tabela_sql = f"""
    SELECT al.numero AS "Auto", al.tipo::text AS "Tipo",
           al.itinerario AS "Itinerario",
           COALESCE(p.nome, '–') AS "Empresa",
           COALESCE(al.cidade_inicial, '–') AS "Cidade Inicial",
           COALESCE(al.cidade_final, '–') AS "Cidade Final",
           COUNT(DISTINCT r.id) AS "Reclamacoes",
           ROUND(COALESCE(SUM(ra.pontuacao), 0)::numeric, 4) AS "Pontuacao"
    FROM reclamacao_autos ra
    JOIN autos_linha al ON al.id = ra.auto_id
    LEFT JOIN permissionarias p ON p.id = al.permissionaria_id
    JOIN reclamacoes r ON r.id = ra.reclamacao_id
    JOIN ouvidorias o ON o.id = r.ouvidoria_id
    LEFT JOIN categorias cat ON cat.id = r.categoria_id
    {_ger_ot}
    {_ger_join}
    WHERE o.criado_em::date BETWEEN :ini AND :fim
    {_ger_where}
    {_tipo_srv_where}
    {"AND al.permissionaria_id = :perm_id" if perm_id else ""}
    {"AND cat.nome = ANY(:cats)" if cat_sel else ""}
    GROUP BY al.numero, al.tipo, al.itinerario, p.nome, al.cidade_inicial, al.cidade_final
    ORDER BY "Pontuacao" DESC
"""
tabela_rows = _exec(tabela_sql, base_params)
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

    def _to_excel(df):
        buf = BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Autos")
        return buf.getvalue()

    c_dl1, c_dl2, _ = st.columns([1, 1, 3])
    c_dl1.download_button(
        label="Exportar Excel",
        data=_to_excel(df_tabela),
        file_name=f"autos_pontuacao_{data_ini}_{data_fim}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )
else:
    st.info("Sem dados de autos no periodo.")
