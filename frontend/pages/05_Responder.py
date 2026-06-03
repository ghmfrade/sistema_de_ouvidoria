"""Registrar resposta técnica em uma ouvidoria atribuída."""

import os
import sys
from datetime import date

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import auth
from auth import usuario_logado
from api.client.enums import (
    TIPO_USUARIO_GESTOR, TIPO_USUARIO_TECNICO,
    STATUS_EM_ANALISE_TECNICA, STATUS_CONCLUIDO,
)
from api.client.catalogo_client import carregar_categorias, carregar_subcategorias
from api.client.autos_client import carregar_cidades_atendidas, carregar_cidades_destino
from api.client.catalogo_client import carregar_municipios
from api.client.ouvidoria_client import (
    atualizar_reclamacoes,
    carregar_ouvidoria_para_resposta_tecnica,
    deletar_resposta_permissionaria,
    download_anexo,
    registrar_resposta_permissionaria,
    registrar_resposta_tecnica,
)
from components import reduz_margem_side_bar, reduz_margem_topo_page
from components.reclamacoes import secao_nova_reclamacao, secao_vincular_autos
from utils.formatters import TC_REGIOES

_TIPO_SERVICO_FRET  = ("Fretamento Intermunicipal", "Fretamento Metropolitano")
_TIPO_SERVICO_METRO = "Regular – Metropolitano"
_TIPO_SERVICO_INTER = "Regular – Intermunicipal"
_OPCAO_NAO_INFORMADO = "Não informado"
_TIPO_BASE_MAP = {
    "Fretamento Intermunicipal": _TIPO_SERVICO_INTER,
    "Fretamento Metropolitano": _TIPO_SERVICO_METRO,
}

st.set_page_config(page_title="Registrar Resposta", page_icon="✍️", layout="wide")
st.markdown('<style>[data-testid="stSidebar"]{width:220px!important;min-width:220px!important;}</style>', unsafe_allow_html=True)
auth.require_auth()

u = usuario_logado()
reduz_margem_topo_page()

# ── Sidebar ──────────────────────────────────────────────────────────────────
reduz_margem_side_bar()
with st.sidebar:
    st.markdown(f"**{u['nome']}**")
    st.caption(f"Perfil: {'Gestor' if u.get('tipo') == TIPO_USUARIO_GESTOR else 'Técnico'}")
    st.divider()
    if st.button("← Voltar", use_container_width=True):
        st.switch_page("pages/01_Ouvidorias.py")
    if st.button("Sair", use_container_width=True):
        auth.fazer_logout(); st.rerun()

ouvidoria_id = st.session_state.get("ouvidoria_id")
if not ouvidoria_id:
    st.error("Nenhuma ouvidoria selecionada.")
    st.stop()

view = carregar_ouvidoria_para_resposta_tecnica(ouvidoria_id, u["usuario_id"])
if view is None:
    st.error("Ouvidoria não encontrada.")
    st.stop()

ouvidoria   = view["ouvidoria"]
atribuicao  = view["atribuicao"]
historico   = view["historico"]
resps_perm  = ouvidoria["respostas_permissionaria"]
anexos_data = ouvidoria["anexos"]

if u.get("tipo") == TIPO_USUARIO_TECNICO and atribuicao is None:
    st.error("Esta ouvidoria não está atribuída a você.")
    st.stop()

st.title(f"✍️ Resposta Técnica – Ouvidoria #{ouvidoria['id']}")

# ── Resumo fixo ───────────────────────────────────────────────────────────────
st.caption("Conteúdo da Ouvidoria")
conteudo_preview = ouvidoria["conteudo"] or ""
if len(conteudo_preview) > 300:
    st.info(conteudo_preview[:300] + "…")
    with st.expander("Ver conteúdo completo"):
        st.text(ouvidoria["conteudo"])
else:
    st.info(conteudo_preview)

col_status, col_prazo = st.columns(2)
col_status.write(f"**Status:** {ouvidoria['status']}")
col_prazo.write(f"**Prazo:** {ouvidoria['prazo']}")

