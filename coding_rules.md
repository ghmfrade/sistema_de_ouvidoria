# 📋 Coding Rules — Sistema de Ouvidorias ARTESP

Convenções, padrões e diretrizes de codificação para manutenção de consistência e qualidade do projeto.

## 🎯 Princípios Fundamentais

1. **Clareza > Brevidade**: Código deve ser legível. Nomes explícitos, sem abreviações.
2. **Type Safety**: Usar TypedDicts, type hints e validação de entrada.
3. **Single Responsibility**: Cada função/classe tem responsabilidade única.
4. **DRY (Don't Repeat Yourself)**: Lógica comum extraída em funções/repositórios reutilizáveis.
5. **Fail Fast**: Validar entrada imediatamente, retornar erros explícitos.

## 📝 Nomenclatura

### Variáveis e Funções (snake_case)

```python
# ✅ Bom
usuario_id = 123
tempo_resposta = datetime.now()
def calcular_tempo_decorrido(data_inicio: date) -> int:
    pass

# ❌ Evitar
usuarioId = 123  # camelCase
tempResposta = datetime.now()
def calc_tempo(d1):  # abreviado
    pass
```

### Classes (PascalCase)

```python
# ✅ Bom
class OuvidoriaTecnico:
    pass

class RespostaTecnicaDict(TypedDict):
    pass

# ❌ Evitar
class ouvidoriaTecnico:
    pass

class resposta_tecnica:  # snake_case
    pass
```

### Constantes (SCREAMING_SNAKE_CASE)

```python
# ✅ Bom
MAX_ANEXOS = 10
TIMEOUT_SESSAO = 3600
PREFIXO_PROTOCOLO = "OUVI"

# ❌ Evitar
max_anexos = 10
timeoutSessao = 3600
```

### Booleanos (is_, has_, pode_, deve_)

```python
# ✅ Bom
is_gestor = usuario.tipo == TipoUsuario.gestor
has_atribuicoes = len(atribuicoes) > 0
pode_responder = usuario.tipo == TipoUsuario.tecnico
deve_enviar_notificacao = status_novo != status_antigo

# ❌ Evitar
gestor = usuario.tipo == TipoUsuario.gestor
atribuicoes = len(atribuicoes) > 0
```

## 🔤 Imports

### Ordem de Imports

```python
# 1. Standard Library
import os
from datetime import date, datetime
from typing import TypedDict
from contextlib import contextmanager

# 2. Third-party
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.orm import joinedload

# 3. Local/Project
from database.connection import db_session
from models import Ouvidoria, Usuario
from repositories.types import OuvidoriaResumoDict
```

### Regra: Um import por linha (exceto tuples)

```python
# ✅ Bom
from models import Ouvidoria, Reclamacao, Usuario
from database.connection import db_session

# ❌ Evitar
from models import Ouvidoria; from models import Reclamacao
```

### Evitar import *

```python
# ❌ Nunca
from models import *

# ✅ Bom
from models import Ouvidoria, Reclamacao, Usuario
```

## 🗂️ Organização de Código

### Estrutura de Arquivos de Repositório

```python
"""Consultas ao banco para carregamento de ouvidorias."""

from sqlalchemy.orm import joinedload

from database.connection import db_session
from models import Ouvidoria, Reclamacao, OuvidoriaTecnico
from repositories.types import OuvidoriaResumoDict, OuvidoriaDetalheDict


# ── Helpers de conversão ──────────────────────────────────
# Private functions (_prefixo) que convertem ORM → TypedDict

def _to_ouvidoria_resumo(ou: Ouvidoria) -> OuvidoriaResumoDict:
    """Converte ORM para TypedDict (resumo)."""
    return OuvidoriaResumoDict(...)


def _to_ouvidoria_detalhe(ou: Ouvidoria) -> OuvidoriaDetalheDict:
    """Converte ORM para TypedDict (detalhe completo)."""
    return OuvidoriaDetalheDict(...)


# ── Funções Públicas ─────────────────────────────────────
# Queries que retornam TypedDicts

def listar_ouvidorias() -> list[OuvidoriaResumoDict]:
    """Lista todas as ouvidorias com resumo."""
    with db_session() as s:
        # Query
        return [_to_ouvidoria_resumo(ou) for ou in ...]


def get_ouvidoria_detalhe(ouvidoria_id: int) -> OuvidoriaDetalheDict | None:
    """Carrega ouvidoria completa."""
    with db_session() as s:
        # Query com joinedload
        return _to_ouvidoria_detalhe(ou) if ou else None
```

### Estrutura de Página Streamlit

```python
"""Página XX - Descrição da Página."""

import streamlit as st
from datetime import date

import auth
from auth import usuario_logado, require_auth, require_gestor
from repositories import ouvidoria_repo, catalog_repo
from repositories.ouvidoria_write_repo import criar_ouvidoria


# ── Page Config & Proteção ─────────────────────────────────

auth.require_auth()  # Exigir autenticação
st.set_page_config(page_title="Título", layout="wide")

# ── State Management ────────────────────────────────────────

if "form_state" not in st.session_state:
    st.session_state.form_state = {}


# ── Sidebar ─────────────────────────────────────────────────

with st.sidebar:
    st.title("Filtros")
    data_inicio = st.date_input("Data de início")


# ── Main Content ────────────────────────────────────────────

st.title("Título da Página")

# Carrega dados
try:
    ouvidorias = ouvidoria_repo.listar()
except Exception as e:
    st.error(f"Erro: {e}")
    st.stop()

# Renderiza UI
col1, col2 = st.columns(2)
with col1:
    st.metric("Total", len(ouvidorias))

# Tabela com dados
st.dataframe(ouvidorias)
```

## 📂 Repositories: Read vs Write

### ✅ Read Repository: `ouvidoria_repo.py`

```python
"""Consultas ao banco — leitura apenas."""

from database.connection import db_session
from repositories.types import OuvidoriaResumoDict

def listar_ouvidorias() -> list[OuvidoriaResumoDict]:
    """Retorna lista de resumos de ouvidorias."""
    with db_session() as s:
        ouvidorias = s.query(Ouvidoria).all()
        # Conversão ORM → TypedDict DENTRO da sessão
        return [_to_resumo(ou) for ou in ouvidorias]
        # Ao sair de with: session.close()
        # TypedDicts são retornados (safe, imutáveis)
```

**Garantias:**
- ✅ Nenhuma modificação de banco
- ✅ Retorna TypedDicts (contratos imutáveis)
- ✅ Conversão ORM → dict acontece **dentro** de `with db_session()`
- ✅ Sem "lazy loading traps" (joinedload quando necessário)

### ✅ Write Repository: `ouvidoria_write_repo.py`

```python
"""Escrita ao banco — insert, update, delete."""

from database.connection import db_session
from models import Ouvidoria, StatusOuvidoria

def criar_ouvidoria(
    protocolo: str,
    conteudo: str,
    prazo: date,
    criado_por_id: int,
) -> int:
    """Cria nova ouvidoria e retorna seu ID."""
    with db_session() as s:
        ou = Ouvidoria(
            protocolo=protocolo,
            conteudo=conteudo,
            prazo=prazo,
            criado_por_id=criado_por_id,
            status=StatusOuvidoria.AGUARDANDO_ACOES,
        )
        s.add(ou)
        s.flush()  # Popula ou.id
        novo_id = ou.id
        # Sai de with: commit automático
    return novo_id

def atualizar_status(ouvidoria_id: int, novo_status: str) -> None:
    """Atualiza status de ouvidoria."""
    with db_session() as s:
        ou = s.query(Ouvidoria).filter_by(id=ouvidoria_id).first()
        if ou:
            ou.status = StatusOuvidoria(novo_status)
            # Sai de with: commit automático
```

**Regras:**
- ✅ Operações CRUD no banco
- ✅ Validação de integridade referencial
- ✅ Commit automático (ou rollback em exceção)
- ✅ Retorna apenas scalares (IDs, contadores, booleanos)
- ❌ Nunca retorna instâncias ORM (use read repo depois)

## 🔐 TypedDicts & Type Safety

### Defina Contratos Explícitos

```python
# ❌ Evitar: retornar dict genérico
def listar() -> list[dict]:
    return [{"id": 1, "nome": "..."}]

# ✅ Bom: contrato explícito
class OuvidoriaResumoDict(TypedDict):
    id: int
    protocolo: str | None
    status: str
    atribuicoes: list[OuvidoriaTecnicoDict]

def listar() -> list[OuvidoriaResumoDict]:
    return [OuvidoriaResumoDict(...), ...]
```

### Sempre Adicione ao `repositories/types.py`

```python
# repositories/types.py
class NovaStructureDict(TypedDict):
    """Descrição da estrutura."""
    campo1: int
    campo2: str | None
    campo3: list[OutraStructureDict]
```

## 🛡️ Validação de Entrada

### Validar Imediatamente

```python
# ❌ Evitar: confiar em entrada
def processar(email: str):
    usuario = Usuario.query.filter_by(email=email).first()

# ✅ Bom: validar primeiro
def processar(email: str):
    if not email or "@" not in email:
        raise ValueError("Email inválido")
    usuario = Usuario.query.filter_by(email=email).first()
    if not usuario:
        raise ValueError("Usuário não encontrado")
```

### Em Streamlit: Validar Forms

```python
# ✅ Bom
with st.form("form_ouvidoria"):
    protocolo = st.text_input("Protocolo", max_chars=50)
    conteudo = st.text_area("Conteúdo", min_chars=10)
    submit = st.form_submit_button("Criar")

    if submit:
        if not protocolo.strip():
            st.error("Protocolo é obrigatório")
        elif not conteudo.strip():
            st.error("Conteúdo é obrigatório")
        else:
            # Validação passou, processa
            ...
```

## 🔄 Tratamento de Erros

### Padrão Try/Except

```python
# ❌ Evitar: catch-all genérico
try:
    ...
except:  # SOS!
    pass

# ✅ Bom: specific exceptions
try:
    ouvidoria = ouvidoria_repo.get_detalhe(id)
except ValueError as e:
    st.error(f"ID inválido: {e}")
except Exception as e:
    logger.error(f"Erro no banco", exc_info=True)
    st.error("Erro ao carregar dados")
```

### Em Repositórios: Não Catch

```python
# ❌ Evitar em repos: silenciar exceções
def get_ouvidoria(id: int) -> OuvidoriaDict | None:
    with db_session() as s:
        try:
            return s.query(Ouvidoria).filter_by(id=id).first()
        except:  # ❌ Hides the bug!
            return None

# ✅ Bom: deixar exceção propagar
def get_ouvidoria(id: int) -> OuvidoriaDict | None:
    with db_session() as s:
        ou = s.query(Ouvidoria).filter_by(id=id).first()
        return _to_dict(ou) if ou else None
```

**Regra:** Deixe exceções do banco propagarem. Páginas/services as tratam e exibem ao usuário.

## 📊 SQLAlchemy Best Practices

### Sempre Use Joinedload para Relacionamentos

```python
# ❌ Ruim: N+1 query problem
ouvidoria = s.query(Ouvidoria).first()
for r in ouvidoria.reclamacoes:  # ← Query para cada reclamação!
    print(r.descricao)

# ✅ Bom: eager loading
ouvidoria = s.query(Ouvidoria).options(
    joinedload(Ouvidoria.reclamacoes)
).first()
for r in ouvidoria.reclamacoes:  # ← Já carregado
    print(r.descricao)
```

### Use Session Scope Appropriate

```python
# ❌ Evitar: session vaza para fora
def get_usuario(id: int) -> Usuario:
    session = get_session()
    return session.query(Usuario).get(id)  # ← Session aberta!

# ✅ Bom: conversão dentro de db_session
def get_usuario(id: int) -> UsuarioDict | None:
    with db_session() as s:
        usuario = s.query(Usuario).get(id)
        return _to_dict(usuario) if usuario else None
```

### Filter vs Get

```python
# ✅ Ambos são válidos, escolha por contexto

# Get (por PK)
ouvidoria = s.query(Ouvidoria).get(123)  # id=123

# Filter (por qualquer coluna)
ouvidoria = s.query(Ouvidoria).filter_by(protocolo="OUVI-001").first()
ouvidoria = s.query(Ouvidoria).filter(Ouvidoria.status == "Concluído").all()
```

## 🎨 Streamlit Conventions

### Sempre Proteja com @require_auth()

```python
# ✅ Bom
import auth
auth.require_auth()  # no topo da página

# Ou mais específico
auth.require_gestor()  # apenas gestores
```

### Use Session State para Estado

```python
# ✅ Bom
if "filtros" not in st.session_state:
    st.session_state.filtros = {}

st.session_state.filtros["status"] = "Concluído"

# ❌ Evitar: variáveis globais
filtro_global = "Concluído"  # Será recriado a cada rerun!
```

### Sidebar para Filtros/Config

```python
# ✅ Estrutura padrão
with st.sidebar:
    st.title("Filtros")
    data_inicio = st.date_input("Data início")
    status = st.selectbox("Status", ["Todos", "Concluído"])

# Main content abaixo
st.title("Ouvidorias")
```

### Tabs para Múltiplas Views

```python
tab1, tab2, tab3 = st.tabs(["Listagem", "Detalhes", "Relatório"])

with tab1:
    st.dataframe(ouvidorias)

with tab2:
    st.write(ouvidoria_selecionada)

with tab3:
    st.download_button("Download Excel", ...)
```

## 📚 Documentação

### Docstrings (Tipos com type hints)

```python
def criar_ouvidoria(protocolo: str, conteudo: str, prazo: date) -> int:
    """Cria nova ouvidoria e retorna seu ID.
    
    Args:
        protocolo: Código único da ouvidoria (ex: "OUVI-001")
        conteudo: Descrição do problema reportado
        prazo: Data final para resposta técnica
    
    Returns:
        ID da ouvidoria criada
        
    Raises:
        ValueError: Se protocolo duplicado
    """
    ...
```

**Regra:** Type hints + docstring simples. Sem redundância.

```python
# ❌ Redundante
def get_usuario(usuario_id: int) -> Usuario:
    """
    Recupera um usuário pelo ID do banco de dados.
    
    This function queries the database for a user with the given
    usuario_id parameter and returns the Usuario object if found.
    """
    ...

# ✅ Conciso
def get_usuario(usuario_id: int) -> Usuario | None:
    """Carrega usuário pelo ID, ou None se não encontrado."""
    ...
```

## 🔍 Code Review Checklist

Antes de fazer commit/PR, verifique:

- [ ] **Nomenclatura**: snake_case (funções), PascalCase (classes)
- [ ] **Type Hints**: Todas as funções têm tipos explícitos
- [ ] **Imports**: Ordenados corretamente, sem unused
- [ ] **Validação**: Entrada validada imediatamente
- [ ] **Sessions**: Todas as queries em `with db_session()`
- [ ] **TypedDicts**: Retornados, nunca instâncias ORM
- [ ] **Joinedload**: Relacionamentos carregados eficientemente
- [ ] **Logs**: Erros loggados com exc_info=True
- [ ] **Testes**: Mudanças testadas localmente
- [ ] **Docs**: Funções públicas documentadas
- [ ] **Migrations**: Schema changes em alembic (não em código)

## ⚠️ Anti-Patterns

### ❌ Never

1. **Retornar instâncias ORM fora de sessão**
   ```python
   # ❌ Nunca
   def get_ouvidoria(id: int):
       session = SessionLocal()
       return session.query(Ouvidoria).get(id)  # ← LazyLoad trap!
   ```

2. **Misturar Lógica de Negócio em Pages**
   ```python
   # ❌ Evitar
   # pages/03_Detalhe.py
   with db_session() as s:
       ou = s.query(Ouvidoria).get(id)
       ou.status = "Concluído"  # Lógica aqui?
   
   # ✅ Bom
   from repositories.ouvidoria_write_repo import atualizar_status
   atualizar_status(id, "Concluído")
   ```

3. **Catch-All Exception Handlers**
   ```python
   # ❌ Nunca
   try:
       ...
   except:
       pass
   
   # ✅ Bom
   except ValueError as e:
       st.error(f"Erro: {e}")
   except Exception as e:
       logger.error("...", exc_info=True)
   ```

4. **Global Mutable State**
   ```python
   # ❌ Evitar
   _cache_global = {}
   
   # ✅ Bom
   if "cache" not in st.session_state:
       st.session_state.cache = {}
   ```

5. **Magic Numbers**
   ```python
   # ❌ Evitar
   if len(anexos) > 10:  # Por que 10?
       raise ValueError("Muitos anexos")
   
   # ✅ Bom
   MAX_ANEXOS = 10
   if len(anexos) > MAX_ANEXOS:
       raise ValueError(f"Máximo {MAX_ANEXOS} anexos permitidos")
   ```

## 🚀 Performance Tips

1. **Use `@st.cache_data` para dados estáticos**
   ```python
   @st.cache_data
   def listar_categorias():
       return catalog_repo.listar_categorias()
   ```

2. **Selecione apenas colunas necessárias**
   ```python
   # ✅ Melhor
   s.query(Ouvidoria.id, Ouvidoria.protocolo, Ouvidoria.status)
   
   # ❌ Evitar quando não necessário
   s.query(Ouvidoria)
   ```

3. **Agregue no banco, não em Python**
   ```python
   # ✅ Bom
   count = s.query(func.count(Ouvidoria.id)).scalar()
   
   # ❌ Ruim
   ouvidorias = s.query(Ouvidoria).all()
   count = len(ouvidorias)  # ← Carrega tudo
   ```

## 📋 Referências Internas

- [architecture.md](architecture.md) - Padrões de design e arquitetura
- [README.md](README.md) - Visão geral e setup
