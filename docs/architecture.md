# Arquitetura – Sistema de Ouvidorias ARTESP

## Visão Geral

Sistema web para gerenciamento de ouvidorias (reclamações de passageiros) recebidas pela ARTESP. Dois perfis de usuário operam o sistema: **Gestor** (SUCOL) e **Técnico** (gerências/coordenações). O fluxo começa com o Gestor cadastrando uma ouvidoria e termina com ele concluindo após receber as respostas técnicas.

---

## Stack

| Camada | Tecnologia |
|---|---|
| Frontend | Streamlit 1.54 (multi-page app) |
| Backend API | FastAPI 0.115 + Uvicorn |
| Autenticação | JWT (python-jose, HS256, 60 min) |
| ORM | SQLAlchemy 2.0 (Declarative, `mapped_column`) |
| Banco de dados | PostgreSQL (psycopg2-binary) |
| HTTP Client | httpx (Streamlit → FastAPI) |
| Runtime | Python 3.13, venv em `.venv/` |

---

## Arquitetura em Camadas

```
┌─────────────────────────────────────────────┐
│          Streamlit (pages/)                 │  UI pura
│          auth.py, app.py                   │  sem SQLAlchemy
└─────────────────┬───────────────────────────┘
                  │ HTTP (httpx, JWT Bearer)
┌─────────────────▼───────────────────────────┐
│          FastAPI (api/routers/)             │  API REST
│          api/services/                      │  orquestração
│          api/schemas/                       │  Pydantic DTOs
└─────────────────┬───────────────────────────┘
                  │ chamadas diretas (Python)
┌─────────────────▼───────────────────────────┐
│          repositories/                      │  Data Access Layer
│          (retornam TypedDicts)              │  sem ORM exposto
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│          models/ + database/                │  SQLAlchemy ORM
│          PostgreSQL                         │
└─────────────────────────────────────────────┘
```

**Regra fundamental:** nenhum arquivo de `pages/`, `auth.py` ou `app.py` pode importar de `repositories/`, `models/` ou `database/`.

---

## Autenticação

1. `POST /auth/login` — valida email + senha (bcrypt), retorna JWT
2. JWT armazenado em `st.session_state["api_session"]` (server-side, não vai ao browser)
3. Todas as requests HTTP incluem `Authorization: Bearer <token>`
4. `api/deps.py` — `usuario_corrente()` decodifica o token em cada endpoint
5. `requer_gestor()` — bloqueia acesso de técnicos a endpoints administrativos

```python
# Variável obrigatória no .env
JWT_SECRET_KEY=<chave-aleatória-64-chars>
```

---

## Padrão de Sessão com Banco

Apenas `db_session()` é usado (commit/rollback automático). A conversão ORM → TypedDict ocorre **dentro** do `with db_session()`.

```python
# Leitura — conversão dentro da sessão
with db_session() as s:
    objs = s.query(Modelo).options(joinedload(...)).all()
    return [ModeloDict(id=o.id, ...) for o in objs]

# Escrita — commit automático
with db_session() as s:
    s.add(NovoObjeto(...))
```

Nenhum objeto SQLAlchemy vivo sai da sessão — eliminando `DetachedInstanceError`.

---

## Fluxo Típico de Leitura

```
pages/01_Ouvidorias.py
  └── from api.client.ouvidoria_client import listar_ouvidorias
        └── GET /ouvidorias  (httpx)
              └── api/routers/ouvidorias.py → get_ouvidorias(...)
                    └── repositories/ouvidoria_repo.py
                          └── db_session() + ORM + _to_resumo()
                                └── list[OuvidoriaResumoDict]
```

## Fluxo Típico de Escrita

```
pages/03_Detalhe_Ouvidoria.py
  └── from api.client.ouvidoria_client import atribuir_tecnico
        └── POST /ouvidorias/{id}/atribuir-tecnico  (httpx)
              └── api/routers/ouvidorias.py → atribuir_tecnico(...)
                    └── repositories/ouvidoria_write_repo.py
                          └── db_session() + ORM writes
```

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

### Diagrama Entidade-Relacionamento (simplificado)

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

## Testes de Paridade

A suite em `tests/` verifica que cada endpoint retorna exatamente os mesmos dados que o repositório retorna diretamente:

```python
# Padrão dos testes de leitura
esperado = get_categorias()               # repositório direto (fonte da verdade)
r = client.get("/catalogo/categorias", headers=headers_gestor)
assert {c["id"] for c in esperado} == {c["id"] for c in r.json()}
```

**Limpeza de dados de teste:** `conftest.py` cria usuários `_pytest_*` no início e remove **todos** os dados com prefixo `_pytest_%` no início e fim de cada sessão.

---

## Como Rodar

```bash
# Terminal 1 — API FastAPI
uvicorn api.main:app --port 8000 --reload

# Terminal 2 — Streamlit
streamlit run app.py

# Testes
pytest tests/ -v

# Documentação interativa da API
# http://localhost:8000/docs
```

---

## Como Adicionar um Endpoint

1. Criar/atualizar `api/schemas/*.py` (request e response)
2. Adicionar função em `api/routers/*.py` (chamar repositório ou service)
3. Criar em `api/services/` **apenas** se houver orquestração de múltiplos repositórios
4. Adicionar função em `api/client/*.py` para o Streamlit consumir
5. Adicionar teste de paridade em `tests/`

---

## Busca por Trecho

`repositories/autos_repo.py → buscar_autos_por_trecho()` usa **EXISTS subqueries** sobre `trechos_auto_linha` com FK para `municipios`:

```python
q = q.filter(exists().where(
    (TrechoAutoLinha.auto_id == AutoLinha.id) &
    (TrechoAutoLinha.municipio_a_id == mun_id_a)
))
```
