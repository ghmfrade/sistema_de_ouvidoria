"""Callbacks reativos do Dashboard de Qualidade."""

import pandas as pd
import dash_bootstrap_components as dbc
from dash import Input, Output, State, ctx, html
import plotly.graph_objects as go

from qualidade_dash import api_client as api
from qualidade_dash.layout import LAYOUT_PLOTLY, NOMES_MESES, TS_FRETA, TS_INTER, TS_METRO

_COLORSCALE = [[0, "#2ecc71"], [0.5, "#f1c40f"], [1, "#e74c3c"]]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _tipo_servico(tab_id: str) -> str | None:
    return {"metro": TS_METRO, "inter": TS_INTER, "freta": TS_FRETA}.get(tab_id)


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
    """Barras horizontais com maior valor no topo (dados em ordem DECRESCENTE).
    xmax: se informado, fixa o range do eixo X para consistência entre páginas."""
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


def _heatmap_empresa(dados: list[dict], zmax: float | None = None) -> go.Figure:
    """Heatmap assunto × empresa. zmax: escala global para consistência entre páginas."""
    if not dados:
        return _fig_vazia()

    df = pd.DataFrame(dados)
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


def _heatmap_auto(dados: list[dict], zmax: float | None = None) -> go.Figure:
    """Heatmap assunto × auto. Eixo X: só número do auto; tooltip: nome completo."""
    if not dados:
        return _fig_vazia()

    df = pd.DataFrame(dados)
    col_order = df.groupby("auto")["pontuacao"].sum().sort_values(ascending=False).index.tolist()
    pivot = df.pivot_table(index="assunto", columns="auto", values="pontuacao",
                           aggfunc="sum", fill_value=0)
    pivot = pivot.reindex(columns=[c for c in col_order if c in pivot.columns])

    # Customdata por célula: [empresa, label completo "NUMERO - CidadeA à CidadeB"]
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
            "Autos: <b>%{customdata[1]}</b><br>"
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
    """Pizza com percentagem nas fatias — legenda lateral com nomes."""
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
    for tab_id in ("metro", "inter"):
        _register_aba_regular(app, tab_id)
    _register_aba_fretamento(app)


