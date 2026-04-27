"""Queries ORM para o Relatório de Reclamações (script relatorios/gerar_reclamacoes.py).

Filtro fixo: apenas registros da Categoria "Reclamação".
Padrão idêntico ao de repositories/dashboard/qualidade_repo.py.
"""

from datetime import date

from sqlalchemy import Date, String, cast, distinct, func, or_

from database.connection import db_session
from models import (
    AutoLinha,
    Categoria,
    Ouvidoria,
    Permissionaria,
    Reclamacao,
    ReclamacaoAuto,
    Subcategoria,
)

CATEGORIA_RECLAMACAO = "RECLAMAÇÃO"
SUBCAT_EXCLUIR_PONTUACAO = "TRANSPORTE IRREGULAR / CLANDESTINO"

# Filtro que exclui a subcategoria acima do somatório de pontuação,
# mas mantém reclamações sem subcategoria (NULL) no cálculo.
def _excluir_transporte_irregular(q):
    return q.filter(
        or_(
            Subcategoria.nome != SUBCAT_EXCLUIR_PONTUACAO,
            Subcategoria.nome.is_(None),
        )
    )


def _base_rec(s, ano: int, tipos: list[str]):
    """Query base filtrada por ano, categoria Reclamação e tipos de serviço."""
    data_ini = date(ano, 1, 1)
    data_fim = date(ano, 12, 31)
    return (
        s.query(Reclamacao)
        .join(Ouvidoria, Ouvidoria.id == Reclamacao.ouvidoria_id)
        .join(Categoria, Categoria.id == Reclamacao.categoria_id)
        .outerjoin(Subcategoria, Subcategoria.id == Reclamacao.subcategoria_id)
        .outerjoin(ReclamacaoAuto, ReclamacaoAuto.reclamacao_id == Reclamacao.id)
        .outerjoin(AutoLinha, AutoLinha.id == ReclamacaoAuto.auto_id)
        .outerjoin(Permissionaria, Permissionaria.id == AutoLinha.permissionaria_id)
        .filter(
            cast(Ouvidoria.criado_em, Date).between(data_ini, data_fim),
            Categoria.nome == CATEGORIA_RECLAMACAO,
            cast(Reclamacao.tipo_servico, String).in_(tipos),
        )
    )


# ─── KPIs ─────────────────────────────────────────────────────────────────────

def query_kpis_sistema(ano: int, tipos: list[str]) -> tuple[int, str, int]:
    """Retorna (total_reclamacoes, top_assunto, top_assunto_cnt)."""
    assunto_expr = func.coalesce(Subcategoria.nome, "(sem assunto)")
    with db_session() as s:
        base = _base_rec(s, ano, tipos)
        total = base.with_entities(
            func.count(distinct(Reclamacao.id)).label("total"),
        ).scalar() or 0
        top = (
            base.with_entities(
                assunto_expr.label("assunto"),
                func.count(distinct(Reclamacao.id)).label("cnt"),
            )
            .group_by(assunto_expr)
            .order_by(func.count(distinct(Reclamacao.id)).desc())
            .first()
        )
    top_nome = top[0] if top else "–"
    top_cnt = int(top[1]) if top else 0
    return int(total), top_nome, top_cnt


def query_kpis_fretamento(ano: int, tipos: list[str]) -> tuple[int, str, int]:
    """Retorna (total_reclamacoes, top_assunto, top_assunto_cnt) — sem autos."""
    assunto_expr = func.coalesce(Subcategoria.nome, "(sem assunto)")
    with db_session() as s:
        base = _base_rec(s, ano, tipos)
        total = base.with_entities(func.count(distinct(Reclamacao.id))).scalar() or 0
        top = (
            base.with_entities(
                assunto_expr.label("assunto"),
                func.count(distinct(Reclamacao.id)).label("cnt"),
            )
            .group_by(assunto_expr)
            .order_by(func.count(distinct(Reclamacao.id)).desc())
            .first()
        )
    top_nome = top[0] if top else "–"
    top_cnt = int(top[1]) if top else 0
    return int(total), top_nome, top_cnt


