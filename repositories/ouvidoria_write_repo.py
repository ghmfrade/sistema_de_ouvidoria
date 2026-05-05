"""Operações de escrita no banco para ouvidorias."""

from datetime import date, datetime

from database.connection import db_session
from repositories.pontuacao import calcular_pontuacao_auto
from models import (
    AnexoOuvidoria,
    Ouvidoria,
    OuvidoriaTecnico,
    Reclamacao,
    ReclamacaoAuto,
    RespostaPermissionaria,
    RespostaTecnica,
    StatusOuvidoria,
    TipoServico,
)


def criar_ouvidoria(protocolo, conteudo, prazo, prazo_permissionaria,
                    status, criado_por_id, recs_draft, anexos_meta):
    """Cria ouvidoria com reclamações, autos e anexos em uma transação.
    recs_draft: lista de dicts com dados das reclamações.
    anexos_meta: lista de dicts {nome_arquivo, nome_storage, tipo_mime, tamanho, enviado_por_id}.
    Retorna o id da ouvidoria criada."""
    with db_session() as session:
        ouvidoria = Ouvidoria(
            protocolo=protocolo.strip(),
            conteudo=conteudo.strip(),
            prazo=prazo,
            prazo_permissionaria=prazo_permissionaria,
            status=status,
            criado_por_id=criado_por_id,
        )
        session.add(ouvidoria)
        session.flush()

        for rec_draft in recs_draft:
            tipo_srv = None
            ts_val = rec_draft.get("tipo_servico")
            if ts_val:
                for ts in TipoServico:
                    if ts.value == ts_val:
                        tipo_srv = ts
                        break

            rec = Reclamacao(
                ouvidoria_id=ouvidoria.id,
                numero_item=rec_draft["numero_item"],
                categoria_id=rec_draft["categoria_id"],
                subcategoria_id=rec_draft.get("subcategoria_id"),
                tipo_servico=tipo_srv,
                local_embarque=rec_draft["local_embarque"],
                local_desembarque=rec_draft["local_desembarque"],
                descricao=rec_draft["descricao"],
                empresa_fretamento=rec_draft.get("empresa_fretamento"),
            )
            session.add(rec)
            session.flush()

            autos_rec = rec_draft["autos"]
            pontuacao = calcular_pontuacao_auto(len(autos_rec))
            for a in autos_rec:
                session.add(ReclamacaoAuto(
                    reclamacao_id=rec.id,
                    auto_id=a["id"],
                    pontuacao=pontuacao,
                ))

        for meta in anexos_meta:
            session.add(AnexoOuvidoria(
                ouvidoria_id=ouvidoria.id,
                nome_arquivo=meta["nome_arquivo"],
                nome_storage=meta["nome_storage"],
                tipo_mime=meta["tipo_mime"],
                tamanho=meta["tamanho"],
                enviado_por_id=meta["enviado_por_id"],
            ))

        return ouvidoria.id


def editar_ouvidoria(
    oid,
    protocolo=None,
    conteudo=None,
    prazo=None,
    prazo_permissionaria=None,
    status=None
):
    """Atualiza dados da ouvidoria (parcial ou completo)."""
    with db_session() as s:
        o = s.query(Ouvidoria).filter_by(id=oid).first()

        if not o:
            return

        if protocolo is not None:
            o.protocolo = protocolo.strip()

        if conteudo is not None:
            o.conteudo = conteudo.strip()

        if prazo is not None:
            o.prazo = prazo

        if prazo_permissionaria is not None:
            o.prazo_permissionaria = prazo_permissionaria

        if status is not None:
            novo_status = StatusOuvidoria(status)
            o.status = novo_status

            if novo_status == StatusOuvidoria.CONCLUIDO:
                o.concluido_em = datetime.now()
            else:
                o.concluido_em = None


def atualizar_prazo_permissionaria(oid: int, prazo: date | None):
    """Define ou apaga o prazo da permissionária. Aceita None para remover."""
    with db_session() as s:
        o = s.query(Ouvidoria).filter_by(id=oid).first()
        if o:
            o.prazo_permissionaria = prazo


def atribuir_tecnico(ouvidoria_id: int, tecnico_id: int):
    """Atribui técnico a ouvidoria. Retorna False se já atribuído."""
    with db_session() as s:
        existe = s.query(OuvidoriaTecnico).filter_by(
            ouvidoria_id=ouvidoria_id, tecnico_id=tecnico_id
        ).first()
        if existe:
            return False
        s.add(OuvidoriaTecnico(ouvidoria_id=ouvidoria_id, tecnico_id=tecnico_id))
        o = s.query(Ouvidoria).filter_by(id=ouvidoria_id).first()
        if o and o.status == StatusOuvidoria.AGUARDANDO_ACOES:
            o.status = StatusOuvidoria.EM_ANALISE_TECNICA
    return True


