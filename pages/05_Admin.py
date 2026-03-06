"""Administração: usuários, categorias, gerências e coordenações."""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import auth
from auth import usuario_logado
from database.connection import db_session, get_session
from models import Usuario, TipoUsuario, Categoria, Gerencia, Coordenacao

st.set_page_config(page_title="Administração", page_icon="⚙️", layout="wide")
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

tab_users, tab_cats, tab_ger, tab_coord = st.tabs(
    ["Usuários", "Categorias", "Gerências", "Coordenações"]
)

# ════════════════════════════════════════════════════════════════════════════
# Tab: Usuários
# ════════════════════════════════════════════════════════════════════════════
with tab_users:
    st.subheader("Usuários Técnicos")

    def listar_usuarios():
        s = get_session()
        try:
            users = s.query(Usuario).order_by(Usuario.nome).all()
            result = []
            for usr in users:
                g = usr.gerencia.nome if usr.gerencia else "–"
                c = usr.coordenacao.nome if usr.coordenacao else "–"
                result.append({
                    "id": usr.id,
                    "nome": usr.nome,
                    "email": usr.email,
                    "tipo": usr.tipo.value,
                    "gerencia": g,
                    "coordenacao": c,
                    "ativo": "✅" if usr.ativo else "❌",
                })
            return result
        finally:
            s.close()

    users = listar_usuarios()
    if users:
        import pandas as pd
        df = pd.DataFrame(users).rename(columns={
            "id": "ID", "nome": "Nome", "email": "E-mail",
            "tipo": "Perfil", "gerencia": "Gerência",
            "coordenacao": "Coordenação", "ativo": "Ativo",
        })
        st.dataframe(df.drop(columns=["ID"]), use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("#### Novo Usuário / Editar Senha")

    def carregar_gerencias():
        s = get_session()
        try:
            gs = s.query(Gerencia).order_by(Gerencia.nome).all()
            return [(g.id, g.nome) for g in gs]
        finally:
            s.close()

    def carregar_coordenacoes(gerencia_id=None):
        s = get_session()
        try:
            q = s.query(Coordenacao)
            if gerencia_id:
                q = q.filter_by(gerencia_id=gerencia_id)
            cs = q.order_by(Coordenacao.nome).all()
            return [(c.id, c.nome) for c in cs]
        finally:
            s.close()

    gerencias = carregar_gerencias()
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
            s = get_session()
            existe = s.query(Usuario).filter_by(email=novo_email.strip()).first()
            s.close()
            if existe:
                st.error("Já existe um usuário com este e-mail.")
            else:
                with db_session() as s:
                    s.add(Usuario(
                        nome=novo_nome.strip(),
                        email=novo_email.strip(),
                        senha_hash=auth.hash_senha(nova_senha),
                        tipo=TipoUsuario(novo_tipo),
                        gerencia_id=ger_id_final,
                        coordenacao_id=coord_id_final,
                        ativo=True,
                    ))
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
            with db_session() as s:
                usr = s.query(Usuario).filter_by(id=sel_user_id).first()
                usr.ativo = True
            st.toast("Usuário ativado!", icon="✅")
            st.rerun()
        if col_dat.button("Desativar"):
            with db_session() as s:
                usr = s.query(Usuario).filter_by(id=sel_user_id).first()
                usr.ativo = False
            st.toast("Usuário desativado!", icon="⛔")
            st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# Tab: Categorias
# ════════════════════════════════════════════════════════════════════════════
with tab_cats:
    st.subheader("Categorias de Reclamação")

    def listar_cats():
        s = get_session()
        try:
            cats = s.query(Categoria).order_by(Categoria.nome).all()
            return [{"id": c.id, "nome": c.nome, "descricao": c.descricao or "", "ativo": "✅" if c.ativo else "❌"} for c in cats]
        finally:
            s.close()

    cats = listar_cats()
    if cats:
        import pandas as pd
        df_c = pd.DataFrame(cats).rename(columns={"id": "ID", "nome": "Nome", "descricao": "Descrição", "ativo": "Ativo"})
        st.dataframe(df_c.drop(columns=["ID"]), use_container_width=True, hide_index=True)

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
            with db_session() as s:
                s.add(Categoria(nome=cat_nome.strip(), descricao=cat_desc.strip() or None))
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
            with db_session() as s:
                cat = s.query(Categoria).filter_by(id=cat_sel_id).first()
                cat.ativo = True
            st.success("Ativada.")
            st.rerun()
        if c2.button("Desativar cat."):
            with db_session() as s:
                cat = s.query(Categoria).filter_by(id=cat_sel_id).first()
                cat.ativo = False
            st.success("Desativada.")
            st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# Tab: Gerências
# ════════════════════════════════════════════════════════════════════════════
with tab_ger:
    st.subheader("Gerências")

    def listar_ger():
        s = get_session()
        try:
            gs = s.query(Gerencia).order_by(Gerencia.nome).all()
            return [{"id": g.id, "nome": g.nome} for g in gs]
        finally:
            s.close()

    gers = listar_ger()
    if gers:
        import pandas as pd
        st.dataframe(
            pd.DataFrame(gers).rename(columns={"id": "ID", "nome": "Nome"}).drop(columns=["ID"]),
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
            with db_session() as s:
                s.add(Gerencia(nome=ger_nome.strip()))
            st.success("Gerência criada.")
            st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# Tab: Coordenações
# ════════════════════════════════════════════════════════════════════════════
with tab_coord:
    st.subheader("Coordenações")

    def listar_coord():
        s = get_session()
        try:
            cs = s.query(Coordenacao).order_by(Coordenacao.nome).all()
            return [{"id": c.id, "nome": c.nome, "gerencia": c.gerencia.nome if c.gerencia else "–"} for c in cs]
        finally:
            s.close()

    coords = listar_coord()
    if coords:
        import pandas as pd
        st.dataframe(
            pd.DataFrame(coords).rename(columns={"id": "ID", "nome": "Nome", "gerencia": "Gerência"}).drop(columns=["ID"]),
            use_container_width=True,
            hide_index=True,
        )

    def carregar_ger_simples():
        s = get_session()
        try:
            gs = s.query(Gerencia).order_by(Gerencia.nome).all()
            return [(g.id, g.nome) for g in gs]
        finally:
            s.close()

    with st.form("form_coord"):
        gs_form = carregar_ger_simples()
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
                    with db_session() as s:
                        s.add(Coordenacao(nome=coord_nome.strip(), gerencia_id=ger_map_form[ger_coord]))
                    st.success("Coordenação criada.")
                    st.rerun()
