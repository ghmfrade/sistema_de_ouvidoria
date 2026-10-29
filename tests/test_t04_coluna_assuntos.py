"""T04/T08 — lista de ouvidorias expõe `assuntos` (subcategorias, ou categoria como fallback,
sem repetição, na ordem dos itens)."""
from datetime import date, timedelta
from api.repositories.catalog_repo import get_categorias, get_subcategorias


def _reclamacao(numero_item: int, cat_id: int, sub_id: int | None) -> dict:
    return {
        "numero_item": numero_item,
        "categoria_id": cat_id,
        "subcategoria_id": sub_id,
        "tipo_servico": None,
        "local_embarque": None,
        "local_desembarque": None,
        "empresa_fretamento": None,
        "descricao": f"Reclamação de teste {numero_item}",
        "autos": [],
    }


def _payload(reclamacoes: list[dict], protocolo: str) -> dict:
    return {
        "protocolo": protocolo,
        "conteudo": "Ouvidoria criada por teste automatizado — pode ser deletada",
        "prazo": (date.today() + timedelta(days=30)).isoformat(),
        "prazo_permissionaria": None,
        "status": "Aguardando ações",
        "criado_por_id": 1,
        "reclamacoes": reclamacoes,
    }


def _assuntos_da_lista(client, headers, oid: int) -> list[str]:
    r = client.get("/ouvidorias?ocultar_concluidos=false", headers=headers)
    assert r.status_code == 200, r.text
    return next(o for o in r.json() if o["id"] == oid)["assuntos"]


def test_lista_traz_subcategorias_sem_repeticao_na_ordem(client, headers_gestor):
    subs = get_subcategorias()
    assert len(subs) >= 2, "Banco precisa de ao menos 2 subcategorias — execute o seed"
    sub_a = subs[0]
    sub_b = next((s for s in subs if s["nome"] != sub_a["nome"]), None)
    assert sub_b is not None, "Banco precisa de 2 subcategorias com nomes distintos"
    payload = _payload(
        [
            _reclamacao(1, sub_a["categoria_id"], sub_a["id"]),
            _reclamacao(2, sub_b["categoria_id"], sub_b["id"]),
            _reclamacao(3, sub_a["categoria_id"], sub_a["id"]),
        ],
        "PYTEST-T08A",
    )
    r = client.post("/ouvidorias", json=payload, headers=headers_gestor)
    assert r.status_code == 200, r.text
    oid = r.json()["id"]
    try:
        assert _assuntos_da_lista(client, headers_gestor, oid) == [sub_a["nome"], sub_b["nome"]]
    finally:
        client.delete(f"/ouvidorias/{oid}", headers=headers_gestor)


def test_lista_usa_categoria_quando_sem_subcategoria(client, headers_gestor):
    cats = get_categorias()
    assert cats, "Banco precisa de ao menos 1 categoria — execute o seed"
    cat = cats[0]
    r = client.post(
        "/ouvidorias",
        json=_payload([_reclamacao(1, cat["id"], None)], "PYTEST-T08B"),
        headers=headers_gestor,
    )
    assert r.status_code == 200, r.text
    oid = r.json()["id"]
    try:
        assert _assuntos_da_lista(client, headers_gestor, oid) == [cat["nome"]]
    finally:
        client.delete(f"/ouvidorias/{oid}", headers=headers_gestor)
