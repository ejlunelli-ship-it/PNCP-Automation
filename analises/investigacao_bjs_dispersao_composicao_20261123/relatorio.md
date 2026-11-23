# Investigação complementar: BJS × estudo de eventos, dispersão histórica × contemporânea e composição das compras (23/11/2026)

**Todos os resultados são exploratórios.** As definições estão em `protocolo.md`, escrito antes da execução (hash em
`registro_execucao.json`). Nenhuma especificação foi escolhida pela significância.

Regras seguidas:
- **Bases:** a de 23/11 e o motor item a item de `../robustez_dispersao_20261123/`, que reproduz exatamente M0 (−1,91 lp,
  152 eventos) e M1 (−3,76 lp, 150 eventos). Nada foi alterado, e o `pncp.db` não foi lido.
- **Eventos reservados:** o último mês de evento usado é 2025-10. Os 56 eventos de 2025-11 em diante, reservados para a
  validação confirmatória, não entraram; o script confere isso.
- **Inferência:** agrupada por órgão (CNPJ), com bootstrap selvagem restrito (Webb, B = 9.999). As diferenças pareadas
  usam bootstrap não restrito do t.
- **Influência:** retirando os eventos de um órgão de cada vez, informam-se o mínimo, o máximo e a maior variação.

Unidades: lp = 100 × diferença em log; p.p. = pontos percentuais (100 × diferença de parcelas).

## Resumo dos resultados verificados

1. **BJS × estudo de eventos com os mesmos insumos.** Com os mesmos itens, eventos, controles, janela e elegibilidade,
   trocar o estimador muda pouco e sem significância:
   - **especificação A:** −1,83 lp (IC [−7,55; +3,89], p = 0,56);
   - **especificação G:** +0,13 lp (IC [−3,15; +3,40], p = 0,94).

   Nenhum dos três componentes da diferença entre o BJS original e o empilhado é significativo: amostra de itens,
   estimador, conjunto de controles e períodos. O total fica em −1,63 lp (p = 0,37) em A e −1,08 lp (p = 0,59) em G.
   - **Itens imputáveis:** o BJS do evento só imputa 32% (A) e 29% (G) dos itens pós-troca das tratadas, por exigir o
     mesmo produto no mesmo trimestre entre os controles.
   - **Ponderação:** com pesos iguais, a estimativa G nos itens imputáveis cai de −4,68 para −0,96 lp, e a do BJS do
     evento de −4,56 para −0,04 lp. O resultado G está concentrado nos eventos com muitas compras.
2. **Dispersão histórica × contemporânea na amostra comum** (mesmos itens, eventos, controles e pesos):

   | Filtro | Efeito do AF | IC95 | p | Eventos |
   |---|---:|---|---:|---:|
   | Contemporâneo | −3,99 lp | [−7,30; −0,56] | 0,025 | 140 |
   | Histórico | −1,58 lp | [−5,94; +2,66] | 0,47 | 139 |
   | Diferença | −2,46 lp | [−5,62; +0,71] | 0,13 | 139 |

   - Retirar os itens sem histórico não muda o resultado contemporâneo (−0,08 lp, p = 0,94). A divergência vem de quais
     itens cada filtro mantém, não da falta de histórico.
   - 25,0% dos pares item–evento não têm histórico. A falta de histórico não muda com a troca de modo: DiD de +1,4 p.p.
     (p = 0,29) e, com as características do produto, item de compra AF +0,2 p.p. (p = 0,89).
   - O que explica a falta de histórico é a raridade do produto: −17,5 p.p. por unidade de log do nº de UASGs que o
     compram. Os itens excluídos são mais raros, mais caros e com bem menos medicamentos.
