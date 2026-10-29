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
        "senha": "troquei",
    })
    assert r.status_code == 200
    data = r.json()
    assert "token" in data
    assert data["tipo"] == "gestor"
    assert data["usuario_id"] > 0


# ── Renovação de token (/auth/refresh) ────────────────────────────────────────

def test_login_retorna_expira_em(client):
    r = client.post("/auth/login", json={
        "email": "admin@artesp.sp.gov.br",
        "senha": "troquei",
    })
    assert r.status_code == 200
    data = r.json()
    from api.services.auth_service import decodificar_token
    assert data["expira_em"] == decodificar_token(data["token"])["exp"]


def test_refresh_renova_mantendo_login_em(client, _usuarios_teste):
    import time
    from api.services.auth_service import criar_token, decodificar_token
    login_em = int(time.time()) - 600
    usuario = {"usuario_id": _usuarios_teste["gestor_id"], "tipo": "gestor"}
    antigo = decodificar_token(criar_token(usuario, login_em))

    r = client.post("/auth/refresh", headers={"Authorization": f"Bearer {criar_token(usuario, login_em)}"})
    assert r.status_code == 200
    data = r.json()
    novo = decodificar_token(data["token"])
    assert novo["login_em"] == login_em
    assert novo["exp"] >= antigo["exp"]
    assert data["usuario_id"] == _usuarios_teste["gestor_id"]
    assert data["expira_em"] == novo["exp"]


def test_refresh_token_invalido_retorna_401(client):
    r = client.post("/auth/refresh", headers={"Authorization": "Bearer token_invalido"})
    assert r.status_code == 401


def test_refresh_sem_token_retorna_422(client):
    r = client.post("/auth/refresh")
    assert r.status_code == 422


def test_exp_nunca_passa_do_teto(_usuarios_teste):
    import time
    from api.services import auth_service
    login_em = int(time.time()) - int(auth_service._MAX_SESSION_HOURS * 3600) + 60
    usuario = {"usuario_id": _usuarios_teste["gestor_id"], "tipo": "gestor"}
    payload = auth_service.decodificar_token(auth_service.criar_token(usuario, login_em))
    assert payload["exp"] <= login_em + auth_service._MAX_SESSION_HOURS * 3600


def test_refresh_apos_teto_recusa(_usuarios_teste):
    """Token ainda assinado, mas login há mais que o teto: renovar() recusa."""
    import time
    from api.services import auth_service
    login_em = int(time.time()) - int(auth_service._MAX_SESSION_HOURS * 3600) - 60
    payload = {"sub": str(_usuarios_teste["gestor_id"]), "tipo": "gestor", "login_em": login_em}
    usuario, erro = auth_service.renovar(payload)
    assert usuario is None
    assert erro
