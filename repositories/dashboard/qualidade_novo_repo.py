"""Queries ORM para o novo Dashboard de Qualidade (Dash, v2).

Diferenças em relação ao repo anterior:
- Filtra exclusivamente por Categoria.nome (default "RECLAMAÇÃO")
- Usa Subcategoria como "assunto" (não Categoria)
- Filtra por ano + lista de meses (não data_ini/data_fim)
- tipo_servico aceita lista de valores (para Fretamento = 2 tipos)
"""

from sqlalchemy import String, cast, distinct, func, or_

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
from utils.formatters import TC_REGIOES

_IRREGULAR = "TRANSPORTE IRREGULAR / CLANDESTINO"
_TS_METRO = "Regular – Metropolitano"
_TS_INTER = "Regular – Intermunicipal"


def _fantasia_map(s) -> dict[str, str]:
    """Retorna {nome: nome_fantasia_ou_nome} para todas as permissionárias."""
    rows = s.query(
        Permissionaria.nome,
        func.coalesce(Permissionaria.nome_fantasia, Permissionaria.nome),
    ).all()
    return {r[0]: r[1] for r in rows}


def _apply_regiao_filter(q, regioes: list[str]):
    """Filtra query por regiões metropolitanas e TC.

    Formatos esperados:
    - "RM Campinas", "RM ...", etc. → filtro regiao_metropolitana
    - "TC1", "TC2", ..., "TC5" → filtro tc
    """
    if not regioes:
        return q

    rm_vals = [r for r in regioes if not r.startswith("TC")]
    tc_vals = []
    for r in regioes:
        if r.startswith("TC"):
            try:
                tc_vals.append(int(r[2:]))
            except (ValueError, IndexError):
                pass

    conditions = []
    if rm_vals:
        conditions.append(AutoLinha.regiao_metropolitana.in_(rm_vals))
    if tc_vals:
        conditions.append(AutoLinha.tc.in_(tc_vals))

    if conditions:
        return q.filter(or_(*conditions))
    return q


def _base_novo(s, ano: int, meses: list[int], tipo_servicos: list[str], categoria: str = "RECLAMAÇÃO"):
    """Query base: filtra por categoria, ano, meses e tipo(s) de serviço."""
    q = (
        s.query(Reclamacao)
        .join(Ouvidoria, Ouvidoria.id == Reclamacao.ouvidoria_id)
        .outerjoin(ReclamacaoAuto, ReclamacaoAuto.reclamacao_id == Reclamacao.id)
        .outerjoin(AutoLinha, AutoLinha.id == ReclamacaoAuto.auto_id)
        .outerjoin(Permissionaria, Permissionaria.id == AutoLinha.permissionaria_id)
        .outerjoin(Categoria, Categoria.id == Reclamacao.categoria_id)
        .outerjoin(Subcategoria, Subcategoria.id == Reclamacao.subcategoria_id)
        .filter(Categoria.nome == categoria)
        .filter(func.extract("year", Ouvidoria.criado_em) == ano)
    )
    if meses:
        q = q.filter(func.extract("month", Ouvidoria.criado_em).in_(meses))
    if tipo_servicos:
        from sqlalchemy import or_
        # Inclui tanto registros com AutoLinha vinculado quanto sem (ex: fretamento com empresa_fretamento)
        q = q.filter(
            or_(
                cast(AutoLinha.tipo, String).in_(tipo_servicos),
                cast(Reclamacao.tipo_servico, String).in_(tipo_servicos),
            )
        )
    return q


# ── Filtros disponíveis ───────────────────────────────────────────────────────

def query_anos_disponiveis() -> list[int]:
    """Anos que possuem pelo menos uma reclamação categorizada como RECLAMAÇÃO."""
    with db_session() as s:
        rows = (
            s.query(func.extract("year", Ouvidoria.criado_em).label("ano"))
            .join(Reclamacao, Reclamacao.ouvidoria_id == Ouvidoria.id)
            .join(Categoria, Categoria.id == Reclamacao.categoria_id)
            .filter(Categoria.nome == "RECLAMAÇÃO")
            .group_by("ano")
            .order_by("ano")
            .all()
        )
        return [int(r[0]) for r in rows]