_cats_resumo = sorted({
    r["categoria_nome"] for r in ouvidoria["reclamacoes"] if r.get("categoria_nome")
})
if _cats_resumo:
    st.write("**Categorias:** " + " · ".join(f"`{c}`" for c in _cats_resumo))

_subcats_resumo = sorted({
    r["subcategoria_nome"] for r in ouvidoria["reclamacoes"] if r.get("subcategoria_nome")
})
if _subcats_resumo:
    st.write("**Assunto:** " + " · ".join(f"`{s}`" for s in _subcats_resumo))

_autos_vistos: set[int] = set()
_autos_resumo: list[str] = []
for _rec in ouvidoria["reclamacoes"]:
    for _a in _rec.get("autos", []):
        _aid = _a.get("auto_id") or _a.get("id")
        if _aid in _autos_vistos:
            continue
        _autos_vistos.add(_aid)
        _tc = _a.get("tc")
        _tc_str = f" – TC{_tc} {TC_REGIOES[_tc]}" if _tc and _tc in TC_REGIOES else ""
        _den = " → ".join(filter(None, [_a.get("denominacao_a"), _a.get("denominacao_b")])) or _a.get("numero", "")
        _perm = _a.get("permissionaria_nome") or ""
        _autos_resumo.append(f"{_a.get('numero', '')} – {_perm} – {_den}{_tc_str}")
if _autos_resumo:
    with st.expander(f"Autos vinculados ({len(_autos_resumo)})"):
        for _linha in _autos_resumo:
            st.write(f"- {_linha}")

# ── Estado de edição das reclamações ─────────────────────────────────────────
if "resp_recs_edit" not in st.session_state:
    st.session_state["resp_recs_edit"] = [
        {
            "id": r["id"],
            "numero_item": r["numero_item"],
            "categoria_id": r["categoria_id"],
            "categoria_nome": r["categoria_nome"],
            "subcategoria_id": r["subcategoria_id"],
            "subcategoria_nome": r["subcategoria_nome"],
            "tipo_servico": r["tipo_servico"] or _TIPO_SERVICO_INTER,
            "local_embarque": r["local_embarque"],
            "local_desembarque": r["local_desembarque"],
            "descricao": r["descricao"],
            "empresa_fretamento": r["empresa_fretamento"],
            "autos": [
                {
                    "id": a["auto_id"],
                    "numero": a["numero"],
                    "denominacao_a": a.get("denominacao_a"),
                    "denominacao_b": a.get("denominacao_b"),
                    "permissionaria": a["permissionaria_nome"],
                }
                for a in r["autos"]
            ],
        }
        for r in ouvidoria["reclamacoes"]
    ]

st.session_state.setdefault("resp_autos_checklist", [])
st.session_state.setdefault("resp_rec_alvo_anterior", None)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_responder, tab_editar = st.tabs(["✍️ Responder", "✏️ Editar Ouvidoria"])

