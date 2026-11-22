# Desconto por etapa nos PDFs: base completa (22/11/2026)

Refaz todas as análises por etapa sobre a base completa
`dados/extracao/aberto-fechado_parser-1.9.1.db`:

- **Aberto-Fechado (AF):** 43 meses, de 2023-04 a 2026-10, lidos pelo parser 1.9.1.
- **Fechado-Aberto (FA):** 42 meses, de 2023-05 a 2026-10, lidos pelo parser 1.10.0.

Entram aqui as análises principais do `analise_etapas.py` e os estudos que em 18/11 só cobriam 4 meses de 2026
(`analises/etapas_pdf_af_20261118/`): regressão com sensibilidades, testes por grupo, heterogeneidade e economia em R$.
Há também uma comparação nova, AF × FA. O mês de cada item é o **primeiro mês do resultado da compra** (regra de
22/11, docs/05). Tudo é descritivo: o órgão escolhe o modo de disputa, então nada aqui é efeito causal.

## Resumo

1. **No Aberto-Fechado, a etapa fechada dobra quase o desconto da aberta.**
   - O melhor lance da etapa aberta fica 19,4% abaixo do estimado. Depois da fechada, o melhor preço fica 34,7% abaixo.
   - O ganho da fechada é de **15,4 p.p.** (IC95 15,2–15,5) com todos os fornecedores e de **14,1 p.p.** (13,9–14,2)
     só com os fornecedores válidos.
   - Em preço, a fechada baixa o melhor lance em 22,0% (todos) e em 19,7% (válidos), numa regressão com efeito fixo de
     item.
   - A fechada melhora o preço em 78% dos itens.
2. **O resultado é estável.** O ganho fica entre 15,2 e 16,6 p.p. em cada ano de 2023 a 2026, e o desvio-padrão entre
   os 43 meses é de 1,3 p.p. Também resiste às sensibilidades da regressão com o mesmo desfecho (−20,6 a −26,3 log-pontos, todos os fornecedores) e aos
   recortes que tiram casos suspeitos. Sem esses casos o ganho **sobe** para 17,7 p.p., então a estimativa principal é
   conservadora.
3. **O desconto final é de 34,3%.** Ele se decompõe em 22,1 (aberta) + 16,0 (fechada) − 3,7 (pós-disputa) com todos os
   fornecedores, ou 19,5 + 14,1 + 0,8 só com os válidos.
   - O "−3,7" vem de líderes desclassificados: em 23% dos itens o valor aceito fica acima do melhor lance.
   - Só com fornecedores válidos, o valor final é o melhor lance válido em 92% dos itens.
4. **O número de licitantes é o que mais modera o ganho, e de forma não linear.** O ganho é de 2 p.p. com 1 licitante
   e de 14 p.p. com 2. Chega ao máximo, 18–19 p.p., com 3 a 10 licitantes, e cai a 12 p.p. com mais de 10, quando a
   aberta já deu 39% de desconto.
5. **Material, serviço e orçamento sigiloso não mudam o tamanho do ganho em p.p.**
   - Nos testes de médias, Holm dá p = 1 nos dois casos.
   - O orçamento sigiloso só reduz a **frequência** com que a fechada melhora o preço: 73,4% contra 79,5%, cerca de
     −6 p.p., robusto.
   - Na regressão em log, o sigilo aparece com +3 log-pontos (ganho menor), mas o efeito some dentro da UASG e se
     inverte com peso igual por compra. Não é robusto.
6. **Economia potencial da fechada:** R$ 28,4 bi (15,8% do valor no melhor lance aberto) com todos os fornecedores, ou
   R$ 23,6 bi (12,8%) só com os válidos, sobre R$ 226 bi estimados. As quantidades são estimadas, muitas de registro de
   preços, e 1% dos itens concentra 79% da economia.
7. **No Fechado-Aberto, a segunda etapa (aberta) ganha menos.**
   - A fechada dá 15,9% de desconto; depois da aberta, 25,8%. O ganho é de **9,9 p.p.** (9,0–10,9) com todos os
     fornecedores e de 10,5 p.p. só com os válidos, ou −14,6 log-pontos.
   - O desconto final é de 27,8%.
   - A mesma curva dos licitantes aparece. O orçamento sigiloso reduz o ganho da aberta (+4,6 log-pontos) e a chance de
     a aberta melhorar o preço (−12 p.p.).
8. **No mesmo órgão, o AF fecha com desconto final 4,8 p.p. maior que o FA** (IC95 2,8–6,9; p < 0,001). A comparação
   usa as 168 UASGs que usaram os dois modos e controla mês, tipo, sigilo, valor e número de licitantes, que é igual nos
   dois modos. A diferença vem da segunda etapa: a fechada do AF rende 3,9 p.p. a mais que a aberta do FA. É
   associação, não efeito causal.

