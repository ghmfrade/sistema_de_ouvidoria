"""Loaders do painel Admin: expõe dados de catálogo para as tabelas administrativas.

Estas funções existem para manter a boundary arquitetural pages/ → utils/ → repositories/.
A formatação de exibição (emojis, rótulos) é responsabilidade da page ou de formatters.py.
"""

from repositories.catalog_repo import (
    get_categorias,
    get_coordenacoes,
    get_gerencias,
    get_subcategorias,
    get_usuarios,
)
from repositories.types import (
    CategoriaDict,
    CoordenacaoDict,
    GerenciaDict,
    SubcategoriaDict,
    UsuarioDict,
)


def listar_usuarios_e_status() -> list[UsuarioDict]:
    """Todos os usuários para tabela admin."""
    return get_usuarios()


def listar_categorias_e_status() -> list[CategoriaDict]:
    """Categorias para tabela admin."""
    return get_categorias()


def listar_subcat_e_status() -> list[SubcategoriaDict]:
    """Subcategorias para tabela admin."""
    return get_subcategorias()


def listar_gerencias_e_status() -> list[GerenciaDict]:
    """Gerências para tabela admin."""
    return get_gerencias()


def listar_coord_e_status() -> list[CoordenacaoDict]:
    """Coordenações para tabela admin."""
    return get_coordenacoes()
