"""Loaders de dados de ouvidorias especificas: detalhe, resposta permissionaria, resposta tecnica."""

import streamlit as st

from database.connection import get_session
from models import (
    AutoLinha,
    Ouvidoria,
    OuvidoriaTecnico,
    RespostaTecnica,
    TipoServico,
    Usuario,
)


def carregar_detalhe_ouvidoria(oid: int):
    """Carrega ouvidoria com todos os dados para a pagina de detalhe/edicao.
    Retorna (ouvidoria, reclamacoes, rec_autos, atribuicoes, tecnicos_info, resp_info, resps_perm, anexos).
    Retorna tupla de Nones se nao encontrada."""
    session = get_session()
    try:
        o = session.query(Ouvidoria).filter_by(id=oid).first()
        if not o:
            return None, [], {}, [], {}, [], [], []
        atribuicoes = list(o.atribuicoes)
        respostas = list(o.respostas)

        # Reclamacoes
        recs_data = []
        for r in o.reclamacoes:
            recs_data.append({
                "id": r.id,
                "numero_item": r.numero_item,
                "categoria": r.categoria.nome if r.categoria else None,
                "subcategoria": r.subcategoria.nome if r.subcategoria else None,
                "tipo_servico": r.tipo_servico.value if r.tipo_servico else None,
                "local_embarque": r.local_embarque,
                "local_desembarque": r.local_desembarque,
                "descricao": r.descricao,
                "empresa_fretamento": r.empresa_fretamento,
            })

        # Autos de cada reclamacao
        rec_autos = {}
        for r in o.reclamacoes:
            autos_info = []
            for ra in r.autos_vinculados:
                auto = session.query(AutoLinha).filter_by(id=ra.auto_id).first()
                if auto:
                    perm_nome = auto.permissionaria.nome if auto.permissionaria else "–"
                    autos_info.append({
                        "numero": auto.numero,
                        "cidade_inicial": auto.cidade_inicial or "?",
                        "cidade_final": auto.cidade_final or "?",
                        "permissionaria": perm_nome,
                        "tipo": auto.tipo.value if auto.tipo else None,
                        "regiao_metropolitana": auto.regiao_metropolitana,
                    })
            rec_autos[r.id] = autos_info

        # Tecnicos
        tecnicos_info = {}
        for at in atribuicoes:
            tec = session.query(Usuario).filter_by(id=at.tecnico_id).first()
            if tec:
                tecnicos_info[at.tecnico_id] = {
                    "nome": tec.nome,
                    "respondido": at.respondido,
                    "respondido_em": at.respondido_em,
                }

        # Respostas tecnicas
        resp_info = []
        for r in respostas:
            tec = session.query(Usuario).filter_by(id=r.tecnico_id).first()
            resp_info.append({
                "id": r.id,
                "tecnico": tec.nome if tec else "?",
                "data": r.data_resposta,
                "texto": r.texto_resposta,
            })

        # Respostas da permissionaria
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
                "enviado_por": an.enviado_por.nome if an.enviado_por else "?",
                "criado_em": an.criado_em,
            })

        session.expunge_all()
        return o, recs_data, rec_autos, atribuicoes, tecnicos_info, resp_info, resps_perm, anexos
    finally:
        session.close()


@st.cache_data(ttl=60)
def carregar_ouvidoria_para_permissionaria(_oid: int) -> dict | None:
    """Carrega ouvidoria com dados resumidos + respostas da permissionaria.
    Retorna dict ou None se nao encontrada."""
    session = get_session()
    try:
        o = session.get(Ouvidoria, _oid)
        if not o:
            return None
        resps = []
        for r in o.respostas_permissionaria:
            resps.append(
                {
                    "id": r.id,
                    "conteudo": r.conteudo,
                    "data_resposta": r.data_resposta,
                    "registrado_por": r.registrado_por.nome if r.registrado_por else "—",
                    "criado_em": r.criado_em,
                }
            )
        return {
            "id": o.id,
            "conteudo": o.conteudo,
            "status": o.status.value,
            "prazo": o.prazo,
            "prazo_permissionaria": o.prazo_permissionaria,
            "respostas_permissionaria": resps,
        }
    finally:
        session.close()


def carregar_ouvidoria_para_resposta_tecnica(oid: int, tecnico_id: int):
    """Carrega ouvidoria com dados para resposta tecnica.
    Retorna (ouvidoria, atribuicao, reclamacoes, resposta_existente, resps_perm, anexos, resps_tecnico)."""
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

        # Busca TODAS as respostas tecnicas deste tecnico para esta ouvidoria
        respostas_tecnico = (
            session.query(RespostaTecnica)
            .filter_by(ouvidoria_id=oid, tecnico_id=tecnico_id)
            .order_by(RespostaTecnica.data_resposta.desc())
            .all()
        )
        resposta_existente = respostas_tecnico[0] if respostas_tecnico else None

        # Respostas da permissionaria
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

        # Serializa respostas tecnicas anteriores
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
