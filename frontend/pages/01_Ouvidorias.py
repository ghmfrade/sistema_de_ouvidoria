"""Lista de Ouvidorias – visão geral com filtros."""

import html
import os
import sys
from datetime import date

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import auth
from auth import usuario_logado
from api.client.enums import (
    STATUS_OUVIDORIA, TIPO_SERVICO,
    STATUS_CONCLUIDO, STATUS_RETORNO_TECNICO,
    STATUS_EM_ANALISE_TECNICA, STATUS_AGUARDANDO_ACOES,
    STATUS_AGUARDANDO_PERMISSIONARIA,
    TIPO_USUARIO_GESTOR, CORES_MARCACAO, EMOJI_COR,
)
from api.client.catalogo_client import carregar_categorias, carregar_subcategorias, carregar_tecnicos_disponiveis
from api.client.ouvidoria_client import (
    listar_ouvidorias, atribuir_tecnico, editar_ouvidoria,
    concluir_ouvidoria, excluir_ouvidoria,
    remover_tecnico, devolver_ao_tecnico,
)
from api.client.marcacao_client import (
    definir_marcacao, remover_marcacao, carregar_legenda, salvar_legenda,
)
from api.client.autos_client import carregar_permissionarias, carregar_todos_autos
from api.client.base import API_PUBLIC_URL

from utils import prazo_circle_label, fmt_data
from utils.formatters import fmt_auto
from components import reduz_margem_side_bar, reduz_margem_topo_page, reduz_gap_elementos_body

st.set_page_config(page_title="Ouvidorias", page_icon="📋", layout="wide")

reduz_margem_topo_page()
reduz_gap_elementos_body()
auth.require_auth()

# Painel dos popovers mais largo (nome do técnico + botão na mesma linha).
# st.popover(width=) só controla o botão, não o painel; o CSS vale para todos os popovers da página.
st.markdown(
    "<style>[data-testid='stPopoverBody']{min-width:min(420px,90vw);}</style>",
    unsafe_allow_html=True,
)

st.session_state.setdefault("ov_cache_buster", 0)
u = usuario_logado()

ABREV_TIPO_REGULAR = {"Regular – Metropolitano": "Metro", "Regular – Intermunicipal": "Inter"}
TIPOS_REGULARES = list(ABREV_TIPO_REGULAR)

STATUS_EMOJI = {
    STATUS_AGUARDANDO_ACOES:          "🔴",
    STATUS_AGUARDANDO_PERMISSIONARIA: "🟡",
    STATUS_EM_ANALISE_TECNICA:        "🟣",
    STATUS_RETORNO_TECNICO:           "🟢",
    STATUS_CONCLUIDO:                 "⚫",
}


def _assuntos_html(assuntos: list) -> str:
    """Um assunto por linha; o que não couber na largura termina com reticências."""
    if not assuntos:
        return "–"
    estilo = "white-space:nowrap; overflow:hidden; text-overflow:ellipsis;"
    return "".join(
        f'<div style="{estilo}" title="{html.escape(a, quote=True)}">{html.escape(a)}</div>'
        for a in assuntos
    )


def _responsaveis(atribuicoes: list) -> str:
    return ", ".join(
        a["tecnico_nome"] for a in atribuicoes
        if a.get("tecnico_nome") and not a.get("respondido")
    ) or "–"


_legenda = {i["cor"]: i["rotulo"] for i in carregar_legenda(cache_buster=st.session_state["ov_cache_buster"])}
_cores_nomeadas = [c for c in CORES_MARCACAO if (_legenda.get(c) or "").strip()]


def _rotulo_cor(cor: str) -> str:
    """'🔴 Ana' quando a cor tem nome na legenda; '🔴 vermelho' quando não."""
    return f"{EMOJI_COR[cor]} {_legenda.get(cor) or cor}"


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
_col_tit, _col_cor, _col_leg, _col_tipo = st.columns([1.6, 1.2, 0.6, 1.6])
with _col_tit:
    st.title("📋 Ouvidorias")
with _col_leg:
    st.write("")
    with st.popover("🎨 Legenda"):
        st.caption("Dê um nome a cada cor. Vale para todos que usam este login.")
        for cor in CORES_MARCACAO:
            st.text_input(EMOJI_COR[cor], value=_legenda.get(cor, ""), max_chars=40, key=f"leg_{cor}")
        if st.button("💾 Salvar", key="leg_salvar"):
            try:
                salvar_legenda([
                    {"cor": cor, "rotulo": st.session_state.get(f"leg_{cor}", "").strip()}
                    for cor in CORES_MARCACAO
                ])
                st.session_state["ov_cache_buster"] += 1; st.rerun()
            except Exception as e:
                st.error(f"Erro ao salvar legenda: {e}")
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
        data_ini = st.date_input("De", value=date.today().replace(day=1), format="DD/MM/YYYY")
with col_ate:
    if usar_periodo:
        data_fim = st.date_input("Até", value=date.today(), format="DD/MM/YYYY")
