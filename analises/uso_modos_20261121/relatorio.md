# Uso dos modos Aberto-Fechado e Fechado-Aberto: tendência e associações — 21/11/2026

Perguntas: (1) o uso do Aberto-Fechado (AF) e do Fechado-Aberto (FA) aumenta ou diminui com o tempo?
(2) a que esse uso está associado: unidade compradora, categoria do objeto, plataforma, esfera, região,
características da compra? O desenho foi fixado antes das estimativas em [protocolo.md](protocolo.md).
O que foi acrescentado depois está marcado como **posterior ao protocolo**.

## Resposta curta

1. **Tendência: o uso dos dois modos está praticamente estável.**
   - **AF:** cerca de 37–38% das compras no Compras.gov.br e 21% nas outras plataformas, sem tendência
     significativa depois de Holm. No Compras.gov.br, a parcela caiu de 41,9% (2023) para 37,4% (2025)
     porque entraram na base unidades que usam pouco o AF. Dentro das mesmas unidades, ela subiu um
     pouco (+1,2 p.p. por ano; p = 0,03; p Holm = 0,09).
   - **FA:** cai no Compras.gov.br (−0,25 p.p. por ano dentro da unidade; p Holm = 0,02, **o único teste
     de tendência significativo**) e sobe nas outras plataformas (+0,12 p.p. por ano dentro da unidade;
     p Holm = 0,09). A alta nas outras plataformas vem quase toda de uma plataforma, a Agili Software
     (municípios de Mato Grosso), que usa FA em 93–98% das suas compras.
2. **Associação: o modo é uma escolha da unidade compradora, não do objeto.**
   - A unidade explica **82–84%** da variação do uso de AF, e o órgão (CNPJ), 55–78%. A categoria do
     objeto explica **2%** sozinha e quase nada além da unidade (+0,1 p.p. de R²). O item de catálogo
     acrescenta cerca de 1 p.p. de R² além da UASG.
   - **Muitas unidades usam um modo só.** No Compras.gov.br, entre as unidades com 20 ou mais compras,
     49% quase nunca usam AF (< 5% das compras) e 23% usam quase sempre (> 95%).
   - O que distingue quem usa AF: a **plataforma** (Compras.gov.br bem acima da maioria das privadas), a
     **região Nordeste** (+16 p.p.) e **governos estaduais com política própria** (na esfera estadual,
     Ceará 98% de AF, Paraíba 82%, Espírito Santo 79% e Minas Gerais 71%; Goiás e Rio Grande do Sul,
     menos de 1%).
   - Dentro da mesma unidade, as características da compra quase não mudam o modo. Só o valor estimado
     tem associação significativa com o AF, e pequena (+0,4 p.p. quando o valor é 10 vezes maior).
     Três categorias de serviço e material ficam um pouco acima da média (apoio administrativo +4,9 p.p.,
     vigilância +2,7, conexões hidráulicas +1,7).
   - O FA é muito concentrado: 1% das unidades faz 88% das compras FA. Ele aparece sobretudo no
     Centro-Oeste (+2,5 p.p.), pela Agili em Mato Grosso, e em poucas unidades grandes (Secretaria de
     Estado da Saúde de SP, UFSC). Nenhuma categoria se associa ao FA depois de Holm.

## Amostra

Pregão Eletrônico, modos Aberto, Aberto-Fechado e Fechado-Aberto, publicação de nov/2022 a out/2026,
todas as plataformas. Unidade de análise: a compra.

| | Compras | Aberto-Fechado | Fechado-Aberto | Unidades compradoras | Órgãos (CNPJ) |
|---|---|---|---|---|---|
| Compras.gov.br | 327.550 | 37,8% | 0,55% | 5.554 | 3.037 |
| Outras plataformas | 743.357 | 20,8% | 0,83% | 29.644 | 12.459 |
| Total | 1.070.907 | 26,0% | 0,74% | 35.198 | 14.336 |

**Cuidado com 2023:** a base tem só 23,5 mil compras do Compras.gov.br em 2023, contra 104 mil em 2024.
Foi o ano de transição para a Lei 14.133, e quem já a usava era um grupo particular de unidades. A
parcela bruta de 2023 não se compara diretamente com a dos anos seguintes. Por isso a tendência principal
é estimada dentro da unidade, e há uma sensibilidade a partir de 2024.

## Parte 1 — tendência

### Parcela observada por ano

