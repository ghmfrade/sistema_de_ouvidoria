"""Operações administrativas: delega ao admin_write_repo. Zero db_session direto."""

from repositories.admin_write_repo import (
    criar_categoria,
    criar_coordenacao,
    criar_gerencia,
    criar_subcategoria,
    criar_usuario,
    email_existe,
    toggle_categoria,
    toggle_coordenacao,
    toggle_gerencia,
    toggle_subcategoria,
    toggle_usuario,
)

__all__ = [
    "email_existe",
    "criar_usuario",
    "toggle_usuario",
    "criar_categoria",
    "toggle_categoria",
    "criar_subcategoria",
    "toggle_subcategoria",
    "criar_gerencia",
    "toggle_gerencia",
    "criar_coordenacao",
    "toggle_coordenacao",
]
