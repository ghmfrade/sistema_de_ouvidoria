"""Cliente HTTP para os endpoints /dashboard/qualidade-v2/* da FastAPI."""

import os
import requests

_BASE = os.getenv("API_URL", "http://localhost:8000")
_TIMEOUT = 30


def _get(path: str, params: dict) -> dict | list:
    # Remove params None para não poluir a query string
    params = {k: v for k, v in params.items() if v is not None}
    r = requests.get(f"{_BASE}/dashboard/qualidade-v2/{path}", params=params, timeout=_TIMEOUT)
    r.raise_for_status()
    return r.json()


def get_anos_disponiveis() -> list[int]:
    return _get("anos-disponiveis", {})


def get_meses_disponiveis(ano: int, tipo_servico: str | None = None, categoria: str = "RECLAMAÇÃO") -> list[int]:
    return _get("meses-disponiveis", {"ano": ano, "tipo_servico": tipo_servico, "categoria": categoria})


def get_resumo(ano: int, meses: str | None, tipo_servico: str | None, categoria: str = "RECLAMAÇÃO") -> dict:
    return _get("resumo", {"ano": ano, "meses": meses, "tipo_servico": tipo_servico, "categoria": categoria})


def get_evolucao_mensal(ano: int, meses: str | None, tipo_servico: str | None, categoria: str = "RECLAMAÇÃO") -> list:
    return _get("evolucao-mensal", {"ano": ano, "meses": meses, "tipo_servico": tipo_servico, "categoria": categoria})


def get_assuntos_pizza(ano: int, meses: str | None, tipo_servico: str | None, categoria: str = "RECLAMAÇÃO") -> list:
    return _get("assuntos-pizza", {"ano": ano, "meses": meses, "tipo_servico": tipo_servico, "categoria": categoria})


def get_empresas_pontuacao(ano: int, meses: str | None, tipo_servico: str | None, categoria: str = "RECLAMAÇÃO") -> list:
    return _get("empresas-pontuacao", {"ano": ano, "meses": meses, "tipo_servico": tipo_servico, "categoria": categoria})


def get_empresas_irregular(ano: int, meses: str | None, tipo_servico: str | None, categoria: str = "RECLAMAÇÃO") -> list:
    return _get("empresas-irregular", {"ano": ano, "meses": meses, "tipo_servico": tipo_servico, "categoria": categoria})


def get_heatmap_assunto_empresa(
    ano: int, meses: str | None, tipo_servico: str | None, pagina: int = 1, categoria: str = "RECLAMAÇÃO"
) -> dict:
    return _get(
        "heatmap-assunto-empresa",
        {"ano": ano, "meses": meses, "tipo_servico": tipo_servico, "pagina": pagina, "categoria": categoria},
    )


def get_autos_pontuacao(
    ano: int, meses: str | None, tipo_servico: str | None, pagina: int = 1, categoria: str = "RECLAMAÇÃO"
) -> dict:
    return _get(
        "autos-pontuacao",
        {"ano": ano, "meses": meses, "tipo_servico": tipo_servico, "pagina": pagina, "categoria": categoria},
    )


def get_autos_irregular(
    ano: int, meses: str | None, tipo_servico: str | None, pagina: int = 1, categoria: str = "RECLAMAÇÃO"
) -> dict:
    return _get(
        "autos-irregular",
        {"ano": ano, "meses": meses, "tipo_servico": tipo_servico, "pagina": pagina, "categoria": categoria},
    )


def get_heatmap_assunto_auto(
    ano: int,
    meses: str | None,
    tipo_servico: str | None,
    perm_ids: str | None = None,
    pagina: int = 1,
    categoria: str = "RECLAMAÇÃO",
) -> dict:
    return _get(
        "heatmap-assunto-auto",
        {
            "ano": ano, "meses": meses, "tipo_servico": tipo_servico,
            "perm_ids": perm_ids, "pagina": pagina, "categoria": categoria,
        },
    )


def get_locais_embarque(ano: int, meses: str | None, pagina: int = 1, categoria: str = "RECLAMAÇÃO") -> dict:
    return _get("locais-embarque", {"ano": ano, "meses": meses, "pagina": pagina, "categoria": categoria})


def get_empresas_lista(tipo_servico: str | None) -> list:
    return _get("empresas-lista", {"tipo_servico": tipo_servico})
