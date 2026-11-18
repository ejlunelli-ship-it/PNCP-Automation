# Etapa aberta × etapa fechada nos PDFs Aberto-Fechado (2026-02, 03, 04, 08)

Claude, 18/11/2026. Script `analisar.py` (reexecutável, ~30 s); números em `resultados.json`,
tabelas em `tabelas.xlsx` e dados por item em `por_item.csv.gz`.

## Base

- `PNCP-Automation/dados/extracao/aberto-fechado_2026-08.db`, tabela `itens` (apesar do nome, tem os
  quatro meses), parser 1.7.1/1.7.2, versão de 18/11/2026 10:50. Aberta só para leitura; o script
  confere que o mtime não mudou. O `pncp.db` não foi usado.
- Funil: 180.909 itens → 180.799 OK (REVISAR fora, decisão de 18/11) → 178.124 Menor Preço →
  173.458 com lance aberto → **166.596 itens** com desconto entre −100% e 99% (mesmo filtro do
  `matching_desconto.py`). São 8.018 compras de 1.203 UASGs. Nenhum item em grupo.
- Definições (docs/01 e docs/05): desconto = 1 − valor/estimado; "após a fechada" = mín(melhor aberto,
  melhor fechado); item sem lance fechado tem ganho zero. IC 95% por bootstrap de conglomerados (compra,
  2.000 réplicas).

## Resultados principais

| Medida (% do estimado) | Média | IC 95% | Mediana |
|---|---|---|---|
| Desconto da etapa aberta | 20,2 | 19,4 – 21,0 | 12,7 |
| Desconto após a etapa fechada | 35,6 | 34,8 – 36,4 | 35,3 |
| **Ganho da etapa fechada (p.p.)** | **15,4** | 15,0 – 15,9 | 9,2 |
| Ganho relativo (% abaixo do melhor aberto) | 19,0 | 18,5 – 19,5 | 13,3 |
| Desconto final (lance aceito/negociado) | 34,4 | 33,7 – 35,1 | 32,3 |

- 87,9% dos itens tiveram lance na etapa fechada; em 78,8% ela melhorou o preço (89,6% dos que tiveram lance).
- Comparação direta (itens com lance fechado, n = 145.180): o melhor lance fechado ficou 15,4 p.p. abaixo do
  melhor aberto (mediana 12,0); fechado melhor em 90,5%, pior em 9,1%. Wilcoxon e t: p < 10⁻¹⁵.
  (1.314 lances fechados absurdos, fora de −100% a 99%, ficaram de fora deste teste; não afetam o mínimo.)
- Em valor: sobre R$ 28,2 bi estimados, a etapa fechada reduziu **R$ 3,08 bi (13,9%)** em relação ao
  melhor lance aberto. Desconto ponderado pelo valor: 21,3% na aberta → 32,2% após a fechada.
- O resultado final fica perto do melhor lance da disputa: igual em 69% dos itens adjudicados, pior em 26%
  (desclassificação do melhor) e melhor em 5% (negociação); em média 4,6 p.p. abaixo do "após a fechada".

## Heterogeneidade

- **Por mês** o padrão é estável: ganho relativo de 18,1% (fev), 20,0% (mar), 19,4% (abr), 18,3% (ago).
  Kruskal-Wallis rejeita igualdade (p ≈ 0, efeito de n grande); na regressão só março difere de fevereiro
  (+1,4 p.p., p = 0,03).
- **Por número de fornecedores**: com 1 fornecedor quase não há etapa fechada (13%; ganho 1,7%); com 2, ganho
  de 12,1%; de 3 em diante, 19–22%. O desconto da etapa aberta cresce muito com a concorrência (−4% com 1,
  37% com mais de 10); o ganho da fechada cresce até 6–10 fornecedores e cai um pouco depois.
- **Por valor total do item** (quintis): ganho relativo praticamente constante (17,7% a 19,8%).
- Regressão (EP agrupado por UASG, n = 166.596): ganho relativo = +4,0 p.p. por log de fornecedores
  (p < 0,001) e −0,33 p.p. por log do valor total (p < 0,001), controlando mês.

## Controle por material × serviço e orçamento aberto × sigiloso

`ligar_pncp.py` traz `material_ou_servico` e `orcamento_sigiloso` do `dados/pncp.db` (somente leitura;
tamanho e mtime conferidos antes e depois, iguais aos registrados), pela chave do docs/07 §7 (`id_compra` do
nome do PDF + item, `registro_principal = 1`). As 8.326 compras foram achadas; 2 itens com registro duplo
foram descartados. Ligaram **162.339 dos 166.596 itens (97,4%)**. Todas as compras ligadas são Aberto-Fechado
no banco. No PDF o valor estimado aparece também nos itens sigilosos, então o desconto pode ser calculado.

