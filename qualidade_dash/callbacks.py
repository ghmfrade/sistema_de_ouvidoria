"""Callbacks reativos do Dashboard de Qualidade — Visão Unificada."""

import pandas as pd
import dash_bootstrap_components as dbc
from dash import Input, Output, State, ctx, html
import plotly.graph_objects as go

from qualidade_dash import api_client as api
from qualidade_dash.layout import (
    LAYOUT_PLOTLY, NOMES_MESES, SERVICOS_REGULAR, SERVICOS_DEFAULT,
)

_COLORSCALE = [[0, "#2ecc71"], [0.5, "#f1c40f"], [1, "#e74c3c"]]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _tipo_servico_str(servicos: list[str] | None) -> str | None:
    """Converte lista de serviços para string comma-separated."""
    if not servicos:
        return None
    return ",".join(servicos)


def _tem_regular(servicos: list[str] | None) -> bool:
    """Verifica se algum tipo Regular está selecionado."""
    return any(s in SERVICOS_REGULAR for s in (servicos or []))


def _meses_str(meses: list[int] | None) -> str | None:
    if not meses:
        return None
    return ",".join(str(m) for m in meses)


def _fig_vazia(msg: str = "Sem dados para o período") -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        **LAYOUT_PLOTLY,
        annotations=[dict(text=msg, showarrow=False, xref="paper", yref="paper",
                          x=0.5, y=0.5, font=dict(size=14, color="#999"))],
    )
    return fig


def _barra_horizontal(nomes, valores, cor: str, n_items: int = 0,
                      xmax: float | None = None,
                      customdata=None, hovertemplate: str | None = None):
    """Barras horizontais com maior valor no topo."""
    height = max(400, n_items * 32 + 120)
    xaxis_cfg = dict(showgrid=True, gridcolor="#f0f0f0", gridwidth=1)
    if xmax:
        xaxis_cfg["range"] = [0, xmax * 1.08]

    fig = go.Figure(go.Bar(
        x=valores, y=nomes, orientation="h",
        marker_color=cor,
        customdata=customdata,
        hovertemplate=hovertemplate,
    ))
    fig.update_layout(
        **LAYOUT_PLOTLY,
        height=height,
        yaxis=dict(autorange="reversed", showgrid=False),
        xaxis=xaxis_cfg,
        margin=dict(t=30, b=40, l=220, r=20),
    )
    return fig


def _heatmap_empresa(dados: list[dict], zmax: float | None = None, sort_assuntos: list[str] | None = None) -> go.Figure:
    """Heatmap assunto × empresa com ordenação opcional por assunto."""
    if not dados:
        return _fig_vazia()

    df = pd.DataFrame(dados)

    # Se há assuntos de ordenação, priorizar esses e depois o resto
    if sort_assuntos:
        df_sort = df[df["assunto"].isin(sort_assuntos)]
        col_order = (df_sort.groupby("empresa")["pontuacao"].sum()
                           .sort_values(ascending=False).index.tolist())
        rest = [c for c in df.groupby("empresa")["pontuacao"].sum()
                              .sort_values(ascending=False).index if c not in col_order]
        col_order = col_order + rest
    else:
        col_order = df.groupby("empresa")["pontuacao"].sum().sort_values(ascending=False).index.tolist()

    pivot = df.pivot_table(index="assunto", columns="empresa", values="pontuacao",
                           aggfunc="sum", fill_value=0)
    pivot = pivot.reindex(columns=[c for c in col_order if c in pivot.columns])

    linha_lookup = {(r["empresa"], r["assunto"]): (r.get("linha_top", "–"), r.get("pts_linha", 0.0))
                    for r in dados}
    cd = [[linha_lookup.get((emp, ass), ("–", 0.0)) for emp in pivot.columns]
          for ass in pivot.index]

    text = [[f"{v:.1f}" for v in row] for row in pivot.values.tolist()]

    fig = go.Figure(go.Heatmap(
        z=pivot.values.tolist(),
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        colorscale=_COLORSCALE,
        zmin=0, zmax=zmax,
        text=text, texttemplate="%{text}",
        hoverongaps=False,
        colorbar=dict(title="Pts"),
        customdata=cd,
        hovertemplate=(
            "Empresa: <b>%{x}</b><br>"
            "Assunto: <b>%{y}</b><br>"
            "Pontuação: <b>%{z:.2f}</b><br>"
            "Linha top: <b>%{customdata[0]}</b> | Pts: <b>%{customdata[1]:.2f}</b>"
            "<extra></extra>"
        ),
    ))
    n_assuntos = len(pivot.index)
    fig.update_layout(
        **LAYOUT_PLOTLY,
        xaxis=dict(tickangle=-45, side="bottom", showgrid=False),
        yaxis=dict(showgrid=False),
        height=max(400, n_assuntos * 46 + 200),
        margin=dict(t=40, b=160, l=260, r=40),
    )
    return fig


