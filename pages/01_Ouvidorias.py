"""Lista de Ouvidorias – visão geral com filtros."""

import os
import sys
from datetime import date

import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import auth
from auth import usuario_logado
from api.client.enums import (
    STATUS_OUVIDORIA, TIPO_SERVICO,
    STATUS_CONCLUIDO, STATUS_RETORNO_TECNICO,
    STATUS_EM_ANALISE_TECNICA, STATUS_AGUARDANDO_ACOES,
    STATUS_AGUARDANDO_PERMISSIONARIA,
    TIPO_USUARIO_GESTOR,
)
from api.client.catalogo_client import carregar_categorias, carregar_subcategorias, carregar_tecnicos_disponiveis
from api.client.ouvidoria_client import (
    listar_ouvidorias, atribuir_tecnico, editar_ouvidoria,
    concluir_ouvidoria, excluir_ouvidoria,
)
from api.client.base import API_PUBLIC_URL


from utils import prazo_circle_label
from components import reduz_margem_side_bar, reduz_margem_topo_page, reduz_gap_elementos_body

st.set_page_config(page_title="Ouvidorias", page_icon="📋", layout="wide")

reduz_margem_topo_page()
reduz_gap_elementos_body()
auth.require_auth()

st.session_state.setdefault("ov_cache_buster", 0)
u = usuario_logado()

STATUS_EMOJI = {
    STATUS_AGUARDANDO_ACOES:          "🔴",
    STATUS_AGUARDANDO_PERMISSIONARIA: "🟡",
    STATUS_EM_ANALISE_TECNICA:        "🟣",
    STATUS_RETORNO_TECNICO:           "🟢",
    STATUS_CONCLUIDO:                 "⚫",
}


def _coord_ger(atribuicoes: list) -> str:
    partes = set()
    for a in atribuicoes:
        c = a.get("coordenacao_nome") or ""
        g = a.get("gerencia_nome") or ""
        if c:
            partes.add(c)
        elif g:
            partes.add(g)
    return ", ".join(sorted(partes)) or "–"


def _responsaveis(atribuicoes: list) -> str:
    return ", ".join(a["tecnico_nome"] for a in atribuicoes if a.get("tecnico_nome")) or "–"


# ── Sidebar ──────────────────────────────────────────────────────────────────
reduz_margem_side_bar()
with st.sidebar:
    st.markdown(f"**{u['nome']}**")
    st.caption(f"Perfil: {'Gestor' if u.get('tipo') == TIPO_USUARIO_GESTOR else 'Técnico'}")
    st.divider()
    if st.button("Sair", use_container_width=True):
        auth.fazer_logout()
        st.rerun()

# ── Filtros ──────────────────────────────────────────────────────────────────
_col_tit, _col_tipo = st.columns([2, 2])
with _col_tit:
    st.title("📋 Ouvidorias")
with _col_tipo:
    st.write("")
    _opcoes_tipo = [("", "Todos os Tipos")] + [(ts, ts) for ts in TIPO_SERVICO]
    _sel_tipo = st.selectbox("Tipo de Serviço", _opcoes_tipo, format_func=lambda x: x[1], label_visibility="collapsed")
    _filtro_tipo = _sel_tipo[0] if _sel_tipo[0] else None

col_cat, col_sub, col_checks, col_de, col_ate, col_nova = st.columns([1.8, 1.8, 1.1, 1.3, 1.3, 1.6])

_cats = carregar_categorias()
_opcoes_cat = [(0, "Todas Categorias")] + _cats

with col_cat:
    sel_categoria = st.selectbox("Categoria", _opcoes_cat, format_func=lambda x: x[1])
_cat_id_sel = sel_categoria[0] if sel_categoria[0] else None
_subs = carregar_subcategorias(_cat_id_sel) if _cat_id_sel else []

with col_sub:
    sel_subcategoria = st.selectbox("Subcategoria", [(0, "Todas Subcategorias")] + _subs, format_func=lambda x: x[1])
_filtrar_apenas_atribuidas = True
with col_checks:
    ocultar_concluidos = st.checkbox("Ocultar Concluídas", value=True)
    if u.get("tipo") != TIPO_USUARIO_GESTOR:
        _filtrar_apenas_atribuidas = st.checkbox("Apenas atribuídas", value=True)
    usar_periodo = st.checkbox("Filtrar por período")

data_ini = data_fim = None
with col_de:
    if usar_periodo:
        data_ini = st.date_input("De", value=date.today().replace(day=1))
with col_ate:
    if usar_periodo:
        data_fim = st.date_input("Até", value=date.today())
with col_nova:
    st.write("")
    if u.get("tipo") == TIPO_USUARIO_GESTOR:
        if st.button("+ Nova Ouvidoria", use_container_width=True, type="primary"):
            st.switch_page("pages/02_Nova_Ouvidoria.py")

periodo = (data_ini, data_fim) if usar_periodo and data_ini and data_fim else None
_filtro_cat_id = sel_categoria[0] if sel_categoria[0] else None
_filtro_sub_id = sel_subcategoria[0] if sel_subcategoria[0] else None

