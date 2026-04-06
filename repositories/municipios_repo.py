"""Consultas ao banco relacionadas a municípios."""

from database.connection import db_session
from models import AutoLinha, Municipio, TrechoAutoLinha
from repositories.types import MunicipioDict


def get_municipios_sp() -> list[MunicipioDict]:
    """Municípios de SP ordenados por nome."""
    with db_session() as s:
        munis = s.query(Municipio).filter_by(estado="SP").order_by(Municipio.nome).all()
        return [
            MunicipioDict(id=m.id, nome=m.nome, estado=m.estado,
                          cod_ibge=m.cod_ibge, populacao=m.populacao)
            for m in munis
        ]


def get_municipios_por_tipo_servico(tipo_servico: str) -> list[MunicipioDict]:
    """Municípios com trechos em linhas ativas do tipo informado."""
    with db_session() as s:
        mun_a = (
            s.query(Municipio)
            .join(TrechoAutoLinha, TrechoAutoLinha.municipio_a_id == Municipio.id)
            .join(AutoLinha, AutoLinha.id == TrechoAutoLinha.auto_id)
            .filter(AutoLinha.tipo == tipo_servico, AutoLinha.ativo == True)
        )
        mun_b = (
            s.query(Municipio)
            .join(TrechoAutoLinha, TrechoAutoLinha.municipio_b_id == Municipio.id)
            .join(AutoLinha, AutoLinha.id == TrechoAutoLinha.auto_id)
            .filter(AutoLinha.tipo == tipo_servico, AutoLinha.ativo == True)
        )
        munis = mun_a.union(mun_b).order_by(Municipio.nome).all()
        return [
            MunicipioDict(id=m.id, nome=m.nome, estado=m.estado,
                          cod_ibge=m.cod_ibge, populacao=m.populacao)
            for m in munis
        ]
