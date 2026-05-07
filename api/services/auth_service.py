"""Autenticação JWT.

Replica a lógica de auth.py atual mas retorna dict puro (sem ORM fora da sessão)
e produz/valida tokens JWT.

Variável de ambiente obrigatória: JWT_SECRET_KEY
"""
import os
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt, JWTError

from database.connection import get_session
from models import Usuario

_SECRET = os.environ.get("JWT_SECRET_KEY", "")
_ALGORITHM = "HS256"
_EXPIRE_MINUTES = 60


def autenticar(email: str, senha: str) -> dict | None:
    """Valida credenciais e retorna dict com dados do usuário, ou None."""
    session = get_session()
    try:
        u = session.query(Usuario).filter_by(email=email.strip(), ativo=True).first()
        if u is None:
            return None
        if not bcrypt.checkpw(senha.encode(), u.senha_hash.encode()):
            return None
        # Carrega relacionamentos enquanto a sessão está aberta
        gerencia_nome = u.gerencia.nome if u.gerencia else None
        coordenacao_nome = u.coordenacao.nome if u.coordenacao else None
        return {
            "usuario_id": u.id,
            "nome": u.nome,
            "email": u.email,
            "tipo": u.tipo.value,
            "gerencia_id": u.gerencia_id,
            "gerencia_nome": gerencia_nome,
            "coordenacao_id": u.coordenacao_id,
            "coordenacao_nome": coordenacao_nome,
        }
    finally:
        session.close()


def criar_token(usuario: dict) -> str:
    """Gera JWT a partir do dict retornado por autenticar()."""
    if not _SECRET:
        raise RuntimeError("JWT_SECRET_KEY não configurada no ambiente")
    payload = {
        "sub": str(usuario["usuario_id"]),
        "tipo": usuario["tipo"],
        "exp": datetime.now(timezone.utc) + timedelta(minutes=_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)


def decodificar_token(token: str) -> dict:
    """Decodifica e valida JWT. Lança JWTError se inválido ou expirado."""
    if not _SECRET:
        raise RuntimeError("JWT_SECRET_KEY não configurada no ambiente")
    return jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])
