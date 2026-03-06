"""Criar nova ouvidoria com reclamações itemizadas."""
import streamlit as st
from datetime import date, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import auth
from auth import usuario_logado
from database.connection import db_session, get_session
from models import (
    Ouvidoria, StatusOuvidoria, Reclamacao, ReclamacaoAuto,
    AutoLinha, Categoria, Permissionaria, ParadaAutoLinha,
)
from sqlalchemy import select, exists

st.set_page_config(page_title="Nova Ouvidoria", page_icon="➕", layout="wide")
auth.require_gestor()

u = usuario_logado()

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"**{u.nome}**")
    st.caption("Gestor")
    st.divider()
    if st.button("← Voltar para Ouvidorias", use_container_width=True):
        st.switch_page("pages/01_Ouvidorias.py")
    if st.button("Sair", use_container_width=True):
        auth.fazer_logout()
        st.rerun()

# ── Dados auxiliares ─────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def carregar_categorias():
    session = get_session()
    try:
        cats = session.query(Categoria).filter_by(ativo=True).order_by(Categoria.nome).all()
        return [(c.id, c.nome) for c in cats]
    finally:
        session.close()


@st.cache_data(ttl=300)
def carregar_cidades():
    """Retorna lista ordenada de todas as cidades únicas de paradas_auto_linha."""
    session = get_session()
    try:
        rows = session.execute(select(ParadaAutoLinha.cidade).distinct()).all()
        return sorted({r[0].strip() for r in rows if r[0]})
    finally:
        session.close()


@st.cache_data(ttl=300)
def carregar_todos_autos():
    """Retorna todos os autos: (id, numero, cidade_ini, cidade_fim)."""
    session = get_session()
    try:
        autos = session.query(AutoLinha).order_by(AutoLinha.numero).all()
        return [(a.id, a.numero, a.cidade_inicial or "", a.cidade_final or "") for a in autos]
    finally:
        session.close()


@st.cache_data(ttl=300)
def carregar_permissionarias():
    session = get_session()
    try:
        perms = session.query(Permissionaria).order_by(Permissionaria.nome).all()
        return [(p.id, p.nome) for p in perms]
    finally:
        session.close()


def buscar_autos_por_trecho(cidade_a: str, cidade_b: str):
    """Retorna autos que têm paradas em AMBAS as cidades informadas."""
    session = get_session()
    try:
        q = session.query(AutoLinha)
        if cidade_a:
            q = q.filter(
                exists().where(
                    (ParadaAutoLinha.auto_id == AutoLinha.id) &
                    (ParadaAutoLinha.cidade == cidade_a)
                )
            )
        if cidade_b:
            q = q.filter(
                exists().where(
                    (ParadaAutoLinha.auto_id == AutoLinha.id) &
                    (ParadaAutoLinha.cidade == cidade_b)
                )
            )
        autos = q.order_by(AutoLinha.numero).all()
        return [(a.id, a.numero, a.cidade_inicial or "", a.cidade_final or "") for a in autos]
    finally:
        session.close()


def buscar_autos_por_permissionaria(perm_id: int):
    session = get_session()
    try:
        autos = session.query(AutoLinha).filter_by(permissionaria_id=perm_id).order_by(AutoLinha.numero).all()
        return [(a.id, a.numero, a.cidade_inicial or "", a.cidade_final or "") for a in autos]
    finally:
        session.close()


# ── Estado ────────────────────────────────────────────────────────────────────
if "reclamacoes_draft" not in st.session_state:
    st.session_state["reclamacoes_draft"] = []
if "autos_checklist" not in st.session_state:
    st.session_state["autos_checklist"] = []  # [{id, numero, cidade_ini, cidade_fim}]
if "rec_alvo_anterior" not in st.session_state:
    st.session_state["rec_alvo_anterior"] = None

# ── Cabeçalho da Ouvidoria ────────────────────────────────────────────────────
st.title("➕ Nova Ouvidoria")

