"""Registrar resposta técnica em uma ouvidoria atribuída."""
import streamlit as st
from datetime import date, datetime
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import auth
from auth import usuario_logado
from database.connection import db_session, get_session
from models import (
    Ouvidoria, StatusOuvidoria, OuvidoriaTecnico,
    RespostaTecnica, Reclamacao, ReclamacaoAuto,
    TipoUsuario, AutoLinha, Categoria, Permissionaria, ParadaAutoLinha,
)
from sqlalchemy import select, exists

st.set_page_config(page_title="Registrar Resposta", page_icon="✍️", layout="wide")
auth.require_auth()

u = usuario_logado()

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"**{u.nome}**")
    st.caption(f"Perfil: {'Gestor' if u.tipo.value == 'gestor' else 'Técnico'}")
    st.divider()
    if st.button("← Voltar", use_container_width=True):
        st.switch_page("pages/01_Ouvidorias.py")
    if st.button("Sair", use_container_width=True):
        auth.fazer_logout()
        st.rerun()

ouvidoria_id = st.session_state.get("ouvidoria_id")
if not ouvidoria_id:
    st.error("Nenhuma ouvidoria selecionada.")
    st.stop()


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
    session = get_session()
    try:
        rows = session.execute(select(ParadaAutoLinha.cidade).distinct()).all()
        return sorted({r[0].strip() for r in rows if r[0]})
    finally:
        session.close()


@st.cache_data(ttl=300)
def carregar_todos_autos():
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


# ── Carrega dados da ouvidoria ───────────────────────────────────────────────
def carregar_dados(oid: int, tecnico_id: int):
    session = get_session()
    try:
        o = session.query(Ouvidoria).filter_by(id=oid).first()
        if not o:
            return None, None, [], None

        atribuicao = session.query(OuvidoriaTecnico).filter_by(
            ouvidoria_id=oid, tecnico_id=tecnico_id
        ).first()

        recs_data = []
        for r in o.reclamacoes:
            autos_info = []
            for ra in r.autos_vinculados:
                auto = session.query(AutoLinha).filter_by(id=ra.auto_id).first()
                if auto:
                    perm_nome = auto.permissionaria.nome if auto.permissionaria else "–"
                    autos_info.append({
                        "id": auto.id,
                        "numero": auto.numero,
                        "cidade_ini": auto.cidade_inicial or "?",
                        "cidade_fim": auto.cidade_final or "?",
                        "permissionaria": perm_nome,
                    })
            recs_data.append({
                "id": r.id,
                "numero_item": r.numero_item,
                "categoria_id": r.categoria_id,
                "categoria": r.categoria.nome if r.categoria else None,
                "local_embarque": r.local_embarque,
                "local_desembarque": r.local_desembarque,
                "descricao": r.descricao,
                "autos": autos_info,
            })

        resposta_existente = session.query(RespostaTecnica).filter_by(
            ouvidoria_id=oid, tecnico_id=tecnico_id
        ).first()

        session.expunge_all()
        return o, atribuicao, recs_data, resposta_existente
    finally:
        session.close()


result = carregar_dados(ouvidoria_id, u.id)
if result[0] is None:
    st.error("Ouvidoria não encontrada.")
    st.stop()

ouvidoria, atribuicao, recs_data, resposta_existente = result

# Verifica se o técnico tem acesso
if u.tipo == TipoUsuario.tecnico and atribuicao is None:
    st.error("Esta ouvidoria não está atribuída a você.")
    st.stop()

st.title(f"✍️ Resposta Técnica – Ouvidoria #{ouvidoria.id}")
st.write(f"**Processo SEI:** {ouvidoria.numero_sei}")
st.write(f"**Status:** {ouvidoria.status.value}")
st.write(f"**Prazo:** {ouvidoria.prazo.strftime('%d/%m/%Y')}")

# Se já respondeu, mostra a resposta
if resposta_existente and atribuicao and atribuicao.respondido:
    st.success("Você já registrou sua resposta técnica para esta ouvidoria.")
    with st.expander("Ver resposta registrada"):
        st.write(f"**Nº SEI Resposta:** {resposta_existente.numero_sei_resposta or '–'}")
        st.write(f"**Data:** {resposta_existente.data_resposta.strftime('%d/%m/%Y')}")
        st.write(f"**Texto:** {resposta_existente.texto_resposta}")
    st.stop()

st.divider()

# ── Inicializa estado com dados existentes ───────────────────────────────────
if "resp_recs_edit" not in st.session_state:
    st.session_state["resp_recs_edit"] = [dict(r) for r in recs_data]
