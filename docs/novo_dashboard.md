Vamos substituir o atual dashboard de qualidade por um novo dashboard.
A aba do antigo dashboard terá apenas um botão que acessa ao link do DASHBOARD que estará rodando em DASH.

Frotend desse novo dashboard será em DASH e ele deve consultar os dados por meio da api.
Aproveitar na medida do possivel os atuais endpoints do dashboard.
Possivelmente, precisará criar novos endpoints e portanto também novos repositorios.
Aquele endpoint e codigo do repositorio que deixar de ser usado (que era usado no antigo dashboard) deve ser removido.

Crie um painel administrativo de visualização de reclamações de sistemas de transporte público com três abas:

## Estrutura Geral

- Header fixo no topo com título "Painel de Reclamações - Sistema de Transporte"
- Sistema de abas com três opções:
  1. "Sistema Regular Metropolitano" (ícone de ônibus) (dados do sistema regular metropolitano)
  2. "Sistema Regular Intermunicipal" (ícone de mapa) (dados do sistema regular intermunicipal)
  3. "Fretamento" (ícone de pessoas) (dados de ambos os sistemas de fretamento - intermunicipal e metropolitano)
- Cada aba deve ter visual distinto quando ativa (azul) vs inativa (cinza claro)
- Fundo geral em cinza claro, cards em branco com sombras suaves
- Deve funcionar para telas de pc wide e também ficar em telas de celular em pé.

## Filtros (presentes em todas as abas, no topo)

As reclamações utilizadas serão as categorizadas como RECLAMAÇÃO.

- **Filtro de Ano**: dropdown/select mostrando anos com dados disponíveis, valor o ano mais recente
- **Filtro de Meses**: dropdown/select multi-seleção com:
  - Opções: "Todos os meses", "Nenhum mês", e cada mês individualmente (meses com dados disponiveis no ano escolhido)
  - Exibir quantos meses estão selecionados quando não for "todos" ou "nenhum"
  - Permitir marcar/desmarcar meses individualmente dentro do dropdown
  - Valor padrão: selecionado todos os meses disponiveis no ano selecionado
- Filtros devem estar lado a lado em um card branco com sombra

## Aba 1 e 2: Sistemas Regulares (Metropolitano e Intermunicipal)

### Cards de Resumo (2 cards lado a lado)

Reclamações categorizadas como RECLAMAÇÃO e filtradas conforme #Filtros. Todas subcategorias consideradas.

- **Card 1** (fundo azul claro):
  - Título: "Total de Reclamações"
  - Valor grande em azul
- **Card 2** (fundo laranja claro):
  - Título: "Assunto Mais Reclamado"
  - Nome do assunto em destaque (laranja)
  - Quantidade de ocorrências abaixo em texto menor

### Gráfico 1: Evolução Mensal das Reclamações

Reclamações categorizadas como RECLAMAÇÃO e filtradas conforme #Filtros. Todas subcategorias consideradas.

- Gráfico de linha com curva suave
- Eixo X: meses (Jan, Fev, Mar, etc.)
- Eixo Y: quantidade de reclamações
- Linha azul com pontos marcados
- Grade de fundo tracejada
- Legenda

### Gráfico 2: Reclamações por Assunto

Reclamações categorizadas como RECLAMAÇÃO e filtradas conforme #Filtros. Todas subcategorias consideradas.

- Gráfico de pizza/setores
- Cada fatia com cor diferente
- Labels mostrando: "Nome do Assunto (Subcategorias): Quantidade"
- Tooltip ao passar mouse mostrando: quantidade de reclamações e nome do assunto
- Legenda ao lado direito (se a tela permitir, abaixo se a tela for de celular)

### Gráfico 3: Empresas por Pontuação de Reclamação

Pontuação de reclamações por empresa, considerando dados de Reclamações categorizadas como RECLAMAÇÃO e filtradas conforme #Filtros.
Todas subcategorias **exceto** TRANSPORTE IRREGULAR / CLANDESTINO.

- Gráfico de barras horizontal
- Empresas do serviço da aba (metropolitano ou intermunicipal) ordenadas da maior para menor pontuação
- Barras em vermelho
- Tooltip ao passar mouse mostrando:
  - Nome da empresa
  - Pontuação total
  - Linha mais reclamada
  - Assunto mais reclamado

### Gráfico 4: Incidência de Transporte Irregular por Empresa

Pontuação de reclamações da subcategoria TRANSPORTE IRREGULAR por empresa considerando os #Filtros

- Gráfico de barras horizontal
- Empresas do serviço da aba (metropolitano ou intermunicipal) ordenadas da maior para menor considerando a pontuação de insidência (pontuação da subcategoria TRANSPORTE IRREGULAR)
- Barras em vermelho
- Tooltip ao passar mouse mostrando:
  - Nome da empresa
  - Pontuação de Insidência
  - Linha mais prejudicada

### Gráfico 5: Mapa de Calor - Pontuação por Assunto x Empresa

Pontuação de reclamações por assunto por empresa, considerando as reclamacoes categorizadas como RECLAMAÇÃO e filtradas conforme #Filtros. Todas subcategorias **exceto** TRANSPORTE IRREGULAR / CLANDESTINO.

- **Layout**:
  - Empresas no eixo X
  - Assuntos no eixo Y
  - Empresas inclinados em -45°
  - Visual moderno e limpo
  - Quadrados colados, sem aparência de tabela
  - Mostrar valor dentro de cada célula
- **Cores**:  
   Usar escala suave e pouco saturada: - Verde claro suave → baixa pontuação - Amarelo suave → média-baixa - Laranja suave → média-alta - Vermelho suave → alta pontuação
  As cores devem ser visualmente leves e elegantes, evitando tons muito fortes ou “chapados”.
