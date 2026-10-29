# T01 — Gestor remove técnico responsável no detalhe da ouvidoria

## Objetivo
No **Detalhe da Ouvidoria** (login de gestor), na seção **👥 Técnicos Responsáveis**, cada técnico listado
ganha um botão de lixeira (🗑). Ao clicar, o técnico deixa de ser responsável por aquela ouvidoria.

## Contexto atual
- Atribuição = linha em `ouvidoria_tecnicos` (`api/models/associations.py`, classe `OuvidoriaTecnico`,
  PK composta `ouvidoria_id` + `tecnico_id`).
- Atribuir: `atribuir_tecnico()` em `api/repositories/ouvidoria_write_repo.py`, rota
  `POST /ouvidorias/{id}/atribuir-tecnico` em `api/routers/ouvidorias.py`, client
  `atribuir_tecnico()` em `api/client/ouvidoria_client.py`.
- Não existe remoção.
- A seção fica em `frontend/pages/03_Detalhe_Ouvidoria.py` (bloco `### 👥 Técnicos Responsáveis`,
  laço `for tid, info in tecnicos_info.items()`).

## Arquivos envolvidos
- `api/repositories/ouvidoria_write_repo.py`
- `api/routers/ouvidorias.py`
- `api/client/ouvidoria_client.py`
- `frontend/pages/03_Detalhe_Ouvidoria.py`
- `tests/test_t01_remover_tecnico.py` (novo)

## O que fazer
1. **Repositório** — `remover_tecnico(ouvidoria_id: int, tecnico_id: int) -> bool`:
   - apaga a linha de `OuvidoriaTecnico`; retorna `False` se não existir;
   - depois de remover, se a ouvidoria estiver `EM_ANALISE_TECNICA` e **não restar nenhuma atribuição pendente**
     (`respondido=False`): vai para `RETORNO_TECNICO` se a ouvidoria tiver alguma `RespostaTecnica`,
     senão volta para `AGUARDANDO_ACOES`. Outros status não mudam.
   - Respostas técnicas já registradas pelo técnico **não** são apagadas.
2. **Rota** — `DELETE /ouvidorias/{ouvidoria_id}/tecnicos/{tecnico_id}`, protegida por `requer_gestor`.
   Retorna `{"ok": True}`; `404` com `detail="Técnico não atribuído a esta ouvidoria"` se `remover_tecnico` retornar `False`.
   Siga o padrão das rotas vizinhas (import local do write repo).
3. **Client** — `remover_tecnico(oid: int, tecnico_id: int) -> None` usando o helper `delete` de `api/client/base.py`
   (confira o nome real do helper; siga o padrão de `excluir_ouvidoria`).
4. **Página 03** — na lista de técnicos responsáveis:
   - para gestor: cada técnico em uma linha `st.columns([6, 1])`, nome com o ícone de status à esquerda e
     `st.button("🗑", key=f"rem_tec_{tid}", help="Remover técnico")` à direita;
   - ao clicar: chama `remover_tecnico`, `st.toast("Técnico removido.")` e `st.rerun()`;
   - para técnico: continua só o texto, sem botão.
   - Não mexa no restante da página.
5. **Testes** — `tests/test_t01_remover_tecnico.py` (use as fixtures `client`, `headers_gestor`, `headers_tecnico`,
   `_tecnico_id` de `tests/conftest.py`; crie a ouvidoria como em `tests/test_e5_writes.py` e apague no `finally`):
   - gestor atribui o técnico de teste, remove → 200, e `GET /ouvidorias/{id}` não traz mais o técnico em `atribuicoes`;
   - remover de novo → 404;
   - técnico tentando remover → 403;
   - status: ouvidoria em `Em análise técnica` sem respostas técnicas volta para `Aguardando ações` ao remover o único técnico.

## Critérios de aceite
- C1: `DELETE /ouvidorias/{id}/tecnicos/{tecnico_id}` existe, exige gestor, retorna 404 se não atribuído.
- C2: remoção apaga só a atribuição; respostas técnicas permanecem.
- C3: regra de status do passo 1 implementada (e não altera status fora de `EM_ANALISE_TECNICA`).
- C4: botão 🗑 aparece ao lado de cada técnico só para gestor, com `key` única por técnico; clique remove e recarrega.
- C5: page só usa `api/client` (sem import de repositório).
- C6: testes novos passam, além de `tests/test_page_imports.py` e `tests/test_e5_writes.py`.

## Fora de escopo
Confirmação antes de remover; remoção pela página de lista (01); qualquer mudança no fluxo de resposta (é a T02).
