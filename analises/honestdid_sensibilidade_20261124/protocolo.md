# Protocolo: sensibilidade HonestDiD (Rambachan e Roth, 2023) do estudo de eventos A × AF (24/11/2026)

**Status: exploratório.** Escrito antes de qualquer estimativa nova; o hash SHA-256 deste arquivo vai para
`registro_execucao.json`. Nenhuma especificação, grade ou parâmetro é escolhido pelo valor-p.

## 0. O que já era conhecido antes deste protocolo

Os resultados abaixo já foram vistos em análises anteriores. Eles não definem nenhuma escolha deste protocolo.

- **Modelo principal (M0)**, em `testes_desenho_causal_20261123/resultados.json`:
  - efeito do AF de −1,91 lp, IC95 WCR [−5,67; 1,93], p = 0,32;
  - 152 eventos e 70 órgãos.
- **Perfil por trimestre do pré-registro de 23/11** (base −1; pesos de precisão do M0):

  | Trimestre | Coeficiente | EP CR1 | Eventos |
  |---|---:|---:|---:|
  | −2 | +0,53 | 3,59 | 110 |
  | 0 | −3,14 | 3,21 | 136 |
  | +1 | −3,12 | 2,88 | 120 |

- **Janela de 12 meses:**
  - 78 eventos;
  - perfil de −4 a +3, com 14, 25 e 46 eventos nos trimestres −4, −3 e −2;
  - teste conjunto pré com só 9 eventos.
- **Sensibilidade "rambachan_roth" de 23/11:** uma versão simplificada, com erros-padrão isolados e sem matriz de
  covariância. **Não é usada aqui**; este protocolo a substitui pelo pacote oficial com a matriz conjunta.
- **Modelo filtrado M1** (referência G, dispersão ≤ 0,80): −3,76 lp, IC [−6,67; −0,89]. Também foi visto o perfil por
  trimestre da investigação de composição.

## 1. Dados e amostra

- **Base:** a de 23/11 (`dados/testes_desenho_causal/`), lida pelo motor de `../robustez_dispersao_20261123/`. O `pncp.db`
  não é lido, e nada anterior é alterado.
- **Eventos:** `Base.eventos(6)`, com mês do evento até 2025-10. Os 56 eventos posteriores, reservados para a validação,
  não entram em nenhuma etapa. O script confere isso e para se algum entrar.
- **Índice:** `e_ok`, isto é, log P menos a referência A por produto × trimestre, sem a própria UASG; |e| ≤ ln 10.
  Média por compra, como no M0.
- **Controles e elegibilidade:** os do M0.
  - Controles: mesma esfera, estáveis no modo de partida nas duas meias janelas, sem evento próprio a menos de 6 meses,
    pelo menos 5 por evento.
  - Tratada: pelo menos 2 compras em cada meia janela.
- **Pesos:** de precisão do M0, w = 1/(a + b·h), com a = 0,009415, b = 0,23849 e h = 1/c_pré + 1/c_pós (compras da
  tratada nas meias janelas). O peso de cada evento é o mesmo em todos os trimestres, como no perfil de 23/11.
- **Agrupamento:** órgão (CNPJ).

## 2. Coeficientes dinâmicos (principal)

**Perfil por trimestre relativo** q ∈ {−2, −1, 0, +1} da janela de 6 meses, com referência no trimestre −1, o
imediatamente anterior à troca. É o estimador do perfil de 23/11.

- **Por evento:** `b_q` = [ȳ_tratada(q) − ȳ_tratada(−1)] − média dos controles de [ȳ_c(q) − ȳ_c(−1)], em que ȳ é a média
  por compra do índice no trimestre.
- **Exigências por trimestre:**
  - a tratada precisa ter compra em q e em −1;
  - entram os controles do M0 com compra em q e em −1, e são exigidos pelo menos 5.
- **Sinal:** efeito do AF (sinal +1 para A → AF e −1 para AF → A), aplicado ao vetor inteiro, inclusive ao pré-período.
- **β_q** é a média ponderada dos eventos com dado em q. Cada trimestre tem seus eventos; não há preenchimento nem zero
  no lugar de coeficiente ausente.
- **Vetor do HonestDiD:** β = (β₋₂ | β₀, β₊₁), com 1 pré-período e 2 pós-períodos. A referência fica fora do vetor.

  | Trimestre | Índice do pacote (t) |
  |---|---:|
  | −2 | −1 |
  | −1 (referência) | 0 |
  | 0 | 1 |
  | +1 | 2 |

**Conferência obrigatória:** os β_q e os EP por coeficiente reproduzem o perfil de 23/11, e o M0 é reproduzido.

