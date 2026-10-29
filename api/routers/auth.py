from fastapi import APIRouter, Depends, HTTPException

from api.deps import usuario_corrente
from api.schemas.auth import LoginRequest, TokenResponse

router = APIRouter()


def _token_response(usuario: dict, login_em: int | None = None) -> TokenResponse:
    from api.services.auth_service import criar_token, decodificar_token
    token = criar_token(usuario, login_em)
    return TokenResponse(token=token, expira_em=decodificar_token(token)["exp"], **usuario)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    from api.services.auth_service import autenticar
    usuario, erro = autenticar(body.email, body.senha)
    if not usuario:
        raise HTTPException(status_code=401, detail=erro)
    return _token_response(usuario)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: dict = Depends(usuario_corrente)):
    """Troca um token ainda válido por um novo, mantendo o horário do login original."""
    from api.services.auth_service import renovar
    usuario, erro = renovar(payload)
    if not usuario:
        raise HTTPException(status_code=401, detail=erro)
    return _token_response(usuario, payload["login_em"])


@router.get("/me")
def me(payload: dict = Depends(usuario_corrente)):
    """Retorna dados do usuário logado a partir do token JWT."""
    return payload
