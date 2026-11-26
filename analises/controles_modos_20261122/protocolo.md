# Protocolo — orçamento sigiloso e material × serviço nos três modos (22/11/2026)

Escrito antes das estimativas. Pergunta: o orçamento sigiloso e o tipo de objeto (material ou serviço)
estão associados ao desconto sobre o preço de referência e ao preço homologado em relação à mediana de
itens comparáveis, em cada modo de disputa (Aberto, Aberto-Fechado, Fechado-Aberto)? Esse efeito difere
entre os modos? As diferenças entre os modos mudam quando esses controles entram?

O número de licitantes ficou de fora: não está no `pncp.db` nem em nenhuma API pública testada (ver o
relatório). Decisão do usuário em 22/11/2026.

## Amostra

- `dados/pncp.db` (snapshot de 10/11/2026), somente leitura.
- `fonte = 'dados_abertos'` (Compras.gov.br): é a única fonte com código de catálogo, necessário para a
  mediana de comparáveis; nas outras plataformas a marcação de sigilo e a situação do item não são
  confiáveis (docs/03 §3.4 item 15; docs/05 pendência 11).
- Pregão Eletrônico, modos Aberto (A), Aberto-Fechado (AF) e Fechado-Aberto (FA), `registro_principal = 1`.
- Publicação de 2023-01 a 2026-06 (mesmo recorte da análise de desfecho; meses recentes fora por
  apuração incompleta).
- Item homologado (`situacao_item = 'Homologado'`), critério Menor preço, valor unitário homologado
  `P > 0`. A sigilosidade é a do item (`orcamento_sigiloso`); valor ausente fica fora.

## Desfechos

1. **Desconto sobre o preço de referência:** `D = 100 × (1 − P/R)`, com `R` = valor unitário estimado.
   Exige `R > 0` e `D` entre −100 e 99 (o mesmo filtro de `analise_itens.elegivel`), **também nos
   sigilosos**: o estimado positivo de um item sigiloso é o do snapshot e não prova que o valor era
   público na disputa. A cobertura de `R` por modo e sigilo é reportada.
2. **Preço em relação à mediana de comparáveis:** `L = 100 × ln(P/M)` (log-pontos; −10 ≈ 9,5% abaixo
   da mediana). `M` = mediana das medianas por pregão do mesmo **produto** (código de catálogo + unidade
   de medida) × **ano de publicação** × **UF** do órgão, **excluindo todos os pregões do próprio CNPJ**,
   com no mínimo 5 pregões de pelo menos 2 outros CNPJs. Os doadores são todos os itens da amostra
   (os três modos, sigilosos ou não), para que a referência seja comum. Itens sem `M` ficam fora deste
   desfecho. É uma referência de compras públicas, não de mercado.

## Controles em teste

- `sigiloso` (0/1, do item).
- `servico` (0/1: `material_ou_servico = 'S'`).

## Especificações (modelo linear, item como observação)

| Código | Efeitos fixos | Covariáveis adicionais |
|---|---|---|
| E1 | mês de publicação | — |
| **E2 (principal)** | mês + UASG | SRP, log da quantidade, log do nº de itens da compra, exclusiva ME/EPP, cota ME/EPP |
| E3 | E2 + produto × ano | as de E2 (`servico` não é identificado: é constante no produto) |

Para cada desfecho e especificação, três modelos:

- **(a) Efeito em cada modo:** o modelo estimado separadamente em A, AF e FA, com `sigiloso` e
  `servico` juntos.
- **(b) Diferença do efeito entre modos:** os três modos juntos, com indicadores de AF e FA,
  `sigiloso`, `servico` e as interações `sigiloso × AF`, `sigiloso × FA`, `servico × AF`,
  `servico × FA`. As interações dizem se o efeito no AF (ou FA) difere do efeito no Aberto.
- **(c) Diferença entre modos com e sem os controles:** os três modos juntos, coeficientes de AF e FA
  sem `sigiloso` e `servico` e com eles (sem interações). Descritivo: mostra quanto da diferença entre
  modos passa pelos dois controles.

## Inferência

Erro-padrão agrupado em duas vias, por CNPJ do órgão e por código de catálogo (Cameron, Gelbach e
Miller); t com graus de liberdade = menor número de grupos − 1. Observações sozinhas em seu grupo de
efeito fixo são removidas antes de estimar.

**Famílias para Holm (α = 5%), todas em E2:**

- **F1, efeito em cada modo:** 2 desfechos × 2 controles × 3 modos = 12 testes.
- **F2, diferença do efeito entre modos:** 2 desfechos × 2 controles × 2 interações (AF, FA) = 8 testes.

E1 e E3 são sensibilidades, com p bruto. Sensibilidade adicional: E2 com o desfecho winsorizado em
1% e 99% (dentro da amostra de cada desfecho).

## Leitura

Associações, não efeitos causais: o órgão escolhe o sigilo e o modo, e o serviço difere do material em
muitas dimensões. Não significância não prova ausência de efeito. Com milhões de itens, efeitos pequenos
podem ser significativos: o tamanho em p.p. ou log-pontos importa mais que o p.
