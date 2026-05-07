"""Etapa 6 — paridade entre endpoints de admin e repositórios atuais."""
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
    import uuid
    nome = f"_pytest_ger_{uuid.uuid4().hex[:8]}"
    r = client.post("/admin/gerencias", json={"nome": nome}, headers=headers_gestor)
    assert r.status_code == 200
    gers = get_gerencias()
    nova = next((g for g in gers if g["nome"] == nome), None)
    assert nova is not None
    # Limpeza: desativar
    client.patch(f"/admin/gerencias/{nova['id']}/toggle", json={"ativo": False}, headers=headers_gestor)
