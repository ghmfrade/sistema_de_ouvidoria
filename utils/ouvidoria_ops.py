"""Operações sobre ouvidorias: listar (formatação), carregar técnicos.
Operações de escrita delegadas a repositories/ouvidoria_write_repo.py."""

import streamlit as st

from repositories.catalog_repo import get_tecnicos_ativos
from repositories.ouvidoria_repo import get_id_por_protocolo, get_ouvidorias
from repositories.ouvidoria_write_repo import (
    atribuir_tecnico as _atribuir_tecnico,
    concluir_ouvidoria as _concluir_ouvidoria,
    excluir_ouvidoria as _excluir_ouvidoria,
    editar_ouvidoria as _editar_ouvidoria
)
from utils.formatters import formatar_atribuicoes

@st.cache_data(show_spinner=False, ttl=60)
def listar_ouvidorias(filtro_status=None, filtro_periodo=None, ocultar_concluidos=True,
                      usuario_id: int | None = None, usuario_tipo: str | None = None,
                      filtro_categoria_id=None, filtro_subcategoria_id=None,
                      filtro_tipo_servico=None, cache_buster: int = 0):
    """Retorna lista de ouvidorias formatadas para a tabela da página 01."""
    ouvidorias = get_ouvidorias(
        filtro_status, filtro_periodo, ocultar_concluidos,
        usuario_id=usuario_id, usuario_tipo=usuario_tipo,
        filtro_categoria_id=filtro_categoria_id,
        filtro_subcategoria_id=filtro_subcategoria_id,
        filtro_tipo_servico=filtro_tipo_servico,
    )

    resultado = []
    for o in ouvidorias:
        coord_ger, responsaveis = formatar_atribuicoes(o["atribuicoes"])
        resultado.append({
            "id": o["id"],
            "protocolo": o["protocolo"] or "–",
            "status": o["status"],
            "prazo": o["prazo"],
            "prazo_permissionaria": o["prazo_permissionaria"],
            "criado_em": o["criado_em"],
            "concluido_em": o["concluido_em"],
            "coord_ger": coord_ger,
            "responsaveis": responsaveis,
        })
    return resultado

def carregar_tecnicos_disponiveis():
    """Retorna lista de técnicos ativos: [(id, nome)]."""
    return [(t["id"], t["nome"]) for t in get_tecnicos_ativos()]

def atribuir_tecnico(ouvidoria_id: int, tecnico_id: int):
    """Atribui técnico a ouvidoria. Retorna False se já atribuído."""
    return _atribuir_tecnico(ouvidoria_id, tecnico_id)

def excluir_ouvidoria(oid: int):
    """Exclui ouvidoria por id."""
    _excluir_ouvidoria(oid)

def buscar_ouvidoria_por_protocolo(protocolo: str) -> int | None:
    """Retorna o id da ouvidoria com o protocolo informado, ou None se não encontrado."""
    return get_id_por_protocolo(protocolo)

def alterar_status_ouvidoria(oid, status):
    _editar_ouvidoria(oid, status=status)

def concluir_ouvidoria(oid: int):
    """Marca ouvidoria como concluída."""
    _concluir_ouvidoria(oid)
