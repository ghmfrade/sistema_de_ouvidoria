"""Autos de linha operados por terceiro via termo de requisição.

Quando uma delegatária deixa de operar um auto, a ARTESP emite termo de
requisição e outra permissionária assume a operação. O auto continua
registrado na delegatária, mas o usuário reclama da empresa que viu no ônibus.

Sem esse mapa, a reclamação nomeia a operadora, a busca de autos filtra por ela
e não acha nada — o auto está na delegatária. O mapa serve apenas para
*encontrar* o auto: a pontuação continua no auto e, portanto, na delegatária.

Fonte: pasta_seed/termos_requisicao.xlsx
  Autos | Denominação da Linha | Característica | Delegatária do Autos
        | Nome da Operadora- operando por termo de requisição
        | emissão do ultimo termo | validade

As datas de emissão e validade são ignoradas: o mapa vale para todo o período
coberto pelo seed.
"""
import os
import re

import pandas as pd

from api.models import AutoLinha, TipoServico
from api.database.match_permissionaria import casar, construir_universo

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TERMOS_REQUISICAO = os.path.join(BASE_DIR, "pasta_seed", "termos_requisicao.xlsx")

COL_AUTO = "Autos"
COL_DELEGATARIA = "Delegatária do Autos"
COL_OPERADORA = "Nome da Operadora- operando por termo de requisição"


def parse_numero_auto(valor) -> str | None:
    """Converte o 'Autos' da planilha no `numero` usado em autos_linha.

    O seed de autos monta numero = str(nº Autos) + Iti, sem zeros à esquerda.
    A planilha de termos traz o número com o itinerário e a seção:

        '3323-A-1' → '3323A'
        '0012-A-2' → '12A'
        '8033'     → '8033A'   (itinerário omitido, assume 'A')
    """
    texto = re.sub(r"\s+", "", str(valor).strip().upper())
    match = re.match(r"^(\d+)(?:-?([A-Z]))?", texto)
    if not match:
        return None
    numero = str(int(match.group(1)))      # remove zeros à esquerda
    itinerario = match.group(2) or "A"
    return numero + itinerario


def carregar_operadores(session, verbose: bool = True) -> dict[int, int]:
    """Mapa auto_id → permissionaria_id de quem opera por termo de requisição.

    Só inclui autos ativos existentes no banco e operadoras resolvíveis no
    universo do regular. Devolve {} se a planilha não existir.
    """
    if not os.path.exists(TERMOS_REQUISICAO):
        if verbose:
            print(f"  [aviso] {os.path.basename(TERMOS_REQUISICAO)} não encontrado — "
                  "termos de requisição ignorados.")
        return {}

    df = pd.read_excel(TERMOS_REQUISICAO)
    df.columns = [str(c).strip() for c in df.columns]

    faltando = [c for c in (COL_AUTO, COL_OPERADORA) if c not in df.columns]
    if faltando:
        raise RuntimeError(
            f"{os.path.basename(TERMOS_REQUISICAO)} sem as colunas {faltando}. "
            f"Colunas encontradas: {list(df.columns)}"
        )

    # numero → [auto_id] dos autos ativos
    autos_por_numero: dict[str, list[int]] = {}
    for auto_id, numero in session.query(AutoLinha.id, AutoLinha.numero).filter(
            AutoLinha.ativo.is_(True)).all():
        autos_por_numero.setdefault(numero.strip().upper(), []).append(auto_id)

    # as operadoras são sempre empresas do regular; o universo dos dois tipos
    # cobre tanto intermunicipal quanto metropolitano
    universo = construir_universo(session, TipoServico.REGULAR_INTERMUNICIPAL)
    vistos = {e["id"] for e in universo}
    universo += [e for e in construir_universo(session, TipoServico.REGULAR_METROPOLITANO)
                 if e["id"] not in vistos]

    operadores: dict[int, int] = {}
    cache_operadora: dict[str, int | None] = {}
    autos_ausentes: list[str] = []
    operadoras_nao_resolvidas: set[str] = set()

    for _, row in df.iterrows():
        numero = parse_numero_auto(row[COL_AUTO])
        if not numero:
            continue

        auto_ids = autos_por_numero.get(numero)
        if not auto_ids:
            autos_ausentes.append(f"{row[COL_AUTO]} -> {numero}")
            continue

        operadora = row[COL_OPERADORA]
        if not isinstance(operadora, str) or not operadora.strip():
            continue
        chave = operadora.strip()
        if chave not in cache_operadora:
            perm_id, _etapa = casar(chave, universo)
            cache_operadora[chave] = perm_id
        perm_id = cache_operadora[chave]

        if perm_id is None:
            operadoras_nao_resolvidas.add(chave)
            continue

        for auto_id in auto_ids:
            operadores[auto_id] = perm_id

    if verbose:
        print(f"  {len(df)} linhas na planilha de termos de requisição.")
        print(f"  {len(operadores)} autos mapeados para operadora por requisição.")
        if autos_ausentes:
            print(f"  [aviso] {len(autos_ausentes)} auto(s) da planilha não existem "
                  f"ativos no banco: {', '.join(autos_ausentes)}")
        if operadoras_nao_resolvidas:
            print(f"  [aviso] {len(operadoras_nao_resolvidas)} operadora(s) não "
                  f"resolvida(s): {', '.join(sorted(operadoras_nao_resolvidas))}")

    return operadores
