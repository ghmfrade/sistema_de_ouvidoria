"""Serviço de ouvidoria: orquestra repositórios de leitura e escrita."""
import os
import uuid
from pathlib import Path

from repositories.ouvidoria_write_repo import criar_ouvidoria

UPLOADS_DIR = Path(os.environ.get("UPLOADS_DIR", "uploads"))


def criar_ouvidoria_sem_anexos(body) -> int:
    """Cria ouvidoria a partir de CriarOuvidoriaRequest (sem arquivos)."""
    recs_draft = [
        {
            "numero_item": r.numero_item,
            "categoria_id": r.categoria_id,
            "subcategoria_id": r.subcategoria_id,
            "tipo_servico": r.tipo_servico,
            "local_embarque": r.local_embarque,
            "local_desembarque": r.local_desembarque,
            "empresa_fretamento": r.empresa_fretamento,
            "descricao": r.descricao,
            "autos": [{"id": a.id} for a in r.autos],
        }
        for r in body.reclamacoes
    ]
    return criar_ouvidoria(
        protocolo=body.protocolo or "",
        conteudo=body.conteudo or "",
        prazo=body.prazo,
        prazo_permissionaria=body.prazo_permissionaria,
        status=body.status,
        criado_por_id=body.criado_por_id,
        recs_draft=recs_draft,
        anexos_meta=[],
    )


def criar_ouvidoria_com_anexos(body, arquivos: list[tuple]) -> int:
    """Cria ouvidoria salvando arquivos em disco.

    arquivos: lista de (nome_original, conteudo_bytes, mime, tamanho, usuario_id)
    Faz rollback dos arquivos se o DB falhar.
    """
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    anexos_meta = []
    salvos: list[Path] = []
    try:
        for nome_orig, conteudo, mime, tamanho, uid in arquivos:
            ext = Path(nome_orig).suffix
            nome_storage = f"{uuid.uuid4().hex}{ext}"
            caminho = UPLOADS_DIR / nome_storage
            caminho.write_bytes(conteudo)
            salvos.append(caminho)
            anexos_meta.append({
                "nome_arquivo": nome_orig,
                "nome_storage": nome_storage,
                "tipo_mime": mime,
                "tamanho": tamanho,
                "enviado_por_id": uid,
            })
        recs_draft = [
            {
                "numero_item": r.numero_item,
                "categoria_id": r.categoria_id,
                "subcategoria_id": r.subcategoria_id,
                "tipo_servico": r.tipo_servico,
                "local_embarque": r.local_embarque,
                "local_desembarque": r.local_desembarque,
                "empresa_fretamento": r.empresa_fretamento,
                "descricao": r.descricao,
                "autos": [{"id": a.id} for a in r.autos],
            }
            for r in body.reclamacoes
        ]
        return criar_ouvidoria(
            protocolo=body.protocolo or "",
            conteudo=body.conteudo or "",
            prazo=body.prazo,
            prazo_permissionaria=body.prazo_permissionaria,
            status=body.status,
            criado_por_id=body.criado_por_id,
            recs_draft=recs_draft,
            anexos_meta=anexos_meta,
        )
    except Exception:
        for p in salvos:
            p.unlink(missing_ok=True)
        raise
