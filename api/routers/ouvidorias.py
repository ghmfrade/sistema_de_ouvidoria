from typing import Optional
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse

from api import storage
from api.deps import usuario_corrente, requer_gestor
from api.schemas.ouvidoria import (
    OuvidoriaResumoSchema, OuvidoriaDetalheSchema,
    OuvidoriaPermissionariaSchema, RespostaTecnicaSchema, AtribuicaoScalarSchema,
    CriarOuvidoriaRequest, EditarOuvidoriaRequest, AtribuirTecnicoRequest,
    AtualizarPrazoPermissionariaRequest, RegistrarRespostaTecnicaRequest,
    AtualizarReclamacoesRequest, RegistrarRespostaPermissionariaRequest,
    OuvidoriaIdResponse, RespostaTecnicaConcluidaResponse,
)
from api.repositories.ouvidoria_repo import (
    get_ouvidorias, get_ouvidoria_completa, get_id_por_protocolo,
    get_ouvidoria_permissionaria, get_atribuicao_tecnico, get_respostas_tecnico,
    get_anexo,
)

router = APIRouter()


# ── Leitura ───────────────────────────────────────────────────────────────────

@router.get("", response_model=list[OuvidoriaResumoSchema])
def listar_ouvidorias(
    filtro_status: Optional[str] = None,
    filtro_de: Optional[str] = None,
    filtro_ate: Optional[str] = None,
    ocultar_concluidos: bool = True,
    usuario_id: Optional[int] = None,
    usuario_tipo: Optional[str] = None,
    filtro_categoria_id: Optional[int] = None,
    filtro_subcategoria_id: Optional[int] = None,
    filtro_tipo_servico: Optional[str] = None,
    filtrar_apenas_atribuidas: bool = True,
    _=Depends(usuario_corrente),
):
    return get_ouvidorias(
        filtro_status=filtro_status,
        filtro_de=filtro_de,
        filtro_ate=filtro_ate,
        ocultar_concluidos=ocultar_concluidos,
        usuario_id=usuario_id,
        usuario_tipo=usuario_tipo,
        filtro_categoria_id=filtro_categoria_id,
        filtro_subcategoria_id=filtro_subcategoria_id,
        filtro_tipo_servico=filtro_tipo_servico,
        filtrar_apenas_atribuidas=filtrar_apenas_atribuidas,
    )


@router.get("/por-protocolo/{protocolo}")
def buscar_por_protocolo(protocolo: str, _=Depends(usuario_corrente)) -> Optional[int]:
    return get_id_por_protocolo(protocolo)


@router.get("/{ouvidoria_id}", response_model=OuvidoriaDetalheSchema)
def detalhe_ouvidoria(ouvidoria_id: int, _=Depends(usuario_corrente)):
    dado = get_ouvidoria_completa(ouvidoria_id)
    if dado is None:
        raise HTTPException(status_code=404, detail="Ouvidoria não encontrada")
    return dado


@router.get("/{ouvidoria_id}/permissionaria", response_model=OuvidoriaPermissionariaSchema)
def ouvidoria_permissionaria(ouvidoria_id: int, _=Depends(usuario_corrente)):
    dado = get_ouvidoria_permissionaria(ouvidoria_id)
    if dado is None:
        raise HTTPException(status_code=404, detail="Ouvidoria não encontrada")
    return dado


@router.get("/{ouvidoria_id}/resposta-tecnica")
def resposta_tecnica_view(
    ouvidoria_id: int,
    tecnico_id: int,
    _=Depends(usuario_corrente),
):
    atribuicao = get_atribuicao_tecnico(ouvidoria_id, tecnico_id)
    historico   = get_respostas_tecnico(ouvidoria_id, tecnico_id)
    ouvidoria   = get_ouvidoria_completa(ouvidoria_id)
    if ouvidoria is None:
        raise HTTPException(status_code=404, detail="Ouvidoria não encontrada")
    return {
        "ouvidoria": ouvidoria,
        "atribuicao": atribuicao,
        "historico": historico,
    }


@router.get("/{ouvidoria_id}/resumo-html", response_class=HTMLResponse)
def resumo_html(ouvidoria_id: int):
    from api.utils.html_resumo import gerar_html_resumo
    return gerar_html_resumo(ouvidoria_id)


# ── Escrita — implementada na Etapa 5 ─────────────────────────────────────────

@router.post("", response_model=OuvidoriaIdResponse)
def criar_ouvidoria(body: CriarOuvidoriaRequest, _=Depends(requer_gestor)):
    from api.services.ouvidoria_service import criar_ouvidoria_sem_anexos
    oid = criar_ouvidoria_sem_anexos(body)
    return OuvidoriaIdResponse(id=oid)


@router.patch("/{ouvidoria_id}")
def editar_ouvidoria(
    ouvidoria_id: int,
    body: EditarOuvidoriaRequest,
    _=Depends(requer_gestor),
):
    from api.repositories.ouvidoria_write_repo import editar_ouvidoria as _editar
    _editar(
        ouvidoria_id,
        protocolo=body.protocolo,
        conteudo=body.conteudo,
        prazo=body.prazo,
        prazo_permissionaria=body.prazo_permissionaria,
        status=body.status,
    )
    return {"ok": True}


@router.delete("/{ouvidoria_id}")
def excluir_ouvidoria(ouvidoria_id: int, _=Depends(requer_gestor)):
    from api.repositories.ouvidoria_write_repo import excluir_ouvidoria as _excluir
    storages = _excluir(ouvidoria_id)
    for nome_storage in storages:
        storage.remove_file(nome_storage)
    return {"ok": True}


