# Composição dos produtos e efeito do AF no preço homologado: relatório (23/11/2026)

**Exploratório.** O protocolo (`protocolo.md`) foi escrito antes da execução; o hash está em `registro_execucao.json`.
Nenhuma especificação foi escolhida pelo valor-p, e a falta de significância não é lida como falta de efeito.

**Pergunta.** As diferenças de preço associadas à troca de modo vêm de mudanças no preço de produtos comparáveis ou de
mudanças na composição das compras?

**Base e controles da execução.**
- Base de 23/11 e motor de `../robustez_dispersao_20261123/`. M0 (−1,91 lp, 152 eventos) e M1 (−3,76 lp, 150 eventos)
  foram reproduzidos exatamente.
- Os 56 eventos posteriores a 2025-10, reservados para a validação, não foram usados.
- O `pncp.db` não foi lido, e nada anterior foi alterado. Não se controlou pelo número de licitantes.

**Especificações.**
- **A:** referência original, todas as células; base M0.
- **G:** referência G com dispersão contemporânea ≤ 0,80; base M1.
- **Medicamentos:** classe CATMAT 6505, classificação de catálogo, sem uso de preço. São 14,5% dos itens com índice em A
  e 14,9% em G.

**Inferência.** Agrupada por órgão (CNPJ). IC e p vêm do bootstrap selvagem restrito (Webb, B = 9.999); as diferenças
pareadas usam bootstrap selvagem não restrito do t.

## Resumo dos resultados obtidos

1. **O efeito estimado está nos demais materiais, não nos medicamentos.**
   - Demais materiais: −2,33 lp em A (IC [−6,46; 1,88], p = 0,26) e **−4,08 lp em G** (IC [−7,34; −0,83], p = 0,015). Usam
     os mesmos eventos (150–152) e órgãos (68–70) que o total, e a estimativa é igual ou maior que a do total (−1,91 e
     −3,76).
   - Medicamentos: +0,41 lp em A e −1,30 lp em G, com IC de cerca de ±11 lp. São só 41–42 eventos e cerca de 7 órgãos
     efetivos. Isso não permite concluir nada sobre o efeito nos medicamentos.
2. **A interação AF × medicamentos não é identificável com estes dados.**
   - A diferença medicamentos − demais é de +1,3 a +6,0 lp (p de 0,47 a 0,87).
   - O efeito mínimo detectável fica entre 16 e 22 lp.
   - Faltam órgãos efetivos: 8,5 a 9,2, abaixo dos 10 fixados no protocolo.
3. **A queda da parcela de medicamentos na adoção do AF (−3,2 p.p.) não produz o efeito no preço.** Retirar os
   medicamentos não enfraquece a estimativa; ela fica igual ou mais negativa.
4. **O índice de composição fixa é muito impreciso.**
   - Só 10–15% dos itens estão em produtos comprados nas duas meias janelas.
   - Na amostra com produtos continuados (77 eventos em A, 71 em G), ele dá −8,5 lp em A (p = 0,05) e −3,7 lp em G
     (p = 0,24).
   - A diferença contra o índice original não é significativa: −6,9 lp (p = 0,09) e +2,2 lp (p = 0,49).
5. **Na decomposição em G, a maior parte da variação vem do preço de produtos comparáveis.**
   - Total por item: −5,31 lp (p = 0,004), igual a −3,74 de preço + −0,82 de recomposição + −0,75 de entrada e saída.
   - A identidade fecha com resíduo de 10⁻¹⁶.
   - Os componentes de composição são pequenos e não significativos. Em A, os componentes são grandes, se compensam e são
     ruidosos (−8,5 e +5,7).
6. **Validade.**
   - As pré-tendências são nulas, com uma exceção nominal entre cerca de 20 testes: a recomposição em A na pseudojanela
     (−3,4, p = 0,04).
   - Na troca para o AF, a continuidade de produtos cai 4–6 p.p. e a parcela de medicamentos cai 3,2 p.p.

**Leitura.**
- Não há evidência de que as diferenças de preço venham de mudanças de composição.
  - Excluir os medicamentos, cuja participação muda, mantém ou aumenta a estimativa.
  - Na especificação filtrada, a decomposição atribui a maior parte da variação ao preço de produtos comparáveis.
- Mas a análise de composição fixa tem pouco poder, porque poucos produtos são comprados antes e depois na mesma unidade.
  Ela não descarta contribuições de composição de alguns log-pontos.
- A especificação A segue sem efeito significativo em qualquer recorte.

## Teste 1 — Medicamentos × demais materiais

- **Principal:** eventos, controles, referência e janelas do modelo base. Só os itens do grupo entram nas médias por
  compra, com pelo menos 1 compra do grupo em cada meia janela.
- **Sensibilidade:** controles selecionados de novo para o grupo.

