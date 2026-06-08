"""Layout do Painel SOUVI — single-screen com cards-botão e gráfico dinâmico."""

import dash_bootstrap_components as dbc
from dash import dcc, html

from qualidade_dash.components import kpi_card_button

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

# ── Cores de destaque dos 9 cards ─────────────────────────────────────────────
CARD_COLORS = {
    1: "#1a73e8",  # Total
    2: "#e8720c",  # Assunto top
    3: "#16a085",  # Local crítico
    4: "#8e44ad",  # Empresa mais reclamada
    5: "#c0392b",  # Empresa mais vulnerável
    6: "#2980b9",  # Auto mais reclamado
    7: "#d35400",  # Auto mais vulnerável
    8: "#27ae60",  # Mapa empresas
    9: "#7f8c8d",  # Mapa autos
}


# ── Faixa de filtros globais (compacta) ───────────────────────────────────────

def _filtros_globais():
    return html.Div(
        className="souvi-filtros",
        children=dbc.Row([
            dbc.Col([
                html.Label("Tipo de Serviço"),
                dcc.Dropdown(
                    id="filtro-servico",
                    options=SERVICOS_OPCOES,
                    value=SERVICOS_DEFAULT,
                    multi=True,
                    placeholder="Selecione tipos de serviço",
                ),
            ], xs=12, md=3),
            dbc.Col([
                html.Label("Ano"),
                dcc.Dropdown(id="filtro-ano", clearable=False),
            ], xs=6, md=1),
            dbc.Col([
                html.Label("Meses"),
                dcc.Dropdown(
                    id="filtro-meses",
                    multi=True,
                    placeholder="Todos os meses",
                ),
            ], xs=6, md=2),
            dbc.Col([
                html.Label("Região"),
                dcc.Dropdown(
                    id="filtro-regiao",
                    multi=True,
                    placeholder="Todas as regiões",
                ),
            ], xs=12, md=2, id="col-filtro-regiao"),
            dbc.Col([
                html.Label("Permissionária"),
                dcc.Dropdown(
                    id="filtro-empresa",
                    multi=True,
                    placeholder="Todas as empresas",
                ),
            ], xs=12, md=2, id="col-filtro-empresa"),
            dbc.Col([
                html.Label("Assunto"),
                dcc.Dropdown(
                    id="filtro-assunto",
                    multi=True,
                    placeholder="Todos os assuntos",
                ),
            ], xs=12, md=2),
        ], className="g-2 align-items-end"),
    )


# ── Linha dos 9 cards-botão ───────────────────────────────────────────────────

def _kpi_grid():
    return html.Div(
        className="kpi-grid",
        children=[
            kpi_card_button(
                1, "Total de Reclamações",
                value_id="kpi-val-1", icon="📊",
                accent_color=CARD_COLORS[1],
            ),
            kpi_card_button(
                2, "Assunto Mais Reclamado",
                value_id="kpi-val-2", sub_id="kpi-sub-2", icon="🏷️",
                accent_color=CARD_COLORS[2],
            ),
            kpi_card_button(
                3, "Embarque Mais Crítico",
                value_id="kpi-val-3", sub_id="kpi-sub-3",
                label_id="kpi-label-3", icon="📍",
                accent_color=CARD_COLORS[3],
            ),
            kpi_card_button(
                4, "Empresa Mais Reclamada",
                value_id="kpi-val-4", sub_id="kpi-sub-4", icon="🏢",
                accent_color=CARD_COLORS[4],
            ),
            kpi_card_button(
                5, "Empresa Mais Vulnerável",
                value_id="kpi-val-5", sub_id="kpi-sub-5", icon="⚠️",
                accent_color=CARD_COLORS[5],
            ),
            kpi_card_button(
                6, "Auto Mais Reclamado",
                value_id="kpi-val-6", sub_id="kpi-sub-6", icon="🚌",
                accent_color=CARD_COLORS[6],
            ),
            kpi_card_button(
                7, "Auto Mais Vulnerável",
                value_id="kpi-val-7", sub_id="kpi-sub-7", icon="🛡️",
                accent_color=CARD_COLORS[7],
            ),
            kpi_card_button(
                8, "Mapa de Calor por Empresa",
                only_button=True, icon="🗺️",
                accent_color=CARD_COLORS[8],
            ),
            kpi_card_button(
                9, "Mapa de Calor por Autos",
                only_button=True, icon="🗺️",
                accent_color=CARD_COLORS[9],
            ),
        ],
    )


# ── Paginação ─────────────────────────────────────────────────────────────────

def _paginacao(prefix: str):
    return html.Div(
        className="graph-pagination",
        children=[
            dbc.Button("← Anterior", id=f"{prefix}-prev", color="light", size="sm", n_clicks=0),
            html.Span(id=f"{prefix}-info"),
            dbc.Button("Próxima →", id=f"{prefix}-next", color="light", size="sm", n_clicks=0),
        ],
    )


