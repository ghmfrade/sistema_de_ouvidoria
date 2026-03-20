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
from database.connection import db_session, get_session
from models import (
    AnexoOuvidoria,
    AutoLinha,
    Ouvidoria,
    OuvidoriaTecnico,
    RespostaTecnica,
    StatusOuvidoria,
    TipoUsuario,
    Usuario,
)

st.set_page_config(page_title="Detalhe Ouvidoria", page_icon="🔍", layout="wide")
st.markdown('<style>[data-testid="stSidebar"]{width:220px!important;min-width:220px!important;}</style>', unsafe_allow_html=True)
auth.require_auth()

u = usuario_logado()

UPLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

ALLOWED_MIMES = {
    "application/pdf",
    "image/png", "image/jpeg", "image/gif", "image/bmp",
    "video/mp4", "video/x-msvideo", "video/quicktime", "video/x-matroska", "video/webm",
}

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"**{u.nome}**")
    st.caption(f"Perfil: {'Gestor' if u.tipo.value == 'gestor' else 'Técnico'}")
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


def carregar_ouvidoria(oid: int):
    session = get_session()
    try:
        o = session.query(Ouvidoria).filter_by(id=oid).first()
        if not o:
            return None, [], {}, [], {}, [], [], []
        atribuicoes = list(o.atribuicoes)
        respostas = list(o.respostas)

        # Reclamações
        recs_data = []
        for r in o.reclamacoes:
            recs_data.append({
                "id": r.id,
                "numero_item": r.numero_item,
                "categoria": r.categoria.nome if r.categoria else None,
                "subcategoria": r.subcategoria.nome if r.subcategoria else None,
                "tipo_servico": r.tipo_servico.value if r.tipo_servico else None,
                "local_embarque": r.local_embarque,
                "local_desembarque": r.local_desembarque,
                "descricao": r.descricao,
                "empresa_fretamento": r.empresa_fretamento,
            })

        # Autos de cada reclamação
        rec_autos = {}
        for r in o.reclamacoes:
            autos_info = []
            for ra in r.autos_vinculados:
                auto = session.query(AutoLinha).filter_by(id=ra.auto_id).first()
                if auto:
                    perm_nome = auto.permissionaria.nome if auto.permissionaria else "–"
                    autos_info.append({
                        "numero": auto.numero,
                        "cidade_inicial": auto.cidade_inicial or "?",
                        "cidade_final": auto.cidade_final or "?",
                        "permissionaria": perm_nome,
                        "tipo": auto.tipo.value if auto.tipo else None,
                        "regiao_metropolitana": auto.regiao_metropolitana,
                    })
            rec_autos[r.id] = autos_info

        # Técnicos
        tecnicos_info = {}
        for at in atribuicoes:
            tec = session.query(Usuario).filter_by(id=at.tecnico_id).first()
            if tec:
                tecnicos_info[at.tecnico_id] = {
                    "nome": tec.nome,
                    "respondido": at.respondido,
                    "respondido_em": at.respondido_em,
                }

        # Respostas técnicas
        resp_info = []
        for r in respostas:
            tec = session.query(Usuario).filter_by(id=r.tecnico_id).first()
            resp_info.append({
                "id": r.id,
                "tecnico": tec.nome if tec else "?",
                "data": r.data_resposta,
                "texto": r.texto_resposta,
            })

        # Respostas da permissionária
        resps_perm = []
        for rp in o.respostas_permissionaria:
            resps_perm.append({
                "id": rp.id,
                "conteudo": rp.conteudo,
                "data_resposta": rp.data_resposta,
                "registrado_por": rp.registrado_por.nome if rp.registrado_por else "—",
            })

        # Anexos
        anexos = []
        for an in o.anexos:
            anexos.append({
                "id": an.id,
                "nome_arquivo": an.nome_arquivo,
                "nome_storage": an.nome_storage,
                "tipo_mime": an.tipo_mime,
                "tamanho": an.tamanho,
                "enviado_por": an.enviado_por.nome if an.enviado_por else "?",
                "criado_em": an.criado_em,
            })

        session.expunge_all()
        return o, recs_data, rec_autos, atribuicoes, tecnicos_info, resp_info, resps_perm, anexos
    finally:
        session.close()