| Espec. | Grupo | Controles | Pesos | coef (lp) | EP | IC95 | p | eventos (A→AF + AF→A) | itens | compras | UASGs trat./ctrl. | órgãos (efet.) | sem um órgão: mín.–máx. | Δ vs −1,91 | Δ vs −3,76 |
|---|---|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A | todos | do modelo base | precisão (h do grupo) | −1,91 | 1,90 | [−5,67; 1,93] | 0,321 | 152 (76 + 76) | 55.617 | 3.671 | 133 / 2.142 | 70 (24,7) | −2,52 a −1,40 | 0,00 | 1,85 |
| A | todos | do modelo base | iguais | −3,10 | 2,64 | [−8,32; 2,26] | 0,247 | 152 (76 + 76) | 55.617 | 3.671 | 133 / 2.142 | 70 (21,1) | −4,26 a −2,12 | −1,19 | 0,66 |
| A | medicamentos | do modelo base | precisão (h do grupo) | 0,41 | 4,89 | [−11,22; 13,90] | 0,939 | 42 (18 + 24) | 6.727 | 572 | 37 / 613 | 20 (7,1) | −3,41 a 2,93 | 2,32 | 4,17 |
| A | medicamentos | do modelo base | iguais | 3,28 | 5,93 | [−6,99; 20,83] | 0,659 | 42 (18 + 24) | 6.727 | 572 | 37 / 613 | 20 (9,2) | −1,28 a 5,90 | 5,19 | 7,04 |
| A | medicamentos | selecionados de novo | precisão (h do grupo) | −1,62 | 5,99 | [−20,13; 9,98] | 0,786 | 20 (10 + 10) | 4.268 | 485 | 17 / 305 | 11 (5,4) | −5,45 a 1,84 | 0,29 | 2,14 |
| A | demais materiais | do modelo base | precisão (h do grupo) | −2,33 | 2,08 | [−6,46; 1,88] | 0,263 | 152 (76 + 76) | 46.741 | 3.200 | 133 / 2.140 | 70 (25,7) | −2,98 a −1,80 | −0,42 | 1,43 |
| A | demais materiais | do modelo base | iguais | −3,24 | 2,72 | [−8,76; 2,08] | 0,237 | 152 (76 + 76) | 46.741 | 3.200 | 133 / 2.140 | 70 (21,1) | −4,38 a −2,26 | −1,33 | 0,52 |
| A | demais materiais | selecionados de novo | precisão (h do grupo) | −2,24 | 2,08 | [−6,40; 2,01] | 0,292 | 149 (74 + 75) | 46.269 | 3.110 | 131 / 2.135 | 69 (25,7) | −2,88 a −1,69 | −0,33 | 1,52 |
| G | todos | do modelo base | precisão (h do grupo) | −3,76 | 1,46 | [−6,67; −0,89] | 0,012 | 150 (73 + 77) | 50.179 | 3.507 | 131 / 2.079 | 68 (23,0) | −4,39 a −3,33 | −1,85 | 0,00 |
| G | todos | do modelo base | iguais | −3,01 | 1,77 | [−6,58; 0,55] | 0,091 | 150 (73 + 77) | 50.179 | 3.507 | 131 / 2.079 | 68 (20,3) | −3,55 a −2,19 | −1,10 | 0,75 |
| G | medicamentos | do modelo base | precisão (h do grupo) | −1,29 | 4,06 | [−11,63; 10,42] | 0,730 | 41 (19 + 22) | 6.181 | 580 | 36 / 604 | 20 (6,9) | −4,03 a 1,57 | 0,62 | 2,47 |
| G | medicamentos | do modelo base | iguais | −1,43 | 7,30 | [−18,04; 18,27] | 0,880 | 41 (19 + 22) | 6.181 | 580 | 36 / 604 | 20 (8,9) | −4,85 a 5,82 | 0,48 | 2,33 |
| G | medicamentos | selecionados de novo | precisão (h do grupo) | −0,66 | 3,51 | [−9,23; 8,48] | 0,862 | 20 (10 + 10) | 4.064 | 497 | 17 / 301 | 11 (5,3) | −3,17 a 0,81 | 1,25 | 3,10 |
| G | demais materiais | do modelo base | precisão (h do grupo) | −4,08 | 1,62 | [−7,34; −0,83] | 0,015 | 150 (73 + 77) | 41.858 | 3.024 | 131 / 2.075 | 68 (23,8) | −4,76 a −3,43 | −2,17 | −0,32 |
| G | demais materiais | do modelo base | iguais | −3,07 | 1,94 | [−7,00; 0,89] | 0,117 | 150 (73 + 77) | 41.858 | 3.024 | 131 / 2.075 | 68 (20,3) | −3,71 a −2,25 | −1,16 | 0,69 |
| G | demais materiais | selecionados de novo | precisão (h do grupo) | −4,03 | 1,61 | [−7,29; −0,75] | 0,019 | 147 (70 + 77) | 41.591 | 2.980 | 128 / 2.059 | 67 (23,7) | −4,70 a −3,37 | −2,12 | −0,27 |

Sentidos da troca e simetria:

| Espec. | Grupo | Controles | Pesos | A → AF (p) | AF → A (p) | Soma dos sentidos (p) | maior Δ sem um órgão |
|---|---|---|---|---|---|---|---:|
| A | todos | do modelo base | precisão (h do grupo) | −0,71 (0,795) | 2,95 (0,338) | 2,24 (0,618) | 0,61 |
| A | todos | do modelo base | iguais | −2,41 (0,552) | 3,78 (0,385) | 1,36 (0,830) | 1,16 |
| A | medicamentos | do modelo base | precisão (h do grupo) | 7,31 (0,654) | 2,92 (0,473) | 10,23 (0,275) | 3,82 |
| A | medicamentos | do modelo base | iguais | 0,69 (0,947) | −5,22 (0,349) | −4,53 (0,651) | 4,56 |
| A | medicamentos | selecionados de novo | precisão (h do grupo) | 11,57 (0,520) | 7,80 (0,362) | 19,37 (0,163) | 3,83 |
| A | demais materiais | do modelo base | precisão (h do grupo) | −0,91 (0,760) | 3,57 (0,294) | 2,66 (0,587) | 0,64 |
| A | demais materiais | do modelo base | iguais | −2,51 (0,553) | 3,97 (0,377) | 1,46 (0,829) | 1,14 |
| A | demais materiais | selecionados de novo | precisão (h do grupo) | −0,70 (0,816) | 3,56 (0,296) | 2,86 (0,564) | 0,65 |
| G | todos | do modelo base | precisão (h do grupo) | −5,85 (0,007) | 1,99 (0,401) | −3,87 (0,246) | 0,64 |
| G | todos | do modelo base | iguais | −4,27 (0,097) | 1,82 (0,552) | −2,45 (0,550) | 0,82 |
| G | medicamentos | do modelo base | precisão (h do grupo) | −0,23 (0,978) | 1,82 (0,569) | 1,58 (0,882) | 2,87 |
| G | medicamentos | do modelo base | iguais | −6,33 (0,601) | −2,80 (0,704) | −9,12 (0,209) | 7,25 |
| G | medicamentos | selecionados de novo | precisão (h do grupo) | 4,79 (0,737) | 3,10 (0,363) | 7,89 (0,537) | 2,52 |
| G | demais materiais | do modelo base | precisão (h do grupo) | −6,26 (0,008) | 2,22 (0,375) | −4,03 (0,230) | 0,68 |
| G | demais materiais | do modelo base | iguais | −4,80 (0,087) | 1,43 (0,659) | −3,37 (0,430) | 0,82 |
| G | demais materiais | selecionados de novo | precisão (h do grupo) | −6,11 (0,009) | 2,29 (0,360) | −3,82 (0,256) | 0,67 |

