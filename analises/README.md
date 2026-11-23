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
| `fevereiro_campos_novos.py` | 2026-02 com os campos do parser 1.8.0: marcas do parser e sensibilidade "só fornecedores válidos" | `fevereiro_campos_novos.{json,xlsx}` |

Os `.csv.gz` (dados por item) ficam fora do Git. Para reexecutar, copie a pasta para `../analise/etapas_pdf_af_20261118/` (irmã de `PNCP-Automation/`) e rode, nesta ordem, `ligar_pncp.py`, `analisar.py`, `testes_grupos.py`, `regressao_etapas.py` e `decomposicao_marcas.py` com o Python do `.venv` (precisa de `openpyxl`). Exige `PNCP-Automation/dados/extracao/aberto-fechado_2026-08.db` e `dados/pncp.db` na raiz do workspace. Resultados descritivos da dinâmica dentro do Aberto-Fechado, não efeito causal do modo de disputa.

**Desfecho dos itens e compras por modo de disputa — 21/11/2026**

[`desfecho_modos_20261121/`](desfecho_modos_20261121/relatorio.md): fracassados, desertos e não homologados (item) e compras sem item ou com todos os itens homologados, Aberto × Aberto-Fechado × Fechado-Aberto, no Compras.gov.br de 2023-01 a 2026-06 (5,08 milhões de itens decididos, 263 mil compras). Modelo linear de probabilidade em quatro especificações (bruta; mês × material/serviço com controles; + UASG, a principal; UASG × CATMAT × ano), erro-padrão agrupado por CNPJ e CATMAT, Holm sobre os 10 testes principais. Protocolo em [`protocolo.md`](desfecho_modos_20261121/protocolo.md).

Na família principal, só um teste é significativo: compras Fechado-Aberto têm 5,2 p.p. menos chance de homologar todos os itens decididos (IC95 −8,0 a −2,5; p Holm = 0,002). Nenhuma diferença Aberto-Fechado × Aberto é significativa; a diferença bruta vem da composição de órgãos. Para reexecutar: `python analises/desfecho_modos_20261121/testes_desfecho.py` (~50 min; a extração fica em `dados/analise_desfecho/`, fora do git). Saídas: `resultados.csv`, `descritivas_itens.csv`, `descritivas_compras.csv`.

**Uso dos modos Aberto-Fechado e Fechado-Aberto: tendência e associações — 21/11/2026**

[`uso_modos_20261121/`](uso_modos_20261121/relatorio.md): parcela das compras em Aberto-Fechado e Fechado-Aberto no Pregão Eletrônico, nov/2022 a out/2026, todas as plataformas (1,07 milhão de compras, 35 mil unidades). Tendência bruta e dentro da unidade (principal; Holm sobre 4 testes), por semestre e com decomposição entrada/saída; perfil por esfera, região, plataforma e características da compra; R² de unidade, órgão, categoria, item de catálogo e plataforma; efeitos de 148 categorias CATMAT/CATSER dentro da unidade; concentração nas unidades. Protocolo em [`protocolo.md`](uso_modos_20261121/protocolo.md).

Uso estável: o Aberto-Fechado fica em ~37% (Compras.gov.br) e ~21% (outras plataformas), sem tendência significativa depois de Holm; o Fechado-Aberto cai no Compras.gov.br (−0,25 p.p./ano dentro da unidade; p Holm 0,02) e sobe nas outras plataformas por causa da Agili Software em Mato Grosso (93–98% FA). A unidade explica 82–84% da escolha do Aberto-Fechado; a categoria do objeto, 2%, e quase nada além da unidade. Para reexecutar: `extracao.py` e depois `uso_modos.py` por partes (ver o relatório; a extração fica em `dados/analise_uso_modos/`, fora do git).

**Desconto por etapa nos PDFs: base completa, Aberto-Fechado e Fechado-Aberto — 22/11/2026**

[`etapas_completo_20261122/`](etapas_completo_20261122/relatorio.md) refaz todas as análises por etapa na base completa
`aberto-fechado_parser-1.9.1.db`:

- **Aberto-Fechado:** 43 meses (2023-04 a 2026-10), 1,34 milhão de itens, 73 mil compras.
- **Fechado-Aberto:** 20 mil itens, 1.149 compras.

O relatório traz:

- as duas medidas principais (todos os fornecedores; só válidos);
- a decomposição do desconto final, marcas e sensibilidades;
- a economia em R$;
- a série por ano e por mês;
- a heterogeneidade;
- os testes de médias por grupo;
- a regressão com efeito fixo de item e 13 sensibilidades;
- a comparação AF × FA, nova.

Resultado de referência: no AF, a etapa fechada acrescenta 15,4 p.p. (todos) ou 14,1 p.p. (válidos) ao desconto da aberta,
que é de 19,4%, com desconto final de 34,3%. É estável de 2023 a 2026. No FA, a etapa aberta acrescenta 9,9 p.p. Nas 168
UASGs que usam os dois modos, o desconto final do FA é 4,8 p.p. menor (associação).

Scripts:

- `complementares.py` e `economia.py`, que reutilizam a amostra do `analise_etapas.py`;
- resultados em `resultados/`;
- comandos de reexecução no fim do relatório.

**Compras do Aberto a baixar para controlar licitantes no matching — 23/11/2026**

[`aberto_licitantes_matching_20261123/`](aberto_licitantes_matching_20261123/README.md): `listar.py` reconstrói os itens dos
matchings A × AF (mensal de 13/11; anual com sigilo de 17/11, conferido com o `resultados.json`) e lista as compras do modo
Aberto cujos PDFs faltam para ter o número de licitantes: 45 (mensal), 2.747 (mensal + anual principal) ou 5.859 (com o anual
simples). Também mede quantos itens AF desses estratos já têm licitantes na base de extração.

**Parecer: desenho de inferência causal para o efeito do modo (A × AF) — 23/11/2026**

[`parecer_desenho_causal_20261123/`](parecer_desenho_causal_20261123/parecer.md) revisa todos os estudos do projeto e
recomenda os desenhos. Os diagnósticos são só de leitura (`diagnosticos.py`, `diagnosticos_d.py`, `diagnosticos_e.py`;
números em `diagnosticos.json`):

- como o modo varia dentro da unidade (sequências e mudanças de regime);
- o suporte de pareamentos alternativos;
- a etapa aberta do AF comparada ao Aberto nos mesmos estratos;
- a cobertura de preço por fonte;
- o poder de um estudo de eventos por unidade, calculado com placebos em unidades que não mudam de modo.

**Testes do desenho causal A × AF (pré-registrados) — 23/11/2026**

[`testes_desenho_causal_20261123/`](testes_desenho_causal_20261123/README.md) executa os testes recomendados no parecer.
O pré-registro (`protocolo.md`) foi commitado antes das estimativas. Principal: estudo de eventos na unidade compradora, 152
mudanças de regime, efeito do AF de −1,9 lp, IC95 [−5,7; +1,9], com todos os testes de falsificação aprovados. Inclui:

- imputação BJS, PanelMatch e DiD sintético;
- desfechos placebo e secundários, limites de Lee e heterogeneidade;
- matching de itens descritivo (AIPW, entropia, Γ de Rosenbaum, Cinelli–Hazlett);
- a lista do Aberto a baixar para o desenho intraleilão.

Resultados em `relatorio.md`; reexecução no fim do relatório.
