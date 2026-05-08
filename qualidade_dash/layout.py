"""Layout do Dash: header, filtros globais e 3 abas."""

import dash_bootstrap_components as dbc
from dash import dcc, html

# ── Constantes de tipo de serviço ─────────────────────────────────────────────

TS_METRO = "Regular – Metropolitano"
TS_INTER = "Regular – Intermunicipal"
TS_FRETA = "Fretamento Intermunicipal,Fretamento Metropolitano"

NOMES_MESES = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}

# ── Estilos base ──────────────────────────────────────────────────────────────

CARD_STYLE = {
    "backgroundColor": "white",
    "borderRadius": "10px",
    "boxShadow": "0 2px 8px rgba(0,0,0,0.08)",
    "padding": "20px",
    "marginBottom": "16px",
}

GRAPH_CONFIG = {"responsive": True, "displayModeBar": False}

LAYOUT_PLOTLY = dict(
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(family="Segoe UI, Arial, sans-serif", size=12),
    hoverlabel=dict(bgcolor="#333", font_color="white", font_size=13),
)

# Escala de cores para heatmaps (verde suave → vermelho suave)
HEATMAP_COLORSCALE = [
    [0.0, "#d4edda"],
    [0.33, "#fff3cd"],
    [0.66, "#ffd0b5"],
    [1.0, "#f5a6a6"],
]


# ── Componentes de filtro global ──────────────────────────────────────────────

def _filtros_globais(tab_id: str):
    return dbc.Card(
        dbc.CardBody(
            dbc.Row([
                dbc.Col([
                    html.Label("Ano", className="fw-semibold mb-1"),
                    dcc.Dropdown(
                        id=f"filtro-ano-{tab_id}",
                        clearable=False,
                        style={"minWidth": "120px"},
                    ),
                ], xs=12, sm=6, md=3, lg=2),
                dbc.Col([
                    html.Label("Meses", className="fw-semibold mb-1"),
                    dcc.Dropdown(
                        id=f"filtro-meses-{tab_id}",
                        multi=True,
                        placeholder="Todos os meses",
                        style={"minWidth": "220px"},
                    ),
                ], xs=12, sm=6, md=6, lg=5),
            ], className="g-3 align-items-end"),
        ),
        style=CARD_STYLE,
    )


def _filtro_empresas_g8(tab_id: str):
    return dbc.Card(
        dbc.CardBody([
            html.Label("Filtrar por Empresa (Gráfico Heatmap Autos)", className="fw-semibold mb-1"),
            dcc.Dropdown(
                id=f"filtro-empresas-g8-{tab_id}",
                multi=True,
                placeholder="Todas as empresas",
            ),
        ]),
        style={**CARD_STYLE, "marginBottom": "8px"},
    )


# ── Cards de resumo ───────────────────────────────────────────────────────────

def _cards_resumo(tab_id: str, cor_total: str = "#1a73e8", fundo_total: str = "#e8f0fe"):
    return dbc.Row([
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.P("Total de Reclamações", className="text-muted mb-1", style={"fontSize": "13px"}),
                    html.H2(id=f"card-total-{tab_id}", className="fw-bold mb-0",
                            style={"color": cor_total, "fontSize": "2.5rem"}),
                ]),
                style={**CARD_STYLE, "backgroundColor": fundo_total, "marginBottom": "0"},
            ),
            xs=12, md=6,
        ),
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.P("Assunto Mais Reclamado", className="text-muted mb-1", style={"fontSize": "13px"}),
                    html.H4(id=f"card-assunto-{tab_id}", className="fw-bold mb-1",
                            style={"color": "#e8720c"}),
                    html.P(id=f"card-assunto-qty-{tab_id}", className="text-muted mb-0",
                           style={"fontSize": "13px"}),
                ]),
                style={**CARD_STYLE, "backgroundColor": "#fff3e0", "marginBottom": "0"},
            ),
            xs=12, md=6,
        ),
    ], className="mb-3")


# ── Paginação ─────────────────────────────────────────────────────────────────