| Estrato | Itens | Compras | Desc. aberta | Desc. após fechada | Ganho (p.p.) [IC 95%] | Ganho relativo [IC 95%] |
|---|---|---|---|---|---|---|
| Material | 155.377 | 6.223 | 20,0 | 35,5 | 15,5 [15,0–15,9] | 18,9 [18,5–19,4] |
| Serviço | 6.962 | 1.863 | 23,5 | 38,7 | 15,2 [13,4–17,0] | 20,0 [17,8–22,2] |
| Orçamento aberto | 131.097 | 5.584 | 20,5 | 35,7 | 15,2 [14,8–15,7] | 19,2 [18,7–19,8] |
| Orçamento sigiloso | 31.242 | 2.521 | 19,0 | 35,4 | 16,4 [15,6–17,3] | 17,9 [17,2–18,7] |
| Material, aberto | 124.757 | 4.105 | 20,3 | 35,6 | 15,2 [14,7–15,7] | 19,2 [18,6–19,8] |
| Material, sigiloso | 30.620 | 2.206 | 18,8 | 35,2 | 16,4 [15,6–17,3] | 17,9 [17,2–18,6] |
| Serviço, aberto | 6.340 | 1.539 | 23,0 | 38,2 | 15,3 [13,5–17,3] | 20,2 [18,0–22,6] |
| Serviço, sigiloso | 622 | 329 | 29,3 | 43,9 | 14,6 [11,5–18,3] | 18,0 [14,1–22,5] |

Regressão com os dois controles e a interação, além de log de fornecedores, log do valor total e mês
(EP agrupado por UASG, n = 162.339, 1.202 UASGs; coeficientes em p.p.):

| Variável dependente | Serviço | Sigiloso | Serviço × sigiloso |
|---|---|---|---|
| Ganho relativo | +0,2 (p = 0,89) | −1,0 (p = 0,10) | −0,2 (p = 0,94) |
| Ganho (p.p. do estimado) | +0,4 (p = 0,65) | +1,4 (p = 0,05) | −1,6 (p = 0,49) |
| Desconto da etapa aberta | −3,5 (p = 0,001) | −0,9 (p = 0,64) | +10,3 (p = 0,002) |
| Desconto após a fechada | −3,1 (p = 0,04) | +0,5 (p = 0,71) | +8,7 (p = 0,005) |
| Desconto final | −1,8 (p = 0,21) | +1,6 (p = 0,17) | +1,3 (p = 0,69) |

- **O ganho da etapa fechada não depende do tipo de objeto nem do sigilo.** Nenhum coeficiente é
  significativo a 5% no ganho relativo. No ganho em p.p., o sigilo fica no limite (+1,4; p = 0,05), mas o
  sinal se inverte na medida relativa (−1,0). Isso reflete a base diferente, não um efeito claro.
- Os controles quase não mudam o efeito do número de fornecedores (+4,0 p.p. por log no ganho relativo).
- **Nível do desconto:** serviços com orçamento aberto têm descontos uns 3 p.p. menores que materiais com
  os mesmos fornecedores e valor. Serviços sigilosos têm descontos bem maiores (interação de +9 a +10 p.p.),
  mas são só 622 itens em 329 compras. A diferença some no desconto final.
- O total de 166.596 itens cai para 162.339 com a ligação. A estimativa geral praticamente não muda.

## Tabela completa dos grupos e testes de diferença de médias

Script `testes_grupos.py`; saídas `estatisticas_grupos.csv`, `testes_grupos.csv` e `testes_grupos.xlsx`. Mesma amostra
ligada da seção anterior (162.339 itens). Valores em %, exceto o ganho em p.p. do estimado.

### Médias por grupo (desvio-padrão entre parênteses)

| Tipo | Orçamento | Itens | Compras | UASGs | Desc. aberta | Desc. após fechada | Ganho (p.p.) | Ganho relativo | Desc. final | Teve lance fechado | Fechada melhorou |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Material | todos | 155.377 | 6.223 | 947 | 20,0 (29,5) | 35,5 (28,8) | 15,5 (18,2) | 18,9 (19,6) | 34,4 (24,8) | 87,7 (32,8) | 78,6 (41,0) |
| Serviço | todos | 6.962 | 1.863 | 738 | 23,5 (24,6) | 38,7 (25,3) | 15,2 (16,5) | 20,0 (19,4) | 34,5 (24,3) | 92,8 (25,9) | 86,1 (34,6) |
| todos | Aberto | 131.097 | 5.584 | 1.083 | 20,5 (25,1) | 35,7 (26,9) | 15,2 (17,2) | 19,2 (19,8) | 34,3 (24,6) | 87,7 (32,8) | 80,2 (39,9) |
| todos | Sigiloso | 31.242 | 2.521 | 221 | 19,0 (42,7) | 35,4 (35,2) | 16,4 (21,7) | 17,9 (18,6) | 34,7 (25,5) | 88,9 (31,4) | 73,4 (44,2) |
| Material | Aberto | 124.757 | 4.105 | 844 | 20,3 (25,2) | 35,6 (27,1) | 15,2 (17,2) | 19,2 (19,9) | 34,3 (24,6) | 87,5 (33,1) | 79,8 (40,1) |
| Material | Sigiloso | 30.620 | 2.206 | 184 | 18,8 (42,7) | 35,2 (35,2) | 16,4 (21,7) | 17,9 (18,5) | 34,7 (25,4) | 88,9 (31,4) | 73,5 (44,1) |
| Serviço | Aberto | 6.340 | 1.539 | 658 | 22,9 (22,1) | 38,2 (24,0) | 15,3 (16,0) | 20,2 (19,2) | 34,6 (23,9) | 93,0 (25,5) | 87,6 (33,0) |
| Serviço | Sigiloso | 622 | 329 | 109 | 29,3 (41,8) | 43,9 (36,1) | 14,6 (21,3) | 18,0 (20,9) | 33,9 (27,8) | 90,2 (29,8) | 70,7 (45,5) |

