# T02 — Ouvidoria sai da tela do técnico depois que ele responde (e pode ser devolvida)

## Objetivo
1. Quando o técnico registra a resposta técnica (página **05 Responder** → "📤 Enviar Resposta"),
   ele deixa de ser **técnico responsável** e a ouvidoria sai da tela dele.
2. O gestor precisa conseguir **devolver** a ouvidoria a um técnico que já respondeu, para complementação.
   Ao devolver, a ouvidoria volta para a tela daquele técnico e ele pode registrar uma nova resposta.
   Isso pode acontecer quantas vezes for necessário.

## Modelo de registro (ver README)
- "Responsável" = linha em `ouvidoria_tecnicos` com `respondido=False`.
- Responder → `respondido=True`, `respondido_em=agora` (já é o que `registrar_resposta_tecnica` faz) + nova linha em `respostas_tecnicas`.
- Devolver → mesma linha volta para `respondido=False`, `respondido_em=None`. As respostas anteriores continuam em `respostas_tecnicas`
  (cada rodada é uma linha nova, com técnico e data), então o histórico de todas as rodadas fica preservado.
- **Não apagar** a linha de `ouvidoria_tecnicos` ao responder: o dashboard de produtividade
  (`api/repositories/dashboard/produtividade_repo.py`) depende dela.

## Contexto atual
- `registrar_resposta_tecnica()` (`api/repositories/ouvidoria_write_repo.py`) marca `respondido=True`/`respondido_em`
  e muda o status para `RETORNO_TECNICO` quando todos responderam. **Não mudar.**
- `get_ouvidorias()` (`api/repositories/ouvidoria_repo.py`): no filtro "apenas atribuídas" do técnico, faz join em
  `OuvidoriaTecnico` filtrando só `tecnico_id` — por isso a ouvidoria continua aparecendo depois de respondida.
- `atribuir_tecnico()` retorna `False` (rota → 409) se a linha já existe, mesmo respondida.
- Hoje o gestor "devolve" mudando o status para `Em análise técnica` (popover de status da página 01 ou dialog
  "✏️ Editar" da página 03, ambos via `editar_ouvidoria()` no write repo). A página 05 tem a mensagem
  "O gestor retornou esta ouvidoria para análise técnica…".
- Página 03 mostra todos os técnicos com ✅/⏳; o seletor "➕ Atribuir Técnico" exclui todos os já atribuídos;
  o botão "✍️ Inserir Resposta Técnica" aparece se o técnico estiver em `tecnicos_info`.
- Página 01, `_responsaveis()` lista todos os técnicos atribuídos.

## Arquivos envolvidos
- `api/repositories/ouvidoria_repo.py`
- `api/repositories/ouvidoria_write_repo.py`
- `api/routers/ouvidorias.py`
- `api/client/ouvidoria_client.py`
- `frontend/pages/03_Detalhe_Ouvidoria.py`
- `frontend/pages/01_Ouvidorias.py`
- `frontend/pages/05_Responder.py` (só a mensagem de complementação)
- `tests/test_t02_tecnico_sai_apos_responder.py` (novo)

## O que fazer

### Backend
1. **`get_ouvidorias`**: no filtro "apenas atribuídas" do técnico, acrescentar `OuvidoriaTecnico.respondido.is_(False)`.
   O resto da consulta não muda (com "Apenas atribuídas" desmarcado o técnico continua vendo todas).
2. **Write repo — `devolver_ao_tecnico(ouvidoria_id: int, tecnico_id: int) -> bool`**:
   - se a atribuição não existe → `False`;
   - se existe e já está pendente → `True` sem mudar nada (idempotente);
   - se está respondida → `respondido=False`, `respondido_em=None`;
   - status: se não estiver `CONCLUIDO`, passa para `EM_ANALISE_TECNICA`. Se estiver `CONCLUIDO`, não devolve e retorna `False`.
3. **`atribuir_tecnico`**: se a linha já existe e está **respondida**, em vez de 409 reaproveita `devolver_ao_tecnico`
   (mesmo efeito) e retorna `True`. Se existe e está pendente → `False` (409), como hoje. Além do caso atual
   (`AGUARDANDO_ACOES` → `EM_ANALISE_TECNICA`), uma atribuição nova em `RETORNO_TECNICO` também vai para `EM_ANALISE_TECNICA`.
4. **`editar_ouvidoria`** (rede de segurança para o hábito atual): quando o `status` muda **para** `EM_ANALISE_TECNICA`
   e a ouvidoria **não tem nenhuma atribuição pendente**, reabrir todas as atribuições respondidas
   (`respondido=False`, `respondido_em=None`). Se já houver alguma pendente, não mexe nas atribuições.
