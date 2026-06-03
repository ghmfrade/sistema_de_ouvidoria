"""Callbacks reativos do Dashboard de Qualidade — Visão Unificada."""

import pandas as pd
import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, ctx, html, no_update
from concurrent.futures import ThreadPoolExecutor
import plotly.graph_objects as go

from qualidade_dash import api_client as api
from qualidade_dash.layout import (
    CARD_COLORS, LAYOUT_PLOTLY, NOMES_MESES, SERVICOS_REGULAR, SERVICOS_DEFAULT,
)

_COLORSCALE = [[0, "#2ecc71"], [0.5, "#f1c40f"], [1, "#e74c3c"]]

_SERVICO_LABEL = {
    "Regular – Metropolitano":   "Regular Metropolitano",
    "Regular – Intermunicipal":  "Regular Intermunicipal",
    "Fretamento Intermunicipal": "Fretamento Intermunicipal",
    "Fretamento Metropolitano":  "Fretamento Metropolitano",
}


# ── Helpers básicos ───────────────────────────────────────────────────────────

def _tipo_servico_str(servicos: list[str] | None) -> str | None:
    if not servicos:
        return None
    return ",".join(servicos)


def _tem_regular(servicos: list[str] | None) -> bool:
    return any(s in SERVICOS_REGULAR for s in (servicos or []))


def _meses_str(meses: list[int] | None) -> str | None:
    if not meses:
        return None
    return ",".join(str(m) for m in meses)


def _perm_ids_str(empresa_ids: list | None) -> str | None:
    if not empresa_ids:
        return None
    return ",".join(str(e) for e in empresa_ids)


def _assuntos_str(assuntos: list[str] | None) -> str | None:
    if not assuntos:
        return None
    return ",".join(assuntos)


def _empresa_nomes_from_opts(empresa_ids: list | None, opts: list[dict] | None) -> list[str]:
    """Resolve a lista de nomes display das empresas a partir das opções do dropdown."""
    if not empresa_ids or not opts:
        return []
    ids_set = set(empresa_ids)
    return [opt.get("label") for opt in (opts or []) if opt.get("value") in ids_set]


# ── Helpers de subtítulo ──────────────────────────────────────────────────────

def _regiao_label_curto(regiao_id: str) -> str:
    """Converte ID de região para texto curto: 'TC1' ou 'Campinas' (sem 'RM ')."""
    if regiao_id.startswith("TC"):
        return regiao_id
    return regiao_id.replace("RM ", "").strip()


def _regioes_texto(regioes_ids: list[str] | None) -> str | None:
    """Monta texto como 'da Baixada Santista' ou 'de TC1 e TC3'."""
    if not regioes_ids:
        return None
    labels = [_regiao_label_curto(r) for r in regioes_ids]
    if len(labels) == 1:
        return f"da {labels[0]}"
    return "de " + ", ".join(labels[:-1]) + " e " + labels[-1]


def _subtitulo_servico(servicos: list[str] | None) -> str:
    """Subtítulo base para gráficos compartilhados — reflete apenas o serviço."""
    sel = set(servicos or [])
    if not sel or len(sel) >= 4:
        return ""
    tem_mfret = "Fretamento Metropolitano" in sel
    tem_ifret  = "Fretamento Intermunicipal" in sel
    tem_mreg   = "Regular – Metropolitano" in sel
    tem_ireg   = "Regular – Intermunicipal" in sel

    if tem_mfret and tem_ifret and not tem_mreg and not tem_ireg:
        return "Serviço de Fretamento"
    if tem_ifret and not tem_mfret and not tem_mreg and not tem_ireg:
        return "Fretamento Intermunicipal"
    if tem_mfret and not tem_ifret and not tem_mreg and not tem_ireg:
        return "Fretamento Metropolitano"
    if tem_mreg and tem_ireg and not tem_mfret and not tem_ifret:
        return "Serviço Regular"
    if tem_mreg and not tem_ireg and not tem_mfret and not tem_ifret:
        return "Serviço Regular Metropolitano"
    if tem_ireg and not tem_mreg and not tem_mfret and not tem_ifret:
        return "Serviço Regular Intermunicipal"

    labels = [_SERVICO_LABEL[s] for s in [
        "Regular – Metropolitano", "Regular – Intermunicipal",
        "Fretamento Intermunicipal", "Fretamento Metropolitano"
    ] if s in sel]
    if len(labels) == 2:
        return f"{labels[0]} e {labels[1]}"
    return ", ".join(labels[:-1]) + " e " + labels[-1]


def _reg_label_base(servicos: list[str] | None) -> str:
    """Rótulo base somente para dados Regular."""
    metro = "Regular – Metropolitano" in (servicos or [])
    inter = "Regular – Intermunicipal" in (servicos or [])
    if metro and inter:
        return "Serviço Regular"
    if metro:
        return "Serviço Regular Metropolitano"
    if inter:
        return "Serviço Regular Intermunicipal"
    return "Serviço Regular"


def _assunto_label(assuntos: list[str] | None) -> str | None:
    """Converte lista de assuntos em texto curto para subtítulos."""
    if not assuntos:
        return None
    if len(assuntos) == 1:
        return assuntos[0]
    return f"{len(assuntos)} assuntos"


def _build_subtitulo_compartilhado(
    servicos: list[str] | None,
    regioes_ids: list[str] | None,
    empresa_nome: str | None,
    assuntos: list[str] | str | None,
) -> str:
    """Subtítulo para G1 (evolução), G2 (pizza), G-locais."""
    assunto_txt = _assunto_label(assuntos if isinstance(assuntos, list) else ([assuntos] if assuntos else None))
    sel = set(servicos or [])
    tem_fret = any("Fretamento" in s for s in sel)
    tem_reg  = any(s in SERVICOS_REGULAR for s in sel)

    if empresa_nome and tem_fret and tem_reg:
        base = f"Dados do Serviço de Fretamento e Serviço Regular da Empresa {empresa_nome}"
    elif empresa_nome and tem_reg:
        base = f"{_reg_label_base(servicos)} da Empresa {empresa_nome}"
    else:
        base_serv = _subtitulo_servico(servicos)
        reg_txt = _regioes_texto(regioes_ids)
        if base_serv and reg_txt and tem_reg:
            base = f"{base_serv} {reg_txt}"
        else:
            base = base_serv

    if assunto_txt and base:
        return f"{base} — {assunto_txt}"
    if assunto_txt:
        return f"Assunto: {assunto_txt}"
    return base


