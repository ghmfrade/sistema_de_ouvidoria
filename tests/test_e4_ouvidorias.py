"""Etapa 4 — paridade entre endpoints de ouvidorias e repositórios atuais."""
from datetime import date, timedelta
import pytest
from repositories.ouvidoria_repo import get_ouvidorias, get_ouvidoria_completa
from tests.conftest import OUVIDORIA_ID_FIXTURE

DATA_INI = (date.today() - timedelta(days=365)).isoformat()
DATA_FIM = date.today().isoformat()


def test_paridade_listar_ouvidorias(client, headers_gestor):
    esperado = get_ouvidorias()
    r = client.get("/ouvidorias", headers=headers_gestor)
    assert r.status_code == 200
    obtido = r.json()
    assert len(obtido) == len(esperado)
    assert {o["id"] for o in esperado} == {o["id"] for o in obtido}


def test_paridade_listar_com_filtro_status(client, headers_gestor):
    status = "Concluído"
    esperado = get_ouvidorias(filtro_status=status)
    r = client.get("/ouvidorias", headers=headers_gestor,
                   params={"filtro_status": status})
    assert r.status_code == 200
    assert len(r.json()) == len(esperado)


def test_paridade_detalhe_ouvidoria(client, headers_gestor):
    esperado = get_ouvidoria_completa(OUVIDORIA_ID_FIXTURE)
    assert esperado is not None, (
        f"Ouvidoria {OUVIDORIA_ID_FIXTURE} não encontrada. Ajuste TEST_OUVIDORIA_ID no .env"
    )
    r = client.get(f"/ouvidorias/{OUVIDORIA_ID_FIXTURE}", headers=headers_gestor)
    assert r.status_code == 200
    obtido = r.json()
    assert obtido["id"] == esperado["id"]
    assert obtido["protocolo"] == esperado["protocolo"]
    assert obtido["status"] == esperado["status"]
    assert len(obtido["reclamacoes"]) == len(esperado["reclamacoes"])
    assert len(obtido["atribuicoes"]) == len(esperado["atribuicoes"])


def test_detalhe_inexistente_retorna_404(client, headers_gestor):
    r = client.get("/ouvidorias/999999999", headers=headers_gestor)
    assert r.status_code == 404


def test_busca_por_protocolo(client, headers_gestor):
    dado = get_ouvidoria_completa(OUVIDORIA_ID_FIXTURE)
    protocolo = dado["protocolo"]
    r = client.get(f"/ouvidorias/por-protocolo/{protocolo}", headers=headers_gestor)
    assert r.status_code == 200
    assert r.json() == OUVIDORIA_ID_FIXTURE


def test_ouvidoria_permissionaria(client, headers_gestor):
    r = client.get(f"/ouvidorias/{OUVIDORIA_ID_FIXTURE}/permissionaria", headers=headers_gestor)
    assert r.status_code == 200
    data = r.json()
    assert "id" in data
    assert "respostas_permissionaria" in data


def test_resumo_html(client, headers_gestor):
    r = client.get(f"/ouvidorias/{OUVIDORIA_ID_FIXTURE}/resumo-html", headers=headers_gestor)
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "Ouvidoria" in r.text


# ── Dashboard ─────────────────────────────────────────────────────────────────

def test_kpis_produtividade(client, headers_gestor):
    r = client.get("/dashboard/produtividade/kpis", headers=headers_gestor,
                   params={"data_ini": DATA_INI, "data_fim": DATA_FIM})
    assert r.status_code == 200
    data = r.json()
    assert "total" in data and "concluidas" in data and "vencidas" in data
    assert data["total"] >= 0


def test_volume_por_mes(client, headers_gestor):
    r = client.get("/dashboard/produtividade/volume-por-mes", headers=headers_gestor,
                   params={"data_ini": DATA_INI, "data_fim": DATA_FIM})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_distribuicao_status(client, headers_gestor):
    r = client.get("/dashboard/produtividade/distribuicao-status", headers=headers_gestor,
                   params={"data_ini": DATA_INI, "data_fim": DATA_FIM})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_kpis_qualidade(client, headers_gestor):
    r = client.get("/dashboard/qualidade/kpis", headers=headers_gestor,
                   params={"data_ini": DATA_INI, "data_fim": DATA_FIM})
    assert r.status_code == 200
    data = r.json()
    assert "total_reclamacoes" in data


def test_evolucao_mensal_qualidade(client, headers_gestor):
    r = client.get("/dashboard/qualidade/evolucao-mensal", headers=headers_gestor,
                   params={"data_ini": DATA_INI, "data_fim": DATA_FIM})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_tecnico_nao_acessa_dashboard(client, headers_tecnico):
    r = client.get("/dashboard/produtividade/kpis", headers=headers_tecnico,
                   params={"data_ini": DATA_INI, "data_fim": DATA_FIM})
    assert r.status_code == 403