def _paginacao(prefix: str):
    return dbc.Row([
        dbc.Col(
            dbc.Button("← Anterior", id=f"{prefix}-prev", color="light", size="sm", n_clicks=0),
            width="auto",
        ),
        dbc.Col(
            html.Span(id=f"{prefix}-info", className="text-muted", style={"fontSize": "13px"}),
            className="d-flex align-items-center",
        ),
        dbc.Col(
            dbc.Button("Próxima →", id=f"{prefix}-next", color="light", size="sm", n_clicks=0),
            width="auto",
        ),
    ], className="justify-content-center align-items-center g-2 mt-1")


# ── Graficos em card ──────────────────────────────────────────────────────────

def _graph_card(graph_id: str, titulo: str, extra: list | None = None):
    children = [html.H6(titulo, className="fw-semibold text-secondary mb-3")]
    if extra:
        children += extra
    children.append(dcc.Graph(id=graph_id, config=GRAPH_CONFIG))
    return dbc.Card(dbc.CardBody(children), style=CARD_STYLE)


# ── Layout de aba regular (Metropolitano ou Intermunicipal) ───────────────────

def _aba_regular(tab_id: str):
    return html.Div([
        _filtros_globais(tab_id),
        _cards_resumo(tab_id),
        html.Div(id=f"aviso-sem-dados-{tab_id}"),

        # G1: Evolução mensal
        _graph_card(f"g1-evolucao-{tab_id}", "Evolução Mensal das Reclamações"),

        # G2: Pizza assuntos
        _graph_card(f"g2-pizza-{tab_id}", "Reclamações por Assunto"),

        # G3: Empresas por pontuação
        _graph_card(f"g3-empresas-{tab_id}", "Incidência de Reclamação do Serviço"),

        # G4: Empresas por incidência irregular
        _graph_card(f"g4-irregular-{tab_id}", "Incidência de Transporte Irregular por Empresa"),

        # G5: Heatmap assunto × empresa (paginado)
        dbc.Card(dbc.CardBody([
            html.H6("Mapa de Calor — Pontuação por Assunto × Empresa",
                    className="fw-semibold text-secondary mb-3"),
            dcc.Store(id=f"g5-pagina-{tab_id}", data=1),
            dcc.Graph(id=f"g5-heatmap-empresa-{tab_id}", config=GRAPH_CONFIG),
            _paginacao(f"g5-{tab_id}"),
        ]), style=CARD_STYLE),

        # G6: Autos por pontuação (paginado)
        dbc.Card(dbc.CardBody([
            html.H6("Incidência de Reclamação do Serviço por Autos de Linha", className="fw-semibold text-secondary mb-3"),
            dcc.Store(id=f"g6-pagina-{tab_id}", data=1),
            dcc.Graph(id=f"g6-autos-{tab_id}", config=GRAPH_CONFIG),
            _paginacao(f"g6-{tab_id}"),
        ]), style=CARD_STYLE),

        # G7: Autos por incidência irregular (paginado)
        dbc.Card(dbc.CardBody([
            html.H6("Autos por Incidência de Transporte Irregular",
                    className="fw-semibold text-secondary mb-3"),
            dcc.Store(id=f"g7-pagina-{tab_id}", data=1),
            dcc.Graph(id=f"g7-irregular-{tab_id}", config=GRAPH_CONFIG),
            _paginacao(f"g7-{tab_id}"),
        ]), style=CARD_STYLE),

        # G8: Heatmap assunto × autos (filtro empresa + paginado)
        dbc.Card(dbc.CardBody([
            html.H6("Mapa de Calor — Pontuação por Assunto × Autos",
                    className="fw-semibold text-secondary mb-3"),
            _filtro_empresas_g8(tab_id),
            dcc.Store(id=f"g8-pagina-{tab_id}", data=1),
            dcc.Graph(id=f"g8-heatmap-auto-{tab_id}", config=GRAPH_CONFIG),
            _paginacao(f"g8-{tab_id}"),
        ]), style=CARD_STYLE),
    ])


# ── Layout de aba Fretamento ──────────────────────────────────────────────────