3. **Composição na troca de modo.** A única mudança com sinais opostos na entrada e na saída do AF, e no momento da troca,
   é a **parcela de medicamentos**:
   - efeito com sinal −3,18 p.p. (IC [−5,41; −0,91], p = 0,004, Holm 0,06);
   - A → AF −4,29 p.p. (p = 0,016) e AF → A +2,20 p.p. (p = 0,079);
   - sem pré-tendência (−0,60, p = 0,58), queda já no trimestre da troca (−3,30, p < 0,001);
   - na troca fictícia, nulo (+0,82, p = 0,79).

   As demais mudanças:
   - **Repetição de produtos e de CATMAT:** −3 a −4 p.p. com sinal (p ≈ 0,02; Holm ≈ 0,3), vindo sobretudo do abandono
     do AF (+5 a +6 p.p.) e sem padrão no tempo.
   - **Estimado:** +3,0 lp (p = 0,06), vindo da adoção (+6,0, p = 0,046), sem padrão no tempo.
   - **Sem mudança sistemática:** quantidade, nº de itens e de CATMATs, parcela com índice e elegibilidade ao filtro
     (contemporâneo −1,35 p.p., p = 0,36; histórico −0,94 p.p., p = 0,47).

   Nada resiste a Holm a 5%.

**Leitura.**
- A diferença entre o BJS e o estudo de eventos não é efeito do estimador: com os mesmos insumos, os dois concordam.
- A diferença entre os filtros de dispersão também não é significativa, mas o efeito de −4 lp continua aparecendo só com
  a dispersão contemporânea e com pesos de precisão.
- A troca para o AF coincide com menos medicamentos nas compras. Como o índice de preço compara o mesmo produto, isso não
  enviesa mecanicamente o preço, mas aponta uma mudança de carteira junto com o modo. Vale estimar o efeito em separado
  para medicamentos e para os demais itens num próximo protocolo.

## 1. BJS × estudo de eventos com os mesmos insumos

- **Base:** eventos e controles de M0 (A) e de M1 (G); usam-se os eventos presentes nos quatro passos (128 em A, 124 em G).
- **S0:** DiD empilhado do modelo base.
- **S1:** DiD empilhado só com os itens pós-troca imputáveis pelo BJS do evento; os itens pré e os dos controles ficam
  iguais.
- **S2:** BJS do evento com os mesmos itens: log P = α_unidade + γ_produto×trimestre, estimado com os controles e com os
  itens pré da tratada.
- **S3:** BJS original, com as unidades estáveis no período todo.
- **Itens pós-troca imputáveis:** 9.540 de 29.611 em A (32%) e 7.559 de 25.945 em G (29%).

