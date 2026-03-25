"""Registrar resposta técnica em uma ouvidoria atribuída."""

import os
import sys
from datetime import date, datetime

import streamlit as st
from sqlalchemy import exists
from sqlalchemy.orm import aliased

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import auth
from auth import usuario_logado
from database.connection import db_session, get_session
from models import (
    AnexoOuvidoria,
    AutoLinha,
    Municipio,
    Ouvidoria,
    OuvidoriaTecnico,
    ParadaAutoLinha,
    Permissionaria,
    Reclamacao,
    ReclamacaoAuto,
    RespostaPermissionaria,
    RespostaTecnica,
    StatusOuvidoria,
    TipoServico,
    TipoUsuario,
)
from utils.cache import carregar_categorias, carregar_municipios, carregar_subcategorias

st.set_page_config(page_title="Registrar Resposta", page_icon="✍️", layout="wide")
st.markdown('<style>[data-testid="stSidebar"]{width:220px!important;min-width:220px!important;}</style>', unsafe_allow_html=True)
auth.require_auth()

u = usuario_logado()

UPLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")

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
OPCAO_TODAS = "Todas"
OPCAO_QUALQUER = "Qualquer"
OPCAO_NAO_INFORMADO = "Não informado"


@st.cache_data(ttl=300)
def carregar_cidades_por_tipo(tipo_servico: str):
    """Retorna cidades de origem via nome IBGE (municipio.nome), filtradas pelo tipo de serviço.
    Fretamento: todos os municípios SP. Regular: apenas cidades com paradas ativas."""
    session = get_session()
    try:
        if "Fretamento" in tipo_servico:
            rows = session.query(Municipio.nome).filter_by(estado="SP").order_by(Municipio.nome).all()
            return [r[0] for r in rows]
        q = (
            session.query(Municipio.nome)
            .join(ParadaAutoLinha, ParadaAutoLinha.municipio_id == Municipio.id)
            .join(AutoLinha, AutoLinha.id == ParadaAutoLinha.auto_id)
            .filter(AutoLinha.tipo == tipo_servico, AutoLinha.ativo == True)
        )
        return sorted({r[0] for r in q.distinct().all() if r[0]})
    finally:
        session.close()


@st.cache_data(ttl=300)
def carregar_cidades(tipo_servico: str, perm_id: int | None = None, regiao: str | None = None):
    """Retorna cidades via nome IBGE para busca por trecho, com filtros opcionais."""
    session = get_session()
    try:
        q = (
            session.query(Municipio.nome)
            .join(ParadaAutoLinha, ParadaAutoLinha.municipio_id == Municipio.id)
            .join(AutoLinha, AutoLinha.id == ParadaAutoLinha.auto_id)
            .filter(AutoLinha.tipo == tipo_servico, AutoLinha.ativo == True)
        )
        if perm_id is not None:
            q = q.filter(AutoLinha.permissionaria_id == perm_id)
        if regiao is not None:
            q = q.filter(AutoLinha.regiao_metropolitana == regiao)
        return sorted({r[0] for r in q.distinct().all() if r[0]})
    finally:
        session.close()


def carregar_cidades_destino(tipo_servico: str, nome_origem: str,
                             perm_id: int | None = None, regiao: str | None = None):
    """Retorna cidades alcançáveis a partir da origem via linhas do tipo especificado."""
    session = get_session()
    try:
        if "Fretamento" in tipo_servico:
            rows = session.query(Municipio.nome).filter_by(estado="SP").order_by(Municipio.nome).all()
            return [r[0] for r in rows if r[0] != nome_origem]

        mun_id_orig = session.query(Municipio.id).filter_by(nome=nome_origem).scalar()
        if not mun_id_orig:
            return []

        ParadaOrig = aliased(ParadaAutoLinha)
        q = (
            session.query(Municipio.nome)
            .join(ParadaAutoLinha, ParadaAutoLinha.municipio_id == Municipio.id)
            .join(AutoLinha, AutoLinha.id == ParadaAutoLinha.auto_id)
            .filter(
                AutoLinha.tipo == tipo_servico,
                AutoLinha.ativo == True,
                Municipio.id != mun_id_orig,
                exists().where(
                    (ParadaOrig.auto_id == AutoLinha.id) &
                    (ParadaOrig.municipio_id == mun_id_orig)
                ),
            )
        )
        if perm_id is not None:
            q = q.filter(AutoLinha.permissionaria_id == perm_id)
        if regiao is not None:
            q = q.filter(AutoLinha.regiao_metropolitana == regiao)
        return sorted({r[0] for r in q.distinct().all() if r[0]})
    finally:
        session.close()


