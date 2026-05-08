"""Criar nova ouvidoria com reclamações itemizadas."""

import os
import mimetypes
import sys
from datetime import date, timedelta

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import auth
from auth import usuario_logado
from api.client.enums import STATUS_AGUARDANDO_ACOES, STATUS_AGUARDANDO_PERMISSIONARIA
from api.client.ouvidoria_client import add_anexo
from api.client.base import post
from components import reduz_margem_side_bar, reduz_margem_topo_page
from components.reclamacoes import secao_nova_reclamacao, secao_vincular_autos

st.set_page_config(page_title="Nova Ouvidoria", page_icon="➕", layout="wide")
st.markdown('<style>[data-testid="stSidebar"]{width:220px!important;min-width:220px!important;}</style>', unsafe_allow_html=True)

auth.require_gestor()
u = usuario_logado()
reduz_margem_topo_page()

UPLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

ALLOWED_MIMES = {
    "application/pdf",
    "image/png", "image/jpeg", "image/gif", "image/bmp",
    "video/mp4", "video/x-msvideo", "video/quicktime", "video/x-matroska", "video/webm",
}

# ── Sidebar ──────────────────────────────────────────────────────────────────
reduz_margem_side_bar()
with st.sidebar:
    st.markdown(f"**{u['nome']}**")
    st.caption("Gestor")
    st.divider()
    if st.button("← Voltar para Ouvidorias", use_container_width=True):
        st.switch_page("pages/01_Ouvidorias.py")
    if st.button("Sair", use_container_width=True):
        auth.fazer_logout(); st.rerun()

# ── Estado ────────────────────────────────────────────────────────────────────
st.session_state.setdefault("reclamacoes_draft", [])
st.session_state.setdefault("autos_checklist", [])
st.session_state.setdefault("rec_alvo_anterior", None)

# ── Cabeçalho da Ouvidoria ────────────────────────────────────────────────────
st.title("➕ Nova Ouvidoria")

protocolo = st.text_input("Protocolo da Ouvidoria *", placeholder="Ex.: 202405241486076")
conteudo  = st.text_area("Conteúdo da Ouvidoria *", height=300, placeholder="Cole aqui o conteúdo completo da ouvidoria...")
prazo     = st.date_input("Prazo de resposta *", value=date.today() + timedelta(days=15))

enviado_permissionaria = st.checkbox("Enviado para a permissionária")
prazo_permissionaria = None
if enviado_permissionaria:
    prazo_permissionaria = st.date_input("Prazo de resposta da permissionária", value=date.today() + timedelta(days=30))

st.markdown("#### Anexos")
arquivos_upload = st.file_uploader(
    "Anexar arquivos (PDF, fotos ou vídeos)",
    accept_multiple_files=True,
    type=["pdf", "png", "jpg", "jpeg", "gif", "bmp", "mp4", "avi", "mov", "mkv", "webm"],
)

st.divider()

# ── Reclamações existentes no draft ───────────────────────────────────────────
st.subheader("Reclamações")

if st.session_state["reclamacoes_draft"]:
    for i, rec in enumerate(st.session_state["reclamacoes_draft"]):
        label_emb    = rec["local_embarque"]   or "Não informado"
        label_desemb = rec["local_desembarque"] or "Não informado"
        tipo_label   = rec.get("tipo_servico", "")
        subcat_label = rec.get("subcategoria_nome") or "Sem subcategoria"
        with st.expander(
            f"{rec['numero_item']} - {rec.get('categoria_nome') or 'Sem categoria'} - {subcat_label} - {tipo_label} "
            f"({label_emb} → {label_desemb})", expanded=False,
        ):
            st.write(f"**Tipo de Serviço:** {tipo_label}")
            st.write(f"**Subcategoria:** {rec.get('subcategoria_nome') or '–'}")
            if rec.get("empresa_fretamento"):
                st.write(f"**Empresa de Fretamento:** {rec['empresa_fretamento']}")
            st.write(f"**Embarque:** {label_emb}")
            st.write(f"**Desembarque:** {label_desemb}")
            st.write(f"**Descrição:** {rec['descricao'] or '–'}")
            if rec["autos"]:
                st.write(f"**Autos vinculados ({len(rec['autos'])}):** " + ", ".join(a["numero"] for a in rec["autos"]))
            else:
                st.write("**Autos vinculados:** Nenhum")
            if st.button("🗑 Remover reclamação", key=f"rem_{i}"):
                st.session_state["reclamacoes_draft"].pop(i); st.rerun()

