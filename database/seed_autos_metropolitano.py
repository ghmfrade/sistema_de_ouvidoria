"""Seed de autos metropolitanos e seus trechos (all-pairs).

Fase 1 — Autos:   linhas metropolitanas.xlsx  (Linha, Operadora, Fantasia, Denominação_A/B...)
Fase 2 — Trechos: municipios_GESTEC LINHAS.xlsx  (RM, MUNICÍPIO, LINHA)
           → Para cada linha, gera todos os pares possíveis de municípios (all-pairs)

Regras:
  - Filtrar Situação = "EM OPERAÇÃO"
  - Lookup permissionária por Fantasia em permissionarias.nome_fantasia
    (fallback: lookup por nome normalizado)
  - Invariante de ordem: municipio_a_id < municipio_b_id
"""

import itertools
import os
import re
import sys
import unicodedata

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import db_session
from database.normalize_municipio import construir_indices, normalizar, resolver_municipio_id
from models import AutoLinha, Permissionaria, TrechoAutoLinha, TipoServico

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA_SEED = os.path.join(BASE, "pasta_seed")


def _norm(s: str) -> str:
    """Normalização simples para comparação de strings."""
    s = unicodedata.normalize("NFD", str(s).strip().upper())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s).strip()


def _construir_mapas_permissionarias(session):
    """Retorna (fantasia_map, nome_map) para lookup."""
    perms = session.query(Permissionaria).all()
    fantasia_map = {_norm(p.nome_fantasia): p.id for p in perms if p.nome_fantasia}
    nome_map     = {_norm(p.nome): p.id for p in perms}
    return fantasia_map, nome_map


def seed_autos(session) -> dict[str, int]:
    """Insere autos metropolitanos. Retorna mapa (numero_normalizado, rm_norm)→id."""
    path = os.path.join(PASTA_SEED, "linhas_metropolitano.xlsx")
    df = pd.read_excel(path, header=2, dtype=str)
    df.columns = [c.strip() for c in df.columns]

    # Filtrar apenas linhas em operação e com número válido
    col_sit  = next(c for c in df.columns if "situa" in c.lower() or "Situa" in c)
    col_lin  = next(c for c in df.columns if c.strip() == "Linha")
    col_oper = next(c for c in df.columns if "Operadora" in c or "operadora" in c.lower())
    col_fant = next(c for c in df.columns if "Fantasia" in c or "fantasia" in c.lower())
    col_rm   = next(c for c in df.columns if "Reg_" in c or "Regi" in c)
    col_sub  = next(c for c in df.columns if "Sub" in c or "sub" in c.lower())
    col_da   = next(c for c in df.columns if "Denomina" in c and "_A" in c)
    col_db   = next(c for c in df.columns if "Denomina" in c and "_B" in c)
    col_via  = next((c for c in df.columns if c.strip() == "Via"), None)
    col_serv = next((c for c in df.columns if c.strip() == "Serviço" or "servi" in c.lower()), None)

    df = df[df[col_sit].str.strip().str.upper() == "EM OPERAÇÃO"]
    df = df.dropna(subset=[col_lin])

    fantasia_map, nome_map = _construir_mapas_permissionarias(session)

    inseridos = 0
    sem_perm = 0
    auto_map: dict[tuple[str, str], int] = {}

    for _, row in df.iterrows():
        numero = str(row[col_lin]).strip()
        rm     = str(row[col_rm]).strip() if pd.notna(row[col_rm]) else None
        sub    = str(row[col_sub]).strip() if pd.notna(row[col_sub]) else None

        chave = (numero, _norm(rm) if rm else "")
        if chave in auto_map:
            continue

        fantasia = str(row[col_fant]).strip() if pd.notna(row[col_fant]) else None
        perm_id = fantasia_map.get(_norm(fantasia)) if fantasia else None
        if perm_id is None:
            operadora = str(row[col_oper]).strip() if pd.notna(row[col_oper]) else None
            if operadora:
                perm_id = nome_map.get(_norm(operadora))
        if perm_id is None:
            sem_perm += 1

        da = str(row[col_da]).strip() if pd.notna(row[col_da]) else None
        db = str(row[col_db]).strip() if pd.notna(row[col_db]) else None
        via  = str(row[col_via]).strip() if col_via and pd.notna(row[col_via]) else None
        serv = str(row[col_serv]).strip() if col_serv and pd.notna(row[col_serv]) else None

        auto = AutoLinha(
            numero=numero,
            tipo=TipoServico.REGULAR_METROPOLITANO,
            denominacao_a=da,
            denominacao_b=db,
            via=via,
            servico=serv,
            regiao_metropolitana=rm,
            sub_regiao=sub,
            permissionaria_id=perm_id,
            ativo=True,
        )
        session.add(auto)
        session.flush()
        auto_map[chave] = auto.id
        inseridos += 1

    print(f"  [autos metro] {inseridos} inseridos | {sem_perm} sem permissionária encontrada")
    return auto_map