### Diferenças de médias (grupo B − grupo A)

Cada célula traz a diferença, o IC 95% e o p do teste t com EP agrupado por UASG, que é a inferência principal.
Marcas: \*\*\* p < 0,001; \*\* p < 0,01; \* p < 0,05; † p < 0,10. Em **negrito**, o que continua significativo a 5%
depois da correção de Holm para as 42 comparações. Os p do Welch e do Mann-Whitney (item como unidade) estão no
CSV; quase todos são < 0,001 porque ignoram que itens da mesma UASG não são independentes.

| Variável | Material × Serviço (todos) | Aberto × Sigiloso (todos) | Material: aberto × sigiloso | Serviço: aberto × sigiloso | Orç. aberto: material × serviço | Orç. sigiloso: material × serviço |
|---|---|---|---|---|---|---|
| Desc. aberta | +3,48\*\* [0,9; 6,1] p = 0,008 | -1,44 [-5,0; 2,1] p = 0,430 | -1,52 [-5,1; 2,1] p = 0,412 | +6,32† [-0,8; 13,4] p = 0,083 | +2,61† [-0,0; 5,3] p = 0,054 | +10,45\*\* [2,9; 18,0] p = 0,007 |
| Desc. após fechada | +3,23\* [0,1; 6,3] p = 0,042 | -0,28 [-3,1; 2,6] p = 0,850 | -0,32 [-3,2; 2,6] p = 0,829 | +5,67\* [0,4; 11,0] p = 0,037 | +2,66 [-0,7; 6,0] p = 0,123 | **+8,66\*\*\* [3,7; 13,6] p < 0,001** |
| Ganho (p.p.) | -0,25 [-2,0; 1,5] p = 0,779 | +1,16† [-0,2; 2,5] p = 0,094 | +1,20† [-0,2; 2,6] p = 0,090 | -0,64 [-4,9; 3,6] p = 0,765 | +0,05 [-1,8; 1,9] p = 0,959 | -1,79 [-5,8; 2,3] p = 0,386 |
| Ganho relativo | +1,06 [-1,2; 3,3] p = 0,357 | -1,34\* [-2,5; -0,1] p = 0,029 | -1,30\* [-2,5; -0,1] p = 0,038 | -2,19 [-7,2; 2,9] p = 0,395 | +1,00 [-1,5; 3,5] p = 0,423 | +0,11 [-4,4; 4,6] p = 0,963 |
| Desc. final | +0,15 [-2,9; 3,2] p = 0,925 | +0,41 [-2,0; 2,8] p = 0,734 | +0,44 [-2,0; 2,8] p = 0,716 | -0,67 [-6,5; 5,1] p = 0,820 | +0,29 [-3,0; 3,6] p = 0,865 | -0,83 [-5,5; 3,9] p = 0,728 |
| Teve lance fechado | **+5,02\*\*\* [3,2; 6,9] p < 0,001** | +1,21 [-0,9; 3,3] p = 0,261 | +1,46 [-0,7; 3,6] p = 0,176 | -2,82 [-8,5; 2,9] p = 0,331 | **+5,56\*\*\* [3,5; 7,6] p < 0,001** | +1,29 [-3,3; 5,9] p = 0,584 |
| Fechada melhorou | **+7,52\*\*\* [5,1; 10,0] p < 0,001** | **-6,74\*\*\* [-9,3; -4,2] p < 0,001** | **-6,30\*\*\* [-8,9; -3,8] p < 0,001** | **-16,85\*\*\* [-26,1; -7,6] p < 0,001** | **+7,78\*\*\* [5,3; 10,3] p < 0,001** | -2,76 [-11,3; 5,8] p = 0,526 |

Grupo A × grupo B em cada coluna: Material × Serviço; Aberto × Sigiloso; dentro de material ou serviço,
orçamento aberto × sigiloso; dentro de orçamento aberto ou sigiloso, material × serviço.

### Diferenças ajustadas pelo número de licitantes

O número de licitantes é a `quantidade_fornecedores` do PDF (propostas do item). A diferença ajustada é o
coeficiente da dummy do grupo B numa regressão com efeito fixo para cada número de licitantes (1 a 20 um a um,
21–30 e 31 ou mais), com EP agrupado por UASG. A versão com log(licitantes) linear está no CSV
(`dif_ajust_log_licitantes`, `p_ajust_log`) e dá o mesmo quadro. Mesmas marcas e mesmo critério de negrito
(Holm, agora sobre as 42 diferenças ajustadas).

Número médio de licitantes por grupo:

| Tipo | Orçamento | Média | DP |
|---|---|---|---|
| Material | todos | 8,7 | 7,0 |
| Serviço | todos | 12,5 | 10,6 |
| todos | Aberto | 9,0 | 7,4 |
| todos | Sigiloso | 8,3 | 6,4 |
| Material | Aberto | 8,8 | 7,2 |
| Material | Sigiloso | 8,2 | 6,3 |
| Serviço | Aberto | 12,6 | 10,7 |
| Serviço | Sigiloso | 11,3 | 9,9 |