def _heatmap_auto(dados: list[dict], zmax: float | None = None, sort_assuntos: list[str] | None = None) -> go.Figure:
    """Heatmap assunto × auto com ordenação opcional por assunto."""
    if not dados:
        return _fig_vazia()

    df = pd.DataFrame(dados)

    # Se há assuntos de ordenação, priorizar esses e depois o resto
    if sort_assuntos:
        df_sort = df[df["assunto"].isin(sort_assuntos)]
        col_order = (df_sort.groupby("auto")["pontuacao"].sum()
                           .sort_values(ascending=False).index.tolist())
        rest = [c for c in df.groupby("auto")["pontuacao"].sum()
                              .sort_values(ascending=False).index if c not in col_order]
        col_order = col_order + rest
    else:
        col_order = df.groupby("auto")["pontuacao"].sum().sort_values(ascending=False).index.tolist()

    pivot = df.pivot_table(index="assunto", columns="auto", values="pontuacao",
                           aggfunc="sum", fill_value=0)
    pivot = pivot.reindex(columns=[c for c in col_order if c in pivot.columns])

    empresa_lookup = {r["auto"]: r.get("empresa", "–") for r in dados}
    label_lookup = {r["auto"]: f"{r['auto']} - {r['cidade_a']} à {r['cidade_b']}" for r in dados}
    cd_matrix = [
        [[empresa_lookup.get(a, "–"), label_lookup.get(a, a)] for a in pivot.columns]
        for _ in pivot.index
    ]

    text = [[f"{v:.1f}" for v in row] for row in pivot.values.tolist()]

    fig = go.Figure(go.Heatmap(
        z=pivot.values.tolist(),
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        colorscale=_COLORSCALE,
        zmin=0, zmax=zmax,
        text=text, texttemplate="%{text}",
        hoverongaps=False,
        colorbar=dict(title="Pts"),
        customdata=cd_matrix,
        hovertemplate=(
            "Empresa: <b>%{customdata[0]}</b><br>"
            "Auto: <b>%{customdata[1]}</b><br>"
            "Assunto: <b>%{y}</b><br>"
            "Pontuação: <b>%{z:.2f}</b>"
            "<extra></extra>"
        ),
    ))
    n_assuntos = len(pivot.index)
    fig.update_layout(
        **LAYOUT_PLOTLY,
        xaxis=dict(tickangle=-45, side="bottom", showgrid=False),
        yaxis=dict(showgrid=False),
        height=max(400, n_assuntos * 46 + 200),
        margin=dict(t=40, b=120, l=260, r=40),
    )
    return fig


def _scatter_evolucao(rows: list[dict], cor: str = "#1a73e8") -> go.Figure:
    xs = [NOMES_MESES.get(r["mes"], str(r["mes"])) for r in rows]
    ys = [r["total"] for r in rows]
    fig = go.Figure(go.Scatter(
        x=xs, y=ys, mode="lines+markers",
        line=dict(color=cor, width=2, shape="spline"),
        marker=dict(size=7, color=cor),
        hovertemplate="<b>%{x}</b><br>Reclamações: %{y}<extra></extra>",
    ))
    fig.update_layout(
        **LAYOUT_PLOTLY,
        height=380,
        margin=dict(t=40, b=40, l=60, r=20),
        xaxis=dict(showgrid=True, gridcolor="#f0f0f0", gridwidth=1, griddash="dot"),
        yaxis=dict(showgrid=True, gridcolor="#f0f0f0", gridwidth=1, griddash="dot"),
    )
    return fig


