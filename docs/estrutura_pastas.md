# Estrutura de Pastas — Sistema de Ouvidorias ARTESP

## Visão Geral

```
sistema_de_ouvidoria/
├── api/                         # Camada FastAPI (backend desacoplado)
│   ├── main.py                  # FastAPI app + inclusão de routers
│   ├── deps.py                  # Dependências injetáveis (JWT, requer_gestor)
│   ├── schemas/                 # Pydantic schemas (DTOs de entrada e saída)
│   │   ├── auth.py              # LoginRequest, TokenResponse
│   │   ├── catalog.py           # CategoriaSchema, GerenciaSchema, ...
│   │   ├── ouvidoria.py         # OuvidoriaResumoSchema, OuvidoriaDetalheSchema, ...
│   │   ├── dashboard.py         # KpisProdutividadeSchema, ...
│   │   └── admin.py             # CriarUsuarioRequest, ToggleRequest, ...
│   ├── routers/                 # Endpoints FastAPI por domínio
│   │   ├── auth.py              # POST /auth/login, GET /auth/me
│   │   ├── catalogo.py          # GET /catalogo/*
│   │   ├── autos.py             # GET /autos/*
│   │   ├── ouvidorias.py        # GET+POST+PATCH+DELETE /ouvidorias/*
│   │   ├── dashboard.py         # GET /dashboard/produtividade/* e /qualidade/*
│   │   └── admin.py             # GET+POST+PATCH /admin/*
│   ├── services/                # Lógica de orquestração (onde há mais de um repo)
│   │   ├── auth_service.py      # autenticar(), criar_token(), decodificar_token()
│   │   └── ouvidoria_service.py # criar_ouvidoria_sem_anexos(), criar_ouvidoria_com_anexos()
│   └── client/                  # HTTP clients usados pelo Streamlit
│       ├── base.py              # get/post/patch/delete + ApiError
│       ├── auth_client.py       # login()
│       ├── enums.py             # STATUS_OUVIDORIA, TIPO_SERVICO (sem SQLAlchemy)
│       ├── catalogo_client.py   # carregar_categorias(), carregar_gerencias_ativas(), ...
│       ├── autos_client.py      # carregar_todos_autos(), buscar_autos_por_trecho(), ...
│       ├── ouvidoria_client.py  # listar_ouvidorias(), criar_ouvidoria(), ...
│       ├── dashboard_client.py  # query_kpis_produtividade(), query_evolucao_mensal(), ...
│       └── admin_client.py      # listar_usuarios_e_status(), criar_usuario(), ...
│
├── app.py                       # Entrypoint Streamlit (login + sidebar)
├── auth.py                      # Autenticação via API (sem SQLAlchemy)
│
├── pages/                       # Páginas Streamlit (UI pura, só consome api/client/)
│   ├── 01_Ouvidorias.py         # Listagem + filtros + ações por linha
│   ├── 02_Nova_Ouvidoria.py     # Formulário de criação + upload de anexos
│   ├── 03_Detalhe_Ouvidoria.py  # Detalhe + edição + atribuição + anexos
│   ├── 04_Resposta_Permissionaria.py
│   ├── 05_Responder.py          # Resposta técnica + edição de reclamações
│   ├── 06_Dashboard_Produtividade.py
│   ├── 07_Dashboard_Qualidade.py
│   └── 08_Admin.py              # Gestão de usuários, categorias, gerências
│
├── repositories/                # Data access layer — NUNCA modificar
│   ├── types.py                 # TypedDicts (contratos de dados)
│   ├── catalog_repo.py          # Leitura: categorias, gerências, técnicos
│   ├── autos_repo.py            # Leitura: autos de linha, trechos
│   ├── municipios_repo.py       # Leitura: municípios SP
│   ├── ouvidoria_repo.py        # Leitura: ouvidorias (detalhe, listagem, etc.)
│   ├── ouvidoria_write_repo.py  # Escrita: criar, editar, anexos, respostas
│   ├── admin_write_repo.py      # Escrita: usuários, categorias, gerências
│   ├── pontuacao.py             # Cálculo de pontuação de autos
│   └── dashboard/
│       ├── produtividade_repo.py
│       └── qualidade_repo.py
│
├── models/                      # SQLAlchemy ORM — NUNCA modificar
├── database/                    # Configuração + seeds — NUNCA modificar
├── migrations/                  # Alembic — NUNCA modificar
│
├── tests/                       # Suite de testes de paridade
│   ├── conftest.py              # Fixtures: TestClient, usuários de teste, limpeza _pytest_%
│   ├── test_e1_schemas.py       # Schemas Pydantic instanciam corretamente
│   ├── test_e2_auth.py          # Login JWT, validação de token
│   ├── test_e3_catalogo.py      # Paridade endpoints de catálogo e autos
│   ├── test_e4_ouvidorias.py    # Paridade endpoints de ouvidorias e dashboard
│   ├── test_e5_writes.py        # Ciclo completo de escrita de ouvidorias
│   └── test_e6_admin.py         # Paridade e escrita de admin
│
├── utils/                       # Utilitários de formatação (mantidos)
│   ├── formatters.py            # fmt_auto, fmt_ativo, prazo_circle_label, to_excel
│   ├── html_resumo.py           # gerar_html_resumo() — usado pela API server-side
│   └── types.py                 # View Models auxiliares
│
├── components/                  # Componentes Streamlit reutilizáveis
│   └── estilo_css.py
│
├── uploads/                     # Arquivos enviados pelos usuários
├── relatorios/                  # Relatórios HTML gerados
├── docs/                        # Documentação do projeto
└── .env                         # Variáveis de ambiente (não comitar)
```