if "resp_autos_checklist" not in st.session_state:
    st.session_state["resp_autos_checklist"] = []
if "resp_rec_alvo_anterior" not in st.session_state:
    st.session_state["resp_rec_alvo_anterior"] = None

categorias = carregar_categorias()
cat_map = {nome: cid for cid, nome in categorias}
cat_nomes = [nome for _, nome in categorias]
cidades = carregar_cidades()
OPCAO_NAO_INFORMADO = "Não informado"

# ── Reclamações editáveis ────────────────────────────────────────────────────
st.subheader("Reclamações")

for i, rec in enumerate(st.session_state["resp_recs_edit"]):
    with st.expander(
        f"Item {rec['numero_item']} – {rec['categoria'] or 'Sem categoria'}",
        expanded=False,
    ):
        # Categoria
        cat_idx = 0
        if rec["categoria"] and rec["categoria"] in cat_nomes:
            cat_idx = cat_nomes.index(rec["categoria"]) + 1
        cat_sel = st.selectbox(
            "Categoria", ["(Sem categoria)"] + cat_nomes,
            index=cat_idx, key=f"resp_cat_{rec['id']}"
        )
        if cat_sel != "(Sem categoria)":
            st.session_state["resp_recs_edit"][i]["categoria"] = cat_sel
            st.session_state["resp_recs_edit"][i]["categoria_id"] = cat_map.get(cat_sel)
        else:
            st.session_state["resp_recs_edit"][i]["categoria"] = None
            st.session_state["resp_recs_edit"][i]["categoria_id"] = None

        # Embarque / Desembarque
        cidades_opcoes = [OPCAO_NAO_INFORMADO] + cidades
        emb_val = rec["local_embarque"] or OPCAO_NAO_INFORMADO
        emb_idx = cidades_opcoes.index(emb_val) if emb_val in cidades_opcoes else 0
        emb_sel = st.selectbox(
            "Local de Embarque", cidades_opcoes,
            index=emb_idx, key=f"resp_emb_{rec['id']}"
        )
        st.session_state["resp_recs_edit"][i]["local_embarque"] = None if emb_sel == OPCAO_NAO_INFORMADO else emb_sel

        des_val = rec["local_desembarque"] or OPCAO_NAO_INFORMADO
        des_idx = cidades_opcoes.index(des_val) if des_val in cidades_opcoes else 0
        des_sel = st.selectbox(
            "Local de Desembarque", cidades_opcoes,
            index=des_idx, key=f"resp_des_{rec['id']}"
        )
        st.session_state["resp_recs_edit"][i]["local_desembarque"] = None if des_sel == OPCAO_NAO_INFORMADO else des_sel

        # Descrição
        desc = st.text_area("Descrição", value=rec["descricao"] or "", key=f"resp_desc_{rec['id']}", height=100)
        st.session_state["resp_recs_edit"][i]["descricao"] = desc or None

        # Autos vinculados
        st.markdown("**Autos vinculados:**")
        if rec["autos"]:
            for a in rec["autos"]:
                col_auto, col_rem = st.columns([5, 1])
                col_auto.write(f"- {a['numero']} ({a['cidade_ini']} até {a['cidade_fim']}) - {a['permissionaria']}")
                if col_rem.button("✕", key=f"rem_auto_{rec['id']}_{a['id']}"):
                    st.session_state["resp_recs_edit"][i]["autos"] = [
                        x for x in rec["autos"] if x["id"] != a["id"]
                    ]
                    st.rerun()
        else:
            st.write("Nenhum auto vinculado")