Perfil por trimestre de evento (base −1; IC por t(G − 1)):

| Espec. | Grupo | trim. −2 (p) | trim. 0 (p) | trim. +1 (p) | p conjunto pós |
|---|---|---|---|---|---:|
| A | todos | 0,52 (0,884; 110 ev.) | −3,14 (0,331; 136 ev.) | −3,12 (0,281; 120 ev.) | 0,503 |
| A | medicamentos | −4,42 (0,534; 12 ev.) | 0,55 (0,922; 23 ev.) | −8,01 (0,312; 22 ev.) | 0,359 |
| A | demais materiais | 0,21 (0,956; 109 ev.) | −3,90 (0,253; 136 ev.) | −3,85 (0,195; 120 ev.) | 0,375 |
| G | todos | −1,92 (0,573; 107 ev.) | −4,15 (0,195; 133 ev.) | −5,46 (0,041; 125 ev.) | 0,117 |
| G | medicamentos | −5,10 (0,503; 11 ev.) | −2,52 (0,550; 23 ev.) | −5,18 (0,240; 20 ev.) | 0,491 |
| G | demais materiais | −2,05 (0,560; 105 ev.) | −5,01 (0,131; 132 ev.) | −5,73 (0,045; 125 ev.) | 0,114 |

- **Demais materiais.** Carregam a estimativa nas duas especificações, com pré-tendência nula (p = 0,96 em A; 0,56 em G).
  Os pesos iguais enfraquecem o resultado de G (−3,07, p = 0,12), como no modelo total. Selecionar os controles de novo
  não muda nada (−4,03).
- **Medicamentos.** Estimativas próximas de zero, com IC de ±10 a ±16 lp. A maioria dos eventos não tem compras de
  medicamentos nas duas meias janelas: 110 dos 152 em A só têm demais materiais. Com controles selecionados de novo,
  restam 20 eventos.
- **Influência.** A maior variação ao retirar um órgão é de 0,6–1,1 lp nos demais materiais e de 2,5–7,3 lp nos
  medicamentos, que têm menos órgãos.

## Teste 2 — Interação AF × medicamentos

A interação é a diferença pareada, por evento, entre o efeito em medicamentos e nos demais, nos eventos que têm os dois
grupos.

| Espec. | Pesos | Diferença med. − demais (lp) | EP | IC95 | p | eventos (A→AF + AF→A) | órgãos (efet.) | efeito mínimo detectável | identificável pelo critério | A → AF (p) | AF → A (p) | sem um órgão: mín.–máx. |
|---|---|---:|---:|---|---:|---:|---:|---:|---|---|---|---:|
| A | precisão da diferença | 5,76 | 7,17 | [−8,42; 23,11] | 0,467 | 42 (18 + 24) | 20 (8,7) | 20,08 lp | não | 8,00 (0,744) | −4,52 (0,558) | 0,32 a 8,87 |
| A | iguais | 6,03 | 7,87 | [−7,56; 29,76] | 0,466 | 42 (18 + 24) | 20 (9,2) | 22,05 lp | não | 0,63 (0,959) | −10,09 (0,268) | 0,85 a 8,91 |
| G | precisão da diferença | 3,85 | 5,59 | [−7,75; 17,46] | 0,541 | 41 (19 + 22) | 20 (8,5) | 15,65 lp | não | 9,32 (0,438) | −0,82 (0,861) | −0,29 a 6,89 |
| G | iguais | 1,29 | 7,49 | [−12,89; 24,49] | 0,869 | 41 (19 + 22) | 20 (8,9) | 20,96 lp | não | 0,30 (0,979) | −2,13 (0,782) | −2,96 a 7,32 |

- **Critério de identificação** (protocolo: ≥ 30 eventos, ≥ 10 por sentido e ≥ 10 órgãos efetivos):
  - eventos e sentidos bastam: 41–42 eventos, sendo 18–19 A → AF e 22–24 AF → A;
  - **órgãos efetivos não: 8,5 a 9,2.**
- O efeito mínimo detectável da diferença é de 16 a 22 lp. As estimativas pontuais sugerem efeito menos negativo nos
  medicamentos, mas os dados não distinguem nada abaixo de ~16 lp.

## Teste 3 — Índice de composição fixa

- **Cesta:** a da pré-janela de cada unidade, em que produto = CATMAT + unidade.
- **Pesos:** parcela de itens na pré-janela, informação pré-tratamento sem preço.
- **Índice:** variação do índice de preço (contra o mesmo produto e trimestre em outras UASGs) nos produtos continuados.
- **Produtos que somem:** saem (principal) ou entram com variação zero (sensibilidade).
- **Comparação:** feita nos mesmos eventos e controles. Cada unidade precisa ter produto continuado, o que reduz a amostra
  a 77 eventos em A e 71 em G.

