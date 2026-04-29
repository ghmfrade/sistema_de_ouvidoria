# 🏗️ Architecture — Sistema de Ouvidorias ARTESP

Documentação da arquitetura técnica, padrões de design e decisões arquiteturais do sistema.

## 📐 Visão Geral

O Sistema de Ouvidorias ARTESP segue uma arquitetura em camadas com separação clara de responsabilidades:

```
┌─────────────────────────────────────────────────────────┐
│              Streamlit Frontend (UI Layer)              │
│  ┌──────────────────────────────────────────────────┐  │
│  │  pages/                                          │  │
│  │  • 01_Ouvidorias.py (Listagem)                   │  │
│  │  • 02_Nova_Ouvidoria.py (Criação)                │  │
│  │  • 03_Detalhe_Ouvidoria.py (Visualização)        │  │
│  │  • 04_Resposta_Permissionaria.py                 │  │
│  │  • 05_Responder.py (Análise Técnica)             │  │
│  │  • 06_Dashboard_Produtividade.py                 │  │
│  │  • 07_Dashboard_Qualidade.py                     │  │
│  │  • 08_Admin.py (Gestão)                          │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  components/  (Componentes Streamlit)            │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│         Application Logic & Services Layer              │
│  ┌──────────────────────────────────────────────────┐  │
│  │  auth.py (Autenticação)                          │  │
│  │  utils/ (Utilitários diversos)                   │  │
│  │  relatorios/ (Geração de relatórios)             │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│          Data Access Layer (Repository Pattern)        │
│  ┌──────────────────────────────────────────────────┐  │
│  │  repositories/                                   │  │
│  │  • *_repo.py (Read-only queries)                 │  │
│  │  • *_write_repo.py (Insert/Update/Delete)        │  │
│  │  • types.py (TypedDict contracts)                │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│           ORM & Domain Layer (SQLAlchemy)              │
│  ┌──────────────────────────────────────────────────┐  │
│  │  models/                                         │  │
│  │  • Entities (Ouvidoria, Reclamacao, Usuario...)  │  │
│  │  • Relationships (1:N, N:N)                      │  │
│  │  • Enums (StatusOuvidoria, TipoUsuario...)       │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│            Database Layer (PostgreSQL)                  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  database/                                       │  │
│  │  • connection.py (Pool de conexões, db_session)  │  │
│  │  • migrations/ (Alembic versioning)              │  │
│  │  • Tabelas normalizadas                          │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## 🎯 Padrões de Design

### 1. Repository Pattern

Separação clara entre **leitura** e **escrita** de dados:

#### Read Repositories
```python
# repositories/ouvidoria_repo.py
def listar_ouvidorias(...) -> list[OuvidoriaResumoDict]:
    """Retorna lista de Ouvidorias como TypedDict (imutável)."""
    with db_session() as s:
        # Query e conversão ORM → TypedDict
        # Nunca retorna instâncias SQLAlchemy fora da sessão
```

**Características:**
- Não modificam o banco de dados
- Retornam **TypedDicts** (contratos de dados imutáveis)
- Conversão ORM → TypedDict acontece **dentro** de `with db_session()`
- Garantem que instâncias ORM nunca escapem da sessão

#### Write Repositories
```python
# repositories/ouvidoria_write_repo.py
def criar_ouvidoria(protocolo: str, ...) -> int:
    """Cria ouvidoria e retorna seu ID."""
    with db_session() as s:
        # Criação de instâncias
        # Commit automático ao sair do context manager
```

**Características:**
- Inserem, atualizam ou deletam registros
- Gerenciam transações automaticamente
- Validam integridade referencial
- Retornam valores escalares ou IDs

### 2. Type Safety com TypedDicts

Contratos de dados explícitos definem exatamente o que cada função retorna:

```python
# repositories/types.py
class OuvidoriaResumoDict(TypedDict):
    id: int
    protocolo: str | None
    status: str  # StatusOuvidoria.value
    prazo: date | None
    atribuicoes: list[OuvidoriaTecnicoDict]
```

**Benefícios:**
- Autocompletar em IDEs (`.` + atributo é seguro)
- Documentação implícita (não precisa de docstring)
- Type checking estático (mypy, pyright)
- Evita retornar dados desnecessários (selectivity)

### 3. Session Management com Context Manager

```python
from database.connection import db_session

with db_session() as s:
    # Session válida aqui
    # Commit automático ao sair
    pass  # Session fechada automaticamente
