"""Seed de autos intermunicipais e seus trechos.

Fase 1 — Autos:  Autos de Linha Ativas.csv
Fase 2 — Trechos: trechos_autos_intermunicipal.csv

Regras:
  - Filtrar Característica contendo "Leito" ou "Executivo" (ex e leito são lançamentos fictícios)
  - numero = str(nº Autos).strip() + Iti.strip()   ex: "1A", "7847A"
  - Trechos: apenas pares com CARACTERISTICA NOT IN ("Rodoviário Executivo", "Rodoviário Leito")
  - Invariante de ordem: municipio_a_id < municipio_b_id
"""

import os
import sys
import unicodedata
import re

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import db_session
from database.normalize_municipio import construir_indices, normalizar, resolver_municipio_id
from models import AutoLinha, Permissionaria, TrechoAutoLinha, TipoServico

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA_SEED = os.path.join(BASE, "pasta_seed")

CARACTERISTICAS_EXCLUIR = {"Rodoviário Executivo", "Rodoviário Leito"}


def _normalizar_nome_empresa(nome: str) -> str:
    """Normaliza nome de empresa para lookup de permissionária."""
    s = unicodedata.normalize("NFD", nome.strip().upper())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s).strip()


def _construir_mapa_permissionarias(session) -> dict[str, int]:
    """Retorna {nome_normalizado: id} para lookup por nome."""
    perms = session.query(Permissionaria.id, Permissionaria.nome).all()
    return {_normalizar_nome_empresa(p.nome): p.id for p in perms}


def seed_autos(session) -> dict[str, int]:
    """Insere autos intermunicipais. Retorna mapa numero→id."""
    path = os.path.join(PASTA_SEED, "autos_intermunicipal_ativos.csv")
    df = pd.read_csv(path, sep=";", encoding="latin-1", dtype=str)
    df.columns = [c.strip() for c in df.columns]

    # Identificar colunas (encoding pode variar)
    col_num   = next(c for c in df.columns if "autos" in c.lower() or "n" in c.lower() and "auto" in c.lower())
    col_iti   = next(c for c in df.columns if c.strip().lower() == "iti")
    col_perm  = next(c for c in df.columns if "permiss" in c.lower())
    col_denom = next(c for c in df.columns if "denomina" in c.lower() or "linha" in c.lower())
    col_carac = next(c for c in df.columns if "carac" in c.lower())
    col_tc    = next((c for c in df.columns if c.strip().upper() == "TC"), None)

    perm_map = _construir_mapa_permissionarias(session)

    inseridos = 0
    atualizados = 0
    sem_perm = 0
    numero_map: dict[str, int] = {}

    for _, row in df.iterrows():
        carac = str(row.get(col_carac, "")).strip()
        if any(excl in carac for excl in ("Leito", "Executivo")):
            continue

        num_raw = str(row[col_num]).strip()
        iti     = str(row[col_iti]).strip()
        numero  = num_raw + iti

        if numero in numero_map:
            continue  # já processado (mesmo número duplicado no CSV)

        tc_val = None
        if col_tc:
            try:
                tc_val = int(str(row[col_tc]).strip())
            except (ValueError, TypeError):
                tc_val = None

        # Verificar se auto já existe no banco
        existente = session.query(AutoLinha).filter_by(
            numero=numero, tipo=TipoServico.REGULAR_INTERMUNICIPAL
        ).first()
        if existente:
            existente.tc = tc_val
            numero_map[numero] = existente.id
            atualizados += 1
            continue

        nome_perm = str(row[col_perm]).strip()
        perm_id   = perm_map.get(_normalizar_nome_empresa(nome_perm))
        if perm_id is None:
            sem_perm += 1

        denom = str(row.get(col_denom, "")).strip()

        auto = AutoLinha(
            numero=numero,
            tipo=TipoServico.REGULAR_INTERMUNICIPAL,
            denominacao_a=denom or None,
            denominacao_b=None,
            tc=tc_val,
            permissionaria_id=perm_id,
            ativo=True,
        )
        session.add(auto)
        session.flush()
        numero_map[numero] = auto.id
        inseridos += 1

    print(f"  [autos] {inseridos} inseridos | {atualizados} atualizados (tc) | {sem_perm} sem permissionária encontrada")
    return numero_map


def seed_trechos(session, numero_map: dict[str, int]) -> None:
    """Insere trechos a partir de trechos_autos_intermunicipal.csv."""
    path = os.path.join(PASTA_SEED, "trechos_intermunicipal.csv")
    df = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
    df.columns = [c.strip() for c in df.columns]

    ibge_exact, ibge_norm = construir_indices(session)

    inseridos = 0
    sem_auto = 0
    sem_mun = 0
    conflito = 0

    for _, row in df.iterrows():
        carac = str(row.get("CARACTERISTICA", "")).strip()
        if any(excl in carac for excl in CARACTERISTICAS_EXCLUIR):
            continue

        n_autos   = str(row["N_AUTOS"]).strip()
        cidade_ini = str(row["CIDADE_INI"]).strip()
        cidade_fim = str(row["CIDADE_FIM"]).strip()

        auto_id = numero_map.get(n_autos)
        if auto_id is None:
            sem_auto += 1
            continue

        mun_a = resolver_municipio_id(cidade_ini, ibge_exact, ibge_norm)
        mun_b = resolver_municipio_id(cidade_fim, ibge_exact, ibge_norm)

        if mun_a is None or mun_b is None:
            sem_mun += 1
            if mun_a is None:
                print(f"    [WARN] município não resolvido: {cidade_ini!r}")
            if mun_b is None:
                print(f"    [WARN] município não resolvido: {cidade_fim!r}")
            continue

        if mun_a == mun_b:
            continue  # trecho circular, ignorar

        min_id, max_id = min(mun_a, mun_b), max(mun_a, mun_b)

        # Verificar conflito antes de inserir
        existe = session.query(TrechoAutoLinha).filter_by(
            auto_id=auto_id, municipio_a_id=min_id, municipio_b_id=max_id
        ).first()
        if existe:
            conflito += 1
            continue

        t = TrechoAutoLinha(auto_id=auto_id, municipio_a_id=min_id, municipio_b_id=max_id)
        session.add(t)
        inseridos += 1

    print(f"  [trechos] {inseridos} inseridos | {sem_auto} sem auto | {sem_mun} sem município | {conflito} duplicatas")


def main() -> None:
    print("=== seed_autos_intermunicipal ===")
    with db_session() as s:
        numero_map = seed_autos(s)
        seed_trechos(s, numero_map)
        total_autos = s.query(AutoLinha).filter_by(tipo=TipoServico.REGULAR_INTERMUNICIPAL).count()
        total_trechos = s.query(TrechoAutoLinha).count()
    print(f"  Total autos intermunicipal: {total_autos}")
    print(f"  Total trechos: {total_trechos}")


if __name__ == "__main__":
    main()