# ════════════════════════════════════════════════════════════════════════════
# Tab: Responder
# ════════════════════════════════════════════════════════════════════════════
with tab_responder:
    # ── Anexos (somente leitura) ─────────────────────────────────────────────
    if anexos_data:
        with st.expander(f"Anexos ({len(anexos_data)})", expanded=False):
            for an in anexos_data:
                tamanho_kb = round(an["tamanho"] / 1024, 1) if an.get("tamanho") else "?"
                st.download_button(
                    f"📎 {an['nome_arquivo']} ({tamanho_kb} KB)",
                    data=download_anexo(ouvidoria_id, an["id"]),
                    file_name=an["nome_arquivo"],
                    mime=an.get("tipo_mime") or "application/octet-stream",
                    key=f"dl_anexo_{an['id']}",
                )

    # ── Verificar se já respondeu ─────────────────────────────────────────────
    todas_respostas = ouvidoria.get("respostas_tecnicas", [])

    # Sempre exibe respostas anteriores (visível para gestor e técnico)
    if todas_respostas:
        with st.expander(f"Ver respostas anteriores ({len(todas_respostas)})"):
            for rt in todas_respostas:
                st.write(f"**Técnico:** {rt['tecnico_nome']}")
                st.write(f"**Data:** {rt['data_resposta']}")
                st.write(f"**Texto:** {rt['texto_resposta']}")
                st.divider()

    resposta_existente = historico[0] if historico else None
    if resposta_existente and atribuicao and atribuicao.get("respondido"):
        if ouvidoria["status"] != STATUS_EM_ANALISE_TECNICA:
            st.success("Você já registrou sua resposta técnica para esta ouvidoria.")
            st.stop()
        else:
            st.info("O gestor retornou esta ouvidoria para análise técnica. Você pode registrar uma nova resposta.")

    # ── Respostas da Permissionária ──────────────────────────────────────────
    st.subheader("Respostas da Permissionária")
    if resps_perm:
        for rp in resps_perm:
            with st.expander(f"{rp['data_resposta']} — por {rp['registrado_por_nome']}"):
                st.text(rp["conteudo"])
                if st.button("🗑 Excluir esta resposta", key=f"del_rp_{rp['id']}"):
                    deletar_resposta_permissionaria(rp["id"], ouvidoria_id)
                    st.success("Resposta excluída."); st.rerun()
    else:
        st.info("Nenhuma resposta da permissionária registrada.")

    nova_manif = st.checkbox("Nova manifestação da permissionária?", key="nova_manif_check")
    if nova_manif:
        manif_conteudo = st.text_area("Conteúdo da manifestação", height=150, key="manif_conteudo")
        manif_data = st.date_input("Data da manifestação", value=date.today(), key="manif_data", format="DD/MM/YYYY")
        if st.button("📥 Registrar manifestação", key="btn_manif"):
            if not manif_conteudo.strip():
                st.error("O conteúdo da manifestação é obrigatório.")
            else:
                registrar_resposta_permissionaria(ouvidoria_id, manif_conteudo, manif_data, u["usuario_id"])
                st.success("Manifestação registrada."); st.rerun()

    # ── Registrar Resposta Técnica ────────────────────────────────────────────
    st.divider()

    if ouvidoria["status"] == STATUS_CONCLUIDO:
        st.warning("Esta ouvidoria está concluída. Não é possível registrar novas respostas técnicas.")
        st.stop()

    st.subheader("Registrar Resposta")

    with st.form("form_resposta"):
        texto = st.text_area("Texto da resposta técnica *", height=200)
        st.date_input("Data da resposta", value=date.today(), disabled=True, format="DD/MM/YYYY")
        enviar = st.form_submit_button("📤 Enviar Resposta", type="primary")

    if enviar:
        if not texto.strip():
            st.error("O texto da resposta é obrigatório.")
        else:
            try:
                todos_responderam = registrar_resposta_tecnica(ouvidoria_id, u["usuario_id"], texto)
                for k in ("resp_recs_edit", "resp_autos_checklist", "resp_rec_alvo_anterior"):
                    st.session_state.pop(k, None)
                msg = "Resposta registrada com sucesso!"
                if todos_responderam:
                    msg += " Status da ouvidoria atualizado para 'Retorno técnico'."
                st.success(msg)
                st.switch_page("pages/01_Ouvidorias.py")
            except Exception as e:
                st.error(f"Erro ao registrar resposta: {e}")