result = carregar_ouvidoria(ouvidoria_id)
if result[0] is None:
    st.error("Ouvidoria não encontrada.")
    st.stop()

ouvidoria, reclamacoes, rec_autos, atribuicoes, tecnicos_info, resp_info, resps_perm, anexos_data = result

# ── Cabeçalho ─────────────────────────────────────────────────────────────────
st.title(f"🔍 Ouvidoria #{ouvidoria.id}")
st.markdown(f"**Protocolo:** {ouvidoria.protocolo}")
dias_restantes = (ouvidoria.prazo - date.today()).days
cor = "🔴" if dias_restantes < 0 else ("🟡" if dias_restantes <= 3 else "🟢")

cols_m = st.columns(4)
cols_m[0].metric("Status", ouvidoria.status.value)
cols_m[1].metric("Prazo", ouvidoria.prazo.strftime("%d/%m/%Y"))
cols_m[2].metric("Dias restantes", f"{cor} {dias_restantes}")
if ouvidoria.prazo_permissionaria:
    dias_perm = (ouvidoria.prazo_permissionaria - date.today()).days
    cor_p = "🔴" if dias_perm < 0 else "🟢"
    cols_m[3].metric("Prazo Permissionária", f"{ouvidoria.prazo_permissionaria.strftime('%d/%m/%Y')} {cor_p} {dias_perm}d")

# Conteúdo da ouvidoria
with st.expander("Conteúdo da Ouvidoria", expanded=True):
    st.text(ouvidoria.conteudo)

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_rec, tab_tecnicos, tab_respostas, tab_resp_perm, tab_anexos, tab_edicao = st.tabs(
    ["Reclamações", "Técnicos", "Respostas Técnicas", "Respostas Permissionária", "Anexos", "Editar"]
)

# ── Tab: Reclamações ──────────────────────────────────────────────────────────
with tab_rec:
    if not reclamacoes:
        st.info("Nenhuma reclamação cadastrada.")
    for r in reclamacoes:
        tipo_label = f" [{r['tipo_servico']}]" if r.get('tipo_servico') else ""
        with st.expander(f"Item {r['numero_item']} –{tipo_label} {r['categoria'] or 'Sem categoria'}"):
            if r.get('tipo_servico'):
                st.write(f"**Tipo de Serviço:** {r['tipo_servico']}")
            if r.get('subcategoria'):
                st.write(f"**Subcategoria:** {r['subcategoria']}")
            if r.get('empresa_fretamento'):
                st.write(f"**Empresa de Fretamento:** {r['empresa_fretamento']}")
            st.write(f"**Embarque:** {r['local_embarque'] or '–'}")
            st.write(f"**Desembarque:** {r['local_desembarque'] or '–'}")
            st.write(f"**Descrição:** {r['descricao'] or '–'}")
            autos = rec_autos.get(r['id'], [])
            if autos:
                st.write(f"**Autos ({len(autos)}):**")
                for a in autos:
                    rm_info = f" | RM: {a['regiao_metropolitana']}" if a.get('regiao_metropolitana') else ""
                    st.write(f"- {a['numero']} – {a['permissionaria']} – {a['cidade_inicial']} → {a['cidade_final']}{rm_info}")
            else:
                st.write("**Autos:** Nenhum vinculado")

