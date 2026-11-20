# 4. Formato dos relatórios (PDF)

## 4.1 Termo de homologação / julgamento do Compras.gov.br (suportado)

Um PDF por item (no zip e, quando publicado, no PNCP). Estrutura:

1. **Cabeçalho da compra**:
   - `TERMO DE HOMOLOGAÇÃO` ou `TERMO DE JULGAMENTO`;
   - `UASG nnnnnn - nome` e `PREGÃO nnnnn/aaaa`;
   - fundamentação, característica (SISPP/SRP), critério de julgamento e **`Modo de disputa:`**
     (`Aberto/Fechado`, `Aberto`, `Fechado/Aberto`), objeto e datas.
2. `Mensagens do chat da compra` e `Eventos da compra`.
3. Para cada item, um bloco **`Item N - descrição`**, com:
   - `Quantidade:`, `Valor estimado:` (unitário e total), `Situação:` e critério de julgamento;
   - `Propostas do Item N`: fornecedor, CNPJ, valor da proposta, situação;
   - `Lances do Item N`: **tabela única** (data/hora, CNPJ, valor), **sem indicação de etapa**;
     `*` = lance excluído;
   - `Mensagens do chat do Item N`, onde ficam os marcos das etapas;
   - `Eventos do Item N`, alternativa ao chat para os marcos;
   - `Fase Recursal do Item` (ignorada).
4. Cada página repete o cabeçalho `UASG`/`PREGÃO` e o rodapé `N de M` + data de emissão;
   `texto.linhas_limpas` remove os dois.

### Marcos das etapas no chat do item (`etapas.py`)

| Marco | Texto |
|---|---|
| Abertura | `O item N foi aberto.` |
| Início da fechada | `A etapa fechada foi iniciada/reiniciada para o item N. …` |
| Fim da fechada | `A etapa fechada do item N foi encerrada. Os seguintes lances foram registrados pelos fornecedores convocados: R$ … e R$ …` |
| Desempate art. 60 / ME/EPP | mensagens próprias (lances vão para `melhor_lance_desempate`) |

**Regra**:
- lance antes do início da etapa fechada → etapa aberta;
- lance dentro da janela → etapa fechada.

A lista de valores da mensagem de encerramento serve **só para conferência** e para desempatar um
lance que caiu no mesmo segundo da troca de etapa. Ela nunca conta como lance.

### Situação do item → `resultado`

`HOMOLOGADO`, `ADJUDICADO`, `FRACASSADO`, `DESERTO`, `REVOGADO`, `ANULADO`, `CANCELADO`,
`SUSPENSO`, `EM ANDAMENTO`. Uma situação desconhecida vira `NÃO IDENTIFICADO`.
"Nenhum lance foi registrado para o Item N." → os campos de lance ficam vazios.

### Layout antigo (PDFs emitidos até fev/2025) — suportado desde o parser 1.9.0

Os termos emitidos até fev/2025 (data de emissão no rodapé) têm as mesmas seções e rótulos, mas outro
formato. Dos 96.758 PDFs de 2023, 95.796 estão nesse layout (emitidos de nov/2023 a fev/2025, sobretudo em
nov-dez/2023 e mai-jun/2024) e 962 no atual (emitidos de fev/2025 a out/2026); a troca foi em fev/2025 (5 PDFs
antigos e 3 atuais emitidos nesse mês). Diferenças, em `extrator_homologacao/layouts.py`:

| | Atual | Antigo |
|---|---|---|
| Ordem interna do texto | a de leitura | embaralhada: no bloco do item, valores antes dos rótulos e o título `Item N - …` no fim da página; a continuação de uma tabela (ex.: chat do item) depois da tabela seguinte (eventos) |
| Data/hora no chat, eventos e lances do item | `28/07/2023 às 11:06:42` | `28/07/2023 11:06:42` (o chat e os eventos **da compra** têm "às") |
| Valores | `R$ 5,5100 (unitário)` / `R$ 275,5000 (total)` | só `R$ 5,5100`, sem total; Maior Desconto igual, `49,00% (R$ 2,1828)` |
| Propostas | `Benefício Me/Epp: …` | `Porte MeEpp/Equiparada: Sim (D)`, depois `Marca/Fabricante:` e `Modelo/versão:` |
| Título da tabela de lances | `Lances do Item 72` | `Lances do Item  72` (dois espaços) |
| Critério do item | `Critério de julgamento:` no bloco do item | no termo de homologação, só o da compra (`Menor Preço / Maior Desconto`); o termo de julgamento traz o do item |
| Parágrafo de situação | `Adjudicado e Homologado por …, melhor lance: R$ X (unitário) / R$ Y (total)` | `Adjucado e Homologado por …, melhor lance: R$ X` |
| Mensagem que não cabe na página | — | continua na seguinte como mensagem nova, com o mesmo autor e a mesma data/hora |
| Eventos da etapa fechada | `Início da etapa fechada.` | `Convocados os fornecedores para a 1º etapa fechada que apresentaram lance entre …` |

