"""Operações de escrita no banco para administração de catálogo."""

from api.database.connection import db_session
from api.models import (
    Categoria,
    Coordenacao,
    Gerencia,
    Subcategoria,
    Usuario,
    TipoUsuario,
)


def email_existe(email: str, apenas_ativos: bool = False, exclude_id: int | None = None) -> bool:
    """Verifica se já existe usuário com o email informado."""
    with db_session() as s:
        q = s.query(Usuario).filter(Usuario.email == email.strip())
        if apenas_ativos:
            q = q.filter(Usuario.ativo == True)  # noqa: E712
        if exclude_id is not None:
            q = q.filter(Usuario.id != exclude_id)
        return q.first() is not None


def criar_usuario(nome, email, senha_hash, tipo, gerencia_id, coordenacao_id):
    """Cria novo usuário."""
    with db_session() as s:
        s.add(Usuario(
            nome=nome.strip(),
            email=email.strip(),
            senha_hash=senha_hash,
            tipo=TipoUsuario(tipo),
            gerencia_id=gerencia_id,
            coordenacao_id=coordenacao_id,
            ativo=True,
        ))


def toggle_usuario(usuario_id: int, ativo: bool):
    """Ativa ou desativa usuário."""
    with db_session() as s:
        usr = s.query(Usuario).filter_by(id=usuario_id).first()
        if usr:
            usr.ativo = ativo


def editar_usuario(usuario_id: int, nova_senha_hash: str | None, tipo: str):
    """Atualiza senha e/ou perfil de um usuário existente."""
    with db_session() as s:
        usr = s.query(Usuario).filter_by(id=usuario_id).first()
        if usr:
            if nova_senha_hash:
                usr.senha_hash = nova_senha_hash
            usr.tipo = TipoUsuario(tipo)


def criar_categoria(nome, descricao=None):
    """Cria nova categoria."""
    with db_session() as s:
        s.add(Categoria(nome=nome.strip(), descricao=descricao.strip() if descricao else None))


def toggle_categoria(cat_id: int, ativo: bool):
    """Ativa ou desativa categoria."""
    with db_session() as s:
        cat = s.query(Categoria).filter_by(id=cat_id).first()
        if cat:
            cat.ativo = ativo


def criar_subcategoria(nome, categoria_id):
    """Cria nova subcategoria."""
    with db_session() as s:
        s.add(Subcategoria(nome=nome.strip(), categoria_id=categoria_id))


def toggle_subcategoria(subcat_id: int, ativo: bool):
    """Ativa ou desativa subcategoria."""
    with db_session() as s:
        sc = s.query(Subcategoria).filter_by(id=subcat_id).first()
        if sc:
            sc.ativo = ativo


def criar_gerencia(nome):
    """Cria nova gerência."""
    with db_session() as s:
        s.add(Gerencia(nome=nome.strip()))


def toggle_gerencia(ger_id: int, ativo: bool):
    """Ativa ou desativa gerência."""
    with db_session() as s:
        ger = s.query(Gerencia).filter_by(id=ger_id).first()
        if ger:
            ger.ativo = ativo


def criar_coordenacao(nome, gerencia_id):
    """Cria nova coordenação."""
    with db_session() as s:
        s.add(Coordenacao(nome=nome.strip(), gerencia_id=gerencia_id))


def toggle_coordenacao(coord_id: int, ativo: bool):
    """Ativa ou desativa coordenação."""
    with db_session() as s:
        coord = s.query(Coordenacao).filter_by(id=coord_id).first()
        if coord:
            coord.ativo = ativo
