# 📋 Sistema de Ouvidorias ARTESP

Sistema web de gerenciamento de ouvidorias desenvolvido para a ARTESP (Agência de Transporte Estadual de São Paulo), permitindo o acompanhamento integrado de reclamações e solicitações de usuários sobre serviços de transporte.

## 🎯 Visão Geral

O Sistema de Ouvidorias ARTESP foi desenvolvido para centralizar e gerenciar o fluxo de ouvidorias (reclamações, sugestões e elogios) relacionadas aos serviços de transporte sob regulação da ARTESP. O sistema integra:

- **Gestão de Ouvidorias**: Registro, acompanhamento e conclusão de ouvidorias
- **Atribuição de Responsáveis**: Distribuição de tarefas entre técnicos por gerência/coordenação
- **Respostas Técnicas**: Documentação de análises e respostas às reclamações
- **Respostas de Permissionárias**: Gerenciamento de respostas das empresas de transporte
- **Análise de Dados**: Dashboards de produtividade e qualidade
- **Relatórios**: Geração de relatórios consolidados

## 🏗️ Arquitetura

```
sistema_de_ouvidoria/
├── app.py                      # Ponto de entrada principal (Streamlit)
├── auth.py                     # Autenticação e controle de sessão
├── models/                     # SQLAlchemy ORM models
├── database/                   # Configuração de banco de dados
├── repositories/               # Data access layer (read/write)
├── pages/                      # Páginas Streamlit numeradas
├── components/                 # Componentes Streamlit reutilizáveis
├── relatorios/                 # Geração de relatórios
├── utils/                      # Utilitários diversos
└── migrations/                 # Alembic migrations (versionamento de schema)
```

## 🚀 Quickstart

### Requisitos
- Python 3.10+
- PostgreSQL 12+
- pip ou conda

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
   ```bash
   cp .env.example .env
   # Edite .env com suas credenciais PostgreSQL
   ```

5. **Inicialize o banco de dados**
   ```bash
   # Crie o banco e execute migrations
   alembic upgrade head
   ```

6. **Inicie a aplicação**
   ```bash
   streamlit run app.py
   ```

A aplicação estará disponível em `http://localhost:8501`

## 📖 Guia de Uso

### Autenticação
- Login com e-mail e senha
- Suporte a dois tipos de usuário: **Gestor** (acesso administrativo) e **Técnico** (acesso a análises)

### Páginas Principais

#### 01 - Ouvidorias
Listagem e gerenciamento de ouvidorias com filtros por status, prazo e responsáveis. Visualize todas as ouvidorias em processamento ou concluídas.

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
Análise da qualidade de respostas e categorização:
- Distribuição por categoria
- Análise por permissionária
- Mapas de calor por região
- Pontuações de qualidade

#### 08 - Admin
Painel administrativo (restrito a gestores):
- Gerenciamento de usuários
- Configuração de catálogos (categorias, subcategorias, gerências, coordenações)
- Gestão de autos (linhas de transporte) e permissionárias

## 🏢 Estrutura de Dados

### Entidades Principais

**Ouvidoria**: Registro central que agrupa uma ou mais reclamações de um mesmo usuário sobre um mesmo tema.
- Status: Aguardando ações → Em análise técnica → Concluído
- Relacionamentos: Reclamações, Atribuições de técnicos, Respostas técnicas, Respostas de permissionárias

**Reclamação**: Item individual dentro de uma ouvidoria, vinculado a um ou mais autos (linhas de transporte).
- Inclui categoria, subcategoria e descrição detalhada
- Pode especificar local de embarque/desembarque

**Auto (Linha de Transporte)**: Linha de transporte específica sob regulação ARTESP.
- Identificado por número único
- Vinculado a permissionária e região metropolitana

**Usuário**: Usuário do sistema com dois perfis:
- Gestor: Acesso administrativo completo
- Técnico: Acesso restrito a análises e respostas

**Atribuição Técnico**: Vínculo entre Ouvidoria e Técnico, rastreando quem é responsável pela resposta.

**Resposta Técnica**: Análise e conclusão técnica sobre uma ouvidoria.

**Resposta Permissionária**: Resposta da empresa de transporte à reclamação.

## 🛠️ Desenvolvimento

### Estrutura de Repositórios

O projeto segue o padrão **Repository Pattern** com separação clara entre leitura e escrita:

- **Read Repositories** (`*_repo.py`): Consultas e carregamento de dados
  - Retornam TypedDicts (contratos de dados imutáveis)
  - Garantem que instâncias ORM não escapem da sessão do banco
  - Conversões ORM → TypedDict ocorrem dentro de `with db_session()`

- **Write Repositories** (`*_write_repo.py`): Inserção, atualização e exclusão
  - Operações de escrita no banco de dados
  - Gerenciamento de transações
  - Validação de integridade referencial

### Convenções de Código

Consulte [coding_rules.md](coding_rules.md) para detalhes completos sobre:
- Nomenclatura de funções e variáveis
- Organização de imports
- Padrões de tratamento de erros
- Boas práticas com SQLAlchemy
- Padrões Streamlit

### Migrations

Utilizamos **Alembic** para versionamento de schema do banco de dados.

```bash
# Criar nova migration
alembic revision --autogenerate -m "descrição da mudança"

# Aplicar todas as migrations pendentes
alembic upgrade head

# Voltar uma versão
alembic downgrade -1
```

### Testes

Para executar testes (quando configurados):
```bash
pytest
```

## 📊 Relatórios

O sistema gera relatórios consolidados em Excel:

- **Relatório Anual**: Consolidação de ouvidorias do ano
- **Relatório por Período**: Agrupamento por data, categoria, permissionária
- **Relatório de Qualidade**: Análise de pontuações e métricas

## 🔐 Segurança

- Senhas armazenadas com hash bcrypt
- Controle de acesso baseado em perfil (Gestor/Técnico)
- Validação de entrada em formulários
- Proteção contra SQL injection via SQLAlchemy ORM

## 📝 Logging

Os logs da aplicação são armazenados em `logs/` (quando configurado). Configure o nível de log via variáveis de ambiente:

```bash
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## 🤝 Contribuindo

1. Crie uma branch para sua feature (`git checkout -b feature/sua-feature`)
2. Commit suas mudanças (`git commit -m 'Adiciona sua feature'`)
3. Push para a branch (`git push origin feature/sua-feature`)
4. Abra um Pull Request

Consulte [coding_rules.md](coding_rules.md) para orientações sobre estilo de código e padrões do projeto.

## 📞 Suporte

Para dúvidas ou problemas, entre em contato com a equipe de desenvolvimento ou abra uma issue no repositório.

## 📄 Licença

Este projeto é propriedade da ARTESP. Todos os direitos reservados.

## 📚 Documentação Adicional

- [Architecture](architecture.md) - Detalhes da arquitetura do sistema
- [Coding Rules](coding_rules.md) - Padrões e convenções de código
- [Alembic Docs](https://alembic.sqlalchemy.org/)
- [Streamlit Docs](https://docs.streamlit.io/)
- [SQLAlchemy Docs](https://docs.sqlalchemy.org/)
