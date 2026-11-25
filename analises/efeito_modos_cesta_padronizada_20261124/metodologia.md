# Metodologia — efeito do modo de disputa na cesta padronizada

Este documento descreve, com as fórmulas, o que o código faz. O que foi fixado antes da estimação está em
[`protocolo.md`](protocolo.md); as correções posteriores estão em [`desvios_registro.md`](desvios_registro.md).

## 1. Unidades e notação

| Símbolo | Significado |
|---|---|
| i | item (`numero_controle_pncp`, `numero_item`) |
| k | compra |
| u | UASG, com 6 dígitos |
| o(u) | CNPJ do órgão da UASG |
| c | produto da cesta (CATMAT × unidade normalizada, com subtipo quando houver) |
| t | trimestre de abertura da proposta |
| AF_i | 1 se a compra do item foi em Aberto-Fechado; 0 se em Aberto |
| P_i | preço unitário homologado (`valor_unitario_resultado`, `registro_principal = 1`) |
| E_i | preço unitário estimado |

O produto de cada item vem da cesta congelada (`universo_produto`). Não se recalcula, e nenhum produto é reclassificado.

## 2. Desfecho

`Y_i = 100 [ln P_i − ln R_{c,t,−u}]`.

- A referência R é calculada com os itens elegíveis (mesmos filtros do item focal, nos dois modos) de **outras** UASGs na
  célula (c, t).
- Mínimos: n_{−u} ≥ 5 itens e k_{−u} ≥ 3 UASGs.
- Como os mínimos são contagens, a disponibilidade é a mesma para as 14 variantes. Isso dá a amostra comum.
- **Cálculo sem subtração:** para as estatísticas que são somas, a soma das outras UASGs é obtida por somas acumuladas
  à frente e atrás dentro da célula, nunca como "total − focal". As somas em nível usam a escala do máximo da célula.
  Medianas e aparas ordenam só os itens (ou as estatísticas de UASG) das outras unidades.
- **Variantes:**
  - A1 = média de ln P; A2 = ln da média de P; A3 = mediana de ln P;
  - A4 = ln da média de P depois de aparar ⌊0,1n⌋ por cauda (n ≥ 10); A5 = média aparada de ln P;
  - B_{w,b} = estatística b entre UASGs da estatística w dentro de cada UASG, com w, b ∈ {aritmética, geométrica, mediana}
    e peso igual por UASG comparadora.
- **Extremos:** a máscara principal é `|Y_A1| ≤ 100 ln 10`. Cada variante também tem a sua máscara própria.
- **Conversão:** log-pontos para percentual exato, `100[exp(β/100) − 1]`.

## 3. Efeitos fixos

`Y_i = β AF_i + α_u + λ_{c,t} + γ ln q_i + ε_i`, com q = quantidade prevista.

- **Estimação:** projeções alternadas (Guimarães–Portugal/Gaure), com tolerância de 1e-8 e remoção iterativa de
  singletons. β sai por FWL.
- **Erro-padrão:** CR1 agrupado por CNPJ, com G/(G−1)·(n−1)/(n−k) e valor crítico t(G−1).
- **Duas vias:** Cameron–Gelbach–Miller (CNPJ, produto), com correção de autovalores negativos.
- **WCR com pesos de Webb:** restrito sob H0: β = 0 e escrito em somas por cluster. Com s_g = Σ_{i∈g} x̃ᵢ ε̂ᵢ^r e
  q_g = Σ_{i∈g} x̃ᵢ², cada réplica é β* = Σ_g w_g s_g / Σ q, e o resíduo por cluster é w_g s_g − β* q_g.
- O IC WCU é percentil-t.
- **Contribuição do órgão g:** Σ_{i∈g} x̃ᵢ² / Σ x̃². O número efetivo de órgãos é 1/Σ(contribuição²).

## 4. Regime e eventos

- **Fração AF da UASG no trimestre:** calculada com **todas** as compras A/AF da UASG na fonte. D_{u,t} = 1 se a fração
  for ≥ 0,5.
- **Troca:** F_u = 1º trimestre observado com D ≠ D inicial. Exige D_{F−1} observado igual ao inicial e D_F, D_{F+1}
  observados no novo regime.