| Ano | AF Compras.gov.br | AF outras | FA Compras.gov.br | FA outras |
|---|---|---|---|---|
| 2023 | 41,9% | 20,5% | 0,95% | 0,48% |
| 2024 | 36,3% | 20,6% | 0,74% | 0,61% |
| 2025 | 37,4% | 20,7% | 0,45% | 0,91% |
| 2026 (jan–out) | 38,9% | 21,0% | 0,35% | 1,00% |

Parcela mensal em `mensal_modos.csv`; por plataforma e ano em `perfil_plataforma_ano.csv`.

### Testes de tendência (p.p. por ano)

T1 = bruta, com sazonalidade. **T2 = dentro da mesma unidade (principal; Holm sobre os 4 testes)**.
T3 = T2 com plataforma e características da compra. T2-2024 = T2 só a partir de jan/2024 (posterior ao
protocolo). Erro-padrão agrupado por CNPJ.

| Fonte | Modo | T1 bruta | **T2 dentro da unidade** (IC95) | p T2 | **p Holm** | T3 | T2-2024 |
|---|---|---|---|---|---|---|---|
| Compras.gov.br | AF | +0,08 (p 0,92) | +1,16 (+0,11 a +2,22) | 0,031 | 0,092 | +1,16 (0,03) | +1,08 (0,10) |
| Compras.gov.br | FA | **−0,24 (0,04)** | **−0,25 (−0,42 a −0,07)** | 0,006 | **0,023** | **−0,25 (0,006)** | **−0,20 (0,045)** |
| Outras plataformas | AF | +0,23 (0,54) | −0,28 (−0,62 a +0,06) | 0,109 | 0,109 | −0,23 (0,19) | −0,27 (0,13) |
| Outras plataformas | FA | **+0,20 (0,0001)** | +0,12 (+0,01 a +0,23) | 0,038 | 0,092 | +0,07 (0,18) | **+0,12 (0,005)** |
| Todas | AF | −0,29 (0,41) | +0,26 (0,27) | | | +0,28 (0,24) | +0,20 (0,46) |
| Todas | FA | +0,07 (0,25) | −0,02 (0,77) | | | −0,05 (0,36) | +0,01 (0,82) |

Em negrito, p < 0,05 (na coluna p Holm, p Holm < 0,05).

### Por semestre, dentro da unidade (ref. 2023-S1)

| Semestre | AF Compras.gov.br | FA Compras.gov.br | AF outras | FA outras |
|---|---|---|---|---|
| 2023-S2 | **−2,3** | −0,3 | **−1,9** | +0,3 |
| 2024-S1 | −0,8 | −0,3 | −1,2 | +0,2 |
| 2024-S2 | −0,1 | **−0,8** | **−1,6** | +0,2 |
| 2025-S1 | +1,0 | **−0,9** | **−1,9** | +0,4 |
| 2025-S2 | +0,3 | **−1,1** | **−2,0** | +0,4 |
| 2026-S1 | +0,3 | **−0,9** | **−2,2** | +0,5 |
| 2026-S2 (jul–out) | **+3,6** | **−1,1** | **−1,7** | +0,4 |

Em p.p., em negrito p < 0,05 (sem correção). `tendencia_semestres.csv` tem os IC.

- **AF no Compras.gov.br:** não há subida contínua. As unidades usaram menos AF no 2º semestre de 2023,
  voltaram ao nível do início de 2023 em 2024–2026 e subiram em jul–out/2026. A tendência linear
  positiva vem desse desenho em "U" e do último semestre, que ainda está incompleto.
- **AF nas outras plataformas:** uma queda de cerca de 2 p.p. depois de 2023-S1, depois estável.
- **FA no Compras.gov.br:** queda de cerca de 1 p.p. a partir do 2º semestre de 2024, mantida até 2026.
  É o resultado de tendência mais firme.
- **FA nas outras plataformas:** subida gradual de 0,2 a 0,5 p.p. dentro da unidade, sem nenhum
  semestre significativo isoladamente.

### De onde vem a mudança entre 2023 e 2025

Decomposição da variação da parcela (em p.p.). "Dentro" = mudança nas unidades presentes nos dois anos;
"entre" = mudança de peso entre elas; "entrada"/"saída" = unidades que entraram ou saíram.

