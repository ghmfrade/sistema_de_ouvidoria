"""Detalhe, edição e ações sobre uma Ouvidoria específica."""

import mimetypes
import os
import sys
import uuid
from datetime import date

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import auth
from auth import usuario_logado
from api.client.enums import STATUS_OUVIDORIA, STATUS_RETORNO_TECNICO, TIPO_USUARIO_GESTOR
from api.client.catalogo_client import carregar_tecnicos_disponiveis
from api.client.ouvidoria_client import (
    buscar_ouvidoria_por_protocolo,
    carregar_detalhe_ouvidoria,
    atribuir_tecnico,
    atualizar_prazo_permissionaria,
    concluir_ouvidoria,
    delete_anexo,
    editar_ouvidoria,
    excluir_ouvidoria,
    add_anexo,
)
from utils import prazo_circle_label
from utils.formatters import TC_REGIOES
from components import reduz_margem_side_bar, reduz_margem_topo_page

st.set_page_config(page_title="Detalhe Ouvidoria", page_icon="🔍", layout="wide")
st.markdown('<style>[data-testid="stSidebar"]{width:220px!important;min-width:220px!important;}</style>', unsafe_allow_html=True)
auth.require_auth()

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
    st.caption(f"Perfil: {'Gestor' if u.get('tipo') == TIPO_USUARIO_GESTOR else 'Técnico'}")
    st.divider()
    protocolo_busca = st.text_input("**🔎 Buscar por protocolo**", placeholder="Ex: 000000000000")
    if st.button("Pesquisar", use_container_width=True):
        if protocolo_busca.strip():
            oid = buscar_ouvidoria_por_protocolo(protocolo_busca)
            if oid:
                st.session_state["ouvidoria_id"] = oid; st.rerun()
            else:
                st.error("Protocolo não cadastrado.")
        else:
            st.warning("Digite um protocolo.")
    st.divider()
    if st.button("← Voltar", use_container_width=True):
        st.switch_page("pages/01_Ouvidorias.py")
    if st.button("Sair", use_container_width=True):
        auth.fazer_logout(); st.rerun()

# ── Carrega ouvidoria ─────────────────────────────────────────────────────────
ouvidoria_id = st.session_state.get("ouvidoria_id")
if not ouvidoria_id:
    st.error("Nenhuma ouvidoria selecionada.")
    st.stop()

view = carregar_detalhe_ouvidoria(ouvidoria_id)
if view is None:
    st.error("Ouvidoria não encontrada.")
    st.stop()

ouvidoria = view
# Indexar rec_autos por rec_id e tecnicos_info por tecnico_id
rec_autos = {r["id"]: r["autos"] for r in ouvidoria["reclamacoes"]}
tecnicos_info = {a["tecnico_id"]: a for a in ouvidoria["atribuicoes"]}

# ── Cabeçalho ─────────────────────────────────────────────────────────────────
st.title(f"🔍 Ouvidoria #{ouvidoria['id']}")
st.markdown(f"**Protocolo:** {ouvidoria['protocolo']}")

prazo_date = date.fromisoformat(ouvidoria["prazo"]) if ouvidoria.get("prazo") else None
dias_restantes = (prazo_date - date.today()).days if prazo_date else 0
cor = "🔴" if dias_restantes < 0 else ("🟡" if dias_restantes <= 3 else "🟢")

cols_m = st.columns(5)
cols_m[0].metric("Status", ouvidoria["status"])
cols_m[1].metric("Prazo", ouvidoria["prazo"] or "–")
cols_m[2].metric("Dias restantes", f"{cor} {dias_restantes}")
if ouvidoria.get("concluido_em"):
    cols_m[4].metric("Concluída em", (ouvidoria["concluido_em"] or "")[:10])
if ouvidoria.get("prazo_permissionaria"):
    cols_m[3].metric("Prazo Permissionária", ouvidoria["prazo_permissionaria"])

