"""T04 — lista de ouvidorias expõe `assuntos` (categorias sem repetição, na ordem dos itens)."""
from datetime import date, timedelta
from api.repositories.catalog_repo import get_categorias


def _reclamacao(numero_item: int, cat_id: int) -> dict:
    return {
        "numero_item": numero_item,
        "categoria_id": cat_id,
        "subcategoria_id": None,
        "tipo_servico": None,
        "local_embarque": None,
        "local_desembarque": None,
        "empresa_fretamento": None,
        "descricao": f"Reclamação de teste {numero_item}",
        "autos": [],
    }


def test_lista_traz_assuntos_sem_repeticao_na_ordem(client, headers_gestor):
    cats = get_categorias()
    assert len(cats) >= 2, "Banco precisa de ao menos 2 categorias — execute o seed"
    cat_a, cat_b = cats[0], cats[1]
    payload = {
        "protocolo": "PYTEST-T04",
        "conteudo": "Ouvidoria criada por teste automatizado — pode ser deletada",
        "prazo": (date.today() + timedelta(days=30)).isoformat(),
        "prazo_permissionaria": None,
        "status": "Aguardando ações",
        "criado_por_id": 1,
        "reclamacoes": [
            _reclamacao(1, cat_a["id"]),
            _reclamacao(2, cat_b["id"]),
            _reclamacao(3, cat_a["id"]),
        ],
    }
    r = client.post("/ouvidorias", json=payload, headers=headers_gestor)
    assert r.status_code == 200, r.text
    oid = r.json()["id"]
    try:
        r = client.get("/ouvidorias?ocultar_concluidos=false", headers=headers_gestor)
        assert r.status_code == 200, r.text
        item = next(o for o in r.json() if o["id"] == oid)
        assert item["assuntos"] == [cat_a["nome"], cat_b["nome"]]
    finally:
        client.delete(f"/ouvidorias/{oid}", headers=headers_gestor)
