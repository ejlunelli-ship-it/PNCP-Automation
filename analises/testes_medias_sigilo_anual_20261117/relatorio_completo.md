**Testes de médias por sigilo do orçamento, com controle anual — 17/11/2026**

Os testes foram refeitos separando orçamento não sigiloso (flag 0) e sigiloso (flag 1), usando ANO no lugar de mês em todos os estratos de comparação e nas medianas de referência. São testes de associação entre modos dentro de cada grupo de sigilo, não estimativas causais do modo ou do sigilo.

**Fonte e preservação da amostra.** Reutilizada a extração íntegra de `PNCP-Automation/dados/pncp.db` dos testes imediatamente anteriores, conferida por hashes e metadados; 305 registros foram novamente conferidos diretamente no SQLite, incluindo flag de sigilo, preços, estimados e extremos. Não é uma nova coleta. Mantidos pregão eletrônico, material, Homologado, Menor preço, A/AF, coorte madura, produto/apresentação e recorrência. O filtro de recorrência herdado conta compras em meses distintos, mas não há controle mensal nos testes. Classes principais: 6505/7510/7530/7930/8540; outras classes na sensibilidade ampliada. Fonte Dados Abertos/Compras.gov.br, não todas as plataformas PNCP.

**Classificação e disponibilidade do estimado.** Houve 0 itens de sigilo desconhecido na população recorrente. Há 870 pregões com itens nas duas classificações no recorte ampliado; a separação é por item. Isso não autoriza inferir uma política uniforme de sigilo por pregão.

| Orçamento | Modo | Itens prioritários antes do suporte | R positivo/finito | Cobertura de R |
|---|---|---|---|---|
| Não sigiloso | A | 99.841 | 99.841 | 100,00% |
| Não sigiloso | AF | 64.055 | 64.055 | 100,00% |
| Sigiloso | A | 52.245 | 50.659 | 96,96% |
| Sigiloso | AF | 33.214 | 32.442 | 97,68% |

O desconto dos sigilosos utiliza os estimados positivos disponíveis no snapshot, diferentemente da execução anterior que exigia sigilo falso. Não foi imputado preço estimado. A flag e o valor observado não comprovam quando o orçamento se tornou público nem se o estimado foi revisado depois da disputa.

**Comparação e inferência.** Dentro de cada grupo, médias padronizadas para a mesma composição de produto×ano×UF, com peso igual por estrato e por modo dentro do estrato. Produto=CATMAT+unidade/apresentação+PDM+descrição resumida. Teste bilateral equivalente à regressão ponderada com interceptos de estrato e AF, erros robustos com agrupamentos CNPJ/CATMAT, correção finita e distribuição t. Não se exige normalidade ou variâncias iguais entre itens; a confiabilidade depende do número e da informação dos grupos. A multiplicidade principal é Holm nos SEIS testes; a planilha também inclui Holm por trio. ICs são individuais.

| Orçamento | Desfecho | Itens A | Itens AF | Total | Pregões | Órgãos | Estratos anuais |
|---|---|---|---|---|---|---|---|
| Não sigiloso | Log do preço | 46.044 | 29.886 | 75.930 | 8.252 | 534 | 15.552 |
| Não sigiloso | Desconto (%) | 46.044 | 29.886 | 75.930 | 8.252 | 534 | 15.552 |
| Não sigiloso | Preço/mediana anual | 26.078 | 13.893 | 39.971 | 4.711 | 367 | 4.673 |
| Sigiloso | Log do preço | 18.033 | 15.392 | 33.425 | 6.930 | 105 | 7.654 |
| Sigiloso | Desconto (%) | 17.791 | 15.105 | 32.896 | 6.881 | 105 | 7.474 |
| Sigiloso | Preço/mediana anual | 9.993 | 6.939 | 16.932 | 4.130 | 98 | 2.856 |

**Resultados: orçamento não sigiloso.**

