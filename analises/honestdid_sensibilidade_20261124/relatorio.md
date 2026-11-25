# Sensibilidade HonestDiD (Rambachan e Roth, 2023) do estudo de eventos A × AF: relatório (24/11/2026)

**Exploratório.** O protocolo (`protocolo.md`) foi escrito antes de estimar; o hash está em `registro_execucao.json`.
Nenhuma especificação, grade ou parâmetro foi escolhido pelo valor-p. Os 56 eventos posteriores a 2025-10, reservados para
a validação, não foram usados. O `pncp.db` não foi lido, e nada anterior foi alterado.

**Pergunta.** Que violações das tendências paralelas são compatíveis com os dados, e como elas alargam o intervalo do
efeito do AF no preço homologado?

**Execução.** Pacote oficial `HonestDiD` 0.2.8, CRAN, em R 4.6.2. A matriz de covariância é conjunta e agrupada por
órgão; nenhum erro-padrão isolado foi usado como substituto.

## Resumo dos resultados verificados

1. **Reprodução.**
   - O M0 sai exato: −1,91 lp, IC95 [−5,67; 1,93], p = 0,32, 152 eventos e 70 órgãos.
   - O perfil de 23/11 também: os coeficientes, os EP e os p do bootstrap.
2. **Coeficientes dinâmicos** (base no trimestre −1):

   | Trimestre | Coeficiente (lp) | EP | Eventos | Órgãos |
   |---|---:|---:|---:|---:|
   | −2 (pré) | +0,52 | 3,59 | 110 | 57 |
   | 0 | −3,14 | 3,21 | 136 | 68 |
   | +1 | −3,12 | 2,88 | 120 | 59 |

   - A matriz CR1 conjunta por órgão é semidefinida positiva, com nº de condição 5,3 e correlações ≈ 0,5.
   - Jackknife e bootstrap por órgão dão EP de 1% a 2% maiores.
3. **Os coeficientes dinâmicos não medem o mesmo que o M0.** Nos mesmos 87 eventos balanceados:
   - o M0 dá −1,33 lp;
   - o análogo em trimestres dá −3,22 lp.

   A diferença vem da agregação (média por compra na meia janela × trimestres de peso igual) e dos controles de cada
   trimestre.
4. **Nenhum conjunto robusto exclui zero, em nenhuma restrição, parâmetro ou especificação.** Por isso não há ponto de
   quebra a relatar: as 73 combinações incluem zero já no menor valor da grade. Na especificação principal:

   | Restrição | (a) 1º trimestre | (b) média |
   |---|---|---|
   | IC original (normal) | [−9,4; 3,2] | [−8,4; 2,1] |
   | M̄ = 1 | [−12,4; 7,1] | [−14,3; 9,5] |
   | M̄ = 2 | [−17,4; 13,3] | [−22,3; 19,1] |
   | Δ^SD com M = 0 a 3 lp | de [−14,2; 9,0] a [−15,5; 10,3] | de [−16,6; 11,9] a [−20,3; 15,6] |

5. **O pré-teste quase não tem poder.**
   - Com um único pré-período de EP 3,6 lp, só uma tendência linear de cerca de 10 lp por trimestre seria detectada com
     80% de probabilidade.
   - Essa tendência daria um viés de 10 lp em (a) e de 15 lp em (b).
   - A pré-tendência não significativa (p = 0,88) não comprova tendências paralelas.
6. **Robustez do resultado qualitativo.** Ele vale:
   - com retirada de um órgão por vez: 68 de 68 conjuntos incluem zero;
   - com pesos iguais, painel balanceado e matrizes jackknife e bootstrap;
   - nas direções separadas;
   - no modelo filtrado: (b) original [−9,7; 0,1] e M̄ = 1 [−19,3; 4,5].
7. **Janela de 12 meses.** Ela traz mais pré-períodos, mas esses pré-coeficientes oscilam (+6,6; −8,0; −1,2 lp, com 14 a 46
   eventos):
   - com 2 ou 3 pré-períodos, o conjunto identificado de Δ^SD fica vazio para M ≤ 3;
   - os conjuntos de Δ^RM ficam de 3 a 7 vezes mais largos.

**Leitura.** O HonestDiD **não traz evidência adicional a favor do AF, só amplia a incerteza**. O resultado principal já
não era significativo e continua não significativo sob qualquer violação admitida. O que depende das tendências
paralelas é o tamanho das faixas excluídas, não a conclusão.
- **Com tendências paralelas exatas no pós:** os dados excluem reduções maiores que ~9 lp e aumentos maiores que ~3 lp.
- **Com violações do tamanho da pré-tendência:** passam a ser compatíveis reduções de até 12–14 lp e aumentos de até 7–10
  lp.

## 1. O que existia nas análises anteriores

**Estimador** (`testes_desenho_causal_20261123/`, reproduzido por `robustez_dispersao_20261123/motor_robustez.py`):
- estudo de eventos empilhado na UASG que troca de modo;
- controles limpos: mesma esfera, estáveis no modo de partida, sem evento próprio a menos de 6 meses, pelo menos 5;
- índice = média por compra do log P menos a referência A (produto × trimestre, sem a própria UASG);
- pesos de precisão;
- inferência agrupada por órgão (CNPJ), com bootstrap selvagem restrito.

**Coeficientes dinâmicos:** o perfil por trimestre de 23/11, com base −1. Só há EP e p por coeficiente.
- **Não havia matriz de covariância conjunta.**
- O teste conjunto pré de 23/11 usava pesos iguais e só eventos com todos os trimestres. Na janela de 12 meses, isso deu
  9 eventos.
- A "sensibilidade Rambachan–Roth" de 23/11 usava EP isolados. Ela **não é usada aqui**.

**Demais pastas** (robustez, investigação, composição): o mesmo motor, também sem matriz conjunta.

**Construção nesta análise:**
- os coeficientes por trimestre foram recalculados com uma réplica do bloco `bins` do motor, igual ao motor em 1.060
  valores (diferença máxima de 0);
- a matriz conjunta é CR1 por órgão, com jackknife e bootstrap de pares por órgão (B = 9.999) como verificação.

## 2. Resultados originais reproduzidos

| Item | Obtido | Referência (23/11) | Diferença |
|---|---:|---:|---:|
| M0 coef (lp) | −1,908 | −1,910 | 0,001850 |
| M0 IC95 WCR inf | −5,671 | −5,670 | −0,001090 |
| M0 IC95 WCR sup | 1,933 | 1,930 | 0,002548 |
| M0 p WCR | 0,321 | 0,320 | 0,001132 |
| M0 eventos | 152 | 152 | 0 |
| M0 órgãos | 70 | 70 | 0 |
| M1 coef (lp) | −3,758 | −3,760 | 0,002432 |
| janela 12 coef (lp) | −1,969 | −1,969 | 0,000000 |
| janela 12 eventos | 78 | 78 | 0 |
| perfil 23/11 b-2 coef (lp) | 0,525 | 0,525 | 0,000000 |
| perfil 23/11 b-2 EP (lp) | 3,589 | 3,589 | 0,000000 |
| perfil 23/11 b-2 p WCR | 0,885 | 0,885 | 0,000000 |
| perfil 23/11 b-2 eventos | 110 | 110 | 0 |
| perfil 23/11 b0 coef (lp) | −3,137 | −3,137 | 0,000000 |
| perfil 23/11 b0 EP (lp) | 3,207 | 3,207 | −0,000000 |
| perfil 23/11 b0 p WCR | 0,329 | 0,329 | 0,000000 |
| perfil 23/11 b0 eventos | 136 | 136 | 0 |
| perfil 23/11 b1 coef (lp) | −3,124 | −3,124 | 0,000000 |
| perfil 23/11 b1 EP (lp) | 2,878 | 2,878 | 0,000000 |
| perfil 23/11 b1 p WCR | 0,281 | 0,281 | 0,000000 |
| perfil 23/11 b1 eventos | 120 | 120 | 0 |
| janela 12 b-4 coef (lp) | 6,569 | 6,569 | 0,000000 |
| janela 12 b-4 eventos | 14 | 14 | 0 |
| janela 12 b-3 coef (lp) | −8,034 | −8,034 | −0,000000 |
| janela 12 b-3 eventos | 25 | 25 | 0 |
| janela 12 b-2 coef (lp) | −1,215 | −1,215 | 0,000000 |
| janela 12 b-2 eventos | 46 | 46 | 0 |
| janela 12 b0 coef (lp) | −4,847 | −4,847 | 0,000000 |
| janela 12 b0 eventos | 69 | 69 | 0 |
| janela 12 b1 coef (lp) | −7,687 | −7,687 | 0,000000 |
| janela 12 b1 eventos | 56 | 56 | 0 |
| janela 12 b2 coef (lp) | −5,987 | −5,987 | 0,000000 |
| janela 12 b2 eventos | 60 | 60 | 0 |
| janela 12 b3 coef (lp) | −4,668 | −4,668 | −0,000000 |
| janela 12 b3 eventos | 59 | 59 | 0 |