def excluir_ouvidoria(oid: int):
    """Exclui ouvidoria por id."""
    with db_session() as s:
        o = s.query(Ouvidoria).filter_by(id=oid).first()
        if o:
            s.delete(o)


def concluir_ouvidoria(oid: int):
    """Marca ouvidoria como concluída."""
    with db_session() as s:
        o = s.query(Ouvidoria).filter_by(id=oid).first()
        if o:
            o.status = StatusOuvidoria.CONCLUIDO
            o.concluido_em = datetime.now()


def add_anexos(ouvidoria_id, anexos_meta):
    """Registra anexos no banco. anexos_meta: lista de dicts com metadados."""
    with db_session() as session:
        for meta in anexos_meta:
            session.add(AnexoOuvidoria(
                ouvidoria_id=ouvidoria_id,
                nome_arquivo=meta["nome_arquivo"],
                nome_storage=meta["nome_storage"],
                tipo_mime=meta["tipo_mime"],
                tamanho=meta["tamanho"],
                enviado_por_id=meta["enviado_por_id"],
            ))


def delete_anexo(anexo_id: int) -> str | None:
    """Remove AnexoOuvidoria do banco. Retorna nome_storage para remoção do disco."""
    with db_session() as s:
        obj = s.get(AnexoOuvidoria, anexo_id)
        if obj:
            nome = obj.nome_storage
            s.delete(obj)
            return nome
    return None


def registrar_resposta_permissionaria(ouvidoria_id, conteudo, data_resposta, registrado_por_id):
    """Registra resposta da permissionária e atualiza status se necessário."""
    with db_session() as session:
        session.add(RespostaPermissionaria(
            ouvidoria_id=ouvidoria_id,
            conteudo=conteudo.strip(),
            data_resposta=data_resposta,
            registrado_por_id=registrado_por_id,
        ))
        o = session.get(Ouvidoria, ouvidoria_id)
        if o and o.status == StatusOuvidoria.AGUARDANDO_PERMISSIONARIA:
            o.status = StatusOuvidoria.AGUARDANDO_ACOES


def deletar_resposta_permissionaria(rp_id: int):
    """Remove RespostaPermissionaria pelo id."""
    with db_session() as session:
        obj = session.get(RespostaPermissionaria, rp_id)
        if obj:
            session.delete(obj)


def registrar_resposta_tecnica(ouvidoria_id, tecnico_id, texto, recs_edit):
    """Salva edições nas reclamações, cria resposta técnica, marca atribuição respondida.
    Retorna True se status mudou para RETORNO_TECNICO."""
    with db_session() as session:
        for rec_edit in recs_edit:
            rec_db = session.query(Reclamacao).filter_by(id=rec_edit["id"]).first()
            if not rec_db:
                continue
            rec_db.categoria_id = rec_edit["categoria_id"]
            rec_db.subcategoria_id = rec_edit.get("subcategoria_id")
            rec_db.local_embarque = rec_edit["local_embarque"]
            rec_db.local_desembarque = rec_edit["local_desembarque"]
            rec_db.descricao = rec_edit["descricao"]
            rec_db.empresa_fretamento = rec_edit.get("empresa_fretamento")

            session.query(ReclamacaoAuto).filter_by(reclamacao_id=rec_db.id).delete()
            session.flush()

            pontuacao = calcular_pontuacao_auto(len(rec_edit["autos"]))
            for a in rec_edit["autos"]:
                session.add(ReclamacaoAuto(
                    reclamacao_id=rec_db.id,
                    auto_id=a["id"],
                    pontuacao=pontuacao,
                ))

        resp = RespostaTecnica(
            ouvidoria_id=ouvidoria_id,
            tecnico_id=tecnico_id,
            data_resposta=date.today(),
            texto_resposta=texto.strip(),
        )
        session.add(resp)

        at = session.query(OuvidoriaTecnico).filter_by(
            ouvidoria_id=ouvidoria_id, tecnico_id=tecnico_id
        ).first()
        if at:
            at.respondido = True
            at.respondido_em = datetime.now()

        todas = session.query(OuvidoriaTecnico).filter_by(ouvidoria_id=ouvidoria_id).all()
        todos_responderam = all(a.respondido for a in todas)

        if todos_responderam:
            o_db = session.query(Ouvidoria).filter_by(id=ouvidoria_id).first()
            if o_db and o_db.status == StatusOuvidoria.EM_ANALISE_TECNICA:
                o_db.status = StatusOuvidoria.RETORNO_TECNICO

    return todos_responderam


def get_auto_permissionaria_nome(auto_id: int) -> str:
    """Busca nome da permissionária de um auto. Retorna '–' se não encontrado."""
    with db_session() as s:
        from models import AutoLinha
        auto = s.query(AutoLinha).filter_by(id=auto_id).first()
        if auto and auto.permissionaria:
            return auto.permissionaria.nome
        return "–"
