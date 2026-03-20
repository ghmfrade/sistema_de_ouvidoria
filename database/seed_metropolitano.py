"""
Script de importacao dos dados metropolitanos a partir dos arquivos Excel.

Uso:
    python database/seed_metropolitano.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from database.connection import init_db, db_session, get_session
from models import Permissionaria, AutoLinha, ParadaAutoLinha, TipoServico
from sqlalchemy import text


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XLSX_LINHAS = os.path.join(BASE_DIR, "linhas metropolitanas.xlsx")
XLSX_MUNICIPIOS = os.path.join(BASE_DIR, "municipios_GESTEC LINHAS.xlsx")


def truncar_metropolitanos():
    """Remove todos os autos metropolitanos existentes."""
    session = get_session()
    try:
        session.execute(text(
            "DELETE FROM reclamacao_autos WHERE auto_id IN "
            "(SELECT id FROM autos_linha WHERE tipo = 'Regular – Metropolitano')"
        ))
        session.execute(text(
            "DELETE FROM paradas_auto_linha WHERE auto_id IN "
            "(SELECT id FROM autos_linha WHERE tipo = 'Regular – Metropolitano')"
        ))
        session.execute(text("DELETE FROM autos_linha WHERE tipo = 'Regular – Metropolitano'"))
        session.commit()
        print("  Dados metropolitanos anteriores removidos.")
    finally:
        session.close()


def importar_linhas_metropolitanas():
    """Le os Excel e popula autos_linha e paradas_auto_linha para linhas metropolitanas."""
    print(f"Lendo {os.path.basename(XLSX_LINHAS)}...")
    df_linhas = pd.read_excel(XLSX_LINHAS, header=2, dtype=str)
    df_linhas = df_linhas.dropna(how="all")

    # Normaliza nomes das colunas (remove espacos extras)
    df_linhas.columns = [c.strip() for c in df_linhas.columns]

    print(f"  Colunas encontradas: {list(df_linhas.columns)}")
    print(f"  Total de linhas no Excel: {len(df_linhas)}")

    # Detecta colunas
    def _find_col(df, *candidates):
        lower_map = {c.lower(): c for c in df.columns}
        for cand in candidates:
            if cand in df.columns:
                return cand
            if cand.lower() in lower_map:
                return lower_map[cand.lower()]
        return None

    col_rm = _find_col(df_linhas, "Reg_Metropolitana", "Reg Metropolitana", "RM") or df_linhas.columns[0]
    col_sub = _find_col(df_linhas, "Sub_Região", "Sub_Regiao", "Sub Região") or df_linhas.columns[1]
    col_linha = _find_col(df_linhas, "Linha") or df_linhas.columns[2]
    col_operadora = _find_col(df_linhas, "Operadora") or df_linhas.columns[3]
    col_fantasia = _find_col(df_linhas, "Fantasia") or df_linhas.columns[4]
    col_situacao = _find_col(df_linhas, "Situação", "Situacao") or df_linhas.columns[5]
    col_denom_a = _find_col(df_linhas, "Denominação_A", "Denominacao_A", "Denominação A") or df_linhas.columns[7]
    col_denom_b = _find_col(df_linhas, "Denominação_B", "Denominacao_B", "Denominação B") or df_linhas.columns[8]
    col_via = _find_col(df_linhas, "Via") or df_linhas.columns[9]
    col_servico = _find_col(df_linhas, "Serviço", "Servico") or df_linhas.columns[10]

    print(f"  Colunas mapeadas: rm={col_rm!r}, linha={col_linha!r}, operadora={col_operadora!r}")

    # Le municipios
    print(f"Lendo {os.path.basename(XLSX_MUNICIPIOS)}...")
    df_mun = pd.read_excel(XLSX_MUNICIPIOS, header=2, dtype=str)
    df_mun = df_mun.dropna(how="all")
    df_mun.columns = [c.strip() for c in df_mun.columns]

    print(f"  Colunas encontradas: {list(df_mun.columns)}")
    print(f"  Total de registros de municipios: {len(df_mun)}")

    col_mun_rm = _find_col(df_mun, "RM", "Reg_Metropolitana") or df_mun.columns[0]
    col_mun_cidade = _find_col(df_mun, "MUNICÍPIO", "MUNICIPIO", "Município") or df_mun.columns[1]
    col_mun_linha = _find_col(df_mun, "LINHA", "Linha") or df_mun.columns[2]

    with db_session() as session:
        # Importa permissionarias (reutiliza existentes)
        permissionarias_map: dict[str, int] = {}

        # Carrega permissionarias existentes
        for perm in session.query(Permissionaria).all():
            permissionarias_map[perm.nome] = perm.id

        nomes_operadoras = df_linhas[col_operadora].dropna().str.strip().unique()
        novas_perms = 0
        for nome in sorted(nomes_operadoras):
            if not nome or nome.lower() in ("nan", "none", ""):
                continue
            if nome not in permissionarias_map:
                perm = Permissionaria(nome=nome)
                session.add(perm)
                session.flush()
                permissionarias_map[nome] = perm.id
                novas_perms += 1
        print(f"  {novas_perms} novas permissionarias criadas ({len(permissionarias_map)} total).")

        # Normaliza nomes de RM (ex: "VALE DO PARAIBA" -> "VALE DO PARAIBA E LITORAL NORTE")
        RM_RENAME = {
            "VALE DO PARAIBA": "VALE DO PARAIBA E LITORAL NORTE",
        }

        # Importa autos metropolitanos
        autos_criados = 0
        # Chave: (numero, regiao_metropolitana) -> auto_id
        autos_map: dict[tuple, int] = {}

        for _, row in df_linhas.iterrows():
            linha_num = str(row.get(col_linha, "")).strip()
            if not linha_num or linha_num.lower() in ("nan", "none", ""):
                continue

            rm = str(row.get(col_rm, "")).strip() if pd.notna(row.get(col_rm)) else None
            if rm:
                rm = RM_RENAME.get(rm, rm)
            sub_regiao = str(row.get(col_sub, "")).strip() if pd.notna(row.get(col_sub)) else None
            operadora = str(row.get(col_operadora, "")).strip() if pd.notna(row.get(col_operadora)) else None
            fantasia = str(row.get(col_fantasia, "")).strip() if pd.notna(row.get(col_fantasia)) else None
            denom_a = str(row.get(col_denom_a, "")).strip() if pd.notna(row.get(col_denom_a)) else None
            denom_b = str(row.get(col_denom_b, "")).strip() if pd.notna(row.get(col_denom_b)) else None
            via_val = str(row.get(col_via, "")).strip() if pd.notna(row.get(col_via)) else None
            servico = str(row.get(col_servico, "")).strip() if pd.notna(row.get(col_servico)) else None
            situacao = str(row.get(col_situacao, "")).strip() if pd.notna(row.get(col_situacao)) else None

            chave = (linha_num, rm)
            if chave in autos_map:
                continue

            perm_id = permissionarias_map.get(operadora) if operadora else None

            # Monta itinerario a partir de denominacao A e B
            itinerario = None
            if denom_a and denom_b:
                itinerario = f"{denom_a} - {denom_b}"
            elif denom_a:
                itinerario = denom_a
            elif denom_b:
                itinerario = denom_b

            auto = AutoLinha(
                numero=linha_num,
                tipo=TipoServico.REGULAR_METROPOLITANO,
                itinerario=itinerario,
                cidade_inicial=denom_a,
                cidade_final=denom_b,
                permissionaria_id=perm_id,
                regiao_metropolitana=rm,
                sub_regiao=sub_regiao,
                nome_fantasia=fantasia,
                denominacao_a=denom_a,
                denominacao_b=denom_b,
                via=via_val if via_val and via_val.lower() not in ("nan", "none", "") else None,
                servico=servico,
                ativo=situacao is not None and "OPERA" in situacao.upper(),
            )
            session.add(auto)
            session.flush()
            autos_map[chave] = auto.id
            autos_criados += 1

        print(f"  {autos_criados} autos metropolitanos criados.")

        # Importa paradas (municipios atendidos por cada linha)
        # Mapa de normalizacao de RMs (municipios pode ter nomes diferentes do metro)
        rms_metro = {rm for (_, rm) in autos_map.keys() if rm}
        rm_normalize: dict[str, str] = {}
        for rm_mun_name in df_mun[col_mun_rm].dropna().str.strip().unique():
            if rm_mun_name in rms_metro:
                rm_normalize[rm_mun_name] = rm_mun_name
            else:
                # Tenta match parcial (ex: "VALE DO PARAIBA E LITORAL NORTE" -> "VALE DO PARAIBA")
                for rm_m in rms_metro:
                    if rm_mun_name.startswith(rm_m) or rm_m.startswith(rm_mun_name):
                        rm_normalize[rm_mun_name] = rm_m
                        break

        paradas_criadas = 0
        vistos: set[tuple] = set()  # (auto_id, cidade)

        for _, row in df_mun.iterrows():
            rm_raw = str(row.get(col_mun_rm, "")).strip() if pd.notna(row.get(col_mun_rm)) else None
            cidade = str(row.get(col_mun_cidade, "")).strip() if pd.notna(row.get(col_mun_cidade)) else None
            linha_num = str(row.get(col_mun_linha, "")).strip() if pd.notna(row.get(col_mun_linha)) else None

            if not cidade or not linha_num or not rm_raw:
                continue
            if cidade.lower() in ("nan", "none", ""):
                continue

            rm = rm_normalize.get(rm_raw, rm_raw)
            chave_auto = (linha_num, rm)
            auto_id = autos_map.get(chave_auto)
            if not auto_id:
                continue

            chave_parada = (auto_id, cidade)
            if chave_parada in vistos:
                continue
            vistos.add(chave_parada)

            session.add(ParadaAutoLinha(auto_id=auto_id, cidade=cidade))
            paradas_criadas += 1

        print(f"  {paradas_criadas} paradas metropolitanas criadas.")


if __name__ == "__main__":
    print("=== Inicializando banco de dados ===")
    init_db()
    print()
    print("=== Removendo dados metropolitanos anteriores ===")
    truncar_metropolitanos()
    print()
    print("=== Importando Linhas Metropolitanas ===")
    importar_linhas_metropolitanas()
    print()
    print("Concluido.")
