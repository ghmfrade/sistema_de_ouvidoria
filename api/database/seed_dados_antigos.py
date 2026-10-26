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
import re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import unicodedata
from collections import Counter

import pandas as pd
from datetime import date, datetime, timedelta

from sqlalchemy import func

from api.database.connection import init_db, db_session
from api.models import (
    AutoLinha,
    Ouvidoria, StatusOuvidoria,
    Reclamacao, TipoServico,
    ReclamacaoAuto,
    RespostaTecnica,
    Categoria, Subcategoria,
    Permissionaria,
    Usuario,
)
from api.repositories.autos_repo import (
    buscar_autos_por_numero,
    buscar_autos_por_trecho,
    get_todos_autos,
)
from api.repositories.pontuacao import calcular_pontuacao_auto
from api.database.match_permissionaria import casar, construir_universo
from api.database.termos_requisicao import carregar_operadores

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DADOS_ANTIGOS = os.path.join(BASE_DIR, "pasta_seed", "dados_antigos_tratado_empresa_e_cidades.csv")
CATEGORIA_MAPPING = os.path.join(BASE_DIR, "normalizacao_dados", "CATEGORIA NOVA X CATEGORIA ANTIGA.xlsx")
OUT_LANCADOS = os.path.join(BASE_DIR, "seed_lancados.xlsx")
OUT_NAO_LANCADOS = os.path.join(BASE_DIR, "seed_nao_lancados.xlsx")
OUT_SEM_AUTOS = os.path.join(BASE_DIR, "seed_sem_autos.xlsx")

PRAZO_PADRAO_DIAS = 10  # fallback quando LIMITE R. está vazio


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