| Fonte | Modo | 2023 | 2025 | Variação | Dentro | Entre | Cruzado | Entrada | Saída |
|---|---|---|---|---|---|---|---|---|---|
| Compras.gov.br | AF | 41,9 | 37,4 | −4,4 | +2,2 | −0,1 | −1,1 | **−5,4** | −0,1 |
| Compras.gov.br | FA | 0,95 | 0,45 | −0,50 | **−0,53** | −0,08 | +0,34 | −0,24 | +0,01 |
| Outras plataformas | AF | 20,5 | 20,7 | +0,1 | −0,2 | −0,6 | +0,1 | +0,4 | +0,5 |
| Outras plataformas | FA | 0,48 | 0,91 | +0,43 | +0,22 | +0,14 | −0,23 | **+0,40** | −0,10 |

- **AF no Compras.gov.br:** a queda bruta é toda de entrada. Em 2025, 55% das compras vêm de unidades
  que não estavam na base em 2023, e elas usam menos AF. As unidades antigas aumentaram o uso.
- **FA no Compras.gov.br:** a queda é de dentro. As mesmas unidades deixaram de usar FA.
- **FA nas outras plataformas:** a subida vem sobretudo de unidades novas.

### Por que o FA sobe nas outras plataformas (posterior ao protocolo)

A plataforma **Agili Software** faz 2.722 das 7.948 compras FA da base (34%), 2.052 delas em
municípios de Mato Grosso (Juína, Sorriso, Rondonópolis, Nova Bandeirantes, Nobres e outros). Nela, o FA
é o padrão:

| Ano | Compras na Agili | Unidades | % FA | % AF |
|---|---|---|---|---|
| 2023 | 14 | 2 | 100 | 0 |
| 2024 | 588 | 12 | 98,1 | 0,5 |
| 2025 | 1.151 | 11 | 94,0 | 5,7 |
| 2026 | 1.123 | 17 | 93,4 | 5,0 |

Sem a Agili, a parcela de FA nas outras plataformas é 0,43% (2023), 0,35% (2024), 0,51% (2025) e 0,52%
(2026): uma alta bem menor. Em Mato Grosso, a parcela de FA foi de 1,1% (2023) para 16,2% (2026). Não dá
para saber pelos dados se a Agili só oferece o FA ou se ele é a opção padrão da plataforma.

### Adoção pelas unidades

Parcela das unidades com 5 ou mais compras no ano que usaram o modo ao menos uma vez:

| Ano | AF Compras.gov.br | FA Compras.gov.br | AF outras | FA outras |
|---|---|---|---|---|
| 2023 | 53,8% | 4,8% | 30,9% | 1,6% |
| 2024 | 49,4% | 5,2% | 30,0% | 2,1% |
| 2025 | 49,6% | 3,9% | 30,9% | 3,0% |
| 2026 | 56,6% | 3,0% | 28,5% | 2,7% |

## Parte 2 — associação

### Quanto cada dimensão explica (R²)

| Base | Efeitos fixos | R² AF | R² ajust. AF | R² FA | R² ajust. FA |
|---|---|---|---|---|---|
| Compras.gov.br, compras¹ | mês | 0,002 | 0,002 | 0,003 | 0,003 |
| | categoria | 0,024 | 0,022 | 0,003 | 0,001 |
| | órgão (CNPJ) | 0,551 | 0,545 | 0,102 | 0,091 |
| | unidade (UASG) | 0,837 | 0,833 | 0,293 | 0,276 |
| | mês + unidade + categoria | 0,838 | 0,834 | 0,297 | 0,278 |
| | mês + unidade × categoria | 0,893 | 0,863 | 0,468 | 0,314 |
| Outras plataformas, compras | mês | 0,000 | 0,000 | 0,001 | 0,001 |
| | plataforma | 0,020 | 0,020 | 0,008 | 0,008 |
| | órgão (CNPJ) | 0,779 | 0,775 | 0,601 | 0,595 |
| | unidade | 0,824 | 0,818 | 0,689 | 0,679 |
| Compras.gov.br, itens² | item de catálogo | 0,169 | 0,141 | 0,093 | 0,062 |
| | UASG | 0,845 | 0,845 | 0,355 | 0,354 |
| | mês + UASG + item de catálogo | 0,861 | 0,856 | 0,401 | 0,380 |
| | mês + UASG × item de catálogo | 0,941 | 0,919 | 0,690 | 0,570 |

