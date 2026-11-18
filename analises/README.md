**Testes de médias de preços por modo de disputa — 17/11/2026**

Resultados, protocolos, código executado e validações dos testes de Aberto versus Aberto-Fechado. As bases individuais, o SQLite e as matrizes volumosas do bootstrap permanecem fora do Git. Os scripts preservam a estrutura de execução do workspace, documentada abaixo.

| Análise | Relatório | Planilha | Protocolo |
|---|---|---|---|
| Comparação por produto/mês/UF | [Mensal](testes_medias_20261117/relatorio_completo.md) | [Excel mensal](testes_medias_20261117/resultados_completos.xlsx) | [Protocolo mensal](testes_medias_20261117/protocolo.md) |
| Separação por sigilo e comparação por produto/ano/UF | [Anual por sigilo](testes_medias_sigilo_anual_20261117/relatorio_completo.md) | [Excel anual](testes_medias_sigilo_anual_20261117/resultados_completos.xlsx) | [Protocolo anual](testes_medias_sigilo_anual_20261117/protocolo.md) |

São 15 especificações mensais e 30 anuais. A inferência principal usa CNPJ e CATMAT como agrupamentos e correção Holm. O bootstrap por órgão é complementar, com perdas de suporte documentadas. Os resultados são associativos; a referência é de compras públicas e não um preço externo certificado de mercado. Os índices em nível têm observações extremamente influentes, auditadas e mantidas.

Na análise anual principal, o grupo não sigiloso apresenta preço geométrico aproximadamente 8,72% menor e desconto 3,29 p.p. maior em AF, ambos com p Holm de 0,0158. A diferença de preço perde significância no bootstrap (p Holm=0,370); desconto permanece significativo (0,018). No grupo sigiloso, os testes principais são inconclusivos. Isso não é um teste formal de diferença de efeitos entre os grupos.

Os arquivos `registro_*.json` e `validacao_*.json` preservam a proveniência da execução original. Os caminhos absolutos nesses registros são históricos. `manifesto.json` permite conferir a integridade dos arquivos versionados, inclusive resultados/planilhas. O código de extração e o gerador de Excel de apoio estão em `painel_efeitos_fixos_20261116`; não são novos resultados de painel.

**Reprodução.** A estrutura esperada é uma pasta de trabalho contendo `PNCP-Automation/` e `analise/` como pastas irmãs. O SQLite deve estar em `PNCP-Automation/dados/pncp.db` e corresponde ao snapshot de 10/11/2026. Use Python com NumPy, pandas e SciPy (versões usadas em `ambiente_execucao.json`).

Na raiz do repositório:

```powershell
python analises/reproduzir.py --verificar
python analises/reproduzir.py --executar
```

`--verificar` confere manifesto e dependências, e confere o banco quando estiver disponível, sem rodar os testes. `--executar` exige o banco, copia somente scripts/protocolos para `../analise/`, recusando sobrescrever fontes diferentes, reconstrói a extração mensal e executa as duas análises e suas validações. Gera dados e relatórios fora da árvore versionada; a execução completa demanda vários minutos e espaço para os arquivos locais. Não modifica o SQLite. Resultados locais já existentes nessas pastas são reestimados quando `--executar` é solicitado.

Para repetir somente a análise anual com as bases mensais preservadas e verificadas por hash, use `--executar --somente-anual`. Os resultados detalhados, incluindo amostra por modo, médias, ICs, erros-padrão, estatísticas, significância e todas as sensibilidades, estão nas planilhas e nos CSVs versionados.

**Etapa aberta × etapa fechada nos PDFs Aberto-Fechado — 18/11/2026**

[`etapas_pdf_af_20261118/`](etapas_pdf_af_20261118/relatorio.md): desconto por etapa dentro do Aberto-Fechado, lido dos termos de homologação de 2026-02, 03, 04 e 08 (166.596 itens de Menor Preço, parser 1.7.1/1.7.2). Relatório em [`relatorio.md`](etapas_pdf_af_20261118/relatorio.md); números em `resultados.json`, `regressao_etapas.json` e `decomposicao_marcas.json`; tabelas nos `.xlsx`.

| Script | O que faz | Saídas |
|---|---|---|
| `analisar.py` | Descritivas, testes pareados, economia em R$, heterogeneidade, estratos | `resultados.json`, `tabelas.xlsx`, `por_item.csv.gz` |
| `ligar_pncp.py` | Material/serviço e orçamento sigiloso do `pncp.db` (só leitura) | `ligacao_pncp.csv.gz`, `ligacao_pncp_meta.json` |
| `testes_grupos.py` | Diferenças de médias entre grupos, ajustadas pelo nº de licitantes | `testes_grupos.{csv,xlsx}`, `estatisticas_grupos.csv` |
| `regressao_etapas.py` | Regressão empilhada (FE de item) com interações e 13 sensibilidades | `regressao_etapas.{json,xlsx}` |
| `decomposicao_marcas.py` | Decomposição aberta + fechada + pós-disputa; marcas dos casos com fechado acima do aberto | `decomposicao_marcas.{json,xlsx}`, `marcas_por_item.csv.gz` |

Os `.csv.gz` (dados por item) ficam fora do Git. Para reexecutar, copie a pasta para `../analise/etapas_pdf_af_20261118/` (irmã de `PNCP-Automation/`) e rode, nesta ordem, `ligar_pncp.py`, `analisar.py`, `testes_grupos.py`, `regressao_etapas.py` e `decomposicao_marcas.py` com o Python do `.venv` (precisa de `openpyxl`). Exige `PNCP-Automation/dados/extracao/aberto-fechado_2026-08.db` e `dados/pncp.db` na raiz do workspace. Resultados descritivos da dinâmica dentro do Aberto-Fechado, não efeito causal do modo de disputa.
