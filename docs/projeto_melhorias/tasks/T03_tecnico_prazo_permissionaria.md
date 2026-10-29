# T03 — Técnico pode inserir, alterar e apagar o prazo da permissionária

## Objetivo
No **Detalhe da Ouvidoria**, o gestor tem o popover **"📅 Prazo Permissionária"** (ver prazo atual,
"✏️ Alterar data", "💾 Salvar") e o botão **"🗑 Apagar prazo da Permissionária"**.
O técnico passa a ter **o mesmo poder do gestor sobre esse prazo**:
- **inserir** um prazo quando não existe;
- **alterar** o prazo existente;
- **apagar** o prazo totalmente.

Nada além desse prazo muda para o técnico (ele continua sem "✏️ Editar" ouvidoria).

## Contexto atual
- Rota `PATCH /ouvidorias/{id}/prazo-permissionaria` em `api/routers/ouvidorias.py` usa `requer_gestor` → técnico recebe 403.
- Client `atualizar_prazo_permissionaria()` em `api/client/ouvidoria_client.py` já existe.
- Em `frontend/pages/03_Detalhe_Ouvidoria.py`, o bloco `# ── Botões de ação (gestor)` cria
  `col_editar, col_prazo_perm, col_apagar_prazo, col_espaco` e tudo (Editar, popover de prazo, Apagar prazo)
  fica dentro de `if u.get("tipo") == TIPO_USUARIO_GESTOR:`.

## Arquivos envolvidos
- `api/routers/ouvidorias.py`
- `frontend/pages/03_Detalhe_Ouvidoria.py`
- `tests/test_t03_tecnico_prazo_permissionaria.py` (novo)

## O que fazer
1. **Rota**: trocar `requer_gestor` por `usuario_corrente` **só** em `atualizar_prazo_permissionaria`
   (a mesma rota já serve para inserir/alterar — data — e apagar — `prazo: null`).
   `PATCH /ouvidorias/{id}` (editar geral) continua exigindo gestor.
2. **Página 03**: reorganizar o bloco de botões para que:
   - as colunas sejam criadas para qualquer usuário;
   - "✏️ Editar" continue **só para gestor**;
   - o popover "📅 Prazo Permissionária" (alterar/salvar; quando não há prazo, mostra "não definido" e permite inserir)
     **e** o botão "🗑 Apagar prazo da Permissionária" (visível quando há prazo) apareçam para **gestor e técnico**,
     com o mesmo comportamento atual;
   - não duplique código — um único bloco usado pelos dois perfis.
3. **Testes** — `tests/test_t03_tecnico_prazo_permissionaria.py` (crie a ouvidoria como gestor **sem** prazo da permissionária e apague no `finally`):
   - técnico **insere** prazo (`PATCH /ouvidorias/{id}/prazo-permissionaria` com data) → 200, `GET /ouvidorias/{id}` retorna a data;
   - técnico **altera** para outra data → 200, `GET` retorna a nova data;
   - técnico **apaga** (`{"prazo": null}`) → 200, `GET` retorna `prazo_permissionaria` nulo;
   - técnico faz `PATCH /ouvidorias/{id}` (editar geral) → 403;
   - gestor continua conseguindo alterar e apagar (200).

## Critérios de aceite
- C1: técnico insere, altera e apaga o prazo da permissionária pela API (200) e pela página 03.
- C2: técnico continua sem acesso a editar ouvidoria (403) e não vê o botão "✏️ Editar".
- C3: comportamento do gestor inalterado.
- C4: sem duplicação do bloco do popover/botão apagar; `key`s de widget continuam únicas.
- C5: testes novos passam, além de `tests/test_page_imports.py` e `tests/test_e5_writes.py`.

## Fora de escopo
Mudar o prazo da permissionária em outras páginas (01, 04, 05).
