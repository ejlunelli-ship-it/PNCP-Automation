# Cesta padronizada de produtos (CATMAT × unidade) — 24/11/2026

Construção e auditoria de uma cesta fixa de produtos padronizados e frequentes no Pregão Eletrônico, **sem uso de preços
nem do modo de disputa** na seleção. Protocolo em [`protocolo.md`](protocolo.md) e resultados em
[`relatorio.md`](relatorio.md).

## Comandos

```powershell
cd PNCP-Automation\analises\cesta_padronizada_20261124
..\..\.venv\Scripts\python.exe executar.py                       # todas as etapas (~1 h)
..\..\.venv\Scripts\python.exe executar.py --etapas selecionar   # só uma etapa (ver --help)
..\..\.venv\Scripts\python.exe -m unittest discover -s testes -v # testes (banco sintético)
..\..\.venv\Scripts\python.exe validar_revisao.py                # gera a cesta validada a partir do formulário preenchido
```

Caminhos padrão em `config/parametros.json → caminhos`, relativos à pasta de trabalho, isto é, a pasta-mãe de
`PNCP-Automation`. Podem ser trocados por `--db`, `--brutos` e `--trabalho`, ou pelas variáveis `PNCP_DB`, `PNCP_BRUTOS`
e `CESTA_TRABALHO`. O banco de trabalho (cerca de 12 GB) fica fora do git; o padrão é `PNCP-Automation/dados/cesta_padronizada/`.

**Rodada de 24/11/2026.** Por falta de espaço no C:, o banco de trabalho foi para `D:\cesta_padronizada_trabalho\`.
Durante a rodada, o `pncp.db` foi movido de `dados/` para `D:\pncp.db`; a impressão digital confere com a da extração.
Para repetir as etapas a partir de `normalizar`:

```powershell
..\..\.venv\Scripts\python.exe executar.py --etapas normalizar,selecionar,auditar,sensibilidade,diagnostico,relatorio `
    --db D:\pncp.db --trabalho D:\cesta_padronizada_trabalho
```

## Etapas

| Etapa | Lê | Faz |
|---|---|---|
| `extrair` | `pncp.db` (mode=ro) | esquema real e mapeamento JSON, universo total descritivo, compras e itens sem colunas monetárias nem modo, deduplicação pela chave composta |
| `brutos` | `dados/brutos/*/itens_pregao_*.csv` | descrição detalhada e PDM, ligação conferida em cardinalidade, SHA-256 de cada arquivo |
| `normalizar` | banco de trabalho | unidades (tabela de aliases) e descrições normalizadas |
| `selecionar` | banco de trabalho | funil, métricas, triagem, auditoria de 100% das descrições, classe A/B/C, subtipos, cesta candidata congelada, formulário |
| `auditar` | banco de trabalho | auditoria de qualidade e integridade, cobertura da cesta |
| `sensibilidade` | banco de trabalho | grade fatorial, cenários nomeados, interseções, recorrência temporal |
| `diagnostico` | `pncp.db` (só o modo) | viabilidade causal, não seletivo, depois do congelamento |
| `relatorio` | saídas | `relatorio.md` e `saidas/registro_execucao.json` |

## Código

`cesta/`:

| Módulo | Conteúdo |
|---|---|
| `comum.py` | conexão ro, snapshot, impressão digital, registro |
| `esquema.py` | descoberta e mapeamento das colunas |
| `normalizacao.py` | normalização de texto, códigos, datas e unidades |
| `extracao.py`, `brutos.py` | leitura do banco e dos CSVs brutos |
| `metricas.py` | funil, frequência, HHI |
| `atributos.py` | extração de atributos por regex |
| `classificacao.py` | classes A/B/C |
| `auditoria.py` | controle de qualidade |
| `selecao.py` | seleção da cesta |
| `cobertura.py` | cobertura da cesta |
| `sensibilidade.py` | grade e cenários |
| `diagnostico.py` | diagnóstico dos modos |
| `relatorio.py` | relatório e registro |

Testes em `testes/` (unittest, banco sintético gerado por `testes/sintetico.py`).

## Saídas (`saidas/`)

- **Cesta:**
  - `cesta_candidata.csv`
  - `congelamento_cesta.json`
  - `formulario_revisao.csv`
  - `cesta_validada.csv` (vazia até a revisão humana)
- **Auditoria:**
  - `descricoes_variantes.csv` (100% das variantes; 64 MB, fora do git, recriado pela etapa `selecionar`)
  - `auditoria_qualidade.{json,csv}`
  - `familias_triadas_descartadas.csv`
  - `familias_metricas.csv.gz` (todas as famílias; fora do git, como todo `*.csv.gz` em `analises/`)
- **Cobertura:**
  - `funil_selecao.csv`
  - `cobertura_temporal.json`
  - `cobertura_cesta.json`
  - `cobertura_por_{ano,trimestre,grupo_material}.csv`
- **Sensibilidade:**
  - `sensibilidade_{grade,uma_dimensao,cenarios,intersecoes,pertinencia}.csv`
  - `recorrencia_temporal.csv`
- **Diagnóstico:**
  - `diagnostico_viabilidade.json`
  - `diagnostico_por_produto.csv`
- **Proveniência:**
  - `esquema/`
  - `registros/`
  - `registro_execucao.json`