@router.post("/{ouvidoria_id}/concluir")
def concluir_ouvidoria(ouvidoria_id: int, _=Depends(requer_gestor)):
    from api.repositories.ouvidoria_write_repo import concluir_ouvidoria as _concluir
    _concluir(ouvidoria_id)
    return {"ok": True}


@router.post("/{ouvidoria_id}/atribuir-tecnico")
def atribuir_tecnico(
    ouvidoria_id: int,
    body: AtribuirTecnicoRequest,
    _=Depends(requer_gestor),
):
    from api.repositories.ouvidoria_write_repo import atribuir_tecnico as _atribuir
    resultado = _atribuir(ouvidoria_id, body.tecnico_id)
    if resultado is False:
        raise HTTPException(status_code=409, detail="Técnico já atribuído a esta ouvidoria")
    return {"ok": True}


@router.patch("/{ouvidoria_id}/prazo-permissionaria")
def atualizar_prazo_permissionaria(
    ouvidoria_id: int,
    body: AtualizarPrazoPermissionariaRequest,
    _=Depends(requer_gestor),
):
    from api.repositories.ouvidoria_write_repo import atualizar_prazo_permissionaria as _prazo
    _prazo(ouvidoria_id, body.prazo)
    return {"ok": True}


@router.patch("/{ouvidoria_id}/reclamacoes")
def atualizar_reclamacoes(
    ouvidoria_id: int,
    body: AtualizarReclamacoesRequest,
    _=Depends(usuario_corrente),
):
    from api.repositories.ouvidoria_write_repo import atualizar_reclamacoes as _upd
    _upd(ouvidoria_id, [r.model_dump() for r in body.recs_edit])
    return {"ok": True}


@router.post("/{ouvidoria_id}/respostas-tecnicas", response_model=RespostaTecnicaConcluidaResponse)
def registrar_resposta_tecnica(
    ouvidoria_id: int,
    body: RegistrarRespostaTecnicaRequest,
    _=Depends(usuario_corrente),
):
    from api.repositories.ouvidoria_write_repo import registrar_resposta_tecnica as _resp
    todos = _resp(ouvidoria_id, body.tecnico_id, body.texto)
    return RespostaTecnicaConcluidaResponse(todos_responderam=bool(todos))


@router.post("/{ouvidoria_id}/respostas-permissionaria")
def registrar_resposta_permissionaria(
    ouvidoria_id: int,
    body: RegistrarRespostaPermissionariaRequest,
    _=Depends(usuario_corrente),
):
    from api.repositories.ouvidoria_write_repo import registrar_resposta_permissionaria as _resp
    _resp(ouvidoria_id, body.conteudo, body.data_resposta, body.registrado_por_id)
    return {"ok": True}


@router.delete("/{ouvidoria_id}/respostas-permissionaria/{rp_id}")
def deletar_resposta_permissionaria(
    ouvidoria_id: int,
    rp_id: int,
    _=Depends(usuario_corrente),
):
    from api.repositories.ouvidoria_write_repo import deletar_resposta_permissionaria as _del
    _del(rp_id)
    return {"ok": True}


_ALLOWED_MIMES = {
    "application/pdf", "image/png", "image/jpeg", "image/jpg",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


@router.post("/{ouvidoria_id}/anexos")
async def upload_anexo(
    ouvidoria_id: int,
    arquivo: UploadFile = File(...),
    payload: dict = Depends(usuario_corrente),
):
    if arquivo.content_type not in _ALLOWED_MIMES:
        raise HTTPException(status_code=422, detail=f"Tipo de arquivo não permitido: {arquivo.content_type}")
    conteudo = await arquivo.read()
    nome_storage = storage.save_bytes(conteudo, arquivo.filename or "arquivo")
    from api.repositories.ouvidoria_write_repo import add_anexos
    add_anexos(ouvidoria_id, [{
        "nome_arquivo": arquivo.filename or nome_storage,
        "nome_storage": nome_storage,
        "tipo_mime": arquivo.content_type,
        "tamanho": len(conteudo),
        "enviado_por_id": int(payload["sub"]),
    }])
    return {"ok": True, "nome_storage": nome_storage}


@router.get("/{ouvidoria_id}/anexos/{anexo_id}/download")
def download_anexo(
    ouvidoria_id: int,
    anexo_id: int,
    _=Depends(usuario_corrente),
):
    anexo = get_anexo(anexo_id)
    if anexo is None or anexo["ouvidoria_id"] != ouvidoria_id:
        raise HTTPException(status_code=404, detail="Anexo não encontrado")
    if not storage.exists(anexo["nome_storage"]):
        raise HTTPException(status_code=410, detail="Arquivo não disponível no storage")
    return FileResponse(
        path=storage.path_for(anexo["nome_storage"]),
        media_type=anexo["tipo_mime"],
        filename=anexo["nome_arquivo"],
    )


@router.delete("/{ouvidoria_id}/anexos/{anexo_id}")
def deletar_anexo(
    ouvidoria_id: int,
    anexo_id: int,
    _=Depends(usuario_corrente),
):
    from api.repositories.ouvidoria_write_repo import delete_anexo
    nome_storage = delete_anexo(anexo_id)
    if nome_storage:
        storage.remove_file(nome_storage)
    return {"ok": True}
