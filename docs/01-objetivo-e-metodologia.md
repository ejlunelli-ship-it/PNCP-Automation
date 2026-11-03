# 1. Objetivo e metodologia

## Pergunta de pesquisa

No Pregão Eletrônico (Lei 14.133/2021, IN SEGES 73/2022), o **modo de disputa** muda o desconto
obtido pela administração?

- **Aberto**: só lances públicos e sucessivos. A sessão dura 10 min e é prorrogada
  automaticamente (2 min) sempre que há lance nos últimos 2 minutos.
- **Aberto-Fechado** (Aberto/Fechado no PDF): primeiro há uma etapa aberta (15 min mais um período
  aleatório de até 10 min). Depois vem a **etapa fechada**: o autor do melhor lance e os que estão
  até 10% acima dele mandam **um lance único e sigiloso** em até 5 min.

## Comparações desejadas

1. **Aberto vs Aberto-Fechado, desconto final** (resultado do item):
   - a) **sem matching**: desconto médio/mediano de cada modo em toda a base;
   - b) **com matching exato UASG × item** (mesma unidade compradora comprando o mesmo código de
     catálogo nos dois modos), para controlar o órgão e o produto.
2. **Por etapa** (só com o PDF):
   - desconto do **modo aberto**: melhor lance do pregão Aberto, e melhor lance da etapa aberta
     do Aberto-Fechado;
   - desconto do **modo fechado**: melhor lance da etapa fechada do Aberto-Fechado;
   - **ganho da etapa fechada** = desconto(fechado) − desconto(aberto) dentro do mesmo item AF;
   - as mesmas versões com e sem matching UASG × item.

## Definições

- `desconto = 1 − valor_unitário / valor_unitário_estimado`, em % (positivo = abaixo do estimado).
- **Desconto final** (API): `valorUnitarioResultado` sobre `valorUnitarioEstimado`, do endpoint de
  itens. Não diz nada sobre as etapas.
- **Desconto por etapa** (PDF): `melhor_lance_modo_aberto` e `melhor_lance_modo_fechado` sobre
  `valor_estimado`, extraídos pelo `extrator_homologacao`.
  - O melhor lance da etapa é o mais vantajoso registrado nela, pelo critério do item: menor valor
    em Menor Preço, maior em Maior Desconto. Conta **mesmo que o fornecedor seja desclassificado
    depois**.
  - `melhor_lance_modo_aberto` inclui as propostas iniciais, que abrem a etapa aberta.
  - Lances de desempate (art. 60, ME/EPP) ficam à parte, em `melhor_lance_desempate`.
  - Lances marcados como excluídos (`*`) não contam.
- **Lance aceito**: vem da situação do item; usa o valor negociado quando houver.

## Por que ler o PDF

As APIs (Dados Abertos e PNCP) só dão o **valor estimado** e o **valor homologado** de cada item.
A tabela de lances, e com ela a separação entre etapa aberta e fechada, só existe nos relatórios
do Compras.gov.br ("Todos os relatórios e termos" de cada compra). A etapa de cada lance é deduzida
pelas janelas de tempo anunciadas no chat do item. Ver [04-formato-dos-relatorios.md](04-formato-dos-relatorios.md).

## Filtros de qualidade (análise com dados da API)

`matching_desconto.py` exclui:
- itens sem resultado;
- itens com orçamento sigiloso;
- itens com valores ≤ 0;
- itens com desconto fora de −100% a 99%.

`matching_normalizado.py` exclui razões fora de 0,1×–10× a mediana nacional do item no ano.

## Estratégia estatística (já implementada em `matching_*.py`)

- **Célula de pareamento**: UASG × `codItemCatalogo`. As variantes acrescentam ano, classe ou
  unidade de medida. Só entram células com itens nos dois modos.
- Por célula: média do desconto em cada modo; teste t pareado e Wilcoxon sobre a diferença AF − A.
- Regressão com **efeito fixo de célula** (within) e erro-padrão agrupado por UASG; robustez
  separando material e serviço; versão ponderada pelo tamanho da célula (média harmônica dos n).

| Script | Variável dependente | Pareamento |
|---|---|---|
| `matching_desconto.py` | desconto sobre o estimado, todos os pregões | UASG × item |
| `matching_homologado.py` | log do unitário homologado (R$ e desconto), só homologados | UASG × item × ano (+ variantes) |
| `matching_normalizado.py` | log(unitário ÷ mediana nacional do item no ano) | UASG × item × ano, UASG × ano × classe, UASG × ano |

**O que falta**: aplicar a mesma estratégia às variáveis por etapa vindas do PDF (base
`homologacoes.db`, tabela `itens`). Isso exige juntar a base do extrator à base de itens da API
pela chave `uasg` + `numero_compra` + `item`, que identifica o item. Ver
[05-decisoes-e-pendencias.md](05-decisoes-e-pendencias.md).

## Cuidados metodológicos já identificados

- **Itens em grupo** (lote): o vencedor é decidido pelo **total do grupo**, não por item. Um item
  pode ser adjudicado a quem tem um valor pior nele. Exemplo: Fortaleza 90119/2025, item 6 — a
  ALPHA ganhou com 0,99 contra 0,88 da MULTIPLA. Marcar esses itens com uma coluna `grupo` e
  analisá-los à parte ou com controle.
- Na etapa fechada de um grupo, o convocado manda um lance para o grupo, composto de valores por
  item. Os itens em que ele não muda o valor ficam com o último lance aberto, e esses **não
  aparecem** como lances novos na tabela. Ver a regra de "melhor lance fechado" em
  [05](05-decisoes-e-pendencias.md).
- Viés de seleção da amostra de PDFs: só há PDF para compras homologadas. Os PDFs vindos do PNCP
  dependem do órgão publicá-los (ex.: Fortaleza). Comparar a amostra com PDF contra a base
  nacional.