def query_meses_disponiveis(ano: int, tipo_servicos: list[str], categoria: str = "RECLAMAÇÃO") -> list[int]:
    """Meses com dados no ano informado."""
    with db_session() as s:
        q = _base_novo(s, ano, [], tipo_servicos, categoria)
        rows = (
            q.with_entities(func.extract("month", Ouvidoria.criado_em).label("mes"))
            .group_by("mes")
            .order_by("mes")
            .all()
        )
        return [int(r[0]) for r in rows]


# ── Filtros de região ────────────────────────────────────────────────────────

def query_regioes_disponiveis(tipo_servicos: list[str]) -> list[dict]:
    """Retorna lista de regiões disponíveis para o tipo de serviço.

    Para Regular Metropolitano: lista de regiao_metropolitana (ex: "RM Campinas")
    Para Regular Intermunicipal: lista "TC1 - Campinas", "TC2 - Sorocaba", etc.
    """
    with db_session() as s:
        resultado = []

        # Se Regular Metropolitano está na seleção
        if _TS_METRO in tipo_servicos:
            rm_rows = (
                s.query(distinct(AutoLinha.regiao_metropolitana))
                .filter(cast(AutoLinha.tipo, String) == _TS_METRO)
                .filter(AutoLinha.regiao_metropolitana.isnot(None))
                .filter(AutoLinha.regiao_metropolitana != "")
                .order_by(AutoLinha.regiao_metropolitana)
                .all()
            )
            for r in rm_rows:
                resultado.append({"id": r[0], "label": r[0]})

        # Se Regular Intermunicipal está na seleção
        if _TS_INTER in tipo_servicos:
            tc_rows = (
                s.query(distinct(AutoLinha.tc))
                .filter(cast(AutoLinha.tipo, String) == _TS_INTER)
                .filter(AutoLinha.tc.isnot(None))
                .order_by(AutoLinha.tc)
                .all()
            )
            for r in tc_rows:
                tc_num = r[0]
                tc_label = TC_REGIOES.get(tc_num, str(tc_num))
                resultado.append({"id": f"TC{tc_num}", "label": f"TC{tc_num} - {tc_label}"})

        return resultado


# ── Cards de resumo ───────────────────────────────────────────────────────────

def query_resumo(ano: int, meses: list[int], tipo_servicos: list[str], categoria: str = "RECLAMAÇÃO") -> dict:
    """Retorna total de reclamações e assunto mais reclamado."""
    with db_session() as s:
        q = _base_novo(s, ano, meses, tipo_servicos, categoria)

        total = q.with_entities(func.count(distinct(Reclamacao.id))).scalar() or 0

        assunto_row = (
            q.with_entities(
                func.coalesce(Subcategoria.nome, "(sem assunto)").label("assunto"),
                func.count(distinct(Reclamacao.id)).label("qty"),
            )
            .group_by(Subcategoria.nome)
            .order_by(func.count(distinct(Reclamacao.id)).desc())
            .first()
        )

        return {
            "total_reclamacoes": int(total),
            "assunto_top": assunto_row[0] if assunto_row else "–",
            "assunto_top_qty": int(assunto_row[1]) if assunto_row else 0,
        }


# ── Gráfico 1: Evolução mensal ────────────────────────────────────────────────

def query_evolucao_mensal_v2(
    ano: int, meses: list[int], tipo_servicos: list[str], categoria: str = "RECLAMAÇÃO"
) -> list[tuple]:
    """Retorna [(mes_int, total)] ordenado por mês."""
    with db_session() as s:
        q = _base_novo(s, ano, meses, tipo_servicos, categoria)
        mes_col = func.extract("month", Ouvidoria.criado_em).label("mes")
        rows = (
            q.with_entities(mes_col, func.count(distinct(Reclamacao.id)).label("total"))
            .group_by(mes_col)
            .order_by(mes_col)
            .all()
        )
        return [(int(r[0]), int(r[1])) for r in rows]


