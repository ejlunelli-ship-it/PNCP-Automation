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
2.2 Demais plataformas (API do PNCP) ───> dados/brutos_pncp/ ──────────┤
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
- **Duplicados:** chave `numeroControlePNCPCompra` + `numeroItemPncp` + `idCompraItem` + fornecedor +
  valor do resultado. Os meses coletados antes de 2026-11-03 usaram a chave sem fornecedor e valor.
- **Conferência:** pelas linhas recebidas, porque `totalRegistros` conta repetições.
- **Retomada:** meses gravados são pulados, exceto o corrente; para atualizar um mês, apague o arquivo.
- **Saída:** `dados/brutos/<ano>/itens_pregao_<ano>-<mês>.{json,csv}`.

Também existem `itens_pregao_adicional_correspondencias_<ano>`, que entram no banco e não repetem
itens dos mensais. **Nenhum script do repositório os gera, e a origem deles não está documentada.**

**Limitações conhecidas:** a paginação perde menos de 1% das contratações e de 1% a 3% dos itens; a
API costuma atrasar cerca de um mês; os meses recentes têm poucos valores homologados.

### 2.1 Coleta dos resultados (`coleta_resultados.py`)

- **Fonte:** `3_consultarResultadoItensContratacoes_PNCP_14133`, dia a dia pela data de resultado.
- **Por quê:** `itens` não separa resultado ativo de cancelado, e o valor diferiu em cerca de 1% dos
  itens (pendência 8).
- **Recorte:** só as compras de `pncp.db`; duplicados por compra, item e `sequencialResultado`.
- **Retomada:** mês com falha não é gravado e é refeito ao rodar de novo.
- **Saída:** `dados/brutos/<ano>/resultados_pregao_<ano>-<mês>.json`, depois tabela `resultados`.

### 2.2 Coleta das demais plataformas (`coleta_pncp.py`)

- **Fonte:** API do PNCP. `contratacoes/publicacao` para a lista; `/itens` e `/itens/{n}/resultados`
  compra a compra.
- **Recorte:** modalidades 6 e 7 (Pregão Eletrônico e Presencial), todos os modos, de 2022-11 a 2026-10.
- **Corte temporal:** mês de `dataPublicacaoPncp`.
- **Duplicados:** descarta o `numeroControlePNCP` já presente e a irmã com mesmo CNPJ, ano, número e
  abertura, comparando com todo o banco. A irmã fica em `compras_duplicadas`, sem baixar itens. Entre
  irmãs novas, fica a de menor `numeroControlePNCP`. Compra sem número ou abertura não é comparada.
- **Lista dia a dia:** cada dia é uma consulta, porque a página funda é lenta (ver docs/03, item 17).
- **Conferência:** a lista de cada dia é repetida uma vez se vier menos que `totalRegistros`, e o log registra a
  diferença. Depois de 3 tentativas, até 50 compras com falha entram sem itens, contadas em
  `coleta_pncp_meses.sem_itens`; acima disso, o mês não é carregado.
- **Velocidade:** 2 s entre páginas da lista e 8 threads nos itens (`--threads`). Um 429 pausa todas as
  threads. Só um processo pode listar por vez: dois juntos levam a 429 seguidos.
- **Retomada:** compra baixada não se repete, e mês carregado é pulado.
- **Saída:** `dados/brutos_pncp/<ano>/contratacoes_<mês>.json.gz` e `itens_<mês>.jsonl.gz`, depois o
  banco, numa transação por mês. `itens_<mês>.completo` marca o mês baixado por inteiro.

**Limitações conhecidas:** o PNCP não traz o item do catálogo (`catalogoCodigoItem` existe, é opcional
no envio e vem sempre vazio), então `cod_item_catalogo` fica vazio e a compra fica fora do pareamento UASG × item; os
meses recentes têm poucos resultados e não são atualizados depois de carregados; `orcamento_sigiloso`
não equivale ao da API Dados Abertos (ver [06](06-banco-de-dados.md)); a chave de irmãs foi conferida
em poucos casos.