@st.cache_data(ttl=300)
def carregar_todos_autos(tipo_servico: str, perm_id: int | None = None, regiao: str | None = None):
    session = get_session()
    try:
        q = session.query(AutoLinha).filter(AutoLinha.tipo == tipo_servico, AutoLinha.ativo == True)
        if perm_id is not None:
            q = q.filter(AutoLinha.permissionaria_id == perm_id)
        if regiao is not None:
            q = q.filter(AutoLinha.regiao_metropolitana == regiao)
        autos = q.order_by(AutoLinha.numero).all()
        return [(a.id, a.numero, a.cidade_inicial or "", a.cidade_final or "",
                 a.permissionaria.nome if a.permissionaria else "") for a in autos]
    finally:
        session.close()


@st.cache_data(ttl=300)
def carregar_permissionarias(tipo_servico: str, regiao: str | None = None):
    session = get_session()
    try:
        q = (
            session.query(Permissionaria)
            .join(AutoLinha, AutoLinha.permissionaria_id == Permissionaria.id)
            .filter(AutoLinha.tipo == tipo_servico, AutoLinha.ativo == True)
        )
        if regiao is not None:
            q = q.filter(AutoLinha.regiao_metropolitana == regiao)
        perms = q.distinct().order_by(Permissionaria.nome).all()
        return [(p.id, p.nome) for p in perms]
    finally:
        session.close()


@st.cache_data(ttl=300)
def carregar_regioes_metropolitanas():
    session = get_session()
    try:
        rows = (
            session.query(AutoLinha.regiao_metropolitana)
            .filter(AutoLinha.tipo == TipoServico.REGULAR_METROPOLITANO.value, AutoLinha.ativo == True)
            .filter(AutoLinha.regiao_metropolitana.isnot(None))
            .distinct()
            .all()
        )
        return sorted({r[0].strip() for r in rows if r[0]})
    finally:
        session.close()


def buscar_autos_por_trecho(tipo_servico: str, cidade_a: str, cidade_b: str,
                            perm_id: int | None = None, regiao: str | None = None):
    """Retorna autos que têm paradas em AMBAS as cidades (filtro por municipio_id)."""
    session = get_session()
    try:
        q = session.query(AutoLinha).filter(AutoLinha.tipo == tipo_servico, AutoLinha.ativo == True)
        if perm_id is not None:
            q = q.filter(AutoLinha.permissionaria_id == perm_id)
        if regiao is not None:
            q = q.filter(AutoLinha.regiao_metropolitana == regiao)
        if cidade_a:
            mun_id_a = session.query(Municipio.id).filter_by(nome=cidade_a).scalar()
            if mun_id_a:
                q = q.filter(exists().where(
                    (ParadaAutoLinha.auto_id == AutoLinha.id) &
                    (ParadaAutoLinha.municipio_id == mun_id_a)
                ))
        if cidade_b:
            mun_id_b = session.query(Municipio.id).filter_by(nome=cidade_b).scalar()
            if mun_id_b:
                q = q.filter(exists().where(
                    (ParadaAutoLinha.auto_id == AutoLinha.id) &
                    (ParadaAutoLinha.municipio_id == mun_id_b)
                ))
        autos = q.order_by(AutoLinha.numero).all()
        return [(a.id, a.numero, a.cidade_inicial or "", a.cidade_final or "",
                 a.permissionaria.nome if a.permissionaria else "") for a in autos]
    finally:
        session.close()


