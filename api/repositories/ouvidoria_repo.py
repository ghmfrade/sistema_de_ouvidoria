"""Consultas ao banco para carregamento de ouvidorias."""

from datetime import date, datetime, timedelta
from sqlalchemy.orm import joinedload

from api.database.connection import db_session
from api.models import (
    AnexoOuvidoria,
    AutoLinha,
    Ouvidoria,
    OuvidoriaTecnico,
    ReclamacaoAuto,
    Reclamacao,
    RespostaPermissionaria,
    RespostaTecnica,
    StatusOuvidoria,
    TipoUsuario,
    Usuario,
)
from api.repositories.types import (
    AnexoDict,
    AtribuicaoScalarDict,
    OuvidoriaDetalheDict,
    OuvidoriaPermissionariaDict,
    OuvidoriaResumoDict,
    OuvidoriaTecnicoDict,
    ReclamacaoAutoDict,
    ReclamacaoDict,
    RespostaPermissionariaDict,
    RespostaTecnicaDict,
)


# ── Helpers de conversão ──────────────────────────────────────────────────────

def _to_atribuicao_dict(at: OuvidoriaTecnico) -> OuvidoriaTecnicoDict:
    tec = at.tecnico
    return OuvidoriaTecnicoDict(
        tecnico_id=at.tecnico_id,
        tecnico_nome=tec.nome if tec else "?",
        gerencia_nome=tec.gerencia.nome if tec and tec.gerencia else None,
        coordenacao_nome=tec.coordenacao.nome if tec and tec.coordenacao else None,
        respondido=at.respondido,
        respondido_em=at.respondido_em,
    )


def _to_reclamacao_dict(r: Reclamacao) -> ReclamacaoDict:
    autos = [
        ReclamacaoAutoDict(
            auto_id=ra.auto.id,
            numero=ra.auto.numero,
            denominacao_a=ra.auto.denominacao_a,
            denominacao_b=ra.auto.denominacao_b,
            permissionaria_nome=(ra.auto.permissionaria.nome_fantasia or ra.auto.permissionaria.nome) if ra.auto.permissionaria else "–",
            tipo=ra.auto.tipo.value if ra.auto.tipo else None,
            regiao_metropolitana=ra.auto.regiao_metropolitana,
            tc=ra.auto.tc,
            pontuacao=ra.pontuacao,
        )
        for ra in r.autos_vinculados
        if ra.auto
    ]
    return ReclamacaoDict(
        id=r.id,
        numero_item=r.numero_item,
        categoria_id=r.categoria_id,
        categoria_nome=r.categoria.nome if r.categoria else None,
        subcategoria_id=r.subcategoria_id,
        subcategoria_nome=r.subcategoria.nome if r.subcategoria else None,
        tipo_servico=r.tipo_servico.value if r.tipo_servico else None,
        local_embarque=r.local_embarque,
        local_desembarque=r.local_desembarque,
        empresa_fretamento=r.empresa_fretamento,
        descricao=r.descricao,
        autos=autos,
    )


def _to_resposta_perm_dict(rp: RespostaPermissionaria) -> RespostaPermissionariaDict:
    return RespostaPermissionariaDict(
        id=rp.id,
        conteudo=rp.conteudo,
        data_resposta=rp.data_resposta,
        registrado_por_nome=rp.registrado_por.nome if rp.registrado_por else "—",
        criado_em=rp.criado_em,
    )


def _to_anexo_dict(an: AnexoOuvidoria) -> AnexoDict:
    return AnexoDict(
        id=an.id,
        nome_arquivo=an.nome_arquivo,
        nome_storage=an.nome_storage,
        tipo_mime=an.tipo_mime,
        tamanho=an.tamanho,
        enviado_por_nome=an.enviado_por.nome if an.enviado_por else "?",
        criado_em=an.criado_em,
    )


def get_anexo(anexo_id: int) -> dict | None:
    """Busca um anexo por id. Retorna dict com dados necessarios para download."""
    with db_session() as session:
        a = session.get(AnexoOuvidoria, anexo_id)
        if a is None:
            return None
        return {
            "id": a.id,
            "ouvidoria_id": a.ouvidoria_id,
            "nome_arquivo": a.nome_arquivo,
            "nome_storage": a.nome_storage,
            "tipo_mime": a.tipo_mime,
        }


