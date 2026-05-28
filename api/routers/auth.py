from fastapi import APIRouter, Depends, HTTPException

from api.deps import usuario_corrente
from api.schemas.auth import LoginRequest, TokenResponse

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    from api.services.auth_service import autenticar, criar_token
    usuario, erro = autenticar(body.email, body.senha)
    if not usuario:
        raise HTTPException(status_code=401, detail=erro)
    return TokenResponse(token=criar_token(usuario), **usuario)


@router.get("/me")
def me(payload: dict = Depends(usuario_corrente)):
    """Retorna dados do usuário logado a partir do token JWT."""
    return payload
