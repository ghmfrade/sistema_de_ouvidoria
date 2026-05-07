from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from api.deps import requer_gestor

router = APIRouter()

# ── Helpers de parâmetros comuns ──────────────────────────────────────────────

def _cat_list(cat_ids: Optional[str]) -> list[int]:
    """Converte query param 'cat_ids=1,2,3' em lista de ints."""
    if not cat_ids:
        return []
    return [int(x) for x in cat_ids.split(",") if x.strip().isdigit()]


# ── Produtividade ─────────────────────────────────────────────────────────────

@router.get("/produtividade/kpis")
def kpis_produtividade(
    data_ini: date,
    data_fim: date,
    ger_id: Optional[int] = None,
    status_ids: Optional[str] = None,
    _=Depends(requer_gestor),
):
    from repositories.dashboard.produtividade_repo import query_kpis_produtividade
    status_list = [s for s in (status_ids or "").split(",") if s]
    total, concluidas, vencidas = query_kpis_produtividade(data_ini, data_fim, ger_id, status_list)
    return {"total": total, "concluidas": concluidas, "vencidas": vencidas}


@router.get("/produtividade/tempo-medio")
def tempo_medio(
    data_ini: date,
    data_fim: date,
    ger_id: Optional[int] = None,
    status_ids: Optional[str] = None,
    _=Depends(requer_gestor),
):
    from repositories.dashboard.produtividade_repo import query_tempo_medio_resposta
    status_list = [s for s in (status_ids or "").split(",") if s]
    resultado = query_tempo_medio_resposta(data_ini, data_fim, ger_id, status_list)
    return {"dias": float(resultado) if resultado is not None else None}


@router.get("/produtividade/volume-por-mes")
def volume_por_mes(
    data_ini: date,
    data_fim: date,
    ger_id: Optional[int] = None,
    status_ids: Optional[str] = None,
    _=Depends(requer_gestor),
):
    from repositories.dashboard.produtividade_repo import query_volume_por_mes
    status_list = [s for s in (status_ids or "").split(",") if s]
    rows = query_volume_por_mes(data_ini, data_fim, ger_id, status_list)
    return [{"mes": str(r[0]), "total": r[1]} for r in rows]


@router.get("/produtividade/distribuicao-status")
def distribuicao_status(
    data_ini: date,
    data_fim: date,
    ger_id: Optional[int] = None,
    status_ids: Optional[str] = None,
    _=Depends(requer_gestor),
):
    from repositories.dashboard.produtividade_repo import query_distribuicao_status
    status_list = [s for s in (status_ids or "").split(",") if s]
    rows = query_distribuicao_status(data_ini, data_fim, ger_id, status_list)
    return [{"status": r[0], "total": r[1]} for r in rows]


@router.get("/produtividade/vencidas-por-coordenacao")
def vencidas_por_coordenacao(
    data_ini: date,
    data_fim: date,
    _=Depends(requer_gestor),
):
    from repositories.dashboard.produtividade_repo import query_vencidas_por_coordenacao
    rows = query_vencidas_por_coordenacao(data_ini, data_fim)
    return [{"coordenacao": r[0], "total": r[1]} for r in rows]


@router.get("/produtividade/tempo-medio-por-tecnico")
def tempo_medio_por_tecnico(
    data_ini: date,
    data_fim: date,
    _=Depends(requer_gestor),
):
    from repositories.dashboard.produtividade_repo import query_tempo_medio_por_tecnico
    rows = query_tempo_medio_por_tecnico(data_ini, data_fim)
    return [{"tecnico_nome": r[0], "dias_medios": float(r[1]) if r[1] else None} for r in rows]


