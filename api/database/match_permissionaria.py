"""Resolução de permissionária a partir do nome livre digitado na ouvidoria.

O cadastro de permissionárias tem ~2.000 empresas, mas apenas ~93 possuem auto
de linha ativo — o resto vem da planilha de fretamento metropolitano
(construtoras, locadoras de van, transporte próprio). Casar o nome contra o
cadastro inteiro produz acertos em empresas que jamais terão auto a imputar,
e o seed então busca autos filtrando por essa empresa e não encontra nada.

Por isso o match aqui roda sempre dentro de um *universo* restrito: as empresas
que têm ao menos um auto ativo do tipo de serviço da linha. São 80 no regular
intermunicipal e 19 no metropolitano, o que também torna seguro aplicar uma
etapa final por similaridade — inviável no cadastro completo.

Uso:
    universo = construir_universo(session, TipoServico.REGULAR_INTERMUNICIPAL)
    perm_id, etapa = casar("GUERINO SEISCENTOS", universo)
"""
import difflib
import re
import unicodedata

from api.models import AutoLinha, Permissionaria


# ── Overrides manuais ─────────────────────────────────────────────────────────
# chave = _norm(EMPRESA) do campo livre, valor = CNPJ (14 dígitos) da correta.
# Só entram aqui nomes que nenhuma etapa resolve e cuja empresa foi conferida
# no cadastro, com auto ativo do tipo da reclamação.
OVERRIDES: dict[str, str] = {
    "VB TRANSPRTES": "46014122000138",               # VB TRANSPORTES E TURISMO LTDA
    "VIACAO TRANSPEN": "75156265000182",             # TRANSPEN-TRANSPORTE COLETIVO E ENCOMENDAS
    "EMPRESA GUERINO SEISCENTOS": "72543978000100",  # GUERINO SEISCENTO TRANSPORTES S/A
    "VIACAO GUERINO": "72543978000100",              # GUERINO SEISCENTO TRANSPORTES S/A
}


# ── Normalização ──────────────────────────────────────────────────────────────

def _norm(s) -> str:
    """Maiúsculas, sem acento, sem pontuação, espaços colapsados."""
    if not isinstance(s, str):
        return ""
    nfkd = unicodedata.normalize("NFKD", s)
    out = "".join(c for c in nfkd if not unicodedata.combining(c)).upper()
    out = re.sub(r"[^A-Z0-9\s]", " ", out)
    return re.sub(r"\s+", " ", out).strip()


def _norm_compact(s) -> str:
    return _norm(s).replace(" ", "")


SUFIXOS = [
    "LTDA", "SA", "S A", "EPP", "ME", "EIRELI", "SS", "SCA",
    "LIMITADA", "SOCIEDADE ANONIMA", "TRANSPORTES", "TURISMO",
    "VIACAO", "ONIBUS", "AUTOCARRO", "TRANSPORTE",
]

STOP = {"DE", "DA", "DO", "DAS", "DOS", "E", "A", "O", "AS", "OS", "EM", "NO", "NA"}


def _remove_sufixos(s) -> str:
    """Remove termos jurídicos e genéricos do ramo ('LTDA', 'VIACAO', ...)."""
    out = _norm(s)
    for suf in sorted(SUFIXOS, key=len, reverse=True):
        out = re.sub(rf"\b{re.escape(suf)}\b", " ", out)
    return re.sub(r"\s+", " ", out).strip()


def _palavras(s: str) -> set[str]:
    return {w for w in s.split() if len(w) >= 3 and w not in STOP}


# ── Universo ──────────────────────────────────────────────────────────────────

def construir_universo(session, tipo_servico) -> list[dict]:
    """Permissionárias com ≥1 auto ativo do tipo informado, já normalizadas.

    `tipo_servico` aceita o enum TipoServico ou o seu .value.
    """
    tipo = getattr(tipo_servico, "value", tipo_servico)

    perms = (
        session.query(Permissionaria)
        .join(AutoLinha, AutoLinha.permissionaria_id == Permissionaria.id)
        .filter(AutoLinha.tipo == tipo, AutoLinha.ativo.is_(True))
        .distinct()
        .all()
    )
    return [_preparar(p.id, p.cnpj, p.nome, p.nome_fantasia) for p in perms]


def _preparar(perm_id, cnpj, nome, nome_fantasia) -> dict:
    """Monta a entrada do universo com todas as variantes pré-calculadas."""
    entrada = {"id": perm_id, "cnpj": (cnpj or "").strip(),
               "nome": nome, "nome_fantasia": nome_fantasia}
    for campo, valor in (("nome", nome), ("fantasia", nome_fantasia)):
        entrada[f"{campo}_norm"] = _norm(valor)
        entrada[f"{campo}_compact"] = _norm_compact(valor)
        entrada[f"{campo}_sem_suf"] = _remove_sufixos(valor)
    return entrada


# ── Match ─────────────────────────────────────────────────────────────────────

LIMIAR_SIMILARIDADE = 0.86
FOLGA_SIMILARIDADE = 0.05


