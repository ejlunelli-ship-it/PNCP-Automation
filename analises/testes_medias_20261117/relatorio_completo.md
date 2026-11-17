**Diferenças de médias — Aberto versus Aberto-Fechado — 17/11/2026**

**Resultado:** o teste principal encontra média de log do preço menor em Aberto-Fechado, com diferença geométrica de -7,70% e p ajustado de 0,0128. Desconto e preço relativo não apresentam diferença significativa a 5% na amostra principal. A significância do log do preço não se mantém após Holm no bootstrap complementar (p=0,0990), que perde muitos estratos. O índice P/M em nível está dominado por registros extremos e não sustenta interpretação econômica da diferença de médias. São associações entre grupos, não efeitos causais da troca de modo.

**Fonte e amostra.** Nova consulta ao banco indicado pelo usuário, `PNCP-Automation/dados/pncp.db`, aberto somente para leitura. Snapshot 10/11/2026. Aberturas de 01/11/2022 a 30/04/2026; elegibilidade detalhada no protocolo. Fonte Dados Abertos/Compras.gov.br, não todas as plataformas do PNCP. A análise principal mantém as classes prioritárias de bens potencialmente padronizáveis dos estudos anteriores; todas as classes entram na sensibilidade ampliada. Excluídos serviços, outras modalidades, Fechado-Aberto, não homologados e critérios diferentes de Menor preço. Recorrência foi novamente verificada usando somente A/AF. Não foram removidos singletons de modelos de painel: este é um novo teste de médias.

**Médias comparáveis.** Produto=CATMAT+apresentação/unidade+PDM+descrição resumida. Somente estratos produto×mês×UF contendo ambos os modos. Cada estrato recebe peso igual, e cada modo tem peso total igual dentro dele. A média padronizada é a média das médias dos estratos. As médias brutas, DP, medianas e quantis também estão disponíveis, mas não devem ser confundidos com as médias padronizadas da tabela.

| Desfecho | Média A | Média AF | Diferença AF−A | IC95% | p nominal | p Holm | Signif. 5% |
|---|---|---|---|---|---|---|---|
| Logaritmo do preço | 0,5639 | 0,4837 | -0,0802 log | [-0,1350; -0,0253] | 0,0043 | 0,0128 | Sim |
| Desconto (%) | 32,85 | 36,01 | 3,16 p.p. | [-0,28; 6,61] | 0,0719 | 0,1438 | Não |
| Preço/mediana pública | 8,16 | 247,85 | 239,69 unidades do indice | [-302,79; 782,18] | 0,3837 | 0,3837 | Não |

Para A, Δlog=-0,08016, EP=0,02790, t=-2,873, gl=414. A transformação 100×[exp(Δ)−1] resulta em -7,70%, IC95% [-12,63; -2,50]. Médias geométricas de produtos com unidades diferentes são índices de composição fixa, não preço de uma cesta física ou gasto médio.

Para B, a diferença é em pontos percentuais; as médias são descontos percentuais. Para C, 1 representa preço igual ao benchmark; a diferença está em unidades da razão, não em pontos percentuais. O valor descritivo da variação relativa das médias de C é exportado à planilha, mas sua interpretação é comprometida pelas caudas. Não foi calculado IC específico para esse quociente de médias.

| Desfecho | Itens A | Itens AF | Total | Pregões | Órgãos A/AF | Órgãos distintos | Produtos | Estratos |
|---|---|---|---|---|---|---|---|---|
| A | 22.291 | 18.273 | 40.564 | 8.507 | 294/186 | 415 | 2.020 | 14.284 |
| B | 10.635 | 8.846 | 19.481 | 3.335 | 237/153 | 341 | 1.308 | 7.396 |
| C | 1.159 | 703 | 1.862 | 706 | 92/58 | 134 | 169 | 320 |

Os órgãos podem aparecer nos dois modos; as contagens por modo não são somadas para obter órgãos distintos. As elegibilidades diferem: B exige estimado válido e sigilo falso; C exige benchmark. A interseção comum foi estimada separadamente.