## Dados e amostra

| Filtro | Aberto-Fechado | Fechado-Aberto |
|---|---:|---:|
| Itens na base (pasta do modo) | 1.469.565 | 22.218 |
| `status_extracao = OK` | 1.463.292 | 22.197 |
| Menor Preço | 1.415.856 | 21.498 |
| Estimado > 0 e lance da 1ª etapa > 0 | 1.393.103 | 21.343 |
| **Amostra, todos os fornecedores** (descontos entre −100% e 99%) | **1.337.832** | **20.177** |
| **Amostra, só fornecedores válidos** | **1.196.727** | **17.470** |
| Compras / UASGs | 73.464 / 2.501 | 1.149 / 232 |

Regras comuns:

- **Desconto** = 1 − valor / estimado unitário.
- **Após a 2ª etapa** = mínimo entre o melhor valor das duas etapas.
- **Ganho** = desconto após a 2ª etapa − desconto da 1ª, em p.p. do estimado. O ganho relativo é a redução sobre o
  melhor valor da 1ª etapa.
- **Desconto final** = valor negociado, se houver; senão, o lance aceito.
- **Medidas** (decisão de 18/11, sempre lado a lado):
  - *todos os fornecedores*: o melhor lance registrado na disputa.
  - *só fornecedores válidos*: sem desclassificados, recusados e inabilitados. É o desconto que o órgão efetivamente
    obtém de cada etapa.
- **Ligação com o `pncp.db`** (só leitura; tamanho e mtime iguais antes e depois): material ou serviço, orçamento
  sigiloso, esfera, UF e registro de preços. Nas regressões entram os itens com material/serviço e sigilo conhecidos,
  número de licitantes > 0 e valor total > 0: 1.299.740 itens no AF (todos) e 19.681 no FA.
- **Intervalos:** os das médias são por bootstrap de compra (2.000 réplicas). Os erros-padrão de regressão e testes são
  agrupados por UASG.

## 1. Aberto-Fechado: resultado principal

| | Todos os fornecedores | Só fornecedores válidos |
|---|---:|---:|
| Itens / compras | 1.337.832 / 73.464 | 1.196.727 / 73.095 |
| Desconto da etapa aberta | 19,35% (19,08–19,64) | 19,35% (19,08–19,63) |
| Desconto após a fechada | 34,73% (34,45–35,00) | 33,42% (33,15–33,68) |
| **Ganho da fechada (p.p.)** | **15,37 (15,22–15,52)** | **14,07 (13,91–14,22)** |
| Ganho relativo (% do melhor aberto) | 18,66 (18,50–18,83) | 16,87 (16,70–17,04) |
| Desconto final | 34,30% (34,04–34,55) | 34,38% (34,12–34,63) |
| Medianas: aberta / após / ganho | 11,8 / 34,6 / 9,1 | 12,2 / 32,3 / 7,7 |
| Fechada melhorou o preço | 78,2% | 76,6% |
| Final = melhor lance / acima / abaixo | 71,6% / 22,8% / 5,4% | 92,4% / 0,0% / 7,3% |

Como ler a tabela:

- Com todos os fornecedores, a etapa fechada acrescenta em média 15 p.p. de desconto sobre o estimado.
- Quando a fechada melhora o preço, o ganho mediano é de 9 p.p.
- O desconto da aberta tem média 19% e mediana 12%: há muitos itens com desconto alto na aberta.
- Só com fornecedores válidos, o ganho cai 1,3 p.p. Parte dos lances fechados vencedores era de fornecedores
  desclassificados depois.
- O desconto final é praticamente igual nas duas medidas (34,3% e 34,4%). Ele não depende da medida, porque é o que o
  órgão pagou.

### Item a item: melhor fechado contra melhor aberto

| | Todos | Válidos |
|---|---:|---:|
| Itens com lance fechado | 1.153.185 | 996.364 |
| Diferença média fechado − aberto (p.p.) | 15,62 | 15,43 |
| Diferença mediana | 12,10 | 11,15 |
| Fechado melhor / pior que o aberto | 90,8% / 8,8% | 92,0% / 7,5% |
| Wilcoxon | p ≈ 0 | p ≈ 0 |

### Decomposição do desconto final

A decomposição usa os 1.179.225 itens que estão nas duas medidas e têm valor final.

| | Etapa aberta | + Etapa fechada | + Pós-disputa | = Final |
|---|---:|---:|---:|---:|
| Todos os fornecedores | 22,06 (21,78–22,36) | 16,04 (15,88–16,21) | −3,73 (−3,81 a −3,64) | 34,38 |
| Só fornecedores válidos | 19,51 (19,23–19,78) | 14,11 (13,97–14,28) | +0,76 (0,73–0,79) | 34,38 |

