"""
Corrige protocolos com sufixo '.0' gravados pelo seed de dados antigos.

O Excel armazenou os números de protocolo como float, então ao exportar para CSV
ficaram no formato "2024121914333021.0". Este script remove o '.0' dos registros
já inseridos no banco.

Uso:
    python database/fix_protocolo_ponto_zero.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api.database.connection import db_session, init_db
from sqlalchemy import text

init_db()

with db_session() as session:
    result = session.execute(text(
        "UPDATE ouvidorias "
        "SET protocolo = LEFT(protocolo, LENGTH(protocolo) - 2) "
        "WHERE protocolo LIKE '%.0'"
    ))
    print(f"{result.rowcount} protocolos corrigidos (sufixo '.0' removido).")