**Estimando e diferença para o M0.** O M0 compara a meia janela pós [m, m+6) com a pré [m−6, m), em 152 eventos. O perfil
compara cada trimestre com o trimestre −1, nos eventos que têm compras nesses trimestres.

O parâmetro (b) adiante, a média de β₀ e β₊₁, não é o estimando do M0, por três razões:
- a base é o trimestre −1, e não a meia janela pré;
- os eventos são outros;
- a ponderação entre trimestres é igual, e não por compra.

O relatório quantifica essa diferença.

## 3. Matriz de covariância

O pacote recebe a matriz completa. Não se usa nenhum EP isolado como substituto.

- **Principal: CR1 conjunta por órgão.**
  - Influência do evento e no coeficiente q: ψ_eq = w_e(y_eq − β_q)/Σ w (zero se e não tem dado em q).
  - Ψ_g = soma das influências dos eventos do órgão g.
  - V = D^½ (Σ_g Ψ_g Ψ_g′) D^½, com D = diag(G_q/(G_q − 1)).
  - A diagonal coincide com o EP CR1 de cada coeficiente usado em 23/11, e V é semidefinida positiva por construção.
- **Verificações:**
  - jackknife por órgão;
  - bootstrap de pares por órgão (B = 9.999, semente fixa);
  - autovalores, número de condição e correlações;
  - variação dos EP ao retirar um órgão;
  - HonestDiD refeito com as matrizes alternativas.
- **Escala:** β e V em lp (100 × log), para que M fique em lp.

## 4. HonestDiD

- **Pacote:** `HonestDiD` oficial em R; a versão consultada na documentação de 24/11/2026 é a 0,2.8 do CRAN. Versões de R
  e dos pacotes vão para o registro. Se o R ou o pacote não estiver disponível:
  - as entradas (β, V) são gravadas;
  - a etapa fica registrada como pendente;
  - **nenhuma implementação própria substitui o pacote**.
- **Modelo** (Rambachan e Roth, 2023). β = τ + δ, com τ_pré = 0. δ é a diferença de tendências; δ₀ = 0 na referência.
  Parâmetro θ = l′τ_pós. α = 0,05.

### A. Magnitudes relativas: Δ^RM(M̄)

Δ^RM(M̄) = {δ : |δ_{t+1} − δ_t| ≤ M̄ · max_{s<0} |δ_{s+1} − δ_s| para todo t ≥ 0}.

- Função: `createSensitivityResults_relativeMagnitudes`, com `bound = "deviation from parallel trends"` e o método
  padrão, `"C-LF"` (híbrido condicional menos favorável).
- **M̄ ∈ {0; 0,5; 1; 1,5; 2; 3}**, a grade pedida.
- Com 1 pré-período, a violação pré de referência é |δ₋₁|, ou seja, a variação entre os trimestres −2 e −1.

### B. Suavidade: Δ^SD(M)

Δ^SD(M) = {δ : |(δ_{t+1} − δ_t) − (δ_t − δ_{t−1})| ≤ M para todo t}.

- Função: `createSensitivityResults`, com o método padrão para Δ^SD sem restrição de sinal ou monotonicidade, o FLCI.
- **M ∈ {0; 0,25; 0,5; 1; 1,5; 2; 3} lp por trimestre** (variação máxima da inclinação de um trimestre para o
  seguinte).

**Justificativa da escala de M.** Em relação à extrapolação linear da pré-tendência, Δ^SD(M) admite um viés de até:
- M no 1º trimestre pós;
- 3M no 2º;
- 2M na média dos dois.

A grade vai de M = 0, tendência diferencial exatamente linear, a M = 3, em que o viés admitido na média chega a 6 lp. Isso
está acima do efeito principal (1,91 lp) e da semiamplitude do IC original (3,8 lp). A escala foi fixada por essa
conta, antes de estimar.

**Com 1 pré-período:**
- o pré-período não informa a curvatura;
- Δ^SD(0) extrapola linearmente a inclinação entre −2 e −1;
- a variante "desvio de tendência linear" (Δ^SDRM) exige mais de 1 pré-período e só entra na janela de 12 meses, se
  houver.

### Parâmetros

| Parâmetro | Definição |
|---|---|
| (a) | 1º trimestre pós: l = (1, 0) |
| (b) | Média dos trimestres pós da janela principal: l = (½, ½) |
| (c) | A → AF separado: o mesmo vetor, só com esses eventos |
| (d) | AF → A separado, com sinal do efeito do AF (vetor × −1) |
| (e) | Combinado: o vetor principal |

