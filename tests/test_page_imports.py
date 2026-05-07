"""Verifica que todos os 'from api.client.X import Y' nas pages existem de fato.

Pega o exato erro que tivemos: ImportError: cannot import name 'carregar_municipios'
from 'api.client.autos_client'.

Não executa o código das pages (evita dependência do Streamlit rodando),
apenas inspeciona os imports via AST e confere que cada nome existe no módulo.
"""
import ast
import importlib
from pathlib import Path

import pytest

PAGES_DIR = Path(__file__).parent.parent / "pages"
PAGE_FILES = sorted(PAGES_DIR.glob("*.py"))


def _extrair_imports_api_client(filepath: Path) -> list[tuple[str, list[str]]]:
    """Retorna lista de (modulo, [nomes]) para imports do tipo 'from api.client.X import Y'."""
    tree = ast.parse(filepath.read_text(encoding="utf-8"))
    resultado = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("api.client"):
            nomes = [alias.name for alias in node.names]
            resultado.append((node.module, nomes))
    return resultado


@pytest.mark.parametrize("page_file", PAGE_FILES, ids=[p.name for p in PAGE_FILES])
def test_imports_api_client_existem(page_file):
    """Cada nome importado de api.client.* deve existir no módulo correspondente."""
    imports = _extrair_imports_api_client(page_file)
    if not imports:
        pytest.skip(f"{page_file.name} não tem imports de api.client.*")

    erros = []
    for modulo, nomes in imports:
        try:
            mod = importlib.import_module(modulo)
        except ImportError as e:
            erros.append(f"Módulo '{modulo}' não pôde ser importado: {e}")
            continue
        for nome in nomes:
            if not hasattr(mod, nome):
                erros.append(f"{page_file.name}: '{nome}' não existe em '{modulo}'")

    assert not erros, "\n".join(erros)
