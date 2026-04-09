"""Administração: usuários, categorias, gerências e coordenações."""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

import auth
from auth import usuario_logado
from utils import (
    fmt_ativo,
    listar_categorias_e_status,
    listar_coord_e_status,
    listar_gerencias_e_status,
    listar_subcat_e_status,
    listar_usuarios_e_status,
    carregar_coordenacoes,
    carregar_categorias,
    carregar_todas_gerencias,
)
from utils.admin_ops import (
    criar_categoria,
    criar_coordenacao,
    criar_gerencia,
    criar_subcategoria,
    criar_usuario,
    email_existe,
    toggle_categoria,
    toggle_coordenacao,
    toggle_gerencia,
    toggle_subcategoria,
    toggle_usuario,
)

st.set_page_config(page_title="Administração", page_icon="⚙️", layout="wide")
st.markdown('<style>[data-testid="stSidebar"]{width:220px!important;min-width:220px!important;}</style>', unsafe_allow_html=True)
auth.require_gestor()

u = usuario_logado()

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"**{u.nome}**")
    st.caption("Gestor")
    st.divider()
    if st.button("← Ouvidorias", use_container_width=True):
        st.switch_page("pages/01_Ouvidorias.py")
    if st.button("Sair", use_container_width=True):
        auth.fazer_logout()
        st.rerun()

st.title("⚙️ Administração")

tab_users, tab_cats, tab_subcats, tab_ger, tab_coord = st.tabs(
    ["Usuários", "Categorias", "Subcategorias", "Gerências", "Coordenações"]
)

