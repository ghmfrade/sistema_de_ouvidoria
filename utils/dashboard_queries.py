"""Queries ORM para os dashboards de Produtividade e Qualidade."""

from datetime import date

from sqlalchemy import Date, String, case, cast, distinct, func

from database.connection import get_session
from models import (
    AutoLinha,
    Categoria,
    Coordenacao,
    Ouvidoria,
    OuvidoriaTecnico,
    Permissionaria,
    Reclamacao,
    ReclamacaoAuto,
    RespostaTecnica,
    StatusOuvidoria,
    Usuario,
)


# ══════════════════════════════════════════════════════════════════════════════
# Helpers internos
# ══════════════════════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════════════════════
# Dashboard Produtividade (pagina 06)
# ══════════════════════════════════════════════════════════════════════════════

def query_kpis_produtividade(data_ini, data_fim, ger_id, status_list):
    """Retorna (total, concluidas, vencidas)."""
    s = get_session()
    try:
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
    finally:
        s.close()


def query_tempo_medio_resposta(data_ini, data_fim, ger_id, status_list):
    """Retorna media de dias para resposta tecnica ou None."""
    s = get_session()
    try:
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
    finally:
        s.close()


def query_volume_por_mes(data_ini, data_fim, ger_id, status_list):
    """Retorna [(mes_str, total)] agrupado por mes."""
    s = get_session()
    try:
        mes_col = func.to_char(func.date_trunc("month", Ouvidoria.criado_em), "YYYY-MM").label("mes")
        q = s.query(
            mes_col,
            func.count(distinct(Ouvidoria.id)).label("total"),
        )
        q = _apply_base_filters(q, data_ini, data_fim, ger_id, status_list)
        q = q.group_by(mes_col).order_by(mes_col)
        return q.all()
    finally:
        s.close()


def query_distribuicao_status(data_ini, data_fim, ger_id, status_list):
    """Retorna [(status_str, total)] ordenado por total desc."""
    s = get_session()
    try:
        q = s.query(
            cast(Ouvidoria.status, String).label("status"),
            func.count(distinct(Ouvidoria.id)).label("total"),
        )
        q = _apply_base_filters(q, data_ini, data_fim, ger_id, status_list)
        q = q.group_by(Ouvidoria.status).order_by(func.count(distinct(Ouvidoria.id)).desc())
        return q.all()
    finally:
        s.close()


def query_vencidas_por_coordenacao(data_ini, data_fim):
    """Retorna [(coordenacao_nome, total)] top 15 coordenacoes com ouvidorias vencidas."""
    s = get_session()
    try:
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
    finally:
        s.close()


def query_tempo_medio_por_tecnico(data_ini, data_fim):
    """Retorna [(tecnico_nome, media_dias)] top 15."""
    s = get_session()
    try:
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
    finally:
        s.close()


def query_ranking_coordenacoes(data_ini, data_fim, ger_id, status_list):
    """Retorna [(coordenacao_nome, total)] top 15 por volume."""
    s = get_session()
    try:
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
    finally:
        s.close()


# ══════════════════════════════════════════════════════════════════════════════
# Dashboard Qualidade (pagina 07)
# ══════════════════════════════════════════════════════════════════════════════

def _base_qualidade(session, data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico):
    """Retorna query base com joins e filtros comuns do dashboard de qualidade.
    A query ja tem: Reclamacao JOIN Ouvidoria, LEFT JOIN ReclamacaoAuto/AutoLinha/Permissionaria/Categoria.
    O chamador adiciona colunas via .with_entities() ou constroi a propria query usando os filtros."""
    from sqlalchemy.orm import Query
    q = (
        session.query(Reclamacao)
        .join(Ouvidoria, Ouvidoria.id == Reclamacao.ouvidoria_id)
        .outerjoin(ReclamacaoAuto, ReclamacaoAuto.reclamacao_id == Reclamacao.id)
        .outerjoin(AutoLinha, AutoLinha.id == ReclamacaoAuto.auto_id)
        .outerjoin(Permissionaria, Permissionaria.id == AutoLinha.permissionaria_id)
        .outerjoin(Categoria, Categoria.id == Reclamacao.categoria_id)
        .filter(cast(Ouvidoria.criado_em, Date).between(data_ini, data_fim))
    )
    if ger_id:
        q = (
            q.join(OuvidoriaTecnico, OuvidoriaTecnico.ouvidoria_id == Ouvidoria.id)
            .join(Usuario, Usuario.id == OuvidoriaTecnico.tecnico_id)
            .filter(Usuario.gerencia_id == ger_id)
        )
    if perm_id:
        q = q.filter(AutoLinha.permissionaria_id == perm_id)
    if cat_list:
        q = q.filter(Categoria.nome.in_(cat_list))
    if tipo_servico:
        q = q.filter(cast(AutoLinha.tipo, String) == tipo_servico)
    return q