| Desfecho | Média A | Média AF | Diferença AF−A | IC95% | p nominal | p Holm seis | Signif. 5% |
|---|---|---|---|---|---|---|---|
| Log do preço | 0,8527 | 0,7614 | -0,0913 log | [-0,1506; -0,0319] | 0,0026 | 0,0158 | Sim |
| Desconto (%) | 32,04 | 35,32 | 3,29 p.p. | [1,12; 5,46] | 0,0031 | 0,0158 | Sim |
| Preço/mediana anual | 362,18 | 86,30 | -275,88 indice | [-686,68; 134,93] | 0,1875 | 0,7174 | Não |

Para preço, Δlog=-0,09127, EP=0,03021, t=-3,022, gl=533. A transformação 100×[exp(Δ)−1] resulta em **-8,72%**, IC95% [-13,98; -3,14].

**Resultados: orçamento sigiloso.**

| Desfecho | Média A | Média AF | Diferença AF−A | IC95% | p nominal | p Holm seis | Signif. 5% |
|---|---|---|---|---|---|---|---|
| Log do preço | 1,0962 | 1,0614 | -0,0349 log | [-0,0860; 0,0163] | 0,1793 | 0,7174 | Não |
| Desconto (%) | 30,67 | 32,36 | 1,69 p.p. | [-1,38; 4,77] | 0,2770 | 0,7174 | Não |
| Preço/mediana anual | 6,16 | 935,03 | 928,87 indice | [-1.147,31; 3.005,05] | 0,3768 | 0,7174 | Não |

Para preço, Δlog=-0,03486, EP=0,02579, t=-1,352, gl=104. A transformação 100×[exp(Δ)−1] resulta em **-3,43%**, IC95% [-8,24; 1,64].

O desconto é apresentado em %, com diferença em pontos percentuais; o índice P/M está em nível, e sua diferença não é percentual. Os estratos e produtos dos dois grupos podem diferir. **Significância em um grupo e ausência dela no outro não constituem teste de diferença entre grupos.** Não foi estimado um efeito causal da interação modo×sigilo.

**Referência anual e valores extremos.** M é a mediana das medianas por pregão no mesmo produto/ano/UF, fora de TODO o CNPJ-alvo, com pelo menos cinco pregões de dois outros CNPJs. Doadores incluem A/AF e os dois grupos de sigilo conhecidos para manter referência comum. É benchmark de compras públicas, não preço externo certificado de mercado, e pode conter compras posteriores à licitação dentro do ano. A inferência analítica do índice é condicional à referência; o bootstrap a recalcula.

| Sigilo | ID do item | CATMAT | Preço P | Mediana M | P/M | Unidade registrada | Quantidade |
|---|---|---|---|---|---|---|---|
| Não | 2713629 | 267778 | 134.274,70 | 0,0546 | 2.459.243,59 | Comprimido | 1 |
| Sim | 590525 | 267512 | 160.000,00 | 0,0600 | 2.666.666,67 | Comprimido | 1 |

Os valores extremos foram confirmados no cadastro SQLite. Isso não certifica que o preço e a unidade física sejam comparáveis: pode haver globalização de quantidades, apresentação efetiva diferente, registro inadequado ou outra condição. Não foi atribuído diagnóstico sem documento e não houve exclusão por magnitude. As médias do índice estão dominadas pelas caudas, e seus sinais opostos entre grupos não sustentam conclusão de superioridade de um modo. Auditoria e análise de influência estão anexadas.

**Bootstrap complementar.** 1.999 sorteios de órgãos, comuns aos dois grupos. Recalculados médias e benchmarks de C; referências com suporte insuficiente e estratos sem ambos os modos ficam ausentes na replicação. Essa renormalização muda a composição: o bootstrap é diagnóstico complementar.

