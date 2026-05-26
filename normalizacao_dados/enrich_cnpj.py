"""
Enriquece DADOS ANTIGOS.xlsx com CNPJ das permissionarias.
Para linhas sem CNPJ, tenta casar o campo EMPRESA com nome ou nome_fantasia
usando múltiplas estratégias de normalização.

Saída:
  - DADOS_ANTIGOS_enriquecido.csv  → dados com CNPJs + colunas do banco (CSV para preservar PROTOCOLO como texto)
  - nao_encontrados.csv            → empresas únicas não identificadas
"""

import re
import unicodedata
import os
import sys
import pandas as pd

# Adiciona o diretório pai ao path para importar database
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from database.connection import get_session
from sqlalchemy import text

# Muda para o diretório do script para ler/escrever arquivos
os.chdir(script_dir)

# ── Overrides manuais: chave = normalize(EMPRESA), valor = CNPJ exato ─────────
# Casos ambíguos ou com múltiplas empresas no campo que foram confirmados manualmente.
OVERRIDES: dict[str, str] = {
    # EMPRESA no xlsx              : CNPJ da permissionária correta
    "BREDA":                                    "05160935000159",  # BREDA TRANSPORTES E SERVIÇOS S/A
    "EXPRESSO DE PRATA ANDORINHA EXPRESSO ADAMANTINA REUNIDAS PAULISTA MOTTA": "45007937000127",  # EXPRESSO DE PRATA LTDA
    "VIACAO PRINCESA EXPRESSO DE PRATA":        "45007937000127",  # EXPRESSO DE PRATA LTDA
    "ITAMARATI LUWASA":                         "59965038000141",  # EXPRESSO ITAMARATI S/A
    "ITAMARATI LUWASA PARATY CRUZ":             "59965038000141",  # EXPRESSO ITAMARATI S/A
    "VIACAO PRINCESA E EXPRESSO DE PRATA":      "45007937000127",  # EXPRESSO DE PRATA LTDA
    "VIACAO NOSSA SENHORA DE FATIMA":           "45606720000133",  # NOSSA SENHORA DE FATIMA AUTO ÔNIBUS LTDA
}


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


def normalize_compact(s: str) -> str:
    return normalize(s).replace(" ", "")


SUFIXOS = [
    "LTDA", "SA", "S A", "EPP", "ME", "EIRELI", "SS", "SCA",
    "LIMITADA", "SOCIEDADE ANONIMA", "TRANSPORTES", "TURISMO",
    "VIACAO", "ONIBUS", "AUTOCARRO", "TRANSPORTE",
]

def remove_sufixos(s: str) -> str:
    normed = normalize(s)
    for suf in sorted(SUFIXOS, key=len, reverse=True):
        normed = re.sub(rf"\b{re.escape(suf)}\b", " ", normed)
    return re.sub(r"\s+", " ", normed).strip()


# ── Carrega permissionarias ───────────────────────────────────────────────────

def load_permissionarias() -> pd.DataFrame:
    session = get_session()
    rows = session.execute(
        text("SELECT cnpj, nome, nome_fantasia FROM permissionarias")
    ).fetchall()
    session.close()

    df = pd.DataFrame(rows, columns=["cnpj", "nome", "nome_fantasia"])

    for col in ("nome", "nome_fantasia"):
        df[f"{col}_norm"]    = df[col].apply(normalize)
        df[f"{col}_compact"] = df[col].apply(normalize_compact)
        df[f"{col}_sem_suf"] = df[col].apply(remove_sufixos)

    return df


# ── Lookup reverso: CNPJ → (nome, nome_fantasia) ─────────────────────────────

def build_cnpj_lookup(perm: pd.DataFrame) -> dict[str, tuple[str, str]]:
    lookup = {}
    for _, row in perm.iterrows():
        lookup[row["cnpj"]] = (row["nome"] or "", row["nome_fantasia"] or "")
    return lookup


# ── Estratégias de busca ──────────────────────────────────────────────────────

STOP = {"DE", "DA", "DO", "DAS", "DOS", "E", "A", "O", "AS", "OS", "EM", "NO", "NA"}


