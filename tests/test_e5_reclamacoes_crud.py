"""Testa o diff de reclamações em registrar_resposta_tecnica.

Cobre:
- Adicionar nova reclamação ao enviar resposta (id=None no payload)
- Remover reclamação ao enviá-la ausente do payload
- Preservar dados relacionados (respostas_permissionaria, etc.) após o diff
- _resolve_tipo_servico retorna enum correto e None para valores inválidos
"""

from datetime import date, timedelta

import pytest

from repositories.catalog_repo import get_categorias
from repositories.ouvidoria_repo import get_ouvidoria_completa
from repositories.ouvidoria_write_repo import _resolve_tipo_servico


# ── Helpers ───────────────────────────────────────────────────────────────────

def _criar_ouvidoria_com_duas_recs(client, headers_gestor, cat_id: int) -> int:
    """Cria ouvidoria temporária com 2 reclamações. Retorna o id."""
    r = client.post("/ouvidorias", json={
        "protocolo": "PYTEST-REC-CRUD",
        "conteudo": "Ouvidoria de teste de CRUD de reclamações",
        "prazo": (date.today() + timedelta(days=30)).isoformat(),
        "prazo_permissionaria": None,
        "status": "Aguardando ações",
        "criado_por_id": 1,
        "reclamacoes": [
            {
                "numero_item": 1,
                "categoria_id": cat_id,
                "subcategoria_id": None,
                "tipo_servico": None,
                "local_embarque": None,
                "local_desembarque": None,
                "empresa_fretamento": None,
                "descricao": "Reclamação 1",
                "autos": [],
            },
            {
                "numero_item": 2,
                "categoria_id": cat_id,
                "subcategoria_id": None,
                "tipo_servico": None,
                "local_embarque": None,
                "local_desembarque": None,
                "empresa_fretamento": None,
                "descricao": "Reclamação 2",
                "autos": [],
            },
        ],
    }, headers=headers_gestor)
    assert r.status_code == 200, r.text
    return r.json()["id"]


@pytest.fixture(scope="module")
def cat_id():
    cats = get_categorias()
    assert cats, "Banco sem categorias — execute o seed"
    return cats[0]["id"]


@pytest.fixture(scope="module")
def tecnico_id_fixture(_usuarios_teste):
    return _usuarios_teste["tecnico_id"]


# ── _resolve_tipo_servico ─────────────────────────────────────────────────────

def test_resolve_tipo_servico_valido():
    from models import TipoServico
    resultado = _resolve_tipo_servico("Regular – Intermunicipal")
    assert resultado == TipoServico.REGULAR_INTERMUNICIPAL


def test_resolve_tipo_servico_none():
    assert _resolve_tipo_servico(None) is None


def test_resolve_tipo_servico_invalido():
    assert _resolve_tipo_servico("Tipo Inexistente") is None


# ── Adicionar reclamação via resposta técnica ─────────────────────────────────

def test_adicionar_reclamacao_via_resposta_tecnica(client, headers_gestor, cat_id, tecnico_id_fixture):
    """Enviar payload com rec nova (id=None) deve criar a reclamação no banco."""
    oid = _criar_ouvidoria_com_duas_recs(client, headers_gestor, cat_id)
    try:
        # Atribuir técnico para poder enviar resposta
        client.post(
            f"/ouvidorias/{oid}/atribuir-tecnico",
            json={"tecnico_id": tecnico_id_fixture},
            headers=headers_gestor,
        )

        dado = get_ouvidoria_completa(oid)
        recs_existentes = dado["reclamacoes"]
        assert len(recs_existentes) == 2

        # Monta payload: 2 existentes + 1 nova (id=None)
        recs_edit = [
            {
                "id": r["id"],
                "numero_item": r["numero_item"],
                "categoria_id": r["categoria_id"],
                "subcategoria_id": None,
                "tipo_servico": None,
                "local_embarque": None,
                "local_desembarque": None,
                "empresa_fretamento": None,
                "descricao": r["descricao"],
                "autos": [],
            }
            for r in recs_existentes
        ] + [
            {
                "id": None,
                "numero_item": 3,
                "categoria_id": cat_id,
                "subcategoria_id": None,
                "tipo_servico": None,
                "local_embarque": None,
                "local_desembarque": None,
                "empresa_fretamento": None,
                "descricao": "Reclamação nova adicionada via resposta",
                "autos": [],
            }
        ]

        r = client.post(
            f"/ouvidorias/{oid}/respostas-tecnicas",
            json={"tecnico_id": tecnico_id_fixture, "texto": "Resposta de teste", "recs_edit": recs_edit},
            headers=headers_gestor,
        )
        assert r.status_code == 200, r.text

        dado_final = get_ouvidoria_completa(oid)
        assert len(dado_final["reclamacoes"]) == 3
        descricoes = {r["descricao"] for r in dado_final["reclamacoes"]}
        assert "Reclamação nova adicionada via resposta" in descricoes
    finally:
        client.delete(f"/ouvidorias/{oid}", headers=headers_gestor)


