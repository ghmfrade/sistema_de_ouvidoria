"""Storage de anexos.

Em prod, configurar UPLOADS_DIR para um volume montado (NFS/NAS) compartilhado
entre as instancias da API. Em dev, default = api/uploads/ local.
"""
import os
import uuid
from pathlib import Path

UPLOADS_DIR = Path(os.environ.get("UPLOADS_DIR", str(Path(__file__).parent / "uploads")))


def ensure_dir() -> None:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def save_bytes(content: bytes, original_filename: str) -> str:
    """Grava bytes no storage e retorna o nome_storage gerado (uuid + extensao)."""
    ensure_dir()
    ext = Path(original_filename).suffix
    nome_storage = f"{uuid.uuid4().hex}{ext}"
    (UPLOADS_DIR / nome_storage).write_bytes(content)
    return nome_storage


def path_for(nome_storage: str) -> Path:
    return UPLOADS_DIR / nome_storage


def exists(nome_storage: str) -> bool:
    return path_for(nome_storage).exists()


def remove_file(nome_storage: str) -> None:
    p = path_for(nome_storage)
    if p.exists():
        p.unlink()
