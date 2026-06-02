from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends

from api.deps import requer_gestor

router = APIRouter()


def _cat_list(cat_ids: Optional[str]) -> list[int]:
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
    from api.repositories.dashboard.produtividade_repo import query_kpis_produtividade
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
    from api.repositories.dashboard.produtividade_repo import query_tempo_medio_resposta
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
    from api.repositories.dashboard.produtividade_repo import query_volume_por_mes
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
    from api.repositories.dashboard.produtividade_repo import query_distribuicao_status
    status_list = [s for s in (status_ids or "").split(",") if s]
    rows = query_distribuicao_status(data_ini, data_fim, ger_id, status_list)
    return [{"status": r[0], "total": r[1]} for r in rows]


@router.get("/produtividade/vencidas-por-coordenacao")
def vencidas_por_coordenacao(
    data_ini: date,
    data_fim: date,
    _=Depends(requer_gestor),
):
    from api.repositories.dashboard.produtividade_repo import query_vencidas_por_coordenacao
    rows = query_vencidas_por_coordenacao(data_ini, data_fim)
    return [{"coordenacao": r[0], "total": r[1]} for r in rows]


@router.get("/produtividade/tempo-medio-por-tecnico")
def tempo_medio_por_tecnico(
    data_ini: date,
    data_fim: date,
    _=Depends(requer_gestor),
):
    from api.repositories.dashboard.produtividade_repo import query_tempo_medio_por_tecnico
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
    from api.repositories.dashboard.produtividade_repo import query_ranking_coordenacoes
    status_list = [s for s in (status_ids or "").split(",") if s]
    rows = query_ranking_coordenacoes(data_ini, data_fim, ger_id, status_list)
    return [{"coordenacao_nome": r[0], "metrica": float(r[1]) if r[1] else None} for r in rows]

