# T07 — Marcação por cores: coluna, filtro e legenda na lista de ouvidorias

## Objetivo
Na página **Ouvidorias** (`frontend/pages/01_Ouvidorias.py`), usar a API da T06 para:
1. **Coluna de cor** em cada linha: mostra a cor do login logado e permite trocar ou tirar.
2. **Filtro "Cor"** no topo.
3. **Popover "🎨 Legenda"** no topo, onde o login dá nome às cores (ex.: 🔴 = "Ana", 🟡 = "Aguardando info").

Vale para gestor e técnico (cada login com as próprias cores — regra da T06).

## Pré-requisitos
T04 (mexe no `col_sizes` desta página) e T06 (API) aprovadas.

## Contexto atual
- Depois da T04: `col_sizes = [1.1, 1.6, 2.5, 1, 3.6, 1.8, 1.0, 1.4, 0.7, 0.7]` e os `headers` correspondentes.
- Cada item da lista (`listar_ouvidorias`) passa a ter `marcacao` (cor ou `None`) — T06.
- Client da T06: `api/client/marcacao_client.py` (`definir_marcacao`, `remover_marcacao`, `carregar_legenda`,
  `salvar_legenda`); constantes `CORES_MARCACAO` e `EMOJI_COR` em `api/client/enums.py`.
- A página invalida dados com `st.session_state["ov_cache_buster"] += 1; st.rerun()`.
- Topo: `_col_tit, _col_tipo = st.columns([2, 2])` (título + Tipo de Serviço). Paginação usa `filtros_hash`.
- O CSS da página já ajusta a largura dos popovers (comentário perto da linha 39) — confira se o da cor fica legível.

## Arquivos envolvidos
- `frontend/pages/01_Ouvidorias.py`
- `tests/test_page_imports.py` (só rodar)

## O que fazer
1. **Legenda carregada uma vez por render**: `legenda = {i["cor"]: i["rotulo"] for i in carregar_legenda(cache_buster=...)}`.
   Helper pequeno `_rotulo_cor(cor) -> str`: `"🔴 Ana"` quando há rótulo, `"🔴 vermelho"` quando não.
2. **Topo**: trocar por `_col_tit, _col_cor, _col_leg, _col_tipo = st.columns([1.6, 1.2, 0.6, 1.6])`
   (pode ajustar as proporções se quebrar visualmente, mantendo título e Tipo de Serviço como estão).
   - `_col_cor`: selectbox **"Cor"** (label colapsado, como o de Tipo de Serviço) com
     `Todas as cores`, as 7 cores via `_rotulo_cor` e `⬜ Sem cor`.
   - `_col_leg`: `st.popover("🎨 Legenda")` com um `st.text_input` por cor (label = emoji, `max_chars=40`,
     valor atual da legenda, `key=f"leg_{cor}"`) e botão **"💾 Salvar"** → `salvar_legenda(...)` com as 7,
     incrementa `ov_cache_buster`, `st.rerun()`. Texto curto explicando: *"Dê um nome a cada cor. Vale para todos que usam este login."*
3. **Filtro**: aplicado na página sobre a lista retornada, **antes** da paginação (`Todas` = sem filtro;
   cor = `o["marcacao"] == cor`; `Sem cor` = `o["marcacao"] is None`). Incluir a escolha em `filtros_hash`
   para voltar à página 1 ao trocar.
4. **Coluna de cor** — nova primeira coluna, antes de `#`:
   - `col_sizes = [0.6, 1.1, 1.6, 2.5, 1, 3.0, 1.8, 1.0, 1.4, 0.7, 0.7]` (Assuntos 3.6→3.0; soma igual à atual);
     cabeçalho `"**Cor**"`; **todos os índices `cols[...]` seguintes andam +1** — revise cada um.
   - Célula: `st.popover(EMOJI_COR[cor] if cor else "⬜", help=_rotulo_cor(cor) if cor else "Sem cor", use_container_width=True)`.
     Dentro: um botão por cor com `_rotulo_cor(cor)` (`type="primary"` na cor atual, `key=f"cor_{o['id']}_{cor}"`)
     e **"✖ Sem cor"** (`key=f"cor_{o['id']}_nenhuma"`, desabilitado quando não há cor).
     Clique → `definir_marcacao` / `remover_marcacao`, incrementa `ov_cache_buster`, `st.rerun()`.
   - Erros da API: `st.error` com a mensagem, como os outros popovers da página.
5. Não mexer em nada além disso (atribuição, status, prazos, popovers 👤/🛠️ continuam iguais).

## Critérios de aceite
- C1: coluna Cor na primeira posição mostra a cor do login (⬜ quando não há) e o rótulo no tooltip.
- C2: escolher uma cor ou "Sem cor" no popover grava pela API e a lista atualiza; cor atual destacada.
- C3: filtro "Cor" (todas / cada cor / sem cor) funciona junto com os demais filtros e reinicia a paginação.
- C4: "🎨 Legenda" mostra os rótulos atuais, salva os 7 (vazio = sem nome) e os nomes aparecem no tooltip, no popover da linha e no filtro.
- C5: larguras conforme o passo 4; índices das colunas existentes corretos (nada trocado de lugar além da nova coluna); `key`s únicas.
- C6: quando a ouvidoria volta à tela do técnico (devolvida/reatribuída) aparece com a cor anterior — conferir manualmente com o fluxo da T06.
- C7: `tests/test_page_imports.py` e `tests/test_t06_marcacao_cores.py` passam.

## Fora de escopo
Página 03 (Detalhe) e demais páginas; mudar a paleta; filtro por cor na API.
