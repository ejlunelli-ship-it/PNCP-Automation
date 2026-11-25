# Conclusão — rodada exploratória A × AF na cesta P1 validada automaticamente (S1)

25/11/2026. Números de [`relatorio.md`](relatorio.md) e `tabelas/`.

**Caráter.**
- Esta rodada é **exploratória**. Não é a execução confirmatória do protocolo anterior, que exigia aprovação técnica
  humana; a cesta validada humana continua vazia.
- A população principal é a S1 da validação **automática** de catálogo: 3.065 produtos, dos quais 3.053 entram na
  amostra analítica.
- S1 não equivale a validação documental individual, e os itens S4 não foram usados.
- As especificações, janelas, pesos, referências, inferência e Holm são exatamente os do estudo anterior: o código foi
  reutilizado sem modificação. Nada foi ajustado depois de ver significância.

## Respostas

**1. A maior homogeneidade técnica muda a associação de ~−6%?** Não de forma material.

| Amostra | E3 (lp) | IC95 | % exato | dCDH agregado (lp) | IC95 | p Holm |
|---|---|---|---|---|---|---|
| S1 | −5,08 | [−7,57; −2,59] | −5,0% | −6,46 | [−14,88; 1,95] | 0,40 |
| S1+S2 | −5,26 | | | −6,30 | | |
| P1 | −5,57 | | | −2,18 | | |
| cesta | −5,96 | [−8,39; −3,53] | −5,8% | −4,58 | [−9,15; −0,02] | 0,15 |

- Na S1, a associação condicional (E3) cai cerca de 0,9 lp em relação à cesta, mas os intervalos se sobrepõem quase
  inteiramente.
- O dCDH agregado da S1 não é significativo: p = 0,13, e Holm 0,40 na família principal. A ponto, ele fica mais
  negativo que na cesta.
- Nas 14 referências alternativas (amostra comum), o E3 varia pouco: de −5,34 a −5,04 lp na S1, de −5,75 a −5,50 na P1 e de −6,08 a −5,80 na cesta. Algumas diferenças pareadas contra A1 são estatisticamente distintas (menor p de Holm ≈ 0,015), mas têm menos de 0,3 lp.

**2. Diminui a diferença entre E3 e E7?** Não.
- E7, que compara dentro de UASG × produto, dá −2,16 lp na S1 (IC95 [−4,67; 0,35]), contra −2,86 na cesta.
- A distância E3 − E7 é 2,92 lp na S1, 3,16 na S1+S2, 3,05 na P1 e 3,10 na cesta.
- Cerca de metade da associação continua vindo de *quais* UASGs usam AF para *quais* produtos, e não da mudança de preço
  dentro da mesma relação UASG × produto.

**3. Os placebos pré-troca ainda rejeitam tendências paralelas?** Sim.

| Placebo l = −1 na S1 | lp | IC95 | Observação |
|---|---|---|---|
| Agregado | +11,7 | [5,7; 17,6] | |
| Abandono do AF | +13,6 | [6,3; 20,9] | Holm F = 0,001 |
| Adoção | +9,7 | [0,2; 19,3] | Holm F = 0,09 |

- O mesmo padrão aparece em S1+S2, P1 e cesta.
- No HonestDiD (Δ^RM com M̄ = 0,5), todos os intervalos incluem zero, em todas as amostras. Por exemplo, na S1 o
  intervalo é [−29,4; 11,0].
- A homogeneidade do catálogo **não** resolve a falha de identificação.

**4. As estimativas são sensíveis à composição institucional, à ponderação ou à seleção de produtos?** Sim, sobretudo
no estudo de eventos.

- **Ponderação.** Na S1, o dCDH dá:

  | Ponderação | lp |
  |---|---|
  | por célula (principal) | −6,46 |
  | peso igual por evento | −4,13 |
  | por compra | −1,84 |
  | janela de 12 meses | −6,16 |

- **Seleção de produtos.** A P1 contém a S1 e acrescenta 1.057 produtos fora dela (107 da S2 e 950 inconclusivos), mas dá −2,18 lp. Com os mesmos
  eventos da S1, a P1 dá −3,16. Ou seja, a composição de produtos dentro dos mesmos eventos move a estimativa em cerca
  de 3 lp, e os intervalos têm cerca de ±8 lp.
- **Decomposição cesta → S1** (dCDH agregado, −4,58 → −6,46):

  | Componente | lp |
  |---|---|
  | redução de eventos (cesta com os eventos da S1) | −0,73 |
  | seleção de produtos dentro dos mesmos eventos | −1,15 |

- **Eventos e órgãos.**
  - Os eventos usados em l = 1 caem de 145 para 99. São só cerca de 15 CNPJs efetivos.
  - O maior CNPJ tem 20,6% do peso do dCDH e 17,2% da variação identificadora do E3; sem ele, o E3 da S1 vai a −4,46.
  - A sobreposição de produtos antes e depois da troca é de só 3,5%: as comparações pré/pós continuam sendo, em grande
    parte, entre produtos diferentes.
- **Composição da S1.** É diagnóstico e não alterou a classificação.
  - A validação automática seleciona por tipo de produto: retém medicamentos (classe 6505, 24% da S1), materiais de
    escritório e alimentos, e quase exclui peças e itens dependentes de compatibilidade (1 contra 412 entre os
    inconclusivos).
  - A frequência, a cobertura anual e a fração de compras AF não mudam: 35,8% na S1 e 34,7% nos inconclusivos.

## Leitura

A restrição a produtos com catálogo homogêneo **não altera** o quadro do estudo anterior:
- persiste uma associação condicional de cerca de −5% entre AF e preço relativo, estável entre referências;
- ela se reduz à metade dentro de UASG × produto;
- o estudo de eventos dá estimativas imprecisas, sensíveis à ponderação e à composição, não significativas após Holm,
  com placebos pré-troca fortemente positivos.

**Não há base para afirmar efeito causal do AF.** O problema central continua sendo a seleção das trocas de modo: há
choques de preço antes do abandono do AF. A heterogeneidade técnica dos produtos não era o problema.

## Pendências e limitações

- **P1:** a robustez (14 referências e R01–R15) foi interrompida uma vez pelo sistema por falta de memória e reexecutada depois, com autorização. Nas 14 referências, o E3 da P1 varia de −5,75 a −5,50 lp.
- **HonestDiD:** na primeira passada não rodou nas novas pastas, porque o script R não estava na pasta de saídas. Foi
  reexecutado com o script original, de hash conferido; ver `amostras/*/log_honestdid.txt`.
- **Equivalência:** a de catálogo (S1) não comprova a conformidade de cada contratação.
- **Endogeneidade:** a escolha do modo continua endógena; a validação técnica não a resolve.
