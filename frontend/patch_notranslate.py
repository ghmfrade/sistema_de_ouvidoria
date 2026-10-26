"""Impede o Chrome de traduzir automaticamente a interface.

O index.html do Streamlit é servido com `<html lang="en">` e sem meta de
notranslate. O Chrome lê o idioma declarado como inglês, vê o texto em
português e traduz para o pt-BR do usuário — alucinando os termos que não estão
no vocabulário do modelo. "Ouvidoria" virava "sânscrito", "slandoria",
"shandoria" e "Óleoria", cada hora de um jeito, e "Dashboard" virava "Painel".

A correção precisa estar no HTML inicial, antes de o Chrome decidir traduzir;
injetar JS depois do carregamento não desfaz a tradução já em curso.

Roda no build (ver frontend/Dockerfile) e é idempotente. Falha o build se o
Streamlit mudar o markup, para não voltar a publicar a interface traduzível em
silêncio.
"""
import pathlib
import sys

import streamlit

META = '<meta name="google" content="notranslate"/>'
HTML_ORIGINAL = '<html lang="en">'
HTML_CORRIGIDO = '<html lang="pt-BR" translate="no">'

arquivo = pathlib.Path(streamlit.__file__).parent / "static" / "index.html"
html = arquivo.read_text(encoding="utf-8")

if HTML_CORRIGIDO in html and META in html:
    print(f"notranslate: {arquivo} já corrigido")
    sys.exit(0)

if HTML_ORIGINAL not in html or "<head>" not in html:
    sys.exit(
        f"notranslate: markup inesperado em {arquivo} "
        f"(streamlit {streamlit.__version__}). Reveja o patch."
    )

html = html.replace(HTML_ORIGINAL, HTML_CORRIGIDO, 1)
html = html.replace("<head>", "<head>" + META, 1)
arquivo.write_text(html, encoding="utf-8")
print(f"notranslate: {arquivo} corrigido (streamlit {streamlit.__version__})")
