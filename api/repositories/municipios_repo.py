"""Consultas ao banco relacionadas a municípios."""

from api.database.connection import db_session
from api.models import AutoLinha, Municipio, TrechoAutoLinha
from api.repositories.types import MunicipioDict


def _to_dict(m: Municipio) -> MunicipioDict:
    return MunicipioDict(
        id=m.id,
        nome=m.nome,
        estado=m.estado,
        cod_ibge=m.cod_ibge,
        populacao=m.populacao
    )

def get_municipios_sp() -> list[MunicipioDict]:
    """Municípios de SP ordenados por nome."""
    with db_session() as s:
        munis = (
            s.query(Municipio)
            .filter_by(estado="SP")
            .order_by(Municipio.nome)
            .all()
        )
        return [_to_dict(m) for m in munis]

def get_municipios_com_linhas(
    tipo_servico: str,
    perm_id: int | None = None,
    regiao: str | None = None
) -> list[MunicipioDict]:
    """Municípios com trechos em linhas ativas do tipo informado."""

    with db_session() as s:
        base_filter = [
            AutoLinha.tipo == tipo_servico,
            AutoLinha.ativo.is_(True)  # pequeno ajuste aqui 👀
        ]

        if perm_id is not None:
            base_filter.append(AutoLinha.permissionaria_id == perm_id)

        if regiao is not None:
            base_filter.append(AutoLinha.regiao_metropolitana == regiao)

        mun_a = (
            s.query(Municipio)
            .join(TrechoAutoLinha, TrechoAutoLinha.municipio_a_id == Municipio.id)
            .join(AutoLinha, AutoLinha.id == TrechoAutoLinha.auto_id)
            .filter(*base_filter)
        )

        mun_b = (
            s.query(Municipio)
            .join(TrechoAutoLinha, TrechoAutoLinha.municipio_b_id == Municipio.id)
            .join(AutoLinha, AutoLinha.id == TrechoAutoLinha.auto_id)
            .filter(*base_filter)
        )

        munis = mun_a.union(mun_b).order_by(Municipio.nome).all()

        return [_to_dict(m) for m in munis]
