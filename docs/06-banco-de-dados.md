# 6. Banco de dados (`dados/pncp.db`)

Banco SQLite da base nacional, gerado por `banco_unificado.py` a partir de `dados/brutos/<ano>/` e
`dados/brutos_pncp/<ano>/`. Reúne compras e itens de pregão de 2022-11 a 2026-10, em todos os modos de
disputa. A coluna `compras.fonte` separa a API Dados Abertos (`dados_abertos`) do PNCP (`pncp`).

Não é o mesmo arquivo que `dados/extracao/homologacoes.db`, que guarda a extração dos PDFs.

```
python banco_unificado.py            # cria; recusa se o banco já existir
python banco_unificado.py --recriar  # sobrescreve, inclusive as colunas de lance
python banco_unificado.py --pncp     # carrega os meses completos do PNCP que faltam no banco
```

O banco fica fora do git, como toda a pasta `dados/`. A carga leva alguns minutos e gera cerca de
2,4 GB. Ela grava em `pncp.db.tmp` e só troca o arquivo no fim; se a troca falhar com acesso
negado, feche os programas que estejam com o banco aberto.

## Conteúdo (carga de 2026-11-03, antes da coleta do PNCP)

| Medida | Total |
|---|---|
| Compras | 328.169 |
| Linhas em `itens` | 6.365.040 |
| Itens distintos (`registro_principal = 1`) | 6.362.668 |
| Itens homologados, uma linha por item | 4.606.939 |
| Compras Aberto / Aberto-Fechado / Fechado-Aberto | 202.480 / 123.777 / 1.912 |

## Conteúdo depois da coleta do PNCP (2026-11-10)

Os 48 meses (2022-11 a 2026-10) estão em `coleta_pncp_meses`. O banco tem cerca de 16 GB.

| Medida | `dados_abertos` | `pncp` | Total |
|---|---|---|---|
| Compras | 328.169 | 772.894 | 1.101.063 |
| Pregão Eletrônico / Presencial | 327.550 / 619 | 745.106 / 27.788 | 1.072.656 / 28.407 |
| Linhas em `itens` | 6.365.040 | 25.132.497 | 31.497.537 |
| Linhas em `resultados` | — | 12.521.130 | 12.521.130 |
| Compras sem itens | — | 20 | |
| Irmãs em `compras_duplicadas` | | 25.118 | |

O PNCP listou 1.126.094 pregões no período, dos quais 328.082 já estavam na base pela API Dados
Abertos. No Pregão Eletrônico, os modos com `fonte = 'pncp'` são: Aberto 582.898, Aberto-Fechado
154.310, Fechado-Aberto 6.149, Fechado 917, Não se aplica 792 e Dispensa Com Disputa 40.

Os meses recentes vieram com poucos resultados porque muitos pregões ainda não tinham sido homologados.
Por exemplo, 2026-10 tem 112.394 resultados para 713.639 itens, contra cerca de 420 mil para 710 mil
em 2026-06. Ver a pendência 12 em [05](05-decisoes-e-pendencias.md).

## Tabela `compras`

Uma linha por `numero_controle_pncp`. Fonte: `contratacoes_pregao_*.json`.