## 3. Coeficientes dinâmicos

**Vetor principal:** (β₋₂ | β₀, β₊₁), com referência no trimestre −1. Ou seja, 1 pré-período e 2 pós-períodos.
- **Sinal:** efeito do AF; as trocas AF → A entram com o sinal invertido no vetor inteiro.
- **Pesos:** os de precisão do M0, os mesmos em todos os trimestres.
- **Eventos por trimestre:** cada trimestre usa os eventos em que a tratada tem compra nele e no trimestre −1, com pelo
  menos 5 controles com dado.
- **Fora do perfil:** 11 dos 152 eventos do M0 não têm compra da tratada no trimestre −1 e não entram.

| Espec. | Trim. | coef (lp) | EP | IC95 normal | p WCR | eventos (A→AF + AF→A) | órgãos (efet.) | UASGs trat. / ctrl. | compras / itens trat. (q + ref.) | baixa precisão |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---|
| principal | −2 | 0,52 | 3,59 | [−6,51; 7,56] | 0,885 | 110 (57 + 53) | 57 (23,9) | 99 / 1.879 | 1.370 / 22.216 | não |
| principal | 0 | −3,14 | 3,21 | [−9,42; 3,15] | 0,329 | 136 (69 + 67) | 68 (24,5) | 124 / 2.012 | 1.864 / 28.340 | não |
| principal | 1 | −3,12 | 2,88 | [−8,77; 2,52] | 0,281 | 120 (59 + 61) | 59 (23,1) | 107 / 1.925 | 1.687 / 26.533 | não |
| balanceado | −2 | −0,05 | 3,88 | [−7,66; 7,55] | 0,990 | 87 (44 + 43) | 48 (22,6) | 78 / 1.822 | 1.246 / 18.606 | não |
| balanceado | 0 | −3,77 | 3,95 | [−11,51; 3,98] | 0,349 | 87 (44 + 43) | 48 (22,6) | 78 / 1.938 | 1.284 / 20.543 | não |
| balanceado | 1 | −2,73 | 3,31 | [−9,22; 3,76] | 0,413 | 87 (44 + 43) | 48 (22,6) | 78 / 1.866 | 1.226 / 21.194 | não |
| pesos iguais | −2 | 2,61 | 4,05 | [−5,33; 10,56] | 0,527 | 110 (57 + 53) | 57 (18,6) | 99 / 1.879 | 1.370 / 22.216 | não |
| pesos iguais | 0 | −4,74 | 3,82 | [−12,23; 2,75] | 0,214 | 136 (69 + 67) | 68 (21,5) | 124 / 2.012 | 1.864 / 28.340 | não |
| pesos iguais | 1 | −1,81 | 3,41 | [−8,50; 4,88] | 0,604 | 120 (59 + 61) | 59 (21,3) | 107 / 1.925 | 1.687 / 26.533 | não |
| filtrado (G ≤ 0,80) | −2 | −1,92 | 3,40 | [−8,59; 4,74] | 0,578 | 107 (55 + 52) | 55 (22,7) | 95 / 1.810 | 1.283 / 20.281 | não |
| filtrado (G ≤ 0,80) | 0 | −4,15 | 3,18 | [−10,37; 2,07] | 0,188 | 133 (65 + 68) | 63 (22,7) | 120 / 1.957 | 1.776 / 25.706 | não |
| filtrado (G ≤ 0,80) | 1 | −5,46 | 2,63 | [−10,60; −0,31] | 0,044 | 125 (61 + 64) | 58 (21,7) | 110 / 1.856 | 1.632 / 23.848 | não |

Especificações (contagens na janela inteira):

| Espec. | Pré / pós | Trimestres | eventos (A→AF + AF→A) | órgãos (efet.) | UASGs trat. | compras / itens trat. (janela) | maior peso de órgão | amostra |
|---|---:|---|---:|---:|---:|---:|---:|---|
| principal | 1 / 2 | −2, 0, 1 | 141 (71 + 70) | 68 (24,4) | 126 | 3.522 / 52.866 | 9,7% | 152 eventos do M0 |
| principal, matriz jackknife | 1 / 2 | −2, 0, 1 | 141 (71 + 70) | 68 (24,4) | 126 | 3.522 / 52.866 | 9,7% | 152 eventos do M0 |
| principal, matriz bootstrap | 1 / 2 | −2, 0, 1 | 141 (71 + 70) | 68 (24,4) | 126 | 3.522 / 52.866 | 9,7% | 152 eventos do M0 |
| só A → AF | 1 / 2 | −2, 0, 1 | 71 (71 + 0) | 47 (25,2) | 71 | 1.361 / 23.936 | 9,5% | eventos A → AF do M0 |
| só AF → A (sinal do AF) | 1 / 2 | −2, 0, 1 | 70 (0 + 70) | 40 (16,7) | 70 | 2.161 / 28.930 | 11,4% | eventos AF → A do M0 |
| pesos iguais | 1 / 2 | −2, 0, 1 | 141 (71 + 70) | 68 (21,3) | 126 | 3.522 / 52.866 | 17,0% | 152 eventos do M0 |
| balanceado | 1 / 2 | −2, 0, 1 | 87 (44 + 43) | 48 (22,6) | 78 | 2.588 / 40.189 | 9,5% | subconjunto do M0 |
| filtrado (G ≤ 0,80) | 1 / 2 | −2, 0, 1 | 141 (70 + 71) | 65 (22,9) | 124 | 3.386 / 47.651 | 10,2% | 150 eventos do M1 |
| antecipação, janela 12, ref. −2 | 2 / 3 | −4, −3, −1, 0, 1 | 51 (27 + 24) | 35 (17,0) | 51 | 1.362 / 29.244 | 16,1% | 78 eventos da janela de 12 |
| janela 12: 1 pré, 2 pós | 1 / 2 | −2, 0, 1 | 71 (38 + 33) | 45 (18,1) | 71 | 2.253 / 36.664 | 12,7% | 78 eventos da janela de 12 |
| janela 12: 1 pré, 4 pós | 1 / 4 | −2, 0, 1, 2, 3 | 71 (38 + 33) | 45 (18,1) | 71 | 2.253 / 36.664 | 12,7% | 78 eventos da janela de 12 |
| janela 12: 2 pré, 2 pós | 2 / 2 | −3, −2, 0, 1 | 71 (38 + 33) | 45 (18,1) | 71 | 2.253 / 36.664 | 12,7% | 78 eventos da janela de 12 |
| janela 12: 2 pré, 4 pós | 2 / 4 | −3, −2, 0, 1, 2, 3 | 71 (38 + 33) | 45 (18,1) | 71 | 2.253 / 36.664 | 12,7% | 78 eventos da janela de 12 |
| janela 12: 3 pré, 2 pós | 3 / 2 | −4, −3, −2, 0, 1 | 71 (38 + 33) | 45 (18,1) | 71 | 2.253 / 36.664 | 12,7% | 78 eventos da janela de 12 |
| janela 12: 3 pré, 4 pós | 3 / 4 | −4, −3, −2, 0, 1, 2, 3 | 71 (38 + 33) | 45 (18,1) | 71 | 2.253 / 36.664 | 12,7% | 78 eventos da janela de 12 |

**Diferença de estimando.** O perfil não reproduz o M0.

| Medida | Eventos | Valor (lp) |
|---|---:|---:|
| M0: meia janela pós − pré, todos os eventos do M0 | 152 | −1,91 |
| M0 nos eventos do perfil (tratada com compra no trimestre −1) | 141 | −1,96 |
| M0 nos eventos com trimestres 0 e +1 | 115 | −1,87 |
| M0 nos eventos balanceados (−2, 0, +1) | 87 | −1,33 |
| parâmetro (b): (β0 + β+1)/2, cada trimestre com seus eventos | 141 | −3,13 |
| média por evento de (q0 + q+1)/2, eventos com os dois | 115 | −3,20 |
| balanceados: (q0 + q+1)/2 − q−2/2 (análogo do M0 em trimestres) | 87 | −3,22 |