col1, col2 = st.columns([2, 1])
with col1:
    numero_sei = st.text_input("Nº do Processo SEI *", placeholder="Ex.: 001.001/2025-00")
with col2:
    prazo = st.date_input("Prazo de resposta *", value=date.today() + timedelta(days=15))

st.divider()

# ── Reclamações ───────────────────────────────────────────────────────────────
st.subheader("Reclamações")

categorias = carregar_categorias()
cat_map = {nome: cid for cid, nome in categorias}
cat_nomes = [nome for _, nome in categorias]
cidades = carregar_cidades()
OPCAO_NAO_INFORMADO = "Não informado"

# Exibe reclamações já adicionadas
if st.session_state["reclamacoes_draft"]:
    for i, rec in enumerate(st.session_state["reclamacoes_draft"]):
        label_embarque = rec["local_embarque"] or OPCAO_NAO_INFORMADO
        label_desembarque = rec["local_desembarque"] or OPCAO_NAO_INFORMADO
        with st.expander(
            f"Item {rec['numero_item']} – {rec['categoria_nome'] or 'Sem categoria'} "
            f"({label_embarque} → {label_desembarque})",
            expanded=False,
        ):
            st.write(f"**Embarque:** {label_embarque}")
            st.write(f"**Desembarque:** {label_desembarque}")
            st.write(f"**Descrição:** {rec['descricao'] or '–'}")
            if rec["autos"]:
                st.write(
                    f"**Autos vinculados ({len(rec['autos'])}):** "
                    + ", ".join(a["numero"] for a in rec["autos"])
                )
            else:
                st.write("**Autos vinculados:** Nenhum")
            if st.button("🗑 Remover reclamação", key=f"rem_{i}"):
                st.session_state["reclamacoes_draft"].pop(i)
                st.rerun()

# ── Formulário: adicionar reclamação ─────────────────────────────────────────
st.markdown("#### Adicionar Reclamação")

with st.form("form_reclamacao", clear_on_submit=True):
    col_a, col_b = st.columns(2)
    with col_a:
        cat_sel = st.selectbox("Categoria *", cat_nomes if cat_nomes else ["(Nenhuma categoria cadastrada)"])
        emb_sel = st.selectbox("Local de Embarque", [OPCAO_NAO_INFORMADO] + cidades)
        desemb_sel = st.selectbox("Local de Desembarque", [OPCAO_NAO_INFORMADO] + cidades)
    with col_b:
        descricao = st.text_area("Descrição", height=150)

    adicionar_rec = st.form_submit_button("✔ Adicionar Reclamação", type="primary")

    if adicionar_rec:
        if not cat_nomes or cat_sel == "(Nenhuma categoria cadastrada)":
            st.error("Cadastre ao menos uma categoria no Admin antes de criar reclamações.")
        elif cat_sel not in cat_map:
            st.error("Selecione uma categoria válida.")
        else:
            proximo_item = len(st.session_state["reclamacoes_draft"]) + 1
            nova_rec = {
                "numero_item": proximo_item,
                "categoria_id": cat_map[cat_sel],
                "categoria_nome": cat_sel,
                "local_embarque": None if emb_sel == OPCAO_NAO_INFORMADO else emb_sel,
                "local_desembarque": None if desemb_sel == OPCAO_NAO_INFORMADO else desemb_sel,
                "descricao": descricao or None,
                "autos": [],
            }
            st.session_state["reclamacoes_draft"].append(nova_rec)
            st.rerun()

