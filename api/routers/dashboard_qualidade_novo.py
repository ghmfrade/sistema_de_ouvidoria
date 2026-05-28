"""Endpoints do novo Dashboard de Qualidade (Dash, v2).

Parâmetros de filtro:
  - ano: int — ano de referência
  - meses: str — meses comma-separated, ex: "1,2,12" (vazio = todos)
  - tipo_servico: str — valor de TipoServico (pode ser múltiplo comma-sep para Fretamento)
  - categoria: str — categoria da reclamação (default "RECLAMAÇÃO", visível no contrato)

Sem autenticação: endpoints read-only de analytics interno.
"""

from fastapi import APIRouter

router = APIRouter()


def _parse_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def _parse_meses(meses_str: str | None) -> list[int]:
    if not meses_str:
        return []
    return [int(m) for m in meses_str.split(",") if m.strip().isdigit()]


def _parse_perm_ids(perm_ids_str: str | None) -> list[int]:
    if not perm_ids_str:
        return []
    return [int(v) for v in perm_ids_str.split(",") if v.strip().isdigit()]


# ── Filtros disponíveis ───────────────────────────────────────────────────────

@router.get("/qualidade-v2/anos-disponiveis")
def anos_disponiveis():
    from repositories.dashboard.qualidade_novo_repo import query_anos_disponiveis
    return query_anos_disponiveis()


@router.get("/qualidade-v2/meses-disponiveis")
def meses_disponiveis(
    ano: int,
    tipo_servico: str | None = None,
    categoria: str = "RECLAMAÇÃO",
):
    from repositories.dashboard.qualidade_novo_repo import query_meses_disponiveis
    return query_meses_disponiveis(ano, _parse_list(tipo_servico), categoria)


@router.get("/qualidade-v2/regioes-disponiveis")
def regioes_disponiveis(tipo_servico: str | None = None):
    from repositories.dashboard.qualidade_novo_repo import query_regioes_disponiveis
    return query_regioes_disponiveis(_parse_list(tipo_servico))


# ── Cards de resumo ───────────────────────────────────────────────────────────

@router.get("/qualidade-v2/resumo")
def resumo(
    ano: int,
    meses: str | None = None,
    tipo_servico: str | None = None,
    categoria: str = "RECLAMAÇÃO",
):
    from repositories.dashboard.qualidade_novo_repo import query_resumo
    return query_resumo(ano, _parse_meses(meses), _parse_list(tipo_servico), categoria)


# ── Gráfico 1: Evolução mensal ────────────────────────────────────────────────

@router.get("/qualidade-v2/evolucao-mensal")
def evolucao_mensal(
    ano: int,
    meses: str | None = None,
    tipo_servico: str | None = None,
    categoria: str = "RECLAMAÇÃO",
):
    from repositories.dashboard.qualidade_novo_repo import query_evolucao_mensal_v2
    rows = query_evolucao_mensal_v2(ano, _parse_meses(meses), _parse_list(tipo_servico), categoria)
    return [{"mes": r[0], "total": r[1]} for r in rows]


# ── Gráfico 2: Pizza de assuntos ─────────────────────────────────────────────

@router.get("/qualidade-v2/assuntos-pizza")
def assuntos_pizza(
    ano: int,
    meses: str | None = None,
    tipo_servico: str | None = None,
    categoria: str = "RECLAMAÇÃO",
):
    from repositories.dashboard.qualidade_novo_repo import query_assuntos_pizza
    rows = query_assuntos_pizza(ano, _parse_meses(meses), _parse_list(tipo_servico), categoria)
    return [{"assunto": r[0], "total": r[1]} for r in rows]


# ── Gráfico 3: Empresas por pontuação ────────────────────────────────────────

@router.get("/qualidade-v2/empresas-pontuacao")
def empresas_pontuacao(
    ano: int,
    meses: str | None = None,
    tipo_servico: str | None = None,
    categoria: str = "RECLAMAÇÃO",
):
    from repositories.dashboard.qualidade_novo_repo import query_empresas_pontuacao_v2
    return query_empresas_pontuacao_v2(ano, _parse_meses(meses), _parse_list(tipo_servico), categoria)


# ── Gráfico 4: Incidência de transporte irregular por empresa ─────────────────