@router.get("/produtividade/ranking-coordenacoes")
def ranking_coordenacoes(
    data_ini: date,
    data_fim: date,
    ger_id: Optional[int] = None,
    status_ids: Optional[str] = None,
    _=Depends(requer_gestor),
):
    from repositories.dashboard.produtividade_repo import query_ranking_coordenacoes
    status_list = [s for s in (status_ids or "").split(",") if s]
    rows = query_ranking_coordenacoes(data_ini, data_fim, ger_id, status_list)
    return [{"coordenacao_nome": r[0], "metrica": float(r[1]) if r[1] else None} for r in rows]


# ── Qualidade ─────────────────────────────────────────────────────────────────

@router.get("/qualidade/kpis")
def kpis_qualidade(
    data_ini: date,
    data_fim: date,
    ger_id: Optional[int] = None,
    perm_id: Optional[int] = None,
    cat_ids: Optional[str] = None,
    tipo_servico: Optional[str] = None,
    _=Depends(requer_gestor),
):
    from repositories.dashboard.qualidade_repo import query_kpis_qualidade
    total, pontuacao, autos_unicos = query_kpis_qualidade(
        data_ini, data_fim, ger_id, perm_id, _cat_list(cat_ids), tipo_servico
    )
    return {
        "total_reclamacoes": total,
        "pontuacao": float(pontuacao) if pontuacao is not None else None,
        "autos_unicos": autos_unicos,
    }


@router.get("/qualidade/top-permissionaria")
def top_permissionaria(
    data_ini: date,
    data_fim: date,
    ger_id: Optional[int] = None,
    perm_id: Optional[int] = None,
    cat_ids: Optional[str] = None,
    tipo_servico: Optional[str] = None,
    _=Depends(requer_gestor),
):
    from repositories.dashboard.qualidade_repo import query_top_permissionaria
    nome, pontos = query_top_permissionaria(
        data_ini, data_fim, ger_id, perm_id, _cat_list(cat_ids), tipo_servico
    )
    return {"nome": nome, "pontos": float(pontos) if pontos is not None else None}


@router.get("/qualidade/top-categoria")
def top_categoria(
    data_ini: date,
    data_fim: date,
    ger_id: Optional[int] = None,
    cat_ids: Optional[str] = None,
    tipo_servico: Optional[str] = None,
    _=Depends(requer_gestor),
):
    from repositories.dashboard.qualidade_repo import query_top_categoria
    return {"categoria": query_top_categoria(data_ini, data_fim, ger_id, _cat_list(cat_ids), tipo_servico)}


@router.get("/qualidade/sla")
def sla(
    data_ini: date,
    data_fim: date,
    ger_id: Optional[int] = None,
    _=Depends(requer_gestor),
):
    from repositories.dashboard.qualidade_repo import query_sla
    total, dentro_prazo = query_sla(data_ini, data_fim, ger_id)
    return {"total": total, "dentro_prazo": dentro_prazo}


@router.get("/qualidade/evolucao-mensal")
def evolucao_mensal(
    data_ini: date,
    data_fim: date,
    ger_id: Optional[int] = None,
    cat_ids: Optional[str] = None,
    tipo_servico: Optional[str] = None,
    _=Depends(requer_gestor),
):
    from repositories.dashboard.qualidade_repo import query_evolucao_mensal
    rows = query_evolucao_mensal(data_ini, data_fim, ger_id, _cat_list(cat_ids), tipo_servico)
    return [{"mes": str(r[0]), "total": r[1]} for r in rows]


@router.get("/qualidade/top-autos")
def top_autos(
    data_ini: date,
    data_fim: date,
    ger_id: Optional[int] = None,
    perm_id: Optional[int] = None,
    cat_ids: Optional[str] = None,
    tipo_servico: Optional[str] = None,
    top_n: int = 20,
    _=Depends(requer_gestor),
):
    from repositories.dashboard.qualidade_repo import query_top_autos_pontuacao
    rows = query_top_autos_pontuacao(
        data_ini, data_fim, ger_id, perm_id, _cat_list(cat_ids), tipo_servico, top_n
    )
    return [{"auto_numero": r[0], "pontuacao": float(r[1]) if r[1] else None} for r in rows]


