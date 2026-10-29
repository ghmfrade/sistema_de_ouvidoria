# T05 — Lista de ouvidorias: gerenciar técnicos no popover 👤

## Objetivo
Na página **Ouvidorias** (`frontend/pages/01_Ouvidorias.py`), login de gestor, o popover **👤** de cada linha
passa a mostrar os técnicos da ouvidoria e a permitir **remover** (T01) e **devolver** (T02) sem abrir o detalhe,
além de atribuir como hoje. Layout pedido:

```
Técnicos responsáveis
⏳ TÉCNICO XYZ        [🗑]
⏳ TÉCNICO HXHS       [🗑]
✅ TÉCNICO ABC        [🔄]
──────────────
Atribuir técnico
[selectbox com técnicos]  [✔️]
```

## Decisões
- **Símbolos:** `⏳` = aguardando resposta (mesmo ícone da página 03); `✅` = já respondeu; `🗑` = remover;
  `🔄` = devolver para complementação (só o símbolo, sem texto); `✔️` = confirmar atribuição (substitui o texto "Atribuir").
  Todos os botões só com símbolo levam `help=` com o texto da ação ("Remover técnico", "Devolver para complementação",
  "Atribuir técnico").
- **Regras iguais às da página 03** (README, decisões 2, 5 e 6): pendentes = `respondido=False`, com 🗑;
  respondidos = `respondido=True`, com 🔄 apenas se a ouvidoria não estiver `Concluído` (se estiver, só o nome com ✅);
  o selectbox de atribuir exclui apenas os técnicos **pendentes** (quem já respondeu pode ser reatribuído = reaberto).
- **Página 03 não muda** nesta task (o "↩ Devolver" de lá continua como está).
- **Largura:** o popover deve ficar largo o suficiente para nome + botão na mesma linha sem quebrar (alvo ~420px).

## Contexto atual
- Popover em `01_Ouvidorias.py`, bloco `if u.get("tipo") == TIPO_USUARIO_GESTOR: with cols[8]: with st.popover("👤"):`.
  Hoje tem só `st.selectbox("Técnico", ...)` + `st.button("Atribuir", key=f"atr_btn_{o['id']}")`.
- Cada `o["atribuicoes"]` traz `tecnico_id`, `tecnico_nome`, `respondido`, `respondido_em` (`OuvidoriaTecnicoDict`
  em `api/repositories/types.py`).
- Client já tem `remover_tecnico(oid, tecnico_id)` e `devolver_ao_tecnico(oid, tecnico_id)` em
  `api/client/ouvidoria_client.py` (T01/T02). A página 03 (`03_Detalhe_Ouvidoria.py`, seção
  `### 👥 Técnicos Responsáveis`) é a referência de comportamento.
- A lista usa `st.session_state["ov_cache_buster"] += 1; st.rerun()` para recarregar após alterações.
- Streamlit: `.venv` tem 1.54.0, `frontend/requirements.txt` fixa 1.58.0.

## Arquivos envolvidos
- `frontend/pages/01_Ouvidorias.py`

## O que fazer
1. Importar `remover_tecnico` e `devolver_ao_tecnico` de `api.client.ouvidoria_client`.
2. No popover 👤, montar o bloco "Técnicos responsáveis" (`st.write("**Técnicos responsáveis**")`):
   - pendentes primeiro, depois respondidos, cada um em `st.columns([5, 1])`: nome com ícone à esquerda, botão à direita;
   - 🗑: `key=f"rem_tec_{o['id']}_{tid}"` → `remover_tecnico`, `st.toast("Técnico removido.")`;
   - 🔄: `key=f"dev_tec_{o['id']}_{tid}"` → `devolver_ao_tecnico`, `st.toast("Ouvidoria devolvida ao técnico.")`;
   - após cada ação: `st.session_state["ov_cache_buster"] += 1; st.rerun()`;
   - sem atribuições: `st.caption("Nenhum técnico atribuído.")`.
3. `st.divider()` e o bloco "Atribuir técnico" (`st.write("**Atribuir técnico**")`): `st.columns([5, 1])` com o
   selectbox (`label_visibility="collapsed"`, mesma key `atr_tec_{o['id']}`) e o botão `✔️` (mesma key `atr_btn_{o['id']}`),
   mantendo o toast/aviso atuais. Lista sem os pendentes; se vazia, `st.caption("Nenhum técnico disponível.")`.
4. **Largura do popover:** verificar se `st.popover` tem parâmetro nativo para a largura do painel nas versões 1.54 e 1.58.
   Se não tiver, aplicar CSS uma única vez na página (fora do laço) via `st.markdown("<style>…</style>", unsafe_allow_html=True)`
   mirando o corpo do popover (confira o `data-testid` real no DOM da versão instalada, ex. `stPopoverBody`), com
   `min-width` ~420px. O CSS não pode alterar o popover de status (coluna 3) nem o 🛠️ de forma que quebre o layout —
   se só for possível afetar todos os popovers, aceite desde que os outros continuem legíveis e informe no relatório.
5. Não mexer em mais nada da página (colunas, outros popovers, filtros).

## Critérios de aceite
- C1: popover 👤 lista pendentes (⏳ + 🗑) e respondidos (✅ + 🔄, sem 🔄 quando `Concluído`), na ordem pendentes → respondidos.
- C2: 🗑 e 🔄 chamam as funções do client, mostram o toast e recarregam a lista; keys únicas por ouvidoria **e** técnico.
- C3: bloco "Atribuir técnico" abaixo de um divider, selectbox + botão ✔️ na mesma linha; exclui só os pendentes.
- C4: todos os botões só com símbolo têm `help`.
- C5: popover 👤 mais largo, nome e botão na mesma linha para nomes comuns; outros popovers não quebram.
- C6: page só usa `api/client`; continua visível só para gestor.
- C7: `tests/test_page_imports.py`, `tests/test_t01_remover_tecnico.py` e `tests/test_t02_tecnico_sai_apos_responder.py` passam.

## Fora de escopo
Mudar a página 03; confirmação antes de remover; mudanças na API.
