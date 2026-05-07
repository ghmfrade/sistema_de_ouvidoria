from pydantic import BaseModel


class KpisProdutividadeSchema(BaseModel):
    total: int
    concluidas: int
    vencidas: int


class TempoMedioSchema(BaseModel):
    dias: float | None = None


class VolumeItemSchema(BaseModel):
    mes: str
    total: int


class StatusItemSchema(BaseModel):
    status: str
    total: int


class CoordenacaoVencidaSchema(BaseModel):
    coordenacao: str
    total: int


class TecnicoTempoMedioSchema(BaseModel):
    tecnico_nome: str
    dias_medios: float | None = None


class RankingCoordenacaoSchema(BaseModel):
    coordenacao_nome: str
    metrica: float | None = None


# ── Qualidade ─────────────────────────────────────────────────────────────────

class KpisQualidadeSchema(BaseModel):
    total_reclamacoes: int
    pontuacao: float | None = None
    autos_unicos: int


class TopPermissionariaSchema(BaseModel):
    nome: str | None = None
    pontos: float | None = None


class SlaSchema(BaseModel):
    total: int
    dentro_prazo: int


class EvolucaoMensalItemSchema(BaseModel):
    mes: str
    total: int


class AutoPontuacaoSchema(BaseModel):
    auto_numero: str
    pontuacao: float | None = None


class EmpresaPontuacaoSchema(BaseModel):
    empresa: str
    pontos: float | None = None


class CategoriaPizzaSchema(BaseModel):
    categoria: str
    total: int


class CidadeSchema(BaseModel):
    cidade: str
    count: int


class HeatmapItemSchema(BaseModel):
    categoria: str
    empresa: str
    count: int


class TendenciaEmpresaSchema(BaseModel):
    periodo: str
    empresa: str
    valor: float | None = None