# ── Carrega dados da ouvidoria ───────────────────────────────────────────────
def carregar_dados(oid: int, tecnico_id: int):
    session = get_session()
    try:
        o = session.query(Ouvidoria).filter_by(id=oid).first()
        if not o:
            return None, None, [], None, [], [], []

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
                "subcategoria_id": r.subcategoria_id,
                "subcategoria": r.subcategoria.nome if r.subcategoria else None,
                "tipo_servico": r.tipo_servico.value if r.tipo_servico else TipoServico.REGULAR_INTERMUNICIPAL.value,
                "local_embarque": r.local_embarque,
                "local_desembarque": r.local_desembarque,
                "descricao": r.descricao,
                "empresa_fretamento": r.empresa_fretamento,
                "autos": autos_info,
            })

        # Busca TODAS as respostas técnicas deste técnico para esta ouvidoria
        respostas_tecnico = (
            session.query(RespostaTecnica)
            .filter_by(ouvidoria_id=oid, tecnico_id=tecnico_id)
            .order_by(RespostaTecnica.data_resposta.desc())
            .all()
        )
        resposta_existente = respostas_tecnico[0] if respostas_tecnico else None

        # Respostas da permissionária
        resps_perm = []
        for rp in o.respostas_permissionaria:
            resps_perm.append({
                "id": rp.id,
                "conteudo": rp.conteudo,
                "data_resposta": rp.data_resposta,
                "registrado_por": rp.registrado_por.nome if rp.registrado_por else "—",
            })

        # Anexos
        anexos = []
        for an in o.anexos:
            anexos.append({
                "id": an.id,
                "nome_arquivo": an.nome_arquivo,
                "nome_storage": an.nome_storage,
                "tipo_mime": an.tipo_mime,
                "tamanho": an.tamanho,
            })

        # Serializa respostas técnicas anteriores
        resps_tecnico_data = []
        for rt in respostas_tecnico:
            resps_tecnico_data.append({
                "id": rt.id,
                "data_resposta": rt.data_resposta,
                "texto_resposta": rt.texto_resposta,
            })

        session.expunge_all()
        return o, atribuicao, recs_data, resposta_existente, resps_perm, anexos, resps_tecnico_data
    finally:
        session.close()


result = carregar_dados(ouvidoria_id, u.id)
if result[0] is None:
    st.error("Ouvidoria não encontrada.")
    st.stop()

ouvidoria, atribuicao, recs_data, resposta_existente, resps_perm, anexos_data, resps_tecnico_data = result

# Verifica se o técnico tem acesso
if u.tipo == TipoUsuario.tecnico and atribuicao is None:
    st.error("Esta ouvidoria não está atribuída a você.")
    st.stop()

st.title(f"✍️ Resposta Técnica – Ouvidoria #{ouvidoria.id}")

with st.expander("Conteúdo da Ouvidoria", expanded=False):
    st.text(ouvidoria.conteudo)
st.write(f"**Status:** {ouvidoria.status.value}")
st.write(f"**Prazo:** {ouvidoria.prazo.strftime('%d/%m/%Y')}")

# ── Anexos (somente leitura) ─────────────────────────────────────────────────
if anexos_data:
    with st.expander(f"Anexos ({len(anexos_data)})", expanded=False):
        for an in anexos_data:
            caminho = os.path.join(UPLOADS_DIR, an["nome_storage"])
            tamanho_kb = round(an["tamanho"] / 1024, 1) if an["tamanho"] else "?"
            if os.path.exists(caminho):
                with open(caminho, "rb") as f:
                    st.download_button(
                        f"📎 {an['nome_arquivo']} ({tamanho_kb} KB)",
                        data=f.read(),
                        file_name=an["nome_arquivo"],
                        mime=an["tipo_mime"] or "application/octet-stream",
                        key=f"dl_anexo_{an['id']}",
                    )
            else:
                st.write(f"📎 {an['nome_arquivo']} — arquivo não encontrado no servidor")

# Se já respondeu, verifica se o status permite nova resposta
if resposta_existente and atribuicao and atribuicao.respondido:
    if ouvidoria.status != StatusOuvidoria.EM_ANALISE_TECNICA:
        # Bloqueado: já respondeu e ouvidoria não foi retornada para análise
        st.success("Você já registrou sua resposta técnica para esta ouvidoria.")
        if resps_tecnico_data:
            with st.expander(f"Ver respostas anteriores ({len(resps_tecnico_data)})"):
                for rt in resps_tecnico_data:
                    st.write(f"**Data:** {rt['data_resposta'].strftime('%d/%m/%Y')}")
                    st.write(f"**Texto:** {rt['texto_resposta']}")
                    st.divider()
        st.stop()
    else:
        # Permitir nova resposta — gestor retornou o status para EM_ANALISE_TECNICA
        st.info("O gestor retornou esta ouvidoria para análise técnica. Você pode registrar uma nova resposta.")
        if resps_tecnico_data:
            with st.expander(f"Ver respostas anteriores ({len(resps_tecnico_data)})"):
                for rt in resps_tecnico_data:
                    st.write(f"**Data:** {rt['data_resposta'].strftime('%d/%m/%Y')}")
                    st.write(f"**Texto:** {rt['texto_resposta']}")
                    st.divider()

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

