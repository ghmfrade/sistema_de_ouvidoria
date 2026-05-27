"""Etapa 6 — paridade entre endpoints de admin e repositórios atuais."""
import uuid
import pytest
from repositories.catalog_repo import get_usuarios, get_categorias, get_gerencias, get_coordenacoes


def test_paridade_usuarios(client, headers_gestor):
    esperado = get_usuarios()
    r = client.get("/admin/usuarios", headers=headers_gestor)
    assert r.status_code == 200
    ids_esperados = {u["id"] for u in esperado}
    ids_obtidos   = {u["id"] for u in r.json()}
    # Os usuários de teste do conftest aparecem — verificamos que todos os reais estão presentes
    assert ids_esperados.issubset(ids_obtidos)


def test_tecnico_nao_acessa_admin(client, headers_tecnico):
    r = client.get("/admin/usuarios", headers=headers_tecnico)
    assert r.status_code == 403


def test_email_existe_real(client, headers_gestor):
    r = client.get("/admin/usuarios/email-existe", headers=headers_gestor,
                   params={"email": "admin@artesp.sp.gov.br"})
    assert r.status_code == 200
    assert r.json() is True


def test_email_nao_existe(client, headers_gestor):
    r = client.get("/admin/usuarios/email-existe", headers=headers_gestor,
                   params={"email": "ninguem@artesp.test.xyz"})
    assert r.status_code == 200
    assert r.json() is False


def test_paridade_categorias(client, headers_gestor):
    esperado = get_categorias()
    r = client.get("/admin/categorias", headers=headers_gestor)
    assert r.status_code == 200
    assert {c["id"] for c in esperado} == {c["id"] for c in r.json()}


def test_paridade_gerencias(client, headers_gestor):
    esperado = get_gerencias()
    r = client.get("/admin/gerencias", headers=headers_gestor)
    assert r.status_code == 200
    assert {g["id"] for g in esperado} == {g["id"] for g in r.json()}


def test_paridade_coordenacoes(client, headers_gestor):
    esperado = get_coordenacoes()
    r = client.get("/admin/coordenacoes", headers=headers_gestor)
    assert r.status_code == 200
    assert {c["id"] for c in esperado} == {c["id"] for c in r.json()}


def test_criar_e_toggle_categoria(client, headers_gestor):
    """Cria categoria de teste com nome único, faz toggle inativo e restaura."""
    import uuid
    nome = f"_pytest_cat_{uuid.uuid4().hex[:8]}"
    r = client.post("/admin/categorias", json={"nome": nome}, headers=headers_gestor)
    assert r.status_code == 200

    cats = get_categorias()
    nova = next((c for c in cats if c["nome"] == nome), None)
    assert nova is not None
    cat_id = nova["id"]

    r2 = client.patch(f"/admin/categorias/{cat_id}/toggle",
                      json={"ativo": False}, headers=headers_gestor)
    assert r2.status_code == 200

    cats_depois = get_categorias()
    inativa = next((c for c in cats_depois if c["id"] == cat_id), None)
    assert inativa is not None
    assert inativa["ativo"] is False

    # Restaurar para não poluir o banco
    client.patch(f"/admin/categorias/{cat_id}/toggle", json={"ativo": True}, headers=headers_gestor)


def test_criar_gerencia(client, headers_gestor):
    nome = f"_pytest_ger_{uuid.uuid4().hex[:8]}"
    r = client.post("/admin/gerencias", json={"nome": nome}, headers=headers_gestor)
    assert r.status_code == 200
    gers = get_gerencias()
    nova = next((g for g in gers if g["nome"] == nome), None)
    assert nova is not None
    # Limpeza: desativar
    client.patch(f"/admin/gerencias/{nova['id']}/toggle", json={"ativo": False}, headers=headers_gestor)


# ── Criação de usuários: regras de e-mail duplicado ───────────────────────────

def _payload_usuario(email: str) -> dict:
    """Payload mínimo para criar usuário de teste via API."""
    return {
        "nome": "Pytest Usuário",
        "email": email,
        "senha": "TestSenha@2025",
        "tipo": "tecnico",
        "gerencia_id": None,
        "coordenacao_id": None,
    }


def _buscar_id_por_email(email: str) -> int | None:
    """Retorna o id do usuário com o e-mail informado, ou None."""
    from database.connection import db_session
    from models import Usuario
    with db_session() as s:
        u = s.query(Usuario).filter(Usuario.email == email).first()
        return u.id if u else None