| Coluna | Campo da API | Observação |
|---|---|---|
| `numero_controle_pncp` | `numeroControlePNCP` | Chave primária |
| `id_compra` | `idCompra` | Liga aos PDFs; **não é único** |
| `uasg` | `unidadeOrgaoCodigoUnidade` | UASG da compra |
| `numero_compra`, `ano_compra` | `numeroCompra`, `anoCompraPncp` | |
| `orgao_cnpj`, `orgao_nome` | `orgaoEntidadeCnpj`, `orgaoEntidadeRazaoSocial` | |
| `esfera`, `poder` | `orgaoEntidadeEsferaId`, `orgaoEntidadePoderId` | Códigos, ex.: `F`, `E`, `M`, `D` |
| `uf`, `municipio`, `codigo_ibge` | `unidadeOrgaoUfSigla`, `unidadeOrgaoMunicipioNome`, `unidadeOrgaoCodigoIbge` | |
| `modalidade_nome` | `modalidadeNome` | Pregão Eletrônico ou Presencial |
| `modo_disputa` | `modoDisputaNomePncp` | Aberto, Aberto-Fechado, Fechado-Aberto |
| `srp`, `existe_resultado` | `srp`, `existeResultado` | 0 ou 1 |
| `valor_total_estimado`, `valor_total_homologado` | `valorTotalEstimado`, `valorTotalHomologado` | |
| `data_publicacao`, `data_abertura_proposta` | `dataPublicacaoPncp`, `dataAberturaPropostaPncp` | Texto ISO |
| `ano_publicacao` | derivada | Ano de `data_publicacao`; usado no pareamento |
| `objeto_compra` | `objetoCompra` | |
| `fonte` | gerada | `dados_abertos` ou `pncp` |
| `usuario_nome` | `usuarioNome` | Plataforma que publicou; só em `fonte = 'pncp'` |
| `codigo_unidade`, `nome_unidade` | `unidadeOrgao` | Só em `fonte = 'pncp'`; o código pode não ser UASG |
| `situacao_compra` | `situacaoCompraNome` | Divulgada, Revogada, Anulada, Suspensa; só em `fonte = 'pncp'` |

Em `fonte = 'pncp'`, `id_compra` fica vazio, e `uasg` só é preenchida se a plataforma for o
Compras.gov.br. `baixar_api.py` ignora as compras sem `id_compra`.

## Tabela `itens`

Uma linha por registro da API, e não por item. Fonte: `itens_pregao_*.csv`, incluindo os arquivos
`adicional_correspondencias`, que não repetem itens dos mensais.

| Coluna | Campo da API | Observação |
|---|---|---|
| `id` | gerada | Chave primária |
| `numero_controle_pncp`, `numero_item` | `numeroControlePNCPCompra`, `numeroItemPncp` | Identificam o item; igual a `numeroItemCompra` em todas as linhas |
| `id_compra_item` | `idCompraItem` | Também não é único |
| `registro_principal` | gerada | 1 em exatamente uma linha por item |
| `uasg_item` | `unidadeOrgaoCodigoUnidade` | Difere de `compras.uasg` em 2.475 linhas; é a usada nos `matching_*.py` |
| `cod_item_catalogo` | `codItemCatalogo` | Vazio em 1.360.047 linhas |
| `material_ou_servico` | `materialOuServico` | `M` ou `S` |
| `codigo_classe`, `codigo_grupo`, `codigo_pdm` | `codigoClasse`, `codigoGrupo`, `codigoPdm` | Catálogo; `codigo_grupo` não é o grupo da disputa |
| `unidade_medida`, `descricao_resumida` | `unidadeMedida`, `descricaoResumida` | |
| `criterio_julgamento` | `criterioJulgamentoNome` | Menor preço, Maior desconto, Não se aplica |
| `tipo_beneficio` | `tipoBeneficioNome` | Exclusividade ME/EPP, cota etc. |
| `numero_grupo` | `numeroGrupo` | Sempre 0 na base, mesmo em itens de grupo; o grupo só vem do PDF |
| `orcamento_sigiloso` | `orcamentoSigiloso` | 0 ou 1 |
| `situacao_item` | `situacaoCompraItemNome` | Em andamento, Homologado, Anulado/Revogado/Cancelado, Deserto, Fracassado |
| `homologado` | derivada | 1 se `situacao_item = 'Homologado'` |
| `quantidade`, `valor_unitario_estimado` | `quantidade`, `valorUnitarioEstimado` | |
| `tem_resultado` | `temResultado` | 1 ou vazio; a API não traz falso |
| `quantidade_resultado`, `valor_unitario_resultado`, `valor_total_resultado` | `quantidadeResultado`, `valorUnitarioResultado`, `valorTotalResultado` | |
| `data_resultado`, `data_atualizacao` | `dataResultado`, `dataAtualizacaoPncp` | |
| `cod_fornecedor`, `nome_fornecedor` | `codFornecedor`, `nomeFornecedor` | Vencedor do registro |

### Colunas vindas dos PDFs (vazias por enquanto)

Têm os nomes do extrator (ver [02](02-arquitetura-e-pipeline.md)). A carga ainda não existe.

