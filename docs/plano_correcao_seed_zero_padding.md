# Plano: Correção do mismatch de zero-padding nos trechos de autos intermunicipais

## Contexto

O seed de trechos (`seed_trechos`) busca cada auto no `numero_map` usando o valor bruto da coluna `N_AUTOS` do CSV `trechos_intermunicipal.csv`. Esse CSV registra autos com número < 1000 com zero-padding de 4 dígitos (ex: `0395A`), enquanto o CSV de autos (`autos_intermunicipal_ativos.csv`) não usa padding — e portanto o banco armazena `395A`.

O lookup `numero_map.get("0395A")` falha silenciosamente; o trecho é contado em `sem_auto` e ignorado. Resultado: **47 autos** sem trechos associados no banco, apesar de existirem no CSV de trechos.

O seed é idempotente (verifica `TrechoAutoLinha` existente antes de inserir), então re-executá-lo após a correção é suficiente.

## Diagnóstico

| CSV | Formato do número | Exemplo |
|-----|-------------------|---------|
| `pasta_seed/autos_intermunicipal_ativos.csv` | sem padding | `395;A` → `"395A"` |
| `pasta_seed/trechos_intermunicipal.csv` | 4 dígitos zero-padded | `0395A` |
| banco (`autos_linha.numero`) | sem padding | `"395A"` |

## Correção — 1 linha modificada

**Arquivo:** `api/database/seed_autos_intermunicipal.py`

**Antes (linha 145):**
```python
n_autos = str(row["N_AUTOS"]).strip()
```

**Depois:**
```python
n_autos_raw = str(row["N_AUTOS"]).strip()
# Normaliza "0395A" → "395A" para coincidir com o formato armazenado no banco.
m = re.match(r'^(\d+)([A-Za-z]*)$', n_autos_raw)
n_autos = (str(int(m.group(1))) + m.group(2)) if m else n_autos_raw
```

`re` já está importado no arquivo (linha 17). A lógica extrai a parte numérica, converte para `int` (removendo zeros à esquerda) e reconstrói o número — espelhando exatamente o que `seed_autos` faz com `num_raw + iti` (linha 73).

## Passos de execução

1. Editar `api/database/seed_autos_intermunicipal.py` — substituir linha 145 conforme acima.
2. Re-executar o seed individualmente (não precisa rodar `seed_all.py` inteiro):
   ```
   python api/database/seed_autos_intermunicipal.py
   ```
3. Verificar output esperado: `sem_auto` deve cair de ~47 para próximo de 0.

## Verificação pós-execução

```sql
-- Confirmar que 395A agora tem trechos
SELECT a.numero, ma.nome, mb.nome
FROM trechos_auto_linha t
JOIN autos_linha a ON a.id = t.auto_id
JOIN municipios ma ON ma.id = t.municipio_a_id
JOIN municipios mb ON mb.id = t.municipio_b_id
WHERE a.numero = '395A';
-- Esperado: Cabreúva↔Itu, Cabreúva↔Jundiaí, Itu↔Jundiaí

-- Verificar quantos autos ainda ficam sem trechos (deve ser perto de 0)
SELECT COUNT(*) FROM autos_linha a
WHERE a.tipo = 'Regular – Intermunicipal'
  AND NOT EXISTS (SELECT 1 FROM trechos_auto_linha t WHERE t.auto_id = a.id);
```

## Arquivos modificados

- `api/database/seed_autos_intermunicipal.py` — única mudança necessária