O pós-disputa negativo, com todos os fornecedores, é o líder que cai na habilitação ou na aceitação: o órgão contrata o
seguinte, mais caro. Só com os válidos, o pós-disputa é a negociação, que traz +0,8 p.p.

### Casos suspeitos (marcas do parser) e sensibilidade

| Marca | Itens | % da amostra | Dos 113.263 com fechado acima do aberto |
|---|---:|---:|---:|
| A líder da aberta sem lance fechado | 391.150 | 29,2% | 113.263 |
| A3 líder da aberta desclassificado | 345.138 | 25,8% | 59.760 |
| B etapa fechada reiniciada | 120.705 | 9,0% | 34.952 |
| C lance aberto isolado (< 50% do 2º fornecedor) | 69.080 | 5,2% | 22.344 |
| D lance fechado > 3 × aberto | 19.486 | 1,5% | 19.486 |
| Fechado acima do aberto | 113.263 | 8,5% | — |

| Recorte (todos os fornecedores) | Itens | Aberta | Ganho da fechada (IC95) | Final |
|---|---:|---:|---:|---:|
| Amostra principal | 1.337.832 | 19,35 | 15,37 (15,22–15,52) | 34,30 |
| sem A3 | 992.694 | 19,07 | 16,94 (16,77–17,12) | 35,76 |
| sem B | 1.217.127 | 18,24 | 16,10 (15,95–16,26) | 34,59 |
| sem C | 1.268.752 | 19,06 | 15,76 (15,61–15,92) | 34,54 |
| sem D | 1.318.346 | 18,85 | 15,60 (15,45–15,75) | 34,29 |
| sem A3, B, C e D | 928.394 | 18,68 | **17,65 (17,47–17,82)** | 35,95 |

Os casos suspeitos *reduzem* o ganho medido. Tirá-los aumenta o ganho em até 2,3 p.p., então a estimativa principal é
um piso.

## 2. Economia em R$ e descontos ponderados pelo valor

A quantidade de cada item é o valor estimado total dividido pelo estimado unitário. A economia da fechada é
(melhor aberto − melhor após a fechada) × quantidade.

| Aberto-Fechado | Todos | Válidos |
|---|---:|---:|
| Itens | 1.337.811 | 1.196.706 |
| Valor estimado total | R$ 225,9 bi | R$ 215,1 bi |
| No melhor lance aberto | R$ 179,2 bi | R$ 183,4 bi |
| Após a fechada | R$ 150,8 bi | R$ 159,8 bi |
| **Economia da fechada** | **R$ 28,4 bi (15,8% do aberto)** | **R$ 23,6 bi (12,8%)** |
| Desconto ponderado: aberta → após a fechada | 20,7% → 33,2% | 14,7% → 25,7% |
| Desconto final ponderado | 26,7% | 26,7% |
| Parcela da economia no 1% de itens com maior economia | 79% | 81% |

O Fechado-Aberto tem economia da etapa aberta de R$ 113 mi, 5,5% do valor no melhor lance fechado (R$ 93 mi, 4,6%, só
com os válidos), sobre R$ 2,56 bi estimados.

Leitura:

- **A economia é muito concentrada.** Os 10 itens de maior economia somam 13% do total, e os 1.000 maiores somam 53%.
  São compras enormes de verdade, com milhões de unidades: vacinas e medicamentos do Ministério da Saúde (UASG 250005,
  várias vezes) e de outros órgãos.
- **O valor é potencial.** Como muitas são atas de registro de preços, a quantidade é a estimada, não a contratada.
- **Com todos os fornecedores, o desconto final ponderado (26,7%) fica bem abaixo do desconto após a fechada (33,2%).**
  Nos itens grandes, o melhor lance fechado é com frequência de quem depois foi desclassificado.
- **Em R$, a medida mais fiel é a dos válidos:** a fechada leva o desconto ponderado de 14,7% para 25,7%.

## 3. Estabilidade no tempo

| Ano | Itens | Licitantes (média) | Aberta | Após a fechada | Ganho (EP) | Fechada melhorou | Final |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2023 (abr–dez) | 87.366 | 6,1 | 16,6 | 33,2 | 16,6 (0,45) | 77,1% | 32,8 |
| 2024 | 412.316 | 7,8 | 19,7 | 35,1 | 15,4 (0,21) | 78,6% | 35,1 |
| 2025 | 511.400 | 8,7 | 19,5 | 34,7 | 15,2 (0,18) | 78,2% | 34,3 |
| 2026 (jan–out) | 326.750 | 8,6 | 19,4 | 34,7 | 15,3 (0,20) | 78,3% | 33,7 |

Os valores são da medida com todos os fornecedores. Só com os válidos, o ganho por ano é 15,4, 14,2, 13,9 e 13,8 p.p.