# ── Vincular Autos à Reclamação ──────────────────────────────────────────────
if st.session_state["resp_recs_edit"]:
    st.divider()
    st.subheader("Vincular Autos à Reclamação")

    rec_labels = [
        f"Item {r['numero_item']} – {r['categoria'] or 'Sem categoria'}"
        for r in st.session_state["resp_recs_edit"]
    ]
    rec_sel_label = st.selectbox("Reclamação alvo", rec_labels, key="resp_rec_alvo_sel")
    rec_idx = rec_labels.index(rec_sel_label)

    # Detecta troca de reclamação alvo
    if st.session_state["resp_rec_alvo_anterior"] != rec_sel_label:
        for a in st.session_state["resp_autos_checklist"]:
            st.session_state.pop(f"resp_chk_{a['id']}", None)
        st.session_state["resp_autos_checklist"] = []
        st.session_state["resp_rec_alvo_anterior"] = rec_sel_label

    perms = carregar_permissionarias()
    todos_autos = carregar_todos_autos()
    perm_map = {nome: pid for pid, nome in perms}

    col_modo1, col_modo2, col_modo3 = st.columns(3)

    # Busca por trecho
    with col_modo1:
        st.markdown("**Por Trecho**")
        cidade_orig_sel = st.selectbox(
            "Cidade A", [OPCAO_NAO_INFORMADO] + cidades, key="resp_trecho_orig"
        )
        cidade_dest_sel = st.selectbox(
            "Cidade B", [OPCAO_NAO_INFORMADO] + cidades, key="resp_trecho_dest"
        )
        if st.button("🔍 Buscar por trecho", use_container_width=True, key="resp_btn_trecho"):
            orig = None if cidade_orig_sel == OPCAO_NAO_INFORMADO else cidade_orig_sel
            dest = None if cidade_dest_sel == OPCAO_NAO_INFORMADO else cidade_dest_sel
            if orig or dest:
                encontrados = buscar_autos_por_trecho(orig or "", dest or "")
                ids_existentes = {a["id"] for a in st.session_state["resp_autos_checklist"]}
                adicionados = 0
                for aid, anum, aori, adest in encontrados:
                    if aid not in ids_existentes:
                        st.session_state["resp_autos_checklist"].append(
                            {"id": aid, "numero": anum, "cidade_ini": aori, "cidade_fim": adest}
                        )
                        ids_existentes.add(aid)
                        adicionados += 1
                st.success(f"{adicionados} autos adicionados ({len(encontrados)} encontrados).")
                st.rerun()
            else:
                st.warning("Selecione ao menos uma cidade.")

    # Busca por permissionária
    with col_modo2:
        st.markdown("**Por Permissionária**")
        perm_nome_sel = st.selectbox(
            "Permissionária", [n for _, n in perms], key="resp_perm_sel"
        )
        if st.button("🔍 Buscar por permissionária", use_container_width=True, key="resp_btn_perm"):
            perm_id = perm_map[perm_nome_sel]
            encontrados = buscar_autos_por_permissionaria(perm_id)
            ids_existentes = {a["id"] for a in st.session_state["resp_autos_checklist"]}
            adicionados = 0
            for aid, anum, aori, adest in encontrados:
                if aid not in ids_existentes:
                    st.session_state["resp_autos_checklist"].append(
                        {"id": aid, "numero": anum, "cidade_ini": aori, "cidade_fim": adest}
                    )
                    ids_existentes.add(aid)
                    adicionados += 1
            st.success(f"{adicionados} autos adicionados ({len(encontrados)} encontrados).")
            st.rerun()

    # Busca por número
    with col_modo3:
        st.markdown("**Por Número**")
        num_opcoes = [a[1] for a in todos_autos]
        num_sel = st.selectbox("Número do Auto", num_opcoes, key="resp_num_sel")
        if st.button("➕ Adicionar", use_container_width=True, key="resp_btn_num"):
            auto_row = next((a for a in todos_autos if a[1] == num_sel), None)
            if auto_row:
                aid, anum, aori, adest = auto_row
                ids_existentes = {a["id"] for a in st.session_state["resp_autos_checklist"]}
                if aid not in ids_existentes:
                    st.session_state["resp_autos_checklist"].append(
                        {"id": aid, "numero": anum, "cidade_ini": aori, "cidade_fim": adest}
                    )
                    st.success(f"Auto {anum} adicionado.")
                    st.rerun()
                else:
                    st.info("Auto já está na lista.")

    # Checklist acumulada
    if st.session_state["resp_autos_checklist"]:
        st.markdown(f"**Lista de Autos ({len(st.session_state['resp_autos_checklist'])} encontrados) — marque os que deseja vincular:**")

        ids_ja_salvos = {a["id"] for a in st.session_state["resp_recs_edit"][rec_idx]["autos"]}

        for auto in st.session_state["resp_autos_checklist"]:
            ja_salvo = auto["id"] in ids_ja_salvos
            label = f"**{auto['numero']}** – {auto['cidade_ini']} → {auto['cidade_fim']}"
            if ja_salvo:
                st.checkbox(label + "  ✅ *já vinculado*", key=f"resp_chk_{auto['id']}", value=True, disabled=True)
            else:
                st.checkbox(label, key=f"resp_chk_{auto['id']}", value=True)

        col_btn1, col_btn2 = st.columns([2, 1])
        with col_btn1:
            if st.button("✔ Registrar Autos Selecionados", type="primary", use_container_width=True, key="resp_reg_autos"):
                ids_existentes = {a["id"] for a in st.session_state["resp_recs_edit"][rec_idx]["autos"]}
                novos = [
                    a for a in st.session_state["resp_autos_checklist"]
                    if st.session_state.get(f"resp_chk_{a['id']}", True) and a["id"] not in ids_existentes
                ]
                # Busca permissionária para cada auto
                session = get_session()
                try:
                    for a in novos:
                        auto_db = session.query(AutoLinha).filter_by(id=a["id"]).first()
                        perm_nome = auto_db.permissionaria.nome if auto_db and auto_db.permissionaria else "–"
                        st.session_state["resp_recs_edit"][rec_idx]["autos"].append({
                            "id": a["id"],
                            "numero": a["numero"],
                            "cidade_ini": a["cidade_ini"],
                            "cidade_fim": a["cidade_fim"],
                            "permissionaria": perm_nome,
                        })
                finally:
                    session.close()
                for a in st.session_state["resp_autos_checklist"]:
                    st.session_state.pop(f"resp_chk_{a['id']}", None)
                st.session_state["resp_autos_checklist"] = []
                st.success(f"{len(novos)} autos vinculados à reclamação.")
                st.rerun()
        with col_btn2:
            if st.button("🗑 Limpar lista", use_container_width=True, key="resp_limpar"):
                for a in st.session_state["resp_autos_checklist"]:
                    st.session_state.pop(f"resp_chk_{a['id']}", None)
                st.session_state["resp_autos_checklist"] = []
                st.rerun()
    else:
        st.info("Use as buscas acima para encontrar e acumular autos na lista.")

