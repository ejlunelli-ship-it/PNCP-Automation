# Protocolo — desfecho dos itens e compras por modo de disputa (21/11/2026)

Escrito antes das estimativas. Pergunta: a frequência de itens fracassados, desertos e não homologados,
e de compras inteiramente fracassadas/desertas, difere entre Aberto (A), Aberto-Fechado (AF) e
Fechado-Aberto (FA)?

## Amostra

- `dados/pncp.db` (snapshot de 10/11/2026), somente leitura.
- `fonte = 'dados_abertos'` (Compras.gov.br). A fonte `pncp` fica fora: nela a situação do item quase
  nunca é atualizada (40–65% dos itens de 2023–2024 seguem "Em andamento").
- Pregão Eletrônico, modos A, AF e FA, `registro_principal = 1`.
- Publicação de 2023-01 a 2026-06. Os meses de 2026-07 a 2026-10 ficam fora porque ainda estão em apuração.
- **Itens:** só os decididos (Homologado, Fracassado ou Deserto). Cancelados e em andamento ficam fora.
- **Compras:** as que têm ao menos um item decidido.

## Desfechos (0/1, estimados em pontos percentuais)

| Código | Nível | Definição |
|---|---|---|
| `fracassado` | item | situação = Fracassado |
| `deserto` | item | situação = Deserto |
| `nao_homologado` | item | Fracassado ou Deserto |
| `compra_sem_hom` | compra | nenhum item decidido foi homologado (todos fracassados/desertos) |
| `compra_toda_hom` | compra | todos os itens decididos foram homologados |

## Contrastes

AF − A e FA − A (A é a referência), por modelo linear de probabilidade.

## Especificações

| Código | Efeitos fixos | Controles |
|---|---|---|
| E1 | nenhum | nenhum (diferença bruta de proporções) |
| E2 | mês × material/serviço (item); mês (compra) | SRP, orçamento sigiloso, Maior desconto, benefício ME/EPP (exclusiva, cota), log do valor estimado do item, log do nº de itens da compra; na compra: SRP, log do valor estimado total, log do nº de itens decididos, parcela de itens de material, parcela sigilosa, parcela exclusiva ME/EPP |
| **E3 (principal)** | E2 + UASG | iguais a E2 |
| E4 (pareamento, só itens) | UASG × CATMAT × ano + mês × material/serviço | iguais a E2; itens sem código de catálogo ficam fora |

Observações em grupos de efeito fixo com uma só observação são removidas antes de estimar. O valor
estimado ausente ou ≤ 0 entra como 0 no log, com indicador de ausência.

## Inferência

- Itens: erro-padrão agrupado em duas vias, por CNPJ do órgão e por CATMAT (Cameron, Gelbach e Miller).
  Um item sem CATMAT forma um grupo com os demais itens sem CATMAT da mesma compra.
- Compras: erro-padrão agrupado por CNPJ do órgão.
- t bilateral com graus de liberdade = menor número de grupos − 1.
- **Família principal para Holm:** E3 × 5 desfechos × 2 contrastes = 10 testes, α = 5%.
  E1, E2 e E4 são sensibilidades, com p bruto.

## Leitura

Diferenças associativas, não efeito causal do modo. A escolha do modo pode refletir o objeto e o
comprador; E3 e E4 reduzem, mas não eliminam, esse viés. Não significância não prova equivalência.