# ── Gráfico 2: Pizza de assuntos ─────────────────────────────────────────────

def query_assuntos_pizza(
    ano: int, meses: list[int], tipo_servicos: list[str], categoria: str = "RECLAMAÇÃO"
) -> list[tuple]:
    """Retorna [(assunto, total)] para pizza."""
    with db_session() as s:
        q = _base_novo(s, ano, meses, tipo_servicos, categoria)
        rows = (
            q.with_entities(
                func.coalesce(Subcategoria.nome, "(sem assunto)").label("assunto"),
                func.count(distinct(Reclamacao.id)).label("total"),
            )
            .group_by(Subcategoria.nome)
            .order_by(func.count(distinct(Reclamacao.id)).desc())
            .all()
        )
        return [(r[0], int(r[1])) for r in rows]


# ── Gráfico 3: Empresas por pontuação (excl. irregular) ──────────────────────

def query_empresas_pontuacao_v2(
    ano: int, meses: list[int], tipo_servicos: list[str], categoria: str = "RECLAMAÇÃO"
) -> list[dict]:
    """Ranking de empresas por pontuação. Exclui subcategoria TRANSPORTE IRREGULAR."""
    with db_session() as s:
        q = _base_novo(s, ano, meses, tipo_servicos, categoria)
        q = q.filter(
            (Subcategoria.nome != _IRREGULAR) | (Subcategoria.nome.is_(None))
        ).filter(Permissionaria.nome.isnot(None))

        rows = (
            q.with_entities(
                Permissionaria.nome.label("empresa"),
                func.round(func.coalesce(func.sum(ReclamacaoAuto.pontuacao), 0), 2).label("pontuacao"),
                func.count(distinct(Reclamacao.id)).label("num_reclamacoes"),
            )
            .group_by(Permissionaria.nome)
            .order_by(func.sum(ReclamacaoAuto.pontuacao).desc())
            .all()
        )

        fm = _fantasia_map(s)
        result = []
        for r in rows:
            empresa = r[0]
            linha_top = _linha_top_empresa(s, ano, meses, tipo_servicos, categoria, empresa)
            assunto_top = _assunto_top_empresa(s, ano, meses, tipo_servicos, categoria, empresa)
            result.append({
                "empresa": fm.get(empresa, empresa),
                "pontuacao": float(r[1]),
                "num_reclamacoes": int(r[2]),
                "linha_top": linha_top,
                "assunto_top": assunto_top,
            })
        return result


def _linha_top_empresa(s, ano, meses, tipo_servicos, categoria, empresa):
    q = _base_novo(s, ano, meses, tipo_servicos, categoria)
    row = (
        q.filter(Permissionaria.nome == empresa)
        .filter(AutoLinha.numero.isnot(None))
        .with_entities(
            AutoLinha.numero,
            func.round(func.sum(ReclamacaoAuto.pontuacao), 2).label("pts"),
        )
        .group_by(AutoLinha.numero)
        .order_by(func.sum(ReclamacaoAuto.pontuacao).desc())
        .first()
    )
    return row[0] if row else "–"


def _assunto_top_empresa(s, ano, meses, tipo_servicos, categoria, empresa):
    q = _base_novo(s, ano, meses, tipo_servicos, categoria)
    row = (
        q.filter(Permissionaria.nome == empresa)
        .filter(Subcategoria.nome.isnot(None))
        .with_entities(
            Subcategoria.nome,
            func.count(distinct(Reclamacao.id)).label("qty"),
        )
        .group_by(Subcategoria.nome)
        .order_by(func.count(distinct(Reclamacao.id)).desc())
        .first()
    )
    return row[0] if row else "–"


# ── Gráfico 4: Incidência de transporte irregular por empresa ─────────────────