def buscar_cnpj(empresa: str, perm: pd.DataFrame) -> str | None:
    """
    Tenta casar `empresa` com as permissionarias usando estratégias em cascata.
    Retorna o CNPJ cru (14 dígitos) ou None.
    """
    if not isinstance(empresa, str) or not empresa.strip():
        return None

    emp_norm    = normalize(empresa)
    emp_compact = normalize_compact(empresa)
    emp_sem_suf = remove_sufixos(empresa)

    # Override manual (chave já normalizada)
    if emp_norm in OVERRIDES:
        return OVERRIDES[emp_norm]

    # Estratégia 1: nome normalizado exato
    for col in ("nome_norm", "nome_fantasia_norm"):
        mask = perm[col] == emp_norm
        if mask.any():
            return perm.loc[mask, "cnpj"].iloc[0]

    # Estratégia 2: compacto (sem espaços)
    for col in ("nome_compact", "nome_fantasia_compact"):
        mask = perm[col] == emp_compact
        if mask.any():
            return perm.loc[mask, "cnpj"].iloc[0]

    # Estratégia 3: sem sufixos jurídicos
    if emp_sem_suf:
        for col in ("nome_sem_suf", "nome_fantasia_sem_suf"):
            mask = perm[col] == emp_sem_suf
            if mask.any():
                return perm.loc[mask, "cnpj"].iloc[0]

    # Estratégia 4: empresa contida no nome cadastrado (único resultado)
    for col in ("nome_norm", "nome_fantasia_norm"):
        mask = perm[col].str.contains(re.escape(emp_norm), na=False)
        if mask.any() and mask.sum() == 1:
            return perm.loc[mask, "cnpj"].iloc[0]

    # Estratégia 5: nome cadastrado contido na empresa
    for col in ("nome_norm", "nome_fantasia_norm"):
        for _, row in perm[perm[col].str.len() > 4].iterrows():
            if row[col] and row[col] in emp_norm:
                return row["cnpj"]

    # Estratégia 6: prefixo compacto (único resultado)
    for col in ("nome_compact", "nome_fantasia_compact"):
        mask = perm[col].apply(
            lambda x: bool(x) and (emp_compact.startswith(x) or x.startswith(emp_compact))
        )
        if mask.any() and mask.sum() == 1:
            return perm.loc[mask, "cnpj"].iloc[0]

    emp_words = {w for w in emp_norm.split() if len(w) >= 3 and w not in STOP}

    # Estratégia 7a: Jaccard de palavras significativas
    if len(emp_words) >= 2:
        def word_jaccard(db_str):
            db_words = {w for w in db_str.split() if len(w) >= 3 and w not in STOP}
            if not db_words:
                return 0
            return len(emp_words & db_words) / len(emp_words | db_words)

        for col in ("nome_norm", "nome_fantasia_norm"):
            scores = perm[col].apply(word_jaccard)
            best = scores.max()
            if best >= 0.6:
                best_matches = perm[scores == best]
                if len(best_matches) == 1:
                    return best_matches["cnpj"].iloc[0]

    # Estratégia 7b: recall de palavras (≥ 75% das palavras da empresa no nome cadastrado)
    if len(emp_words) >= 2:
        def word_recall(db_str):
            db_words = {w for w in db_str.split() if len(w) >= 3 and w not in STOP}
            if not db_words:
                return 0
            return len(emp_words & db_words) / len(emp_words)

        for col in ("nome_norm", "nome_fantasia_norm"):
            scores = perm[col].apply(word_recall)
            best = scores.max()
            if best >= 0.75:
                best_matches = perm[scores == best]
                if len(best_matches) == 1:
                    return best_matches["cnpj"].iloc[0]

    return None


def format_cnpj(raw: str) -> str:
    digits = re.sub(r"\D", "", str(raw))
    if len(digits) == 14:
        return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"
    return raw


# ── Pipeline principal ────────────────────────────────────────────────────────

def main():
    print("Carregando planilha...")
    df = pd.read_excel("../pasta_seed/Novo Modelo Base Ouvidoria 2.xlsx", header=1)

    print("Carregando permissionarias do banco...")
    perm = load_permissionarias()
    cnpj_lookup = build_cnpj_lookup(perm)
    print(f"  {len(perm)} permissionarias carregadas.")

    # Insere colunas NOME DA EMPRESA BANCO e NOME FANTASIA BANCO logo após EMPRESA
    emp_pos = df.columns.get_loc("EMPRESA")
    df.insert(emp_pos + 1, "NOME DA EMPRESA BANCO", "")
    df.insert(emp_pos + 2, "NOME FANTASIA BANCO", "")

    # Preenche as colunas do banco para linhas que já TÊM CNPJ
    for idx, row in df[df["CNPJ"].notna()].iterrows():
        raw_cnpj = re.sub(r"\D", "", str(row["CNPJ"]))
        if raw_cnpj in cnpj_lookup:
            nome, fantasia = cnpj_lookup[raw_cnpj]
            df.at[idx, "NOME DA EMPRESA BANCO"] = nome
            df.at[idx, "NOME FANTASIA BANCO"]   = fantasia

    sem_cnpj = df["CNPJ"].isna()
    total_sem = sem_cnpj.sum()
    print(f"\nLinhas sem CNPJ: {total_sem} / {len(df)}")

    encontrados = 0
    nao_encontrados_idx = []

    for idx in df[sem_cnpj].index:
        empresa = df.at[idx, "EMPRESA"]
        cnpj_raw = buscar_cnpj(empresa, perm)

        if cnpj_raw:
            df.at[idx, "CNPJ"] = format_cnpj(cnpj_raw)
            nome, fantasia = cnpj_lookup.get(cnpj_raw, ("", ""))
            df.at[idx, "NOME DA EMPRESA BANCO"] = nome
            df.at[idx, "NOME FANTASIA BANCO"]   = fantasia
            encontrados += 1
        else:
            nao_encontrados_idx.append(idx)

    print(f"\nResultados:")
    print(f"  Encontrados      : {encontrados}")
    print(f"  Não encontrados  : {len(nao_encontrados_idx)}")

    # Salva CSV enriquecido (CSV preserva PROTOCOLO como texto, evitando perda de precisão do Excel)
    output_csv = "NOVO_MODELO_enriquecido.csv"
    df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    print(f"\nArquivo salvo: {output_csv}")

    # Salva empresas únicas não encontradas
    if nao_encontrados_idx:
        unicas = (
            df.loc[nao_encontrados_idx, "EMPRESA"]
            .dropna()
            .unique()
        )
        pd.DataFrame({"EMPRESA": unicas}).to_csv(
            "nao_encontrados.csv", index=False, encoding="utf-8-sig"
        )
        print(f"Empresas únicas não encontradas ({len(unicas)}): nao_encontrados.csv")
    else:
        print("Todas as empresas foram identificadas!")


if __name__ == "__main__":
    main()
