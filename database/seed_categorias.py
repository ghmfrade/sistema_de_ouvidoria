"""
Importa categorias e subcategorias do CATEGORIAS.xlsx para o banco.

Uso:
    python database/seed_categorias.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from database.connection import init_db, db_session, get_session
from models import Categoria, Subcategoria
from sqlalchemy import text

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XLSX = os.path.join(BASE_DIR, "CATEGORIAS.xlsx")


def truncar_categorias():
    session = get_session()
    try:
        session.execute(text("TRUNCATE TABLE subcategorias RESTART IDENTITY CASCADE"))
        session.execute(text("TRUNCATE TABLE categorias RESTART IDENTITY CASCADE"))
        session.commit()
        print("  Dados anteriores de categorias/subcategorias removidos.")
    finally:
        session.close()


def importar_categorias():
    print(f"Lendo {os.path.basename(XLSX)}...")
    df = pd.read_excel(XLSX)
    df.columns = [c.strip() for c in df.columns]
    df = df.dropna(how="all")

    categorias_unicas = df["CATEGORIA"].dropna().unique()
    print(f"  Categorias encontradas: {len(categorias_unicas)}")
    print(f"  Subcategorias encontradas: {len(df)}")

    with db_session() as session:
        # Insere categorias e guarda referência id
        cat_map: dict[str, int] = {}
        for nome_cat in sorted(categorias_unicas):
            nome_cat = str(nome_cat).strip()
            cat = Categoria(nome=nome_cat)
            session.add(cat)
            session.flush()
            cat_map[nome_cat] = cat.id

        # Insere subcategorias
        for _, row in df.iterrows():
            nome_sub = str(row["SUBCATEGORIA"]).strip()
            nome_cat = str(row["CATEGORIA"]).strip()
            cat_id = cat_map.get(nome_cat)
            if cat_id is None:
                print(f"  [AVISO] Categoria '{nome_cat}' não encontrada para subcategoria '{nome_sub}' — pulando.")
                continue
            session.add(Subcategoria(nome=nome_sub, categoria_id=cat_id))

    print(f"  {len(categorias_unicas)} categorias e {len(df)} subcategorias importadas.")


if __name__ == "__main__":
    print("=== Inicializando banco ===")
    init_db()
    print()
    print("=== Removendo categorias/subcategorias anteriores ===")
    truncar_categorias()
    print()
    print("=== Importando Categorias e Subcategorias ===")
    importar_categorias()
    print()
    print("Concluído.")