def _aba_fretamento():
    tab_id = "freta"
    return html.Div([
        _filtros_globais(tab_id),
        _cards_resumo(tab_id, cor_total="#6f42c1", fundo_total="#f3e8ff"),
        html.Div(id=f"aviso-sem-dados-{tab_id}"),

        # G0: Evolução mensal
        _graph_card(f"g0-evolucao-{tab_id}", "Evolução Mensal das Reclamações"),

        # G1: Pizza assuntos
        _graph_card(f"g1-pizza-{tab_id}", "Reclamações por Assunto"),

        # G2: Locais de embarque (paginado)
        dbc.Card(dbc.CardBody([
            html.H6("Locais de Embarque Mais Reclamados",
                    className="fw-semibold text-secondary mb-3"),
            dcc.Store(id=f"g2-pagina-{tab_id}", data=1),
            dcc.Graph(id=f"g2-locais-{tab_id}", config=GRAPH_CONFIG),
            _paginacao(f"g2-{tab_id}"),
        ]), style=CARD_STYLE),
    ])


# ── Layout principal ──────────────────────────────────────────────────────────

def build_layout():
    return html.Div(
        style={"backgroundColor": "#f0f2f5", "minHeight": "100vh"},
        children=[
            # Header
            html.Div(
                html.H4(
                    "Painel de Reclamações — Sistema de Transporte",
                    className="mb-0 text-white fw-bold",
                    style={"fontSize": "1.2rem"},
                ),
                style={
                    "backgroundColor": "#1a73e8",
                    "padding": "16px 24px",
                    "position": "sticky",
                    "top": "0",
                    "zIndex": "1000",
                    "boxShadow": "0 2px 6px rgba(0,0,0,0.15)",
                },
            ),

            # Conteúdo principal
            html.Div(
                dcc.Tabs(
                    id="tabs-principal",
                    value="metro",
                    children=[
                        dcc.Tab(
                            label="🚌  Sistema Regular Metropolitano",
                            value="metro",
                            children=[html.Div(_aba_regular("metro"), style={"padding": "20px"})],
                            style={"color": "#555", "backgroundColor": "#e8ecef",
                                   "padding": "10px 20px", "borderBottom": "none"},
                            selected_style={
                                "color": "white", "backgroundColor": "#1565c0",
                                "fontWeight": "600", "padding": "10px 20px",
                                "borderTop": "3px solid #0d47a1",
                                "borderBottom": "none", "borderLeft": "none", "borderRight": "none",
                                "boxShadow": "0 3px 10px rgba(13, 71, 161, 0.3)",
                            },
                        ),
                        dcc.Tab(
                            label="🗺️  Sistema Regular Intermunicipal",
                            value="inter",
                            children=[html.Div(_aba_regular("inter"), style={"padding": "20px"})],
                            style={"color": "#555", "backgroundColor": "#e8ecef",
                                   "padding": "10px 20px", "borderBottom": "none"},
                            selected_style={
                                "color": "white", "backgroundColor": "#1565c0",
                                "fontWeight": "600", "padding": "10px 20px",
                                "borderTop": "3px solid #0d47a1",
                                "borderBottom": "none", "borderLeft": "none", "borderRight": "none",
                                "boxShadow": "0 3px 10px rgba(13, 71, 161, 0.3)",
                            },
                        ),
                        dcc.Tab(
                            label="👥  Fretamento",
                            value="freta",
                            children=[html.Div(_aba_fretamento(), style={"padding": "20px"})],
                            style={"color": "#555", "backgroundColor": "#e8ecef",
                                   "padding": "10px 20px", "borderBottom": "none"},
                            selected_style={
                                "color": "white", "backgroundColor": "#1565c0",
                                "fontWeight": "600", "padding": "10px 20px",
                                "borderTop": "3px solid #0d47a1",
                                "borderBottom": "none", "borderLeft": "none", "borderRight": "none",
                                "boxShadow": "0 3px 10px rgba(13, 71, 161, 0.3)",
                            },
                        ),
                    ],
                    style={"fontFamily": "Segoe UI, Arial, sans-serif"},
                ),
                style={"maxWidth": "1600px", "margin": "0 auto"},
            ),
        ],
    )