@router.get("/qualidade/empresas-pontuacao")
def empresas_pontuacao(
    data_ini: date,
    data_fim: date,
    ger_id: Optional[int] = None,
    perm_id: Optional[int] = None,
    cat_ids: Optional[str] = None,
    tipo_servico: Optional[str] = None,
    _=Depends(requer_gestor),
):
    from repositories.dashboard.qualidade_repo import query_empresas_pontuacao
    rows = query_empresas_pontuacao(data_ini, data_fim, ger_id, perm_id, _cat_list(cat_ids), tipo_servico)
    return [{"empresa": r[0], "pontos": float(r[1]) if r[1] else None} for r in rows]


@router.get("/qualidade/categorias-pizza")
def categorias_pizza(
    data_ini: date,
    data_fim: date,
    ger_id: Optional[int] = None,
    cat_ids: Optional[str] = None,
    tipo_servico: Optional[str] = None,
    _=Depends(requer_gestor),
):
    from repositories.dashboard.qualidade_repo import query_categorias_pizza
    rows = query_categorias_pizza(data_ini, data_fim, ger_id, _cat_list(cat_ids), tipo_servico)
    return [{"categoria": r[0], "total": r[1]} for r in rows]


@router.get("/qualidade/cidades")
def cidades(
    data_ini: date,
    data_fim: date,
    ger_id: Optional[int] = None,
    tipo_servico: Optional[str] = None,
    tipo_cidade: str = "Ambos",
    _=Depends(requer_gestor),
):
    from repositories.dashboard.qualidade_repo import query_cidades
    rows = query_cidades(data_ini, data_fim, ger_id, tipo_servico, tipo_cidade)
    return [{"cidade": r[0], "count": r[1]} for r in rows]


@router.get("/qualidade/heatmap-cat-empresa")
def heatmap_cat_empresa(
    data_ini: date,
    data_fim: date,
    ger_id: Optional[int] = None,
    perm_id: Optional[int] = None,
    cat_ids: Optional[str] = None,
    tipo_servico: Optional[str] = None,
    _=Depends(requer_gestor),
):
    from repositories.dashboard.qualidade_repo import query_heatmap_cat_empresa
    rows = query_heatmap_cat_empresa(data_ini, data_fim, ger_id, perm_id, _cat_list(cat_ids), tipo_servico)
    return [{"categoria": r[0], "empresa": r[1], "count": r[2]} for r in rows]


@router.get("/qualidade/tendencia-empresa")
def tendencia_empresa(
    data_ini: date,
    data_fim: date,
    ger_id: Optional[int] = None,
    perm_id: Optional[int] = None,
    cat_ids: Optional[str] = None,
    tipo_servico: Optional[str] = None,
    _=Depends(requer_gestor),
):
    from repositories.dashboard.qualidade_repo import query_tendencia_empresa
    rows = query_tendencia_empresa(data_ini, data_fim, ger_id, perm_id, _cat_list(cat_ids), tipo_servico)
    return [{"periodo": str(r[0]), "empresa": r[1], "valor": float(r[2]) if r[2] else None} for r in rows]


@router.get("/qualidade/tabela-analitica")
def tabela_analitica(
    data_ini: date,
    data_fim: date,
    ger_id: Optional[int] = None,
    perm_id: Optional[int] = None,
    cat_ids: Optional[str] = None,
    tipo_servico: Optional[str] = None,
    _=Depends(requer_gestor),
):
    from decimal import Decimal
    from repositories.dashboard.qualidade_repo import query_tabela_analitica
    rows = query_tabela_analitica(data_ini, data_fim, ger_id, perm_id, _cat_list(cat_ids), tipo_servico)
    def _serializar(v):
        return float(v) if isinstance(v, Decimal) else v
    return JSONResponse(content=[{k: _serializar(v) for k, v in r._mapping.items()} for r in rows] if rows else [])
