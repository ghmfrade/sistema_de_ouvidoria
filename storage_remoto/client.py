"""Cliente HTTP para a API de storage remoto.

Esta pasta é temporária — existe enquanto o storage definitivo não estiver configurado.
Endereço da API: http://10.23.42.237:8001

Endpoints esperados (ver docs/estrutura_pastas.md):
  PUT    /arquivos/{nome_storage}  — armazena o arquivo (multipart, campo "file")
  GET    /arquivos/{nome_storage}  — baixa os bytes do arquivo
  DELETE /arquivos/{nome_storage}  — remove o arquivo
  HEAD   /arquivos/{nome_storage}  — verifica existência (200 = existe, 404 = não existe)
"""
import httpx

_BASE = "http://10.23.42.237:8001"
_TIMEOUT = 30.0


def upload(nome_storage: str, conteudo: bytes, content_type: str = "application/octet-stream") -> None:
    r = httpx.put(
        f"{_BASE}/arquivos/{nome_storage}",
        files={"file": (nome_storage, conteudo, content_type)},
        timeout=_TIMEOUT,
    )
    r.raise_for_status()


def download(nome_storage: str) -> bytes:
    r = httpx.get(f"{_BASE}/arquivos/{nome_storage}", timeout=_TIMEOUT)
    r.raise_for_status()
    return r.content


def remove(nome_storage: str) -> None:
    r = httpx.delete(f"{_BASE}/arquivos/{nome_storage}", timeout=_TIMEOUT)
    r.raise_for_status()


def exists(nome_storage: str) -> bool:
    r = httpx.head(f"{_BASE}/arquivos/{nome_storage}", timeout=_TIMEOUT)
    return r.status_code == 200
