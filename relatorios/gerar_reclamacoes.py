#!/usr/bin/env python3
"""
Gerador de Relatórios HTML de Reclamações – ARTESP

Execução (a partir da raiz do projeto):
    python relatorios/gerar_reclamacoes.py

Saída:
    relatorios/relatorio_reclamacoes_2025.html
    relatorios/relatorio_reclamacoes_2026.html

Filtro exclusivo: Categoria = "RECLAMAÇÃO"

Seções:
  1. Sistema Regular Metropolitano
  2. Sistema Regular Intermunicipal
  3. Fretamento (Metropolitano + Intermunicipal unificados)
"""

import os
import sys

# garante que a raiz do projeto está no path ao executar diretamente
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from repositories.relatorios.reclamacoes_repo import (
    query_empresas_pontuacao,
    query_evolucao_mensal,
    query_heatmap_assunto_empresa,
    query_kpis_fretamento,
    query_kpis_sistema,
    query_pizza_assuntos,
    query_top15_autos_pontuacao,
    query_top15_embarques,
)

# ─── tipos de serviço ─────────────────────────────────────────────────────────

TIPO_REG_METRO = "Regular – Metropolitano"
TIPO_REG_INTER = "Regular – Intermunicipal"
TIPO_FRET_METRO = "Fretamento Metropolitano"
TIPO_FRET_INTER = "Fretamento Intermunicipal"

TIPOS_FRETAMENTO = [TIPO_FRET_METRO, TIPO_FRET_INTER]

# ─── paleta ───────────────────────────────────────────────────────────────────

BLUE_DARK = "#003F7F"
BLUE_MID = "#005FA3"
CHART_COLORS = px.colors.qualitative.Set2

MES_PT = {
    "01": "Jan", "02": "Fev", "03": "Mar", "04": "Abr",
    "05": "Mai", "06": "Jun", "07": "Jul", "08": "Ago",
    "09": "Set", "10": "Out", "11": "Nov", "12": "Dez",
}

# ─── helpers ──────────────────────────────────────────────────────────────────

def _fmt(v: int) -> str:
    return f"{v:,}".replace(",", ".")


def _mes_label(s: str) -> str:
    """'2025-03' → 'Mar/25'"""
    try:
        ano, m = s.split("-")
        return f"{MES_PT.get(m, m)}/{ano[2:]}"
    except Exception:
        return s


# ─── configuração padrão dos gráficos ────────────────────────────────────────

_EXPORT = {"full_html": False, "include_plotlyjs": False, "config": {"displayModeBar": False}}

_LAYOUT = dict(
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(family="Segoe UI, Arial, sans-serif", size=12),
)

def _empty() -> str:
    return '<div class="empty-chart"><p>Sem dados para o período selecionado.</p></div>'


# ─── gráficos ─────────────────────────────────────────────────────────────────

def chart_evolucao(rows: list, titulo: str) -> str:
    if not rows:
        return _empty()
    df = pd.DataFrame(rows, columns=["mes", "total"])
    df["label"] = df["mes"].apply(_mes_label)
    labels = df["label"].tolist()
    totais = df["total"].tolist()
    fig = go.Figure(go.Scatter(
        x=labels, y=totais,
        mode="lines+markers+text",
        line=dict(shape="spline", width=2.5, color=BLUE_DARK),
        marker=dict(size=8, color=BLUE_DARK),
        text=totais, textposition="top center",
    ))
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=14, color=BLUE_DARK)),
        xaxis_title="Mês", yaxis_title="Reclamações",
        yaxis=dict(gridcolor="#e5e7eb", rangemode="tozero"),
        height=380, margin=dict(t=55, b=45, l=55, r=30),
        **_LAYOUT,
    )
    return fig.to_html(**_EXPORT)


def chart_pizza(rows: list, titulo: str) -> str:
    if not rows:
        return _empty()
    df = pd.DataFrame(rows, columns=["assunto", "total"])
    fig = go.Figure(go.Pie(
        labels=df["assunto"].tolist(),
        values=df["total"].tolist(),
        hole=0.35,
        textposition="inside",
        textinfo="percent",
        marker=dict(colors=CHART_COLORS),
    ))
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=14, color=BLUE_DARK)),
        showlegend=True,
        legend=dict(orientation="v", x=1.02, y=0.5, font=dict(size=12)),
        height=560, margin=dict(t=55, b=20, l=20, r=220),
        **_LAYOUT,
    )
    return fig.to_html(**_EXPORT)