with col_nova:
    st.write("")
    if u.get("tipo") == TIPO_USUARIO_GESTOR:
        if st.button("+ Nova Ouvidoria", use_container_width=True, type="primary"):
            st.switch_page("pages/02_Nova_Ouvidoria.py")

_filtro_cat_id = sel_categoria[0] if sel_categoria[0] else None
_filtro_sub_id = sel_subcategoria[0] if sel_subcategoria[0] else None

# Empresa / Auto de linha: só para tipos regulares; dependem do Tipo de Serviço (e o Auto, da Empresa).
_filtro_perm_id = _filtro_auto_id = None
if _filtro_tipo is None or _filtro_tipo in TIPOS_REGULARES:
    _tipos_opcoes = [_filtro_tipo] if _filtro_tipo else TIPOS_REGULARES
    _opcoes_empresa = [(0, "Todas as empresas")]
    _perms_por_id: dict = {}
    for _t in _tipos_opcoes:
        for _p in carregar_permissionarias(_t):
            _perms_por_id.setdefault(_p["id"], _p.get("nome_fantasia") or _p["nome"])
    _opcoes_empresa += sorted(_perms_por_id.items(), key=lambda par: par[1].casefold())

    _col_emp, _col_auto, _ = st.columns([1.8, 1.8, 6.3])
    if st.session_state.get("filtro_empresa") not in _opcoes_empresa:
        st.session_state["filtro_empresa"] = _opcoes_empresa[0]
    with _col_emp:
        _sel_empresa = st.selectbox("Empresa", _opcoes_empresa, format_func=lambda x: x[1], key="filtro_empresa")
    _filtro_perm_id = _sel_empresa[0] or None

    _opcoes_auto = [(0, "Todos os autos")]
    for _t in _tipos_opcoes:
        _prefixo = f"[{ABREV_TIPO_REGULAR[_t]}] " if _filtro_tipo is None else ""
        for _a in carregar_todos_autos(_t, perm_id=_filtro_perm_id):
            _opcoes_auto.append((_a["id"], _prefixo + fmt_auto(_a)))
    if st.session_state.get("filtro_auto") not in _opcoes_auto:
        st.session_state["filtro_auto"] = _opcoes_auto[0]
    with _col_auto:
        _sel_auto = st.selectbox("Auto de linha", _opcoes_auto, format_func=lambda x: x[1], key="filtro_auto")
    _filtro_auto_id = _sel_auto[0] or None

ouvidorias = listar_ouvidorias(
    filtro_de=data_ini if usar_periodo else None,
    filtro_ate=data_fim if usar_periodo else None,
    ocultar_concluidos=ocultar_concluidos,
    usuario_id=u["usuario_id"],
    usuario_tipo=u.get("tipo"),
    filtro_categoria_id=_filtro_cat_id,
    filtro_subcategoria_id=_filtro_sub_id,
    filtro_tipo_servico=_filtro_tipo,
    filtro_permissionaria_id=_filtro_perm_id,
    filtro_auto_id=_filtro_auto_id,
    filtrar_apenas_atribuidas=_filtrar_apenas_atribuidas,
    cache_buster=st.session_state["ov_cache_buster"],
)

# Filtro Cor (desenhado aqui para usar as cores em uso na lista; fica na coluna _col_cor, no topo)
_cores_em_uso = {o.get("marcacao") for o in ouvidorias if o.get("marcacao")}
_opcoes_cor = (
    [("", "Todas as cores")]
    + [(c, _rotulo_cor(c)) for c in CORES_MARCACAO if c in _cores_nomeadas or c in _cores_em_uso]
    + [("sem", "- Sem cor")]
)
with _col_cor:
    st.write("")
    _sel_cor = st.selectbox("Cor", _opcoes_cor, format_func=lambda x: x[1], label_visibility="collapsed")
    _filtro_cor = _sel_cor[0]

if _filtro_cor == "sem":
    ouvidorias = [o for o in ouvidorias if o.get("marcacao") is None]
elif _filtro_cor:
    ouvidorias = [o for o in ouvidorias if o.get("marcacao") == _filtro_cor]

st.divider()

# ── Paginação ─────────────────────────────────────────────────────────────────
st.session_state.setdefault("pag_atual", 1)
st.session_state.setdefault("por_pagina", 15)
st.session_state.setdefault("filtros_hash_anterior", None)

