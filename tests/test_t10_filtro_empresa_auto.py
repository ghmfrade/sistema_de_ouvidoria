"""T10 — filtros por Empresa (permissionária) e Auto de linha na lista de ouvidorias.

Dados criados são apagados ao final, mesmo em caso de falha.
"""
from datetime import date, timedelta
import pytest
from api.database.connection import db_session
from api.models import AutoLinha
from api.repositories.catalog_repo import get_categorias
from api.repositories.ouvidoria_repo import get_ouvidorias


def _payload(cat_id: int, protocolo: str, auto_ids: list[int]) -> dict:
    return {
        "protocolo": protocolo,
        "conteudo": "Ouvidoria criada por teste automatizado — pode ser deletada",
        "prazo": (date.today() + timedelta(days=30)).isoformat(),
        "prazo_permissionaria": None,
        "status": "Aguardando ações",
        "criado_por_id": 1,
        "reclamacoes": [{
            "numero_item": 1, "categoria_id": cat_id, "subcategoria_id": None,
            "tipo_servico": None, "local_embarque": None, "local_desembarque": None,
            "empresa_fretamento": None, "descricao": "Reclamação de teste",
            "autos": [{"id": i} for i in auto_ids],
        }],
    }


@pytest.fixture(scope="module")
def cat_id():
    cats = get_categorias()
    assert cats, "Banco sem categorias — execute o seed"
    return cats[0]["id"]


@pytest.fixture(scope="module")
def autos_duas_empresas():
    """(auto_a, auto_b) de permissionárias diferentes: [(auto_id, permissionaria_id)]."""
    with db_session() as s:
        vistos: dict[int, int] = {}
        for a in s.query(AutoLinha).filter(
            AutoLinha.ativo.is_(True), AutoLinha.permissionaria_id.isnot(None)
        ).order_by(AutoLinha.id).all():
            vistos.setdefault(a.permissionaria_id, a.id)
            if len(vistos) == 2:
                break
    if len(vistos) < 2:
        pytest.skip("Banco sem autos de duas permissionárias distintas")
    (perm_a, auto_a), (perm_b, auto_b) = list(vistos.items())
    return (auto_a, perm_a), (auto_b, perm_b)


@pytest.fixture
def criar(client, headers_gestor, cat_id):
    """Cria ouvidorias de teste e apaga todas ao final."""
    ids: list[int] = []

    def _criar(protocolo: str, auto_ids: list[int]) -> int:
        r = client.post("/ouvidorias", json=_payload(cat_id, protocolo, auto_ids), headers=headers_gestor)
        assert r.status_code == 200, r.text
        ids.append(r.json()["id"])
        return ids[-1]

    try:
        yield _criar
    finally:
        for oid in ids:
            client.delete(f"/ouvidorias/{oid}", headers=headers_gestor)


def _ids(**filtros) -> set[int]:
    return {o["id"] for o in get_ouvidorias(ocultar_concluidos=False, **filtros)}


def test_filtro_por_empresa(criar, autos_duas_empresas):
    (auto_a, perm_a), (auto_b, perm_b) = autos_duas_empresas
    oid_a = criar("PYTEST-T10-A", [auto_a])
    oid_b = criar("PYTEST-T10-B", [auto_b])
    por_a = _ids(filtro_permissionaria_id=perm_a)
    por_b = _ids(filtro_permissionaria_id=perm_b)
    assert oid_a in por_a and oid_b not in por_a
    assert oid_b in por_b and oid_a not in por_b


def test_filtro_por_auto(criar, autos_duas_empresas):
    (auto_a, _), (auto_b, _) = autos_duas_empresas
    oid_a = criar("PYTEST-T10-A", [auto_a])
    oid_b = criar("PYTEST-T10-B", [auto_b])
    por_auto_a = _ids(filtro_auto_id=auto_a)
    assert oid_a in por_auto_a and oid_b not in por_auto_a


def test_empresa_e_auto_combinados(criar, autos_duas_empresas):
    (auto_a, perm_a), (auto_b, perm_b) = autos_duas_empresas
    oid_a = criar("PYTEST-T10-A", [auto_a])
    oid_b = criar("PYTEST-T10-B", [auto_b])
    assert oid_a in _ids(filtro_permissionaria_id=perm_a, filtro_auto_id=auto_a)
    # empresa de um, auto do outro → AND não casa com nenhuma das duas
    cruzado = _ids(filtro_permissionaria_id=perm_a, filtro_auto_id=auto_b)
    assert oid_a not in cruzado and oid_b not in cruzado


def test_sem_filtros_inclui_ouvidoria_sem_auto(criar, autos_duas_empresas):
    (auto_a, perm_a), _ = autos_duas_empresas
    oid_sem = criar("PYTEST-T10-SEM", [])
    oid_a = criar("PYTEST-T10-A", [auto_a])
    todas = _ids()
    assert oid_sem in todas and oid_a in todas
    assert oid_sem not in _ids(filtro_permissionaria_id=perm_a)
    assert oid_sem not in _ids(filtro_auto_id=auto_a)