def _register_aba_regular(app, tab_id: str):
    ts = _tipo_servico(tab_id)

    @app.callback(
        Output(f"filtro-ano-{tab_id}", "options"),
        Output(f"filtro-ano-{tab_id}", "value"),
        Input("tabs-principal", "value"),
        prevent_initial_call=False,
    )
    def init_anos(_tab, _ts=ts):
        anos = api.get_anos_disponiveis()
        if not anos:
            return [], None
        opts = [{"label": str(a), "value": a} for a in sorted(anos, reverse=True)]
        return opts, opts[0]["value"]

    @app.callback(
        Output(f"filtro-meses-{tab_id}", "options"),
        Output(f"filtro-meses-{tab_id}", "value"),
        Input(f"filtro-ano-{tab_id}", "value"),
        prevent_initial_call=False,
    )
    def init_meses(ano, _ts=ts):
        if ano is None:
            return [], []
        meses = api.get_meses_disponiveis(ano, _ts)
        opts = [{"label": NOMES_MESES[m], "value": m} for m in sorted(meses)]
        return opts, list(meses)

    @app.callback(
        Output(f"filtro-meses-{tab_id}", "placeholder"),
        Input(f"filtro-meses-{tab_id}", "value"),
        Input(f"filtro-meses-{tab_id}", "options"),
        prevent_initial_call=False,
    )
    def placeholder_meses(value, options, _ts=ts):
        total = len(options or [])
        sel = len(value or [])
        if sel == 0:
            return "Nenhum mês selecionado"
        if sel == total:
            return "Todos os meses"
        return f"{sel} meses selecionados"

    @app.callback(
        Output(f"card-total-{tab_id}", "children"),
        Output(f"card-assunto-{tab_id}", "children"),
        Output(f"card-assunto-qty-{tab_id}", "children"),
        Output(f"aviso-sem-dados-{tab_id}", "children"),
        Input(f"filtro-ano-{tab_id}", "value"),
        Input(f"filtro-meses-{tab_id}", "value"),
        prevent_initial_call=False,
    )
    def update_cards(ano, meses, _ts=ts):
        if ano is None:
            return "–", "–", "", ""
        data = api.get_resumo(ano, _meses_str(meses or []), _ts)
        if data["total_reclamacoes"] == 0:
            return "0", "–", "", _aviso_sem_dados()
        return (
            f"{data['total_reclamacoes']:,}",
            data["assunto_top"],
            f"{data['assunto_top_qty']:,} ocorrências",
            "",
        )

    @app.callback(
        Output(f"g1-evolucao-{tab_id}", "figure"),
        Input(f"filtro-ano-{tab_id}", "value"),
        Input(f"filtro-meses-{tab_id}", "value"),
        prevent_initial_call=False,
    )
    def update_evolucao(ano, meses, _ts=ts):
        if ano is None:
            return _fig_vazia()
        rows = api.get_evolucao_mensal(ano, _meses_str(meses or []), _ts)
        return _scatter_evolucao(rows) if rows else _fig_vazia()

    @app.callback(
        Output(f"g2-pizza-{tab_id}", "figure"),
        Input(f"filtro-ano-{tab_id}", "value"),
        Input(f"filtro-meses-{tab_id}", "value"),
        prevent_initial_call=False,
    )
    def update_pizza(ano, meses, _ts=ts):
        if ano is None:
            return _fig_vazia()
        rows = api.get_assuntos_pizza(ano, _meses_str(meses or []), _ts)
        if not rows:
            return _fig_vazia()
        return _pizza([r["assunto"] for r in rows], [r["total"] for r in rows])

    @app.callback(
        Output(f"g3-empresas-{tab_id}", "figure"),
        Input(f"filtro-ano-{tab_id}", "value"),
        Input(f"filtro-meses-{tab_id}", "value"),
        prevent_initial_call=False,
    )
    def update_empresas(ano, meses, _ts=ts):
        if ano is None:
            return _fig_vazia()
        rows = api.get_empresas_pontuacao(ano, _meses_str(meses or []), _ts)
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

    @app.callback(
        Output(f"g4-irregular-{tab_id}", "figure"),
        Input(f"filtro-ano-{tab_id}", "value"),
        Input(f"filtro-meses-{tab_id}", "value"),
        prevent_initial_call=False,
    )
    def update_irregular_empresa(ano, meses, _ts=ts):
        if ano is None:
            return _fig_vazia()
        rows = api.get_empresas_irregular(ano, _meses_str(meses or []), _ts)
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

    # G5: Heatmap assunto × empresa
    @app.callback(
        Output(f"g5-pagina-{tab_id}", "data"),
        Input(f"g5-{tab_id}-prev", "n_clicks"),
        Input(f"g5-{tab_id}-next", "n_clicks"),
        State(f"g5-pagina-{tab_id}", "data"),
        State(f"filtro-ano-{tab_id}", "value"),
        State(f"filtro-meses-{tab_id}", "value"),
        prevent_initial_call=True,
    )
    def pagina_g5(prev_c, next_c, pagina, ano, meses, _ts=ts):
        resp = api.get_heatmap_assunto_empresa(ano, _meses_str(meses or []), _ts, pagina=pagina)
        total = resp.get("total_paginas", 1)
        if ctx.triggered_id and "prev" in ctx.triggered_id:
            return max(1, pagina - 1)
        if ctx.triggered_id and "next" in ctx.triggered_id:
            return min(total, pagina + 1)
        return pagina

    @app.callback(
        Output(f"g5-heatmap-empresa-{tab_id}", "figure"),
        Output(f"g5-{tab_id}-info", "children"),
        Input(f"filtro-ano-{tab_id}", "value"),
        Input(f"filtro-meses-{tab_id}", "value"),
        Input(f"g5-pagina-{tab_id}", "data"),
        prevent_initial_call=False,
    )
    def update_heatmap_empresa(ano, meses, pagina, _ts=ts):
        if ano is None:
            return _fig_vazia(), ""
        resp = api.get_heatmap_assunto_empresa(ano, _meses_str(meses or []), _ts, pagina=pagina or 1)
        dados = resp.get("dados", [])
        total_pags = resp.get("total_paginas", 1)
        pag_atual = resp.get("pagina", 1)
        zmax = resp.get("zmax_global")
        return _heatmap_empresa(dados, zmax=zmax), f"Página {pag_atual} de {total_pags}"

    # G6: Autos por pontuação
    @app.callback(
        Output(f"g6-pagina-{tab_id}", "data"),
        Input(f"g6-{tab_id}-prev", "n_clicks"),
        Input(f"g6-{tab_id}-next", "n_clicks"),
        State(f"g6-pagina-{tab_id}", "data"),
        State(f"filtro-ano-{tab_id}", "value"),
        State(f"filtro-meses-{tab_id}", "value"),
        prevent_initial_call=True,
    )
    def pagina_g6(prev_c, next_c, pagina, ano, meses, _ts=ts):
        resp = api.get_autos_pontuacao(ano, _meses_str(meses or []), _ts, pagina=pagina)
        total = resp.get("total_paginas", 1)
        if ctx.triggered_id and "prev" in ctx.triggered_id:
            return max(1, pagina - 1)
        if ctx.triggered_id and "next" in ctx.triggered_id:
            return min(total, pagina + 1)
        return pagina

    @app.callback(
        Output(f"g6-autos-{tab_id}", "figure"),
        Output(f"g6-{tab_id}-info", "children"),
        Input(f"filtro-ano-{tab_id}", "value"),
        Input(f"filtro-meses-{tab_id}", "value"),
        Input(f"g6-pagina-{tab_id}", "data"),
        prevent_initial_call=False,
    )
    def update_autos_pontuacao(ano, meses, pagina, _ts=ts):
        if ano is None:
            return _fig_vazia(), ""
        resp = api.get_autos_pontuacao(ano, _meses_str(meses or []), _ts, pagina=pagina or 1)
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

    # G7: Autos por incidência irregular
    @app.callback(
        Output(f"g7-pagina-{tab_id}", "data"),
        Input(f"g7-{tab_id}-prev", "n_clicks"),
        Input(f"g7-{tab_id}-next", "n_clicks"),
        State(f"g7-pagina-{tab_id}", "data"),
        State(f"filtro-ano-{tab_id}", "value"),
        State(f"filtro-meses-{tab_id}", "value"),
        prevent_initial_call=True,
    )
    def pagina_g7(prev_c, next_c, pagina, ano, meses, _ts=ts):
        resp = api.get_autos_irregular(ano, _meses_str(meses or []), _ts, pagina=pagina)
        total = resp.get("total_paginas", 1)
        if ctx.triggered_id and "prev" in ctx.triggered_id:
            return max(1, pagina - 1)
        if ctx.triggered_id and "next" in ctx.triggered_id:
            return min(total, pagina + 1)
        return pagina

    @app.callback(
        Output(f"g7-irregular-{tab_id}", "figure"),
        Output(f"g7-{tab_id}-info", "children"),
        Input(f"filtro-ano-{tab_id}", "value"),
        Input(f"filtro-meses-{tab_id}", "value"),
        Input(f"g7-pagina-{tab_id}", "data"),
        prevent_initial_call=False,
    )
    def update_autos_irregular(ano, meses, pagina, _ts=ts):
        if ano is None:
            return _fig_vazia(), ""
        resp = api.get_autos_irregular(ano, _meses_str(meses or []), _ts, pagina=pagina or 1)
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

    # G8: filtro de empresas
    @app.callback(
        Output(f"filtro-empresas-g8-{tab_id}", "options"),
        Input("tabs-principal", "value"),
        prevent_initial_call=False,
    )
    def init_empresas_g8(_tab, _ts=ts):
        rows = api.get_empresas_lista(_ts)
        return [{"label": r["nome"], "value": r["id"]} for r in rows]

    @app.callback(
        Output(f"g8-pagina-{tab_id}", "data"),
        Input(f"g8-{tab_id}-prev", "n_clicks"),
        Input(f"g8-{tab_id}-next", "n_clicks"),
        State(f"g8-pagina-{tab_id}", "data"),
        State(f"filtro-ano-{tab_id}", "value"),
        State(f"filtro-meses-{tab_id}", "value"),
        State(f"filtro-empresas-g8-{tab_id}", "value"),
        prevent_initial_call=True,
    )
    def pagina_g8(prev_c, next_c, pagina, ano, meses, empresas, _ts=ts):
        perm_ids = ",".join(str(e) for e in (empresas or []))
        resp = api.get_heatmap_assunto_auto(
            ano, _meses_str(meses or []), _ts, perm_ids or None, pagina=pagina
        )
        total = resp.get("total_paginas", 1)
        if ctx.triggered_id and "prev" in ctx.triggered_id:
            return max(1, pagina - 1)
        if ctx.triggered_id and "next" in ctx.triggered_id:
            return min(total, pagina + 1)
        return pagina

    @app.callback(
        Output(f"g8-heatmap-auto-{tab_id}", "figure"),
        Output(f"g8-{tab_id}-info", "children"),
        Input(f"filtro-ano-{tab_id}", "value"),
        Input(f"filtro-meses-{tab_id}", "value"),
        Input(f"filtro-empresas-g8-{tab_id}", "value"),
        Input(f"g8-pagina-{tab_id}", "data"),
        prevent_initial_call=False,
    )
    def update_heatmap_auto(ano, meses, empresas, pagina, _ts=ts):
        if ano is None:
            return _fig_vazia(), ""
        perm_ids = ",".join(str(e) for e in (empresas or []))
        resp = api.get_heatmap_assunto_auto(
            ano, _meses_str(meses or []), _ts, perm_ids or None, pagina=pagina or 1
        )
        dados = resp.get("dados", [])
        total_pags = resp.get("total_paginas", 1)
        pag_atual = resp.get("pagina", 1)
        zmax = resp.get("zmax_global")
        return _heatmap_auto(dados, zmax=zmax), f"Página {pag_atual} de {total_pags}"


