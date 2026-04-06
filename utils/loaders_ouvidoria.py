"""Loaders de ouvidorias: monta View Models para a interface a partir dos TypedDicts do repositório."""

import streamlit as st

from repositories.ouvidoria_repo import (
    get_atribuicao_tecnico,
    get_ouvidoria_completa,
    get_ouvidoria_permissionaria,
    get_respostas_tecnico,
)
from repositories.types import OuvidoriaPermissionariaDict
from utils.types import DetalheOuvidoriaView, RespostaTecnicaView


def carregar_detalhe_ouvidoria(oid: int) -> DetalheOuvidoriaView | None:
    """Carrega ouvidoria completa para a página de detalhe (03).

    Além do OuvidoriaDetalheDict, constrói dois índices de acesso rápido:
    - rec_autos: reclamacao_id → lista de autos vinculados
    - tecnicos_info: tecnico_id → dados da atribuição
    """
    o = get_ouvidoria_completa(oid)
    if not o:
        return None
    return DetalheOuvidoriaView(
        ouvidoria=o,
        rec_autos={r["id"]: r["autos"] for r in o["reclamacoes"]},
        tecnicos_info={a["tecnico_id"]: a for a in o["atribuicoes"]},
    )


@st.cache_data(ttl=60)
def carregar_ouvidoria_para_permissionaria(_oid: int) -> OuvidoriaPermissionariaDict | None:
    """Carrega ouvidoria com dados resumidos + respostas da permissionária (página 04)."""
    return get_ouvidoria_permissionaria(_oid)


def carregar_ouvidoria_para_resposta_tecnica(oid: int, tecnico_id: int) -> RespostaTecnicaView | None:
    """Carrega ouvidoria com dados necessários para resposta técnica (página 05)."""
    o = get_ouvidoria_completa(oid)
    if not o:
        return None
    historico = get_respostas_tecnico(oid, tecnico_id)
    return RespostaTecnicaView(
        ouvidoria=o,
        atribuicao=get_atribuicao_tecnico(oid, tecnico_id),
        resposta_existente=historico[0] if historico else None,
        historico=historico,
    )
