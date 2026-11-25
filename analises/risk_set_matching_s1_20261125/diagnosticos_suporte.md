# Diagnósticos de suporte (descritivos, posteriores ao estudo)

25/11/2026.
- **Comando:** `python executar.py --etapas diagnosticos`.
- **Código:** `scripts/diagnosticos_suporte.py`.
- **Tabelas:** `tabelas/diag_*.csv` e `resultados/diagnosticos_suporte.json`.
- **Alcance:** só contagens e disponibilidade, de 2023T2 a 2026T1. Nenhum efeito foi estimado e o protocolo congelado
  não foi alterado.
- **Unidades institucionais:** UASG, CNPJ (órgão) e UF (estado).

## 1. Coexistência de A e AF na mesma instituição e período

O critério é ter pelo menos 1 compra em A e 1 em AF na mesma célula, no trimestre. Valores para itens S1 com índice A1:

| Célula | Células com A e AF | % das células | Compras A / AF | Instituições | Nº efetivo | CNPJs | Produtos | Células com ≥ 2 compras em cada modo |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| UASG × trimestre | 707 | 4,1% | 2.524 / 2.381 | 363 UASGs | 197 | 215 | — | 192 |
| UASG × produto × trimestre | 548 | 0,13% | 889 / 716 | 53 UASGs | 7,3 | 44 | 280 | 46 |
| CNPJ × trimestre | 874 | 10,0% | 20.339 / 11.130 | 264 CNPJs | 146 | 264 | — | 477 |
| CNPJ × produto × trimestre | 21.521 | 6,9% | 62.955 / 46.088 | 91 CNPJs | **4,5** | 91 | 2.717 | 7.003 |
| UF × trimestre | 315 | 97% | 37.938 / 21.019 | 27 UFs | 26,9 | 2.149 | — | 299 |
| UF × produto × trimestre | 47.094 | 21,7% | 133.096 / 74.911 | 27 UFs | 9,9 | 1.881 | 3.025 | 9.692 |

**Períodos mais longos** (mesmo nível; tabela completa em `tabelas/diag_coexistencia_A_AF.csv`):

| Período | UASG × produto | CNPJ × produto | UF × produto |
|---|---|---|---|
| semestre | 888 células, 87 UASGs | 20.463 células, 110 CNPJs | 49.588 células |
| ano | 1.827 células, 147 UASGs, 100 CNPJs | 18.734 células, 144 CNPJs | 46.420 células |

**Todas as compras A/AF**, sem restringir a S1:
- UASG × trimestre: 3.360 células mistas (10,1%), 1.263 UASGs e 709 CNPJs.
- CNPJ × trimestre: 2.474 células (15,8%), com 58% das compras.

**Leitura:**
- **Dentro da UASG**, a variação contemporânea é rara. Nas células UASG × produto × trimestre ela fica concentrada: a
  UASG 453079 responde por 32% das células, e o número efetivo de UASGs é 7,3.
- **Dentro do CNPJ**, há muitas células, mas o número efetivo de órgãos é 4,5:
  - Comando do Exército: 44% das células;
  - EBSERH (dois CNPJs): 20%;
  - Marinha: 7%;
  - Aeronáutica: 6%;
  - SES-SP: 5%.

  A mediana é de 3 UASGs por célula, e só 543 células têm a mesma UASG nos dois modos. Na prática, a comparação é
  entre UASGs diferentes do mesmo órgão: decisões descentralizadas, com a mesma regra institucional.
- **Dentro da UF**, há suporte amplo, mas a comparação é entre instituições diferentes, com a seleção de modo entre
  órgãos plenamente ativa.
- Um desenho no nível da licitação dentro de CNPJ × produto × período tem suporte numérico. Porém:
  - ficaria identificado por cerca de 5 órgãos federais e de saúde;
  - não resolve a seleção, que ocorre entre UASGs de um mesmo órgão ou de uma mesma UASG entre compras.

## 2. Origem da ausência de índice S1

Cascata exclusiva por unidade-trimestre com compras A/AF:

| Causa | UASG | % dos sem índice | CNPJ | % dos sem índice |
|---|---:|---:|---:|---:|
| com índice | 17.445 (52,6%) | — | 8.739 (55,9%) | — |
| **sem item de produto S1** | 13.905 | **88,4%** | 5.916 | **85,6%** |
| itens S1 só fora de A/AF ou de menor preço | 222 | 1,4% | 104 | 1,5% |
| sem homologação: em andamento | 354 | 2,3% | 249 | 3,6% |
| sem homologação: fracassado/deserto | 387 | 2,5% | 219 | 3,2% |
| sem homologação: anulado/cancelado | 309 | 2,0% | 157 | 2,3% |
| homologado sem preço unitário | 0 | 0% | 0 | 0% |
| sem referência externa (< 5 itens de ≥ 3 outras UASGs) | 368 | 2,3% | 164 | 2,4% |
| valor extremo (\|Y\| > 100·ln 10) | 182 | 1,2% | 99 | 1,4% |

Todos os 324 UF-trimestres têm índice.

**Recuperação de dados observáveis** (só disponibilidade; qualquer uso exige um desenho pré-registrado):
- **Preço unitário:** só 3 itens S1 homologados não têm preço, e nenhum tem valor alternativo no banco. Não há o que
  recuperar.
- **Itens em andamento:** 354 UASG-trimestres, com 7.783 itens. Podem ganhar preço com uma nova coleta de resultados.
  É o único ganho por atualização de dados.
- **Referência externa em células mais largas** (mesmos mínimos, leave-one-UASG-out):
  - Produto × semestre recupera 182 dos 368 UASG-trimestres sem referência; produto × ano, 285.
  - Os valores extremos não são recuperáveis por referência.
  - Ganho total: 17.445 → 17.809 com semestre, ou 17.912 com ano.
- **Cestas mais amplas**, que são a única fonte de ganho relevante e reduzem a garantia técnica:

  | Cesta | UASG-trimestres com índice |
  |---|---:|
  | S1 (atual) | 17.445 |
  | S1+S2 | 17.799 |
  | P1 | 18.492 |
  | cesta candidata (16.248 produtos) | 20.835 |

  Mesmo na cesta candidata, 11 mil UASG-trimestres continuam sem índice: as compras A/AF desses trimestres não têm
  nenhum produto da cesta.

**Foco no desenho:** os 309 eventos da janela, em t0−1 e t0−2.

| Situação | t0−1 | t0−2 |
|---|---:|---:|
| com índice | 94 | 78 |
| sem item S1 | 206 | 112 |
| sem compras A/AF | 0 | 111 |
| causas recuperáveis (homologação, referência, extremos) | < 10 | < 10 |

Eventos com índice em t0−2 e t0−1 ao mesmo tempo, por fonte:

| Fonte | Eventos |
|---|---:|
| atual | 40 |
| referência produto × semestre ou × ano | 41 |
| S1+S2 | 41 |
| P1 | 46 |
| cesta candidata | 65 |

**Conclusão:** a ausência de índice não é, em geral, perda recuperável de dados (homologação, preço ou referência
somam menos de 12% dos casos). Ela reflete o fato de que, na maioria dos trimestres, a UASG não compra produtos S1. A
recuperação possível é pequena: itens em andamento e células de referência mais largas. Ampliar a cesta ajuda de forma
moderada (de 40 para 65 eventos com os dois períodos reservados), em troca de menor homogeneidade técnica.
