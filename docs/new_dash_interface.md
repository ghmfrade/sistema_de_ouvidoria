Vamos fazer mais uma grande alteração de interface.
A ideia é apresentar tudo na mesma tela, sem a necessidade de scrol.

margem lateral reduzida para quase nada, quase uma borda
-- Painel de Reclamações - Sistema de Gestão de Ouvidorias (SIGO) titulo no inicio, mesmas cores que ja estão. 
-- Faixa de filtragem da forma como está. Porém mais apertada e pressionada proximo da faixa azul.

[total de reclamacoes (1)][assunto mais reclamado (2)][Local de embarque crítico (3)] [Empresa mais reclamada (4)] [Empresa mais Vulnerável (5)][Autos mais reclamado (6)][Autos mais Vulnerável (7)][Botão mapa de calor por empresa (8)][Mapa de calor por Autos (9)] -> cada um desses serão containers com os dados descritos, porém, também serão botões que ao clicarem, mostrarão os dados daquele tema num gráfico.
/n
[Gráfico que se alterará de acordo com a escolha do usuario]

Observações e descrições dos botoes/containers
(1) Esse containter deve conter exatamente os mesmos dados do atual Total de Reclamações e deve ser um botão, que ao ser clicado, abre no gráfico abaixo a Evolução Mensal das Reclamações, com os filtros marcados pela faixa de filtragem, exatamente como já funciona hoje. (nesse modelo não será mais necessário os subtitulos, apenas o titulo, já que o filtro estará próximo) (os dados do container devem considerar os filtros, como já funciona hoje)
(2) Esse container deve conter o assunto mais reclamado, com a mesma aparencia Mas o titulo provavelmente terá que receber uma quebra no meio e terá de ter letra menor, para caber num container mais fino. Além disso, ele deve ser um botão que altera o gráfico abaixo para o gráfico de Reclamação por Assunto (pizza). Ele deve aceitar exatamente os mesmos filtros e manter as mesmas funcionalidades, especialmente quanto ao destaque de assunto (quando escolhido apenas um). (os dados do container deve considerar os filtros, como já funciona hoje)
(3) Mostrar a cidade com embarque mais crítico (considerando os filtros). Deve ser um botão que carrega o gráfico Locais de embarque/desembarque mais reclamados. Remover subtitulo do mapa, mas manter todas regras de filtro e manter botao de escolha de embarque e desembarque. (ao escolher desembarque, alterar dado do container, alterando para Desembarque mais crítico)
(4) Mostra a empresa com mais reclamacão e sua pontuação (caso não seja filtrado a empresa.) Se filtrado a empresa, mostra a empresa filtrada escolhida e sua pontauçaõ. Caso filtrado varias, mostra a com maior pontuação de reclamacao da lista escolhida. Fazer ser um botão que ao ser clicado, abre o gráfico de Incidência de Reclamação do Serviço, com o mesmo comportamento frente aos filtros e seleção (com cor azul) da empresa filtrada.
(5) Mostra empresa mais vulneravel e sua pontuaçãod e vulnerabilidade (valor é o usado no grafico indicador de vulnerabilidade (caso com maior pontuacao)). Se filtrado a empresa, mostra a empresa filtrada escolhida e sua pontauçaõ. Caso filtrado varias, mostra a com maior pontuação de reclamacao da lista escolhida. Fazer ser um botão que ao ser clicado, abre o gráfico de Indicador de Vulnerabilidade a transporte irregular por empresa, com o mesmo comportamento frente aos filtros e seleção (com cor azul) da empresa filtrada.
(6) MOstra o Autos mais reclamado, sua empresa e regiao, e pontuação. Ao clicar (mostra Incidencia de reclamação do serviço publico por Autos de linha)
(7) Mostra autos mais vulneravel. Mesma logica do 6, mas com dados do Autos por Vulnerabilidade ao Transporte Irregular.
(8) Apenas um botão par aabrir o mapa de calor por empresa. Que já abre filtrado com os filtros gerais. Mantem as mesmas regras de filtro e seleção do atual mapa (regrs de destacar as empresas escolhidas e etc)
(9) Botão para abrir mapa de calor por Autos. Manter mesmas regras de filtragem do atual mapa.
 
