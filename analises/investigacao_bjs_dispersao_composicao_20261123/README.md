# Investigação complementar: BJS × estudo de eventos, dispersão histórica × contemporânea, composição (23/11/2026)

**Exploratória.** Complementa `../robustez_dispersao_20261123/` e `../testes_desenho_causal_20261123/`.

- `protocolo.md`: definições escritas antes da execução. O hash está em `registro_execucao.json`.
- `relatorio.md`: relatório técnico com os resultados verificados.

## Reprodução (da pasta `PNCP-Automation`)

```
python analises/investigacao_bjs_dispersao_composicao_20261123/investigar.py
```

Pré-requisitos:
- a base de 23/11 em `dados/testes_desenho_causal/` (`../testes_desenho_causal_20261123/preparar.py`);
- `dados/robustez_dispersao/descricoes_catmat.pkl` (`../robustez_dispersao_20261123/preparar_descricoes.py`).

O script não lê o `pncp.db` nem altera bases ou resultados anteriores. O motor de `../robustez_dispersao_20261123/` só é
importado. Para um teste rápido do código, use `INVESTIGACAO_LIMITE_EVENTOS=60`; as saídas vão para
`dados/investigacao_bjs_dispersao_composicao/teste_rapido/`.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `investigar.py` | As três partes, o registro de execução e as conferências |
| `tabelas/p1_passos.csv`, `p1_decomposicao.csv`, `p1_eventos.csv` | BJS × estudo de eventos: passos S0–S3, decomposição e valores por evento |
| `tabelas/p2_filtros.csv`, `p2_exclusoes_*.csv` | Dispersão histórica × contemporânea na amostra comum; exclusões por falta de histórico |
| `tabelas/p3_composicao.csv`, `p3_perfil.csv`, `p3_placebo.csv` | Composição das compras na troca de modo: efeitos, perfil por trimestre, troca fictícia |
| `tabelas/todas_estimativas.csv` | Todas as estimativas, com os campos padrão e a influência dos órgãos |
| `resultados.json`, `registro_execucao.json` | Resultados e registro (status, exclusões, conferências, eventos reservados) |