def seed_trechos(session, auto_map: dict[tuple[str, str], int]) -> None:
    """Insere trechos all-pairs por linha a partir do GESTEC."""
    path = os.path.join(PASTA_SEED, "municipios_por_linha_metropolitano.xlsx")
    df = pd.read_excel(path, header=2, dtype=str)
    df.columns = [c.strip() for c in df.columns]

    col_rm   = next(c for c in df.columns if c.strip() == "RM")
    col_mun  = next(c for c in df.columns if "MUNIC" in c.upper())
    col_lin  = next(c for c in df.columns if c.strip() == "LINHA")
    col_sit  = next((c for c in df.columns if "SITUA" in c.upper()), None)

    if col_sit:
        df = df[df[col_sit].str.strip().str.upper() == "EM OPERAÇÃO"]

    df = df.dropna(subset=[col_lin, col_mun])

    ibge_exact, ibge_norm = construir_indices(session)

    inseridos = 0
    sem_auto = 0
    sem_mun = 0
    conflito = 0
    nao_resolvidos: set[str] = set()

    # Agrupar por (RM, LINHA)
    for (rm_val, lin_val), grupo in df.groupby([col_rm, col_lin]):
        rm_str = str(rm_val).strip()
        lin_str = str(lin_val).strip()
        chave = (lin_str, _norm(rm_str))

        auto_id = auto_map.get(chave)
        if auto_id is None:
            sem_auto += 1
            continue

        # Resolver todos os municípios do grupo
        mun_ids = []
        for mun_nome in grupo[col_mun].unique():
            mun_nome = str(mun_nome).strip()
            mid = resolver_municipio_id(mun_nome, ibge_exact, ibge_norm)
            if mid is None:
                nao_resolvidos.add(mun_nome)
                sem_mun += 1
            else:
                mun_ids.append(mid)

        mun_ids = list(set(mun_ids))  # deduplicate
        if len(mun_ids) < 2:
            continue

        for a_id, b_id in itertools.combinations(sorted(mun_ids), 2):
            existe = session.query(TrechoAutoLinha).filter_by(
                auto_id=auto_id, municipio_a_id=a_id, municipio_b_id=b_id
            ).first()
            if existe:
                conflito += 1
                continue
            t = TrechoAutoLinha(auto_id=auto_id, municipio_a_id=a_id, municipio_b_id=b_id)
            session.add(t)
            inseridos += 1

    if nao_resolvidos:
        print(f"  [WARN] {len(nao_resolvidos)} municípios GESTEC não resolvidos:")
        for nm in sorted(nao_resolvidos):
            print(f"    - {nm!r}")
    print(f"  [trechos metro] {inseridos} inseridos | {sem_auto} sem auto | {sem_mun} registros sem município | {conflito} duplicatas")


def main() -> None:
    print("=== seed_autos_metropolitano ===")
    with db_session() as s:
        auto_map = seed_autos(s)
        seed_trechos(s, auto_map)
        total_autos = s.query(AutoLinha).filter_by(tipo=TipoServico.REGULAR_METROPOLITANO).count()
        total_trechos = s.query(TrechoAutoLinha).count()
    print(f"  Total autos metropolitano: {total_autos}")
    print(f"  Total trechos (acumulado): {total_trechos}")


if __name__ == "__main__":
    main()
