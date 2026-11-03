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

## 4.2 Itens em grupo (lote) — **ainda não suportado**

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
1. O título é `Item N do Grupo GX - …`, que não casa com `RE_INICIO_ITEM` (`^Item (\d+) - `).
   Hoje o PDF é descartado (sem itens reconhecidos).
2. A **janela da etapa fechada** está no chat do **grupo**:
   `A etapa fechada foi iniciada para o item G1…` / `A etapa fechada do item G1 foi encerrada…`.
   Cada item precisa herdá-la.
3. Os **valores do encerramento são totais do grupo**. Verificado:
   - para cada convocado, soma por item de (lance fechado do item **ou**, se ele não deu lance
     fechado naquele item, o último lance aberto) × quantidade;
   - resultado: ALPHA R$ 46.680,00 e MULTIPLA R$ 52.591,25, **exatamente** os valores do chat;
   - a conferência por grupo deve usar essa soma, não a comparação valor a valor.
4. O fornecedor aceito e o texto "… para FORNECEDOR, CNPJ …" provavelmente estão no bloco do grupo.
   Ainda não verificado se cada item repete essa informação.
5. O vencedor é definido pelo total do grupo, então um item pode ter lance aceito pior que o de
   outro fornecedor.

Lances do exemplo (janela fechada 10:23:50–10:28:51):

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
