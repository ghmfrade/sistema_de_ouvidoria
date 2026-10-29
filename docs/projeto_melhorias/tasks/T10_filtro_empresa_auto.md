# T10 — Lista de ouvidorias: filtros por Empresa e por Auto de linha

## Objetivo
Na página **Ouvidorias** (`frontend/pages/01_Ouvidorias.py`), permitir filtrar a lista por **empresa**
(permissionária) e por **auto de linha**. Os dois filtros ficam **numa linha nova, logo abaixo** de
**Categoria** e **Subcategoria**, e dependem do filtro **Tipo de Serviço** (topo da página).

## Decisões
- **Empresa** = `Permissionaria`; **Auto de linha** = `AutoLinha`. A ouvidoria entra no filtro quando alguma
  de suas reclamações tem um auto vinculado (`reclamacao_autos`) que atende ao filtro. Ouvidoria sem auto
  vinculado não aparece quando um desses filtros está ativo. `Reclamacao.empresa_fretamento` (texto livre)
  **não** entra.
- **Dependência do Tipo de Serviço:**
  - Tipo = "Regular – Metropolitano" ou "Regular – Intermunicipal" → Empresa lista só as empresas com autos
    ativos daquele tipo; Auto lista só autos daquele tipo.
  - "Todos os Tipos" → Empresa lista todas as empresas dos dois tipos regulares (sem repetição, ordem
    alfabética pelo rótulo); Auto idem (autos dos dois tipos regulares).
  - Tipo = "Fretamento Metropolitano" ou "Fretamento Intermunicipal" → os dois selectboxes **não aparecem**
    e os filtros de empresa/auto ficam desligados (`None`), mesmo que algo estivesse selecionado antes.
- **Dependência da Empresa:** empresa escolhida → Auto lista só os autos dessa empresa (respeitando o tipo).
  "Todas as empresas" → Auto lista todos os autos do(s) tipo(s) acima.
- Opção "nenhum filtro": `"Todas as empresas"` e `"Todos os autos"` (primeira opção, padrão).
- Se a opção escolhida deixar de existir (o usuário trocou o tipo ou a empresa), o filtro volta para
  "Todas…" — não pode ficar filtrando por algo que não está na lista.
- Escolher auto sem escolher empresa é permitido (filtra só pelo auto).
- **Rótulos:** empresa = `nome_fantasia or nome` (como em `frontend/components/reclamacoes/vincular_autos.py`);
  auto = `fmt_auto(a)` de `utils/formatters.py`. Em "Todos os Tipos", prefixar o auto com o tipo abreviado
  (`[Metro]` / `[Inter]`), pois o mesmo número pode existir nos dois tipos.
- Filtros por **id** (`permissionaria_id`, `auto_id`), não por nome.
- Só ativos nas opções (é o que os endpoints atuais já devolvem).

## Contexto atual
- Filtro de tipo: `_col_tipo` no topo, `_filtro_tipo` (string de `TIPO_SERVICO` ou `None`).
- Linha `col_cat, col_sub, col_checks, col_de, col_ate, col_nova = st.columns([1.8, 1.8, 1.1, 1.3, 1.3, 1.6])`.
- `listar_ouvidorias(...)` (`api/client/ouvidoria_client.py`) → `GET /ouvidorias` (`api/routers/ouvidorias.py`)
  → `api/repositories/ouvidoria_repo.py::listar_ouvidorias`, que já filtra por `filtro_subcategoria_id` e
  `filtro_tipo_servico` com `Ouvidoria.reclamacoes.any(...)`.
- Opções já disponíveis no cliente (`api/client/autos_client.py`, com cache de 300 s):
  `carregar_permissionarias(tipo_servico)` e `carregar_todos_autos(tipo_servico, perm_id=...)`.
  Ambos exigem um tipo; para "Todos os Tipos" chame os dois tipos regulares e junte (sem endpoint novo).
- Relação: `Reclamacao.autos_vinculados` → `ReclamacaoAuto.auto` → `AutoLinha.permissionaria_id`
  (`api/models/associations.py`, `api/models/auto_linha.py`).
- `filtros_hash` controla a volta para a página 1 da paginação.

