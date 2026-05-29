"""Componentes reutilizáveis do Painel SIGO."""

from __future__ import annotations

from dash import html


def kpi_card_button(
    index: int,
    label: str,
    *,
    value_id: str | None = None,
    sub_id: str | None = None,
    label_id: str | None = None,
    icon: str = "",
    accent_color: str = "#1a73e8",
    only_button: bool = False,
) -> html.Div:
    """Card-botão clicável com KPI (ou apenas botão visual).

    Implementado como `html.Div` (e não `dbc.Card`) porque a versão atual de
    dash-bootstrap-components não expõe `n_clicks` em Card. O CSS `.kpi-card`
    confere o visual de card e a cor de destaque vem da variável CSS `--accent`.
    O `id` é pattern-matching ({"type": "kpi-card", "index": N}).
    """
    label_kwargs = {"className": "kpi-label"}
    if label_id:
        label_kwargs["id"] = label_id

    inner: list = [
        html.Div(icon, className="kpi-icon"),
        html.Div(label, **label_kwargs),
    ]
    if not only_button:
        value_kwargs = {"className": "kpi-value"}
        if value_id:
            value_kwargs["id"] = value_id
        inner.append(html.Div("—", **value_kwargs))
        if sub_id:
            inner.append(html.Div("", id=sub_id, className="kpi-sub"))

    return html.Div(
        html.Div(inner, className="kpi-body"),
        id={"type": "kpi-card", "index": index},
        className="kpi-card",
        style={"--accent": accent_color},
        n_clicks=0,
    )