**Condições do combinado (e).** Ele soma direções com sinal e supõe que o efeito do AF é simétrico, a mesma suposição do
M0. Uma tendência comum às unidades que trocam, qualquer que seja a direção, se cancela no combinado, mas não nas
direções separadas. Por isso (c) e (d) são relatados lado a lado com (e).

### Saídas por especificação, parâmetro e valor

- IC robusto de 95% (lb, ub) e se inclui zero.
- Reduções e aumentos compatíveis.
- Conjunto identificado no ponto estimado, isto é, o conjunto de θ compatível com β = β̂ e δ ∈ Δ, sem erro amostral:
  - é a "estimativa correspondente";
  - em Δ^RM, o centro é l′β̂;
  - em Δ^SD, o centro é a estimativa corrigida pela tendência linear;
  - é calculado com as funções internas do pacote, quando existirem, e conferido por programação linear em Python.
- IC original do pacote (`constructOriginalCS`).

### Ponto de quebra

Só para os parâmetros cujo IC no menor valor da grade (M̄ = 0 ou M = 0) exclui zero: o menor valor em que o IC passa a
incluir zero.
- **Busca:** bisseção entre os pontos da grade, com precisão de 0,01.
- **Se ainda exclui zero no maior valor:** quebra > 3.
- **Parâmetros cujo IC já inclui zero:** não há conclusão de significância a perder. O relatório dá só as faixas
  compatíveis e não apresenta "ponto de perda de significância".

## 5. Testes complementares

Em todos, a mudança de amostra ou de estimando fica explícita.

1. **Pré-tendência:**
   - teste do pré-coeficiente (CR1, normal e t(G − 1), e o p WCR de 23/11);
   - na janela de 12 meses, Wald conjunto com a matriz conjunta;
   - poder do pré-teste contra tendências lineares δ_t = γ·t (Roth, 2022): o γ detectado com 50% e 80% de poder e o viés
     que ele induz em (a) e (b).
2. **Número de pré-períodos:** janela de 12 meses (`Base.eventos(12)`, especificação já existente, com 78 eventos), com
   1, 2 e 3 pré-períodos (β₋₂; β₋₃, β₋₂; β₋₄, β₋₃, β₋₂).
3. **Janela posterior:** na janela de 12 meses, 2 pós-períodos (0 e +1) ou 4 (0 a +3). A média em (b) acompanha a janela.
4. **Pesos:** os do M0 contra pesos iguais por evento.
5. **Painel balanceado:** só eventos com dado nos três trimestres (−2, 0, +1).
6. **Influência:** retirar um órgão por vez, com HonestDiD em M̄ = 1 e M = 1 lp (valores fixados aqui) para (a) e (b).
7. **Estabilidade da matriz:** CR1, jackknife e bootstrap por órgão, com o HonestDiD refeito com cada uma.
8. **Antecipação:**
   - na janela de 6 meses, com referência no trimestre −2, o coeficiente do trimestre −1 mede a antecipação. Sem
     pré-período, o HonestDiD não se aplica; é só diagnóstico;
   - na janela de 12 meses, com referência −2 e pré-períodos −4 e −3, os pós-períodos são −1, 0 e +1, e os parâmetros são
     0, a média de 0 e +1 e −1, a antecipação.
9. **Filtrado** (M1, referência G com dispersão ≤ 0,80): o mesmo perfil e o HonestDiD. Exploratório, nunca o principal.

## 6. Critérios de validade técnica (registrados, não de seleção)

- **Matriz:** V semidefinida positiva e número de condição relatado.
- **Precisão dos coeficientes:** um coeficiente com menos de 30 eventos ou 20 órgãos é marcado como de baixa precisão.
  A especificação roda, mas não sustenta conclusão.
- **Pré-períodos:**
  - 1 pré-período basta formalmente para Δ^RM e para Δ^SD com FLCI;
  - com 1 só, o pré-período não informa a curvatura, e a magnitude pré de referência é um único coeficiente impreciso;
  - essa limitação entra no relatório.
- **Aproximação normal:** o pacote trata β̂ como normal com V conhecida. Com 50–70 órgãos, é uma aproximação, e o IC
  original do pacote é comparado com o IC WCR do M0.

## 7. Saídas

- `tabelas/*.csv`: coeficientes, matrizes, HonestDiD por família, parâmetro e valor, quebras, influência e
  sensibilidades.
- `entradas/`: β e V de cada especificação, lidas pelo R.
- `graficos/*.svg`.
- `registro_execucao.json`: parâmetros, versões, conferências e falhas.
- `relatorio.md`.

Comando único: `python analises/honestdid_sensibilidade_20261124/executar.py`.