def query_kpis_qualidade(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico):
    """Retorna (total_reclamacoes, pontuacao_total, autos_unicos)."""
    s = get_session()
    try:
        q = _base_qualidade(s, data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico)
        q = q.with_entities(
            func.count(distinct(Reclamacao.id)).label("total_rec"),
            func.coalesce(func.sum(ReclamacaoAuto.pontuacao), 0).label("pontuacao_total"),
            func.count(distinct(AutoLinha.id)).label("autos_unicos"),
        )
        row = q.one()
        return (int(row.total_rec), float(row.pontuacao_total), int(row.autos_unicos))
    finally:
        s.close()


def query_top_permissionaria(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico):
    """Retorna (nome, pontuacao) da empresa com maior pontuacao, ou None."""
    s = get_session()
    try:
        q = _base_qualidade(s, data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico)
        q = q.with_entities(
            Permissionaria.nome,
            func.round(func.coalesce(func.sum(ReclamacaoAuto.pontuacao), 0), 2).label("pts"),
        ).filter(Permissionaria.nome.isnot(None))
        q = q.group_by(Permissionaria.nome).order_by(func.sum(ReclamacaoAuto.pontuacao).desc()).limit(1)
        row = q.first()
        return (row[0], float(row[1])) if row else None
    finally:
        s.close()


def query_top_categoria(data_ini, data_fim, ger_id, cat_list, tipo_servico):
    """Retorna nome da categoria mais reclamada ou '–'."""
    s = get_session()
    try:
        q = (
            s.query(
                Categoria.nome,
                func.count(Reclamacao.id).label("total"),
            )
            .join(Ouvidoria, Ouvidoria.id == Reclamacao.ouvidoria_id)
            .join(Categoria, Categoria.id == Reclamacao.categoria_id)
            .filter(cast(Ouvidoria.criado_em, Date).between(data_ini, data_fim))
        )
        if ger_id:
            q = (
                q.join(OuvidoriaTecnico, OuvidoriaTecnico.ouvidoria_id == Ouvidoria.id)
                .join(Usuario, Usuario.id == OuvidoriaTecnico.tecnico_id)
                .filter(Usuario.gerencia_id == ger_id)
            )
        if cat_list:
            q = q.filter(Categoria.nome.in_(cat_list))
        if tipo_servico:
            q = q.filter(cast(Reclamacao.tipo_servico, String) == tipo_servico)
        q = q.group_by(Categoria.nome).order_by(func.count(Reclamacao.id).desc()).limit(1)
        row = q.first()
        return row[0] if row else "–"
    finally:
        s.close()


def query_sla(data_ini, data_fim, ger_id):
    """Retorna (total, dentro_prazo)."""
    s = get_session()
    try:
        q = s.query(
            func.count(distinct(Ouvidoria.id)).label("total"),
            func.sum(case(
                (
                    (cast(Ouvidoria.status, String) == StatusOuvidoria.CONCLUIDO.value) &
                    (cast(Ouvidoria.atualizado_em, Date) <= Ouvidoria.prazo),
                    1,
                ),
                else_=0,
            )).label("dentro_prazo"),
        ).filter(cast(Ouvidoria.criado_em, Date).between(data_ini, data_fim))
        if ger_id:
            q = (
                q.join(OuvidoriaTecnico, OuvidoriaTecnico.ouvidoria_id == Ouvidoria.id)
                .join(Usuario, Usuario.id == OuvidoriaTecnico.tecnico_id)
                .filter(Usuario.gerencia_id == ger_id)
            )
        row = q.one()
        return (int(row.total or 0), int(row.dentro_prazo or 0))
    finally:
        s.close()


