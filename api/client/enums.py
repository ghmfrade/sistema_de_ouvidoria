"""Constantes de domínio para uso no Streamlit — sem importar SQLAlchemy."""

STATUS_OUVIDORIA = [
    "Aguardando ações",
    "Aguardando resposta da permissionária",
    "Em análise técnica",
    "Retorno técnico",
    "Concluído",
]

STATUS_CONCLUIDO               = "Concluído"
STATUS_RETORNO_TECNICO         = "Retorno técnico"
STATUS_EM_ANALISE_TECNICA      = "Em análise técnica"
STATUS_AGUARDANDO_ACOES        = "Aguardando ações"
STATUS_AGUARDANDO_PERMISSIONARIA = "Aguardando resposta da permissionária"

TIPO_SERVICO = [
    "Regular – Metropolitano",
    "Regular – Intermunicipal",
    "Fretamento Metropolitano",
    "Fretamento Intermunicipal",
]

TIPO_USUARIO_GESTOR  = "gestor"
TIPO_USUARIO_TECNICO = "tecnico"
