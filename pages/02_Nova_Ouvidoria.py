"""Criar nova ouvidoria com reclamações itemizadas."""

import os
import uuid
import mimetypes
import sys
from datetime import date, timedelta

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
    ParadaAutoLinha,
    Permissionaria,
    Reclamacao,
    ReclamacaoAuto,
    StatusOuvidoria,
    TipoServico,
)
from utils.cache import carregar_categorias, carregar_municipios, carregar_subcategorias

st.set_page_config(page_title="Nova Ouvidoria", page_icon="➕", layout="wide")
st.markdown('<style>[data-testid="stSidebar"]{width:220px!important;min-width:220px!important;}</style>', unsafe_allow_html=True)
auth.require_gestor()

u = usuario_logado()

UPLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

ALLOWED_MIMES = {
    "application/pdf",
    "image/png", "image/jpeg", "image/gif", "image/bmp",
    "video/mp4", "video/x-msvideo", "video/quicktime", "video/x-matroska", "video/webm",
}

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
    """Retorna cidades via nome IBGE para a seção de busca por trecho, com filtros opcionais."""
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
    """Retorna cidades alcançáveis a partir da origem (via linhas que passam pela origem).
    Fretamento: todos os municípios SP (sem filtro). Regular: filtra por linhas em comum."""
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
    """Retorna todos os autos filtrados: (id, numero, cidade_ini, cidade_fim, empresa)."""
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
    """Retorna permissionárias que possuem autos do tipo informado."""
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
    """Retorna lista de regiões metropolitanas distintas."""
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


# ── Estado ────────────────────────────────────────────────────────────────────
if "reclamacoes_draft" not in st.session_state:
    st.session_state["reclamacoes_draft"] = []
if "autos_checklist" not in st.session_state:
    st.session_state["autos_checklist"] = []
if "rec_alvo_anterior" not in st.session_state:
    st.session_state["rec_alvo_anterior"] = None

# ── Cabeçalho da Ouvidoria ────────────────────────────────────────────────────
st.title("➕ Nova Ouvidoria")

protocolo = st.text_input("Protocolo da Ouvidoria *", placeholder="Ex.: 202405241486076")
conteudo = st.text_area("Conteúdo da Ouvidoria *", height=300, placeholder="Cole aqui o conteúdo completo da ouvidoria...")
prazo = st.date_input("Prazo de resposta *", value=date.today() + timedelta(days=15))

# ── Controle da Permissionária ────────────────────────────────────────────────
enviado_permissionaria = st.checkbox("Enviado para a permissionária")
prazo_permissionaria = None
if enviado_permissionaria:
    prazo_permissionaria = st.date_input(
        "Prazo de resposta da permissionária",
        value=date.today() + timedelta(days=30),
    )

# ── Anexos ────────────────────────────────────────────────────────────────────
st.markdown("#### Anexos")
arquivos_upload = st.file_uploader(
    "Anexar arquivos (PDF, fotos ou vídeos)",
    accept_multiple_files=True,
    type=["pdf", "png", "jpg", "jpeg", "gif", "bmp", "mp4", "avi", "mov", "mkv", "webm"],
)

st.divider()

# ── Reclamações ───────────────────────────────────────────────────────────────
st.subheader("Reclamações")

categorias = carregar_categorias()
cat_map = {nome: cid for cid, nome in categorias}
cat_nomes = [nome for _, nome in categorias]

# Exibe reclamações já adicionadas
if st.session_state["reclamacoes_draft"]:
    for i, rec in enumerate(st.session_state["reclamacoes_draft"]):
        label_embarque = rec["local_embarque"] or OPCAO_NAO_INFORMADO
        label_desembarque = rec["local_desembarque"] or OPCAO_NAO_INFORMADO
        tipo_label = rec.get("tipo_servico", "")
        with st.expander(
            f"{rec['numero_item']} - {rec['categoria_nome'] or 'Sem categoria'} - {tipo_label} "
            f"({label_embarque} → {label_desembarque})",
            expanded=False,
        ):
            st.write(f"**Tipo de Serviço:** {tipo_label}")
            subcat_label = rec.get("subcategoria_nome") or "–"
            st.write(f"**Subcategoria:** {subcat_label}")
            if rec.get("empresa_fretamento"):
                st.write(f"**Empresa de Fretamento:** {rec['empresa_fretamento']}")
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

