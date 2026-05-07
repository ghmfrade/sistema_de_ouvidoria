from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    senha: str


class TokenResponse(BaseModel):
    token: str
    usuario_id: int
    nome: str
    tipo: str
    gerencia_id: int | None = None
    gerencia_nome: str | None = None
    coordenacao_id: int | None = None
    coordenacao_nome: str | None = None
