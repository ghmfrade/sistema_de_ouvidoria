"""utils/ — Modulos utilitarios do frontend (loaders, formatters, queries)."""

from .formatters import fmt_auto, prazo_circle_label, to_excel
from .loaders_admin import (
    carregar_coordenacoes,
    carregar_gerencias,
    listar_cats,
    listar_coord,
    listar_ger,
    listar_subcats,
    listar_usuarios,
)
from .loaders_auto import (
    buscar_autos_por_trecho,
    carregar_cidades,
    carregar_cidades_destino,
    carregar_cidades_por_tipo,
    carregar_permissionarias,
    carregar_regioes_metropolitanas,
    carregar_todos_autos,
)
from .loaders_catalog import (
    carregar_categorias,
    carregar_gerencias_ativas,
    carregar_municipios,
    carregar_subcategorias,
)
from .loaders_ouvidoria import (
    carregar_detalhe_ouvidoria,
    carregar_ouvidoria_para_permissionaria,
    carregar_ouvidoria_para_resposta_tecnica,
)
from .ouvidoria_ops import (
    atribuir_tecnico,
    carregar_tecnicos_disponiveis,
    concluir_ouvidoria,
    excluir_ouvidoria,
    listar_ouvidorias,
)

__all__ = [
    # formatters
    "fmt_auto", "prazo_circle_label", "to_excel",
    # loaders_admin
    "carregar_coordenacoes", "carregar_gerencias", "listar_cats", "listar_coord",
    "listar_ger", "listar_subcats", "listar_usuarios",
    # loaders_auto
    "buscar_autos_por_trecho", "carregar_cidades", "carregar_cidades_destino",
    "carregar_cidades_por_tipo", "carregar_permissionarias",
    "carregar_regioes_metropolitanas", "carregar_todos_autos",
    # loaders_catalog
    "carregar_categorias", "carregar_gerencias_ativas", "carregar_municipios",
    "carregar_subcategorias",
    # loaders_ouvidoria
    "carregar_detalhe_ouvidoria", "carregar_ouvidoria_para_permissionaria",
    "carregar_ouvidoria_para_resposta_tecnica",
    # ouvidoria_ops
    "atribuir_tecnico", "carregar_tecnicos_disponiveis", "concluir_ouvidoria",
    "excluir_ouvidoria", "listar_ouvidorias",
]
