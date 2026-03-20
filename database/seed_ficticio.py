"""
Popula o banco com dados fictícios para testes dos dashboards.
- 5 técnicos distribuídos nas coordenações de GFISC e GPLA
- 7 categorias (mantém as existentes, acrescenta as faltantes)
- ~20 ouvidorias com 1-3 reclamações e 1-3 autos cada
- Autos repetidos entre reclamações para gerar pontuação acumulada significativa

Uso:
    python database/seed_ficticio.py
"""
import sys
import os
import random
from datetime import date, timedelta, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database.connection import get_session, db_session
from models import (
    Usuario, TipoUsuario, Categoria, Ouvidoria, StatusOuvidoria,
    Reclamacao, OuvidoriaTecnico, ReclamacaoAuto, RespostaTecnica,
)
import auth

random.seed(42)

# ── Constantes ────────────────────────────────────────────────────────────────

# Coordenações existentes (confirmadas no banco)
# GFISC: METROPOLITANO=1, INTERMUNICIPAL=2, GPLA: INTERMUNICIPAL=4, METROPOLITANO=5
COORD_MAP = {
    "GFISC/METROPOLITANO": 1,
    "GFISC/INTERMUNICIPAL": 2,
    "GPLA/INTERMUNICIPAL": 4,
    "GPLA/METROPOLITANO": 5,
}
GERENCIA_MAP = {
    "GPLA": 1,
    "GFISC": 2,
}

TECNICOS = [
    {"nome": "Ana Paula Ferreira",   "email": "anapaula@artesp.sp.gov.br",  "coord": "GFISC/METROPOLITANO",  "ger": "GFISC"},
    {"nome": "Carlos Eduardo Lima",  "email": "carlosedu@artesp.sp.gov.br", "coord": "GFISC/INTERMUNICIPAL", "ger": "GFISC"},
    {"nome": "Fernanda Souza",       "email": "fernanda@artesp.sp.gov.br",  "coord": "GFISC/INTERMUNICIPAL", "ger": "GFISC"},
    {"nome": "Roberto Alves",        "email": "roberto@artesp.sp.gov.br",   "coord": "GPLA/INTERMUNICIPAL",  "ger": "GPLA"},
    {"nome": "Mariana Costa",        "email": "mariana@artesp.sp.gov.br",   "coord": "GPLA/METROPOLITANO",   "ger": "GPLA"},
]

CATEGORIAS_NOVAS = [
    ("CONDUTOR", "Reclamações sobre comportamento do condutor"),
    ("ESTADO DO VEÍCULO", "Reclamações sobre conservação e limpeza do veículo"),
    ("COBRADOR", "Reclamações sobre atendimento do cobrador"),
    ("TRAJETO", "Reclamações sobre desvios ou alterações de trajeto"),
    ("TARIFA", "Reclamações sobre cobranças indevidas ou valores incorretos"),
]

CIDADES_EMBARQUE = [
    "São Paulo", "Campinas", "Sorocaba", "Santos", "Ribeirão Preto",
    "São José dos Campos", "Bauru", "Piracicaba", "Jundiaí", "Franca",
]
CIDADES_DESEMBARQUE = [
    "Campinas", "São Paulo", "Guarulhos", "Osasco", "Mauá",
    "Diadema", "São Bernardo do Campo", "Carapicuíba", "Cotia", "Itapevi",
]

PROCESSOS_SEI = [
    "6011.2024.00001-1", "6011.2024.00002-2", "6011.2024.00003-3",
    "6011.2024.00004-4", "6011.2024.00005-5", "6011.2024.00006-6",
    "6011.2024.00007-7", "6011.2024.00008-8", "6011.2024.00009-9",
    "6011.2024.00010-0", "6011.2025.00001-1", "6011.2025.00002-2",
    "6011.2025.00003-3", "6011.2025.00004-4", "6011.2025.00005-5",
    "6011.2025.00006-6", "6011.2025.00007-7", "6011.2025.00008-8",
    "6011.2025.00009-9", "6011.2025.00010-0",
]

DESCRICOES = [
    "Passageiro relata atraso superior a 30 minutos na linha.",
    "Veículo apresentava ar-condicionado com defeito durante o trajeto.",
    "Condutor desembarcou passageiros fora do ponto.",
    "Cobrador cobrou tarifa errada para trecho metropolitano.",
    "Superlotação registrada em horário de pico.",
    "Veículo com bancos danificados e odor desagradável.",
    "Trajeto alterado sem aviso prévio aos passageiros.",
    "Passageiro relata grosseria do cobrador durante viagem.",
    "Atraso de 45 minutos em horário de pico.",
    "Desvio de rota sem sinalização ou comunicação.",
    "Veículo com janelas quebradas comprometendo segurança.",
    "Reclamação sobre falta de condução na linha às 22h.",
]


