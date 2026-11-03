# 7. Metodologia de extração

Como os dados são obtidos e transformados, dos brutos até a base de análise. **Este documento é
atualizado sempre que algo muda**: altere a etapa afetada e acrescente uma linha ao
[histórico](#histórico-de-mudanças).

Definições de desconto e estratégia estatística: [01](01-objetivo-e-metodologia.md). Colunas do
banco: [06](06-banco-de-dados.md). Formato dos PDFs: [04](04-formato-dos-relatorios.md).

## Visão geral

```
1. Contratações (API Dados Abertos)  ─┐
2. Itens (API Dados Abertos)         ─┴─> dados/brutos/ ─> 3. Banco dados/pncp.db
                                                                   │ 4. seleção
                                                                   ▼
                5. Download dos relatórios (PNCP; depois zip manual)
                                                                   │
                                                                   ▼
                6. Extração dos PDFs ─> 7. Carga no banco (ainda não feita)
```

## 1. Coleta das contratações (`coleta_anos.py`)

- **Fonte:** API Dados Abertos do Compras.gov.br, `1_consultarContratacoes_PNCP_14133`.
- **Recorte:** `codigoModalidade = 5` (Pregão, Eletrônico e Presencial), todos os órgãos e modos.
- **Período:** de 2022-11, primeiro mês com pregões na API, até o mês corrente.
- **Corte temporal:** mês de `dataPublicacaoPncp`; a data final da API é exclusiva.
- **Duplicados:** removidos por `numeroControlePNCP`, porque `idCompra` se repete.
- **Conferência:** compara o total salvo com `totalRegistros`, com até 3 tentativas por mês.
- **Saída:** `dados/brutos/<ano>/contratacoes_pregao_<ano>-<mês>.{json,csv}`.

## 2. Coleta dos itens (`coleta_itens.py`)

- **Fonte:** `2_consultarItensContratacoes_PNCP_14133`, dia a dia pela data de inclusão.
- **Recorte:** mantém só os itens das compras coletadas na etapa 1.
- **Duplicados:** chave `numeroControlePNCPCompra` + `numeroItemPncp` + `idCompraItem`.
- **Conferência:** pelas linhas recebidas, porque `totalRegistros` conta repetições.
- **Retomada:** meses gravados são pulados, exceto o corrente; para atualizar um mês, apague o arquivo.
- **Saída:** `dados/brutos/<ano>/itens_pregao_<ano>-<mês>.{json,csv}`.

Também existem `itens_pregao_adicional_correspondencias_<ano>`, que entram no banco e não repetem
itens dos mensais. **Nenhum script do repositório os gera, e a origem deles não está documentada.**

**Limitações conhecidas:** a paginação perde menos de 1% das contratações e de 1% a 3% dos itens; a
API costuma atrasar cerca de um mês; os meses recentes têm poucos valores homologados; a chave de
duplicados pode descartar um segundo resultado do item (pendência 8).

## 3. Banco unificado (`banco_unificado.py`)

Carrega os brutos em `dados/pncp.db`, sem filtrar modos. Marca `registro_principal` (uma linha por
item) e `homologado`. Regras completas em [06](06-banco-de-dados.md). Depois de uma nova coleta, o
banco precisa ser recriado.

## 4. Seleção das compras para download

Só pregões **Aberto-Fechado com item homologado**: `modo_disputa = 'Aberto-Fechado'`,
`homologado = 1`, `registro_principal = 1`, com o mês definido por `data_resultado`.

- **Motivo:** o melhor lance de cada etapa só existe no relatório.
- **Pregão Aberto:** usa o resultado da API, que é o valor homologado e pode diferir do melhor lance
  por negociação ou desclassificação. Isso é limitação do estudo.

## 5. Download dos relatórios

### 5.1 Pelo PNCP (`baixar_api.py`, `pncp_arquivos.py`)

Automático, pela API pública, sem navegador e sem tocar no captcha.

1. **Passada própria:** lista os arquivos da contratação. É rápida.
2. **Passada das irmãs (`--irmas`):** busca contratações do mesmo CNPJ, ano, número e abertura, só nas
   compras ainda incompletas. É lenta: cerca de 12 s por página da consulta. Dá para restringir a um
   órgão (`--cnpj`) ou a órgãos sorteados com semente fixa (`--amostra-orgaos N`).

No fim de cada rodada, `inventario_pdfs.py` registra o que há em disco na tabela `relatorios_pdf`.

Para cada arquivo:

| Passo | Regra |
|---|---|
| Candidato | Tipos 26, 27 e 28 sempre; tipos ignorados nunca, como edital; os demais só se o título lembrar termo, ata, relatório, sessão ou lance |
| Termo reconhecido | Conteúdo é termo de homologação ou julgamento, com itens e com UASG e número da compra certos. Vai para `relatorios/`, um arquivo por item, com o nome do padrão do zip |
| Outro formato | Candidato não reconhecido é guardado em `outros_formatos/` se mencionar lances, não tiver texto, for ilegível ou não for PDF. Todos entram em `manifesto.csv` |

Cada compra grava em `motivos.csv`:

| Motivo | Significado |
|---|---|
| `termos encontrados` | Ao menos um item coberto; `situacao` diz se é completo ou parcial |
| `outros formatos guardados` | Há arquivo para adaptar o leitor depois |
| `candidatos sem lances` | Candidatos legíveis, sem menção a lances |
| `nenhum candidato` | Há arquivos publicados, mas nenhum passou no filtro |
| `nenhum arquivo publicado` | A consulta funcionou e não há arquivos |
| `erro na API` | Falhou; é refeita ao retomar a rodada |

Nenhum motivo prova que o PDF não existe. Ver [03 §3.4](03-fontes-de-dados-e-apis.md).

### 5.2 Manual (`relatorios.py`)

O que não estiver no PNCP só existe no zip do Compras.gov.br. O script abre a compra no navegador, e
a pessoa resolve o captcha e clica no download. **O hCaptcha não é contornado.**

### Seleção do relatório por item (`selecao.py`)

Mantém o termo de homologação; sem ele, o termo de julgamento da última sessão.

## 6. Extração dos PDFs (`extrator_homologacao`)

Parser determinístico, com PyMuPDF e regex. Sem modelos de linguagem.

1. **Texto:** camada de texto do PDF; sem ela, OCR do PyMuPDF. Remove cabeçalho e rodapé repetidos.
2. **Segmentação:** cabeçalho da compra e, por item, propostas, lances, chat e eventos. Grupos têm
   bloco próprio.
3. **Etapas:** a tabela de lances não indica a etapa, então ela é deduzida pelos marcos de tempo no
   chat, ou nos eventos. Em grupo, os marcos vêm do bloco do grupo.
4. **Classificação:** lance antes do início da fechada é da etapa aberta; dentro da janela, da
   fechada; em janela de desempate, vai à parte.
5. **Melhor lance por etapa:**
   - menor valor em Menor Preço, maior em Maior Desconto;
   - conta mesmo que o fornecedor seja desclassificado depois;
   - lances excluídos (`*`) não contam;
   - a etapa aberta inclui as propostas iniciais;
   - a etapa fechada usa só lances enviados na janela, inclusive em grupo.
6. **Conferência:** compara com os valores da mensagem de encerramento. Em grupo, pela soma de
   valor × quantidade dos itens de cada convocado.
7. **Status:** `OK`, `REVISAR` (com motivos) ou `ERRO`.

Cache por hash do arquivo, item e `VERSAO_PARSER`. Ao mudar o parser, incremente a versão.

**Limitações:** OCR lê o texto, mas o parser ainda não o entende, e o PDF sai como `ERRO`; Ata Final
de outras plataformas não é lida; grupos foram testados em um único pregão.

## 7. Carga no banco (ainda não feita)

As colunas de lance de `itens` estão vazias. A carga deve ligar `homologacoes.db` ao banco por UASG,
número, ano e item, validando a ligação, porque há contratações irmãs.

## Análise

Regras em [01](01-objetivo-e-metodologia.md). Filtro `elegivel`, `homologado = 1` e, por recomendação
ainda não decidida, só Menor Preço.

## Histórico de mudanças

| Data | Etapa | Mudança |
|---|---|---|
| 2026-11-03 | 3 | Banco unificado criado; valores em `REAL` depois de erro de divisão inteira na primeira carga |
| 2026-11-03 | 4 | Download restrito a Aberto-Fechado com item homologado |
| 2026-11-03 | 5 | `baixar_api.py`: seleção pelo banco, duas passadas, motivo por compra e retomada |
| 2026-11-03 | 5 | Candidatos não reconhecidos passam a ser guardados em `outros_formatos/` |
| 2026-11-03 | 5 | Filtro de título passa a reconhecer `AtaTotal_<n>`, `Ata_Final` e títulos com "lance" |
| 2026-11-03 | 6 | Parser 1.6.0: itens em grupo; cache passa a considerar o item |
| 2026-11-03 | 6 | OCR pelo PyMuPDF no lugar de OCRmyPDF; extração de escaneados ainda não funciona |
| 2026-11-03 | 5 | `--cnpj`, `--amostra-orgaos` e inventário dos PDFs em `relatorios_pdf` |
| 2026-11-03 | 5 | Passada própria de janeiro/2026: 2.364 compras, nenhum candidato. A busca de termos depende da passada das irmãs |