def _to_detalhe(o: Ouvidoria) -> OuvidoriaDetalheDict:
    return OuvidoriaDetalheDict(
        id=o.id,
        protocolo=o.protocolo,
        conteudo=o.conteudo,
        status=o.status.value,
        prazo=o.prazo,
        prazo_permissionaria=o.prazo_permissionaria,
        criado_em=o.criado_em,
        concluido_em=o.concluido_em,
        reclamacoes=[_to_reclamacao_dict(r) for r in o.reclamacoes],
        atribuicoes=[_to_atribuicao_dict(at) for at in o.atribuicoes],
        respostas_tecnicas=[
            RespostaTecnicaDict(
                id=r.id,
                tecnico_id=r.tecnico_id,
                tecnico_nome=r.tecnico.nome if r.tecnico else "?",
                data_resposta=r.data_resposta,
                texto_resposta=r.texto_resposta,
            )
            for r in o.respostas
        ],
        respostas_permissionaria=[_to_resposta_perm_dict(rp) for rp in o.respostas_permissionaria],
        anexos=[_to_anexo_dict(an) for an in o.anexos],
    )


# ── Funções públicas ──────────────────────────────────────────────────────────

def get_ouvidoria_completa(oid: int) -> OuvidoriaDetalheDict | None:
    """Ouvidoria com TODOS os relacionamentos. Retorna OuvidoriaDetalheDict | None."""
    with db_session() as s:
        o = (
            s.query(Ouvidoria)
            .options(
                joinedload(Ouvidoria.reclamacoes)
                    .joinedload(Reclamacao.categoria),
                joinedload(Ouvidoria.reclamacoes)
                    .joinedload(Reclamacao.subcategoria),
                joinedload(Ouvidoria.reclamacoes)
                    .joinedload(Reclamacao.autos_vinculados)
                    .joinedload(ReclamacaoAuto.auto)
                    .joinedload(AutoLinha.permissionaria),
                joinedload(Ouvidoria.atribuicoes)
                    .joinedload(OuvidoriaTecnico.tecnico)
                    .joinedload(Usuario.gerencia),
                joinedload(Ouvidoria.atribuicoes)
                    .joinedload(OuvidoriaTecnico.tecnico)
                    .joinedload(Usuario.coordenacao),
                joinedload(Ouvidoria.respostas)
                    .joinedload(RespostaTecnica.tecnico),
                joinedload(Ouvidoria.respostas_permissionaria)
                    .joinedload(RespostaPermissionaria.registrado_por),
                joinedload(Ouvidoria.anexos)
                    .joinedload(AnexoOuvidoria.enviado_por),
            )
            .filter_by(id=oid)
            .first()
        )
        if not o:
            return None
        return _to_detalhe(o)


def get_ouvidoria_permissionaria(oid: int) -> OuvidoriaPermissionariaDict | None:
    """Ouvidoria com respostas_permissionaria para a página 04."""
    with db_session() as s:
        o = (
            s.query(Ouvidoria)
            .options(
                joinedload(Ouvidoria.respostas_permissionaria)
                    .joinedload(RespostaPermissionaria.registrado_por),
            )
            .filter_by(id=oid)
            .first()
        )
        if not o:
            return None
        return OuvidoriaPermissionariaDict(
            id=o.id,
            conteudo=o.conteudo,
            status=o.status.value,
            prazo=o.prazo,
            prazo_permissionaria=o.prazo_permissionaria,
            respostas_permissionaria=[_to_resposta_perm_dict(rp) for rp in o.respostas_permissionaria],
        )


def get_atribuicao_tecnico(ouvidoria_id: int, tecnico_id: int) -> AtribuicaoScalarDict | None:
    """Atribuição específica de técnico a uma ouvidoria."""
    with db_session() as s:
        at = (
            s.query(OuvidoriaTecnico)
            .filter_by(ouvidoria_id=ouvidoria_id, tecnico_id=tecnico_id)
            .first()
        )
        if not at:
            return None
        return AtribuicaoScalarDict(
            ouvidoria_id=at.ouvidoria_id,
            tecnico_id=at.tecnico_id,
            respondido=at.respondido,
            respondido_em=at.respondido_em,
        )


