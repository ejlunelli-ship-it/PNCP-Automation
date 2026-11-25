# Conclusão — o risk-set matching não melhorou a identificação do efeito do AF na S1

25/11/2026. Os números vêm de [`relatorio.md`](relatorio.md), `tabelas/` e `resultados/`.

**Resumo:**
- Com as regras predefinidas, o desenho **não tem suporte**: 4 eventos pareados (de 309 na janela), todos adoções.
- Só 2 eventos têm desfecho observável em t0.
- O protocolo declarou a insuficiência **antes** da Fase II, por isso as estimativas abaixo são **descritivas**.
- O matching **não resolveu a endogeneidade** e não oferece evidência causal mais convincente que o estudo anterior.

## Respostas

**1. Quantas UASGs que mudaram de modo encontraram controles adequados?** Quatro, de quatro CNPJs, todas adoções A→AF.

| Etapa | Eventos |
|---|---|
| eventos inequívocos (todos) | 612 |
| na janela de calendário | 309 |
| histórico suficiente | 9 |
| com controles no conjunto de risco | 9 |
| no suporte comum do PS | 5 |
| matching aceito | 5 |
| balanceamento do evento aceitável | 4 |

**2. Qual proporção dos eventos foi preservada?**
- No desenho: 4/309 = 1,3%.
- Com desfecho estimável em t0: 2/309 = 0,6%.

As perdas vêm do histórico de modo (182 eventos com trimestre misto ou no destino entre t0−6 e t0−2) e da falta de
índice S1 nos períodos pré (118). A tabela de viabilidade (só contagens) mostra que nem regras bem mais fracas dariam
um desenho com placebo reservado de tamanho razoável:
- 40 eventos, sem exigir histórico de modo e só com t−1 e t−2;
- 25 eventos, pela regra de maioria do estudo anterior com a completude principal.

**3. O matching melhorou o balanceamento institucional?** Em parte, mas não o suficiente.

| Covariável | SMD antes | SMD depois |
|---|---|---|
| log de compras | −1,11 | −0,33 |
| log de itens | −1,27 | −0,22 |
| valor médio | −1,20 | 0,15 |
| SRP | 0,62 | 0,15 |

Ainda assim, 14 covariáveis M0 ficam com |SMD| ≥ 0,10; a pior é a recorrência de produtos, com 0,82. Com 4 eventos,
essas medidas são frágeis.

**4. Houve melhora nas tendências anteriores não usadas no matching?** Não há como afirmar.
- Placebo reservado t0−2 → t0−1, em M0: −50,9 lp, IC95 [−118,1; 16,2].
- MDE de 80% = 94 lp; poder contra ±5 lp = 5%; TOST p = 0,92, ou seja, não há equivalência.
- As tratadas desviam −17 lp do nível de formação em t0−1, um choque pré-troca.
- Nos outros métodos, o placebo vai de −24 a −51 lp, sempre com IC enorme.

**5. O placebo anterior permanece relevante?** Sim, e o matching não o substitui.
- O placebo do dCDH na S1, +11,7 lp [5,7; 17,6] com 99 eventos, continua sendo o diagnóstico informativo.
- O placebo pareado tem outra população, sem nenhum evento em comum, e é imprecisão pura: compatível tanto com
  ausência de pré-tendência quanto com violações de dezenas de log-pontos.

**6. O efeito estimado de AF mudou?** Não é possível dizer.
- R1 dá +16,2 lp [−53,1; 85,5] com 2 eventos.
- Isso não é comparável ao dCDH (−6,5 lp [−14,9; 2,0]) nem ao E3 (−5,1 [−7,6; −2,6]): populações diferentes e
  nenhuma amostra comum.

**7. Qual é o resultado com peso igual por evento?** +16,2 lp, IC95 [−53,1; 85,5], com 2 eventos e 6 clusters.
- p(t) = 0,57; p(WCR) = 0,54. É descritivo.

**8. Qual é o resultado com peso igual por compra?**
- Por compra (R5): +16,2 lp, igual a R1 porque as duas tratadas têm o mesmo número de compras com índice em t0.
- Por item (R6): +34,5 lp [−23,1; 92,2].

**9. A estimativa depende do histórico de preços usado para parear?**
- No efeito, M1 = M0 (+16,2): nos 2 eventos estimáveis os controles são os mesmos, porque há ≤ 5 candidatas dentro dos
  calipers.
- No placebo, depende: M1 dá −27,6 lp e M0 −50,9 lp.
- A simulação dos testes (efeito verdadeiro zero, troca após choque transitório) mostra que o DiD fica negativo e o
  placebo positivo. Parear em preços não protege contra seleção por choques transitórios.

**10. O resultado muda entre adoção e abandono?** Não é estimável. O único abandono com histórico suficiente ficou fora
do suporte comum (AUC = 1 no PS de AF→A). Não há teste de simetria.

**11. A baixa repetição dos mesmos produtos continua comprometendo o desenho?** Sim.
- Nenhuma das 4 tratadas recompra em t0 um produto de t0−2..t0−1, de modo que C3 (mesmo produto) e C2 (cesta de
  classes pré-fixada) não são estimáveis.
- O Jaccard de produtos pré/pós das tratadas vai de 0 a 0,27, e a distância entre distribuições de classes de 0,86 a
  1,0.

**12. Quantos órgãos efetivos sustentam a estimativa?** 2 CNPJs efetivos no efeito e 4 no desenho.

**13. Os resultados são sensíveis à exclusão de um órgão?** Totalmente.
- O jackknife por CNPJ vai de −0,3 a +35,4 lp.
- Sem os 3 CNPJs dominantes resta 1 evento (+32,7).

**14. A inferência é confiável para a estrutura de dependência observada?** Não.
- Com 2 eventos e 6 clusters, nem a variância CR1 por CNPJ nem o bootstrap selvagem são confiáveis.
- Os dois são condicionais aos pares e não capturam a incerteza do pareamento.
- O PS tem separação quase perfeita (AUC 0,99–1,00) com 8 tratadas e 1 tratada.

**15. Há evidência causal mais convincente do que no estudo anterior?** Não.

## Leitura

- Na S1, com regimes inequívocos e um histórico pré-evento que permita parear e reservar um placebo, quase não existem
  UASGs que mudam de modo e têm preços S1 observados de forma contínua.
- A compra de itens S1 com preço é esporádica, 10% dos trimestres misturam os modos e as trocas inequívocas raramente
  têm um histórico limpo.
- O que o matching consegue construir são comparações entre 2 ou 4 órgãos, com cestas de produtos que mudam quase
  inteiramente entre o pré e o pós.
- **A melhora parcial do balanceamento não é evidência causal.** O matching não resolveu a endogeneidade da escolha do
  modo.
- Continuam válidas as conclusões do estudo anterior: associação condicional de cerca de −5% (E3) que cai pela metade
  dentro de UASG × produto (E7), e estudo de eventos com placebos positivos antes da troca.

**Para um desenho futuro (não executado):** seria preciso pré-registrar uma das opções abaixo e aceitar estimandos mais
fracos:
- um desfecho com mais cobertura, como a cesta P1 ou todos os produtos com referência;
- semestres em vez de trimestres;
- regimes por maioria com sensibilidade aos mistos.

A tabela `tabelas/viabilidade_regras_alternativas.csv` dá a ordem de grandeza: no máximo algumas dezenas de eventos com
placebo.
