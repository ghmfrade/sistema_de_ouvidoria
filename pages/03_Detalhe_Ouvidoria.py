"""Detalhe, edição e ações sobre uma Ouvidoria específica."""
import streamlit as st
from datetime import date, datetime
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import auth
from auth import usuario_logado
from database.connection import db_session, get_session
from models import (
    Ouvidoria, StatusOuvidoria, Reclamacao, ReclamacaoAuto,
    OuvidoriaTecnico, RespostaTecnica, Usuario, TipoUsuario, AutoLinha,
)

st.set_page_config(page_title="Detalhe Ouvidoria", page_icon="🔍", layout="wide")
auth.require_auth()

u = usuario_logado()

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
            return None, [], [], []
        atribuicoes = list(o.atribuicoes)
        respostas = list(o.respostas)

        # Converte reclamações para dicts enquanto a sessão está aberta (evita DetachedInstanceError)
        recs_data = []
        for r in o.reclamacoes:
            recs_data.append({
                "id": r.id,
                "numero_item": r.numero_item,
                "categoria": r.categoria.nome if r.categoria else None,
                "local_embarque": r.local_embarque,
                "local_desembarque": r.local_desembarque,
                "descricao": r.descricao,
            })

        # Carrega detalhes dos autos de cada reclamação
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
                    })
            rec_autos[r.id] = autos_info

        # Carrega nomes dos técnicos
        tecnicos_info = {}
        for at in atribuicoes:
            tec = session.query(Usuario).filter_by(id=at.tecnico_id).first()
            if tec:
                tecnicos_info[at.tecnico_id] = {"nome": tec.nome, "respondido": at.respondido, "respondido_em": at.respondido_em}

        # Carrega nomes dos técnicos das respostas
        resp_info = []
        for r in respostas:
            tec = session.query(Usuario).filter_by(id=r.tecnico_id).first()
            resp_info.append({
                "id": r.id,
                "tecnico": tec.nome if tec else "?",
                "numero_sei": r.numero_sei_resposta,
                "data": r.data_resposta,
                "texto": r.texto_resposta,
            })

        session.expunge_all()
        return o, recs_data, rec_autos, atribuicoes, tecnicos_info, resp_info
    finally:
        session.close()


result = carregar_ouvidoria(ouvidoria_id)
if result[0] is None:
    st.error("Ouvidoria não encontrada.")
    st.stop()

ouvidoria, reclamacoes, rec_autos, atribuicoes, tecnicos_info, resp_info = result

# ── Cabeçalho ─────────────────────────────────────────────────────────────────
st.title(f"🔍 Ouvidoria #{ouvidoria.id} – {ouvidoria.numero_sei}")
dias_restantes = (ouvidoria.prazo - date.today()).days
cor = "🔴" if dias_restantes < 0 else ("🟡" if dias_restantes <= 3 else "🟢")

col_i1, col_i2, col_i3 = st.columns(3)
col_i1.metric("Status", ouvidoria.status.value)
col_i2.metric("Prazo", ouvidoria.prazo.strftime("%d/%m/%Y"))
col_i3.metric("Dias restantes", f"{cor} {dias_restantes}")

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_rec, tab_tecnicos, tab_respostas, tab_edicao = st.tabs(
    ["Reclamações", "Técnicos", "Respostas", "Editar"]
)

# ── Tab: Reclamações ──────────────────────────────────────────────────────────
with tab_rec:
    if not reclamacoes:
        st.info("Nenhuma reclamação cadastrada.")
    for r in reclamacoes:
        with st.expander(f"Item {r['numero_item']} – {r['categoria'] or 'Sem categoria'}"):
            st.write(f"**Embarque:** {r['local_embarque'] or '–'}")
            st.write(f"**Desembarque:** {r['local_desembarque'] or '–'}")
            st.write(f"**Descrição:** {r['descricao'] or '–'}")
            autos = rec_autos.get(r['id'], [])
            if autos:
                st.write(f"**Autos ({len(autos)}):**")
                for a in autos:
                    st.write(f"- {a['numero']} ({a['cidade_inicial']} até {a['cidade_final']}) - {a['permissionaria']}")
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

# ── Tab: Respostas ────────────────────────────────────────────────────────────
with tab_respostas:
    if not resp_info:
        st.info("Nenhuma resposta técnica registrada ainda.")
    for resp in resp_info:
        with st.expander(f"Resposta de {resp['tecnico']} – {resp['data'].strftime('%d/%m/%Y') if resp['data'] else '?'}"):
            st.write(f"**Nº SEI Resposta:** {resp['numero_sei'] or '–'}")
            st.write(f"**Texto:** {resp['texto']}")

# ── Tab: Editar ───────────────────────────────────────────────────────────────
with tab_edicao:
    if u.tipo != TipoUsuario.gestor:
        st.warning("Apenas gestores podem editar a ouvidoria.")
    else:
        with st.form("form_editar"):
            novo_sei = st.text_input("Nº Processo SEI", value=ouvidoria.numero_sei)
            novo_prazo = st.date_input("Prazo", value=ouvidoria.prazo)
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
                o_db.numero_sei = novo_sei.strip()
                o_db.prazo = novo_prazo
                o_db.status = StatusOuvidoria(novo_status_val)
            st.success("Ouvidoria atualizada.")
            st.rerun()

        st.divider()
        # Botão Concluir
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
        # Botão Excluir
        if not st.session_state.get("confirmar_exclusao"):
            if st.button("🗑 Excluir Ouvidoria", type="secondary"):
                st.session_state["confirmar_exclusao"] = True
                st.rerun()
        else:
            st.warning("⚠️ Esta ação não pode ser desfeita. Confirmar exclusão?")
            col_s, col_n = st.columns(2)
            if col_s.button("Sim, excluir", type="primary"):
                with db_session() as s:
                    o_db = s.query(Ouvidoria).filter_by(id=ouvidoria_id).first()
                    if o_db:
                        s.delete(o_db)
                st.session_state.pop("confirmar_exclusao", None)
                st.switch_page("pages/01_Ouvidorias.py")
            if col_n.button("Cancelar"):
                st.session_state.pop("confirmar_exclusao", None)
                st.rerun()
