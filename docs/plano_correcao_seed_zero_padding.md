# Plano: Correção do mismatch de zero-padding nos trechos de autos intermunicipais

## Contexto

O seed de trechos (`seed_trechos`) busca cada auto no `numero_map` usando o valor bruto da coluna `N_AUTOS` do CSV `trechos_intermunicipal.csv`. Esse CSV registra autos com número < 1000 com zero-padding de 4 dígitos (ex: `0395A`), enquanto o CSV de autos (`autos_intermunicipal_ativos.csv`) não usa padding — e portanto o banco armazena `395A`.

O lookup `numero_map.get("0395A")` falha silenciosamente; o trecho é contado em `sem_auto` e ignorado. Resultado: **47 autos** sem trechos associados no banco, apesar de existirem no CSV de trechos.

## Diagnóstico

| CSV | Formato do número | Exemplo |
|-----|-------------------|---------|
| `pasta_seed/autos_intermunicipal_ativos.csv` | sem padding | `395;A` → `"395A"` |
| `pasta_seed/trechos_intermunicipal.csv` | 4 dígitos zero-padded | `0395A` |
| banco (`autos_linha.numero`) | sem padding | `"395A"` |

## Impacto em cascata

O `seed_dados_antigos.py` usa `buscar_autos_por_trecho` e `buscar_autos_por_numero` (de `api/repositories/autos_repo.py`) para vincular reclamações a autos. Com os 47 autos sem trechos no banco, as buscas por trecho retornaram vazio para essas linhas — as ouvidorias históricas associadas a elas ficaram sem vínculo de auto (`ReclamacaoAuto`).

Por isso não basta só corrigir os trechos: o seed de dados antigos também precisa ser re-executado para que esses vínculos sejam criados corretamente.

## O que NÃO precisa ser feito manualmente

- **Nenhum SQL de limpeza manual** — `seed_dados_antigos.py` já chama `_limpar_ouvidorias()` no início de cada execução (linhas 169-175 do script), que executa `TRUNCATE TABLE ouvidorias CASCADE`, limpando todas as tabelas filhas automaticamente.
- **Não apagar os autos do banco** — `seed_autos_intermunicipal.py` é idempotente: se o auto já existe, apenas atualiza o campo `tc` e segue. Não duplica.

## Como funciona a idempotência do seed de autos

O script tem duas fases, cada uma com verificação antes de inserir:

**Fase 1 — Autos** (`seed_autos_intermunicipal.py`, linhas 86-93):
```python
existente = session.query(AutoLinha).filter_by(
    numero=numero, tipo=TipoServico.REGULAR_INTERMUNICIPAL
).first()
if existente:
    existente.tc = tc_val  # só atualiza tc
    numero_map[numero] = existente.id
    atualizados += 1
    continue  # não insere novamente
```

**Fase 2 — Trechos** (`seed_autos_intermunicipal.py`, linhas 171-176):
```python
existe = session.query(TrechoAutoLinha).filter_by(
    auto_id=auto_id, municipio_a_id=min_id, municipio_b_id=max_id
).first()
if existe:
    conflito += 1
    continue  # não insere novamente
```

Ao re-rodar após a correção: todos os autos já existem (só atualiza `tc`), trechos já existentes são pulados, e os **47 trechos novos** — que antes falhavam por causa do zero-padding — serão inseridos pela primeira vez.

---

## Passo 1 — Aplicar a correção no script

**Arquivo:** `api/database/seed_autos_intermunicipal.py`, **linha 145**

**Antes:**
```python
n_autos   = str(row["N_AUTOS"]).strip()
```

**Depois:**
```python
n_autos_raw = str(row["N_AUTOS"]).strip()
# Normaliza "0395A" → "395A" para coincidir com o formato armazenado no banco.
m = re.match(r'^(\d+)([A-Za-z]*)$', n_autos_raw)
n_autos = (str(int(m.group(1))) + m.group(2)) if m else n_autos_raw
```

`re` já está importado na linha 17 do arquivo. A lógica extrai a parte numérica, converte para `int` (remove zeros à esquerda) e reconstrói o número — espelhando exatamente o que `seed_autos` faz ao construir `numero = num_raw + iti` na linha 73.

---

## Passo 2 — Re-rodar o seed de autos/trechos

```
python api/database/seed_autos_intermunicipal.py
```

**O que vai acontecer:**
- Autos já existentes: apenas atualizam o campo `tc` (sem duplicar)
- Trechos já existentes: pulados silenciosamente (sem duplicar)
- Os 47 trechos que falhavam por zero-padding: **serão inseridos agora**

**Verificar no output:** o contador `sem_auto` deve cair de ~47 para próximo de 0.