## 3. Banco unificado (`banco_unificado.py`)

Carrega os brutos em `dados/pncp.db`, sem filtrar modos. Marca `registro_principal` (uma linha por
item) e `homologado`. Regras completas em [06](06-banco-de-dados.md). Depois de uma nova coleta da API
Dados Abertos, o banco precisa ser recriado. A coleta do PNCP entra direto no banco existente, e
`--recriar` a recarrega de `dados/brutos_pncp/`.

## 4. Seleção das compras para download

Só pregões **Aberto-Fechado com item homologado**: `modo_disputa = 'Aberto-Fechado'`,
`homologado = 1`, `registro_principal = 1`, com o mês definido por `data_resultado`. Compras sem
`id_compra`, que são as vindas do PNCP, ainda ficam de fora.

- **Motivo:** o melhor lance de cada etapa só existe no relatório.
- **Pregão Aberto:** usa o resultado da API, que é o valor homologado e pode diferir do melhor lance
  por negociação ou desclassificação. Isso é limitação do estudo.

## 5. Download dos relatórios

### 5.1 Pelo PNCP (`baixar_api.py`, `pncp_arquivos.py`)

Automático, pela API pública, sem navegador e sem tocar no captcha.

Varredura mês a mês: `python baixar_api.py <mês>`, e o mês seguinte só roda por comando do usuário.

1. **Índice de publicações:** `dados/pncp_publicadas/<AAAA-MM>.json` lista os pregões Aberto-Fechado
   publicados no mês, de todos os órgãos, uma única vez. Respeita o limite do PNCP, com 2 s entre
   páginas. Cada compra usa o mês da publicação e os vizinhos.
2. **Por compra:** olha a própria contratação e as irmãs do índice, com mesmo CNPJ, ano, número e
   abertura.
3. **Sem repetição:** compra já buscada em qualquer mês não é buscada de novo.
4. **Registro:** `inventario_pdfs.py` atualiza `relatorios_pdf`, `busca_pdf` e
   `dados/pendentes_manual.csv`, que é a lista do download manual.

Opções: `--sem-irmas`, `--cnpj`, `--amostra-orgaos N`, `--limite N`.

**Limitação do índice:** uma irmã cadastrada com outro modo de disputa não é encontrada. As 3 irmãs
conferidas de Fortaleza têm o mesmo modo.

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
| 2026-11-03 | 2 | Chave de duplicados dos itens inclui fornecedor e valor; nova coleta de resultados e tabela `resultados` |
| 2026-11-03 | 5 | Irmãs pelo índice mensal de publicações, só Aberto-Fechado, no lugar da consulta por órgão; compra já buscada não repete; `busca_pdf` e `pendentes_manual.csv` |
| 2026-11-03 | 5 | `--cnpj`, `--amostra-orgaos` e inventário dos PDFs em `relatorios_pdf` |
| 2026-11-03 | 5 | Lista de órgão que falhou não é repetida na mesma rodada; as compras seguem como `erro na API` |
| 2026-11-03 | 5 | Irmãs de janeiro/2026: Fortaleza 25 de 26 compras com termos; amostra de 40 órgãos (359 compras), nenhuma |
| 2026-11-03 | 5 | Passada própria de janeiro/2026: 2.364 compras, nenhum candidato. A busca de termos depende da passada das irmãs |
| 2026-11-06 | 2.2 e 3 | `coleta_pncp.py`: pregões fora da API Dados Abertos entram pelo PNCP, com `compras.fonte`, `compras_duplicadas`, `coleta_pncp_meses` e brutos em `dados/brutos_pncp/`; `--pncp`; `--recriar` recarrega esses brutos; `--resultados` preserva os do PNCP |
| 2026-11-06 | 4 | `baixar_api.py` ignora compras sem `id_compra` |
| 2026-11-07 | 2.2 | `coleta_pncp.py` lista o mês dia a dia, e não mais o mês inteiro de uma vez: mesmas compras, cerca de 40% menos tempo |
