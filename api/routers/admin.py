from typing import Optional
from fastapi import APIRouter, Depends, HTTPException

from api.deps import requer_gestor
from api.schemas.catalog import (
    CategoriaSchema, SubcategoriaSchema, GerenciaSchema,
    CoordenacaoSchema, UsuarioSchema,
)
from api.schemas.admin import (
    CriarUsuarioRequest, CriarCategoriaRequest, CriarSubcategoriaRequest,
    CriarGerenciaRequest, CriarCoordenacaoRequest, ToggleRequest, EditarUsuarioRequest,
)
from repositories.catalog_repo import (
    get_usuarios, get_usuario_por_id, get_categorias, get_subcategorias,
    get_gerencias, get_coordenacoes,
)
from repositories.admin_write_repo import (
    email_existe as _email_existe,
    criar_usuario as _criar_usuario,
    toggle_usuario as _toggle_usuario,
    editar_usuario as _editar_usuario,
    criar_categoria as _criar_categoria,
    toggle_categoria as _toggle_categoria,
    criar_subcategoria as _criar_subcategoria,
    toggle_subcategoria as _toggle_subcategoria,
    criar_gerencia as _criar_gerencia,
    toggle_gerencia as _toggle_gerencia,
    criar_coordenacao as _criar_coordenacao,
    toggle_coordenacao as _toggle_coordenacao,
)

router = APIRouter()


# ── Usuários ──────────────────────────────────────────────────────────────────

@router.get("/usuarios", response_model=list[UsuarioSchema])
def listar_usuarios(_=Depends(requer_gestor)):
    return get_usuarios()


@router.get("/usuarios/email-existe")
def email_existe(
    email: str,
    apenas_ativos: bool = False,
    exclude_id: int | None = None,
    _=Depends(requer_gestor),
) -> bool:
    return _email_existe(email, apenas_ativos=apenas_ativos, exclude_id=exclude_id)


@router.post("/usuarios")
def criar_usuario(body: CriarUsuarioRequest, _=Depends(requer_gestor)):
    if _email_existe(body.email, apenas_ativos=True):
        raise HTTPException(
            status_code=409,
            detail=f"Já existe um login ativo com o e-mail '{body.email}'. "
                   "Inative o usuário existente antes de criar um novo com o mesmo e-mail.",
        )
    import bcrypt
    senha_hash = bcrypt.hashpw(body.senha.encode(), bcrypt.gensalt()).decode()
    _criar_usuario(
        nome=body.nome,
        email=body.email,
        senha_hash=senha_hash,
        tipo=body.tipo,
        gerencia_id=body.gerencia_id,
        coordenacao_id=body.coordenacao_id,
    )
    return {"ok": True}


@router.patch("/usuarios/{usuario_id}/toggle")
def toggle_usuario(usuario_id: int, body: ToggleRequest, _=Depends(requer_gestor)):
    if body.ativo:
        usr = get_usuario_por_id(usuario_id)
        if usr and _email_existe(usr["email"], apenas_ativos=True, exclude_id=usuario_id):
            raise HTTPException(
                status_code=409,
                detail=f"O e-mail '{usr['email']}' já está em uso por outro login ativo.",
            )
    _toggle_usuario(usuario_id, body.ativo)
    return {"ok": True}


@router.patch("/usuarios/{usuario_id}/editar")
def editar_usuario(usuario_id: int, body: EditarUsuarioRequest, _=Depends(requer_gestor)):
    import bcrypt
    hash_ = bcrypt.hashpw(body.nova_senha.encode(), bcrypt.gensalt()).decode() if body.nova_senha else None
    _editar_usuario(usuario_id, hash_, body.tipo)
    return {"ok": True}


# ── Categorias ────────────────────────────────────────────────────────────────

@router.get("/categorias", response_model=list[CategoriaSchema])
def listar_categorias(_=Depends(requer_gestor)):
    return get_categorias()


@router.post("/categorias")
def criar_categoria(body: CriarCategoriaRequest, _=Depends(requer_gestor)):
    _criar_categoria(nome=body.nome, descricao=body.descricao)
    return {"ok": True}


@router.patch("/categorias/{cat_id}/toggle")
def toggle_categoria(cat_id: int, body: ToggleRequest, _=Depends(requer_gestor)):
    _toggle_categoria(cat_id, body.ativo)
    return {"ok": True}


# ── Subcategorias ─────────────────────────────────────────────────────────────

@router.get("/subcategorias", response_model=list[SubcategoriaSchema])
def listar_subcategorias(
    categoria_id: Optional[int] = None,
    _=Depends(requer_gestor),
):
    return get_subcategorias(categoria_id)


@router.post("/subcategorias")
def criar_subcategoria(body: CriarSubcategoriaRequest, _=Depends(requer_gestor)):
    _criar_subcategoria(nome=body.nome, categoria_id=body.categoria_id)
    return {"ok": True}


@router.patch("/subcategorias/{subcat_id}/toggle")
def toggle_subcategoria(subcat_id: int, body: ToggleRequest, _=Depends(requer_gestor)):
    _toggle_subcategoria(subcat_id, body.ativo)
    return {"ok": True}


# ── Gerências ─────────────────────────────────────────────────────────────────

@router.get("/gerencias", response_model=list[GerenciaSchema])
def listar_gerencias(_=Depends(requer_gestor)):
    return get_gerencias()


@router.post("/gerencias")
def criar_gerencia(body: CriarGerenciaRequest, _=Depends(requer_gestor)):
    _criar_gerencia(nome=body.nome)
    return {"ok": True}


@router.patch("/gerencias/{ger_id}/toggle")
def toggle_gerencia(ger_id: int, body: ToggleRequest, _=Depends(requer_gestor)):
    _toggle_gerencia(ger_id, body.ativo)
    return {"ok": True}


# ── Coordenações ──────────────────────────────────────────────────────────────

@router.get("/coordenacoes", response_model=list[CoordenacaoSchema])
def listar_coordenacoes(
    gerencia_id: Optional[int] = None,
    _=Depends(requer_gestor),
):
    return get_coordenacoes(gerencia_id)


@router.post("/coordenacoes")
def criar_coordenacao(body: CriarCoordenacaoRequest, _=Depends(requer_gestor)):
    _criar_coordenacao(nome=body.nome, gerencia_id=body.gerencia_id)
    return {"ok": True}


@router.patch("/coordenacoes/{coord_id}/toggle")
def toggle_coordenacao(coord_id: int, body: ToggleRequest, _=Depends(requer_gestor)):
    _toggle_coordenacao(coord_id, body.ativo)
    return {"ok": True}