- **Mesmos 87 eventos balanceados:**
  - o M0 (meia janela pós contra pré, média por compra) dá −1,33 lp;
  - a combinação dos trimestres que imita o M0, (β₀ + β₊₁)/2 − β₋₂/2, dá −3,22 lp;
  - a diferença de cerca de 1,9 lp vem da agregação, e não da amostra. O M0 pondera as compras dentro de cada meia janela;
    o perfil dá peso igual a cada trimestre e usa, em cada trimestre, só os controles com compra nele e no trimestre −1.
- **Amostras:** a amostra do perfil (141 eventos) tem M0 de −1,96, perto do total.
- **Consequência:** os parâmetros (a) e (b) do HonestDiD são efeitos dinâmicos contra o trimestre −1. Não são o −1,91 do
  M0, e a comparação com −1,91 é só uma referência.

## 4. Matrizes de covariância e verificações

Matriz CR1 conjunta da especificação principal:

| CR1 (lp²) | trim. −2 | trim. 0 | trim. 1 |
|---|---:|---:|---:|
| trim. −2 | 12,88 | 5,83 | 5,02 |
| trim. 0 | 5,83 | 10,28 | 5,10 |
| trim. 1 | 5,02 | 5,10 | 8,29 |

Verificações:

| Espec. | Estimador | EP por coeficiente (lp) | razão EP / CR1 | correlações | nº de condição | semidefinida positiva | réplicas |
|---|---|---|---|---|---:|---|---:|
| principal | CR1 | 3,589; 3,207; 2,878 | 1,000; 1,000; 1,000 | 0,506; 0,486; 0,553 | 5,3 | sim | 68 |
| principal | jackknife | 3,665; 3,273; 2,943 | 1,021; 1,021; 1,022 | 0,520; 0,501; 0,563 | 5,4 | sim | 68 |
| principal | bootstrap | 3,667; 3,244; 2,942 | 1,022; 1,012; 1,022 | 0,492; 0,469; 0,544 | 5,1 | sim | 9.999 |
| balanceado | CR1 | 3,879; 3,951; 3,309 | 1,000; 1,000; 1,000 | 0,431; 0,419; 0,516 | 4,4 | sim | 48 |
| balanceado | jackknife | 3,956; 4,029; 3,361 | 1,020; 1,020; 1,016 | 0,451; 0,427; 0,523 | 4,5 | sim | 48 |
| balanceado | bootstrap | 3,942; 3,969; 3,373 | 1,016; 1,004; 1,019 | 0,421; 0,411; 0,517 | 4,3 | sim | 9.999 |
| filtrado (G ≤ 0,80) | CR1 | 3,400; 3,175; 2,626 | 1,000; 1,000; 1,000 | 0,609; 0,578; 0,493 | 5,8 | sim | 65 |
| filtrado (G ≤ 0,80) | jackknife | 3,491; 3,206; 2,679 | 1,027; 1,010; 1,020 | 0,606; 0,589; 0,496 | 5,9 | sim | 65 |
| filtrado (G ≤ 0,80) | bootstrap | 3,429; 3,220; 2,640 | 1,009; 1,014; 1,006 | 0,603; 0,567; 0,479 | 5,7 | sim | 9.999 |
| só A → AF | CR1 | 5,316; 4,188; 3,931 | 1,000; 1,000; 1,000 | 0,409; 0,167; 0,257 | 3,1 | sim | 47 |
| só A → AF | jackknife | 5,428; 4,201; 3,959 | 1,021; 1,003; 1,007 | 0,421; 0,170; 0,248 | 3,2 | sim | 47 |
| só A → AF | bootstrap | 5,265; 4,254; 3,942 | 0,990; 1,016; 1,003 | 0,406; 0,165; 0,265 | 3,1 | sim | 9.999 |
| só AF → A (sinal do AF) | CR1 | 5,309; 4,927; 4,299 | 1,000; 1,000; 1,000 | 0,619; 0,701; 0,764 | 12,5 | sim | 40 |
| só AF → A (sinal do AF) | jackknife | 5,505; 5,090; 4,411 | 1,037; 1,033; 1,026 | 0,643; 0,723; 0,777 | 13,6 | sim | 40 |
| só AF → A (sinal do AF) | bootstrap | 5,434; 5,030; 4,456 | 1,024; 1,021; 1,037 | 0,605; 0,692; 0,755 | 11,8 | sim | 9.999 |
| janela 12: 3 pré, 4 pós | CR1 | 7,994; 9,265; 6,757; 4,166; 5,771; 5,994; 5,522 | 1,000; 1,000; 1,000; 1,000; 1,000; 1,000; 1,000 | 0,657; 0,596; 0,481; 0,395; 0,468; 0,525; 0,520; 0,252; 0,436; 0,241; 0,458; 0,388; 0,320; 0,663; 0,384; 0,543; 0,658; 0,470; 0,403; 0,585; 0,326 | 33,7 | sim | 45 |
| janela 12: 3 pré, 4 pós | jackknife | 8,352; 9,758; 6,903; 4,187; 5,851; 6,106; 5,706 | 1,045; 1,053; 1,021; 1,005; 1,014; 1,019; 1,033 | 0,678; 0,622; 0,484; 0,411; 0,479; 0,517; 0,526; 0,243; 0,453; 0,234; 0,445; 0,398; 0,339; 0,662; 0,388; 0,533; 0,662; 0,452; 0,385; 0,589; 0,295 | 36,5 | sim | 45 |
| janela 12: 3 pré, 4 pós | bootstrap | 8,708; 9,288; 6,819; 4,251; 5,901; 6,054; 5,644 | 1,089; 1,003; 1,009; 1,020; 1,023; 1,010; 1,022 | 0,627; 0,538; 0,414; 0,343; 0,423; 0,453; 0,510; 0,252; 0,418; 0,243; 0,440; 0,367; 0,292; 0,650; 0,367; 0,554; 0,645; 0,491; 0,414; 0,584; 0,349 | 31,2 | sim | 9.999 |
| antecipação, janela 12, ref. −2 | CR1 | 8,239; 9,398; 6,757; 6,414; 8,767 | 1,000; 1,000; 1,000; 1,000; 1,000 | 0,341; 0,603; 0,439; 0,139; 0,560; 0,432; 0,660; 0,705; 0,476; 0,621 | 21,0 | sim | 35 |
| antecipação, janela 12, ref. −2 | jackknife | 8,790; 9,862; 6,880; 6,471; 8,813 | 1,067; 1,049; 1,018; 1,009; 1,005 | 0,337; 0,626; 0,452; 0,142; 0,540; 0,388; 0,660; 0,704; 0,465; 0,597 | 21,9 | sim | 35 |
| antecipação, janela 12, ref. −2 | bootstrap | 8,260; 9,498; 6,813; 6,531; 8,900 | 1,003; 1,011; 1,008; 1,018; 1,015 | 0,361; 0,565; 0,415; 0,148; 0,571; 0,453; 0,659; 0,705; 0,486; 0,633 | 20,7 | sim | 9.999 |

- **CR1 conjunta:** semidefinida positiva em todas as especificações.
  - O nº de condição é de 4 a 6 na janela de 6 meses e de 21 a 34 na de 12 meses, cujos trimestres −4 e −3 têm de 13 a 27
    eventos.
  - As correlações entre coeficientes ficam em torno de 0,5, porque todos usam o mesmo trimestre de referência.
- **Jackknife e bootstrap por órgão** (9.999 réplicas): EP de 0% a 9% maiores que os do CR1, com as mesmas correlações.
- **HonestDiD com cada matriz:** os resultados quase não mudam (seção 8.1).
- **Retirando um órgão por vez:** os EP variam no máximo 10% (seção 8.4).

## 5. Pré-tendências e poder do pré-teste

