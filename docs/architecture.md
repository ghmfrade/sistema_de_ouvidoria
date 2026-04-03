# Arquitetura – Sistema de Ouvidorias ARTESP

## Visão Geral

Sistema web para gerenciamento de ouvidorias (reclamações de passageiros) recebidas pela ARTESP. Dois perfis de usuário operam o sistema: **Gestor** (SUCOL) e **Técnico** (gerências/coordenações). O fluxo começa com o Gestor cadastrando uma ouvidoria e termina com ele concluindo após receber as respostas técnicas.

---

## Stack

| Camada | Tecnologia |
|---|---|
| Frontend | Streamlit 1.54 (multi-page app) |
| ORM | SQLAlchemy 2.0 (Declarative, `mapped_column`) |
| Banco de dados | PostgreSQL 16 (local, porta 5432) |
| Autenticação | bcrypt + `st.session_state` |
| Leitura de dados | pandas (CSVs em Latin-1, separador `;`) |
| Runtime | Python 3.14, venv em `.venv/` |

---

## Estrutura de Arquivos

```
sistema_de_ouvidoria/
├── app.py                          # Entry point — tela de login
├── auth.py                         # Hash de senha, verificação, guards de rota
├── requirements.txt
├── .env                            # Credenciais PostgreSQL (não versionar)
│
├── models/
│   ├── base.py                     # DeclarativeBase
│   ├── permissionaria.py           # Empresa operadora de linha
│   ├── gerencia.py                 # Unidade organizacional (nível 1)
│   ├── coordenacao.py              # Unidade organizacional (nível 2, ligada a gerência)
│   ├── usuario.py                  # Usuário (gestor ou técnico)
│   ├── categoria.py                # Categoria de reclamação (ex: Acessibilidade)
│   ├── subcategoria.py             # Subcategoria vinculada a uma categoria
│   ├── auto_linha.py               # Auto de linha; inclui TipoServico e campos metropolitanos
│   ├── parada_auto_linha.py        # Municípios atendidos por cada auto (FK → municipios)
│   ├── municipio.py                # Municípios do estado de SP (cod_ibge, populacao)
│   ├── ouvidoria.py                # Processo de ouvidoria (entidade principal)
│   ├── reclamacao.py               # Item de reclamação dentro de uma ouvidoria
│   ├── anexo_ouvidoria.py          # Arquivo anexado a uma ouvidoria
│   ├── associations.py             # OuvidoriaTecnico, ReclamacaoAuto (tabelas N:N)
│   ├── resposta_permissionaria.py  # Resposta registrada pela permissionária
│   ├── resposta_tecnica.py         # Resposta registrada por um técnico
│   └── __init__.py                 # Re-exporta todos os modelos
│
├── database/
│   ├── connection.py               # Engine, SessionLocal, get_session(), db_session(), init_db()
│   └── seed.py                     # Importa CSVs + cria usuário admin padrão
│
├── repositories/                   # Camada de acesso a dados — apenas ORM, sem lógica de UI
│   ├── ouvidoria_repo.py           # Leitura: get_ouvidoria_completa, get_ouvidorias, …
│   ├── ouvidoria_write_repo.py     # Escrita: criar_ouvidoria, registrar_resposta_tecnica, …
│   ├── catalog_repo.py             # Leitura: get_categorias, get_tecnicos_ativos, …
│   ├── admin_write_repo.py         # Escrita: criar_usuario, toggle_categoria, …
│   ├── autos_repo.py               # Leitura: get_todos_autos, buscar_autos_por_trecho, …
│   ├── municipios_repo.py          # Leitura: get_municipios_sp, get_municipios_por_tipo_servico
│   ├── dashboard/
│   │   ├── produtividade_repo.py   # Queries ORM de produtividade (func, case, cast, joins)
│   │   └── qualidade_repo.py       # Queries ORM de qualidade (func, case, cast, joins)
│   └── __init__.py
│
├── utils/                          # Camada intermediária — cache, formatação, lógica frontend
│   ├── loaders_ouvidoria.py        # Formata objetos ORM de ouvidoria para dicts da UI
│   ├── loaders_catalog.py          # Wrappers cacheados para catálogo (categorias, gerências…)
│   ├── loaders_auto.py             # Wrappers cacheados para autos, cidades, permissionárias
│   ├── loaders_admin.py            # Wrappers cacheados para listagens administrativas
│   ├── loaders_dashboard.py        # Wrappers @st.cache_data(ttl=120) para dashboard
│   ├── ouvidoria_ops.py            # Fachada: listar_ouvidorias (com formatação), atribuir_tecnico…
│   ├── admin_ops.py                # Fachada: re-exporta operações de admin_write_repo
│   ├── formatters.py               # Funções puras de formatação (fmt_auto, prazo_circle_label…)
│   └── __init__.py                 # Re-exporta toda a API pública de utils/
│
├── pages/
│   ├── 01_Ouvidorias.py            # Listagem com filtros, ações rápidas
│   ├── 02_Nova_Ouvidoria.py        # Cadastro de ouvidoria + reclamações (Gestor)
│   ├── 03_Detalhe_Ouvidoria.py     # Detalhe, edição, atribuição de técnicos (Gestor)
│   ├── 04_Resposta_Permissionaria.py  # Registro de resposta da permissionária (Gestor)
│   ├── 05_Responder.py             # Resposta técnica + edição de reclamações (Técnico)
│   ├── 06_Dashboard_Produtividade.py  # Dashboard de produtividade interna
│   ├── 07_Dashboard_Qualidade.py   # Dashboard de qualidade por empresa/categoria
│   └── 08_Admin.py                 # CRUD: usuários, categorias, gerências, coordenações
│
├── docs/
│   ├── architecture.md             # Este arquivo
│   └── coding_rules.md             # Padrões de código do projeto
│
├── tasks/
│   └── todo.md                     # Backlog e pendências
│
└── uploads/                        # Anexos salvos em disco
```