`melhor_lance_modo_aberto`, `melhor_lance_modo_fechado`, `melhor_lance_desempate`, `lance_aceito`,
`valor_negociado_aceito`, `valor_estimado_pdf`, `quantidade_fornecedores`, `status_extracao`,
`erros_extracao`, `versao_parser`, `arquivo_origem`.

Ligação com o PDF: `compras.uasg` + `numero_compra` + `ano_compra` e `itens.numero_item`. Como
`id_compra` se repete e há contratações irmãs, valide a ligação ao fazer a carga.

## Tabela `resultados`

Um registro por resultado do item, de `coleta_resultados.py`. Chave: `numero_controle_pncp`,
`numero_item`, `sequencial_resultado`. Carregada por `banco_unificado.py --resultados`.

`situacao_resultado` separa `Informado` (ativo) de `Cancelado`, o que a tabela `itens` não faz. Em
dois dias testados, o valor de `itens` diferiu do resultado ativo em 1,0% dos itens. A view
`analise_itens` ainda usa o valor de `itens` (pendência 8).

Colunas: `id_compra_item`, `situacao_resultado`, `motivo_cancelamento`, `ni_fornecedor`,
`nome_fornecedor`, `porte_fornecedor`, `quantidade_homologada`, `valor_unitario_homologado`,
`valor_total_homologado`, `data_resultado`, `data_atualizacao`, `data_cancelamento`.

Compras do PNCP entram nessa mesma tabela, e `--resultados` não as apaga.

## Compras do PNCP (`fonte = 'pncp'`)

Carga de `coleta_pncp.py`, um mês por transação. Diferenças em relação à API Dados Abertos:

- **Uma linha por item em `itens`**, sempre com `registro_principal = 1`. Todos os resultados ficam em
  `resultados`.
- **Resultado do item:** o ativo com valor positivo, atualização mais recente, maior quantidade e menor
  valor. Item só com resultado cancelado fica com os campos de resultado vazios.
- **Vazias:** `id_compra_item`, `cod_item_catalogo`, `codigo_classe`, `codigo_grupo`, `codigo_pdm`,
  `numero_grupo`. Sem código de catálogo, essas compras ficam fora do pareamento UASG × item.
- **`descricao_resumida`** guarda a descrição completa do PNCP.
- **`modo_disputa`** pode ter valores que a outra fonte não tem, como `Fechado`.

Tabelas de apoio:

| Tabela | Conteúdo |
|---|---|
| `compras_duplicadas` | Irmãs que não entraram em `compras`: `numero_controle_pncp`, `duplicata_de`, `usuario_nome`, `mes` |
| `coleta_pncp_meses` | Um registro por mês carregado: `publicadas`, `ja_na_base`, `duplicadas`, `novas`, `itens`, `resultados`, `sem_itens`, `carregado_em` |

## Tabela `relatorios_pdf`

Inventário dos relatórios já baixados, gerado por `inventario_pdfs.py` a partir do disco. Uma linha
por arquivo. O `baixar_api.py` a atualiza no fim de cada rodada. **`banco_unificado.py --recriar`
apaga a tabela**: rode `python inventario_pdfs.py` em seguida. Uma cópia fica em
`dados/inventario_pdfs.csv`.

| Coluna | Conteúdo |
|---|---|
| `id_compra` | Do nome do arquivo ou da pasta |
| `numero_controle_pncp` | Preenchido só quando `id_compra` aponta para uma única compra |
| `item` | Número do item; vazio em outros formatos |
| `tipo` | Termo de homologação, termo de julgamento ou outro formato |
| `arquivo` | Caminho relativo a `dados/`; chave primária |
| `tamanho`, `sha256` | O PDF de um grupo se repete, com o mesmo hash, em cada item |
| `pasta` | Rodada de origem, ex.: `aberto-fechado_2026-01` |

## Tabela `busca_pdf`

Última busca de cada compra no PNCP, refeita por `inventario_pdfs.py` a partir dos `motivos.csv`. Uma
compra completa em qualquer mês fica como completa. `baixar_api.py` não busca de novo uma compra já
buscada, e **`dados/pendentes_manual.csv` é a lista a usar no download manual**: traz as compras
buscadas sem todos os termos, com o link. Compras com `situacao = 'completo'` não entram nela.

Colunas: `numero_controle_pncp`, `id_compra`, `mes`, `passada`, `situacao`, `motivo`, `itens_cobertos`,
`outros_guardados`.

