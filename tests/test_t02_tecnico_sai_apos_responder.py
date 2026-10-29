"""T02 — ouvidoria sai da tela do técnico depois que ele responde; gestor pode devolver.

Dados criados são apagados ao final, mesmo em caso de falha.
"""
from datetime import date, timedelta
import pytest
from api.repositories.catalog_repo import get_categorias


def _payload_ouvidoria(cat_id: int) -> dict:
    return {
        "protocolo": "PYTEST-T02",
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


def _detalhe(client, headers, oid):
    r = client.get(f"/ouvidorias/{oid}", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def _atribuicao(client, headers, oid, tecnico_id):
    return next(a for a in _detalhe(client, headers, oid)["atribuicoes"]
                if a["tecnico_id"] == tecnico_id)


def _ids_listagem_tecnico(client, headers, tecnico_id) -> set[int]:
    r = client.get("/ouvidorias", params={
        "usuario_id": tecnico_id,
        "usuario_tipo": "tecnico",
        "filtrar_apenas_atribuidas": "true",
        "ocultar_concluidos": "true",
    }, headers=headers)
    assert r.status_code == 200, r.text
    return {o["id"] for o in r.json()}


def _atribuir(client, headers, oid, tecnico_id):
    return client.post(f"/ouvidorias/{oid}/atribuir-tecnico",
                       json={"tecnico_id": tecnico_id}, headers=headers)


def _responder(client, headers, oid, tecnico_id, texto="Resposta de teste"):
    r = client.post(f"/ouvidorias/{oid}/respostas-tecnicas",
                    json={"tecnico_id": tecnico_id, "texto": texto}, headers=headers)
    assert r.status_code == 200, r.text


def test_fluxo_responder_devolver_e_responder_de_novo(
    client, headers_gestor, headers_tecnico, _tecnico_id, ouvidoria_teste
):
    oid = ouvidoria_teste
    assert _atribuir(client, headers_gestor, oid, _tecnico_id).status_code == 200
    assert oid in _ids_listagem_tecnico(client, headers_tecnico, _tecnico_id)

    _responder(client, headers_tecnico, oid, _tecnico_id, "Primeira")
    assert oid not in _ids_listagem_tecnico(client, headers_tecnico, _tecnico_id)
    det = _detalhe(client, headers_gestor, oid)
    assert _atribuicao(client, headers_gestor, oid, _tecnico_id)["respondido"] is True
    assert len(det["respostas_tecnicas"]) == 1

    r = client.post(f"/ouvidorias/{oid}/tecnicos/{_tecnico_id}/devolver", headers=headers_gestor)
    assert r.status_code == 200, r.text
    assert _detalhe(client, headers_gestor, oid)["status"] == "Em análise técnica"
    assert _atribuicao(client, headers_gestor, oid, _tecnico_id)["respondido"] is False
    assert oid in _ids_listagem_tecnico(client, headers_tecnico, _tecnico_id)

    _responder(client, headers_tecnico, oid, _tecnico_id, "Segunda")
    assert oid not in _ids_listagem_tecnico(client, headers_tecnico, _tecnico_id)
    assert len(_detalhe(client, headers_gestor, oid)["respostas_tecnicas"]) == 2


def test_status_em_analise_reabre_respondidos(client, headers_gestor, _tecnico_id, ouvidoria_teste):
    oid = ouvidoria_teste
    _atribuir(client, headers_gestor, oid, _tecnico_id)
    _responder(client, headers_gestor, oid, _tecnico_id)
    assert _atribuicao(client, headers_gestor, oid, _tecnico_id)["respondido"] is True
    assert _detalhe(client, headers_gestor, oid)["status"] == "Retorno técnico"

    r = client.patch(f"/ouvidorias/{oid}", json={"status": "Em análise técnica"},
                     headers=headers_gestor)
    assert r.status_code == 200, r.text
    assert _atribuicao(client, headers_gestor, oid, _tecnico_id)["respondido"] is False


def test_atribuir_pendente_409_e_respondido_reabre(client, headers_gestor, _tecnico_id, ouvidoria_teste):
    oid = ouvidoria_teste
    assert _atribuir(client, headers_gestor, oid, _tecnico_id).status_code == 200
    assert _atribuir(client, headers_gestor, oid, _tecnico_id).status_code == 409

    _responder(client, headers_gestor, oid, _tecnico_id)
    assert _atribuir(client, headers_gestor, oid, _tecnico_id).status_code == 200
    assert _atribuicao(client, headers_gestor, oid, _tecnico_id)["respondido"] is False
    assert _detalhe(client, headers_gestor, oid)["status"] == "Em análise técnica"


def test_devolver_nao_atribuido_404_e_tecnico_403(
    client, headers_gestor, headers_tecnico, _tecnico_id, ouvidoria_teste
):
    oid = ouvidoria_teste
    r = client.post(f"/ouvidorias/{oid}/tecnicos/{_tecnico_id}/devolver", headers=headers_gestor)
    assert r.status_code == 404

    _atribuir(client, headers_gestor, oid, _tecnico_id)
    r = client.post(f"/ouvidorias/{oid}/tecnicos/{_tecnico_id}/devolver", headers=headers_tecnico)
    assert r.status_code == 403


def test_devolver_ouvidoria_concluida_409(client, headers_gestor, _tecnico_id, ouvidoria_teste):
    oid = ouvidoria_teste
    _atribuir(client, headers_gestor, oid, _tecnico_id)
    _responder(client, headers_gestor, oid, _tecnico_id)
    r = client.post(f"/ouvidorias/{oid}/concluir", headers=headers_gestor)
    assert r.status_code == 200, r.text

    r = client.post(f"/ouvidorias/{oid}/tecnicos/{_tecnico_id}/devolver", headers=headers_gestor)
    assert r.status_code == 409