# tipo_servico fora do form para reatividade das cidades
tipo_servico_sel = st.radio(
    "Tipo de Serviço *",
    [ts.value for ts in TipoServico],
    horizontal=True,
    key="novo_rec_tipo",
)

# Determina se é fretamento
is_fretamento = tipo_servico_sel in (
    TipoServico.FRETAMENTO_INTERMUNICIPAL.value,
    TipoServico.FRETAMENTO_METROPOLITANO.value,
)

# Tipo base para filtrar autos (Regular == mesmo tipo base)
tipo_base_para_autos = {
    TipoServico.REGULAR_INTERMUNICIPAL.value: TipoServico.REGULAR_INTERMUNICIPAL.value,
    TipoServico.REGULAR_METROPOLITANO.value: TipoServico.REGULAR_METROPOLITANO.value,
    TipoServico.FRETAMENTO_INTERMUNICIPAL.value: TipoServico.REGULAR_INTERMUNICIPAL.value,
    TipoServico.FRETAMENTO_METROPOLITANO.value: TipoServico.REGULAR_METROPOLITANO.value,
}.get(tipo_servico_sel, tipo_servico_sel)

# Empresa de fretamento (campo livre, sem vínculo de autos)
empresa_fretamento_val = None
if is_fretamento:
    empresa_fretamento_val = st.text_input("Empresa de Fretamento", key="empresa_fretamento_input")

# Categoria e Subcategoria fora do form para reatividade dinâmica
cat_sel = st.selectbox("Categoria *", cat_nomes if cat_nomes else ["(Nenhuma categoria cadastrada)"], key="novo_rec_cat")
cat_id_sel = cat_map.get(cat_sel)

# Subcategorias filtradas pela categoria
subcat_id_sel = None
subcat_nome_sel = None
if cat_id_sel:
    subcats = carregar_subcategorias(cat_id_sel)
    if subcats:
        subcat_nomes = [n for _, n in subcats]
        subcat_map_local = {n: sid for sid, n in subcats}
        subcat_sel = st.selectbox("Subcategoria", ["(Nenhuma)"] + subcat_nomes, key="novo_rec_subcat")
        if subcat_sel != "(Nenhuma)":
            subcat_id_sel = subcat_map_local[subcat_sel]
            subcat_nome_sel = subcat_sel

# Embarque/Desembarque fora do form para reatividade (destino filtra com base na origem)
col_emb, col_desemb = st.columns(2)
if not is_fretamento:
    cidades_origem = carregar_cidades_por_tipo(tipo_base_para_autos)
    with col_emb:
        emb_sel = st.selectbox("Local de Embarque", [OPCAO_NAO_INFORMADO] + cidades_origem, key="rec_emb_sel")
    emb_val = None if emb_sel == OPCAO_NAO_INFORMADO else emb_sel
    with col_desemb:
        if emb_val:
            cidades_destino_rec = carregar_cidades_destino(tipo_base_para_autos, emb_val)
            if cidades_destino_rec:
                desemb_sel = st.selectbox("Local de Desembarque", [OPCAO_NAO_INFORMADO] + cidades_destino_rec, key="rec_desemb_sel")
            else:
                st.warning("Sem atendimento a partir desta cidade.")
                desemb_sel = OPCAO_NAO_INFORMADO
                st.session_state["rec_desemb_sel"] = OPCAO_NAO_INFORMADO
        else:
            desemb_sel = st.selectbox("Local de Desembarque", [OPCAO_NAO_INFORMADO] + cidades_origem, key="rec_desemb_sel")
else:
    municipios_sp = carregar_municipios()
    with col_emb:
        emb_sel = st.selectbox("Local de Embarque", [OPCAO_NAO_INFORMADO] + municipios_sp, key="rec_emb_sel")
    with col_desemb:
        desemb_sel = st.selectbox("Local de Desembarque", [OPCAO_NAO_INFORMADO] + municipios_sp, key="rec_desemb_sel")

