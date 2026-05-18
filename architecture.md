# Architecture — Sistema de Ouvidorias ARTESP

Documentação da arquitetura técnica, padrões de design e decisões arquiteturais do sistema.

## Visão Geral

O sistema é composto por três processos independentes que se comunicam via HTTP:

```
┌──────────────────────────────────────────────────────────────────┐
│  Streamlit App  (porta 8501)                                     │
│  app.py  +  pages/                                               │
│  Interface principal: login, ouvidorias, admin, dashboards       │
└──────────────────────────────┬───────────────────────────────────┘
                               │ HTTP (api/client/)
┌──────────────────────────────▼───────────────────────────────────┐
│  FastAPI  (porta 8000)                                           │
│  api/main.py  →  api/routers/  →  repositories/  →  PostgreSQL  │
│  REST API interna; endpoints de analytics sem autenticação       │
└──────────────────────────────┬───────────────────────────────────┘
                               │ HTTP (/dashboard/qualidade-v2/*)
┌──────────────────────────────▼───────────────────────────────────┐
│  Plotly Dash  (porta 8050)                                       │
│  run_dash.py  →  qualidade_dash/                                 │
│  Dashboard interativo de qualidade/fiscalização                  │
└──────────────────────────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────┐
│  PostgreSQL  (porta 5432  —  banco: sistema_de_ouvidoria)        │
└──────────────────────────────────────────────────────────────────┘
```

## Estrutura de Diretórios

```
app.py                          # Entry point Streamlit (login)
auth.py                         # bcrypt + session_state
run_dash.py                     # Entry point Plotly Dash

pages/
  01_Ouvidorias.py              # Listagem (gestor: todas | técnico: atribuídas)
  02_Nova_Ouvidoria.py          # Criar ouvidoria + reclamações
  03_Detalhe_Ouvidoria.py       # Detalhe, editar, atribuir técnicos
  04_Resposta_Permissionaria.py # Resposta da permissionária
  05_Responder.py               # Análise técnica (técnico)
  06_Dashboard_Produtividade.py # Dashboard produtividade (Streamlit nativo)
  07_Dashboard_Qualidade.py     # Iframe/link para o app Dash
  08_Admin.py                   # CRUD usuários, categorias, gerências

api/
  main.py                       # FastAPI app + inclusão de routers
  deps.py                       # Dependências compartilhadas (auth, DB)
  routers/
    auth.py                     # POST /auth/login
    ouvidorias.py               # CRUD /ouvidorias
    catalogo.py                 # GET /catalogo (categorias, permissionárias)
    autos.py                    # GET /autos (busca por trecho/número)
    dashboard.py                # GET /dashboard (produtividade)
    dashboard_qualidade_novo.py # GET /dashboard/qualidade-v2/* (consumido pelo Dash)
    admin.py                    # CRUD /admin (usuários, gerências)
  schemas/                      # Pydantic models (request/response)
  services/                     # Lógica de negócio (auth_service, ouvidoria_service)
  client/                       # Clientes HTTP usados pelo Streamlit

qualidade_dash/
  app.py                        # Dash app object
  layout.py                     # build_layout() — estrutura dos componentes
  callbacks.py                  # register_callbacks(app) — interatividade
  api_client.py                 # Chamadas para FastAPI /dashboard/qualidade-v2/*

repositories/
  types.py                      # TypedDicts (contratos de dados)
  ouvidoria_repo.py             # Queries read-only de ouvidorias
  ouvidoria_write_repo.py       # Insert/Update/Delete de ouvidorias
  catalog_repo.py               # Categorias, permissionárias
  autos_repo.py                 # Autos de linha e paradas
  municipios_repo.py            # Cidades / municípios
  admin_write_repo.py           # CRUD usuários, gerências, coordenações
  pontuacao.py                  # Cálculo de pontuação de reclamações
  dashboard/
    produtividade_repo.py       # Queries do dashboard de produtividade
    qualidade_novo_repo.py      # Queries do dashboard de qualidade (Dash v2)
  relatorios/
    reclamacoes_repo.py         # Queries para geração de relatórios

models/                         # SQLAlchemy ORM (Declarative, mapped_column)
database/
  connection.py                 # engine, db_session() context manager, init_db()
  seed.py                       # Importa CSVs + cria admin padrão
migrations/                     # Alembic (versões do schema)
```

## Padrões de Design

### 1. Repository Pattern

Separação explícita entre leitura e escrita:

```python
# Read — nunca modifica, retorna TypedDicts
# repositories/ouvidoria_repo.py
def listar_ouvidorias(...) -> list[OuvidoriaResumoDict]:
    with db_session() as s:
        # Query → conversão ORM → TypedDict (dentro da sessão)
        ...

# Write — insert/update/delete, retorna ID ou None
# repositories/ouvidoria_write_repo.py
def criar_ouvidoria(...) -> int:
    with db_session() as s:
        ...  # commit automático ao sair
```

