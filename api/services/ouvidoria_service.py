"""Serviço de ouvidoria: orquestra repositórios de leitura e escrita."""
from api import storage
from api.repositories.ouvidoria_write_repo import criar_ouvidoria


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
    """Cria ouvidoria salvando arquivos via storage.

    arquivos: lista de (nome_original, conteudo_bytes, mime, tamanho, usuario_id)
    Faz rollback dos arquivos se o DB falhar.
    """
    anexos_meta = []
    salvos: list[str] = []
    try:
        for nome_orig, conteudo, mime, tamanho, uid in arquivos:
            nome_storage = storage.save_bytes(conteudo, nome_orig)
            salvos.append(nome_storage)
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
        for nome_storage in salvos:
            storage.remove_file(nome_storage)
        raise
