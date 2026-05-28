"""Fixtures globais de teste.

Usuários de teste são criados automaticamente no início da sessão e deletados
ao final. Nenhuma credencial de usuário real é usada ou guardada no código.

Convenção de nomenclatura de dados de teste:
    Todos os dados criados pelos testes usam o prefixo '_pytest_' no nome/email.
    Ao iniciar e ao encerrar a sessão, esses dados são removidos do banco.
    Isso garante limpeza mesmo após falhas que interromperam o teardown anterior.

Variáveis de ambiente necessárias no .env:
    JWT_SECRET_KEY      chave secreta para assinar JWT
    TEST_OUVIDORIA_ID   ID de uma ouvidoria existente no banco de dev (default: 1)
"""
import os
import uuid
import pytest
from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()

# Credenciais geradas para a sessão de teste (não pertencem a nenhum usuário real)
_SENHA_TESTE = "TestSenha@2025"
_EMAIL_GESTOR_TESTE  = f"_pytest_gestor_{uuid.uuid4().hex[:8]}@artesp.test"
_EMAIL_TECNICO_TESTE = f"_pytest_tecnico_{uuid.uuid4().hex[:8]}@artesp.test"

OUVIDORIA_ID_FIXTURE = int(os.environ.get("TEST_OUVIDORIA_ID", "1"))


def _limpar_dados_pytest():
    """Remove todos os dados de teste do banco (prefixo '_pytest_').

    Executado no início E no fim da sessão para garantir limpeza mesmo após
    falhas que abortaram o teardown anterior.
    """
    from database.connection import db_session
    with db_session() as s:
        # Ordem importa: remover dependentes antes dos pais
        s.execute(text("DELETE FROM subcategorias WHERE nome LIKE '_pytest_%'"))
        s.execute(text("DELETE FROM categorias   WHERE nome LIKE '_pytest_%'"))
        s.execute(text("DELETE FROM coordenacoes WHERE nome LIKE '_pytest_%'"))
        s.execute(text("DELETE FROM gerencias    WHERE nome LIKE '_pytest_%'"))
        s.execute(text(
            "DELETE FROM usuarios WHERE email LIKE '_pytest_%@artesp.test'"
        ))


# ── Criação e limpeza de usuários de teste ────────────────────────────────────

def _criar_usuario_teste(session, email: str, tipo: str, gerencia_id=None):
    from models import Usuario, TipoUsuario
    import bcrypt
    senha_hash = bcrypt.hashpw(_SENHA_TESTE.encode(), bcrypt.gensalt()).decode()
    u = Usuario(
        nome=f"Pytest {tipo.capitalize()}",
        email=email,
        senha_hash=senha_hash,
        tipo=TipoUsuario[tipo],
        ativo=True,
        gerencia_id=gerencia_id,
    )
    session.add(u)
    session.flush()
    return u.id


@pytest.fixture(scope="session", autouse=True)
def _usuarios_teste():
    """Cria usuários de teste antes da sessão e os remove ao final.

    Também executa _limpar_dados_pytest() no início (lixo de runs anteriores)
    e no fim da sessão.
    """
    from database.connection import db_session
    from models import Usuario

    # Limpeza inicial — remove lixo de runs anteriores que falharam
    _limpar_dados_pytest()

    with db_session() as s:
        # Busca gerência existente para o gestor (opcional)
        from models import Gerencia
        ger = s.query(Gerencia).filter_by(ativo=True).first()
        ger_id = ger.id if ger else None

        gestor_id  = _criar_usuario_teste(s, _EMAIL_GESTOR_TESTE,  "gestor",  ger_id)
        tecnico_id = _criar_usuario_teste(s, _EMAIL_TECNICO_TESTE, "tecnico", ger_id)

    yield {"gestor_id": gestor_id, "tecnico_id": tecnico_id}

    # Limpeza ao final da sessão — remove TODOS os dados de teste
    _limpar_dados_pytest()


# ── Fixtures de token e headers ───────────────────────────────────────────────

@pytest.fixture(scope="session")
def _tecnico_id(_usuarios_teste):
    return _usuarios_teste["tecnico_id"]


@pytest.fixture(scope="session")
def client():
    from api.main import app
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def token_gestor():
    from api.services.auth_service import autenticar, criar_token
    usuario, erro = autenticar(_EMAIL_GESTOR_TESTE, _SENHA_TESTE)
    assert usuario is not None, f"Falha ao autenticar gestor de teste: {erro}"
    return criar_token(usuario)


@pytest.fixture(scope="session")
def token_tecnico():
    from api.services.auth_service import autenticar, criar_token
    usuario, erro = autenticar(_EMAIL_TECNICO_TESTE, _SENHA_TESTE)
    assert usuario is not None, f"Falha ao autenticar técnico de teste: {erro}"
    return criar_token(usuario)


@pytest.fixture(scope="session")
def headers_gestor(token_gestor):
    return {"Authorization": f"Bearer {token_gestor}"}


@pytest.fixture(scope="session")
def headers_tecnico(token_tecnico):
    return {"Authorization": f"Bearer {token_tecnico}"}
