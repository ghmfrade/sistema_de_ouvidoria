"""Operações sobre ouvidorias: listar (formatação), carregar técnicos.
Operações de escrita delegadas a repositories/ouvidoria_write_repo.py."""

import streamlit as st

from repositories.catalog_repo import get_tecnicos_ativos
from repositories.ouvidoria_repo import get_ouvidorias
from repositories.ouvidoria_write_repo import (
    atribuir_tecnico as _atribuir_tecnico,
    concluir_ouvidoria as _concluir_ouvidoria,
    excluir_ouvidoria as _excluir_ouvidoria,
)


def listar_ouvidorias(filtro_status=None, filtro_periodo=None, ocultar_concluidos=True, usuario=None):
    """Retorna lista de ouvidorias formatadas para a tabela da página 01."""
    ouvidorias = get_ouvidorias(filtro_status, filtro_periodo, ocultar_concluidos, usuario)

    resultado = []
    for o in ouvidorias:
        atribuicoes = list(o.atribuicoes)
        if atribuicoes:
            partes = []
            seen: set[str] = set()
            pendentes = []
            todos_responderam = True
            for at in atribuicoes:
                tec = at.tecnico
                if tec:
                    ger = tec.gerencia.nome if tec.gerencia else "?"
                    coord = tec.coordenacao.nome if tec.coordenacao else "?"
                    chave = f"{ger}-{coord}"
                    if chave not in seen:
                        partes.append(chave)
                        seen.add(chave)
                    if not at.respondido:
                        pendentes.append(tec.nome)
                        todos_responderam = False
            if todos_responderam:
                coord_ger = "SUCOL - Ouvidoria"
            else:
                coord_ger = " / ".join(partes) if partes else "Em análise"
            responsaveis = ", ".join(pendentes) if pendentes else "–"
        else:
            coord_ger = "SUCOL - Ouvidoria"
            responsaveis = "–"

        resultado.append({
            "id": o.id,
            "protocolo": o.protocolo or "–",
            "status": o.status,
            "prazo": o.prazo,
            "prazo_permissionaria": o.prazo_permissionaria,
            "coord_ger": coord_ger,
            "responsaveis": responsaveis,
        })
    return resultado


@st.cache_data(ttl=60)
def carregar_tecnicos_disponiveis():
    """Retorna lista de técnicos ativos: [(id, nome)]."""
    return [(t.id, t.nome) for t in get_tecnicos_ativos()]


def atribuir_tecnico(ouvidoria_id: int, tecnico_id: int):
    """Atribui técnico a ouvidoria. Retorna False se já atribuído."""
    return _atribuir_tecnico(ouvidoria_id, tecnico_id)


def excluir_ouvidoria(oid: int):
    """Exclui ouvidoria por id."""
    _excluir_ouvidoria(oid)


def concluir_ouvidoria(oid: int):
    """Marca ouvidoria como concluída."""
    _concluir_ouvidoria(oid)
