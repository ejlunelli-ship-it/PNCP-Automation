# Composição dos produtos e efeito do AF no preço homologado (23/11/2026). Exploratório

Pergunta: as diferenças de preço associadas à troca de modo vêm do preço de produtos comparáveis ou da composição das
compras?

- `protocolo.md`: definições e hipóteses, escritas antes da execução.
- `relatorio.md`: metodologia, resultados e interpretação.

## Reprodução (da pasta `PNCP-Automation`)

```
python analises/composicao_precos_medicamentos_20261123/executar.py
```

Comando único, de cerca de 5 minutos: roda os cinco testes, grava as tabelas, os gráficos, `resultados.json` e
`registro_execucao.json`. Pré-requisito: a base de 23/11 em `dados/testes_desenho_causal/`
(`../testes_desenho_causal_20261123/preparar.py`).
- O motor (`../robustez_dispersao_20261123/motor_robustez.py`) e as funções de gráfico são só importados.
- O `pncp.db` não é lido.
- Os 56 eventos reservados para validação não entram.
- `COMPOSICAO_LIMITE_EVENTOS=60` roda um teste rápido, com saídas em `dados/composicao_precos_medicamentos/teste_rapido/`.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `executar.py` | Testes 1–5, conferências (reprodução de M0/M1, identidade da decomposição, eventos reservados) e registro |
| `graficos_composicao.py` | Gráficos de efeitos e IC95 (SVG), lidos de `tabelas/todas_estimativas.csv` |
| `tabelas/t1_grupos.csv`, `t1_perfil.csv` | Medicamentos × demais materiais (A e G), com perfil por trimestre |
| `tabelas/t2_interacao.csv` | Interação AF × medicamentos, critério de identificação e efeito mínimo detectável |
| `tabelas/t3_composicao_fixa.csv` | Índice original × índice de composição fixa, com diferenças pareadas |
| `tabelas/t4_decomposicao.csv` | ΔĒ = A (preço de comparáveis) + B1 (recomposição) + B2 (entrada e saída) |
| `tabelas/t5_*.csv` | Pré-tendência na pseudojanela, cobertura de produtos e parcela de medicamentos |
| `tabelas/eventos_*.csv` | Valores por evento de cada modelo |
| `tabelas/todas_estimativas.csv` | Todas as estimativas, com os campos padrão, a influência e as diferenças contra −1,91 e −3,76 lp |
| `graficos/g1`–`g5_*.svg` | Efeitos e IC95 por teste |
