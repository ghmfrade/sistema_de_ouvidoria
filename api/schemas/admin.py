from pydantic import BaseModel


class CriarUsuarioRequest(BaseModel):
    nome: str
    email: str
    senha: str
    tipo: str
    gerencia_id: int | None = None
    coordenacao_id: int | None = None


class ToggleRequest(BaseModel):
    ativo: bool


class EditarUsuarioRequest(BaseModel):
    nova_senha: str | None = None
    tipo: str


class CriarCategoriaRequest(BaseModel):
    nome: str
    descricao: str | None = None


class CriarSubcategoriaRequest(BaseModel):
    nome: str
    categoria_id: int


class CriarGerenciaRequest(BaseModel):
    nome: str


class CriarCoordenacaoRequest(BaseModel):
    nome: str
    gerencia_id: int | None = None


class EmailExisteResponse(BaseModel):
    existe: bool
