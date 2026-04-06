"""Contratos de dados (TypedDicts) retornados pelos repositórios de leitura.

Regra: nenhuma função de repositório retorna instâncias SQLAlchemy fora da sessão.
Toda conversão ORM → TypedDict acontece dentro do bloco `with db_session() as s:`.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TypedDict


# ── Catálogo ──────────────────────────────────────────────────────────────────

class MunicipioDict(TypedDict):
    id: int
    nome: str
    estado: str
    cod_ibge: int
    populacao: int


class CategoriaDict(TypedDict):
    id: int
    nome: str
    descricao: str | None
    ativo: bool


class SubcategoriaDict(TypedDict):
    id: int
    nome: str
    categoria_id: int
    categoria_nome: str
    ativo: bool


class GerenciaDict(TypedDict):
    id: int
    nome: str
    ativo: bool


class CoordenacaoDict(TypedDict):
    id: int
    nome: str
    gerencia_id: int | None
    gerencia_nome: str | None
    ativo: bool


class PermissionariaDict(TypedDict):
    id: int
    nome: str
    nome_fantasia: str | None
    cnpj: str


class UsuarioDict(TypedDict):
    id: int
    nome: str
    email: str
    tipo: str               # TipoUsuario.value
    gerencia_id: int | None
    gerencia_nome: str | None
    coordenacao_id: int | None
    coordenacao_nome: str | None
    ativo: bool


# ── Autos ─────────────────────────────────────────────────────────────────────

class AutoDict(TypedDict):
    id: int
    numero: str
    denominacao_a: str | None   # descrição do ponto inicial/sentido A
    denominacao_b: str | None   # descrição do ponto final/sentido B
    permissionaria_id: int | None
    permissionaria_nome: str    # nome_fantasia OR nome (resolvido no repo)
    tipo: str                   # TipoServico.value
    regiao_metropolitana: str | None
    sub_regiao: str | None
    tc: int | None              # região TC (1=Campinas, 2=Sorocaba, 3=Bauru, 4=Araraquara, 5=São Paulo)
    ativo: bool


# ── Ouvidoria — estruturas aninhadas ──────────────────────────────────────────

class ReclamacaoAutoDict(TypedDict):
    """Auto vinculado a uma reclamação (ReclamacaoAuto N:N)."""
    auto_id: int
    numero: str
    denominacao_a: str | None
    denominacao_b: str | None
    permissionaria_nome: str
    tipo: str | None            # TipoServico.value
    regiao_metropolitana: str | None
    tc: int | None              # região TC (1=Campinas, 2=Sorocaba, 3=Bauru, 4=Araraquara, 5=São Paulo)
    pontuacao: float | None


class ReclamacaoDict(TypedDict):
    id: int
    numero_item: int
    categoria_id: int | None
    categoria_nome: str | None
    subcategoria_id: int | None
    subcategoria_nome: str | None
    tipo_servico: str | None    # TipoServico.value
    local_embarque: str | None
    local_desembarque: str | None
    empresa_fretamento: str | None
    descricao: str | None
    autos: list[ReclamacaoAutoDict]


class OuvidoriaTecnicoDict(TypedDict):
    """Atribuição de técnico a uma ouvidoria."""
    tecnico_id: int
    tecnico_nome: str
    gerencia_nome: str | None
    coordenacao_nome: str | None
    respondido: bool
    respondido_em: datetime | None


class AtribuicaoScalarDict(TypedDict):
    """Resultado de get_atribuicao_tecnico — apenas scalars de OuvidoriaTecnico."""
    ouvidoria_id: int
    tecnico_id: int
    respondido: bool
    respondido_em: datetime | None


class RespostaTecnicaDict(TypedDict):
    id: int
    tecnico_id: int
    tecnico_nome: str
    data_resposta: datetime | None
    texto_resposta: str | None


class RespostaPermissionariaDict(TypedDict):
    id: int
    conteudo: str | None
    data_resposta: date | None
    registrado_por_nome: str
    criado_em: datetime | None


class AnexoDict(TypedDict):
    id: int
    nome_arquivo: str
    nome_storage: str
    tipo_mime: str | None
    tamanho: int | None
    enviado_por_nome: str
    criado_em: datetime | None


class OuvidoriaResumoDict(TypedDict):
    """Ouvidoria na listagem (página 01). Contém atribuições para cálculo de coord/responsáveis."""
    id: int
    protocolo: str | None
    conteudo: str | None
    status: str             # StatusOuvidoria.value
    prazo: date | None
    prazo_permissionaria: date | None
    atribuicoes: list[OuvidoriaTecnicoDict]


class OuvidoriaDetalheDict(TypedDict):
    """Ouvidoria completa para página de detalhe/resposta técnica."""
    id: int
    protocolo: str | None
    conteudo: str | None
    status: str             # StatusOuvidoria.value
    prazo: date | None
    prazo_permissionaria: date | None
    criado_em: datetime | None
    reclamacoes: list[ReclamacaoDict]
    atribuicoes: list[OuvidoriaTecnicoDict]
    respostas_tecnicas: list[RespostaTecnicaDict]
    respostas_permissionaria: list[RespostaPermissionariaDict]
    anexos: list[AnexoDict]


class OuvidoriaPermissionariaDict(TypedDict):
    """Ouvidoria para a página de resposta da permissionária (página 04)."""
    id: int
    conteudo: str | None
    status: str
    prazo: date | None
    prazo_permissionaria: date | None
    respostas_permissionaria: list[RespostaPermissionariaDict]
