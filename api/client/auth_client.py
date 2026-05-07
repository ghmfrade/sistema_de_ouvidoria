"""Client de autenticação — não usa token (é quem gera o token)."""
from api.client.base import post_public


def login(email: str, senha: str) -> dict:
    """Autentica e retorna dict com token + dados do usuário.

    Retorna: {"token", "usuario_id", "nome", "tipo", "gerencia_id",
              "gerencia_nome", "coordenacao_id", "coordenacao_nome"}
    """
    return post_public("/auth/login", json={"email": email, "senha": senha})
