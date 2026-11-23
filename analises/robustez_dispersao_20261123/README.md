# Testes de robustez da dispersão no estudo de eventos A × AF (23/11/2026). Exploratórios

São 15 testes que complementam `../testes_desenho_causal_20261123/` (relatório §3 e §12). Todos são exploratórios: o corte
de dispersão foi sugerido depois de ver os resultados do estudo principal.

- `protocolo.md`: definições, escritas antes de executar. O hash está em `registro_execucao.json`.
- `relatorio.md`: relatório técnico, com a comparação com −1,91 e −3,76 lp e a lista do que não foi executado.

## Reprodução (da pasta `PNCP-Automation`)

```
python analises/robustez_dispersao_20261123/preparar_descricoes.py --pncp-db ../dados/pncp.db   # uma vez, ~3 min
python analises/robustez_dispersao_20261123/executar_todos.py                                   # comando único
```

O segundo comando roda os 15 testes, grava as tabelas e os gráficos e confere a integridade das saídas. Pré-requisito: a
base de 23/11 em `dados/testes_desenho_causal/` (gerada por `../testes_desenho_causal_20261123/preparar.py`).
`ROBUSTEZ_LIMITE_EVENTOS=80` roda um teste rápido do código, com saídas em `dados/robustez_dispersao/teste_rapido/`.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `motor_robustez.py` | Motor item a item: filtros por evento, controles fixos, pesos por item, dispersão histórica, influência, Wald conjunto |
| `executar_todos.py` | Os 15 testes, o registro de execução e as conferências |
| `graficos.py` | Gráficos de diagnóstico em SVG, lidos das tabelas |
| `preparar_descricoes.py` | Descrições e unidades por CATMAT (teste 08), lidas do `pncp.db` só para leitura |
| `tabelas/` | Um CSV por teste (`t00`–`t15`), `todas_estimativas.csv` e os eventos por modelo (`eventos_*.csv`) |
| `graficos/` | `g1_coeficientes.svg`, `g2_dinamica.svg`, `g3_orgaos.svg`, `g4_dispersao.svg`, `g5_faixas.svg` |
| `resultados.json` | Todas as estimativas, com os detalhes de cada teste |
| `registro_execucao.json` | Status e tempo de cada teste, erros, exclusões, parâmetros e conferências |

Os scripts de 23/11 são só importados, sem gravar `__pycache__` naquela pasta. O `pncp.db` só é lido por
`preparar_descricoes.py`, que confere tamanho e mtime.