| Espec. | pré-coeficientes (lp) | Wald (gl) | p χ² | p F(gl, G−1) | órgãos pré | γ com 50% de poder | γ com 80% | viés em (a) com 80% | viés em (b) com 80% |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| principal | 0,525 | 0,02 (1) | 0,884 | 0,884 | 57 | 7,03 | 10,05 | 10,05 | 15,08 |
| só A → AF | 2,726 | 0,26 (1) | 0,608 | 0,611 | 41 | 10,42 | 14,89 | 14,89 | 22,34 |
| só AF → A (sinal do AF) | −1,447 | 0,07 (1) | 0,785 | 0,787 | 31 | 10,40 | 14,87 | 14,87 | 22,31 |
| pesos iguais | 2,613 | 0,42 (1) | 0,519 | 0,522 | 57 | 7,95 | 11,36 | 11,36 | 17,04 |
| balanceado | −0,053 | 0,00 (1) | 0,989 | 0,989 | 48 | 7,60 | 10,87 | 10,87 | 16,30 |
| filtrado (G ≤ 0,80) | −1,923 | 0,32 (1) | 0,572 | 0,574 | 55 | 6,66 | 9,52 | 9,52 | 14,29 |
| antecipação, janela 12, ref. −2 | −4,644; −9,528 | 1,08 (2) | 0,582 | 0,591 | 20 | 9,12 | 12,72 | 25,44 | 31,80 |
| janela 12: 1 pré, 2 pós | −1,215 | 0,03 (1) | 0,857 | 0,859 | 32 | 13,24 | 18,93 | 18,93 | 28,40 |
| janela 12: 1 pré, 4 pós | −1,215 | 0,03 (1) | 0,857 | 0,859 | 32 | 13,24 | 18,93 | 18,93 | 47,33 |
| janela 12: 2 pré, 2 pós | −8,034; −1,215 | 0,85 (2) | 0,653 | 0,656 | 33 | 10,13 | 14,12 | 14,12 | 21,18 |
| janela 12: 2 pré, 4 pós | −8,034; −1,215 | 0,85 (2) | 0,653 | 0,656 | 33 | 10,13 | 14,12 | 14,12 | 35,29 |
| janela 12: 3 pré, 2 pós | 6,569; −8,034; −1,215 | 4,36 (3) | 0,225 | 0,245 | 35 | 6,19 | 8,52 | 8,52 | 12,78 |
| janela 12: 3 pré, 4 pós | 6,569; −8,034; −1,215 | 4,36 (3) | 0,225 | 0,245 | 35 | 6,19 | 8,52 | 8,52 | 21,30 |

- **Pré-tendências:** nenhuma é significativa.
  - Na especificação principal, β₋₂ = +0,52 lp (p = 0,88).
  - Na janela de 12 meses, o Wald conjunto dos 3 pré-coeficientes dá p = 0,23.
- **Poder:** muito baixo.
  - O γ é a inclinação linear por trimestre que o pré-teste a 5% detecta com 50% ou 80% de probabilidade.
  - Na especificação principal, γ = 7 e 10 lp por trimestre.
  - Uma tendência linear que o pré-teste não pegaria em 20% das vezes deslocaria (a) em 10 lp e (b) em 15 lp, de 3 a 5
    vezes os coeficientes estimados.
  - Nas direções separadas e na janela de 12 meses, o poder é ainda menor.
- **Conclusão:** a ausência de pré-tendência significativa não comprova tendências paralelas. Os dados só não detectam
  violações menores que ~10 lp por trimestre.

## 6. HonestDiD na especificação principal

**Restrições e métodos:**
- **Δ^RM(M̄):** a violação pós entre trimestres consecutivos é no máximo M̄ vezes a maior violação pré. Com 1
  pré-período, a violação pré é |β₋₂|. Método C-LF.
- **Δ^SD(M):** a inclinação da tendência diferencial muda no máximo M lp por trimestre. Método FLCI.

**Conjunto identificado:** o conjunto de efeitos compatível com β = β̂, sem erro amostral. É calculado pelas funções
internas do pacote e confere com a programação linear em Python.

### Parâmetro (a): 1º trimestre pós

| Restrição | Valor | IC robusto 95% | inclui 0 | maior redução compatível | maior aumento compatível | conjunto identificado (β = β̂) | largura / original |
|---|---:|---|---|---:|---:|---|---:|
| original (normal) | — | [−9,42; 3,15] | sim | 9,42 | 3,15 | −3,14 (estimativa) | 1,00 |
| Δ^RM, M̄ | 0,00 | [−9,31; 3,02] | sim | 9,31 | 3,02 | [−3,14; −3,14] | 0,98 |
| Δ^RM, M̄ | 0,50 | [−10,46; 4,56] | sim | 10,46 | 4,56 | [−3,40; −2,87] | 1,20 |
| Δ^RM, M̄ | 1,00 | [−12,39; 7,13] | sim | 12,39 | 7,13 | [−3,66; −2,61] | 1,55 |
| Δ^RM, M̄ | 1,50 | [−14,83; 10,21] | sim | 14,83 | 10,21 | [−3,92; −2,35] | 1,99 |
| Δ^RM, M̄ | 2,00 | [−17,40; 13,29] | sim | 17,40 | 13,29 | [−4,19; −2,09] | 2,44 |
| Δ^RM, M̄ | 3,00 | [−22,66; 19,58] | sim | 22,66 | 19,58 | [−4,71; −1,56] | 3,36 |
| Δ^SD, M (lp) | 0,00 | [−14,19; 8,97] | sim | 14,19 | 8,97 | [−2,61; −2,61] | 1,84 |
| Δ^SD, M (lp) | 0,25 | [−14,19; 8,97] | sim | 14,19 | 8,97 | [−2,86; −2,36] | 1,84 |
| Δ^SD, M (lp) | 0,50 | [−14,22; 9,00] | sim | 14,22 | 9,00 | [−3,11; −2,11] | 1,85 |
| Δ^SD, M (lp) | 1,00 | [−14,34; 9,12] | sim | 14,34 | 9,12 | [−3,61; −1,61] | 1,87 |
| Δ^SD, M (lp) | 1,50 | [−14,54; 9,32] | sim | 14,54 | 9,32 | [−4,11; −1,11] | 1,90 |
| Δ^SD, M (lp) | 2,00 | [−14,80; 9,58] | sim | 14,80 | 9,58 | [−4,61; −0,61] | 1,94 |
| Δ^SD, M (lp) | 3,00 | [−15,52; 10,29] | sim | 15,52 | 10,29 | [−5,61; 0,39] | 2,05 |

### Parâmetro (b): média dos dois trimestres pós

| Restrição | Valor | IC robusto 95% | inclui 0 | maior redução compatível | maior aumento compatível | conjunto identificado (β = β̂) | largura / original |
|---|---:|---|---|---:|---:|---|---:|
| original (normal) | — | [−8,39; 2,13] | sim | 8,39 | 2,13 | −3,13 (estimativa) | 1,00 |
| Δ^RM, M̄ | 0,00 | [−8,32; 2,09] | sim | 8,32 | 2,09 | [−3,13; −3,13] | 0,99 |
| Δ^RM, M̄ | 0,50 | [−10,68; 4,99] | sim | 10,68 | 4,99 | [−3,52; −2,74] | 1,49 |
| Δ^RM, M̄ | 1,00 | [−14,34; 9,50] | sim | 14,34 | 9,50 | [−3,92; −2,34] | 2,27 |
| Δ^RM, M̄ | 1,50 | [−18,20; 14,23] | sim | 18,20 | 14,23 | [−4,31; −1,95] | 3,08 |
| Δ^RM, M̄ | 2,00 | [−22,28; 19,06] | sim | 22,28 | 19,06 | [−4,71; −1,56] | 3,93 |
| Δ^RM, M̄ | 3,00 | [−30,34; 28,62] | sim | 30,34 | 28,62 | [−5,49; −0,77] | 5,61 |
| Δ^SD, M (lp) | 0,00 | [−16,55; 11,87] | sim | 16,55 | 11,87 | [−2,34; −2,34] | 2,70 |
| Δ^SD, M (lp) | 0,25 | [−16,58; 11,89] | sim | 16,58 | 11,89 | [−2,84; −1,84] | 2,71 |
| Δ^SD, M (lp) | 0,50 | [−16,67; 11,98] | sim | 16,67 | 11,98 | [−3,34; −1,34] | 2,73 |
| Δ^SD, M (lp) | 1,00 | [−17,06; 12,37] | sim | 17,06 | 12,37 | [−4,34; −0,34] | 2,80 |
| Δ^SD, M (lp) | 1,50 | [−17,66; 12,97] | sim | 17,66 | 12,97 | [−5,34; 0,66] | 2,91 |
| Δ^SD, M (lp) | 2,00 | [−18,44; 13,76] | sim | 18,44 | 13,76 | [−6,34; 1,66] | 3,06 |
| Δ^SD, M (lp) | 3,00 | [−20,27; 15,59] | sim | 20,27 | 15,59 | [−8,34; 3,66] | 3,41 |

**Magnitudes relativas, Δ^RM:**
- Em M̄ = 0 (sem violação pós), o IC fica igual ao original, com a pequena diferença do método C-LF.
- O IC se alarga quase linearmente com M̄, porque a violação pré de referência (|β₋₂| = 0,5 lp) é estimada com EP de 3,6
  lp. O procedimento considera violações pré tão grandes quanto as compatíveis com esse erro.