| Variável | Material × Serviço (todos) | Aberto × Sigiloso (todos) | Material: aberto × sigiloso | Serviço: aberto × sigiloso | Orç. aberto: material × serviço | Orç. sigiloso: material × serviço |
|---|---|---|---|---|---|---|
| Licitantes (dif. bruta) | +3,80 [2,7; 4,9] p < 0,001 | -0,74 [-1,4; -0,1] p = 0,017 | -0,62 [-1,2; -0,0] p = 0,047 | -1,35 [-4,4; 1,7] p = 0,388 | +3,80 [2,6; 5,0] p < 0,001 | +3,07 [0,2; 5,9] p = 0,037 |
| Desc. aberta | -2,83\*\* [-4,8; -0,8] p = 0,005 | -0,41 [-3,9; 3,1] p = 0,817 | -0,72 [-4,3; 2,8] p = 0,693 | +8,49\*\* [2,3; 14,7] p = 0,007 | **-3,94\*\*\* [-6,0; -1,9] p < 0,001** | +7,31\* [1,1; 13,6] p = 0,023 |
| Desc. após fechada | -2,54† [-5,3; 0,2] p = 0,071 | +0,33 [-2,4; 3,1] p = 0,818 | +0,05 [-2,8; 2,9] p = 0,969 | +8,12\*\* [3,2; 13,1] p = 0,001 | -3,68\* [-6,6; -0,7] p = 0,015 | **+7,13\*\* [2,9; 11,4] p = 0,001** |
| Ganho (p.p.) | +0,29 [-1,5; 2,1] p = 0,750 | +0,74 [-0,5; 2,0] p = 0,260 | +0,77 [-0,5; 2,1] p = 0,249 | -0,37 [-4,3; 3,6] p = 0,856 | +0,26 [-1,6; 2,2] p = 0,789 | -0,18 [-4,2; 3,9] p = 0,931 |
| Ganho relativo | +0,40 [-1,9; 2,7] p = 0,736 | -1,57\*\* [-2,7; -0,4] p = 0,007 | -1,57\*\* [-2,7; -0,4] p = 0,008 | -1,51 [-6,5; 3,4] p = 0,550 | -0,06 [-2,5; 2,4] p = 0,964 | +1,19 [-3,5; 5,9] p = 0,621 |
| Desc. final | -3,19\* [-5,9; -0,5] p = 0,021 | +1,08 [-1,3; 3,4] p = 0,367 | +0,97 [-1,4; 3,3] p = 0,422 | +1,30 [-4,7; 7,3] p = 0,672 | -3,58\* [-6,5; -0,7] p = 0,016 | -0,91 [-5,5; 3,7] p = 0,698 |
| Teve lance fechado | +0,22 [-1,4; 1,8] p = 0,790 | +0,97 [-0,4; 2,4] p = 0,181 | +0,97 [-0,4; 2,4] p = 0,175 | +0,22 [-5,2; 5,6] p = 0,937 | +0,22 [-1,5; 1,9] p = 0,804 | +0,85 [-4,3; 6,0] p = 0,746 |
| Fechada melhorou | **+3,76\*\* [1,5; 6,0] p = 0,001** | **-7,10\*\*\* [-9,3; -4,9] p < 0,001** | **-6,86\*\*\* [-9,1; -4,6] p < 0,001** | -14,55\*\* [-24,1; -5,0] p = 0,003 | +3,41\*\* [1,1; 5,7] p = 0,003 | -2,40 [-11,8; 7,0] p = 0,618 |

#### O que muda com o controle

1. **Material × serviço:** serviços têm 3,8 licitantes a mais em média. Isso explica a maior parte das vantagens
   brutas dos serviços. Com o controle, o sinal do desconto se inverte: serviços ficam 2,8 p.p. abaixo na etapa aberta
   (p = 0,005) e 3,2 abaixo no desconto final (p = 0,02). A maior frequência de lance fechado some (+0,2; p = 0,79).
   A fechada ainda melhora o preço mais vezes em serviços (+3,8; p = 0,001, que resiste a Holm).
   Com orçamento aberto, o desconto da etapa aberta em serviços fica 3,9 p.p. menor (p < 0,001, resiste a Holm).
2. **Aberto × sigiloso:** o sigiloso tem 0,7 licitante a menos (p = 0,02). Com o controle, o ganho relativo da fechada fica
   1,6 p.p. menor no sigiloso (p = 0,007; não resiste a Holm, p = 0,22). A fechada melhora o preço 7,1 p.p. menos vezes,
   o que resiste a Holm. Os descontos e o desconto final continuam iguais.
3. **Serviços com orçamento sigiloso:** a vantagem de desconto se mantém ou aumenta (+8,1 p.p. depois da fechada frente
   a serviços com orçamento aberto; +7,1 frente a materiais sigilosos, que resiste a Holm). O desconto final, porém, não
   difere, e continua valendo o cuidado com a amostra pequena (622 itens, 109 UASGs).
4. **Ganho da etapa fechada:** continua sem diferença entre material e serviço em qualquer recorte. A única diferença
   que aparece é a do sigilo no ganho relativo (cerca de −1,6 p.p.), que não resiste à correção de Holm.

### Leitura (diferenças brutas)

1. **Ganho da etapa fechada (em p.p. e relativo):** não difere entre material e serviço em nenhum recorte.
   Entre orçamento aberto e sigiloso, o ganho relativo é 1,3 p.p. menor no sigiloso (p = 0,03; 0,04 só em
   materiais). Já o ganho em p.p. é 1,2 maior (p = 0,09). Nada disso resiste à correção de Holm.
