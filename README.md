# Contratações PNCP 

Scripts para coletar as contratações (Lei 14.133/2021) dos órgãos filtrados (`--orgaos`) na API de
Dados Abertos do Compras.gov.br, separá-las em pastas por modalidade e modo de disputa, organizar o zip "Todos os relatórios e
termos" de cada compra e extrair os campos dos relatórios para Excel e SQLite.


## Requisitos

- Python 3.10+
- `pip install -r requirements.txt`
- Rodar os comandos a partir da pasta do projeto.

### Onde ficam os dados

Por padrão em `dados/`, dentro do projeto. Para usar outra pasta (outro disco, pasta de backup
etc.), defina a variável de ambiente `PNCP_DADOS`; todos os scripts passam a ler e gravar lá
(`<PNCP_DADOS>/brutos`, `filtrados`, `orgaos`, `extracao`):

```powershell
$env:PNCP_DADOS = "D:\pncp"                                          # só nesta sessão
[Environment]::SetEnvironmentVariable("PNCP_DADOS", "D:\pncp", "User")  # permanente (abra outro terminal)
```

Nos exemplos abaixo, `dados/` significa essa pasta. Ao mudar de pasta, mova o conteúdo de `dados/`
junto, ou os relatórios já baixados serão pedidos de novo.

## Uso

### 0. Listar órgãos — `orgaos.py` (opcional)

```bash
python orgaos.py [--inicio AAAA-MM-DD] [--fim AAAA-MM-DD] [--modalidades COD ...] [--minimo 5]
```

Lista os órgãos do **Brasil todo** que publicaram contratações no período, para usar em
`get.py --orgaos dados/orgaos/orgaos.txt`. Consulta a mesma API do `get.py` sem filtrar CNPJ, mês a
mês, e agrega por órgão.

| Opção | Padrão |
|---|---|
| `--inicio` / `--fim` | últimos 365 dias até hoje |
| `--modalidades` | `5` (Pregão Eletrônico e Presencial; nessa API, `6` é Dispensa e `7` Inexigibilidade) |
| `--minimo` | `5`: só entram órgãos com pelo menos 5 contratações no período |

- Gera `dados/orgaos/orgaos.txt` (CNPJ por linha; contratações, homologadas, município e nome em
  comentário) e `orgaos.csv` (com esfera, poder e contagem por modo de disputa).
- Cada mês concluído fica em `orgaos.parcial.json`: se cair no meio, rode de novo que ele continua
  de onde parou. Meses com falha são avisados no fim.
- Volume: ~9 mil pregões por mês no país (~200 páginas por ano). A API costuma estar cerca de um
  mês atrasada, e a paginação dela não é estável (perde-se menos de 1% dos registros).

### 1. Coletar e separar — `get.py`

```bash
python get.py [--orgaos CNPJ|ARQUIVO ...] [--inicio AAAA-MM-DD] [--fim AAAA-MM-DD]
              [--modos MODO ...] [--modalidades COD ...] [--relatorios]
```

| Opção | Padrão | Exemplo |
|---|---|---|
| `--orgaos` | `08778326000156` (João Pessoa) | `--orgaos 08778326000156 09012345000199` ou `--orgaos orgaos.txt` (um CNPJ por linha, `#` comenta) |
| `--inicio` / `--fim` | últimos 365 dias até hoje | `--inicio 2026-01-01 --fim 2026-06-30` |
| `--modos` | todos | `--modos aberto-fechado aberto` (sem acento/maiúsculas; também `fechado-aberto`, `"dispensa com disputa"`, `"nao se aplica"`) |
| `--modalidades` | 1 a 19 | `--modalidades 6 8` |
| `--relatorios` | — | baixa os relatórios das contratações selecionadas logo em seguida |

- Consulta a API `modulo-contratacoes/1_consultarContratacoes_PNCP_14133`, com paginação e retry
  em erros temporários (429/5xx/timeout), e remove duplicadas por `idCompra`.
