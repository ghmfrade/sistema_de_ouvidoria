"""View Models da camada de aplicação (utils/).

Contratos entre loaders e pages — estruturas de apresentação montadas
a partir dos TypedDicts de repositório (repositories/types.py).

Separação conceitual (Clean Architecture):
  repositories/types.py  →  DTOs da camada de persistência
  utils/types.py         →  View Models da camada de aplicação
"""

from __future__ import annotations

from typing import TypedDict

from repositories.types import (
    AtribuicaoScalarDict,
    OuvidoriaDetalheDict,
    OuvidoriaTecnicoDict,
    ReclamacaoAutoDict,
    RespostaTecnicaDict,
)


class DetalheOuvidoriaView(TypedDict):
    """Retorno de carregar_detalhe_ouvidoria — usado pela página 03."""
    ouvidoria: OuvidoriaDetalheDict
    rec_autos: dict[int, list[ReclamacaoAutoDict]]  # reclamacao_id → autos
    tecnicos_info: dict[int, OuvidoriaTecnicoDict]  # tecnico_id → atribuicao


class RespostaTecnicaView(TypedDict):
    """Retorno de carregar_ouvidoria_para_resposta_tecnica — usado pela página 05."""
    ouvidoria: OuvidoriaDetalheDict
    atribuicao: AtribuicaoScalarDict | None
    resposta_existente: RespostaTecnicaDict | None
    historico: list[RespostaTecnicaDict]
