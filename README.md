# SIGO-SUCOL — Sistema Integrado de Gestão de Ouvidorias da SUCOL

Sistema web de gerenciamento de ouvidorias desenvolvido para a ARTESP (Agência de Transporte Estadual de São Paulo), permitindo o acompanhamento integrado de reclamações e solicitações de usuários sobre serviços de transporte.

## Visão Geral

O SIGO-SUCOL centraliza e gerencia o fluxo de ouvidorias (reclamações, sugestões e elogios) relacionadas aos serviços de transporte sob regulação da ARTESP. O sistema integra:

- **Gestão de Ouvidorias**: Registro, acompanhamento e conclusão de ouvidorias
- **Atribuição de Responsáveis**: Distribuição de tarefas entre técnicos por gerência/coordenação
- **Respostas Técnicas**: Documentação de análises e respostas às reclamações
- **Respostas de Permissionárias**: Gerenciamento de respostas das empresas de transporte
- **Análise de Dados**: Dashboard de produtividade (Streamlit) e qualidade (Plotly Dash)
- **Relatórios**: Geração de relatórios consolidados em HTML

## Arquitetura

```
sistema_de_ouvidoria/
├── app.py                      # Ponto de entrada principal (Streamlit)
├── auth.py                     # Autenticação e controle de sessão
├── run_dash.py                 # Ponto de entrada do Dashboard de Qualidade (Dash)
├── gerador_de_relatorios.py    # Geração de relatórios HTML
├── alembic.ini                 # Configuração do Alembic
├── models/                     # SQLAlchemy ORM models
├── database/                   # Configuração do banco de dados
├── repositories/               # Data access layer (read/write)
├── api/                        # Backend FastAPI (rotas REST)
├── pages/                      # Páginas Streamlit numeradas
├── components/                 # Componentes Streamlit reutilizáveis
├── qualidade_dash/             # App Plotly Dash (Dashboard de Qualidade)
├── relatorios/                 # Relatórios HTML gerados
├── migrations/                 # Alembic migrations (versionamento de schema)
├── tasks/                      # Tarefas assíncronas/agendadas
├── tests/                      # Testes automatizados
├── tools/                      # Scripts utilitários pontuais
├── docs/                       # Documentação adicional
└── utils/                      # Utilitários diversos
```

## Quickstart

### Requisitos

- Python 3.11+
- PostgreSQL 12+

### Instalação

1. **Clone o repositório**

   ```bash
   git clone <repository-url>
   cd sistema_de_ouvidoria
   ```

2. **Crie um ambiente virtual**

   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # Unix
   source .venv/bin/activate
   ```

3. **Instale as dependências**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure variáveis de ambiente**

   Crie um arquivo `.env` na raiz com as seguintes variáveis:

   ```env
   POSTGRES_USER=seu_usuario
   POSTGRES_PASSWORD=sua_senha
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   POSTGRES_DB=sistema_de_ouvidoria
   POSTGRES_SCHEMA=ouvidoria

   JWT_SECRET_KEY=chave_para_uso_da_api
   ```

5. **Inicialize o banco de dados**

   ```bash
   alembic upgrade head
   python database/seed.py
   ```

6. **Inicie a aplicação Streamlit**

   ```bash
   streamlit run app.py
   ```

7. **(Opcional) Inicie o Dashboard de Qualidade**

   ```bash
   python run_dash.py
   ```

8. **(Opcional) Inicie o backend FastAPI**

   **Windows:**
   ```powershell
   .venv\Scripts\uvicorn.exe api.main:app --reload --host 0.0.0.0 --port 8000
   ```

   **Linux/macOS:**
   ```bash
   .venv/bin/uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
   ```

A aplicação Streamlit estará disponível em `http://localhost:8501`.
O Dashboard de Qualidade estará disponível em `http://localhost:8050`.
A API FastAPI estará disponível em:
- **Localmente**: `http://localhost:8000` ou `http://127.0.0.1:8000`
- **De outro PC na rede**: `http://<seu-ip>:8000` (ex: `http://10.23.42.237:8000`)
- **Documentação Swagger**: `http://localhost:8000/docs`

## Guia de Uso

### Autenticação

- Login com e-mail e senha
- Dois tipos de usuário: **Gestor** (acesso administrativo) e **Técnico** (acesso a análises)
- Usuário padrão: `admin@artesp.sp.gov.br` / `admin123`

### Páginas Principais

#### 01 - Ouvidorias

Listagem e gerenciamento de ouvidorias com filtros por status, prazo e responsáveis. Gestores visualizam todas; técnicos visualizam apenas as atribuídas a eles.

#### 02 - Nova Ouvidoria

Formulário para registro de novas ouvidorias. Inclui vinculação de reclamações a autos (linhas de transporte), categorização e atribuição inicial de responsáveis.

#### 03 - Detalhe Ouvidoria

Visualização completa de uma ouvidoria com:

- Reclamações vinculadas
- Atribuições de técnicos
- Respostas técnicas registradas
- Respostas da permissionária
- Anexos (documentos suportivos)

#### 04 - Resposta Permissionária

Formulário para registrar respostas das empresas de transporte às reclamações.

#### 05 - Responder

Página de resposta técnica para técnicos registrarem suas análises e conclusões sobre as reclamações.

