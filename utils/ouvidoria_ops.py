"""Operacoes sobre ouvidorias: listar, atribuir tecnicos, excluir, concluir."""

import streamlit as st

from database.connection import db_session, get_session
from models import (
    Ouvidoria,
    OuvidoriaTecnico,
    StatusOuvidoria,
    TipoUsuario,
    Usuario,
)


def listar_ouvidorias(filtro_status=None, filtro_periodo=None, ocultar_concluidos=True, usuario=None):
    """Retorna lista de ouvidorias com filtros aplicados.
    Se usuario for tecnico, retorna apenas as atribuidas a ele."""
    session = get_session()
    try:
        q = session.query(Ouvidoria)
        if usuario and usuario.tipo == TipoUsuario.tecnico:
            q = (
                q.join(OuvidoriaTecnico, OuvidoriaTecnico.ouvidoria_id == Ouvidoria.id)
                .filter(OuvidoriaTecnico.tecnico_id == usuario.id)
            )
        if filtro_status:
            q = q.filter(Ouvidoria.status == filtro_status)
        elif ocultar_concluidos:
            q = q.filter(Ouvidoria.status != StatusOuvidoria.CONCLUIDO)
        if filtro_periodo:
            inicio, fim = filtro_periodo
            q = q.filter(Ouvidoria.criado_em >= inicio, Ouvidoria.criado_em <= fim)
        ouvidorias = q.order_by(Ouvidoria.prazo.asc()).all()

        resultado = []
        for o in ouvidorias:
            atribuicoes = session.query(OuvidoriaTecnico).filter_by(ouvidoria_id=o.id).all()
            if atribuicoes:
                partes = []
                seen: set[str] = set()
                pendentes = []
                todos_responderam = True
                for at in atribuicoes:
                    tec = session.query(Usuario).filter_by(id=at.tecnico_id).first()
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
    finally:
        session.close()


@st.cache_data(ttl=60)
def carregar_tecnicos_disponiveis():
    """Retorna lista de tecnicos ativos: [(id, nome)]."""
    session = get_session()
    try:
        tecs = (
            session.query(Usuario)
            .filter_by(tipo=TipoUsuario.tecnico, ativo=True)
            .order_by(Usuario.nome)
            .all()
        )
        return [(t.id, t.nome) for t in tecs]
    finally:
        session.close()


def atribuir_tecnico(ouvidoria_id: int, tecnico_id: int):
    """Atribui tecnico a ouvidoria. Retorna False se ja atribuido."""
    with db_session() as s:
        existe = s.query(OuvidoriaTecnico).filter_by(
            ouvidoria_id=ouvidoria_id, tecnico_id=tecnico_id
        ).first()
        if existe:
            return False
        s.add(OuvidoriaTecnico(ouvidoria_id=ouvidoria_id, tecnico_id=tecnico_id))
        o = s.query(Ouvidoria).filter_by(id=ouvidoria_id).first()
        if o and o.status == StatusOuvidoria.AGUARDANDO_ACOES:
            o.status = StatusOuvidoria.EM_ANALISE_TECNICA
    return True


def excluir_ouvidoria(oid: int):
    """Exclui ouvidoria por id."""
    with db_session() as s:
        o = s.query(Ouvidoria).filter_by(id=oid).first()
        if o:
            s.delete(o)


def concluir_ouvidoria(oid: int):
    """Marca ouvidoria como concluida."""
    with db_session() as s:
        o = s.query(Ouvidoria).filter_by(id=oid).first()
        if o:
            o.status = StatusOuvidoria.CONCLUIDO
