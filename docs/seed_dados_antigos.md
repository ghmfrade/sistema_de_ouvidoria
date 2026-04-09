Inserir dados antigos no sistema.

dados: dados_antigos_tratado_empresa_e_cidades.xlsx

Criar script python que efetue o seed dos dados antigos.

Preencher no sistema. Cada linha é uma ouvidoria. O sistema antigo, só registrava uma reclamação por ouvidoria, assim cada linha é uma ouvidoria com uma reclamaçao vinculada.

Protocolo da Ouvidoria: COLUNA PROTOCOLO
Conteúdo da Ouvidoria: COLUNA N° SEI (as vezes tem dado as vezes não, se nao tiver "SEM DADOS")
Não marcar resposta da Permissionária (não tem dados disso na tabela)
Não tem anexo.
Tipo de Serviço é encontrado com a combinação das colunas SISTEMA e SUBSISTEMA, SISTEMA diz se é intermunicipal ou metropolitano, SUBSISTEMA diz se é REGULAR ou FRETAMENTO.

SE Marcado REGULAR:
registrar a reclamação com categoria e subcategoria, a partir da coluna ASSUNTO (apenas se o assunto tiver preenchido, se nao tiver preenchido nao registra a ouvidoria) - obs.: O assunto é a subcategoria antiga, para registrar corretamente, deve cruzar o dado com a planilha CATEGORIA NOVA X CATEGORIA ANTIGA.xlsx em normalizacao_dados - Local de embarque e desembarque é para preencher os municipios que estão nas colunas ORIGEM_IBGE e DESTINO_IBGE. - Vincular os Autos que são da empresa da planilha (NOME DA EMPRESA BANCO) e atendem ao trecho (ORIGEM_IBGE e DESTINO_IBGE) (caso nao tenha nome da empresa, vincula a todos os autos que atendem ao trecho, caso nao tenha origem e destino, vincula a todos autos da empresa, não registra autos nenhum se não tiver ambos)
SE Marcado FRETAMENTO
registra reclamacao com categoria e subcategoria a partir da coluna assunto (apenas se o assunto tiver preenchido, se nao tiver preenchido nao registra a ouvidoria) - obs.: O assunto é a subcategoria antiga, para registrar corretamente, deve cruzar o dado com a planilha CATEGORIA NOVA X CATEGORIA ANTIGA.xlsx em normalizacao_dados - Local de embarque e desembarque é para preencher os municipios que estão nas colunas ORIGEM_IBGE e DESTINO_IBGE, se tiver vazio, registra apenas se tiver nome da empresa. - em fretamento nao se vincula Autos, entao, registra-se apenas o nome da empresa de fretamento (se nao tiver nome da empresa, não registra, exceto se for do assunto transporte irregular/clandestino, ai registra sem nome [mas se também nao tiver origem e destino, aí nao registra mesmo independente se for transporte clandestino]) (nome da empresa está no NOME DA EMPRESA BANCO)

DATA é a data de entrada da ouvidoria.
LIMITE R. é a data limite de resposta. (use para definir os prazos de resposta)
DATA R. é a data da resposta técnica da ouvidoria.
Pode concluir todas.