2. **Desconto final:** nenhuma diferença em nenhum recorte (todos os p > 0,7). Os grupos chegam ao mesmo
   resultado médio, cerca de 34% abaixo do estimado.
3. **Nível do desconto nas etapas:** serviços têm desconto maior que materiais (+3,5 p.p. na aberta,
   +3,2 após a fechada). A diferença vem sobretudo dos serviços com orçamento sigiloso (+10,4 e +8,7 p.p.; só o
   segundo resiste a Holm). São 622 itens de 109 UASGs, então é pouco para generalizar. Como o desconto final
   não difere, parte disso pode vir do valor estimado (o estimado sigiloso de serviço seria mais alto) ou de
   desclassificações depois da disputa.
4. **Frequência da etapa fechada:** é o que mais muda e resiste a Holm.
   - Em serviços há lance fechado com mais frequência (+5 p.p.) e a fechada melhora o preço mais vezes (+7,5 p.p.).
   - Com orçamento sigiloso a fechada melhora o preço menos vezes (−6,7 p.p.; −16,8 p.p. em serviços). O ganho
     médio fica parecido porque, quando há melhora, ela é maior.
5. Os testes por item (Welch, Mann-Whitney) dão p < 0,001 em quase tudo. Isso acontece porque tratam como
   independentes itens da mesma compra e da mesma UASG. O t agrupado por UASG é o mais adequado; o sigilo,
   em especial, se concentra em 221 UASGs.

## Regressão empilhada: duas observações por item

Script `regressao_etapas.py`; saídas `regressao_etapas.json` e `regressao_etapas.xlsx` (coeficientes, testes de Wald e
efeitos marginais). Amostra: os 162.339 itens ligados ao `pncp.db` (8.012 pregões, 1.202 UASGs, 32.760 fornecedores
do lance aceito). Valor total e CNPJ do fornecedor vêm da base de extração, aberta só para leitura.

**Modelo:** y_ie = α_i + β·F_e + γ′(F_e × Z_i) + ε_ie, com e ∈ {fim da etapa aberta, após a fechada}. α_i é o efeito
fixo de item. F = 1 na observação após a fechada. Z = {log licitantes, sigiloso, serviço}, com os controles
log(valor total) e mês também interagidos com F. Z está centrado na média da amostra, então β é a variação média
entre as etapas e cada γ é quanto o fator modifica essa variação. **y principal = 100·ln(preço unitário)**: o
efeito fixo absorve ln(estimado), e o resultado não depende da qualidade da estimativa. Erro-padrão agrupado por
UASG, sem contar os efeitos fixos de item, que estão dentro das UASGs.

**Conferência:** com T = 2, o efeito fixo de item equivale à primeira diferença. Empilhado (324.678 observações) e
em diferença, os coeficientes coincidem (diferença máxima de 2.3e-13) e os erros-padrão
também. Se os efeitos fixos fossem contados nos graus de liberdade (o `areg` do Stata), os erros-padrão ficariam
41% maiores sem motivo.

Coeficientes em log-pontos × 100 (−10 ≈ preço 9,5% menor). Sinal negativo nas interações = fator **aumenta** o
ganho da fechada. Erro-padrão entre parênteses. \*\*\* p < 0,001; \*\* p < 0,01; \* p < 0,05; † p < 0,10.

| Especificação | n | Grupos | β: etapa fechada | F × log licitantes | F × sigiloso | F × serviço | Wald (3 interações) |
|---|---|---|---|---|---|---|---|
| P  principal: 100·ln(preço), EP por UASG | 162.339 | 1.202 | -25,39\*\*\* (0,48) | -5,11\*\*\* (0,44) | 2,29\* (0,89) | 0,01 (1,91) | p < 0,001 |
| S1 desconto em p.p. do estimado | 162.339 | 1.202 | 15,46\*\*\* (0,26) | 0,83\*\*\* (0,24) | 1,34† (0,70) | 0,28 (0,89) | p < 0,001 |
| S2 licitantes em faixas (base 6-10) | 162.339 | 1.202 | -25,39\*\*\* (0,48) | faixas: ver abaixo | 2,90\*\*\* (0,87) | -0,14 (1,94) | p < 0,001 |
| S3 + serviço × sigiloso | 162.339 | 1.202 | -25,39\*\*\* (0,48) | -5,11\*\*\* (0,44) | 2,34\* (0,91) | 0,21 (2,01) | p < 0,001 |
| S4 EP por pregão | 162.339 | 8.012 | -25,39\*\*\* (0,39) | -5,11\*\*\* (0,35) | 2,29\*\* (0,72) | 0,01 (1,88) | p < 0,001 |
| S5 EP duas dimensões UASG + fornecedor | 162.339 | 1.202 | -25,39\*\*\* (0,53) | -5,11\*\*\* (0,46) | 2,29\* (0,92) | 0,01 (2,21) | p < 0,001 |
| S6 peso igual por pregão | 162.339 | 1.202 | -22,25\*\*\* (0,40) | -2,15\*\*\* (0,32) | -1,95\* (0,86) | 2,62\*\* (0,90) | p < 0,001 |
| S7 FE UASG × etapa (identificação dentro da UASG) | 162.339 | 1.202 | — | -5,81\*\*\* (0,46) | -2,87 (1,95) | -0,17 (2,21) | p < 0,001 |
| S8 parte extensiva: P(fechada melhora), MLP | 162.339 | 1.202 | 78,88\*\*\* (0,47) | 15,91\*\*\* (0,62) | -5,80\*\*\* (1,19) | 1,81 (1,41) | p < 0,001 |
| S9 parte intensiva: dy só nos itens que melhoraram | 128.057 | 1.158 | -32,19\*\*\* (0,52) | 0,02 (0,57) | 0,60 (0,90) | 0,64 (2,13) | p = 0,910 |
| S10 só adjudicados | 141.753 | 1.199 | -26,91\*\*\* (0,52) | -3,31\*\*\* (0,47) | 2,98\*\* (0,99) | 0,31 (1,99) | p < 0,001 |
| S11 corte 1%/99% de dy | 160.715 | 1.202 | -23,54\*\*\* (0,41) | -5,03\*\*\* (0,39) | 1,00 (0,82) | -0,51 (1,68) | p < 0,001 |
| S12 agregado por pregão (médias) | 8.012 | 1.202 | -21,43\*\*\* (0,41) | -1,16\*\* (0,35) | -1,74† (0,89) | 2,01\* (0,95) | p < 0,001 |
| S13 sem itens de 1 licitante | 154.841 | 1.197 | -26,52\*\*\* (0,50) | -2,17\*\*\* (0,56) | 2,83\*\* (0,91) | -0,02 (1,97) | p < 0,001 |