# ── Vincular Autos à Reclamação ───────────────────────────────────────────────
if st.session_state["reclamacoes_draft"]:
    st.divider()
    st.subheader("Vincular Autos à Reclamação")

    rec_labels = [
        f"Item {r['numero_item']} – {r['categoria_nome'] or 'Sem categoria'}"
        for r in st.session_state["reclamacoes_draft"]
    ]
    rec_sel_label = st.selectbox("Reclamação alvo", rec_labels, key="rec_alvo_sel")
    rec_idx = rec_labels.index(rec_sel_label)

    # Detecta troca de reclamação alvo e limpa a checklist
    if st.session_state["rec_alvo_anterior"] != rec_sel_label:
        for a in st.session_state["autos_checklist"]:
            st.session_state.pop(f"chk_{a['id']}", None)
        st.session_state["autos_checklist"] = []
        st.session_state["rec_alvo_anterior"] = rec_sel_label

    perms = carregar_permissionarias()
    todos_autos = carregar_todos_autos()
    perm_map = {nome: pid for pid, nome in perms}

    col_modo1, col_modo2, col_modo3 = st.columns(3)

    # ── Busca por trecho ──────────────────────────────────────────────────────
    with col_modo1:
        st.markdown("**Por Trecho**")
        cidade_orig_sel = st.selectbox(
            "Cidade de Origem", [OPCAO_NAO_INFORMADO] + cidades, key="trecho_orig"
        )
        cidade_dest_sel = st.selectbox(
            "Cidade de Destino", [OPCAO_NAO_INFORMADO] + cidades, key="trecho_dest"
        )
        if st.button("🔍 Buscar por trecho", use_container_width=True):
            orig = None if cidade_orig_sel == OPCAO_NAO_INFORMADO else cidade_orig_sel
            dest = None if cidade_dest_sel == OPCAO_NAO_INFORMADO else cidade_dest_sel
            if orig or dest:
                encontrados = buscar_autos_por_trecho(orig or "", dest or "")
                print(encontrados)
                ids_existentes = {a["id"] for a in st.session_state["autos_checklist"]}
                adicionados = 0
                for aid, anum, aori, adest in encontrados:
                    if aid not in ids_existentes:
                        st.session_state["autos_checklist"].append(
                            {"id": aid, "numero": anum, "cidade_ini": aori, "cidade_fim": adest}
                        )
                        ids_existentes.add(aid)
                        adicionados += 1
                st.success(f"{adicionados} autos adicionados à lista ({len(encontrados)} encontrados).")
                st.rerun()
            else:
                st.warning("Selecione ao menos origem ou destino.")

    # ── Busca por permissionária ──────────────────────────────────────────────
    with col_modo2:
        st.markdown("**Por Permissionária**")
        perm_nome_sel = st.selectbox(
            "Permissionária", [n for _, n in perms], key="perm_sel"
        )
        if st.button("🔍 Buscar por permissionária", use_container_width=True):
            perm_id = perm_map[perm_nome_sel]
            encontrados = buscar_autos_por_permissionaria(perm_id)
            ids_existentes = {a["id"] for a in st.session_state["autos_checklist"]}
            adicionados = 0
            for aid, anum, aori, adest in encontrados:
                if aid not in ids_existentes:
                    st.session_state["autos_checklist"].append(
                        {"id": aid, "numero": anum, "cidade_ini": aori, "cidade_fim": adest}
                    )
                    ids_existentes.add(aid)
                    adicionados += 1
            st.success(f"{adicionados} autos adicionados à lista ({len(encontrados)} encontrados).")
            st.rerun()

    # ── Busca por número ──────────────────────────────────────────────────────
    with col_modo3:
        st.markdown("**Por Número**")
        num_opcoes = [a[1] for a in todos_autos]
        num_sel = st.selectbox("Número do Auto", num_opcoes, key="num_sel")
        if st.button("➕ Adicionar à lista", use_container_width=True):
            auto_row = next((a for a in todos_autos if a[1] == num_sel), None)
            if auto_row:
                aid, anum, aori, adest = auto_row
                ids_existentes = {a["id"] for a in st.session_state["autos_checklist"]}
                if aid not in ids_existentes:
                    st.session_state["autos_checklist"].append(
                        {"id": aid, "numero": anum, "cidade_ini": aori, "cidade_fim": adest}
                    )
                    st.success(f"Auto {anum} adicionado à lista.")
                    st.rerun()
                else:
                    st.info("Auto já está na lista.")

    # ── Checklist acumulada ───────────────────────────────────────────────────
    if st.session_state["autos_checklist"]:
        st.markdown(f"**Lista de Autos ({len(st.session_state['autos_checklist'])} encontrados) — marque os que deseja vincular:**")

        # Autos já salvos nessa reclamação
        ids_ja_salvos = {a["id"] for a in st.session_state["reclamacoes_draft"][rec_idx]["autos"]}

        for auto in st.session_state["autos_checklist"]:
            ja_salvo = auto["id"] in ids_ja_salvos
            label = f"**{auto['numero']}** – {auto['cidade_ini']} → {auto['cidade_fim']}"
            if ja_salvo:
                st.checkbox(label + "  ✅ *já vinculado*", key=f"chk_{auto['id']}", value=True, disabled=True)
            else:
                st.checkbox(label, key=f"chk_{auto['id']}", value=True)

        col_btn1, col_btn2 = st.columns([2, 1])
        with col_btn1:
            if st.button("✔ Registrar Autos Selecionados", type="primary", use_container_width=True):
                ids_existentes = {a["id"] for a in st.session_state["reclamacoes_draft"][rec_idx]["autos"]}
                novos = [
                    a for a in st.session_state["autos_checklist"]
                    if st.session_state.get(f"chk_{a['id']}", True) and a["id"] not in ids_existentes
                ]
                for a in novos:
                    st.session_state["reclamacoes_draft"][rec_idx]["autos"].append(
                        {"id": a["id"], "numero": a["numero"]}
                    )
                # Limpa checklist e chaves
                for a in st.session_state["autos_checklist"]:
                    st.session_state.pop(f"chk_{a['id']}", None)
                st.session_state["autos_checklist"] = []
                st.success(f"{len(novos)} autos vinculados à reclamação.")
                st.rerun()
        with col_btn2:
            if st.button("🗑 Limpar lista", use_container_width=True):
                for a in st.session_state["autos_checklist"]:
                    st.session_state.pop(f"chk_{a['id']}", None)
                st.session_state["autos_checklist"] = []
                st.rerun()
    else:
        st.info("Use as buscas acima para encontrar e acumular autos na lista.")

