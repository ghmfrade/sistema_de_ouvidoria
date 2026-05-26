# Bug: PATCH /ouvidorias/{id}/reclamacoes não aparece no /docs do FastAPI

## Status
Investigação em andamento — acesso remoto perdido. Continuar presencialmente.

---

## Contexto do bug

Após o commit `10c0bc0` foram adicionados:
- Endpoint `PATCH /ouvidorias/{ouvidoria_id}/reclamacoes` em `api/routers/ouvidorias.py` (linha 164)
- Schema `AtualizarReclamacoesRequest` em `api/schemas/ouvidoria.py` (linha 195)
- Função `atualizar_reclamacoes` em `repositories/ouvidoria_write_repo.py` (linha 259)
- Função `atualizar_reclamacoes` no cliente em `api/client/ouvidoria_client.py`
- `registrar_resposta_tecnica` simplificado: não altera mais reclamações

**Sintomas observados no servidor remoto (VM Windows):**
1. `PATCH /ouvidorias/{ouvidoria_id}/reclamacoes` **NÃO aparece** no `/docs`
2. Clicar "💾 Salvar Edição" na página Responder retorna **API 404**
3. Clicar "📤 Enviar Resposta" **deleta todas as reclamações** da ouvidoria

---

## O que já foi verificado

| Verificação | Resultado |
|---|---|
| `git log --oneline -5` no servidor | ✅ `10c0bc0` está como HEAD |
| `Select-String "reclamacoes" api\routers\ouvidorias.py` | ✅ Linha 164 tem o endpoint |
| `Select-String "AtualizarReclamacoesRequest" api\schemas\ouvidoria.py` | ✅ Linha 195 tem a classe |
| `python -c "from api.routers.ouvidorias import router; print('OK')"` | ✅ Retornou OK |
| Limpeza de `__pycache__` e `.pyc` | ✅ Feito |
| Kill de todos processos uvicorn + reinício | ✅ Feito |
| Endpoint no `/docs` após tudo isso | ❌ Ainda não aparece |

**Havia dois processos uvicorn rodando simultâneos** (PIDs 10008 e 15312 + o exe 15980). Ambos foram encerrados e um novo foi iniciado — mesmo assim o endpoint não apareceu.

---

## Prompt para rodar no servidor (Claude Code)

```
Estou debugando um problema no servidor FastAPI desta aplicação (SIGO-SUCOL, sistema de ouvidorias ARTESP).
O servidor está rodando `uvicorn api.main:app --reload --host 0.0.0.0 --port 8000`
a partir de `C:\Projetos\sistema_de_ouvidoria`.

**Problema:** O endpoint `PATCH /ouvidorias/{ouvidoria_id}/reclamacoes` não aparece no `/docs`
do FastAPI em execução, apesar de existir no arquivo `api/routers/ouvidorias.py` (linha 164)
e o import manual funcionar (`python -c "from api.routers.ouvidorias import router; print('OK')`).

**O que preciso que você faça:**
1. Rode `(Invoke-WebRequest -Uri "http://localhost:8000/openapi.json").Content | Select-String "reclamacoes"`
   para confirmar se o endpoint está ou não no servidor ativo
2. Verifique se há algum erro no console do uvicorn (ou tente capturá-lo)
3. Investigue por que o endpoint não está sendo registrado no servidor em execução,
   mesmo estando no código
4. Corrija o problema — seja limpando cache, reiniciando o processo corretamente,
   ou ajustando o código se houver um bug sutil
5. Confirme que `PATCH /ouvidorias/{ouvidoria_id}/reclamacoes` aparece no `/docs` após a correção

O código local (`git log --oneline -1`) deve mostrar o commit `10c0bc0`.
```

---

## Hipóteses não descartadas

1. **Bug sutil no código do router**: FastAPI às vezes não registra rotas se houver um erro
   dentro de uma rota anterior que impeça o processamento do decorador seguinte.
   Verificar se há alguma exceção em tempo de decoração.

2. **Problema no `--reload` do uvicorn**: O watcher pode estar com uma versão antiga em memória.
   Tentar rodar **sem `--reload`** e ver se o endpoint aparece:
   ```
   uvicorn api.main:app --host 0.0.0.0 --port 8000
   ```

3. **Conflito de rota**: `PATCH /{ouvidoria_id}` pode estar mascarando `PATCH /{ouvidoria_id}/reclamacoes`
   em alguma versão do FastAPI/Starlette. Verificar versões instaladas:
   ```
   pip show fastapi starlette uvicorn
   ```

4. **Arquivo diferente carregado**: Confirmar que o uvicorn está no diretório correto:
   ```powershell
   Get-Location
   ```
   antes de iniciar.