| Especificação | Passo | Pesos | coef (lp) | IC95 | p | eventos | órgãos (efet.) | itens tratadas | sem um órgão: mín.–máx. | maior Δ |
|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|
| A | S0 empilhado, modelo base | pesos de S0 congelados | −0,97 | [−4,87; 3,08] | 0,618 | 128 | 60 (22,4) | 52.048 | −1,62 a −0,34 | 0,65 |
| A | S1 empilhado, só itens imputáveis | pesos de S0 congelados | −0,25 | [−5,67; 4,96] | 0,920 | 128 | 60 (22,4) | 31.977 | −1,31 a 0,44 | 1,06 |
| A | S2 BJS do evento (mesmos itens, controles e janela) | pesos de S0 congelados | −2,08 | [−8,08; 3,67] | 0,501 | 128 | 60 (22,4) | 31.977 | −3,19 a −0,49 | 1,59 |
| A | S3 BJS original (unidades estáveis, período todo) | pesos de S0 congelados | −2,60 | [−6,10; 1,20] | 0,168 | 128 | 60 (22,4) | 20.335 | −3,22 a −2,06 | 0,62 |
| A | S0 empilhado, modelo base | pesos iguais | 0,02 | [−5,29; 6,36] | 0,993 | 128 | 60 (18,0) | 52.048 | −1,29 a 1,21 | 1,32 |
| A | S1 empilhado, só itens imputáveis | pesos iguais | 2,21 | [−4,49; 8,63] | 0,507 | 128 | 60 (18,0) | 31.977 | 0,69 a 3,45 | 1,52 |
| A | S2 BJS do evento (mesmos itens, controles e janela) | pesos iguais | −1,23 | [−9,64; 5,67] | 0,760 | 128 | 60 (18,0) | 31.977 | −2,39 a 0,87 | 2,10 |
| A | S3 BJS original (unidades estáveis, período todo) | pesos iguais | −1,67 | [−6,90; 3,91] | 0,523 | 128 | 60 (18,0) | 20.335 | −2,79 a −0,71 | 1,12 |
| A | S0 empilhado, modelo base | precisão própria | −0,97 | [−4,87; 3,08] | 0,618 | 128 | 60 (22,4) | 52.048 | −1,62 a −0,34 | 0,65 |
| A | S1 empilhado, só itens imputáveis | precisão própria | −0,01 | [−4,93; 4,76] | 0,995 | 128 | 60 (20,5) | 31.977 | −0,95 a 0,70 | 0,93 |
| A | S2 BJS do evento (mesmos itens, controles e janela) | precisão própria | −1,91 | [−6,82; 2,85] | 0,438 | 128 | 60 (20,5) | 31.977 | −2,77 a −1,04 | 0,87 |
| A | S3 BJS original (unidades estáveis, período todo) | precisão própria | −2,60 | [−6,10; 1,20] | 0,168 | 128 | 60 (22,4) | 20.335 | −3,22 a −2,06 | 0,62 |
| G | S0 empilhado, modelo base | pesos de S0 congelados | −3,90 | [−6,92; −0,85] | 0,014 | 124 | 57 (20,4) | 46.516 | −4,60 a −3,43 | 0,70 |
| G | S1 empilhado, só itens imputáveis | pesos de S0 congelados | −4,68 | [−9,32; −0,49] | 0,026 | 124 | 57 (20,4) | 28.130 | −5,41 a −3,66 | 1,03 |
| G | S2 BJS do evento (mesmos itens, controles e janela) | pesos de S0 congelados | −4,56 | [−9,38; −0,02] | 0,049 | 124 | 57 (20,4) | 28.130 | −5,44 a −3,32 | 1,23 |
| G | S3 BJS original (unidades estáveis, período todo) | pesos de S0 congelados | −4,98 | [−8,04; −1,95] | 0,005 | 124 | 57 (20,4) | 15.767 | −5,49 a −4,42 | 0,56 |
| G | S0 empilhado, modelo base | pesos iguais | −2,70 | [−6,11; 0,89] | 0,117 | 124 | 57 (16,7) | 46.516 | −3,35 a −2,27 | 0,64 |
| G | S1 empilhado, só itens imputáveis | pesos iguais | −0,96 | [−6,15; 4,48] | 0,702 | 124 | 57 (16,7) | 28.130 | −1,90 a −0,41 | 0,94 |
| G | S2 BJS do evento (mesmos itens, controles e janela) | pesos iguais | −0,04 | [−6,38; 5,70] | 0,990 | 124 | 57 (16,7) | 28.130 | −1,35 a 0,72 | 1,31 |
| G | S3 BJS original (unidades estáveis, período todo) | pesos iguais | −3,20 | [−7,70; 0,81] | 0,106 | 124 | 57 (16,7) | 15.767 | −4,13 a −2,61 | 0,93 |
| G | S0 empilhado, modelo base | precisão própria | −3,90 | [−6,92; −0,85] | 0,014 | 124 | 57 (20,4) | 46.516 | −4,60 a −3,43 | 0,70 |
| G | S1 empilhado, só itens imputáveis | precisão própria | −4,43 | [−8,39; −0,84] | 0,015 | 124 | 57 (18,6) | 28.130 | −5,09 a −3,85 | 0,66 |
| G | S2 BJS do evento (mesmos itens, controles e janela) | precisão própria | −4,12 | [−7,93; −0,52] | 0,026 | 124 | 57 (18,6) | 28.130 | −4,97 a −3,47 | 0,84 |
| G | S3 BJS original (unidades estáveis, período todo) | precisão própria | −4,98 | [−8,04; −1,95] | 0,005 | 124 | 57 (20,4) | 15.767 | −5,49 a −4,42 | 0,56 |

**Decomposição** (diferenças pareadas nos mesmos eventos):