def test_criar_usuario_email_novo(client, headers_gestor):
    """Cria usuário com e-mail inédito — deve retornar 200."""
    email = f"_pytest_novo_{uuid.uuid4().hex[:8]}@artesp.test"
    r = client.post("/admin/usuarios", json=_payload_usuario(email), headers=headers_gestor)
    assert r.status_code == 200, r.text
    # Limpeza: remove via banco (o conftest também apaga ao final da sessão)
    from database.connection import db_session
    from models import Usuario
    from sqlalchemy import text
    with db_session() as s:
        s.execute(text("DELETE FROM usuarios WHERE email = :e"), {"e": email})


def test_criar_usuario_email_ativo_retorna_409(client, headers_gestor):
    """Tenta criar usuário com e-mail de usuário ATIVO — deve retornar 409."""
    email = f"_pytest_dup_{uuid.uuid4().hex[:8]}@artesp.test"
    # Cria o usuário inicial
    r1 = client.post("/admin/usuarios", json=_payload_usuario(email), headers=headers_gestor)
    assert r1.status_code == 200, f"Falha ao criar usuário inicial: {r1.text}"

    # Tenta criar novamente com mesmo e-mail (usuário ainda ativo) → 409
    r2 = client.post("/admin/usuarios", json=_payload_usuario(email), headers=headers_gestor)
    assert r2.status_code == 409, f"Esperado 409, obtido {r2.status_code}: {r2.text}"
    assert "ativo" in r2.json()["detail"].lower()

    # Limpeza
    from database.connection import db_session
    from sqlalchemy import text
    with db_session() as s:
        s.execute(text("DELETE FROM usuarios WHERE email = :e"), {"e": email})


def test_criar_usuario_email_inativo_permitido(client, headers_gestor):
    """Cria usuário com e-mail de usuário INATIVO — deve ser permitido (200)."""
    email = f"_pytest_inativo_{uuid.uuid4().hex[:8]}@artesp.test"

    # Cria o usuário e o inativa
    r1 = client.post("/admin/usuarios", json=_payload_usuario(email), headers=headers_gestor)
    assert r1.status_code == 200, f"Falha ao criar usuário inicial: {r1.text}"
    uid = _buscar_id_por_email(email)
    assert uid is not None
    r_toggle = client.patch(f"/admin/usuarios/{uid}/toggle", json={"ativo": False}, headers=headers_gestor)
    assert r_toggle.status_code == 200

    # Agora cria novo usuário com o mesmo e-mail → deve funcionar
    r2 = client.post("/admin/usuarios", json=_payload_usuario(email), headers=headers_gestor)
    assert r2.status_code == 200, (
        f"Deveria permitir criar com e-mail de inativo, obtido {r2.status_code}: {r2.text}"
    )

    # Limpeza: remove ambos os usuários com este e-mail
    from database.connection import db_session
    from sqlalchemy import text
    with db_session() as s:
        s.execute(text("DELETE FROM usuarios WHERE email = :e"), {"e": email})


def test_reativar_usuario_email_conflito_retorna_409(client, headers_gestor):
    """Tenta reativar usuário cujo e-mail já está em uso por outro ativo — deve retornar 409."""
    email = f"_pytest_reativ_{uuid.uuid4().hex[:8]}@artesp.test"

    # Cria usuário A e o inativa
    r1 = client.post("/admin/usuarios", json=_payload_usuario(email), headers=headers_gestor)
    assert r1.status_code == 200
    uid_a = _buscar_id_por_email(email)
    assert uid_a is not None
    client.patch(f"/admin/usuarios/{uid_a}/toggle", json={"ativo": False}, headers=headers_gestor)

    # Cria usuário B com o mesmo e-mail (agora liberado)
    r2 = client.post("/admin/usuarios", json=_payload_usuario(email), headers=headers_gestor)
    assert r2.status_code == 200, f"Deveria criar B com e-mail de inativo: {r2.text}"

    # Tenta reativar A (e-mail já em uso por B ativo) → 409
    r_reativ = client.patch(f"/admin/usuarios/{uid_a}/toggle", json={"ativo": True}, headers=headers_gestor)
    assert r_reativ.status_code == 409, (
        f"Esperado 409 ao reativar com e-mail em conflito, obtido {r_reativ.status_code}: {r_reativ.text}"
    )

    # Limpeza
    from database.connection import db_session
    from sqlalchemy import text
    with db_session() as s:
        s.execute(text("DELETE FROM usuarios WHERE email = :e"), {"e": email})