5. **Rota** — `POST /ouvidorias/{ouvidoria_id}/tecnicos/{tecnico_id}/devolver`, `requer_gestor`.
   `{"ok": True}`; `404` "Técnico não atribuído a esta ouvidoria" ou `409` "Ouvidoria concluída" conforme o caso
   (distinga os dois no repositório como achar mais limpo, ex. retornando um motivo).
6. **Client** — `devolver_ao_tecnico(oid: int, tecnico_id: int) -> None`.

### Frontend
7. **Página 03** (`03_Detalhe_Ouvidoria.py`), seção "👥 Técnicos Responsáveis":
   - separar `ouvidoria["atribuicoes"]` em **pendentes** e **respondidas**;
   - lista principal = pendentes (⏳ nome; para gestor, o botão 🗑 da T01 continua aqui);
   - abaixo, se houver respondidas, um subtítulo pequeno "Já responderam" com ✅ nome e, **só para gestor** e se a ouvidoria
     não estiver concluída, `st.button("↩ Devolver", key=f"dev_tec_{tid}", help="Devolver para complementação")`
     → chama `devolver_ao_tecnico`, `st.toast("Ouvidoria devolvida ao técnico.")`, `st.rerun()`;
   - o seletor "➕ Atribuir Técnico" exclui só os técnicos **pendentes**;
   - o botão "✍️ Inserir Resposta Técnica" só aparece se o técnico logado tiver atribuição **pendente**.
8. **Página 01**: `_responsaveis()` lista só técnicos pendentes (`"–"` se nenhum).
9. **Página 05**: trocar a condição/mensagem atual de "o gestor retornou…" para: se o técnico tem atribuição **pendente**
   e já tem resposta anterior (`historico` não vazio) → `st.info("O gestor devolveu esta ouvidoria para complementação. Registre uma nova resposta.")`.
   Se a atribuição estiver respondida → mensagem de sucesso "Você já registrou sua resposta…" e `st.stop()` (independente do status).
   Não mexer no resto da página.

### Testes — `tests/test_t02_tecnico_sai_apos_responder.py`
Fixtures de `tests/conftest.py`; ouvidoria criada pelo gestor e apagada no `finally`. Listagem do técnico =
`GET /ouvidorias?usuario_id=<tec>&usuario_tipo=tecnico&filtrar_apenas_atribuidas=true&ocultar_concluidos=true`.
- atribui → aparece na listagem do técnico;
- técnico responde → **some** da listagem; `GET /ouvidorias/{id}` tem a atribuição com `respondido=True` e 1 resposta técnica;
- gestor devolve (`POST …/devolver`) → 200, status `Em análise técnica`, atribuição pendente, **reaparece** na listagem;
- técnico responde de novo → some; agora há **2** respostas técnicas (histórico preservado);
- gestor muda status para `Em análise técnica` via `PATCH /ouvidorias/{id}` (sem pendentes) → atribuição volta a pendente;
- atribuir enquanto pendente → 409; atribuir após respondido → 200 e volta a pendente;
- devolver técnico não atribuído → 404; técnico chamando devolver → 403;
- ouvidoria concluída: devolver → 409.

## Critérios de aceite
- C1: depois de responder, a ouvidoria some da lista do técnico ("Apenas atribuídas" marcado).
- C2: a atribuição não é apagada; dashboards intactos; `registrar_resposta_tecnica` e `produtividade_repo.py` não alterados.
- C3: gestor devolve um técnico específico pelo botão "↩ Devolver" na página 03; a ouvidoria volta à tela dele com status `Em análise técnica`.
- C4: devolver pode se repetir várias vezes; cada resposta fica em `respostas_tecnicas` (histórico completo).
- C5: mudar o status para `Em análise técnica` sem técnicos pendentes reabre os que responderam (o fluxo atual do gestor continua funcionando).
- C6: técnico que já respondeu não aparece como responsável (páginas 01 e 03), mas aparece em "Já responderam".
- C7: atribuir técnico pendente → 409; técnico que já respondeu pode ser reatribuído (equivale a devolver).
- C8: página 05 mostra a mensagem de complementação quando devolvida, e bloqueia nova resposta quando já respondida.
- C9: testes novos passam, além de `tests/test_page_imports.py`, `tests/test_e4_ouvidorias.py` e `tests/test_e5_writes.py`.

## Fora de escopo
Coluna Coord./Gerência (é a T04); botão de devolver na página 01; notificação por e-mail.