# ════════════════════════════════════════════════════════════════════════════
# Tab: Editar Ouvidoria
# ════════════════════════════════════════════════════════════════════════════
with tab_editar:
    categorias = carregar_categorias()
    cat_map    = {nome: cid for cid, nome in categorias}
    cat_nomes  = [nome for _, nome in categorias]

    # ── Reclamações editáveis ─────────────────────────────────────────────────
    st.subheader("Reclamações")

    total_recs = len(st.session_state["resp_recs_edit"])

    for i, rec in enumerate(st.session_state["resp_recs_edit"]):
        tipo_label  = rec.get("tipo_servico", "")
        is_fret     = tipo_label in _TIPO_SERVICO_FRET
        tipo_base   = _TIPO_BASE_MAP.get(tipo_label, tipo_label)
        cidades_rec = carregar_cidades_atendidas(tipo_base) if not is_fret else carregar_municipios()

        rec_id_key = rec["id"] if rec.get("id") else f"novo_{i}"

        subcat_label = rec.get("subcategoria_nome") or "Sem subcategoria"
        with st.expander(
            f"{rec['numero_item']} - {rec.get('categoria_nome') or 'Sem categoria'} - {subcat_label} - {tipo_label}",
            expanded=False,
        ):
            st.write(f"**Tipo de Serviço:** {tipo_label}")

            cat_idx = (cat_nomes.index(rec["categoria_nome"]) + 1) if rec.get("categoria_nome") and rec["categoria_nome"] in cat_nomes else 0
            cat_sel = st.selectbox(
                "Categoria", ["(Sem categoria)"] + cat_nomes,
                index=cat_idx, key=f"resp_cat_{rec_id_key}",
            )
            if cat_sel != "(Sem categoria)":
                st.session_state["resp_recs_edit"][i].update({"categoria_nome": cat_sel, "categoria_id": cat_map.get(cat_sel)})
            else:
                st.session_state["resp_recs_edit"][i].update({"categoria_nome": None, "categoria_id": None})

            cat_id_atual = st.session_state["resp_recs_edit"][i].get("categoria_id")
            if cat_id_atual:
                subcats = carregar_subcategorias(cat_id_atual)
                if subcats:
                    subcat_nomes     = [n for _, n in subcats]
                    subcat_map_local = {n: sid for sid, n in subcats}
                    subcat_idx = (subcat_nomes.index(rec.get("subcategoria_nome")) + 1) if rec.get("subcategoria_nome") and rec["subcategoria_nome"] in subcat_nomes else 0
                    subcat_sel = st.selectbox(
                        "Subcategoria", ["(Nenhuma)"] + subcat_nomes,
                        index=subcat_idx, key=f"resp_subcat_{rec_id_key}",
                    )
                    if subcat_sel != "(Nenhuma)":
                        st.session_state["resp_recs_edit"][i].update({"subcategoria_id": subcat_map_local[subcat_sel], "subcategoria_nome": subcat_sel})
                    else:
                        st.session_state["resp_recs_edit"][i].update({"subcategoria_id": None, "subcategoria_nome": None})

            if is_fret:
                emp_fret = st.text_input(
                    "Empresa de Fretamento",
                    value=rec.get("empresa_fretamento") or "",
                    key=f"resp_empfret_{rec_id_key}",
                )
                st.session_state["resp_recs_edit"][i]["empresa_fretamento"] = emp_fret or None

            emb_idx = (cidades_rec.index(rec["local_embarque"]) + 1) if rec.get("local_embarque") and rec["local_embarque"] in cidades_rec else 0
            emb_sel = st.selectbox(
                "Local de Embarque", [_OPCAO_NAO_INFORMADO] + cidades_rec,
                index=emb_idx, key=f"resp_emb_{rec_id_key}",
            )
            emb_val = None if emb_sel == _OPCAO_NAO_INFORMADO else emb_sel
            st.session_state["resp_recs_edit"][i]["local_embarque"] = emb_val

            if not is_fret and emb_val:
                cidades_dest_rec = carregar_cidades_destino(tipo_base, emb_val)
                des_idx = (cidades_dest_rec.index(rec["local_desembarque"]) + 1) if cidades_dest_rec and rec.get("local_desembarque") and rec["local_desembarque"] in cidades_dest_rec else 0
                des_sel = (
                    st.selectbox("Local de Desembarque", [_OPCAO_NAO_INFORMADO] + (cidades_dest_rec or []),
                                 index=des_idx, key=f"resp_des_{rec_id_key}")
                    if cidades_dest_rec else _OPCAO_NAO_INFORMADO
                )
            else:
                des_idx = (cidades_rec.index(rec["local_desembarque"]) + 1) if rec.get("local_desembarque") and rec["local_desembarque"] in cidades_rec else 0
                des_sel = st.selectbox(
                    "Local de Desembarque", [_OPCAO_NAO_INFORMADO] + cidades_rec,
                    index=des_idx, key=f"resp_des_{rec_id_key}",
                )
            st.session_state["resp_recs_edit"][i]["local_desembarque"] = None if des_sel == _OPCAO_NAO_INFORMADO else des_sel

            desc = st.text_area("Descrição", value=rec["descricao"] or "", key=f"resp_desc_{rec_id_key}", height=100)
            st.session_state["resp_recs_edit"][i]["descricao"] = desc or None

            if not is_fret:
                st.markdown("**Autos vinculados:**")
                if rec["autos"]:
                    for a in rec["autos"]:
                        col_auto, col_rem = st.columns([5, 1])
                        denom = " – ".join(filter(None, [a.get("denominacao_a"), a.get("denominacao_b")])) or a["numero"]
                        col_auto.write(f"- {a['numero']} – {a.get('permissionaria', '')} – {denom}")
                        if col_rem.button("✕", key=f"rem_auto_{rec_id_key}_{a['id']}"):
                            st.session_state["resp_recs_edit"][i]["autos"] = [x for x in rec["autos"] if x["id"] != a["id"]]
                            st.rerun()
                else:
                    st.write("Nenhum auto vinculado")

            if total_recs > 1:
                st.divider()
                if st.button("🗑 Remover reclamação", key=f"rem_rec_{rec_id_key}", type="secondary"):
                    st.session_state["resp_recs_edit"].pop(i)
                    for a in st.session_state["resp_autos_checklist"]:
                        st.session_state.pop(f"resp_chk_{a['id']}", None)
                    st.session_state["resp_autos_checklist"] = []
                    st.session_state["resp_rec_alvo_anterior"] = None
                    st.rerun()

    # ── Adicionar Reclamação ──────────────────────────────────────────────────
    st.markdown("#### Adicionar Reclamação")
    secao_nova_reclamacao("resp_recs_edit", key_prefix="resp_", checklist_key="resp_autos_checklist", chk_prefix="resp_chk_")

    # ── Vincular Autos ────────────────────────────────────────────────────────
    secao_vincular_autos(
        recs_state_key="resp_recs_edit",
        checklist_key="resp_autos_checklist",
        alvo_anterior_key="resp_rec_alvo_anterior",
        chk_prefix="resp_chk_",
        btn_prefix="resp_",
        extended_auto_info=True,
    )

    # ── Ações da aba Editar ───────────────────────────────────────────────────
    st.divider()
    col_salvar, col_limpar = st.columns(2)

    if col_salvar.button("💾 Salvar Edição", type="primary", use_container_width=True):
        recs_payload = [
            {
                "id": r["id"],
                "numero_item": r["numero_item"],
                "categoria_id": r["categoria_id"],
                "subcategoria_id": r["subcategoria_id"],
                "tipo_servico": r["tipo_servico"],
                "local_embarque": r["local_embarque"],
                "local_desembarque": r["local_desembarque"],
                "empresa_fretamento": r["empresa_fretamento"],
                "descricao": r["descricao"],
                "autos": [{"id": a["id"]} for a in r["autos"]],
            }
            for r in st.session_state["resp_recs_edit"]
        ]
        try:
            atualizar_reclamacoes(ouvidoria_id, recs_payload)
            st.toast("Edições salvas com sucesso!", icon="✅")
            st.session_state.pop("resp_recs_edit", None)
            st.session_state.pop("resp_autos_checklist", None)
            st.session_state["resp_rec_alvo_anterior"] = None
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao salvar edições: {e}")

    if col_limpar.button("↩ Limpar Alterações", use_container_width=True):
        st.session_state.pop("resp_recs_edit", None)
        st.session_state.pop("resp_autos_checklist", None)
        st.session_state["resp_rec_alvo_anterior"] = None
        st.rerun()
