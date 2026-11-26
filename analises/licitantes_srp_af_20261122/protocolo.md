# Protocolo — número de licitantes no Aberto-Fechado: SRP × não SRP (22/11/2026)

Escrito antes das estimativas. Pergunta: no Aberto-Fechado, o número de licitantes por item difere entre
compras com e sem registro de preços (SRP)?

## Amostra

- **Licitantes:** `quantidade_fornecedores` (propostas do item no termo de homologação) dos bancos de
  extração desta máquina, somente leitura: `aberto-fechado_2024-11_a_2024-12.db` (parser 1.9.1),
  `junho2025.db`, `aberto-fechado_2025-12_a_2026-07.db`, `aberto-fechado_2026-03_04_08.db` e
  `aberto-fechado_2026-09_a_2026-10.db` (1.8.0). Meses: 2024-11, 2024-12, 2025-06, 2025-07, 2025-12,
  2026-01 e 2026-03 a 2026-10 (pasta de download = mês do resultado). Não são todos os meses: a base
  consolidada está na outra máquina.
- `status_extracao = 'OK'`, `quantidade_fornecedores ≥ 1`. Item repetido entre bancos (mesma UASG,
  compra e item) entra uma vez.
- **SRP e demais variáveis:** `dados/pncp.db`, somente leitura. Ligação pelo `id_compra` (parte final do
  nome da pasta) + número do item, com `registro_principal = 1`, só `fonte = 'dados_abertos'` e
  `modo_disputa = 'Aberto-Fechado'`. `id_compra` que aponta para mais de uma compra fica fora.

## Desfechos

1. `licitantes` (número de propostas do item).
2. `ln(licitantes)`, em log-pontos (×100), menos sensível às caudas.

Contraste: SRP − não SRP, modelo linear.

## Especificações

| Código | Efeitos fixos | Controles |
|---|---|---|
| S1 | — | — (diferença bruta) |
| S2 | mês de publicação × material/serviço | orçamento sigiloso, log do valor estimado total do item, log do nº de itens da compra, exclusiva ME/EPP, cota ME/EPP |
| **S3 (principal)** | S2 + UASG | iguais a S2 |
| S4 | UASG × código de catálogo × ano + mês × material/serviço | iguais a S2; só itens com código de catálogo |

Sensibilidade: S3 em nível de compra (média de licitantes por item da compra; erro-padrão por CNPJ).

## Inferência

Erro-padrão agrupado em duas vias, por CNPJ do órgão e por código de catálogo (item sem código: grupo da
compra); t com graus de liberdade = menor número de grupos − 1. Observações sozinhas em seu grupo de
efeito fixo são removidas. **Holm sobre os 2 testes principais** (S3 × 2 desfechos), α = 5%; S1, S2, S4 e
a versão por compra são sensibilidades, com p bruto.

## Leitura

Associação, não efeito causal: o órgão escolhe o SRP e o SRP costuma ter objetos diferentes. A amostra é
a das compras com termo de homologação baixado, que não representa necessariamente todo o Aberto-Fechado.
