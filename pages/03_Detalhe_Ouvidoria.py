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
from models import StatusOuvidoria, TipoUsuario
from repositories.ouvidoria_write_repo import (
    add_anexos,
    atribuir_tecnico,
    atualizar_prazo_permissionaria,
    concluir_ouvidoria,
    delete_anexo,
    editar_ouvidoria,
    excluir_ouvidoria,
)
from utils import buscar_ouvidoria_por_protocolo, carregar_detalhe_ouvidoria, carregar_tecnicos_disponiveis, prazo_circle_label
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
    st.markdown(f"**{u.nome}**")
    st.caption(f"Perfil: {'Gestor' if u.tipo.value == 'gestor' else 'Técnico'}")
    st.divider()
    protocolo_busca = st.text_input("**🔎 Buscar por protocolo**", label_visibility="visible", placeholder="Ex: 000000000000")
    if st.button("Pesquisar", use_container_width=True):
        if protocolo_busca.strip():
            oid = buscar_ouvidoria_por_protocolo(protocolo_busca)
            if oid:
                st.session_state["ouvidoria_id"] = oid
                st.rerun()
            else:
                st.error("Protocolo não cadastrado.")
        else:
            st.warning("Digite um protocolo.")
    st.divider()
    if st.button("← Voltar", use_container_width=True):
        st.switch_page("pages/01_Ouvidorias.py")
    if st.button("Sair", use_container_width=True):
        auth.fazer_logout()
        st.rerun()

# ── Carrega ouvidoria ─────────────────────────────────────────────────────────
ouvidoria_id = st.session_state.get("ouvidoria_id")
if not ouvidoria_id:
    st.error("Nenhuma ouvidoria selecionada.")
    st.stop()

view = carregar_detalhe_ouvidoria(ouvidoria_id)
if view is None:
    st.error("Ouvidoria não encontrada.")
    st.stop()

ouvidoria     = view["ouvidoria"]
rec_autos     = view["rec_autos"]
tecnicos_info = view["tecnicos_info"]

# ── Cabeçalho ─────────────────────────────────────────────────────────────────
st.title(f"🔍 Ouvidoria #{ouvidoria['id']}")
st.markdown(f"**Protocolo:** {ouvidoria['protocolo']}")
dias_restantes = (ouvidoria["prazo"] - date.today()).days
cor = "🔴" if dias_restantes < 0 else ("🟡" if dias_restantes <= 3 else "🟢")

cols_m = st.columns(5)
cols_m[0].metric("Status", ouvidoria["status"])
cols_m[1].metric("Prazo", ouvidoria["prazo"].strftime("%d/%m/%Y"))
cols_m[2].metric("Dias restantes", f"{cor} {dias_restantes}")
if ouvidoria["concluido_em"]:
    cols_m[4].metric("Concluída em", ouvidoria["concluido_em"].strftime("%d/%m/%Y %H:%M"))
if ouvidoria["prazo_permissionaria"]:
    cols_m[3].metric("Prazo Permissionária", f"{ouvidoria['prazo_permissionaria'].strftime('%d/%m/%Y')}")

# ── Dialog para editar a ouvidoria ──────────────────────────────────────────
@st.dialog("Editar Ouvidoria", width="large")
def dialog_editar():
    with st.form("form_editar"):
        novo_protocolo = st.text_input("Protocolo", value=ouvidoria["protocolo"])
        novo_conteudo = st.text_area("Conteúdo da Ouvidoria", value=ouvidoria["conteudo"], height=150)
        novo_prazo = st.date_input("Prazo", value=ouvidoria["prazo"])
        status_opcoes = [s.value for s in StatusOuvidoria]
        novo_status_val = st.selectbox(
            "Status",
            status_opcoes,
            index=status_opcoes.index(ouvidoria["status"]),
        )
        salvar_edicao = st.form_submit_button("💾 Salvar alterações", type="primary", use_container_width=True)

    if salvar_edicao:
        editar_ouvidoria(
            ouvidoria_id,
            novo_protocolo,
            novo_conteudo,
            novo_prazo,
            ouvidoria["prazo_permissionaria"],
            novo_status_val,
        )
        st.success("Ouvidoria atualizada.")
        st.rerun()

    if st.button("Cancelar", use_container_width=True):
        st.rerun()

