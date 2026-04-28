"""utils/ — Módulos utilitários do frontend (loaders, formatters, queries)."""

from .formatters import fmt_auto, fmt_ativo, formatar_atribuicoes, prazo_circle_label, to_excel
from .html_resumo import gerar_html_resumo
from .loaders_admin import (
    listar_categorias_e_status,
    listar_coord_e_status,
    listar_gerencias_e_status,
    listar_subcat_e_status,
    listar_usuarios_e_status,
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
    carregar_coordenacoes,
    carregar_gerencias_ativas,
    carregar_municipios,
    carregar_subcategorias,
    carregar_todas_gerencias,
    carregar_todas_permissionarias,
)
from .loaders_dashboard import (
    query_categorias_pizza,
    query_cidades,
    query_distribuicao_status,
    query_empresas_pontuacao,
    query_evolucao_mensal,
    query_heatmap_cat_empresa,
    query_kpis_produtividade,
    query_kpis_qualidade,
    query_ranking_coordenacoes,
    query_sla,
    query_tabela_analitica,
    query_tempo_medio_por_tecnico,
    query_tempo_medio_resposta,
    query_tendencia_empresa,
    query_top_autos_pontuacao,
    query_top_categoria,
    query_top_permissionaria,
    query_vencidas_por_coordenacao,
    query_volume_por_mes,
)
from .loaders_ouvidoria import (
    carregar_detalhe_ouvidoria,
    carregar_ouvidoria_para_permissionaria,
    carregar_ouvidoria_para_resposta_tecnica,
)
from .ouvidoria_ops import (
    atribuir_tecnico,
    buscar_ouvidoria_por_protocolo,
    carregar_tecnicos_disponiveis,
    alterar_status_ouvidoria,
    concluir_ouvidoria,
    excluir_ouvidoria,
    listar_ouvidorias,
)
from .types import DetalheOuvidoriaView, RespostaTecnicaView

__all__ = [
    # formatters
    "gerar_html_resumo",
    "fmt_auto",
    "fmt_ativo",
    "formatar_atribuicoes",
    "prazo_circle_label",
    "to_excel",
    # loaders_admin
    "listar_categorias_e_status",
    "listar_coord_e_status",
    "listar_gerencias_e_status",
    "listar_subcat_e_status",
    "listar_usuarios_e_status",
    # loaders_auto
    "buscar_autos_por_trecho",
    "carregar_cidades",
    "carregar_cidades_destino",
    "carregar_cidades_por_tipo",
    "carregar_permissionarias",
    "carregar_regioes_metropolitanas",
    "carregar_todos_autos",
    # loaders_catalog
    "carregar_categorias",
    "carregar_coordenacoes",
    "carregar_gerencias_ativas",
    "carregar_municipios",
    "carregar_subcategorias",
    "carregar_todas_gerencias",
    "carregar_todas_permissionarias",
    # loaders_dashboard (produtividade)
    "query_kpis_produtividade",
    "query_tempo_medio_resposta",
    "query_volume_por_mes",
    "query_distribuicao_status",
    "query_vencidas_por_coordenacao",
    "query_tempo_medio_por_tecnico",
    "query_ranking_coordenacoes",
    # loaders_dashboard (qualidade)
    "query_kpis_qualidade",
    "query_top_permissionaria",
    "query_top_categoria",
    "query_sla",
    "query_evolucao_mensal",
    "query_top_autos_pontuacao",
    "query_empresas_pontuacao",
    "query_categorias_pizza",
    "query_cidades",
    "query_heatmap_cat_empresa",
    "query_tendencia_empresa",
    "query_tabela_analitica",
    # loaders_ouvidoria
    "carregar_detalhe_ouvidoria",
    "carregar_ouvidoria_para_permissionaria",
    "carregar_ouvidoria_para_resposta_tecnica",
    # ouvidoria_ops
    "atribuir_tecnico",
    "buscar_ouvidoria_por_protocolo",
    "carregar_tecnicos_disponiveis",
    "alterar_status_ouvidoria",
    "concluir_ouvidoria",
    "excluir_ouvidoria",
    "listar_ouvidorias",
    # types (View Models)
    "DetalheOuvidoriaView",
    "RespostaTecnicaView",
]
