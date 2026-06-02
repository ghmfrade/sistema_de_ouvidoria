import streamlit as st

def reduz_margem_side_bar():
    st.markdown("""
    <style>
    section[data-testid="stSidebar"] p {
        margin-bottom: 0.2rem;
    }

    section[data-testid="stSidebar"] hr {
        margin-top: 0.2rem;
        margin-bottom: 0.2rem;
    }

    section[data-testid="stSidebar"] .stTextInput {
        margin-top: -0.3rem;
    }
    </style>
    """, unsafe_allow_html=True)


def reduz_margem_topo_page():
    st.markdown("""
    <style>
    section[data-testid="stSidebar"] {
        width:220px!important;
        min-width:220px!important;
    }

    div.block-container {
        padding-top:2.6rem!important;
    }
    </style>
    """, unsafe_allow_html=True)


def reduz_gap_elementos_body():
    st.markdown("""
    <style>
    section[data-testid="stMain"] div[data-testid="stVerticalBlock"] {
        gap: 0.4rem;
    }
    </style>
    """, unsafe_allow_html=True)


def reduz_margem_divider_body():
    st.markdown("""
    <style>
    section[data-testid="stMain"] div[data-testid="stDivider"] {
        margin: 0.2rem 0;
    }
    </style>
    """, unsafe_allow_html=True)


def reduz_estilo_botoes_body():
    st.markdown("""
    <style>
    section[data-testid="stMain"] div.stButton {
        margin: 0rem;
    }

    section[data-testid="stMain"] div.stButton > button {
        padding-top: 0.15rem;
        padding-bottom: 0.15rem;
    }
    </style>
    """, unsafe_allow_html=True)


def reduz_margem_markdown_body():
    st.markdown("""
    <style>
    section[data-testid="stMain"] div[data-testid="stMarkdownContainer"] p {
        margin-bottom: 0.2rem;
    }
    </style>
    """, unsafe_allow_html=True)


def reduz_margem_headers_body():
    st.markdown("""
    <style>
    section[data-testid="stMain"] h1,
    section[data-testid="stMain"] h2,
    section[data-testid="stMain"] h3,
    section[data-testid="stMain"] h4 {
        margin-top: 0.3rem;
        margin-bottom: 0.3rem;
    }
    </style>
    """, unsafe_allow_html=True)


def esconde_indice_table():
    st.markdown("""
    <style>
    [data-testid="stTable"] thead th:first-child,
    [data-testid="stTable"] tbody th {
        width: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
        border: none !important;
        overflow: hidden !important;
        visibility: hidden !important;
        font-size: 0 !important;
    }
    </style>
    """, unsafe_allow_html=True)


def estiliza_tabela_usuarios():
    st.markdown("""
    <style>
    /* Centralizar coluna ID */
    [data-testid="stTable"] tbody td:first-child {
        text-align: center !important;
        font-weight: 600 !important;
    }

    /* Estilizar célula ID como botão */
    [data-testid="stTable"] tbody td:first-child {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        padding: 0.6rem 0.8rem !important;
        border-radius: 0.4rem !important;
        font-size: 0.9rem !important;
    }

    /* Melhorar tabela em geral */
    [data-testid="stTable"] {
        border-collapse: collapse !important;
    }

    [data-testid="stTable"] thead {
        background-color: #262626 !important;
        font-weight: 600 !important;
    }

    [data-testid="stTable"] thead th {
        padding: 0.8rem !important;
        border-bottom: 2px solid #404040 !important;
        color: #e0e0e0 !important;
        text-align: center !important;
    }

    /* Header da coluna de índice (escondida) */
    [data-testid="stTable"] thead th:first-child {
        background-color: #262626 !important;
        border-bottom: 2px solid #404040 !important;
    }

    [data-testid="stTable"] tbody td {
        padding: 0.8rem !important;
        border-bottom: 1px solid #f0f0f0 !important;
    }

    [data-testid="stTable"] tbody tr:hover {
        background-color: #2a2a2a !important;
    }
    </style>
    """, unsafe_allow_html=True)