# ── Reclamações editáveis ────────────────────────────────────────────────────
st.subheader("Reclamações")

for i, rec in enumerate(st.session_state["resp_recs_edit"]):
    tipo_label = rec.get("tipo_servico", "")
    is_fret = tipo_label in (TipoServico.FRETAMENTO_INTERMUNICIPAL.value, TipoServico.FRETAMENTO_METROPOLITANO.value)
    # Mapear fretamento para tipo base para buscar cidades
    tipo_base = {
        TipoServico.REGULAR_INTERMUNICIPAL.value: TipoServico.REGULAR_INTERMUNICIPAL.value,
        TipoServico.REGULAR_METROPOLITANO.value: TipoServico.REGULAR_METROPOLITANO.value,
        TipoServico.FRETAMENTO_INTERMUNICIPAL.value: TipoServico.REGULAR_INTERMUNICIPAL.value,
        TipoServico.FRETAMENTO_METROPOLITANO.value: TipoServico.REGULAR_METROPOLITANO.value,
    }.get(tipo_label, tipo_label)
    cidades_rec = carregar_cidades_por_tipo(tipo_base) if not is_fret else carregar_municipios()

    with st.expander(
        f"{rec['numero_item']} - {rec['categoria'] or 'Sem categoria'} - {tipo_label}",
        expanded=False,
    ):
        st.write(f"**Tipo de Serviço:** {tipo_label}")

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

        # Subcategoria (filtrada pela categoria selecionada)
        cat_id_atual = st.session_state["resp_recs_edit"][i].get("categoria_id")
        if cat_id_atual:
            subcats = carregar_subcategorias(cat_id_atual)
            if subcats:
                subcat_nomes = [n for _, n in subcats]
                subcat_map_local = {n: sid for sid, n in subcats}
                subcat_idx = 0
                if rec.get("subcategoria") and rec["subcategoria"] in subcat_nomes:
                    subcat_idx = subcat_nomes.index(rec["subcategoria"]) + 1
                subcat_sel = st.selectbox(
                    "Subcategoria", ["(Nenhuma)"] + subcat_nomes,
                    index=subcat_idx, key=f"resp_subcat_{rec['id']}"
                )
                if subcat_sel != "(Nenhuma)":
                    st.session_state["resp_recs_edit"][i]["subcategoria_id"] = subcat_map_local[subcat_sel]
                    st.session_state["resp_recs_edit"][i]["subcategoria"] = subcat_sel
                else:
                    st.session_state["resp_recs_edit"][i]["subcategoria_id"] = None
                    st.session_state["resp_recs_edit"][i]["subcategoria"] = None

        # Empresa de fretamento
        if is_fret:
            emp_fret = st.text_input(
                "Empresa de Fretamento",
                value=rec.get("empresa_fretamento") or "",
                key=f"resp_empfret_{rec['id']}"
            )
            st.session_state["resp_recs_edit"][i]["empresa_fretamento"] = emp_fret or None

        # Embarque — mesma lista independente de fret (cidades_rec já tem a lista certa)
        emb_idx = 0
        if rec["local_embarque"] and rec["local_embarque"] in cidades_rec:
            emb_idx = cidades_rec.index(rec["local_embarque"]) + 1
        emb_sel = st.selectbox(
            "Local de Embarque", [OPCAO_NAO_INFORMADO] + cidades_rec,
            index=emb_idx, key=f"resp_emb_{rec['id']}"
        )
        emb_val = None if emb_sel == OPCAO_NAO_INFORMADO else emb_sel
        st.session_state["resp_recs_edit"][i]["local_embarque"] = emb_val

        # Desembarque — filtra a partir da origem quando não é fretamento
        if not is_fret and emb_val:
            cidades_dest_rec = carregar_cidades_destino(tipo_base, emb_val)
            if cidades_dest_rec:
                des_idx = 0
                if rec["local_desembarque"] and rec["local_desembarque"] in cidades_dest_rec:
                    des_idx = cidades_dest_rec.index(rec["local_desembarque"]) + 1
                des_sel = st.selectbox(
                    "Local de Desembarque", [OPCAO_NAO_INFORMADO] + cidades_dest_rec,
                    index=des_idx, key=f"resp_des_{rec['id']}"
                )
            else:
                st.info("Sem atendimento a partir desta cidade.")
                des_sel = OPCAO_NAO_INFORMADO
        else:
            des_idx = 0
            if rec["local_desembarque"] and rec["local_desembarque"] in cidades_rec:
                des_idx = cidades_rec.index(rec["local_desembarque"]) + 1
            des_sel = st.selectbox(
                "Local de Desembarque", [OPCAO_NAO_INFORMADO] + cidades_rec,
                index=des_idx, key=f"resp_des_{rec['id']}"
            )
        st.session_state["resp_recs_edit"][i]["local_desembarque"] = (
            None if des_sel == OPCAO_NAO_INFORMADO else des_sel
        )

        # Descrição
        desc = st.text_area("Descrição", value=rec["descricao"] or "", key=f"resp_desc_{rec['id']}", height=100)
        st.session_state["resp_recs_edit"][i]["descricao"] = desc or None

        # Autos vinculados (não exibir para fretamento)
        if not is_fret:
            st.markdown("**Autos vinculados:**")
            if rec["autos"]:
                for a in rec["autos"]:
                    col_auto, col_rem = st.columns([5, 1])
                    col_auto.write(f"- {a['numero']} – {a['permissionaria']} – {a['cidade_ini']} → {a['cidade_fim']}")
                    if col_rem.button("✕", key=f"rem_auto_{rec['id']}_{a['id']}"):
                        st.session_state["resp_recs_edit"][i]["autos"] = [
                            x for x in rec["autos"] if x["id"] != a["id"]
                        ]
                        st.rerun()
            else:
                st.write("Nenhum auto vinculado")