- **Por mês** (tabela `por_mes`), o ganho com todos os fornecedores fica entre 13,2 e 17,9 p.p. em todos os meses com
  mais de 1.000 itens.
- Só 2023-04 (224 itens; 10,4 p.p.) fica fora dessa faixa.
- O desvio-padrão entre os 43 meses, só com os válidos, é de 1,3 p.p.
- Em 2023 a aberta rende menos (16,6%) e a fechada um pouco mais (16,6 p.p.). Isso acompanha o menor número de
  licitantes daquele ano.

## 4. Heterogeneidade

Médias da medida com todos os fornecedores, com o erro-padrão agrupado por UASG entre parênteses. A tabela completa,
com as duas medidas, está em `complementares.xlsx`, aba `heterogeneidade`.

### Número de licitantes

| Licitantes | Itens | Aberta | Após a fechada | Ganho (EP) | Ganho relativo | Fechada melhorou | Final |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 81.208 | −5,6 | −3,5 | 2,1 (0,09) | 1,9 | 15,3% | 6,2 |
| 2 | 116.867 | 0,0 | 14,0 | 14,0 (0,25) | 13,4 | 63,1% | 18,3 |
| 3–5 | 377.668 | 9,3 | 28,0 | 18,7 (0,20) | 19,9 | 80,2% | 27,9 |
| 6–10 | 419.001 | 22,8 | 40,8 | 18,0 (0,23) | 22,1 | 86,5% | 37,6 |
| > 10 | 343.088 | 38,7 | 50,9 | 12,2 (0,20) | 19,0 | 86,1% | 45,5 |

O desconto final cresce sem parar com a concorrência, de 6% para 46%. O ganho da fechada, porém, desenha um "U"
invertido:

- **1 licitante:** quase não há o que ganhar. Não há outro fornecedor, e o líder raramente baixa o próprio lance.
- **2 licitantes:** aqui a fechada mais importa em relação ao que a aberta deu, já que a aberta fica em 0%.
- **Mais de 10 licitantes:** a aberta já levou o preço para perto do piso e sobra menos para a fechada, embora em termos
  relativos (19%) o ganho continue alto.

### Valor do item (quintis do valor estimado total)

| Quintil | Licitantes | Aberta | Ganho (EP) | Final |
|---|---:|---:|---:|---:|
| Q1 (menor) | 4,9 | 12,8 | 15,6 (0,20) | 31,3 |
| Q2 | 6,6 | 17,3 | 16,1 (0,18) | 34,3 |
| Q3 | 8,1 | 20,0 | 16,0 (0,18) | 35,4 |
| Q4 | 9,7 | 22,3 | 15,4 (0,20) | 35,9 |
| Q5 (maior) | 11,8 | 24,4 | 13,7 (0,20) | 34,6 |

Itens maiores atraem mais licitantes e têm aberta mais forte. O ganho da fechada só cai no quintil mais alto.

### Material/serviço × orçamento

| Grupo | Itens | Licitantes | Aberta | Ganho (EP) | Fechada melhorou | Final |
|---|---:|---:|---:|---:|---:|---:|
| Material, orçamento aberto | 964.045 | 8,0 | 19,3 | 15,3 (0,17) | 79,2% | 33,9 |
| Material, sigiloso | 262.137 | 8,2 | 18,7 | 15,7 (0,43) | 73,5% | 35,7 |
| Serviço, orçamento aberto | 65.581 | 10,8 | 21,4 | 15,2 (0,45) | 84,0% | 33,8 |
| Serviço, sigiloso | 7.997 | 9,3 | 28,1 | 12,7 (0,87) | 68,9% | 36,0 |

### Esfera, região e registro de preços

Esfera, UF e registro de preços (SRP) vêm do `pncp.db`, porque estão vazios na base de extração.

| Grupo | Itens | Compras | UASGs | Licitantes | Aberta | Ganho, todos (EP) | Ganho, válidos | Fechada melhorou | Final |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Federal | 740.748 | 24.838 | 1.306 | 7,9 | 17,2 | 16,6 (0,17) | 15,4 | 79,1% | 33,6 |
| Estadual | 176.701 | 22.929 | 673 | 8,3 | 20,5 | 13,3 (0,38) | 11,5 | 73,3% | 32,9 |
| Municipal | 354.452 | 22.200 | 543 | 9,0 | 24,0 | 13,8 (0,29) | 12,3 | 79,7% | 36,5 |
| Distrital | 10.541 | 1.093 | 25 | 8,3 | 3,4 | 17,8 (1,01) | 17,3 | 75,9% | 23,1 |
| Esfera não informada | 55.390 | 2.404 | 201 | 7,5 | 18,3 | 15,6 (0,62) | 14,2 | 73,1% | 34,7 |
| Centro-Oeste | 144.356 | 7.562 | 327 | 8,2 | 15,7 | 16,8 (0,43) | 15,7 | 79,6% | 33,0 |
| Nordeste | 292.860 | 14.346 | 522 | 8,0 | 17,3 | 15,6 (0,31) | 14,2 | 77,8% | 32,6 |
| Norte | 138.067 | 4.172 | 447 | 8,7 | 21,9 | 14,4 (0,55) | 13,2 | 76,9% | 35,4 |
| Sudeste | 486.104 | 37.157 | 843 | 8,8 | 21,8 | 14,6 (0,27) | 13,3 | 77,0% | 36,0 |
| Sul | 276.445 | 10.227 | 363 | 7,1 | 17,8 | 16,2 (0,27) | 14,9 | 80,8% | 33,4 |
| Registro de preços | 1.120.103 | 38.925 | 1.653 | 8,1 | 19,3 | 15,6 (0,18) | 14,4 | 78,6% | 34,6 |
| Sem registro de preços | 217.729 | 34.539 | 1.994 | 8,9 | 19,8 | 14,0 (0,24) | 12,4 | 76,3% | 32,7 |

