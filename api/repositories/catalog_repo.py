"""Consultas ao banco de dados de catálogo: usuários, categorias, subcategorias, gerências, coordenações."""

from sqlalchemy.orm import joinedload

from api.database.connection import db_session
from api.models import Categoria, Coordenacao, Gerencia, Permissionaria, Subcategoria, TipoUsuario, Usuario
from api.repositories.types import (
    CategoriaDict,
    CoordenacaoDict,
    GerenciaDict,
    PermissionariaDict,
    SubcategoriaDict,
    UsuarioDict,
)


def get_usuario_por_id(usuario_id: int) -> UsuarioDict | None:
    """Retorna um usuário pelo id, ou None se não encontrado."""
    with db_session() as s:
        u = (
            s.query(Usuario)
            .options(joinedload(Usuario.gerencia), joinedload(Usuario.coordenacao))
            .filter(Usuario.id == usuario_id)
            .first()
        )
        if not u:
            return None
        return UsuarioDict(
            id=u.id,
            nome=u.nome,
            email=u.email,
            tipo=u.tipo.value,
            gerencia_id=u.gerencia_id,
            gerencia_nome=u.gerencia.nome if u.gerencia else None,
            coordenacao_id=u.coordenacao_id,
            coordenacao_nome=u.coordenacao.nome if u.coordenacao else None,
            ativo=u.ativo,
        )


def get_usuarios() -> list[UsuarioDict]:
    """Todos os usuários com gerência e coordenação."""
    with db_session() as s:
        users = (
            s.query(Usuario)
            .options(joinedload(Usuario.gerencia), joinedload(Usuario.coordenacao))
            .order_by(Usuario.nome)
            .all()
        )
        return [
            UsuarioDict(
                id=u.id,
                nome=u.nome,
                email=u.email,
                tipo=u.tipo.value,
                gerencia_id=u.gerencia_id,
                gerencia_nome=u.gerencia.nome if u.gerencia else None,
                coordenacao_id=u.coordenacao_id,
                coordenacao_nome=u.coordenacao.nome if u.coordenacao else None,
                ativo=u.ativo,
            )
            for u in users
        ]


def get_categorias() -> list[CategoriaDict]:
    """Todas as categorias ordenadas por nome."""
    with db_session() as s:
        cats = s.query(Categoria).order_by(Categoria.nome).all()
        return [
            CategoriaDict(id=c.id, nome=c.nome, descricao=c.descricao, ativo=c.ativo)
            for c in cats
        ]


def get_subcategorias(categoria_id: int | None = None) -> list[SubcategoriaDict]:
    """Todas as subcategorias, opcionalmente filtradas por categoria."""
    with db_session() as s:
        q = (
            s.query(Subcategoria)
            .options(joinedload(Subcategoria.categoria))
            .order_by(Subcategoria.nome)
        )
        if categoria_id is not None:
            q = q.filter_by(categoria_id=categoria_id)
        subcats = q.all()
        return [
            SubcategoriaDict(
                id=sc.id,
                nome=sc.nome,
                categoria_id=sc.categoria_id,
                categoria_nome=sc.categoria.nome if sc.categoria else "",
                ativo=sc.ativo,
            )
            for sc in subcats
        ]


def get_gerencias() -> list[GerenciaDict]:
    """Todas as gerências ordenadas por nome."""
    with db_session() as s:
        gs = s.query(Gerencia).order_by(Gerencia.nome).all()
        return [GerenciaDict(id=g.id, nome=g.nome, ativo=g.ativo) for g in gs]


def get_coordenacoes(gerencia_id: int | None = None) -> list[CoordenacaoDict]:
    """Coordenações, opcionalmente filtradas por gerência."""
    with db_session() as s:
        q = (
            s.query(Coordenacao)
            .options(joinedload(Coordenacao.gerencia))
            .order_by(Coordenacao.nome)
        )
        if gerencia_id is not None:
            q = q.filter_by(gerencia_id=gerencia_id)
        coords = q.all()
        return [
            CoordenacaoDict(
                id=c.id,
                nome=c.nome,
                gerencia_id=c.gerencia_id,
                gerencia_nome=c.gerencia.nome if c.gerencia else None,
                ativo=c.ativo,
            )
            for c in coords
        ]


def get_tecnicos_ativos() -> list[UsuarioDict]:
    """Técnicos ativos ordenados por nome."""
    with db_session() as s:
        tecs = (
            s.query(Usuario)
            .filter_by(tipo=TipoUsuario.tecnico, ativo=True)
            .order_by(Usuario.nome)
            .all()
        )
        return [
            UsuarioDict(
                id=t.id,
                nome=t.nome,
                email=t.email,
                tipo=t.tipo.value,
                gerencia_id=t.gerencia_id,
                gerencia_nome=None,
                coordenacao_id=t.coordenacao_id,
                coordenacao_nome=None,
                ativo=t.ativo,
            )
            for t in tecs
        ]


def get_todas_permissionarias() -> list[PermissionariaDict]:
    """Todas as permissionárias ordenadas por nome."""
    with db_session() as s:
        perms = s.query(Permissionaria).order_by(Permissionaria.nome).all()
        return [PermissionariaDict(id=p.id, nome=p.nome) for p in perms]