# ── Vincular Autos à Reclamação ──────────────────────────────────────────────
recs_nao_fret = [
    r for r in st.session_state["resp_recs_edit"]
    if r.get("tipo_servico") not in (TipoServico.FRETAMENTO_INTERMUNICIPAL.value, TipoServico.FRETAMENTO_METROPOLITANO.value)
]
if recs_nao_fret:
    st.divider()
    st.subheader("Vincular Autos à Reclamação")

    rec_labels = [
        f"{r['numero_item']} - {r['categoria'] or 'Sem categoria'} - {r.get('tipo_servico', '')}"
        for r in recs_nao_fret
    ]
    rec_idx_map = [
        i for i, r in enumerate(st.session_state["resp_recs_edit"])
        if r.get("tipo_servico") not in (TipoServico.FRETAMENTO_INTERMUNICIPAL.value, TipoServico.FRETAMENTO_METROPOLITANO.value)
    ]
    rec_sel_label = st.selectbox("Reclamação alvo", rec_labels, key="resp_rec_alvo_sel")
    rec_idx = rec_idx_map[rec_labels.index(rec_sel_label)]

    # Detecta troca de reclamação alvo
    if st.session_state["resp_rec_alvo_anterior"] != rec_sel_label:
        for a in st.session_state["resp_autos_checklist"]:
            st.session_state.pop(f"resp_chk_{a['id']}", None)
        st.session_state["resp_autos_checklist"] = []
        st.session_state["resp_rec_alvo_anterior"] = rec_sel_label

    # Tipo de serviço da reclamação selecionada (mapeado para tipo base)
    rec_tipo_raw = st.session_state["resp_recs_edit"][rec_idx].get("tipo_servico", TipoServico.REGULAR_INTERMUNICIPAL.value)
    rec_tipo = {
        TipoServico.REGULAR_INTERMUNICIPAL.value: TipoServico.REGULAR_INTERMUNICIPAL.value,
        TipoServico.REGULAR_METROPOLITANO.value: TipoServico.REGULAR_METROPOLITANO.value,
        TipoServico.FRETAMENTO_INTERMUNICIPAL.value: TipoServico.REGULAR_INTERMUNICIPAL.value,
        TipoServico.FRETAMENTO_METROPOLITANO.value: TipoServico.REGULAR_METROPOLITANO.value,
    }.get(rec_tipo_raw, rec_tipo_raw)

    # Auto-fill: embarque/desembarque da reclamação alvo
    rec_alvo = st.session_state["resp_recs_edit"][rec_idx]
    auto_fill_orig = rec_alvo.get("local_embarque")
    auto_fill_dest = rec_alvo.get("local_desembarque")
    trecho_disabled = (auto_fill_orig is None and auto_fill_dest is None)

    # ── Filtros comuns ────────────────────────────────────────────────────────
    regiao_sel_val = None

    if rec_tipo == TipoServico.REGULAR_METROPOLITANO.value:
        regioes = carregar_regioes_metropolitanas()
        regiao_sel = st.selectbox("Região Metropolitana", [OPCAO_QUALQUER] + regioes, key="resp_filtro_rm")
        regiao_sel_val = None if regiao_sel == OPCAO_QUALQUER else regiao_sel

    perms = carregar_permissionarias(rec_tipo, regiao=regiao_sel_val)
    perm_nomes = [n for _, n in perms]
    perm_map = {nome: pid for pid, nome in perms}

    empresa_sel = st.selectbox("Empresa", [OPCAO_TODAS] + perm_nomes, key="resp_filtro_empresa")
    perm_id_sel = None if empresa_sel == OPCAO_TODAS else perm_map.get(empresa_sel)

    cidades = carregar_cidades(rec_tipo, perm_id=perm_id_sel, regiao=regiao_sel_val)

    # ── Layout de 2 colunas ──────────────────────────────────────────────────
    col_trecho, col_todos = st.columns(2)

    with col_trecho:
        st.markdown("**Buscar por Trecho**")

        idx_orig = 0
        if auto_fill_orig and auto_fill_orig in cidades:
            idx_orig = cidades.index(auto_fill_orig) + 1

        cidade_orig_sel = st.selectbox(
            "Cidade de Origem", [OPCAO_NAO_INFORMADO] + cidades, index=idx_orig, key="resp_trecho_orig"
        )

        # Destino: filtra com base na origem escolhida
        orig_val = None if cidade_orig_sel == OPCAO_NAO_INFORMADO else cidade_orig_sel
        if orig_val:
            destinos_trecho = carregar_cidades_destino(rec_tipo, orig_val, perm_id=perm_id_sel, regiao=regiao_sel_val)
            if destinos_trecho:
                idx_dest = 0
                if auto_fill_dest and auto_fill_dest in destinos_trecho:
                    idx_dest = destinos_trecho.index(auto_fill_dest) + 1
                cidade_dest_sel = st.selectbox(
                    "Cidade de Destino", [OPCAO_NAO_INFORMADO] + destinos_trecho, index=idx_dest, key="resp_trecho_dest"
                )
            else:
                st.info("Sem atendimento a partir desta cidade.")
                cidade_dest_sel = OPCAO_NAO_INFORMADO
        else:
            idx_dest = 0
            if auto_fill_dest and auto_fill_dest in cidades:
                idx_dest = cidades.index(auto_fill_dest) + 1
            cidade_dest_sel = st.selectbox(
                "Cidade de Destino", [OPCAO_NAO_INFORMADO] + cidades, index=idx_dest, key="resp_trecho_dest"
            )

        buscar_disabled = trecho_disabled and cidade_orig_sel == OPCAO_NAO_INFORMADO and cidade_dest_sel == OPCAO_NAO_INFORMADO
        if st.button("🔍 Buscar por trecho", use_container_width=True, key="resp_btn_trecho", disabled=buscar_disabled):
            orig = None if cidade_orig_sel == OPCAO_NAO_INFORMADO else cidade_orig_sel
            dest = None if cidade_dest_sel == OPCAO_NAO_INFORMADO else cidade_dest_sel
            if orig or dest:
                encontrados = buscar_autos_por_trecho(
                    rec_tipo, orig or "", dest or "",
                    perm_id=perm_id_sel, regiao=regiao_sel_val,
                )
                ids_existentes = {a["id"] for a in st.session_state["resp_autos_checklist"]}
                adicionados = 0
                for aid, anum, aori, adest, aemp in encontrados:
                    if aid not in ids_existentes:
                        st.session_state["resp_autos_checklist"].append(
                            {"id": aid, "numero": anum, "cidade_ini": aori, "cidade_fim": adest, "empresa": aemp}
                        )
                        ids_existentes.add(aid)
                        adicionados += 1
                st.success(f"{adicionados} autos adicionados ({len(encontrados)} encontrados).")
                st.rerun()
            else:
                st.warning("Selecione ao menos uma cidade.")

    with col_todos:
        st.markdown("**Todos os Autos**")
        todos_autos = carregar_todos_autos(rec_tipo, perm_id=perm_id_sel, regiao=regiao_sel_val)
        if todos_autos:
            def _fmt_auto(a):
                num, emp, ori, dest = a[1], a[4], a[2], a[3]
                partes = [num]
                if emp:
                    partes.append(emp)
                if ori or dest:
                    partes.append(f"{ori} → {dest}")
                return " – ".join(partes)
            num_opcoes = [_fmt_auto(a) for a in todos_autos]
            num_sel = st.selectbox("Selecione o Auto", num_opcoes, key="resp_num_sel")
            sel_idx = num_opcoes.index(num_sel)
            if st.button("➕ Adicionar", use_container_width=True, key="resp_btn_num"):
                auto_row = todos_autos[sel_idx]
                aid, anum, aori, adest, aemp = auto_row
                ids_existentes = {a["id"] for a in st.session_state["resp_autos_checklist"]}
                if aid not in ids_existentes:
                    st.session_state["resp_autos_checklist"].append(
                        {"id": aid, "numero": anum, "cidade_ini": aori, "cidade_fim": adest, "empresa": aemp}
                    )
                    st.success(f"Auto {anum} adicionado.")
                    st.rerun()
                else:
                    st.info("Auto já está na lista.")
        else:
            st.info("Nenhum auto encontrado para os filtros selecionados.")

    # Checklist acumulada
    if st.session_state["resp_autos_checklist"]:
        st.markdown(f"**Lista de Autos ({len(st.session_state['resp_autos_checklist'])} encontrados) — marque os que deseja vincular:**")

        ids_ja_salvos = {a["id"] for a in st.session_state["resp_recs_edit"][rec_idx]["autos"]}

        for auto in st.session_state["resp_autos_checklist"]:
            ja_salvo = auto["id"] in ids_ja_salvos
            emp = auto.get('empresa', '')
            label = f"**{auto['numero']}** – {emp + ' – ' if emp else ''}{auto['cidade_ini']} → {auto['cidade_fim']}"
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