# ── Registrar Resposta ───────────────────────────────────────────────────────
st.divider()
st.subheader("Registrar Resposta")

with st.form("form_resposta"):
    num_sei_resp = st.text_input("Nº do Documento SEI (resposta)", placeholder="Ex.: 001.002/2025-01")
    texto = st.text_area("Texto da resposta técnica *", height=200)
    data_resp = st.date_input("Data da resposta", value=date.today(), disabled=True)
    enviar = st.form_submit_button("📤 Enviar Resposta", type="primary")

if enviar:
    if not texto.strip():
        st.error("O texto da resposta é obrigatório.")
    else:
        try:
            with db_session() as session:
                # Salva alterações nas reclamações
                for rec_edit in st.session_state["resp_recs_edit"]:
                    rec_db = session.query(Reclamacao).filter_by(id=rec_edit["id"]).first()
                    if not rec_db:
                        continue
                    rec_db.categoria_id = rec_edit["categoria_id"]
                    rec_db.local_embarque = rec_edit["local_embarque"]
                    rec_db.local_desembarque = rec_edit["local_desembarque"]
                    rec_db.descricao = rec_edit["descricao"]

                    # Atualiza autos vinculados
                    session.query(ReclamacaoAuto).filter_by(reclamacao_id=rec_db.id).delete()
                    session.flush()

                    n_autos = len(rec_edit["autos"])
                    pontuacao = round(1.0 / n_autos, 4) if n_autos > 0 else 0
                    for a in rec_edit["autos"]:
                        session.add(ReclamacaoAuto(
                            reclamacao_id=rec_db.id,
                            auto_id=a["id"],
                            pontuacao=pontuacao,
                        ))

                # Registra resposta
                resp = RespostaTecnica(
                    ouvidoria_id=ouvidoria_id,
                    tecnico_id=u.id,
                    numero_sei_resposta=num_sei_resp.strip() or None,
                    data_resposta=date.today(),
                    texto_resposta=texto.strip(),
                )
                session.add(resp)

                # Atualiza atribuição
                at = session.query(OuvidoriaTecnico).filter_by(
                    ouvidoria_id=ouvidoria_id, tecnico_id=u.id
                ).first()
                if at:
                    at.respondido = True
                    at.respondido_em = datetime.now()

                # Verifica se todos os técnicos responderam
                todas = session.query(OuvidoriaTecnico).filter_by(ouvidoria_id=ouvidoria_id).all()
                todos_responderam = all(a.respondido for a in todas)

                if todos_responderam:
                    o_db = session.query(Ouvidoria).filter_by(id=ouvidoria_id).first()
                    if o_db and o_db.status == StatusOuvidoria.EM_ANALISE_TECNICA:
                        o_db.status = StatusOuvidoria.RETORNO_TECNICO

            # Limpa estado
            st.session_state.pop("resp_recs_edit", None)
            st.session_state.pop("resp_autos_checklist", None)
            st.session_state.pop("resp_rec_alvo_anterior", None)

            msg = "Resposta registrada com sucesso!"
            if todos_responderam:
                msg += " Status da ouvidoria atualizado para 'Retorno técnico'."
            st.success(msg)
            st.switch_page("pages/01_Ouvidorias.py")
        except Exception as e:
            st.error(f"Erro ao registrar resposta: {e}")