def _parse_linha(val) -> list[str]:
    """Parseia célula LINHA em lista de números de autos.

    Suporta separadores ' - ' e '/'.
    '801 - 802 - 803' → ['801', '802', '803']
    '660/662'         → ['660', '662']
    """
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return []
    s = str(val).strip()
    if not s or s.lower() == "nan":
        return []
    parts = re.split(r"\s*[-/]\s*", s)
    return [p.strip() for p in parts if p.strip()]


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
        existing_protocols: set[str]
        admin_id: int
        tecnico_legados_id: int
        universos: {tipo_servico_value: universo de match (ver match_permissionaria)}
        operadores: {auto_id: permissionaria_id que opera por termo de requisicao}
    """
    sub_map: dict[str, tuple[int, int]] = {}
    for sub in session.query(Subcategoria).all():
        sub_map[_norm_upper(sub.nome)] = (sub.id, sub.categoria_id)

    # O match por nome é feito por match_permissionaria, dentro do universo
    # do regular; aqui só o índice por CNPJ, usado para validar o CNPJ do CSV.
    perm_by_cnpj: dict[str, int] = {}
    for p in session.query(Permissionaria).all():
        if p.cnpj:
            perm_by_cnpj[p.cnpj.strip()] = p.id

    existing = set(
        r[0] for r in session.query(Ouvidoria.protocolo).all()
    )

    admin = session.query(Usuario).filter_by(email="admin@artesp.sp.gov.br").first()
    if admin is None:
        raise RuntimeError("Admin não encontrado — execute seed_all.py primeiro.")

    dados_legados = session.query(Usuario).filter(
        Usuario.nome.ilike("Dados Legados")
    ).first()
    if dados_legados is None:
        raise RuntimeError("Usuário 'Dados Legados' não encontrado — execute seed_usuarios.py primeiro.")

    # Universo de match por tipo de servico regular: apenas empresas com auto
    # ativo daquele tipo. Ver o cabecalho de match_permissionaria.py.
    universos = {
        tipo.value: construir_universo(session, tipo)
        for tipo in (TipoServico.REGULAR_INTERMUNICIPAL, TipoServico.REGULAR_METROPOLITANO)
    }

    operadores = carregar_operadores(session)

    return (sub_map, perm_by_cnpj, existing, admin.id,
            dados_legados.id, universos, operadores)


# ── Resolução de empresa e de autos ───────────────────────────────────────────

def resolver_permissionaria(row, tipo_servico, universos, perm_by_cnpj) -> tuple[int | None, str]:
    """Resolve a permissionária de uma linha REGULAR dentro do universo do tipo.

    1. CNPJ do CSV, aceito somente se a empresa estiver no universo — o CSV
       traz CNPJ errado em parte das linhas, apontando para empresas que nunca
       terão auto (ex. GUERINI PLANEJAMENTOS no lugar de GUERINO SEISCENTO).
    2. Senão, casa o nome livre da coluna EMPRESA. Usa-se EMPRESA e não
       NOME DA EMPRESA BANCO porque esta última já é a saída do enriquecimento.
    """
    universo = universos.get(tipo_servico.value, [])
    ids_do_universo = {e["id"] for e in universo}

    cnpj_raw = _val(row, "CNPJ")
    if cnpj_raw:
        cnpj_digits = "".join(c for c in cnpj_raw if c.isdigit())
        if len(cnpj_digits) == 14:
            perm_id = perm_by_cnpj.get(cnpj_digits)
            if perm_id is not None and perm_id in ids_do_universo:
                return perm_id, "cnpj"

    return casar(_val(row, "EMPRESA"), universo)


def _atribuivel(auto: dict, perm_id: int | None, operadores: dict[int, int]) -> bool:
    """True se o auto pertence à empresa ou é operado por ela via requisição."""
    if perm_id is None:
        return False
    return auto["permissionaria_id"] == perm_id or operadores.get(auto["id"]) == perm_id


def _par_de_cidades(origem_ibge, destino_ibge) -> tuple[str, str]:
    """Argumentos de trecho para buscar_autos_por_trecho.

    A busca ignora o filtro de trecho quando cidade_a vem vazia, então o
    município conhecido tem de ir sempre em cidade_a: com só um dos dois
    preenchidos o filtro é "auto que toca esse município".
    """
    if origem_ibge and destino_ibge:
        return origem_ibge, destino_ibge
    return (origem_ibge or destino_ibge or ""), ""


def indexar_autos_por_empresa(universos, operadores) -> dict[str, dict[int, list[dict]]]:
    """{tipo_servico: {perm_id: autos atribuíveis}} para os tipos regulares.

    Usado quando a reclamação não informa trecho: aí ela é contra a empresa,
    e vale para toda a frota dela.
    """
    indice: dict[str, dict[int, list[dict]]] = {}
    for tipo_value in universos:
        por_empresa: dict[int, list[dict]] = {}
        for auto in get_todos_autos(tipo_value):
            for perm_id in {auto["permissionaria_id"], operadores.get(auto["id"])}:
                if perm_id is not None:
                    por_empresa.setdefault(perm_id, []).append(auto)
        indice[tipo_value] = por_empresa
    return indice


def resolver_autos(row, tipo_servico, perm_id, origem_ibge, destino_ibge,
                   operadores, autos_por_empresa) -> list[dict]:
    """Autos a vincular à reclamação regular.

    A busca roda sem filtro de empresa no repositório e o filtro é aplicado
    aqui, para que o termo de requisição entre sem alterar autos_repo (usado
    pela API).

    Exige empresa resolvida para a busca por trecho: sem isso o seed anexava os
    autos de TODAS as empresas da rota.
    """
    numeros_linha = _parse_linha(row.get("LINHA"))

    if numeros_linha:
        candidatos = buscar_autos_por_numero(
            numeros=numeros_linha,
            tipo_servico=tipo_servico.value,
            perm_id=None,
        )
        autos = [a for a in candidatos if _atribuivel(a, perm_id, operadores)]
        # O número do auto é mais autoritativo que o nome da empresa: se o
        # número casou mas a empresa não, fica com os autos do número.
        if not autos and candidatos:
            return candidatos
        if autos:
            return autos

    if perm_id is None:
        return []

    # Sem nenhum município: a reclamação é contra a empresa, linha
    # desconhecida. Distribui entre toda a frota dela — a pontuação 1/n
    # mantém a reclamação valendo 1 ponto no total.
    if not (origem_ibge or destino_ibge):
        return autos_por_empresa.get(tipo_servico.value, {}).get(perm_id, [])

    cidade_a, cidade_b = _par_de_cidades(origem_ibge, destino_ibge)
    candidatos = buscar_autos_por_trecho(
        tipo_servico=tipo_servico.value,
        cidade_a=cidade_a,
        cidade_b=cidade_b,
        perm_id=None,
    )
    return [a for a in candidatos if _atribuivel(a, perm_id, operadores)]


def classificar_sem_auto(perm_id, etapa, origem_ibge, destino_ibge,
                         n_autos_empresa, trecho_tem_auto) -> str:
    """Causa de a reclamação regular ter ficado sem nenhum auto."""
    if perm_id is None and not (origem_ibge and destino_ibge):
        return "C. sem empresa e sem origem/destino"
    if perm_id is None:
        return f"C. empresa não resolvida (match: {etapa})"
    if n_autos_empresa == 0:
        return "A. empresa casada não tem nenhum auto ativo"
    if not (origem_ibge or destino_ibge):
        return "G. empresa resolvida sem nenhum auto atribuível"
    if not trecho_tem_auto:
        return "F. trecho inexistente em trechos_auto_linha"
    return "B. trecho existe, mas sob outra empresa"


def _registro_sem_auto(protocolo, row, tipo_servico, perm_id, etapa_match,
                       origem_ibge, destino_ibge, autos_por_perm) -> dict:
    """Linha do relatório seed_sem_autos.xlsx, com a causa da lacuna."""
    # Autos de QUALQUER empresa nesse trecho: separa a causa B da F.
    autos_do_trecho = []
    if origem_ibge or destino_ibge:
        cidade_a, cidade_b = _par_de_cidades(origem_ibge, destino_ibge)
        autos_do_trecho = buscar_autos_por_trecho(
            tipo_servico=tipo_servico.value,
            cidade_a=cidade_a,
            cidade_b=cidade_b,
            perm_id=None,
        )

    n_autos_empresa = autos_por_perm.get(perm_id, 0) if perm_id is not None else None
    operadoras = ", ".join(sorted({
        a["permissionaria_nome"] for a in autos_do_trecho if a["permissionaria_nome"]
    }))

    return {
        "PROTOCOLO": protocolo,
        "TIPO_SERVICO": tipo_servico.value,
        "EMPRESA_PLANILHA": _val(row, "EMPRESA"),
        "CNPJ_PLANILHA": _val(row, "CNPJ"),
        "LINHA": _val(row, "LINHA"),
        "EMBARQUE": origem_ibge,
        "DESEMBARQUE": destino_ibge,
        "PERM_ID_CASADA": perm_id,
        "ETAPA_MATCH": etapa_match,
        "AUTOS_ATIVOS_DA_EMPRESA": n_autos_empresa,
        "CAUSA": classificar_sem_auto(
            perm_id, etapa_match, origem_ibge, destino_ibge,
            n_autos_empresa, bool(autos_do_trecho),
        ),
        "EMPRESAS_QUE_OPERAM_O_TRECHO": operadoras or None,
    }


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

def _limpar_ouvidorias():
    """Remove TODAS as ouvidorias e registros derivados via TRUNCATE CASCADE."""
    from sqlalchemy import text as _text
    with db_session() as session:
        count = session.execute(_text("SELECT COUNT(*) FROM ouvidorias")).scalar()
        session.execute(_text("TRUNCATE TABLE ouvidorias CASCADE"))
        print(f"  {count} ouvidorias removidas do banco.\n")


def seed_dados_antigos(dry_run: bool = False):
    if dry_run:
        print("=== DRY-RUN: nada será gravado no banco ===\n")
    else:
        print("=== Limpando ouvidorias existentes ===")
        _limpar_ouvidorias()

    print(f"Lendo {os.path.basename(DADOS_ANTIGOS)}...")
    df = pd.read_csv(DADOS_ANTIGOS, dtype={"PROTOCOLO": str}, encoding="utf-8-sig")
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
        (sub_map, perm_by_cnpj, existing, admin_id,
         tecnico_legados_id, universos, operadores) = build_lookups(session)
    print(f"Referências carregadas: {len(sub_map)} subcategorias, "
          f"{len(perm_by_cnpj)} CNPJs, {len(existing)} protocolos já existentes.")
    for tipo_value, universo in universos.items():
        print(f"  universo de match '{tipo_value}': {len(universo)} empresas com auto ativo")

    # A execução real faz TRUNCATE antes de inserir, então os protocolos que
    # já estão no banco não são duplicatas de verdade. Zerar aqui faz o
    # dry-run percorrer as mesmas linhas que a execução real percorreria.
    if dry_run:
        print(f"  dry-run: ignorando os {len(existing)} protocolos já no banco "
              "(a execução real os recria)")
        existing = set()
    print()

    # Nº de autos ativos por permissionária, para classificar as lacunas.
    with db_session() as session:
        autos_por_perm = dict(
            session.query(AutoLinha.permissionaria_id, func.count(AutoLinha.id))
            .filter(AutoLinha.ativo.is_(True))
            .group_by(AutoLinha.permissionaria_id)
            .all()
        )

    autos_por_empresa = indexar_autos_por_empresa(universos, operadores)
    for tipo_value, por_empresa in autos_por_empresa.items():
        print(f"  frota indexada '{tipo_value}': {len(por_empresa)} empresas")
    print()

    # Reclamações regulares inseridas sem nenhum auto vinculado.
    sem_autos: list[dict] = []
    etapas_match: list[str] = []   # etapa que resolveu a empresa, por linha regular

    # ── Fase 2: processar linha a linha, cada uma com sua própria sessão ──────
    for idx, row in df.iterrows():
        def _pula(motivo: str):
            idx_nao_lancados.append(idx)
            motivos[idx] = motivo
            stats["puladas"] += 1

        # ── 1. Protocolo ──────────────────────────────────────────────────────
        protocolo = _val(row, "PROTOCOLO")
        # Remove sufixo ".0" gerado pelo Excel ao converter número para float
        if protocolo and protocolo.endswith(".0"):
            protocolo = protocolo[:-2]
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
        empresa_nome = _val(row, "NOME DA EMPRESA BANCO")

        perm_id: int | None = None
        etapa_match = "nao_aplicavel"
        if is_regular:
            perm_id, etapa_match = resolver_permissionaria(
                row, tipo_servico, universos, perm_by_cnpj)
            etapas_match.append(etapa_match)

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
        data_resposta_raw = _to_date(row.get("DATA R."))
        status_csv = _norm_upper(_val(row, "STATUS") or "")

        if limite_resposta is None:
            base = data_entrada or date.today()
            limite_resposta = base + timedelta(days=PRAZO_PADRAO_DIAS)

        # Resolve data_resposta com fallback e regras de expurgo
        if data_resposta_raw is None:
            if status_csv == "NO PRAZO":
                data_resposta = limite_resposta
            else:
                _pula(f"DATA R. vazia e STATUS='{status_csv or 'vazio'}' — expurgado")
                continue
        elif data_resposta_raw.year < 2024:
            if status_csv == "NO PRAZO":
                data_resposta = limite_resposta
            else:
                _pula(f"DATA R. inválida ({data_resposta_raw}) e STATUS='{status_csv}' — expurgado")
                continue
        else:
            data_resposta = data_resposta_raw

        criado_em = (
            datetime(data_entrada.year, data_entrada.month, data_entrada.day)
            if data_entrada else datetime.now()
        )
        concluido_em = datetime(data_resposta.year, data_resposta.month, data_resposta.day)

        sei = _val(row, "N° SEI")
        conteudo = sei if sei else "SEM DADOS"

        # ── 8. Resolver autos (somente leitura) ───────────────────────────
        autos: list[dict] = []
        if is_regular:
            autos = resolver_autos(
                row, tipo_servico, perm_id, origem_ibge, destino_ibge,
                operadores, autos_por_empresa,
            )
            if not autos:
                sem_autos.append(_registro_sem_auto(
                    protocolo, row, tipo_servico, perm_id, etapa_match,
                    origem_ibge, destino_ibge, autos_por_perm,
                ))

        # ── 9. Inserir no banco (sessão própria por linha) ────────────────
        try:
            if not dry_run:
                with db_session() as session:
                    ouvidoria = Ouvidoria(
                        protocolo=protocolo,
                        conteudo=conteudo,
                        prazo=limite_resposta,
                        prazo_permissionaria=None,
                        status=StatusOuvidoria.CONCLUIDO,
                        criado_por_id=admin_id,
                        criado_em=criado_em,
                        concluido_em=concluido_em,
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

                    if autos:
                        pontuacao = calcular_pontuacao_auto(len(autos))
                        for auto in autos:
                            session.add(ReclamacaoAuto(
                                reclamacao_id=reclamacao.id,
                                auto_id=auto["id"],
                                pontuacao=pontuacao,
                            ))

                    session.add(RespostaTecnica(
                        ouvidoria_id=ouvidoria.id,
                        tecnico_id=tecnico_legados_id,
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

    if sem_autos:
        pd.DataFrame(sem_autos).to_excel(OUT_SEM_AUTOS, index=False)
        print(f"  Sem autos:    {OUT_SEM_AUTOS}")
    else:
        print("  Toda reclamação regular ficou com auto — arquivo não gerado.")

    # ── Relatório final ───────────────────────────────────────────────────────
    print(f"\nResultado:")
    print(f"  Inseridas:   {stats['inseridas']}")
    print(f"  Puladas:     {stats['puladas']}")
    print(f"  Duplicadas:  {stats['duplicadas']}")
    print(f"  Erros:       {stats['erros']}")

    print(f"\nResolução de empresa nas linhas regulares:")
    for etapa, qtd in Counter(etapas_match).most_common():
        print(f"  {qtd:>5}x  {etapa}")

    print(f"\nReclamações regulares inseridas sem nenhum auto: {len(sem_autos)}")
    if sem_autos:
        for causa, qtd in Counter(r["CAUSA"] for r in sem_autos).most_common():
            print(f"  {qtd:>5}x  {causa}")

if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv

    if not dry_run:
        print("=== Inicializando banco ===")
        init_db()
        print()

    print("=== Importando dados históricos ===")
    seed_dados_antigos(dry_run=dry_run)
    print()
    print("Concluído (dry-run, nada gravado)." if dry_run else "Concluído.")
