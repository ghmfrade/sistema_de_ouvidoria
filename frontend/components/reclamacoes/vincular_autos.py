"""Seção reutilizável de vincular autos a uma reclamação."""

import streamlit as st

from api.client.autos_client import (
    buscar_autos_por_trecho,
    carregar_cidades_atendidas,
    carregar_cidades_destino,
    carregar_permissionarias,
    carregar_todos_autos,
)
from api.client.catalogo_client import carregar_regioes_metropolitanas
from utils.formatters import fmt_auto, TC_REGIOES

_TIPO_SERVICO_FRET = ("Fretamento Intermunicipal", "Fretamento Metropolitano")
_TIPO_SERVICO_METRO = "Regular – Metropolitano"
_TIPO_SERVICO_INTER = "Regular – Intermunicipal"

_OPCAO_TODAS = "Todas"
_OPCAO_QUALQUER = "Qualquer"
_OPCAO_NAO_INFORMADO = "Não informado"

_TIPO_BASE_MAP = {
    "Fretamento Intermunicipal": _TIPO_SERVICO_INTER,
    "Fretamento Metropolitano": _TIPO_SERVICO_METRO,
}


def _label_auto(auto: dict) -> str:
    emp = auto.get("empresa", "")
    den = " – ".join(filter(None, [auto.get("denominacao_a"), auto.get("denominacao_b")]))
    tc = auto.get("tc")
    tc_str = f" – TC{tc} {TC_REGIOES[tc]}" if tc and tc in TC_REGIOES else ""
    return f"**{auto['numero']}** – {emp + ' – ' if emp else ''}{den}{tc_str}"


