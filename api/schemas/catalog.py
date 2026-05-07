from pydantic import BaseModel


class MunicipioSchema(BaseModel):
    id: int
    nome: str
    estado: str
    cod_ibge: int
    populacao: int

    model_config = {"from_attributes": True}


class CategoriaSchema(BaseModel):
    id: int
    nome: str
    descricao: str | None = None
    ativo: bool

    model_config = {"from_attributes": True}


class SubcategoriaSchema(BaseModel):
    id: int
    nome: str
    categoria_id: int
    categoria_nome: str
    ativo: bool

    model_config = {"from_attributes": True}


class GerenciaSchema(BaseModel):
    id: int
    nome: str
    ativo: bool

    model_config = {"from_attributes": True}


class CoordenacaoSchema(BaseModel):
    id: int
    nome: str
    gerencia_id: int | None = None
    gerencia_nome: str | None = None
    ativo: bool

    model_config = {"from_attributes": True}


class PermissionariaSchema(BaseModel):
    id: int
    nome: str
    nome_fantasia: str | None = None
    cnpj: str | None = None

    model_config = {"from_attributes": True}


class UsuarioSchema(BaseModel):
    id: int
    nome: str
    email: str
    tipo: str
    gerencia_id: int | None = None
    gerencia_nome: str | None = None
    coordenacao_id: int | None = None
    coordenacao_nome: str | None = None
    ativo: bool

    model_config = {"from_attributes": True}
