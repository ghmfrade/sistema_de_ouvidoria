"""Marcação por cores das ouvidorias (por login) e legenda de cores."""
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from api.database.connection import db_session
from api.models import CorMarcacao, MarcadorLegenda, Ouvidoria, OuvidoriaMarcacao
from api.repositories.types import LegendaItemDict


def definir_marcacao(ouvidoria_id: int, usuario_id: int, cor: str) -> bool:
    """Upsert da cor. Retorna False se a ouvidoria não existir."""
    with db_session() as s:
        if s.get(Ouvidoria, ouvidoria_id) is None:
            return False
        stmt = pg_insert(OuvidoriaMarcacao).values(
            ouvidoria_id=ouvidoria_id, usuario_id=usuario_id, cor=cor
        )
        s.execute(stmt.on_conflict_do_update(
            index_elements=["ouvidoria_id", "usuario_id"],
            set_={"cor": cor, "marcado_em": func.now()},
        ))
    return True


def remover_marcacao(ouvidoria_id: int, usuario_id: int) -> None:
    """Remove a cor; idempotente."""
    with db_session() as s:
        s.query(OuvidoriaMarcacao).filter_by(
            ouvidoria_id=ouvidoria_id, usuario_id=usuario_id
        ).delete(synchronize_session=False)


def get_marcacoes_usuario(usuario_id: int, ouvidoria_ids: list[int]) -> dict[int, str]:
    """{ouvidoria_id: cor} do usuário, em uma única query."""
    if not ouvidoria_ids:
        return {}
    with db_session() as s:
        linhas = (
            s.query(OuvidoriaMarcacao.ouvidoria_id, OuvidoriaMarcacao.cor)
            .filter(
                OuvidoriaMarcacao.usuario_id == usuario_id,
                OuvidoriaMarcacao.ouvidoria_id.in_(ouvidoria_ids),
            )
            .all()
        )
        return {oid: cor for oid, cor in linhas}


def get_legenda(usuario_id: int) -> list[LegendaItemDict]:
    """Sempre as 7 cores na ordem do enum; rotulo vazio quando não definido."""
    with db_session() as s:
        rotulos = dict(
            s.query(MarcadorLegenda.cor, MarcadorLegenda.rotulo)
            .filter(MarcadorLegenda.usuario_id == usuario_id)
            .all()
        )
    return [LegendaItemDict(cor=c.value, rotulo=rotulos.get(c.value, "")) for c in CorMarcacao]


def salvar_legenda(usuario_id: int, itens: list[dict]) -> None:
    """Rótulo vazio apaga; senão upsert. Cores não enviadas ficam como estão."""
    with db_session() as s:
        for item in itens:
            rotulo = item["rotulo"].strip()
            if not rotulo:
                s.query(MarcadorLegenda).filter_by(
                    usuario_id=usuario_id, cor=item["cor"]
                ).delete(synchronize_session=False)
                continue
            stmt = pg_insert(MarcadorLegenda).values(
                usuario_id=usuario_id, cor=item["cor"], rotulo=rotulo
            )
            s.execute(stmt.on_conflict_do_update(
                index_elements=["usuario_id", "cor"], set_={"rotulo": rotulo},
            ))
