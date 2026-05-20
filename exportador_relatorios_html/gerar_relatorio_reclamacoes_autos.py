#!/usr/bin/env python3
"""Gera relatorio de pontuacao de autos por subcategoria em 2025."""

import sys
from datetime import date
from pathlib import Path
from sqlalchemy import func

# Adicionar raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import db_session
from models import AutoLinha, Ouvidoria, Reclamacao, ReclamacaoAuto, Subcategoria


def consultar_auto(session, numero_auto: str):
    """Busca pontuacao total de um auto por subcategoria em 2025."""
    auto = session.query(AutoLinha).filter(
        AutoLinha.numero == numero_auto
    ).first()

    if not auto:
        return None

    inicio_2025 = date(2025, 1, 1)
    fim_2025 = date(2025, 12, 31)

    resultado = session.query(
        Subcategoria.nome.label("subcategoria"),
        func.count(ReclamacaoAuto.reclamacao_id).label("quantidade"),
        func.sum(ReclamacaoAuto.pontuacao).label("pontuacao_total")
    ).join(
        Reclamacao,
        Reclamacao.id == ReclamacaoAuto.reclamacao_id
    ).join(
        Subcategoria,
        Subcategoria.id == Reclamacao.subcategoria_id
    ).join(
        Ouvidoria,
        Ouvidoria.id == Reclamacao.ouvidoria_id
    ).filter(
        ReclamacaoAuto.auto_id == auto.id,
        Ouvidoria.criado_em >= inicio_2025,
        Ouvidoria.criado_em <= fim_2025
    ).group_by(
        Subcategoria.id,
        Subcategoria.nome
    ).order_by(
        func.sum(ReclamacaoAuto.pontuacao).desc()
    ).all()

    return {
        "auto": auto,
        "resultado": resultado,
    }


def gerar_relatorio_markdown(autos_numeros: list[str]) -> str:
    """Gera relatorio em markdown com dados dos autos."""
    with db_session() as session:
        dados_autos = []

        for numero_auto in autos_numeros:
            dados = consultar_auto(session, numero_auto)
            if dados:
                dados_autos.append(dados)

        if not dados_autos:
            return "Nenhum auto encontrado."

        # Construir markdown
        md = f"# Relatorio de Reclamacoes por Autos\n\n"
        md += f"**Data de Geracao:** {date.today().strftime('%d/%m/%Y')}\n"
        md += f"**Periodo Analisado:** 2025\n"
        md += f"**Quantidade de Autos:** {len(dados_autos)}\n\n"
        md += "---\n\n"

        total_geral = 0.0
        total_reclamacoes_geral = 0

        for dados in dados_autos:
            auto = dados["auto"]
            resultado = dados["resultado"]

            md += f"## Auto {auto.numero}\n\n"
            md += f"- **Denominacao A:** {auto.denominacao_a}\n"
            md += f"- **Denominacao B:** {auto.denominacao_b}\n"
            md += f"- **Tipo:** {auto.tipo.value if auto.tipo else 'N/A'}\n"
            md += f"- **Status:** {'Ativo' if auto.ativo else 'Inativo'}\n\n"

            if not resultado:
                md += "Nenhuma reclamacao encontrada em 2025.\n\n"
                md += "---\n\n"
                continue

            total_pontos = sum(float(r.pontuacao_total) for r in resultado if r.pontuacao_total)
            total_reclamacoes = sum(r.quantidade for r in resultado)

            total_geral += total_pontos
            total_reclamacoes_geral += total_reclamacoes

            md += "### Resumo\n\n"
            md += f"- **Total de Pontos:** {total_pontos:.4f}\n"
            md += f"- **Total de Reclamacoes:** {total_reclamacoes}\n\n"

            md += "### Distribuicao por Subcategoria\n\n"
            md += "| Assunto | Qtd | Pontos | % |\n"
            md += "|---------|-----|--------|-----|\n"

            for row in resultado:
                subcategoria = row.subcategoria or "Sem assunto"
                qtd = row.quantidade
                pontos = float(row.pontuacao_total) if row.pontuacao_total else 0.0
                percentual = (pontos / total_pontos * 100) if total_pontos else 0
                md += f"| {subcategoria} | {qtd} | {pontos:.4f} | {percentual:.2f}% |\n"

            md += "\n"
            md += "---\n\n"

        # Resumo geral
        md += "## Resumo Geral\n\n"
        md += f"- **Total de Autos Analisados:** {len(dados_autos)}\n"
        md += f"- **Total de Pontos:** {total_geral:.4f}\n"
        md += f"- **Total de Reclamacoes:** {total_reclamacoes_geral}\n"

        return md


def main():
    if len(sys.argv) < 2:
        print("Uso: python gerar_relatorio_reclamacoes_autos.py <auto1> [auto2] [auto3] ...")
        print("Exemplo: python gerar_relatorio_reclamacoes_autos.py 9207A 9208A")
        sys.exit(1)

    autos = sys.argv[1:]
    md_content = gerar_relatorio_markdown(autos)

    # Salvar arquivo na pasta do script
    script_dir = Path(__file__).parent
    nome_arquivo = f"reclamacoes_por_autos_{len(autos)}.md"
    output_path = script_dir / nome_arquivo

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"Relatorio gerado com sucesso: {output_path}")


if __name__ == "__main__":
    main()