# ── Botões de ação (gestor) ──────────────────────────────────────────────────
if u.tipo == TipoUsuario.gestor:
    col_editar, col_prazo_perm, col_apagar_prazo, col_espaco = st.columns([1, 2, 2, 5])

    if col_editar.button("✏️ Editar", use_container_width=True):
        dialog_editar()

    prazo_perm_atual = ouvidoria["prazo_permissionaria"]
    with col_prazo_perm.popover("📅 Prazo Permissionária", use_container_width=True):
        if prazo_perm_atual:
            data_resp_perm = max(
                (r["data_resposta"] for r in ouvidoria["respostas_permissionaria"] if r["data_resposta"]),
                default=None,
            )
            perm_label, _ = prazo_circle_label(prazo_perm_atual, data_resp_perm)
            st.markdown(f"**Prazo atual:** {prazo_perm_atual.strftime('%d/%m/%Y')} {perm_label}")
        else:
            st.markdown("**Prazo atual:** não definido")

        if st.button("✏️ Alterar data", key="btn_alterar_prazo_perm", use_container_width=True):
            st.session_state["alterar_prazo_perm"] = True

        if st.session_state.get("alterar_prazo_perm"):
            novo_prazo_perm = st.date_input("Nova data", value=prazo_perm_atual or date.today(), label_visibility="collapsed")
            if st.button("💾 Salvar", key="btn_salvar_prazo_perm", use_container_width=True):
                atualizar_prazo_permissionaria(ouvidoria_id, novo_prazo_perm)
                st.session_state.pop("alterar_prazo_perm", None)
                st.toast("Prazo da permissionária atualizado.")
                st.rerun()

    if prazo_perm_atual:
        if col_apagar_prazo.button("🗑 Apagar prazo da Permissionária", use_container_width=True):
            atualizar_prazo_permissionaria(ouvidoria_id, None)
            st.toast("Prazo da permissionária removido.")
            st.rerun()

# ── Layout de 2 colunas ─────────────────────────────────────────────────────
col_esq, col_dir = st.columns([2, 1])

# ── COLUNA ESQUERDA ─────────────────────────────────────────────────────────
with col_esq:
    st.markdown("### 📝 Conteúdo da Ouvidoria")
    st.markdown(ouvidoria["conteudo"].replace("\n", "\n\n"))

    st.divider()

    st.markdown("### 🏢 Respostas da Permissionária")
    if not ouvidoria["respostas_permissionaria"]:
        st.info("Nenhuma resposta da permissionária.")
    else:
        for rp in ouvidoria["respostas_permissionaria"]:
            data = rp['data_resposta'].strftime('%d/%m/%Y') if rp['data_resposta'] else "?"
            with st.expander(f"{data} — por {rp['registrado_por_nome']}"):
                st.markdown(rp["conteudo"].replace("\n", "\n\n"))
    if st.button("✍️ Inserir Resposta Permissionária", type="primary", use_container_width=False):
        st.switch_page("pages/04_Resposta_Permissionaria.py")
    st.divider()

    st.markdown("### 👨‍🔧 Respostas Técnicas")
    if not ouvidoria["respostas_tecnicas"]:
        st.info("Nenhuma resposta técnica registrada ainda.")
    else:
        for resp in ouvidoria["respostas_tecnicas"]:
            data = resp['data_resposta'].strftime('%d/%m/%Y') if resp['data_resposta'] else "?"
            with st.expander(f"{resp['tecnico_nome']} – {data}"):
                st.markdown(resp["texto_resposta"].replace("\n", "\n\n"))

    # Botão para técnico inserir resposta
    if u.tipo == TipoUsuario.tecnico and u.id in tecnicos_info:
        if st.button("✍️ Inserir Resposta Técnica", type="primary", use_container_width=False):
            st.switch_page("pages/05_Responder.py")