Leitura:

- **Esfera:**
  - Órgãos federais, que são 55% dos itens, têm aberta mais fraca (17%) e fechada mais forte (16,6 p.p.).
  - Estados e municípios partem de uma aberta mais forte (20–24%) e ganham 13–14 p.p. na fechada.
  - O desconto final fica entre 33% e 37% nas três esferas.
- **Região:** as diferenças são de no máximo 2,4 p.p. no ganho. O Centro-Oeste e o Sul ganham mais na fechada; o Norte e
  o Sudeste, menos, mas com aberta mais forte.
- **Registro de preços:** 84% dos itens são de SRP. Nessas compras, o ganho é 1,6 p.p. maior e o desconto final é 1,9
  p.p. maior.
- **De modo geral, onde a aberta rende menos, a fechada compensa parte da diferença.**

No FA, os grupos são pequenos. A esfera federal ganha 11,1 p.p. na aberta e a estadual 8,2; com SRP o ganho é de 10,4
p.p., sem SRP de 8,7. Tudo está na aba `heterogeneidade` de `resultados/fechado-aberto/complementares.xlsx`.

## 5. Testes de diferença de médias por grupo

São seis comparações: material × serviço e orçamento aberto × sigiloso, no total e dentro de cada grupo. Cada uma é
testada em sete variáveis. O teste principal é o t com EP agrupado por UASG, com correção de Holm sobre a família.
Também entram Welch, Mann-Whitney e uma versão **ajustada pelo número de licitantes** (efeito fixo de 1 a 20, 21–30
e 31+). Tudo está em `complementares.xlsx`, aba `testes_grupos`.

Resultados principais no AF, com todos os fornecedores (diferença B − A, p de Holm):

| Comparação | Ganho da fechada (p.p.) | Ganho relativo | Fechada melhorou (p.p.) | Desconto da aberta | Desconto final |
|---|---:|---:|---:|---:|---:|
| Serviço − material | −0,43 (p = 1) | +0,44 (1) | **+4,33 (< 0,001)** | **+2,90 (0,002)** | −0,25 (1) |
| … ajustado por licitantes | +0,12 (1) | +0,36 (1) | +2,49 (0,004) | −0,94 (1) | −2,04 (0,20) |
| Sigiloso − aberto | +0,33 (1) | **−1,76 (< 0,001)** | **−6,15 (< 0,001)** | −0,43 (1) | +1,79 (1) |
| … ajustado por licitantes | +0,14 (1) | −2,04 (< 0,001) | −7,01 (< 0,001) | −0,89 (1) | +1,44 (1) |

Leitura:

- **O ganho da fechada em p.p. não difere** entre material e serviço, nem entre orçamento aberto e sigiloso. Vale para
  as duas medidas e para as seis comparações (Holm p ≥ 0,12).
- **Serviços:**
  - Têm 2,5 licitantes a mais (10,6 contra 8,1) e desconto 2,9 p.p. maior na aberta.
  - A diferença na aberta some com o ajuste por licitantes. É a concorrência, não o tipo de objeto.
- **Orçamento sigiloso:**
  - A fechada melhora o preço 6–7 p.p. menos vezes (73,4% contra 79,5%) e o ganho relativo é 1,8 p.p. menor.
  - O desconto final é igual ou até maior.
  - Sem o estimado à vista, os licitantes partem de lances diferentes, e o resultado final não piora.
- **Só com os fornecedores válidos**, as conclusões são as mesmas. A diferença de sigilo em "fechada melhorou" é de
  −6,5 p.p. (Holm < 0,001).

## 6. Regressão com efeito fixo de item e 13 sensibilidades

