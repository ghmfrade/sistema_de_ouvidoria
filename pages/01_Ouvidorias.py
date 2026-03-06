"""Lista de Ouvidorias – visão geral com filtros."""
import streamlit as st
from datetime import date
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import auth
from auth import usuario_logado
from database.connection import get_session, db_session
from models import Ouvidoria, StatusOuvidoria, Usuario, TipoUsuario, OuvidoriaTecnico

st.set_page_config(page_title="Ouvidorias", page_icon="📋", layout="wide")
auth.require_auth()

u = usuario_logado()

STATUS_EMOJI = {
    StatusOuvidoria.AGUARDANDO_ACOES:          "🔴",
    StatusOuvidoria.AGUARDANDO_PERMISSIONARIA: "🟡",
    StatusOuvidoria.EM_ANALISE_TECNICA:        "🟣",
    StatusOuvidoria.RETORNO_TECNICO:           "🟢",
    StatusOuvidoria.CONCLUIDO:                 "⚫",
}


def cor_prazo(prazo: date) -> str:
    dias = (prazo - date.today()).days
    if dias < 0:
        return "🔴"
    if dias <= 3:
        return "🟡"
    return "🟢"


def carregar_ouvidorias(filtro_status=None, filtro_periodo=None, ocultar_concluidos=True):
    session = get_session()
    try:
        q = session.query(Ouvidoria)
        if u.tipo == TipoUsuario.tecnico:
            q = (
                q.join(OuvidoriaTecnico, OuvidoriaTecnico.ouvidoria_id == Ouvidoria.id)
                .filter(OuvidoriaTecnico.tecnico_id == u.id)
            )
        if filtro_status:
            q = q.filter(Ouvidoria.status == filtro_status)
        elif ocultar_concluidos:
            q = q.filter(Ouvidoria.status != StatusOuvidoria.CONCLUIDO)
        if filtro_periodo:
            inicio, fim = filtro_periodo
            q = q.filter(Ouvidoria.criado_em >= inicio, Ouvidoria.criado_em <= fim)
        ouvidorias = q.order_by(Ouvidoria.prazo.asc()).all()

        resultado = []
        for o in ouvidorias:
            atribuicoes = session.query(OuvidoriaTecnico).filter_by(ouvidoria_id=o.id).all()
            if atribuicoes:
                partes = []
                seen: set[str] = set()
                pendentes = []
                todos_responderam = True
                for at in atribuicoes:
                    tec = session.query(Usuario).filter_by(id=at.tecnico_id).first()
                    if tec:
                        ger = tec.gerencia.nome if tec.gerencia else "?"
                        coord = tec.coordenacao.nome if tec.coordenacao else "?"
                        chave = f"{ger}-{coord}"
                        if chave not in seen:
                            partes.append(chave)
                            seen.add(chave)
                        if not at.respondido:
                            pendentes.append(tec.nome)
                            todos_responderam = False
                # Após retorno técnico, volta para SUCOL
                if todos_responderam:
                    coord_ger = "SUCOL - Ouvidoria"
                else:
                    coord_ger = " / ".join(partes) if partes else "Em análise"
                responsaveis = ", ".join(pendentes) if pendentes else "–"
            else:
                coord_ger = "SUCOL - Ouvidoria"
                responsaveis = "–"

            resultado.append({
                "id": o.id,
                "numero_sei": o.numero_sei,
                "status": o.status,
                "prazo": o.prazo,
                "coord_ger": coord_ger,
                "responsaveis": responsaveis,
            })
        return resultado
    finally:
        session.close()


def excluir_ouvidoria(oid: int):
    with db_session() as s:
        o = s.query(Ouvidoria).filter_by(id=oid).first()
        if o:
            s.delete(o)


def concluir_ouvidoria(oid: int):
    with db_session() as s:
        o = s.query(Ouvidoria).filter_by(id=oid).first()
        if o:
            o.status = StatusOuvidoria.CONCLUIDO


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"**{u.nome}**")
    st.caption(f"Perfil: {'Gestor' if u.tipo.value == 'gestor' else 'Técnico'}")
    st.divider()
    if st.button("Sair", use_container_width=True):
        auth.fazer_logout()
        st.rerun()

# ── Filtros ──────────────────────────────────────────────────────────────────
st.title("📋 Ouvidorias")

col_f1, col_f2, col_f3, col_f4 = st.columns([2, 1, 2, 1])
with col_f1:
    opcoes_status = ["Todos"] + [s.value for s in StatusOuvidoria]
    sel_status = st.selectbox("Filtrar por Status", opcoes_status)
