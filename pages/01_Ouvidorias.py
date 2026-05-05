"""Lista de Ouvidorias – visão geral com filtros."""

import base64
import os
import sys
from datetime import date

import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import auth
from auth import usuario_logado
from models import StatusOuvidoria, TipoServico, TipoUsuario
from utils import (
    atribuir_tecnico,
    carregar_categorias,
    carregar_subcategorias,
    carregar_tecnicos_disponiveis,
    alterar_status_ouvidoria,
    concluir_ouvidoria,
    excluir_ouvidoria,
    gerar_html_resumo,
    listar_ouvidorias,
    prazo_circle_label,
)

from components import (
    reduz_margem_side_bar, 
    reduz_margem_topo_page, 
    reduz_gap_elementos_body,
)

st.set_page_config(page_title="Ouvidorias", page_icon="📋", layout="wide")

reduz_margem_topo_page()
reduz_gap_elementos_body()


auth.require_auth()

st.session_state.setdefault("ov_cache_buster", 0)

_resumo_id = st.session_state.pop("abrir_resumo_id", None)

u = usuario_logado()

STATUS_EMOJI = {
    StatusOuvidoria.AGUARDANDO_ACOES:          "🔴",
    StatusOuvidoria.AGUARDANDO_PERMISSIONARIA: "🟡",
    StatusOuvidoria.EM_ANALISE_TECNICA:        "🟣",
    StatusOuvidoria.RETORNO_TECNICO:           "🟢",
    StatusOuvidoria.CONCLUIDO:                 "⚫",
}

# ── Sidebar ──────────────────────────────────────────────────────────────────
reduz_margem_side_bar()

with st.sidebar:
    st.markdown(f"**{u.nome}**")
    st.caption(f"Perfil: {'Gestor' if u.tipo.value == 'gestor' else 'Técnico'}")
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
    _opcoes_tipo = [("", "Todos os Tipos")] + [(ts.value, ts.value) for ts in TipoServico]
    _sel_tipo = st.selectbox("Tipo de Serviço", _opcoes_tipo, format_func=lambda x: x[1], label_visibility="collapsed")
    _filtro_tipo = _sel_tipo[0] if _sel_tipo[0] else None

data_ini = None
data_fim = None
periodo = None

col_cat, col_sub, col_checks, col_de, col_ate, col_nova = st.columns([1.8, 1.8, 1.1, 1.3, 1.3, 1.6])

_cats = carregar_categorias()
_opcoes_cat = [(0, "Todas Categorias")] + [(cid, nome) for cid, nome in _cats]

with col_cat:
    sel_categoria = st.selectbox(
        "Categoria", _opcoes_cat,
        format_func=lambda x: x[1],
        label_visibility="visible",
    )

_cat_id_sel = sel_categoria[0] if sel_categoria[0] else None
_subs = carregar_subcategorias(_cat_id_sel)
_opcoes_sub = [(0, "Todas Subcategorias")] + [(sid, nome) for sid, nome in _subs]

with col_sub:
    sel_subcategoria = st.selectbox(
        "Subcategoria", _opcoes_sub,
        format_func=lambda x: x[1],
        label_visibility="visible",
    )

with col_checks:
    ocultar_concluidos = st.checkbox("Ocultar Concluídas", value=True)
    usar_periodo = st.checkbox("Filtrar por período")
with col_de:
    if usar_periodo:
        data_ini = st.date_input("De", value=date.today().replace(day=1))
with col_ate:
    if usar_periodo:
        data_fim = st.date_input("Até", value=date.today())
with col_nova:
    st.write("")
    if u.tipo == TipoUsuario.gestor:
        if st.button("+ Nova Ouvidoria", use_container_width=True, type="primary"):
            st.switch_page("pages/02_Nova_Ouvidoria.py")

if usar_periodo and data_ini and data_fim:
    periodo = (data_ini, data_fim)

_filtro_cat_id = sel_categoria[0] if sel_categoria[0] else None
_filtro_sub_id = sel_subcategoria[0] if sel_subcategoria[0] else None

ouvidorias = listar_ouvidorias(
    filtro_periodo=periodo,
    ocultar_concluidos=ocultar_concluidos,
    usuario_id=u.id,
    usuario_tipo=u.tipo.value,
    filtro_categoria_id=_filtro_cat_id,
    filtro_subcategoria_id=_filtro_sub_id,
    filtro_tipo_servico=_filtro_tipo,
    cache_buster=st.session_state["ov_cache_buster"],
)

st.divider()

# ── Paginação ──────────────────────────────────────────────────────────────────
# Inicializar session_state para paginação
if "pag_atual" not in st.session_state:
    st.session_state.pag_atual = 1
if "por_pagina" not in st.session_state:
    st.session_state.por_pagina = 15
