"""
Seed de dados históricos no sistema de ouvidoria.

Cada linha do Excel corresponde a uma Ouvidoria com uma Reclamacao vinculada.
As regras de inserção variam por tipo de serviço (REGULAR vs FRETAMENTO).

Uso:
    python database/seed_dados_antigos.py

Pré-requisito: o seed base (seed_all.py) deve ter sido executado antes.

Saída:
    seed_lancados.xlsx     — linhas efetivamente inseridas no banco
    seed_nao_lancados.xlsx — linhas puladas, com coluna MOTIVO
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unicodedata
import pandas as pd
from datetime import date, datetime, timedelta

from database.connection import init_db, db_session
from models import (
    Ouvidoria, StatusOuvidoria,
    Reclamacao, TipoServico,
    ReclamacaoAuto,
    RespostaTecnica,
    Categoria, Subcategoria,
    Permissionaria,
    Usuario,
)
from utils.loaders_auto import buscar_autos_por_trecho
from repositories.pontuacao import calcular_pontuacao_auto

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DADOS_ANTIGOS = os.path.join(BASE_DIR, "pasta_seed", "dados_antigos_tratado_empresa_e_cidades.xlsx")
CATEGORIA_MAPPING = os.path.join(BASE_DIR, "normalizacao_dados", "CATEGORIA NOVA X CATEGORIA ANTIGA.xlsx")
OUT_LANCADOS = os.path.join(BASE_DIR, "seed_lancados.xlsx")
OUT_NAO_LANCADOS = os.path.join(BASE_DIR, "seed_nao_lancados.xlsx")

PRAZO_PADRAO_DIAS = 15  # fallback quando LIMITE R. está vazio


# ── Helpers ───────────────────────────────────────────────────────────────────

def _val(row, col):
    """Retorna o valor da coluna ou None se ausente/nulo/nan."""
    v = row.get(col)
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip()
    return s if s and s.lower() != "nan" else None


def _to_date(val) -> date | None:
    if val is None:
        return None
    try:
        if pd.isna(val):  # cobre NaT, NaN, None
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(val, pd.Timestamp):
        return val.date()
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    try:
        result = pd.to_datetime(val)
        return None if pd.isna(result) else result.date()
    except Exception:
        return None


def _norm_upper(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s).strip().upper())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


# ── Carregamento de dados de referência ───────────────────────────────────────

def load_categoria_mapping() -> dict[str, str]:
    """Retorna {assunto_upper: nova_subcategoria_upper}.

    Coluna 1 'ANTIGAS SUBCATEGORIAS (ASSUNTO)' = valor do campo ASSUNTO nos dados.
    Coluna 2 'NOVAS SUBCATEGORIAS' = nome da subcategoria no banco.
    """
    df = pd.read_excel(CATEGORIA_MAPPING)
    df.columns = [c.strip() for c in df.columns]
    mapping: dict[str, str] = {}
    for _, row in df.iterrows():
        assunto = _val(row, "ANTIGAS SUBCATEGORIAS (ASSUNTO)")
        nova = _val(row, "NOVAS SUBCATEGORIAS")
        if assunto and nova:
            mapping[_norm_upper(assunto)] = _norm_upper(nova)
    return mapping


def build_lookups(session) -> tuple:
    """
    Retorna:
        sub_map: {nome_subcategoria_upper: (subcategoria_id, categoria_id)}
        perm_by_cnpj: {cnpj: permissionaria_id}
        perm_by_nome: {nome_upper: permissionaria_id}
        existing_protocols: set[str]
        admin_id: int
    """
    sub_map: dict[str, tuple[int, int]] = {}
    for sub in session.query(Subcategoria).all():
        sub_map[_norm_upper(sub.nome)] = (sub.id, sub.categoria_id)

    perm_by_cnpj: dict[str, int] = {}
    perm_by_nome: dict[str, int] = {}
    for p in session.query(Permissionaria).all():
        if p.cnpj:
            perm_by_cnpj[p.cnpj.strip()] = p.id
        perm_by_nome[_norm_upper(p.nome)] = p.id
        if p.nome_fantasia:
            perm_by_nome[_norm_upper(p.nome_fantasia)] = p.id

    existing = set(
        r[0] for r in session.query(Ouvidoria.protocolo).all()
    )

    admin = session.query(Usuario).first()
    if admin is None:
        raise RuntimeError("Nenhum usuário encontrado — execute seed_all.py primeiro.")

    return sub_map, perm_by_cnpj, perm_by_nome, existing, admin.id


# ── Mapeamento de tipo de serviço ─────────────────────────────────────────────

# Variantes de ASSUNTO não cobertas pela planilha de mapeamento
_ASSUNTO_ALIASES: dict[str, str] = {
    "BENEFICIO DO ESTUDANTE": "BENEFICIO DE ESTUDANTE",
}

_TIPO_MAP: dict[tuple[str, str], TipoServico] = {
    ("INTERMUNICIPAL", "REGULAR"): TipoServico.REGULAR_INTERMUNICIPAL,
    ("METROPOLITANO", "REGULAR"): TipoServico.REGULAR_METROPOLITANO,
    ("INTERMUNICIPAL", "FRETAMENTO"): TipoServico.FRETAMENTO_INTERMUNICIPAL,
    ("METROPOLITANO", "FRETAMENTO"): TipoServico.FRETAMENTO_METROPOLITANO,
}


# ── Seed principal ────────────────────────────────────────────────────────────

def seed_dados_antigos():
    print(f"Lendo {os.path.basename(DADOS_ANTIGOS)}...")
    df = pd.read_excel(DADOS_ANTIGOS)
    df.columns = [c.strip() for c in df.columns]
    total = len(df)
    print(f"  {total} linhas encontradas.\n")

    print(f"Lendo mapeamento de categorias...")
    cat_mapping = load_categoria_mapping()
    print(f"  {len(cat_mapping)} mapeamentos carregados.\n")

    stats = {"inseridas": 0, "puladas": 0, "duplicadas": 0, "erros": 0}

    # Rastreamento para os relatórios de saída
    idx_lancados: list[int] = []
    idx_nao_lancados: list[int] = []
    motivos: dict[int, str] = {}  # idx → motivo da não inserção

    # ── Fase 1: carregar lookups uma única vez ────────────────────────────────
    with db_session() as session:
        sub_map, perm_by_cnpj, perm_by_nome, existing, admin_id = build_lookups(session)
    print(f"Referências carregadas: {len(sub_map)} subcategorias, "
          f"{len(perm_by_cnpj)} CNPJs, {len(existing)} protocolos já existentes.\n")

    # ── Fase 2: processar linha a linha, cada uma com sua própria sessão ──────
    for idx, row in df.iterrows():
        def _pula(motivo: str):
            idx_nao_lancados.append(idx)
            motivos[idx] = motivo
            stats["puladas"] += 1

        # ── 1. Protocolo ──────────────────────────────────────────────────────
        protocolo = _val(row, "PROTOCOLO")
        if not protocolo:
            _pula("Protocolo vazio")
            continue
        if protocolo in existing:
            stats["duplicadas"] += 1
            continue

        # ── 2. Tipo de serviço ────────────────────────────────────────────────
        sistema = _norm_upper(_val(row, "SISTEMA") or "")
        subsistema = _norm_upper(_val(row, "SUBSISTEMA") or "")
        tipo_servico = _TIPO_MAP.get((sistema, subsistema))
        if tipo_servico is None:
            _pula(f"Tipo de serviço inválido: SISTEMA='{sistema}' SUBSISTEMA='{subsistema}'")
            continue

        is_regular = subsistema == "REGULAR"
        is_fretamento = subsistema == "FRETAMENTO"

        # ── 3. ASSUNTO → subcategoria ─────────────────────────────────────────
        assunto_raw = _val(row, "ASSUNTO")
        if not assunto_raw:
            _pula("ASSUNTO vazio")
            continue

        nova_sub_nome = cat_mapping.get(_norm_upper(assunto_raw))
        if nova_sub_nome is None:
            alias = _ASSUNTO_ALIASES.get(_norm_upper(assunto_raw))
            if alias:
                nova_sub_nome = cat_mapping.get(alias)
        if nova_sub_nome is None:
            _pula(f"ASSUNTO sem mapeamento: '{assunto_raw}'")
            continue

        sub_info = sub_map.get(nova_sub_nome)
        if sub_info is None:
            _pula(f"Subcategoria '{nova_sub_nome}' não encontrada no banco")
            continue

        subcategoria_id, categoria_id = sub_info

        # ── 4. Empresa ────────────────────────────────────────────────────────
        cnpj_raw = _val(row, "CNPJ")
        empresa_nome = _val(row, "NOME DA EMPRESA BANCO")

        perm_id: int | None = None
        if cnpj_raw:
            cnpj_digits = "".join(c for c in cnpj_raw if c.isdigit())
            if len(cnpj_digits) == 14:
                perm_id = perm_by_cnpj.get(cnpj_digits)
        if perm_id is None and empresa_nome:
            perm_id = perm_by_nome.get(_norm_upper(empresa_nome))

        empresa_filled = empresa_nome is not None

        # ── 5. Municípios ─────────────────────────────────────────────────────
        origem_ibge = _val(row, "ORIGEM_IBGE")
        destino_ibge = _val(row, "DESTINO_IBGE")
        has_trecho = bool(origem_ibge and destino_ibge)

        # ── 6. Regras FRETAMENTO ──────────────────────────────────────────────
        if is_fretamento and not empresa_filled:
            is_clandestino = (
                "CLANDESTINO" in nova_sub_nome or
                "IRREGULAR" in nova_sub_nome
            )
            if not is_clandestino:
                _pula("Fretamento sem empresa (assunto não é transporte irregular/clandestino)")
                continue
            if not has_trecho:
                _pula("Fretamento clandestino sem empresa e sem origem/destino")
                continue

        # ── 7. Datas ──────────────────────────────────────────────────────────
        data_entrada = _to_date(row.get("DATA"))
        limite_resposta = _to_date(row.get("LIMITE R."))
        data_resposta = _to_date(row.get("DATA R."))

        if limite_resposta is None:
            base = data_entrada or date.today()
            limite_resposta = base + timedelta(days=PRAZO_PADRAO_DIAS)

        criado_em = (
            datetime(data_entrada.year, data_entrada.month, data_entrada.day)
            if data_entrada else datetime.now()
        )

        sei = _val(row, "N° SEI")
        conteudo = sei if sei else "SEM DADOS"

        # ── 8. Inserir no banco (sessão própria por linha) ────────────────────
        try:
            with db_session() as session:
                ouvidoria = Ouvidoria(
                    protocolo=protocolo,
                    conteudo=conteudo,
                    prazo=limite_resposta,
                    prazo_permissionaria=None,
                    status=StatusOuvidoria.CONCLUIDO,
                    criado_por_id=admin_id,
                    criado_em=criado_em,
                )
                session.add(ouvidoria)
                session.flush()

                empresa_fretamento = empresa_nome if is_fretamento else None
                reclamacao = Reclamacao(
                    ouvidoria_id=ouvidoria.id,
                    numero_item=1,
                    categoria_id=categoria_id,
                    subcategoria_id=subcategoria_id,
                    tipo_servico=tipo_servico,
                    local_embarque=origem_ibge or None,
                    local_desembarque=destino_ibge or None,
                    descricao=None,
                    empresa_fretamento=empresa_fretamento,
                )
                session.add(reclamacao)
                session.flush()

                if is_regular and (perm_id is not None or has_trecho):
                    autos = buscar_autos_por_trecho(
                        tipo_servico=tipo_servico.value,
                        cidade_a=origem_ibge or "",
                        cidade_b=destino_ibge or "",
                        perm_id=perm_id,
                    )
                    pontuacao = calcular_pontuacao_auto(len(autos))
                    for auto in autos:
                        session.add(ReclamacaoAuto(
                            reclamacao_id=reclamacao.id,
                            auto_id=auto["id"],
                            pontuacao=pontuacao,
                        ))

                if data_resposta:
                    session.add(RespostaTecnica(
                        ouvidoria_id=ouvidoria.id,
                        tecnico_id=admin_id,
                        data_resposta=data_resposta,
                        texto_resposta="SEM DADOS",
                    ))

            existing.add(protocolo)
            idx_lancados.append(idx)
            stats["inseridas"] += 1

            if stats["inseridas"] % 100 == 0:
                print(f"  {stats['inseridas']} ouvidorias inseridas...")

        except Exception as e:
            msg = str(e).split("\n")[0]
            print(f"  [ERRO] Linha {idx + 2}: {msg}")
            idx_nao_lancados.append(idx)
            motivos[idx] = f"Erro: {msg}"
            stats["erros"] += 1

    # ── Resumo de motivos ─────────────────────────────────────────────────────
    if motivos:
        from collections import Counter
        contagem = Counter(motivos.values())
        print(f"\nMotivos das {stats['puladas']} linhas puladas:")
        for motivo, qtd in contagem.most_common():
            print(f"  {qtd:>5}x  {motivo}")

    # ── Exportar relatórios ───────────────────────────────────────────────────
    print("\nGerando relatórios Excel...")

    if idx_lancados:
        df_lancados = df.loc[idx_lancados].copy()
        df_lancados.to_excel(OUT_LANCADOS, index=False)
        print(f"  Lançados:     {OUT_LANCADOS}")
    else:
        print("  Nenhuma linha lançada — arquivo não gerado.")

    if idx_nao_lancados:
        df_nao = df.loc[idx_nao_lancados].copy()
        df_nao.insert(0, "MOTIVO", df_nao.index.map(motivos))
        df_nao.to_excel(OUT_NAO_LANCADOS, index=False)
        print(f"  Não lançados: {OUT_NAO_LANCADOS}")
    else:
        print("  Todos foram lançados — arquivo de não lançados não gerado.")

    # ── Relatório final ───────────────────────────────────────────────────────
    print(f"\nResultado:")
    print(f"  Inseridas:   {stats['inseridas']}")
    print(f"  Puladas:     {stats['puladas']}")
    print(f"  Duplicadas:  {stats['duplicadas']}")
    print(f"  Erros:       {stats['erros']}")


if __name__ == "__main__":
    print("=== Inicializando banco ===")
    init_db()
    print()
    print("=== Importando dados históricos ===")
    seed_dados_antigos()
    print()
    print("Concluído.")