# ── Adicionar Reclamação ──────────────────────────────────────────────────────
st.markdown("#### Adicionar Reclamação")
secao_nova_reclamacao("reclamacoes_draft")

# ── Vincular Autos ────────────────────────────────────────────────────────────
secao_vincular_autos(
    recs_state_key="reclamacoes_draft",
    checklist_key="autos_checklist",
    alvo_anterior_key="rec_alvo_anterior",
    chk_prefix="chk_",
    btn_prefix="nova_",
    extended_auto_info=False,
)

# ── Salvar ouvidoria ──────────────────────────────────────────────────────────
st.divider()
if st.button("💾 Salvar Ouvidoria", type="primary", use_container_width=True):
    if not protocolo.strip():
        st.error("Informe o protocolo da ouvidoria.")
    elif not conteudo.strip():
        st.error("Informe o conteúdo da ouvidoria.")
    elif not st.session_state["reclamacoes_draft"]:
        st.warning("Adicione ao menos uma reclamação antes de salvar.")
    else:
        arquivos_validos = []
        for arq in (arquivos_upload or []):
            mime = arq.type or mimetypes.guess_type(arq.name)[0] or ""
            if mime not in ALLOWED_MIMES:
                st.error(f"Arquivo '{arq.name}' não é um tipo permitido.")
                st.stop()
            arquivos_validos.append(arq)

        arquivos_bytes = [(arq.name, arq.getbuffer().tobytes(), arq.type) for arq in arquivos_validos]

        status_inicial = (STATUS_AGUARDANDO_PERMISSIONARIA if enviado_permissionaria and prazo_permissionaria
                          else STATUS_AGUARDANDO_ACOES)

        recs_draft = [
            {
                "numero_item": r["numero_item"],
                "categoria_id": r["categoria_id"],
                "subcategoria_id": r["subcategoria_id"],
                "tipo_servico": r["tipo_servico"],
                "local_embarque": r["local_embarque"],
                "local_desembarque": r["local_desembarque"],
                "empresa_fretamento": r.get("empresa_fretamento"),
                "descricao": r["descricao"],
                "autos": [{"id": a["id"]} for a in r["autos"]],
            }
            for r in st.session_state["reclamacoes_draft"]
        ]

        try:
            result = post("/ouvidorias", json={
                "protocolo": protocolo,
                "conteudo": conteudo,
                "prazo": prazo.isoformat(),
                "prazo_permissionaria": prazo_permissionaria.isoformat() if prazo_permissionaria else None,
                "status": status_inicial,
                "criado_por_id": u["usuario_id"],
                "reclamacoes": recs_draft,
            })
            oid = result["id"]
            for nome_orig, conteudo_bytes, mime in arquivos_bytes:
                add_anexo(oid, conteudo_bytes, nome_orig, mime)

            st.session_state["reclamacoes_draft"] = []
            st.session_state["autos_checklist"] = []
            st.session_state["rec_alvo_anterior"] = None
            st.success("Ouvidoria salva com sucesso!")
            st.switch_page("pages/01_Ouvidorias.py")
        except Exception as e:
            msg = str(e)
            if "protocolo" in msg.lower() and ("unique" in msg.lower() or "duplicate" in msg.lower()):
                st.error(f"Já existe uma ouvidoria com o protocolo **{protocolo}**.")
            else:
                st.error(f"Erro ao salvar: {e}")
