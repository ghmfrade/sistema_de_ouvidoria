"""Gerador de HTML auto-contido para o Resumo da Ouvidoria."""

import html
from datetime import datetime

from api.repositories.ouvidoria_repo import get_ouvidoria_completa

_CSS = """
body{font-family:Arial,sans-serif;max-width:1000px;margin:0 auto;padding:20px;color:#333;}
h1{font-size:1.4em;margin-bottom:4px;}
hr{border:none;border-top:1px solid #ddd;margin:16px 0;}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;}
.card{border:1px solid #ddd;border-radius:8px;padding:16px;}
h2{font-size:1.05em;color:#444;margin:0 0 10px 0;border-bottom:1px solid #eee;padding-bottom:6px;}
.field{margin:5px 0;font-size:.95em;}
.label{font-weight:bold;}
.caption{font-size:.82em;color:#888;margin-bottom:3px;}
.rec-sep{border:none;border-top:1px solid #eee;margin:10px 0;}
.pre{white-space:pre-wrap;word-wrap:break-word;margin:0;}
@media print{.card{break-inside:avoid;}}
"""


def _e(val) -> str:
    if val is None:
        return "—"
    return html.escape(str(val))


def _fmt_data(d) -> str:
    if d is None:
        return "—"
    if isinstance(d, datetime):
        return d.strftime("%d/%m/%Y")
    return d.strftime("%d/%m/%Y")


def gerar_html_resumo(ouvidoria_id: int) -> str:
    """Gera string HTML auto-contida com todos os dados da ouvidoria."""
    o = get_ouvidoria_completa(ouvidoria_id)
    if not o:
        return "<html><body><p>Ouvidoria não encontrada.</p></body></html>"

    p: list[str] = []

    def w(s: str) -> None:
        p.append(s)

    w(f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Resumo Ouvidoria #{o['id']}</title>
<style>{_CSS}</style>
</head>
<body>
<h1>📋 Resumo da Ouvidoria #{o['id']}</h1>
<hr>
<div class="grid2">""")

    # ── Card Ouvidoria ────────────────────────────────────────────────────────
    w('<div class="card"><h2>Ouvidoria</h2>')
    w(f'<p class="field"><span class="label">Protocolo:</span> {_e(o["protocolo"])}</p>')
    w(f'<p class="field"><span class="label">Status:</span> {_e(o["status"])}</p>')
    w(f'<p class="field"><span class="label">Prazo de resposta:</span> {_fmt_data(o["prazo"])}</p>')
    if o.get("concluido_em"):
        w(f'<p class="field"><span class="label">Data respondida:</span> {_fmt_data(o["concluido_em"])}</p>')
    w("</div>")

    # ── Card Reclamações ──────────────────────────────────────────────────────
    w('<div class="card"><h2>Reclamações</h2>')
    reclamacoes = o.get("reclamacoes") or []
    if reclamacoes:
        for i, rec in enumerate(reclamacoes):
            if i > 0:
                w('<hr class="rec-sep">')
            w(f'<p class="field"><span class="label">Categoria:</span> {_e(rec.get("categoria_nome"))}</p>')
            w(f'<p class="field"><span class="label">Subcategoria:</span> {_e(rec.get("subcategoria_nome"))}</p>')
            if rec.get("tipo_servico"):
                w(f'<p class="field"><span class="label">Tipo de serviço:</span> {_e(rec["tipo_servico"])}</p>')
            if rec.get("empresa_fretamento"):
                w(f'<p class="field"><span class="label">Empresa de fretamento:</span> {_e(rec["empresa_fretamento"])}</p>')
            w(f'<p class="field"><span class="label">Descrição:</span> {_e(rec.get("descricao"))}</p>')
            w(f'<p class="field"><span class="label">Embarque:</span> {_e(rec.get("local_embarque"))}</p>')
            w(f'<p class="field"><span class="label">Desembarque:</span> {_e(rec.get("local_desembarque"))}</p>')
            autos = rec.get("autos") or []
            numeros = ", ".join(a["numero"] for a in autos if a.get("numero"))
            w(f'<p class="field"><span class="label">Nº dos Autos:</span> {_e(numeros or None)}</p>')
    else:
        w("<p>Sem reclamações vinculadas.</p>")
    w("</div>")

    w("</div>")  # end .grid2

    # ── Manifestação do usuário ───────────────────────────────────────────────
    w('<div class="card"><h2>Manifestação do usuário</h2>')
    w(f'<p class="pre">{_e(o.get("conteudo"))}</p>')
    w("</div>")

    # ── Manifestação da permissionária ────────────────────────────────────────
    respostas_perm = o.get("respostas_permissionaria") or []
    if respostas_perm:
        w('<div class="card"><h2>Manifestação da permissionária</h2>')
        for rp in respostas_perm:
            w(f'<p class="caption">Registrado por {_e(rp.get("registrado_por_nome", "—"))} em {_fmt_data(rp.get("data_resposta"))}</p>')
            w(f'<p class="pre">{_e(rp.get("conteudo"))}</p>')
        w("</div>")

    # ── Manifestação técnica ──────────────────────────────────────────────────
    w('<div class="card"><h2>Manifestação técnica</h2>')
    atribuicoes = o.get("atribuicoes") or []
    if atribuicoes:
        nomes = ", ".join(_e(a["tecnico_nome"]) for a in atribuicoes)
        w(f'<p class="field"><span class="label">Técnico(s) responsável(is):</span> {nomes}</p>')
    else:
        w('<p class="field"><span class="label">Técnico(s) responsável(is):</span> —</p>')

    respostas_tec = o.get("respostas_tecnicas") or []
    if respostas_tec:
        for rt in respostas_tec:
            w(f'<p class="caption">{_e(rt.get("tecnico_nome", "—"))} — {_fmt_data(rt.get("data_resposta"))}</p>')
            w(f'<p class="pre">{_e(rt.get("texto_resposta"))}</p>')
            w('<hr class="rec-sep">')
    else:
        w("<p><em>Nenhuma resposta técnica registrada.</em></p>")
    w("</div>")

    # ── Anexos ────────────────────────────────────────────────────────────────
    anexos = o.get("anexos") or []
    if anexos:
        w('<div class="card"><h2>Anexos</h2><ul>')
        for an in anexos:
            tamanho_kb = round(an["tamanho"] / 1024, 1) if an.get("tamanho") else "?"
            w(f'<li>📎 {_e(an["nome_arquivo"])} ({tamanho_kb} KB)</li>')
        w("</ul></div>")

    w("</body></html>")
    return "".join(p)