| Especificação | Componente | Pesos | Δ (lp) | IC95 (WCU) | p | eventos | órgãos |
|---|---|---|---:|---|---:|---:|---:|
| A | amostra de itens (S1 − S0) | pesos de S0 congelados | 0,72 | [−3,37; 4,81] | 0,747 | 128 | 60 |
| A | estimador, mesmos insumos (S2 − S1) | pesos de S0 congelados | −1,83 | [−7,55; 3,89] | 0,561 | 128 | 60 |
| A | controles e períodos do BJS original (S3 − S2) | pesos de S0 congelados | −0,52 | [−6,09; 5,04] | 0,866 | 128 | 60 |
| A | total (S3 − S0) | pesos de S0 congelados | −1,63 | [−5,09; 1,83] | 0,370 | 128 | 60 |
| A | amostra de itens (S1 − S0) | pesos iguais | 2,19 | [−1,82; 6,19] | 0,302 | 128 | 60 |
| A | estimador, mesmos insumos (S2 − S1) | pesos iguais | −3,43 | [−10,04; 3,17] | 0,350 | 128 | 60 |
| A | controles e períodos do BJS original (S3 − S2) | pesos iguais | −0,44 | [−6,64; 5,75] | 0,904 | 128 | 60 |
| A | total (S3 − S0) | pesos iguais | −1,69 | [−6,01; 2,63] | 0,458 | 128 | 60 |
| G | amostra de itens (S1 − S0) | pesos de S0 congelados | −0,78 | [−3,80; 2,23] | 0,621 | 124 | 57 |
| G | estimador, mesmos insumos (S2 − S1) | pesos de S0 congelados | 0,13 | [−3,15; 3,40] | 0,944 | 124 | 57 |
| G | controles e períodos do BJS original (S3 − S2) | pesos de S0 congelados | −0,42 | [−3,96; 3,12] | 0,842 | 124 | 57 |
| G | total (S3 − S0) | pesos de S0 congelados | −1,08 | [−4,91; 2,76] | 0,587 | 124 | 57 |
| G | amostra de itens (S1 − S0) | pesos iguais | 1,74 | [−1,95; 5,44] | 0,358 | 124 | 57 |
| G | estimador, mesmos insumos (S2 − S1) | pesos iguais | 0,93 | [−2,86; 4,72] | 0,645 | 124 | 57 |
| G | controles e períodos do BJS original (S3 − S2) | pesos iguais | −3,16 | [−6,81; 0,49] | 0,096 | 124 | 57 |
| G | total (S3 − S0) | pesos iguais | −0,49 | [−4,60; 3,62] | 0,809 | 124 | 57 |

- **Estimador.** Com os mesmos insumos, a troca de estimador fica dentro do ruído: −1,83 lp em A e +0,13 lp em G. Em G,
  S1 e S2 quase coincidem (−4,68 e −4,56).
- **Amostra.** Restringir aos itens imputáveis muda pouco com os pesos de S0 (+0,72 em A, −0,78 em G).
- **Controles e períodos.** O conjunto do BJS original acrescenta −0,4 a −0,5 lp com os pesos de S0. Com pesos iguais, em
  G, acrescenta −3,16 lp (p = 0,096).
- **Ponderação.** É o fator que mais mexe em G. Com pesos iguais, S1 vai a −0,96 e S2 a −0,04, enquanto S0 fica em −2,70.
  O efeito de −4 a −5 lp depende dos eventos com mais compras, que os pesos de precisão favorecem.
- **Eventos.** Nos 128 eventos comuns de A, o próprio S0 é −0,97 lp, contra −1,91 nos 152. A composição de eventos também
  pesa.
- **Influência.** Nenhum órgão muda as conclusões: a maior variação ao retirar um órgão vai de 0,56 a 2,10 lp. Há 16,7 a
  22,4 órgãos efetivos.

## 2. Dispersão histórica × contemporânea na amostra comum

- **Base:** G com todas as células, 161 eventos e 75 órgãos. Eventos, controles e pesos (precisão de G-todas) ficam fixos.
- **Amostra comum:** itens com as duas dispersões definidas.