def _hoje_menos(dias):
    return date.today() - timedelta(days=dias)


def _rand_date(dias_ini, dias_fim):
    d = random.randint(dias_ini, dias_fim)
    return date.today() - timedelta(days=d)


# ── Técnicos ──────────────────────────────────────────────────────────────────
def criar_tecnicos(s):
    tec_ids = []
    for t in TECNICOS:
        existe = s.query(Usuario).filter_by(email=t["email"]).first()
        if not existe:
            u = Usuario(
                nome=t["nome"],
                email=t["email"],
                senha_hash=auth.hash_senha("senha123"),
                tipo=TipoUsuario.tecnico,
                gerencia_id=GERENCIA_MAP[t["ger"]],
                coordenacao_id=COORD_MAP[t["coord"]],
                ativo=True,
            )
            s.add(u)
            s.flush()
            print(f"  Técnico criado: {t['nome']}")
            tec_ids.append(u.id)
        else:
            print(f"  Técnico já existe: {t['nome']}")
            tec_ids.append(existe.id)
    return tec_ids


# ── Categorias ────────────────────────────────────────────────────────────────
def criar_categorias(s):
    cat_ids = []
    # Recupera existentes
    existentes = {c.nome: c.id for c in s.query(Categoria).all()}
    cat_ids.extend(existentes.values())
    for nome, desc in CATEGORIAS_NOVAS:
        if nome not in existentes:
            c = Categoria(nome=nome, descricao=desc)
            s.add(c)
            s.flush()
            print(f"  Categoria criada: {nome}")
            cat_ids.append(c.id)
        else:
            print(f"  Categoria já existe: {nome}")
    return cat_ids


# ── Autos populares ───────────────────────────────────────────────────────────
def buscar_autos_populares(s):
    """Pega os primeiros 20 autos para simular linhas com muitas reclamações."""
    rows = s.execute(text("SELECT id FROM autos_linha ORDER BY id LIMIT 20")).fetchall()
    return [r[0] for r in rows]


