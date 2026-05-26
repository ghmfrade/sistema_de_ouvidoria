"""Consultas ao banco relacionadas a autos de linha, permissionárias e regiões."""

import re
import unicodedata

from sqlalchemy import union_all
from sqlalchemy.orm import aliased, joinedload

from database.connection import db_session
from models import AutoLinha, Municipio, Permissionaria, TipoServico, TrechoAutoLinha
from repositories.types import AutoDict, MunicipioDict, PermissionariaDict


# ── Helpers ───────────────────────────────────────────────────────────────────

def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s).strip().upper())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s).strip()


def _municipio_to_dict(m: Municipio) -> MunicipioDict:
    return MunicipioDict(id=m.id, nome=m.nome, estado=m.estado,
                         cod_ibge=m.cod_ibge, populacao=m.populacao)


def _auto_to_dict(a: AutoLinha) -> AutoDict:
    perm = a.permissionaria
    perm_nome = (perm.nome_fantasia or perm.nome) if perm else ""
    return AutoDict(
        id=a.id,
        numero=a.numero,
        denominacao_a=a.denominacao_a,
        denominacao_b=a.denominacao_b,
        permissionaria_id=a.permissionaria_id,
        permissionaria_nome=perm_nome,
        tipo=a.tipo.value if a.tipo else "",
        regiao_metropolitana=a.regiao_metropolitana,
        sub_regiao=a.sub_regiao if hasattr(a, "sub_regiao") else None,
        tc=a.tc,
        ativo=a.ativo,
    )


def _resolver_municipio_id(session, nome: str) -> int | None:
    """Busca municipio.id pelo nome (case-insensitive, depois normalizado)."""
    mun = session.query(Municipio.id).filter(
        Municipio.nome.ilike(nome.strip())
    ).scalar()
    if mun:
        return mun
    # fallback normalizado
    nome_norm = _norm(nome)
    rows = session.query(Municipio.id, Municipio.nome).filter_by(estado="SP").all()
    for mid, mnome in rows:
        if _norm(mnome) == nome_norm:
            return mid
    return None


def _base_auto_query(session, tipo_servico: str, perm_id: int | None, regiao: str | None):
    q = (
        session.query(AutoLinha)
        .options(joinedload(AutoLinha.permissionaria))
        .filter(AutoLinha.tipo == tipo_servico, AutoLinha.ativo == True)
    )
    if perm_id is not None:
        q = q.filter(AutoLinha.permissionaria_id == perm_id)
    if regiao is not None:
        q = q.filter(AutoLinha.regiao_metropolitana == regiao)
    return q

def _filtro_por_trecho(q, mun_a: int, mun_b: int | None = None):
    if mun_b:
        min_id, max_id = min(mun_a, mun_b), max(mun_a, mun_b)
        return q.filter(
            AutoLinha.trechos.any(
                (TrechoAutoLinha.municipio_a_id == min_id) &
                (TrechoAutoLinha.municipio_b_id == max_id)
            )
        )
    else:
        return q.filter(
            AutoLinha.trechos.any(
                (TrechoAutoLinha.municipio_a_id == mun_a) |
                (TrechoAutoLinha.municipio_b_id == mun_a)
            )
        )


# ── Funções públicas ──────────────────────────────────────────────────────────

def get_municipios_destino(
    tipo_servico: str,
    nome_origem: str,
    perm_id: int | None = None,
    regiao: str | None = None
) -> list[MunicipioDict]:
    """Municípios alcançáveis a partir da origem (exceto a própria origem)."""

    with db_session() as s:
        origem_id = _resolver_municipio_id(s, nome_origem)
        if not origem_id:
            return []

        base_filter = [
            AutoLinha.tipo == tipo_servico,
            AutoLinha.ativo.is_(True)
        ]

        if perm_id is not None:
            base_filter.append(AutoLinha.permissionaria_id == perm_id)

        if regiao is not None:
            base_filter.append(AutoLinha.regiao_metropolitana == regiao)

        # origem → destino (A → B)
        MunB = aliased(Municipio)
        q_b = (
            s.query(MunB)
            .join(TrechoAutoLinha, TrechoAutoLinha.municipio_b_id == MunB.id)
            .join(AutoLinha, AutoLinha.id == TrechoAutoLinha.auto_id)
            .filter(
                TrechoAutoLinha.municipio_a_id == origem_id,
                MunB.id != origem_id,
                *base_filter
            )
        )

        # destino → origem (B → A)
        MunA = aliased(Municipio)
        q_a = (
            s.query(MunA)
            .join(TrechoAutoLinha, TrechoAutoLinha.municipio_a_id == MunA.id)
            .join(AutoLinha, AutoLinha.id == TrechoAutoLinha.auto_id)
            .filter(
                TrechoAutoLinha.municipio_b_id == origem_id,
                MunA.id != origem_id,
                *base_filter
            )
        )

        munis = q_a.union(q_b).order_by(Municipio.nome).all()

        return [_municipio_to_dict(m) for m in munis]