def chart_empresas(rows: list, titulo: str) -> str:
    if not rows:
        return _empty()
    df = pd.DataFrame(rows, columns=["empresa", "pts"]).sort_values("pts", ascending=True).reset_index(drop=True)
    fig = go.Figure(go.Bar(
        x=df["pts"].tolist(), y=df["empresa"].tolist(), orientation="h",
        marker_color=BLUE_DARK,
        text=df["pts"].apply(lambda v: f"{v:.2f}").tolist(),
        textposition="outside", cliponaxis=False,
    ))
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=14, color=BLUE_DARK)),
        xaxis_title="Pontuação", xaxis=dict(gridcolor="#e5e7eb"),
        height=max(350, len(df) * 30 + 100),
        margin=dict(t=55, b=40, l=220, r=90),
        **_LAYOUT,
    )
    return fig.to_html(**_EXPORT)


_ASSUNTO_EXCLUIR_HEAT = "TRANSPORTE IRREGULAR / CLANDESTINO"


def chart_heatmap(rows: list, titulo: str) -> str:
    if not rows:
        return _empty()
    df = pd.DataFrame(rows, columns=["empresa", "assunto", "pts"])
    df = df[df["assunto"] != _ASSUNTO_EXCLUIR_HEAT]
    # Top 10 empresas por pontuação total; todos os assuntos
    top_emp = df.groupby("empresa")["pts"].sum().nlargest(10).index.tolist()
    df_f = df[df["empresa"].isin(top_emp)]
    if df_f.empty:
        return _empty()
    pivot = df_f.pivot_table(
        index="assunto", columns="empresa", values="pts",
        aggfunc="sum", fill_value=0,
    )
    col_order = [c for c in top_emp if c in pivot.columns]
    pivot = pivot.reindex(columns=col_order)
    # Escala verde (0) → amarelo (médio) → vermelho (alto)
    colorscale = [[0, "#2ecc71"], [0.5, "#f1c40f"], [1, "#e74c3c"]]
    text_annot = [[f"{v:.1f}" for v in row] for row in pivot.values.tolist()]
    fig = go.Figure(go.Heatmap(
        z=pivot.values.tolist(),
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        colorscale=colorscale,
        text=text_annot,
        texttemplate="%{text}",
        hoverongaps=False,
        colorbar=dict(title="Pts"),
    ))
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=14, color=BLUE_DARK)),
        xaxis=dict(tickangle=-40, side="bottom"),
        height=max(480, len(pivot.index) * 46 + 220),
        margin=dict(t=55, b=160, l=260, r=40),
        **_LAYOUT,
    )
    return fig.to_html(**_EXPORT)


def chart_top_autos(rows: list, titulo: str) -> str:
    if not rows:
        return _empty()
    df = pd.DataFrame(rows, columns=["auto", "pts"]).sort_values("pts", ascending=True).reset_index(drop=True)
    fig = go.Figure(go.Bar(
        x=df["pts"].tolist(), y=df["auto"].astype(str).tolist(), orientation="h",
        marker_color=BLUE_MID,
        text=df["pts"].apply(lambda v: f"{v:.2f}").tolist(),
        textposition="outside", cliponaxis=False,
    ))
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=14, color=BLUE_DARK)),
        xaxis_title="Pontuação", xaxis=dict(gridcolor="#e5e7eb"),
        yaxis_title="Auto",
        height=500, margin=dict(t=55, b=40, l=90, r=90),
        **_LAYOUT,
    )
    return fig.to_html(**_EXPORT)


