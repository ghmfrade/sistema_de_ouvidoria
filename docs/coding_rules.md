# Coding Rules — Sistema de Ouvidorias ARTESP

Convenções, padrões e diretrizes de codificação para manutenção de consistência e qualidade do projeto.

## Princípios Fundamentais

1. **Clareza > Brevidade**: Código deve ser legível. Nomes explícitos, sem abreviações.
2. **Type Safety**: Usar TypedDicts, type hints e validação de entrada.
3. **Single Responsibility**: Cada função/classe tem responsabilidade única.
4. **DRY (Don't Repeat Yourself)**: Lógica comum extraída em funções/repositórios reutilizáveis.
5. **Fail Fast**: Validar entrada imediatamente, retornar erros explícitos.

---

## Separação de Camadas (regra principal)

```
pages/ + qualidade_dash/  →  api/client/  →  FastAPI  →  repositories/  →  models/ + database/
```

- **`pages/`** e **`qualidade_dash/`** nunca importam de `repositories/`, `models/` ou `database/`. Todo acesso ao banco passa pela API via HTTP.
- **`api/client/`** encapsula URLs, headers de autenticação e deserialização — é o único ponto de contato entre o frontend e a API.
- **`api/routers/`** chama repositórios (leitura) ou services (escrita complexa).
- **`repositories/`** não importa `streamlit`. Só ORM, SQL e TypedDicts.
- **`models/`** sem dependências externas além de SQLAlchemy.

```python
# ❌ ERRADO — page fazendo import direto do banco
# pages/03_Detalhe_Ouvidoria.py
from repositories.ouvidoria_repo import get_ouvidoria_detalhe

# ✅ CORRETO — page chama api/client/
from api.client.ouvidoria_client import get_ouvidoria_detalhe
ouvidoria = get_ouvidoria_detalhe(token=st.session_state["token"], ouvidoria_id=oid)
```

---

## Nomenclatura

### Variáveis e Funções (snake_case)

```python
# ✅ Bom
usuario_id = 123
tempo_resposta = datetime.now()
def calcular_tempo_decorrido(data_inicio: date) -> int:
    pass

# ❌ Evitar
usuarioId = 123
def calc_tempo(d1):
    pass
```

### Classes (PascalCase)

```python
# ✅ Bom
class OuvidoriaTecnico:
    pass

class RespostaTecnicaDict(TypedDict):
    pass
```

### Constantes (SCREAMING_SNAKE_CASE)

```python
MAX_ANEXOS = 10
TIMEOUT_SESSAO = 3600
PREFIXO_PROTOCOLO = "OUVI"
```

### Booleanos (is_, has_, pode_, deve_)

```python
is_gestor = usuario.tipo == TipoUsuario.gestor
has_atribuicoes = len(atribuicoes) > 0
pode_responder = usuario.tipo == TipoUsuario.tecnico
```

### Tabela de Convenções

| Tipo | Convenção | Exemplo |
|---|---|---|
| Tabelas SQL | `snake_case` plural | `autos_linha`, `ouvidoria_tecnicos` |
| Classes Python | `PascalCase` | `AutoLinha`, `OuvidoriaTecnico` |
| Funções | `snake_case` | `listar_ouvidorias()` |
| Chaves `session_state` | `snake_case` | `ouvidoria_id`, `resp_recs_edit` |
| Arquivos de página | `NN_NomePagina.py` | `01_Ouvidorias.py` |
| Chaves de widget Streamlit | `prefixo_descricao` | `resp_cat_42`, `trecho_orig` |
| Funções de repositório | `get_*` (leitura), verbo direto (escrita) | `get_ouvidoria_completa`, `criar_usuario` |

---

## Imports

### Ordem

```python
# 1. Standard Library
import os
from datetime import date, datetime
from typing import TypedDict

# 2. Third-party
import streamlit as st
from sqlalchemy.orm import joinedload

# 3. Local/Project
from database.connection import db_session
from models import Ouvidoria, Usuario
from repositories.types import OuvidoriaResumoDict
```

### Regras

```python
# ✅ Um import por linha (exceto tuples do mesmo módulo)
from models import Ouvidoria, Reclamacao, Usuario

# ❌ Nunca import *
from models import *
```

---

## Estrutura de Página Streamlit

```python
"""Página XX - Descrição da Página."""

import streamlit as st
from datetime import date

import auth
from auth import usuario_logado, require_auth
from api.client.ouvidoria_client import listar_ouvidorias
from api.client.catalog_client import listar_categorias


# ── Page Config & Proteção ─────────────────────────────────

st.set_page_config(page_title="Título", layout="wide")
auth.require_auth()   # ou auth.require_gestor() para páginas restritas

u = usuario_logado()

# ── Sidebar ─────────────────────────────────────────────────

with st.sidebar:
    st.markdown(f"**{u['nome']}**")
    st.title("Filtros")
    data_inicio = st.date_input("Data de início")

# ── Main Content ────────────────────────────────────────────

st.title("Título da Página")

try:
    ouvidorias = listar_ouvidorias(token=st.session_state["token"])
except Exception as e:
    st.error("Erro ao carregar dados")
    st.stop()
```

### Guards de acesso

| Função | Uso |
|---|---|
| `auth.require_auth()` | Qualquer usuário autenticado |
| `auth.require_gestor()` | Apenas gestores |

---

## Streamlit — Formulários e Estado

### Nunca coloque seletores dinâmicos dentro de `st.form()`

`st.form()` bloqueia reruns até o submit. Seletores que dependem uns dos outros (ex: Gerência → Coordenação) devem ficar **fora** do form:

```python
# FORA do form — atualiza ao trocar gerência
ger_sel = st.selectbox("Gerência", gerencias, key="nu_gerencia")
coords = carregar_coordenacoes(ger_map.get(ger_sel))
coord_sel = st.selectbox("Coordenação", coords, key="nu_coordenacao")

# DENTRO do form — apenas campos que não dependem de outros
with st.form("form_novo"):
    nome = st.text_input("Nome")
    criar = st.form_submit_button("Criar")
```

### Use `st.toast()` + `st.rerun()` para feedback após ações

```python
# ❌ st.success() some antes do rerun
st.success("Feito!")
st.rerun()

# ✅ st.toast() persiste após o rerun
st.toast("Feito!", icon="✅")
st.rerun()
```

### Limpe o estado ao navegar entre páginas

```python
st.session_state.pop("resp_recs_edit", None)
st.session_state.pop("resp_autos_checklist", None)
st.switch_page("pages/05_Responder.py")
```

### Cache

Use `@st.cache_data(ttl=N)` nos clientes de `api/client/`:

| TTL | Usado para |
|---|---|
| `ttl=300` | Catálogos raramente alterados (municípios, permissionárias, gerências) |
| `ttl=120` | Queries de dashboard |
| `ttl=60` | Dados semi-dinâmicos (técnicos disponíveis, status de ouvidoria) |

Após qualquer escrita que afete dados cacheados, invalide com `.clear()` + `st.rerun()`.

---

## Repositories: Read vs Write

### Read Repository

```python
"""Consultas ao banco — leitura apenas."""

from database.connection import db_session
from repositories.types import OuvidoriaResumoDict

def listar_ouvidorias() -> list[OuvidoriaResumoDict]:
    with db_session() as s:
        ouvidorias = s.query(Ouvidoria).options(joinedload(...)).all()
        return [_to_resumo(ou) for ou in ouvidorias]
        # Conversão ORM → TypedDict DENTRO da sessão
```

**Garantias:**
- Nenhuma modificação de banco
- Retorna TypedDicts (contratos imutáveis)
- Conversão ORM → dict acontece **dentro** de `with db_session()`
- Sem "lazy loading traps" (joinedload quando necessário)

### Write Repository

```python
"""Escrita ao banco — insert, update, delete."""

from database.connection import db_session
from models import Ouvidoria, StatusOuvidoria

def criar_ouvidoria(protocolo: str, conteudo: str, prazo: date, criado_por_id: int) -> int:
    with db_session() as s:
        ou = Ouvidoria(
            protocolo=protocolo,
            conteudo=conteudo,
            prazo=prazo,
            criado_por_id=criado_por_id,
            status=StatusOuvidoria.AGUARDANDO_ACOES,
        )
        s.add(ou)
        s.flush()
        novo_id = ou.id
    return novo_id
```

**Regras:**
- Commit automático (ou rollback em exceção)
- Retorna apenas scalars (IDs, contadores, booleanos)
- Nunca retorna instâncias ORM — use read repo depois

---

## TypedDicts & Type Safety

### Defina Contratos Explícitos

```python
# ❌ Evitar: dict genérico
def listar() -> list[dict]:
    return [{"id": 1, "nome": "..."}]

# ✅ Bom: contrato explícito
class OuvidoriaResumoDict(TypedDict):
    id: int
    protocolo: str | None
    status: str
    atribuicoes: list[OuvidoriaTecnicoDict]

def listar() -> list[OuvidoriaResumoDict]:
    ...
```

Todos os TypedDicts ficam em `repositories/types.py`.

---

## Session Management

```python
from database.connection import db_session

with db_session() as s:
    # commit automático em sucesso
    # rollback automático em exceção
    # session sempre fechada
```

### Nunca retorne instâncias ORM fora da sessão

```python
# ❌ PROIBIDO — objeto ORM fora da sessão
with db_session() as s:
    o = s.query(Ouvidoria).filter_by(id=oid).first()
return o   # DetachedInstanceError em qualquer acesso a relacionamento

# ❌ PROIBIDO — expunge_all() como muleta
with db_session() as s:
    objs = s.query(Modelo).options(joinedload(...)).all()
    s.expunge_all()
    return objs   # Contrato implícito frágil

# ✅ CORRETO — conversão dentro da sessão
with db_session() as s:
    o = s.query(Ouvidoria).options(joinedload(...)).filter_by(id=oid).first()
    return _to_detalhe(o) if o else None
```

---

## SQLAlchemy Best Practices

### Sempre use Joinedload para relacionamentos

```python
# ❌ N+1 query problem
ouvidoria = s.query(Ouvidoria).first()
for r in ouvidoria.reclamacoes:  # ← Query para cada item!
    print(r.descricao)

# ✅ Eager loading
ouvidoria = s.query(Ouvidoria).options(
    joinedload(Ouvidoria.reclamacoes)
).first()
```

### Use `mapped_column` e `Mapped` (SQLAlchemy 2.0)

```python
class Exemplo(Base):
    __tablename__ = "exemplos"
    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    campo_opcional: Mapped[str | None] = mapped_column(String(200), nullable=True)
```

### Cascade delete em relacionamentos pai→filho

```python
reclamacoes: Mapped[list["Reclamacao"]] = relationship(
    back_populates="ouvidoria", cascade="all, delete-orphan"
)
```

### Queries agregadas em dashboards

Para queries agregadas, retornar tuples/scalars diretamente é correto — sem necessidade de TypedDicts:

```python
def query_kpis_produtividade(...) -> tuple[int, int, int]:
    with db_session() as s:
        return s.query(func.count(), ...).one()
```

---

## FastAPI — Padrões da API REST

O diretório `api/` expõe endpoints REST consumidos por todos os clientes: Streamlit (`api/client/`), Plotly Dash (`qualidade_dash/api_client.py`) e potencialmente integrações externas.

### Estrutura de Router

```python
# api/routers/meu_dominio.py
from fastapi import APIRouter, Depends, HTTPException
from api.deps import usuario_corrente, requer_gestor
from api.schemas.meu_dominio import MeuSchema, CriarMeuRequest
from repositories.meu_repo import listar_meus, get_meu

router = APIRouter()

# ── Leitura ───────────────────────────────────────────────
@router.get("", response_model=list[MeuSchema])
def listar(_=Depends(usuario_corrente)):
    return listar_meus()

@router.get("/{id}", response_model=MeuSchema)
def detalhe(id: int, _=Depends(usuario_corrente)):
    dado = get_meu(id)
    if dado is None:
        raise HTTPException(status_code=404, detail="Não encontrado")
    return dado

# ── Escrita ───────────────────────────────────────────────
@router.post("", response_model=MeuSchema)
def criar(body: CriarMeuRequest, _=Depends(requer_gestor)):
    ...
```

**Regras:**
- `Depends(usuario_corrente)` em todas as rotas autenticadas
- `Depends(requer_gestor)` para operações restritas a gestores
- Routers chamam repositórios (leitura simples) ou services (escrita complexa com múltiplos repos)

### Schemas Pydantic

```python
# api/schemas/meu_dominio.py

# ── Response schemas ──────────────────────────────────────
class MeuSchema(BaseModel):
    id: int
    nome: str
    model_config = {"from_attributes": True}

# ── Request schemas ───────────────────────────────────────
class CriarMeuRequest(BaseModel):
    nome: str
    data: date
```

- Response schemas com `model_config = {"from_attributes": True}`
- Nunca reutilize schema de resposta como schema de request

### Services

Use `api/services/` apenas quando a operação envolve mais de um repositório ou lógica não trivial. Para operações simples, o router chama o repositório diretamente.

### Autenticação JWT

```python
@router.get("/")
def rota(payload: dict = Depends(usuario_corrente)):
    usuario_id = int(payload["sub"])
    tipo = payload["tipo"]  # "gestor" | "tecnico"
```

### Registrar novo router

```python
# api/main.py
from api.routers import meu_dominio
app.include_router(meu_dominio.router, prefix="/meu-dominio", tags=["meu-dominio"])
```

### Checklist FastAPI

- [ ] Router registrado em `api/main.py`
- [ ] Todas as rotas têm `Depends(usuario_corrente)` ou `Depends(requer_gestor)`
- [ ] `response_model=` explícito
- [ ] `HTTPException(404)` quando recurso não encontrado
- [ ] Função adicionada em `api/client/` para o Streamlit consumir

---

## Tratamento de Erros

```python
# ❌ Catch-all genérico
try:
    ...
except:
    pass

# ✅ Exceções específicas
try:
    ouvidoria = ouvidoria_client.get_detalhe(token, id)
except ValueError as e:
    st.error(f"ID inválido: {e}")
except Exception as e:
    logger.error("Erro ao carregar ouvidoria", exc_info=True)
    st.error("Erro ao carregar dados")
```

Em repositórios, **não capture exceções** — deixe propagar para a página ou endpoint tratarem.

---

## Validação de Entrada

```python
# ✅ Validar forms antes de persistir
with st.form("form_ouvidoria"):
    protocolo = st.text_input("Protocolo", max_chars=50)
    submit = st.form_submit_button("Criar")

    if submit:
        if not protocolo.strip():
            st.error("Protocolo é obrigatório")
        else:
            ...
```

---

## Detecção de Colunas em CSVs

CSVs têm colunas com caracteres especiais (acentos, °). Use o helper `_col()`:

```python
def _col(df, *candidates):
    lower_map = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand in df.columns:
            return cand
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    return None

col_perm = _col(df, "Permissionária", "Permissionaria") or \
           next((c for c in df.columns if "permiss" in c.lower()), None)
```

---

## Performance

1. **`@st.cache_data` para dados estáticos**
   ```python
   @st.cache_data(ttl=300)
   def listar_categorias():
       return catalog_client.listar_categorias(token=...)
   ```

2. **Selecione apenas colunas necessárias**
   ```python
   s.query(Ouvidoria.id, Ouvidoria.protocolo, Ouvidoria.status)
   ```

3. **Agregue no banco, não em Python**
   ```python
   count = s.query(func.count(Ouvidoria.id)).scalar()
   ```

---

## Segurança

- Senhas sempre hasheadas com bcrypt — nunca texto plano.
- Não expor stacktraces ao usuário final — use `st.error("Mensagem amigável")`.
- Variáveis de ambiente em `.env` (não versionar). Usar `python-dotenv`.
- Validar campos obrigatórios antes de persistir no banco.

---

## Code Review Checklist

- [ ] **Nomenclatura**: snake_case (funções), PascalCase (classes)
- [ ] **Type Hints**: Todas as funções têm tipos explícitos
- [ ] **Imports**: Ordenados corretamente, sem unused
- [ ] **Camadas**: pages/ usa apenas `api/client/`, nunca `repositories/` direto
- [ ] **Sessions**: Todas as queries em `with db_session()`
- [ ] **TypedDicts**: Repositórios retornam TypedDicts, nunca instâncias ORM
- [ ] **Joinedload**: Relacionamentos carregados dentro da sessão
- [ ] **Testes**: Mudanças testadas localmente
- [ ] **Migrations**: Alterações de schema em alembic (não em código)

---

## Anti-Patterns

1. **Retornar instâncias ORM fora de sessão**
   ```python
   # ❌ Nunca
   def get_ouvidoria(id: int):
       session = SessionLocal()
       return session.query(Ouvidoria).get(id)  # LazyLoad trap
   ```

2. **Pages acessando banco diretamente**
   ```python
   # ❌ Evitar
   # pages/03_Detalhe.py
   with db_session() as s:
       ou = s.query(Ouvidoria).get(id)
   
   # ✅ Bom
   from api.client.ouvidoria_client import get_ouvidoria_detalhe
   ou = get_ouvidoria_detalhe(token=st.session_state["token"], ouvidoria_id=id)
   ```

3. **Catch-All Exception Handlers** — nunca `except: pass`

4. **Global Mutable State**
   ```python
   # ❌ Evitar — será recriado a cada rerun
   _cache_global = {}
   
   # ✅ Bom
   if "cache" not in st.session_state:
       st.session_state.cache = {}
   ```

5. **Magic Numbers**
   ```python
   # ❌ Evitar
   if len(anexos) > 10:
       raise ValueError("Muitos anexos")
   
   # ✅ Bom
   MAX_ANEXOS = 10
   if len(anexos) > MAX_ANEXOS:
       raise ValueError(f"Máximo {MAX_ANEXOS} anexos permitidos")
   ```

---

## Referências Internas

- [docs/architecture.md](architecture.md) — Padrões de design e arquitetura
- [README.md](../README.md) — Visão geral e setup