- **Interação**:
  Tooltip ao passar mouse: - Empresa - Assunto - Pontuação total - Linha mais reclamada - Pontuação da linha
  Adicionar leve destaque visual no hover, compatível com Plotly/Dash, sem JavaScript complexo.
- **Paginação**:
  - 10 empresas por página (Mais pontuação de reclamação para menos)
  - Botões anterior/próxima
  - Indicador “Página X de Y”
- **Assuntos** (Assuntos são as subcategorias da categoria Reclamação):
  - Mostrar apenas os assuntos que tiverem alguma pontuação #FILTRO considerado.

### Gráfico 6: Autos por Pontuação

Considerar #Filtros, **exceto** TRANSPORTE IRREGULAR / CLANDESTINO

- Gráfico de barras horizontal
- Autos ordenados do maior para menor pontuação
- Barras em azul
- Tooltip ao passar mouse mostrando:
  - Nome do auto
  - Pontuação
  - Principal assunto
- **Paginação**:
  - Mostrar 15 autos por vez
  - Botões de navegação (anterior/próxima)
  - Indicador "Página X de Y"

### Gráfico 7: Autos por Incidência de Transporte Irregular

Pontuação de reclamações da subcategoria TRANSPORTE IRREGULAR por autos considerando os #Filtros

- Gráfico de barras horizontal
- Autos ordenados do maior para menor Pontuação de Insidência
- Barras em azul
- Tooltip ao passar mouse mostrando:
  - Nome do auto
  - Pontuação de Insidência
- **Paginação**:
  - Mostrar 15 autos por vez (mais incidencia para menos)
  - Botões de navegação (anterior/próxima)
  - Indicador "Página X de Y"

### Gráfico 8: Mapa de Calor - Pontuação por Assunto x Autos

- **Filtro de Empresas**: dropdown/select multi-seleção com:
  - Opções: "Todos as empresas", "Nenhuma empresa", e cada empresa individualmente (empresas do sistema da aba [metropolitano ou intermunicipal])
  - Exibir empresa selecionada, caso seja mais de uma, exibir X empresas selecionadas
  - Permitir marcar/desmarcar meses individualmente dentro do dropdown
  - Valor padrão: selecionado todas empresas
  - Em card de sombra semelhante ao filtro inicial
  - Aplica-se apenas a este gráfico

Pontuação de reclamações por assunto por Autos, considerando as reclamacoes categorizadas como RECLAMAÇÃO e filtradas conforme #Filtros. Todas subcategorias **exceto** TRANSPORTE IRREGULAR / CLANDESTINO.

- **Layout**:
  - Autos de linha no eixo X
  - Assuntos no eixo Y
  - Assuntos inclinados em -45°
  - Visual moderno e limpo
  - Quadrados colados, sem aparência de tabela
  - Mostrar valor dentro de cada célula
- **Cores**:  
   Usar escala suave e pouco saturada: - Verde claro suave → baixa pontuação - Amarelo suave → média-baixa - Laranja suave → média-alta - Vermelho suave → alta pontuação
  As cores devem ser visualmente leves e elegantes, evitando tons muito fortes ou “chapados”.
- **Interação**:
  Tooltip ao passar mouse: - Empresa do Autos - N° do Autos - Cidade Origem - Cidade Destino - Assunto - Pontuação
  Adicionar leve destaque visual no hover, compatível com Plotly/Dash, sem JavaScript complexo.
- **Paginação**:
  - 10 Autos por página (Mais pontuação de reclamação para menos)
  - Botões anterior/próxima
  - Indicador “Página X de Y”
- **Assuntos** (Assuntos são as subcategorias da categoria Reclamação):
  - Mostrar apenas os assuntos que tiverem alguma pontuação #FILTRO considerado.

## Aba 3: Fretamento

### Cards de Resumo (2 cards lado a lado)

- **Card 1** (fundo roxo claro):
  - Título: "Total de Reclamações"
  - Valor grande em roxo
- **Card 2** (fundo laranja claro):
  - Título: "Assunto Mais Reclamado"
  - Nome do assunto em destaque (laranja)
  - Quantidade de ocorrências abaixo em texto menor

### Gráfico 1: Reclamações por Assunto

- Gráfico de pizza/setores
- Cada fatia com cor diferente
- Labels mostrando: "Nome do Assunto: Porcentagem%"
- Tooltip ao passar mouse mostrando: quantidade de reclamações, porcentagem e nome do assunto
- Legenda

### Gráfico 2: Locais de Embarque Mais Reclamados

- Gráfico de barras horizontal
- Locais ordenados do maior para menor pontuação
- Barras em azul
- Tooltip ao passar mouse mostrando:
  - Nome do local
  - Pontuação
  - Assunto mais reclamado (Principal Assunto)
- **Paginação**:
  - Mostrar 15 locais por vez
  - Botões de navegação (anterior/próxima)
  - Indicador "Página X de Y"

## Comportamento dos Filtros

- Quando meses são desmarcados, os valores nos gráficos devem diminuir proporcionalmente
- Quando nenhum mês está selecionado, todos os valores devem ser zero
- Mudança de ano ou meses deve atualizar todos os gráficos simultaneamente
- Filtros são independentes por aba (mudar em uma aba não afeta as outras)

## Dados

- Use API para integrar-se ao banco.

## Estilo Visual

- Design limpo e profissional
- Cards brancos com sombras suaves sobre fundo cinza claro
- Espaçamento generoso entre elementos
- Cores vibrantes mas não excessivas
- Responsivo quando possível
- Tooltips com fundo escuro e texto branco
- Transições suaves em hovers e mudanças de aba