- Os conjuntos identificados (barras dos gráficos) são estreitos, de ±0,5 lp × M̄ em (a): com β = β̂, a pré-tendência
  é quase nula.
- Quase toda a largura vem da incerteza amostral sobre a própria pré-tendência.

**Suavidade, Δ^SD:**
- Já em M = 0 (tendência diferencial exatamente linear), o IC é largo: [−14,2; 9,0] em (a). A extrapolação linear a partir
  de um único pré-coeficiente impreciso propaga o erro dele para o pós.
- Aumentar M até 3 lp acrescenta pouco.
- O conjunto identificado em M = 0 é a estimativa corrigida pela tendência linear: −2,61 em (a) e −2,34 em (b).

**Faixas compatíveis:**
- **Reduções:** em (a), até 9,3 lp com M̄ = 0, 12,4 com M̄ = 1 e 17,4 com M̄ = 2. Em (b), até 8,3, 14,3 e 22,3. Com Δ^SD,
  até 14–16 lp em (a) e 17–20 lp em (b).
- **Aumentos:** em (a), até 3,0, 7,1 e 13,3 lp. Em (b), até 2,1, 9,5 e 19,1 lp. Com Δ^SD, até 9–10 lp em (a) e 12–16 lp em
  (b).

## 7. Direções da troca: (c), (d) e (e)

Coeficientes por direção:

| Espec. | Trim. | coef (lp) | EP | IC95 normal | p WCR | eventos (A→AF + AF→A) | órgãos (efet.) | UASGs trat. / ctrl. | compras / itens trat. (q + ref.) | baixa precisão |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---|
| só A → AF | −2 | 2,73 | 5,32 | [−7,69; 13,15] | 0,617 | 57 (57 + 0) | 41 (23,8) | 57 / 1.244 | 526 / 9.897 | não |
| só A → AF | 0 | −2,45 | 4,19 | [−10,66; 5,76] | 0,579 | 69 (69 + 0) | 45 (24,5) | 69 / 1.349 | 778 / 13.471 | não |
| só A → AF | 1 | −0,90 | 3,93 | [−8,60; 6,81] | 0,821 | 59 (59 + 0) | 40 (23,7) | 59 / 1.301 | 675 / 12.140 | não |
| só AF → A (sinal do AF) | −2 | −1,45 | 5,31 | [−11,85; 8,96] | 0,790 | 53 (0 + 53) | 31 (14,6) | 53 / 636 | 844 / 12.319 | não |
| só AF → A (sinal do AF) | 0 | −3,73 | 4,93 | [−13,39; 5,92] | 0,458 | 67 (0 + 67) | 39 (16,6) | 67 / 667 | 1.086 / 14.869 | não |
| só AF → A (sinal do AF) | 1 | −4,99 | 4,30 | [−13,41; 3,44] | 0,246 | 61 (0 + 61) | 35 (15,6) | 61 / 628 | 1.012 / 14.393 | não |

Conjuntos robustos. ✱ marca IC que exclui zero.

| Espec. | Parâm. | estimativa (Δ vs −1,91) | IC original | Δ^RM M̄=0 | Δ^RM M̄=1 | Δ^RM M̄=2 | Δ^SD M=0 | Δ^SD M=1 | Δ^SD M=2 |
|---|---|---:|---|---|---|---|---|---|---|
| principal | (a) 1º trim. | −3,14 (−1,23) | [−9,4; 3,1] | [−9,3; 3,0] | [−12,4; 7,1] | [−17,4; 13,3] | [−14,2; 9,0] | [−14,3; 9,1] | [−14,8; 9,6] |
| principal | (b) média pós | −3,13 (−1,22) | [−8,4; 2,1] | [−8,3; 2,1] | [−14,3; 9,5] | [−22,3; 19,1] | [−16,6; 11,9] | [−17,1; 12,4] | [−18,4; 13,8] |
| só A → AF | (a) 1º trim. | −2,45 (−0,54) | [−10,7; 5,8] | [−10,6; 5,6] | [−13,8; 13,5] | [−24,1; 24,6] | [−15,4; 16,0] | [−15,5; 16,1] | [−15,9; 16,4] |
| só A → AF | (b) média pós | −1,68 (0,23) | [−8,0; 4,6] | [−7,9; 4,6] | [−18,1; 18,4] | [−34,7; 35,3] | [−16,5; 21,3] | [−16,9; 21,7] | [−18,0; 22,8] |
| só AF → A (sinal do AF) | (a) 1º trim. | −3,73 (−1,82) | [−13,4; 5,9] | [−13,1; 5,6] | [−20,4; 10,0] | [−30,3; 17,1] | [−23,3; 12,9] | [−23,3; 13,0] | [−23,7; 13,3] |
| só AF → A (sinal do AF) | (b) média pós | −4,36 (−2,45) | [−12,9; 4,1] | [−12,8; 4,1] | [−25,4; 12,2] | [−40,7; 23,0] | [−28,9; 15,9] | [−29,3; 16,2] | [−30,2; 17,2] |

- **As pré-tendências diferem por direção:**
  - A → AF: +2,73 lp, p = 0,61;
  - AF → A, com sinal do AF: −1,45 lp, p = 0,79.

  No combinado, elas se cancelam em parte (+0,52). Isso é o que se espera se houver uma tendência comum às unidades que
  trocam, em qualquer direção, mas os dados não têm precisão para afirmá-lo.
- **Direções separadas:** os conjuntos são bem mais largos que os do combinado e todos incluem zero. Em M̄ = 1, (b) dá:
  - A → AF: [−18,1; 18,4];
  - AF → A: [−25,4; 12,2].
- **Combinado (e):** é a especificação principal. Ele supõe efeito simétrico (o mesmo do M0); as direções separadas não
  rejeitam nem confirmam essa suposição.

## 8. Sensibilidades

### 8.1 Pesos, painel balanceado, matrizes alternativas e modelo filtrado

| Espec. | Parâm. | estimativa (Δ vs −1,91) | IC original | Δ^RM M̄=0 | Δ^RM M̄=1 | Δ^RM M̄=2 | Δ^SD M=0 | Δ^SD M=1 | Δ^SD M=2 |
|---|---|---:|---|---|---|---|---|---|---|
| principal | (a) 1º trim. | −3,14 (−1,23) | [−9,4; 3,1] | [−9,3; 3,0] | [−12,4; 7,1] | [−17,4; 13,3] | [−14,2; 9,0] | [−14,3; 9,1] | [−14,8; 9,6] |
| principal | (b) média pós | −3,13 (−1,22) | [−8,4; 2,1] | [−8,3; 2,1] | [−14,3; 9,5] | [−22,3; 19,1] | [−16,6; 11,9] | [−17,1; 12,4] | [−18,4; 13,8] |
| principal, matriz jackknife | (a) 1º trim. | −3,14 (−1,23) | [−9,6; 3,3] | [−9,5; 3,2] | [−12,6; 7,4] | [−17,9; 13,7] | [−14,5; 9,3] | [−14,6; 9,4] | [−15,1; 9,9] |
| principal, matriz jackknife | (b) média pós | −3,13 (−1,22) | [−8,5; 2,3] | [−8,4; 2,1] | [−14,6; 9,8] | [−22,8; 19,5] | [−16,9; 12,2] | [−17,4; 12,7] | [−18,8; 14,1] |
| principal, matriz bootstrap | (a) 1º trim. | −3,14 (−1,23) | [−9,5; 3,2] | [−9,4; 3,2] | [−12,5; 7,2] | [−17,7; 13,6] | [−14,3; 9,1] | [−14,5; 9,3] | [−14,9; 9,7] |
| principal, matriz bootstrap | (b) média pós | −3,13 (−1,22) | [−8,5; 2,2] | [−8,4; 2,1] | [−14,5; 9,7] | [−22,7; 19,4] | [−16,8; 12,1] | [−17,3; 12,6] | [−18,6; 13,9] |
| pesos iguais | (a) 1º trim. | −4,74 (−2,83) | [−12,2; 2,7] | [−12,2; 2,7] | [−14,5; 8,8] | [−22,4; 17,5] | [−15,0; 10,8] | [−15,2; 10,9] | [−15,6; 11,3] |
| pesos iguais | (b) média pós | −3,27 (−1,36) | [−9,4; 2,8] | [−9,3; 2,8] | [−16,6; 13,6] | [−29,8; 27,3] | [−14,8; 16,1] | [−15,3; 16,5] | [−16,6; 17,8] |
| balanceado | (a) 1º trim. | −3,77 (−1,86) | [−11,5; 4,0] | [−11,5; 3,9] | [−14,8; 7,0] | [−20,8; 13,1] | [−16,8; 9,2] | [−17,0; 9,3] | [−17,4; 9,7] |
| balanceado | (b) média pós | −3,25 (−1,34) | [−9,5; 3,0] | [−9,4; 2,9] | [−16,3; 9,6] | [−25,8; 18,8] | [−18,8; 12,1] | [−19,2; 12,6] | [−20,5; 13,9] |
| filtrado (G ≤ 0,80) | (a) 1º trim. | −4,15 (−2,24) | [−10,4; 2,1] | [−10,4; 2,0] | [−15,8; 3,6] | [−23,1; 8,8] | [−17,6; 5,5] | [−17,8; 5,7] | [—; —] ✱ |
| filtrado (G ≤ 0,80) | (b) média pós | −4,80 (−2,89) | [−9,7; 0,1] | [−9,7; 0,1] | [−19,3; 4,5] | [−30,6; 15,4] | [−21,5; 6,2] | [−22,1; 6,7] | [−23,5; 8,1] |