O modelo usa duas observações por item, o melhor preço ao fim da aberta e após a fechada: y = 100·ln(preço), com efeito
fixo de item. É estimado em primeira diferença, numericamente igual ao painel empilhado. Os regressores são F, F ×
{ln licitantes, sigiloso, serviço} e F × {ln valor, mês}, centrados, com EP agrupado por UASG. O coeficiente de F é a
variação média do preço entre as etapas. Uma interação positiva quer dizer **menos** ganho.

Aberto-Fechado: coeficiente (EP), com * p < 0,05, ** p < 0,01 e *** p < 0,001.

| Especificação | F, todos | ln lic | sigiloso | serviço | F, válidos | ln lic | sigiloso | serviço |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **P principal** | **−24,81 (0,26)*** ** | −5,09*** | +3,05*** | −0,43 | **−21,96 (0,25)*** ** | −1,43*** | +2,23*** | −1,62* |
| S1 ganho em p.p. | 15,37*** | +0,89*** | +0,56 | +0,13 | 14,05*** | −1,11*** | +0,76 | +0,56 |
| S2 licitantes em faixas | −24,81*** | (faixas) | +3,40*** | −0,52 | −21,96*** | (faixas) | +2,42*** | −1,65* |
| S3 + serviço × sigiloso | −24,81*** | −5,09*** | +3,02*** | −0,51 | −21,96*** | −1,43*** | +2,21*** | −1,70 |
| S4 EP por compra | −24,81*** | −5,09*** | +3,05*** | −0,43 | −21,96*** | −1,43*** | +2,23*** | −1,62* |
| S5 EP UASG + fornecedor | −24,81*** | −5,09*** | +3,05*** | −0,43 | −21,96*** | −1,43*** | +2,23*** | −1,62 |
| S6 peso igual por compra | −21,77*** | −2,38*** | −0,66 | +1,52** | −17,80*** | +0,45 | **−1,54*** ** | −0,57 |
| S7 FE UASG × etapa | — | −5,29*** | **+1,01** | −0,84 | — | −1,53*** | **−0,58** | −2,16** |
| S8 P(fechada melhora), MLP | 78,23*** | +16,55*** | **−6,48*** ** | +0,45 | 76,59*** | +8,93*** | **−6,38*** ** | +0,63 |
| S9 só itens que melhoraram | −31,71*** | +0,35 | +1,44* | −0,41 | −28,68*** | +2,02*** | +0,69 | −1,97* |
| S10 só adjudicados | −26,28*** | −3,43*** | +3,53*** | −0,24 | −22,06*** | −1,41*** | +2,20*** | −1,65* |
| S11 corte 1%/99% | −23,03*** | −4,97*** | +1,91*** | −0,20 | −20,39*** | −1,65*** | +1,16* | −0,98 |
| S12 agregado por compra | −20,58*** | −1,48*** | **−0,55** | +0,93 | −16,23*** | +1,14*** | **−1,46** ** | −1,02* |
| S13 sem 1 licitante | −26,26*** | −1,38*** | +3,51*** | −0,47 | −22,85*** | +2,07*** | +2,52*** | −1,73* |

Faixas de licitantes (S2, base 6–10), todos / válidos:

| 1 licitante | 2 | 3–5 | > 10 |
|---:|---:|---:|---:|
| +27,8*** / +23,4*** | +12,2*** / +7,1*** | +3,1*** / +0,5 | +4,6*** / +6,2*** |

Leitura:

- **O efeito médio é robusto.** A fechada baixa o preço entre 16 e 32 log-pontos em todas as especificações. Na
  principal são −24,8 e −22,0 log-pontos, ou −22,0% e −19,7% no preço.
- **Licitantes:**
  - É o moderador robusto, e sobretudo na margem extensiva (S8): mais licitantes aumentam a chance de a fechada
    melhorar o preço.
  - A relação não é linear (S2): o ganho é mínimo com 1 licitante, máximo entre 3 e 10 e menor acima de 10.
  - Por isso o sinal do log se inverte quando se tiram os itens de 1 licitante (S13 válidos: +2,07).
- **Orçamento sigiloso:**
  - Na margem extensiva o efeito é robusto: a fechada melhora o preço 6,5 p.p. menos vezes (S8, as duas medidas).
  - Na magnitude em log o efeito não é robusto. É +3,0 na principal, mas some dentro da UASG (S7: +1,0, n.s.) e se
    inverte com peso igual por compra (S6) e na regressão agregada (S12).
  - O "ganho menor com sigilo" da principal reflete a composição de UASGs e de compras com muitos itens, não o sigilo em
    si. É o mesmo diagnóstico do estudo de 18/11, agora com 8 vezes mais dados.
- **Serviço:** efeito nulo ou pequeno. Só com os válidos, o ganho é 1,6–2,2 log-pontos maior para serviços em algumas
  especificações, sem significância nas de EP mais conservador (S5).
