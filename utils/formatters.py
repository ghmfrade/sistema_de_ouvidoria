"""Funcoes de formatacao para UI: autos, prazos, status, exportacao Excel."""

from datetime import date
from io import BytesIO
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from repositories.types import AutoDict, OuvidoriaTecnicoDict


def formatar_atribuicoes(atribuicoes: list["OuvidoriaTecnicoDict"]) -> tuple[str, str]:
    """Retorna (coord_ger, responsaveis) para exibição na listagem de ouvidorias.

    - coord_ger: gerências/coordenações únicas dos técnicos pendentes,
      ou "SUCOL - Ouvidoria" se todos já responderam ou não há atribuições.
    - responsaveis: nomes dos técnicos que ainda não responderam,
      ou "–" se todos responderam ou não há atribuições.
    """
    if not atribuicoes:
        return "SUCOL - Ouvidoria", "–"

    partes: list[str] = []
    seen: set[str] = set()
    pendentes: list[str] = []

    for at in atribuicoes:
        ger = at["gerencia_nome"] or "?"
        coord = at["coordenacao_nome"] or "?"
        chave = f"{ger}-{coord}"
        if chave not in seen:
            partes.append(chave)
            seen.add(chave)
        if not at["respondido"]:
            pendentes.append(at["tecnico_nome"])

    if not pendentes:
        return "SUCOL - Ouvidoria", "–"

    coord_ger = " / ".join(partes) if partes else "Em análise"
    responsaveis = ", ".join(pendentes)
    return coord_ger, responsaveis


TC_REGIOES: dict[int, str] = {
    1: "Campinas",
    2: "Sorocaba",
    3: "Bauru",
    4: "Araraquara",
    5: "São Paulo",
}


def fmt_auto(a: "AutoDict") -> str:
    """Formata AutoDict para exibição: 'numero – empresa – denominacao – TCX Região'."""
    partes = [a["numero"]]
    if a["permissionaria_nome"]:
        partes.append(a["permissionaria_nome"])
    desc = " – ".join(filter(None, [a.get("denominacao_a"), a.get("denominacao_b")]))
    if desc:
        partes.append(desc)
    tc = a.get("tc")
    if tc and tc in TC_REGIOES:
        partes.append(f"TC{tc} {TC_REGIOES[tc]}")
    return " – ".join(partes)


def fmt_ativo(ativo: bool) -> str:
    """Converte bool de status ativo para emoji de exibição."""
    return "✅" if ativo else "❌"


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