## View `analise_itens`

Junta `itens` e `compras`, só com `registro_principal = 1`. Descontos em %.

| Coluna | Definição |
|---|---|
| `desconto_final` | `100 × (1 − valor_unitario_resultado / valor_unitario_estimado)`, com os dois valores > 0 |
| `elegivel` | 1 se `tem_resultado = 1`, orçamento não sigiloso, valores > 0 e `desconto_final` entre −100 e 99 |
| `por_preco` | 1 se o critério for Menor preço |
| `desconto_aberto`, `desconto_fechado` | Desconto do melhor lance de cada etapa; só Menor preço |
| `melhor_lance_apos_fechada` | Menor valor entre as duas etapas; só Aberto-Fechado e Menor preço |
| `ganho_fechada` | Desconto ganho na etapa fechada; item sem melhora entra com zero |

## Regras e cuidados

- **Fonte:** `analise_itens` traz as duas fontes e as colunas `fonte`, `usuario_nome` e
  `situacao_compra`. Para repetir os números anteriores à coleta do PNCP, use
  `fonte = 'dados_abertos'`. Os `matching_*.py` leem `dados/brutos/` e seguem só com essa fonte.
- **Sigilo no PNCP:** `orcamento_sigiloso` vem falso em parte dos itens que a API Dados Abertos marca
  como sigilosos (167 de 2.266 numa amostra). Assim, `elegivel` pode incluir no PNCP itens que seriam
  excluídos na outra fonte.
- **Filtro de homologados:** `elegivel` repete os filtros do `matching_desconto.py` e não exige
  homologação. Use `elegivel = 1 AND homologado = 1`. Há 10.865 linhas com resultado e valor que
  não estão homologadas.
- **Sempre use `analise_itens` ou filtre `registro_principal = 1`:** contar direto em `itens`
  conta registros, não itens.
- **`registro_principal`:** prioriza homologado, valor de resultado positivo, atualização mais
  recente, maior quantidade e menor valor. Em 355 itens há mais de um resultado com valor, e só um
  entra na análise.
- **Homologados sem valor válido:** 441 linhas sem valor de resultado e 267 com valor ≤ 0 têm
  `homologado = 1`, mas ficam fora de `elegivel`.
- **Valores em `REAL`, nunca `NUMERIC`:** com `NUMERIC`, o SQLite guarda 80,0 como inteiro e
  `80 / 100` vira divisão inteira (0), o que excluiu indevidamente 211 mil itens na primeira carga.
- **Maior desconto:** na API o resultado é comparável ao estimado, então `desconto_final` vale. Os
  descontos por etapa ficam vazios porque o lance do PDF pode ser percentual; ainda não verificado.
- **Meses recentes mudam:** `valor_total_homologado` estava vazio em 93% das compras de 2026-10.
- **Perdas da API:** ver as armadilhas em [03 §3.1](03-fontes-de-dados-e-apis.md).

## Validação da carga de 2026-11-03

- Contagens e filtros conferidos passo a passo contra os arquivos brutos.
- `quick_check` ok; nenhum item sem compra; exatamente um `registro_principal` por item.
- Com os filtros do `matching_desconto.py`, o banco dá 3.161.123 itens e o script, 3.161.373. A
  diferença de 250 deve vir dos registros repetidos, que o script conta; não foi conferida linha a
  linha.

## Exemplos

```sql
-- desconto médio por modo, só homologados
SELECT modo_disputa, COUNT(*) AS itens, ROUND(AVG(desconto_final), 2) AS desconto_medio
FROM analise_itens
WHERE elegivel = 1 AND homologado = 1 AND modalidade_nome = 'Pregão - Eletrônico'
GROUP BY modo_disputa;

-- células UASG × item × ano com os dois modos
SELECT uasg_item, cod_item_catalogo, ano_publicacao, COUNT(*) AS itens
FROM analise_itens
WHERE elegivel = 1 AND homologado = 1 AND cod_item_catalogo IS NOT NULL
  AND modo_disputa IN ('Aberto', 'Aberto-Fechado')
GROUP BY 1, 2, 3
HAVING COUNT(DISTINCT modo_disputa) = 2;
```