- **Matrizes jackknife e bootstrap:** praticamente o mesmo resultado (diferenças < 0,3 lp nos limites).
- **Pesos iguais:**
  - o coeficiente do 1º trimestre fica mais negativo (−4,74) e o pré-coeficiente maior (+2,61);
  - por isso, os conjuntos de Δ^RM ficam mais largos: em M̄ = 1, (b) vai de −16,6 a 13,6.
- **Painel balanceado** (87 eventos, com o mesmo conjunto de eventos em todos os trimestres): o pré-coeficiente é ≈ 0
  (−0,05), e os conjuntos ficam parecidos com os do principal.
- **Modelo filtrado** (exploratório):
  - o efeito médio é mais negativo (−4,80), e o IC original de (b) quase exclui zero ([−9,72; 0,12]);
  - em M̄ = 0, o IC continua incluindo zero ([−9,7; 0,1]), e em M̄ = 1 vai de −19,3 a 4,5;
  - o FLCI do pacote falhou numericamente em M = 2 e 3 em (a) (registrado).

### 8.2 Número de pré-períodos e janela posterior (janela de 12 meses)

Os 78 eventos da janela de 12 meses são outra amostra: o critério de vizinhança é de 12 meses, e a troca precisa ter
magnitude ≥ 0,5. Desses eventos, 71 têm compra no trimestre −1.

| Espec. | Trim. | coef (lp) | EP | IC95 normal | p WCR | eventos (A→AF + AF→A) | órgãos (efet.) | UASGs trat. / ctrl. | compras / itens trat. (q + ref.) | baixa precisão |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---|
| janela 12: 3 pré, 4 pós | −4 | 6,57 | 7,99 | [−9,10; 22,24] | 0,446 | 14 (4 + 10) | 12 (8,1) | 14 / 628 | 108 / 1.961 | sim |
| janela 12: 3 pré, 4 pós | −3 | −8,03 | 9,26 | [−26,19; 10,12] | 0,448 | 25 (10 + 15) | 19 (12,6) | 25 / 1.368 | 216 / 3.878 | sim |
| janela 12: 3 pré, 4 pós | −2 | −1,21 | 6,76 | [−14,46; 12,03] | 0,862 | 46 (25 + 21) | 32 (17,5) | 46 / 1.774 | 336 / 6.270 | não |
| janela 12: 3 pré, 4 pós | 0 | −4,85 | 4,17 | [−13,01; 3,32] | 0,248 | 69 (38 + 31) | 45 (18,7) | 69 / 1.856 | 726 / 11.283 | não |
| janela 12: 3 pré, 4 pós | 1 | −7,69 | 5,77 | [−19,00; 3,62] | 0,190 | 56 (28 + 28) | 36 (17,2) | 56 / 1.697 | 684 / 12.098 | não |
| janela 12: 3 pré, 4 pós | 2 | −5,99 | 5,99 | [−17,73; 5,76] | 0,338 | 60 (33 + 27) | 39 (18,0) | 60 / 1.737 | 625 / 10.805 | não |
| janela 12: 3 pré, 4 pós | 3 | −4,67 | 5,52 | [−15,49; 6,15] | 0,413 | 59 (30 + 29) | 38 (17,6) | 59 / 1.716 | 675 / 10.622 | não |

| Espec. | Parâm. | estimativa (Δ vs −1,91) | IC original | Δ^RM M̄=0 | Δ^RM M̄=1 | Δ^RM M̄=2 | Δ^SD M=0 | Δ^SD M=1 | Δ^SD M=2 |
|---|---|---:|---|---|---|---|---|---|---|
| janela 12: 1 pré, 2 pós | (a) 1º trim. | −4,85 (−2,94) | [−13,0; 3,3] | [−12,9; 3,3] | [−21,4; 9,3] | [−33,3; 18,8] | [−24,1; 12,0] | [−24,2; 12,1] | [−24,5; 12,4] |
| janela 12: 1 pré, 2 pós | (b) média pós | −6,27 (−4,36) | [−14,9; 2,3] | [−14,6; 2,2] | [−28,7; 12,5] | [−47,1; 28,9] | [−32,7; 16,5] | [−33,0; 16,8] | [−33,8; 17,7] |
| janela 12: 2 pré, 2 pós | (a) 1º trim. | −4,85 (−2,94) | [−13,0; 3,3] | [−12,9; 3,3] | [−26,8; 17,4] | [−46,1; 36,9] | [−22,6; 4,7] | [−22,9; 5,0] | [−23,5; 6,1] |
| janela 12: 2 pré, 2 pós | (b) média pós | −6,27 (−4,36) | [−14,9; 2,3] | [−14,6; 2,2] | [−38,9; 24,5] | [−68,9; 54,3] | [−30,7; 6,8] | [−31,4; 7,5] | [−32,9; 9,7] |
| janela 12: 3 pré, 2 pós | (a) 1º trim. | −4,85 (−2,94) | [−13,0; 3,3] | [−12,9; 3,3] | [−32,1; 24,9] | [−57,6; 50,8] | [−13,2; 9,1] | [−14,9; 9,0] | [−17,7; 9,6] |
| janela 12: 3 pré, 2 pós | (b) média pós | −6,27 (−4,36) | [−14,9; 2,3] | [−14,6; 2,2] | [−47,5; 35,2] | [−86,6; 74,3] | [−14,1; 13,0] | [−17,0; 13,8] | [−21,9; 15,9] |
| janela 12: 1 pré, 4 pós | (a) 1º trim. | −4,85 (−2,94) | [−13,0; 3,3] | [−12,9; 3,3] | [−21,3; 9,3] | [−33,1; 18,8] | [−24,1; 12,0] | [−24,2; 12,1] | [−24,5; 12,4] |
| janela 12: 1 pré, 4 pós | (b) média pós | −5,80 (−3,89) | [−14,1; 2,5] | [−13,9; 2,3] | [−41,3; 23,9] | [−72,0; 52,6] | [−47,3; 29,6] | [−48,5; 30,8] | [−51,7; 34,0] |
| janela 12: 2 pré, 4 pós | (a) 1º trim. | −4,85 (−2,94) | [−13,0; 3,3] | [−12,9; 3,3] | [−26,6; 17,4] | [−46,3; 37,1] | [−22,6; 4,7] | [−22,9; 5,0] | [−23,5; 6,1] |
| janela 12: 2 pré, 4 pós | (b) média pós | −5,80 (−3,89) | [−14,1; 2,5] | [−13,9; 2,3] | [−57,8; 45,7] | [−84,3; 84,3] | [−42,8; 12,0] | [−44,9; 14,7] | [−49,9; 20,5] |
| janela 12: 3 pré, 4 pós | (a) 1º trim. | −4,85 (−2,94) | [−13,0; 3,3] | [−12,9; 3,3] | [−31,9; 24,8] | [−57,8; 50,8] | [−13,2; 9,1] | [−14,9; 9,0] | [−17,7; 9,6] |
| janela 12: 3 pré, 4 pós | (b) média pós | −5,80 (−3,89) | [−14,1; 2,5] | [−13,9; 2,3] | [−72,8; 62,4] | [−84,3; 84,3] | [−15,4; 20,6] | [−21,9; 24,3] | [−31,5; 30,3] |
| antecipação, janela 12, ref. −2 | (a) 1º trim. | −4,96 (−3,05) | [−17,5; 7,6] | [−17,3; 7,6] | [−60,7; 42,5] | [−111,1; 92,1] | [−33,4; 15,4] | [−34,6; 16,6] | [−37,7; 19,7] |
| antecipação, janela 12, ref. −2 | (b) média pós | −6,51 (−4,60) | [−19,9; 6,9] | [−19,9; 7,0] | [−77,2; 50,6] | [−137,0; 112,9] | [−37,2; 16,7] | [−39,4; 18,9] | [−44,6; 24,1] |
| antecipação, janela 12, ref. −2 | trim. −1 | 1,21 (3,12) | [−12,0; 14,5] | [−11,8; 14,2] | [−32,1; 26,1] | [−56,4; 46,7] | [−18,7; 19,2] | [−18,9; 19,5] | [−19,7; 20,2] |

