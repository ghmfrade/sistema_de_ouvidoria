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


# ── Funções públicas ──────────────────────────────────────────────────────────

def get_municipios_com_paradas(tipo_servico: str, perm_id: int | None = None,
                                regiao: str | None = None) -> list[MunicipioDict]:
    """Municípios que aparecem em pelo menos um trecho do tipo de serviço."""
    with db_session() as s:
        auto_q = (
            s.query(AutoLinha.id)
            .filter(AutoLinha.tipo == tipo_servico, AutoLinha.ativo == True)
        )
        if perm_id is not None:
            auto_q = auto_q.filter(AutoLinha.permissionaria_id == perm_id)
        if regiao is not None:
            auto_q = auto_q.filter(AutoLinha.regiao_metropolitana == regiao)
        auto_ids = [r[0] for r in auto_q.all()]

        if not auto_ids:
            return []

        MunA = aliased(Municipio)
        MunB = aliased(Municipio)

        q_a = s.query(MunA).join(TrechoAutoLinha, TrechoAutoLinha.municipio_a_id == MunA.id).filter(
            TrechoAutoLinha.auto_id.in_(auto_ids)
        )
        q_b = s.query(MunB).join(TrechoAutoLinha, TrechoAutoLinha.municipio_b_id == MunB.id).filter(
            TrechoAutoLinha.auto_id.in_(auto_ids)
        )

        municipios = {m.id: m for m in q_a.all()}
        municipios.update({m.id: m for m in q_b.all()})
        return [_municipio_to_dict(m) for m in sorted(municipios.values(), key=lambda m: m.nome)]


def get_municipios_destino(tipo_servico: str, nome_origem: str,
                            perm_id: int | None = None,
                            regiao: str | None = None) -> list[MunicipioDict]:
    """Municípios alcançáveis a partir da origem (exceto a própria origem)."""
    with db_session() as s:
        origem_id = _resolver_municipio_id(s, nome_origem)
        if not origem_id:
            return []

        auto_q = (
            s.query(AutoLinha.id)
            .filter(AutoLinha.tipo == tipo_servico, AutoLinha.ativo == True)
        )
        if perm_id is not None:
            auto_q = auto_q.filter(AutoLinha.permissionaria_id == perm_id)
        if regiao is not None:
            auto_q = auto_q.filter(AutoLinha.regiao_metropolitana == regiao)
        auto_ids = [r[0] for r in auto_q.all()]

        if not auto_ids:
            return []

        # Trechos onde origem é mun_a → retorna mun_b
        MunB = aliased(Municipio)
        q_b = (
            s.query(MunB)
            .join(TrechoAutoLinha, TrechoAutoLinha.municipio_b_id == MunB.id)
            .filter(
                TrechoAutoLinha.auto_id.in_(auto_ids),
                TrechoAutoLinha.municipio_a_id == origem_id,
                MunB.id != origem_id,
            )
        )

        # Trechos onde origem é mun_b → retorna mun_a
        MunA = aliased(Municipio)
        q_a = (
            s.query(MunA)
            .join(TrechoAutoLinha, TrechoAutoLinha.municipio_a_id == MunA.id)
            .filter(
                TrechoAutoLinha.auto_id.in_(auto_ids),
                TrechoAutoLinha.municipio_b_id == origem_id,
                MunA.id != origem_id,
            )
        )

        municipios = {m.id: m for m in q_b.all()}
        municipios.update({m.id: m for m in q_a.all()})
        return [_municipio_to_dict(m) for m in sorted(municipios.values(), key=lambda m: m.nome)]


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


def buscar_autos_por_trecho(tipo_servico: str, cidade_a: str, cidade_b: str,
                             perm_id: int | None = None,
                             regiao: str | None = None) -> list[AutoDict]:
    """Autos com trecho explícito entre cidade_a e cidade_b."""
    with db_session() as s:
        q = _base_auto_query(s, tipo_servico, perm_id, regiao)

        if cidade_a:
            mun_a = _resolver_municipio_id(s, cidade_a)
            if mun_a:
                if cidade_b:
                    mun_b = _resolver_municipio_id(s, cidade_b)
                    if mun_b:
                        min_id, max_id = min(mun_a, mun_b), max(mun_a, mun_b)
                        q = q.filter(
                            AutoLinha.trechos.any(
                                (TrechoAutoLinha.municipio_a_id == min_id) &
                                (TrechoAutoLinha.municipio_b_id == max_id)
                            )
                        )
                else:
                    # Apenas cidade_a: retorna autos com qualquer trecho passando por ela
                    q = q.filter(
                        AutoLinha.trechos.any(
                            (TrechoAutoLinha.municipio_a_id == mun_a) |
                            (TrechoAutoLinha.municipio_b_id == mun_a)
                        )
                    )

        return [_auto_to_dict(a) for a in q.order_by(AutoLinha.numero).all()]
