"""Página para registrar resposta da permissionária."""

from datetime import date

import streamlit as st
from models import Usuario
from repositories.ouvidoria_write_repo import registrar_resposta_permissionaria
from utils import carregar_ouvidoria_para_permissionaria

st.set_page_config(page_title="Resposta da Permissionária", layout="wide")
st.markdown('<style>[data-testid="stSidebar"]{width:220px!important;min-width:220px!important;}</style>', 
            unsafe_allow_html=True)

# ── Autenticação ──────────────────────────────────────────────────────────
if "usuario" not in st.session_state:
    st.warning("Faça login para acessar esta página.")
    st.stop()

u: Usuario = st.session_state["usuario"]

# ── Ouvidoria selecionada ─────────────────────────────────────────────────
ouvidoria_id = st.session_state.get("ouvidoria_id")
if not ouvidoria_id:
    st.error("Nenhuma ouvidoria selecionada.")
    st.stop()


# ── Carregar dados ────────────────────────────────────────────────────────
dados = carregar_ouvidoria_para_permissionaria(ouvidoria_id)
if not dados:
    st.error("Ouvidoria não encontrada.")
    st.stop()

# ── Cabeçalho ─────────────────────────────────────────────────────────────
st.title(f"Resposta da Permissionária — Ouvidoria #{dados['id']}")

col1, col2, col3 = st.columns(3)
col1.metric("Status", dados["status"])
col2.metric("Prazo Ouvidoria", dados["prazo"].strftime("%d/%m/%Y"))
if dados["prazo_permissionaria"]:
    col3.metric("Prazo Permissionária", dados["prazo_permissionaria"].strftime("%d/%m/%Y"))

with st.expander("Conteúdo da Ouvidoria", expanded=False):
    st.text(dados["conteudo"])

# ── Respostas anteriores ──────────────────────────────────────────────────
st.subheader("Respostas anteriores")
if dados["respostas_permissionaria"]:
    for resp in dados["respostas_permissionaria"]:
        with st.expander(
            f"{resp['data_resposta'].strftime('%d/%m/%Y')} — por {resp['registrado_por_nome']}"
        ):
            st.text(resp["conteudo"])
else:
    st.info("Nenhuma resposta da permissionária registrada.")

# ── Formulário ────────────────────────────────────────────────────────────
st.subheader("Nova resposta da permissionária")

with st.form("form_resp_perm"):
    conteudo_resp = st.text_area("Conteúdo da resposta *", height=250)
    data_resp = st.date_input("Data da resposta", value=date.today())
    submitted = st.form_submit_button("Registrar resposta", type="primary")

if submitted:
    if not conteudo_resp.strip():
        st.error("O conteúdo da resposta é obrigatório.")
    else:
        registrar_resposta_permissionaria(ouvidoria_id, conteudo_resp, data_resp, u.id)
        st.success("Resposta da permissionária registrada com sucesso!")
        carregar_ouvidoria_para_permissionaria.clear()
        st.rerun()