# ════════════════════════════════════════════════════════════════════════════
# Tab: Usuários
# ════════════════════════════════════════════════════════════════════════════
with tab_users:
    st.subheader("Usuários Técnicos")

    users = listar_usuarios_e_status()
    if users:
        df = pd.DataFrame(users)
        df["ativo"] = df["ativo"].map(fmt_ativo)
        df = df.rename(columns={
            "id": "ID", "nome": "Nome", "email": "E-mail",
            "tipo": "Perfil", "gerencia_nome": "Gerência",
            "coordenacao_nome": "Coordenação", "ativo": "Ativo",
        })
        cols_ocultar = [c for c in ["ID", "gerencia_id", "coordenacao_id"] if c in df.columns]
        st.dataframe(df.drop(columns=cols_ocultar), use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("#### Novo Usuário / Editar Senha")

    gerencias = carregar_todas_gerencias()
    ger_map = {nome: gid for gid, nome in gerencias}

    # Gerência e Coordenação FORA do form para permitir atualização dinâmica
    col_ger, col_coord = st.columns(2)
    with col_ger:
        ger_sel = st.selectbox("Gerência", ["(Nenhuma)"] + [n for _, n in gerencias], key="nu_gerencia")
    ger_id_sel = ger_map.get(ger_sel) if ger_sel != "(Nenhuma)" else None
    coords = carregar_coordenacoes(ger_id_sel) if ger_id_sel else []
    coord_map = {nome: cid for cid, nome in coords}
    with col_coord:
        coord_sel = st.selectbox("Coordenação", ["(Nenhuma)"] + [n for _, n in coords], key="nu_coordenacao")

    with st.form("form_novo_user"):
        col1, col2 = st.columns(2)
        with col1:
            novo_nome = st.text_input("Nome *")
            novo_email = st.text_input("E-mail *")
        with col2:
            nova_senha = st.text_input("Senha *", type="password")
            novo_tipo = st.selectbox("Perfil *", ["tecnico", "gestor"])

        criar = st.form_submit_button("➕ Criar Usuário", type="primary")

    if criar:
        ger_id_final = ger_map.get(st.session_state.get("nu_gerencia", "(Nenhuma)"))
        coord_id_final = coord_map.get(st.session_state.get("nu_coordenacao", "(Nenhuma)"))
        if not novo_nome.strip() or not novo_email.strip() or not nova_senha:
            st.error("Nome, e-mail e senha são obrigatórios.")
        else:
            if email_existe(novo_email):
                st.error("Já existe um usuário com este e-mail.")
            else:
                criar_usuario(
                    novo_nome, novo_email, auth.hash_senha(nova_senha),
                    novo_tipo, ger_id_final, coord_id_final,
                )
                st.toast(f"Usuário {novo_email} criado com sucesso!", icon="✅")
                st.rerun()

    st.divider()
    st.markdown("#### Ativar / Desativar Usuário")
    if users:
        user_emails = [f"{usr['nome']} ({usr['email']})" for usr in users]
        sel_user_label = st.selectbox("Selecionar usuário", user_emails, key="toggle_user")
        sel_user_id = users[user_emails.index(sel_user_label)]["id"]
        col_at, col_dat = st.columns(2)
        if col_at.button("Ativar"):
            toggle_usuario(sel_user_id, True)
            st.toast("Usuário ativado!", icon="✅")
            st.rerun()
        if col_dat.button("Desativar"):
            toggle_usuario(sel_user_id, False)
            st.toast("Usuário desativado!", icon="⛔")
            st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# Tab: Categorias
# ════════════════════════════════════════════════════════════════════════════
with tab_cats:
    st.subheader("Categorias de Reclamação")

    cats = listar_categorias_e_status()
    if cats:
        df_c = pd.DataFrame(cats)
        df_c["ativo"] = df_c["ativo"].map(fmt_ativo)
        df_c = df_c.rename(columns={"id": "ID", "nome": "Nome", "descricao": "Descrição", "ativo": "Ativo"})
        st.dataframe(df_c.drop(columns=["ID", "Descrição"], errors="ignore"), use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("#### Nova Categoria")
    with st.form("form_cat"):
        cat_nome = st.text_input("Nome *")
        cat_desc = st.text_area("Descrição", height=80)
        criar_cat = st.form_submit_button("➕ Criar", type="primary")

    if criar_cat:
        if not cat_nome.strip():
            st.error("Informe o nome da categoria.")
        else:
            criar_categoria(cat_nome, cat_desc.strip() or None)
            st.success("Categoria criada.")
            st.rerun()

    if cats:
        st.divider()
        st.markdown("#### Ativar / Desativar Categoria")
        cat_labels = [c["nome"] for c in cats]
        cat_sel_nome = st.selectbox("Categoria", cat_labels, key="toggle_cat")
        cat_sel_id = cats[cat_labels.index(cat_sel_nome)]["id"]
        c1, c2 = st.columns(2)
        if c1.button("Ativar cat."):
            toggle_categoria(cat_sel_id, True)
            st.success("Ativada.")
            st.rerun()
        if c2.button("Desativar cat."):
            toggle_categoria(cat_sel_id, False)
            st.success("Desativada.")
            st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# Tab: Subcategorias
# ════════════════════════════════════════════════════════════════════════════
with tab_subcats:
    st.subheader("Subcategorias de Reclamação")

    subcats = listar_subcat_e_status()
    if subcats:
        df_sc = pd.DataFrame(subcats)
        df_sc["ativo"] = df_sc["ativo"].map(fmt_ativo)
        df_sc = df_sc.rename(columns={
            "id": "ID", "nome": "Nome", "categoria_nome": "Categoria", "ativo": "Ativo"
        })
        cols_ocultar_sc = [c for c in ["ID", "categoria_id"] if c in df_sc.columns]
        st.dataframe(df_sc.drop(columns=cols_ocultar_sc), use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("#### Nova Subcategoria")

    cats_ativas = carregar_categorias()
    if not cats_ativas:
        st.warning("Cadastre ao menos uma Categoria ativa primeiro.")
    else:
        cat_map_sub = {n: cid for cid, n in cats_ativas}
        with st.form("form_subcat"):
            subcat_cat = st.selectbox("Categoria *", [n for _, n in cats_ativas], key="subcat_cat")
            subcat_nome = st.text_input("Nome da Subcategoria *")
            criar_subcat = st.form_submit_button("➕ Criar", type="primary")

        if criar_subcat:
            if not subcat_nome.strip():
                st.error("Informe o nome da subcategoria.")
            else:
                criar_subcategoria(subcat_nome, cat_map_sub[subcat_cat])
                st.success("Subcategoria criada.")
                st.rerun()

    if subcats:
        st.divider()
        st.markdown("#### Ativar / Desativar Subcategoria")
        subcat_labels = [f"{sc['nome']} ({sc['categoria_nome']})" for sc in subcats]
        subcat_sel_label = st.selectbox("Subcategoria", subcat_labels, key="toggle_subcat")
        subcat_sel_id = subcats[subcat_labels.index(subcat_sel_label)]["id"]
        sc1, sc2 = st.columns(2)
        if sc1.button("Ativar subcat."):
            toggle_subcategoria(subcat_sel_id, True)
            st.success("Ativada.")
            st.rerun()
        if sc2.button("Desativar subcat."):
            toggle_subcategoria(subcat_sel_id, False)
            st.success("Desativada.")
            st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# Tab: Gerências
# ════════════════════════════════════════════════════════════════════════════
with tab_ger:
    st.subheader("Gerências")

    gers = listar_gerencias_e_status()
    if gers:
        df_g = pd.DataFrame(gers)
        df_g["ativo"] = df_g["ativo"].map(fmt_ativo)
        st.dataframe(
            df_g.rename(columns={"id": "ID", "nome": "Nome", "ativo": "Ativo"}).drop(columns=["ID"]),
            use_container_width=True,
            hide_index=True,
        )

    with st.form("form_ger"):
        ger_nome = st.text_input("Nome da Gerência *")
        criar_ger = st.form_submit_button("➕ Criar", type="primary")

    if criar_ger:
        if not ger_nome.strip():
            st.error("Informe o nome.")
        else:
            criar_gerencia(ger_nome)
            st.success("Gerência criada.")
            st.rerun()

    if gers:
        st.divider()
        st.markdown("#### Ativar / Desativar Gerência")
        ger_labels = [g["nome"] for g in gers]
        ger_sel_nome = st.selectbox("Gerência", ger_labels, key="toggle_ger")
        ger_sel_id = gers[ger_labels.index(ger_sel_nome)]["id"]
        g1, g2 = st.columns(2)
        if g1.button("Ativar ger."):
            toggle_gerencia(ger_sel_id, True)
            st.success("Ativada.")
            st.rerun()
        if g2.button("Desativar ger."):
            toggle_gerencia(ger_sel_id, False)
            st.success("Desativada.")
            st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# Tab: Coordenações
# ════════════════════════════════════════════════════════════════════════════
with tab_coord:
    st.subheader("Coordenações")

    coords_list = listar_coord_e_status()
    if coords_list:
        df_co = pd.DataFrame(coords_list)
        df_co["ativo"] = df_co["ativo"].map(fmt_ativo)
        df_co = df_co.rename(columns={"id": "ID", "nome": "Nome", "gerencia_nome": "Gerência", "ativo": "Ativo"})
        cols_ocultar_co = [c for c in ["ID", "gerencia_id"] if c in df_co.columns]
        st.dataframe(df_co.drop(columns=cols_ocultar_co), use_container_width=True, hide_index=True)

    with st.form("form_coord"):
        gs_form = carregar_todas_gerencias()
        if not gs_form:
            st.warning("Cadastre ao menos uma Gerência primeiro.")
            st.form_submit_button("➕ Criar", disabled=True)
        else:
            ger_map_form = {n: gid for gid, n in gs_form}
            coord_nome = st.text_input("Nome da Coordenação *")
            ger_coord = st.selectbox("Gerência *", [n for _, n in gs_form])
            criar_coord = st.form_submit_button("➕ Criar", type="primary")

            if criar_coord:
                if not coord_nome.strip():
                    st.error("Informe o nome.")
                else:
                    criar_coordenacao(coord_nome, ger_map_form[ger_coord])
                    st.success("Coordenação criada.")
                    st.rerun()

    if coords_list:
        st.divider()
        st.markdown("#### Ativar / Desativar Coordenação")
        coord_labels = [f"{c['nome']} ({c['gerencia_nome']})" for c in coords_list]
        coord_sel_label = st.selectbox("Coordenação", coord_labels, key="toggle_coord")
        coord_sel_id = coords_list[coord_labels.index(coord_sel_label)]["id"]
        cc1, cc2 = st.columns(2)
        if cc1.button("Ativar coord."):
            toggle_coordenacao(coord_sel_id, True)
            st.success("Ativada.")
            st.rerun()
        if cc2.button("Desativar coord."):
            toggle_coordenacao(coord_sel_id, False)
            st.success("Desativada.")
            st.rerun()