¹ 179.362 compras de unidades que compram a mesma categoria mais de uma vez (mesma amostra em todas as
linhas). ² 3,4 milhões de itens com código de catálogo, jan/2023 a jun/2026, em pares UASG × item com
mais de um item.

- **A unidade sozinha explica 82–84% da variação no AF.** Saber quem compra praticamente determina o
  modo.
- **Categoria e item quase não acrescentam:** +0,1 p.p. de R² pela categoria e +1,1 p.p. pelo item de
  catálogo, além da unidade. Sozinhos, eles explicam 2% (categoria) e 17% (item, porque cada item tende
  a ser comprado por poucas unidades).
- **A combinação unidade × categoria (ou × item) explica mais** (R² ajustado de 0,86 e 0,92): algumas
  unidades usam um modo para certos objetos e outro modo para os demais. Esse padrão é de cada unidade e
  não se generaliza entre unidades.
- **A plataforma sozinha explica pouco (2%) nas outras plataformas**, porque dentro de cada plataforma há
  unidades dos dois tipos. O órgão explica 78%.
- **No FA**, a unidade explica menos no Compras.gov.br (29%) do que nas outras plataformas (69%). No
  Compras.gov.br, várias unidades usam o FA em poucas compras, misturado com os outros modos.

### Concentração nas unidades

Unidades com 20 ou mais compras no período:

| Fonte | Modo | Unidades | Nunca usaram | < 5% | 5–95% | > 95% | Compras do modo feitas pelo 1% das unidades que mais usam |
|---|---|---|---|---|---|---|---|
| Compras.gov.br | AF | 2.654 | 35% | 49% | 28% | 23% | 36% |
| Compras.gov.br | FA | 2.654 | 89% | 97% | 3% | 0,04% | 71% |
| Outras plataformas | AF | 7.918 | 60% | 69% | 19% | 12% | 43% |
| Outras plataformas | FA | 7.918 | 95% | 98% | 2% | 0,35% | 91% |

A distribuição da parcela de AF por unidade tem dois picos: 0% e 90–100% (`distribuicao_unidades.csv`).

**Unidades com mais compras AF:** Estado do Ceará (5.403 compras, 99% AF), Fundo Municipal de Saúde (SP,
95%), Secretaria da Saúde do Ceará (outra plataforma, 99,8%), Fundo Municipal de Saúde de Itatiaia (74%),
uma diretoria de licitações de SC (99,5%), Secretaria de Saúde da Bahia (Licitações-E BB, 98,7%) e os
Estados do Espírito Santo (99,9%) e de São Paulo (99,6%).

**Unidades com mais compras FA:** Secretaria de Estado da Saúde de SP (250 compras, 56% FA), prefeituras
de Mato Grosso (Juína 100%, Sorriso 99%, Rondonópolis 86%, Nova Ubiratã 69%, Nova Bandeirantes 100%),
Mirador-PR (100%), Nilópolis-RJ (87%), Carnaúba dos Dantas-RN (98%) e a UFSC (45%).
Lista completa em `unidades_top.csv`.

### Perfil de quem usa: A1 (todas as plataformas, sem efeito fixo de unidade)

Diferença na probabilidade de a compra ser AF ou FA, em p.p., mantendo as outras variáveis e o mês
fixos. Referências: esfera municipal, Sudeste, Compras.gov.br. Holm sobre todos os coeficientes de cada
modelo. Base de AF = 26,0%; de FA = 0,74%.