# ── Tab: Técnicos ─────────────────────────────────────────────────────────────
with tab_tecnicos:
    if tecnicos_info:
        st.markdown("**Técnicos atribuídos:**")
        for tid, info in tecnicos_info.items():
            status_resp = "✅ Respondido" if info["respondido"] else "⏳ Aguardando"
            st.write(f"- {info['nome']} – {status_resp}")
    else:
        st.info("Nenhum técnico atribuído ainda.")

    if u.tipo == TipoUsuario.gestor:
        st.divider()
        st.markdown("**Atribuir técnico:**")

        @st.cache_data(ttl=60)
        def listar_tecnicos():
            s = get_session()
            try:
                tecs = s.query(Usuario).filter_by(tipo=TipoUsuario.tecnico, ativo=True).order_by(Usuario.nome).all()
                return [(t.id, t.nome) for t in tecs]
            finally:
                s.close()

        todos_tecs = listar_tecnicos()
        ja_atribuidos = set(tecnicos_info.keys())
        disponiveis = [(tid, nome) for tid, nome in todos_tecs if tid not in ja_atribuidos]

        if disponiveis:
            tec_sel_nome = st.selectbox("Técnico", [nome for _, nome in disponiveis])
            tec_sel_id = next(tid for tid, nome in disponiveis if nome == tec_sel_nome)
            if st.button("Atribuir técnico"):
                with db_session() as s:
                    o_db = s.query(Ouvidoria).filter_by(id=ouvidoria_id).first()
                    s.add(OuvidoriaTecnico(ouvidoria_id=ouvidoria_id, tecnico_id=tec_sel_id))
                    if o_db.status == StatusOuvidoria.AGUARDANDO_ACOES:
                        o_db.status = StatusOuvidoria.EM_ANALISE_TECNICA
                st.success("Técnico atribuído. Status atualizado para Em análise técnica.")
                listar_tecnicos.clear()
                st.rerun()
        else:
            st.info("Todos os técnicos disponíveis já foram atribuídos.")

# ── Tab: Respostas Técnicas ──────────────────────────────────────────────────
with tab_respostas:
    if not resp_info:
        st.info("Nenhuma resposta técnica registrada ainda.")
    for resp in resp_info:
        with st.expander(f"Resposta de {resp['tecnico']} – {resp['data'].strftime('%d/%m/%Y') if resp['data'] else '?'}"):
            st.write(f"**Texto:** {resp['texto']}")

# ── Tab: Respostas Permissionária ────────────────────────────────────────────
with tab_resp_perm:
    if not resps_perm:
        st.info("Nenhuma resposta da permissionária registrada.")
    for rp in resps_perm:
        with st.expander(f"{rp['data_resposta'].strftime('%d/%m/%Y')} — por {rp['registrado_por']}"):
            st.text(rp["conteudo"])

# ── Tab: Anexos ──────────────────────────────────────────────────────────────
with tab_anexos:
    if anexos_data:
        for an in anexos_data:
            caminho = os.path.join(UPLOADS_DIR, an["nome_storage"])
            tamanho_kb = round(an["tamanho"] / 1024, 1) if an["tamanho"] else "?"
            col_info, col_dl, col_del = st.columns([4, 1, 1])
            col_info.write(f"📎 **{an['nome_arquivo']}** ({tamanho_kb} KB) — {an['enviado_por']} em {an['criado_em'].strftime('%d/%m/%Y %H:%M') if an['criado_em'] else '?'}")
            if os.path.exists(caminho):
                with open(caminho, "rb") as f:
                    col_dl.download_button(
                        "⬇",
                        data=f.read(),
                        file_name=an["nome_arquivo"],
                        mime=an["tipo_mime"] or "application/octet-stream",
                        key=f"dl_{an['id']}",
                    )
            if u.tipo == TipoUsuario.gestor:
                if col_del.button("🗑", key=f"del_anexo_{an['id']}"):
                    with db_session() as s:
                        obj = s.get(AnexoOuvidoria, an["id"])
                        if obj:
                            # Remove arquivo do disco
                            try:
                                os.remove(caminho)
                            except OSError:
                                pass
                            s.delete(obj)
                    st.toast("Anexo excluído.")
                    st.rerun()
    else:
        st.info("Nenhum anexo.")

    # Upload de novos anexos (gestor)
    if u.tipo == TipoUsuario.gestor:
        st.divider()
        novos_anexos = st.file_uploader(
            "Adicionar anexos",
            accept_multiple_files=True,
            type=["pdf", "png", "jpg", "jpeg", "gif", "bmp", "mp4", "avi", "mov", "mkv", "webm"],
            key="det_upload",
        )
        if novos_anexos and st.button("📤 Enviar anexos", key="btn_enviar_anexos"):
            with db_session() as session:
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
                    session.add(AnexoOuvidoria(
                        ouvidoria_id=ouvidoria_id,
                        nome_arquivo=arq.name,
                        nome_storage=nome_storage,
                        tipo_mime=arq.type,
                        tamanho=arq.size,
                        enviado_por_id=u.id,
                    ))
            st.success("Anexos enviados.")
            st.rerun()

