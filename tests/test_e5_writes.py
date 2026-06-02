"""Etapa 5 — testa endpoints de escrita de ouvidorias.

Todos os testes que criam dados os limpam ao final para não poluir o banco de dev.
"""
from datetime import date, timedelta
import pytest
from api.repositories.catalog_repo import get_categorias
from api.repositories.ouvidoria_repo import get_ouvidoria_completa
from tests.conftest import OUVIDORIA_ID_FIXTURE


# ── Helpers ───────────────────────────────────────────────────────────────────

def _payload_ouvidoria(cat_id: int, protocolo: str = "PYTEST-AUTO") -> dict:
    return {
        "protocolo": protocolo,
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


# ── Criar e excluir ───────────────────────────────────────────────────────────

def test_criar_e_excluir_ouvidoria(client, headers_gestor, cat_id):
    """Ciclo completo: criar → verificar → excluir → confirmar 404."""
    r = client.post("/ouvidorias", json=_payload_ouvidoria(cat_id), headers=headers_gestor)
    assert r.status_code == 200, r.text
    oid = r.json()["id"]
    assert oid > 0

    r2 = client.get(f"/ouvidorias/{oid}", headers=headers_gestor)
    assert r2.status_code == 200
    assert r2.json()["protocolo"] == "PYTEST-AUTO"

    r3 = client.delete(f"/ouvidorias/{oid}", headers=headers_gestor)
    assert r3.status_code == 200

    r4 = client.get(f"/ouvidorias/{oid}", headers=headers_gestor)
    assert r4.status_code == 404


def test_tecnico_nao_pode_criar(client, headers_tecnico, cat_id):
    r = client.post("/ouvidorias", json=_payload_ouvidoria(cat_id), headers=headers_tecnico)
    assert r.status_code == 403


# ── Editar ────────────────────────────────────────────────────────────────────

def test_editar_ouvidoria(client, headers_gestor, cat_id):
    r = client.post("/ouvidorias", json=_payload_ouvidoria(cat_id, "PYTEST-EDIT"), headers=headers_gestor)
    assert r.status_code == 200
    oid = r.json()["id"]
    try:
        r2 = client.patch(f"/ouvidorias/{oid}", json={"protocolo": "PYTEST-EDITADO"}, headers=headers_gestor)
        assert r2.status_code == 200

        dado = get_ouvidoria_completa(oid)
        assert dado["protocolo"] == "PYTEST-EDITADO"
    finally:
        client.delete(f"/ouvidorias/{oid}", headers=headers_gestor)


# ── Prazo permissionária ──────────────────────────────────────────────────────

def test_atualizar_prazo_permissionaria(client, headers_gestor):
    novo_prazo = (date.today() + timedelta(days=10)).isoformat()
    r = client.patch(
        f"/ouvidorias/{OUVIDORIA_ID_FIXTURE}/prazo-permissionaria",
        json={"prazo": novo_prazo},
        headers=headers_gestor,
    )
    assert r.status_code == 200
    dado = get_ouvidoria_completa(OUVIDORIA_ID_FIXTURE)
    assert dado["prazo_permissionaria"] is not None


# ── Atribuir técnico ──────────────────────────────────────────────────────────

def test_atribuir_tecnico(client, headers_gestor, _tecnico_id):
    """Cria ouvidoria temporária, atribui técnico e verifica."""
    cats = get_categorias()
    r = client.post("/ouvidorias", json=_payload_ouvidoria(cats[0]["id"], "PYTEST-ATRIB"), headers=headers_gestor)
    assert r.status_code == 200
    oid = r.json()["id"]
    try:
        r2 = client.post(
            f"/ouvidorias/{oid}/atribuir-tecnico",
            json={"tecnico_id": _tecnico_id},
            headers=headers_gestor,
        )
        assert r2.status_code == 200

        # Tentar atribuir de novo: deve retornar 409
        r3 = client.post(
            f"/ouvidorias/{oid}/atribuir-tecnico",
            json={"tecnico_id": _tecnico_id},
            headers=headers_gestor,
        )
        assert r3.status_code == 409
    finally:
        client.delete(f"/ouvidorias/{oid}", headers=headers_gestor)


# ── Resposta permissionária ───────────────────────────────────────────────────

def test_registrar_e_deletar_resposta_permissionaria(client, headers_gestor):
    r_list_antes = get_ouvidoria_completa(OUVIDORIA_ID_FIXTURE)
    total_antes = len(r_list_antes["respostas_permissionaria"])
    rp_id = None
    try:
        r = client.post(
            f"/ouvidorias/{OUVIDORIA_ID_FIXTURE}/respostas-permissionaria",
            json={
                "conteudo": "Resposta de teste automatizado",
                "data_resposta": date.today().isoformat(),
                "registrado_por_id": 1,
            },
            headers=headers_gestor,
        )
        assert r.status_code == 200

        dado = get_ouvidoria_completa(OUVIDORIA_ID_FIXTURE)
        assert len(dado["respostas_permissionaria"]) == total_antes + 1
        rp_id = dado["respostas_permissionaria"][-1]["id"]
    finally:
        if rp_id:
            client.delete(
                f"/ouvidorias/{OUVIDORIA_ID_FIXTURE}/respostas-permissionaria/{rp_id}",
                headers=headers_gestor,
            )

    dado_final = get_ouvidoria_completa(OUVIDORIA_ID_FIXTURE)
    assert len(dado_final["respostas_permissionaria"]) == total_antes


# ── Upload de anexo ───────────────────────────────────────────────────────────

def test_upload_e_delete_anexo(client, headers_gestor, tmp_path):
    pdf_bytes = b"%PDF-1.4 teste pytest"
    r = client.post(
        f"/ouvidorias/{OUVIDORIA_ID_FIXTURE}/anexos",
        files={"arquivo": ("teste.pdf", pdf_bytes, "application/pdf")},
        headers=headers_gestor,
    )
    assert r.status_code == 200
    nome_storage = r.json()["nome_storage"]
    anexo_id = None
    try:
        dado = get_ouvidoria_completa(OUVIDORIA_ID_FIXTURE)
        anexo = next((a for a in dado["anexos"] if a["nome_storage"] == nome_storage), None)
        assert anexo is not None
        anexo_id = anexo["id"]
    finally:
        if anexo_id:
            client.delete(
                f"/ouvidorias/{OUVIDORIA_ID_FIXTURE}/anexos/{anexo_id}",
                headers=headers_gestor,
            )


def test_upload_tipo_invalido(client, headers_gestor):
    r = client.post(
        f"/ouvidorias/{OUVIDORIA_ID_FIXTURE}/anexos",
        files={"arquivo": ("script.exe", b"MZ", "application/x-msdownload")},
        headers=headers_gestor,
    )
    assert r.status_code == 422
