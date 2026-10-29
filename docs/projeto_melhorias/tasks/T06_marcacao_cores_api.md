# T06 — Marcação por cores: banco e API

## Objetivo
O login do técnico é compartilhado por um núcleo de 4–5 pessoas. Elas precisam marcar ouvidorias com uma
**cor** (ex.: uma cor por pessoa, ou "aguardando info") e dar um **nome** a cada cor (legenda).
Esta task cria o banco e a API; a interface é a T07.

Regras:
- **Por login**: cada usuário vê só as próprias marcações e a própria legenda. Ninguém vê as de outro login
  (nem o gestor). Qualquer perfil (gestor ou técnico) pode usar.
- **Uma cor por ouvidoria por login.**
- **A cor nunca se perde sozinha.** Ela não depende de atribuição, resposta ou status: continua gravada se o
  técnico for removido (T01), se responder e a ouvidoria sair da tela (T02), se for devolvido, ou se a
  ouvidoria for concluída. Quando a ouvidoria voltar a aparecer, volta com a mesma cor.
  A marcação só some quando o usuário escolhe **"sem cor"** ou quando a ouvidoria é excluída.
- **Paleta fixa** de 7 cores: `vermelho`, `laranja`, `amarelo`, `verde`, `azul`, `roxo`, `marrom`.
- Trocar o rótulo da legenda não mexe nas marcações (a ouvidoria 🔴 continua 🔴, só muda o nome exibido).

## Contexto atual
- Modelos em `api/models/` (exportados em `api/models/__init__.py`); migrations Alembic em `api/migrations/versions/`.
  **Head atual: `a2b3c4d5e6f7`** (`remove_unique_email_usuarios`). Banco é PostgreSQL.
- `GET /ouvidorias` (`api/routers/ouvidorias.py::listar_ouvidorias`) usa `_=Depends(usuario_corrente)` e recebe
  `usuario_id` por query param (só para o filtro do técnico). O id confiável do usuário logado é
  `int(payload["sub"])` do token (exemplo em `upload` de anexos, mesmo arquivo).
- `get_ouvidorias()` (`api/repositories/ouvidoria_repo.py`) monta `OuvidoriaResumoDict` (`api/repositories/types.py`);
  schema `OuvidoriaResumoSchema` (`api/schemas/ouvidoria.py`).
- `excluir_ouvidoria()` faz `s.delete(o)` via ORM. `tests/conftest.py::_limpar_dados_pytest` apaga usuários de
  teste com SQL cru (`DELETE FROM usuarios ...`).
- Constantes para o Streamlit ficam em `api/client/enums.py` (sem SQLAlchemy).

## Arquivos envolvidos
- `api/models/marcacao.py` (novo) e `api/models/__init__.py`
- `api/migrations/versions/<rev>_add_marcacoes_cores.py` (novo)
- `api/repositories/marcacao_repo.py` (novo)
- `api/repositories/types.py`, `api/repositories/ouvidoria_repo.py`
- `api/schemas/ouvidoria.py` (ou `api/schemas/marcacao.py` novo, se preferir)
- `api/routers/ouvidorias.py`, `api/routers/marcacoes.py` (novo), `api/main.py`
- `api/client/marcacao_client.py` (novo), `api/client/enums.py`
- `tests/test_t06_marcacao_cores.py` (novo)

## O que fazer
1. **Modelos** (`api/models/marcacao.py`):
   - `CorMarcacao(str, enum.Enum)` com os 7 valores acima (nesta ordem).
   - `OuvidoriaMarcacao` — tabela `ouvidoria_marcacoes`:
     `ouvidoria_id` (FK `ouvidorias.id`, `ondelete="CASCADE"`, PK), `usuario_id` (FK `usuarios.id`,
     `ondelete="CASCADE"`, PK), `cor` (`String(20)`, not null), `marcado_em` (`DateTime`, `server_default=func.now()`,
     `onupdate=func.now()`).
   - `MarcadorLegenda` — tabela `marcador_legendas`:
     `usuario_id` (FK `usuarios.id`, `ondelete="CASCADE"`, PK), `cor` (`String(20)`, PK), `rotulo` (`String(40)`, not null).
   - Guardar `cor` como string (não criar ENUM no Postgres); a validação fica no schema.
   - **Não** criar relationship em `Ouvidoria`/`OuvidoriaTecnico`: a marcação é independente da atribuição.
     A exclusão da ouvidoria e do usuário apaga as linhas pelo `ON DELETE CASCADE` do banco.
   - Exportar os três em `api/models/__init__.py`.
2. **Migration** com `down_revision = "a2b3c4d5e6f7"`: cria as duas tabelas com as FKs `ON DELETE CASCADE`
   e um `CheckConstraint` em `cor` limitando aos 7 valores. `downgrade` apaga as duas.
   Rode `alembic upgrade head` no banco de dev.
3. **Repositório** (`api/repositories/marcacao_repo.py`), seguindo a regra de `types.py` (sem ORM fora da sessão):
   - `definir_marcacao(ouvidoria_id, usuario_id, cor) -> bool` — upsert; `False` se a ouvidoria não existir.
   - `remover_marcacao(ouvidoria_id, usuario_id) -> None` — idempotente.
   - `get_marcacoes_usuario(usuario_id, ouvidoria_ids) -> dict[int, str]` — **uma** query, `{ouvidoria_id: cor}`.
   - `get_legenda(usuario_id) -> list[LegendaItemDict]` — sempre as 7 cores na ordem do enum,
     `rotulo=""` quando não definido. Adicione `LegendaItemDict(cor: str, rotulo: str)` em `types.py`.
   - `salvar_legenda(usuario_id, itens: list[dict]) -> None` — para cada item: `rotulo.strip()`; vazio apaga a
     linha, senão upsert. Cores não enviadas ficam como estão.