def query_evolucao_mensal(data_ini, data_fim, ger_id, cat_list, tipo_servico):
    """Retorna [(mes_str, total)] evolucao mensal de reclamacoes."""
    s = get_session()
    try:
        mes_col = func.to_char(func.date_trunc("month", Ouvidoria.criado_em), "YYYY-MM").label("mes")
        q = (
            s.query(
                mes_col,
                func.count(Reclamacao.id).label("total"),
            )
            .join(Ouvidoria, Ouvidoria.id == Reclamacao.ouvidoria_id)
            .outerjoin(Categoria, Categoria.id == Reclamacao.categoria_id)
            .filter(cast(Ouvidoria.criado_em, Date).between(data_ini, data_fim))
        )
        if ger_id:
            q = (
                q.join(OuvidoriaTecnico, OuvidoriaTecnico.ouvidoria_id == Ouvidoria.id)
                .join(Usuario, Usuario.id == OuvidoriaTecnico.tecnico_id)
                .filter(Usuario.gerencia_id == ger_id)
            )
        if cat_list:
            q = q.filter(Categoria.nome.in_(cat_list))
        if tipo_servico:
            q = q.filter(cast(Reclamacao.tipo_servico, String) == tipo_servico)
        q = q.group_by(mes_col).order_by(mes_col)
        return q.all()
    finally:
        s.close()


def query_top_autos_pontuacao(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico, top_n=20):
    """Retorna [(numero_auto, pontuacao, empresa)] top N autos por pontuacao."""
    s = get_session()
    try:
        q = _base_qualidade(s, data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico)
        q = q.with_entities(
            AutoLinha.numero,
            func.coalesce(func.sum(ReclamacaoAuto.pontuacao), 0).label("pts"),
            Permissionaria.nome.label("empresa"),
        ).filter(AutoLinha.numero.isnot(None))
        q = q.group_by(AutoLinha.numero, Permissionaria.nome)
        q = q.order_by(func.sum(ReclamacaoAuto.pontuacao).desc()).limit(top_n)
        return q.all()
    finally:
        s.close()


def query_empresas_pontuacao(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico):
    """Retorna [(empresa, pontuacao, num_reclamacoes)] top 20."""
    s = get_session()
    try:
        q = _base_qualidade(s, data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico)
        q = q.with_entities(
            Permissionaria.nome.label("empresa"),
            func.coalesce(func.sum(ReclamacaoAuto.pontuacao), 0).label("pts"),
            func.count(distinct(Reclamacao.id)).label("num_reclamacoes"),
        ).filter(Permissionaria.nome.isnot(None))
        q = q.group_by(Permissionaria.nome)
        q = q.order_by(func.sum(ReclamacaoAuto.pontuacao).desc()).limit(20)
        return q.all()
    finally:
        s.close()


def query_categorias_pizza(data_ini, data_fim, ger_id, cat_list, tipo_servico):
    """Retorna [(categoria, total)] para grafico pizza."""
    s = get_session()
    try:
        q = (
            s.query(
                func.coalesce(Categoria.nome, "(sem categoria)").label("categoria"),
                func.count(Reclamacao.id).label("total"),
            )
            .join(Ouvidoria, Ouvidoria.id == Reclamacao.ouvidoria_id)
            .outerjoin(Categoria, Categoria.id == Reclamacao.categoria_id)
            .filter(cast(Ouvidoria.criado_em, Date).between(data_ini, data_fim))
        )
        if ger_id:
            q = (
                q.join(OuvidoriaTecnico, OuvidoriaTecnico.ouvidoria_id == Ouvidoria.id)
                .join(Usuario, Usuario.id == OuvidoriaTecnico.tecnico_id)
                .filter(Usuario.gerencia_id == ger_id)
            )
        if cat_list:
            q = q.filter(Categoria.nome.in_(cat_list))
        if tipo_servico:
            q = q.filter(cast(Reclamacao.tipo_servico, String) == tipo_servico)
        q = q.group_by("categoria").order_by(func.count(Reclamacao.id).desc())
        return q.all()
    finally:
        s.close()


