"""api/utils/ — Utilitários server-side (dependem de api.repositories)."""

from .html_resumo import gerar_html_resumo
from .types import DetalheOuvidoriaView, RespostaTecnicaView

__all__ = [
    "gerar_html_resumo",
    "DetalheOuvidoriaView",
    "RespostaTecnicaView",
]
