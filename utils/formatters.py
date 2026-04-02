"""Funcoes de formatacao para UI: autos, prazos, exportacao Excel."""

from datetime import date
from io import BytesIO

import pandas as pd


def fmt_auto(a) -> str:
    """Formata tupla de auto (id, numero, cidade_ini, cidade_fim, empresa) para exibicao."""
    num, emp, ori, dest = a[1], a[4], a[2], a[3]
    partes = [num]
    if emp:
        partes.append(emp)
    if ori or dest:
        partes.append(f"{ori} → {dest}")
    return " – ".join(partes)


def prazo_circle_label(prazo: date | None) -> tuple[str, str]:
    """Retorna (label_curto, tooltip) para prazo. label_curto ex: '🟢 5d', tooltip: 'DD/MM/AAAA'."""
    if prazo is None:
        return "---", ""
    dias = (prazo - date.today()).days
    emoji = "🟢" if dias >= 0 else "🔴"
    return f"{emoji} {dias}d", prazo.strftime("%d/%m/%Y")


def to_excel(df: pd.DataFrame) -> bytes:
    """Converte DataFrame para bytes de um arquivo Excel."""
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Dados")
    return buf.getvalue()
