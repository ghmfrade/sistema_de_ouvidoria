"""Substitui utils/loaders_ouvidoria.py e utils/ouvidoria_ops.py."""
from datetime import date
import streamlit as st
from api.client.base import get, post, patch, delete, post_file


# ── Leitura ───────────────────────────────────────────────────────────────────

def listar_ouvidorias(
    filtro_status: str | None = None,
    filtro_periodo: str | None = None,
    ocultar_concluidos: bool = True,
    usuario_id: int | None = None,
    usuario_tipo: str | None = None,
    filtro_categoria_id: int | None = None,
    filtro_subcategoria_id: int | None = None,
    filtro_tipo_servico: str | None = None,
    cache_buster: int = 0,
) -> list[dict]:
    params = {"ocultar_concluidos": ocultar_concluidos}
    if filtro_status:
        params["filtro_status"] = filtro_status
    if filtro_periodo:
        params["filtro_periodo"] = filtro_periodo
    if usuario_id:
        params["usuario_id"] = usuario_id
    if usuario_tipo:
        params["usuario_tipo"] = usuario_tipo
    if filtro_categoria_id:
        params["filtro_categoria_id"] = filtro_categoria_id
    if filtro_subcategoria_id:
        params["filtro_subcategoria_id"] = filtro_subcategoria_id
    if filtro_tipo_servico:
        params["filtro_tipo_servico"] = filtro_tipo_servico
    return get("/ouvidorias", params=params)


def carregar_detalhe_ouvidoria(oid: int) -> dict | None:
    from api.client.base import get, ApiError
    try:
        return get(f"/ouvidorias/{oid}")
    except ApiError as e:
        if e.status_code == 404:
            return None
        raise


@st.cache_data(ttl=60)
def carregar_ouvidoria_para_permissionaria(oid: int) -> dict | None:
    from api.client.base import get, ApiError
    try:
        return get(f"/ouvidorias/{oid}/permissionaria")
    except ApiError as e:
        if e.status_code == 404:
            return None
        raise


def carregar_ouvidoria_para_resposta_tecnica(oid: int, tecnico_id: int) -> dict | None:
    from api.client.base import get, ApiError
    try:
        return get(f"/ouvidorias/{oid}/resposta-tecnica", params={"tecnico_id": tecnico_id})
    except ApiError as e:
        if e.status_code == 404:
            return None
        raise


def buscar_ouvidoria_por_protocolo(protocolo: str) -> int | None:
    return get(f"/ouvidorias/por-protocolo/{protocolo}")


def gerar_html_resumo(oid: int) -> str:
    import httpx
    from api.client.base import API_BASE, _headers
    r = httpx.get(f"{API_BASE}/ouvidorias/{oid}/resumo-html", headers=_headers(), timeout=20.0)
    return r.text


# ── Escrita ───────────────────────────────────────────────────────────────────

def criar_ouvidoria(
    protocolo: str,
    conteudo: str,
    prazo: date | None,
    prazo_permissionaria: date | None,
    status: str,
    criado_por_id: int,
    recs_draft: list[dict],
) -> int:
    body = {
        "protocolo": protocolo,
        "conteudo": conteudo,
        "prazo": prazo.isoformat() if prazo else None,
        "prazo_permissionaria": prazo_permissionaria.isoformat() if prazo_permissionaria else None,
        "status": status,
        "criado_por_id": criado_por_id,
        "reclamacoes": recs_draft,
    }
    return post("/ouvidorias", json=body)["id"]


def editar_ouvidoria(
    oid: int,
    protocolo: str | None = None,
    conteudo: str | None = None,
    prazo: date | None = None,
    prazo_permissionaria: date | None = None,
    status: str | None = None,
) -> None:
    body = {}
    if protocolo is not None:
        body["protocolo"] = protocolo
    if conteudo is not None:
        body["conteudo"] = conteudo
    if prazo is not None:
        body["prazo"] = prazo.isoformat()
    if prazo_permissionaria is not None:
        body["prazo_permissionaria"] = prazo_permissionaria.isoformat()
    if status is not None:
        body["status"] = status
    patch(f"/ouvidorias/{oid}", json=body)


def atualizar_prazo_permissionaria(oid: int, prazo: date | None) -> None:
    patch(f"/ouvidorias/{oid}/prazo-permissionaria",
          json={"prazo": prazo.isoformat() if prazo else None})


def atribuir_tecnico(oid: int, tecnico_id: int) -> bool:
    from api.client.base import ApiError
    try:
        post(f"/ouvidorias/{oid}/atribuir-tecnico", json={"tecnico_id": tecnico_id})
        return True
    except ApiError as e:
        if e.status_code == 409:
            return False
        raise


def concluir_ouvidoria(oid: int) -> None:
    post(f"/ouvidorias/{oid}/concluir")


def excluir_ouvidoria(oid: int) -> None:
    delete(f"/ouvidorias/{oid}")


def add_anexo(oid: int, file_bytes: bytes, filename: str, content_type: str) -> str:
    return post_file(f"/ouvidorias/{oid}/anexos", file_bytes, filename, content_type)["nome_storage"]


def delete_anexo(oid: int, anexo_id: int) -> None:
    delete(f"/ouvidorias/{oid}/anexos/{anexo_id}")


def registrar_resposta_tecnica(
    oid: int,
    tecnico_id: int,
    texto: str,
    recs_edit: list[dict],
) -> bool:
    result = post(f"/ouvidorias/{oid}/respostas-tecnicas", json={
        "tecnico_id": tecnico_id,
        "texto": texto,
        "recs_edit": recs_edit,
    })
    return result.get("todos_responderam", False)


def registrar_resposta_permissionaria(
    oid: int,
    conteudo: str,
    data_resposta: date,
    registrado_por_id: int,
) -> None:
    post(f"/ouvidorias/{oid}/respostas-permissionaria", json={
        "conteudo": conteudo,
        "data_resposta": data_resposta.isoformat(),
        "registrado_por_id": registrado_por_id,
    })


def deletar_resposta_permissionaria(rp_id: int, oid: int) -> None:
    delete(f"/ouvidorias/{oid}/respostas-permissionaria/{rp_id}")