- **Regras:**
  - irregular: a 1ª mudança não persiste;
  - sem pré: F−1 não observado;
  - as duas situações saem do estudo de eventos, como tratadas e como controles.

## 5. dCDH (DID_l)

**Painel:** Y_{u,t} é a média de Y_i dos itens da UASG no trimestre (estimando por item, peso N_{u,t} = itens), ou a
média das médias por compra (estimando por compra, peso = compras).

**Efeito para cada troca u e l = 1..L:**

DID_{u,l} = (Y_{u,F−1+l} − Y_{u,F−1}) − Σ_{v∈C} N_{v,F−1+l} (Y_{v,F−1+l} − Y_{v,F−1}) / Σ_{v∈C} N_{v,F−1+l}

- O grupo de controle C tem as UASGs válidas com o mesmo regime inicial, F_v > F−1+l (ou que nunca trocam), Y observado
  em F−1 e em F−1+l, e |C| ≥ 5.
- **Placebo l = −k:** a mesma fórmula com Y_{u,F−1−k}, e o mesmo grupo de controle do efeito k (F_v > F−1+k).
- **Agregação:** DID_l = Σ_u w_u S_u DID_{u,l} / Σ_u w_u.
  - S_u = +1 na adoção e −1 no abandono: a estimativa é sempre "efeito do AF".
  - w_u = N_{u,F−1+l} (por item), ou 1 (peso igual por evento).
- **Média dos efeitos:** soma de l = 1..L ponderada por Σ w.
- **Simetria:** adoção − abandono.
- **Inferência:** bootstrap por CNPJ (reamostragem com reposição dos órgãos). As multiplicidades entram como pesos em
  tratados e controles. Saem EP, IC normal e percentil, valor-p normal e DMD com 80% de poder (2,80·EP).
- A covariância conjunta de placebos e efeitos vem dos mesmos draws.

## 6. BJS

- **Subconjunto:** UASGs sempre em A e adotantes A→AF que não voltam a A depois de F. Nesse subconjunto o tratamento é
  absorvente, como o BJS exige.
- **Estimação:** Y_{u,t} = α_u + λ_t é ajustado só nas células não tratadas, com pesos N. Daí τ_{u,t} = Y − Ŷ(0) nas
  células tratadas, e τ_e é a média ponderada por tempo de evento.

## 7. HonestDiD

- β = (placebos l = −L..−1, efeitos l = 1..L) e Σ = covariância dos draws da própria especificação.
- **Alvo:** média simples dos efeitos pós.
- **Δ^RM:** M̄ ∈ {0; 0,5; 1; 1,5; 2}.
- **Δ^SD:** M ∈ {0; 0,5; 1; 2} lp, só com ≥ 2 pré-períodos.
- Execução: R, `HonestDiD` (`honestdid.R`).

## 8. Secundários e seleção

- **Desconto:** 100(1 − P/E), com E > 0, orçamento não sigiloso e desconto em [−100, 99].
- **Homologação, fracasso e deserção:** 100 × indicador, sobre os itens **decididos** (exclui "Em andamento") dos produtos
  da cesta, em A/AF e Menor preço, com o mesmo denominador nos três.
- Os três são estimados com E3 e com dCDH, como os preços. A taxa de homologação também entra no balanço do §10.

## 9. Testes automatizados (`testes/`)

**`test_metodos.py`:**
- referências contra força bruta (14 variantes);
- exclusão total da UASG focal (preços +50 log não mexem na referência);
- mínimos e amostra comum;
- transformação exata;
- regras de evento (troca, irregular, sem pré, nunca, volta);
- adoção × abandono com efeitos conhecidos (10 e 4) e placebo nulo;
- controles sem observações futuras (Y dos controles depois de F−1+l não mexe em DID_l);
- BJS no subconjunto absorvente;
- bootstrap reprodutível;
- FE igual à regressão com dummies;
- CR1 igual à fórmula manual;
- duas vias e WCR reprodutível;
- singletons e Holm.

**`test_integracao.py`** (mundo sintético com τ = −5 lp, pipeline completo):
- fontes inalteradas;
- funil e chaves;
- eventos identificados;
- efeito recuperado (dCDH e FE);
- reprodução byte a byte;
- amostra principal vazia sem aprovação e ativada com aprovação.
