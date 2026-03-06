"""
Script de importação inicial dos dados dos CSVs e criação do usuário gestor padrão.

Uso:
    python database/seed.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from database.connection import init_db, db_session, get_session
from models import Permissionaria, AutoLinha, ParadaAutoLinha, Usuario, TipoUsuario
import auth

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_ATIVAS = os.path.join(BASE_DIR, "Autos de Linha Ativas.csv")
CSV_PONTOS = os.path.join(BASE_DIR, "Pontos dos Autos de linha.csv")


def _col(df, *candidates):
    """Retorna o primeiro nome de coluna que existe no DataFrame (busca case-insensitive)."""
    lower_map = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand in df.columns:
            return cand
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    return None


def truncar_dados():
    """Remove todos os autos, paradas e permissionárias existentes."""
    from sqlalchemy import text
    session = get_session()
    try:
        session.execute(text("DELETE FROM reclamacao_autos"))
        session.execute(text("DELETE FROM paradas_auto_linha"))
        session.execute(text("DELETE FROM autos_linha"))
        session.execute(text("DELETE FROM permissionarias"))
        session.commit()
        print("  Dados anteriores removidos.")
    finally:
        session.close()


def importar_autos():
    """Lê os CSVs e popula permissionarias, autos_linha e paradas_auto_linha."""
    print(f"Lendo {os.path.basename(CSV_ATIVAS)}...")
    df_ativas = pd.read_csv(CSV_ATIVAS, sep=";", dtype=str, encoding="latin-1")
    df_ativas = df_ativas.dropna(how="all")

    print(f"Lendo {os.path.basename(CSV_PONTOS)}...")
    df_pontos = pd.read_csv(CSV_PONTOS, sep=";", dtype=str, encoding="latin-1")
    df_pontos = df_pontos.dropna(how="all")

    # Detecta colunas no CSV de ativas
    col_n_autos = _col(df_ativas, "n° Autos", "n\u00ba Autos", "n\u00b0 Autos", "n Autos") or df_ativas.columns[0]
    col_iti = _col(df_ativas, "Iti") or "Iti"
    col_perm = _col(df_ativas, "Permissionária", "Permissionaria", "Permission\u00e1ria") or \
               next((c for c in df_ativas.columns if "permiss" in c.lower()), None)
    col_denom = _col(df_ativas, "Denominação da Linha", "Denomina\u00e7\u00e3o da Linha") or \
                next((c for c in df_ativas.columns if "denom" in c.lower()), None)

    # Detecta colunas no CSV de pontos
    col_p_autos = _col(df_pontos, "Autos") or "Autos"
    col_p_iti = _col(df_pontos, "Itinerario", "Itinerário") or "Itinerario"
    col_p_cidade_ini = _col(df_pontos, "Cidade Inicial da linha", "Cidade_Origem") or \
                       next((c for c in df_pontos.columns if "inicial" in c.lower()), None)
    col_p_cidade_fim = _col(df_pontos, "Cidade Fim da linha", "Cidade_Destino") or \
                       next((c for c in df_pontos.columns if "fim" in c.lower()), None)
    col_p_cidade_at = _col(df_pontos, "Cidade Atendida") or \
                      next((c for c in df_pontos.columns if "atendida" in c.lower()), None)

    print(f"  Colunas Ativas: n_autos={col_n_autos!r}, iti={col_iti!r}, perm={col_perm!r}, denom={col_denom!r}")
    print(f"  Colunas Pontos: autos={col_p_autos!r}, iti={col_p_iti!r}, cidade_at={col_p_cidade_at!r}")

    # Normaliza o CSV de ativas
    df_ativas = df_ativas.rename(columns={col_n_autos: "n_autos", col_iti: "iti"})
    df_ativas["n_autos"] = df_ativas["n_autos"].str.strip()
    df_ativas["iti"] = df_ativas["iti"].str.strip()
    if col_denom:
        df_ativas = df_ativas.rename(columns={col_denom: "denominacao"})
    if col_perm:
        df_ativas = df_ativas.rename(columns={col_perm: "permissionaria"})

    # Gera número do auto: "0001" + "A" → "0001-A"
    def formatar_numero(n_autos, iti):
        try:
            n = int(str(n_autos).strip())
            return f"{n:04d}-{str(iti).strip()}"
        except (ValueError, TypeError):
            return None

    df_ativas["numero"] = df_ativas.apply(
        lambda r: formatar_numero(r["n_autos"], r["iti"]), axis=1
    )
    df_ativas = df_ativas.dropna(subset=["numero"])
    df_ativas = df_ativas[~df_ativas["numero"].str.lower().isin(["nan", "none", ""])]

    print(f"  Total de autos no CSV Ativas: {len(df_ativas)}")

    # Normaliza CSV de pontos
    df_pontos = df_pontos.rename(columns={col_p_autos: "n_autos", col_p_iti: "iti"})
    df_pontos["n_autos"] = df_pontos["n_autos"].str.strip()
    df_pontos["iti"] = df_pontos["iti"].str.strip()

    # Deduplica pontos por (n_autos, iti, cidade_atendida)
    if col_p_cidade_at:
        df_pontos = df_pontos.rename(columns={col_p_cidade_at: "cidade_atendida"})
    if col_p_cidade_ini:
        df_pontos = df_pontos.rename(columns={col_p_cidade_ini: "cidade_inicial"})
    if col_p_cidade_fim:
        df_pontos = df_pontos.rename(columns={col_p_cidade_fim: "cidade_final"})

    # Pega cidade_inicial/cidade_final por (n_autos, iti) — primeiro registro
    cols_cid = ["n_autos", "iti"]
    extra_cols = [c for c in ["cidade_inicial", "cidade_final"] if c in df_pontos.columns]
    df_cid = df_pontos[cols_cid + extra_cols].drop_duplicates(subset=["n_autos", "iti"])
    df_cid = df_cid.set_index(["n_autos", "iti"])

    with db_session() as session:
        # Importa permissionárias
        permissionarias_map: dict[str, int] = {}
        if "permissionaria" in df_ativas.columns:
            nomes = df_ativas["permissionaria"].dropna().str.strip().unique()
            for nome in sorted(nomes):
                if not nome or nome.lower() in ("nan", "none", ""):
                    continue
                perm = session.query(Permissionaria).filter_by(nome=nome).first()
                if not perm:
                    perm = Permissionaria(nome=nome)
                    session.add(perm)
                    session.flush()
                permissionarias_map[nome] = perm.id
            print(f"  {len(permissionarias_map)} permissionárias importadas.")

        # Importa autos
        autos_criados = 0
        numeros_vistos: dict[str, int] = {}  # numero → auto_id

        for _, row in df_ativas.iterrows():
            numero = row["numero"]
            if numero in numeros_vistos:
                continue

            perm_id = None
            if "permissionaria" in df_ativas.columns and pd.notna(row.get("permissionaria")):
                perm_nome = str(row["permissionaria"]).strip()
                perm_id = permissionarias_map.get(perm_nome)

            itinerario = None
            if "denominacao" in df_ativas.columns and pd.notna(row.get("denominacao")):
                itinerario = str(row["denominacao"]).strip()

            # Busca cidade_inicial/final do CSV de pontos
            n_autos_key = str(row["n_autos"]).strip()
            iti_key = str(row["iti"]).strip()
            cidade_ini = None
            cidade_fim = None
            try:
                row_cid = df_cid.loc[(n_autos_key, iti_key)]
                if "cidade_inicial" in df_cid.columns:
                    v = row_cid["cidade_inicial"]
                    cidade_ini = str(v).strip() if pd.notna(v) else None
                if "cidade_final" in df_cid.columns:
                    v = row_cid["cidade_final"]
                    cidade_fim = str(v).strip() if pd.notna(v) else None
            except KeyError:
                pass

            auto = AutoLinha(
                numero=numero,
                itinerario=itinerario,
                cidade_inicial=cidade_ini,
                cidade_final=cidade_fim,
                permissionaria_id=perm_id,
            )
            session.add(auto)
            session.flush()
            numeros_vistos[numero] = auto.id
            autos_criados += 1

        print(f"  {autos_criados} autos criados.")

        # Importa paradas
        if "cidade_atendida" in df_pontos.columns:
            # Monta mapa n_autos+iti → numero
            ativas_map: dict[tuple, str] = {}
            for _, r in df_ativas.iterrows():
                ativas_map[(r["n_autos"], r["iti"])] = r["numero"]

            paradas_criadas = 0
            vistos: set[tuple] = set()  # (auto_id, cidade)

            for _, row in df_pontos.iterrows():
                n_autos_k = str(row["n_autos"]).strip()
                iti_k = str(row["iti"]).strip()
                numero = ativas_map.get((n_autos_k, iti_k))
                if not numero:
                    continue
                auto_id = numeros_vistos.get(numero)
                if not auto_id:
                    continue

                cidade = str(row["cidade_atendida"]).strip() if pd.notna(row.get("cidade_atendida")) else None
                if not cidade or cidade.lower() in ("nan", "none", ""):
                    continue

                chave = (auto_id, cidade)
                if chave in vistos:
                    continue
                vistos.add(chave)

                session.add(ParadaAutoLinha(auto_id=auto_id, cidade=cidade))
                paradas_criadas += 1

            print(f"  {paradas_criadas} paradas criadas.")
        else:
            print("  Coluna 'Cidade Atendida' não encontrada — paradas não importadas.")


def create_admin(email: str = "admin@artesp.sp.gov.br", senha: str = "admin123", nome: str = "Administrador"):
    """Cria um usuário gestor inicial caso não exista."""
    with db_session() as session:
        existe = session.query(Usuario).filter_by(email=email).first()
        if existe:
            print(f"Usuário {email} já existe.")
            return
        usuario = Usuario(
            nome=nome,
            email=email,
            senha_hash=auth.hash_senha(senha),
            tipo=TipoUsuario.gestor,
            ativo=True,
        )
        session.add(usuario)
    print(f"Usuário gestor criado: {email} / senha: {senha}")
    print("ATENÇÃO: Altere a senha após o primeiro login!")


if __name__ == "__main__":
    print("=== Inicializando banco de dados ===")
    init_db()
    print()
    print("=== Removendo dados anteriores ===")
    truncar_dados()
    print()
    print("=== Importando Autos de Linha ===")
    importar_autos()
    print()
    print("=== Criando usuário gestor padrão ===")
    create_admin()
    print()
    print("Concluído.")