- Cada contratação vai para a pasta `<modalidade>_<modo de disputa>`, ex.: `pregao_aberto-fechado`,
  `pregao_aberto`, `concorrencia_fechado-aberto`, `dispensa_com-disputa`; quando o modo é
  "Não se aplica", só a modalidade (`dispensa`, `inexigibilidade`).

### 2. Baixar os relatórios — `relatorios.py`

```bash
python relatorios.py [dados/filtrados/<pasta>/contratacoes_<pasta>.json ...]
```

Sem argumento, percorre todas as pastas de `dados/filtrados/`.

O download no Compras.gov.br é protegido por hCaptcha, por isso ele é feito **manualmente**:

1. O script abre cada compra no navegador padrão.
2. Você clica em **Downloads → Todos os relatórios e termos**.
3. O script detecta `relatorios-compra-<idCompra>.zip` na pasta Downloads, move para a pasta da
   compra, extrai só o relatório escolhido para cada item (regra abaixo) e abre a próxima.

Detalhes:

- Compras ainda não homologadas (sem `existeResultado`/`valorTotalHomologado`) são puladas, pois
  o site não oferece os relatórios para elas.
- Para economizar espaço, fica **um relatório por item**: o termo de homologação
  (`relatorio-termo-homologacao-*.pdf`) ou, se o item não tiver, o termo de julgamento da última
  sessão (`relatorio-julg-hab-*-s<N>-*.pdf`). O zip e o resto (outras sessões, diligências etc.)
  são apagados. Se nenhum relatório se encaixar nessa regra, nada é apagado. A regra fica em
  `extrator_homologacao/selecao.py` e é a mesma usada pelo extrator.
- Compras que já têm relatório (ou zip) na pasta são puladas, então pode rodar de novo para baixar
  só o que falta; nessas pastas o que estiver fora da regra também é apagado.
- Se o download não acontecer em 5 minutos, a compra é pulada.

### 3. Extrair os campos dos relatórios — `extrator_homologacao`

```bash
python -m extrator_homologacao [pasta] [--saida dados/extracao/homologacoes.xlsx] [--padrao "*.pdf"] [--todos] [--reprocessar] [--sem-ocr] [--workers 4] [--sem-separar] [--db arquivo.db]
```

Lê os relatórios da pasta (padrão: `dados/filtrados`, todas as subpastas) e gera
`dados/extracao/homologacoes.xlsx` consolidado e um Excel por subpasta
(`dados/extracao/<pasta>.xlsx`), com **uma linha por PDF**, abas `relatorios`, `revisar`
(status ≠ OK) e `metadados`, além de `homologacoes.log` e `homologacoes.cache.json`.

Também grava `dados/extracao/homologacoes.db` (SQLite; outro arquivo com `--db`), tabela `itens`
com as mesmas colunas e **uma linha por item** (chave `uasg` + `modalidade_compra` +
`numero_compra` + `item`; o número da compra se repete entre modalidades da mesma UASG). Cada
execução atualiza os itens processados e mantém os demais, então o banco acumula execuções de
pastas ou órgãos diferentes; colunas novas do parser são adicionadas a um banco existente. Com
`--todos` o banco não é atualizado (haveria vários relatórios por item).

- Por padrão entra **um relatório por item**: o termo de homologação, que traz os mesmos campos do
  julgamento já com a situação final (`Adjudicado e Homologado`, `Fracassado e Homologado`); sem
  ele, o termo de julgamento da última sessão. Os julgamentos repetem o item e há um por sessão
  (`-s1-`, `-s2-`): uma sessão anterior pode mostrar um lance aceito que depois fracassou.
  Use `--todos` para processar todos os PDFs, incluindo todas as sessões e diligências.

- Separação dos lances por etapa conforme o modo de disputa do cabeçalho: `Aberto/Fechado` (janelas
  do chat, abaixo), `Aberto` ou `Fechado` (etapa única; desempates à parte). Outros modos (ex.:
  `Fechado/Aberto`) vão para `REVISAR` com os campos de lance vazios.