```

**Garantias:**
- ✅ Commit automático em sucesso
- ✅ Rollback automático em exceção
- ✅ Session sempre fechada
- ✅ Sem "connection leaks"

### 4. Lazy Loading com Joinedload

Carregamento eficiente de relacionamentos:

```python
# Carrega ouvidoria com reclamações em uma query (eager loading)
ouvidoria = session.query(Ouvidoria).options(
    joinedload(Ouvidoria.reclamacoes)
).first()
```

**Por quê:**
- N+1 query problem evitado
- Performance melhorada
- Dados consistentes mesmo após session.close()

## 🗄️ Estrutura de Dados

### Diagrama ER (Conceitual)

```
                    ┌──────────────┐
                    │   Usuario    │
                    │──────────────│
                    │ id (PK)      │
                    │ email        │
                    │ tipo         │
                    │ gerencia_id  │
                    └──────────────┘
                          ▲
                          │
        ┌─────────────────┼─────────────────┐
        │ (1:N)           │ (1:N)           │
        │ criado_por      │ atribuicao      │
        │                 │                 │
    ┌───┴────────┐   ┌────┴──────────┐
    │ Ouvidoria  │   │OuvidoriaTecnico
    │────────────│   │─────────────────┤
    │ id (PK)    │◄──┤ ouvidoria_id (FK)
    │ protocolo  │   │ tecnico_id (FK)
    │ status     │   │ respondido
    │ prazo      │   │ respondido_em
    │ conteudo   │   └─────────────────┘
    └────┬───────┘
         │ (1:N) possui
         │
    ┌────▼──────────────┐
    │   Reclamacao      │
    │───────────────────│
    │ id (PK)           │
    │ numero_item       │
    │ categoria_id (FK) │
    │ descricao         │
    │ local_embarque    │
    └────┬──────────────┘
         │ (N:N) via ReclamacaoAuto
         │
    ┌────▼──────────────┐
    │   AutoLinha       │
    │───────────────────│
    │ id (PK)           │
    │ numero            │
    │ permissionaria_id │
    │ tipo              │
    └───────────────────┘
```

### Entidades Principais

#### Ouvidoria (Central)
- **Propósito**: Agrupa uma ou mais reclamações do mesmo usuário sobre o mesmo tema
- **Status**: Aguardando ações → Em análise técnica → Concluído
- **Relacionamentos**:
  - 1:N com Reclamacao (detalhes da reclamação)
  - 1:N com OuvidoriaTecnico (atribuições)
  - 1:N com RespostaTecnica (análises)
  - 1:N com RespostaPermissionaria (respostas empresariais)

#### Reclamacao
- **Propósito**: Item específico dentro de uma ouvidoria
- **Detalhes**: Categoria, subcategoria, local embarque/desembarque
- **Relacionamentos**:
  - N:M com AutoLinha via ReclamacaoAuto
  - 1:N com Ouvidoria

#### AutoLinha (Serviço de Transporte)
- **Propósito**: Linha de transporte específica (ex: 3100-10 SAUDE/PRAIA GRANDE)
- **Atributos**: Número, denominação A/B, tipo, região TC
- **Relacionamentos**:
  - 1:N com Permissionaria (empresa operadora)
  - N:M com Reclamacao via ReclamacaoAuto

#### Usuario
- **Perfis**: Gestor (admin), Técnico (responde)
- **Vinculação**: Gerência e Coordenação (unidade organizacional)
- **Segurança**: Senha com hash bcrypt

#### OuvidoriaTecnico (Atribuição)
- **Propósito**: Rastreia qual técnico é responsável por qual ouvidoria
- **Rastreamento**: Data de atribuição, resposta, quem respondeu
- **Índice**: Facilita queries "ouvidorias de um técnico"

## 🔄 Fluxo de Dados

### Caso de Uso: Criar Nova Ouvidoria

```
1. Usuário preenche formulário (pages/02_Nova_Ouvidoria.py)
   ↓
2. Validação de entrada (email, campos obrigatórios)
   ↓
3. Chamada write_repo.criar_ouvidoria(...)
   ↓
4. Repository cria instâncias ORM dentro de db_session()
   ↓
5. SQLAlchemy persiste no PostgreSQL
   ↓
6. db_session() faz commit automático
   ↓
7. Repository retorna ID da ouvidoria criada
   ↓
8. UI redireciona para detalhe (st.rerun())
   ↓
9. pages/03_Detalhe_Ouvidoria.py carrega dados via ouvidoria_repo.get_detalhe(id)
   ↓
10. Repository converte ORM → TypedDict e retorna
```

### Caso de Uso: Responder Ouvidoria (Técnico)

```
1. Técnico acessa pages/05_Responder.py
   ↓
2. Carrega ouvidorias atribuídas via ouvidoria_repo.listar_atribuidas_tecnico()
   ↓
3. Seleciona ouvidoria e entra formulário de resposta
   ↓
4. Preenche análise técnica, categorização, pontuação
   ↓
5. Submit → ouvidoria_write_repo.criar_resposta_tecnica(...)
   ↓
6. Repository cria RespostaTecnica + atualiza OuvidoriaTecnico.respondido=true
   ↓
7. db_session() faz commit automático
   ↓
8. Opcional: Se responder TODAS as reclamações → marca Ouvidoria.status = CONCLUÍDO
```

## 🔐 Autenticação e Autorização

### Fluxo de Autenticação

```python
# 1. Login (app.py)
usuario = auth.autenticar(email, senha)
st.session_state["usuario"] = usuario

# 2. Verificação em tempo de acesso
@require_auth()  # Para qualquer página
@require_gestor()  # Apenas gestores
def pagina_admin():
    pass
