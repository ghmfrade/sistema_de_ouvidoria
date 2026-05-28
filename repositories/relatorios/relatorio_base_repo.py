from datetime import date
from sqlalchemy import cast, Date, func
from models.ouvidoria import Ouvidoria, StatusOuvidoria
from models.reclamacao import Reclamacao
from models.auto_linha import AutoLinha
from models.associations import ReclamacaoAuto
from models.categoria import Categoria
from models.subcategoria import Subcategoria
from models.permissionaria import Permissionaria
from models.resposta_tecnica import RespostaTecnica
from database.connection import db_session


def get_relatorio_base(data_ini: date, data_fim: date) -> list[dict]:
    """
    Retorna lista de dicts desnormalizados: uma linha por (ouvidoria, reclamacao, auto).
    """
    with db_session() as s:
        # Subquery para primeira resposta técnica por ouvidoria
        primeira_resposta_sq = (
            s.query(
                RespostaTecnica.ouvidoria_id,
                func.min(RespostaTecnica.data_resposta).label("data_resposta")
            )
            .group_by(RespostaTecnica.ouvidoria_id)
            .subquery()
        )

        # Query principal: JOIN ouvidoria → reclamacao → reclamacao_autos → auto_linha
        q = (
            s.query(
                Ouvidoria.id,
                Ouvidoria.protocolo,
                Ouvidoria.status,
                Ouvidoria.criado_em.label("data_entrada"),
                primeira_resposta_sq.c.data_resposta.label("data_1a_resposta_tecnica"),
                Ouvidoria.concluido_em.label("data_conclusao"),
                Reclamacao.id.label("id_reclamacao"),
                Categoria.nome.label("categoria"),
                Subcategoria.nome.label("assunto"),
                Reclamacao.local_embarque.label("cidade_origem"),
                Reclamacao.local_desembarque.label("cidade_destino"),
                AutoLinha.numero.label("n_autos"),
                AutoLinha.denominacao_a.label("origem"),
                AutoLinha.denominacao_b.label("destino"),
                Permissionaria.nome.label("permissionaria"),
                ReclamacaoAuto.pontuacao,
            )
            .join(Reclamacao, Ouvidoria.id == Reclamacao.ouvidoria_id)
            .join(ReclamacaoAuto, Reclamacao.id == ReclamacaoAuto.reclamacao_id)
            .join(AutoLinha, ReclamacaoAuto.auto_id == AutoLinha.id)
            .outerjoin(Categoria, Reclamacao.categoria_id == Categoria.id)
            .outerjoin(Subcategoria, Reclamacao.subcategoria_id == Subcategoria.id)
            .outerjoin(Permissionaria, AutoLinha.permissionaria_id == Permissionaria.id)
            .outerjoin(primeira_resposta_sq, Ouvidoria.id == primeira_resposta_sq.c.ouvidoria_id)
            .filter(cast(Ouvidoria.criado_em, Date).between(data_ini, data_fim))
            .order_by(Ouvidoria.id, Reclamacao.numero_item, AutoLinha.numero)
        )

        rows = q.all()

        # Converter para list de dicts
        result = []
        for row in rows:
            result.append({
                "id": row.id,
                "protocolo": row.protocolo,
                "status": row.status.value if row.status else None,
                "data_entrada": row.data_entrada,
                "data_1a_resposta_tecnica": row.data_1a_resposta_tecnica,
                "data_conclusao": row.data_conclusao,
                "id_reclamacao": row.id_reclamacao,
                "categoria": row.categoria,
                "assunto": row.assunto,
                "cidade_origem": row.cidade_origem,
                "cidade_destino": row.cidade_destino,
                "n_autos": row.n_autos,
                "origem": row.origem,
                "destino": row.destino,
                "permissionaria": row.permissionaria,
                "pontuacao": row.pontuacao,
            })

        return result
