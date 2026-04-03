"""Loaders de ouvidorias: formata objetos ORM para a interface."""

import streamlit as st

from models import TipoServico
from repositories.ouvidoria_repo import (
    get_atribuicao_tecnico,
    get_ouvidoria_completa,
    get_ouvidoria_permissionaria,
    get_respostas_tecnico,
)


def carregar_detalhe_ouvidoria(oid: int):
    """Carrega ouvidoria com todos os dados para a página de detalhe/edição.
    Retorna (ouvidoria, reclamacoes, rec_autos, atribuicoes, tecnicos_info, resp_info, resps_perm, anexos).
    Retorna tupla de Nones/vazios se não encontrada."""
    o = get_ouvidoria_completa(oid)
    if not o:
        return None, [], {}, [], {}, [], [], []

    recs_data = [
        {
            "id": r.id,
            "numero_item": r.numero_item,
            "categoria": r.categoria.nome if r.categoria else None,
            "subcategoria": r.subcategoria.nome if r.subcategoria else None,
            "tipo_servico": r.tipo_servico.value if r.tipo_servico else None,
            "local_embarque": r.local_embarque,
            "local_desembarque": r.local_desembarque,
            "descricao": r.descricao,
            "empresa_fretamento": r.empresa_fretamento,
        }
        for r in o.reclamacoes
    ]

    rec_autos = {}
    for r in o.reclamacoes:
        autos_info = []
        for ra in r.autos_vinculados:
            if ra.auto:
                autos_info.append({
                    "numero": ra.auto.numero,
                    "cidade_inicial": ra.auto.cidade_inicial or "?",
                    "cidade_final": ra.auto.cidade_final or "?",
                    "permissionaria": ra.auto.permissionaria.nome if ra.auto.permissionaria else "–",
                    "tipo": ra.auto.tipo.value if ra.auto.tipo else None,
                    "regiao_metropolitana": ra.auto.regiao_metropolitana,
                })
        rec_autos[r.id] = autos_info

    tecnicos_info = {}
    for at in o.atribuicoes:
        if at.tecnico:
            tecnicos_info[at.tecnico_id] = {
                "nome": at.tecnico.nome,
                "respondido": at.respondido,
                "respondido_em": at.respondido_em,
            }

    resp_info = [
        {
            "id": r.id,
            "tecnico": r.tecnico.nome if r.tecnico else "?",
            "data": r.data_resposta,
            "texto": r.texto_resposta,
        }
        for r in o.respostas
    ]

    resps_perm = [
        {
            "id": rp.id,
            "conteudo": rp.conteudo,
            "data_resposta": rp.data_resposta,
            "registrado_por": rp.registrado_por.nome if rp.registrado_por else "—",
            "criado_em": rp.criado_em,
        }
        for rp in o.respostas_permissionaria
    ]

    anexos = [
        {
            "id": an.id,
            "nome_arquivo": an.nome_arquivo,
            "nome_storage": an.nome_storage,
            "tipo_mime": an.tipo_mime,
            "tamanho": an.tamanho,
            "enviado_por": an.enviado_por.nome if an.enviado_por else "?",
            "criado_em": an.criado_em,
        }
        for an in o.anexos
    ]

    return o, recs_data, rec_autos, list(o.atribuicoes), tecnicos_info, resp_info, resps_perm, anexos


@st.cache_data(ttl=60)
def carregar_ouvidoria_para_permissionaria(_oid: int) -> dict | None:
    """Carrega ouvidoria com dados resumidos + respostas da permissionária."""
    o = get_ouvidoria_permissionaria(_oid)
    if not o:
        return None
    return {
        "id": o.id,
        "conteudo": o.conteudo,
        "status": o.status.value,
        "prazo": o.prazo,
        "prazo_permissionaria": o.prazo_permissionaria,
        "respostas_permissionaria": [
            {
                "id": r.id,
                "conteudo": r.conteudo,
                "data_resposta": r.data_resposta,
                "registrado_por": r.registrado_por.nome if r.registrado_por else "—",
                "criado_em": r.criado_em,
            }
            for r in o.respostas_permissionaria
        ],
    }


def carregar_ouvidoria_para_resposta_tecnica(oid: int, tecnico_id: int):
    """Carrega ouvidoria com dados para resposta técnica.
    Retorna (ouvidoria, atribuicao, reclamacoes, resposta_existente, resps_perm, anexos, resps_tecnico)."""
    o = get_ouvidoria_completa(oid)
    if not o:
        return None, None, [], None, [], [], []

    atribuicao = get_atribuicao_tecnico(oid, tecnico_id)

    recs_data = []
    for r in o.reclamacoes:
        autos_info = []
        for ra in r.autos_vinculados:
            if ra.auto:
                autos_info.append({
                    "id": ra.auto.id,
                    "numero": ra.auto.numero,
                    "cidade_ini": ra.auto.cidade_inicial or "?",
                    "cidade_fim": ra.auto.cidade_final or "?",
                    "permissionaria": ra.auto.permissionaria.nome if ra.auto.permissionaria else "–",
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

    respostas_tecnico = get_respostas_tecnico(oid, tecnico_id)
    resposta_existente = respostas_tecnico[0] if respostas_tecnico else None

    resps_perm = [
        {
            "id": rp.id,
            "conteudo": rp.conteudo,
            "data_resposta": rp.data_resposta,
            "registrado_por": rp.registrado_por.nome if rp.registrado_por else "—",
        }
        for rp in o.respostas_permissionaria
    ]

    anexos = [
        {
            "id": an.id,
            "nome_arquivo": an.nome_arquivo,
            "nome_storage": an.nome_storage,
            "tipo_mime": an.tipo_mime,
            "tamanho": an.tamanho,
        }
        for an in o.anexos
    ]

    resps_tecnico_data = [
        {
            "id": rt.id,
            "data_resposta": rt.data_resposta,
            "texto_resposta": rt.texto_resposta,
        }
        for rt in respostas_tecnico
    ]

    return o, atribuicao, recs_data, resposta_existente, resps_perm, anexos, resps_tecnico_data