| Variante ou comparação | coef (lp) | IC95 | p | eventos | órgãos (efet.) | itens tratadas | compras tratadas | sem um órgão: mín.–máx. | maior Δ |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| (a) todos os itens G | −1,61 | [−5,81; 2,50] | 0,425 | 161 | 75 (25,3) | 66.729 | 4.068 | −2,32 a −1,11 | 0,71 |
| (b) amostra comum (as duas dispersões definidas) | 1,14 | [−4,47; 7,02] | 0,707 | 143 | 69 (26,3) | 46.245 | 3.275 | −0,28 a 1,94 | 1,41 |
| (c) amostra comum, contemporânea ≤ 0,80 | −3,99 | [−7,30; −0,56] | 0,025 | 140 | 67 (25,8) | 35.901 | 2.845 | −4,65 a −3,54 | 0,66 |
| (d) amostra comum, histórica ≤ 0,80 | −1,58 | [−5,94; 2,66] | 0,465 | 139 | 66 (25,7) | 37.694 | 2.863 | −2,28 a −0,91 | 0,71 |
| (e) todos os itens, contemporânea ≤ 0,80 | −4,03 | [−7,05; −1,14] | 0,007 | 161 | 75 (25,3) | 50.446 | 3.547 | −4,70 a −3,58 | 0,68 |
| definição do filtro, mesmos itens: (c) − (d) | −2,46 | [−5,62; 0,71] | 0,134 | 139 | 66 | — | — | — | — |
| retirar itens sem histórico, filtro contemporâneo: (e) − (c) | −0,08 | [−2,36; 2,20] | 0,944 | 140 | 67 | — | — | — | — |
| retirar itens sem histórico, sem filtro: (b) − (a) | 3,06 | [−1,01; 7,13] | 0,152 | 143 | 69 | — | — | — | — |
| filtro histórico contra todos: (d) − (a) | 0,25 | [−3,20; 3,71] | 0,889 | 139 | 66 | — | — | — | — |
| filtro contemporâneo contra todos: (e) − (a) | −2,41 | [−6,18; 1,35] | 0,209 | 161 | 75 | — | — | — | — |

- **Mesmos itens.** O filtro contemporâneo (c) dá −3,99 e o histórico (d) −1,58. A diferença de −2,46 lp não é
  significativa (p = 0,13).
- **Itens sem histórico.** Retirá-los não muda o resultado do filtro contemporâneo: (e) − (c) = −0,08.
- **Sem filtro.** Na amostra comum sem filtro (b), a estimativa sobe para +1,14. Os dois filtros puxam o resultado para
  baixo: o contemporâneo em −5,1 lp, o histórico em −2,7.

**Exclusões por falta de histórico.**
- 3.628.157 de 14.485.864 pares item–evento com índice G (25,0%) não têm dispersão histórica. Os pares incluem as unidades
  tratadas e os controles de cada evento. Detalhe em `tabelas/p2_exclusoes_por_grupo.csv`.
- Nas tratadas:

  | Sentido | Pré, compras A | Pré, compras AF | Pós, compras A | Pós, compras AF |
  |---|---:|---:|---:|---:|
  | A → AF | 28,6% | 20,1% | 34,6% | 41,9% |
  | AF → A | 9,2% | 26,2% | 31,1% | 31,5% |

- Nos controles, a falta de histórico sobe de 16–23% no pré para 27–29% no pós. É mecânico: a dispersão histórica olha os
  4 trimestres antes da janela, e produtos comprados mais tarde estão menos cobertos.

| Teste (itens das tratadas, efeito fixo de evento; 75 órgãos) | Coeficiente | IC95 | p |
|---|---:|---|---:|
| DiD da parcela sem histórico (tratada pós − pré − controles; 161 eventos) | +1,41 p.p. | [−1,29; +4,04] | 0,29 |
| — só A → AF / só AF → A | +1,83 / −1,03 p.p. | | 0,30 / 0,60 |
| sem histórico ~ compra AF (n = 66.729) | +1,90 p.p. | [−0,99; +4,78] | 0,19 |
| sem histórico ~ compra AF + características (n = 60.740): coef. de compra AF | +0,16 p.p. | [−2,16; +2,48] | 0,89 |
| — coef. do log da frequência do produto (nº de UASGs que o compram) | −17,46 p.p. | [−19,73; −15,20] | < 0,001 |
| — coef. de medicamento | +1,73 p.p. | [−1,39; +4,84] | 0,28 |
| — coef. do nível de preço de mercado (log) | +0,35 p.p. | [−0,04; +0,75] | 0,07 |
| sem histórico ~ pós-troca (n = 66.729) | +6,61 p.p. | [+3,74; +9,49] | < 0,001 |