| Sigilo | Desfecho | p bootstrap | p Holm seis bootstrap | IC95 básico | Estratos retidos em média |
|---|---|---|---|---|---|
| Não sigiloso | Log do preço | 0,0740 | 0,3700 | [-0,1344; 0,0078] | 59,80% |
| Não sigiloso | Desconto (%) | 0,0030 | 0,0180 | [1,46; 6,57] | 59,80% |
| Não sigiloso | Preço/mediana anual | 0,2810 | 1,0000 | [-827,10; 322,94] | 48,36% |
| Sigiloso | Log do preço | 0,2690 | 1,0000 | [-0,0925; 0,0155] | 59,86% |
| Sigiloso | Desconto (%) | 0,3550 | 1,0000 | [-2,53; 4,76] | 59,83% |
| Sigiloso | Preço/mediana anual | 0,5490 | 1,0000 | [-1.853,44; 1.869,50] | 44,93% |

**Distribuições e concentração.** DP, quantis, assimetria/curtose e médias brutas constam na planilha. Para log do preço, a participação dos dez maiores órgãos nos pesos AF é 59,04% no grupo não sigiloso e 81,07% no sigiloso. Contagem elevada de itens não equivale a muitas decisões independentes. O teste robusto não corrige erro de mensuração ou falta de comparabilidade física.

No principal não sigiloso, o bootstrap apresenta p ajustado de 0,3700 para log do preço e 0,0180 para desconto. Assim, a conclusão de significância do preço é sensível ao procedimento de inferência, enquanto o desconto é corroborado nessa verificação. A perda de estratos do bootstrap continua relevante e impede tratá-lo como solução definitiva.

**Sensibilidades anuais, todas registradas.** Condições de compra adiciona SRP, benefício e faixa de quantidade fator dois. Ampliado usa todas as classes. Amostra comum exige elegibilidade simultânea para os três desfechos dentro de cada sigilo. Winsor altera o desfecho pelos quantis 1/99 dentro de produto/grupo, sem substituir o principal; no seu bootstrap, referência e limites ficam fixados. Os valores-p dessas famílias são exploratórios, com Holm em seis testes por família.

| Análise | Itens A/AF | Órgãos | Diferença | IC95% | p Holm seis |
|---|---|---|---|---|---|
| principal_s0_A | 46.044/29.886 | 534 | -8,72 % geom. | [-13,98; -3,14] | 0,0158 |
| principal_s0_B | 46.044/29.886 | 534 | 3,29 p.p. | [1,12; 5,46] | 0,0158 |
| principal_s0_C | 26.078/13.893 | 367 | -275,88 indice | [-686,68; 134,93] | 0,7174 |
| principal_s1_A | 18.033/15.392 | 105 | -3,43 % geom. | [-8,24; 1,64] | 0,7174 |
| principal_s1_B | 17.791/15.105 | 105 | 1,69 p.p. | [-1,38; 4,77] | 0,7174 |
| principal_s1_C | 9.993/6.939 | 98 | 928,87 indice | [-1.147,31; 3.005,05] | 0,7174 |
| condicoes_compra_s0_A | 6.637/5.981 | 298 | -5,97 % geom. | [-8,23; -3,65] | <0,0001 |
| condicoes_compra_s0_B | 6.637/5.981 | 298 | 4,27 p.p. | [1,45; 7,09] | 0,0126 |
| condicoes_compra_s0_C | 4.342/3.783 | 223 | -0,10 indice | [-0,28; 0,09] | 0,3548 |
| condicoes_compra_s1_A | 2.830/2.847 | 57 | -4,87 % geom. | [-6,31; -3,42] | <0,0001 |
| condicoes_compra_s1_B | 2.782/2.796 | 57 | 3,19 p.p. | [-0,71; 7,09] | 0,3195 |
| condicoes_compra_s1_C | 1.540/1.444 | 51 | -0,40 indice | [-1,00; 0,19] | 0,3548 |
| ampliado_s0_A | 255.575/159.106 | 1.170 | -6,96 % geom. | [-9,04; -4,84] | <0,0001 |
| ampliado_s0_B | 255.571/159.105 | 1.170 | 4,83 p.p. | [3,48; 6,18] | <0,0001 |
| ampliado_s0_C | 121.738/53.614 | 1.006 | -111,88 indice | [-252,99; 29,22] | 0,2401 |
| ampliado_s1_A | 57.575/38.200 | 250 | -10,23 % geom. | [-17,93; -1,80] | 0,0558 |
| ampliado_s1_B | 57.027/37.576 | 249 | 3,02 p.p. | [0,70; 5,33] | 0,0434 |
| ampliado_s1_C | 26.967/12.599 | 216 | 512,67 indice | [-606,73; 1.632,07] | 0,3677 |
| amostra_comum_s0_A | 26.078/13.893 | 367 | -10,07 % geom. | [-17,32; -2,19] | 0,0805 |
| amostra_comum_s0_B | 26.078/13.893 | 367 | 2,56 p.p. | [-0,38; 5,50] | 0,4358 |
| amostra_comum_s0_C | 26.078/13.893 | 367 | -275,88 indice | [-686,68; 134,93] | 0,7498 |
| amostra_comum_s1_A | 9.949/6.890 | 98 | -3,11 % geom. | [-9,25; 3,45] | 0,7956 |
| amostra_comum_s1_B | 9.949/6.890 | 98 | 2,67 p.p. | [-2,06; 7,40] | 0,7956 |
| amostra_comum_s1_C | 9.949/6.890 | 98 | 937,07 indice | [-1.157,25; 3.031,39] | 0,7956 |
| winsor_s0_A | 46.044/29.886 | 534 | -8,16 % geom. | [-13,05; -2,98] | 0,0144 |
| winsor_s0_B | 46.044/29.886 | 534 | 3,30 p.p. | [1,15; 5,44] | 0,0144 |
| winsor_s0_C | 26.078/13.893 | 367 | -75,45 indice | [-194,94; 44,04] | 0,6455 |
| winsor_s1_A | 18.033/15.392 | 105 | -3,61 % geom. | [-8,19; 1,21] | 0,5530 |
| winsor_s1_B | 17.791/15.105 | 105 | 1,70 p.p. | [-1,33; 4,73] | 0,6455 |
| winsor_s1_C | 9.993/6.939 | 98 | 51,51 indice | [-73,12; 176,13] | 0,6455 |

