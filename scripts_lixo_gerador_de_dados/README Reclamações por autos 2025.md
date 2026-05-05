# Gerador de Relatórios de Reclamações por Autos

Script para gerar relatórios em Markdown com as pontuações de reclamações por auto de linha e subcategoria (assunto).

## Uso

```powershell
 .\relatorio_por_autos <auto1> [auto2] [auto3] ...
```

### Exemplos

Gerar relatório para um único auto:

```powershell
 .\relatorio_por_autos 9207A
```

Gera: `reclamacoes_por_autos_1.md`

Gerar relatório para múltiplos autos:

```powershell
 .\relatorio_por_autos 9207A 9208A 9209A
```

Gera: `reclamacoes_por_autos_3.md`

## O que o script faz

1. Consulta o banco de dados para cada auto informado
2. Busca todas as reclamações vinculadas ao auto no ano de 2025
3. Agrupa as reclamações por subcategoria (assunto)
4. Calcula a pontuação total por subcategoria
5. Gera um relatório em Markdown com:
   - Informações do auto (denominação A, B, tipo, status)
   - Total de pontos e reclamações
   - Tabela com distribuição por subcategoria (quantidade, pontos, percentual)
   - Resumo geral

## Saída

O relatório é salvo nesta pasta com o nome: `reclamacoes_por_autos_[n_autos].md`

Onde `[n_autos]` é o número de autos consultados.

## Estrutura do Relatório

O markdown gerado contém:

- **Cabeçalho:** Data de geração, período analisado, quantidade de autos
- **Por Auto:** Informações do auto, resumo e tabela de distribuição por subcategoria
- **Resumo Geral:** Totalizações de todos os autos analisados
