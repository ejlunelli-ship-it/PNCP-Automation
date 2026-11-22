# Protocolo — uso dos modos Aberto-Fechado e Fechado-Aberto (21/11/2026)

Escrito antes das estimativas. Duas perguntas:

1. **Tendência:** o uso do Aberto-Fechado (AF) e do Fechado-Aberto (FA) aumenta ou diminui com o tempo?
2. **Associação:** o uso desses modos está associado à unidade compradora, à categoria do objeto, à
   plataforma, à esfera, à região ou a características da compra?

## Amostra

- `dados/pncp.db` (snapshot de 10/11/2026), somente leitura.
- Pregão Eletrônico, modos Aberto (A), AF e FA. Publicação de 2022-11 a 2026-10.
- **Unidade de análise: a compra.** O modo é escolhido por compra; contar itens daria mais peso às
  compras grandes.
- As duas fontes: `dados_abertos` (Compras.gov.br) e `pncp` (outras plataformas). O modo é informado na
  publicação nas duas, então os meses recentes valem (ao contrário da análise de desfecho).
- **Unidade compradora:** UASG no Compras.gov.br; CNPJ do órgão + `codigo_unidade` nas outras
  plataformas.
- **Categoria** (só Compras.gov.br): classe do CATMAT nos itens de material, grupo do CATSER nos de
  serviço. A categoria da compra é a que tem mais itens (empate: menor código).

## Variáveis da compra

SRP; log do valor estimado (soma de quantidade × valor unitário estimado dos itens; ausente = 0 com
indicador); log do nº de itens; parcelas de itens de material, com critério Maior desconto, com
participação exclusiva ME/EPP, com cota ME/EPP e com orçamento sigiloso; esfera (F, E, M, D, outra);
Judiciário e Legislativo (o campo `poder` vem como "N" em boa parte dos municípios, então só esses dois
são usados); região da UF; plataforma (Compras.gov.br e as 12 plataformas com mais pregões; as demais
juntas).

## Parte 1 — tendência

Desfechos: AF (0/1) e FA (0/1). Tendência `t` = meses desde 2022-11 ÷ 12, então o coeficiente é
**p.p. por ano**. Modelo linear de probabilidade.

| Código | Efeitos fixos | Controles | Pergunta |
|---|---|---|---|
| T1 | mês do ano (sazonalidade) | — | A parcela muda com o tempo? |
| **T2 (principal)** | mês do ano + unidade compradora | — | A mesma unidade passa a usar mais (ou menos) o modo? |
| T3 | T2 + plataforma | variáveis da compra | A mudança dentro da unidade continua com compras de perfil parecido? |

- Estimado por fonte (Compras.gov.br; outras plataformas) e com as duas juntas (sensibilidade).
- Não linearidade: T2 com indicadores de semestre (ref. 2023-S1) no lugar de `t`, descritivo.
- **Decomposição** da mudança da parcela de AF e FA entre 2023 e 2025 (anos completos), por fonte:
  dentro das unidades presentes nos dois anos (peso de 2023), entre unidades (mudança de peso), termo
  cruzado, entrada e saída de unidades.
- **Família para Holm:** T2 × {AF, FA} × {Compras.gov.br, outras} = 4 testes, α = 5%.

## Parte 2 — associação

**A1. Perfil de quem usa (todas as fontes).** AF e FA contra esfera (ref. municipal), Judiciário,
Legislativo, região (ref. Sudeste), plataforma (ref. Compras.gov.br) e variáveis da compra, com efeito
fixo de mês de publicação. Holm sobre todos os coeficientes de cada modelo.

**A2. Dentro da unidade.** AF e FA contra as variáveis da compra, com efeitos fixos de unidade e de mês,
por fonte. Pergunta: quando a mesma unidade escolhe entre os modos, que tipo de compra vai para AF/FA?
Holm sobre os coeficientes de cada modelo.

**A3. Quanto cada dimensão explica.** R² (e R² ajustado pelo nº de efeitos fixos) de AF e FA com
efeitos fixos de: mês; unidade; órgão (CNPJ); categoria; plataforma; e combinações. Compras.gov.br em
nível de compra (com categoria). Nas outras plataformas: mês, unidade, órgão e plataforma. Em nível de
item no Compras.gov.br (2023-01 a 2026-06, base da análise de desfecho): UASG, CATMAT/CATSER e
UASG × CATMAT, para ver se o item explica algo além da unidade.

**A4. Categorias associadas, dentro da unidade.** Compras.gov.br, nível de compra: AF (e FA) contra
efeitos fixos de unidade, mês e categoria. Efeito de cada categoria = média de y − α_unidade − δ_mês
nas compras da categoria, menos a média geral; erro-padrão agrupado por CNPJ (aproximação que ignora o
erro dos efeitos fixos estimados). Categorias elegíveis: ≥ 300 compras em ≥ 30 unidades. Holm sobre as
elegíveis. Rótulo da categoria: as descrições de item mais frequentes nela.

**A5. Concentração nas unidades.** Unidades com ≥ 20 compras no período: distribuição da parcela de AF
(e FA); parcela que usa quase só A (< 5% AF), quase só AF (> 95%) e misto; parcela das compras FA feita
pelas 10 e pelas 50 unidades que mais usam FA. Lista das unidades e plataformas que mais usam cada modo.

## Inferência

Erro-padrão agrupado por CNPJ do órgão; t com graus de liberdade = nº de órgãos − 1. Observações
sozinhas em seu grupo de efeito fixo são removidas antes de estimar.

## Leitura

Associações, não efeitos causais. Não significância não prova ausência de associação. Com centenas de
milhares de compras, efeitos pequenos podem ser significativos: o tamanho (p.p., R²) importa mais que
o p.
