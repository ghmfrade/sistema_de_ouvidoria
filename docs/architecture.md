# Arquitetura – Sistema de Ouvidorias ARTESP

Documentação da arquitetura técnica, padrões de design e decisões arquiteturais do sistema.

## Visão Geral

O sistema é composto por três processos independentes. **Streamlit** e **Plotly Dash** são clientes HTTP distintos que consomem a mesma API FastAPI. Não há dependência direta entre Streamlit e Dash.

```
┌──────────────────────────┐        ┌──────────────────────────────┐
│  Streamlit  (porta 8501) │        │  Plotly Dash  (porta 8050)   │
│  app.py + pages/         │        │  run_dash.py                 │
│  auth.py                 │        │  qualidade_dash/             │
└────────────┬─────────────┘        └───────────────┬──────────────┘
             │ HTTP (httpx)                         │ HTTP (httpx)
             │ api/client/                          │ qualidade_dash/api_client.py
             └───────────────────┬──────────────────┘
                                 ▼
┌────────────────────────────────────────────────────────────────────┐
│  FastAPI  (porta 8000)                                             │
│  api/main.py  →  api/routers/  →  api/services/                   │
│  auth · ouvidorias · catalogo · autos · admin ·                    │
│  dashboard produtividade · dashboard qualidade                     │
└────────────────────────────────┬───────────────────────────────────┘
                                 │ chamadas diretas (Python)
┌────────────────────────────────▼───────────────────────────────────┐
│  repositories/                                                     │
│  ouvidoria_repo.py         ouvidoria_write_repo.py                 │
│  catalog_repo.py           autos_repo.py                          │
│  admin_write_repo.py       municipios_repo.py                     │
│  pontuacao.py                                                      │
│  dashboard/produtividade_repo.py                                   │
│  dashboard/qualidade_novo_repo.py                                  │
│  relatorios/reclamacoes_repo.py                                    │
└────────────────────────────────┬───────────────────────────────────┘
                                 │ SQLAlchemy ORM
┌────────────────────────────────▼───────────────────────────────────┐
│  models/  +  database/                                             │
│  PostgreSQL  (porta 5432  —  banco: souvi)                         │
└────────────────────────────────────────────────────────────────────┘
```

**Regra fundamental:** nenhum arquivo de `pages/`, `auth.py` ou `app.py` pode importar de `repositories/`, `models/` ou `database/` — todo acesso ao banco passa pela API.

---

## Stack

| Camada | Tecnologia |
|---|---|
| Frontend principal | Streamlit 1.54 (multi-page app) |
| Dashboard interativo | Plotly Dash |
| Backend API | FastAPI 0.115 + Uvicorn |
| Autenticação | JWT (python-jose, HS256, 60 min) |
| ORM | SQLAlchemy 2.0 (Declarative, `mapped_column`) |
| Banco de dados | PostgreSQL (psycopg2-binary) |
| HTTP Client | httpx (Streamlit → FastAPI, Dash → FastAPI) |
| Runtime | Python 3.13, venv em `.venv/` |

---

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

---

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

### 4. Camada de Cliente HTTP

Streamlit e Dash não acessam o banco diretamente — tudo passa pela API:

```python
# pages/01_Ouvidorias.py
from api.client.ouvidoria_client import listar_ouvidorias
ouvidorias = listar_ouvidorias(token=st.session_state["token"], ...)

# qualidade_dash/api_client.py
response = httpx.get(f"{API_BASE}/dashboard/qualidade-v2/...")
```

---

## Fluxos de Dados

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

---

## Autenticação

1. `POST /auth/login` — valida email + senha (bcrypt), retorna JWT
2. JWT armazenado em `st.session_state["api_session"]` (server-side, não vai ao browser)
3. Todas as requests HTTP incluem `Authorization: Bearer <token>`
4. `api/deps.py` — `usuario_corrente()` decodifica o token em cada endpoint
5. `requer_gestor()` — bloqueia acesso de técnicos a endpoints administrativos
6. Endpoints do dashboard de qualidade são públicos (analytics interno, read-only)

```python
# Variável obrigatória no .env
JWT_SECRET_KEY=<chave-aleatória-64-chars>
```

---

## Contratos de Dados

`repositories/types.py` define todos os TypedDicts. Os schemas Pydantic em `api/schemas/` são a contraparte HTTP — cada TypedDict tem um schema equivalente com `model_config = {"from_attributes": True}`.

| TypedDict | Schema Pydantic | Endpoint |
|---|---|---|
| `OuvidoriaResumoDict` | `OuvidoriaResumoSchema` | `GET /ouvidorias` |
| `OuvidoriaDetalheDict` | `OuvidoriaDetalheSchema` | `GET /ouvidorias/{id}` |
| `CategoriaDict` | `CategoriaSchema` | `GET /catalogo/categorias` |
| `AutoDict` | `AutoSchema` | `GET /autos` |
| `UsuarioDict` | `UsuarioSchema` | `GET /admin/usuarios` |

---

## Modelo de Dados

### Status da Ouvidoria (fluxo)

```
AGUARDANDO_ACOES
    → (gestor atribui técnico)       → EM_ANALISE_TECNICA
    → (todos técnicos respondem)     → RETORNO_TECNICO
    → (gestor conclui)               → CONCLUIDO

    → (gestor ativa permissionária)  → AGUARDANDO_PERMISSIONARIA
        → (gestor registra resposta) → AGUARDANDO_ACOES
```

