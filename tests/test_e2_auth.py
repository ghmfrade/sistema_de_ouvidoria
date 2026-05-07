"""Etapa 2 — testa autenticação JWT.

Usa os usuários de teste criados pelo conftest.py (sem credenciais reais).
"""


def test_login_gestor_valido(client, token_gestor):
    """token_gestor fixture já valida o login; aqui testamos o endpoint diretamente."""
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token_gestor}"})
    assert r.status_code == 200
    data = r.json()
    assert data["tipo"] == "gestor"


def test_login_tecnico_valido(client, token_tecnico):
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token_tecnico}"})
    assert r.status_code == 200
    data = r.json()
    assert data["tipo"] == "tecnico"


def test_login_senha_errada_retorna_401(client):
    r = client.post("/auth/login", json={
        "email": "admin@artesp.sp.gov.br",
        "senha": "senha_totalmente_errada_xyz",
    })
    assert r.status_code == 401


def test_login_email_inexistente_retorna_401(client):
    r = client.post("/auth/login", json={
        "email": "nao_existe@artesp.test",
        "senha": "qualquer",
    })
    assert r.status_code == 401


def test_endpoint_sem_token_retorna_422(client):
    """Header Authorization ausente → FastAPI retorna 422 (campo obrigatório faltando)."""
    r = client.get("/auth/me")
    assert r.status_code == 422


def test_endpoint_token_invalido_retorna_401(client):
    r = client.get("/auth/me", headers={"Authorization": "Bearer token_invalido"})
    assert r.status_code == 401


def test_endpoint_scheme_errado_retorna_401(client):
    r = client.get("/auth/me", headers={"Authorization": "Basic abc123"})
    assert r.status_code == 401


def test_login_via_endpoint_retorna_token(client):
    """Testa o POST /auth/login com credenciais de um usuário real conhecido."""
    r = client.post("/auth/login", json={
        "email": "admin@artesp.sp.gov.br",
        "senha": "admin123",
    })
    assert r.status_code == 200
    data = r.json()
    assert "token" in data
    assert data["tipo"] == "gestor"
    assert data["usuario_id"] > 0
