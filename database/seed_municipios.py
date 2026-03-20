"""
Importa municípios do CSV pop_municipios.csv para a tabela municipios.

Uso:
    python database/seed_municipios.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from database.connection import init_db, db_session, get_session
from models import Municipio
from sqlalchemy import text

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_POP = os.path.join(BASE_DIR, "pop_municipios.csv")


def truncar_municipios():
    session = get_session()
    try:
        session.execute(text("DELETE FROM municipios"))
        session.commit()
        print("  Dados anteriores de municípios removidos.")
    finally:
        session.close()


def importar_municipios():
    print(f"Lendo {os.path.basename(CSV_POP)}...")
    df = pd.read_csv(CSV_POP, dtype={"cod_municipio": int, "populacao_residente": int})
    df = df.dropna(how="all")

    print(f"  Total de municípios no CSV: {len(df)}")

    with db_session() as session:
        criados = 0
        for _, row in df.iterrows():
            cod = int(row["cod_municipio"])
            nome = str(row["nome_municipio"]).strip()
            estado = str(row["estado"]).strip()
            pop = int(row["populacao_residente"])

            session.add(Municipio(
                cod_ibge=cod,
                nome=nome,
                estado=estado,
                populacao=pop,
            ))
            criados += 1

        print(f"  {criados} municípios importados.")


if __name__ == "__main__":
    print("=== Inicializando banco de dados ===")
    init_db()
    print()
    print("=== Removendo municípios anteriores ===")
    truncar_municipios()
    print()
    print("=== Importando Municípios ===")
    importar_municipios()
    print()
    print("Concluído.")