with col_f2:
    ocultar_concluidos = st.checkbox("Ocultar concluídos", value=True)
with col_f3:
    usar_periodo = st.checkbox("Filtrar por período de cadastro")
    periodo = None
    if usar_periodo:
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            data_ini = st.date_input("De", value=date.today().replace(day=1))
        with col_d2:
            data_fim = st.date_input("Até", value=date.today())
        periodo = (data_ini, data_fim)
with col_f4:
    st.write("")
    if u.tipo == TipoUsuario.gestor:
        if st.button("+ Nova Ouvidoria", use_container_width=True, type="primary"):
            st.switch_page("pages/02_Nova_Ouvidoria.py")

filtro_s = None if sel_status == "Todos" else StatusOuvidoria(sel_status)
ouvidorias = carregar_ouvidorias(
    filtro_status=filtro_s,
    filtro_periodo=periodo,
    ocultar_concluidos=ocultar_concluidos if sel_status == "Todos" else False,
)

st.divider()

if not ouvidorias:
    st.info("Nenhuma ouvidoria encontrada com os filtros aplicados.")
else:
    # Cabeçalho
    if u.tipo == TipoUsuario.gestor:
        col_sizes = [1, 3, 3, 3, 3, 2, 1, 1, 1, 1]
        cols_header = st.columns(col_sizes)
        headers = ["**#**", "**Nº SEI**", "**Status**", "**Coord./Gerência**",
                    "**Responsáveis**", "**Prazo**", "**Dias**", "", "", ""]
    else:
        col_sizes = [1, 3, 3, 3, 3, 2, 1, 1, 1]
        cols_header = st.columns(col_sizes)
        headers = ["**#**", "**Nº SEI**", "**Status**", "**Coord./Gerência**",
                    "**Responsáveis**", "**Prazo**", "**Dias**", "", ""]
    for idx, h in enumerate(headers):
        if h:
            cols_header[idx].markdown(h)
    st.divider()

    for o in ouvidorias:
        dias_restantes = (o["prazo"] - date.today()).days
        emoji_status = STATUS_EMOJI.get(o["status"], "")
        status_label = f"{emoji_status} {o['status'].value}"
        label_dias = f"{cor_prazo(o['prazo'])} {dias_restantes}d"

        confirmar_key = f"confirmar_excluir_{o['id']}"

        cols = st.columns(col_sizes)

        cols[0].write(o["id"])
        cols[1].write(o["numero_sei"])
        cols[2].write(status_label)
        cols[3].write(o["coord_ger"])
        cols[4].write(o["responsaveis"])
        cols[5].write(o["prazo"].strftime("%d/%m/%Y"))
        cols[6].write(label_dias)

        # Botão Abrir (ícone)
        if cols[7].button("🔍", key=f"abrir_{o['id']}", help="Abrir detalhe"):
            st.session_state["ouvidoria_id"] = o["id"]
            st.switch_page("pages/03_Detalhe_Ouvidoria.py")

        # Botão Responder (ícone)
        if cols[8].button("✍️", key=f"resp_{o['id']}", help="Responder"):
            st.session_state["ouvidoria_id"] = o["id"]
            # Limpa estado anterior de edição de resposta
            st.session_state.pop("resp_recs_edit", None)
            st.session_state.pop("resp_autos_checklist", None)
            st.session_state.pop("resp_rec_alvo_anterior", None)
            st.switch_page("pages/04_Responder.py")

        if u.tipo == TipoUsuario.gestor:
            with cols[9]:
                pode_concluir = o["status"] == StatusOuvidoria.RETORNO_TECNICO

                with st.popover("⚙"):
                    if pode_concluir:
                        if st.button("✅ Concluir", key=f"concluir_{o['id']}"):
                            concluir_ouvidoria(o["id"])
                            st.toast("Ouvidoria concluída!", icon="✅")
                            st.rerun()

                    if not st.session_state.get(confirmar_key):
                        if st.button("🗑 Excluir", key=f"excluir_{o['id']}"):
                            st.session_state[confirmar_key] = True
                            st.rerun()
                    else:
                        st.warning("Confirmar exclusão?")
                        if st.button("Sim", key=f"sim_excluir_{o['id']}"):
                            excluir_ouvidoria(o["id"])
                            st.session_state.pop(confirmar_key, None)
                            st.toast("Ouvidoria excluída.", icon="🗑")
                            st.rerun()
                        if st.button("Não", key=f"nao_excluir_{o['id']}"):
                            st.session_state.pop(confirmar_key, None)
                            st.rerun()
