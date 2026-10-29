from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    senha: str


class TokenResponse(BaseModel):
    token: str
    expira_em: int  # epoch do `exp` do token, para o frontend saber quando renovar
    usuario_id: int
    nome: str
    tipo: str
    gerencia_id: int | None = None
    gerencia_nome: str | None = None
    coordenacao_id: int | None = None
    coordenacao_nome: str | None = None
