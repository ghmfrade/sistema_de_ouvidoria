"""Secao reutilizavel de anexos (listar, baixar, enviar, excluir)."""

import mimetypes
import unicodedata

import streamlit as st

from api.client.ouvidoria_client import add_anexo, delete_anexo, download_anexo
from .estilo_css import afasta_erro_upload

ALLOWED_MIMES = {
    "application/pdf",
    "image/png", "image/jpeg", "image/gif", "image/bmp",
    "video/mp4", "video/x-msvideo", "video/quicktime", "video/x-matroska", "video/webm",
}
ALLOWED_EXTENSIONS = ["pdf", "png", "jpg", "jpeg", "gif", "bmp", "mp4", "avi", "mov", "mkv", "webm"]
MAX_UPLOAD_MB = 10


def _nome_download(nome: str) -> str:
    """Nome ASCII para o download.

    O servidor Starlette do Streamlit em producao devolve 500 quando o
    Content-Disposition tem caracteres latin-1 (ex.: "relatório.pdf", "às").
    """
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFKD", nome) if not unicodedata.combining(c)
    )
    ascii_nome = "".join(c if c.isascii() else "_" for c in sem_acento).strip()
    return ascii_nome or "anexo"


def secao_anexos(ouvidoria_id: int, anexos: list[dict], key_prefix: str) -> None:
    if anexos:
        for an in anexos:
            tamanho_kb = round(an["tamanho"] / 1024, 1) if an.get("tamanho") else "?"
            col_info, col_dl, col_del = st.columns([3, 1, 1])
            col_info.write(f"📎 **{an['nome_arquivo']}** ({tamanho_kb} KB)")
            col_dl.download_button(
                "⬇",
                data=download_anexo(ouvidoria_id, an["id"]),
                file_name=_nome_download(an["nome_arquivo"]),
                mime=an.get("tipo_mime") or "application/octet-stream",
                key=f"{key_prefix}dl_{an['id']}",
                use_container_width=True,
            )
            if col_del.button("🗑", key=f"{key_prefix}del_anexo_{an['id']}", use_container_width=True):
                delete_anexo(ouvidoria_id, an["id"])
                st.toast("Anexo excluído."); st.rerun()
    else:
        st.info("Nenhum anexo.")

    with st.expander("➕ Adicionar Anexos"):
        st.caption(f"Tamanho máximo: {MAX_UPLOAD_MB} MB por arquivo.")
        afasta_erro_upload()
        novos_anexos = st.file_uploader(
            "Selecione arquivos",
            accept_multiple_files=True,
            type=ALLOWED_EXTENSIONS,
            max_upload_size=MAX_UPLOAD_MB,
            key=f"{key_prefix}upload", label_visibility="collapsed",
        )
        if novos_anexos and st.button("📤 Enviar", key=f"{key_prefix}enviar_anexos", use_container_width=True):
            for arq in novos_anexos:
                mime = arq.type or mimetypes.guess_type(arq.name)[0] or ""
                if mime not in ALLOWED_MIMES:
                    st.error(f"Arquivo '{arq.name}' não é um tipo permitido.")
                    continue
                add_anexo(ouvidoria_id, arq.getbuffer().tobytes(), arq.name, arq.type)
            st.success("Anexos enviados."); st.rerun()