def query_empresas_incidencia_irregular(
    ano: int, meses: list[int], tipo_servicos: list[str], categoria: str = "RECLAMAÇÃO"
) -> list[dict]:
    """Ranking de empresas pela pontuação exclusiva de TRANSPORTE IRREGULAR."""
    with db_session() as s:
        q = _base_novo(s, ano, meses, tipo_servicos, categoria)
        q = q.filter(Subcategoria.nome == _IRREGULAR).filter(Permissionaria.nome.isnot(None))

        rows = (
            q.with_entities(
                Permissionaria.nome.label("empresa"),
                func.round(func.coalesce(func.sum(ReclamacaoAuto.pontuacao), 0), 2).label("pontuacao"),
            )
            .group_by(Permissionaria.nome)
            .order_by(func.sum(ReclamacaoAuto.pontuacao).desc())
            .all()
        )

        fm = _fantasia_map(s)
        result = []
        for r in rows:
            empresa = r[0]
            linha_top = _linha_top_empresa_irregular(s, ano, meses, tipo_servicos, categoria, empresa)
            result.append({
                "empresa": fm.get(empresa, empresa),
                "pontuacao": float(r[1]),
                "linha_top": linha_top,
            })
        return result


def _linha_top_empresa_irregular(s, ano, meses, tipo_servicos, categoria, empresa):
    q = _base_novo(s, ano, meses, tipo_servicos, categoria)
    row = (
        q.filter(Subcategoria.nome == _IRREGULAR)
        .filter(Permissionaria.nome == empresa)
        .filter(AutoLinha.numero.isnot(None))
        .with_entities(
            AutoLinha.numero,
            func.round(func.sum(ReclamacaoAuto.pontuacao), 2).label("pts"),
        )
        .group_by(AutoLinha.numero)
        .order_by(func.sum(ReclamacaoAuto.pontuacao).desc())
        .first()
    )
    return row[0] if row else "–"


# ── Gráfico 5: Heatmap Assunto × Empresa (excl. irregular, paginado) ─────────