| Espec. | Medida | Pesos | coef | EP | IC95 | p | eventos (A→AF + AF→A) | órgãos (efet.) | A → AF (p) | AF → A (p) | Soma (p) | sem um órgão: mín.–máx. | Δ vs −1,91 | Δ vs −3,76 |
|---|---|---|---:|---:|---|---:|---:|---:|---|---|---|---:|---:|---:|
| A | índice original (médias por compra) | pesos do modelo base | −1,66 | 2,11 | [−6,02; 2,83] | 0,438 | 77 (36 + 41) | 39 (17,2) | −0,08 (0,976) | 2,89 (0,295) | 2,80 (0,379) | −2,50 a −0,63 | 0,25 | 2,10 |
| A | índice original (médias por compra) | iguais | −2,66 | 3,24 | [−8,66; 5,19] | 0,481 | 77 (36 + 41) | 39 (13,0) | −0,03 (0,995) | 4,96 (0,281) | 4,93 (0,288) | −3,81 a −0,21 | −0,75 | 1,10 |
| A | A: preço de produtos comparáveis (composição fixa) | pesos do modelo base | −8,51 | 4,18 | [−17,58; 0,03] | 0,051 | 77 (36 + 41) | 39 (17,2) | 2,08 (0,637) | 16,72 (0,021) | 18,80 (0,087) | −9,53 a −5,62 | −6,60 | −4,75 |
| A | A: preço de produtos comparáveis (composição fixa) | iguais | −9,69 | 6,58 | [−22,45; 5,26] | 0,272 | 77 (36 + 41) | 39 (13,0) | 7,26 (0,145) | 24,56 (0,109) | 31,82 (0,075) | −11,45 a −4,49 | −7,78 | −5,93 |
| A | índice fixo com produtos que somem imputados (variação zero) | pesos do modelo base | −0,57 | 0,50 | [−1,59; 0,45] | 0,265 | 77 (36 + 41) | 39 (17,2) | −0,36 (0,446) | 0,75 (0,402) | 0,39 (0,701) | −0,89 a −0,33 | 1,34 | 3,19 |
| A | índice fixo com produtos que somem imputados (variação zero) | iguais | −0,81 | 0,83 | [−2,80; 0,63] | 0,383 | 77 (36 + 41) | 39 (13,0) | −0,14 (0,779) | 1,40 (0,426) | 1,26 (0,486) | −1,17 a −0,17 | 1,10 | 2,95 |
| G | índice original (médias por compra) | pesos do modelo base | −5,92 | 1,63 | [−9,23; −2,39] | 0,004 | 71 (34 + 37) | 35 (15,7) | −9,39 (< 0,001) | 3,18 (0,153) | −6,21 (0,023) | −6,58 a −5,28 | −4,01 | −2,16 |
| G | índice original (médias por compra) | iguais | −6,20 | 2,06 | [−10,07; −1,33] | 0,016 | 71 (34 + 37) | 35 (13,0) | −8,62 (0,009) | 3,97 (0,232) | −4,65 (0,141) | −6,70 a −4,72 | −4,29 | −2,44 |
| G | A: preço de produtos comparáveis (composição fixa) | pesos do modelo base | −3,74 | 2,97 | [−9,72; 3,15] | 0,243 | 71 (34 + 37) | 35 (15,7) | 0,55 (0,890) | 7,13 (0,181) | 7,67 (0,235) | −5,21 a −2,50 | −1,83 | 0,02 |
| G | A: preço de produtos comparáveis (composição fixa) | iguais | −2,23 | 3,65 | [−9,15; 6,59] | 0,577 | 71 (34 + 37) | 35 (13,0) | 3,99 (0,416) | 7,96 (0,299) | 11,95 (0,207) | −3,91 a 0,20 | −0,32 | 1,53 |
| G | índice fixo com produtos que somem imputados (variação zero) | pesos do modelo base | −0,53 | 0,34 | [−1,25; 0,26] | 0,175 | 71 (34 + 37) | 35 (15,7) | −0,46 (0,364) | 0,58 (0,179) | 0,12 (0,831) | −0,65 a −0,36 | 1,38 | 3,23 |
| G | índice fixo com produtos que somem imputados (variação zero) | iguais | −0,59 | 0,40 | [−1,52; 0,21] | 0,151 | 71 (34 + 37) | 35 (13,0) | −0,31 (0,626) | 0,84 (0,057) | 0,53 (0,510) | −0,79 a −0,36 | 1,32 | 3,17 |

Diferenças pareadas (mesmos eventos e controles):

| Espec. | Comparação | Pesos | Diferença (lp) | EP | IC95 (WCU) | p | eventos | órgãos |
|---|---|---|---:|---:|---|---:|---:|---:|
| A | A: preço de produtos comparáveis (composição fixa) − índice original (médias por compra) | pesos do modelo base | −6,85 | 4,08 | [−14,71; 1,00] | 0,089 | 77 | 39 |
| A | índice fixo com produtos que somem imputados (variação zero) − índice original (médias por compra) | pesos do modelo base | 1,09 | 2,11 | [−2,96; 5,13] | 0,611 | 77 | 39 |
| A | ΔĒ, média por item − índice original (médias por compra) | pesos do modelo base | −1,53 | 1,45 | [−4,28; 1,22] | 0,294 | 77 | 39 |
| A | A: preço de produtos comparáveis (composição fixa) − ΔĒ, média por item | pesos do modelo base | −5,32 | 3,57 | [−12,12; 1,49] | 0,134 | 77 | 39 |
| A | A: preço de produtos comparáveis (composição fixa) − índice original (médias por compra) | iguais | −7,03 | 5,00 | [−16,66; 2,59] | 0,162 | 77 | 39 |
| A | índice fixo com produtos que somem imputados (variação zero) − índice original (médias por compra) | iguais | 1,85 | 3,13 | [−3,93; 7,62] | 0,593 | 77 | 39 |
| A | ΔĒ, média por item − índice original (médias por compra) | iguais | −1,08 | 1,65 | [−4,25; 2,09] | 0,523 | 77 | 39 |
| A | A: preço de produtos comparáveis (composição fixa) − ΔĒ, média por item | iguais | −5,96 | 4,73 | [−14,89; 2,98] | 0,213 | 77 | 39 |
| G | A: preço de produtos comparáveis (composição fixa) − índice original (médias por compra) | pesos do modelo base | 2,17 | 3,09 | [−3,75; 8,09] | 0,488 | 71 | 35 |
| G | índice fixo com produtos que somem imputados (variação zero) − índice original (médias por compra) | pesos do modelo base | 5,39 | 1,66 | [2,19; 8,58] | < 0,001 | 71 | 35 |
| G | ΔĒ, média por item − índice original (médias por compra) | pesos do modelo base | 0,61 | 1,44 | [−2,17; 3,40] | 0,679 | 71 | 35 |
| G | A: preço de produtos comparáveis (composição fixa) − ΔĒ, média por item | pesos do modelo base | 1,56 | 2,96 | [−4,08; 7,21] | 0,605 | 71 | 35 |
| G | A: preço de produtos comparáveis (composição fixa) − índice original (médias por compra) | iguais | 3,97 | 3,61 | [−2,94; 10,88] | 0,278 | 71 | 35 |
| G | índice fixo com produtos que somem imputados (variação zero) − índice original (médias por compra) | iguais | 5,61 | 2,19 | [1,49; 9,74] | 0,005 | 71 | 35 |
| G | ΔĒ, média por item − índice original (médias por compra) | iguais | −0,18 | 1,52 | [−3,07; 2,70] | 0,907 | 71 | 35 |
| G | A: preço de produtos comparáveis (composição fixa) − ΔĒ, média por item | iguais | 4,15 | 3,11 | [−1,76; 10,07] | 0,181 | 71 | 35 |

