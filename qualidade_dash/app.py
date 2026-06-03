"""Entry point do Dashboard de Qualidade (Plotly Dash)."""

import os
import dash
import dash_bootstrap_components as dbc

from qualidade_dash.layout import build_layout
from qualidade_dash.callbacks import register_callbacks

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title="Painel SOUVI — Reclamações",
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)

app.layout = build_layout()
register_callbacks(app)

server = app.server  # expõe o Flask server para uso com gunicorn se necessário

if __name__ == "__main__":
    port = int(os.getenv("DASH_PORT", "8050"))
    debug = os.getenv("DASH_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