def chart_embarques(rows: list, titulo: str) -> str:
    if not rows:
        return _empty()
    df = pd.DataFrame(rows, columns=["local", "total"]).sort_values("total", ascending=True).reset_index(drop=True)
    fig = go.Figure(go.Bar(
        x=df["total"].tolist(), y=df["local"].tolist(), orientation="h",
        marker_color=BLUE_DARK,
        text=df["total"].tolist(), textposition="outside", cliponaxis=False,
    ))
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=14, color=BLUE_DARK)),
        xaxis_title="Reclamações", xaxis=dict(gridcolor="#e5e7eb"),
        height=520, margin=dict(t=55, b=40, l=230, r=90),
        **_LAYOUT,
    )
    return fig.to_html(**_EXPORT)


# ─── blocos de seção HTML ─────────────────────────────────────────────────────

def _kpi_card(label: str, value: str, sub: str = "") -> str:
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    return f"""
    <div class="col-half">
      <div class="kpi-card">
        <div class="kpi-value">{value}</div>
        <div class="kpi-label">{label}</div>
        {sub_html}
      </div>
    </div>"""


def _wrap(html: str) -> str:
    return f'<div class="chart-wrap">{html}</div>'


def section_sistema(titulo: str, icon: str, ano: int, tipos: list[str]) -> str:
    total, top_ass, top_cnt = query_kpis_sistema(ano, tipos)
    kpis = (
        _kpi_card("Total de Reclamações", _fmt(total))
        + _kpi_card("Assunto Mais Reclamado", top_ass, f"{_fmt(top_cnt)} ocorrências")
    )
    evo   = chart_evolucao(query_evolucao_mensal(ano, tipos), "Evolução Mensal de Reclamações")
    pizza = chart_pizza(query_pizza_assuntos(ano, tipos), "Reclamações por Assunto")
    emps  = chart_empresas(query_empresas_pontuacao(ano, tipos), "Empresas por Pontuação — Maior → Menor")
    heat  = chart_heatmap(query_heatmap_assunto_empresa(ano, tipos),
                          "Mapa de Calor: Pontuação por Assunto × Empresa (Top 10 Empresas)")
    autos = chart_top_autos(query_top15_autos_pontuacao(ano, tipos),
                            "Top 15 Autos por Pontuação de Reclamação")

    return f"""
  <section class="report-section">
    <div class="sec-header">
      <span class="sec-icon">{icon}</span>
      <h2>{titulo}</h2>
    </div>
    <div class="row g-3 mb-4">{kpis}</div>
    <div class="row g-3 mb-4">
      <div class="col-12">{_wrap(evo)}</div>
    </div>
    <div class="row g-3 mb-4">
      <div class="col-12">{_wrap(pizza)}</div>
    </div>
    <div class="row g-3 mb-4">
      <div class="col-12">{_wrap(emps)}</div>
    </div>
    <div class="row g-3 mb-4">
      <div class="col-12">{_wrap(heat)}</div>
    </div>
    <div class="row g-3">
      <div class="col-12">{_wrap(autos)}</div>
    </div>
  </section>"""


def section_fretamento(ano: int) -> str:
    total, top_ass, top_cnt = query_kpis_fretamento(ano, TIPOS_FRETAMENTO)
    kpis = (
        _kpi_card("Total de Reclamações", _fmt(total))
        + _kpi_card("Assunto Mais Reclamado", top_ass, f"{_fmt(top_cnt)} ocorrências")
    )
    evo     = chart_evolucao(query_evolucao_mensal(ano, TIPOS_FRETAMENTO),
                             "Evolução Mensal de Reclamações — Fretamento")
    pizza   = chart_pizza(query_pizza_assuntos(ano, TIPOS_FRETAMENTO),
                          "Reclamações por Assunto — Fretamento")
    embarq  = chart_embarques(query_top15_embarques(ano, TIPOS_FRETAMENTO),
                              "Top 15 Locais de Embarque Mais Reclamados")

    return f"""
  <section class="report-section">
    <div class="sec-header">
      <span class="sec-icon">🚐</span>
      <h2>Fretamento <span class="badge-sub">Metropolitano + Intermunicipal</span></h2>
    </div>
    <div class="row g-3 mb-4">{kpis}</div>
    <div class="row g-3 mb-4">
      <div class="col-12">{_wrap(evo)}</div>
    </div>
    <div class="row g-3 mb-4">
      <div class="col-12">{_wrap(pizza)}</div>
    </div>
    <div class="row g-3">
      <div class="col-12">{_wrap(embarq)}</div>
    </div>
  </section>"""


