"""Ponto de entrada do Sistema de Ouvidorias ARTESP."""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
from components import reduz_margem_side_bar

st.set_page_config(
    page_title="SOUVI",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

import auth
from auth import usuario_logado


def pagina_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("📋 SOUVI")
        st.subheader("Sistema de Ouvidorias da SUCOL")
        st.divider()
        with st.form("form_login"):
            email = st.text_input("E-mail", placeholder="usuario@artesp.sp.gov.br")
            senha = st.text_input("Senha", type="password")
            entrar = st.form_submit_button("Entrar", use_container_width=True)

        if entrar:
            if not email or not senha:
                st.error("Preencha Login e senha.")
            else:
                usuario, erro = auth.autenticar(email, senha)
                if usuario:
                    st.session_state["api_session"] = usuario
                    st.rerun()
                else:
                    st.error(erro)


def sidebar_usuario():
    u = usuario_logado()
    if u:
        with st.sidebar:
            st.markdown(f"**{u['nome']}**")
            st.caption(f"Perfil: {'Gestor' if u.get('tipo') == 'gestor' else 'Técnico'}")
            st.divider()
            if st.button("Sair", use_container_width=True):
                auth.fazer_logout()
                st.rerun()

            with st.container(border=True):
                st.markdown("<p style='text-align: center; font-size: 16px;'><b>Manual de classificação</b></p>", unsafe_allow_html=True)
                guia_pdf = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "GUIA_OPERACIONAL_Manual_Classificacao.pdf",
                )
                with open(guia_pdf, "rb") as pdf_file:
                    st.download_button(
                        label="📥",
                        data=pdf_file,
                        file_name="GUIA_OPERACIONAL_Manual_Classificacao.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )


# ── Roteamento ──────────────────────────────────────────────────────────────
u = usuario_logado()

if not u:
    pagina_login()
else:
    reduz_margem_side_bar()
    sidebar_usuario()
    st.title("📋 SOUVI")
    st.subheader("Sistema de Ouvidorias da SUCOL")
    st.info("Use o menu na barra lateral para navegar.")