# ─── Evolução mensal ──────────────────────────────────────────────────────────

def query_evolucao_mensal(ano: int, tipos: list[str]) -> list[tuple[str, int]]:
    """Retorna [(mes 'YYYY-MM', total)] ordenado por mês."""
    mes_col = func.to_char(func.date_trunc("month", Ouvidoria.criado_em), "YYYY-MM")
    with db_session() as s:
        rows = (
            _base_rec(s, ano, tipos)
            .with_entities(mes_col.label("mes"), func.count(distinct(Reclamacao.id)).label("total"))
            .group_by(mes_col)
            .order_by(mes_col)
            .all()
        )
    return [(r.mes, int(r.total)) for r in rows]


# ─── Pizza assuntos ───────────────────────────────────────────────────────────

def query_pizza_assuntos(ano: int, tipos: list[str]) -> list[tuple[str, int]]:
    """Retorna [(assunto, total)] ordenado decrescente."""
    assunto_expr = func.coalesce(Subcategoria.nome, "(sem assunto)")
    with db_session() as s:
        rows = (
            _base_rec(s, ano, tipos)
            .with_entities(assunto_expr.label("assunto"), func.count(distinct(Reclamacao.id)).label("total"))
            .group_by(assunto_expr)
            .order_by(func.count(distinct(Reclamacao.id)).desc())
            .all()
        )
    return [(r.assunto, int(r.total)) for r in rows]


# ─── Empresas por pontuação ───────────────────────────────────────────────────

def query_empresas_pontuacao(ano: int, tipos: list[str]) -> list[dict]:
    """Retorna [dict] com empresas por pontuação.
    Cada dict contém: empresa, pts, linha_top, subcategoria_top.
    Exclui pontuação de reclamações subcategorizadas como TRANSPORTE IRREGULAR / CLANDESTINO."""
    from collections import defaultdict
    empresa_expr = func.coalesce(Permissionaria.nome_fantasia, Permissionaria.nome)

    with db_session() as s:
        rows = (
            _excluir_transporte_irregular(_base_rec(s, ano, tipos))
            .with_entities(
                empresa_expr.label("empresa"),
                AutoLinha.numero.label("auto"),
                func.coalesce(Subcategoria.nome, "(sem assunto)").label("subcategoria"),
                func.round(func.coalesce(func.sum(ReclamacaoAuto.pontuacao), 0), 2).label("pts"),
            )
            .filter(Permissionaria.nome.isnot(None))
            .group_by(
                empresa_expr,
                AutoLinha.numero,
                func.coalesce(Subcategoria.nome, "(sem assunto)"),
            )
            .all()
        )

    empresas = defaultdict(lambda: {"pts": 0.0, "auto_pts": defaultdict(float), "sub_pts": defaultdict(float)})
    for r in rows:
        empresas[r.empresa]["pts"] += float(r.pts)
        empresas[r.empresa]["auto_pts"][r.auto or "(sem linha)"] += float(r.pts)
        empresas[r.empresa]["sub_pts"][r.subcategoria or "(sem assunto)"] += float(r.pts)

    result = []
    for empresa, data in empresas.items():
        linha_top = max(data["auto_pts"], key=data["auto_pts"].get, default="(sem linha)")
        sub_top = max(data["sub_pts"], key=data["sub_pts"].get, default="(sem assunto)")
        result.append({
            "empresa": empresa,
            "pts": round(data["pts"], 2),
            "linha_top": linha_top,
            "subcategoria_top": sub_top,
        })

    result.sort(key=lambda x: x["pts"], reverse=True)
    return result


# ─── Heatmap assunto × empresa ────────────────────────────────────────────────

