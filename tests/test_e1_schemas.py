"""Etapa 1 — verifica que os schemas Pydantic instanciam corretamente
a partir dos dados que os repositórios retornam hoje.

Não sobe a API; testa apenas a camada de schemas.
"""
import pytest
from repositories.catalog_repo import (
    get_categorias,
    get_subcategorias,
    get_gerencias,
    get_coordenacoes,
    get_tecnicos_ativos,
    get_todas_permissionarias,
)
from repositories.municipios_repo import get_municipios_sp
from repositories.ouvidoria_repo import get_ouvidorias, get_ouvidoria_completa
from api.schemas.catalog import (
    CategoriaSchema, SubcategoriaSchema, GerenciaSchema,
    CoordenacaoSchema, UsuarioSchema, PermissionariaSchema, MunicipioSchema,
)
from api.schemas.ouvidoria import (
    OuvidoriaResumoSchema, OuvidoriaDetalheSchema,
)
from tests.conftest import OUVIDORIA_ID_FIXTURE


# ── Catálogo ──────────────────────────────────────────────────────────────────

def test_schema_categorias():
    dados = get_categorias()
    assert len(dados) > 0, "Banco não tem categorias — execute o seed"
    parsed = [CategoriaSchema(**d) for d in dados]
    assert all(p.id > 0 for p in parsed)


def test_schema_subcategorias():
    categorias = get_categorias()
    if not categorias:
        pytest.skip("Sem categorias no banco")
    cat_id = categorias[0]["id"]
    dados = get_subcategorias(cat_id)
    parsed = [SubcategoriaSchema(**d) for d in dados]
    assert all(p.categoria_id == cat_id for p in parsed)


def test_schema_gerencias():
    dados = get_gerencias()
    assert len(dados) > 0
    parsed = [GerenciaSchema(**d) for d in dados]
    assert all(isinstance(p.nome, str) for p in parsed)


def test_schema_coordenacoes():
    dados = get_coordenacoes()
    parsed = [CoordenacaoSchema(**d) for d in dados]
    assert isinstance(parsed, list)


def test_schema_tecnicos():
    dados = get_tecnicos_ativos()
    parsed = [UsuarioSchema(**d) for d in dados]
    assert all(p.tipo == "tecnico" for p in parsed)


def test_schema_permissionarias():
    dados = get_todas_permissionarias()
    assert len(dados) > 0
    parsed = [PermissionariaSchema(**d) for d in dados]
    assert all(isinstance(p.nome, str) for p in parsed)


def test_schema_municipios():
    dados = get_municipios_sp()
    assert len(dados) > 0
    parsed = [MunicipioSchema(**d) for d in dados]
    assert all(p.estado == "SP" for p in parsed)


# ── Ouvidorias ────────────────────────────────────────────────────────────────

def test_schema_ouvidoria_resumo():
    dados = get_ouvidorias(ocultar_concluidos=False)
    assert len(dados) > 0, "Banco não tem ouvidorias — execute o seed"
    parsed = [OuvidoriaResumoSchema(**d) for d in dados]
    assert all(p.id > 0 for p in parsed)


def test_schema_ouvidoria_detalhe():
    dado = get_ouvidoria_completa(OUVIDORIA_ID_FIXTURE)
    assert dado is not None, (
        f"Ouvidoria {OUVIDORIA_ID_FIXTURE} não encontrada. "
        "Ajuste TEST_OUVIDORIA_ID no .env"
    )
    parsed = OuvidoriaDetalheSchema(**dado)
    assert parsed.id == OUVIDORIA_ID_FIXTURE
    assert isinstance(parsed.reclamacoes, list)
    assert isinstance(parsed.atribuicoes, list)
    assert isinstance(parsed.respostas_tecnicas, list)
    assert isinstance(parsed.respostas_permissionaria, list)
    assert isinstance(parsed.anexos, list)