def _pizza(labels: list[str], values: list[int]) -> go.Figure:
    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        textinfo="percent",
        textfont=dict(size=13),
        hovertemplate="<b>%{label}</b><br>Qtd: %{value}<br>%{percent}<extra></extra>",
        hole=0.3,
    ))
    fig.update_layout(
        **LAYOUT_PLOTLY,
        height=480,
        margin=dict(t=40, b=40, l=40, r=180),
        legend=dict(orientation="v", x=1.02, y=0.5),
    )
    return fig


def _aviso_sem_dados():
    return dbc.Alert("Sem dados no período selecionado.", color="warning",
                     className="mt-2 mb-2")


# ── Registro de callbacks ─────────────────────────────────────────────────────

def register_callbacks(app):
    # Inicialização de anos
    @app.callback(
        Output("filtro-ano", "options"),
        Output("filtro-ano", "value"),
        Input("filtro-servico", "value"),
        prevent_initial_call=False,
    )
    def init_anos(servicos):
        anos = api.get_anos_disponiveis()
        if not anos:
            return [], None
        opts = [{"label": str(a), "value": a} for a in sorted(anos, reverse=True)]
        return opts, opts[0]["value"]

    # Inicialização de meses
    @app.callback(
        Output("filtro-meses", "options"),
        Output("filtro-meses", "value"),
        Input("filtro-ano", "value"),
        Input("filtro-servico", "value"),
        prevent_initial_call=False,
    )
    def init_meses(ano, servicos):
        if ano is None:
            return [], []
        ts = _tipo_servico_str(servicos)
        meses = api.get_meses_disponiveis(ano, ts)
        opts = [{"label": NOMES_MESES[m], "value": m} for m in sorted(meses)]
        return opts, list(meses)

    # Placeholder de meses
    @app.callback(
        Output("filtro-meses", "placeholder"),
        Input("filtro-meses", "value"),
        Input("filtro-meses", "options"),
        prevent_initial_call=False,
    )
    def placeholder_meses(value, options):
        total = len(options or [])
        sel = len(value or [])
        if sel == 0:
            return "Nenhum mês selecionado"
        if sel == total:
            return "Todos os meses"
        return f"{sel} meses selecionados"

    # Visibilidade da seção regular
    @app.callback(
        Output("secao-regular", "style"),
        Input("filtro-servico", "value"),
        prevent_initial_call=False,
    )
    def visibilidade_secao_regular(servicos):
        if _tem_regular(servicos):
            return {"display": "block"}
        return {"display": "none"}

    # Cards de resumo
    @app.callback(
        Output("card-total", "children"),
        Output("card-assunto", "children"),
        Output("card-assunto-qty", "children"),
        Output("aviso-sem-dados", "children"),
        Input("filtro-ano", "value"),
        Input("filtro-meses", "value"),
        Input("filtro-servico", "value"),
        prevent_initial_call=False,
    )
    def update_cards(ano, meses, servicos):
        if ano is None:
            return "–", "–", "", ""
        ts = _tipo_servico_str(servicos)
        data = api.get_resumo(ano, _meses_str(meses or []), ts)
        if data["total_reclamacoes"] == 0:
            return "0", "–", "", _aviso_sem_dados()
        return (
            f"{data['total_reclamacoes']:,}",
            data["assunto_top"],
            f"{data['assunto_top_qty']:,} ocorrências",
            "",
        )

    # Evolução mensal
    @app.callback(
        Output("g-evolucao", "figure"),
        Input("filtro-ano", "value"),
        Input("filtro-meses", "value"),
        Input("filtro-servico", "value"),
        prevent_initial_call=False,
    )
    def update_evolucao(ano, meses, servicos):
        if ano is None:
            return _fig_vazia()
        ts = _tipo_servico_str(servicos)
        rows = api.get_evolucao_mensal(ano, _meses_str(meses or []), ts)
        return _scatter_evolucao(rows) if rows else _fig_vazia()

    # Pizza de assuntos (e atualiza opções de sort)
    @app.callback(
        Output("g-pizza", "figure"),
        Output("filtro-sort-assunto-g5", "options"),
        Output("filtro-sort-assunto-g8", "options"),
        Input("filtro-ano", "value"),
        Input("filtro-meses", "value"),
        Input("filtro-servico", "value"),
        prevent_initial_call=False,
    )
    def update_pizza(ano, meses, servicos):
        if ano is None:
            return _fig_vazia(), [], []
        ts = _tipo_servico_str(servicos)
        rows = api.get_assuntos_pizza(ano, _meses_str(meses or []), ts)
        if not rows:
            return _fig_vazia(), [], []
        assuntos = [r["assunto"] for r in rows]
        opts = [{"label": a, "value": a} for a in assuntos]
        return _pizza(assuntos, [r["total"] for r in rows]), opts, opts

    # Opções de regiões para heatmaps
    @app.callback(
        Output("filtro-regioes-g5", "options"),
        Output("filtro-regioes-g5", "value"),
        Output("filtro-regioes-g8", "options"),
        Output("filtro-regioes-g8", "value"),
        Input("filtro-servico", "value"),
        prevent_initial_call=False,
    )
    def update_regioes_opcoes(servicos):
        regular_servicos = [s for s in (servicos or []) if s in SERVICOS_REGULAR]
        if not regular_servicos:
            return [], [], [], []
        ts = _tipo_servico_str(regular_servicos)
        regioes_data = api.get_regioes_disponiveis(ts)
        opts = [{"label": r["label"], "value": r["id"]} for r in regioes_data]
        return opts, [], opts, []

    # Empresas por pontuação (G3)
    @app.callback(
        Output("g3-empresas", "figure"),
        Input("filtro-ano", "value"),
        Input("filtro-meses", "value"),
        Input("filtro-servico", "value"),
        prevent_initial_call=False,
    )
    def update_empresas(ano, meses, servicos):
        if ano is None or not _tem_regular(servicos):
            return _fig_vazia()
        ts = _tipo_servico_str([s for s in servicos if s in SERVICOS_REGULAR])
        rows = api.get_empresas_pontuacao(ano, _meses_str(meses or []), ts)
        if not rows:
            return _fig_vazia()
        rows_s = sorted(rows, key=lambda r: r["pontuacao"], reverse=True)
        nomes = [r["empresa"] for r in rows_s]
        vals = [r["pontuacao"] for r in rows_s]
        cd = [[r["linha_top"], r["assunto_top"]] for r in rows_s]
        hover = (
            "<b>%{y}</b><br>Pontuação: %{x:.2f}<br>"
            "Linha top: %{customdata[0]}<br>Assunto top: %{customdata[1]}<extra></extra>"
        )
        return _barra_horizontal(nomes, vals, "#e53935", n_items=len(nomes),
                                 customdata=cd, hovertemplate=hover)

    # Empresas por incidência irregular (G4)
    @app.callback(
        Output("g4-irregular", "figure"),
        Input("filtro-ano", "value"),
        Input("filtro-meses", "value"),
        Input("filtro-servico", "value"),
        prevent_initial_call=False,
    )
    def update_irregular_empresa(ano, meses, servicos):
        if ano is None or not _tem_regular(servicos):
            return _fig_vazia()
        ts = _tipo_servico_str([s for s in servicos if s in SERVICOS_REGULAR])
        rows = api.get_empresas_irregular(ano, _meses_str(meses or []), ts)
        if not rows:
            return _fig_vazia()
        rows_s = sorted(rows, key=lambda r: r["pontuacao"], reverse=True)
        nomes = [r["empresa"] for r in rows_s]
        vals = [r["pontuacao"] for r in rows_s]
        cd = [[r["linha_top"]] for r in rows_s]
        hover = (
            "<b>%{y}</b><br>Pontuação Irregular: %{x:.2f}<br>"
            "Linha mais prejudicada: %{customdata[0]}<extra></extra>"
        )
        return _barra_horizontal(nomes, vals, "#e53935", n_items=len(nomes),
                                 customdata=cd, hovertemplate=hover)

    # G5: Paginação
    @app.callback(
        Output("g5-pagina", "data"),
        Input("g5-prev", "n_clicks"),
        Input("g5-next", "n_clicks"),
        State("g5-pagina", "data"),
        State("filtro-ano", "value"),
        State("filtro-meses", "value"),
        State("filtro-servico", "value"),
        State("filtro-regioes-g5", "value"),
        prevent_initial_call=True,
    )
    def pagina_g5(prev_c, next_c, pagina, ano, meses, servicos, regioes):
        ts = _tipo_servico_str([s for s in servicos if s in SERVICOS_REGULAR])
        regioes_str = _tipo_servico_str(regioes)
        resp = api.get_heatmap_assunto_empresa(ano, _meses_str(meses or []), ts, pagina=pagina, regioes=regioes_str)
        total = resp.get("total_paginas", 1)
        if ctx.triggered_id and "prev" in ctx.triggered_id:
            return max(1, pagina - 1)
        if ctx.triggered_id and "next" in ctx.triggered_id:
            return min(total, pagina + 1)
        return pagina

    # G5: Heatmap empresa
    @app.callback(
        Output("g5-heatmap-empresa", "figure"),
        Output("g5-info", "children"),
        Input("filtro-ano", "value"),
        Input("filtro-meses", "value"),
        Input("filtro-servico", "value"),
        Input("filtro-regioes-g5", "value"),
        Input("filtro-sort-assunto-g5", "value"),
        Input("g5-pagina", "data"),
        prevent_initial_call=False,
    )
    def update_heatmap_empresa(ano, meses, servicos, regioes, sort_assuntos, pagina):
        if ano is None or not _tem_regular(servicos):
            return _fig_vazia(), ""
        ts = _tipo_servico_str([s for s in servicos if s in SERVICOS_REGULAR])
        regioes_str = _tipo_servico_str(regioes)
        resp = api.get_heatmap_assunto_empresa(ano, _meses_str(meses or []), ts, pagina=pagina or 1, regioes=regioes_str)
        dados = resp.get("dados", [])
        total_pags = resp.get("total_paginas", 1)
        pag_atual = resp.get("pagina", 1)
        zmax = resp.get("zmax_global")
        return _heatmap_empresa(dados, zmax=zmax, sort_assuntos=sort_assuntos), f"Página {pag_atual} de {total_pags}"

    # G6: Paginação
    @app.callback(
        Output("g6-pagina", "data"),
        Input("g6-prev", "n_clicks"),
        Input("g6-next", "n_clicks"),
        State("g6-pagina", "data"),
        State("filtro-ano", "value"),
        State("filtro-meses", "value"),
        State("filtro-servico", "value"),
        prevent_initial_call=True,
    )
    def pagina_g6(prev_c, next_c, pagina, ano, meses, servicos):
        ts = _tipo_servico_str([s for s in servicos if s in SERVICOS_REGULAR])
        resp = api.get_autos_pontuacao(ano, _meses_str(meses or []), ts, pagina=pagina)
        total = resp.get("total_paginas", 1)
        if ctx.triggered_id and "prev" in ctx.triggered_id:
            return max(1, pagina - 1)
        if ctx.triggered_id and "next" in ctx.triggered_id:
            return min(total, pagina + 1)
        return pagina

    # G6: Autos por pontuação
    @app.callback(
        Output("g6-autos", "figure"),
        Output("g6-info", "children"),
        Input("filtro-ano", "value"),
        Input("filtro-meses", "value"),
        Input("filtro-servico", "value"),
        Input("g6-pagina", "data"),
        prevent_initial_call=False,
    )
    def update_autos_pontuacao(ano, meses, servicos, pagina):
        if ano is None or not _tem_regular(servicos):
            return _fig_vazia(), ""
        ts = _tipo_servico_str([s for s in servicos if s in SERVICOS_REGULAR])
        resp = api.get_autos_pontuacao(ano, _meses_str(meses or []), ts, pagina=pagina or 1)
        dados = resp.get("dados", [])
        total_pags = resp.get("total_paginas", 1)
        pag_atual = resp.get("pagina", 1)
        xmax = resp.get("xmax_global")
        if not dados:
            return _fig_vazia(), f"Página {pag_atual} de {total_pags}"
        dados_s = sorted(dados, key=lambda r: r["pontuacao"], reverse=True)
        nomes = [r["auto"] for r in dados_s]
        vals = [r["pontuacao"] for r in dados_s]
        cd = [[r["assunto_top"]] for r in dados_s]
        hover = (
            "<b>Auto:</b> %{y}<br>Pontuação: %{x:.2f}<br>"
            "Principal assunto: %{customdata[0]}<extra></extra>"
        )
        return _barra_horizontal(nomes, vals, "#1a73e8", n_items=len(nomes),
                                 xmax=xmax, customdata=cd, hovertemplate=hover), \
               f"Página {pag_atual} de {total_pags}"

    # G7: Paginação
    @app.callback(
        Output("g7-pagina", "data"),
        Input("g7-prev", "n_clicks"),
        Input("g7-next", "n_clicks"),
        State("g7-pagina", "data"),
        State("filtro-ano", "value"),
        State("filtro-meses", "value"),
        State("filtro-servico", "value"),
        prevent_initial_call=True,
    )
    def pagina_g7(prev_c, next_c, pagina, ano, meses, servicos):
        ts = _tipo_servico_str([s for s in servicos if s in SERVICOS_REGULAR])
        resp = api.get_autos_irregular(ano, _meses_str(meses or []), ts, pagina=pagina)
        total = resp.get("total_paginas", 1)
        if ctx.triggered_id and "prev" in ctx.triggered_id:
            return max(1, pagina - 1)
        if ctx.triggered_id and "next" in ctx.triggered_id:
            return min(total, pagina + 1)
        return pagina

    # G7: Autos por incidência irregular
    @app.callback(
        Output("g7-irregular", "figure"),
        Output("g7-info", "children"),
        Input("filtro-ano", "value"),
        Input("filtro-meses", "value"),
        Input("filtro-servico", "value"),
        Input("g7-pagina", "data"),
        prevent_initial_call=False,
    )
    def update_autos_irregular(ano, meses, servicos, pagina):
        if ano is None or not _tem_regular(servicos):
            return _fig_vazia(), ""
        ts = _tipo_servico_str([s for s in servicos if s in SERVICOS_REGULAR])
        resp = api.get_autos_irregular(ano, _meses_str(meses or []), ts, pagina=pagina or 1)
        dados = resp.get("dados", [])
        total_pags = resp.get("total_paginas", 1)
        pag_atual = resp.get("pagina", 1)
        xmax = resp.get("xmax_global")
        if not dados:
            return _fig_vazia(), f"Página {pag_atual} de {total_pags}"
        dados_s = sorted(dados, key=lambda r: r["pontuacao"], reverse=True)
        nomes = [r["auto"] for r in dados_s]
        vals = [r["pontuacao"] for r in dados_s]
        hover = "<b>Auto:</b> %{y}<br>Pontuação Irregular: %{x:.2f}<extra></extra>"
        return _barra_horizontal(nomes, vals, "#1a73e8", n_items=len(nomes),
                                 xmax=xmax, hovertemplate=hover), \
               f"Página {pag_atual} de {total_pags}"

    # G8: Opções de empresas
    @app.callback(
        Output("filtro-empresas-g8", "options"),
        Input("filtro-servico", "value"),
        prevent_initial_call=False,
    )
    def init_empresas_g8(servicos):
        ts = _tipo_servico_str([s for s in servicos if s in SERVICOS_REGULAR])
        if not ts:
            return []
        rows = api.get_empresas_lista(ts)
        return [{"label": r["nome"], "value": r["id"]} for r in rows]

    # G8: Paginação
    @app.callback(
        Output("g8-pagina", "data"),
        Input("g8-prev", "n_clicks"),
        Input("g8-next", "n_clicks"),
        State("g8-pagina", "data"),
        State("filtro-ano", "value"),
        State("filtro-meses", "value"),
        State("filtro-servico", "value"),
        State("filtro-empresas-g8", "value"),
        State("filtro-regioes-g8", "value"),
        prevent_initial_call=True,
    )
    def pagina_g8(prev_c, next_c, pagina, ano, meses, servicos, empresas, regioes):
        ts = _tipo_servico_str([s for s in servicos if s in SERVICOS_REGULAR])
        perm_ids = ",".join(str(e) for e in (empresas or []))
        regioes_str = _tipo_servico_str(regioes)
        resp = api.get_heatmap_assunto_auto(
            ano, _meses_str(meses or []), ts, perm_ids or None, pagina=pagina, regioes=regioes_str
        )
        total = resp.get("total_paginas", 1)
        if ctx.triggered_id and "prev" in ctx.triggered_id:
            return max(1, pagina - 1)
        if ctx.triggered_id and "next" in ctx.triggered_id:
            return min(total, pagina + 1)
        return pagina

    # G8: Heatmap auto
    @app.callback(
        Output("g8-heatmap-auto", "figure"),
        Output("g8-info", "children"),
        Input("filtro-ano", "value"),
        Input("filtro-meses", "value"),
        Input("filtro-servico", "value"),
        Input("filtro-empresas-g8", "value"),
        Input("filtro-regioes-g8", "value"),
        Input("filtro-sort-assunto-g8", "value"),
        Input("g8-pagina", "data"),
        prevent_initial_call=False,
    )
    def update_heatmap_auto(ano, meses, servicos, empresas, regioes, sort_assuntos, pagina):
        if ano is None or not _tem_regular(servicos):
            return _fig_vazia(), ""
        ts = _tipo_servico_str([s for s in servicos if s in SERVICOS_REGULAR])
        perm_ids = ",".join(str(e) for e in (empresas or []))
        regioes_str = _tipo_servico_str(regioes)
        resp = api.get_heatmap_assunto_auto(
            ano, _meses_str(meses or []), ts, perm_ids or None, pagina=pagina or 1, regioes=regioes_str
        )
        dados = resp.get("dados", [])
        total_pags = resp.get("total_paginas", 1)
        pag_atual = resp.get("pagina", 1)
        zmax = resp.get("zmax_global")
        return _heatmap_auto(dados, zmax=zmax, sort_assuntos=sort_assuntos), f"Página {pag_atual} de {total_pags}"

    # Locais de embarque/desembarque: Paginação
    @app.callback(
        Output("g-pagina-locais", "data"),
        Input("g-locais-prev", "n_clicks"),
        Input("g-locais-next", "n_clicks"),
        State("g-pagina-locais", "data"),
        State("filtro-ano", "value"),
        State("filtro-meses", "value"),
        State("filtro-servico", "value"),
        State("filtro-tipo-local", "value"),
        prevent_initial_call=True,
    )
    def pagina_locais(prev_c, next_c, pagina, ano, meses, servicos, tipo_local):
        ts = _tipo_servico_str(servicos)
        resp = api.get_locais_embarque(ano, _meses_str(meses or []), ts, tipo_local, pagina=pagina)
        total = resp.get("total_paginas", 1)
        if ctx.triggered_id and "prev" in ctx.triggered_id:
            return max(1, pagina - 1)
        if ctx.triggered_id and "next" in ctx.triggered_id:
            return min(total, pagina + 1)
        return pagina

    # Locais de embarque/desembarque: Gráfico
    @app.callback(
        Output("g-locais", "figure"),
        Output("g-locais-info", "children"),
        Input("filtro-ano", "value"),
        Input("filtro-meses", "value"),
        Input("filtro-servico", "value"),
        Input("filtro-tipo-local", "value"),
        Input("g-pagina-locais", "data"),
        prevent_initial_call=False,
    )
    def update_locais(ano, meses, servicos, tipo_local, pagina):
        if ano is None:
            return _fig_vazia(), ""
        ts = _tipo_servico_str(servicos)
        resp = api.get_locais_embarque(ano, _meses_str(meses or []), ts, tipo_local, pagina=pagina or 1)
        dados = resp.get("dados", [])
        total_pags = resp.get("total_paginas", 1)
        pag_atual = resp.get("pagina", 1)
        xmax = resp.get("xmax_global")
        if not dados:
            return _fig_vazia(), f"Página {pag_atual} de {total_pags}"
        dados_s = sorted(dados, key=lambda r: r["total"], reverse=True)
        nomes = [r["local"] for r in dados_s]
        vals = [r["total"] for r in dados_s]
        cd = [[r["assunto_top"]] for r in dados_s]
        hover = (
            "<b>%{y}</b><br>Reclamações: %{x}<br>"
            "Principal assunto: %{customdata[0]}<extra></extra>"
        )
        return _barra_horizontal(nomes, vals, "#1a73e8", n_items=len(nomes),
                                 xmax=xmax, customdata=cd, hovertemplate=hover), \
               f"Página {pag_atual} de {total_pags}"