S1 está em p.p. do estimado, com sinal oposto (positivo = mais ganho). S8 está em p.p. de probabilidade
(positivo = melhora mais vezes). Em S7, o efeito fixo de UASG × etapa absorve β, e as interações são identificadas só pela variação dentro de cada UASG.

S2, licitantes em faixas (base 6–10): 1: 27,56\*\*\* (0,73); 2: 13,48\*\*\* (0,93); 3-5: 3,76\*\*\* (0,77); >10: 3,22\*\*\* (0,68).
S3, interação tripla serviço × sigiloso: -2,18 (5,22).

**Efeitos marginais** (variação prevista do preço entre as etapas, em %, com os demais controles na média):

| Tipo | Orçamento | 2 licitantes | 5 | 10 | 20 |
|---|---|---|---|---|---|
| Material | Aberto | -17,9% [-18,8; -17,0] | -21,7% [-22,5; -20,8] | -24,4% [-25,4; -23,4] | -27,0% [-28,3; -25,7] |
| Material | Sigiloso | -16,0% [-17,4; -14,6] | -19,8% [-21,0; -18,7] | -22,6% [-23,8; -21,5] | -25,3% [-26,6; -24,0] |
| Serviço | Aberto | -17,9% [-20,9; -14,7] | -21,7% [-24,4; -18,8] | -24,4% [-27,0; -21,7] | -27,0% [-29,6; -24,4] |
| Serviço | Sigiloso | -16,0% [-19,5; -12,4] | -19,8% [-22,9; -16,6] | -22,6% [-25,5; -19,6] | -25,3% [-28,1; -22,4] |

### Leitura

1. **Ganho médio:** a etapa fechada reduz o preço em 25,4 log-pontos, cerca de **22,4% abaixo do melhor lance aberto**
   (EP 0,48). É estável em todas as especificações, de −21,4 (agregado por pregão) a −26,9 (só adjudicados). Em p.p. do
   estimado, são 15,5 p.p.
2. **Número de licitantes:** é o único moderador robusto. Cada log a mais aumenta o ganho em 5,1 log-pontos, com
   p < 0,001 em todas as especificações. A relação não é linear:
   - com 1 licitante o ganho praticamente some (+27,6 contra a faixa de 6–10);
   - com 2 licitantes ele é metade (+13,5);
   - o ganho é máximo em 6–10 e cai um pouco acima de 10 (+3,2).
   O efeito vem todo da parte extensiva: mais licitantes aumentam a chance de a fechada melhorar o preço (S8, +15,9 p.p.
   por log), mas não o tamanho da melhora quando ela ocorre (S9, +0,02; p = 0,97). Isso é compatível com o mecanismo
   da regra, em que mais licitantes significam mais convocados até 10% do melhor lance. É descritivo, não causal.
3. **Sigilo:** na principal, a fechada rende 2,3 log-pontos *a menos* com orçamento sigiloso (p = 0,01). O resultado
   **não é robusto**:
   - o sinal se inverte com peso igual por pregão (S6, −1,9; p = 0,02) e no agregado por pregão (S12, −1,7; p = 0,05);
   - perde significância dentro da UASG (S7, −2,9; p = 0,14; só 102 UASGs usam os dois regimes) e com corte de caudas
     (S11, +1,0; p = 0,22).
   O que se mantém em todas é a parte extensiva: com sigilo, a fechada melhora o preço 5,8 p.p. menos vezes (p < 0,001).
   Quando melhora, a melhora é igual (S9, p = 0,51).
4. **Tipo de objeto:** sem efeito na principal (0,0; p = 0,99) nem dentro da UASG (S7). Só aparece quando cada pregão
   pesa igual (S6 +2,6; S12 +2,0): em pregões pequenos de serviço, o ganho é algo menor. Isso é frágil.
