"""Consultas ao banco relacionadas a municípios."""

from database.connection import db_session
from models import AutoLinha, Municipio, ParadaAutoLinha


def get_municipios_sp():
    """Municípios de SP ordenados por nome. Retorna list[Municipio]."""
    with db_session() as s:
        munis = s.query(Municipio).filter_by(estado="SP").order_by(Municipio.nome).all()
        s.expunge_all()
        return munis


def get_municipios_por_tipo_servico(tipo_servico: str):
    """Municípios com paradas em linhas ativas do tipo informado. Retorna list[Municipio]."""
    with db_session() as s:
        munis = (
            s.query(Municipio)
            .join(ParadaAutoLinha, ParadaAutoLinha.municipio_id == Municipio.id)
            .join(AutoLinha, AutoLinha.id == ParadaAutoLinha.auto_id)
            .filter(
                AutoLinha.tipo == tipo_servico,
                AutoLinha.ativo == True,
            )
            .distinct()
            .all()
        )
        s.expunge_all()
        return munis
