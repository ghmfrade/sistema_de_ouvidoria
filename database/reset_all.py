"""
Reseta o banco completamente (DROP + CREATE de todas as tabelas) e
executa todos os seeds na ordem correta.

ATENÇÃO: todos os dados existentes serão apagados permanentemente.

Uso:
    python database/reset_all.py
"""
import subprocess
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import engine, init_db
from models import Base  # noqa: F401 – garante que todos os models são carregados

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SEEDS = [
    "seed_municipios.py",
    "seed_empresas.py",
    "seed_autos_intermunicipal.py",
    "seed_autos_metropolitano.py",
    "seed_usuarios.py",
    "seed_categorias.py",
]


def reset_banco():
    print("=== Apagando todas as tabelas (DROP ALL) ===")
    Base.metadata.drop_all(bind=engine)
    print("  Tabelas removidas.")
    print()
    print("=== Recriando todas as tabelas (CREATE ALL) ===")
    Base.metadata.create_all(bind=engine)
    print("  Tabelas criadas.")


if __name__ == "__main__":
    reset_banco()

    for script in SEEDS:
        path = os.path.join(BASE_DIR, script)
        print()
        print(f"{'='*60}")
        print(f">>> Executando: {script}")
        print(f"{'='*60}")
        result = subprocess.run([sys.executable, path], check=False)
        if result.returncode != 0:
            print(f"\n[ERRO] Falha em {script} (codigo {result.returncode}). Abortando.")
            sys.exit(result.returncode)

    print()
    print(f"{'='*60}")
    print("Reset e seed completos.")
    print(f"{'='*60}")
