"""Consultas ao banco relacionadas a autos de linha, permissionárias e regiões."""

from sqlalchemy import exists
from sqlalchemy.orm import aliased, joinedload

from database.connection import db_session
from models import AutoLinha, Municipio, ParadaAutoLinha, Permissionaria, TipoServico


def get_municipios_com_paradas(tipo_servico: str, perm_id: int | None = None, regiao: str | None = None):
    """Municípios com paradas ativas no tipo de serviço. Retorna list[Municipio]."""
    with db_session() as s:
        q = (
            s.query(Municipio)
            .join(ParadaAutoLinha, ParadaAutoLinha.municipio_id == Municipio.id)
            .join(AutoLinha, AutoLinha.id == ParadaAutoLinha.auto_id)
            .filter(AutoLinha.tipo == tipo_servico, AutoLinha.ativo == True)
        )
        if perm_id is not None:
            q = q.filter(AutoLinha.permissionaria_id == perm_id)
        if regiao is not None:
            q = q.filter(AutoLinha.regiao_metropolitana == regiao)
        munis = q.distinct().all()
        s.expunge_all()
        return munis


def get_municipios_destino(tipo_servico: str, nome_origem: str,
                           perm_id: int | None = None, regiao: str | None = None):
    """Municípios alcançáveis a partir da origem (exceto a origem). Retorna list[Municipio]."""
    with db_session() as s:
        mun_id_orig = s.query(Municipio.id).filter_by(nome=nome_origem).scalar()
        if not mun_id_orig:
            return []

        ParadaOrig = aliased(ParadaAutoLinha)
        q = (
            s.query(Municipio)
            .join(ParadaAutoLinha, ParadaAutoLinha.municipio_id == Municipio.id)
            .join(AutoLinha, AutoLinha.id == ParadaAutoLinha.auto_id)
            .filter(
                AutoLinha.tipo == tipo_servico,
                AutoLinha.ativo == True,
                Municipio.id != mun_id_orig,
                exists().where(
                    (ParadaOrig.auto_id == AutoLinha.id) &
                    (ParadaOrig.municipio_id == mun_id_orig)
                ),
            )
        )
        if perm_id is not None:
            q = q.filter(AutoLinha.permissionaria_id == perm_id)
        if regiao is not None:
            q = q.filter(AutoLinha.regiao_metropolitana == regiao)
        munis = q.distinct().all()
        s.expunge_all()
        return munis


def get_todos_autos(tipo_servico: str, perm_id: int | None = None, regiao: str | None = None):
    """Todos os autos ativos filtrados. Retorna list[AutoLinha] com permissionaria carregada."""
    with db_session() as s:
        q = (
            s.query(AutoLinha)
            .options(joinedload(AutoLinha.permissionaria))
            .filter(AutoLinha.tipo == tipo_servico, AutoLinha.ativo == True)
        )
        if perm_id is not None:
            q = q.filter(AutoLinha.permissionaria_id == perm_id)
        if regiao is not None:
            q = q.filter(AutoLinha.regiao_metropolitana == regiao)
        autos = q.order_by(AutoLinha.numero).all()
        s.expunge_all()
        return autos


def get_permissionarias(tipo_servico: str, regiao: str | None = None):
    """Permissionárias com autos ativos do tipo informado. Retorna list[Permissionaria]."""
    with db_session() as s:
        q = (
            s.query(Permissionaria)
            .join(AutoLinha, AutoLinha.permissionaria_id == Permissionaria.id)
            .filter(AutoLinha.tipo == tipo_servico, AutoLinha.ativo == True)
        )
        if regiao is not None:
            q = q.filter(AutoLinha.regiao_metropolitana == regiao)
        perms = q.distinct().order_by(Permissionaria.nome).all()
        s.expunge_all()
        return perms


def get_autos_regioes_metropolitanas():
    """Autos regulares metropolitanos ativos com regiao_metropolitana preenchida.
    Retorna list[AutoLinha] (apenas para extração de regiao_metropolitana no loader)."""
    with db_session() as s:
        autos = (
            s.query(AutoLinha)
            .filter(
                AutoLinha.tipo == TipoServico.REGULAR_METROPOLITANO.value,
                AutoLinha.ativo == True,
                AutoLinha.regiao_metropolitana.isnot(None),
            )
            .all()
        )
        s.expunge_all()
        return autos


def buscar_autos_por_trecho(tipo_servico: str, cidade_a: str, cidade_b: str,
                            perm_id: int | None = None, regiao: str | None = None):
    """Autos que possuem paradas em AMBAS as cidades. Retorna list[AutoLinha] com permissionaria."""
    with db_session() as s:
        q = (
            s.query(AutoLinha)
            .options(joinedload(AutoLinha.permissionaria))
            .filter(AutoLinha.tipo == tipo_servico, AutoLinha.ativo == True)
        )
        if perm_id is not None:
            q = q.filter(AutoLinha.permissionaria_id == perm_id)
        if regiao is not None:
            q = q.filter(AutoLinha.regiao_metropolitana == regiao)
        if cidade_a:
            mun_id_a = s.query(Municipio.id).filter_by(nome=cidade_a).scalar()
            if mun_id_a:
                q = q.filter(exists().where(
                    (ParadaAutoLinha.auto_id == AutoLinha.id) &
                    (ParadaAutoLinha.municipio_id == mun_id_a)
                ))
        if cidade_b:
            mun_id_b = s.query(Municipio.id).filter_by(nome=cidade_b).scalar()
            if mun_id_b:
                q = q.filter(exists().where(
                    (ParadaAutoLinha.auto_id == AutoLinha.id) &
                    (ParadaAutoLinha.municipio_id == mun_id_b)
                ))
        autos = q.order_by(AutoLinha.numero).all()
        s.expunge_all()
        return autos
