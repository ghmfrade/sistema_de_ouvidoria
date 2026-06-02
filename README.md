# SOUVI — Sistema de Ouvidorias da SUCOL

> **SOUVI** é uma sigla-trocadilho:
> **SOU**VI = **SOU** + **OUVI** → _sistema de ouvidorias_ que ao mesmo tempo remete ao verbo _ouvir_ ("sou ouvido").

Sistema web de gerenciamento de ouvidorias desenvolvido para a ARTESP (Agência de Transporte Estadual de São Paulo), permitindo o acompanhamento integrado de reclamações e solicitações de usuários sobre serviços de transporte.

## Visão Geral

O SOUVI centraliza e gerencia o fluxo de ouvidorias (reclamações, sugestões e elogios) relacionadas aos serviços de transporte sob regulação da ARTESP. O sistema integra:

- **Gestão de Ouvidorias**: Registro, acompanhamento e conclusão de ouvidorias
- **Atribuição de Responsáveis**: Distribuição de tarefas entre técnicos por gerência/coordenação
- **Respostas Técnicas**: Documentação de análises e respostas às reclamações
- **Respostas de Permissionárias**: Gerenciamento de respostas das empresas de transporte
- **Análise de Dados**: Dashboard de produtividade (Streamlit) e qualidade (Plotly Dash)
- **Relatórios Estáticos**: Geração pontual de relatórios HTML via `gerador_de_relatorios.py` (uso secundário — o Dashboard de Qualidade cobre os mesmos dados de forma interativa)

## Arquitetura

O projeto é um monorepo com três serviços independentes e código auxiliar agrupado por dono:

```
sistema_de_ouvidoria/
├── frontend/                   # Streamlit (UI principal)
│   ├── app.py                  # Entry point
│   ├── auth.py                 # Sessão + login via API
│   ├── pages/                  # Páginas numeradas 01..09
│   ├── components/             # Componentes Streamlit reutilizáveis
│   └── .streamlit/config.toml
│
├── api/                        # FastAPI + camada de dados completa
│   ├── main.py                 # FastAPI app + registro de routers
│   ├── routers/                # Endpoints REST por domínio
│   ├── schemas/                # Pydantic (request/response)
│   ├── services/               # Lógica de negócio
│   ├── client/                 # HTTP client SDK (consumido pelo frontend)
│   ├── models/                 # SQLAlchemy ORM
│   ├── database/               # Conexão + scripts seed
│   ├── repositories/           # Read/Write repos (TypedDicts)
│   ├── migrations/             # Alembic versionamento de schema
│   ├── utils/                  # Utilitários server-side (html_resumo, types)
│   └── alembic.ini
│
├── qualidade_dash/             # Plotly Dash — Dashboard de Qualidade (principal)
│   ├── app.py
│   ├── api_client.py           # Consome a API via HTTP
│   ├── layout.py, callbacks.py, components.py
│   └── run.py                  # Entry point (`python -m qualidade_dash.run`)
│
├── utils/                      # Compartilhado entre frontend e api
│   └── formatters.py
│
├── scripts/                    # Scripts auxiliares server-side (ver scripts/README.md)
│
├── tests/                      # Suíte pytest
├── docs/                       # Documentação adicional
├── pasta_seed/                 # Planilhas de entrada para seeds
├── normalizacao_dados/         # Planilhas usadas pelos scripts de enriquecimento
├── relatorios/                 # HTMLs gerados por gerador_de_relatorios.py
└── gerador_de_relatorios.py    # Launcher de scripts/gerar_reclamacoes.py
```

**Comunicação entre serviços:** o frontend Streamlit e o `qualidade_dash` conversam com o backend **exclusivamente via HTTP** (FastAPI). Não há acesso direto ao banco a partir do frontend.

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
   POSTGRES_DB=souvi
   POSTGRES_SCHEMA=ouvidoria

   JWT_SECRET_KEY=chave_para_uso_da_api
   ```

5. **Inicialize o banco de dados**

   Todos os comandos abaixo rodam a partir da raiz do projeto.

   **Aplicar migrations** (Alembic mora dentro de `api/`):

   ```bash
   cd api
   py -m alembic upgrade head
   cd ..
   ```

   **Popular o banco com dados base** (na ordem):

   ```bash
   py api/database/seed_all.py
   ```

   Ou seeds individuais:

   ```bash
   py api/database/seed_municipios.py
   py api/database/seed_empresas.py
   py api/database/seed_autos_intermunicipal.py
   py api/database/seed_autos_metropolitano.py
   py api/database/seed_categorias.py
   py api/database/seed_usuarios.py
   ```

   **(Opcional) Importar dados históricos** (planilha em `pasta_seed/`):

   ```bash
   py api/database/seed_dados_antigos.py
   ```

6. **Inicie o backend FastAPI** (precisa estar de pé para o frontend e o Dash funcionarem)

   ```bash
   uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
   ```

7. **Inicie a aplicação Streamlit** (em outro terminal)

   ```bash
   streamlit run frontend/app.py
   ```

8. **(Opcional) Inicie o Dashboard de Qualidade** (em outro terminal)

   ```bash
   py -m qualidade_dash.run
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
- Usuário padrão criado pelo seed: `admin@artesp.sp.gov.br` / `admin123`

