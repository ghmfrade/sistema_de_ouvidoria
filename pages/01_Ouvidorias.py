"""Lista de Ouvidorias – visão geral com filtros."""

import os
import sys
from datetime import date

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import auth
from auth import usuario_logado
from models import StatusOuvidoria, TipoUsuario
from utils import (
    atribuir_tecnico,
    carregar_tecnicos_disponiveis,
    concluir_ouvidoria,
    excluir_ouvidoria,
    listar_ouvidorias,
    prazo_circle_label,
)

st.set_page_config(page_title="Ouvidorias", page_icon="📋", layout="wide")
st.markdown('<style>[data-testid="stSidebar"]{width:220px!important;min-width:220px!important;}</style>', unsafe_allow_html=True)
auth.require_auth()

u = usuario_logado()

STATUS_EMOJI = {
    StatusOuvidoria.AGUARDANDO_ACOES:          "🔴",
    StatusOuvidoria.AGUARDANDO_PERMISSIONARIA: "🟡",
    StatusOuvidoria.EM_ANALISE_TECNICA:        "🟣",
    StatusOuvidoria.RETORNO_TECNICO:           "🟢",
    StatusOuvidoria.CONCLUIDO:                 "⚫",
}


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
ouvidorias = listar_ouvidorias(
    filtro_status=filtro_s,
    filtro_periodo=periodo,
    ocultar_concluidos=ocultar_concluidos if sel_status == "Todos" else False,
    usuario=u,
)

st.divider()

if not ouvidorias:
    st.info("Nenhuma ouvidoria encontrada com os filtros aplicados.")
else:
    # Cabeçalho — Prazo Perm. antes de Prazo Resp., ambos com círculo+tooltip
    if u.tipo == TipoUsuario.gestor:
        col_sizes = [0.6, 2.3, 2.5, 2.5, 2.5, 1.4, 1.4, 0.6, 0.7, 0.8, 0.6]
        headers = ["**#**", "**Protocolo**", "**Status**", "**Coord./Gerência**",
                    "**Responsáveis**", "**Prazo Perm.**", "**Prazo Resp.**",
                    "", "", "", ""]
    else:
        col_sizes = [0.6, 2.3, 2.5, 2.5, 2.5, 1.5, 1.5, 0.5, 0.8]
        headers = ["**#**", "**Protocolo**", "**Status**", "**Coord./Gerência**",
                    "**Responsáveis**", "**Prazo Perm.**", "**Prazo Resp.**",
                    "", ""]

    cols_header = st.columns(col_sizes)
    for idx, h in enumerate(headers):
        if h:
            cols_header[idx].markdown(h)
    st.divider()

    # Pré-carregar técnicos para o popover de atribuição
    if u.tipo == TipoUsuario.gestor:
        todos_tecs = carregar_tecnicos_disponiveis()

    for o in ouvidorias:
        emoji_status = STATUS_EMOJI.get(o["status"], "")
        status_label = f"{emoji_status} {o['status']}"

        # Prazo Permissionária (círculo + dias, tooltip com data)
        perm_label, perm_tip = prazo_circle_label(o["prazo_permissionaria"])
        # Prazo de Resposta (círculo + dias, tooltip com data)
        resp_label, resp_tip = prazo_circle_label(o["prazo"])

        confirmar_key = f"confirmar_excluir_{o['id']}"

        cols = st.columns(col_sizes)

        cols[0].write(o["id"])
        cols[1].write(o["protocolo"])
        cols[2].write(status_label)
        cols[3].write(o["coord_ger"])
        cols[4].write(o["responsaveis"])
        
        # Prazo Perm. — botão desabilitado com tooltip
        if perm_tip:
            cols[5].button(perm_label, key=f"pperm_{o['id']}", disabled=True, help=perm_tip)
        else:
            cols[5].write(perm_label)

        # Prazo Resp. — botão desabilitado com tooltip
        cols[6].button(resp_label, key=f"presp_{o['id']}", disabled=True, help=resp_tip)

        # Botão Abrir (lupa)
        if cols[7].button("🔍", key=f"abrir_{o['id']}", help="Abrir detalhe"):
            st.session_state["ouvidoria_id"] = o["id"]
            st.switch_page("pages/03_Detalhe_Ouvidoria.py")

        # Botão Responder (popover com 2 opções)
        if u.tipo == TipoUsuario.gestor:
            with cols[8]:
                with st.popover("✍️"):
                    if st.button("Resposta Técnico", key=f"resp_tec_{o['id']}"):
                        st.session_state["ouvidoria_id"] = o["id"]
                        st.session_state.pop("resp_recs_edit", None)
                        st.session_state.pop("resp_autos_checklist", None)
                        st.session_state.pop("resp_rec_alvo_anterior", None)
                        st.switch_page("pages/05_Responder.py")
                    if st.button("Resposta Permissionária", key=f"resp_perm_{o['id']}"):
                        st.session_state["ouvidoria_id"] = o["id"]
                        st.switch_page("pages/04_Resposta_Permissionaria.py")

            # Botão atribuir técnico (pessoa)
            with cols[9]:
                with st.popover("👤"):
                    if todos_tecs:
                        tec_nomes = [n for _, n in todos_tecs]
                        tec_sel = st.selectbox("Técnico", tec_nomes, key=f"atr_tec_{o['id']}")
                        tec_id = dict([(n, tid) for tid, n in todos_tecs]).get(tec_sel)
                        if st.button("Atribuir", key=f"atr_btn_{o['id']}"):
                            ok = atribuir_tecnico(o["id"], tec_id)
                            if ok:
                                st.toast(f"Técnico {tec_sel} atribuído!", icon="✅")
                                st.rerun()
                            else:
                                st.warning("Técnico já atribuído.")
                    else:
                        st.write("Nenhum técnico disponível.")

            # Botão engrenagem (concluir/excluir)
            with cols[10]:
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
        else:
            # Técnico: botão responder direto
            if cols[8].button("✍️", key=f"resp_{o['id']}", help="Responder"):
                st.session_state["ouvidoria_id"] = o["id"]
                st.session_state.pop("resp_recs_edit", None)
                st.session_state.pop("resp_autos_checklist", None)
                st.session_state.pop("resp_rec_alvo_anterior", None)
                st.switch_page("pages/05_Responder.py")