**Cobertura.** Os produtos continuados respondem por:
- **em A:** 14,6% dos itens pré e 10,2% dos itens pós das tratadas (controles: 11,5% e 9,0%);
- **em G:** 13,8% e 10,8% (controles: 10,5% e 9,0%).

O índice de composição fixa usa, portanto, só 10–15% dos itens. Isso explica o EP de 3 a 4 lp e torna o teste pouco
informativo.

**Variante com variação zero para os produtos que somem.** Ela encolhe o índice para cerca de −0,5 lp por construção: 85%
a 90% da cesta entra com variação zero.

## Teste 4 — Decomposição preço × composição

ΔĒ é a variação da média do índice por item. A identidade ΔĒ = A + B1 + B2 vale exatamente por unidade e por evento: o
resíduo máximo é de 5,7 × 10⁻¹⁶ por unidade e 4,6 × 10⁻¹⁶ no DiD por evento.

| Componente | Significado |
|---|---|
| A | preço dos produtos comparáveis, com pesos pré |
| B1 | recomposição entre produtos continuados |
| B2 | entrada e saída de produtos |

| Espec. | Medida | Pesos | coef | EP | IC95 | p | eventos (A→AF + AF→A) | órgãos (efet.) | A → AF (p) | AF → A (p) | Soma (p) | sem um órgão: mín.–máx. | Δ vs −1,91 | Δ vs −3,76 |
|---|---|---|---:|---:|---|---:|---:|---:|---|---|---|---:|---:|---:|
| A | ΔĒ, média por item | pesos do modelo base | −3,20 | 2,25 | [−7,64; 1,61] | 0,176 | 77 (36 + 41) | 39 (17,2) | −0,80 (0,807) | 5,06 (0,064) | 4,26 (0,238) | −3,92 a −1,82 | −1,29 | 0,56 |
| A | ΔĒ, média por item | iguais | −3,73 | 3,63 | [−10,58; 4,85] | 0,390 | 77 (36 + 41) | 39 (13,0) | −0,38 (0,938) | 6,67 (0,212) | 6,29 (0,260) | −4,95 a −0,96 | −1,82 | 0,03 |
| A | A: preço de produtos comparáveis (composição fixa) | pesos do modelo base | −8,51 | 4,18 | [−17,58; 0,03] | 0,051 | 77 (36 + 41) | 39 (17,2) | 2,08 (0,637) | 16,72 (0,021) | 18,80 (0,087) | −9,53 a −5,62 | −6,60 | −4,75 |
| A | A: preço de produtos comparáveis (composição fixa) | iguais | −9,69 | 6,58 | [−22,45; 5,26] | 0,272 | 77 (36 + 41) | 39 (13,0) | 7,26 (0,145) | 24,56 (0,109) | 31,82 (0,075) | −11,45 a −4,49 | −7,78 | −5,93 |
| A | B1: recomposição entre produtos continuados | pesos do modelo base | −0,39 | 1,41 | [−3,37; 2,34] | 0,805 | 77 (36 + 41) | 39 (17,2) | −0,52 (0,507) | 0,30 (0,914) | −0,22 (0,938) | −1,39 a 0,21 | 1,52 | 3,37 |
| A | B1: recomposição entre produtos continuados | iguais | −0,48 | 0,91 | [−2,42; 1,45] | 0,614 | 77 (36 + 41) | 39 (13,0) | −0,64 (0,356) | 0,34 (0,825) | −0,29 (0,869) | −1,08 a 0,02 | 1,43 | 3,28 |
| A | B2: entrada e saída de produtos | pesos do modelo base | 5,71 | 3,41 | [−1,07; 12,98] | 0,101 | 77 (36 + 41) | 39 (17,2) | −2,36 (0,609) | −11,96 (0,088) | −14,32 (0,173) | 4,19 a 6,70 | 7,62 | 9,47 |
| A | B2: entrada e saída de produtos | iguais | 6,44 | 4,72 | [−4,30; 15,24] | 0,250 | 77 (36 + 41) | 39 (13,0) | −7,00 (0,247) | −18,24 (0,165) | −25,24 (0,135) | 3,61 a 7,55 | 8,35 | 10,20 |
| G | ΔĒ, média por item | pesos do modelo base | −5,31 | 1,58 | [−8,53; −1,92] | 0,004 | 71 (34 + 37) | 35 (15,7) | −7,33 (0,006) | 3,71 (0,112) | −3,62 (0,203) | −5,81 a −4,38 | −3,40 | −1,55 |
| G | ΔĒ, média por item | iguais | −6,38 | 2,15 | [−10,61; −1,44] | 0,011 | 71 (34 + 37) | 35 (13,0) | −8,64 (0,006) | 4,31 (0,260) | −4,33 (0,193) | −7,05 a −4,70 | −4,47 | −2,62 |
| G | A: preço de produtos comparáveis (composição fixa) | pesos do modelo base | −3,74 | 2,97 | [−9,72; 3,15] | 0,243 | 71 (34 + 37) | 35 (15,7) | 0,55 (0,890) | 7,13 (0,181) | 7,67 (0,235) | −5,21 a −2,50 | −1,83 | 0,02 |
| G | A: preço de produtos comparáveis (composição fixa) | iguais | −2,23 | 3,65 | [−9,15; 6,59] | 0,577 | 71 (34 + 37) | 35 (13,0) | 3,99 (0,416) | 7,96 (0,299) | 11,95 (0,207) | −3,91 a 0,20 | −0,32 | 1,53 |
| G | B1: recomposição entre produtos continuados | pesos do modelo base | −0,82 | 0,65 | [−2,17; 0,53] | 0,244 | 71 (34 + 37) | 35 (15,7) | −0,81 (0,298) | 0,82 (0,524) | 0,02 (0,987) | −1,24 a −0,36 | 1,09 | 2,94 |
| G | B1: recomposição entre produtos continuados | iguais | −0,78 | 0,62 | [−2,10; 0,55] | 0,230 | 71 (34 + 37) | 35 (13,0) | −0,34 (0,586) | 1,19 (0,264) | 0,85 (0,534) | −1,10 a −0,31 | 1,13 | 2,98 |
| G | B2: entrada e saída de produtos | pesos do modelo base | −0,75 | 3,08 | [−7,45; 5,39] | 0,810 | 71 (34 + 37) | 35 (15,7) | −7,07 (0,143) | −4,24 (0,413) | −11,31 (0,114) | −1,88 a 0,79 | 1,16 | 3,01 |
| G | B2: entrada e saída de produtos | iguais | −3,37 | 3,18 | [−10,63; 2,62] | 0,290 | 71 (34 + 37) | 35 (13,0) | −12,29 (0,018) | −4,84 (0,367) | −17,13 (0,044) | −4,38 a −1,59 | −1,46 | 0,39 |

