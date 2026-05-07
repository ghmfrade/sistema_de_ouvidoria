"""utils/ — Utilitários de formatação e tipos auxiliares."""

from .formatters import fmt_auto, fmt_ativo, formatar_atribuicoes, prazo_circle_label, to_excel
from .html_resumo import gerar_html_resumo
from .types import DetalheOuvidoriaView, RespostaTecnicaView

__all__ = [
    "fmt_auto",
    "fmt_ativo",
    "formatar_atribuicoes",
    "prazo_circle_label",
    "to_excel",
    "gerar_html_resumo",
    "DetalheOuvidoriaView",
    "RespostaTecnicaView",
]
