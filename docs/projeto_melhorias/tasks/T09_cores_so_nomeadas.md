# T09 — Marcação por cores: oferecer só as cores nomeadas na legenda + novo símbolo de "sem cor" (revisão da T07)

## Objetivo
Na página **Ouvidorias** (`frontend/pages/01_Ouvidorias.py`), criada/alterada na T07:
1. As cores oferecidas para marcar uma ouvidoria (popover da coluna **Cor**) e no filtro **Cor** devem ser
   **apenas as que têm nome** na legenda (popover **🎨 Legenda**). Cor sem nome não aparece para escolha.
2. O símbolo de "sem cor" hoje é `⬜` (quadrado branco), que chama atenção. Trocar por um **traço** `-` (hífen).

## Decisões
- "Cor nomeada" = cor cujo rótulo na legenda, sem espaços nas pontas, não é vazio.
- **Popover da linha (coluna Cor):** lista só as cores nomeadas. Exceção: se a ouvidoria já está marcada com
  uma cor que perdeu o nome, essa cor continua aparecendo (para o usuário ver qual é e poder trocar).
  "✖ Sem cor" continua igual.
- **Nenhuma cor nomeada:** o popover da linha mostra `st.caption("Dê nome às cores em 🎨 Legenda para usá-las.")`
  no lugar dos botões de cor ("✖ Sem cor" continua, para limpar marcações antigas).
- **Filtro Cor:** "Todas as cores" + cores nomeadas + cores **sem nome que ainda estão em uso** + "- Sem cor",
  na ordem de `CORES_MARCACAO`. "Em uso" = a cor aparece em `marcacao` de alguma ouvidoria devolvida por
  `listar_ouvidorias` (com os demais filtros aplicados, antes do filtro de cor). A cor sem nome aparece com o
  nome da própria cor (ex.: "🔴 vermelho", como `_rotulo_cor` já faz). Assim, ouvidorias marcadas com uma cor
  que perdeu o nome continuam encontráveis pelo filtro.
- **Nome da cor:** pertence à cor, não à marcação. Apagar o nome mantém a cor nas ouvidorias marcadas;
  dar um nome novo vale na hora para todas elas. Nada a implementar além do que já existe.
- **Popover 🎨 Legenda:** continua mostrando as 7 cores (é onde se dá nome a elas).
- **Símbolo `-`** substitui `⬜` em todos os lugares: rótulo do botão da coluna Cor quando não há cor e a
  opção "- Sem cor" do filtro. O tooltip continua "Sem cor".
- Nada muda na API, no banco nem na T06: é só a página.

## Contexto atual
- `_legenda` (dict cor → rótulo) é carregada uma vez por render; `_rotulo_cor(cor)` monta "emoji + rótulo".
- Filtro: `_opcoes_cor = [("", "Todas as cores")] + [(c, _rotulo_cor(c)) for c in CORES_MARCACAO] + [("sem", "⬜ Sem cor")]`.
- Coluna Cor: popover com rótulo `EMOJI_COR[cor_atual] if cor_atual else "⬜"` e laço `for cor in CORES_MARCACAO`.

## Arquivos envolvidos
- `frontend/pages/01_Ouvidorias.py`

## O que fazer
1. Criar a lista das cores nomeadas uma vez, logo após carregar `_legenda`
   (ex.: `_cores_nomeadas = [c for c in CORES_MARCACAO if (_legenda.get(c) or "").strip()]`), mantendo a
   ordem de `CORES_MARCACAO`.
2. Filtro Cor: usar `_cores_nomeadas` + cores sem nome em uso + `"- Sem cor"`. Hoje o selectbox é desenhado
   antes de `listar_ouvidorias`; se precisar, carregue a lista antes de montar as opções (pode reordenar o
   código, mas sem mudar o layout nem chamar a API mais de uma vez por render).
3. Popover da coluna Cor: laço sobre as cores nomeadas, mais a cor atual se ela não estiver na lista;
   caption quando não houver nenhuma cor para oferecer; rótulo do popover `"-"` quando não há cor.
4. Não alterar keys existentes (`cor_{id}_{cor}`, `cor_{id}_nenhuma`, `leg_*`).

## Critérios de aceite
- C1: o popover da linha oferece só cores nomeadas (mais a cor atual, se ela não tiver nome).
- C2: sem nenhuma cor nomeada, aparece o caption pedido e "✖ Sem cor" continua disponível.
- C3: o filtro Cor lista "Todas as cores", as cores nomeadas, as cores sem nome que estão em uso e "- Sem cor";
  o filtro continua funcionando e `listar_ouvidorias` é chamada uma única vez por render.
- C4: o popover 🎨 Legenda continua com as 7 cores.
- C5: `⬜` não aparece mais na página; "sem cor" usa `-`.
- C6: sem mudança de API/banco; testes passam: `tests/test_page_imports.py`, `tests/test_t06_marcacao_cores.py`.

## Fora de escopo
Mudar a paleta de 7 cores; validar no backend se a cor tem nome; mudar outras páginas.