def get_respostas_tecnico(ouvidoria_id: int, tecnico_id: int) -> list[RespostaTecnicaDict]:
    """Respostas técnicas de um técnico para uma ouvidoria, desc por data."""
    with db_session() as s:
        resps = (
            s.query(RespostaTecnica)
            .options(joinedload(RespostaTecnica.tecnico))
            .filter_by(ouvidoria_id=ouvidoria_id, tecnico_id=tecnico_id)
            .order_by(RespostaTecnica.data_resposta.desc())
            .all()
        )
        return [
            RespostaTecnicaDict(
                id=r.id,
                tecnico_id=r.tecnico_id,
                tecnico_nome=r.tecnico.nome if r.tecnico else "?",
                data_resposta=r.data_resposta,
                texto_resposta=r.texto_resposta,
            )
            for r in resps
        ]


def get_id_por_protocolo(protocolo: str) -> int | None:
    """Retorna o id da ouvidoria com o protocolo informado, ou None se não existir."""
    with db_session() as s:
        row = s.query(Ouvidoria.id).filter_by(protocolo=protocolo.strip()).first()
        return row[0] if row else None


def get_ouvidorias(filtro_status=None, filtro_de=None, filtro_ate=None,
                   ocultar_concluidos=True,
                   usuario_id: int | None = None, usuario_tipo: str | None = None,
                   filtro_categoria_id: int | None = None,
                   filtro_subcategoria_id: int | None = None,
                   filtro_tipo_servico: str | None = None,
                   filtrar_apenas_atribuidas: bool = True) -> list[OuvidoriaResumoDict]:
    """Lista de ouvidorias com filtros e atribuições. Retorna list[OuvidoriaResumoDict]."""
    with db_session() as s:
        q = (
            s.query(Ouvidoria)
            .options(
                joinedload(Ouvidoria.atribuicoes)
                    .joinedload(OuvidoriaTecnico.tecnico)
                    .joinedload(Usuario.gerencia),
                joinedload(Ouvidoria.atribuicoes)
                    .joinedload(OuvidoriaTecnico.tecnico)
                    .joinedload(Usuario.coordenacao),
                joinedload(Ouvidoria.respostas_permissionaria),
            )
        )
        if usuario_id and usuario_tipo == TipoUsuario.tecnico.value and filtrar_apenas_atribuidas:
            q = (
                q.join(OuvidoriaTecnico, OuvidoriaTecnico.ouvidoria_id == Ouvidoria.id)
                .filter(OuvidoriaTecnico.tecnico_id == usuario_id)
            )
        if filtro_status:
            q = q.filter(Ouvidoria.status == filtro_status)
        elif ocultar_concluidos:
            q = q.filter(Ouvidoria.status != StatusOuvidoria.CONCLUIDO)
        if filtro_de and filtro_ate:
            de = datetime.combine(date.fromisoformat(filtro_de), datetime.min.time())
            ate = datetime.combine(date.fromisoformat(filtro_ate), datetime.min.time()) + timedelta(days=1)
            q = q.filter(Ouvidoria.criado_em >= de, Ouvidoria.criado_em < ate)
        if filtro_categoria_id:
            q = q.filter(Ouvidoria.reclamacoes.any(
                Reclamacao.categoria_id == filtro_categoria_id
            ))
        if filtro_subcategoria_id:
            q = q.filter(Ouvidoria.reclamacoes.any(
                Reclamacao.subcategoria_id == filtro_subcategoria_id
            ))
        if filtro_tipo_servico:
            q = q.filter(Ouvidoria.reclamacoes.any(
                Reclamacao.tipo_servico == filtro_tipo_servico
            ))
        ouvidorias = q.order_by(Ouvidoria.criado_em.desc(), Ouvidoria.id.desc()).all()
        return [
            OuvidoriaResumoDict(
                id=o.id,
                protocolo=o.protocolo,
                conteudo=o.conteudo,
                status=o.status.value,
                prazo=o.prazo,
                prazo_permissionaria=o.prazo_permissionaria,
                data_resposta_perm=max(
                    (rp.data_resposta for rp in o.respostas_permissionaria if rp.data_resposta),
                    default=None,
                ),
                criado_em=o.criado_em,
                concluido_em=o.concluido_em,
                atribuicoes=[_to_atribuicao_dict(at) for at in o.atribuicoes],
            )
            for o in ouvidorias
        ]
