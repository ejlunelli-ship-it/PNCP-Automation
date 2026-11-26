# Relatório — número de licitantes no Aberto-Fechado: SRP × não SRP (22/11/2026)

Protocolo: [protocolo.md](protocolo.md). Script: `licitantes_srp.py` (155 s). Saídas: `descritivas.csv`,
`descritivas_ano.csv`, `resultados.csv`, `log_execucao.txt`.

## Amostra

- 643.694 itens nos 5 bancos de extração; 621.672 com status OK e ≥ 1 licitante; 593.749 sem repetidos
  (14 meses, 2024-11 a 2026-10, não contínuos).
- 578.243 ligados ao `pncp.db` (97,4%): 32.510 compras, 1.167 CNPJs, 2.112 UASGs. 17 `id_compra`
  repetidos ficaram fora.

| | Itens | Compras | CNPJs | Média | DP | Mediana | P25–P75 | % com 1 licitante | % serviço | % sigiloso |
|---|---|---|---|---|---|---|---|---|---|---|
| Não SRP | 100.772 | 15.900 | 945 | 8,87 | 8,50 | 6 | 3–11 | 6,7 | 10,9 | 33,2 |
| SRP | 477.471 | 16.610 | 760 | 8,06 | 6,74 | 6 | 3–11 | 7,3 | 4,2 | 18,1 |

As compras SRP têm muito mais itens (28,7 por compra, contra 6,3 nas não SRP), por isso dominam a
amostra por item.

## Resultados (SRP − não SRP)

| Nível | Espec. | Licitantes | IC 95% | p | ln (log-pontos) | IC 95% | p |
|---|---|---|---|---|---|---|---|
| Item | S1 bruta | −0,81 | −1,64 a 0,03 | 0,058 | −5,1 | −14,7 a 4,5 | 0,300 |
| Item | S2 mês×MS + controles | −0,61 | −1,12 a −0,11 | 0,017 | −6,1 | −12,4 a 0,2 | 0,056 |
| **Item** | **S3 + UASG (principal)** | **−0,55** | **−1,22 a 0,12** | **0,108 (Holm 0,216)** | **−4,9** | **−12,1 a 2,4** | **0,190 (Holm 0,216)** |
| Item | S4 UASG×catálogo×ano | +0,23 | −0,67 a 1,13 | 0,618 | +12,7 | −2,6 a 28,1 | 0,103 |
| Compra | S3 | −1,53 | −2,59 a −0,47 | 0,005 | −14,3 | −23,9 a −4,7 | 0,004 |

Erro-padrão agrupado por CNPJ e código de catálogo (por compra: CNPJ). Holm só sobre os 2 testes
principais.

## Leitura

- **No teste principal não há diferença estatisticamente significativa.** Na mesma UASG, com os
  controles, o item SRP tem 0,55 licitante a menos (cerca de 5% a menos), com p 0,11 (Holm 0,22).
- O sinal negativo aparece em quase todas as especificações, mas some quando se compara o mesmo
  produto na mesma UASG e no mesmo ano (S4, que usa só 21% da amostra).
- **Por compra a diferença é significativa:** −1,5 licitante por item (cerca de 13% a menos), p 0,005.
  Como cada compra pesa igual, esse resultado reflete as compras pequenas, que são sobretudo não SRP.
  É sensibilidade (p bruto) e não substitui o teste principal.
- É associação, não efeito causal. A amostra se limita às compras com termo de homologação baixado nos
  meses extraídos nesta máquina.