- **G.** O total por item é −5,31 lp, dos quais −3,74 (70%) vêm do preço de produtos comparáveis e −1,57 da composição
  (B1 + B2). Nenhum componente é significativo sozinho; o total é.
- **A.** O total (−3,20) junta um preço de comparáveis de −8,52 (p = 0,05) com entrada e saída de +5,71 (p = 0,10). São
  componentes grandes, de sinais opostos e imprecisos.
- **Sem leitura causal isolada.** B1 e B2 refletem escolhas de compra que podem responder ao modo, e A usa só os 10–15%
  de itens continuados.
- **Amostra.** Nesta amostra, o índice original dá −1,66 em A e −5,92 em G, contra −1,91 e −3,76 nas amostras completas.

## Teste 5 — Validade e robustez

**Pré-tendência** nas mesmas medidas, na pseudojanela [m−6, m−3) contra [m−3, m), com os mesmos controles (33 eventos em A,
27 em G):

| Espec. | Medida | Pesos | coef | EP | IC95 | p | eventos (A→AF + AF→A) | órgãos (efet.) | A → AF (p) | AF → A (p) | Soma (p) | sem um órgão: mín.–máx. | Δ vs −1,91 | Δ vs −3,76 |
|---|---|---|---:|---:|---|---:|---:|---:|---|---|---|---:|---:|---:|
| A | índice original (médias por compra) | pesos do modelo base | −0,38 | 3,64 | [−7,75; 7,93] | 0,910 | 33 (14 + 19) | 21 (12,1) | −3,72 (0,596) | −2,32 (0,732) | −6,03 (0,614) | −1,63 a 1,97 | 1,53 | 3,38 |
| A | índice original (médias por compra) | iguais | 2,80 | 4,61 | [−6,53; 13,06] | 0,537 | 33 (14 + 19) | 21 (13,8) | −0,78 (0,918) | −5,45 (0,461) | −6,23 (0,592) | 0,68 a 4,52 | 4,71 | 6,56 |
| A | ΔĒ, média por item | pesos do modelo base | 2,07 | 3,28 | [−5,86; 8,69] | 0,555 | 33 (14 + 19) | 21 (12,1) | −4,99 (0,591) | −7,78 (0,043) | −12,77 (0,116) | 0,84 a 4,57 | 3,98 | 5,83 |
| A | ΔĒ, média por item | iguais | 3,68 | 4,06 | [−4,31; 12,69] | 0,367 | 33 (14 + 19) | 21 (13,8) | −2,07 (0,773) | −7,92 (0,173) | −9,99 (0,297) | 1,99 a 5,43 | 5,59 | 7,44 |
| A | A: preço de produtos comparáveis (composição fixa) | pesos do modelo base | 4,13 | 11,52 | [−21,68; 29,06] | 0,758 | 33 (14 + 19) | 21 (12,1) | −2,55 (0,886) | −9,54 (0,519) | −12,09 (0,676) | −1,91 a 12,21 | 6,04 | 7,89 |
| A | A: preço de produtos comparáveis (composição fixa) | iguais | −3,39 | 8,86 | [−20,96; 14,92] | 0,734 | 33 (14 + 19) | 21 (13,8) | −18,32 (0,428) | −7,61 (0,188) | −25,94 (0,289) | −7,29 a 3,17 | −1,48 | 0,37 |
| A | B1: recomposição entre produtos continuados | pesos do modelo base | −3,40 | 1,26 | [−6,20; −0,23] | 0,038 | 33 (14 + 19) | 21 (12,1) | −2,61 (0,066) | 4,03 (0,118) | 1,42 (0,488) | −3,67 a −2,28 | −1,49 | 0,36 |
| A | B1: recomposição entre produtos continuados | iguais | −1,31 | 0,97 | [−3,58; 0,65] | 0,204 | 33 (14 + 19) | 21 (13,8) | −1,52 (0,091) | 1,17 (0,442) | −0,35 (0,798) | −1,65 a −0,58 | 0,60 | 2,45 |
| A | B2: entrada e saída de produtos | pesos do modelo base | 1,33 | 11,69 | [−24,64; 27,29] | 0,912 | 33 (14 + 19) | 21 (12,1) | 0,17 (0,993) | −2,27 (0,835) | −2,11 (0,944) | −6,32 a 8,76 | 3,24 | 5,09 |
| A | B2: entrada e saída de produtos | iguais | 8,39 | 9,28 | [−10,54; 27,77] | 0,387 | 33 (14 + 19) | 21 (13,8) | 17,77 (0,454) | −1,48 (0,839) | 16,29 (0,528) | 2,18 a 13,08 | 10,30 | 12,15 |
| G | índice original (médias por compra) | pesos do modelo base | 3,71 | 5,54 | [−7,53; 19,11] | 0,537 | 27 (11 + 16) | 18 (10,2) | 15,51 (0,051) | 5,62 (0,480) | 21,13 (0,047) | 1,96 a 8,43 | 5,62 | 7,47 |
| G | índice original (médias por compra) | iguais | 8,77 | 6,24 | [−3,82; 24,54] | 0,173 | 27 (11 + 16) | 18 (12,8) | 23,43 (0,008) | 1,31 (0,870) | 24,74 (0,040) | 6,39 a 12,10 | 10,68 | 12,53 |
| G | ΔĒ, média por item | pesos do modelo base | 0,58 | 4,19 | [−8,25; 9,70] | 0,904 | 27 (11 + 16) | 18 (10,2) | −1,33 (0,914) | −2,10 (0,570) | −3,43 (0,771) | −0,89 a 3,83 | 2,49 | 4,34 |
| G | ΔĒ, média por item | iguais | 2,21 | 4,56 | [−7,09; 12,42] | 0,623 | 27 (11 + 16) | 18 (12,8) | 1,83 (0,820) | −2,48 (0,677) | −0,66 (0,949) | 0,26 a 4,23 | 4,12 | 5,97 |
| G | A: preço de produtos comparáveis (composição fixa) | pesos do modelo base | 12,82 | 10,84 | [−11,51; 39,11] | 0,279 | 27 (11 + 16) | 18 (10,2) | 25,13 (0,217) | −3,09 (0,845) | 22,04 (0,349) | 6,40 a 19,29 | 14,73 | 16,58 |
| G | A: preço de produtos comparáveis (composição fixa) | iguais | −1,72 | 8,06 | [−18,59; 16,34] | 0,835 | 27 (11 + 16) | 18 (12,8) | 1,98 (0,901) | 4,26 (0,727) | 6,24 (0,735) | −6,14 a 2,96 | 0,19 | 2,04 |
| G | B1: recomposição entre produtos continuados | pesos do modelo base | −0,90 | 1,31 | [−4,26; 1,72] | 0,795 | 27 (11 + 16) | 18 (10,2) | 0,26 (0,745) | 1,82 (0,809) | 2,08 (0,572) | −1,15 a 0,47 | 1,01 | 2,86 |
| G | B1: recomposição entre produtos continuados | iguais | 0,72 | 0,79 | [−0,91; 2,57] | 0,378 | 27 (11 + 16) | 18 (12,8) | 0,66 (0,704) | −0,76 (0,540) | −0,11 (0,951) | 0,35 a 1,11 | 2,63 | 4,48 |
| G | B2: entrada e saída de produtos | pesos do modelo base | −11,34 | 12,10 | [−41,06; 13,03] | 0,413 | 27 (11 + 16) | 18 (10,2) | −26,72 (0,354) | −0,83 (0,947) | −27,55 (0,330) | −16,53 a −1,46 | −9,43 | −7,58 |
| G | B2: entrada e saída de produtos | iguais | 3,21 | 10,68 | [−19,75; 26,34] | 0,779 | 27 (11 + 16) | 18 (12,8) | −0,81 (0,971) | −5,98 (0,784) | −6,79 (0,800) | −3,50 a 9,72 | 5,12 | 6,97 |