# ── Respostas da Permissionária ──────────────────────────────────────────────
st.divider()
st.subheader("Respostas da Permissionária")

if resps_perm:
    for rp in resps_perm:
        with st.expander(f"{rp['data_resposta'].strftime('%d/%m/%Y')} — por {rp['registrado_por']}"):
            st.text(rp["conteudo"])
            if st.button("🗑 Excluir esta resposta", key=f"del_rp_{rp['id']}"):
                with db_session() as session:
                    obj = session.get(RespostaPermissionaria, rp["id"])
                    if obj:
                        session.delete(obj)
                st.success("Resposta excluída.")
                st.rerun()
else:
    st.info("Nenhuma resposta da permissionária registrada.")

# Nova manifestação da permissionária
nova_manif = st.checkbox("Nova manifestação da permissionária?", key="nova_manif_check")
if nova_manif:
    with st.container():
        manif_conteudo = st.text_area("Conteúdo da manifestação", height=150, key="manif_conteudo")
        manif_data = st.date_input("Data da manifestação", value=date.today(), key="manif_data")
        if st.button("📥 Registrar manifestação", key="btn_manif"):
            if not manif_conteudo.strip():
                st.error("O conteúdo da manifestação é obrigatório.")
            else:
                with db_session() as session:
                    session.add(RespostaPermissionaria(
                        ouvidoria_id=ouvidoria_id,
                        conteudo=manif_conteudo.strip(),
                        data_resposta=manif_data,
                        registrado_por_id=u.id,
                    ))
                st.success("Manifestação registrada.")
                st.rerun()

# ── Registrar Resposta Técnica ───────────────────────────────────────────────
st.divider()
st.subheader("Registrar Resposta")

with st.form("form_resposta"):
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
                    rec_db.subcategoria_id = rec_edit.get("subcategoria_id")
                    rec_db.local_embarque = rec_edit["local_embarque"]
                    rec_db.local_desembarque = rec_edit["local_desembarque"]
                    rec_db.descricao = rec_edit["descricao"]
                    rec_db.empresa_fretamento = rec_edit.get("empresa_fretamento")

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

                # Registra resposta (sem SEI)
                resp = RespostaTecnica(
                    ouvidoria_id=ouvidoria_id,
                    tecnico_id=u.id,
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