@router.get("/qualidade-v2/empresas-irregular")
def empresas_irregular(
    ano: int,
    meses: str | None = None,
    tipo_servico: str | None = None,
    categoria: str = "RECLAMAÇÃO",
):
    from repositories.dashboard.qualidade_novo_repo import query_empresas_incidencia_irregular
    return query_empresas_incidencia_irregular(
        ano, _parse_meses(meses), _parse_list(tipo_servico), categoria
    )


# ── Gráfico 5: Heatmap Assunto × Empresa ─────────────────────────────────────

@router.get("/qualidade-v2/heatmap-assunto-empresa")
def heatmap_assunto_empresa(
    ano: int,
    meses: str | None = None,
    tipo_servico: str | None = None,
    pagina: int = 1,
    por_pagina: int = 10,
    categoria: str = "RECLAMAÇÃO",
    regioes: str | None = None,
):
    from repositories.dashboard.qualidade_novo_repo import query_heatmap_assunto_empresa
    return query_heatmap_assunto_empresa(
        ano, _parse_meses(meses), _parse_list(tipo_servico), pagina, por_pagina, categoria,
        _parse_list(regioes),
    )


# ── Gráfico 6: Autos por pontuação ───────────────────────────────────────────

@router.get("/qualidade-v2/autos-pontuacao")
def autos_pontuacao(
    ano: int,
    meses: str | None = None,
    tipo_servico: str | None = None,
    pagina: int = 1,
    por_pagina: int = 15,
    categoria: str = "RECLAMAÇÃO",
):
    from repositories.dashboard.qualidade_novo_repo import query_autos_pontuacao_v2
    return query_autos_pontuacao_v2(
        ano, _parse_meses(meses), _parse_list(tipo_servico), pagina, por_pagina, categoria
    )


# ── Gráfico 7: Autos por incidência de transporte irregular ──────────────────

@router.get("/qualidade-v2/autos-irregular")
def autos_irregular(
    ano: int,
    meses: str | None = None,
    tipo_servico: str | None = None,
    pagina: int = 1,
    por_pagina: int = 15,
    categoria: str = "RECLAMAÇÃO",
):
    from repositories.dashboard.qualidade_novo_repo import query_autos_incidencia_irregular
    return query_autos_incidencia_irregular(
        ano, _parse_meses(meses), _parse_list(tipo_servico), pagina, por_pagina, categoria
    )


# ── Gráfico 8: Heatmap Assunto × Autos ───────────────────────────────────────

@router.get("/qualidade-v2/heatmap-assunto-auto")
def heatmap_assunto_auto(
    ano: int,
    meses: str | None = None,
    tipo_servico: str | None = None,
    perm_ids: str | None = None,
    pagina: int = 1,
    por_pagina: int = 10,
    categoria: str = "RECLAMAÇÃO",
    regioes: str | None = None,
):
    from repositories.dashboard.qualidade_novo_repo import query_heatmap_assunto_auto
    return query_heatmap_assunto_auto(
        ano,
        _parse_meses(meses),
        _parse_list(tipo_servico),
        _parse_perm_ids(perm_ids),
        pagina,
        por_pagina,
        categoria,
        _parse_list(regioes),
    )


# ── Locais de embarque/desembarque ──────────────────────────────────────────

@router.get("/qualidade-v2/locais-embarque")
def locais_embarque(
    ano: int,
    meses: str | None = None,
    tipo_servico: str | None = None,
    pagina: int = 1,
    por_pagina: int = 15,
    categoria: str = "RECLAMAÇÃO",
    tipo_local: str = "embarque",
):
    from repositories.dashboard.qualidade_novo_repo import query_locais_embarque, query_locais_embarque_fretamento

    tipo_servicos = _parse_list(tipo_servico)
    if tipo_servicos:
        return query_locais_embarque(ano, _parse_meses(meses), tipo_servicos, pagina, por_pagina, categoria, tipo_local)
    else:
        # Se nenhum tipo foi especificado, usa o padrão legado (fretamento)
        return query_locais_embarque_fretamento(ano, _parse_meses(meses), pagina, por_pagina, categoria)


# ── Lista de empresas para filtro do Gráfico 8 ───────────────────────────────

@router.get("/qualidade-v2/empresas-lista")
def empresas_lista(
    tipo_servico: str | None = None,
):
    from repositories.dashboard.qualidade_novo_repo import query_empresas_lista
    return query_empresas_lista(_parse_list(tipo_servico))