**Distribuição e escolha do teste.** O teste é bilateral de diferença de médias padronizadas, equivalente a WLS com interceptos de estrato, indicador AF e pesos 1/n_estrato_modo. O sandwich aceita heteroscedasticidade e dependência dentro do CNPJ e do CATMAT; usa t e correções finitas especificadas. Não pressupõe normalidade dos itens ou variâncias iguais, mas sua aproximação requer informação suficiente entre grupos. Welch isolado não resolve a dependência entre itens. Mann–Whitney testa uma hipótese de distribuição e não genericamente igualdade de médias; não foi usado como substituto. Não houve escolha de teste por Shapiro ou pelo resultado mais significativo. Referências: [agrupamentos múltiplos](https://www.nber.org/papers/t0327), [Welch](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.ttest_ind.html), [Mann–Whitney](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.mannwhitneyu.html).

| Desfecho/modo | Média bruta | DP | Mediana | P99 | Máximo | Assimetria | Curtose excesso |
|---|---|---|---|---|---|---|---|
| A/A | 0,49 | 2,22 | 0,54 | 7,30 | 13,24 | 0,64 | 1,21 |
| A/AF | 0,50 | 2,28 | 0,51 | 7,87 | 13,23 | 0,77 | 1,45 |
| B/A | 32,63 | 25,41 | 29,25 | 92,52 | 100,00 | 0,50 | -0,69 |
| B/AF | 36,25 | 25,06 | 33,93 | 93,58 | 99,74 | 0,35 | -0,62 |
| C/A | 9,46 | 200,14 | 1,00 | 88,42 | 6.700,17 | 32,50 | 1.082,35 |
| C/AF | 338,02 | 8.929,70 | 0,98 | 3,20 | 236.764,71 | 26,51 | 703,00 |

**Auditoria do preço relativo.** A referência é a mediana contemporânea de compras públicas de outros órgãos, com ≥5 pregões e ≥2 CNPJs; uma mediana por pregão, mesmo produto/mês/UF. Não é um preço externo do mercado privado. Foram reproduzidas 50 referências por algoritmo independente. O teste principal de C é condicional às referências observadas; o bootstrap complementar as recalcula.

A maior razão é 236.764,71: preço registrado de R$ 16.100,00 dividido pela mediana R$ 0,068. O registro tem CATMAT 268493, apresentação registrada COMPRIMIDO e quantidade prevista 1. Esses valores foram confirmados no SQLite; confirmar o registro não comprova equivalência física. Não foi possível certificar se há embalagem/globalização/erro ou outra causa. Os maiores casos e seus doadores estão em `auditoria_extremos_indice.csv` e `doadores_tres_extremos.csv`. Não houve correção conjectural ou exclusão por magnitude.

As medianas brutas das razões são próximas de 1 nos dois modos, enquanto as médias são muito maiores. Isso não autoriza trocar média por mediana e manter a mesma hipótese. A winsorização registrada foi mostrada separadamente; em produtos com poucos itens, os quantis interpolados podem modificar mais de 2% dos registros.

**Bootstrap complementar e concentração.** Foram feitas 1.999 replicações por CNPJ, mantendo juntos os itens de cada órgão. Referências de C foram recalculadas com multiplicidade dos doadores, exclusão do órgão-alvo e mínimos de suporte. Estratos sem ambos os modos ou sem referência válida ficam ausentes na replicação. Essa perda altera a composição; os números abaixo não são uma segunda certificação da inferência principal.

| Desfecho | IC95 básico (escala original) | p bootstrap | p Holm bootstrap | Estratos retidos em média |
|---|---|---|---|---|
| A | [-0,1316; -0,0110] | 0,0330 | 0,0990 | 50,93% |
| B | [-0,08; 7,30] | 0,0600 | 0,1200 | 48,82% |
| C | [-659,73; 514,38] | 0,1150 | 0,1200 | 17,78% |

Para log do preço, a correção Holm é significativa no teste principal, mas não no bootstrap. Para desconto e índice, os dois procedimentos permanecem sem rejeição após Holm. A forte perda de suporte, sobretudo em C, impede usar o bootstrap como solução definitiva para a distribuição irregular. ICs percentis e inferência somente por órgão também estão no JSON/planilha. Não rejeição não demonstra equivalência.

**Sensibilidades registradas.** “Condições de compra” exige também SRP, benefício e faixa de quantidade fator dois iguais. Não exige mesmo comprador. “Ampliado” usa todas as classes; “Amostra comum” usa os mesmos itens elegíveis para os três desfechos; “Winsor” altera o desfecho pelos quantis 1/99 de cada produto. Populações/variáveis mudam, e nenhum resultado substitui o principal. Holm é aplicado separadamente por trio exploratório.

| Análise | Itens A/AF | Órgãos | Diferença | IC95% | p Holm |
|---|---|---|---|---|---|
| principal_A | 22291/18273 | 415 | -7,70 % geom. | [-12,63; -2,50] | 0,0128 |
| principal_B | 10635/8846 | 341 | 3,16 p.p. | [-0,28; 6,61] | 0,1438 |
| principal_C | 1159/703 | 134 | 239,69 unidades do indice | [-302,79; 782,18] | 0,3837 |
| condicoes_compra_A | 1548/1489 | 185 | -5,51 % geom. | [-8,16; -2,78] | 0,0004 |
| condicoes_compra_B | 670/654 | 152 | 4,45 p.p. | [-1,81; 10,72] | 0,3241 |
| condicoes_compra_C | 110/99 | 70 | -0,03 unidades do indice | [-0,08; 0,02] | 0,3241 |
| ampliado_A | 110657/67417 | 1.091 | -6,75 % geom. | [-9,77; -3,64] | <0,0001 |
| ampliado_B | 70753/45619 | 980 | 4,64 p.p. | [3,22; 6,07] | <0,0001 |
| ampliado_C | 13535/5125 | 555 | 34,59 unidades do indice | [-52,04; 121,22] | 0,4332 |
| amostra_comum_A | 740/471 | 100 | -8,67 % geom. | [-28,28; 16,30] | 0,7710 |
| amostra_comum_B | 740/471 | 100 | 6,65 p.p. | [1,39; 11,91] | 0,0411 |
| amostra_comum_C | 740/471 | 100 | 473,33 unidades do indice | [-604,11; 1.550,77] | 0,7710 |
| winsor_A | 22291/18273 | 415 | -7,04 % geom. | [-11,42; -2,44] | 0,0094 |
| winsor_B | 10635/8846 | 341 | 3,18 p.p. | [-0,23; 6,59] | 0,1354 |
| winsor_C | 1159/703 | 134 | 229,76 unidades do indice | [-285,73; 745,25] | 0,3796 |

Na comparação adicional com condições de compra semelhantes, o log do preço corresponde a -5,51%, IC95% [-8,16; -2,78], p Holm=0,0004; bootstrap Holm=0,0030. Esse resultado reforça a associação negativa nessa população específica, sem remover confundimento entre compradores. Para C, a mesma restrição reduz a amostra a 209 itens e aproxima as médias de 1, mas a diferença permanece não significativa.

**Limites.** A análise compara compras homologadas e recorrentes, selecionadas e não aleatórias. Catálogo/apresentação não certificam equivalência técnica integral. Quantidade/SRP no snapshot não garantem versões anteriores à decisão do modo. Referências usam preços públicos contemporâneos, inclusive dos dois modos; podem refletir a composição institucional e efeitos compartilhados. O benchmark não deve ser chamado de preço verdadeiro de mercado. Campos de lote e resultados ativos continuam incompletos. A análise não mede execução, entrega ou economia fiscal. As diferenças em relação ao painel e matching anteriores decorrem também de outro alvo (peso igual por produto/mês/UF), recortes e ajustes; não são três estimativas intercambiáveis do mesmo efeito.

**Integridade e reprodução.** 179 itens conferidos diretamente no SQLite, incluindo extremos; valores, quantidades, status e identificadores coincidiram. Coeficiente e variância comparados a WLS com dummies explícitas em dados sintéticos e 101 itens reais. Medianas bootstrap comparadas à expansão literal de doadores. Banco preservado em tamanho/mtime. Protocolo e emenda computacional antes da estimação, hashes, extração, amostras, sorteios e scripts preservados. A emenda de inferência durante a extração é transparente; não se reivindica pré-registro público.

Arquivos: `resultados_completos.xlsx`, `todas_estimativas.csv`, `descritivas.csv`, `resultados.json`, `amostra_principal_A/B/C.csv.gz`, `protocolo.md`, `emenda_antes_estimacao.md`. Reprodução: `preparar.py`, `validar_calculo.py`, `executar.py`, `auditar.py`, `relatar.py`, `validar_entrega.py`, usando o Python portátil do workspace.