def secao_vincular_autos(
    recs_state_key: str,
    checklist_key: str,
    alvo_anterior_key: str,
    chk_prefix: str,
    btn_prefix: str = "",
    extended_auto_info: bool = False,
) -> None:
    """Renderiza a seção completa de busca e vinculação de autos a uma reclamação.

    Args:
        recs_state_key: chave em st.session_state com a lista de reclamações.
        checklist_key: chave em st.session_state para a lista de autos encontrados.
        alvo_anterior_key: chave em st.session_state para rastrear troca de reclamação alvo.
        chk_prefix: prefixo para as keys de checkbox (ex: "chk_" ou "resp_chk_").
        btn_prefix: prefixo para as keys de botão (ex: "" ou "resp_").
        extended_auto_info: se True, armazena denominação e permissionária nos autos
            vinculados (necessário quando a página exibe cada auto individualmente).
    """
    recs = st.session_state[recs_state_key]
    recs_com_autos = [r for r in recs if r.get("tipo_servico") not in _TIPO_SERVICO_FRET]

    if not recs_com_autos:
        return

    st.divider()
    st.subheader("Vincular Autos à Reclamação")

    rec_labels = [
        f"{r['numero_item']} - {r.get('categoria_nome') or 'Sem categoria'} - {r.get('subcategoria_nome') or 'Sem subcategoria'} - {r.get('tipo_servico', '')}"
        for r in recs_com_autos
    ]
    rec_idx_map = [i for i, r in enumerate(recs) if r.get("tipo_servico") not in _TIPO_SERVICO_FRET]

    rec_sel_label = st.selectbox("Reclamação alvo", rec_labels, key=f"{btn_prefix}rec_alvo_sel")
    rec_idx = rec_idx_map[rec_labels.index(rec_sel_label)]

    if st.session_state[alvo_anterior_key] != rec_sel_label:
        for a in st.session_state[checklist_key]:
            st.session_state.pop(f"{chk_prefix}{a['id']}", None)
        st.session_state[checklist_key] = []
        st.session_state[alvo_anterior_key] = rec_sel_label

    rec_tipo_raw = recs[rec_idx].get("tipo_servico", _TIPO_SERVICO_INTER)
    rec_tipo = _TIPO_BASE_MAP.get(rec_tipo_raw, rec_tipo_raw)
    rec_alvo = recs[rec_idx]
    auto_fill_orig = rec_alvo.get("local_embarque")
    auto_fill_dest = rec_alvo.get("local_desembarque")

    regiao_sel_val = None
    if rec_tipo == _TIPO_SERVICO_METRO:
        regioes = carregar_regioes_metropolitanas()
        regiao_sel = st.selectbox(
            "Região Metropolitana", [_OPCAO_QUALQUER] + regioes, key=f"{btn_prefix}filtro_rm",
        )
        regiao_sel_val = None if regiao_sel == _OPCAO_QUALQUER else regiao_sel

    perms = carregar_permissionarias(rec_tipo, regiao=regiao_sel_val)
    perm_nomes = [p.get("nome_fantasia") or p["nome"] for p in perms]
    perm_map = {(p.get("nome_fantasia") or p["nome"]): p["id"] for p in perms}
    empresa_sel = st.selectbox("Empresa", [_OPCAO_TODAS] + perm_nomes, key=f"{btn_prefix}filtro_empresa")
    perm_id_sel = None if empresa_sel == _OPCAO_TODAS else perm_map.get(empresa_sel)
    cidades = carregar_cidades_atendidas(rec_tipo, perm_id=perm_id_sel, regiao=regiao_sel_val)

    col_trecho, col_todos = st.columns(2)

    with col_trecho:
        st.markdown("**Buscar por Trecho**")
        idx_orig = (cidades.index(auto_fill_orig) + 1) if auto_fill_orig and auto_fill_orig in cidades else 0
        cidade_orig_sel = st.selectbox(
            "Cidade de Origem", [_OPCAO_NAO_INFORMADO] + cidades,
            index=idx_orig, key=f"{btn_prefix}trecho_orig",
        )
        orig_val = None if cidade_orig_sel == _OPCAO_NAO_INFORMADO else cidade_orig_sel

        if orig_val:
            destinos_trecho = carregar_cidades_destino(rec_tipo, orig_val, perm_id=perm_id_sel, regiao=regiao_sel_val)
            if destinos_trecho:
                idx_dest = (
                    destinos_trecho.index(auto_fill_dest) + 1
                ) if auto_fill_dest and auto_fill_dest in destinos_trecho else 0
                cidade_dest_sel = st.selectbox(
                    "Cidade de Destino", [_OPCAO_NAO_INFORMADO] + destinos_trecho,
                    index=idx_dest, key=f"{btn_prefix}trecho_dest",
                )
            else:
                st.info("Sem atendimento a partir desta cidade.")
                cidade_dest_sel = _OPCAO_NAO_INFORMADO
        else:
            idx_dest = (cidades.index(auto_fill_dest) + 1) if auto_fill_dest and auto_fill_dest in cidades else 0
            cidade_dest_sel = st.selectbox(
                "Cidade de Destino", [_OPCAO_NAO_INFORMADO] + cidades,
                index=idx_dest, key=f"{btn_prefix}trecho_dest",
            )

        buscar_disabled = not orig_val and cidade_dest_sel == _OPCAO_NAO_INFORMADO
        if st.button(
            "🔍 Buscar por trecho", use_container_width=True,
            disabled=buscar_disabled, key=f"{btn_prefix}btn_buscar_trecho",
        ):
            orig = None if cidade_orig_sel == _OPCAO_NAO_INFORMADO else cidade_orig_sel
            dest = None if cidade_dest_sel == _OPCAO_NAO_INFORMADO else cidade_dest_sel
            if orig or dest:
                encontrados = buscar_autos_por_trecho(
                    rec_tipo, orig or "", dest or "", perm_id=perm_id_sel, regiao=regiao_sel_val,
                )
                ids_existentes = {a["id"] for a in st.session_state[checklist_key]}
                adicionados = 0
                for a in encontrados:
                    if a["id"] not in ids_existentes:
                        st.session_state[checklist_key].append({
                            "id": a["id"], "numero": a["numero"],
                            "denominacao_a": a.get("denominacao_a"),
                            "denominacao_b": a.get("denominacao_b"),
                            "empresa": a["permissionaria_nome"],
                            "tc": a.get("tc"),
                        })
                        ids_existentes.add(a["id"])
                        adicionados += 1
                st.success(f"{adicionados} autos adicionados ({len(encontrados)} encontrados).")
                st.rerun()
            else:
                st.warning("Selecione ao menos origem ou destino.")

    with col_todos:
        st.markdown("**Todos os Autos**")
        todos_autos = carregar_todos_autos(rec_tipo, perm_id=perm_id_sel, regiao=regiao_sel_val)
        if todos_autos:
            num_opcoes = [fmt_auto(a) for a in todos_autos]
            num_sel = st.selectbox("Selecione o Auto", num_opcoes, key=f"{btn_prefix}num_sel")
            sel_idx = num_opcoes.index(num_sel)
            if st.button("➕ Adicionar à lista", use_container_width=True, key=f"{btn_prefix}btn_add_auto"):
                auto_row = todos_autos[sel_idx]
                ids_existentes = {a["id"] for a in st.session_state[checklist_key]}
                if auto_row["id"] not in ids_existentes:
                    st.session_state[checklist_key].append({
                        "id": auto_row["id"], "numero": auto_row["numero"],
                        "denominacao_a": auto_row.get("denominacao_a"),
                        "denominacao_b": auto_row.get("denominacao_b"),
                        "empresa": auto_row["permissionaria_nome"],
                        "tc": auto_row.get("tc"),
                    })
                    st.success(f"Auto {auto_row['numero']} adicionado.")
                    st.rerun()
                else:
                    st.info("Auto já está na lista.")
        else:
            st.info("Nenhum auto encontrado para os filtros selecionados.")

    checklist = st.session_state[checklist_key]
    if checklist:
        ids_ja_salvos = {a["id"] for a in recs[rec_idx]["autos"]}
        st.markdown(f"**Lista de Autos ({len(checklist)}) — marque os que deseja vincular:**")
        for auto in checklist:
            ja_salvo = auto["id"] in ids_ja_salvos
            label = _label_auto(auto)
            if ja_salvo:
                st.checkbox(label + "  ✅ *já vinculado*", key=f"{chk_prefix}{auto['id']}", value=True, disabled=True)
            else:
                st.checkbox(label, key=f"{chk_prefix}{auto['id']}", value=True)

        col_btn1, col_btn2 = st.columns([2, 1])
        with col_btn1:
            if st.button(
                "✔ Registrar Autos Selecionados", type="primary",
                use_container_width=True, key=f"{btn_prefix}btn_registrar_autos",
            ):
                ids_existentes = {a["id"] for a in recs[rec_idx]["autos"]}
                novos = [
                    a for a in checklist
                    if st.session_state.get(f"{chk_prefix}{a['id']}", True) and a["id"] not in ids_existentes
                ]
                for a in novos:
                    auto_entry = {"id": a["id"], "numero": a["numero"]}
                    if extended_auto_info:
                        auto_entry["denominacao_a"] = a.get("denominacao_a")
                        auto_entry["denominacao_b"] = a.get("denominacao_b")
                        auto_entry["permissionaria"] = a.get("empresa", "")
                    recs[rec_idx]["autos"].append(auto_entry)
                for a in checklist:
                    st.session_state.pop(f"{chk_prefix}{a['id']}", None)
                st.session_state[checklist_key] = []
                st.success(f"{len(novos)} autos vinculados.")
                st.rerun()
        with col_btn2:
            if st.button("🗑 Limpar lista", use_container_width=True, key=f"{btn_prefix}btn_limpar_autos"):
                for a in checklist:
                    st.session_state.pop(f"{chk_prefix}{a['id']}", None)
                st.session_state[checklist_key] = []
                st.rerun()
    else:
        st.info("Use as buscas acima para encontrar e acumular autos na lista.")
