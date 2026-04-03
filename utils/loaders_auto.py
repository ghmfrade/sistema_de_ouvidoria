"""Loaders de autos de linha, cidades, permissionárias e regiões metropolitanas."""

import streamlit as st

from repositories.autos_repo import (
    buscar_autos_por_trecho as _buscar_autos_por_trecho,
    get_autos_regioes_metropolitanas,
    get_municipios_com_paradas,
    get_municipios_destino,
    get_permissionarias,
    get_todos_autos,
)
from repositories.municipios_repo import (
    get_municipios_por_tipo_servico,
    get_municipios_sp,
)


@st.cache_data(ttl=300)
def carregar_cidades_por_tipo(tipo_servico: str):
    """Cidades de origem filtradas pelo tipo de serviço, ordenadas."""
    if "Fretamento" in tipo_servico:
        return [m.nome for m in get_municipios_sp()]
    return sorted([m.nome for m in get_municipios_por_tipo_servico(tipo_servico) if m.nome])


@st.cache_data(ttl=300)
def carregar_cidades(tipo_servico: str, perm_id: int | None = None, regiao: str | None = None):
    """Cidades para busca por trecho, ordenadas."""
    return sorted([m.nome for m in get_municipios_com_paradas(tipo_servico, perm_id, regiao) if m.nome])


def carregar_cidades_destino(tipo_servico: str, nome_origem: str,
                             perm_id: int | None = None, regiao: str | None = None):
    """Cidades alcançáveis a partir da origem, ordenadas."""
    if "Fretamento" in tipo_servico:
        return [m.nome for m in get_municipios_sp() if m.nome != nome_origem]
    return sorted([m.nome for m in get_municipios_destino(tipo_servico, nome_origem, perm_id, regiao) if m.nome])


@st.cache_data(ttl=300)
def carregar_todos_autos(tipo_servico: str, perm_id: int | None = None, regiao: str | None = None):
    """Todos os autos filtrados: [(id, numero, cidade_ini, cidade_fim, empresa)]."""
    return [
        (a.id, a.numero, a.cidade_inicial or "", a.cidade_final or "",
         a.permissionaria.nome if a.permissionaria else "")
        for a in get_todos_autos(tipo_servico, perm_id, regiao)
    ]


@st.cache_data(ttl=300)
def carregar_permissionarias(tipo_servico: str, regiao: str | None = None):
    """Permissionárias com autos do tipo informado: [(id, nome)]."""
    return [(p.id, p.nome) for p in get_permissionarias(tipo_servico, regiao)]


@st.cache_data(ttl=300)
def carregar_regioes_metropolitanas():
    """Regiões metropolitanas distintas, ordenadas e limpas."""
    return sorted(
        {a.regiao_metropolitana.strip() for a in get_autos_regioes_metropolitanas() if a.regiao_metropolitana}
        )


def buscar_autos_por_trecho(tipo_servico: str, cidade_a: str, cidade_b: str,
                            perm_id: int | None = None, regiao: str | None = None):
    """Autos que possuem paradas em AMBAS as cidades: [(id, numero, cidade_ini, cidade_fim, empresa)]."""
    return [
        (a.id, a.numero, a.cidade_inicial or "", a.cidade_final or "",
         a.permissionaria.nome if a.permissionaria else "")
        for a in _buscar_autos_por_trecho(tipo_servico, cidade_a, cidade_b, perm_id, regiao)
    ]