def _graph_wrapper(wrap_id: str, children: list) -> html.Div:
    """Wrapper de cada gráfico dinâmico (oculto por padrão; o callback liga `.active`)."""
    return html.Div(
        id=wrap_id,
        className="graph-wrap",
        children=[html.Div(className="graph-card", children=children)],
    )


# ── Área de gráficos dinâmicos ────────────────────────────────────────────────

def _graph_area():
    return html.Div(
        className="graph-area",
        children=[
            # Wrap 1 — Evolução mensal (card 1)
            _graph_wrapper("wrap-g1", [
                dcc.Graph(id="g-evolucao", config=GRAPH_CONFIG, style={"height": "100%"}),
            ]),

            # Wrap 2 — Pizza de assuntos (card 2)
            _graph_wrapper("wrap-g2", [
                dcc.Graph(id="g-pizza", config=GRAPH_CONFIG, style={"height": "100%"}),
            ]),

            # Wrap 3 — Locais embarque/desembarque (card 3)
            _graph_wrapper("wrap-g3", [
                html.Div(className="graph-controls", children=[
                    html.Label("Tipo de Local"),
                    dbc.RadioItems(
                        id="filtro-tipo-local",
                        options=[
                            {"label": " Embarque", "value": "embarque"},
                            {"label": " Desembarque", "value": "desembarque"},
                        ],
                        value="embarque",
                        inline=True,
                    ),
                ]),
                dcc.Store(id="g-pagina-locais", data=1),
                dcc.Graph(id="g-locais", config=GRAPH_CONFIG, style={"height": "100%"}),
                _paginacao("g-locais"),
            ]),

            # Wrap 4 — Empresas pontuação (card 4)
            _graph_wrapper("wrap-g4", [
                dcc.Graph(id="g3-empresas", config=GRAPH_CONFIG, style={"height": "100%"}),
            ]),

            # Wrap 5 — Empresas irregular (card 5)
            _graph_wrapper("wrap-g5", [
                dcc.Graph(id="g4-irregular", config=GRAPH_CONFIG, style={"height": "100%"}),
            ]),

            # Wrap 6 — Autos pontuação (card 6)
            _graph_wrapper("wrap-g6", [
                dcc.Store(id="g6-pagina", data=1),
                dcc.Graph(id="g6-autos", config=GRAPH_CONFIG, style={"height": "100%"}),
                _paginacao("g6"),
            ]),

            # Wrap 7 — Autos irregular (card 7)
            _graph_wrapper("wrap-g7", [
                dcc.Store(id="g7-pagina", data=1),
                dcc.Graph(id="g7-irregular", config=GRAPH_CONFIG, style={"height": "100%"}),
                _paginacao("g7"),
            ]),

            # Wrap 8 — Heatmap empresa (card 8)
            _graph_wrapper("wrap-g8", [
                html.Div(className="graph-controls", children=[
                    html.Label("Ordenar por Assunto"),
                    dcc.Dropdown(
                        id="filtro-sort-assunto-g5",
                        multi=True,
                        placeholder="Todos os assuntos",
                        style={"minWidth": "260px"},
                    ),
                ]),
                dcc.Store(id="g5-pagina", data=1),
                dcc.Graph(id="g5-heatmap-empresa", config=GRAPH_CONFIG, style={"height": "100%"}),
                _paginacao("g5"),
            ]),

            # Wrap 9 — Heatmap auto (card 9)
            _graph_wrapper("wrap-g9", [
                html.Div(className="graph-controls", children=[
                    html.Label("Ordenar por Assunto"),
                    dcc.Dropdown(
                        id="filtro-sort-assunto-g8",
                        multi=True,
                        placeholder="Todos os assuntos",
                        style={"minWidth": "260px"},
                    ),
                ]),
                dcc.Store(id="g8-pagina", data=1),
                dcc.Graph(id="g8-heatmap-auto", config=GRAPH_CONFIG, style={"height": "100%"}),
                _paginacao("g8"),
            ]),
        ],
    )


# ── Layout principal ──────────────────────────────────────────────────────────

def build_layout():
    return html.Div(
        className="souvi-shell",
        children=[
            html.Div(
                className="souvi-header",
                children=html.H1(
                    "Painel de Reclamações — Sistema de Ouvidorias (SOUVI)"
                ),
            ),
            _filtros_globais(),
            dcc.Store(id="card-ativo", data=1),
            dcc.Store(id="store-loading", data=True),
            dcc.Store(id="store-orientacao", data="landscape"),
            dcc.Interval(id="interval-orientacao", interval=200, max_intervals=1),
            html.Div(
                className="content-wrapper",
                children=[
                    html.Div(
                        id="loading-overlay",
                        className="loading-overlay ativo",
                        children=html.Div(className="loading-spinner"),
                    ),
                    _kpi_grid(),
                    html.Div(id="aviso-sem-dados", className="souvi-aviso"),
                    _graph_area(),
                ],
            ),
            html.Div(id="dummy-resize", style={"display": "none"}),
        ],
    )
