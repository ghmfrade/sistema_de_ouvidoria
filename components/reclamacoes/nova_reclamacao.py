"""Formulário reutilizável para adicionar uma nova reclamação a uma lista em session_state."""

import streamlit as st

from api.client.enums import TIPO_SERVICO
from api.client.catalogo_client import carregar_categorias, carregar_municipios, carregar_subcategorias
from api.client.autos_client import carregar_cidades_atendidas, carregar_cidades_destino

_TIPO_SERVICO_FRET = ("Fretamento Intermunicipal", "Fretamento Metropolitano")
_TIPO_SERVICO_METRO = "Regular – Metropolitano"
_TIPO_SERVICO_INTER = "Regular – Intermunicipal"
_OPCAO_NAO_INFORMADO = "Não informado"

_TIPO_BASE_MAP = {
    "Fretamento Intermunicipal": _TIPO_SERVICO_INTER,
    "Fretamento Metropolitano": _TIPO_SERVICO_METRO,
}


def secao_nova_reclamacao(recs_state_key: str, key_prefix: str = "") -> None:
    """Renderiza o formulário de adicionar reclamação e anexa o resultado em session_state[recs_state_key].

    Args:
        recs_state_key: chave em st.session_state que contém a lista de reclamações.
        key_prefix: prefixo para widgets keys (use para evitar conflito entre páginas).
    """
    kp = key_prefix

    categorias = carregar_categorias()
    cat_map = {nome: cid for cid, nome in categorias}
    cat_nomes = [nome for _, nome in categorias]

    tipo_servico_sel = st.radio(
        "Tipo de Serviço *", TIPO_SERVICO, horizontal=True, key=f"{kp}novo_rec_tipo",
    )
    is_fretamento = tipo_servico_sel in _TIPO_SERVICO_FRET
    tipo_base = _TIPO_BASE_MAP.get(tipo_servico_sel, tipo_servico_sel)

    empresa_fretamento_val = None
    if is_fretamento:
        empresa_fretamento_val = st.text_input(
            "Empresa de Fretamento", key=f"{kp}empresa_fretamento_input",
        )

    cat_sel = st.selectbox(
        "Categoria *",
        cat_nomes if cat_nomes else ["(Nenhuma categoria cadastrada)"],
        key=f"{kp}novo_rec_cat",
    )
    cat_id_sel = cat_map.get(cat_sel)

    subcat_id_sel = subcat_nome_sel = None
    if cat_id_sel:
        subcats = carregar_subcategorias(cat_id_sel)
        if subcats:
            subcat_nomes = [n for _, n in subcats]
            subcat_map_local = {n: sid for sid, n in subcats}
            subcat_sel = st.selectbox(
                "Subcategoria *", subcat_nomes, key=f"{kp}novo_rec_subcat",
            )
            subcat_id_sel = subcat_map_local[subcat_sel]
            subcat_nome_sel = subcat_sel

    col_emb, col_desemb = st.columns(2)
    if not is_fretamento:
        cidades_origem = carregar_cidades_atendidas(tipo_base)
        with col_emb:
            emb_sel = st.selectbox(
                "Local de Embarque", [_OPCAO_NAO_INFORMADO] + cidades_origem,
                key=f"{kp}rec_emb_sel",
            )
        emb_val = None if emb_sel == _OPCAO_NAO_INFORMADO else emb_sel
        with col_desemb:
            if emb_val:
                cidades_destino = carregar_cidades_destino(tipo_base, emb_val)
                if cidades_destino:
                    desemb_sel = st.selectbox(
                        "Local de Desembarque", [_OPCAO_NAO_INFORMADO] + cidades_destino,
                        key=f"{kp}rec_desemb_sel",
                    )
                else:
                    st.warning("Sem atendimento a partir desta cidade.")
                    desemb_sel = _OPCAO_NAO_INFORMADO
            else:
                desemb_sel = st.selectbox(
                    "Local de Desembarque", [_OPCAO_NAO_INFORMADO] + cidades_origem,
                    key=f"{kp}rec_desemb_sel",
                )
    else:
        municipios_sp = carregar_municipios()
        with col_emb:
            emb_sel = st.selectbox(
                "Local de Embarque", [_OPCAO_NAO_INFORMADO] + municipios_sp,
                key=f"{kp}rec_emb_sel",
            )
        with col_desemb:
            desemb_sel = st.selectbox(
                "Local de Desembarque", [_OPCAO_NAO_INFORMADO] + municipios_sp,
                key=f"{kp}rec_desemb_sel",
            )
        emb_val = None if emb_sel == _OPCAO_NAO_INFORMADO else emb_sel

    with st.form(f"{kp}form_reclamacao", clear_on_submit=True):
        col_a, col_b = st.columns([1, 2])
        with col_a:
            st.caption(f"Embarque: **{emb_sel}**")
            st.caption(f"Desembarque: **{desemb_sel}**")
        with col_b:
            descricao = st.text_area("Descrição", height=100)
        adicionar_rec = st.form_submit_button("✔ Adicionar Reclamação", type="primary")

        if adicionar_rec:
            if not cat_nomes or cat_sel == "(Nenhuma categoria cadastrada)":
                st.error("Cadastre ao menos uma categoria no Admin antes de criar reclamações.")
            elif cat_sel not in cat_map:
                st.error("Selecione uma categoria válida.")
            elif subcat_id_sel is None:
                st.error("Selecione uma subcategoria. Caso não existam subcategorias para esta categoria, cadastre-as no Admin.")
            else:
                recs = st.session_state[recs_state_key]
                proximo_item = max((r["numero_item"] for r in recs), default=0) + 1
                recs.append({
                    "id": None,
                    "numero_item": proximo_item,
                    "categoria_id": cat_map[cat_sel],
                    "categoria_nome": cat_sel,
                    "subcategoria_id": subcat_id_sel,
                    "subcategoria_nome": subcat_nome_sel,
                    "tipo_servico": tipo_servico_sel,
                    "local_embarque": None if emb_sel == _OPCAO_NAO_INFORMADO else emb_sel,
                    "local_desembarque": None if desemb_sel == _OPCAO_NAO_INFORMADO else desemb_sel,
                    "descricao": descricao or None,
                    "empresa_fretamento": empresa_fretamento_val if is_fretamento else None,
                    "autos": [],
                })
                st.rerun()