- **Wald das interações:** os moderadores, em conjunto, são significativos em todas as especificações do AF (p < 0,03).

Efeitos marginais da principal (todos os fornecedores), em variação do preço da aberta para depois da fechada:

| Licitantes | Material, orçamento aberto | Material, sigiloso | Serviço, orçamento aberto | Serviço, sigiloso |
|---:|---:|---:|---:|---:|
| 2 | −18,0% | −15,4% | −18,3% | −15,8% |
| 5 | −21,7% | −19,3% | −22,1% | −19,6% |
| 10 | −24,4% | −22,1% | −24,8% | −22,4% |
| 20 | −27,1% | −24,8% | −27,4% | −25,1% |

## 7. Fechado-Aberto

No FA a ordem se inverte: primeiro a etapa fechada, com propostas sigilosas, e depois a aberta, com lances. As marcas
A e B não existem nesse modo.

| | Todos os fornecedores | Só fornecedores válidos |
|---|---:|---:|
| Itens / compras / UASGs | 20.177 / 1.149 / 232 | 17.470 / 1.136 / — |
| Desconto da etapa fechada | 15,89% (13,44–18,41) | 15,79% (13,74–17,95) |
| Desconto após a aberta | 25,83% (23,58–28,12) | 26,31% (24,32–28,26) |
| **Ganho da aberta (p.p.)** | **9,94 (8,99–10,93)** | **10,52 (9,45–11,64)** |
| Ganho relativo | 11,06% | 11,66% |
| Mediana do ganho | 1,3 | 1,8 |
| Desconto final | 27,77% (25,97–29,56) | 27,87% (26,07–29,71) |
| Aberta melhorou o preço | 62,6% | 64,2% |
| Decomposição: fechada + aberta + pós = final | 19,06 + 10,65 − 1,83 = 27,87 | 15,76 + 10,52 + 1,59 = 27,87 |
| Regressão, coeficiente de A (EP) | **−14,64 (0,71)** | **−15,26 (0,72)** |
| A × ln licitantes | −5,13*** | −4,08*** |
| A × sigiloso | +4,64*** | +2,45 (p = 0,064) |
| A × serviço | +1,61 (n.s.) | +1,71 (n.s.) |
| Economia da aberta | R$ 113 mi (5,5%) | R$ 93 mi (4,6%) |

- **Ganho médio de 10 p.p. com mediana de 1,3.** Em quase 4 de cada 10 itens a aberta não muda nada; quando muda, muda
  muito.
- **Sensibilidade às marcas:**
  - Sem A3, o ganho é de 10,9 p.p.; sem C, 10,4; sem D, 9,0; sem A3, C e D, 10,5.
  - O desconto final fica entre 27,0% e 28,0%.
- **Licitantes:** a mesma curva do AF. O ganho é de 0,6 p.p. com 1 licitante, 4,5 com 2, 10,1 com 3–5, 13,6 com 6–10 e
  9,5 com mais de 10.
- **Sigilo:**
  - Com orçamento sigiloso, a aberta melhora o preço 13,6 p.p. menos vezes (Holm < 0,001) e o ganho relativo é 3,5 p.p.
    menor.
  - Na regressão, +4,6 log-pontos com todos os fornecedores. Diferentemente do AF, o efeito se mantém com peso por
    compra (S6: +4,4***) e na regressão agregada (S12: +4,7***), mas não dentro da UASG (S7: +2,9, p ≈ 0,05).
  - Só com os válidos, o efeito é mais fraco (p = 0,06).
- **Tempo:**
  - Por ano, o ganho é de 16,0 p.p. em 2023 (1.276 itens) e de 9–10 p.p. de 2024 a 2026.
  - Por mês, a série é ruidosa: há meses com poucos itens, e uma compra pesa muito.
- **Serviços** são só 795 itens, com 19 licitantes em média (contra 8 nos materiais). O desconto maior que eles têm na
  fechada some com o ajuste por licitantes.

## 8. Aberto-Fechado × Fechado-Aberto

Os itens dos dois modos foram empilhados (todos os fornecedores) e regredidos numa dummy FA, com EP agrupado por UASG.
São três especificações:

- **Bruta.**
- **Com controles:** mês, faixa de licitantes, tipo, sigilo e ln do valor.
- **Com efeito fixo de UASG:** só as 168 UASGs que usaram os dois modos, com 237.363 itens AF e 13.233 FA.

| Diferença FA − AF (p.p.) | Bruta | Com controles | FE de UASG |
|---|---:|---:|---:|
| Desconto da 1ª etapa (AF: aberta; FA: fechada) | −3,4 (p = 0,19) | −4,3 (0,003) | −2,9 (0,13) |
| Desconto ao fim da disputa | −8,8 (< 0,001) | −9,7 (< 0,001) | **−6,8 (< 0,001)** |
| **Desconto final** | −6,5 (0,001) | −7,3 (< 0,001) | **−4,8 (IC −6,9 a −2,8; < 0,001)** |
| Ganho da 2ª etapa | −5,4 (< 0,001) | −5,4 (< 0,001) | **−3,9 (0,001)** |
| Número de licitantes | +0,4 (0,59) | +0,8 (0,26) | +0,9 (0,09) |

