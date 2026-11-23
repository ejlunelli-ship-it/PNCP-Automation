# Testes do desenho causal A × AF (23/11/2026)

Execução dos testes recomendados no parecer `../parecer_desenho_causal_20261123/parecer.md`.

- `protocolo.md`: pré-registro, commitado em `ff8b2d2` antes das estimativas. A especificação lida pelos scripts está em
  `especificacao.json`.
- `relatorio.md`: resultados e leitura.

## Resultado em uma linha

Estudo de eventos na unidade compradora (152 mudanças de regime, 76 A → AF e 76 AF → A): efeito do AF no preço de −1,9 lp,
IC95 [−5,7; +1,9], p = 0,32. Os testes de falsificação passam (pré-tendência, simetria, estimado e placebo no tempo). Não há
efeito detectável, mas o poder para −4,5% era de 54%. O matching de itens entre unidades dá −4,5 lp, frágil a confundimento
(Γ = 1,25; RV = 3,2%).

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `preparar.py` | Base (só leitura do `pncp.db`): índices, competição esperada, painéis unidade × mês, eventos |
| `comum.py`, `motor.py` | Funções comuns; motor do DiD empilhado, perfil e DiD sintético |
| `poder.py` → `poder.json` | Poder com placebos em unidades estáveis (feito antes do pré-registro) |
| `executar.py` → `resultados.json`, `eventos_did.csv` | Estudo de eventos e todos os seus testes |
| `item_descritivo.py` → `resultados_item.json` | Matching de itens descritivo |
| `lista_aberto.py` → `lista_aberto/` | Compras do Aberto a baixar para o desenho intraleilão |
| `exploratorio.py` → `exploratorio.json` | Verificações feitas depois de ver os resultados |
| `base.json`, `eventos.csv` | Contagens da base; eventos (só modo de disputa, sem desfecho) |

Os dados intermediários ficam em `dados/testes_desenho_causal/` (fora do git), com as saídas de depuração.
