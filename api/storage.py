"""Storage de anexos.

USAR_STORAGE_REMOTO = True  → envia/busca arquivos via API em http://10.23.42.237:8001
USAR_STORAGE_REMOTO = False → salva em disco local (api/uploads/), comportamento original

Em prod, manter True. Para desenvolvimento local sem acesso à API remota, trocar para False.
"""
import uuid
from pathlib import Path

# Troca para False para usar disco local (desenvolvimento sem acesso à API remota)
USAR_STORAGE_REMOTO = True

UPLOADS_DIR = Path(__file__).parent / "uploads"


def _usar_remoto() -> bool:
    return USAR_STORAGE_REMOTO


def ensure_dir() -> None:
    if not _usar_remoto():
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def save_bytes(content: bytes, original_filename: str, content_type: str = "application/octet-stream") -> str:
    """Grava bytes no storage e retorna o nome_storage gerado (uuid + extensao)."""
    ext = Path(original_filename).suffix
    nome_storage = f"{uuid.uuid4().hex}{ext}"
    if _usar_remoto():
        from storage_remoto.client import upload
        upload(nome_storage, content, content_type)
    else:
        ensure_dir()
        (UPLOADS_DIR / nome_storage).write_bytes(content)
    return nome_storage


def get_bytes(nome_storage: str) -> bytes:
    """Retorna os bytes do arquivo (local ou remoto)."""
    if _usar_remoto():
        from storage_remoto.client import download
        return download(nome_storage)
    return path_for(nome_storage).read_bytes()


def path_for(nome_storage: str) -> Path:
    return UPLOADS_DIR / nome_storage


def exists(nome_storage: str) -> bool:
    if _usar_remoto():
        from storage_remoto.client import exists as _exists
        return _exists(nome_storage)
    return path_for(nome_storage).exists()


def remove_file(nome_storage: str) -> None:
    if _usar_remoto():
        from storage_remoto.client import remove
        remove(nome_storage)
    else:
        p = path_for(nome_storage)
        if p.exists():
            p.unlink()
