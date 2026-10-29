# T04 — Lista de ouvidorias: trocar "Coord./Gerência" por "Assuntos"

## Objetivo
Na página **Ouvidorias** (`frontend/pages/01_Ouvidorias.py`), remover a coluna **Coord./Gerência** e
colocar a coluna **Assuntos**: a lista de categorias das reclamações da ouvidoria, **uma por linha**.
Exemplo — ouvidoria com 3 reclamações:
```
ACESSIBILIDADE
CONDIÇÃO VEICULAR
QUALQUER_OUTRA_COISA
```
Diminuir as colunas **Responsáveis** e **Prazo Perm.** para dar espaço à nova coluna.
Assunto que não couber na largura termina com reticências (`…`).

## Decisão
"Assunto" = `categoria.nome` de cada reclamação, na ordem de `numero_item`, **sem repetir** categoria,
ignorando reclamações sem categoria. Texto exatamente como está no banco.

## Contexto atual
- `get_ouvidorias()` (`api/repositories/ouvidoria_repo.py`) monta `OuvidoriaResumoDict`
  (`api/repositories/types.py`) — não carrega reclamações.
- Schema de resposta: `OuvidoriaResumoSchema` (`api/schemas/ouvidoria.py`).
- Página 01: `_coord_ger()`, `col_sizes = [1.1, 1.6, 2.5, 1, 2.5, 2.5, 1.4, 1.4, 0.7, 0.7]`,
  `headers` com `"**Coord./Gerência**"` na posição 4 e `cols[4].write(_coord_ger(...))`.

## Arquivos envolvidos
- `api/repositories/types.py`
- `api/schemas/ouvidoria.py`
- `api/repositories/ouvidoria_repo.py`
- `frontend/pages/01_Ouvidorias.py`
- `tests/test_t04_coluna_assuntos.py` (novo)

## O que fazer
1. **Tipos/schema**: adicionar `assuntos: list[str]` em `OuvidoriaResumoDict` e
   `assuntos: list[str] = []` em `OuvidoriaResumoSchema`.
2. **`get_ouvidorias`**: carregar `Ouvidoria.reclamacoes` → `Reclamacao.categoria` com `joinedload`
   (evitar N+1) e preencher `assuntos` conforme a decisão acima. Extraia a montagem para um helper pequeno
   (ex.: `_assuntos(o)`). Não mude filtros nem ordenação.
3. **Página 01**:
   - remover `_coord_ger()` e a coluna Coord./Gerência (cabeçalho e célula);
   - nova coluna **Assuntos** na mesma posição;
   - larguras: `col_sizes = [1.1, 1.6, 2.5, 1, 3.6, 1.8, 1.0, 1.4, 0.7, 0.7]`
     (Assuntos 3.6, Responsáveis 2.5→1.8, Prazo Perm. 1.4→1.0; soma total igual à atual);
   - célula: cada assunto em uma linha, via `st.markdown(..., unsafe_allow_html=True)` com cada item num
     `<div>` com `white-space:nowrap; overflow:hidden; text-overflow:ellipsis;` e `title` com o texto completo
     (tooltip). **Escape o texto com `html.escape`.** Sem assuntos → `"–"`;
   - `_responsaveis` não muda nesta task (a T02 já o ajustou).
4. **Testes** — `tests/test_t04_coluna_assuntos.py`: criar ouvidoria (gestor) com 3 reclamações usando duas
   categorias distintas, com a primeira repetida no 3º item; `GET /ouvidorias?ocultar_concluidos=false` →
   o item da ouvidoria tem `assuntos == [nome_cat_A, nome_cat_B]`. Apagar no `finally`.
   Use `get_categorias()` como em `tests/test_e5_writes.py` para obter 2 categorias.

## Critérios de aceite
- C1: coluna Coord./Gerência removida da página 01 (e `_coord_ger` apagado).
- C2: coluna Assuntos mostra uma categoria por linha, na ordem dos itens, sem repetição; `–` se vazia.
- C3: texto que não cabe termina com reticências (CSS `text-overflow: ellipsis`) e o completo aparece no tooltip; HTML escapado.
- C4: larguras conforme o passo 3; Responsáveis e Prazo Perm. menores.
- C5: `assuntos` vem da API (`/ouvidorias`), sem N+1, sem quebrar os demais campos do resumo.
- C6: testes novos passam, além de `tests/test_page_imports.py` e `tests/test_e4_ouvidorias.py`.

## Fora de escopo
Remover `gerencia_nome`/`coordenacao_nome` da API (outros lugares podem usar); mudar outras páginas.
