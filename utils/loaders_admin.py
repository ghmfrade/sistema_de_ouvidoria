"""Loaders do painel Admin: usuarios, categorias, subcategorias, gerencias, coordenacoes."""

from database.connection import get_session
from models import Categoria, Coordenacao, Gerencia, Subcategoria, Usuario


def listar_usuarios():
    """Retorna todos os usuarios com gerencia/coordenacao como lista de dicts."""
    s = get_session()
    try:
        users = s.query(Usuario).order_by(Usuario.nome).all()
        result = []
        for usr in users:
            g = usr.gerencia.nome if usr.gerencia else "–"
            c = usr.coordenacao.nome if usr.coordenacao else "–"
            result.append({
                "id": usr.id,
                "nome": usr.nome,
                "email": usr.email,
                "tipo": usr.tipo.value,
                "gerencia": g,
                "coordenacao": c,
                "ativo": "✅" if usr.ativo else "❌",
            })
        return result
    finally:
        s.close()


def carregar_gerencias():
    """Retorna todas as gerencias: [(id, nome)]."""
    s = get_session()
    try:
        gs = s.query(Gerencia).order_by(Gerencia.nome).all()
        return [(g.id, g.nome) for g in gs]
    finally:
        s.close()


def carregar_coordenacoes(gerencia_id=None):
    """Retorna coordenacoes, opcionalmente filtradas por gerencia: [(id, nome)]."""
    s = get_session()
    try:
        q = s.query(Coordenacao)
        if gerencia_id:
            q = q.filter_by(gerencia_id=gerencia_id)
        cs = q.order_by(Coordenacao.nome).all()
        return [(c.id, c.nome) for c in cs]
    finally:
        s.close()


def listar_cats():
    """Retorna categorias para admin: [{id, nome, descricao, ativo}]."""
    s = get_session()
    try:
        cats = s.query(Categoria).order_by(Categoria.nome).all()
        return [{"id": c.id, "nome": c.nome, "descricao": c.descricao or "", "ativo": "✅" if c.ativo else "❌"} for c in cats]
    finally:
        s.close()


def listar_subcats():
    """Retorna subcategorias com nome da categoria: [{id, nome, categoria, ativo}]."""
    s = get_session()
    try:
        subcats = (
            s.query(Subcategoria)
            .join(Categoria)
            .order_by(Categoria.nome, Subcategoria.nome)
            .all()
        )
        return [{
            "id": sc.id,
            "nome": sc.nome,
            "categoria": sc.categoria.nome if sc.categoria else "–",
            "ativo": "✅" if sc.ativo else "❌",
        } for sc in subcats]
    finally:
        s.close()


def listar_ger():
    """Retorna gerencias para admin: [{id, nome, ativo}]."""
    s = get_session()
    try:
        gs = s.query(Gerencia).order_by(Gerencia.nome).all()
        return [{"id": g.id, "nome": g.nome, "ativo": "✅" if g.ativo else "❌"} for g in gs]
    finally:
        s.close()


def listar_coord():
    """Retorna coordenacoes com nome da gerencia: [{id, nome, gerencia, ativo}]."""
    s = get_session()
    try:
        cs = s.query(Coordenacao).order_by(Coordenacao.nome).all()
        return [{"id": c.id, 
                 "nome": c.nome, 
                 "gerencia": c.gerencia.nome if c.gerencia else "–", 
                 "ativo": "✅" if c.ativo else "❌"} for c in cs]
    finally:
        s.close()