---

## Verificação após Passo 2 — confirmar trechos antes de continuar

**NÃO prosseguir para o Passo 3 sem antes confirmar que os trechos foram inseridos corretamente.**

```sql
-- 1. Quantos autos intermunicipais ainda estão sem trechos (deve ser ~0)
SELECT COUNT(*) FROM autos_linha a
WHERE a.tipo = 'Regular – Intermunicipal'
  AND NOT EXISTS (SELECT 1 FROM trechos_auto_linha t WHERE t.auto_id = a.id);

-- 2. Confirmar um caso concreto: 395A deve ter trechos agora
SELECT a.numero, ma.nome AS cidade_a, mb.nome AS cidade_b
FROM trechos_auto_linha t
JOIN autos_linha a  ON a.id = t.auto_id
JOIN municipios ma  ON ma.id = t.municipio_a_id
JOIN municipios mb  ON mb.id = t.municipio_b_id
WHERE a.numero = '395A';
-- Esperado: pelo menos Cabreúva↔Itu, Cabreúva↔Jundiaí, Itu↔Jundiaí
```

Se o COUNT ainda for > 0 ou `395A` não retornar linhas, **parar e investigar** antes de continuar — o Passo 3 vai usar esses trechos para vincular ouvidorias.

---

## Passo 3 — Re-rodar o seed de dados antigos

```
python api/database/seed_dados_antigos.py
```

**O que vai acontecer:**
1. O script automaticamente trunca todas as ouvidorias existentes (`TRUNCATE ouvidorias CASCADE`) — não precisa de SQL manual
2. Lê os dados de `pasta_seed/dados_antigos_tratado_empresa_e_cidades.csv`
3. Carrega o mapeamento de categorias de `normalizacao_dados/CATEGORIA NOVA X CATEGORIA ANTIGA.xlsx`
4. Para cada linha, tenta vincular a autos via `buscar_autos_por_numero` e `buscar_autos_por_trecho` — agora com os trechos completos no banco, os 47 autos antes ignorados serão vinculados corretamente
5. Gera dois relatórios na raiz do projeto: `seed_lancados.xlsx` e `seed_nao_lancados.xlsx`

---

## Verificação após Passo 3 — confirmar que os dados antigos encontraram os novos autos

```sql
-- 1. Total de ouvidorias inseridas (comparar com total de linhas do CSV menos as puladas)
SELECT COUNT(*) FROM ouvidorias;

-- 2. Total de vínculos ReclamacaoAuto criados (quanto maior, melhor — indica que os autos foram encontrados)
SELECT COUNT(*) FROM reclamacoes_autos;

-- 3. Verificar se autos que antes eram "fantasmas" agora têm reclamações vinculadas
--    (substituir '395A' por outros números dos 47 autos afetados para checar mais casos)
SELECT a.numero, COUNT(ra.id) AS total_reclamacoes
FROM autos_linha a
LEFT JOIN reclamacoes_autos ra ON ra.auto_id = a.id
WHERE a.tipo = 'Regular – Intermunicipal'
  AND EXISTS (SELECT 1 FROM trechos_auto_linha t WHERE t.auto_id = a.id)
GROUP BY a.numero
ORDER BY total_reclamacoes DESC
LIMIT 20;

-- 4. Verificar especificamente o 395A
SELECT a.numero, COUNT(ra.id) AS total_reclamacoes
FROM autos_linha a
LEFT JOIN reclamacoes_autos ra ON ra.auto_id = a.id
WHERE a.numero = '395A'
GROUP BY a.numero;
```

O indicador principal da correção é o **total de vínculos em `reclamacoes_autos`**: deve ser maior do que na execução anterior, pois os 47 autos que antes não tinham trechos agora serão encontrados pelo `buscar_autos_por_trecho` e seus vínculos serão criados.

---

## Resumo dos arquivos envolvidos

| Arquivo | Papel |
|---------|-------|
| `api/database/seed_autos_intermunicipal.py` | **Corrigir linha 145** — única alteração de código |
| `pasta_seed/trechos_intermunicipal.csv` | Fonte dos trechos (tem zero-padding, não alterar) |
| `pasta_seed/autos_intermunicipal_ativos.csv` | Fonte dos autos (sem padding, não alterar) |
| `pasta_seed/dados_antigos_tratado_empresa_e_cidades.csv` | Fonte dos dados históricos de ouvidoria |
| `normalizacao_dados/CATEGORIA NOVA X CATEGORIA ANTIGA.xlsx` | Mapeamento assunto → subcategoria |
| `api/database/seed_dados_antigos.py` | Re-executar após corrigir trechos (sem alterações) |