# ─── CSS inline ───────────────────────────────────────────────────────────────

_CSS = """
*, *::before, *::after { box-sizing: border-box; }
body {
  font-family: 'Segoe UI', Arial, sans-serif;
  background: #f0f2f5;
  color: #2d3748;
  margin: 0;
}
.page-header {
  background: linear-gradient(135deg, #003F7F 0%, #005FA3 100%);
  color: #fff;
  padding: 2.5rem 1.5rem 2rem;
}
.page-header h1 { font-size: 1.9rem; font-weight: 800; margin: 0 0 .3rem; }
.page-header p  { margin: .2rem 0 0; opacity: .85; font-size: .93rem; }
.year-badge {
  display: inline-block;
  background: rgba(255,255,255,.2);
  border: 1px solid rgba(255,255,255,.4);
  padding: .4rem 1.2rem;
  border-radius: 20px;
  font-size: 1.4rem;
  font-weight: 700;
}
.total-pill {
  display: inline-block;
  background: rgba(255,255,255,.15);
  padding: .3rem 1rem;
  border-radius: 12px;
  font-size: .88rem;
  margin-top: .55rem;
}
.container { max-width: 1300px; margin: 0 auto; padding: 0 1.25rem; }
.report-section {
  background: #fff;
  border-radius: 14px;
  padding: 2rem 1.75rem;
  margin-bottom: 2rem;
  box-shadow: 0 2px 12px rgba(0,0,0,.07);
}
.sec-header {
  display: flex; align-items: center; gap: .75rem;
  border-bottom: 3px solid #003F7F;
  padding-bottom: 1rem; margin-bottom: 1.5rem;
}
.sec-icon { font-size: 1.8rem; line-height: 1; }
.sec-header h2 {
  font-size: 1.25rem; font-weight: 700; color: #003F7F; margin: 0;
  display: flex; align-items: center; gap: .6rem; flex-wrap: wrap;
}
.badge-sub {
  font-size: .72rem; font-weight: 600;
  background: #e8f0fe; color: #003F7F;
  padding: .2rem .6rem; border-radius: 8px;
}
.kpi-card {
  background: linear-gradient(135deg, #f8faff 0%, #e8f0fe 100%);
  border-left: 4px solid #003F7F;
  border-radius: 10px; padding: 1.1rem 1.2rem; height: 100%;
}
.kpi-value {
  font-size: 1.85rem; font-weight: 800; color: #003F7F;
  word-break: break-word; line-height: 1.15;
}
.kpi-label {
  font-size: .76rem; text-transform: uppercase;
  letter-spacing: .5px; color: #6b7280; margin-top: .3rem;
}
.kpi-sub { font-size: .8rem; color: #4b5563; margin-top: .2rem; }
.chart-wrap {
  background: #fff; border: 1px solid #e5e7eb;
  border-radius: 10px; padding: .75rem; overflow: hidden;
}
.empty-chart {
  display: flex; align-items: center; justify-content: center;
  height: 200px; color: #9ca3af; font-size: .95rem;
}
.page-footer {
  background: #003F7F; color: rgba(255,255,255,.7);
  text-align: center; padding: 1.2rem;
  font-size: .82rem; margin-top: .5rem;
}
/* grid utilitário (sem Bootstrap) */
.row { display: flex; flex-wrap: wrap; }
.g-3 { gap: 1rem; }
.g-3 > * { flex: 0 0 auto; }
.mb-4 { margin-bottom: 1.25rem !important; }
.col-12  { width: 100%; }
.col-sm-6 { width: calc(50% - .5rem); }
.col-md-4 { width: calc(33.333% - .667rem); }
.col-lg-5 { width: calc(41.666% - .5rem); }
.col-lg-7 { width: calc(58.333% - .5rem); }
.col-half { width: calc(50% - .5rem); }
.justify-content-center { justify-content: center; }
@media (max-width: 620px) {
  .col-half { width: 100%; }
  .kpi-value { font-size: 1.45rem; }
}
/* card de metodologia de pontuação */
.metodologia-card {
  background: #fffbeb;
  border: 1px solid #fcd34d;
  border-left: 5px solid #f59e0b;
  border-radius: 10px;
  padding: 1.25rem 1.5rem;
  margin-bottom: 2rem;
}
.metodologia-card h3 {
  font-size: 1rem;
  font-weight: 700;
  color: #92400e;
  margin: 0 0 .6rem;
}
.metodologia-card p {
  font-size: .88rem;
  color: #78350f;
  margin: .3rem 0;
  line-height: 1.55;
}
.metodologia-card .exemplo {
  display: inline-block;
  background: #fef3c7;
  border-radius: 6px;
  padding: .3rem .75rem;
  font-size: .83rem;
  color: #92400e;
  margin-top: .4rem;
}
"""


