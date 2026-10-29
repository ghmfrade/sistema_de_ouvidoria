"""T01 — gestor remove técnico responsável de uma ouvidoria.

Dados criados são apagados ao final, mesmo em caso de falha.
"""
from datetime import date, timedelta
import pytest
from api.repositories.catalog_repo import get_categorias


def _payload_ouvidoria(cat_id: int) -> dict:
    return {
        "protocolo": "PYTEST-T01",
        "conteudo": "Ouvidoria criada por teste automatizado — pode ser deletada",
        "prazo": (date.today() + timedelta(days=30)).isoformat(),
        "prazo_permissionaria": None,
        "status": "Aguardando ações",
        "criado_por_id": 1,
        "reclamacoes": [{
            "numero_item": 1,
            "categoria_id": cat_id,
            "subcategoria_id": None,
            "tipo_servico": None,
            "local_embarque": None,
            "local_desembarque": None,
            "empresa_fretamento": None,
            "descricao": "Reclamação de teste",
            "autos": [],
        }],
    }


@pytest.fixture(scope="module")
def cat_id():
    cats = get_categorias()
    assert cats, "Banco sem categorias — execute o seed"
    return cats[0]["id"]


@pytest.fixture
def ouvidoria_teste(client, headers_gestor, cat_id):
    r = client.post("/ouvidorias", json=_payload_ouvidoria(cat_id), headers=headers_gestor)
    assert r.status_code == 200, r.text
    oid = r.json()["id"]
    try:
        yield oid
    finally:
        client.delete(f"/ouvidorias/{oid}", headers=headers_gestor)


def _atribuicoes(client, headers, oid):
    r = client.get(f"/ouvidorias/{oid}", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_remover_tecnico_e_repetir(client, headers_gestor, _tecnico_id, ouvidoria_teste):
    oid = ouvidoria_teste
    r = client.post(f"/ouvidorias/{oid}/atribuir-tecnico",
                    json={"tecnico_id": _tecnico_id}, headers=headers_gestor)
    assert r.status_code == 200, r.text
    ids = [a["tecnico_id"] for a in _atribuicoes(client, headers_gestor, oid)["atribuicoes"]]
    assert _tecnico_id in ids

    r = client.delete(f"/ouvidorias/{oid}/tecnicos/{_tecnico_id}", headers=headers_gestor)
    assert r.status_code == 200, r.text
    ids = [a["tecnico_id"] for a in _atribuicoes(client, headers_gestor, oid)["atribuicoes"]]
    assert _tecnico_id not in ids

    r = client.delete(f"/ouvidorias/{oid}/tecnicos/{_tecnico_id}", headers=headers_gestor)
    assert r.status_code == 404


def test_tecnico_nao_pode_remover(client, headers_gestor, headers_tecnico, _tecnico_id, ouvidoria_teste):
    oid = ouvidoria_teste
    client.post(f"/ouvidorias/{oid}/atribuir-tecnico",
                json={"tecnico_id": _tecnico_id}, headers=headers_gestor)
    r = client.delete(f"/ouvidorias/{oid}/tecnicos/{_tecnico_id}", headers=headers_tecnico)
    assert r.status_code == 403


def test_status_volta_para_aguardando_acoes(client, headers_gestor, _tecnico_id, ouvidoria_teste):
    oid = ouvidoria_teste
    client.post(f"/ouvidorias/{oid}/atribuir-tecnico",
                json={"tecnico_id": _tecnico_id}, headers=headers_gestor)
    assert _atribuicoes(client, headers_gestor, oid)["status"] == "Em análise técnica"

    r = client.delete(f"/ouvidorias/{oid}/tecnicos/{_tecnico_id}", headers=headers_gestor)
    assert r.status_code == 200
    assert _atribuicoes(client, headers_gestor, oid)["status"] == "Aguardando ações"
