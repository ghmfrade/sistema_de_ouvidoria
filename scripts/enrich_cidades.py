"""
Normaliza ORIGEM e DESTINO do DADOS_ANTIGOS_enriquecido.csv contra a tabela
municipios do banco, adicionando as colunas:
  ORIGEM_IBGE, ORIGEM_cod_IBGE, DESTINO_IBGE, DESTINO_cod_IBGE

Saída:
  - dados_antigos_tratado_empresa_e_cidades.csv  (nesta pasta)
  - ../pasta_seed/dados_antigos_tratado_empresa_e_cidades.csv
  - mun_dados_antigos_not_find.csv  (municípios únicos não encontrados, ignora branco)
"""

import re
import unicodedata
import os
import sys
import pandas as pd

# Adiciona o diretório pai ao path para importar api.*
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from api.database.connection import get_session
from sqlalchemy import text

# Lê/escreve arquivos em normalizacao_dados/ (pasta de dados deste script)
os.chdir(os.path.join(parent_dir, "normalizacao_dados"))


# ── Normalização ──────────────────────────────────────────────────────────────

def normalize(s: str) -> str:
    """Remove acentos, pontuação, espaços extras e coloca em maiúsculo."""
    if not isinstance(s, str):
        return ""
    nfkd = unicodedata.normalize("NFKD", s)
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    sem_acento = sem_acento.upper()
    sem_acento = re.sub(r"[^A-Z0-9\s]", " ", sem_acento)
    return re.sub(r"\s+", " ", sem_acento).strip()


# ── Carrega municípios ────────────────────────────────────────────────────────

def load_municipios() -> pd.DataFrame:
    session = get_session()
    rows = session.execute(
        text("SELECT cod_ibge, nome FROM municipios ORDER BY nome")
    ).fetchall()
    session.close()

    df = pd.DataFrame(rows, columns=["cod_ibge", "nome"])
    df["nome_norm"] = df["nome"].apply(normalize)
    return df


# ── Lookup normalizado: nome_norm → (nome_oficial, cod_ibge) ─────────────────

def build_lookup(mun: pd.DataFrame) -> dict[str, tuple[str, int]]:
    lookup = {}
    for _, row in mun.iterrows():
        key = row["nome_norm"]
        # Se houver duplicata de nome_norm, mantém o primeiro (SP tem precedência
        # pois a tabela está ordenada e todos são SP)
        if key not in lookup:
            lookup[key] = (row["nome"], row["cod_ibge"])
    return lookup


# ── Busca município com estratégias em cascata ────────────────────────────────

def buscar_municipio(
    cidade: str,
    lookup: dict[str, tuple[str, int]],
    mun: pd.DataFrame,
) -> tuple[str, int] | tuple[None, None]:
    """Retorna (nome_ibge, cod_ibge) ou (None, None)."""
    if not isinstance(cidade, str) or not cidade.strip():
        return None, None

    city_norm = normalize(cidade)
    if not city_norm:
        return None, None

    # Estratégia 1: exato normalizado
    if city_norm in lookup:
        return lookup[city_norm]

    # Estratégia 2: cidade está contida no nome cadastrado (único)
    mask = mun["nome_norm"].str.contains(rf"\b{re.escape(city_norm)}\b", na=False)
    if mask.sum() == 1:
        row = mun[mask].iloc[0]
        return row["nome"], row["cod_ibge"]

    # Estratégia 3: nome cadastrado contido na cidade (ex: "São Paulo Capital" → "São Paulo")
    # Itera só nomes com >= 4 chars para evitar falso positivo
    for _, row in mun[mun["nome_norm"].str.len() >= 4].iterrows():
        if row["nome_norm"] in city_norm:
            # Verifica que é palavra inteira (não substring parcial)
            pattern = rf"\b{re.escape(row['nome_norm'])}\b"
            if re.search(pattern, city_norm):
                return row["nome"], row["cod_ibge"]

    # Estratégia 4: remoção de sufixos descritivos comuns e nova tentativa
    # Ex: "São Paulo - Capital", "Guarulhos/SP", "CAMPINAS SP"
    city_clean = re.sub(
        r"\b(CAPITAL|INTERIOR|SP|SAO PAULO|GRANDE|REGIAO|CENTRO)\b", "", city_norm
    )
    city_clean = re.sub(r"[-/\\|].*", "", city_clean)  # remove tudo após separador
    city_clean = re.sub(r"\s+", " ", city_clean).strip()
    if city_clean and city_clean != city_norm and city_clean in lookup:
        return lookup[city_clean]

    # Estratégia 5: startswith compacto (sem espaços)
    city_compact = city_norm.replace(" ", "")
    for key, val in lookup.items():
        key_compact = key.replace(" ", "")
        if key_compact == city_compact:
            return val

    return None, None


