from fastapi import APIRouter, Depends
from typing import Optional

from api.deps import usuario_corrente
from api.schemas.ouvidoria import AutoSchema
from repositories.autos_repo import get_todos_autos, buscar_autos_por_trecho
from repositories.ouvidoria_write_repo import get_auto_permissionaria_nome

router = APIRouter()


@router.get("", response_model=list[AutoSchema])
def listar_autos(
    tipo_servico: str,
    perm_id: Optional[int] = None,
    regiao: Optional[str] = None,
    _=Depends(usuario_corrente),
):
    return get_todos_autos(tipo_servico, perm_id, regiao)


@router.get("/por-trecho", response_model=list[AutoSchema])
def autos_por_trecho(
    tipo_servico: str,
    cidade_a: str,
    cidade_b: str,
    perm_id: Optional[int] = None,
    regiao: Optional[str] = None,
    _=Depends(usuario_corrente),
):
    return buscar_autos_por_trecho(tipo_servico, cidade_a, cidade_b, perm_id, regiao)


@router.get("/{auto_id}/permissionaria-nome")
def permissionaria_nome(auto_id: int, _=Depends(usuario_corrente)) -> str:
    return get_auto_permissionaria_nome(auto_id)