def _build_subtitulo_regular(
    servicos: list[str] | None,
    regioes_ids: list[str] | None,
    empresa_nome: str | None,
    assuntos: list[str] | str | None,
    incluir_assunto: bool = True,
) -> str:
    """Subtítulo para gráficos Regular-only (G3–G8)."""
    assunto_txt = _assunto_label(assuntos if isinstance(assuntos, list) else ([assuntos] if assuntos else None))
    base_reg = _reg_label_base(servicos)

    if empresa_nome:
        base = f"{base_reg} da Empresa {empresa_nome}"
    else:
        reg_txt = _regioes_texto(regioes_ids)
        base = f"{base_reg} {reg_txt}" if reg_txt else base_reg

    if incluir_assunto and assunto_txt and base:
        return f"{base} — {assunto_txt}"
    return base


def _empresa_nome_from_opts(empresa_ids: list | None, opts: list[dict] | None) -> str | None:
    """Resolve o nome display (único) da empresa para uso em subtítulos."""
    nomes = _empresa_nomes_from_opts(empresa_ids, opts)
    if not nomes:
        return None
    if len(nomes) == 1:
        return nomes[0]
    return f"{len(nomes)} empresas"


# ── Helpers de figura ─────────────────────────────────────────────────────────

def _fig_vazia(msg: str = "Sem dados para o período") -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        **LAYOUT_PLOTLY,
        annotations=[dict(text=msg, showarrow=False, xref="paper", yref="paper",
                          x=0.5, y=0.5, font=dict(size=14, color="#999"))],
    )
    return fig


def _barra_horizontal(nomes, valores, cor, n_items: int = 0,
                      xmax: float | None = None,
                      customdata=None, hovertemplate: str | None = None):
    """Barras horizontais com maior valor no topo. cor pode ser str ou list."""
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


_CORES_DESTAQUE = [
    "#1a73e8", "#e67e22", "#27ae60", "#8e44ad", "#e74c3c",
    "#16a085", "#f39c12", "#2980b9", "#d35400", "#1abc9c",
]


def _heatmap_empresa(dados: list[dict], zmax: float | None = None,
                     sort_assuntos: list[str] | None = None,
                     empresas_destaque: list[str] | None = None) -> go.Figure:
    """Heatmap assunto × empresa. Empresas destaque vão para o início com borda colorida."""
    if not dados:
        return _fig_vazia()

    df = pd.DataFrame(dados)

    if sort_assuntos:
        df_sort = df[df["assunto"].isin(sort_assuntos)]
        col_order = (df_sort.groupby("empresa")["pontuacao"].sum()
                           .sort_values(ascending=False).index.tolist())
        rest = [c for c in df.groupby("empresa")["pontuacao"].sum()
                              .sort_values(ascending=False).index if c not in col_order]
        col_order = col_order + rest
    else:
        col_order = df.groupby("empresa")["pontuacao"].sum().sort_values(ascending=False).index.tolist()

    # Empresas destaque vão para as primeiras posições (ordenadas por pontuação entre si)
    if empresas_destaque:
        dest_set = set(empresas_destaque)
        dest_order = sorted(
            [c for c in col_order if c in dest_set],
            key=lambda c: df[df["empresa"] == c]["pontuacao"].sum(),
            reverse=True,
        )
        rest_order = [c for c in col_order if c not in dest_set]
        col_order = dest_order + rest_order

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

    # Borda colorida ao redor de cada empresa destaque
    if empresas_destaque:
        cols_list = pivot.columns.tolist()
        for empresa, cor in zip(empresas_destaque, _CORES_DESTAQUE):
            if empresa in cols_list:
                idx = cols_list.index(empresa)
                fig.add_shape(
                    type="rect",
                    x0=idx - 0.5, x1=idx + 0.5,
                    y0=-0.5, y1=n_assuntos - 0.5,
                    line=dict(color=cor, width=3),
                    fillcolor="rgba(0,0,0,0)",
                    xref="x", yref="y",
                )

    return fig


def _heatmap_auto(dados: list[dict], zmax: float | None = None, sort_assuntos: list[str] | None = None) -> go.Figure:
    """Heatmap assunto × auto com ordenação opcional por assunto."""
    if not dados:
        return _fig_vazia()

    df = pd.DataFrame(dados)

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