- O parser foi construído e validado com relatórios de **pregão Aberto/Fechado**. Os de outras
  modalidades/modos ainda não foram baixados e podem ter layout diferente: confira a aba `revisar`
  na primeira execução.

- Extração determinística (PyMuPDF + regex). OCRmyPDF/Tesseract só entram se o PDF não tiver texto.
- Valores monetários são **unitários**, em `Decimal`; ausente = célula vazia, nunca zero.
- **Etapas dos lances**: o relatório tem uma única tabela "Lances do Item N" sem indicação de etapa.
  A etapa de cada lance vem das janelas de tempo anunciadas no chat do item ("A etapa fechada foi
  iniciada/reiniciada…", "…foi encerrada") — ou dos "Eventos do Item" como alternativa. A lista de
  valores da mensagem de encerramento serve só para conferir (e para desempatar lances no mesmo
  segundo da troca de etapa), nunca é contada como lance. Lances de desempate (art. 60 / ME/EPP)
  ficam em `melhor_lance_desempate`, fora das colunas da etapa fechada. Lances marcados com `*`
  (excluídos) são desconsiderados.
- `melhor_lance_*`: lance mais vantajoso registrado na etapa pelo critério do item (menor valor em
  Menor Preço, maior em Maior Desconto), mesmo que o fornecedor tenha sido desclassificado depois.
- **Lance aceito**: vem da situação do item ("Aceito e Habilitado / Adjudicado e Homologado por …
  para FORNECEDOR, CNPJ …, melhor lance …[, valor negociado …]"); usa o valor negociado quando
  houver. É conferido com a tabela de propostas e os eventos do item; qualquer contradição (ex.:
  aceito depois inabilitado) deixa o valor vazio e marca `REVISAR`. Mensagens do chat não são prova.
- `resultado`: resultado do item, padronizado a partir da "Situação:" (mantida em `situacao_item`):
  `HOMOLOGADO`, `ADJUDICADO`, `FRACASSADO`, `DESERTO`, `REVOGADO`, `ANULADO`, `CANCELADO`, `SUSPENSO`
  ou `EM ANDAMENTO` (aceito, aberto para recursos, aguardando adjudicação…). Situação desconhecida
  vira `NÃO IDENTIFICADO`, com aviso em `erros_extracao`. Diferente de `situacao_lance_aceito`, que
  é a validação do lance aceito.
- `quantidade_fornecedores`: CNPJs/CPFs distintos na tabela de propostas do item.
- Status: `OK`, `REVISAR` (motivos em `erros_extracao`), `ERRO` (ex.: relatórios de diligência,
  que não trazem dados do item). `fontes_extracao` registra página/seção de cada campo.
- Cache por SHA-256 + versão do parser (`extrator_homologacao/__init__.py`): arquivos idênticos não
  são reprocessados; ao mudar o parser, incremente `VERSAO_PARSER` ou use `--reprocessar`.

## Saída

```
dados/
├── orgaos/
│   └── orgaos.{txt,csv}                                # lista de órgãos (orgaos.py)
├── brutos/
│   └── contratacoes.{json,csv}                         # tudo o que foi coletado na última execução
├── filtrados/
│   └── <modalidade>_<modo>/                            # ex.: pregao_aberto-fechado
│       ├── contratacoes_<modalidade>_<modo>.{json,csv}
│       └── relatorios/
│           └── <numeroCompra>-<ano>_<idCompra>/       # um relatório por item (homologação ou julgamento)
└── extracao/
    ├── homologacoes.xlsx                               # consolidado
    ├── homologacoes.db                                 # SQLite, tabela itens (acumula execuções)
    └── <modalidade>_<modo>.xlsx                        # um por pasta
```

Os CSVs são gravados em UTF-8 com BOM (abrem direto no Excel). A pasta `dados/` não é versionada.
Cada execução do `get.py` regrava os JSON/CSV das pastas com a seleção atual; os relatórios já
baixados são mantidos.

## Outros agrupamentos

A pasta de cada contratação é definida pela função `grupo` em `get.py`; altere-a para separar por
outro critério (ex.: incluir o CNPJ do órgão no nome da pasta).