def casar(empresa, universo: list[dict]) -> tuple[int | None, str]:
    """Resolve `empresa` (texto livre) num perm_id dentro do universo.

    Devolve (perm_id, etapa). `etapa` identifica o que resolveu, para o
    relatório do seed; é "nenhuma" quando não há match.
    """
    if not isinstance(empresa, str) or not empresa.strip():
        return None, "nenhuma"
    if not universo:
        return None, "nenhuma"

    emp_norm = _norm(empresa)
    emp_compact = _norm_compact(empresa)
    emp_sem_suf = _remove_sufixos(empresa)

    # 0. override manual
    cnpj_override = OVERRIDES.get(emp_norm)
    if cnpj_override:
        for e in universo:
            if e["cnpj"] == cnpj_override:
                return e["id"], "override"

    # 1. nome normalizado exato
    for campo in ("nome_norm", "fantasia_norm"):
        achados = [e for e in universo if e[campo] and e[campo] == emp_norm]
        if achados:
            return achados[0]["id"], "exato"

    # 2. compacto (ignora espaçamento)
    for campo in ("nome_compact", "fantasia_compact"):
        achados = [e for e in universo if e[campo] and e[campo] == emp_compact]
        if achados:
            return achados[0]["id"], "compacto"

    # 3. sem sufixos jurídicos
    if emp_sem_suf:
        for campo in ("nome_sem_suf", "fantasia_sem_suf"):
            achados = [e for e in universo if e[campo] and e[campo] == emp_sem_suf]
            if achados:
                return achados[0]["id"], "sem_sufixo"

    # 4. empresa contida no nome cadastrado, resultado único
    for campo in ("nome_norm", "fantasia_norm"):
        achados = [e for e in universo if e[campo] and emp_norm in e[campo]]
        if len(achados) == 1:
            return achados[0]["id"], "contido_no_cadastro"

    # 5. nome cadastrado contido na empresa, resultado único.
    #    Exige >1 palavra significativa no lado cadastrado: no cadastro completo
    #    esta etapa levava 23 variantes para a empresa cujo nome_fantasia é
    #    "TRANSPORTE", porque a guarda original era só len > 4.
    for campo in ("nome_norm", "fantasia_norm"):
        achados = [
            e for e in universo
            if e[campo] and len(e[campo]) > 4 and e[campo] in emp_norm
            and len(_palavras(e[campo])) > 1
        ]
        if len(achados) == 1:
            return achados[0]["id"], "cadastro_contido"

    # 6. prefixo compacto, resultado único
    for campo in ("nome_compact", "fantasia_compact"):
        achados = [
            e for e in universo
            if e[campo] and (emp_compact.startswith(e[campo])
                             or e[campo].startswith(emp_compact))
        ]
        if len(achados) == 1:
            return achados[0]["id"], "prefixo"

    emp_words = _palavras(emp_norm)

    # 7a. Jaccard das palavras significativas
    if len(emp_words) >= 2:
        melhor = _melhor_por_score(
            universo, lambda alvo: _jaccard(emp_words, alvo), minimo=0.6)
        if melhor:
            return melhor, "jaccard"

    # 7b. recall das palavras da empresa
    if len(emp_words) >= 2:
        melhor = _melhor_por_score(
            universo, lambda alvo: _recall(emp_words, alvo), minimo=0.75)
        if melhor:
            return melhor, "recall"

    # 8. similaridade de string. Só é segura porque o universo tem ~80 empresas.
    #    Recupera erro de digitação de uma letra: PASSARO MARROM -> MARRON,
    #    GUERINO SEISCENTOS -> SEISCENTO.
    perm_id = _por_similaridade(emp_sem_suf or emp_norm, universo)
    if perm_id:
        return perm_id, "similaridade"

    return None, "nenhuma"


def _jaccard(emp_words: set[str], alvo: str) -> float:
    db_words = _palavras(alvo)
    if not db_words:
        return 0.0
    return len(emp_words & db_words) / len(emp_words | db_words)


def _recall(emp_words: set[str], alvo: str) -> float:
    db_words = _palavras(alvo)
    if not db_words:
        return 0.0
    return len(emp_words & db_words) / len(emp_words)


def _melhor_por_score(universo, score, minimo: float) -> int | None:
    """Maior score ≥ minimo, exigindo vencedor único entre as permissionárias."""
    for campo in ("nome_norm", "fantasia_norm"):
        pontuados = [(score(e[campo]), e["id"]) for e in universo if e[campo]]
        if not pontuados:
            continue
        topo = max(p for p, _ in pontuados)
        if topo < minimo:
            continue
        vencedores = {pid for p, pid in pontuados if p == topo}
        if len(vencedores) == 1:
            return vencedores.pop()
    return None


def _por_similaridade(alvo: str, universo) -> int | None:
    """Melhor razão de similaridade, com folga obrigatória sobre o segundo.

    A folga evita escolher entre duas empresas de nome parecido (p.ex.
    PRINCESA DO NORTE x PRINCESA D OESTE): no empate devolve None, e o caso
    aparece no relatório em vez de virar atribuição errada.
    """
    if not alvo:
        return None

    pontuados: list[tuple[float, int]] = []
    for e in universo:
        for campo in ("nome_sem_suf", "fantasia_sem_suf"):
            valor = e[campo]
            if valor:
                razao = difflib.SequenceMatcher(None, alvo, valor).ratio()
                pontuados.append((razao, e["id"]))
    if not pontuados:
        return None

    pontuados.sort(key=lambda x: x[0], reverse=True)
    melhor_razao, melhor_id = pontuados[0]
    if melhor_razao < LIMIAR_SIMILARIDADE:
        return None

    segunda = next((p for p, pid in pontuados if pid != melhor_id), 0.0)
    if melhor_razao - segunda < FOLGA_SIMILARIDADE:
        return None
    return melhor_id