Leitura no parser 1.9.0:
- **detecção** (`layouts.detectar`, no texto na ordem interna): antigo se uma tabela de eventos ou de lances
  começa com data/hora sem "às", ou se há `Porte MeEpp/Equiparada:`. Nos PDFs de 2023, a detecção bate com a
  data de emissão: os emitidos até jan/2025 saem todos antigos e os de mar/2025 em diante, todos atuais;
- **texto na ordem visual** (`texto.paginas_em_ordem_visual`): linhas do PDF agrupadas em células (linhas
  encostadas que se sobrepõem na horizontal) e células em faixas (as que se sobrepõem na vertical); faixas de cima
  para baixo, células da esquerda para a direita. As palavras de um parágrafo justificado, que o PDF posiciona uma a
  uma, voltam a formar a linha. Depois, data/hora ganha o "às" e os espaços duplos somem (`layouts.normalizar`), e o
  resto da leitura é a do layout atual;
- valores sem `(unitário)` são lidos como unitários; `valor_estimado_total` = estimado × quantidade (anotado em
  `fontes_extracao`);
- **critério do item** ausente: com `Menor Preço / Maior Desconto` na compra, `Maior Desconto` se as propostas e os
  lances vêm em `P% (R$ V)`, `Menor Preço` se vêm só em R$; sem valores (item deserto), fica vazio, com aviso;
- a continuação de uma mensagem ou evento na página seguinte (mesma data/hora, texto anterior sem ponto final ou
  continuação em minúscula) é juntada ao registro anterior;
- na comparação das janelas da etapa fechada entre chat e eventos, janelas a até 2 s contam como contíguas (o chat
  reinicia a fechada 1 s depois de encerrá-la e o evento de encerramento às vezes fica 1 s depois da mensagem);
- uma mensagem do chat como `Item 67 - Fracassado.` não abre bloco de item (há data/hora antes de `Quantidade:`).

Conferência numa amostra de 3.000 PDFs de 2023: 2.963 dos 2.964 no layout antigo saem OK (o restante, com o último
evento de adjudicação de outro fornecedor, é REVISAR legítimo); o melhor lance aberto gravado bate com o primeiro
valor da mensagem "A etapa fechada foi iniciada … lance entre R$ X e …" em 470 de 471 itens (no layout atual, 19 de
20); nos 962 PDFs do layout atual das pastas de 2023, nenhum resultado mudou, exceto 4 itens REVISAR que passaram a
OK pela mensagem de fim do desempate ME/EPP sem "Me/Epp" (`O item 7 teve o 1º desempate encerrado às … O tempo
expirou…`), reconhecida desde a 1.9.0 nos dois layouts.

## 4.2 Itens em grupo (lote) — suportado desde o parser 1.6.0

Encontrado em Fortaleza 90119/2025, no arquivo "TERMO DE HOMOLOGAÇÃO-grupo1", de 20 páginas, que
cobre os itens 1 a 6.

```
Grupo 1
  Valor estimado: R$ 56.789,55 (total)   Situação: Adjudicado e Homologado
  Propostas do Grupo G1
  Mensagens do chat do Grupo G1     <- marcos da etapa fechada ficam AQUI ("item G1")
  Eventos do Grupo G1
Item 1 do Grupo G1 - Cateter aspiração traqueal
  Quantidade / Valor estimado (unitário) / Situação
  Propostas do Item 1
  Lances do Item 1                  <- lances POR ITEM, valores unitários
Item 2 do Grupo G1 - ...
...
Fase Recursal do Item/Grupo
```

O que muda em relação ao item comum:
1. O título é `Item N do Grupo GX - …`, e o bloco `Grupo N` vem antes dos itens.
2. A **janela da etapa fechada** está no chat do **grupo**:
   `A etapa fechada foi iniciada para o item G1…` / `A etapa fechada do item G1 foi encerrada…`.
   Cada item precisa herdá-la.
