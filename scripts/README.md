# scripts/

Scripts standalone server-side: enriquecimento de dados, cruzamento com banco e geração de relatórios. Todos importam de `api.*` (models, repositories, database) e por isso precisam do projeto na raiz do `sys.path` — cada script já faz esse ajuste no topo.

Rode sempre **a partir da raiz do projeto** com o `py` launcher (`py scripts/<arquivo>.py`) ou via `python -m scripts.<arquivo>`. Os dados de entrada moram em `pasta_seed/` (planilhas oficiais) e `normalizacao_dados/` (planilhas de trabalho dos enriquecimentos).

---

## Catálogo

### `enrich_cnpj.py` — Enriquece base antiga com CNPJ das permissionárias

Lê uma planilha bruta de ouvidorias antigas, casa o campo `EMPRESA` com a tabela `permissionarias` do banco (várias estratégias de normalização + overrides manuais) e preenche colunas com nome/fantasia/CNPJ.

| | Caminho |
|---|---|
| **Lê** | `pasta_seed/Novo Modelo Base Ouvidoria 2.xlsx` (header=1) |
| **Lê** | tabela `permissionarias` do banco (via `api.database.connection`) |
| **Grava** | `normalizacao_dados/NOVO_MODELO_enriquecido.csv` |
| **Grava** | `normalizacao_dados/nao_encontrados.csv` (empresas sem match) |

Como rodar:

```bash
py scripts/enrich_cnpj.py
```

---

### `enrich_cidades.py` — Normaliza ORIGEM e DESTINO contra `municipios` (IBGE)

Lê o CSV gerado pelo `enrich_cnpj.py`, normaliza os campos `ORIGEM` e `DESTINO` contra a tabela `municipios` e adiciona quatro colunas: `ORIGEM_IBGE`, `ORIGEM_cod_IBGE`, `DESTINO_IBGE`, `DESTINO_cod_IBGE`.

| | Caminho |
|---|---|
| **Lê** | `normalizacao_dados/NOVO_MODELO_enriquecido.csv` (saída do `enrich_cnpj`) |
| **Lê** | tabela `municipios` do banco |
| **Grava** | `normalizacao_dados/dados_antigos_tratado_empresa_e_cidades.csv` |
| **Grava** | `pasta_seed/dados_antigos_tratado_empresa_e_cidades.csv` (cópia para uso do seed `seed_dados_antigos.py`) |
| **Grava** | `normalizacao_dados/mun_dados_antigos_not_find.csv` (municípios sem match) |

Como rodar (depois do `enrich_cnpj.py`):

```bash
py scripts/enrich_cidades.py
```

**Pipeline completo de importação de dados antigos:**

```bash
py scripts/enrich_cnpj.py        # produz NOVO_MODELO_enriquecido.csv
py scripts/enrich_cidades.py     # produz dados_antigos_tratado_empresa_e_cidades.csv (em duas pastas)
py api/database/seed_dados_antigos.py   # importa o CSV no banco
```

---

### `cruzar_municipios.py` — Cruza paradas dos autos com municípios IBGE

Lê paradas dos autos (metropolitano e intermunicipal) do banco e cruza com a tabela `municipios` para identificar quais paradas batem em qual município (três estratégias: exato, normalizado, sem espaço).

| | Caminho |
|---|---|
| **Lê** | tabelas `autos_linha`, `paradas_auto_linha`, `municipios` do banco |
| **Grava** | `cruzamento_municipios.xlsx` (**na raiz do projeto**) — duas abas: Metropolitano e Intermunicipal |

Como rodar:

```bash
py scripts/cruzar_municipios.py
```

---

### `gerar_reclamacoes.py` — Gera relatórios HTML anuais de reclamações

Produz dois HTMLs com gráficos Plotly: KPIs por sistema, evolução mensal, top 15 autos, top 15 pontos de embarque, análise por empresa, heatmap de assuntos.

| | Caminho |
|---|---|
| **Lê** | tabelas via `api.repositories.relatorios.reclamacoes_repo` |
| **Grava** | `relatorios/relatorio_reclamacoes_2025.html` |
| **Grava** | `relatorios/relatorio_reclamacoes_2026.html` |

Como rodar (qualquer das duas formas):

```bash
py gerador_de_relatorios.py            # launcher na raiz (recomendado)
py -m scripts.gerar_reclamacoes        # direto
```

---

### `gerar_relatorio_reclamacoes_autos.py` — Relatório Markdown de pontuação por auto

Recebe um ou mais números de auto via linha de comando e gera um `.md` com a pontuação total de cada auto por subcategoria em 2025.

| | Caminho |
|---|---|
| **Lê** | tabelas `autos_linha`, `ouvidorias`, `reclamacoes`, `reclamacoes_auto`, `subcategorias` |
| **Grava** | `scripts/reclamacoes_por_autos_N.md` (onde `N` = quantidade de autos passados) |

Como rodar:

```bash
py scripts/gerar_relatorio_reclamacoes_autos.py 9207A 9208A
# ou via .bat no Windows:
relatorio_por_autos.bat 9207A
```

---

## Onde os dados moram

- **`pasta_seed/`** — Planilhas oficiais (entrada dos seeds e do `enrich_cnpj.py`). Versionadas/atualizadas periodicamente.
- **`normalizacao_dados/`** — Planilhas e CSVs de trabalho dos scripts de enriquecimento. Atualizadas quando os scripts rodam.
- **`relatorios/`** — HTMLs gerados pelo `gerar_reclamacoes.py`. Saída pública.
- **Raiz do projeto** — `cruzamento_municipios.xlsx` (saída do `cruzar_municipios.py`) e `seed_lancados.xlsx` / `seed_nao_lancados.xlsx` (saídas do `seed_dados_antigos.py`).
