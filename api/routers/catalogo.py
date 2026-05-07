from fastapi import APIRouter, Depends
from typing import Optional

from api.deps import usuario_corrente
from api.schemas.catalog import (
    CategoriaSchema, SubcategoriaSchema, GerenciaSchema,
    CoordenacaoSchema, UsuarioSchema, PermissionariaSchema, MunicipioSchema,
)
from repositories.catalog_repo import (
    get_categorias, get_subcategorias, get_gerencias,
    get_coordenacoes, get_tecnicos_ativos, get_todas_permissionarias,
)
from repositories.municipios_repo import get_municipios_sp, get_municipios_com_linhas
from repositories.autos_repo import get_municipios_destino, get_autos_regioes_metropolitanas
from repositories.autos_repo import get_permissionarias

router = APIRouter()


@router.get("/categorias", response_model=list[CategoriaSchema])
def listar_categorias(_=Depends(usuario_corrente)):
    return get_categorias()


@router.get("/categorias/{categoria_id}/subcategorias", response_model=list[SubcategoriaSchema])
def listar_subcategorias(categoria_id: int, _=Depends(usuario_corrente)):
    return get_subcategorias(categoria_id)


@router.get("/gerencias", response_model=list[GerenciaSchema])
def listar_gerencias(_=Depends(usuario_corrente)):
    return get_gerencias()


@router.get("/coordenacoes", response_model=list[CoordenacaoSchema])
def listar_coordenacoes(
    gerencia_id: Optional[int] = None,
    _=Depends(usuario_corrente),
):
    return get_coordenacoes(gerencia_id)


@router.get("/tecnicos", response_model=list[UsuarioSchema])
def listar_tecnicos(_=Depends(usuario_corrente)):
    return get_tecnicos_ativos()


@router.get("/permissionarias", response_model=list[PermissionariaSchema])
def listar_permissionarias(
    tipo_servico: str,
    regiao: Optional[str] = None,
    _=Depends(usuario_corrente),
):
    return get_permissionarias(tipo_servico, regiao)


@router.get("/municipios", response_model=list[MunicipioSchema])
def listar_municipios(_=Depends(usuario_corrente)):
    return get_municipios_sp()


@router.get("/municipios/com-linhas", response_model=list[MunicipioSchema])
def listar_municipios_com_linhas(
    tipo_servico: str,
    perm_id: Optional[int] = None,
    regiao: Optional[str] = None,
    _=Depends(usuario_corrente),
):
    return get_municipios_com_linhas(tipo_servico, perm_id, regiao)


@router.get("/municipios/destinos", response_model=list[MunicipioSchema])
def listar_municipios_destinos(
    tipo_servico: str,
    nome_origem: str,
    perm_id: Optional[int] = None,
    regiao: Optional[str] = None,
    _=Depends(usuario_corrente),
):
    return get_municipios_destino(tipo_servico, nome_origem, perm_id, regiao)


@router.get("/regioes-metropolitanas", response_model=list[str])
def listar_regioes_metropolitanas(_=Depends(usuario_corrente)):
    return get_autos_regioes_metropolitanas()