**Cobertura de produtos antes e depois da troca** (DiD com sinal do AF, em p.p.):

| Espec. | Medida | Pesos | coef | EP | IC95 | p | eventos (A→AF + AF→A) | órgãos (efet.) | A → AF (p) | AF → A (p) | Soma (p) | sem um órgão: mín.–máx. | Δ vs −1,91 | Δ vs −3,76 |
|---|---|---|---:|---:|---|---:|---:|---:|---|---|---|---:|---:|---:|
| A | cobertura: itens pré em produtos continuados | pesos do modelo base | −6,17 | 2,15 | [−10,91; −1,32] | 0,013 | 77 (36 + 41) | 39 (17,2) | −3,18 (0,331) | 8,48 (0,113) | 5,31 (0,630) | −6,72 a −4,55 | −4,26 | −2,41 |
| A | cobertura: itens pré em produtos continuados | iguais | −5,90 | 2,10 | [−11,14; −1,16] | 0,019 | 77 (36 + 41) | 39 (13,0) | −2,91 (0,334) | 8,53 (0,079) | 5,62 (0,601) | −6,59 a −4,11 | −3,99 | −2,14 |
| A | cobertura: itens pós em produtos continuados | pesos do modelo base | −4,72 | 2,23 | [−9,81; 0,06] | 0,053 | 77 (36 + 41) | 39 (17,2) | −2,59 (0,296) | 6,37 (0,213) | 3,79 (0,562) | −5,39 a −3,19 | −2,81 | −0,96 |
| A | cobertura: itens pós em produtos continuados | iguais | −4,40 | 1,97 | [−9,62; −0,91] | 0,011 | 77 (36 + 41) | 39 (13,0) | −3,43 (0,087) | 5,25 (0,270) | 1,82 (0,795) | −5,30 a −2,74 | −2,49 | −0,64 |
| G | cobertura: itens pré em produtos continuados | pesos do modelo base | −4,66 | 2,28 | [−9,99; 0,13] | 0,057 | 71 (34 + 37) | 35 (15,7) | −1,83 (0,547) | 6,89 (0,297) | 5,05 (0,736) | −5,12 a −2,60 | −2,75 | −0,90 |
| G | cobertura: itens pré em produtos continuados | iguais | −4,61 | 2,30 | [−9,88; 0,63] | 0,090 | 71 (34 + 37) | 35 (13,0) | −1,43 (0,619) | 7,53 (0,177) | 6,10 (0,656) | −5,30 a −2,43 | −2,70 | −0,85 |
| G | cobertura: itens pós em produtos continuados | pesos do modelo base | −3,66 | 2,28 | [−9,12; 1,04] | 0,145 | 71 (34 + 37) | 35 (15,7) | −1,39 (0,580) | 5,45 (0,327) | 4,06 (0,565) | −4,36 a −1,82 | −1,75 | 0,10 |
| G | cobertura: itens pós em produtos continuados | iguais | −3,95 | 2,12 | [−9,69; −0,07] | 0,045 | 71 (34 + 37) | 35 (13,0) | −2,28 (0,238) | 5,49 (0,318) | 3,21 (0,677) | −4,61 a −2,05 | −2,04 | −0,19 |

