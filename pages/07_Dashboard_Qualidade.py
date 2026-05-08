"""Dashboard de Qualidade — redirecionamento para o Dash app."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import auth
from components import reduz_margem_side_bar, reduz_margem_topo_page

st.set_page_config(page_title="Dashboard Qualidade", layout="wide")
reduz_margem_side_bar()
reduz_margem_topo_page()

if not auth.usuario_logado():
    st.warning("Faça login para acessar esta página.")
    st.stop()

DASH_URL = os.getenv("DASH_URL", "http://localhost:8050")

st.title("Dashboard de Qualidade")
st.markdown(
    "Painel de Reclamações — Sistema de Transporte pode ser acessado por meio do botão abaixo."
    )
st.link_button("Abrir Dashboard de Qualidade →", url=DASH_URL, use_container_width=False)
st.caption(f"Disponível em: {DASH_URL}")


