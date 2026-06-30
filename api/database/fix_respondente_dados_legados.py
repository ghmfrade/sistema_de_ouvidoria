"""
Corrige o respondente das ouvidorias de dados antigos.

- Verifica se o usuário 'Dados Legados' já existe (cria se necessário)
- Reatribui respostas_tecnicas e ouvidoria_tecnicos de Eduardo Lotto → Dados Legados

Uso:
    python database/fix_respondente_dados_legados.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import bcrypt
from api.database.connection import db_session, init_db
from api.models import Usuario, TipoUsuario, Gerencia
from sqlalchemy import text

init_db()

with db_session() as session:
    # Verificar/criar Dados Legados
    dados_legados = session.query(Usuario).filter(
        Usuario.nome.ilike("Dados Legados")
    ).first()

    if not dados_legados:
        gplan = session.query(Gerencia).filter(
            Gerencia.nome.ilike("GPLAN")
        ).first()
        if not gplan:
            raise RuntimeError("Gerência 'GPLAN' não encontrada no banco. Verifique o nome correto.")

        senha_hash = bcrypt.hashpw(b"senha_legados@26", bcrypt.gensalt()).decode()
        dados_legados = Usuario(
            nome="Dados Legados",
            email="dados_legados",
            senha_hash=senha_hash,
            tipo=TipoUsuario.tecnico,
            gerencia_id=gplan.id,
            coordenacao_id=None,
            ativo=True,
        )
        session.add(dados_legados)
        session.flush()
        print(f"Usuário 'Dados Legados' criado com id={dados_legados.id}.")
    else:
        print(f"Usuário 'Dados Legados' já existe (id={dados_legados.id}) — nenhuma criação necessária.")

    # Encontrar Eduardo Lotto pelo nome
    eduardo = session.query(Usuario).filter(
        Usuario.nome.ilike("%Eduardo Lotto%")
    ).first()

    if not eduardo:
        print("Usuário 'Eduardo Lotto' não encontrado — nenhuma reatribuição necessária.")
    else:
        print(f"Reatribuindo registros de '{eduardo.nome}' (id={eduardo.id}) para 'Dados Legados' (id={dados_legados.id})...")

        r1 = session.execute(text(
            "UPDATE respostas_tecnicas SET tecnico_id = :novo WHERE tecnico_id = :antigo"
        ), {"novo": dados_legados.id, "antigo": eduardo.id})
        print(f"  {r1.rowcount} respostas_tecnicas reatribuídas.")

        r2 = session.execute(text(
            "UPDATE ouvidoria_tecnicos SET tecnico_id = :novo WHERE tecnico_id = :antigo"
        ), {"novo": dados_legados.id, "antigo": eduardo.id})
        print(f"  {r2.rowcount} ouvidoria_tecnicos reatribuídas.")

print("Concluído.")
