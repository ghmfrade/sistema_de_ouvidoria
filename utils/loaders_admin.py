"""Loaders do painel Admin: organiza dados do catálogo para exibição em tabelas administrativas."""

from repositories.catalog_repo import (
    get_categorias,
    get_coordenacoes,
    get_gerencias,
    get_subcategorias,
    get_usuarios,
)


def listar_usuarios_e_status():
    """Todos os usuários formatados para tabela admin: [dict]."""
    return [
        {
            "id": u.id,
            "nome": u.nome,
            "email": u.email,
            "tipo": u.tipo.value,
            "gerencia": u.gerencia.nome if u.gerencia else "–",
            "coordenacao": u.coordenacao.nome if u.coordenacao else "–",
            "ativo": "✅" if u.ativo else "❌",
        }
        for u in get_usuarios()
    ]


def listar_categorias_e_status():
    """Categorias formatadas para tabela admin: [dict]."""
    return [
        {
            "id": c.id,
            "nome": c.nome,
            "descricao": c.descricao or "",
            "ativo": "✅" if c.ativo else "❌",
        }
        for c in get_categorias()
    ]


def listar_subcat_e_status():
    """Subcategorias formatadas para tabela admin: [dict]."""
    return [
        {
            "id": sc.id,
            "nome": sc.nome,
            "categoria": sc.categoria.nome if sc.categoria else "–",
            "ativo": "✅" if sc.ativo else "❌",
        }
        for sc in get_subcategorias()
    ]


def listar_gerencias_e_status():
    """Gerências formatadas para tabela admin: [dict]."""
    return [
        {"id": g.id, "nome": g.nome, "ativo": "✅" if g.ativo else "❌"}
        for g in get_gerencias()
    ]


def listar_coord_e_status():
    """Coordenações formatadas para tabela admin: [dict]."""
    return [
        {
            "id": c.id,
            "nome": c.nome,
            "gerencia": c.gerencia.nome if c.gerencia else "–",
            "ativo": "✅" if c.ativo else "❌",
        }
        for c in get_coordenacoes()
    ]
