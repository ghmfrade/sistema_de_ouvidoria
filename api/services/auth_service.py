"""Autenticação JWT.

Replica a lógica de auth.py atual mas retorna dict puro (sem ORM fora da sessão)
e produz/valida tokens JWT.

Variável de ambiente obrigatória: JWT_SECRET_KEY
Opcionais: JWT_EXPIRE_MINUTES (janela de inatividade, padrão 120) e
JWT_MAX_SESSION_HOURS (teto desde o login, padrão 8).

O token é renovado via /auth/refresh enquanto o usuário usa o sistema; o claim
`login_em` guarda o login original para impor o teto mesmo após renovações.
"""
import os
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt, JWTError

from api.database.connection import get_session
from api.models import Usuario

_SECRET = os.environ.get("JWT_SECRET_KEY", "")
_ALGORITHM = "HS256"
_EXPIRE_MINUTES = float(os.environ.get("JWT_EXPIRE_MINUTES", "120"))
_MAX_SESSION_HOURS = float(os.environ.get("JWT_MAX_SESSION_HOURS", "8"))


def _usuario_dict(u: Usuario) -> dict:
    """Converte o ORM em dict puro. Deve ser chamado com a sessão aberta."""
    return {
        "usuario_id": u.id,
        "nome": u.nome,
        "email": u.email,
        "tipo": u.tipo.value,
        "gerencia_id": u.gerencia_id,
        "gerencia_nome": u.gerencia.nome if u.gerencia else None,
        "coordenacao_id": u.coordenacao_id,
        "coordenacao_nome": u.coordenacao.nome if u.coordenacao else None,
    }


def _teto_sessao(login_em: int) -> datetime:
    return datetime.fromtimestamp(login_em, timezone.utc) + timedelta(hours=_MAX_SESSION_HOURS)


def autenticar(email: str, senha: str) -> tuple[dict | None, str | None]:
    """Valida credenciais e retorna (dict com dados do usuário, mensagem de erro) ou (None, mensagem de erro).

    Retorna:
        (dict, None) se autenticado com sucesso
        (None, mensagem de erro) se falhar
    """
    session = get_session()
    try:
        u = session.query(Usuario).filter_by(email=email.strip(), ativo=True).first()
        if u is None:
            return None, "Este e-mail não está cadastrado no sistema."
        if not bcrypt.checkpw(senha.encode(), u.senha_hash.encode()):
            return None, "Senha incorreta. Tente novamente."
        return _usuario_dict(u), None
    finally:
        session.close()


def renovar(payload: dict) -> tuple[dict | None, str | None]:
    """Valida um payload já decodificado antes de emitir um token novo.

    Recarrega o usuário do banco (quem foi desativado perde o acesso) e recusa
    se a sessão passou do teto. Retorna (dict do usuário, None) ou (None, erro).
    """
    login_em = payload.get("login_em")
    if login_em is None or datetime.now(timezone.utc) >= _teto_sessao(login_em):
        return None, "Sessão expirada. Faça login novamente."
    session = get_session()
    try:
        u = session.query(Usuario).filter_by(id=int(payload["sub"]), ativo=True).first()
        if u is None:
            return None, "Usuário inativo ou inexistente."
        return _usuario_dict(u), None
    finally:
        session.close()


def criar_token(usuario: dict, login_em: int | None = None) -> str:
    """Gera JWT a partir do dict retornado por autenticar() ou renovar().

    `login_em` (epoch) é o instante do login original; omitido, vale agora.
    O `exp` nunca ultrapassa login_em + JWT_MAX_SESSION_HOURS.
    """
    if not _SECRET:
        raise RuntimeError("JWT_SECRET_KEY não configurada no ambiente")
    agora = datetime.now(timezone.utc)
    if login_em is None:
        login_em = int(agora.timestamp())
    payload = {
        "sub": str(usuario["usuario_id"]),
        "tipo": usuario["tipo"],
        "login_em": login_em,
        "exp": min(agora + timedelta(minutes=_EXPIRE_MINUTES), _teto_sessao(login_em)),
    }
    return jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)


def decodificar_token(token: str) -> dict:
    """Decodifica e valida JWT. Lança JWTError se inválido ou expirado."""
    if not _SECRET:
        raise RuntimeError("JWT_SECRET_KEY não configurada no ambiente")
    return jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])