| Variável | AF | p Holm | FA | p Holm |
|---|---|---|---|---|
| Esfera federal | +11,8 | 0,10 | −0,73 | 0,09 |
| Esfera estadual | +5,3 | 1,00 | −0,65 | 0,14 |
| Distrito Federal | +20,6 | 1,00 | **−3,31** | **< 0,001** |
| Judiciário | +7,1 | 1,00 | −0,31 | 1,00 |
| Legislativo | −0,4 | 1,00 | −0,20 | 1,00 |
| Região Norte | −5,2 | 0,47 | +0,04 | 1,00 |
| **Região Nordeste** | **+15,6** | **< 0,001** | +0,22 | 1,00 |
| Região Centro-Oeste | +2,9 | 1,00 | **+2,46** | **0,004** |
| Região Sul | −2,2 | 1,00 | −0,01 | 1,00 |
| Plataforma Novo BBMNET | **−26,4** | **< 0,001** | **−0,84** | **< 0,001** |
| Plataforma AZ Informática | **−21,4** | **< 0,001** | **−1,12** | **< 0,001** |
| Plataforma Licitanet | **−20,5** | **< 0,001** | −0,31 | 1,00 |
| Plataforma BNC | **−18,6** | **< 0,001** | −0,46 | 0,25 |
| Plataforma Licitar Digital | **−16,2** | **< 0,001** | **−0,67** | **< 0,001** |
| Plataforma ECustomize | **−14,2** | **< 0,001** | **−0,81** | **< 0,001** |
| Demais plataformas (inclui Agili) | **−10,5** | **0,012** | **+0,87** | **0,001** |
| Plataforma Betha | −9,5 | 0,53 | **−1,02** | **< 0,001** |
| Plataforma Licitações-E BB | −8,9 | 1,00 | −0,52 | 0,09 |
| Plataforma Governançabrasil | −7,2 | 1,00 | **−0,68** | **0,003** |
| Plataforma BLL | −6,2 | 1,00 | **−0,73** | **< 0,001** |
| Plataforma Elotech | −4,8 | 1,00 | −0,20 | 1,00 |
| Plataforma IPM | +1,8 | 1,00 | +0,89 | 1,00 |
| Registro de preços | +2,8 | 0,47 | +0,13 | 1,00 |
| Log do valor estimado (por unidade de log) | **+0,73** | **0,001** | −0,01 | 1,00 |
| Sem valor estimado | **+12,0** | **0,002** | −0,10 | 1,00 |
| Log do nº de itens | **−0,99** | **0,003** | **+0,06** | **0,012** |
| Parcela de material | +1,1 | 1,00 | −0,14 | 1,00 |
| Parcela Maior desconto | −1,2 | 1,00 | +0,33 | 0,60 |
| Parcela exclusiva ME/EPP | +2,3 | 0,58 | −0,22 | 0,83 |
| Parcela com cota ME/EPP | +6,8 | 1,00 | +2,40 | 1,00 |
| Parcela com orçamento sigiloso | +1,7 | 1,00 | +0,48 | 1,00 |

- **Plataforma:** mesmo comparando compras da mesma esfera, região e perfil, as compras nas plataformas
  privadas têm de 10 a 26 p.p. menos chance de serem AF que as do Compras.gov.br. A exceção é a IPM, igual
  ao Compras.gov.br. Como a plataforma quase não varia dentro da unidade, isso pode refletir tanto a
  plataforma (opção padrão, interface) quanto quem escolhe cada plataforma.
- **Região:** o Nordeste usa muito mais o AF, o que é coerente com o uso quase exclusivo do AF pelos
  governos estaduais do Ceará e da Paraíba. O Centro-Oeste usa mais o FA, pela Agili em Mato Grosso.
- **Esfera:** a federal tende a usar mais o AF (+11,8 p.p.), mas a diferença não passa na correção de
  Holm (p bruto 0,005). Os erros-padrão são largos porque poucos órgãos grandes pesam muito.
- **Compra:** compras de valor maior, sem valor informado e com menos itens usam um pouco mais o AF.

### Dentro da mesma unidade: A2

Quando a mesma unidade escolhe entre os modos, o tipo de compra quase não importa:

| Fonte | Modo | Associações significativas depois de Holm |
|---|---|---|
| Compras.gov.br | AF | Log do valor estimado: +0,18 p.p. por unidade de log (p Holm 0,013); cerca de +0,4 p.p. para um valor 10 vezes maior |
| Compras.gov.br | FA | nenhuma |
| Outras plataformas | AF | nenhuma |
| Outras plataformas | FA | Parcela de material: −0,12 p.p. (p Holm 0,001); compras de serviço usam um pouco mais o FA |

Registro de preços, critério, benefício ME/EPP, sigilo e nº de itens não têm associação significativa
com a escolha dentro da unidade. Os intervalos são estreitos: no AF do Compras.gov.br, o registro de
preços fica entre −1,7 e +2,1 p.p.

### Categorias associadas, dentro da unidade: A4

148 categorias elegíveis (≥ 300 compras em ≥ 30 unidades). Efeito = diferença em relação à categoria
média, na mesma unidade e mês. O desvio-padrão dos efeitos é de 1,0 p.p. no AF e 0,24 p.p. no FA: as
categorias diferem pouco.

**AF, significativas depois de Holm (3 de 148):**

