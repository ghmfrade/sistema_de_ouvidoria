"""Página para registrar resposta da permissionária."""

import sys, os
from datetime import date

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import auth
from auth import usuario_logado
from api.client.ouvidoria_client import (
    carregar_ouvidoria_para_permissionaria,
    registrar_resposta_permissionaria,
)
from components import reduz_margem_topo_page

st.set_page_config(page_title="Resposta da Permissionária", layout="wide")
st.markdown('<style>[data-testid="stSidebar"]{width:220px!important;min-width:220px!important;}</style>',
            unsafe_allow_html=True)

reduz_margem_topo_page()
auth.require_auth()
u = usuario_logado()

# ── Ouvidoria selecionada ─────────────────────────────────────────────────────
ouvidoria_id = st.session_state.get("ouvidoria_id")
if not ouvidoria_id:
    st.error("Nenhuma ouvidoria selecionada.")
    st.stop()

dados = carregar_ouvidoria_para_permissionaria(ouvidoria_id)
if not dados:
    st.error("Ouvidoria não encontrada.")
    st.stop()

# ── Cabeçalho ─────────────────────────────────────────────────────────────────
st.title(f"Resposta da Permissionária — Ouvidoria #{dados['id']}")

col1, col2, col3 = st.columns(3)
col1.metric("Status", dados["status"])
col2.metric("Prazo Ouvidoria", dados["prazo"])
if dados["prazo_permissionaria"]:
    col3.metric("Prazo Permissionária", dados["prazo_permissionaria"])

with st.expander("Conteúdo da Ouvidoria", expanded=False):
    st.text(dados["conteudo"])

# ── Respostas anteriores ──────────────────────────────────────────────────────
st.subheader("Respostas anteriores")
if dados["respostas_permissionaria"]:
    for resp in dados["respostas_permissionaria"]:
        with st.expander(f"{resp['data_resposta']} — por {resp['registrado_por_nome']}"):
            st.text(resp["conteudo"])
else:
    st.info("Nenhuma resposta da permissionária registrada.")

# ── Formulário ────────────────────────────────────────────────────────────────
st.subheader("Nova resposta da permissionária")

with st.form("form_resp_perm"):
    conteudo_resp = st.text_area("Conteúdo da resposta *", height=250)
    data_resp = st.date_input("Data da resposta", value=date.today(), format="DD/MM/YYYY")
    submitted = st.form_submit_button("Registrar resposta", type="primary")

if submitted:
    if not conteudo_resp.strip():
        st.error("O conteúdo da resposta é obrigatório.")
    else:
        registrar_resposta_permissionaria(ouvidoria_id, conteudo_resp, data_resp, u["usuario_id"])
        st.success("Resposta da permissionária registrada com sucesso!")
        st.switch_page("pages/01_Ouvidorias.py")