def get_todos_autos(tipo_servico: str, perm_id: int | None = None,
                    regiao: str | None = None) -> list[AutoDict]:
    """Todos os autos ativos filtrados."""
    with db_session() as s:
        q = _base_auto_query(s, tipo_servico, perm_id, regiao)
        return [_auto_to_dict(a) for a in q.order_by(AutoLinha.numero).all()]


def get_permissionarias(tipo_servico: str, regiao: str | None = None) -> list[PermissionariaDict]:
    """Permissionárias com autos ativos do tipo informado."""
    with db_session() as s:
        q = (
            s.query(Permissionaria)
            .join(AutoLinha, AutoLinha.permissionaria_id == Permissionaria.id)
            .filter(AutoLinha.tipo == tipo_servico, AutoLinha.ativo == True)
        )
        if regiao is not None:
            q = q.filter(AutoLinha.regiao_metropolitana == regiao)
        perms = q.distinct().order_by(Permissionaria.nome).all()
        return [
            PermissionariaDict(
                id=p.id,
                nome=p.nome,
                nome_fantasia=p.nome_fantasia,
                cnpj=p.cnpj,
            )
            for p in perms
        ]


def get_autos_regioes_metropolitanas() -> list[str]:
    """Regiões metropolitanas distintas de autos regulares metropolitanos ativos."""
    with db_session() as s:
        rows = (
            s.query(AutoLinha.regiao_metropolitana)
            .filter(
                AutoLinha.tipo == TipoServico.REGULAR_METROPOLITANO.value,
                AutoLinha.ativo == True,
                AutoLinha.regiao_metropolitana.isnot(None),
            )
            .distinct()
            .all()
        )
        return [row[0] for row in rows if row[0]]


def _numero_prefixo_valido(stored: str, query: str) -> bool:
    """True se stored começa com query E o próximo char (se houver) não é dígito.

    '232' valida '232VP' e '232H', mas NÃO '2329'.
    """
    if not stored.startswith(query):
        return False
    resto = stored[len(query):]
    return not resto or not resto[0].isdigit()


def buscar_autos_por_numero(
    numeros: list[str],
    tipo_servico: str,
    perm_id: int | None = None,
) -> list[AutoDict]:
    """Busca autos pelo número declarado na coluna LINHA.

    Para cada número:
      - Tenta match exato primeiro. Se encontrar, usa só esses.
      - Caso contrário, expande por prefixo alfanumérico
        ('232' → '232VP', '232H', mas NÃO '2329').
    Retorna lista deduplicada.
    """
    with db_session() as s:
        seen_ids: set[int] = set()
        result: list[AutoLinha] = []

        for num in numeros:
            num = num.strip()
            if not num:
                continue

            base_q = (
                s.query(AutoLinha)
                .options(joinedload(AutoLinha.permissionaria))
                .filter(
                    AutoLinha.ativo == True,
                    AutoLinha.tipo == tipo_servico,
                )
                .order_by(AutoLinha.numero)
            )

            exatos = base_q.filter(AutoLinha.numero == num).all()
            if exatos:
                candidatos = exatos
            else:
                todos = base_q.filter(AutoLinha.numero.like(f"{num}%")).all()
                candidatos = [a for a in todos if _numero_prefixo_valido(a.numero, num)]

            for a in candidatos:
                if a.id not in seen_ids:
                    seen_ids.add(a.id)
                    result.append(a)

        if perm_id is not None:
            result = [a for a in result if a.permissionaria_id == perm_id]

        return [_auto_to_dict(a) for a in result]


def buscar_autos_por_trecho(
    tipo_servico: str,
    cidade_a: str,
    cidade_b: str,
    perm_id: int | None = None,
    regiao: str | None = None
) -> list[AutoDict]:
    """Autos com trecho explícito entre cidade_a e cidade_b."""

    with db_session() as s:
        q = _base_auto_query(s, tipo_servico, perm_id, regiao)

        if cidade_a:
            mun_a = _resolver_municipio_id(s, cidade_a)

            if mun_a:
                mun_b = _resolver_municipio_id(s, cidade_b) if cidade_b else None
                q = _filtro_por_trecho(q, mun_a, mun_b)

        return [_auto_to_dict(a) for a in q.order_by(AutoLinha.numero).all()]
