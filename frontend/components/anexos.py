"""Secao reutilizavel de anexos (listar, baixar, enviar, excluir)."""

import mimetypes

import streamlit as st

from api.client.ouvidoria_client import add_anexo, delete_anexo, download_anexo

ALLOWED_MIMES = {
    "application/pdf",
    "image/png", "image/jpeg", "image/gif", "image/bmp",
    "video/mp4", "video/x-msvideo", "video/quicktime", "video/x-matroska", "video/webm",
}
ALLOWED_EXTENSIONS = ["pdf", "png", "jpg", "jpeg", "gif", "bmp", "mp4", "avi", "mov", "mkv", "webm"]


def secao_anexos(ouvidoria_id: int, anexos: list[dict], key_prefix: str) -> None:
    if anexos:
        for an in anexos:
            tamanho_kb = round(an["tamanho"] / 1024, 1) if an.get("tamanho") else "?"
            col_info, col_dl, col_del = st.columns([3, 1, 1])
            col_info.write(f"📎 **{an['nome_arquivo']}** ({tamanho_kb} KB)")
            col_dl.download_button(
                "⬇",
                data=download_anexo(ouvidoria_id, an["id"]),
                file_name=an["nome_arquivo"],
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
        novos_anexos = st.file_uploader(
            "Selecione arquivos",
            accept_multiple_files=True,
            type=ALLOWED_EXTENSIONS,
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