# ── Pipeline principal ────────────────────────────────────────────────────────

def enrich_col(
    df: pd.DataFrame,
    col_in: str,
    col_ibge: str,
    col_cod: str,
    lookup: dict,
    mun: pd.DataFrame,
) -> set[str]:
    """Preenche col_ibge e col_cod no df. Retorna conjunto de não encontrados."""
    nao_encontrados = set()
    for idx, val in df[col_in].items():
        if not isinstance(val, str) or not val.strip():
            continue  # branco → ignora
        nome_ibge, cod_ibge = buscar_municipio(val, lookup, mun)
        if nome_ibge:
            df.at[idx, col_ibge] = nome_ibge
            df.at[idx, col_cod]  = cod_ibge
        else:
            nao_encontrados.add(val.strip())
    return nao_encontrados


def main():
    print("Carregando planilha enriquecida...")
    df = pd.read_csv("NOVO_MODELO_enriquecido.csv", dtype={"PROTOCOLO": str}, encoding="utf-8-sig")

    print("Carregando municípios do banco...")
    mun = load_municipios()
    lookup = build_lookup(mun)
    print(f"  {len(mun)} municípios carregados.")

    # Insere as 4 colunas logo após DESTINO
    orig_pos  = df.columns.get_loc("ORIGEM")
    dest_pos  = df.columns.get_loc("DESTINO")

    df.insert(orig_pos + 1, "ORIGEM_IBGE",     "")
    df.insert(orig_pos + 2, "ORIGEM_cod_IBGE", "")

    # DESTINO agora está 2 posições à frente
    dest_pos += 2
    df.insert(dest_pos + 1, "DESTINO_IBGE",     "")
    df.insert(dest_pos + 2, "DESTINO_cod_IBGE", "")

    print("\nNormalizando ORIGEM...")
    nf_orig = enrich_col(df, "ORIGEM",  "ORIGEM_IBGE",  "ORIGEM_cod_IBGE",  lookup, mun)
    orig_ok = df["ORIGEM_IBGE"].replace("", pd.NA).notna().sum()
    print(f"  Encontrados: {orig_ok} / {df['ORIGEM'].notna().sum()}")

    print("Normalizando DESTINO...")
    nf_dest = enrich_col(df, "DESTINO", "DESTINO_IBGE", "DESTINO_cod_IBGE", lookup, mun)
    dest_ok = df["DESTINO_IBGE"].replace("", pd.NA).notna().sum()
    print(f"  Encontrados: {dest_ok} / {df['DESTINO'].notna().sum()}")

    # Salva CSV final em duas localizações
    output_csv = "dados_antigos_tratado_empresa_e_cidades.csv"
    seed_csv = os.path.join(parent_dir, "pasta_seed", "dados_antigos_tratado_empresa_e_cidades.csv")

    df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    print(f"\nArquivo salvo: {output_csv}")

    df.to_csv(seed_csv, index=False, encoding="utf-8-sig")
    print(f"Arquivo salvo: {seed_csv}")

    # Salva não encontrados (união de ORIGEM e DESTINO, sem branco)
    nao_enc = sorted(nf_orig | nf_dest)
    if nao_enc:
        pd.DataFrame({"MUNICIPIO": nao_enc}).to_csv(
            "mun_dados_antigos_not_find.csv", index=False, encoding="utf-8-sig"
        )
        print(f"Municípios não encontrados ({len(nao_enc)}): mun_dados_antigos_not_find.csv")
    else:
        print("Todos os municípios foram identificados!")


if __name__ == "__main__":
    main()
