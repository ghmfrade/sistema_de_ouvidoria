"""
Cria o banco de dados 'sistema_de_ouvidoria' no servidor PostgreSQL caso não exista.

Conecta ao banco administrativo 'pgsql-sandbox' (banco existente no servidor) e emite
CREATE DATABASE. Deve ser executado antes de rodar as migrations pela primeira vez.

Uso:
    python database/create_db.py
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

HOST = os.getenv("POSTGRES_HOST", "localhost")
PORT = os.getenv("POSTGRES_PORT", "5432")
USER = os.getenv("POSTGRES_USER", "postgres")
PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
TARGET_DB = os.getenv("POSTGRES_DB", "sistema_de_ouvidoria")
ADMIN_DB = "postgres"  # banco admin padrão do servidor usado para conexão inicial

conn = psycopg2.connect(
    host=HOST,
    port=PORT,
    user=USER,
    password=PASSWORD,
    dbname=ADMIN_DB,
)
conn.autocommit = True
cur = conn.cursor()

cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (TARGET_DB,))
if cur.fetchone():
    print(f"Banco '{TARGET_DB}' já existe — nenhuma ação necessária.")
else:
    cur.execute(f'CREATE DATABASE "{TARGET_DB}"')
    print(f"Banco '{TARGET_DB}' criado com sucesso.")

cur.close()
conn.close()