# ── Dialog para editar ────────────────────────────────────────────────────────
@st.dialog("Editar Ouvidoria", width="large")
def dialog_editar():
    with st.form("form_editar"):
        novo_protocolo = st.text_input("Protocolo", value=ouvidoria["protocolo"])
        novo_conteudo  = st.text_area("Conteúdo da Ouvidoria", value=ouvidoria["conteudo"], height=150)
        novo_prazo     = st.date_input("Prazo", value=date.fromisoformat(ouvidoria["prazo"]) if ouvidoria.get("prazo") else date.today())
        novo_status    = st.selectbox("Status", STATUS_OUVIDORIA,
            index=STATUS_OUVIDORIA.index(ouvidoria["status"]) if ouvidoria["status"] in STATUS_OUVIDORIA else 0)
        salvar = st.form_submit_button("💾 Salvar alterações", type="primary", use_container_width=True)
    if salvar:
        editar_ouvidoria(ouvidoria_id, novo_protocolo, novo_conteudo, novo_prazo,
                         date.fromisoformat(ouvidoria["prazo_permissionaria"]) if ouvidoria.get("prazo_permissionaria") else None,
                         novo_status)
        st.success("Ouvidoria atualizada.")
        st.rerun()
    if st.button("Cancelar", use_container_width=True):
        st.rerun()

# ── Botões de ação (gestor) ──────────────────────────────────────────────────
if u.get("tipo") == TIPO_USUARIO_GESTOR:
    col_editar, col_prazo_perm, col_apagar_prazo, col_espaco = st.columns([1, 2, 2, 5])
    if col_editar.button("✏️ Editar", use_container_width=True):
        dialog_editar()

    prazo_perm_atual = ouvidoria.get("prazo_permissionaria")
    with col_prazo_perm.popover("📅 Prazo Permissionária", use_container_width=True):
        if prazo_perm_atual:
            data_resp_perm = max(
                (r["data_resposta"] for r in ouvidoria["respostas_permissionaria"] if r.get("data_resposta")),
                default=None,
            )
            perm_label, _ = prazo_circle_label(prazo_perm_atual, data_resp_perm)
            st.markdown(f"**Prazo atual:** {prazo_perm_atual} {perm_label}")
        else:
            st.markdown("**Prazo atual:** não definido")
        if st.button("✏️ Alterar data", key="btn_alterar_prazo_perm", use_container_width=True):
            st.session_state["alterar_prazo_perm"] = True
        if st.session_state.get("alterar_prazo_perm"):
            prazo_perm_default = date.fromisoformat(prazo_perm_atual) if prazo_perm_atual else date.today()
            novo_prazo_perm = st.date_input("Nova data", value=prazo_perm_default, label_visibility="collapsed")
            if st.button("💾 Salvar", key="btn_salvar_prazo_perm", use_container_width=True):
                atualizar_prazo_permissionaria(ouvidoria_id, novo_prazo_perm)
                st.session_state.pop("alterar_prazo_perm", None)
                st.toast("Prazo da permissionária atualizado."); st.rerun()
    if prazo_perm_atual:
        if col_apagar_prazo.button("🗑 Apagar prazo da Permissionária", use_container_width=True):
            atualizar_prazo_permissionaria(ouvidoria_id, None)
            st.toast("Prazo da permissionária removido."); st.rerun()

# ── Layout de 2 colunas ─────────────────────────────────────────────────────
col_esq, col_dir = st.columns([2, 1])