# ── Remover reclamação via resposta técnica ───────────────────────────────────

def test_remover_reclamacao_via_resposta_tecnica(client, headers_gestor, cat_id, tecnico_id_fixture):
    """Omitir reclamação existente do payload deve excluí-la do banco."""
    oid = _criar_ouvidoria_com_duas_recs(client, headers_gestor, cat_id)
    try:
        client.post(
            f"/ouvidorias/{oid}/atribuir-tecnico",
            json={"tecnico_id": tecnico_id_fixture},
            headers=headers_gestor,
        )

        dado = get_ouvidoria_completa(oid)
        recs_existentes = dado["reclamacoes"]
        assert len(recs_existentes) == 2

        # Envia apenas a primeira reclamação — a segunda deve ser excluída
        primeira = recs_existentes[0]
        recs_edit = [{
            "id": primeira["id"],
            "numero_item": primeira["numero_item"],
            "categoria_id": primeira["categoria_id"],
            "subcategoria_id": None,
            "tipo_servico": None,
            "local_embarque": None,
            "local_desembarque": None,
            "empresa_fretamento": None,
            "descricao": primeira["descricao"],
            "autos": [],
        }]

        r = client.post(
            f"/ouvidorias/{oid}/respostas-tecnicas",
            json={"tecnico_id": tecnico_id_fixture, "texto": "Resposta de teste", "recs_edit": recs_edit},
            headers=headers_gestor,
        )
        assert r.status_code == 200, r.text

        dado_final = get_ouvidoria_completa(oid)
        assert len(dado_final["reclamacoes"]) == 1
        assert dado_final["reclamacoes"][0]["id"] == primeira["id"]
    finally:
        client.delete(f"/ouvidorias/{oid}", headers=headers_gestor)


# ── Dados relacionados são preservados ───────────────────────────────────────

def test_dados_relacionados_preservados_apos_diff(client, headers_gestor, cat_id, tecnico_id_fixture):
    """Após diff de reclamações, respostas da permissionária devem ser mantidas."""
    oid = _criar_ouvidoria_com_duas_recs(client, headers_gestor, cat_id)
    try:
        # Adicionar resposta da permissionária
        client.post(
            f"/ouvidorias/{oid}/respostas-permissionaria",
            json={
                "conteudo": "Resposta da permissionária de teste",
                "data_resposta": date.today().isoformat(),
                "registrado_por_id": 1,
            },
            headers=headers_gestor,
        )

        client.post(
            f"/ouvidorias/{oid}/atribuir-tecnico",
            json={"tecnico_id": tecnico_id_fixture},
            headers=headers_gestor,
        )

        dado = get_ouvidoria_completa(oid)
        assert len(dado["respostas_permissionaria"]) == 1

        # Enviar resposta técnica modificando reclamações (remove a 2ª)
        primeira = dado["reclamacoes"][0]
        recs_edit = [{
            "id": primeira["id"],
            "numero_item": primeira["numero_item"],
            "categoria_id": primeira["categoria_id"],
            "subcategoria_id": None,
            "tipo_servico": None,
            "local_embarque": None,
            "local_desembarque": None,
            "empresa_fretamento": None,
            "descricao": primeira["descricao"],
            "autos": [],
        }]

        client.post(
            f"/ouvidorias/{oid}/respostas-tecnicas",
            json={"tecnico_id": tecnico_id_fixture, "texto": "Resposta de teste", "recs_edit": recs_edit},
            headers=headers_gestor,
        )

        dado_final = get_ouvidoria_completa(oid)
        assert len(dado_final["reclamacoes"]) == 1
        assert len(dado_final["respostas_permissionaria"]) == 1, "Resposta da permissionária foi perdida"
        assert len(dado_final["respostas_tecnicas"]) == 1, "Resposta técnica não foi registrada"
    finally:
        client.delete(f"/ouvidorias/{oid}", headers=headers_gestor)