**Leitura substantiva.** No principal anual, há evidência de associação entre AF, menor preço e maior desconto no grupo não sigiloso; no sigiloso, os testes principais de preço e desconto são inconclusivos. A sensibilidade com condições de compra semelhantes pode alterar essa conclusão por mudar os estratos e a população: deve ser apresentada lado a lado. Não atribuir ao sigilo a causa das diferenças, não interpretar ausência de significância como equivalência, e não tratar o índice extremo como evidência de economia ou sobrepreço causal.

**Limites do controle anual.** O ano amplia o suporte, mas não absorve sazonalidade e mudanças intranuais de preço, logística ou composição da demanda. A cobertura termina em abril de 2026, de modo que esse ano é parcial. A seleção por homologação, recorrência e presença de estimado permanece. Não há certificação independente de resultado ativo para todos os registros, nem informação completa de lotes e alterações anteriores. Classes prioritárias são proxies de bens padronizáveis. Os resultados não se estendem automaticamente a todas as plataformas PNCP ou à economia fiscal executada.

**Validação e reprodução.** 305 registros conferidos diretamente no banco, 128 não sigilosos e 177 sigilosos. Conferidos classificação, preços, estimados, quantidades, modalidades e homologação. Sessenta referências reproduzidas independentemente; coeficiente e variância confrontados com WLS de dummies explícitas, inclusive 148 itens reais anuais. Medianas de reamostragem conferidas por expansão literal dos doadores. Hashes de entradas e scripts e metadados do banco preservados.

Reprodução: `validar_calculo.py`, `executar.py`, `auditar.py`, `relatar.py`, `validar_entrega.py`, com o Python portátil. Depende das extrações preservadas em `../testes_medias_20261117`; em caso de alteração do banco, reextrair antes. Entregas: `resultados_completos.xlsx`, `todas_estimativas.csv`, `descritivas.csv`, `resultados.json`, `protocolo.md`, amostras principais legíveis CSV.gz e demais amostras PKL.
