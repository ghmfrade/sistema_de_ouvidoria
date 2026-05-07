"""Dependências injetáveis do FastAPI."""
from fastapi import Depends, HTTPException, Header
from jose import JWTError

from api.services.auth_service import decodificar_token


async def usuario_corrente(authorization: str = Header(...)) -> dict:
    """Extrai e valida o JWT do header Authorization: Bearer <token>."""
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Token ausente ou malformado")
    try:
        return decodificar_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")


async def requer_gestor(payload: dict = Depends(usuario_corrente)) -> dict:
    """Bloqueia acesso se o usuário não for gestor."""
    if payload.get("tipo") != "gestor":
        raise HTTPException(status_code=403, detail="Acesso restrito a gestores")
    return payload
