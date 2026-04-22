"""Queries ORM para o Dashboard de Qualidade (página 07)."""

from sqlalchemy import Date, String, case, cast, distinct, func

from database.connection import db_session
from models import (
    AutoLinha,
    Categoria,
    Ouvidoria,
    OuvidoriaTecnico,
    Permissionaria,
    Reclamacao,
    ReclamacaoAuto,
    StatusOuvidoria,
    Usuario,
)


def _base_qualidade(s, data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico):
    """Query base com joins e filtros comuns do dashboard de qualidade."""
    q = (
        s.query(Reclamacao)
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
    with db_session() as s:
        q = _base_qualidade(s, data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico)
        q = q.with_entities(
            func.count(distinct(Reclamacao.id)).label("total_rec"),
            func.coalesce(func.sum(ReclamacaoAuto.pontuacao), 0).label("pontuacao_total"),
            func.count(distinct(AutoLinha.id)).label("autos_unicos"),
        )
        row = q.one()
        return (int(row.total_rec), float(row.pontuacao_total), int(row.autos_unicos))


def query_top_permissionaria(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico):
    """Retorna (nome, pontuacao) da empresa com maior pontuação, ou None."""
    with db_session() as s:
        q = _base_qualidade(s, data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico)
        q = q.with_entities(
            Permissionaria.nome,
            func.round(func.coalesce(func.sum(ReclamacaoAuto.pontuacao), 0), 2).label("pts"),
        ).filter(Permissionaria.nome.isnot(None))
        q = q.group_by(Permissionaria.nome).order_by(func.sum(ReclamacaoAuto.pontuacao).desc()).limit(1)
        row = q.first()
        return (row[0], float(row[1])) if row else None


def query_top_categoria(data_ini, data_fim, ger_id, cat_list, tipo_servico):
    """Retorna nome da categoria mais reclamada ou '–'."""
    with db_session() as s:
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


def query_sla(data_ini, data_fim, ger_id):
    """Retorna (total, dentro_prazo)."""
    with db_session() as s:
        q = s.query(
            func.count(distinct(Ouvidoria.id)).label("total"),
            func.sum(case(
                (
                    (cast(Ouvidoria.status, String) == StatusOuvidoria.CONCLUIDO.value) &
                    (Ouvidoria.concluido_em != None) &  # noqa: E711
                    (cast(Ouvidoria.concluido_em, Date) <= Ouvidoria.prazo),
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


def query_evolucao_mensal(data_ini, data_fim, ger_id, cat_list, tipo_servico):
    """Retorna [(mes_str, total)] evolução mensal de reclamações."""
    with db_session() as s:
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


def query_top_autos_pontuacao(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico, top_n=20):
    """Retorna [(numero_auto, pontuacao, empresa)] top N autos por pontuação."""
    with db_session() as s:
        q = _base_qualidade(s, data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico)
        q = q.with_entities(
            AutoLinha.numero,
            func.coalesce(func.sum(ReclamacaoAuto.pontuacao), 0).label("pts"),
            Permissionaria.nome.label("empresa"),
        ).filter(AutoLinha.numero.isnot(None))
        q = q.group_by(AutoLinha.numero, Permissionaria.nome)
        q = q.order_by(func.sum(ReclamacaoAuto.pontuacao).desc()).limit(top_n)
        return q.all()


def query_empresas_pontuacao(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico):
    """Retorna [(empresa, pontuacao, num_reclamacoes)] top 20."""
    with db_session() as s:
        q = _base_qualidade(s, data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico)
        q = q.with_entities(
            Permissionaria.nome.label("empresa"),
            func.coalesce(func.sum(ReclamacaoAuto.pontuacao), 0).label("pts"),
            func.count(distinct(Reclamacao.id)).label("num_reclamacoes"),
        ).filter(Permissionaria.nome.isnot(None))
        q = q.group_by(Permissionaria.nome)
        q = q.order_by(func.sum(ReclamacaoAuto.pontuacao).desc()).limit(20)
        return q.all()


def query_categorias_pizza(data_ini, data_fim, ger_id, cat_list, tipo_servico):
    """Retorna [(categoria, total)] para gráfico pizza."""
    with db_session() as s:
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


def query_cidades(data_ini, data_fim, ger_id, tipo_servico, tipo_cidade="Ambos"):
    """Retorna [(cidade, total)] top 20 cidades.
    tipo_cidade: 'Embarque', 'Desembarque' ou 'Ambos'."""
    with db_session() as s:
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


def query_heatmap_cat_empresa(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico):
    """Retorna [(empresa, categoria, total)] para heatmap."""
    with db_session() as s:
        q = _base_qualidade(s, data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico)
        q = q.with_entities(
            Permissionaria.nome.label("empresa"),
            func.coalesce(Categoria.nome, "(sem)").label("categoria"),
            func.count(Reclamacao.id).label("total"),
        ).filter(Permissionaria.nome.isnot(None))
        q = q.group_by(Permissionaria.nome, "categoria")
        q = q.order_by(func.count(Reclamacao.id).desc())
        return q.all()


def query_tendencia_empresa(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico):
    """Retorna [(mes_str, empresa, total)] tendência mensal por empresa."""
    with db_session() as s:
        mes_col = func.to_char(func.date_trunc("month", Ouvidoria.criado_em), "YYYY-MM").label("mes")
        q = _base_qualidade(s, data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico)
        q = q.with_entities(
            mes_col,
            Permissionaria.nome.label("empresa"),
            func.count(Reclamacao.id).label("total"),
        ).filter(Permissionaria.nome.isnot(None))
        q = q.group_by(mes_col, Permissionaria.nome).order_by(mes_col)
        return q.all()


def query_tabela_analitica(data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico):
    """Retorna lista de tuplas para tabela analítica de autos."""
    with db_session() as s:
        q = _base_qualidade(s, data_ini, data_fim, ger_id, perm_id, cat_list, tipo_servico)
        q = q.with_entities(
            AutoLinha.numero.label("Auto"),
            cast(AutoLinha.tipo, String).label("Tipo"),
            AutoLinha.itinerario.label("Itinerario"),
            func.coalesce(Permissionaria.nome_fantasia, Permissionaria.nome, "–").label("Empresa"),
            func.coalesce(AutoLinha.denominacao_a, "–").label("Denominacao_A"),
            func.coalesce(AutoLinha.denominacao_b, "–").label("Denominacao_B"),
            func.count(distinct(Reclamacao.id)).label("Reclamacoes"),
            func.round(func.coalesce(func.sum(ReclamacaoAuto.pontuacao), 0), 4).label("Pontuacao"),
        ).filter(AutoLinha.numero.isnot(None))
        q = q.group_by(
            AutoLinha.numero, AutoLinha.tipo, AutoLinha.itinerario,
            Permissionaria.nome_fantasia, Permissionaria.nome,
            AutoLinha.denominacao_a, AutoLinha.denominacao_b,
        )
        q = q.order_by(func.coalesce(func.sum(ReclamacaoAuto.pontuacao), 0).desc())
        return q.all()