5. **Dependência entre itens:**
   - agrupar por pregão reduz o erro-padrão (por exemplo, de 0,89 para 0,72 no sigilo), como esperado, porque o pregão
     está dentro da UASG;
   - agrupar em duas dimensões, UASG e fornecedor, aumenta o erro-padrão de 3% a 16%, sem mudar nenhuma conclusão.
   A inferência principal por UASG é adequada e conservadora.
6. **Peso por item versus por pregão:** a diferença entre P e S6/S12 mostra que os resultados por item são puxados
   pelos pregões grandes. Pondero que a pergunta da pesquisa é por item comprado, então P é a estimativa principal, e
   S6/S12 indicam heterogeneidade entre pregões. Na parte intensiva (S9), nenhum dos três fatores importa (Wald
   p = 0,91).
7. **Interpretação:** continua sendo a dinâmica dentro do Aberto-Fechado, não o efeito causal do modo de disputa.

## Casos com lance fechado acima do aberto: decomposição e marcas

Script `decomposicao_marcas.py`; saídas `decomposicao_marcas.{json,xlsx}` e `marcas_por_item.csv.gz` (marcas por item,
para escolher PDFs a conferir). Só leitura de `por_item.csv.gz` e da base de extração; parser não alterado.

A revisão manual de PDFs de 2026-02 mostrou quatro situações em que o melhor lance fechado supera o melhor aberto. As
regras de medida continuam as mesmas (melhor lance da etapa conta mesmo se o fornecedor cair depois; "após a fechada" =
mínimo das duas etapas). O que muda é que cada situação passa a ter uma marca e uma sensibilidade.

| Grupo | Situação no PDF | Marca provisória | Itens |
|---|---|---|---|
| A | Líder da aberta não dá lance fechado; os convocados ficam acima dele; ele vence | fechado > aberto e final = aberto | 5.737 |
| A3 | Idem, mas o líder é desclassificado e vence um lance fechado mais alto | `lider_aberto_caiu` | 5.710 |
| | Generalização: o melhor lance da disputa (de qualquer etapa) não venceu | `vencedor_caiu`: final > após a fechada | 37.570 (22,6%) |
| B | Ninguém dá lance fechado; a etapa é reiniciada para os lances seguintes | não identificável sem o chat (parser) | — |
| C | Melhor lance aberto absurdo (erro de digitação, inexequível) | `aberto_isolado`: aberto < 50% do final | 3.206 (1,9%) |
| D | Lance fechado absurdamente alto | `fechado_outlier`: fechado > 3 × aberto | 2.382 (1,4%) |

Dos 14.513 itens com fechado acima do aberto: 5.737 o líder venceu, 5.710 o líder caiu, 470 houve negociação abaixo e
2.596 não têm valor final (fracassado, revogado etc.). O filtro de desconto ≤ 99% já tira os casos C mais extremos
(por exemplo R$ 389 num item estimado em R$ 514 mil).

### Decomposição do desconto final

Para os 145.410 itens com valor final: **desconto final = desconto da aberta + ganho da fechada + ajuste pós-disputa**,
com ajuste = d_final − d_após (negativo quando o melhor lance da disputa não vence; positivo com negociação).

| Recorte | Itens | Aberta | + Fechada | + Pós-disputa | = Final |
|---|---|---|---|---|---|
| Amostra com valor final | 145.410 | 22,8 [22,0; 23,6] | 16,1 [15,7; 16,5] | −4,6 [−4,8; −4,3] | 34,4 [33,7; 35,1] |
| Sem C | 142.204 | 21,6 | 16,4 | −3,4 | 34,6 |
| 1 licitante | 4.575 | −0,5 | 2,2 | +4,7 | 6,4 |
| 2 licitantes | 8.653 | 3,1 | 14,5 | −0,5 | 17,1 |
| 3–5 | 36.298 | 10,2 | 19,3 | −3,2 | 26,3 |
| 6–10 | 49.746 | 23,3 | 18,2 | −5,2 | 36,3 |
| > 10 | 46.138 | 38,2 | 13,1 | −6,6 | 44,7 |

Em p.p. do estimado, médias com IC 95% por bootstrap de compra. A soma confere exatamente. Em 25,8% dos itens o melhor
lance da disputa não venceu, e nesses o preço final ficou em média 19,4 p.p. acima dele; em 4,8% houve negociação abaixo
do melhor lance (+9,3 p.p.). O ajuste pós-disputa cresce com o número de licitantes (mais lances baixos que depois caem);
com 1 licitante é positivo, porque a negociação é a única forma de reduzir o preço.

### Sensibilidade às marcas

| Variante | Itens | Aberta | Após a fechada | Ganho (p.p.) | Ganho relativo (%) | Final |
|---|---|---|---|---|---|---|
| Principal | 166.596 | 20,2 | 35,6 | 15,4 [15,0; 15,8] | 19,0 | 34,4 |
| Sem C (aberto < 50% do final) | 163.390 | 19,0 | 34,7 | 15,7 | 19,1 | 34,6 |
| Sem C' (aberto < 50% do fechado) | 162.786 | 19,4 | 35,2 | 15,8 | 19,4 | 34,3 |
| Sem C extremo (< 10% do final) | 166.090 | 20,0 | 35,5 | 15,5 | 19,0 | 34,4 |
| Sem A3 (vencedor da disputa caiu) | 129.026 | 16,7 | 32,2 | 15,5 | 18,5 | 36,6 |
| Sem A3 restrito (líder da aberta caiu) | 160.886 | 19,0 | 35,0 | 16,0 | 19,6 | 34,5 |
| Sem D (fechado > 3× aberto) | 164.214 | 19,6 | 35,3 | 15,7 | 19,2 | 34,4 |
| Sem A3, C e D | 127.766 | 16,5 | 32,1 | 15,6 | 18,6 | 36,5 |