# ─── HTML completo ────────────────────────────────────────────────────────────

def build_html(ano: int) -> str:
    print(f"\nColetando dados {ano}...")
    s_metro = section_sistema("Sistema Regular Metropolitano", "🚌", ano, [TIPO_REG_METRO])
    print("  OK Regular Metropolitano")
    s_inter = section_sistema("Sistema Regular Intermunicipal", "🚎", ano, [TIPO_REG_INTER])
    print("  OK Regular Intermunicipal")
    s_fret  = section_fretamento(ano)
    print("  OK Fretamento")

    hoje = date.today().strftime("%d/%m/%Y")

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Relatório de Reclamações {ano} – ARTESP</title>
  <script src="https://cdn.plot.ly/plotly-2.26.0.min.js" charset="utf-8"></script>
  <style>{_CSS}</style>
</head>
<body>

<header class="page-header">
  <div class="container" style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:1rem">
    <div>
      <h1>Relatório de Reclamações</h1>
      <p>Agência de Transporte do Estado de São Paulo – ARTESP</p>
      <p style="opacity:.7;font-size:.82rem;margin-top:.4rem">
        Filtro: Categoria <strong>RECLAMAÇÃO</strong> &nbsp;·&nbsp; Gerado em {hoje}
      </p>
    </div>
    <div style="text-align:right">
      <div class="year-badge">{ano}</div>
    </div>
  </div>
</header>

<div class="container" style="padding-top:2rem;padding-bottom:2rem">

  <div class="metodologia-card">
    <h3>ℹ️ Metodologia de Pontuação de Reclamações por Auto</h3>
    <p>
      Os dados históricos da planilha de controle da ARTESP <strong>não possuem vinculação direta entre o auto de linha
      e a ouvidoria/reclamação</strong>. Para viabilizar a análise por veículo, foi adotado um
      <strong>sistema de pontuação proporcional</strong>:
    </p>
    <p>
      Quando uma reclamação envolve um trecho (Cidade&nbsp;A → Cidade&nbsp;B), ela é distribuída igualmente entre
      <strong>todos os autos que atendem àquele trecho</strong>. Cada auto recebe uma fração de
      <strong>1 ÷ nº de autos do trecho</strong> como pontuação.
    </p>
    <span class="exemplo">
      Exemplo: autos 001, 002 e 003 atendem o trecho A→B
      → cada auto recebe <strong>0,33 pts</strong> pela reclamação.
    </span>
    <p style="margin-top:.6rem">
      A <strong>pontuação acumulada</strong> reflete o volume ponderado de reclamações associadas a cada auto ou empresa.
      Quanto maior a pontuação, maior o histórico de reclamações relacionadas àquele veículo/operador.
    </p>
  </div>

  {s_metro}
  {s_inter}
  {s_fret}
</div>

<footer class="page-footer">
  Relatório de Reclamações {ano} &nbsp;·&nbsp; ARTESP &nbsp;·&nbsp; Gerado em {hoje}
</footer>

</body>
</html>"""


# ─── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    out_dir = os.path.dirname(os.path.abspath(__file__))
    for ano in [2025, 2026]:
        print(f"\n{'=' * 55}")
        html = build_html(ano)
        path = os.path.join(out_dir, f"relatorio_reclamacoes_{ano}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        kb = os.path.getsize(path) // 1024
        print(f"  Salvo: relatorios/relatorio_reclamacoes_{ano}.html  ({kb} KB)")

    print("\nPronto! Abra os arquivos .html no navegador.")


if __name__ == "__main__":
    main()