# ── COLUNA DIREITA ──────────────────────────────────────────────────────────
with col_dir:
    container_reclamacoes = st.container(border=True)

    with container_reclamacoes:
        st.markdown("### 📌 Reclamações")
        if not ouvidoria["reclamacoes"]:
            st.info("Nenhuma reclamação cadastrada.")
        else:
            for r in ouvidoria["reclamacoes"]:
                tipo_label = f" [{r['tipo_servico']}]" if r.get('tipo_servico') else ""
                with st.expander(f"Item {r['numero_item']} {tipo_label}"):
                    if r.get('categoria_nome'):
                        st.write(f"**Categoria:** {r['categoria_nome']}")
                    if r.get('subcategoria_nome'):
                        st.write(f"**Subcategoria:** {r['subcategoria_nome']}")
                    if r.get('empresa_fretamento'):
                        st.write(f"**Empresa:** {r['empresa_fretamento']}")
                    if r.get('local_embarque'):
                        st.write(f"**Embarque:** {r['local_embarque']}")
                    if r.get('local_desembarque'):
                        st.write(f"**Desembarque:** {r['local_desembarque']}")
                    if r.get('descricao'):
                        st.write(f"**Descrição:** {r['descricao']}")

                    autos = rec_autos.get(r['id'], [])
                    if autos:
                        st.write(f"**Autos ({len(autos)}):**")
                        for a in autos:
                            from utils.formatters import fmt_auto, TC_REGIOES
                            rm_info = f" | RM: {a['regiao_metropolitana']}" if a.get('regiao_metropolitana') else ""
                            tc = a.get("tc")
                            tc_info = f" – TC{tc} {TC_REGIOES[tc]}" if tc and tc in TC_REGIOES else ""
                            denom = " – ".join(filter(None, [a.get("denominacao_a"), a.get("denominacao_b")])) or a["numero"]
                            st.write(f"- {a['numero']} – {a['permissionaria_nome']} – {denom}{tc_info}{rm_info}")
                    else:
                        st.write("**Autos:** Nenhum")

        st.divider()
        st.markdown("### 👥 Técnicos Responsáveis")
        if tecnicos_info:
            for tid, info in tecnicos_info.items():
                status = "✅" if info["respondido"] else "⏳"
                col_tec, col_popover = st.columns([4, 1])
                col_tec.write(f"{status} {info['tecnico_nome']}")
        else:
            st.info("Nenhum técnico atribuído.")

        if u.tipo == TipoUsuario.gestor:
            todos_tecs = carregar_tecnicos_disponiveis()
            ja_atribuidos = set(tecnicos_info.keys())
            disponiveis = [(tid, nome) for tid, nome in todos_tecs if tid not in ja_atribuidos]

            if disponiveis:
                with st.popover("➕ Atribuir Técnico", use_container_width=True):
                    tec_sel_nome = st.selectbox("Técnico", [nome for _, nome in disponiveis], label_visibility="collapsed")
                    tec_sel_id = next(tid for tid, nome in disponiveis if nome == tec_sel_nome)
                    if st.button("Atribuir", use_container_width=True):
                        atribuir_tecnico(ouvidoria_id, tec_sel_id)
                        st.success("Técnico atribuído!")
                        carregar_tecnicos_disponiveis.clear()
                        st.rerun()
            else:
                st.caption("Todos os técnicos disponíveis já foram atribuídos.")
        
        st.divider()

        st.markdown("### 📎 Anexos")
        if ouvidoria["anexos"]:
            for an in ouvidoria["anexos"]:
                caminho = os.path.join(UPLOADS_DIR, an["nome_storage"])
                tamanho_kb = round(an["tamanho"] / 1024, 1) if an["tamanho"] else "?"

                col_info, col_dl, col_del = st.columns([3, 1, 1])
                col_info.write(f"📎 **{an['nome_arquivo']}** ({tamanho_kb} KB)")

                if os.path.exists(caminho):
                    with open(caminho, "rb") as f:
                        col_dl.download_button(
                            "⬇",
                            data=f.read(),
                            file_name=an["nome_arquivo"],
                            mime=an["tipo_mime"] or "application/octet-stream",
                            key=f"dl_{an['id']}",
                            use_container_width=True,
                        )

                if u.tipo == TipoUsuario.gestor:
                    if col_del.button("🗑", key=f"del_anexo_{an['id']}", use_container_width=True):
                        nome_storage = delete_anexo(an["id"])
                        if nome_storage:
                            try:
                                os.remove(os.path.join(UPLOADS_DIR, nome_storage))
                            except OSError:
                                pass
                        st.toast("Anexo excluído.")
                        st.rerun()
        else:
            st.info("Nenhum anexo.")

        # Upload de novos anexos (gestor)
        if u.tipo == TipoUsuario.gestor:
            with st.expander("➕ Adicionar Anexos"):
                novos_anexos = st.file_uploader(
                    "Selecione arquivos",
                    accept_multiple_files=True,
                    type=["pdf", "png", "jpg", "jpeg", "gif", "bmp", "mp4", "avi", "mov", "mkv", "webm"],
                    key="det_upload",
                    label_visibility="collapsed",
                )
                if novos_anexos and st.button("📤 Enviar", use_container_width=True):
                    anexos_meta = []
                    for arq in novos_anexos:
                        mime = arq.type or mimetypes.guess_type(arq.name)[0] or ""
                        if mime not in ALLOWED_MIMES:
                            st.error(f"Arquivo '{arq.name}' não é um tipo permitido.")
                            continue
                        ext = os.path.splitext(arq.name)[1]
                        nome_storage = f"{uuid.uuid4().hex}{ext}"
                        caminho_arq = os.path.join(UPLOADS_DIR, nome_storage)
                        with open(caminho_arq, "wb") as f:
                            f.write(arq.getbuffer())
                        anexos_meta.append({
                            "nome_arquivo": arq.name,
                            "nome_storage": nome_storage,
                            "tipo_mime": arq.type,
                            "tamanho": arq.size,
                            "enviado_por_id": u.id,
                        })
                    if anexos_meta:
                        add_anexos(ouvidoria_id, anexos_meta)
                    st.success("Anexos enviados.")
                    st.rerun()

# ── Seção de ações finais (gestor) ──────────────────────────────────────────
st.divider()

if u.tipo == TipoUsuario.gestor:
    col_acao1, col_acao2 = st.columns(2)

    pode_concluir = ouvidoria["status"] == StatusOuvidoria.RETORNO_TECNICO.value
    if pode_concluir:
        if col_acao1.button("✅ Concluir Ouvidoria", type="primary", use_container_width=True):
            concluir_ouvidoria(ouvidoria_id)
            st.success("Ouvidoria concluída!")
            st.rerun()
    else:
        col_acao1.info("✅ Concluir ativado quando status for 'Retorno técnico'")

    if not st.session_state.get("confirmar_exclusao"):
        if col_acao2.button("🗑 Excluir Ouvidoria", type="secondary", use_container_width=True):
            st.session_state["confirmar_exclusao"] = True
            st.rerun()
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
            st.session_state.pop("confirmar_exclusao", None)
            st.rerun()
