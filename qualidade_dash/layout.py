"""Layout do Dash: header, filtros globais e gráficos unificados."""

import dash_bootstrap_components as dbc
from dash import dcc, html

# ── Constantes de tipo de serviço ─────────────────────────────────────────────

SERVICOS_OPCOES = [
    {"label": "Regular Metropolitano", "value": "Regular – Metropolitano"},
    {"label": "Regular Intermunicipal", "value": "Regular – Intermunicipal"},
    {"label": "Fretamento Intermunicipal", "value": "Fretamento Intermunicipal"},
    {"label": "Fretamento Metropolitano", "value": "Fretamento Metropolitano"},
]
SERVICOS_REGULAR = {"Regular – Metropolitano", "Regular – Intermunicipal"}
SERVICOS_DEFAULT = [s["value"] for s in SERVICOS_OPCOES]  # Todos selecionados

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

HEATMAP_COLORSCALE = [
    [0.0, "#d4edda"],
    [0.33, "#fff3cd"],
    [0.66, "#ffd0b5"],
    [1.0, "#f5a6a6"],
]


# ── Componentes de filtro global ──────────────────────────────────────────────

def _filtros_globais():
    return dbc.Card(
        dbc.CardBody(
            dbc.Row([
                dbc.Col([
                    html.Label("Tipo de Serviço", className="fw-semibold mb-1"),
                    dcc.Dropdown(
                        id="filtro-servico",
                        options=SERVICOS_OPCOES,
                        value=SERVICOS_DEFAULT,
                        multi=True,
                        placeholder="Selecione tipos de serviço",
                        style={"minWidth": "300px"},
                    ),
                ], xs=12, md=4),
                dbc.Col([
                    html.Label("Ano", className="fw-semibold mb-1"),
                    dcc.Dropdown(
                        id="filtro-ano",
                        clearable=False,
                        style={"minWidth": "120px"},
                    ),
                ], xs=12, sm=6, md=2),
                dbc.Col([
                    html.Label("Meses", className="fw-semibold mb-1"),
                    dcc.Dropdown(
                        id="filtro-meses",
                        multi=True,
                        placeholder="Todos os meses",
                        style={"minWidth": "220px"},
                    ),
                ], xs=12, sm=6, md=4),
            ], className="g-3 align-items-end"),
        ),
        style=CARD_STYLE,
    )


# ── Cards de resumo ───────────────────────────────────────────────────────────