3. Os **valores do encerramento são totais do grupo**. Verificado:
   - para cada convocado, soma por item de (lance fechado do item **ou**, se ele não deu lance
     fechado naquele item, o último lance aberto) × quantidade;
   - resultado: ALPHA R$ 46.680,00 e MULTIPLA R$ 52.591,25, **exatamente** os valores do chat;
   - a conferência por grupo deve usar essa soma, não a comparação valor a valor.
4. O fornecedor aceito aparece no bloco do grupo, com o total, e **cada item repete** a informação
   com o valor unitário: `… melhor lance: R$ 0,6900 (unitário) / R$ 6.555,0000 (total)`.
5. O vencedor é definido pelo total do grupo, então um item pode ter lance aceito pior que o de
   outro fornecedor.

Lances do exemplo (janela fechada 10:23:50–10:28:51). A coluna "Melhor aberto" considera só a
tabela de lances; `melhor_lance_modo_aberto` inclui as propostas iniciais e, por isso, é menor
(0,53 no item 1, proposta da GIRASSOL, depois inabilitada):

| Item | Abertos | Melhor aberto | Fechados (na janela) |
|---|---|---|---|
| 1 | 10 | 0,74 | ALPHA 0,69 |
| 2 | 11 | 0,79 | ALPHA 0,70 |
| 3 | 10 | 0,80 | MULTIPLA 0,87 · ALPHA 0,75 |
| 4 | 12 | 0,85 | ALPHA 0,75 |
| 5 | 11 | 0,85 | ALPHA 0,78 |
| 6 | 11 | 0,92 | MULTIPLA 0,88 |

### Lances: item avulso × item em grupo

| Aspecto | Item avulso | Item em grupo |
|---|---|---|
| Lance da etapa fechada | Um lance para o item | Um lance para o grupo, composto de valores por item |
| Tabela de lances | Valores unitários do item | Valores unitários por item; um item cujo valor o convocado não mudou fica com o último lance aberto e **não ganha linha nova** |
| Marcos da etapa fechada | Chat do item | Chat do grupo (`item G1`); cada item herda a janela |
| Valores na mensagem de encerramento | Lances dos convocados, comparáveis valor a valor | Totais do grupo: soma de valor × quantidade de cada item |
| Vencedor | Melhor lance do item | Melhor total do grupo; pode ter valor pior em um item (Fortaleza 90119/2025, item 6: ALPHA 0,99 contra MULTIPLA 0,88) |

**Regra de `melhor_lance_modo_fechado`** (decidida em 2026-11-03, ver
[05](05-decisoes-e-pendencias.md)): nos dois casos, só os lances enviados na janela da etapa
fechada. O item sem lance na janela fica vazio.

Consequência para a análise: um lance na janela pode ser pior que o melhor aberto, e o item sem
lance ficaria fora de uma média calculada só com essa coluna. Por isso a view `analise_itens`
calcula `ganho_fechada` a partir de `melhor_lance_apos_fechada`, o melhor valor entre as duas
etapas: um item Aberto-Fechado sem melhora entra com ganho zero.

## 4.3 "Ata Final" do Portal de Compras Públicas — **não suportado**

Plataforma diferente, com o rodapé `validaarquivo.portaldecompraspublicas.com.br`. Aparece no PNCP
como `AtaTotal_<n>.pdf` ou "Ata Final". Seções:

- `ATA FINAL`, órgão, `Pregão Eletrônico - nnnnn/aaaa`, datas;
- `Itens Licitados` (ou `Lotes Licitados`): código, descrição, valor de referência, quantidade,
  situação;
- `Vencedores`, `Propostas Enviadas` (com a coluna `LC 123/2006`), `Validade das Propostas`;
- **`Lances Enviados`**: data/hora, valor (as propostas iniciais vêm marcadas com `(proposta)`),
  CNPJ - nome, **situação do lance** (`Válido` / `Cancelado - data`);
- `Chat`: aqui o modo aparece por texto. Exemplo: *"No modo de disputa aberto a etapa de envio de
  lances … durará dez minutos e … será prorrogada automaticamente…"*.

Exemplo: João Pessoa 08002/2025 (Aberto), 1 item, 10 propostas, 105 lances (3 cancelados),
vencedor R$ 60,00 contra referência de R$ 117,56. O modo de disputa **não está num campo
estruturado** do PDF e precisa vir da API ou do texto do chat. Ainda não temos exemplo de Ata Final
Aberto-Fechado analisado (há um de Vitória 123/2025 para estudar).