| Categoria | Exemplos | Compras | Efeito | p Holm |
|---|---|---|---|---|
| S911 (serviço) | apoio administrativo, terceirização de mão de obra | 1.408 | +4,9 p.p. | < 0,001 |
| S852 (serviço) | vigilância armada, brigadista | 2.337 | +2,7 p.p. | 0,004 |
| M4730 (material) | conexões hidráulicas | 1.417 | +1,7 p.p. | 0,012 |

No outro extremo, sem significância depois de Holm: materiais de construção (tijolo, bloco, −2,4 p.p.),
quadros elétricos (−2,0) e obras civis (−1,9). **FA: nenhuma categoria significativa depois de Holm**
(18 com p < 0,05 sem correção, perto das 7 esperadas por acaso). Tabela completa, com descrições, em
`associacao_categorias.csv`.

## Leitura

1. **O modo é um hábito ou uma regra da unidade.** A unidade explica mais de 80% da escolha do AF, e
   quase metade das unidades usa um modo só. O objeto, o valor e o tipo de compra explicam muito pouco
   dentro da unidade. Isso é coerente com regulamentos e práticas locais, por exemplo decretos estaduais
   (na esfera estadual, Ceará 98% e Espírito Santo 79% de AF; Goiás e Rio Grande do Sul, menos de 1%) e
   configurações padrão das plataformas.
2. **Para a medida de desconto do projeto**, isso confirma que comparar AF e Aberto sem controlar a
   unidade mistura o efeito do modo com quem o usa. Também mostra que o pareamento UASG × item só aproveita as
   unidades que usam os dois modos. Só 28% das unidades do Compras.gov.br com 20 ou mais compras têm uso
   misto de fato (entre 5% e 95% de AF), e elas não são necessariamente representativas das demais.
3. **O uso não está mudando muito.** O AF se mantém estável. O FA, que sempre foi raro, está sumindo no
   Compras.gov.br e cresce nas outras plataformas por causa de uma plataforma e de uma região.

## Limitações

- Associativo: não identifica por que a unidade escolhe o modo, que pode ser uma norma local, a
  configuração da plataforma ou a preferência do pregoeiro.
- A base de 2023 é pequena e composta por quem adotou cedo a Lei 14.133; os resultados brutos que
  comparam 2023 com os anos seguintes devem ser lidos com cuidado.
- A categoria só existe no Compras.gov.br. Nas outras plataformas não há catálogo, e a unidade é o
  CNPJ do órgão mais `codigo_unidade`, que pode não corresponder a uma UASG.
- O R² de efeitos fixos com muitas unidades pequenas superestima o poder explicativo; o R² ajustado
  corrige parte disso, e as conclusões não mudam com ele.
- O erro-padrão dos efeitos de categoria (A4) ignora o erro dos efeitos fixos de unidade e mês
  estimados. Com 148 categorias e milhares de unidades, a aproximação deve ser razoável, mas os p ficam
  um pouco otimistas.
- A análise da Agili e a sensibilidade a partir de 2024 foram feitas depois de ver os dados.

## Reprodução

```powershell
.\.venv\Scripts\python.exe analises\uso_modos_20261121\extracao.py          # ~10 min
.\.venv\Scripts\python.exe analises\uso_modos_20261121\uso_modos.py desc conc
.\.venv\Scripts\python.exe analises\uso_modos_20261121\uso_modos.py tend    # ~15 min
.\.venv\Scripts\python.exe analises\uso_modos_20261121\uso_modos.py perfil
.\.venv\Scripts\python.exe analises\uso_modos_20261121\uso_modos.py cat
.\.venv\Scripts\python.exe analises\uso_modos_20261121\uso_modos.py r2      # usa dados/analise_desfecho/base_itens.pkl
```

Rodar as partes em processos separados evita falta de memória. A extração lê `dados/pncp.db` somente
para leitura e grava em `dados/analise_uso_modos/` (fora do git). A parte `r2` em nível de item usa a base
da análise de desfecho (`analises/desfecho_modos_20261121/testes_desfecho.py`).

Saídas nesta pasta: `tendencia.csv`, `tendencia_semestres.csv`, `tendencia_decomposicao.csv`,
`adocao_unidades.csv`, `mensal_modos.csv`, `perfil_*.csv`, `associacao_perfil.csv`,
`associacao_r2.csv`, `associacao_categorias.csv`, `concentracao_unidades.csv`,
`distribuicao_unidades.csv`, `unidades_top.csv`.