#### 06 - Dashboard Produtividade

Métricas de produtividade da equipe técnica:

- Quantidade de ouvidorias por técnico
- Taxa de conclusão
- Tempo médio de resposta

#### 07 - Dashboard Qualidade

Redireciona para o app Plotly Dash (`run_dash.py`) com análise avançada:

- Distribuição por categoria e subcategoria
- Análise por permissionária
- Mapas de calor por região
- Pontuações de qualidade

#### 08 - Admin

Painel administrativo (restrito a gestores):

- Gerenciamento de usuários
- Configuração de catálogos (categorias, subcategorias, gerências, coordenações)
- Gestão de autos (linhas de transporte) e permissionárias

## Estrutura de Dados

### Entidades Principais

**Ouvidoria**: Registro central que agrupa uma ou mais reclamações de um mesmo usuário sobre um mesmo tema.

- Status: Aguardando ações → Em análise técnica → Concluído
- Relacionamentos: Reclamações, Atribuições de técnicos, Respostas técnicas, Respostas de permissionárias

**Reclamação**: Item individual dentro de uma ouvidoria, vinculado a um ou mais autos (linhas de transporte).

- Inclui categoria, subcategoria e descrição detalhada
- Pode especificar local de embarque/desembarque

**Auto (Linha de Transporte)**: Linha de transporte específica sob regulação ARTESP.

- Identificado por número único (ex.: `0001-A`)
- Vinculado a permissionária e municípios atendidos

**Usuário**: Usuário do sistema com dois perfis:

- Gestor: Acesso administrativo completo
- Técnico: Acesso restrito a análises e respostas

**Resposta Técnica**: Análise e conclusão técnica sobre uma ouvidoria.

**Resposta Permissionária**: Resposta da empresa de transporte à reclamação.

## Desenvolvimento

### Estrutura de Repositórios

O projeto segue o padrão **Repository Pattern** com separação entre leitura e escrita:

- **Read Repositories** (`*_repo.py`): Consultas e carregamento de dados
  - Retornam TypedDicts (contratos de dados imutáveis)
  - Garantem que instâncias ORM não escapem da sessão do banco
  - Conversões ORM → TypedDict ocorrem dentro de `with db_session()`

- **Write Repositories** (`*_write_repo.py`): Inserção, atualização e exclusão
  - Gerenciamento de transações e validação de integridade referencial

### Backend FastAPI

O diretório `api/` expõe endpoints REST consumidos por todos os clientes: Streamlit (`api/client/`), Plotly Dash (`qualidade_dash/api_client.py`) e potencialmente integrações externas:

```
api/
├── main.py          # FastAPI app + registro de routers
├── deps.py          # Dependências (sessão DB, auth)
├── routers/         # Endpoints por domínio
├── schemas/         # Pydantic schemas (request/response)
├── services/        # Lógica de negócio
└── client/          # Cliente HTTP para uso interno
```

### Conventions de Código

Consulte [docs/coding_rules.md](docs/coding_rules.md) para detalhes sobre:

- Nomenclatura de funções e variáveis
- Organização de imports
- Padrões de tratamento de erros
- Boas práticas com SQLAlchemy
- Padrões Streamlit

### Migrations

```bash
# Criar nova migration
alembic revision --autogenerate -m "descrição da mudança"

# Aplicar todas as migrations pendentes
alembic upgrade head

# Voltar uma versão
alembic downgrade -1
```

## Relatórios

O sistema gera relatórios consolidados em **HTML com gráficos interativos** (Plotly).

```bash
python gerador_de_relatorios.py
```

Relatórios gerados em `relatorios/`:

- `relatorio_reclamacoes_2025.html` — Reclamações de 2025
- `relatorio_reclamacoes_2026.html` — Reclamações de 2026

**Conteúdo dos relatórios:**

- KPIs por sistema (Regular Metropolitano, Regular Intermunicipal, Fretamento)
- Evolução mensal de reclamações
- Top 15 autos com mais reclamações
- Top 15 pontos de embarque
- Análise por empresa (pontuação e volume)
- Heatmap de assuntos por empresa
- Distribuição por tipo de serviço

## Segurança

- Senhas armazenadas com hash bcrypt
- Controle de acesso baseado em perfil (Gestor/Técnico)
- Proteção contra SQL injection via SQLAlchemy ORM

## Contribuindo

1. Crie uma branch para sua feature (`git checkout -b feature/sua-feature`)
2. Commit suas mudanças (`git commit -m 'Adiciona sua feature'`)
3. Push para a branch (`git push origin feature/sua-feature`)
4. Abra um Pull Request

Consulte [docs/coding_rules.md](docs/coding_rules.md) para orientações sobre estilo de código e padrões do projeto.

## Documentação Adicional

- [Architecture](docs/architecture.md) — Detalhes da arquitetura do sistema
- [Coding Rules](docs/coding_rules.md) — Padrões e convenções de código
- [Alembic Docs](https://alembic.sqlalchemy.org/)
- [Streamlit Docs](https://docs.streamlit.io/)
- [SQLAlchemy Docs](https://docs.sqlalchemy.org/)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Plotly Dash Docs](https://dash.plotly.com/)

## Licença

Este projeto é propriedade da ARTESP. Todos os direitos reservados.
