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
│   ├── auto_linha.py               # Auto de linha (itinerário operado por permissionária)
│   ├── parada_auto_linha.py        # Cidades atendidas por cada auto
│   ├── ouvidoria.py                # Processo de ouvidoria (entidade principal)
│   ├── reclamacao.py               # Item de reclamação dentro de uma ouvidoria
│   ├── associations.py             # OuvidoriaTecnico, ReclamacaoAuto (tabelas N:N)
│   ├── resposta_tecnica.py         # Resposta registrada por um técnico
│   └── __init__.py                 # Re-exporta todos os modelos
│
├── database/
│   ├── connection.py               # Engine, SessionLocal, get_session(), db_session(), init_db()
│   └── seed.py                     # Importa CSVs + cria usuário admin padrão
│
├── pages/
│   ├── 01_Ouvidorias.py            # Listagem com filtros, ações rápidas
│   ├── 02_Nova_Ouvidoria.py        # Cadastro de ouvidoria + reclamações (Gestor)
│   ├── 03_Detalhe_Ouvidoria.py     # Detalhe, edição, atribuição de técnicos (Gestor)
│   ├── 04_Responder.py             # Resposta técnica + edição de reclamações (Técnico)
│   └── 05_Admin.py                 # CRUD: usuários, categorias, gerências, coordenações
│
├── docs/
│   ├── architecture.md             # Este arquivo
│   └── coding_rules.md             # Padrões de código do projeto
│
├── tasks/
│   └── todo.md                     # Backlog e pendências
│
└── Autos de Linha Ativas.csv       # Fonte de dados (Latin-1, sep=;)
    Pontos dos Autos de linha.csv   # Fonte de paradas (Latin-1, sep=;)
```

---

## Modelo de Dados

### Diagrama Entidade-Relacionamento (simplificado)

```
permissionarias ──< autos_linha >──< paradas_auto_linha
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
     └──< respostas_tecnicas >── usuarios
```

### Tabelas Principais

| Tabela | Descrição |
|---|---|
| `permissionarias` | Empresas operadoras (ex: COMETA) |
| `autos_linha` | Auto de linha com número no formato `0001-A` |
| `paradas_auto_linha` | Cidades atendidas por cada auto (para busca por trecho) |
| `gerencias` | Gerências da ARTESP |
| `coordenacoes` | Coordenações, vinculadas a uma gerência |
| `usuarios` | Gestores e técnicos; ligados a gerência + coordenação |
| `categorias` | Categorias de reclamação (ex: Acessibilidade, Pontualidade) |
| `ouvidorias` | Processo principal; tem SEI, prazo, status, reclamações |
| `reclamacoes` | Itens de reclamação dentro de uma ouvidoria |
| `reclamacao_autos` | Autos vinculados a uma reclamação (N:N, com pontuação) |
| `ouvidoria_tecnicos` | Técnicos atribuídos a uma ouvidoria (N:N, com flag `respondido`) |
| `respostas_tecnicas` | Resposta registrada por cada técnico |

### Status da Ouvidoria (fluxo)

```
AGUARDANDO_ACOES
    → (gestor atribui técnico) → EM_ANALISE_TECNICA
    → (todos técnicos respondem) → RETORNO_TECNICO
    → (gestor conclui) → CONCLUIDO

Em qualquer momento o gestor pode alterar manualmente o status
ou mover para AGUARDANDO_PERMISSIONARIA
```

---

## Perfis e Permissões

| Ação | Gestor | Técnico |
|---|---|---|
| Ver lista de ouvidorias | Todas | Apenas atribuídas |
| Criar ouvidoria | ✅ | ❌ |
| Editar SEI / prazo / status | ✅ | ❌ |
| Atribuir técnicos | ✅ | ❌ |
| Concluir / Excluir ouvidoria | ✅ | ❌ |
| Registrar resposta técnica | ❌ | ✅ (atribuídas) |
| Editar reclamações ao responder | ❌ | ✅ (atribuídas) |
| Admin (usuários, categorias) | ✅ | ❌ |

---

## Fluxo de Sessão

1. `app.py` exibe formulário de login.
2. `auth.autenticar()` verifica senha bcrypt e armazena o objeto `Usuario` em `st.session_state["usuario"]`.
3. Todas as páginas chamam `auth.require_auth()` ou `auth.require_gestor()` no topo — redireciona para login se não autenticado.
4. `auth.usuario_logado()` retorna o objeto do usuário da sessão.
5. Logout limpa toda a `session_state` e redireciona para `app.py`.

---

## Padrão de Sessão com Banco

Dois helpers em `database/connection.py`:

```python
# Para leituras (o chamador fecha manualmente no finally)
session = get_session()
try:
    ...
finally:
    session.close()

# Para escrita (commit/rollback automático)
with db_session() as session:
    session.add(...)
```

**Regra crítica**: Nunca retornar objetos SQLAlchemy vivos fora da sessão. Converter para `dict` enquanto a sessão estiver aberta para evitar `DetachedInstanceError`.

---

## Fontes de Dados

| Arquivo | Encoding | Separador | Uso |
|---|---|---|---|
| `Autos de Linha Ativas.csv` | Latin-1 | `;` | Cria `autos_linha` e `permissionarias` |
| `Pontos dos Autos de linha.csv` | Latin-1 | `;` | Cria `paradas_auto_linha` |

Colunas relevantes:
- **Ativas**: `n° Autos`, `Iti`, `Permissionária`, `Denominação da Linha`
- **Pontos**: `Autos`, `Itinerario`, `Cidade Inicial da linha`, `Cidade Fim da linha`, `Cidade Atendida`

Número do auto gerado como: `f"{int(n_autos):04d}-{iti}"` → ex: `"0001-A"`

---

## Busca por Trecho

A função `buscar_autos_por_trecho(cidade_a, cidade_b)` usa **EXISTS subqueries** sobre `paradas_auto_linha` para retornar autos que atendem **ambas** as cidades, não apenas as pontas do itinerário:

```python
q = session.query(AutoLinha).filter(
    exists().where((ParadaAutoLinha.auto_id == AutoLinha.id) & (ParadaAutoLinha.cidade == cidade_a)),
    exists().where((ParadaAutoLinha.auto_id == AutoLinha.id) & (ParadaAutoLinha.cidade == cidade_b))
)
```