with st.form("form_reclamacao", clear_on_submit=True):
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.caption(f"Embarque: **{emb_sel}**")
        st.caption(f"Desembarque: **{desemb_sel}**")
    with col_b:
        descricao = st.text_area("Descrição", height=100)

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
                "subcategoria_id": subcat_id_sel,
                "subcategoria_nome": subcat_nome_sel,
                "tipo_servico": tipo_servico_sel,
                "local_embarque": None if emb_sel == OPCAO_NAO_INFORMADO else emb_sel,
                "local_desembarque": None if desemb_sel == OPCAO_NAO_INFORMADO else desemb_sel,
                "descricao": descricao or None,
                "empresa_fretamento": empresa_fretamento_val if is_fretamento else None,
                "autos": [],
            }
            st.session_state["reclamacoes_draft"].append(nova_rec)
            st.rerun()

# ── Vincular Autos à Reclamação ───────────────────────────────────────────────
# Apenas para reclamações não-fretamento
recs_com_autos = [r for r in st.session_state["reclamacoes_draft"] if not r.get("empresa_fretamento")]
if recs_com_autos and st.session_state["reclamacoes_draft"]:
    st.divider()
    st.subheader("Vincular Autos à Reclamação")

    # Formato: "1 - CATEGORIA - Tipo" (somente reclamações sem fretamento)
    rec_labels = [
        f"{r['numero_item']} - {r['categoria_nome'] or 'Sem categoria'} - {r.get('tipo_servico', '')}"
        for r in st.session_state["reclamacoes_draft"]
        if not r.get("empresa_fretamento")
    ]
    # Mapeamento de label para índice real
    rec_idx_map = [
        i for i, r in enumerate(st.session_state["reclamacoes_draft"])
        if not r.get("empresa_fretamento")
    ]
    if not rec_labels:
        st.info("Todas as reclamações são de fretamento — vinculação de autos não aplicável.")
        st.stop()
    rec_sel_label = st.selectbox("Reclamação alvo", rec_labels, key="rec_alvo_sel")
    rec_idx = rec_idx_map[rec_labels.index(rec_sel_label)]

    # Detecta troca de reclamação alvo e limpa a checklist
    if st.session_state["rec_alvo_anterior"] != rec_sel_label:
        for a in st.session_state["autos_checklist"]:
            st.session_state.pop(f"chk_{a['id']}", None)
        st.session_state["autos_checklist"] = []
        st.session_state["rec_alvo_anterior"] = rec_sel_label

    # Tipo de serviço da reclamação selecionada
    rec_tipo_raw = st.session_state["reclamacoes_draft"][rec_idx].get("tipo_servico", TipoServico.REGULAR_INTERMUNICIPAL.value)
    # Mapear fretamento para o tipo base de autos
    rec_tipo = {
        TipoServico.REGULAR_INTERMUNICIPAL.value: TipoServico.REGULAR_INTERMUNICIPAL.value,
        TipoServico.REGULAR_METROPOLITANO.value: TipoServico.REGULAR_METROPOLITANO.value,
        TipoServico.FRETAMENTO_INTERMUNICIPAL.value: TipoServico.REGULAR_INTERMUNICIPAL.value,
        TipoServico.FRETAMENTO_METROPOLITANO.value: TipoServico.REGULAR_METROPOLITANO.value,
    }.get(rec_tipo_raw, rec_tipo_raw)

    # Auto-fill: embarque/desembarque da reclamação alvo
    rec_alvo = st.session_state["reclamacoes_draft"][rec_idx]
    auto_fill_orig = rec_alvo.get("local_embarque")
    auto_fill_dest = rec_alvo.get("local_desembarque")
    trecho_disabled = (auto_fill_orig is None and auto_fill_dest is None)

    # ── Filtros comuns ────────────────────────────────────────────────────────
    regiao_sel_val = None

    if rec_tipo == TipoServico.REGULAR_METROPOLITANO.value:
        regioes = carregar_regioes_metropolitanas()
        regiao_sel = st.selectbox("Região Metropolitana", [OPCAO_QUALQUER] + regioes, key="filtro_rm")
        regiao_sel_val = None if regiao_sel == OPCAO_QUALQUER else regiao_sel

    perms = carregar_permissionarias(rec_tipo, regiao=regiao_sel_val)
    perm_nomes = [n for _, n in perms]
    perm_map = {nome: pid for pid, nome in perms}

    empresa_sel = st.selectbox("Empresa", [OPCAO_TODAS] + perm_nomes, key="filtro_empresa")
    perm_id_sel = None if empresa_sel == OPCAO_TODAS else perm_map.get(empresa_sel)

    # Cidades filtradas pelo tipo, empresa e região
    cidades = carregar_cidades(rec_tipo, perm_id=perm_id_sel, regiao=regiao_sel_val)

    # ── Layout de 2 colunas: Trecho | Todos os Autos ─────────────────────────
    col_trecho, col_todos = st.columns(2)

    # ── Coluna 1: Busca por Trecho ───────────────────────────────────────────
    with col_trecho:
        st.markdown("**Buscar por Trecho**")

        # Pré-selecionar as cidades da reclamação alvo
        idx_orig = 0
        if auto_fill_orig and auto_fill_orig in cidades:
            idx_orig = cidades.index(auto_fill_orig) + 1  # +1 por causa do "Não informado"

        cidade_orig_sel = st.selectbox(
            "Cidade de Origem", [OPCAO_NAO_INFORMADO] + cidades, index=idx_orig, key="trecho_orig"
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
                    "Cidade de Destino", [OPCAO_NAO_INFORMADO] + destinos_trecho, index=idx_dest, key="trecho_dest"
                )
            else:
                st.info("Sem atendimento a partir desta cidade.")
                cidade_dest_sel = OPCAO_NAO_INFORMADO
        else:
            idx_dest = 0
            if auto_fill_dest and auto_fill_dest in cidades:
                idx_dest = cidades.index(auto_fill_dest) + 1
            cidade_dest_sel = st.selectbox(
                "Cidade de Destino", [OPCAO_NAO_INFORMADO] + cidades, index=idx_dest, key="trecho_dest"
            )

        buscar_disabled = trecho_disabled and cidade_orig_sel == OPCAO_NAO_INFORMADO and cidade_dest_sel == OPCAO_NAO_INFORMADO
        if st.button("🔍 Buscar por trecho", use_container_width=True, disabled=buscar_disabled):
            orig = None if cidade_orig_sel == OPCAO_NAO_INFORMADO else cidade_orig_sel
            dest = None if cidade_dest_sel == OPCAO_NAO_INFORMADO else cidade_dest_sel
            if orig or dest:
                encontrados = buscar_autos_por_trecho(
                    rec_tipo, orig or "", dest or "",
                    perm_id=perm_id_sel, regiao=regiao_sel_val,
                )
                ids_existentes = {a["id"] for a in st.session_state["autos_checklist"]}
                adicionados = 0
                for aid, anum, aori, adest, aemp in encontrados:
                    if aid not in ids_existentes:
                        st.session_state["autos_checklist"].append(
                            {"id": aid, "numero": anum, "cidade_ini": aori, "cidade_fim": adest, "empresa": aemp}
                        )
                        ids_existentes.add(aid)
                        adicionados += 1
                st.success(f"{adicionados} autos adicionados à lista ({len(encontrados)} encontrados).")
                st.rerun()
            else:
                st.warning("Selecione ao menos origem ou destino.")

    # ── Coluna 2: Todos os Autos da empresa/região ──────────────────────────
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
            num_sel = st.selectbox("Selecione o Auto", num_opcoes, key="num_sel")
            sel_idx = num_opcoes.index(num_sel)
            if st.button("➕ Adicionar à lista", use_container_width=True):
                auto_row = todos_autos[sel_idx]
                aid, anum, aori, adest, aemp = auto_row
                ids_existentes = {a["id"] for a in st.session_state["autos_checklist"]}
                if aid not in ids_existentes:
                    st.session_state["autos_checklist"].append(
                        {"id": aid, "numero": anum, "cidade_ini": aori, "cidade_fim": adest, "empresa": aemp}
                    )
                    st.success(f"Auto {anum} adicionado à lista.")
                    st.rerun()
                else:
                    st.info("Auto já está na lista.")
        else:
            st.info("Nenhum auto encontrado para os filtros selecionados.")

    # ── Checklist acumulada ───────────────────────────────────────────────────
    if st.session_state["autos_checklist"]:
        st.markdown(f"**Lista de Autos ({len(st.session_state['autos_checklist'])} encontrados) — marque os que deseja vincular:**")

        ids_ja_salvos = {a["id"] for a in st.session_state["reclamacoes_draft"][rec_idx]["autos"]}

        for auto in st.session_state["autos_checklist"]:
            ja_salvo = auto["id"] in ids_ja_salvos
            emp = auto.get('empresa', '')
            label = f"**{auto['numero']}** – {emp + ' – ' if emp else ''}{auto['cidade_ini']} → {auto['cidade_fim']}"
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
    if not protocolo.strip():
        st.error("Informe o protocolo da ouvidoria.")
    elif not conteudo.strip():
        st.error("Informe o conteúdo da ouvidoria.")
    elif not st.session_state["reclamacoes_draft"]:
        st.warning("Adicione ao menos uma reclamação antes de salvar.")
    else:
        # Validar anexos (MIME)
        arquivos_validos = []
        for arq in (arquivos_upload or []):
            mime = arq.type or mimetypes.guess_type(arq.name)[0] or ""
            if mime not in ALLOWED_MIMES:
                st.error(f"Arquivo '{arq.name}' não é um tipo permitido (apenas PDF, fotos e vídeos).")
                st.stop()
            arquivos_validos.append(arq)

        try:
            with db_session() as session:
                status_inicial = (
                    StatusOuvidoria.AGUARDANDO_PERMISSIONARIA
                    if enviado_permissionaria and prazo_permissionaria
                    else StatusOuvidoria.AGUARDANDO_ACOES
                )
                ouvidoria = Ouvidoria(
                    protocolo=protocolo.strip(),
                    conteudo=conteudo.strip(),
                    prazo=prazo,
                    prazo_permissionaria=prazo_permissionaria if enviado_permissionaria else None,
                    status=status_inicial,
                    criado_por_id=u.id,
                )
                session.add(ouvidoria)
                session.flush()

                for rec_draft in st.session_state["reclamacoes_draft"]:
                    # Mapeia string para enum
                    tipo_srv = None
                    ts_val = rec_draft.get("tipo_servico")
                    if ts_val:
                        for ts in TipoServico:
                            if ts.value == ts_val:
                                tipo_srv = ts
                                break

                    rec = Reclamacao(
                        ouvidoria_id=ouvidoria.id,
                        numero_item=rec_draft["numero_item"],
                        categoria_id=rec_draft["categoria_id"],
                        subcategoria_id=rec_draft.get("subcategoria_id"),
                        tipo_servico=tipo_srv,
                        local_embarque=rec_draft["local_embarque"],
                        local_desembarque=rec_draft["local_desembarque"],
                        descricao=rec_draft["descricao"],
                        empresa_fretamento=rec_draft.get("empresa_fretamento"),
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

                # Salvar anexos
                for arq in arquivos_validos:
                    ext = os.path.splitext(arq.name)[1]
                    nome_storage = f"{uuid.uuid4().hex}{ext}"
                    caminho = os.path.join(UPLOADS_DIR, nome_storage)
                    with open(caminho, "wb") as f:
                        f.write(arq.getbuffer())
                    session.add(AnexoOuvidoria(
                        ouvidoria_id=ouvidoria.id,
                        nome_arquivo=arq.name,
                        nome_storage=nome_storage,
                        tipo_mime=arq.type,
                        tamanho=arq.size,
                        enviado_por_id=u.id,
                    ))

            st.session_state["reclamacoes_draft"] = []
            st.session_state["autos_checklist"] = []
            st.session_state["rec_alvo_anterior"] = None
            st.success("Ouvidoria salva com sucesso!")
            st.switch_page("pages/01_Ouvidorias.py")
        except Exception as e:
            msg = str(e)
            if "uq_ouvidorias_protocolo" in msg or "protocolo" in msg.lower() and "unique" in msg.lower():
                st.error(f"Já existe uma ouvidoria com o protocolo **{protocolo}**. Informe um protocolo diferente.")
            else:
                st.error(f"Erro ao salvar: {e}")
