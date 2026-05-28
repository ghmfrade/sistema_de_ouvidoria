from __future__ import annotations

from datetime import date, datetime
from pydantic import BaseModel


class AutoSchema(BaseModel):
    id: int
    numero: str
    denominacao_a: str | None = None
    denominacao_b: str | None = None
    permissionaria_id: int | None = None
    permissionaria_nome: str
    tipo: str
    regiao_metropolitana: str | None = None
    sub_regiao: str | None = None
    tc: int | None = None
    ativo: bool

    model_config = {"from_attributes": True}


class ReclamacaoAutoSchema(BaseModel):
    auto_id: int
    numero: str
    denominacao_a: str | None = None
    denominacao_b: str | None = None
    permissionaria_nome: str
    tipo: str | None = None
    regiao_metropolitana: str | None = None
    tc: int | None = None
    pontuacao: float | None = None

    model_config = {"from_attributes": True}


class ReclamacaoSchema(BaseModel):
    id: int
    numero_item: int
    categoria_id: int | None = None
    categoria_nome: str | None = None
    subcategoria_id: int | None = None
    subcategoria_nome: str | None = None
    tipo_servico: str | None = None
    local_embarque: str | None = None
    local_desembarque: str | None = None
    empresa_fretamento: str | None = None
    descricao: str | None = None
    autos: list[ReclamacaoAutoSchema] = []

    model_config = {"from_attributes": True}


class AtribuicaoTecnicoSchema(BaseModel):
    tecnico_id: int
    tecnico_nome: str
    gerencia_nome: str | None = None
    coordenacao_nome: str | None = None
    respondido: bool
    respondido_em: datetime | None = None

    model_config = {"from_attributes": True}


class AtribuicaoScalarSchema(BaseModel):
    ouvidoria_id: int
    tecnico_id: int
    respondido: bool
    respondido_em: datetime | None = None

    model_config = {"from_attributes": True}


class RespostaTecnicaSchema(BaseModel):
    id: int
    tecnico_id: int
    tecnico_nome: str
    data_resposta: datetime | None = None
    texto_resposta: str | None = None

    model_config = {"from_attributes": True}


class RespostaPermissionariaSchema(BaseModel):
    id: int
    conteudo: str | None = None
    data_resposta: date | None = None
    registrado_por_nome: str
    criado_em: datetime | None = None

    model_config = {"from_attributes": True}


class AnexoSchema(BaseModel):
    id: int
    nome_arquivo: str
    nome_storage: str
    tipo_mime: str | None = None
    tamanho: int | None = None
    enviado_por_nome: str
    criado_em: datetime | None = None

    model_config = {"from_attributes": True}


class OuvidoriaResumoSchema(BaseModel):
    id: int
    protocolo: str | None = None
    conteudo: str | None = None
    status: str
    prazo: date | None = None
    prazo_permissionaria: date | None = None
    data_resposta_perm: date | None = None
    criado_em: datetime | None = None
    concluido_em: datetime | None = None
    atribuicoes: list[AtribuicaoTecnicoSchema] = []

    model_config = {"from_attributes": True}


class OuvidoriaDetalheSchema(BaseModel):
    id: int
    protocolo: str | None = None
    conteudo: str | None = None
    status: str
    prazo: date | None = None
    prazo_permissionaria: date | None = None
    criado_em: datetime | None = None
    concluido_em: datetime | None = None
    reclamacoes: list[ReclamacaoSchema] = []
    atribuicoes: list[AtribuicaoTecnicoSchema] = []
    respostas_tecnicas: list[RespostaTecnicaSchema] = []
    respostas_permissionaria: list[RespostaPermissionariaSchema] = []
    anexos: list[AnexoSchema] = []

    model_config = {"from_attributes": True}


class OuvidoriaPermissionariaSchema(BaseModel):
    id: int
    conteudo: str | None = None
    status: str
    prazo: date | None = None
    prazo_permissionaria: date | None = None
    respostas_permissionaria: list[RespostaPermissionariaSchema] = []

    model_config = {"from_attributes": True}


# ── Request bodies ────────────────────────────────────────────────────────────

class ReclamacaoDraftAuto(BaseModel):
    id: int


class ReclamacaoDraft(BaseModel):
    id: int | None = None  # presente em recs_edit (edição), ausente em recs_draft (criação)
    numero_item: int
    categoria_id: int | None = None
    subcategoria_id: int | None = None
    tipo_servico: str | None = None
    local_embarque: str | None = None
    local_desembarque: str | None = None
    empresa_fretamento: str | None = None
    descricao: str | None = None
    autos: list[ReclamacaoDraftAuto] = []


class CriarOuvidoriaRequest(BaseModel):
    protocolo: str | None = None
    conteudo: str | None = None
    prazo: date | None = None
    prazo_permissionaria: date | None = None
    status: str
    criado_por_id: int
    reclamacoes: list[ReclamacaoDraft] = []


class EditarOuvidoriaRequest(BaseModel):
    protocolo: str | None = None
    conteudo: str | None = None
    prazo: date | None = None
    prazo_permissionaria: date | None = None
    status: str | None = None


class AtribuirTecnicoRequest(BaseModel):
    tecnico_id: int


class AtualizarPrazoPermissionariaRequest(BaseModel):
    prazo: date | None = None


class AtualizarReclamacoesRequest(BaseModel):
    recs_edit: list[ReclamacaoDraft] = []


class RegistrarRespostaTecnicaRequest(BaseModel):
    tecnico_id: int
    texto: str


class RegistrarRespostaPermissionariaRequest(BaseModel):
    conteudo: str
    data_resposta: date
    registrado_por_id: int


# ── Response simples ──────────────────────────────────────────────────────────

class OuvidoriaIdResponse(BaseModel):
    id: int


class RespostaTecnicaConcluidaResponse(BaseModel):
    todos_responderam: bool