Características dos itens sem histórico, contra os com histórico, no mesmo evento (148 eventos, 71 órgãos; todas com
p < 0,01):

| Característica | Diferença | IC95 |
|---|---:|---|
| Medicamentos | −16,4 p.p. | [−17,3; −15,6] |
| Apresentação padronizada (H1) | −1,7 p.p. | [−2,7; −0,6] |
| Nível de preço de mercado | +1,27 log, ≈ 3,6 vezes | [1,20; 1,35] |
| Índice de quantidade | −0,19 log | [−0,28; −0,11] |
| Frequência do produto | −1,28 log | [−1,30; −1,26] |

A falta de histórico não acompanha a troca de modo. Ela depende de quão comum é o produto. O filtro histórico exclui,
sobretudo, produtos raros e caros e preserva os medicamentos.

## 3. Composição das compras na troca de modo

- **Base:** eventos, controles e pesos de G-todas (161 eventos, 75 órgãos, 25,3 efetivos).
- **Efeito com sinal:** A → AF menos AF → A, ou seja, o componente específico do AF.
- **Soma dos sentidos:** componente comum a qualquer troca.
- Holm entre as 15 características.

| Característica | Efeito do AF (com sinal) | IC95 | p (Holm) | A → AF (p) | AF → A (p) | Soma dos sentidos (p; Holm) | eventos | órgãos (efet.) | sem um órgão: mín.–máx. |
|---|---:|---|---|---|---|---|---:|---:|---:|
| repetição de CATMAT (12 meses) | −3,45 | [−6,46; −0,50] | 0,020 (0,281) | −1,28 (0,374) | 5,35 (0,023) | 4,07 (0,158; 1,000) | 161 | 75 (25,3) | −3,97 a −2,55 |
| repetição de produto (12 meses) | −3,12 | [−5,99; −0,45] | 0,022 (0,286) | −1,17 (0,454) | 4,83 (0,025) | 3,66 (0,263; 1,000) | 161 | 75 (25,3) | −3,63 a −2,24 |
| parcela de medicamentos (6505) | −3,18 | [−5,41; −0,91] | 0,004 (0,060) | −4,29 (0,016) | 2,20 (0,079) | −2,09 (0,295; 1,000) | 161 | 75 (25,3) | −3,36 a −2,40 |
| log do nº de CATMATs distintos | −3,67 | [−16,01; 8,70] | 0,554 (1,000) | −2,31 (0,773) | 4,86 (0,540) | 2,55 (0,782; 1,000) | 161 | 75 (25,3) | −6,05 a −0,47 |
| índice de quantidade | 0,88 | [−12,16; 12,75] | 0,886 (1,000) | 5,09 (0,646) | 2,80 (0,728) | 7,89 (0,600; 1,000) | 161 | 75 (25,3) | −1,77 a 3,12 |
| log da quantidade | 1,56 | [−25,03; 28,37] | 0,905 (1,000) | 2,17 (0,883) | −1,02 (0,952) | 1,15 (0,956; 1,000) | 161 | 75 (25,3) | −3,60 a 6,58 |
| índice do estimado (eR) | 2,99 | [−0,20; 6,24] | 0,064 (0,624) | 5,99 (0,046) | −0,34 (0,900) | 5,66 (0,228; 1,000) | 160 | 75 (25,5) | 2,39 a 3,49 |
| parcela com índice G | −0,23 | [−3,28; 2,90] | 0,877 (1,000) | −0,39 (0,844) | 0,09 (0,961) | −0,30 (0,899; 1,000) | 161 | 75 (25,3) | −0,74 a 0,46 |
| parcela elegível (contemporânea) | −1,35 | [−4,22; 1,68] | 0,355 (1,000) | −0,57 (0,766) | 2,03 (0,297) | 1,47 (0,553; 1,000) | 161 | 75 (25,3) | −1,71 a −0,74 |
| log do nº de itens | −5,41 | [−16,99; 6,14] | 0,362 (1,000) | −3,77 (0,603) | 6,84 (0,335) | 3,07 (0,731; 1,000) | 161 | 75 (25,3) | −7,22 a −2,15 |
| sobreposição de produtos | −3,66 | [−7,15; −0,41] | 0,025 (0,302) | −1,88 (0,235) | 5,22 (0,159) | 3,34 (0,498; 1,000) | 161 | 75 (25,3) | −4,13 a −2,65 |
| sobreposição de CATMAT | −4,20 | [−8,33; −0,42] | 0,026 (0,302) | −1,66 (0,364) | 6,43 (0,145) | 4,77 (0,464; 1,000) | 161 | 75 (25,3) | −4,72 a −2,79 |
| Duncan (classes) | 7,05 | [−0,55; 13,71] | 0,062 (0,624) | −0,79 (0,860) | −13,92 (0,090) | −14,71 (0,120; 1,000) | 161 | 75 (25,3) | 5,05 a 8,52 |
| parcela com dispersão histórica (DiD) | −1,41 | [−4,04; 1,29] | 0,294 (1,000) | −1,83 (0,304) | 1,03 (0,604) | −0,80 (0,756; 1,000) | 161 | 75 (25,3) | −1,78 a −0,92 |
| parcela histórica ≤ 0,80 (DiD) | −0,94 | [−3,46; 1,69] | 0,473 (1,000) | 0,94 (0,639) | 2,55 (0,119) | 3,49 (0,157; 1,000) | 143 | 69 (26,3) | −1,42 a −0,53 |

