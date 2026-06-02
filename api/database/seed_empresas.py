"""Seed de permissionárias com CNPJ.

Fontes:
  - EMPRESAS SIGA.xlsx      → intermunicipais (Permissionária, CNPJ)
  - FROTA METROPOLITANO.xlsx → metropolitanas  (Nome, Fantasia, CNPJ)

Lógica de upsert por CNPJ:
  - SIGA:  insere nome=Permissionária, nome_fantasia=None
  - FROTA: insere nome=Nome, nome_fantasia=Fantasia
  - Se CNPJ do FROTA já existe (veio do SIGA): atualiza nome_fantasia se ainda ausente
"""

import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api.database.connection import db_session
from api.models import Permissionaria

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PASTA_SEED = os.path.join(BASE, "pasta_seed")


def _normalizar_cnpj(val) -> str | None:
    """Remove tudo que não é dígito; retorna None se não tiver 14 dígitos."""
    digits = re.sub(r"\D", "", str(val))
    return digits if len(digits) == 14 else None


def _normalizar_nome(val) -> str:
    return str(val).strip()


def seed_siga(session) -> dict[str, int]:
    """Insere empresas intermunicipais. Retorna mapa cnpj→id."""
    path = os.path.join(PASTA_SEED, "empresas_intermunicipal_siga.xlsx")
    df = pd.read_excel(path, header=1)
    df.columns = [str(c).strip() for c in df.columns]

    # Coluna pode aparecer com encoding variado
    col_nome = next(c for c in df.columns if "permission" in c.lower() or "Permission" in c)
    col_cnpj = next(c for c in df.columns if "cnpj" in c.lower() or "CNPJ" in c)

    inseridos = 0
    ignorados = 0
    cnpj_map: dict[str, int] = {}

    for _, row in df.iterrows():
        cnpj = _normalizar_cnpj(row[col_cnpj])
        nome = _normalizar_nome(row[col_nome])
        if not cnpj or not nome or nome.upper() in ("NAN", ""):
            ignorados += 1
            continue

        existente = session.query(Permissionaria).filter_by(cnpj=cnpj).first()
        if existente:
            cnpj_map[cnpj] = existente.id
        else:
            p = Permissionaria(nome=nome, cnpj=cnpj, nome_fantasia=None)
            session.add(p)
            session.flush()
            cnpj_map[cnpj] = p.id
            inseridos += 1

    print(f"  [SIGA] {inseridos} inseridas, {ignorados} ignoradas (CNPJ inválido/vazio)")
    return cnpj_map


def seed_frota(session, cnpj_map: dict[str, int]) -> None:
    """Insere/atualiza empresas metropolitanas."""
    path = os.path.join(PASTA_SEED, "empresas_metropolitano_frota.xlsx")
    df = pd.read_excel(path, header=2)
    df.columns = [str(c).strip() for c in df.columns]

    col_nome    = next(c for c in df.columns if c.strip() == "Nome")
    col_fantasia = next(c for c in df.columns if c.strip() == "Fantasia")
    col_cnpj    = next(c for c in df.columns if c.strip() == "CNPJ")

    # Deduplicate por CNPJ (keep first)
    df_unique = (
        df[[col_cnpj, col_nome, col_fantasia]]
        .dropna(subset=[col_cnpj])
        .drop_duplicates(subset=[col_cnpj])
    )

    inseridos = 0
    atualizados = 0
    ignorados = 0

    for _, row in df_unique.iterrows():
        cnpj = _normalizar_cnpj(row[col_cnpj])
        nome = _normalizar_nome(row[col_nome]) if pd.notna(row[col_nome]) else None
        fantasia = _normalizar_nome(row[col_fantasia]) if pd.notna(row[col_fantasia]) else None

        if not cnpj or not nome:
            ignorados += 1
            continue

        existente = session.query(Permissionaria).filter_by(cnpj=cnpj).first()
        if existente:
            if not existente.nome_fantasia and fantasia:
                existente.nome_fantasia = fantasia
                atualizados += 1
        else:
            p = Permissionaria(nome=nome, cnpj=cnpj, nome_fantasia=fantasia)
            session.add(p)
            session.flush()
            inseridos += 1

    print(f"  [FROTA] {inseridos} inseridas, {atualizados} atualizadas (fantasia), {ignorados} ignoradas")


def main() -> None:
    print("=== seed_empresas ===")
    with db_session() as s:
        cnpj_map = seed_siga(s)
        seed_frota(s, cnpj_map)
        total = s.query(Permissionaria).count()
    print(f"  Total permissionárias no banco: {total}")


if __name__ == "__main__":
    main()