```

**Armazenamento de Senha:**
- Hash bcrypt no banco (irreversível)
- Never store plain text
- Verify on login: `bcrypt.checkpw(entrada, hash_armazenado)`

**Sessão:**
- Streamlit `st.session_state` persiste na memória do cliente
- Logout: remove entrada da session_state
- Rerun automático redireciona para login

## 📊 Dashboards

### Dashboard Produtividade
- Métrica: Ouvidorias por técnico
- Métrica: Taxa de conclusão
- Métrica: Tempo médio para resposta

**Query Pattern:**
```python
# repositories/dashboard/produtividade_repo.py
def metricas_por_tecnico() -> list[MetricaTecnicoDict]:
    # Agregação de OuvidoriaTecnico.respondido_em, count(*)
```

### Dashboard Qualidade
- Métrica: Distribuição por categoria
- Métrica: Análise por permissionária
- Métrica: Pontuação média

**Query Pattern:**
```python
# repositories/dashboard/qualidade_repo.py
def metrica_qualidade() -> list[QualidadeDict]:
    # Join com Reclamacao, Categoria, Permissionaria
    # Group by e agregação de pontuação
```

## 🚀 Performance

### Índices no Banco

Consulte `migrations/` para índices definidos em:
- `ouvidorias.protocolo` (unique, busca rápida)
- `ouvidorias.status` (filtros frequentes)
- `ouvidorias_tecnicos.tecnico_id` (queries por técnico)
- `reclamacoes.categoria_id` (agrupamentos)

### Lazy Loading vs Eager Loading

**Lazy Loading (default):**
```python
ouvidoria = session.query(Ouvidoria).first()
print(ouvidoria.reclamacoes)  # ⚠️ N+1 query aqui!
```

**Eager Loading (bom):**
```python
ouvidoria = session.query(Ouvidoria).options(
    joinedload(Ouvidoria.reclamacoes)
).first()
print(ouvidoria.reclamacoes)  # ✅ Já carregado
```

### Caching (quando aplicável)

Streamlit cache:
```python
@st.cache_data
def listar_categorias():
    return catalog_repo.listar_categorias()
```

**Invalidação:** Cache é invalidado quando mudanças são feitas via write repos.

## 🔄 Migrations (Alembic)

### Estrutura

```
migrations/
├── env.py              # Configuração do Alembic
├── script.py.mako      # Template para novas migrations
└── versions/           # Migrations históricas
    ├── 0001_initial.py
    ├── 0002_add_prazo_permissionaria.py
    └── ...
```

### Workflow

```bash
# 1. Fazer mudança no models/
# 2. Gerar migration auto
alembic revision --autogenerate -m "add prazo_permissionaria"

# 3. Revisar migrations/versions/xxxxx_add_prazo_permissionaria.py
# 4. Aplicar
alembic upgrade head

# 5. Commitar: migration file + models/
```

## 🛡️ Tratamento de Erros

### Padrão Recomendado

```python
# pages/01_Ouvidorias.py
try:
    ouvidorias = ouvidoria_repo.listar(...)
except ValueError as e:
    st.error(f"Filtro inválido: {e}")
except Exception as e:
    st.error(f"Erro ao carregar: {e}")
    logger.error(f"DB error", exc_info=True)
```

### Erros Esperados (Validação)
- ValueError: entrada inválida
- KeyError: recurso não encontrado

### Erros Não Esperados (System)
- SQLAlchemy exceptions: problemas de DB
- IOError: problemas de arquivo

**Sempre:**
- Log do erro completo (`exc_info=True`)
- Mensagem amigável ao usuário
- Nunca exponha stack trace ao usuário

## 📝 Logging

Configure em `.env`:

```env
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

**Níveis:**
- DEBUG: Queries SQL, valores de variáveis
- INFO: Ações principais (login, criação)
- WARNING: Comportamentos inesperados
- ERROR: Erros que precisam atenção
- CRITICAL: Sistema indisponível

## 🔗 Extensibilidade

### Adicionar Nova Página

```
1. Criar pages/XX_NovaFeature.py
2. Implementar com @require_auth() ou @require_gestor()
3. Usar repositórios existing (não duplicar lógica)
4. Adicionar ao menu lateral em app.py (Streamlit carrega automaticamente)
```

### Adicionar Nova Entidade

```
1. Criar models/nova_entidade.py (SQLAlchemy model)
2. Criar migration alembic
3. Criar repositories/nova_entidade_repo.py e *_write_repo.py
4. Adicionar TypedDicts em repositories/types.py
5. Usar em pages/
```

### Modificar Schema

```
1. Editar models/*.py
2. Gerar migration: alembic revision --autogenerate -m "descricao"
3. Revisar migration em migrations/versions/
4. Aplicar: alembic upgrade head
5. Commitar migration + models/
```

## 🔗 Referências

- [SQLAlchemy ORM](https://docs.sqlalchemy.org/en/20/)
- [Alembic Migrations](https://alembic.sqlalchemy.org/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