def _pizza(labels: list[str], values: list[int], assunto_destaque: str | None = None) -> go.Figure:
    pull = [0.12 if assunto_destaque and lbl == assunto_destaque else 0 for lbl in labels]
    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        textinfo="percent",
        textfont=dict(size=13),
        hovertemplate="<b>%{label}</b><br>Qtd: %{value}<br>%{percent}<extra></extra>",
        hole=0.3,
        pull=pull,
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

    # ── Ativa overlay imediatamente quando qualquer filtro muda (client-side) ──
    app.clientside_callback(
        "function() { return true; }",
        Output("store-loading", "data", allow_duplicate=True),
        Input("filtro-ano", "value"),
        Input("filtro-meses", "value"),
        Input("filtro-servico", "value"),
        Input("filtro-regiao", "value"),
        Input("filtro-empresa", "value"),
        Input("filtro-assunto", "value"),
        Input("filtro-tipo-local", "value"),
        prevent_initial_call=True,
    )

    # ── Controla visibilidade do overlay conforme store-loading (client-side) ──
    app.clientside_callback(
        "function(loading) { return loading ? 'loading-overlay ativo' : 'loading-overlay'; }",
        Output("loading-overlay", "className"),
        Input("store-loading", "data"),
        prevent_initial_call=False,
    )

    # ── Inicialização de anos ─────────────────────────────────────────────────
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

    # ── Inicialização de meses ────────────────────────────────────────────────
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

    # ── Placeholder de meses ──────────────────────────────────────────────────
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

    # ── Visibilidade dos filtros de região/empresa ────────────────────────────
    @app.callback(
        Output("col-filtro-regiao", "style"),
        Output("col-filtro-empresa", "style"),
        Input("filtro-servico", "value"),
        prevent_initial_call=False,
    )
    def visibilidade_filtros_regular(servicos):
        if _tem_regular(servicos):
            return {}, {}
        return {"display": "none"}, {"display": "none"}

    # ── Limite de seleção de empresas (máx. 10) ───────────────────────────────
    @app.callback(
        Output("filtro-empresa", "value"),
        Input("filtro-empresa", "value"),
        prevent_initial_call=True,
    )
    def limit_empresa_selection(ids):
        if ids and len(ids) > 10:
            return ids[:10]
        return ids

    # ── Opções de região (filtro global) ──────────────────────────────────────
    @app.callback(
        Output("filtro-regiao", "options"),
        Output("filtro-regiao", "value"),
        Input("filtro-servico", "value"),
        prevent_initial_call=False,
    )
    def update_regioes_opcoes(servicos):
        regular_servicos = [s for s in (servicos or []) if s in SERVICOS_REGULAR]
        if not regular_servicos:
            return [], []
        ts = _tipo_servico_str(regular_servicos)
        regioes_data = api.get_regioes_disponiveis(ts)
        opts = [{"label": r["label"], "value": r["id"]} for r in regioes_data]
        return opts, []

    # ── Opções de empresa em cascata (filtro global) ──────────────────────────
    @app.callback(
        Output("filtro-empresa", "options"),
        Output("filtro-empresa", "value"),
        Input("filtro-servico", "value"),
        Input("filtro-regiao", "value"),
        prevent_initial_call=False,
    )
    def update_empresas_opcoes(servicos, regioes):
        ts = _tipo_servico_str([s for s in (servicos or []) if s in SERVICOS_REGULAR])
        if not ts:
            return [], []
        regioes_str = _tipo_servico_str(regioes)
        rows = api.get_empresas_lista(ts, regioes=regioes_str)
        opts = [{"label": r["nome"], "value": r["id"]} for r in rows]
        return opts, []

    # ── Evolução mensal ───────────────────────────────────────────────────────
    @app.callback(
        Output("g-evolucao", "figure"),
        Input("filtro-ano", "value"),
        Input("filtro-meses", "value"),
        Input("filtro-servico", "value"),
        Input("filtro-regiao", "value"),
        Input("filtro-empresa", "value"),
        Input("filtro-assunto", "value"),
        prevent_initial_call=False,
    )
    def update_evolucao(ano, meses, servicos, regioes, empresa_ids, assuntos):
        if ano is None:
            return _fig_vazia()
        ts = _tipo_servico_str(servicos)
        regioes_str = _tipo_servico_str(regioes)
        perm_ids = _perm_ids_str(empresa_ids)
        rows = api.get_evolucao_mensal(
            ano, _meses_str(meses or []), ts,
            regioes=regioes_str, perm_ids=perm_ids, assuntos=_assuntos_str(assuntos),
        )
        return _scatter_evolucao(rows) if rows else _fig_vazia()

    # ── Pizza de assuntos ─────────────────────────────────────────────────────
    @app.callback(
        Output("g-pizza", "figure"),
        Output("filtro-sort-assunto-g5", "options"),
        Output("filtro-sort-assunto-g8", "options"),
        Output("filtro-assunto", "options"),
        Input("filtro-ano", "value"),
        Input("filtro-meses", "value"),
        Input("filtro-servico", "value"),
        Input("filtro-regiao", "value"),
        Input("filtro-empresa", "value"),
        Input("filtro-assunto", "value"),
        prevent_initial_call=False,
    )
    def update_pizza(ano, meses, servicos, regioes, empresa_ids, assuntos):
        if ano is None:
            return _fig_vazia(), [], [], []
        ts = _tipo_servico_str(servicos)
        regioes_str = _tipo_servico_str(regioes)
        perm_ids = _perm_ids_str(empresa_ids)
        rows = api.get_assuntos_pizza(ano, _meses_str(meses or []), ts, regioes=regioes_str, perm_ids=perm_ids)
        if not rows:
            return _fig_vazia(), [], [], []
        opts = [{"label": r["assunto"], "value": r["assunto"]} for r in rows]
        labels_full = [r["assunto"] for r in rows]
        values_full = [r["total"] for r in rows]
        if not assuntos:
            return _pizza(labels_full, values_full), opts, opts, opts
        if len(assuntos) == 1:
            return _pizza(labels_full, values_full, assunto_destaque=assuntos[0]), opts, opts, opts
        assuntos_set = set(assuntos)
        rows_sel = [r for r in rows if r["assunto"] in assuntos_set]
        if not rows_sel:
            return _fig_vazia(), opts, opts, opts
        return _pizza([r["assunto"] for r in rows_sel], [r["total"] for r in rows_sel]), opts, opts, opts

    # ── G3: Empresas por pontuação ────────────────────────────────────────────
    @app.callback(
        Output("g3-empresas", "figure"),
        Input("filtro-ano", "value"),
        Input("filtro-meses", "value"),
        Input("filtro-servico", "value"),
        Input("filtro-regiao", "value"),
        Input("filtro-empresa", "value"),
        Input("filtro-empresa", "options"),
        Input("filtro-assunto", "value"),
        prevent_initial_call=False,
    )
    def update_empresas(ano, meses, servicos, regioes, empresa_ids, empresa_opts, assuntos):
        if ano is None or not _tem_regular(servicos):
            return _fig_vazia()
        ts = _tipo_servico_str([s for s in servicos if s in SERVICOS_REGULAR])
        regioes_str = _tipo_servico_str(regioes)
        empresa_nomes = _empresa_nomes_from_opts(empresa_ids, empresa_opts)

        rows = api.get_empresas_pontuacao(
            ano, _meses_str(meses or []), ts,
            regioes=regioes_str,
            assuntos=_assuntos_str(assuntos),
        )
        if not rows and not empresa_nomes:
            return _fig_vazia()

        rows_s = sorted(rows, key=lambda r: r["pontuacao"], reverse=True)

        if empresa_nomes:
            empresa_nomes_set = set(empresa_nomes)
            selecionadas = sorted(
                [r for r in rows_s if r["empresa"] in empresa_nomes_set],
                key=lambda r: r["pontuacao"], reverse=True,
            )
            outras = [r for r in rows_s if r["empresa"] not in empresa_nomes_set]
            encontradas = {r["empresa"] for r in selecionadas}
            for nome in empresa_nomes:
                if nome not in encontradas:
                    selecionadas.append({"empresa": nome, "pontuacao": 0.0,
                                         "num_reclamacoes": 0, "linha_top": "–", "assunto_top": "–"})
            rows_final = selecionadas + outras
            cores = ["#1a73e8" if r["empresa"] in empresa_nomes_set else "#e53935" for r in rows_final]
        else:
            rows_final = rows_s
            cores = "#e53935"

        if not rows_final:
            return _fig_vazia()

        nomes = [r["empresa"] for r in rows_final]
        vals  = [r["pontuacao"] for r in rows_final]
        cd    = [[r["linha_top"], r["assunto_top"]] for r in rows_final]
        hover = (
            "<b>%{y}</b><br>Pontuação: %{x:.2f}<br>"
            "Linha top: %{customdata[0]}<br>Assunto top: %{customdata[1]}<extra></extra>"
        )
        return _barra_horizontal(nomes, vals, cores, n_items=len(nomes),
                                 customdata=cd, hovertemplate=hover)

    # ── G4: Empresas por incidência irregular ─────────────────────────────────
    @app.callback(
        Output("g4-irregular", "figure"),
        Input("filtro-ano", "value"),
        Input("filtro-meses", "value"),
        Input("filtro-servico", "value"),
        Input("filtro-regiao", "value"),
        Input("filtro-empresa", "value"),
        Input("filtro-empresa", "options"),
        prevent_initial_call=False,
    )
    def update_irregular_empresa(ano, meses, servicos, regioes, empresa_ids, empresa_opts):
        if ano is None or not _tem_regular(servicos):
            return _fig_vazia()
        ts = _tipo_servico_str([s for s in servicos if s in SERVICOS_REGULAR])
        regioes_str = _tipo_servico_str(regioes)
        empresa_nomes = _empresa_nomes_from_opts(empresa_ids, empresa_opts)

        rows = api.get_empresas_irregular(ano, _meses_str(meses or []), ts, regioes=regioes_str)
        if not rows and not empresa_nomes:
            return _fig_vazia()

        rows_s = sorted(rows, key=lambda r: r["pontuacao"], reverse=True)

        if empresa_nomes:
            empresa_nomes_set = set(empresa_nomes)
            selecionadas_raw = sorted(
                [r for r in rows_s if r["empresa"] in empresa_nomes_set],
                key=lambda r: r["pontuacao"], reverse=True,
            )
            outras = [r for r in rows_s if r["empresa"] not in empresa_nomes_set]
            encontradas = {r["empresa"] for r in selecionadas_raw}
            selecionadas = []
            for r in selecionadas_raw:
                if r["pontuacao"] == 0:
                    selecionadas.append({
                        "empresa": f"{r['empresa']} — Sem registro de denúncia por transporte irregular",
                        "pontuacao": 0.0, "linha_top": "–",
                    })
                else:
                    selecionadas.append(r)
            for nome in empresa_nomes:
                if nome not in encontradas:
                    selecionadas.append({
                        "empresa": f"{nome} — Sem registro de denúncia por transporte irregular",
                        "pontuacao": 0.0, "linha_top": "–",
                    })
            rows_final = selecionadas + outras
            n_sel = len(selecionadas)
            cores = ["#1a73e8" if i < n_sel else "#e53935" for i in range(len(rows_final))]
        else:
            rows_final = rows_s
            cores = "#e53935"

        if not rows_final:
            return _fig_vazia()

        nomes = [r["empresa"] for r in rows_final]
        vals  = [r["pontuacao"] for r in rows_final]
        cd    = [[r["linha_top"]] for r in rows_final]
        hover = (
            "<b>%{y}</b><br>Pontuação Irregular: %{x:.2f}<br>"
            "Linha mais prejudicada: %{customdata[0]}<extra></extra>"
        )
        return _barra_horizontal(nomes, vals, cores, n_items=len(nomes),
                                 customdata=cd, hovertemplate=hover)

    # ── G5: Paginação ─────────────────────────────────────────────────────────
    @app.callback(
        Output("g5-pagina", "data"),
        Input("g5-prev", "n_clicks"),
        Input("g5-next", "n_clicks"),
        State("g5-pagina", "data"),
        State("filtro-ano", "value"),
        State("filtro-meses", "value"),
        State("filtro-servico", "value"),
        State("filtro-regiao", "value"),
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

    # ── G5: Heatmap empresa ───────────────────────────────────────────────────
    @app.callback(
        Output("g5-heatmap-empresa", "figure"),
        Output("g5-info", "children"),
        Input("filtro-ano", "value"),
        Input("filtro-meses", "value"),
        Input("filtro-servico", "value"),
        Input("filtro-regiao", "value"),
        Input("filtro-empresa", "value"),
        Input("filtro-empresa", "options"),
        Input("filtro-sort-assunto-g5", "value"),
        Input("g5-pagina", "data"),
        prevent_initial_call=False,
    )
    def update_heatmap_empresa(ano, meses, servicos, regioes, empresa_ids, empresa_opts, sort_assuntos, pagina):
        if ano is None or not _tem_regular(servicos):
            return _fig_vazia(), ""
        ts = _tipo_servico_str([s for s in servicos if s in SERVICOS_REGULAR])
        regioes_str = _tipo_servico_str(regioes)
        empresa_nomes = _empresa_nomes_from_opts(empresa_ids, empresa_opts)

        resp = api.get_heatmap_assunto_empresa(
            ano, _meses_str(meses or []), ts, pagina=pagina or 1, regioes=regioes_str
        )
        dados = resp.get("dados", [])
        total_pags = resp.get("total_paginas", 1)
        pag_atual  = resp.get("pagina", 1)
        zmax       = resp.get("zmax_global")

        return (
            _heatmap_empresa(dados, zmax=zmax, sort_assuntos=sort_assuntos,
                             empresas_destaque=empresa_nomes or None),
            f"Página {pag_atual} de {total_pags}",
        )

    # ── G6: Paginação ─────────────────────────────────────────────────────────
    @app.callback(
        Output("g6-pagina", "data"),
        Input("g6-prev", "n_clicks"),
        Input("g6-next", "n_clicks"),
        State("g6-pagina", "data"),
        State("filtro-ano", "value"),
        State("filtro-meses", "value"),
        State("filtro-servico", "value"),
        State("filtro-regiao", "value"),
        State("filtro-empresa", "value"),
        State("filtro-assunto", "value"),
        prevent_initial_call=True,
    )
    def pagina_g6(prev_c, next_c, pagina, ano, meses, servicos, regioes, empresa_ids, assuntos):
        ts = _tipo_servico_str([s for s in servicos if s in SERVICOS_REGULAR])
        regioes_str = _tipo_servico_str(regioes)
        perm_ids = _perm_ids_str(empresa_ids)
        resp = api.get_autos_pontuacao(
            ano, _meses_str(meses or []), ts, pagina=pagina,
            regioes=regioes_str, perm_ids=perm_ids, assuntos=_assuntos_str(assuntos),
        )
        total = resp.get("total_paginas", 1)
        if ctx.triggered_id and "prev" in ctx.triggered_id:
            return max(1, pagina - 1)
        if ctx.triggered_id and "next" in ctx.triggered_id:
            return min(total, pagina + 1)
        return pagina

    # ── G6: Autos por pontuação ───────────────────────────────────────────────
    @app.callback(
        Output("g6-autos", "figure"),
        Output("g6-info", "children"),
        Input("filtro-ano", "value"),
        Input("filtro-meses", "value"),
        Input("filtro-servico", "value"),
        Input("filtro-regiao", "value"),
        Input("filtro-empresa", "value"),
        Input("filtro-assunto", "value"),
        Input("g6-pagina", "data"),
        prevent_initial_call=False,
    )
    def update_autos_pontuacao(ano, meses, servicos, regioes, empresa_ids, assuntos, pagina):
        if ano is None or not _tem_regular(servicos):
            return _fig_vazia(), ""
        ts = _tipo_servico_str([s for s in servicos if s in SERVICOS_REGULAR])
        regioes_str = _tipo_servico_str(regioes)
        perm_ids = _perm_ids_str(empresa_ids)
        resp = api.get_autos_pontuacao(
            ano, _meses_str(meses or []), ts, pagina=pagina or 1,
            regioes=regioes_str, perm_ids=perm_ids, assuntos=_assuntos_str(assuntos),
        )
        dados      = resp.get("dados", [])
        total_pags = resp.get("total_paginas", 1)
        pag_atual  = resp.get("pagina", 1)
        xmax       = resp.get("xmax_global")
        if not dados:
            return _fig_vazia(), f"Página {pag_atual} de {total_pags}"
        dados_s = sorted(dados, key=lambda r: r["pontuacao"], reverse=True)
        nomes = [r["auto"] for r in dados_s]
        vals  = [r["pontuacao"] for r in dados_s]
        cd    = [[r["assunto_top"]] for r in dados_s]
        hover = (
            "<b>Auto:</b> %{y}<br>Pontuação: %{x:.2f}<br>"
            "Principal assunto: %{customdata[0]}<extra></extra>"
        )
        return (_barra_horizontal(nomes, vals, "#1a73e8", n_items=len(nomes),
                                  xmax=xmax, customdata=cd, hovertemplate=hover),
                f"Página {pag_atual} de {total_pags}")

    # ── G7: Paginação ─────────────────────────────────────────────────────────
    @app.callback(
        Output("g7-pagina", "data"),
        Input("g7-prev", "n_clicks"),
        Input("g7-next", "n_clicks"),
        State("g7-pagina", "data"),
        State("filtro-ano", "value"),
        State("filtro-meses", "value"),
        State("filtro-servico", "value"),
        State("filtro-regiao", "value"),
        State("filtro-empresa", "value"),
        prevent_initial_call=True,
    )
    def pagina_g7(prev_c, next_c, pagina, ano, meses, servicos, regioes, empresa_ids):
        ts = _tipo_servico_str([s for s in servicos if s in SERVICOS_REGULAR])
        regioes_str = _tipo_servico_str(regioes)
        perm_ids = _perm_ids_str(empresa_ids)
        resp = api.get_autos_irregular(
            ano, _meses_str(meses or []), ts, pagina=pagina,
            regioes=regioes_str, perm_ids=perm_ids,
        )
        total = resp.get("total_paginas", 1)
        if ctx.triggered_id and "prev" in ctx.triggered_id:
            return max(1, pagina - 1)
        if ctx.triggered_id and "next" in ctx.triggered_id:
            return min(total, pagina + 1)
        return pagina

    # ── G7: Autos por incidência irregular ────────────────────────────────────
    @app.callback(
        Output("g7-irregular", "figure"),
        Output("g7-info", "children"),
        Input("filtro-ano", "value"),
        Input("filtro-meses", "value"),
        Input("filtro-servico", "value"),
        Input("filtro-regiao", "value"),
        Input("filtro-empresa", "value"),
        Input("g7-pagina", "data"),
        prevent_initial_call=False,
    )
    def update_autos_irregular(ano, meses, servicos, regioes, empresa_ids, pagina):
        if ano is None or not _tem_regular(servicos):
            return _fig_vazia(), ""
        ts = _tipo_servico_str([s for s in servicos if s in SERVICOS_REGULAR])
        regioes_str = _tipo_servico_str(regioes)
        perm_ids = _perm_ids_str(empresa_ids)
        resp = api.get_autos_irregular(
            ano, _meses_str(meses or []), ts, pagina=pagina or 1,
            regioes=regioes_str, perm_ids=perm_ids,
        )
        dados      = resp.get("dados", [])
        total_pags = resp.get("total_paginas", 1)
        pag_atual  = resp.get("pagina", 1)
        xmax       = resp.get("xmax_global")
        if not dados:
            msg = (
                "Não há registros de autos de linha com vulnerabilidade ao transporte "
                "irregular para as empresas filtradas."
                if perm_ids else "Sem dados para o período"
            )
            return _fig_vazia(msg), f"Página {pag_atual} de {total_pags}"
        dados_s = sorted(dados, key=lambda r: r["pontuacao"], reverse=True)
        nomes = [r["auto"] for r in dados_s]
        vals  = [r["pontuacao"] for r in dados_s]
        hover = "<b>Auto:</b> %{y}<br>Pontuação Irregular: %{x:.2f}<extra></extra>"
        return (_barra_horizontal(nomes, vals, "#1a73e8", n_items=len(nomes),
                                  xmax=xmax, hovertemplate=hover),
                f"Página {pag_atual} de {total_pags}")

    # ── G8: Paginação ─────────────────────────────────────────────────────────
    @app.callback(
        Output("g8-pagina", "data"),
        Input("g8-prev", "n_clicks"),
        Input("g8-next", "n_clicks"),
        State("g8-pagina", "data"),
        State("filtro-ano", "value"),
        State("filtro-meses", "value"),
        State("filtro-servico", "value"),
        State("filtro-empresa", "value"),
        State("filtro-regiao", "value"),
        prevent_initial_call=True,
    )
    def pagina_g8(prev_c, next_c, pagina, ano, meses, servicos, empresa_ids, regioes):
        ts = _tipo_servico_str([s for s in servicos if s in SERVICOS_REGULAR])
        perm_ids = _perm_ids_str(empresa_ids)
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

    # ── G8: Heatmap auto ──────────────────────────────────────────────────────
    @app.callback(
        Output("g8-heatmap-auto", "figure"),
        Output("g8-info", "children"),
        Input("filtro-ano", "value"),
        Input("filtro-meses", "value"),
        Input("filtro-servico", "value"),
        Input("filtro-empresa", "value"),
        Input("filtro-regiao", "value"),
        Input("filtro-sort-assunto-g8", "value"),
        Input("g8-pagina", "data"),
        prevent_initial_call=False,
    )
    def update_heatmap_auto(ano, meses, servicos, empresa_ids, regioes, sort_assuntos, pagina):
        if ano is None or not _tem_regular(servicos):
            return _fig_vazia(), ""
        ts = _tipo_servico_str([s for s in servicos if s in SERVICOS_REGULAR])
        perm_ids = _perm_ids_str(empresa_ids)
        regioes_str = _tipo_servico_str(regioes)
        resp = api.get_heatmap_assunto_auto(
            ano, _meses_str(meses or []), ts, perm_ids or None, pagina=pagina or 1, regioes=regioes_str
        )
        dados      = resp.get("dados", [])
        total_pags = resp.get("total_paginas", 1)
        pag_atual  = resp.get("pagina", 1)
        zmax       = resp.get("zmax_global")
        return (_heatmap_auto(dados, zmax=zmax, sort_assuntos=sort_assuntos),
                f"Página {pag_atual} de {total_pags}")

    # ── Locais de embarque/desembarque: Paginação ─────────────────────────────
    @app.callback(
        Output("g-pagina-locais", "data"),
        Input("g-locais-prev", "n_clicks"),
        Input("g-locais-next", "n_clicks"),
        State("g-pagina-locais", "data"),
        State("filtro-ano", "value"),
        State("filtro-meses", "value"),
        State("filtro-servico", "value"),
        State("filtro-tipo-local", "value"),
        State("filtro-regiao", "value"),
        State("filtro-empresa", "value"),
        State("filtro-assunto", "value"),
        prevent_initial_call=True,
    )
    def pagina_locais(prev_c, next_c, pagina, ano, meses, servicos, tipo_local, regioes, empresa_ids, assuntos):
        ts = _tipo_servico_str(servicos)
        regioes_str = _tipo_servico_str(regioes)
        perm_ids = _perm_ids_str(empresa_ids)
        resp = api.get_locais_embarque(
            ano, _meses_str(meses or []), ts, tipo_local, pagina=pagina,
            regioes=regioes_str, perm_ids=perm_ids, assuntos=_assuntos_str(assuntos),
        )
        total = resp.get("total_paginas", 1)
        if ctx.triggered_id and "prev" in ctx.triggered_id:
            return max(1, pagina - 1)
        if ctx.triggered_id and "next" in ctx.triggered_id:
            return min(total, pagina + 1)
        return pagina

    # ── Locais de embarque/desembarque: Gráfico ───────────────────────────────
    @app.callback(
        Output("g-locais", "figure"),
        Output("g-locais-info", "children"),
        Input("filtro-ano", "value"),
        Input("filtro-meses", "value"),
        Input("filtro-servico", "value"),
        Input("filtro-tipo-local", "value"),
        Input("filtro-regiao", "value"),
        Input("filtro-empresa", "value"),
        Input("filtro-assunto", "value"),
        Input("g-pagina-locais", "data"),
        prevent_initial_call=False,
    )
    def update_locais(ano, meses, servicos, tipo_local, regioes, empresa_ids, assuntos, pagina):
        if ano is None:
            return _fig_vazia(), ""
        ts = _tipo_servico_str(servicos)
        regioes_str = _tipo_servico_str(regioes)
        perm_ids = _perm_ids_str(empresa_ids)
        resp = api.get_locais_embarque(
            ano, _meses_str(meses or []), ts, tipo_local, pagina=pagina or 1,
            regioes=regioes_str, perm_ids=perm_ids, assuntos=_assuntos_str(assuntos),
        )
        dados      = resp.get("dados", [])
        total_pags = resp.get("total_paginas", 1)
        pag_atual  = resp.get("pagina", 1)
        xmax       = resp.get("xmax_global")
        if not dados:
            return _fig_vazia(), f"Página {pag_atual} de {total_pags}"
        dados_s = sorted(dados, key=lambda r: r["total"], reverse=True)
        nomes = [r["local"] for r in dados_s]
        vals  = [r["total"] for r in dados_s]
        cd    = [[r["assunto_top"]] for r in dados_s]
        hover = (
            "<b>%{y}</b><br>Reclamações: %{x}<br>"
            "Principal assunto: %{customdata[0]}<extra></extra>"
        )
        return (_barra_horizontal(nomes, vals, "#1a73e8", n_items=len(nomes),
                                  xmax=xmax, customdata=cd, hovertemplate=hover),
                f"Página {pag_atual} de {total_pags}")

    # ── KPI Cards: valores dos 7 primeiros + aviso ────────────────────────────
    @app.callback(
        Output("kpi-val-1", "children"),
        Output("kpi-val-2", "children"),
        Output("kpi-sub-2", "children"),
        Output("kpi-val-3", "children"),
        Output("kpi-sub-3", "children"),
        Output("kpi-label-3", "children"),
        Output("kpi-val-4", "children"),
        Output("kpi-sub-4", "children"),
        Output("kpi-val-5", "children"),
        Output("kpi-sub-5", "children"),
        Output("kpi-val-6", "children"),
        Output("kpi-sub-6", "children"),
        Output("kpi-val-7", "children"),
        Output("kpi-sub-7", "children"),
        Output("aviso-sem-dados", "children"),
        Output("store-loading", "data", allow_duplicate=True),
        Input("filtro-ano", "value"),
        Input("filtro-meses", "value"),
        Input("filtro-servico", "value"),
        Input("filtro-regiao", "value"),
        Input("filtro-empresa", "value"),
        Input("filtro-empresa", "options"),
        Input("filtro-assunto", "value"),
        Input("filtro-tipo-local", "value"),
        prevent_initial_call="initial_duplicate",
    )
    def update_kpi_cards(ano, meses, servicos, regioes, empresa_ids, empresa_opts, assuntos, tipo_local):
        vazio = "—"
        label_card3 = "Embarque Mais Crítico" if (tipo_local or "embarque") == "embarque" else "Desembarque Mais Crítico"

        if ano is None:
            return (vazio, vazio, "", vazio, "", label_card3,
                    vazio, "", vazio, "", vazio, "", vazio, "", "", False)

        ts = _tipo_servico_str(servicos)
        regioes_str = _tipo_servico_str(regioes)
        perm_ids = _perm_ids_str(empresa_ids)
        meses_str = _meses_str(meses or [])
        assuntos_str = _assuntos_str(assuntos)
        tem_reg = _tem_regular(servicos)
        empresa_nomes = _empresa_nomes_from_opts(empresa_ids, empresa_opts)
        empresa_nomes_set = set(empresa_nomes)
        ts_reg = _tipo_servico_str([s for s in (servicos or []) if s in SERVICOS_REGULAR]) if tem_reg else None

        # Busca paralela de todos os endpoints necessários
        with ThreadPoolExecutor(max_workers=6) as ex:
            f_resumo = ex.submit(
                api.get_resumo, ano, meses_str, ts,
                regioes=regioes_str, perm_ids=perm_ids, assuntos=assuntos_str,
            )
            f_locais = ex.submit(
                api.get_locais_embarque, ano, meses_str, ts, tipo_local or "embarque",
                pagina=1, regioes=regioes_str, perm_ids=perm_ids, assuntos=assuntos_str,
            )
            f_emp_pont = ex.submit(
                api.get_empresas_pontuacao, ano, meses_str, ts_reg,
                regioes=regioes_str, assuntos=assuntos_str,
            ) if tem_reg else None
            f_emp_irr = ex.submit(
                api.get_empresas_irregular, ano, meses_str, ts_reg,
                regioes=regioes_str,
            ) if tem_reg else None
            f_aut_pont = ex.submit(
                api.get_autos_pontuacao, ano, meses_str, ts_reg, pagina=1,
                regioes=regioes_str, perm_ids=perm_ids, assuntos=assuntos_str,
            ) if tem_reg else None
            f_aut_irr = ex.submit(
                api.get_autos_irregular, ano, meses_str, ts_reg, pagina=1,
                regioes=regioes_str, perm_ids=perm_ids,
            ) if tem_reg else None

        # Card 1 e 2: resumo geral
        resumo = f_resumo.result()
        total = resumo.get("total_reclamacoes", 0) or 0
        aviso = _aviso_sem_dados() if total == 0 else ""
        card1_val = f"{total:,}".replace(",", ".") if total else "0"
        if total > 0 and resumo.get("assunto_top"):
            card2_val = resumo["assunto_top"]
            card2_sub = f"{resumo.get('assunto_top_qty', 0):,} ocorrências".replace(",", ".")
        else:
            card2_val, card2_sub = vazio, ""

        # Card 3: local crítico (embarque/desembarque)
        try:
            resp_loc = f_locais.result()
            loc_dados = resp_loc.get("dados", [])
            if loc_dados:
                top_loc = loc_dados[0]
                card3_val = top_loc.get("local", vazio)
                card3_sub = f"{top_loc.get('total', 0):,} reclamações".replace(",", ".")
            else:
                card3_val, card3_sub = vazio, ""
        except Exception:
            card3_val, card3_sub = vazio, ""

        # Cards 4-7: dependem de Regular
        card4_val = card5_val = vazio
        card4_sub = card5_sub = ""
        card6_val = card7_val = vazio
        card6_sub = card7_sub = ""

        if tem_reg:
            # Card 4: empresa mais reclamada
            try:
                emp_rows = f_emp_pont.result()
                if empresa_nomes_set:
                    emp_rows = [r for r in emp_rows if r.get("empresa") in empresa_nomes_set]
                if emp_rows:
                    top4 = max(emp_rows, key=lambda r: r.get("pontuacao", 0))
                    card4_val = top4.get("empresa", vazio)
                    card4_sub = f"Pontuação: {top4.get('pontuacao', 0):.2f}"
            except Exception:
                pass

            # Card 5: empresa mais vulnerável
            try:
                vul_rows = f_emp_irr.result()
                if empresa_nomes_set:
                    vul_rows = [r for r in vul_rows if r.get("empresa") in empresa_nomes_set]
                if vul_rows:
                    top5 = max(vul_rows, key=lambda r: r.get("pontuacao", 0))
                    card5_val = top5.get("empresa", vazio)
                    card5_sub = f"Vulnerabilidade: {top5.get('pontuacao', 0):.2f}"
            except Exception:
                pass

            # Card 6: auto mais reclamado
            try:
                resp_a = f_aut_pont.result()
                a_dados = resp_a.get("dados", [])
                if a_dados:
                    top6 = a_dados[0]
                    card6_val = f"Auto {top6.get('auto', vazio)}"
                    partes = [str(top6.get("empresa") or "")]
                    if top6.get("regiao") and top6["regiao"] != "–":
                        partes.append(str(top6["regiao"]))
                    partes.append(f"Pts: {top6.get('pontuacao', 0):.2f}")
                    card6_sub = " — ".join(p for p in partes if p)
            except Exception:
                pass

            # Card 7: auto mais vulnerável
            try:
                resp_i = f_aut_irr.result()
                i_dados = resp_i.get("dados", [])
                if i_dados:
                    top7 = i_dados[0]
                    card7_val = f"Auto {top7.get('auto', vazio)}"
                    partes = [str(top7.get("empresa") or "")]
                    if top7.get("regiao") and top7["regiao"] != "–":
                        partes.append(str(top7["regiao"]))
                    partes.append(f"Vuln: {top7.get('pontuacao', 0):.2f}")
                    card7_sub = " — ".join(p for p in partes if p)
            except Exception:
                pass

        return (
            card1_val,
            card2_val, card2_sub,
            card3_val, card3_sub, label_card3,
            card4_val, card4_sub,
            card5_val, card5_sub,
            card6_val, card6_sub,
            card7_val, card7_sub,
            aviso,
            False,  # desativa overlay ao concluir
        )

    # ── Clique em card → atualiza card-ativo ──────────────────────────────────
    @app.callback(
        Output("card-ativo", "data"),
        Input({"type": "kpi-card", "index": ALL}, "n_clicks"),
        State("filtro-servico", "value"),
        State("card-ativo", "data"),
        prevent_initial_call=True,
    )
    def set_card_ativo(nclicks_list, servicos, atual):
        if not nclicks_list or not any(nclicks_list):
            return no_update
        triggered = ctx.triggered_id
        if not isinstance(triggered, dict):
            return no_update
        idx = triggered.get("index")
        if idx is None:
            return no_update
        # Bloqueia clique em cards Regular-only quando filtro = só Fretamento
        if idx in (4, 5, 6, 7, 8, 9) and not _tem_regular(servicos):
            return no_update
        return idx

    # ── Toggle: gráfico ativo + classes dos cards ─────────────────────────────
    @app.callback(
        Output("wrap-g1", "style"),
        Output("wrap-g2", "style"),
        Output("wrap-g3", "style"),
        Output("wrap-g4", "style"),
        Output("wrap-g5", "style"),
        Output("wrap-g6", "style"),
        Output("wrap-g7", "style"),
        Output("wrap-g8", "style"),
        Output("wrap-g9", "style"),
        Output({"type": "kpi-card", "index": ALL}, "className"),
        Input("card-ativo", "data"),
        Input("filtro-servico", "value"),
        State({"type": "kpi-card", "index": ALL}, "id"),
        prevent_initial_call=False,
    )
    def toggle_grafico_e_cards(ativo, servicos, all_ids):
        tem_reg = _tem_regular(servicos)
        # Se ativo está desabilitado, mostra wrap-g1 visualmente (sem alterar Store)
        ativo_efetivo = 1 if (ativo in (4, 5, 6, 7, 8, 9) and not tem_reg) else (ativo or 1)

        wrap_styles = []
        for i in range(1, 10):
            if i == ativo_efetivo:
                wrap_styles.append({"display": "flex", "flexDirection": "column", "height": "100%"})
            else:
                wrap_styles.append({"display": "none"})

        classnames = []
        indices = [d.get("index") for d in (all_ids or [])]
        for idx in indices:
            classes = ["kpi-card"]
            if idx == ativo_efetivo:
                classes.append("active")
            if not tem_reg and idx in (4, 5, 6, 7, 8, 9):
                classes.append("disabled")
            if idx in (8, 9):
                classes.append("only-button")
            classnames.append(" ".join(classes))

        return (*wrap_styles, classnames)
