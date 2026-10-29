"""Marcação por cores das ouvidorias e legenda (por login). Sem cache."""
from api.client.base import get, put, delete


def definir_marcacao(oid: int, cor: str) -> None:
    put(f"/ouvidorias/{oid}/marcacao", json={"cor": cor})


def remover_marcacao(oid: int) -> None:
    delete(f"/ouvidorias/{oid}/marcacao")


def carregar_legenda(cache_buster: int = 0) -> list[dict]:
    return get("/marcacoes/legenda")


def salvar_legenda(itens: list[dict]) -> None:
    put("/marcacoes/legenda", json={"itens": itens})