> **Importante:** Após executar `py api/database/seed_all.py` (ou ao menos `seed_usuarios.py`), acesse o painel **Admin → Usuários** e troque a senha do administrador antes de disponibilizar o sistema.

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

Redireciona para o app Plotly Dash (`py -m qualidade_dash.run`, porta 8050). Interface single-screen: 9 cards-botão no topo, cada um exibe seu gráfico ao ser clicado.

**Filtros globais** (barra superior):

| Filtro | Observação |
|---|---|
| Tipo de Serviço | Regular Metropolitano, Regular Intermunicipal, Fretamento Intermunicipal, Fretamento Metropolitano |
| Ano | Anos disponíveis no banco |
| Meses | Seleção múltipla; padrão = todos |
| Região | Só aparece quando há tipo Regular selecionado |
| Permissionária | Só aparece quando há tipo Regular; máximo de 10 selecionadas |
| Assunto | Baseado nos assuntos presentes nos dados filtrados |

**Cards e gráficos:**

| # | Card (KPI) | Gráfico exibido |
|---|---|---|
| 1 | Total de Reclamações | Evolução mensal (linha temporal) |
| 2 | Assunto Mais Reclamado | Pizza de distribuição por assunto |
| 3 | Embarque / Desembarque Mais Crítico | Ranking de locais (paginado); alternável entre embarque e desembarque |
| 4 | Empresa Mais Reclamada | Ranking de permissionárias por pontuação de reclamações (somente Regular) |
| 5 | Empresa Mais Vulnerável | Ranking de permissionárias por incidência de transporte irregular (somente Regular) |
| 6 | Auto Mais Reclamado | Ranking de autos de linha por pontuação (paginado, somente Regular) |
| 7 | Auto Mais Vulnerável | Ranking de autos por vulnerabilidade ao irregular (paginado, somente Regular) |
| 8 | Mapa de Calor por Empresa | Heatmap assunto × empresa, com destaque colorido para empresas selecionadas (paginado, somente Regular) |
| 9 | Mapa de Calor por Autos | Heatmap assunto × auto de linha (paginado, somente Regular) |

Cards 4–9 ficam desabilitados quando o filtro de tipo de serviço não inclui nenhum serviço Regular.

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

O diretório `api/` é a "API + camada de dados" do sistema. Expõe endpoints REST consumidos por todos os clientes: Streamlit (`api/client/`), Plotly Dash (`qualidade_dash/api_client.py`) e potencialmente integrações externas. Mantém também os models SQLAlchemy, repositórios e migrations.

```
api/
├── main.py          # FastAPI app + registro de routers
├── deps.py          # Dependências (sessão DB, auth)
├── routers/         # Endpoints por domínio
├── schemas/         # Pydantic schemas (request/response)
├── services/        # Lógica de negócio
├── client/          # Cliente HTTP para uso interno (importado pelo frontend)
├── models/          # SQLAlchemy ORM
├── database/        # Conexão + seeds
├── repositories/    # Read/write repos
├── migrations/      # Alembic
└── alembic.ini
```

### Conventions de Código

Consulte [docs/coding_rules.md](docs/coding_rules.md) para detalhes sobre:

- Nomenclatura de funções e variáveis
- Organização de imports
- Padrões de tratamento de erros
- Boas práticas com SQLAlchemy
- Padrões Streamlit

### Migrations

Os comandos Alembic rodam de dentro de `api/` (onde mora `alembic.ini` e `migrations/`):

```bash
cd api

# Criar nova migration
py -m alembic revision --autogenerate -m "descrição da mudança"

# Aplicar todas as migrations pendentes
py -m alembic upgrade head

# Voltar uma versão
py -m alembic downgrade -1

# Estado atual
py -m alembic current
```

### Testes

```bash
# Suíte completa (ignora integração que precisa de API rodando)
py -m pytest --ignore=tests/integration

# Suíte de integração (precisa do FastAPI no ar)
py -m pytest tests/integration
```

## Relatórios e scripts auxiliares

Há uma família de scripts standalone em `scripts/` para gerar relatórios, enriquecer planilhas com dados do banco e cruzar municípios. Consulte [scripts/README.md](scripts/README.md) para o catálogo completo de **quais arquivos cada script lê e onde grava as saídas**.

> **Nota:** O snapshot HTML gerado por `gerador_de_relatorios.py` é uma funcionalidade secundária. O **Dashboard de Qualidade** (`qualidade_dash/`, em `py -m qualidade_dash.run`) oferece os mesmos dados de forma interativa e em tempo real — prefira-o para análise cotidiana.

**Gerador de relatórios HTML** (via launcher na raiz):

```bash
py gerador_de_relatorios.py
```

Saída em `relatorios/` (um arquivo por ano-base encontrado nos dados):

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
