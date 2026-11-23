# Compras do modo Aberto a baixar para controlar licitantes no matching (23/11/2026)

O número de licitantes (`quantidade_fornecedores`) só existe nos PDFs de relatório da compra. Foram baixados os do
Aberto-Fechado (AF) e do Fechado-Aberto, não os do Aberto (A). `listar.py` refaz quem entra nos matchings A × AF já
estimados e lista as compras do Aberto que precisam ser baixadas. Nenhum matching é reestimado.

## Matchings considerados

| Matching | Origem | Estrato |
|---|---|---|
| Mensal corrigido (principal do parecer de 17/11) | `analise/materiais_corrigido_20261113/amostra_mensal_{A_desconto,B_preco_mediana_historica}.csv.gz` | CNPJ+UASG × CATMAT/apresentação × mês × SRP × benefício × faixa de quantidade |
| Anual com sigilo, "principal" | `analise/ajuste_sigilo_painel_matching_20261117/` (reconstruído do `painel_principal.pkl`) | CNPJ × produto × ano × sigilo × SRP × benefício × faixa de quantidade |
| Anual com sigilo, "simples" | idem | CNPJ × produto × ano × sigilo |

A reconstrução do anual confere com o `resultados.json` em estratos e itens por modo. Há um detalhe no `executar.py` de 17/11:
o matching principal em log(P) roda duas vezes com o mesmo nome, primeiro na amostra toda e depois na subamostra com preço
estimado válido. A segunda chamada sobrescreve a primeira, então `principal_condicoes_ano_logp` (e o CSV de estratos) guarda a
subamostra com estimado válido. Com sigilo = 0 as duas amostras coincidem; com sigilo = 1, não: são 5.697 estratos contra
6.038, e β fica em −0,0725 contra −0,0733. A lista usa a amostra toda, que contém a subamostra.

## Resultado

| Prioridade | Critério | Compras A | Itens A pareados | Itens homologados nessas compras |
|---|---|---:|---:|---:|
| 1 | mensal (desconto ou preço) | 45 | 775 | 5.021 |
| 1–2 | + anual principal | 2.747 | 49.473 | 146.594 |
| 1–3 | + anual simples | 5.859 | 57.081 | 250.235 |

- Período: de 2023-04 a 2026-10, em 42 meses.
- Órgãos: 87.
- Concentração: o órgão com mais compras responde por 27% a 38% da lista, conforme a prioridade.
- Todas as compras têm `idCompra`.
- A prioridade 1 não se sobrepõe à 2: as compras do mensal e do anual principal são diferentes.

Cobertura do lado AF desses mesmos estratos na base `aberto-fechado_parser-1.9.1.db`, contando itens com `status_extracao = OK`
e licitantes > 0:

| Matching | Itens AF | Com licitantes | % |
|---|---:|---:|---:|
| mensal desconto | 888 | 79 | 8,9 |
| mensal preço | 861 | 73 | 8,5 |
| anual principal | 18.246 | 16.868 | 92,4 |
| anual simples | 43.381 | 39.582 | 91,2 |

No mensal, o AF é dominado por poucas compras grandes que ficaram sem PDF ("sem a opção no site") ou com zip parcial. Por
exemplo, `45307905916502024` tem 376 itens pareados e nenhum PDF. Mesmo baixando o Aberto, o mensal perde mais de 90% do lado
AF quando se exige o número de licitantes.

## Cuidados

- O número de licitantes é posterior à escolha do modo, que pode afetar a participação. Por isso o protocolo de 17/11 não o
  controla, e ao entrar no matching ele deve aparecer como sensibilidade, ao lado da estimativa sem ele.
- O `baixar_manual.py` e o `registro.py` só aceitam `--modo aberto-fechado` e `--modo fechado-aberto`. Falta um modo `aberto`
  que use esta lista.
- É preciso conferir se o parser lê o relatório do Aberto, que tem uma etapa só.

## Arquivos

- `listar.py`: o script. Rodar da pasta `PNCP-Automation`:
  ```
  python analises/aberto_licitantes_matching_20261123/listar.py --pncp-db ../dados/pncp.db --extracao dados/extracao/aberto-fechado_parser-1.9.1.db
  ```
  Leva cerca de 5 minutos. O `pncp.db` é aberto só para leitura, e o script confere tamanho e mtime ao final.
- `compras_aberto.csv`: uma linha por compra Aberto, com:
  - prioridade e mês (primeiro mês de resultado);
  - os campos de `registro/compras/`;
  - UASG, órgão e números dos itens pareados;
  - os indicadores `em_<matching>`.
- `compras_por_mes/<AAAA-MM>.csv`: a mesma lista no formato de `registro/compras/<AAAA-MM>.csv`.
- `itens_aberto.csv.gz`: itens A e AF de cada matching (compra, item, `idCompra`, licitantes na base).
- `resumo.json`: os números acima.
