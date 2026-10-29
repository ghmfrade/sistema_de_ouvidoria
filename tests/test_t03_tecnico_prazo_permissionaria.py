"""T03 — técnico (e gestor) inserem, alteram e apagam o prazo da permissionária."""
from datetime import date, timedelta
import pytest
from api.repositories.catalog_repo import get_categorias


def _payload_ouvidoria(cat_id: int) -> dict:
    return {
        "protocolo": "PYTEST-T03",
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


@pytest.fixture
def ouvidoria_sem_prazo(client, headers_gestor):
    cats = get_categorias()
    assert cats, "Banco sem categorias — execute o seed"
    r = client.post("/ouvidorias", json=_payload_ouvidoria(cats[0]["id"]), headers=headers_gestor)
    assert r.status_code == 200, r.text
    oid = r.json()["id"]
    try:
        yield oid
    finally:
        client.delete(f"/ouvidorias/{oid}", headers=headers_gestor)


def _prazo_atual(client, headers, oid):
    r = client.get(f"/ouvidorias/{oid}", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["prazo_permissionaria"]


def _patch_prazo(client, headers, oid, prazo):
    return client.patch(f"/ouvidorias/{oid}/prazo-permissionaria", json={"prazo": prazo}, headers=headers)


def test_tecnico_insere_altera_e_apaga_prazo(client, headers_tecnico, ouvidoria_sem_prazo):
    oid = ouvidoria_sem_prazo
    assert _prazo_atual(client, headers_tecnico, oid) is None

    d1 = (date.today() + timedelta(days=10)).isoformat()
    assert _patch_prazo(client, headers_tecnico, oid, d1).status_code == 200
    assert _prazo_atual(client, headers_tecnico, oid) == d1

    d2 = (date.today() + timedelta(days=20)).isoformat()
    assert _patch_prazo(client, headers_tecnico, oid, d2).status_code == 200
    assert _prazo_atual(client, headers_tecnico, oid) == d2

    assert _patch_prazo(client, headers_tecnico, oid, None).status_code == 200
    assert _prazo_atual(client, headers_tecnico, oid) is None


def test_tecnico_nao_edita_ouvidoria(client, headers_tecnico, ouvidoria_sem_prazo):
    r = client.patch(f"/ouvidorias/{ouvidoria_sem_prazo}", json={"protocolo": "X"}, headers=headers_tecnico)
    assert r.status_code == 403


def test_gestor_altera_e_apaga_prazo(client, headers_gestor, ouvidoria_sem_prazo):
    oid = ouvidoria_sem_prazo
    d1 = (date.today() + timedelta(days=15)).isoformat()
    assert _patch_prazo(client, headers_gestor, oid, d1).status_code == 200
    assert _prazo_atual(client, headers_gestor, oid) == d1
    assert _patch_prazo(client, headers_gestor, oid, None).status_code == 200
    assert _prazo_atual(client, headers_gestor, oid) is None
