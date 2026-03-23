"""
Utilitários de normalização de nomes de municípios para mapeamento IBGE.

Usado pelos seeds (seed.py, seed_metropolitano.py) para resolver o municipio_id
de cada cidade presente nos CSVs/Excel de origem.

Estratégias (em ordem de prioridade):
  1. Exato (case-insensitive)
  2. Exceção explícita (EXCECOES) + exato
  3. Normalizado (sem acentos, hífen/apóstrofo → espaço, maiúsculas)
"""

import re
import unicodedata

# ---------------------------------------------------------------------------
# Exceções explícitas
# Chave: versão normalizada do nome no CSV  →  Valor: nome exato no IBGE
# ---------------------------------------------------------------------------
EXCECOES: dict[str, str] = {
    "SANTA BARBARA DO OESTE": "Santa Bárbara d'Oeste",  # CSV não tem apóstrofo
    "FLORINIA": "Flor\u00ednea",                             # CSV tem "Flor\u00ednia" (typo); IBGE: "Flor\u00ednea"
}


def normalizar(s: str) -> str:
    """Maiúsculas + sem acentos + hífen/apóstrofo/crase → espaço, espaços normalizados."""
    s = s.upper().strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")  # remove diacríticos
    s = re.sub(r"[-'`]", " ", s)                                   # pontuação → espaço
    return re.sub(r"\s+", " ", s).strip()


def resolver_municipio_id(
    nome_csv: str,
    ibge_exact: dict[str, tuple[int, str]],
    ibge_norm: dict[str, tuple[int, str]],
) -> int | None:
    """
    Resolve o municipio.id para um nome de cidade vindo do CSV.

    Parâmetros
    ----------
    nome_csv   : nome da cidade conforme está no CSV/Excel
    ibge_exact : {nome.strip().lower() -> (id, nome_ibge)}
    ibge_norm  : {normalizar(nome_ibge) -> (id, nome_ibge)}

    Retorna
    -------
    int com o municipio.id ou None se não encontrado.
    """
    # 1. Exato (case-insensitive)
    k1 = nome_csv.strip().lower()
    if k1 in ibge_exact:
        return ibge_exact[k1][0]

    # 2. Exceção explícita (usando chave normalizada)
    k_norm = normalizar(nome_csv)
    if k_norm in EXCECOES:
        nome_ibge_exc = EXCECOES[k_norm].strip().lower()
        if nome_ibge_exc in ibge_exact:
            return ibge_exact[nome_ibge_exc][0]

    # 3. Normalizado
    if k_norm in ibge_norm:
        return ibge_norm[k_norm][0]

    return None


def construir_indices(session) -> tuple[dict, dict]:
    """
    Constrói os dois índices IBGE a partir da sessão do banco.
    Retorna (ibge_exact, ibge_norm) prontos para uso em resolver_municipio_id().
    """
    from models import Municipio

    rows = session.query(Municipio.id, Municipio.nome).filter_by(estado="SP").all()
    ibge_exact = {r.nome.strip().lower(): (r.id, r.nome) for r in rows}
    ibge_norm = {normalizar(r.nome): (r.id, r.nome) for r in rows}
    return ibge_exact, ibge_norm