with col_esq:
    st.markdown("### 📝 Conteúdo da Ouvidoria")
    st.markdown(ouvidoria["conteudo"].replace("\n", "\n\n"))
    st.divider()

    st.markdown("### 🏢 Respostas da Permissionária")
    if not ouvidoria["respostas_permissionaria"]:
        st.info("Nenhuma resposta da permissionária.")
    else:
        for rp in ouvidoria["respostas_permissionaria"]:
            data = rp.get("data_resposta") or "?"
            with st.expander(f"{data} — por {rp['registrado_por_nome']}"):
                st.markdown(rp["conteudo"].replace("\n", "\n\n"))
    if st.button("✍️ Inserir Resposta Permissionária", type="primary"):
        st.switch_page("pages/04_Resposta_Permissionaria.py")
    st.divider()

    st.markdown("### 👨‍🔧 Respostas Técnicas")
    if not ouvidoria["respostas_tecnicas"]:
        st.info("Nenhuma resposta técnica registrada ainda.")
    else:
        for resp in ouvidoria["respostas_tecnicas"]:
            data = resp.get("data_resposta") or "?"
            with st.expander(f"{resp['tecnico_nome']} – {data}"):
                st.markdown(resp["texto_resposta"].replace("\n", "\n\n"))
    if u.get("tipo") != TIPO_USUARIO_GESTOR and u["usuario_id"] in tecnicos_info:
        if st.button("✍️ Inserir Resposta Técnica", type="primary"):
            st.switch_page("pages/05_Responder.py")

with col_dir:
    with st.container(border=True):
        st.markdown("### 📌 Reclamações")
        if not ouvidoria["reclamacoes"]:
            st.info("Nenhuma reclamação cadastrada.")
        else:
            for r in ouvidoria["reclamacoes"]:
                tipo_label = f" [{r['tipo_servico']}]" if r.get("tipo_servico") else ""
                with st.expander(f"Item {r['numero_item']} {tipo_label}"):
                    if r.get("categoria_nome"):  st.write(f"**Categoria:** {r['categoria_nome']}")
                    if r.get("subcategoria_nome"): st.write(f"**Subcategoria:** {r['subcategoria_nome']}")
                    if r.get("empresa_fretamento"): st.write(f"**Empresa:** {r['empresa_fretamento']}")
                    if r.get("local_embarque"):   st.write(f"**Embarque:** {r['local_embarque']}")
                    if r.get("local_desembarque"): st.write(f"**Desembarque:** {r['local_desembarque']}")
                    if r.get("descricao"):        st.write(f"**Descrição:** {r['descricao']}")
                    autos = r.get("autos", [])
                    if autos:
                        st.write(f"**Autos ({len(autos)}):**")
                        for a in autos:
                            tc = a.get("tc")
                            tc_info = f" – TC{tc} {TC_REGIOES[tc]}" if tc and tc in TC_REGIOES else ""
                            rm_info = f" | RM: {a['regiao_metropolitana']}" if a.get("regiao_metropolitana") else ""
                            denom = " – ".join(filter(None, [a.get("denominacao_a"), a.get("denominacao_b")])) or a["numero"]
                            st.write(f"- {a['numero']} – {a['permissionaria_nome']} – {denom}{tc_info}{rm_info}")
                    else:
                        st.write("**Autos:** Nenhum")

        st.divider()
        st.markdown("### 👥 Técnicos Responsáveis")
        if tecnicos_info:
            for tid, info in tecnicos_info.items():
                status = "✅" if info["respondido"] else "⏳"
                st.write(f"{status} {info['tecnico_nome']}")
        else:
            st.info("Nenhum técnico atribuído.")

        if u.get("tipo") == TIPO_USUARIO_GESTOR:
            todos_tecs = carregar_tecnicos_disponiveis()
            ja_atribuidos = set(tecnicos_info.keys())
            disponiveis = [(tid, nome) for tid, nome in todos_tecs if tid not in ja_atribuidos]
            if disponiveis:
                with st.popover("➕ Atribuir Técnico", use_container_width=True):
                    tec_sel_nome = st.selectbox("Técnico", [nome for _, nome in disponiveis], label_visibility="collapsed")
                    tec_sel_id = next(tid for tid, nome in disponiveis if nome == tec_sel_nome)
                    if st.button("Atribuir", use_container_width=True):
                        atribuir_tecnico(ouvidoria_id, tec_sel_id)
                        st.success("Técnico atribuído!"); st.rerun()
            else:
                st.caption("Todos os técnicos disponíveis já foram atribuídos.")

        st.divider()
        st.markdown("### 📎 Anexos")
        if ouvidoria["anexos"]:
            for an in ouvidoria["anexos"]:
                caminho = os.path.join(UPLOADS_DIR, an["nome_storage"])
                tamanho_kb = round(an["tamanho"] / 1024, 1) if an.get("tamanho") else "?"
                col_info, col_dl, col_del = st.columns([3, 1, 1])
                col_info.write(f"📎 **{an['nome_arquivo']}** ({tamanho_kb} KB)")
                if os.path.exists(caminho):
                    with open(caminho, "rb") as f:
                        col_dl.download_button("⬇", data=f.read(), file_name=an["nome_arquivo"],
                                               mime=an.get("tipo_mime") or "application/octet-stream",
                                               key=f"dl_{an['id']}", use_container_width=True)
                if u.get("tipo") == TIPO_USUARIO_GESTOR:
                    if col_del.button("🗑", key=f"del_anexo_{an['id']}", use_container_width=True):
                        nome_storage = delete_anexo(ouvidoria_id, an["id"])
                        if nome_storage:
                            try:
                                os.remove(os.path.join(UPLOADS_DIR, nome_storage))
                            except OSError:
                                pass
                        st.toast("Anexo excluído."); st.rerun()
        else:
            st.info("Nenhum anexo.")

        if u.get("tipo") == TIPO_USUARIO_GESTOR:
            with st.expander("➕ Adicionar Anexos"):
                novos_anexos = st.file_uploader(
                    "Selecione arquivos",
                    accept_multiple_files=True,
                    type=["pdf", "png", "jpg", "jpeg", "gif", "bmp", "mp4", "avi", "mov", "mkv", "webm"],
                    key="det_upload", label_visibility="collapsed",
                )
                if novos_anexos and st.button("📤 Enviar", use_container_width=True):
                    for arq in novos_anexos:
                        mime = arq.type or mimetypes.guess_type(arq.name)[0] or ""
                        if mime not in ALLOWED_MIMES:
                            st.error(f"Arquivo '{arq.name}' não é um tipo permitido.")
                            continue
                        add_anexo(ouvidoria_id, arq.getbuffer().tobytes(), arq.name, arq.type)
                    st.success("Anexos enviados."); st.rerun()