Perfil por trimestre de evento (base −1; IC por t(G − 1)):

| Característica | trim. −2 (p) | trim. 0 (p) | trim. +1 (p) | p conjunto pré | p conjunto pós |
|---|---|---|---|---:|---:|
| repetição de CATMAT (12 meses) | 3,12 (0,118) | −1,79 (0,267) | −1,09 (0,556) | 0,118 | 0,509 |
| repetição de produto (12 meses) | 2,51 (0,217) | −1,64 (0,287) | −0,89 (0,609) | 0,217 | 0,516 |
| parcela de medicamentos (6505) | −0,60 (0,580) | −3,30 (< 0,001) | −3,40 (< 0,001) | 0,580 | < 0,001 |
| log do nº de CATMATs distintos | 7,36 (0,451) | −7,75 (0,401) | 10,44 (0,284) | 0,451 | 0,060 |
| índice de quantidade | 2,88 (0,771) | 3,01 (0,694) | −0,03 (0,998) | 0,771 | 0,893 |
| log da quantidade | −15,62 (0,314) | 2,48 (0,884) | −16,03 (0,364) | 0,314 | 0,454 |
| índice do estimado (eR) | 1,42 (0,671) | 0,83 (0,783) | −0,52 (0,862) | 0,671 | 0,904 |
| parcela com índice G | 0,86 (0,649) | −0,66 (0,663) | 0,27 (0,874) | 0,649 | 0,682 |
| parcela elegível (contemporânea) | 1,09 (0,667) | −2,86 (0,210) | −0,98 (0,713) | 0,667 | 0,355 |
| log do nº de itens | 8,33 (0,403) | −7,25 (0,433) | 8,49 (0,381) | 0,403 | 0,114 |

Troca fictícia 12 meses antes, com a unidade estável (39 trocas válidas, 25 a 30 com dados):

| Característica | Efeito com sinal (p) | Soma dos sentidos (p) | eventos | órgãos |
|---|---|---|---:|---:|
| repetição de CATMAT (12 meses) | −0,35 (0,917) | 10,73 (0,077) | 29 | 21 |
| repetição de produto (12 meses) | 0,01 (0,998) | 11,45 (0,059) | 29 | 21 |
| parcela de medicamentos (6505) | 0,82 (0,789) | 6,90 (0,481) | 30 | 21 |
| log do nº de CATMATs distintos | −2,48 (0,795) | −27,79 (0,149) | 30 | 21 |
| índice de quantidade | 19,89 (0,295) | 17,75 (0,683) | 27 | 20 |
| log da quantidade | 50,79 (0,121) | 68,72 (0,455) | 30 | 21 |
| índice do estimado (eR) | 1,52 (0,756) | 6,67 (0,455) | 25 | 19 |
| parcela com índice G | 3,84 (0,112) | −0,14 (0,978) | 30 | 21 |
| parcela elegível (contemporânea) | −2,41 (0,423) | 11,01 (0,015) | 26 | 20 |
| log do nº de itens | −4,41 (0,700) | −28,88 (0,212) | 30 | 21 |

