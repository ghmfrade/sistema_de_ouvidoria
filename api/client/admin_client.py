"""Substitui utils/loaders_admin.py e operações de admin."""
from api.client.base import get, post, patch


# ── Leitura ───────────────────────────────────────────────────────────────────

def listar_usuarios_e_status() -> list[dict]:
    return get("/admin/usuarios")


def listar_categorias_e_status() -> list[dict]:
    return get("/admin/categorias")


def listar_subcat_e_status(categoria_id: int | None = None) -> list[dict]:
    params = {"categoria_id": categoria_id} if categoria_id else None
    return get("/admin/subcategorias", params=params)


def listar_gerencias_e_status() -> list[dict]:
    return get("/admin/gerencias")


def listar_coord_e_status(gerencia_id: int | None = None) -> list[dict]:
    params = {"gerencia_id": gerencia_id} if gerencia_id else None
    return get("/admin/coordenacoes", params=params)


def email_existe(email: str) -> bool:
    return get("/admin/usuarios/email-existe", params={"email": email})


# ── Escrita ───────────────────────────────────────────────────────────────────

def criar_usuario(nome: str, email: str, senha: str, tipo: str,
                  gerencia_id: int | None = None, coordenacao_id: int | None = None) -> None:
    post("/admin/usuarios", json={
        "nome": nome, "email": email, "senha": senha, "tipo": tipo,
        "gerencia_id": gerencia_id, "coordenacao_id": coordenacao_id,
    })


def toggle_usuario(usuario_id: int, ativo: bool) -> None:
    patch(f"/admin/usuarios/{usuario_id}/toggle", json={"ativo": ativo})


def criar_categoria(nome: str, descricao: str | None = None) -> None:
    post("/admin/categorias", json={"nome": nome, "descricao": descricao})


def toggle_categoria(cat_id: int, ativo: bool) -> None:
    patch(f"/admin/categorias/{cat_id}/toggle", json={"ativo": ativo})


def criar_subcategoria(nome: str, categoria_id: int) -> None:
    post("/admin/subcategorias", json={"nome": nome, "categoria_id": categoria_id})


def toggle_subcategoria(subcat_id: int, ativo: bool) -> None:
    patch(f"/admin/subcategorias/{subcat_id}/toggle", json={"ativo": ativo})


def criar_gerencia(nome: str) -> None:
    post("/admin/gerencias", json={"nome": nome})


def toggle_gerencia(ger_id: int, ativo: bool) -> None:
    patch(f"/admin/gerencias/{ger_id}/toggle", json={"ativo": ativo})


def criar_coordenacao(nome: str, gerencia_id: int | None = None) -> None:
    post("/admin/coordenacoes", json={"nome": nome, "gerencia_id": gerencia_id})


def toggle_coordenacao(coord_id: int, ativo: bool) -> None:
    patch(f"/admin/coordenacoes/{coord_id}/toggle", json={"ativo": ativo})
