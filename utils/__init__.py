"""utils/ — Utilitários de formatação compartilhados entre frontend e API."""

from .formatters import fmt_auto, fmt_ativo, formatar_atribuicoes, prazo_circle_label, to_excel

__all__ = [
    "fmt_auto",
    "fmt_ativo",
    "formatar_atribuicoes",
    "prazo_circle_label",
    "to_excel",
]
