"""Ponto de entrada do Sistema de Ouvidorias ARTESP."""
import streamlit as st

st.set_page_config(
    page_title="Sistema de Ouvidorias – ARTESP",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

import auth
from auth import usuario_logado


def pagina_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("📋 Sistema de Ouvidorias")
        st.subheader("ARTESP")
        st.divider()
        with st.form("form_login"):
            email = st.text_input("E-mail", placeholder="usuario@artesp.sp.gov.br")
            senha = st.text_input("Senha", type="password")
            entrar = st.form_submit_button("Entrar", use_container_width=True)

        if entrar:
            if not email or not senha:
                st.error("Preencha e-mail e senha.")
            else:
                usuario = auth.autenticar(email, senha)
                if usuario:
                    st.session_state["usuario"] = usuario
                    st.rerun()
                else:
                    st.error("E-mail ou senha incorretos.")


def sidebar_usuario():
    u = usuario_logado()
    if u:
        with st.sidebar:
            st.markdown(f"**{u.nome}**")
            st.caption(f"Perfil: {'Gestor' if u.tipo.value == 'gestor' else 'Técnico'}")
            st.divider()
            if st.button("Sair", use_container_width=True):
                auth.fazer_logout()
                st.rerun()


# ── Roteamento ──────────────────────────────────────────────────────────────
u = usuario_logado()

if not u:
    pagina_login()
else:
    sidebar_usuario()
    st.title("📋 Sistema de Ouvidorias – ARTESP")
    st.info("Use o menu na barra lateral para navegar.")