Desvio de tendência linear, Δ^SDRM, só com 2 ou mais pré-períodos:

| Espec. | Parâm. | estimativa (Δ vs −1,91) | IC original | Δ^SDRM M̄=0 | Δ^SDRM M̄=1 | Δ^SDRM M̄=2 |
|---|---|---:|---|---|---|---|
| janela 12: 2 pré, 2 pós | (a) 1º trim. | −4,85 (−2,94) | [−13,0; 3,3] | [−23,8; 11,8] | [−32,3; 31,3] | [−48,6; 55,8] |
| janela 12: 2 pré, 2 pós | (b) média pós | −6,27 (−4,36) | [−14,9; 2,3] | [−32,5; 16,4] | [−51,5; 57,5] | [−87,6; 87,6] |
| janela 12: 3 pré, 2 pós | (a) 1º trim. | −4,85 (−2,94) | [−13,0; 3,3] | [−23,8; 11,8] | [−53,1; 45,1] | [−83,3; 83,3] |
| janela 12: 3 pré, 2 pós | (b) média pós | −6,27 (−4,36) | [−14,9; 2,3] | [−32,5; 16,4] | [−87,6; 87,3] | [−87,6; 87,6] |
| janela 12: 2 pré, 4 pós | (a) 1º trim. | −4,85 (−2,94) | [−13,0; 3,3] | [−24,1; 12,1] | [−31,9; 31,3] | [−48,8; 56,0] |
| janela 12: 2 pré, 4 pós | (b) média pós | −5,80 (−3,89) | [−14,1; 2,5] | [−47,0; 29,5] | [−84,3; 84,3] | [−84,3; 84,3] |
| janela 12: 3 pré, 4 pós | (a) 1º trim. | −4,85 (−2,94) | [−13,0; 3,3] | [−24,1; 12,1] | [−53,0; 45,0] | [−83,3; 83,3] |
| janela 12: 3 pré, 4 pós | (b) média pós | −5,80 (−3,89) | [−14,1; 2,5] | [−47,0; 29,5] | [−84,3; 84,3] | [−84,3; 84,3] |
| antecipação, janela 12, ref. −2 | (a) 1º trim. | −4,96 (−3,05) | [−17,5; 7,6] | [−67,7; 19,6] | [−128,3; 81,3] | [−128,3; 128,3] |
| antecipação, janela 12, ref. −2 | (b) média pós | −6,51 (−4,60) | [−19,9; 6,9] | [−85,7; 25,1] | [−137,0; 129,9] | [−137,0; 137,0] |
| antecipação, janela 12, ref. −2 | trim. −1 | 1,21 (3,12) | [−12,0; 14,5] | [−35,9; 19,3] | [−72,1; 26,7] | [−114,6; 64,5] |

- **Mais pré-períodos não ajudam com estes dados.** Os trimestres −4 e −3 têm de 13 a 27 eventos e de 10 a 19 órgãos.
  - Os pré-coeficientes oscilam: +6,6, −8,0, −1,2.
  - Com 3 pré-períodos, a maior variação pré entre trimestres consecutivos é de ~15 lp. Por isso, os conjuntos de Δ^RM
    em M̄ = 1 chegam a ±25–70 lp.
- **Suavidade:** com 2 ou 3 pré-períodos, a curvatura pré estimada (5,6 a 21 lp) supera todo o M da grade.
  - O conjunto identificado em β = β̂ fica **vazio**: a tendência pré estimada não é suave o bastante para nenhum M ≤ 3.
  - O FLCI do pacote ainda devolve intervalos, porque a inferência considera o erro amostral, mas eles não descrevem um
    conjunto identificado não vazio no ponto estimado.
  - A função interna do pacote, nesses casos, devolve a estimativa pontual como substituto. O relatório usa "vazio",
    conferido por programação linear.
- **Janela posterior:** passar de 2 para 4 pós-períodos alarga o parâmetro (b) da janela de 12 meses, porque a média
  inclui trimestres mais distantes, sobre os quais as restrições acumulam viés.
- **Δ^SDRM** (desvio de tendência linear): também sem conclusão (tabela acima).

### 8.3 Antecipação

| Espec. | Trim. | coef (lp) | EP | IC95 normal | p WCR | eventos (A→AF + AF→A) | órgãos (efet.) | UASGs trat. / ctrl. | compras / itens trat. (q + ref.) | baixa precisão |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---|
| antecipação, janela 6, ref. −2 (diagnóstico) | −1 | −0,52 | 3,59 | [−7,56; 6,51] | 0,885 | 110 (57 + 53) | 57 (23,9) | 99 / 1.879 | 1.370 / 22.216 | não |
| antecipação, janela 6, ref. −2 (diagnóstico) | 0 | −2,53 | 3,55 | [−9,48; 4,43] | 0,484 | 115 (60 + 55) | 58 (24,6) | 102 / 1.918 | 1.549 / 22.450 | não |
| antecipação, janela 6, ref. −2 (diagnóstico) | 1 | −3,74 | 3,77 | [−11,14; 3,65] | 0,331 | 102 (50 + 52) | 53 (23,4) | 92 / 1.879 | 1.432 / 22.720 | não |
| antecipação, janela 12, ref. −2 | −4 | −4,64 | 8,24 | [−20,79; 11,50] | 0,596 | 13 (2 + 11) | 10 (8,0) | 13 / 560 | 156 / 2.674 | sim |
| antecipação, janela 12, ref. −2 | −3 | −9,53 | 9,40 | [−27,95; 8,89] | 0,348 | 27 (10 + 17) | 19 (12,0) | 27 / 1.420 | 276 / 4.974 | sim |
| antecipação, janela 12, ref. −2 | −1 | 1,21 | 6,76 | [−12,03; 14,46] | 0,862 | 46 (25 + 21) | 32 (17,5) | 46 / 1.774 | 336 / 6.270 | não |
| antecipação, janela 12, ref. −2 | 0 | −4,96 | 6,41 | [−17,53; 7,61] | 0,456 | 47 (25 + 22) | 33 (17,6) | 47 / 1.728 | 364 / 7.474 | não |
| antecipação, janela 12, ref. −2 | 1 | −8,05 | 8,77 | [−25,24; 9,13] | 0,376 | 39 (18 + 21) | 28 (17,6) | 39 / 1.675 | 348 / 8.994 | não |

- **Janela de 6 meses** (referência −2): o coeficiente do trimestre −1, que mede a antecipação, é −0,52 lp (EP 3,59;
  p = 0,89). Não há sinal de antecipação, mas a medida tem a mesma imprecisão do pré-teste. Sem pré-período, o HonestDiD
  não se aplica.
- **Janela de 12 meses** (referência −2; pré-períodos −4 e −3):
  - a antecipação estimada é +1,21 lp (IC original [−12,0; 14,5]);
  - os conjuntos robustos são muito largos: (a) em M̄ = 1 vai de −60,7 a 42,5, porque os dois pré-coeficientes (−4,6 e
    −9,5 lp) entram como magnitude pré de referência.

### 8.4 Influência: retirando um órgão por vez

| Parâm. | Restrição | Amostra completa | limite inferior: mín.–máx. | limite superior: mín.–máx. | retiradas com IC sem zero |
|---|---|---|---|---|---:|
| (a) 1º trim. | Δ^RM, M̄ = 1 | [−12,39; 7,13] | −15,00 a −10,71 | 3,24 a 8,70 | 0 de 68 |
| (a) 1º trim. | Δ^SD, M = 1 | [−14,34; 9,12] | −16,89 a −12,52 | 5,09 a 10,91 | 0 de 68 |
| (b) média pós | Δ^RM, M̄ = 1 | [−14,34; 9,50] | −17,50 a −12,49 | 5,09 a 11,94 | 0 de 68 |
| (b) média pós | Δ^SD, M = 1 | [−17,06; 12,37] | −20,21 a −13,86 | 7,78 a 14,88 | 0 de 68 |

Coeficientes dinâmicos sem um órgão:

| Coeficiente | Amostra completa | mín. sem um órgão | máx. sem um órgão | maior variação de EP |
|---|---:|---:|---:|---:|
| trim. −2 | 0,52 | −1,07 | 1,81 | 9,8% |
| trim. 0 | −3,14 | −4,83 | −2,27 | 10,2% |
| trim. 1 | −3,12 | −4,39 | −2,20 | 7,9% |

- **Nenhuma retirada de órgão leva um conjunto robusto a excluir zero:** 0 de 68 em cada combinação de parâmetro e
  restrição.
- **Limites:** o inferior varia de 3 a 6 lp e o superior de 4 a 7 lp entre as retiradas.
- **Coeficientes dinâmicos:** variam de −1,1 a +1,8 (pré), de −4,8 a −2,3 (trimestre 0) e de −4,4 a −2,2 (trimestre +1).

### 8.5 Pontos de quebra

| Espec. | Parâm. | Restrição | Aplica? | Quebra | Nota |
|---|---|---|---|---:|---|
Parâmetros em que o IC já inclui zero no menor valor da grade (sem quebra a relatar): 73 de 73 combinações de especificação, parâmetro e família.

**Nenhum ponto de quebra se aplica.** Em todas as 73 combinações de especificação, parâmetro e família, o conjunto
de confiança já inclui zero no menor valor da grade (M̄ = 0 ou M = 0).

Não há, portanto, "perda de significância" a relatar, e o resultado inicial não era significativo. A conclusão estatística
que muda com M é só a amplitude das faixas compatíveis (seções 6 e 7).

## 9. Respostas às perguntas

1. **Reduções compatíveis com os dados**, admitindo violações (especificação principal):
   - (a), 1º trimestre: até 9,3 lp (M̄ = 0), 12,4 (M̄ = 1), 17,4 (M̄ = 2) ou 22,7 (M̄ = 3); com Δ^SD, até 14–16 lp;
   - (b), média: até 8,3, 14,3, 22,3 ou 30,3 lp; com Δ^SD, até 17–20 lp.

   Em percentual, uma redução de 14 lp corresponde a −13%.
2. **Aumentos compatíveis:**
   - (a): até 3,0 (M̄ = 0), 7,1 (M̄ = 1), 13,3 (M̄ = 2) ou 19,6 lp (M̄ = 3); com Δ^SD, até 9–10 lp;
   - (b): até 2,1, 9,5, 19,1 ou 28,6 lp; com Δ^SD, até 12–16 lp.
3. **Dependência das tendências paralelas.**
   - A conclusão de que não há efeito significativo não depende da hipótese: ela vale sob tendências paralelas exatas e
     sob todas as violações admitidas.
   - Depende da hipótese só a exclusão de efeitos grandes. Sem tendências paralelas exatas, os dados já não excluem
     reduções de 12–20 lp nem aumentos de 7–19 lp.
   - Como o único pré-período tem EP de 3,6 lp e o pré-teste não detecta tendências menores que ~10 lp por trimestre, os
     dados não sustentam tendências paralelas exatas.
4. **Suavidade e magnitudes relativas:** as conclusões qualitativas coincidem (todos os conjuntos incluem zero, e ambos
   são bem mais largos que o original). A forma difere:
   - Δ^RM cresce linearmente com M̄ a partir do IC original;
   - Δ^SD já é largo em M = 0, por extrapolar linearmente um pré-coeficiente impreciso, e cresce pouco;
   - em (a), o Δ^SD com M = 0 equivale, em largura, ao Δ^RM com M̄ ≈ 1,3;
   - na janela de 12 meses, as famílias divergem mais: o conjunto identificado de Δ^SD fica vazio.
5. **Evidência a favor do AF?** Não. A análise só amplia a incerteza.
   - Os coeficientes dinâmicos têm sinal negativo (−3,1 lp), mas nenhum conjunto robusto exclui zero, nem mesmo com
     M̄ = 0.
   - Nada nesta análise permite atribuir a diferença ao AF.
6. **Os dados bastam para aplicar o HonestDiD de forma tecnicamente válida?** Em parte.
   - **O que está correto:**
     - matriz de covariância completa, agrupada por órgão, verificada por jackknife e bootstrap;
     - procedimentos oficiais do pacote;
     - 1 pré-período, aceito pelo pacote para Δ^RM e para Δ^SD com FLCI.
   - **O que é fraco:**
     - na janela principal há **um único pré-período**, impreciso: ele não informa a curvatura da tendência e fixa a
       magnitude pré de referência com muito erro;
     - os pré-períodos extras da janela de 12 meses têm poucos eventos e órgãos;
     - os coeficientes vêm de conjuntos de eventos diferentes;
     - o estimando dinâmico não é o do M0;
     - o FLCI do pacote falhou em 3 pontos.
   - **Conclusão:** o exercício é válido como sensibilidade, mas os dados não têm precisão para limites informativos.

## 10. Limitações de identificação e precisão

**Identificação:**
- Na janela principal há 1 só pré-período (trimestre −2), com EP de 3,6 lp e 110 eventos.
  - O Δ^RM ancora a magnitude pré nesse coeficiente; o Δ^SD não tem informação pré sobre curvatura.
  - O Δ^SDRM não se aplica.
- Os coeficientes por trimestre usam eventos diferentes (110, 136, 120). O balanceado (87) confirma o padrão, mas com
  amostra menor.
- O estimando dinâmico (efeitos contra o trimestre −1) não é o do M0 (meia janela contra meia janela). A diferença,
  medida nos mesmos eventos, é de cerca de 1,9 lp.
- O combinado supõe efeito simétrico entre as direções da troca, como o M0. As pré-tendências por direção têm sinais
  opostos.
- Na janela de 12 meses (78 eventos, 71 com compra no trimestre −1), os trimestres −4 e −3 têm baixa precisão (13 a 27
  eventos e 10 a 19 órgãos).

**Precisão e inferência:**
- O pacote trata β̂ como normal com V conhecida. A V é estimada com 57 a 68 órgãos por coeficiente na janela principal e
  com 10 a 45 na de 12 meses.
- O IC original do pacote (normal) é um pouco diferente do IC WCR do M0, porque também os estimandos diferem.
- Houve falha numérica do FLCI do pacote em F1 (a), com M = 2 e 3, e em P1 com matriz bootstrap (b), com M = 3
  ("valor ausente onde TRUE/FALSE necessário"). Esses valores ficam sem resultado, sem substituto.
- O pacote emitiu 604 avisos ("NaNs produzidos" e reciclagem de vetor descontinuada), registrados por linha em
  `tabelas/honestdid_resultados.csv`.
- Duas linhas (F1|a e P1_BOOT|b) foram refeitas com avaliação valor a valor, depois de a falha num valor de M derrubar a
  chamada inteira. O `executar.R` atual faz isso direto; o registro guarda a reexecução.

**Escopo:**
- Tudo é exploratório.
- Os 56 eventos reservados não foram usados.
- Nenhum teste confirmatório foi feito.

## Gráficos

`graficos/`:

| Arquivo | Conteúdo |
|---|---|
| `g1_coeficientes_dinamicos.svg` | Perfil, janelas de 6 e 12 meses |
| `g2_magnitudes_relativas.svg` | Δ^RM |
| `g3_suavidade.svg` | Δ^SD |
| `g4_direcoes.svg` | Direções |
| `g5_sensibilidades_media.svg`, `g5_sensibilidades_primeiro.svg` | Sensibilidades em M̄ = 1 e M = 1 |
| `g6_influencia_orgaos.svg` | Influência por órgão |

As versões em tabela estão em `tabelas/`.

![Coeficientes dinâmicos](graficos/g1_coeficientes_dinamicos.svg)
![Magnitudes relativas](graficos/g2_magnitudes_relativas.svg)
![Suavidade](graficos/g3_suavidade.svg)
![Direções](graficos/g4_direcoes.svg)
![Sensibilidades, média](graficos/g5_sensibilidades_media.svg)
![Sensibilidades, 1º trimestre](graficos/g5_sensibilidades_primeiro.svg)
![Influência](graficos/g6_influencia_orgaos.svg)

## Reprodução

```
python analises/honestdid_sensibilidade_20261124/executar.py
```

Leva cerca de 35 minutos.

**Pré-requisitos:**
- a base de 23/11 (`../testes_desenho_causal_20261123/preparar.py`);
- R com o pacote `HonestDiD`.

Versões, conferências, falhas e avisos do pacote ficam em `registro_execucao.json`. O log do R fica em
`dados/honestdid_sensibilidade/executar_R.log`, fora do git.
