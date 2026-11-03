# 2. Arquitetura e pipeline

## Dois trilhos de dados

```
Trilho A — base nacional (só API, desconto final)
  coleta_anos.py  ──> dados/brutos/<ano>/contratacoes_pregao_<ano>-<mês>.{json,csv}
  coleta_itens.py ──> dados/brutos/<ano>/itens_pregao_<ano>-<mês>.{json,csv}
  matching_*.py   ──> resultados no terminal

Trilho B — amostra com PDF (desconto por etapa)
  orgaos.py (opcional) ──> dados/orgaos/orgaos.txt
  get.py               ──> dados/filtrados/pregao_<modo>/contratacoes_<pasta>.{json,csv}
  relatorios.py        ──> dados/filtrados/<pasta>/relatorios/<numero>-<ano>_<idCompra>/*.pdf
     ├─ 1º pncp_arquivos.py (automático, PNCP)
     └─ 2º navegador + clique manual (hCaptcha) para o que faltar → pendentes.csv
  extrator_homologacao ──> dados/extracao/homologacoes.{xlsx,db,log,cache.json}
```

O objetivo final é juntar os dois trilhos. O trilho A tem cobertura nacional, mas só o resultado
final. O trilho B tem as etapas, mas só numa amostra.

## Scripts

| Arquivo | Papel |
|---|---|
| `config.py` | `DADOS` = `$PNCP_DADOS` ou `./dados` |
| `orgaos.py` | Órgãos do país com 5+ pregões no período (mês a mês, com retomada via `orgaos.parcial.json`) |
| `get.py` | Pregões (`codigoModalidade=5`) dos órgãos pedidos na API Dados Abertos; dedup por `numeroControlePNCP`; separa em pastas por modo de disputa (`grupo()`) |
| `relatorios.py` | Para cada compra homologada: tenta o PNCP; senão abre a página no navegador e espera o zip em `~/Downloads` (5 min); mantém um relatório por item; grava `pendentes.csv` |
| `pncp_arquivos.py` | Busca os termos no PNCP: arquivos da contratação **e das irmãs**, filtro por tipo/título, validação pelo conteúdo (UASG + número), renomeia no padrão do zip |
| `extrator_homologacao/` | Parser determinístico dos PDFs (PyMuPDF + regex) → Excel e SQLite |
| `coleta_anos.py` / `coleta_itens.py` | Base nacional de pregões (nov/2022+) e itens (dia a dia, 3 meses em paralelo) |
| `banco_unificado.py` | Banco SQLite `dados/pncp.db`: tabelas `compras` e `itens`, view `analise_itens`. Colunas de lance vazias até a carga dos PDFs; `--recriar` as apaga |
| `matching_*.py` | Análises estatísticas Aberto vs Aberto-Fechado (precisam de `scipy`) |

## Regras de seleção do relatório (`extrator_homologacao/selecao.py`)

Por item, mantém **um** PDF:
1. `relatorio-termo-homologacao-<idCompra>-item-<N>.pdf`, que tem a situação final; senão
2. `relatorio-julg-hab-<idCompra>-s<sessão>-item-<N>.pdf` da **última** sessão. Uma sessão anterior
   pode mostrar um lance aceito que depois fracassou.

Os PDFs vindos do PNCP são gravados com esses nomes. O julgamento recebe `s0`, para perder para
qualquer julgamento do zip.

## Estado de cada compra em `relatorios.py`

| Situação | Como é detectada | O que acontece |
|---|---|---|
| Já baixada | pasta tem PDF selecionável ou zip, sem `.pncp_parcial` | pula |
| Não homologada | sem `existeResultado` / `valorTotalHomologado` | pula; entra no `pendentes.csv` |
| Completa no PNCP | itens cobertos ≥ `/itens/quantidade` | grava os PDFs; não abre o navegador |
| Parcial no PNCP | cobre só parte dos itens | grava o que achou, cria `.pncp_parcial` (ex.: `3/9`), pede o zip |
| Sem nada no PNCP | — | pede o zip (ou, com `--so-pncp`, só lista) |
| Zip não recebido | timeout de 5 min | entra no `pendentes.csv` |

O `pendentes.csv` é refeito a cada rodada e apagado quando fica vazio.

## Extrator (`extrator_homologacao/`)

| Módulo | Papel |
|---|---|
| `texto.py` | Texto das páginas (OCR só se não houver texto); remove o cabeçalho e o rodapé repetidos |
| `secoes.py` | Segmenta: cabeçalho da compra; por item, o bloco do item, propostas, lances, chat e eventos |
| `campos.py` | Campos do cabeçalho; situação do item; lance aceito e suas validações |
| `tabelas.py` | Tabelas de propostas e de lances |
| `etapas.py` | Janelas das etapas (aberta, fechada, desempates) pelo chat ou pelos eventos; classifica cada lance; confere com a lista do encerramento |
| `extracao.py` | Orquestra um PDF → dicionário de campos |
| `validacao.py` | Modelo pydantic `RegistroExtracao` (uma linha por PDF) e regras de REVISAR |
| `lote.py` | Lote em paralelo, cache por SHA-256 + `VERSAO_PARSER` |
| `saida.py` / `__main__.py` | Excel (abas `relatorios`, `revisar`, `metadados`), SQLite e CLI |

**Status**:
- `OK`;
- `REVISAR`, com os motivos em `erros_extracao`;
- `ERRO`, para relatório não suportado (ex.: diligência).

**SQLite** `itens`: uma linha por item, com chave `uasg` + `modalidade_compra` + `numero_compra` +
`item`. Acumula execuções.

### Colunas principais de saída

`uasg`, `pregao`, `modo_disputa`, `valor_estimado`, `melhor_lance_modo_aberto`,
`melhor_lance_modo_fechado`, `melhor_lance_desempate`, `lance_aceito`, `valor_negociado_aceito`,
`fornecedor_lance_aceito`, `cnpj_fornecedor_lance_aceito`, `quantidade_fornecedores`, `resultado`,
`situacao_item`, `criterio_julgamento_item`, `esfera`, `uf` (essas duas vêm do JSON do `get.py`),
`status_extracao`, `erros_extracao`, `fontes_extracao`, `versao_parser`, `grupo` (ex.: `G1`, vazio em
item avulso).

## Validação feita até agora

- Em 03/11/2026: Fortaleza 90119/2025, grupo G1 (itens 1 a 6), todos `OK`, com os totais da etapa
  fechada conferidos pela soma. Outros 4 PDFs de item avulso deram resultado idêntico ao do parser 1.5.0.
- Parser validado com pregões Aberto/Fechado e Aberto do Compras.gov.br. A versão atual do parser
  é 1.6.0.
- Em 02/11/2026: 82 PDFs de Fortaleza (12 pregões AF de 01–10/08/2025) baixados do PNCP, todos
  `OK` no extrator.
