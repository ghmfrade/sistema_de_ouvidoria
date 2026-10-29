# Projeto de Melhorias — Ouvidorias

Correções e melhorias de fluxo para gestor e técnico, executadas por agentes:

| Papel | Agente | Modelo | Definição |
|---|---|---|---|
| Orquestrador | sessão principal | — | `.claude/skills/orquestrar/SKILL.md` |
| Executor | `executor` | Sonnet | `.claude/agents/executor.md` |
| Revisor | `revisor` | Opus | `.claude/agents/revisor.md` |

**Como rodar:** no Claude Code, `/orquestrar` (todas as pendentes) ou `/orquestrar T02` (uma task).
O orquestrador chama o executor, depois o revisor; se reprovado, devolve o parecer ao executor (até 3 tentativas).
Estado em [STATUS.md](STATUS.md); histórico em `revisoes/`.

## Tasks

| ID | Objetivo | Arquivo |
|---|---|---|
| T01 | Gestor remove técnico responsável no detalhe da ouvidoria | [tasks/T01_remover_tecnico.md](tasks/T01_remover_tecnico.md) |
| T02 | Ouvidoria sai da tela do técnico depois que ele responde; gestor pode devolver para complementação | [tasks/T02_tecnico_sai_apos_responder.md](tasks/T02_tecnico_sai_apos_responder.md) |
| T03 | Técnico pode inserir, alterar e apagar o prazo da permissionária | [tasks/T03_tecnico_prazo_permissionaria.md](tasks/T03_tecnico_prazo_permissionaria.md) |
| T04 | Lista de ouvidorias: trocar Coord./Gerência por Assuntos | [tasks/T04_coluna_assuntos.md](tasks/T04_coluna_assuntos.md) |

As tasks são sequenciais (T02 e T04 mexem na mesma página que T01/T03).

## Decisões de projeto

1. **Atribuição respondida não é apagada (T02).** `ouvidoria_tecnicos` alimenta o dashboard de produtividade
   (filtro por gerência, ranking e vencidas por coordenação). Apagar a linha quando o técnico responde faria
   essas ouvidorias sumirem dos gráficos. Em vez disso, a atribuição fica com `respondido=True` e passa a ser
   ignorada na tela do técnico e na lista de "responsáveis". Reatribuir o mesmo técnico volta a deixá-la pendente.
2. **Remoção pelo gestor apaga a atribuição (T01).** É uma correção manual (técnico errado/desnecessário),
   então a linha é removida de fato. As respostas técnicas que ele já tiver dado continuam no histórico.
3. **"Assuntos" = categoria de cada reclamação (T04)**, na ordem do item, sem repetição.
4. **Gestor e técnico têm o mesmo poder sobre o prazo da permissionária (T03):** inserir, alterar e apagar.
   Editar a ouvidoria ("✏️ Editar") continua só do gestor.
5. **Registro da T02:** "responsável" = linha em `ouvidoria_tecnicos` com `respondido=False`. Quando o técnico
   responde, a linha fica com `respondido=True` + `respondido_em`, e o texto em `respostas_tecnicas` — o histórico
   de quem foi atribuído, quem respondeu e quando é preservado.
6. **Devolução para complementação (T02):** o gestor devolve um técnico específico pelo botão "↩ Devolver"
   (página 03, em "Já responderam"): a atribuição volta a `respondido=False` e o status a `Em análise técnica`.
   Pode se repetir; cada resposta é uma linha nova em `respostas_tecnicas`. Mudar o status para `Em análise técnica`
   sem nenhum técnico pendente reabre todos os que responderam (mantém o hábito atual do gestor).

## Como os testes rodam
`.venv/Scripts/python.exe -m pytest <arquivos> -q --tb=short` — os testes usam o banco de dev do `.env`
e criam/limpam seus próprios dados (padrão de `tests/test_e5_writes.py`).