### Diagrama ER (Conceitual)

```
municipios ──< trechos_auto_linha >──< autos_linha >── permissionarias
                                              │
                                       reclamacao_autos
                                              │
gerencias ──< coordenacoes ──< usuarios
                                    │
                             ouvidoria_tecnicos >──┐
                                                   │
ouvidorias ──< reclamacoes                         │
     │              └──< reclamacao_autos          │
     │                                             │
     ├──< ouvidoria_tecnicos >── usuarios ─────────┘
     ├──< respostas_tecnicas >── usuarios
     ├──< respostas_permissionaria >── usuarios
     └──< anexos_ouvidoria >── usuarios

categorias ──< subcategorias
categorias ──< reclamacoes
subcategorias ──< reclamacoes
```

### Tabelas Principais

| Tabela | Modelo | Descrição |
|---|---|---|
| `permissionarias` | `Permissionaria` | Empresas operadoras |
| `autos_linha` | `AutoLinha` | Auto de linha (tipo, região metropolitana) |
| `trechos_auto_linha` | `TrechoAutoLinha` | Municípios A→B atendidos por cada auto |
| `municipios` | `Municipio` | Municípios de SP (cod_ibge, populacao) |
| `gerencias` | `Gerencia` | Gerências da ARTESP |
| `coordenacoes` | `Coordenacao` | Coordenações (ligadas a gerência) |
| `usuarios` | `Usuario` | Gestores e técnicos |
| `categorias` | `Categoria` | Categorias de reclamação |
| `subcategorias` | `Subcategoria` | Subcategorias vinculadas a categoria |
| `ouvidorias` | `Ouvidoria` | Processo principal (protocolo, prazo, status) |
| `reclamacoes` | `Reclamacao` | Itens de reclamação |
| `reclamacao_autos` | `ReclamacaoAuto` | Autos vinculados (N:N, com pontuação) |
| `ouvidoria_tecnicos` | `OuvidoriaTecnico` | Técnicos atribuídos (N:N, com `respondido`) |
| `respostas_tecnicas` | `RespostaTecnica` | Resposta por técnico |
| `respostas_permissionaria` | `RespostaPermissionaria` | Resposta da empresa |
| `anexos_ouvidoria` | `AnexoOuvidoria` | Arquivos em disco (`uploads/nome_storage`) |

### Enums

```python
TipoServico:
    "Regular – Intermunicipal"
    "Regular – Metropolitano"
    "Fretamento Intermunicipal"
    "Fretamento Metropolitano"

StatusOuvidoria:
    "Aguardando ações"
    "Aguardando resposta da permissionária"
    "Em análise técnica"
    "Retorno técnico"
    "Concluído"
```

---

## Perfis e Permissões

| Ação | Gestor | Técnico |
|---|---|---|
| Ver lista de ouvidorias | Todas | Apenas atribuídas |
| Criar / Editar / Excluir ouvidoria | ✅ | ❌ |
| Atribuir técnicos | ✅ | ❌ |
| Resposta de permissionária | ✅ | ❌ |
| Concluir ouvidoria | ✅ | ❌ |
| Resposta técnica | ❌ | ✅ (atribuídas) |
| Admin (usuários, categorias, etc.) | ✅ | ❌ |
| Dashboards | ✅ | ❌ |

A proteção ocorre em dois pontos:
1. **API** — `requer_gestor()` nos endpoints administrativos (HTTP 403)
2. **Streamlit** — `auth.require_gestor()` antes de renderizar a página (st.stop)

---

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

# Testes
pytest tests/ -v

# Documentação interativa da API
# http://localhost:8000/docs
```

---

## Migrations (Alembic)

```bash
# Após alterar models/
alembic revision --autogenerate -m "descricao"
# Revisar migrations/versions/xxxxx_descricao.py
alembic upgrade head
# Commitar: migration + models/
```

---

## Como Adicionar um Endpoint

1. Criar/atualizar `api/schemas/*.py` (request e response)
2. Adicionar função em `api/routers/*.py` (chamar repositório ou service)
3. Criar em `api/services/` **apenas** se houver orquestração de múltiplos repositórios
4. Adicionar função em `api/client/*.py` para o Streamlit consumir
5. Adicionar teste de paridade em `tests/`

---

## Testes de Paridade

A suite em `tests/` verifica que cada endpoint retorna exatamente os mesmos dados que o repositório retorna diretamente:

```python
esperado = get_categorias()               # repositório direto (fonte da verdade)
r = client.get("/catalogo/categorias", headers=headers_gestor)
assert {c["id"] for c in esperado} == {c["id"] for c in r.json()}
```

**Limpeza de dados de teste:** `conftest.py` cria usuários `_pytest_*` no início e remove **todos** os dados com prefixo `_pytest_%` no início e fim de cada sessão.

---

## Referências

- [SQLAlchemy ORM 2.0](https://docs.sqlalchemy.org/en/20/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Plotly Dash](https://dash.plotly.com/)
- [Alembic](https://alembic.sqlalchemy.org/)
- [Streamlit](https://docs.streamlit.io/)
