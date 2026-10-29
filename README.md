# Contratações PNCP 

Scripts para coletar as contratações (Lei 14.133/2021) dos órgãos filtrados (`--orgaos`) na API de
Dados Abertos do Compras.gov.br, separá-las em pastas por modalidade e modo de disputa, organizar o zip "Todos os relatórios e
termos" de cada compra e extrair os campos dos relatórios para Excel.


## Requisitos

- Python 3.10+
- `pip install -r requirements.txt`

## Uso

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
   compra, extrai só os termos de homologação e abre a próxima.

Detalhes:

- Compras ainda não homologadas (sem `existeResultado`/`valorTotalHomologado`) são puladas, pois
  o site não oferece os relatórios para elas.
- Para economizar espaço, só os `relatorio-termo-homologacao-*.pdf` são mantidos (é o que o
  extrator usa); o zip e os demais relatórios (julgamento, diligências etc.) são apagados. Se o zip
  não tiver nenhum termo de homologação, nada é apagado.
- Compras que já têm termo de homologação (ou zip) na pasta são puladas, então pode rodar de novo
  para baixar só o que falta; nessas pastas o que sobrou além dos termos também é apagado.
- Se o download não acontecer em 5 minutos, a compra é pulada.

### 3. Extrair os campos dos relatórios — `extrator_homologacao`

```bash
python -m extrator_homologacao [pasta] [--saida dados/extracao/homologacoes.xlsx] [--padrao "relatorio-termo-homologacao-*.pdf"] [--reprocessar] [--sem-ocr] [--workers 4] [--sem-separar]
```

Lê os termos de homologação da pasta (padrão: `dados/filtrados`, todas as subpastas) e gera
`dados/extracao/homologacoes.xlsx` consolidado e um Excel por subpasta
(`dados/extracao/<pasta>.xlsx`), com **uma linha por PDF**, abas `relatorios`, `revisar`
(status ≠ OK) e `metadados`, além de `homologacoes.log` e `homologacoes.cache.json`.

- Por padrão só entram os `relatorio-termo-homologacao-*.pdf` (um por item): eles trazem os mesmos
  campos do termo de julgamento, mas com a situação final do item (`Adjudicado e Homologado`,
  `Fracassado e Homologado`). Os julgamentos repetem o item, e há um por sessão (`-s1-`, `-s2-`):
  uma sessão anterior pode mostrar um lance aceito que depois fracassou. Use `--padrao "*.pdf"`
  para processar todos os relatórios, incluindo julgamentos e diligências.

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
- `quantidade_fornecedores`: CNPJs/CPFs distintos na tabela de propostas do item.
- Status: `OK`, `REVISAR` (motivos em `erros_extracao`), `ERRO` (ex.: relatórios de diligência,
  que não trazem dados do item). `fontes_extracao` registra página/seção de cada campo.
- Cache por SHA-256 + versão do parser (`extrator_homologacao/__init__.py`): arquivos idênticos não
  são reprocessados; ao mudar o parser, incremente `VERSAO_PARSER` ou use `--reprocessar`.

## Saída

```
dados/
├── brutos/
│   └── contratacoes.{json,csv}                         # tudo o que foi coletado na última execução
├── filtrados/
│   └── <modalidade>_<modo>/                            # ex.: pregao_aberto-fechado
│       ├── contratacoes_<modalidade>_<modo>.{json,csv}
│       └── relatorios/
│           └── <numeroCompra>-<ano>_<idCompra>/       # relatorio-termo-homologacao-*.pdf
└── extracao/
    ├── homologacoes.xlsx                               # consolidado
    └── <modalidade>_<modo>.xlsx                        # um por pasta
```

Os CSVs são gravados em UTF-8 com BOM (abrem direto no Excel). A pasta `dados/` não é versionada.
Cada execução do `get.py` regrava os JSON/CSV das pastas com a seleção atual; os relatórios já
baixados são mantidos.

## Outros agrupamentos

A pasta de cada contratação é definida pela função `grupo` em `get.py`; altere-a para separar por
outro critério (ex.: incluir o CNPJ do órgão no nome da pasta).