# ── Ouvidorias ────────────────────────────────────────────────────────────────
def criar_ouvidorias(s, tec_ids, cat_ids, auto_ids, admin_id):
    statuses_dist = [
        StatusOuvidoria.CONCLUIDO,
        StatusOuvidoria.CONCLUIDO,
        StatusOuvidoria.CONCLUIDO,
        StatusOuvidoria.CONCLUIDO,
        StatusOuvidoria.CONCLUIDO,
        StatusOuvidoria.EM_ANALISE_TECNICA,
        StatusOuvidoria.EM_ANALISE_TECNICA,
        StatusOuvidoria.EM_ANALISE_TECNICA,
        StatusOuvidoria.AGUARDANDO_ACOES,
        StatusOuvidoria.AGUARDANDO_ACOES,
        StatusOuvidoria.AGUARDANDO_PERMISSIONARIA,
        StatusOuvidoria.AGUARDANDO_PERMISSIONARIA,
        StatusOuvidoria.RETORNO_TECNICO,
        StatusOuvidoria.RETORNO_TECNICO,
        # vencidas (prazo passado, não concluídas)
        StatusOuvidoria.EM_ANALISE_TECNICA,
        StatusOuvidoria.AGUARDANDO_ACOES,
        StatusOuvidoria.EM_ANALISE_TECNICA,
        StatusOuvidoria.AGUARDANDO_PERMISSIONARIA,
        StatusOuvidoria.CONCLUIDO,
        StatusOuvidoria.CONCLUIDO,
    ]

    # prazos: os últimos 6 são vencidos
    def _prazo(i, criado_em):
        if i >= 14:  # vencidos
            return criado_em + timedelta(days=random.randint(5, 15))
        if statuses_dist[i] == StatusOuvidoria.CONCLUIDO:
            return criado_em + timedelta(days=random.randint(20, 40))
        return date.today() + timedelta(days=random.randint(5, 30))

    ouvidorias_criadas = 0
    for i, sei in enumerate(PROCESSOS_SEI):
        # Não duplicar SEI
        existe = s.query(Ouvidoria).filter(Ouvidoria.conteudo.like(f"%{sei}%")).first()
        if existe:
            print(f"  Ouvidoria {sei} já existe, pulando.")
            continue

        criado_em = _rand_date(30, 365)
        status = statuses_dist[i % len(statuses_dist)]
        prazo = _prazo(i, criado_em)

        # Gera protocolo fictício baseado na data e índice
        protocolo = f"{criado_em.strftime('%Y%m%d')}{1486000 + i:07d}"

        ouvid = Ouvidoria(
            protocolo=protocolo,
            conteudo=f"Conteúdo da ouvidoria referente ao processo {sei}. Reclamação recebida via sistema de ouvidoria ARTESP sobre serviço de transporte intermunicipal.",
            prazo=prazo,
            status=status,
            criado_por_id=admin_id,
            criado_em=datetime.combine(criado_em, datetime.min.time()),
        )
        s.add(ouvid)
        s.flush()

        # Reclamações (1 a 3)
        n_rec = random.randint(1, 3)
        rec_ids = []
        for item_num in range(1, n_rec + 1):
            cat_id = random.choice(cat_ids)
            emb = random.choice(CIDADES_EMBARQUE)
            desemb = random.choice(CIDADES_DESEMBARQUE)
            desc = random.choice(DESCRICOES)
            rec = Reclamacao(
                ouvidoria_id=ouvid.id,
                numero_item=item_num,
                categoria_id=cat_id,
                local_embarque=emb,
                local_desembarque=desemb,
                descricao=desc,
                criado_em=datetime.combine(criado_em, datetime.min.time()),
            )
            s.add(rec)
            s.flush()
            rec_ids.append(rec.id)

            # Autos por reclamação (1 a 3) — concentrados nos mesmos autos
            n_autos = random.randint(1, 3)
            autos_rec = random.sample(auto_ids[:12], min(n_autos, 12))
            pontuacao = round(1.0 / len(autos_rec), 4)
            for aid in autos_rec:
                s.add(ReclamacaoAuto(reclamacao_id=rec.id, auto_id=aid, pontuacao=pontuacao))

        # Atribuição de técnicos (1 a 2)
        n_tecs = random.randint(1, 2)
        tecs_atr = random.sample(tec_ids, min(n_tecs, len(tec_ids)))
        respondido_final = status in (StatusOuvidoria.CONCLUIDO, StatusOuvidoria.RETORNO_TECNICO)
        for tid in tecs_atr:
            respondido = respondido_final
            resp_em = None
            if respondido:
                resp_em = datetime.combine(criado_em + timedelta(days=random.randint(3, 20)), datetime.min.time())
            s.add(OuvidoriaTecnico(ouvidoria_id=ouvid.id, tecnico_id=tid, respondido=respondido, respondido_em=resp_em))

            # Resposta técnica para ouvidorias concluídas/retorno
            if respondido:
                data_resp = (criado_em + timedelta(days=random.randint(3, 20)))
                s.add(RespostaTecnica(
                    ouvidoria_id=ouvid.id,
                    tecnico_id=tid,
                    data_resposta=data_resp,
                    texto_resposta=f"Resposta técnica referente ao processo {sei}. Verificada a ocorrência e encaminhadas as providências cabíveis à permissionária responsável.",
                    criado_em=datetime.combine(data_resp, datetime.min.time()),
                ))

        ouvidorias_criadas += 1

    print(f"  {ouvidorias_criadas} ouvidorias criadas.")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Populando dados fictícios ===\n")

    with db_session() as s:
        # Admin ID
        admin = s.execute(text("SELECT id FROM usuarios WHERE tipo='gestor' LIMIT 1")).fetchone()
        if not admin:
            print("ERRO: Nenhum gestor encontrado. Execute database/seed.py primeiro.")
            sys.exit(1)
        admin_id = admin[0]
        print(f"Usando gestor id={admin_id}\n")

        print("--- Técnicos ---")
        tec_ids = criar_tecnicos(s)

        print("\n--- Categorias ---")
        cat_ids = criar_categorias(s)

        print("\n--- Buscando autos ---")
        auto_ids = buscar_autos_populares(s)
        print(f"  {len(auto_ids)} autos selecionados para as reclamações.")

        print("\n--- Ouvidorias ---")
        criar_ouvidorias(s, tec_ids, cat_ids, auto_ids, admin_id)

    print("\nConcluído.")
