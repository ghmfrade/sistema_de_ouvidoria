from fastapi import APIRouter, Depends

from api.deps import usuario_corrente
from api.repositories.marcacao_repo import get_legenda, salvar_legenda
from api.schemas.marcacao import LegendaItemSchema, SalvarLegendaRequest

router = APIRouter()


@router.get("/legenda", response_model=list[LegendaItemSchema])
def obter_legenda(payload: dict = Depends(usuario_corrente)):
    return get_legenda(int(payload["sub"]))


@router.put("/legenda")
def atualizar_legenda(body: SalvarLegendaRequest, payload: dict = Depends(usuario_corrente)):
    salvar_legenda(
        int(payload["sub"]),
        [{"cor": i.cor.value, "rotulo": i.rotulo} for i in body.itens],
    )
    return {"ok": True}
