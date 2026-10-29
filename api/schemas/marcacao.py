from pydantic import BaseModel, Field

from api.models.marcacao import CorMarcacao


# ── Response schemas ──────────────────────────────────────
class LegendaItemSchema(BaseModel):
    cor: str
    rotulo: str

    model_config = {"from_attributes": True}


# ── Request schemas ───────────────────────────────────────
class DefinirMarcacaoRequest(BaseModel):
    cor: CorMarcacao


class LegendaItemRequest(BaseModel):
    cor: CorMarcacao
    rotulo: str = Field(max_length=40)


class SalvarLegendaRequest(BaseModel):
    itens: list[LegendaItemRequest]