# ── Salvar ouvidoria ──────────────────────────────────────────────────────────
st.divider()
if st.button("💾 Salvar Ouvidoria", type="primary", use_container_width=True):
    if not numero_sei.strip():
        st.error("Informe o número do processo SEI.")
    elif not st.session_state["reclamacoes_draft"]:
        st.warning("Adicione ao menos uma reclamação antes de salvar.")
    else:
        try:
            with db_session() as session:
                ouvidoria = Ouvidoria(
                    numero_sei=numero_sei.strip(),
                    prazo=prazo,
                    status=StatusOuvidoria.AGUARDANDO_ACOES,
                    criado_por_id=u.id,
                )
                session.add(ouvidoria)
                session.flush()

                for rec_draft in st.session_state["reclamacoes_draft"]:
                    rec = Reclamacao(
                        ouvidoria_id=ouvidoria.id,
                        numero_item=rec_draft["numero_item"],
                        categoria_id=rec_draft["categoria_id"],
                        local_embarque=rec_draft["local_embarque"],
                        local_desembarque=rec_draft["local_desembarque"],
                        descricao=rec_draft["descricao"],
                    )
                    session.add(rec)
                    session.flush()

                    autos_rec = rec_draft["autos"]
                    n = len(autos_rec)
                    pontuacao = round(1.0 / n, 4) if n > 0 else 0
                    for a in autos_rec:
                        session.add(ReclamacaoAuto(
                            reclamacao_id=rec.id,
                            auto_id=a["id"],
                            pontuacao=pontuacao,
                        ))

            st.session_state["reclamacoes_draft"] = []
            st.session_state["autos_checklist"] = []
            st.session_state["rec_alvo_anterior"] = None
            st.success("Ouvidoria salva com sucesso!")
            st.switch_page("pages/01_Ouvidorias.py")
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")