filtros_hash = hash((_filtro_cat_id, _filtro_sub_id, _filtro_tipo, _filtro_cor,
                     _filtro_perm_id, _filtro_auto_id, ocultar_concluidos,
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
    col_sizes = [0.6, 1.1, 1.6, 2.5, 1, 3.0, 1.8, 1.0, 1.4, 0.7, 0.7]
    headers = ["**Cor**", "**#**", "**Entrada**", "**Protocolo**", "**Status**",
               "**Assuntos**", "**Responsáveis**", "**Prazo Perm.**", "**Prazo Resp.**", "", ""]
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
        entrada = fmt_data(o["criado_em"])
        confirmar_key = f"confirmar_excluir_{o['id']}"
        pode_concluir = status_str == STATUS_RETORNO_TECNICO

        cols = st.columns(col_sizes)
        cor_atual = o.get("marcacao")
        with cols[0].popover(
            EMOJI_COR[cor_atual] if cor_atual else "-", use_container_width=True,
            help=_rotulo_cor(cor_atual) if cor_atual else "Sem cor",
        ):
            _cores_oferta = [c for c in CORES_MARCACAO if c in _cores_nomeadas or c == cor_atual]
            if not _cores_oferta:
                st.caption("Dê nome às cores em 🎨 Legenda para usá-las.")
            for cor in _cores_oferta:
                if st.button(_rotulo_cor(cor), key=f"cor_{o['id']}_{cor}",
                             type="primary" if cor == cor_atual else "secondary"):
                    try:
                        definir_marcacao(o["id"], cor)
                        st.session_state["ov_cache_buster"] += 1; st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao marcar: {e}")
            if st.button("✖ Sem cor", key=f"cor_{o['id']}_nenhuma", disabled=not cor_atual):
                try:
                    remover_marcacao(o["id"])
                    st.session_state["ov_cache_buster"] += 1; st.rerun()
                except Exception as e:
                    st.error(f"Erro ao remover cor: {e}")

        cols[1].write(o["id"])
        cols[2].write(entrada)
        cols[3].write(o["protocolo"])

        with cols[4].popover(emoji_status, use_container_width=True, help=status_label):
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

        cols[5].markdown(_assuntos_html(o.get("assuntos") or []), unsafe_allow_html=True)
        cols[6].write(_responsaveis(o["atribuicoes"]))
        if perm_tip:
            cols[7].button(perm_label, key=f"pperm_{o['id']}", disabled=True, help=perm_tip)
        else:
            cols[7].write(perm_label)
        cols[8].button(resp_label, key=f"presp_{o['id']}", disabled=True, help=resp_tip)

        if u.get("tipo") == TIPO_USUARIO_GESTOR:
            with cols[9]:
                with st.popover("👤"):
                    st.write("**Técnicos responsáveis**")
                    atribuicoes_ordenadas = (
                        [a for a in o["atribuicoes"] if not a.get("respondido")]
                        + [a for a in o["atribuicoes"] if a.get("respondido")]
                    )
                    if not atribuicoes_ordenadas:
                        st.caption("Nenhum técnico atribuído.")
                    for a in atribuicoes_ordenadas:
                        tid = a["tecnico_id"]
                        col_nome, col_acao = st.columns([5, 1])
                        if not a.get("respondido"):
                            col_nome.write(f"⏳ {a['tecnico_nome']}")
                            if col_acao.button("🗑", key=f"rem_tec_{o['id']}_{tid}", help="Remover técnico"):
                                remover_tecnico(o["id"], tid)
                                st.toast("Técnico removido.")
                                st.session_state["ov_cache_buster"] += 1; st.rerun()
                        else:
                            col_nome.write(f"✅ {a['tecnico_nome']}")
                            if status_str != STATUS_CONCLUIDO and col_acao.button(
                                "🔄", key=f"dev_tec_{o['id']}_{tid}", help="Devolver para complementação"
                            ):
                                devolver_ao_tecnico(o["id"], tid)
                                st.toast("Ouvidoria devolvida ao técnico.")
                                st.session_state["ov_cache_buster"] += 1; st.rerun()

                    st.divider()
                    st.write("**Atribuir técnico**")
                    ids_pendentes = {a["tecnico_id"] for a in o["atribuicoes"] if not a.get("respondido")}
                    tecs_disponiveis = [(tid, n) for tid, n in todos_tecs if tid not in ids_pendentes]
                    if tecs_disponiveis:
                        col_sel, col_ok = st.columns([5, 1])
                        tec_nomes = [n for _, n in tecs_disponiveis]
                        tec_sel = col_sel.selectbox(
                            "Técnico", tec_nomes, key=f"atr_tec_{o['id']}", label_visibility="collapsed"
                        )
                        tec_id = {n: tid for tid, n in tecs_disponiveis}.get(tec_sel)
                        if col_ok.button("✔️", key=f"atr_btn_{o['id']}", help="Atribuir técnico"):
                            if atribuir_tecnico(o["id"], tec_id):
                                st.toast(f"Técnico {tec_sel} atribuído!", icon="✅")
                                st.session_state["ov_cache_buster"] += 1; st.rerun()
                            else:
                                st.warning("Técnico já atribuído.")
                    else:
                        st.caption("Nenhum técnico disponível.")

        with cols[10]:
            with st.popover("🛠️"):
                st.link_button(
                    "📋 Resumo da Ouvidoria",
                    url=f"{API_PUBLIC_URL}/ouvidorias/{o['id']}/resumo-html",
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