- **Medicamentos.** Única característica com sinais opostos na entrada (−4,3 p.p.) e na saída (+2,2) do AF, com a mudança
  concentrada no trimestre da troca e sem pré-tendência. A troca fictícia é nula. Retirando um órgão de cada vez, o efeito
  fica entre −3,36 e −2,40. Na adoção do AF, as unidades passam a comprar proporcionalmente menos medicamentos que os
  controles.
- **Repetição e sobreposição.** O efeito com sinal (−3 a −4 p.p.) vem do abandono do AF (+5 a +6 p.p.). A adoção dá −1 a
  −2 p.p., sem significância, e o perfil não mostra mudança no momento da troca.
- **Estimado.** Sobe na adoção (+6,0 lp, p = 0,046), mas não no abandono, e o perfil é plano. É um sinal fraco.
- **Sem mudança sistemática:** quantidade, nº de itens e de CATMATs, parcela com índice e elegibilidade aos filtros. No
  placebo, a soma dos sentidos da elegibilidade tem p = 0,015, com só 26 eventos, o que indica instabilidade e não um
  efeito.
- **Dissimilaridade de classes (Duncan).** O efeito com sinal (+7,1, p = 0,06) vem de os eventos AF → A mudarem menos de
  classe que seus controles (−13,9, p = 0,09). É um sinal fraco.

## Diagnósticos de influência (resumo)

- **Órgãos efetivos:** de 16,7 a 26,3, conforme a amostra e os pesos.
- **Retirando um órgão de cada vez:**
  - nas estimativas de preço, a maior variação vai de 0,56 a 2,10 lp;
  - nas de composição, de 0,48 a 5,16, chegando a 5,16 lp no log da quantidade, que é muito ruidoso;
  - nas de medicamentos e de repetição, as estimativas ficam entre −3,97 e −2,24 p.p. Nenhum órgão isolado produz os
    padrões.
- Valores por especificação em `tabelas/todas_estimativas.csv`, colunas `loo_*`, `orgao_mais_influente` e
  `peso_maior_orgao`.

## Limitações

- **BJS do evento:** só imputa cerca de 30% dos itens pós-troca. A comparação com os mesmos insumos vale para esse
  subconjunto, de produtos que os controles compram no mesmo trimestre.
- **Amostra comum:** a decomposição usa os eventos presentes em S0 a S3 (128 e 124). Nessa amostra, o S0 de A dá −0,97, não
  −1,91.
- **Dispersão histórica:** depende dos 4 trimestres anteriores. Produtos comprados mais tarde na janela ficam menos
  cobertos, e esse efeito mecânico é igual para tratadas e controles.
- **Composição:** as medidas por evento (sobreposição, Duncan) são de mudança, tratada menos controles, sem pré-tendência
  própria. A troca fictícia tem poucos eventos.
- **Comparações múltiplas:** nada resiste a Holm a 5% na parte 3.
- **Não feito:** o efeito no preço em separado para medicamentos e para os demais itens. Fica sugerido para um próximo
  protocolo, já que a composição de medicamentos muda na troca.

## Registro de execução

- **Execução:** 23/11/2026, 857 s, com `python analises/investigacao_bjs_dispersao_composicao_20261123/investigar.py`.
- **Status:** base, parte 1, parte 2 e parte 3 terminaram com "ok".
- **Conferências:**
  - M0 e M1 reproduzidos;
  - nenhum evento posterior a 2025-10 (56 reservados);
  - todas as tabelas gravadas.
- **Exclusões registradas:**
  - parte 1: eventos sem 2 compras pré e pós com itens imputáveis (A: 152 → 128; G: 150 → 124);
  - parte 2: 25,0% dos pares item–evento sem histórico;
  - parte 3: 39 trocas fictícias válidas.

## Reprodução

```
python analises/investigacao_bjs_dispersao_composicao_20261123/investigar.py
```

Pré-requisitos no `README.md`.
