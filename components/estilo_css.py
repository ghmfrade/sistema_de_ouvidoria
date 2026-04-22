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