## Arquivos envolvidos
- `api/repositories/ouvidoria_repo.py`
- `api/routers/ouvidorias.py`
- `api/client/ouvidoria_client.py`
- `frontend/pages/01_Ouvidorias.py`
- `tests/test_t10_filtro_empresa_auto.py` (novo)

## O que fazer
1. **Repo:** em `listar_ouvidorias`, novos parâmetros opcionais `filtro_permissionaria_id: int | None = None`
   e `filtro_auto_id: int | None = None`:
   - permissionária: `Ouvidoria.reclamacoes.any(Reclamacao.autos_vinculados.any(ReclamacaoAuto.auto.has(AutoLinha.permissionaria_id == X)))`
   - auto: `Ouvidoria.reclamacoes.any(Reclamacao.autos_vinculados.any(ReclamacaoAuto.auto_id == X))`
   Mesmo padrão dos filtros existentes; nada muda quando os dois são `None`.
2. **Router:** aceitar `filtro_permissionaria_id` e `filtro_auto_id` (`Optional[int]`) em `GET /ouvidorias` e repassar.
3. **Cliente:** mesmos parâmetros em `api/client/ouvidoria_client.py::listar_ouvidorias`, enviados só quando
   preenchidos (como `filtro_subcategoria_id`).
4. **Página:**
   - Nova linha de colunas logo abaixo da linha de Categoria/Subcategoria, com as duas primeiras colunas na
     mesma largura de `col_cat`/`col_sub` (ex.: `st.columns([1.8, 1.8, 6.3])`, sobra vazia) para alinhar.
   - Desenhar a linha só quando `_filtro_tipo` for `None` ou um dos dois tipos regulares; caso contrário,
     `_filtro_perm_id = _filtro_auto_id = None` e nada é desenhado.
   - Selectbox "Empresa" e selectbox "Auto de linha" com as opções conforme as Decisões. Usar keys fixas
     (`filtro_empresa`, `filtro_auto`) e, antes de desenhar cada um, se o valor em `st.session_state` não
     estiver mais nas opções, removê-lo/resetá-lo para a opção "Todas…".
   - Passar `filtro_permissionaria_id` e `filtro_auto_id` para `listar_ouvidorias` (continua uma única chamada
     por render).
   - Incluir os dois ids em `filtros_hash`.
5. **Testes** (`tests/test_t10_filtro_empresa_auto.py`, padrão de `tests/test_e5_writes.py`: banco do `.env`,
   cria e limpa os próprios dados), chamando o repo:
   - ouvidoria com auto da empresa A aparece no filtro da empresa A e não no da empresa B;
   - filtro por auto devolve só ouvidorias com aquele auto vinculado;
   - empresa + auto combinados (AND);
   - sem os filtros, o resultado é o mesmo de antes (ouvidoria sem auto continua aparecendo).

## Critérios de aceite
- C1: os selectboxes Empresa e Auto de linha aparecem abaixo de Categoria/Subcategoria, alinhados a elas.
- C2: tipo regular escolhido → Empresa só lista empresas daquele tipo; "Todos os Tipos" → empresas dos dois
  tipos regulares, sem repetição.
- C3: empresa escolhida → Auto só lista os autos dela (no tipo escolhido); sem empresa → todos os autos do(s) tipo(s).
- C4: tipo Fretamento (metro ou inter) → os dois selectboxes somem e não filtram nada.
- C5: trocar tipo/empresa de forma que a seleção atual saia da lista volta o filtro para "Todas…" sem erro.
- C6: a lista filtra corretamente por empresa, por auto e pelos dois; `listar_ouvidorias` é chamada uma vez
  por render; a paginação volta à página 1 ao mudar esses filtros.
- C7: testes passam: `tests/test_t10_filtro_empresa_auto.py`, `tests/test_e4_ouvidorias.py`,
  `tests/test_page_imports.py`, `tests/test_t04_coluna_assuntos.py`, `tests/test_t06_marcacao_cores.py`.

## Fora de escopo
Filtro por região metropolitana; filtrar fretamento por `empresa_fretamento`; novos endpoints de catálogo;
mudanças em outras páginas ou no dashboard; mostrar empresa/auto como coluna da lista.