Teste direto fechado × aberto (itens com lance fechado): principal 15,4 p.p. (mediana 12,0; fechado pior em 9,1%);
sem D 16,2 (12,2; 8,2%); sem C' 16,8 (12,3; 7,5%). O corte "fechado > 3× estimado" não muda nada, porque o filtro de
−100% a 99% já os tira.

Regressão principal P (100·ln preço, FE de item, EP por UASG) nos recortes:

| Recorte | n | β fechada | F × ln licitantes | F × sigiloso | F × serviço |
|---|---|---|---|---|---|
| Principal | 162.339 | −25,39\*\*\* (0,48) | −5,11\*\*\* (0,44) | 2,29\* (0,89) | 0,01 (1,91) |
| Sem C | 159.218 | −25,62\*\*\* (0,49) | −5,30\*\*\* (0,45) | 1,70† (0,90) | −0,12 (1,94) |
| Sem A3 | 125.694 | −24,34\*\*\* (0,48) | −6,16\*\*\* (0,45) | 0,98 (0,90) | −2,51 (2,15) |
| Sem D | 160.032 | −25,76\*\*\* (0,49) | −5,19\*\*\* (0,45) | 1,50† (0,90) | −0,01 (1,92) |
| Sem A3, C e D | 124.473 | −24,58\*\*\* (0,48) | −6,17\*\*\* (0,45) | 0,52 (0,91) | −2,40 (2,15) |

### Leitura

1. **O ganho da fechada não depende desses casos:** fica entre 15,4 e 16,0 p.p. (18,5% a 19,6% abaixo do melhor aberto)
   em todos os recortes, e β entre −24,3 e −25,8 log-pontos. Os casos A, C e D têm ganho zero por construção, então o
   viés que provocam é para baixo (conservador) e pequeno.
2. **Quem muda é o desconto da aberta.** Lances abertos absurdos (C) e lances de quem depois cai (A3) o inflam: 20,2%
   na amostra, 19,0% sem C, 16,7% sem A3. O desconto da aberta "isolado" deve ser lido com isso em mente; o final e o
   ganho da fechada são as medidas firmes.
3. **O ajuste pós-disputa é grande:** −4,6 p.p. em média e −19,4 p.p. quando o vencedor cai. É a distância entre a
   disputa e o preço homologado. Na comparação com o modo Aberto (API, valor homologado), compara-se com o desconto
   final, que já o inclui.
4. **A moderação pelo sigilo vem dos itens em que o vencedor caiu.** Sem A3, F × sigiloso cai de 2,3 (p = 0,01) para
   1,0 (p = 0,28), e para 0,5 sem A3, C e D. Isso reforça que o sigilo não modera o ganho da fechada; o que parecia
   efeito era a maior frequência de desclassificação do melhor lance. O número de licitantes continua o único
   moderador robusto (−5,1 a −6,2).
5. **Pendências do parser** (docs/05, nova versão): (a) segundo melhor lance aberto de outro CNPJ, para trocar a marca
   provisória C (que usa o valor final) por uma regra só da disputa e calcular um "melhor aberto efetivo";
   (b) `fechada_reiniciada`, lida do chat (grupo B); (c) CNPJs desclassificados/recusados, para medir as etapas só com
   fornecedores válidos como sensibilidade (grupo A3). Exige os PDFs de 03, 04 e 08 de volta no disco.

## Sensibilidade

| Variante | Ganho relativo médio | Mediana |
|---|---|---|
| Principal | 19,0 | 13,3 |
| Sem filtro de desconto (173.458) | 19,0 | 13,0 |
| Filtro só no desconto após a fechada (168.344) | 19,3 | 13,6 |
| Só itens adjudicados (145.408) | 20,1 | 15,0 |
| Só ≥ 2 fornecedores | 19,8 | 14,5 |
| Média por compra (8.018 compras) | 16,5 | 14,4 |

## Leitura e limites

1. **Não é efeito causal do modo Aberto-Fechado.** Quem sabe que haverá uma etapa fechada tende a guardar
   o lance na aberta; o ganho mede quanto do desconto do AF se concentra na fechada, não quanto o AF rende
   a mais que o Aberto. Para isso falta comparar com pregões Aberto (desconto final da API), com e sem
   pareamento UASG × item — pendência 2 do docs/05.
2. Só Menor Preço; Maior Desconto (2.675 itens) fica para análise à parte.
3. O desconto depende do valor estimado; o ganho relativo (sobre o melhor aberto) não, e dá o mesmo quadro.
4. Amostra: compras AF homologadas do Compras.gov.br com zip baixado; janeiro e maio–julho ausentes.
5. Há 9% de itens em que o lance fechado é pior que o melhor aberto e lances fechados muito acima do
   estimado; vale conferir alguns PDFs para descartar erro na separação das etapas pelo parser.