if "filtros_hash_anterior" not in st.session_state:
    st.session_state.filtros_hash_anterior = None

# Detectar mudança nos filtros e resetar para página 1
filtros_hash = hash((_filtro_cat_id, _filtro_sub_id, _filtro_tipo, ocultar_concluidos, usar_periodo, data_ini if usar_periodo else None, data_fim if usar_periodo else None))
if st.session_state.filtros_hash_anterior != filtros_hash:
    st.session_state.pag_atual = 1
    st.session_state.filtros_hash_anterior = filtros_hash

# Controles de paginação
if ouvidorias:
    num_paginas = max(1, (len(ouvidorias) + st.session_state.por_pagina - 1) // st.session_state.por_pagina)
    if st.session_state.pag_atual > num_paginas:
        st.session_state.pag_atual = num_paginas
    opcoes_pagina = [f"Página {i}/{num_paginas}" for i in range(1, num_paginas + 1)]
    opcoes_por_pag = [15, 25, 50, 100]

    col_pag1, col_pag2, col_pag3, col_pag4, col_pag5 = st.columns([0.8, 0.8, 1.5, 0.8, 1.2])

    with col_pag1:
        if st.button("⏮ Início", use_container_width=True):
            st.session_state.pag_atual = 1
            st.rerun()

    with col_pag2:
        if st.button("◀ Anterior", use_container_width=True):
            if st.session_state.pag_atual > 1:
                st.session_state.pag_atual -= 1
                st.rerun()

    with col_pag3:
        # Sem key: index controla o valor a cada rerun — botões apenas mudam pag_atual e rerrodam
        pag_sel_str = st.selectbox("Página", opcoes_pagina,
                                   index=st.session_state.pag_atual - 1,
                                   label_visibility="collapsed")
        pag_num = int(pag_sel_str.split()[1].split("/")[0])
        if pag_num != st.session_state.pag_atual:
            st.session_state.pag_atual = pag_num
            st.rerun()

    with col_pag4:
        if st.button("Próxima ▶", use_container_width=True):
            if st.session_state.pag_atual < num_paginas:
                st.session_state.pag_atual += 1
                st.rerun()

    with col_pag5:
        idx_por_pag = opcoes_por_pag.index(st.session_state.por_pagina) if st.session_state.por_pagina in opcoes_por_pag else 1
        por_pag_sel = st.selectbox("Por página", opcoes_por_pag, index=idx_por_pag, label_visibility="collapsed")
        if por_pag_sel != st.session_state.por_pagina:
            st.session_state.por_pagina = por_pag_sel
            st.session_state.pag_atual = 1
            st.rerun()

    # Slice da lista para a página atual
    inicio = (st.session_state.pag_atual - 1) * st.session_state.por_pagina
    fim = inicio + st.session_state.por_pagina
    ouvidorias_pagina = ouvidorias[inicio:fim]

    st.caption(f"Total: {len(ouvidorias)} ouvidorias")

if not ouvidorias:
    st.info("Nenhuma ouvidoria encontrada com os filtros aplicados.")
else:
    # # | Entrada | Protocolo | Status | Coord./Gerência | Responsáveis | Prazo Perm. | Prazo Resp. | 👤 | 🛠️
    # col 8 (👤) fica vazia para técnico
    col_sizes = [1.1, 1.6, 2.5, 1, 2.5, 2.5, 1.4, 1.4, 0.7, 0.7]
    headers = ["**#**", "**Entrada**", "**Protocolo**", "**Status**",
               "**Coord./Gerência**", "**Responsáveis**", "**Prazo Perm.**", "**Prazo Resp.**", "", ""]

    cols_header = st.columns(col_sizes)
    for idx, h in enumerate(headers):
        if h:
            cols_header[idx].markdown(h)
    st.divider()

    if u.tipo == TipoUsuario.gestor:
        todos_tecs = carregar_tecnicos_disponiveis()

    for o in ouvidorias_pagina:
        emoji_status = STATUS_EMOJI.get(o["status"], "")
        status_label = f"{emoji_status} {o['status']}"
        status_opcoes = [s.value for s in StatusOuvidoria]

        perm_label, perm_tip = prazo_circle_label(o["prazo_permissionaria"], o.get("data_resposta_perm"))
        resp_label, resp_tip = prazo_circle_label(o["prazo"], o.get("concluido_em"))

        entrada = o["criado_em"].strftime("%d/%m/%Y") if o["criado_em"] else "–"
        confirmar_key = f"confirmar_excluir_{o['id']}"
        pode_concluir = o["status"] == StatusOuvidoria.RETORNO_TECNICO

        cols = st.columns(col_sizes)
        cols[0].write(o["id"])
        cols[1].write(entrada)
        cols[2].write(o["protocolo"])

        with cols[3].popover(emoji_status,
                             use_container_width=True,
                             help=status_label):
            if u.tipo == TipoUsuario.gestor:
                st.write("**Alterar Status**")
                novo_status_str = st.selectbox(
                    "Novo status:",
                    options=status_opcoes,
                    index=status_opcoes.index(o['status']),
                    key=f"status_{o['id']}"
                )
                if st.button("Atribuir", type="primary", key=f"status_buttom{o['id']}"):
                    alterar_status_ouvidoria(o['id'], novo_status_str)
                    st.session_state["ov_cache_buster"] += 1
                    st.rerun()
            else:
                st.write(status_label)
            
        cols[4].write(o["coord_ger"])
        cols[5].write(o["responsaveis"])

        if perm_tip:
            cols[6].button(perm_label, key=f"pperm_{o['id']}", disabled=True, help=perm_tip)
        else:
            cols[6].write(perm_label)

        cols[7].button(resp_label, key=f"presp_{o['id']}", disabled=True, help=resp_tip)

        # Botão 👤 (apenas gestor)
        if u.tipo == TipoUsuario.gestor:
            with cols[8]:
                with st.popover("👤"):
                    if todos_tecs:
                        tec_nomes = [n for _, n in todos_tecs]
                        tec_sel = st.selectbox("Técnico", tec_nomes, key=f"atr_tec_{o['id']}")
                        tec_id = dict([(n, tid) for tid, n in todos_tecs]).get(tec_sel)
                        if st.button("Atribuir", key=f"atr_btn_{o['id']}"):
                            ok = atribuir_tecnico(o["id"], tec_id)
                            if ok:
                                st.toast(f"Técnico {tec_sel} atribuído!", icon="✅")
                                st.session_state["ov_cache_buster"] += 1
                                st.rerun()
                            else:
                                st.warning("Técnico já atribuído.")
                    else:
                        st.write("Nenhum técnico disponível.")

        # Botão 🛠️ unificado
        with cols[9]:
            with st.popover("🛠️"):
                if st.button("📋 Resumo da Ouvidoria", key=f"resumo_{o['id']}"):
                    st.session_state["abrir_resumo_id"] = o["id"]
                    st.rerun()
                st.divider()
                if st.button("🔍 Abrir detalhe", key=f"abrir_{o['id']}"):
                    st.session_state["ouvidoria_id"] = o["id"]
                    st.switch_page("pages/03_Detalhe_Ouvidoria.py")

                if u.tipo == TipoUsuario.gestor:
                    if st.button("✍️ Resposta Técnico", key=f"resp_tec_{o['id']}"):
                        st.session_state["ouvidoria_id"] = o["id"]
                        st.session_state.pop("resp_recs_edit", None)
                        st.session_state.pop("resp_autos_checklist", None)
                        st.session_state.pop("resp_rec_alvo_anterior", None)
                        st.switch_page("pages/05_Responder.py")

                    if st.button("📤 Resposta Permissionária", key=f"resp_perm_{o['id']}"):
                        st.session_state["ouvidoria_id"] = o["id"]
                        st.switch_page("pages/04_Resposta_Permissionaria.py")

                    st.divider()

                    if pode_concluir:
                        if st.button("✅ Concluir", key=f"concluir_{o['id']}"):
                            concluir_ouvidoria(o["id"])
                            st.toast("Ouvidoria concluída!", icon="✅")
                            st.session_state["ov_cache_buster"] += 1
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
                            st.session_state["ov_cache_buster"] += 1
                            st.rerun()
                        if st.button("Não", key=f"nao_excluir_{o['id']}"):
                            st.session_state.pop(confirmar_key, None)
                            st.rerun()

                else:
                    # Técnico: resposta técnica e permissionária
                    if st.button("✍️ Resposta Técnico", key=f"resp_{o['id']}"):
                        st.session_state["ouvidoria_id"] = o["id"]
                        st.session_state.pop("resp_recs_edit", None)
                        st.session_state.pop("resp_autos_checklist", None)
                        st.session_state.pop("resp_rec_alvo_anterior", None)
                        st.switch_page("pages/05_Responder.py")

                    if st.button("📤 Resposta Permissionária", key=f"resp_perm_tec_{o['id']}"):
                        st.session_state["ouvidoria_id"] = o["id"]
                        st.switch_page("pages/04_Resposta_Permissionaria.py")

# ── Download automático do resumo (ao final para não deslocar layout) ─────────
if _resumo_id:
    _b64 = base64.b64encode(gerar_html_resumo(_resumo_id).encode("utf-8")).decode()
    components.html(
        f'<a id="dl" href="data:text/html;base64,{_b64}"'
        f' download="resumo_ouvidoria_{_resumo_id}.html"></a>'
        f'<script>document.getElementById("dl").click();</script>',
        height=0,
    )