### 2. Type Safety com TypedDicts

```python
# repositories/types.py
class OuvidoriaResumoDict(TypedDict):
    id: int
    protocolo: str | None
    status: str
    prazo: date | None
    atribuicoes: list[OuvidoriaTecnicoDict]
```

Instâncias ORM nunca saem do `with db_session()` — a conversão para TypedDict acontece **dentro** do context manager para evitar `DetachedInstanceError`.

### 3. Session Management

```python
from database.connection import db_session

with db_session() as s:
    # commit automático em sucesso
    # rollback automático em exceção
    # session sempre fechada
```

### 4. Camada de Cliente HTTP (Streamlit → FastAPI)

O Streamlit não acessa o banco diretamente nas páginas; usa os clientes de `api/client/`:

```python
# pages/01_Ouvidorias.py
from api.client.ouvidoria_client import listar_ouvidorias

ouvidorias = listar_ouvidorias(token=st.session_state["token"], ...)
```

Os clientes encapsulam URLs, headers de autenticação e deserialização de resposta.

## Fluxo de Dados

### Criar Nova Ouvidoria

```
Formulário (02_Nova_Ouvidoria.py)
  → api/client/ouvidoria_client.py  (HTTP POST /ouvidorias)
  → api/routers/ouvidorias.py
  → api/services/ouvidoria_service.py
  → repositories/ouvidoria_write_repo.py
  → PostgreSQL (commit)
  → retorna ID
  → st.rerun() → 03_Detalhe_Ouvidoria.py
```

### Dashboard de Qualidade (Dash)

```
Usuário acessa 07_Dashboard_Qualidade.py (Streamlit)
  → iframe / link para Dash em porta 8050

Dash (qualidade_dash/callbacks.py)
  → qualidade_dash/api_client.py  (HTTP GET /dashboard/qualidade-v2/*)
  → api/routers/dashboard_qualidade_novo.py
  → repositories/dashboard/qualidade_novo_repo.py
  → PostgreSQL (read-only)
  → JSON → Plotly figures
```

## Autenticação

- Login via `POST /auth/login` (FastAPI) → retorna JWT
- Streamlit armazena token em `st.session_state["token"]`
- Páginas validam sessão com `@require_auth()` / `@require_gestor()`
- Senhas com hash bcrypt — nunca texto plano
- Endpoints do dashboard de qualidade são públicos (analytics interno, read-only)

## Diagrama ER (Conceitual)

```
Usuario ─────────────────────────────────────┐
  │ criado_por (1:N)                          │ atribuição (1:N)
  │                                           │
Ouvidoria ◄──── OuvidoriaTecnico ────────── Tecnico
  │ (1:N)            respondido / respondido_em
  │
Reclamacao ──── (N:M via ReclamacaoAuto) ──── AutoLinha
  │ categoria_id                                │ permissionaria_id
  │                                             │
Categoria                                  Permissionaria
  └── subcategoria
```

### Entidades Principais

| Entidade | Propósito |
|---|---|
| **Ouvidoria** | Agrupa ≥1 reclamação; ciclo de vida: Aguardando → Em análise → Concluído |
| **Reclamacao** | Item específico com categoria, subcategoria, local embarque/desembarque |
| **AutoLinha** | Linha de transporte (ex: `3100-A — SAUDE/PRAIA GRANDE`) |
| **ParadaAutoLinha** | Cidades atendidas por um auto; usada em busca por trecho |
| **OuvidoriaTecnico** | Rastreia atribuição técnico ↔ ouvidoria e status de resposta |
| **RespostaTecnica** | Análise do técnico (pontuação, categorização, texto) |
| **Usuario** | Gestor ou Técnico; vinculado a Gerência e Coordenação |

## Como Iniciar

```bash
# 1. Banco + seed (primeira vez)
python database/seed.py

# 2. FastAPI
uvicorn api.main:app --reload --port 8000

# 3. Streamlit
streamlit run app.py

# 4. Dashboard Qualidade (opcional)
python run_dash.py          # porta 8050
# ou: DASH_PORT=8050 DASH_DEBUG=true python run_dash.py
```

## Migrations (Alembic)

```bash
# Após alterar models/
alembic revision --autogenerate -m "descricao"
# Revisar migrations/versions/xxxxx_descricao.py
alembic upgrade head
# Commitar: migration + models/
```

## Referências

- [SQLAlchemy ORM 2.0](https://docs.sqlalchemy.org/en/20/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Plotly Dash](https://dash.plotly.com/)
- [Alembic](https://alembic.sqlalchemy.org/)
- [Streamlit](https://docs.streamlit.io/)