# ── Ações finais (gestor) ──────────────────────────────────────────────────
st.divider()
if u.get("tipo") == TIPO_USUARIO_GESTOR:
    col_acao1, col_acao2 = st.columns(2)
    pode_concluir = ouvidoria["status"] == STATUS_RETORNO_TECNICO
    if pode_concluir:
        if col_acao1.button("✅ Concluir Ouvidoria", type="primary", use_container_width=True):
            concluir_ouvidoria(ouvidoria_id)
            st.success("Ouvidoria concluída!")
            st.switch_page("pages/01_Ouvidorias.py")
    else:
        col_acao1.info("✅ Concluir ativado quando status for 'Retorno técnico'")

    if not st.session_state.get("confirmar_exclusao"):
        if col_acao2.button("🗑 Excluir Ouvidoria", type="secondary", use_container_width=True):
            st.session_state["confirmar_exclusao"] = True; st.rerun()
    else:
        st.warning("⚠️ Esta ação não pode ser desfeita. Confirmar exclusão?")
        col_s, col_n = st.columns(2)
        if col_s.button("Sim, excluir", type="primary", use_container_width=True):
            for an in ouvidoria["anexos"]:
                try:
                    os.remove(os.path.join(UPLOADS_DIR, an["nome_storage"]))
                except OSError:
                    pass
            excluir_ouvidoria(ouvidoria_id)
            st.session_state.pop("confirmar_exclusao", None)
            st.switch_page("pages/01_Ouvidorias.py")
        if col_n.button("Cancelar", use_container_width=True):
            st.session_state.pop("confirmar_exclusao", None); st.rerun()