# ── Tab: Editar ───────────────────────────────────────────────────────────────
with tab_edicao:
    if u.tipo != TipoUsuario.gestor:
        st.warning("Apenas gestores podem editar a ouvidoria.")
    else:
        with st.form("form_editar"):
            novo_protocolo = st.text_input("Protocolo", value=ouvidoria.protocolo)
            novo_conteudo = st.text_area("Conteúdo da Ouvidoria", value=ouvidoria.conteudo, height=200)
            novo_prazo = st.date_input("Prazo", value=ouvidoria.prazo)
            novo_prazo_perm = st.date_input(
                "Prazo Permissionária",
                value=ouvidoria.prazo_permissionaria or date.today(),
                disabled=ouvidoria.prazo_permissionaria is None,
            )
            habilitar_prazo_perm = st.checkbox(
                "Definir prazo da permissionária",
                value=ouvidoria.prazo_permissionaria is not None,
            )
            status_opcoes = [s.value for s in StatusOuvidoria]
            novo_status_val = st.selectbox(
                "Status",
                status_opcoes,
                index=status_opcoes.index(ouvidoria.status.value),
            )
            salvar_edicao = st.form_submit_button("💾 Salvar alterações")

        if salvar_edicao:
            with db_session() as s:
                o_db = s.query(Ouvidoria).filter_by(id=ouvidoria_id).first()
                o_db.protocolo = novo_protocolo.strip()
                o_db.conteudo = novo_conteudo.strip()
                o_db.prazo = novo_prazo
                o_db.prazo_permissionaria = novo_prazo_perm if habilitar_prazo_perm else None
                o_db.status = StatusOuvidoria(novo_status_val)
            st.success("Ouvidoria atualizada.")
            st.rerun()

        st.divider()
        # Concluir
        pode_concluir = ouvidoria.status == StatusOuvidoria.RETORNO_TECNICO
        if pode_concluir:
            if st.button("✅ Concluir Ouvidoria", type="primary"):
                with db_session() as s:
                    o_db = s.query(Ouvidoria).filter_by(id=ouvidoria_id).first()
                    o_db.status = StatusOuvidoria.CONCLUIDO
                st.success("Ouvidoria concluída!")
                st.rerun()
        else:
            st.info("O botão 'Concluir' fica disponível quando o status for 'Retorno técnico'.")

        st.divider()
        # Excluir
        if not st.session_state.get("confirmar_exclusao"):
            if st.button("🗑 Excluir Ouvidoria", type="secondary"):
                st.session_state["confirmar_exclusao"] = True
                st.rerun()
        else:
            st.warning("⚠️ Esta ação não pode ser desfeita. Confirmar exclusão?")
            col_s, col_n = st.columns(2)
            if col_s.button("Sim, excluir", type="primary"):
                # Remove anexos do disco
                for an in anexos_data:
                    try:
                        os.remove(os.path.join(UPLOADS_DIR, an["nome_storage"]))
                    except OSError:
                        pass
                with db_session() as s:
                    o_db = s.query(Ouvidoria).filter_by(id=ouvidoria_id).first()
                    if o_db:
                        s.delete(o_db)
                st.session_state.pop("confirmar_exclusao", None)
                st.switch_page("pages/01_Ouvidorias.py")
            if col_n.button("Cancelar"):
                st.session_state.pop("confirmar_exclusao", None)
                st.rerun()
