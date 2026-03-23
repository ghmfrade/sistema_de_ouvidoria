"""
Runner que executa todos os seeds na ordem correta.

Ordem obrigatória:
  1. seed_municipios.py  — tabela municipios (IBGE) deve existir antes das paradas
  2. seed.py             — autos intermunicipais + paradas com municipio_id
  3. seed_metropolitano.py — autos metropolitanos + paradas com municipio_id

Uso:
    python database/seed_all.py
"""
import subprocess
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SEEDS = [
    "seed_municipios.py",
    "seed.py",
    "seed_metropolitano.py",
]

for script in SEEDS:
    path = os.path.join(BASE_DIR, script)
    print(f"\n{'='*60}")
    print(f">>> Executando: {script}")
    print(f"{'='*60}")
    result = subprocess.run([sys.executable, path], check=False)
    if result.returncode != 0:
        print(f"\n[ERRO] Falha em {script} (codigo {result.returncode}). Abortando.")
        sys.exit(result.returncode)

print(f"\n{'='*60}")
print("Todos os seeds executados com sucesso.")
print(f"{'='*60}")
