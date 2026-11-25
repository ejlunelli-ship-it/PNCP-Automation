# Replicação empírica adaptada de Athey, Levin e Seira (2011), Fase 1 (24/11/2026). Exploratório

Esta pasta aplica a estratégia empírica de *Comparing Open and Sealed Bid Auctions* (*QJE* 126: 207–257; seções III e IV.A,
eqs. 5–7) para comparar os preços homologados no Aberto-Fechado (AF) e no Aberto (A):
- logit do modo na compra;
- suporte comum em [0,075; 0,925];
- OLS;
- OLS com interações e efeito médio;
- matching simétrico pelos 4 vizinhos no escore, com EP de Abadie e Imbens.

O resultado é uma replicação metodológica adaptada, **não uma nova identificação causal**. Todas as estimativas são
associações ajustadas. O modelo estrutural (Fase 2) não foi executado.

- `protocolo.md`: definições e regras, escritas antes de estimar.
- `relatorio.md`: resultados, comparação com o artigo e interpretação.

## Reprodução (da pasta `PNCP-Automation`)

```
python analises/replicacao_athey_levin_seira_20261124/executar.py
```

**Pré-requisitos:**
- a base de 23/11 em `dados/testes_desenho_causal/` (`../testes_desenho_causal_20261123/preparar.py`);
- R com os pacotes `quantreg` (regressão mediana) e `Matching` (conferência do matching). Sem R, essas duas partes ficam
  registradas como não executadas;
- o caminho do `Rscript` pode ser dado em `ALS_RSCRIPT`.

**Garantias:**
- o `pncp.db` não é lido;
- nada posterior a 2025-10 entra, o que deixa fora os eventos reservados;
- nada anterior é alterado.

As saídas grandes ficam em `dados/replicacao_athey_levin_seira/`, fora do git.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `amostra.py` | Amostra, exclusões e covariáveis anteriores ao modo (compra e item) |
| `modelos.py` | Logit (EP robusto e agrupado), MQ com efeitos fixos absorvidos e EP CR1 agrupado, combinação linear, Wald, influência por órgão, Holm |
| `matching.py` | Vizinhos com empates, estimador simétrico (eq. 7), efeito nas AF e nas A, variâncias de Abadie e Imbens e adaptação agrupada |
| `qr_mediana.R` | Regressão mediana na compra (`quantreg`), com bootstrap de pares por CNPJ |
| `validar_matching.R` | Conferência no pacote `Matching` (`Match`, M = 4, empates, `Var.calc = 4`) |
| `executar.py` | Comando único: todas as etapas e o registro |
| `graficos_als.py` | Gráficos SVG |
| `tabelas/` | Exclusões, logit, suporte, equilíbrio, OLS, interações, matching, robustez, mediana, secundários e comparação |
| `graficos/` | Escore por modo, equilíbrio, efeitos, robustez e comparação |