def _cards_resumo():
    return dbc.Row([
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.P("Total de Reclamações", className="text-muted mb-1", style={"fontSize": "13px"}),
                    html.H2(id="card-total", className="fw-bold mb-0",
                            style={"color": "#1a73e8", "fontSize": "2.5rem"}),
                ]),
                style={**CARD_STYLE, "backgroundColor": "#e8f0fe", "marginBottom": "0"},
            ),
            xs=12, md=6,
        ),
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.P("Assunto Mais Reclamado", className="text-muted mb-1", style={"fontSize": "13px"}),
                    html.H4(id="card-assunto", className="fw-bold mb-1",
                            style={"color": "#e8720c"}),
                    html.P(id="card-assunto-qty", className="text-muted mb-0",
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


# ── Gráficos em card ──────────────────────────────────────────────────────────

def _graph_card(graph_id: str, titulo: str, extra: list | None = None):
    children = [html.H6(titulo, className="fw-semibold text-secondary mb-3")]
    if extra:
        children += extra
    children.append(dcc.Graph(id=graph_id, config=GRAPH_CONFIG))
    return dbc.Card(dbc.CardBody(children), style=CARD_STYLE)


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
                [
                    # Filtros globais
                    _filtros_globais(),

                    # Cards de resumo
                    _cards_resumo(),
                    html.Div(id="aviso-sem-dados"),

                    # ─────────────────────────────────────────────────────────────────
                    # SEÇÃO COMPARTILHADA (todos os tipos)
                    # ─────────────────────────────────────────────────────────────────

                    # G1: Evolução mensal
                    _graph_card("g-evolucao", "Evolução Mensal das Reclamações"),

                    # G2: Pizza assuntos
                    _graph_card("g-pizza", "Reclamações por Assunto"),

                    # Locais de embarque/desembarque
                    dbc.Card(dbc.CardBody([
                        html.H6("Locais de Embarque/Desembarque Mais Reclamados",
                                className="fw-semibold text-secondary mb-3"),
                        dbc.Row([
                            dbc.Col([
                                html.Label("Tipo de Local", className="fw-semibold mb-1"),
                                dbc.RadioItems(
                                    id="filtro-tipo-local",
                                    options=[
                                        {"label": " Embarque", "value": "embarque"},
                                        {"label": " Desembarque", "value": "desembarque"},
                                    ],
                                    value="embarque",
                                    inline=True,
                                    className="mb-3",
                                ),
                            ], xs=12),
                        ]),
                        dcc.Store(id="g-pagina-locais", data=1),
                        dcc.Graph(id="g-locais", config=GRAPH_CONFIG),
                        _paginacao("g-locais"),
                    ]), style=CARD_STYLE),

                    # ─────────────────────────────────────────────────────────────────
                    # SEÇÃO REGULAR (visibilidade controlada)
                    # ─────────────────────────────────────────────────────────────────
                    html.Div(
                        id="secao-regular",
                        children=[
                            # G3: Empresas por pontuação
                            _graph_card("g3-empresas", "Incidência de Reclamação do Serviço"),

                            # G4: Empresas por incidência irregular
                            _graph_card("g4-irregular", "Indicador de Vulnerabilidade a Transporte Irregular por Empresa"),

                            # G5: Heatmap assunto × empresa
                            dbc.Card(dbc.CardBody([
                                html.H6("Mapa de Calor — Pontuação por Assunto × Empresa",
                                        className="fw-semibold text-secondary mb-3"),
                                dbc.Row([
                                    dbc.Col([
                                        html.Label("Filtrar por Região", className="fw-semibold mb-1"),
                                        dcc.Dropdown(
                                            id="filtro-regioes-g5",
                                            multi=True,
                                            placeholder="Todas as regiões",
                                        ),
                                    ], xs=12, md=6),
                                    dbc.Col([
                                        html.Label("Ordenar por Assunto", className="fw-semibold mb-1"),
                                        dcc.Dropdown(
                                            id="filtro-sort-assunto-g5",
                                            multi=True,
                                            placeholder="Todos os assuntos",
                                        ),
                                    ], xs=12, md=6),
                                ], className="g-3 mb-3"),
                                dcc.Store(id="g5-pagina", data=1),
                                dcc.Graph(id="g5-heatmap-empresa", config=GRAPH_CONFIG),
                                _paginacao("g5"),
                            ]), style=CARD_STYLE),

                            # G6: Autos por pontuação
                            dbc.Card(dbc.CardBody([
                                html.H6("Incidência de Reclamação do Serviço por Autos de Linha",
                                        className="fw-semibold text-secondary mb-3"),
                                dcc.Store(id="g6-pagina", data=1),
                                dcc.Graph(id="g6-autos", config=GRAPH_CONFIG),
                                _paginacao("g6"),
                            ]), style=CARD_STYLE),

                            # G7: Autos por incidência irregular
                            dbc.Card(dbc.CardBody([
                                html.H6("Autos por Vulnerabilidade a Transporte Irregular",
                                        className="fw-semibold text-secondary mb-3"),
                                dcc.Store(id="g7-pagina", data=1),
                                dcc.Graph(id="g7-irregular", config=GRAPH_CONFIG),
                                _paginacao("g7"),
                            ]), style=CARD_STYLE),

                            # G8: Heatmap assunto × autos
                            dbc.Card(dbc.CardBody([
                                html.H6("Mapa de Calor — Pontuação por Assunto × Autos",
                                        className="fw-semibold text-secondary mb-3"),
                                dbc.Row([
                                    dbc.Col([
                                        html.Label("Filtrar por Empresa", className="fw-semibold mb-1"),
                                        dcc.Dropdown(
                                            id="filtro-empresas-g8",
                                            multi=True,
                                            placeholder="Todas as empresas",
                                        ),
                                    ], xs=12, md=4),
                                    dbc.Col([
                                        html.Label("Filtrar por Região", className="fw-semibold mb-1"),
                                        dcc.Dropdown(
                                            id="filtro-regioes-g8",
                                            multi=True,
                                            placeholder="Todas as regiões",
                                        ),
                                    ], xs=12, md=4),
                                    dbc.Col([
                                        html.Label("Ordenar por Assunto", className="fw-semibold mb-1"),
                                        dcc.Dropdown(
                                            id="filtro-sort-assunto-g8",
                                            multi=True,
                                            placeholder="Todos os assuntos",
                                        ),
                                    ], xs=12, md=4),
                                ], className="g-3 mb-3"),
                                dcc.Store(id="g8-pagina", data=1),
                                dcc.Graph(id="g8-heatmap-auto", config=GRAPH_CONFIG),
                                _paginacao("g8"),
                            ]), style=CARD_STYLE),
                        ],
                    ),
                ],
                style={"maxWidth": "1600px", "margin": "0 auto", "padding": "20px"},
            ),
        ],
    )