def query_heatmap_assunto_empresa(ano: int, tipos: list[str]) -> list[dict]:
    """Retorna [dict] com pontuação e auto principal por (empresa, assunto).
    Cada dict contém: empresa, assunto, pts, auto_top."""
    from collections import defaultdict
    empresa_expr = func.coalesce(Permissionaria.nome_fantasia, Permissionaria.nome)
    assunto_expr = func.coalesce(Subcategoria.nome, "(sem assunto)")

    with db_session() as s:
        rows = (
            _base_rec(s, ano, tipos)
            .with_entities(
                empresa_expr.label("empresa"),
                assunto_expr.label("assunto"),
                AutoLinha.numero.label("auto"),
                func.round(func.coalesce(func.sum(ReclamacaoAuto.pontuacao), 0), 2).label("pts"),
            )
            .filter(Permissionaria.nome.isnot(None))
            .group_by(
                func.coalesce(Permissionaria.nome_fantasia, Permissionaria.nome),
                func.coalesce(Subcategoria.nome, "(sem assunto)"),
                AutoLinha.numero,
            )
            .all()
        )

    # Agrega por (empresa, assunto): total pts e pontuação por auto
    cells = defaultdict(lambda: {"pts": 0.0, "auto_pts": defaultdict(float)})
    for r in rows:
        key = (r.empresa, r.assunto)
        cells[key]["pts"] += float(r.pts)
        cells[key]["auto_pts"][r.auto or "(sem linha)"] += float(r.pts)

    result = []
    for (empresa, assunto), data in cells.items():
        auto_top = max(data["auto_pts"], key=data["auto_pts"].get, default="(sem linha)")
        result.append({
            "empresa": empresa,
            "assunto": assunto,
            "pts": round(data["pts"], 2),
            "auto_top": auto_top,
        })

    return result


# ─── Top 15 autos por pontuação ───────────────────────────────────────────────

def query_top15_autos_pontuacao(ano: int, tipos: list[str]) -> list[dict]:
    """Retorna [dict] com top 15 autos por pontuação.
    Cada dict contém: auto, pts, empresa, subcategoria_top.
    Exclui pontuação de reclamações subcategorizadas como TRANSPORTE IRREGULAR / CLANDESTINO."""
    from collections import defaultdict
    empresa_expr = func.coalesce(Permissionaria.nome_fantasia, Permissionaria.nome)

    with db_session() as s:
        rows = (
            _excluir_transporte_irregular(_base_rec(s, ano, tipos))
            .with_entities(
                AutoLinha.numero.label("auto"),
                empresa_expr.label("empresa"),
                func.coalesce(Subcategoria.nome, "(sem assunto)").label("subcategoria"),
                func.round(func.coalesce(func.sum(ReclamacaoAuto.pontuacao), 0), 2).label("pts"),
            )
            .filter(AutoLinha.numero.isnot(None))
            .group_by(
                AutoLinha.numero,
                empresa_expr,
                func.coalesce(Subcategoria.nome, "(sem assunto)"),
            )
            .all()
        )

    autos = defaultdict(lambda: {"pts": 0.0, "empresa": "", "sub_pts": defaultdict(float)})
    for r in rows:
        autos[r.auto]["pts"] += float(r.pts)
        autos[r.auto]["empresa"] = r.empresa or ""
        autos[r.auto]["sub_pts"][r.subcategoria or "(sem assunto)"] += float(r.pts)

    result = []
    for auto, data in autos.items():
        sub_top = max(data["sub_pts"], key=data["sub_pts"].get, default="(sem assunto)")
        result.append({
            "auto": auto,
            "pts": round(data["pts"], 2),
            "empresa": data["empresa"],
            "subcategoria_top": sub_top,
        })

    result.sort(key=lambda x: x["pts"], reverse=True)
    return result[:15]


# ─── Top 15 locais de embarque (fretamento) ───────────────────────────────────

def query_top15_embarques(ano: int, tipos: list[str]) -> list[tuple[str, int]]:
    """Retorna [(local_embarque, total)] top 15 mais reclamados."""
    with db_session() as s:
        rows = (
            _base_rec(s, ano, tipos)
            .with_entities(
                Reclamacao.local_embarque.label("local"),
                func.count(distinct(Reclamacao.id)).label("total"),
            )
            .filter(
                Reclamacao.local_embarque.isnot(None),
                Reclamacao.local_embarque != "",
            )
            .group_by(Reclamacao.local_embarque)
            .order_by(func.count(distinct(Reclamacao.id)).desc())
            .limit(15)
            .all()
        )
    return [(r.local, int(r.total)) for r in rows]