def query_cidades(data_ini, data_fim, ger_id, tipo_servico, tipo_cidade="Ambos"):
    """Retorna [(cidade, total)] top 20 cidades.
    tipo_cidade: 'Embarque', 'Desembarque' ou 'Ambos'."""
    s = get_session()
    try:
        def _city_query(campo):
            q = (
                s.query(
                    campo.label("cidade"),
                    func.count().label("total"),
                )
                .join(Ouvidoria, Ouvidoria.id == Reclamacao.ouvidoria_id)
                .filter(
                    cast(Ouvidoria.criado_em, Date).between(data_ini, data_fim),
                    campo.isnot(None),
                    campo != "",
                )
            )
            if ger_id:
                q = (
                    q.join(OuvidoriaTecnico, OuvidoriaTecnico.ouvidoria_id == Ouvidoria.id)
                    .join(Usuario, Usuario.id == OuvidoriaTecnico.tecnico_id)
                    .filter(Usuario.gerencia_id == ger_id)
                )
            if tipo_servico:
                q = q.filter(cast(Reclamacao.tipo_servico, String) == tipo_servico)
            return q

        if tipo_cidade == "Embarque":
            q = _city_query(Reclamacao.local_embarque)
            q = q.group_by(Reclamacao.local_embarque).order_by(func.count().desc()).limit(20)
        elif tipo_cidade == "Desembarque":
            q = _city_query(Reclamacao.local_desembarque)
            q = q.group_by(Reclamacao.local_desembarque).order_by(func.count().desc()).limit(20)
        else:
            # Ambos: union de embarque + desembarque
            q_emb = _city_query(Reclamacao.local_embarque).group_by(Reclamacao.local_embarque)
            q_des = _city_query(Reclamacao.local_desembarque).group_by(Reclamacao.local_desembarque)
            union = q_emb.union_all(q_des).subquery()
            q = (
                s.query(union.c.cidade, func.sum(union.c.total).label("total"))
                .group_by(union.c.cidade)
                .order_by(func.sum(union.c.total).desc())
                .limit(20)
            )
        return q.all()
    finally:
        s.close()


def query_heatmap_cat_empresa(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico):
    """Retorna [(empresa, categoria, total)] para heatmap."""
    s = get_session()
    try:
        q = _base_qualidade(s, data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico)
        q = q.with_entities(
            Permissionaria.nome.label("empresa"),
            func.coalesce(Categoria.nome, "(sem)").label("categoria"),
            func.count(Reclamacao.id).label("total"),
        ).filter(Permissionaria.nome.isnot(None))
        q = q.group_by(Permissionaria.nome, "categoria")
        q = q.order_by(func.count(Reclamacao.id).desc())
        return q.all()
    finally:
        s.close()


def query_tendencia_empresa(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico):
    """Retorna [(mes_str, empresa, total)] tendencia mensal por empresa."""
    s = get_session()
    try:
        mes_col = func.to_char(func.date_trunc("month", Ouvidoria.criado_em), "YYYY-MM").label("mes")
        q = _base_qualidade(s, data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico)
        q = q.with_entities(
            mes_col,
            Permissionaria.nome.label("empresa"),
            func.count(Reclamacao.id).label("total"),
        ).filter(Permissionaria.nome.isnot(None))
        q = q.group_by(mes_col, Permissionaria.nome).order_by(mes_col)
        return q.all()
    finally:
        s.close()


def query_tabela_analitica(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico):
    """Retorna lista de tuplas para tabela analitica de autos."""
    s = get_session()
    try:
        q = _base_qualidade(s, data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico)
        q = q.with_entities(
            AutoLinha.numero.label("Auto"),
            cast(AutoLinha.tipo, String).label("Tipo"),
            AutoLinha.itinerario.label("Itinerario"),
            func.coalesce(Permissionaria.nome, "–").label("Empresa"),
            func.coalesce(AutoLinha.cidade_inicial, "–").label("Cidade_Inicial"),
            func.coalesce(AutoLinha.cidade_final, "–").label("Cidade_Final"),
            func.count(distinct(Reclamacao.id)).label("Reclamacoes"),
            func.round(func.coalesce(func.sum(ReclamacaoAuto.pontuacao), 0), 4).label("Pontuacao"),
        ).filter(AutoLinha.numero.isnot(None))
        q = q.group_by(
            AutoLinha.numero, AutoLinha.tipo, AutoLinha.itinerario,
            Permissionaria.nome, AutoLinha.cidade_inicial, AutoLinha.cidade_final,
        )
        q = q.order_by(func.coalesce(func.sum(ReclamacaoAuto.pontuacao), 0).desc())
        return q.all()
    finally:
        s.close()