Leitura:

- **No mesmo órgão, o AF termina com desconto final cerca de 5 p.p. maior que o FA**, com o mesmo número de licitantes.
  Desconto aqui é sempre em relação ao estimado.
- **A 1ª etapa é parecida nos dois modos.** A aberta do AF e a fechada do FA rendem quase o mesmo (−2,9, n.s.).
- **A diferença está na 2ª etapa.** No AF, os licitantes dão um lance fechado único depois de ver a disputa aberta. No
  FA, a aberta começa das propostas fechadas e o ganho é menor (3,9 p.p. a menos).
- **É coerente com o estudo de desfecho** (`analises/desfecho_modos_20261121/`): no FA, a compra também tem 5,2 p.p.
  menos chance de homologar todos os itens.
- **É associação.**
  - O órgão escolhe o modo compra a compra, e o FA tem poucas UASGs (232) e compras (1.149).
  - O efeito fixo de UASG e os controles tiram as diferenças fixas entre órgãos, o mês, o tipo de objeto, o sigilo, o
    valor e a concorrência. Não tiram a escolha do modo pelo tipo específico de compra.

## 9. Limites

- **Referência = estimado do órgão.** A qualidade do estimado varia. O desconto mede o preço contra o estimado, não
  contra um preço de mercado.
- **Só Aberto-Fechado e Fechado-Aberto.** Os PDFs não permitem comparar com o modo Aberto, que não tem etapa fechada. Essa
  comparação está nos estudos sobre o `pncp.db` (`analises/testes_medias_*`, `painel_efeitos_fixos_*`).
- **Itens fora da amostra:**
  - Status diferente de OK: 6.273 itens no AF, 0,4%.
  - Critério diferente de Menor Preço.
  - Descontos fora de −100% a 99%: 4% dos itens com lance aberto. Esse filtro de qualidade é o mesmo desde 18/11.
- **Duas medidas.** "Todos os fornecedores" descreve a dinâmica da disputa; "só válidos" descreve o que o órgão obtém.
  A decomposição mostra como uma se transforma na outra.
- **R$ potencial.** A economia usa a quantidade estimada, muitas vezes de registro de preços, e é muito concentrada em
  poucos itens grandes.
- **FA pequeno.** O FA tem 1,5% dos itens do AF, então a série mensal do FA é ruidosa.

## Arquivos

Nesta pasta (versionados):

| Arquivo | Conteúdo |
|---|---|
| `relatorio.md` | este relatório |
| `complementares.py` | regressão com 13 sensibilidades, testes por grupo, heterogeneidade, AF × FA |
| `economia.py` | economia em R$ e descontos ponderados |
| `resultados/aberto-fechado/`, `resultados/fechado-aberto/` | `resultados.json` e `tabelas.xlsx` do `analise_etapas.py`; `complementares.json` e `complementares.xlsx` |
| `resultados/comparacao_af_fa.{json,xlsx}`, `resultados/economia.json` | AF × FA e economia |

Os dados por item (`por_item.csv.gz`, 67 MB no AF) ficam fora do git, em
`dados/analise_etapas/completo_20261122/<modo>/`.

Para reexecutar, da pasta `PNCP-Automation`, com o Python do `.venv`:

```powershell
$env:PNCP_DADOS = "$PWD\dados"
python analise_etapas.py --db dados\extracao\aberto-fechado_parser-1.9.1.db --pncp-db ..\dados\pncp.db --saida dados\analise_etapas\completo_20261122\aberto-fechado
python analise_etapas.py --modo fechado-aberto --db dados\extracao\aberto-fechado_parser-1.9.1.db --pncp-db ..\dados\pncp.db --saida dados\analise_etapas\completo_20261122\fechado-aberto
python analises\etapas_completo_20261122\complementares.py --db dados\extracao\aberto-fechado_parser-1.9.1.db --pncp-db ..\dados\pncp.db --saida dados\analise_etapas\completo_20261122
python analises\etapas_completo_20261122\economia.py --db dados\extracao\aberto-fechado_parser-1.9.1.db --saida dados\analise_etapas\completo_20261122
```

Tempos nesta máquina: cerca de 7 min, 2 min, 15 min e 3 min. Os dois `analise_etapas.py` reproduzem exatamente as
rodadas de referência `2023-04_a_2026-10_parser-1.9.1/` e `fechado-aberto_2023-05_a_2026-10/`: todas as chaves do
`resultados.json` são iguais.
