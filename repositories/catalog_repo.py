"""Consultas ao banco de dados de catálogo: usuários, categorias, subcategorias, gerências, coordenações."""

from sqlalchemy.orm import joinedload

from database.connection import db_session
from models import Categoria, Coordenacao, Gerencia, Permissionaria, Subcategoria, TipoUsuario, Usuario


def get_usuarios():
    """Todos os usuários com gerência e coordenação carregadas."""
    with db_session() as s:
        users = (
            s.query(Usuario)
            .options(joinedload(Usuario.gerencia), joinedload(Usuario.coordenacao))
            .order_by(Usuario.nome)
            .all()
        )
        s.expunge_all()
        return users


def get_categorias():
    """Todas as categorias ordenadas por nome."""
    with db_session() as s:
        cats = s.query(Categoria).order_by(Categoria.nome).all()
        s.expunge_all()
        return cats


def get_subcategorias(categoria_id: int | None = None):
    """Todas as subcategorias, opcionalmente filtradas por categoria, com categoria carregada."""
    with db_session() as s:
        q = (
            s.query(Subcategoria)
            .options(joinedload(Subcategoria.categoria))
            .order_by(Subcategoria.nome)
        )
        if categoria_id is not None:
            q = q.filter_by(categoria_id=categoria_id)
        subcats = q.all()
        s.expunge_all()
        return subcats


def get_gerencias():
    """Todas as gerências ordenadas por nome."""
    with db_session() as s:
        gs = s.query(Gerencia).order_by(Gerencia.nome).all()
        s.expunge_all()
        return gs


def get_coordenacoes(gerencia_id: int | None = None):
    """Coordenações, opcionalmente filtradas por gerência, com gerência carregada."""
    with db_session() as s:
        q = (
            s.query(Coordenacao)
            .options(joinedload(Coordenacao.gerencia))
            .order_by(Coordenacao.nome)
        )
        if gerencia_id is not None:
            q = q.filter_by(gerencia_id=gerencia_id)
        coords = q.all()
        s.expunge_all()
        return coords


def get_tecnicos_ativos():
    """Técnicos ativos ordenados por nome. Retorna list[Usuario]."""
    with db_session() as s:
        tecs = (
            s.query(Usuario)
            .filter_by(tipo=TipoUsuario.tecnico, ativo=True)
            .order_by(Usuario.nome)
            .all()
        )
        s.expunge_all()
        return tecs


def get_todas_permissionarias():
    """Todas as permissionárias ordenadas por nome. Retorna list[Permissionaria]."""
    with db_session() as s:
        perms = s.query(Permissionaria).order_by(Permissionaria.nome).all()
        s.expunge_all()
        return perms