def _register_aba_fretamento(app):
    tab_id = "freta"
    ts = TS_FRETA

    @app.callback(
        Output(f"filtro-ano-{tab_id}", "options"),
        Output(f"filtro-ano-{tab_id}", "value"),
        Input("tabs-principal", "value"),
        prevent_initial_call=False,
    )
    def init_anos_freta(_tab):
        anos = api.get_anos_disponiveis()
        if not anos:
            return [], None
        opts = [{"label": str(a), "value": a} for a in sorted(anos, reverse=True)]
        return opts, opts[0]["value"]

    @app.callback(
        Output(f"filtro-meses-{tab_id}", "options"),
        Output(f"filtro-meses-{tab_id}", "value"),
        Input(f"filtro-ano-{tab_id}", "value"),
        prevent_initial_call=False,
    )
    def init_meses_freta(ano):
        if ano is None:
            return [], []
        meses = api.get_meses_disponiveis(ano, ts)
        opts = [{"label": NOMES_MESES[m], "value": m} for m in sorted(meses)]
        return opts, list(meses)

    @app.callback(
        Output(f"filtro-meses-{tab_id}", "placeholder"),
        Input(f"filtro-meses-{tab_id}", "value"),
        Input(f"filtro-meses-{tab_id}", "options"),
        prevent_initial_call=False,
    )
    def placeholder_meses_freta(value, options):
        total = len(options or [])
        sel = len(value or [])
        if sel == 0:
            return "Nenhum mês selecionado"
        if sel == total:
            return "Todos os meses"
        return f"{sel} meses selecionados"

    @app.callback(
        Output(f"card-total-{tab_id}", "children"),
        Output(f"card-assunto-{tab_id}", "children"),
        Output(f"card-assunto-qty-{tab_id}", "children"),
        Output(f"aviso-sem-dados-{tab_id}", "children"),
        Input(f"filtro-ano-{tab_id}", "value"),
        Input(f"filtro-meses-{tab_id}", "value"),
        prevent_initial_call=False,
    )
    def update_cards_freta(ano, meses):
        if ano is None:
            return "–", "–", "", ""
        data = api.get_resumo(ano, _meses_str(meses or []), ts)
        if data["total_reclamacoes"] == 0:
            return "0", "–", "", _aviso_sem_dados()
        return (
            f"{data['total_reclamacoes']:,}",
            data["assunto_top"],
            f"{data['assunto_top_qty']:,} ocorrências",
            "",
        )

    @app.callback(
        Output(f"g0-evolucao-{tab_id}", "figure"),
        Input(f"filtro-ano-{tab_id}", "value"),
        Input(f"filtro-meses-{tab_id}", "value"),
        prevent_initial_call=False,
    )
    def update_evolucao_freta(ano, meses):
        if ano is None:
            return _fig_vazia()
        rows = api.get_evolucao_mensal(ano, _meses_str(meses or []), ts)
        return _scatter_evolucao(rows, cor="#6f42c1") if rows else _fig_vazia()

    @app.callback(
        Output(f"g1-pizza-{tab_id}", "figure"),
        Input(f"filtro-ano-{tab_id}", "value"),
        Input(f"filtro-meses-{tab_id}", "value"),
        prevent_initial_call=False,
    )
    def update_pizza_freta(ano, meses):
        if ano is None:
            return _fig_vazia()
        rows = api.get_assuntos_pizza(ano, _meses_str(meses or []), ts)
        if not rows:
            return _fig_vazia()
        return _pizza([r["assunto"] for r in rows], [r["total"] for r in rows])

    @app.callback(
        Output(f"g2-pagina-{tab_id}", "data"),
        Input(f"g2-{tab_id}-prev", "n_clicks"),
        Input(f"g2-{tab_id}-next", "n_clicks"),
        State(f"g2-pagina-{tab_id}", "data"),
        State(f"filtro-ano-{tab_id}", "value"),
        State(f"filtro-meses-{tab_id}", "value"),
        prevent_initial_call=True,
    )
    def pagina_g2_freta(prev_c, next_c, pagina, ano, meses):
        resp = api.get_locais_embarque(ano, _meses_str(meses or []), pagina=pagina)
        total = resp.get("total_paginas", 1)
        if ctx.triggered_id and "prev" in ctx.triggered_id:
            return max(1, pagina - 1)
        if ctx.triggered_id and "next" in ctx.triggered_id:
            return min(total, pagina + 1)
        return pagina

    @app.callback(
        Output(f"g2-locais-{tab_id}", "figure"),
        Output(f"g2-{tab_id}-info", "children"),
        Input(f"filtro-ano-{tab_id}", "value"),
        Input(f"filtro-meses-{tab_id}", "value"),
        Input(f"g2-pagina-{tab_id}", "data"),
        prevent_initial_call=False,
    )
    def update_locais(ano, meses, pagina):
        if ano is None:
            return _fig_vazia(), ""
        resp = api.get_locais_embarque(ano, _meses_str(meses or []), pagina=pagina or 1)
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