---

## Padrão de Camadas (regra fundamental)

```
pages/  →  utils/  →  repositories/  →  models/ + database/
```

| Camada | Responsabilidade | O que NÃO deve fazer |
|---|---|---|
| **pages/** | Renderizar UI, ler `session_state`, chamar utils | Chamar `repositories/` ou `db_session()` diretamente |
| **utils/** | Cache (`@st.cache_data`), formatar ORM→dict, coordenar lógica de negócio frontend | Retornar objetos ORM vivos para as pages; duplicar queries que já existem nos repos |
| **repositories/** | Queries e escritas ORM; retornar objetos SQLAlchemy expunged ou primitivos | Importar `streamlit`; conter lógica de apresentação |
| **models/** | Definir tabelas e relacionamentos SQLAlchemy | Ter lógica de negócio ou dependências externas |

### Fluxo típico de leitura

```python
# page → utils/loader → repository
carregar_detalhe_ouvidoria(oid)          # utils/loaders_ouvidoria.py
  └── get_ouvidoria_completa(oid)        # repositories/ouvidoria_repo.py
        └── db_session() + joinedload    # database/connection.py + models/
```

### Fluxo típico de escrita

```python
# page → utils/*_ops → repository
atribuir_tecnico(ouvidoria_id, tecnico_id)   # utils/ouvidoria_ops.py
  └── _atribuir_tecnico(...)                 # repositories/ouvidoria_write_repo.py
        └── db_session() + ORM writes
```

---

## Modelo de Dados

### Diagrama Entidade-Relacionamento (simplificado)

```
municipios ──< paradas_auto_linha >──< autos_linha >── permissionarias
                                            │
                                     reclamacao_autos
                                            │
gerencias ──< coordenacoes ──< usuarios
                                   │
                            ouvidoria_tecnicos >──┐
                                                  │
ouvidorias ──< reclamacoes                        │
     │              └──< reclamacao_autos         │
     │                                            │
     ├──< ouvidoria_tecnicos >── usuarios ────────┘
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
| `permissionarias` | `Permissionaria` | Empresas operadoras (ex: COMETA) |
| `autos_linha` | `AutoLinha` | Auto de linha; `tipo` (TipoServico), campos metropolitanos (`regiao_metropolitana`, `sub_regiao`, etc.), flag `ativo` |
| `paradas_auto_linha` | `ParadaAutoLinha` | Municípios atendidos por cada auto (FK → `municipios.id`) |
| `municipios` | `Municipio` | Municípios de SP com `cod_ibge` e `populacao` |
| `gerencias` | `Gerencia` | Gerências da ARTESP |
| `coordenacoes` | `Coordenacao` | Coordenações, vinculadas a uma gerência |
| `usuarios` | `Usuario` | Gestores e técnicos; ligados a gerência + coordenação |
| `categorias` | `Categoria` | Categorias de reclamação (ex: Acessibilidade, Pontualidade) |
| `subcategorias` | `Subcategoria` | Subcategorias vinculadas a uma categoria; têm flag `ativo` |
| `ouvidorias` | `Ouvidoria` | Processo principal; tem protocolo, prazo, prazo_permissionaria, status |
| `reclamacoes` | `Reclamacao` | Itens de reclamação; `tipo_servico` (TipoServico), `empresa_fretamento` |
| `reclamacao_autos` | `ReclamacaoAuto` | Autos vinculados a uma reclamação (N:N, com pontuação proporcional) |
| `ouvidoria_tecnicos` | `OuvidoriaTecnico` | Técnicos atribuídos a uma ouvidoria (N:N, com flag `respondido` e `respondido_em`) |
| `respostas_tecnicas` | `RespostaTecnica` | Resposta registrada por cada técnico |
| `respostas_permissionaria` | `RespostaPermissionaria` | Respostas recebidas da permissionária; registradas pelo gestor |
| `anexos_ouvidoria` | `AnexoOuvidoria` | Arquivos anexados; `nome_storage` aponta para `uploads/` |

### Enum TipoServico (em `auto_linha.py`)

```
REGULAR_INTERMUNICIPAL   = "Regular – Intermunicipal"
REGULAR_METROPOLITANO    = "Regular – Metropolitano"
FRETAMENTO_INTERMUNICIPAL = "Fretamento Intermunicipal"
FRETAMENTO_METROPOLITANO  = "Fretamento Metropolitano"
```

### Status da Ouvidoria (fluxo)

```
AGUARDANDO_ACOES
    → (gestor atribui técnico) → EM_ANALISE_TECNICA
    → (todos técnicos respondem) → RETORNO_TECNICO
    → (gestor conclui) → CONCLUIDO

    → (gestor move manualmente) → AGUARDANDO_PERMISSIONARIA
        → (gestor registra resposta da perm.) → AGUARDANDO_ACOES

Em qualquer momento o gestor pode alterar manualmente o status.
```

---

## Perfis e Permissões

| Ação | Gestor | Técnico |
|---|---|---|
| Ver lista de ouvidorias | Todas | Apenas atribuídas |
| Criar ouvidoria | ✅ | ❌ |
| Editar SEI / prazo / status | ✅ | ❌ |
| Atribuir técnicos | ✅ | ❌ |
| Registrar resposta de permissionária | ✅ | ❌ |
| Concluir / Excluir ouvidoria | ✅ | ❌ |
| Registrar resposta técnica | ❌ | ✅ (atribuídas) |
| Editar reclamações ao responder | ❌ | ✅ (atribuídas) |
| Admin (usuários, categorias, gerências) | ✅ | ❌ |
| Ver dashboards | ✅ | ❌ |

---

## Fluxo de Sessão

1. `app.py` exibe formulário de login.
2. `auth.autenticar()` verifica senha bcrypt e armazena o objeto `Usuario` em `st.session_state["usuario"]`.
3. Todas as páginas chamam `auth.require_auth()` ou `auth.require_gestor()` no topo — redireciona para login se não autenticado.
4. `auth.usuario_logado()` retorna o objeto do usuário da sessão.
5. Logout limpa toda a `session_state` e redireciona para `app.py`.

---

## Padrão de Sessão com Banco

Apenas o `db_session()` context manager é usado (commit/rollback automático). Leituras também usam `db_session()` nos repositórios, com `s.expunge_all()` para liberar objetos antes de retorná-los.

```python
# Leitura — expunge garante objetos detachados seguros
with db_session() as s:
    objs = s.query(Modelo).options(...).all()
    s.expunge_all()
    return objs

# Escrita — commit automático ao sair do with
with db_session() as s:
    s.add(NovoObjeto(...))
```

**Regra crítica**: Nunca retornar objetos SQLAlchemy vivos fora da sessão. Os loaders em `utils/` convertem para `dict` enquanto o objeto ainda está acessível (após `expunge_all`, os atributos simples ainda funcionam mas relacionamentos lazy falham).

---

## Fontes de Dados

| Arquivo | Encoding | Separador | Uso |
|---|---|---|---|
| `Autos de Linha Ativas.csv` | Latin-1 | `;` | Cria `autos_linha` e `permissionarias` (tipo REGULAR_INTERMUNICIPAL) |
| `Pontos dos Autos de linha.csv` | Latin-1 | `;` | Cria `paradas_auto_linha` para linhas intermunicipais |
| `linhas metropolitanas.xlsx` | UTF-8 | — | Cria `autos_linha` metropolitanos + suas paradas |
| `pop_municipios.csv` | — | `;` | Cria tabela `municipios` com código IBGE e população |

---

## Busca por Trecho

A função `buscar_autos_por_trecho()` em `repositories/autos_repo.py` usa **EXISTS subqueries** sobre `paradas_auto_linha` com FK para `municipios`, filtrando por `tipo` de serviço, permissionária e região metropolitana:

```python
q = q.filter(exists().where(
    (ParadaAutoLinha.auto_id == AutoLinha.id) &
    (ParadaAutoLinha.municipio_id == mun_id_a)
))
```