4. **Resumo da lista**: `marcacao: str | None` em `OuvidoriaResumoDict` e `marcacao: str | None = None` em
   `OuvidoriaResumoSchema`. `get_ouvidorias` ganha `marcador_usuario_id: int | None = None`; depois da query
   principal, chama `get_marcacoes_usuario` uma vez com os ids retornados (sem N+1, sem join que altere
   filtros/ordenação) e preenche `marcacao`. A rota `listar_ouvidorias` passa a usar `payload=Depends(usuario_corrente)`
   e envia `marcador_usuario_id=int(payload["sub"])` — **nunca** o `usuario_id` do query param.
5. **Rotas** (todas com `usuario_corrente`; o usuário é sempre `int(payload["sub"])`):
   - `PUT /ouvidorias/{id}/marcacao` body `{"cor": "<cor>"}` → 200; 404 se a ouvidoria não existe; 422 se a cor
     não é uma das 7 (use `CorMarcacao`/`Literal` no schema do request).
   - `DELETE /ouvidorias/{id}/marcacao` → 200 (mesmo sem marcação).
   - Novo router `api/routers/marcacoes.py`, registrado em `api/main.py` com `prefix="/marcacoes"`:
     `GET /marcacoes/legenda` → lista de `{cor, rotulo}`; `PUT /marcacoes/legenda` body
     `{"itens": [{"cor": ..., "rotulo": ...}]}` → 200, `rotulo` com no máximo 40 caracteres (422 acima disso).
6. **Client** (`api/client/marcacao_client.py`, mesmo estilo de `ouvidoria_client.py`, sem cache):
   `definir_marcacao(oid, cor)`, `remover_marcacao(oid)`, `carregar_legenda(cache_buster: int = 0)`,
   `salvar_legenda(itens)`.
   Em `api/client/enums.py`: `CORES_MARCACAO = ["vermelho", "laranja", "amarelo", "verde", "azul", "roxo", "marrom"]`
   e `EMOJI_COR = {"vermelho": "🔴", "laranja": "🟠", "amarelo": "🟡", "verde": "🟢", "azul": "🔵", "roxo": "🟣", "marrom": "🟤"}`.
7. **Testes** — `tests/test_t06_marcacao_cores.py` (padrão de `tests/test_t02_tecnico_sai_apos_responder.py`;
   crie a ouvidoria como gestor e apague no `finally`; limpe a legenda do técnico de teste ao final):
   - técnico marca `vermelho` → `GET /ouvidorias` (como técnico) traz `marcacao == "vermelho"`; troca para `verde` → `"verde"`.
   - **isolamento**: a mesma ouvidoria listada pelo gestor vem com `marcacao` nula; gestor marca `azul` e o técnico continua vendo `verde`.
   - **persistência** — com a ouvidoria marcada pelo técnico, executar em sequência e conferir que a marcação continua
     a mesma em cada passo (lendo com `filtrar_apenas_atribuidas=false&ocultar_concluidos=false` quando ela não aparecer na fila):
     atribuir técnico → técnico responde (sai da fila) → gestor devolve (volta à fila, com a cor) →
     gestor remove o técnico → gestor reatribui (volta, com a cor) → gestor conclui.
   - `DELETE /ouvidorias/{id}/marcacao` → `marcacao` nula; repetir o DELETE → 200.
   - cor inválida → 422; ouvidoria inexistente → 404.
   - legenda: `GET` sem nada salvo → 7 itens na ordem, rótulos vazios; `PUT` com `vermelho="Ana"`, `verde="  João "` →
     `GET` traz `"Ana"` e `"João"`; `PUT` com `vermelho=""` → volta a `""`; rótulo com 41 caracteres → 422;
     legenda do gestor não é afetada.
   - excluir a ouvidoria marcada não dá erro (cascade).

## Critérios de aceite
- C1: tabelas `ouvidoria_marcacoes` e `marcador_legendas` criadas por migration a partir do head `a2b3c4d5e6f7`, com FKs `ON DELETE CASCADE`.
- C2: marcação e legenda são por login (id do token); um login não vê nem altera as de outro.
- C3: a marcação sobrevive a responder, devolver, remover/reatribuir técnico e concluir; só some com "sem cor" ou exclusão da ouvidoria.
- C4: `GET /ouvidorias` traz `marcacao` com uma query extra no máximo, sem mudar filtros, ordenação nem os demais campos.
- C5: excluir ouvidoria e a limpeza de usuários do `conftest.py` continuam funcionando.
- C6: testes novos passam, além de `tests/test_e4_ouvidorias.py`, `tests/test_e5_writes.py`,
  `tests/test_t01_remover_tecnico.py`, `tests/test_t02_tecnico_sai_apos_responder.py` e `tests/test_page_imports.py`.

## Fora de escopo
Interface (T07); marcação na página 03 (Detalhe); qualquer relatório/dashboard por cor.
