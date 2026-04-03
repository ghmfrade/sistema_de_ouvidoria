"""Consultas ao banco para carregamento de ouvidorias."""

from sqlalchemy.orm import joinedload

from database.connection import db_session
from models import (
    AnexoOuvidoria,
    AutoLinha,
    Ouvidoria,
    OuvidoriaTecnico,
    ReclamacaoAuto,
    Reclamacao,
    RespostaPermissionaria,
    RespostaTecnica,
    StatusOuvidoria,
    TipoUsuario,
    Usuario,
)


def get_ouvidoria_completa(oid: int):
    """Ouvidoria com TODOS os relacionamentos eager-loaded. Retorna Ouvidoria | None."""
    with db_session() as s:
        o = (
            s.query(Ouvidoria)
            .options(
                joinedload(Ouvidoria.reclamacoes)
                    .joinedload(Reclamacao.categoria),
                joinedload(Ouvidoria.reclamacoes)
                    .joinedload(Reclamacao.subcategoria),
                joinedload(Ouvidoria.reclamacoes)
                    .joinedload(Reclamacao.autos_vinculados)
                    .joinedload(ReclamacaoAuto.auto)
                    .joinedload(AutoLinha.permissionaria),
                joinedload(Ouvidoria.atribuicoes)
                    .joinedload(OuvidoriaTecnico.tecnico)
                    .joinedload(Usuario.gerencia),
                joinedload(Ouvidoria.atribuicoes)
                    .joinedload(OuvidoriaTecnico.tecnico)
                    .joinedload(Usuario.coordenacao),
                joinedload(Ouvidoria.respostas)
                    .joinedload(RespostaTecnica.tecnico),
                joinedload(Ouvidoria.respostas_permissionaria)
                    .joinedload(RespostaPermissionaria.registrado_por),
                joinedload(Ouvidoria.anexos)
                    .joinedload(AnexoOuvidoria.enviado_por),
            )
            .filter_by(id=oid)
            .first()
        )
        if o:
            s.expunge_all()
        return o


def get_ouvidoria_permissionaria(oid: int):
    """Ouvidoria com respostas_permissionaria eager-loaded. Retorna Ouvidoria | None."""
    with db_session() as s:
        o = (
            s.query(Ouvidoria)
            .options(
                joinedload(Ouvidoria.respostas_permissionaria)
                    .joinedload(RespostaPermissionaria.registrado_por),
            )
            .filter_by(id=oid)
            .first()
        )
        if o:
            s.expunge_all()
        return o


def get_atribuicao_tecnico(ouvidoria_id: int, tecnico_id: int):
    """Atribuição específica de técnico a uma ouvidoria. Retorna OuvidoriaTecnico | None."""
    with db_session() as s:
        at = (
            s.query(OuvidoriaTecnico)
            .filter_by(ouvidoria_id=ouvidoria_id, tecnico_id=tecnico_id)
            .first()
        )
        if at:
            s.expunge_all()
        return at


def get_respostas_tecnico(ouvidoria_id: int, tecnico_id: int):
    """Respostas técnicas de um técnico para uma ouvidoria, desc por data. Retorna list[RespostaTecnica]."""
    with db_session() as s:
        resps = (
            s.query(RespostaTecnica)
            .filter_by(ouvidoria_id=ouvidoria_id, tecnico_id=tecnico_id)
            .order_by(RespostaTecnica.data_resposta.desc())
            .all()
        )
        s.expunge_all()
        return resps


def get_ouvidorias(filtro_status=None, filtro_periodo=None,
                   ocultar_concluidos=True, usuario=None):
    """Lista de ouvidorias com filtros, com atribuicoes e técnicos eager-loaded.
    Retorna list[Ouvidoria]."""
    with db_session() as s:
        q = (
            s.query(Ouvidoria)
            .options(
                joinedload(Ouvidoria.atribuicoes)
                    .joinedload(OuvidoriaTecnico.tecnico)
                    .joinedload(Usuario.gerencia),
                joinedload(Ouvidoria.atribuicoes)
                    .joinedload(OuvidoriaTecnico.tecnico)
                    .joinedload(Usuario.coordenacao),
            )
        )
        if usuario and usuario.tipo == TipoUsuario.tecnico:
            q = (
                q.join(OuvidoriaTecnico, OuvidoriaTecnico.ouvidoria_id == Ouvidoria.id)
                .filter(OuvidoriaTecnico.tecnico_id == usuario.id)
            )
        if filtro_status:
            q = q.filter(Ouvidoria.status == filtro_status)
        elif ocultar_concluidos:
            q = q.filter(Ouvidoria.status != StatusOuvidoria.CONCLUIDO)
        if filtro_periodo:
            inicio, fim = filtro_periodo
            q = q.filter(Ouvidoria.criado_em >= inicio, Ouvidoria.criado_em <= fim)
        ouvidorias = q.order_by(Ouvidoria.prazo.asc()).all()
        s.expunge_all()
        return ouvidorias
