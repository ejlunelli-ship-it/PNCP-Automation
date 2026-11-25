# Metodologia

## Dados

**Banco** `dados/pncp_v2.db`, aberto somente para leitura (URI `mode=ro` e `PRAGMA query_only`).
- A impressão digital (tamanho, mtime, contador de alterações, SHA-256 do início e do fim) é igual à registrada pelo
  estudo original e à da cópia em `D:/pncp_v2.db`.
- A atividade institucional foi agregada de 325.751 compras A/AF e 6,3 milhões de itens (`registro_principal = 1`) e
  está gravada em `D:/risk_set_matching_s1_trabalho/atividade.pkl.gz`.

**Cesta S1:** 3.065 produtos `AUTO_VALIDADO_CATALOGO`.
- A lista foi conferida contra o congelamento da rodada `efeito_modos_cesta_auto_S1_20261125`.
- A amostra da rodada S1 tem 708.964 itens, 74.167 compras e 4.141 UASGs. Nenhum produto dela fica fora de S1, e
  nenhum é de S2.
- A validação S1 é de catálogo. Não é conferência documental de cada item (S4 tem 36 itens).

**Índice:** `Y = 100 [ln P − média ln P das outras UASGs na célula produto × trimestre]`.
- É a referência A1 leave-one-UASG-out já calculada na rodada S1, com as regras do estudo original: mínimo de 5 itens
  de 3 outras UASGs e |Y| ≤ 100·ln 10.
- Nada foi recalculado nem alterado.
- Alternativas:
  - A1 da cesta candidata original;
  - EST_A1 original, com UASGs estáveis no período todo;
  - A1 só com UASGs comparadoras de regime local estável (inequívoco em t e igual ao de t−1).

**Agregação:** item → compra (pesos iguais) → UASG × trimestre (pesos iguais por compra) → evento (peso igual). O
desfecho é o índice médio das compras observadas. **Não é uma cesta fixa de bens.**

## Isolamento entre desenho e estimação

O painel guarda todos os trimestres, mas a Fase I só o acessa por `PainelPre(t0)`, que copia as colunas t < t0 e
levanta erro em qualquer acesso a t ≥ t0. A única informação contemporânea liberada é o regime de modo em t0.

Os testes 07, 08, 25 e 38 alteram os preços pós-t0 e os de t0−2/t0−1 e conferem que os pares não mudam.

## Estimador

τ_{e,h} = (Y_{u,t0+h} − Y_{u,t0−1}) − Σ_v w_ev (Y_{v,t0+h} − Y_{v,t0−1}).
- No abandono, multiplica-se por −1 para a escala AF − A. O sinal original também é reportado.
- O agregado é Σ a_e τ_e / Σ a_e, com a_e = 1 no principal.

**Variância condicional aos pares:** τ̂ = Σ_r c_r z_r.
- Resíduo de cada linha: o desvio em relação à média dos controles da célula (direção × t0 × h).
- Escore de cada CNPJ: soma de todas as linhas do órgão, como tratada e como controle.
- CR1 com t(G−1); bootstrap selvagem por CNPJ (pesos de Webb, nulidade imposta).
- Não refaz o pareamento (Abadie e Imbens, 2008) e não captura a incerteza da etapa de pareamento.

## Limitações do desenho (registradas antes da Fase II)

Ver `resultados/diagnostico_desenho.json`.
- Só 52,6% dos UASG-trimestres com compras A/AF têm índice S1, e 10,4% dos UASG-trimestres são mistos.
- A exigência de histórico de modo limpo e de preços em t0−1, t0−2 e em 2 trimestres de formação deixa 9 dos 309
  eventos da janela.
- O suporte comum e o balanceamento deixam 4 eventos, todos adoções.