---

## Fluxo de Dados Pós-Migração

```
Streamlit (pages/)
    │
    │  importa de
    ▼
api/client/          ← HTTP (httpx)
    │
    │  chama
    ▼
FastAPI (api/routers/)
    │
    │  delega para
    ▼
api/services/        ← apenas onde há orquestração
    │
    │  usa
    ▼
repositories/        ← Data Access Layer (TypedDicts)
    │
    │  acessa
    ▼
PostgreSQL
```

**Regra fundamental:** nenhum arquivo dentro de `pages/`, `auth.py` ou `app.py` pode importar de `repositories/`, `models/` ou `database/`.

---

## Autenticação

- JWT via `python-jose` (HS256, 60 min)
- Variável obrigatória: `JWT_SECRET_KEY` no `.env`
- Token armazenado em `st.session_state["api_session"]` (server-side, não exposto ao browser)
- Endpoints protegidos com `Authorization: Bearer <token>`
- `GET /auth/me` — retorna dados do usuário logado

---

## Como Adicionar um Novo Endpoint

1. **Schema** — criar/atualizar `api/schemas/*.py` (se há request/response novo)
2. **Router** — adicionar função em `api/routers/*.py` (chamar repositório ou service)
3. **Service** — criar em `api/services/` apenas se houver orquestração de múltiplos repos
4. **Client** — adicionar função em `api/client/*.py` para o Streamlit consumir
5. **Teste** — adicionar teste de paridade em `tests/test_e*.py`

---

## Execução em Paralelo

```bash
# Terminal 1 — API FastAPI
uvicorn api.main:app --port 8000 --reload

# Terminal 2 — Streamlit
streamlit run app.py
```

Documentação interativa da API: http://localhost:8000/docs

---

## Boas Práticas

| Camada | Deve importar de | Nunca importar de |
|--------|-----------------|-------------------|
| `pages/` | `api/client/`, `utils/formatters`, `components/` | `repositories/`, `models/`, `database/` |
| `api/routers/` | `repositories/`, `api/schemas/`, `api/services/`, `api/deps/` | `pages/`, `utils/loaders_*` |
| `api/services/` | `repositories/` | `pages/`, `streamlit` |
| `repositories/` | `models/`, `database/` | qualquer outra coisa |

---

## Testes

```bash
pytest tests/ -v            # todos os testes
pytest tests/test_e1_schemas.py  # schemas apenas
pytest tests/ -q            # resumido
```

Convenção de dados de teste: prefixo `_pytest_` em nomes/emails.
Limpeza automática: `conftest.py` remove todos os dados `_pytest_%` no início e fim da sessão.