def query_heatmap_assunto_empresa(
    ano: int,
    meses: list[int],
    tipo_servicos: list[str],
    pagina: int = 1,
    por_pagina: int = 10,
    categoria: str = "RECLAMAÇÃO",
    regioes: list[str] | None = None,
) -> dict:
    """Retorna dados para heatmap assunto × empresa com paginação por empresa.

    Args:
        regioes: lista de IDs de região ("RM Campinas", "TC1", etc.)
    """
    with db_session() as s:
        q = _base_novo(s, ano, meses, tipo_servicos, categoria)
        q = q.filter(
            (Subcategoria.nome != _IRREGULAR) | (Subcategoria.nome.is_(None))
        ).filter(Permissionaria.nome.isnot(None))
        q = _apply_regiao_filter(q, regioes or [])

        # Empresas ordenadas por pontuação total (para paginação consistente)
        # Usar .all() + slice Python evita comportamento instável de .count() em queries com GROUP BY
        todas_empresas = (
            q.with_entities(
                Permissionaria.nome.label("empresa"),
                func.sum(ReclamacaoAuto.pontuacao).label("pts_total"),
            )
            .group_by(Permissionaria.nome)
            .order_by(func.sum(ReclamacaoAuto.pontuacao).desc())
            .all()
        )
        total_empresas = len(todas_empresas)
        total_paginas = max(1, -(-total_empresas // por_pagina))
        zmax_global = float(max((r[1] for r in todas_empresas if r[1]), default=0))
        offset = (pagina - 1) * por_pagina
        empresas_pagina = [r[0] for r in todas_empresas[offset : offset + por_pagina]]

        if not empresas_pagina:
            return {"dados": [], "total_paginas": total_paginas, "pagina": pagina, "zmax_global": zmax_global}

        rows = (
            q.filter(Permissionaria.nome.in_(empresas_pagina))
            .with_entities(
                Permissionaria.nome.label("empresa"),
                func.coalesce(Subcategoria.nome, "(sem assunto)").label("assunto"),
                func.round(func.coalesce(func.sum(ReclamacaoAuto.pontuacao), 0), 2).label("pontuacao"),
            )
            .group_by(Permissionaria.nome, Subcategoria.nome)
            .all()
        )

        fm = _fantasia_map(s)
        dados = []
        for r in rows:
            empresa_nome = r[0]
            linha_top, pts_linha = _linha_top_empresa_assunto(
                s, ano, meses, tipo_servicos, categoria, empresa_nome, r[1]
            )
            dados.append({
                "empresa": fm.get(empresa_nome, empresa_nome),
                "assunto": r[1],
                "pontuacao": float(r[2]),
                "linha_top": linha_top,
                "pts_linha": pts_linha,
            })

        return {"dados": dados, "total_paginas": total_paginas, "pagina": pagina, "zmax_global": zmax_global}


def _linha_top_empresa_assunto(s, ano, meses, tipo_servicos, categoria, empresa, assunto):
    q = _base_novo(s, ano, meses, tipo_servicos, categoria)
    row = (
        q.filter(Permissionaria.nome == empresa)
        .filter(func.coalesce(Subcategoria.nome, "(sem assunto)") == assunto)
        .filter(AutoLinha.numero.isnot(None))
        .with_entities(
            AutoLinha.numero,
            func.round(func.sum(ReclamacaoAuto.pontuacao), 2).label("pts"),
        )
        .group_by(AutoLinha.numero)
        .order_by(func.sum(ReclamacaoAuto.pontuacao).desc())
        .first()
    )
    return (row[0], float(row[1])) if row else ("–", 0.0)


# ── Gráfico 6: Autos por pontuação (excl. irregular, paginado) ───────────────

def query_autos_pontuacao_v2(
    ano: int,
    meses: list[int],
    tipo_servicos: list[str],
    pagina: int = 1,
    por_pagina: int = 15,
    categoria: str = "RECLAMAÇÃO",
) -> dict:
    """Ranking paginado de autos por pontuação (excl. TRANSPORTE IRREGULAR)."""
    with db_session() as s:
        q = _base_novo(s, ano, meses, tipo_servicos, categoria)
        q = q.filter(
            (Subcategoria.nome != _IRREGULAR) | (Subcategoria.nome.is_(None))
        ).filter(AutoLinha.numero.isnot(None))

        todos_autos = (
            q.with_entities(
                AutoLinha.numero.label("auto"),
                func.round(func.coalesce(func.sum(ReclamacaoAuto.pontuacao), 0), 2).label("pontuacao"),
            )
            .group_by(AutoLinha.numero)
            .order_by(func.sum(ReclamacaoAuto.pontuacao).desc())
            .all()
        )
        total = len(todos_autos)
        xmax_global = float(todos_autos[0][1]) if todos_autos else 0.0
        total_paginas = max(1, -(-total // por_pagina))
        offset = (pagina - 1) * por_pagina
        rows_pag = todos_autos[offset : offset + por_pagina]

        dados = []
        for r in rows_pag:
            assunto_top = _assunto_top_auto(s, ano, meses, tipo_servicos, categoria, r[0])
            dados.append({
                "auto": r[0],
                "pontuacao": float(r[1]),
                "assunto_top": assunto_top,
            })
        return {"dados": dados, "total_paginas": total_paginas, "pagina": pagina, "xmax_global": xmax_global}


def _assunto_top_auto(s, ano, meses, tipo_servicos, categoria, auto_numero):
    q = _base_novo(s, ano, meses, tipo_servicos, categoria)
    row = (
        q.filter(AutoLinha.numero == auto_numero)
        .filter(Subcategoria.nome.isnot(None))
        .with_entities(
            Subcategoria.nome,
            func.count(distinct(Reclamacao.id)).label("qty"),
        )
        .group_by(Subcategoria.nome)
        .order_by(func.count(distinct(Reclamacao.id)).desc())
        .first()
    )
    return row[0] if row else "–"


# ── Gráfico 7: Autos por incidência de transporte irregular (paginado) ────────

def query_autos_incidencia_irregular(
    ano: int,
    meses: list[int],
    tipo_servicos: list[str],
    pagina: int = 1,
    por_pagina: int = 15,
    categoria: str = "RECLAMAÇÃO",
) -> dict:
    """Ranking paginado de autos por pontuação de TRANSPORTE IRREGULAR."""
    with db_session() as s:
        q = _base_novo(s, ano, meses, tipo_servicos, categoria)
        q = q.filter(Subcategoria.nome == _IRREGULAR).filter(AutoLinha.numero.isnot(None))

        todos = (
            q.with_entities(
                AutoLinha.numero.label("auto"),
                func.round(func.coalesce(func.sum(ReclamacaoAuto.pontuacao), 0), 2).label("pontuacao"),
            )
            .group_by(AutoLinha.numero)
            .order_by(func.sum(ReclamacaoAuto.pontuacao).desc())
            .all()
        )
        total = len(todos)
        xmax_global = float(todos[0][1]) if todos else 0.0
        total_paginas = max(1, -(-total // por_pagina))
        offset = (pagina - 1) * por_pagina
        rows_pag = todos[offset : offset + por_pagina]

        return {
            "dados": [{"auto": r[0], "pontuacao": float(r[1])} for r in rows_pag],
            "total_paginas": total_paginas,
            "pagina": pagina,
            "xmax_global": xmax_global,
        }


# ── Gráfico 8: Heatmap Assunto × Autos (excl. irregular, paginado) ───────────

def query_heatmap_assunto_auto(
    ano: int,
    meses: list[int],
    tipo_servicos: list[str],
    perm_ids: list[int],
    pagina: int = 1,
    por_pagina: int = 10,
    categoria: str = "RECLAMAÇÃO",
    regioes: list[str] | None = None,
) -> dict:
    """Heatmap assunto × auto com filtro opcional de empresas, regiões e paginação.

    Args:
        regioes: lista de IDs de região ("RM Campinas", "TC1", etc.)
    """
    with db_session() as s:
        q = _base_novo(s, ano, meses, tipo_servicos, categoria)
        q = q.filter(
            (Subcategoria.nome != _IRREGULAR) | (Subcategoria.nome.is_(None))
        ).filter(AutoLinha.numero.isnot(None))

        if perm_ids:
            q = q.filter(Permissionaria.id.in_(perm_ids))

        q = _apply_regiao_filter(q, regioes or [])

        # Autos ordenados por pontuação total (para paginação consistente)
        todos_autos = (
            q.with_entities(
                AutoLinha.numero.label("auto"),
                func.sum(ReclamacaoAuto.pontuacao).label("pts_total"),
            )
            .group_by(AutoLinha.numero)
            .order_by(func.sum(ReclamacaoAuto.pontuacao).desc())
            .all()
        )
        total_autos = len(todos_autos)
        total_paginas = max(1, -(-total_autos // por_pagina))
        zmax_global = float(max((r[1] for r in todos_autos if r[1]), default=0))
        offset = (pagina - 1) * por_pagina
        autos_pagina = [r[0] for r in todos_autos[offset : offset + por_pagina]]

        if not autos_pagina:
            return {"dados": [], "total_paginas": total_paginas, "pagina": pagina, "zmax_global": zmax_global}

        fm = _fantasia_map(s)
        rows = (
            q.filter(AutoLinha.numero.in_(autos_pagina))
            .with_entities(
                func.coalesce(Permissionaria.nome, "–").label("empresa"),
                AutoLinha.numero.label("auto"),
                func.coalesce(AutoLinha.denominacao_a, "–").label("cidade_a"),
                func.coalesce(AutoLinha.denominacao_b, "–").label("cidade_b"),
                func.coalesce(Subcategoria.nome, "(sem assunto)").label("assunto"),
                func.round(func.coalesce(func.sum(ReclamacaoAuto.pontuacao), 0), 2).label("pontuacao"),
            )
            .group_by(
                Permissionaria.nome, AutoLinha.numero,
                AutoLinha.denominacao_a, AutoLinha.denominacao_b,
                Subcategoria.nome,
            )
            .all()
        )

        return {
            "dados": [
                {
                    "empresa": fm.get(r[0], r[0]),
                    "auto": r[1],
                    "cidade_a": r[2],
                    "cidade_b": r[3],
                    "assunto": r[4],
                    "pontuacao": float(r[5]),
                }
                for r in rows
            ],
            "total_paginas": total_paginas,
            "pagina": pagina,
            "zmax_global": zmax_global,
        }


# ── Locais de embarque/desembarque ──────────────────────────────────────────

def query_locais_embarque(
    ano: int,
    meses: list[int],
    tipo_servicos: list[str],
    pagina: int = 1,
    por_pagina: int = 15,
    categoria: str = "RECLAMAÇÃO",
    tipo_local: str = "embarque",
) -> dict:
    """Ranking paginado de locais de embarque/desembarque.

    Args:
        tipo_servicos: lista de tipos de serviço a filtrar
        tipo_local: "embarque" ou "desembarque"
    """
    with db_session() as s:
        q = _base_novo(s, ano, meses, tipo_servicos, categoria)

        if tipo_local == "desembarque":
            q = q.filter(
                Reclamacao.local_desembarque.isnot(None),
                Reclamacao.local_desembarque != "",
            )
            local_field = Reclamacao.local_desembarque
        else:
            q = q.filter(
                Reclamacao.local_embarque.isnot(None),
                Reclamacao.local_embarque != "",
            )
            local_field = Reclamacao.local_embarque

        todos = (
            q.with_entities(
                local_field.label("local"),
                func.count(distinct(Reclamacao.id)).label("total"),
            )
            .group_by(local_field)
            .order_by(func.count(distinct(Reclamacao.id)).desc())
            .all()
        )
        total = len(todos)
        xmax_global = int(todos[0][1]) if todos else 0
        total_paginas = max(1, -(-total // por_pagina))
        offset = (pagina - 1) * por_pagina
        rows_pag = todos[offset : offset + por_pagina]

        dados = []
        for r in rows_pag:
            assunto_top = _assunto_top_local(s, ano, meses, tipo_servicos, categoria, r[0], tipo_local)
            dados.append({
                "local": r[0],
                "total": int(r[1]),
                "assunto_top": assunto_top,
            })
        return {"dados": dados, "total_paginas": total_paginas, "pagina": pagina, "xmax_global": xmax_global}


def _assunto_top_local(s, ano, meses, tipo_servicos, categoria, local, tipo_local):
    q = _base_novo(s, ano, meses, tipo_servicos, categoria)
    if tipo_local == "desembarque":
        q = q.filter(Reclamacao.local_desembarque == local)
    else:
        q = q.filter(Reclamacao.local_embarque == local)
    row = (
        q.filter(Subcategoria.nome.isnot(None))
        .with_entities(
            Subcategoria.nome,
            func.count(distinct(Reclamacao.id)).label("qty"),
        )
        .group_by(Subcategoria.nome)
        .order_by(func.count(distinct(Reclamacao.id)).desc())
        .first()
    )
    return row[0] if row else "–"


# Compatibilidade com código legado que chama query_locais_embarque_fretamento
def query_locais_embarque_fretamento(
    ano: int,
    meses: list[int],
    pagina: int = 1,
    por_pagina: int = 15,
    categoria: str = "RECLAMAÇÃO",
) -> dict:
    """Alias legado para query_locais_embarque com tipos fretamento."""
    tipo_servicos = ["Fretamento Intermunicipal", "Fretamento Metropolitano"]
    return query_locais_embarque(ano, meses, tipo_servicos, pagina, por_pagina, categoria, "embarque")


# ── Lista de empresas para filtro do Gráfico 8 ───────────────────────────────

def query_empresas_lista(tipo_servicos: list[str]) -> list[dict]:
    """Lista de empresas (id + nome) do tipo de serviço para o filtro do Gráfico 8."""
    with db_session() as s:
        rows = (
            s.query(Permissionaria.id, Permissionaria.nome)
            .join(AutoLinha, AutoLinha.permissionaria_id == Permissionaria.id)
            .filter(cast(AutoLinha.tipo, String).in_(tipo_servicos))
            .filter(AutoLinha.ativo.is_(True))
            .group_by(Permissionaria.id, Permissionaria.nome)
            .order_by(Permissionaria.nome)
            .all()
        )
        return [{"id": r[0], "nome": r[1]} for r in rows]
