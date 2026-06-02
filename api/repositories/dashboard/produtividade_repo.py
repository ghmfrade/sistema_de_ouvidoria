"""Queries ORM para o Dashboard de Produtividade (página 06)."""

from datetime import date

from sqlalchemy import Date, String, case, cast, distinct, func

from api.database.connection import db_session
from api.models import (
    Coordenacao,
    Ouvidoria,
    OuvidoriaTecnico,
    RespostaTecnica,
    StatusOuvidoria,
    Usuario,
)


def _apply_base_filters(q, data_ini, data_fim, ger_id, status_list):
    """Aplica filtros comuns do dashboard de produtividade."""
    q = q.filter(cast(Ouvidoria.criado_em, Date).between(data_ini, data_fim))
    if ger_id:
        q = (
            q.join(OuvidoriaTecnico, OuvidoriaTecnico.ouvidoria_id == Ouvidoria.id)
            .join(Usuario, Usuario.id == OuvidoriaTecnico.tecnico_id)
            .filter(Usuario.gerencia_id == ger_id)
        )
    if status_list:
        q = q.filter(cast(Ouvidoria.status, String).in_(status_list))
    return q


def query_kpis_produtividade(data_ini, data_fim, ger_id, status_list):
    """Retorna (total, concluidas, vencidas)."""
    with db_session() as s:
        q = s.query(
            func.count(distinct(Ouvidoria.id)).label("total"),
            func.sum(case(
                (cast(Ouvidoria.status, String) == StatusOuvidoria.CONCLUIDO.value, 1),
                else_=0,
            )).label("concluidas"),
            func.sum(case(
                (
                    (Ouvidoria.prazo < func.current_date()) &
                    (cast(Ouvidoria.status, String) != StatusOuvidoria.CONCLUIDO.value),
                    1,
                ),
                else_=0,
            )).label("vencidas"),
        )
        q = _apply_base_filters(q, data_ini, data_fim, ger_id, status_list)
        row = q.one()
        return (row.total or 0, row.concluidas or 0, row.vencidas or 0)


def query_tempo_medio_resposta(data_ini, data_fim, ger_id, status_list):
    """Retorna média de dias para resposta técnica ou None."""
    with db_session() as s:
        q = s.query(
            func.avg(RespostaTecnica.data_resposta - cast(Ouvidoria.criado_em, Date)).label("media_dias"),
        ).join(Ouvidoria, Ouvidoria.id == RespostaTecnica.ouvidoria_id)

        q = q.filter(cast(Ouvidoria.criado_em, Date).between(data_ini, data_fim))
        if ger_id:
            q = (
                q.join(OuvidoriaTecnico, OuvidoriaTecnico.ouvidoria_id == Ouvidoria.id)
                .join(Usuario, Usuario.id == OuvidoriaTecnico.tecnico_id)
                .filter(Usuario.gerencia_id == ger_id)
            )
        if status_list:
            q = q.filter(cast(Ouvidoria.status, String).in_(status_list))
        row = q.one()
        return round(float(row.media_dias), 1) if row.media_dias else None


def query_volume_por_mes(data_ini, data_fim, ger_id, status_list):
    """Retorna [(mes_str, total)] agrupado por mês."""
    with db_session() as s:
        mes_col = func.to_char(func.date_trunc("month", Ouvidoria.criado_em), "YYYY-MM").label("mes")
        q = s.query(
            mes_col,
            func.count(distinct(Ouvidoria.id)).label("total"),
        )
        q = _apply_base_filters(q, data_ini, data_fim, ger_id, status_list)
        q = q.group_by(mes_col).order_by(mes_col)
        return q.all()


def query_distribuicao_status(data_ini, data_fim, ger_id, status_list):
    """Retorna [(status_str, total)] ordenado por total desc."""
    with db_session() as s:
        q = s.query(
            cast(Ouvidoria.status, String).label("status"),
            func.count(distinct(Ouvidoria.id)).label("total"),
        )
        q = _apply_base_filters(q, data_ini, data_fim, ger_id, status_list)
        q = q.group_by(Ouvidoria.status).order_by(func.count(distinct(Ouvidoria.id)).desc())
        return q.all()


def query_vencidas_por_coordenacao(data_ini, data_fim):
    """Retorna [(coordenacao_nome, total)] top 15 coordenações com ouvidorias vencidas."""
    with db_session() as s:
        q = (
            s.query(
                Coordenacao.nome.label("coordenacao"),
                func.count(distinct(Ouvidoria.id)).label("total"),
            )
            .join(OuvidoriaTecnico, OuvidoriaTecnico.ouvidoria_id == Ouvidoria.id)
            .join(Usuario, Usuario.id == OuvidoriaTecnico.tecnico_id)
            .join(Coordenacao, Coordenacao.id == Usuario.coordenacao_id)
            .filter(
                Ouvidoria.prazo < func.current_date(),
                cast(Ouvidoria.status, String) != StatusOuvidoria.CONCLUIDO.value,
                cast(Ouvidoria.criado_em, Date).between(data_ini, data_fim),
            )
            .group_by(Coordenacao.nome)
            .order_by(func.count(distinct(Ouvidoria.id)).desc())
            .limit(15)
        )
        return q.all()


def query_tempo_medio_por_tecnico(data_ini, data_fim):
    """Retorna [(tecnico_nome, media_dias)] top 15."""
    with db_session() as s:
        q = (
            s.query(
                Usuario.nome.label("tecnico"),
                func.avg(RespostaTecnica.data_resposta - cast(Ouvidoria.criado_em, Date)).label("media_dias"),
            )
            .join(Ouvidoria, Ouvidoria.id == RespostaTecnica.ouvidoria_id)
            .join(Usuario, Usuario.id == RespostaTecnica.tecnico_id)
            .filter(cast(Ouvidoria.criado_em, Date).between(data_ini, data_fim))
            .group_by(Usuario.nome)
            .order_by(func.avg(RespostaTecnica.data_resposta - cast(Ouvidoria.criado_em, Date)).desc())
            .limit(15)
        )
        return q.all()


def query_ranking_coordenacoes(data_ini, data_fim, ger_id, status_list):
    """Retorna [(coordenacao_nome, total)] top 15 por volume."""
    with db_session() as s:
        q = (
            s.query(
                Coordenacao.nome.label("coordenacao"),
                func.count(distinct(Ouvidoria.id)).label("total"),
            )
            .join(OuvidoriaTecnico, OuvidoriaTecnico.ouvidoria_id == Ouvidoria.id)
            .join(Usuario, Usuario.id == OuvidoriaTecnico.tecnico_id)
            .join(Coordenacao, Coordenacao.id == Usuario.coordenacao_id)
            .filter(cast(Ouvidoria.criado_em, Date).between(data_ini, data_fim))
        )
        if ger_id:
            q = q.filter(Usuario.gerencia_id == ger_id)
        if status_list:
            q = q.filter(cast(Ouvidoria.status, String).in_(status_list))
        q = q.group_by(Coordenacao.nome).order_by(func.count(distinct(Ouvidoria.id)).desc()).limit(15)
        return q.all()
