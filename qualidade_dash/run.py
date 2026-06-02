"""Script para iniciar o Dashboard de Qualidade (Plotly Dash).

Uso:
    python -m qualidade_dash.run

Variáveis de ambiente opcionais:
    API_URL    URL base da FastAPI   (default: http://localhost:8000)
    DASH_PORT  Porta do Dash         (default: 8050)
    DASH_DEBUG Modo debug            (default: false)
"""

from qualidade_dash.app import app
import os

if __name__ == "__main__":
    port = int(os.getenv("DASH_PORT", "8050"))
    debug = os.getenv("DASH_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