**Parcela de medicamentos nas compras** (todos os itens de material; eventos e controles do modelo base):

| Espec. | Medida | Pesos | coef | EP | IC95 | p | eventos (A→AF + AF→A) | órgãos (efet.) | A → AF (p) | AF → A (p) | Soma (p) | sem um órgão: mín.–máx. | Δ vs −1,91 | Δ vs −3,76 |
|---|---|---|---:|---:|---|---:|---:|---:|---|---|---|---:|---:|---:|
| A | cobertura: parcela de medicamentos nas compras | pesos do modelo base | −3,15 | 1,01 | [−5,30; −0,91] | 0,005 | 152 (76 + 76) | 70 (24,7) | −4,41 (0,016) | 2,05 (0,101) | −2,36 (0,258) | −3,34 a −2,44 | −1,24 | 0,61 |
| G | cobertura: parcela de medicamentos nas compras | pesos do modelo base | −3,23 | 1,07 | [−5,58; −0,92] | 0,006 | 150 (73 + 77) | 68 (23,0) | −4,31 (0,017) | 2,31 (0,090) | −1,99 (0,309) | −3,43 a −2,40 | −1,32 | 0,53 |

- **Pré-tendências.**
  - Nulas para o índice original, o total por item e o preço de comparáveis.
  - Exceção nominal: a recomposição em A (−3,40, p = 0,04), 1 em 20 testes, compatível com o acaso.
  - Em G, o índice original na pseudojanela tem efeito de +15,5 no sentido A → AF (p = 0,05; 11 eventos).
- **Simetria.** Rejeitada a 5% em 4 de 74 testes, todos na especificação G:
  - índice original na amostra da decomposição: A → AF −9,4 e AF → A +3,2, soma −6,2, p = 0,023;
  - entrada e saída com pesos iguais: p = 0,044;
  - índice original na pseudojanela: p = 0,047 e 0,040.

  Na especificação G, a entrada no AF concentra os efeitos. Isso pede cautela na leitura agregada.
- **Cobertura.**
  - Na troca para o AF, a fração de itens em produtos continuados cai 6,2 p.p. em A (p = 0,013) e 4,7 p.p. em G
    (p = 0,057).
  - A parcela de medicamentos cai 3,2 p.p. (p ≈ 0,005).
  - A composição muda, mas pouco, e não explica o efeito estimado (testes 1 e 4).
- **Pesos.** Com pesos iguais, as estimativas mudam pouco em A e enfraquecem em G (perdem significância nos demais
  materiais). Os resultados de G dependem, em parte, dos eventos com mais compras.
- **Órgãos.** Na amostra completa há 23 a 26 órgãos efetivos; na amostra da decomposição, 13 a 17; nos medicamentos, 5 a 9.

## Gráficos

`graficos/`: `g1_grupos.svg` (teste 1), `g2_interacao.svg` (teste 2), `g3_composicao_fixa.svg` (teste 3),
`g4_decomposicao.svg` (teste 4) e `g5_pre_tendencia.svg` (teste 5). Cada um tem a versão em tabela em
`tabelas/todas_estimativas.csv`.

![Grupos](graficos/g1_grupos.svg)
![Interação](graficos/g2_interacao.svg)
![Composição fixa](graficos/g3_composicao_fixa.svg)
![Decomposição](graficos/g4_decomposicao.svg)
![Pré-tendência](graficos/g5_pre_tendencia.svg)

## Exclusões, falhas e limitações

- **Execução:** sem falhas (`registro_execucao.json`). Conferido:
  - M0 e M1 reproduzidos;
  - "todos" com controles fixos idêntico ao modelo base (diferença 0);
  - identidade da decomposição;
  - eventos reservados excluídos.
- **Teste 1:**
  - medicamentos com 42 eventos em A e 41 em G, em vez de 152 e 150, porque os outros não têm compras de medicamentos nas
    duas meias janelas;
  - com controles novos, 20 eventos.
- **Teste 2:** interação não identificável pelo critério do protocolo, por falta de órgãos efetivos.
- **Testes 3 e 4:**
  - só eventos em que a tratada e pelo menos 5 controles têm produto continuado: 77 de 152 em A e 71 de 150 em G;
  - na pseudojanela, 33 e 27;
  - os produtos continuados cobrem 10–15% dos itens.
- **Decomposição:** B1 e B2 não têm leitura causal isolada.
- **Ponderação dos índices:** o índice original faz a média por compra; o fixo e a decomposição fazem a média por item.
  A diferença de agregação (ΔĒ − original) é de −1,5 lp em A e +0,6 em G, sem significância.
- **Não feito:**
  - pesos de despesa (P × Q) pré-tratamento, que usariam preço;
  - teste confirmatório.

## Reprodução

```
python analises/composicao_precos_medicamentos_20261123/executar.py
```

Leva cerca de 5 minutos. Pré-requisito: a base de 23/11 (`../testes_desenho_causal_20261123/preparar.py`).
