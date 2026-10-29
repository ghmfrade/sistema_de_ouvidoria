"""T06 — marcação por cores (por login) e legenda.

Dados criados são apagados ao final, mesmo em caso de falha.
"""
from datetime import date, timedelta
import pytest
from sqlalchemy import text
from api.repositories.catalog_repo import get_categorias


def _payload_ouvidoria(cat_id: int) -> dict:
    return {
        "protocolo": "PYTEST-T06",
        "conteudo": "Ouvidoria criada por teste automatizado — pode ser deletada",
        "prazo": (date.today() + timedelta(days=30)).isoformat(),
        "prazo_permissionaria": None,
        "status": "Aguardando ações",
        "criado_por_id": 1,
        "reclamacoes": [{
            "numero_item": 1, "categoria_id": cat_id, "subcategoria_id": None,
            "tipo_servico": None, "local_embarque": None, "local_desembarque": None,
            "empresa_fretamento": None, "descricao": "Reclamação de teste", "autos": [],
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


@pytest.fixture(autouse=True)
def _limpar_legendas(_usuarios_teste):
    yield
    from api.database.connection import db_session
    with db_session() as s:
        s.execute(text("DELETE FROM marcador_legendas WHERE usuario_id IN (:g, :t)"),
                  {"g": _usuarios_teste["gestor_id"], "t": _usuarios_teste["tecnico_id"]})


def _marcacao(client, headers, oid, tecnico_id=None, fila=False):
    """(linha, marcacao) vistos na lista. fila=True lê como a fila do técnico; senão lê tudo."""
    params = {"ocultar_concluidos": "false", "filtrar_apenas_atribuidas": "false"}
    if fila:
        params = {"usuario_id": tecnico_id, "usuario_tipo": "tecnico",
                  "filtrar_apenas_atribuidas": "true", "ocultar_concluidos": "true"}
    r = client.get("/ouvidorias", params=params, headers=headers)
    assert r.status_code == 200, r.text
    linha = next((o for o in r.json() if o["id"] == oid), None)
    return linha, (linha["marcacao"] if linha else None)


def _marcar(client, headers, oid, cor):
    return client.put(f"/ouvidorias/{oid}/marcacao", json={"cor": cor}, headers=headers)


def test_marca_e_troca_cor(client, headers_tecnico, ouvidoria_teste):
    oid = ouvidoria_teste
    assert _marcar(client, headers_tecnico, oid, "vermelho").status_code == 200
    assert _marcacao(client, headers_tecnico, oid)[1] == "vermelho"
    assert _marcar(client, headers_tecnico, oid, "verde").status_code == 200
    assert _marcacao(client, headers_tecnico, oid)[1] == "verde"


def test_isolamento_entre_logins(client, headers_gestor, headers_tecnico, ouvidoria_teste):
    oid = ouvidoria_teste
    _marcar(client, headers_tecnico, oid, "verde")
    assert _marcacao(client, headers_gestor, oid)[1] is None
    assert _marcar(client, headers_gestor, oid, "azul").status_code == 200
    assert _marcacao(client, headers_tecnico, oid)[1] == "verde"
    assert _marcacao(client, headers_gestor, oid)[1] == "azul"


def test_persistencia_no_fluxo(client, headers_gestor, headers_tecnico, _tecnico_id, ouvidoria_teste):
    oid = ouvidoria_teste
    _marcar(client, headers_tecnico, oid, "roxo")

    def conferir(fila):
        linha, cor = _marcacao(client, headers_tecnico, oid, _tecnico_id, fila=fila)
        assert cor == "roxo"
        return linha

    r = client.post(f"/ouvidorias/{oid}/atribuir-tecnico",
                    json={"tecnico_id": _tecnico_id}, headers=headers_gestor)
    assert r.status_code == 200, r.text
    assert conferir(fila=True) is not None

    r = client.post(f"/ouvidorias/{oid}/respostas-tecnicas",
                    json={"tecnico_id": _tecnico_id, "texto": "Resposta"}, headers=headers_tecnico)
    assert r.status_code == 200, r.text
    assert _marcacao(client, headers_tecnico, oid, _tecnico_id, fila=True)[0] is None
    conferir(fila=False)

    r = client.post(f"/ouvidorias/{oid}/tecnicos/{_tecnico_id}/devolver", headers=headers_gestor)
    assert r.status_code == 200, r.text
    assert conferir(fila=True) is not None

    r = client.delete(f"/ouvidorias/{oid}/tecnicos/{_tecnico_id}", headers=headers_gestor)
    assert r.status_code == 200, r.text
    conferir(fila=False)

    r = client.post(f"/ouvidorias/{oid}/atribuir-tecnico",
                    json={"tecnico_id": _tecnico_id}, headers=headers_gestor)
    assert r.status_code == 200, r.text
    assert conferir(fila=True) is not None

    r = client.post(f"/ouvidorias/{oid}/concluir", headers=headers_gestor)
    assert r.status_code == 200, r.text
    conferir(fila=False)


def test_remover_marcacao_idempotente(client, headers_tecnico, ouvidoria_teste):
    oid = ouvidoria_teste
    _marcar(client, headers_tecnico, oid, "azul")
    assert client.delete(f"/ouvidorias/{oid}/marcacao", headers=headers_tecnico).status_code == 200
    assert _marcacao(client, headers_tecnico, oid)[1] is None
    assert client.delete(f"/ouvidorias/{oid}/marcacao", headers=headers_tecnico).status_code == 200


def test_cor_invalida_e_ouvidoria_inexistente(client, headers_tecnico, ouvidoria_teste):
    assert _marcar(client, headers_tecnico, ouvidoria_teste, "rosa").status_code == 422
    assert _marcar(client, headers_tecnico, 999999999, "verde").status_code == 404


def _legenda(client, headers) -> dict[str, str]:
    r = client.get("/marcacoes/legenda", headers=headers)
    assert r.status_code == 200, r.text
    return {i["cor"]: i["rotulo"] for i in r.json()}


def test_legenda(client, headers_gestor, headers_tecnico):
    cores = ["vermelho", "laranja", "amarelo", "verde", "azul", "roxo", "marrom"]
    inicial = _legenda(client, headers_tecnico)
    assert list(inicial) == cores
    assert all(v == "" for v in inicial.values())

    r = client.put("/marcacoes/legenda", headers=headers_tecnico, json={"itens": [
        {"cor": "vermelho", "rotulo": "Ana"}, {"cor": "verde", "rotulo": "  João "}]})
    assert r.status_code == 200, r.text
    leg = _legenda(client, headers_tecnico)
    assert leg["vermelho"] == "Ana" and leg["verde"] == "João"

    assert all(v == "" for v in _legenda(client, headers_gestor).values())

    client.put("/marcacoes/legenda", headers=headers_tecnico,
               json={"itens": [{"cor": "vermelho", "rotulo": ""}]})
    leg = _legenda(client, headers_tecnico)
    assert leg["vermelho"] == "" and leg["verde"] == "João"

    r = client.put("/marcacoes/legenda", headers=headers_tecnico,
                   json={"itens": [{"cor": "azul", "rotulo": "x" * 41}]})
    assert r.status_code == 422


def test_excluir_ouvidoria_marcada(client, headers_gestor, headers_tecnico, cat_id):
    r = client.post("/ouvidorias", json=_payload_ouvidoria(cat_id), headers=headers_gestor)
    assert r.status_code == 200, r.text
    oid = r.json()["id"]
    try:
        _marcar(client, headers_tecnico, oid, "marrom")
    finally:
        r = client.delete(f"/ouvidorias/{oid}", headers=headers_gestor)
    assert r.status_code == 200, r.text