ouvidorias = listar_ouvidorias(
    filtro_periodo=periodo,
    ocultar_concluidos=ocultar_concluidos,
    usuario_id=u["usuario_id"],
    usuario_tipo=u.get("tipo"),
    filtro_categoria_id=_filtro_cat_id,
    filtro_subcategoria_id=_filtro_sub_id,
    filtro_tipo_servico=_filtro_tipo,
    filtrar_apenas_atribuidas=_filtrar_apenas_atribuidas,
    cache_buster=st.session_state["ov_cache_buster"],
)

st.divider()

# ── Paginação ─────────────────────────────────────────────────────────────────
st.session_state.setdefault("pag_atual", 1)
st.session_state.setdefault("por_pagina", 15)
st.session_state.setdefault("filtros_hash_anterior", None)

filtros_hash = hash((_filtro_cat_id, _filtro_sub_id, _filtro_tipo, ocultar_concluidos,
                     usar_periodo, data_ini if usar_periodo else None, data_fim if usar_periodo else None))
if st.session_state.filtros_hash_anterior != filtros_hash:
    st.session_state.pag_atual = 1
    st.session_state.filtros_hash_anterior = filtros_hash

ouvidorias_pagina = ouvidorias
if ouvidorias:
    opcoes_por_pag = [15, 25, 50, 100]
    num_paginas = max(1, (len(ouvidorias) + st.session_state.por_pagina - 1) // st.session_state.por_pagina)
    if st.session_state.pag_atual > num_paginas:
        st.session_state.pag_atual = num_paginas
    opcoes_pagina = [f"Página {i}/{num_paginas}" for i in range(1, num_paginas + 1)]

    col_pag1, col_pag2, col_pag3, col_pag4, col_pag5 = st.columns([0.8, 0.8, 1.5, 0.8, 1.2])
    with col_pag1:
        if st.button("⏮ Início", use_container_width=True):
            st.session_state.pag_atual = 1; st.rerun()
    with col_pag2:
        if st.button("◀ Anterior", use_container_width=True):
            if st.session_state.pag_atual > 1:
                st.session_state.pag_atual -= 1; st.rerun()
    with col_pag3:
        pag_sel_str = st.selectbox("Página", opcoes_pagina, index=st.session_state.pag_atual - 1, label_visibility="collapsed")
        pag_num = int(pag_sel_str.split()[1].split("/")[0])
        if pag_num != st.session_state.pag_atual:
            st.session_state.pag_atual = pag_num; st.rerun()
    with col_pag4:
        if st.button("Próxima ▶", use_container_width=True):
            if st.session_state.pag_atual < num_paginas:
                st.session_state.pag_atual += 1; st.rerun()
    with col_pag5:
        idx_por_pag = opcoes_por_pag.index(st.session_state.por_pagina) if st.session_state.por_pagina in opcoes_por_pag else 1
        por_pag_sel = st.selectbox("Por página", opcoes_por_pag, index=idx_por_pag, label_visibility="collapsed")
        if por_pag_sel != st.session_state.por_pagina:
            st.session_state.por_pagina = por_pag_sel; st.session_state.pag_atual = 1; st.rerun()

    inicio = (st.session_state.pag_atual - 1) * st.session_state.por_pagina
    ouvidorias_pagina = ouvidorias[inicio:inicio + st.session_state.por_pagina]
    st.caption(f"Total: {len(ouvidorias)} ouvidorias")

if not ouvidorias:
    st.info("Nenhuma ouvidoria encontrada com os filtros aplicados.")
else:
    col_sizes = [1.1, 1.6, 2.5, 1, 2.5, 2.5, 1.4, 1.4, 0.7, 0.7]
    headers = ["**#**", "**Entrada**", "**Protocolo**", "**Status**",
               "**Coord./Gerência**", "**Responsáveis**", "**Prazo Perm.**", "**Prazo Resp.**", "", ""]
    cols_h = st.columns(col_sizes)
    for idx, h in enumerate(headers):
        if h:
            cols_h[idx].markdown(h)
    st.divider()

    if u.get("tipo") == TIPO_USUARIO_GESTOR:
        todos_tecs = carregar_tecnicos_disponiveis()

    for o in ouvidorias_pagina:
        status_str = o["status"]
        emoji_status = STATUS_EMOJI.get(status_str, "")
        status_label = f"{emoji_status} {status_str}"
        perm_label, perm_tip = prazo_circle_label(o.get("prazo_permissionaria"), o.get("data_resposta_perm"))
        resp_label, resp_tip = prazo_circle_label(o.get("prazo"), o.get("concluido_em"))
        entrada = (o["criado_em"] or "")[:10] or "–"
        confirmar_key = f"confirmar_excluir_{o['id']}"
        pode_concluir = status_str == STATUS_RETORNO_TECNICO

        cols = st.columns(col_sizes)
        cols[0].write(o["id"])
        cols[1].write(entrada)
        cols[2].write(o["protocolo"])

        with cols[3].popover(emoji_status, use_container_width=True, help=status_label):
            if u.get("tipo") == TIPO_USUARIO_GESTOR:
                st.write("**Alterar Status**")
                novo_status_str = st.selectbox("Novo status:", options=STATUS_OUVIDORIA,
                    index=STATUS_OUVIDORIA.index(status_str) if status_str in STATUS_OUVIDORIA else 0,
                    key=f"status_{o['id']}")
                if st.button("Atribuir", type="primary", key=f"status_buttom{o['id']}"):
                    editar_ouvidoria(o["id"], status=novo_status_str)
                    st.session_state["ov_cache_buster"] += 1; st.rerun()
            else:
                st.write(status_label)

        cols[4].write(_coord_ger(o["atribuicoes"]))
        cols[5].write(_responsaveis(o["atribuicoes"]))
        if perm_tip:
            cols[6].button(perm_label, key=f"pperm_{o['id']}", disabled=True, help=perm_tip)
        else:
            cols[6].write(perm_label)
        cols[7].button(resp_label, key=f"presp_{o['id']}", disabled=True, help=resp_tip)

        if u.get("tipo") == TIPO_USUARIO_GESTOR:
            with cols[8]:
                with st.popover("👤"):
                    if todos_tecs:
                        tec_nomes = [n for _, n in todos_tecs]
                        tec_sel = st.selectbox("Técnico", tec_nomes, key=f"atr_tec_{o['id']}")
                        tec_id = {n: tid for tid, n in todos_tecs}.get(tec_sel)
                        if st.button("Atribuir", key=f"atr_btn_{o['id']}"):
                            if atribuir_tecnico(o["id"], tec_id):
                                st.toast(f"Técnico {tec_sel} atribuído!", icon="✅")
                                st.session_state["ov_cache_buster"] += 1; st.rerun()
                            else:
                                st.warning("Técnico já atribuído.")
                    else:
                        st.write("Nenhum técnico disponível.")

        with cols[9]:
            with st.popover("🛠️"):
                if st.button("📋 Resumo da Ouvidoria", key=f"resumo_{o['id']}"):
                    components.html(
                        f'<script>window.open("{API_PUBLIC_URL}/ouvidorias/{o["id"]}/resumo-html","_blank");</script>',
                        height=0,
                    )
                st.divider()
                if st.button("🔍 Abrir detalhe", key=f"abrir_{o['id']}"):
                    st.session_state["ouvidoria_id"] = o["id"]
                    st.switch_page("pages/03_Detalhe_Ouvidoria.py")
                if u.get("tipo") == TIPO_USUARIO_GESTOR:
                    if st.button("✍️ Resposta Técnico", key=f"resp_tec_{o['id']}"):
                        st.session_state["ouvidoria_id"] = o["id"]
                        for k in ("resp_recs_edit", "resp_autos_checklist", "resp_rec_alvo_anterior"):
                            st.session_state.pop(k, None)
                        st.switch_page("pages/05_Responder.py")
                    if st.button("📤 Resposta Permissionária", key=f"resp_perm_{o['id']}"):
                        st.session_state["ouvidoria_id"] = o["id"]
                        st.switch_page("pages/04_Resposta_Permissionaria.py")
                    st.divider()
                    if pode_concluir:
                        if st.button("✅ Concluir", key=f"concluir_{o['id']}"):
                            concluir_ouvidoria(o["id"])
                            st.toast("Ouvidoria concluída!", icon="✅")
                            st.session_state["ov_cache_buster"] += 1; st.rerun()
                    if not st.session_state.get(confirmar_key):
                        if st.button("🗑 Excluir", key=f"excluir_{o['id']}"):
                            st.session_state[confirmar_key] = True; st.rerun()
                    else:
                        st.warning("Confirmar exclusão?")
                        if st.button("Sim", key=f"sim_excluir_{o['id']}"):
                            excluir_ouvidoria(o["id"])
                            st.session_state.pop(confirmar_key, None)
                            st.toast("Ouvidoria excluída.", icon="🗑")
                            st.session_state["ov_cache_buster"] += 1; st.rerun()
                        if st.button("Não", key=f"nao_excluir_{o['id']}"):
                            st.session_state.pop(confirmar_key, None); st.rerun()
                else:
                    if st.button("✍️ Resposta Técnico", key=f"resp_{o['id']}"):
                        st.session_state["ouvidoria_id"] = o["id"]
                        for k in ("resp_recs_edit", "resp_autos_checklist", "resp_rec_alvo_anterior"):
                            st.session_state.pop(k, None)
                        st.switch_page("pages/05_Responder.py")
                    if st.button("📤 Resposta Permissionária", key=f"resp_perm_tec_{o['id']}"):
                        st.session_state["ouvidoria_id"] = o["id"]
                        st.switch_page("pages/04_Resposta_Permissionaria.py")
