# Nova rodada exploratória A × AF — cesta P1 validada automaticamente (S1)

Gerado em 2026-11-25T15:37:20 por `executar.py comparar`. Protocolo: [`protocolo.md`](protocolo.md); congelamento antes de acessar preços: `congelamento.json` (2026-11-25T14:02:46); conclusão: [`conclusao.md`](conclusao.md).

> **Exploratório.** Esta rodada NÃO é a execução confirmatória do protocolo anterior (que exigia aprovação técnica humana; a cesta validada humana continua vazia). A população principal é a S1 da validação **automática** de catálogo (validador 2.0.0, execução `b83d3184-118d-5b9b-b732-7e310ff1c631`), que não equivale a validação documental individual. Especificações, janelas, pesos, referências e inferência são exatamente os do estudo anterior (código reutilizado sem modificação).

## 1. Funil (itens homologados, preço positivo, referência A1 válida)

| Amostra | Etapa | Itens | Compras | Produtos | UASGs | CNPJs |
|---|---|---|---|---|---|---|
| S1 | 0_cesta_candidata | 2.137.650 | 129.906 | 16.248 | 4.587 | 2.534 |
| S1 | 1_compras_gov_pregao_eletronico | 2.137.650 | 129.906 | 16.248 | 4.587 | 2.534 |
| S1 | 2_modo_A_ou_AF | 2.124.004 | 129.012 | 16.248 | 4.580 | 2.530 |
| S1 | 3_menor_preco | 2.106.560 | 127.626 | 16.248 | 4.562 | 2.520 |
| S1 | 4_data_abertura_valida | 2.106.560 | 127.626 | 16.248 | 4.562 | 2.520 |
| S1 | 5_homologado | 1.671.032 | 112.859 | 16.247 | 4.435 | 2.447 |
| S1 | 6_preco_positivo | 1.671.008 | 112.857 | 16.247 | 4.435 | 2.447 |
| S1 | 7_produto_no_conjunto_S1 | 556.710 | 63.633 | 3.065 | 3.971 | 2.203 |
| S1 | 8_referencia_A1_valida (amostra analítica) | 509.094 | 59.833 | 3.053 | 3.897 | 2.154 |
| S1S2 | 0_cesta_candidata | 2.137.650 | 129.906 | 16.248 | 4.587 | 2.534 |
| S1S2 | 1_compras_gov_pregao_eletronico | 2.137.650 | 129.906 | 16.248 | 4.587 | 2.534 |
| S1S2 | 2_modo_A_ou_AF | 2.124.004 | 129.012 | 16.248 | 4.580 | 2.530 |
| S1S2 | 3_menor_preco | 2.106.560 | 127.626 | 16.248 | 4.562 | 2.520 |
| S1S2 | 4_data_abertura_valida | 2.106.560 | 127.626 | 16.248 | 4.562 | 2.520 |
| S1S2 | 5_homologado | 1.671.032 | 112.859 | 16.247 | 4.435 | 2.447 |
| S1S2 | 6_preco_positivo | 1.671.008 | 112.857 | 16.247 | 4.435 | 2.447 |
| S1S2 | 7_produto_no_conjunto_S1S2 | 591.674 | 65.566 | 3.172 | 4.006 | 2.218 |
| S1S2 | 8_referencia_A1_valida (amostra analítica) | 542.607 | 61.748 | 3.159 | 3.929 | 2.166 |
| P1 | 0_cesta_candidata | 2.137.650 | 129.906 | 16.248 | 4.587 | 2.534 |
| P1 | 1_compras_gov_pregao_eletronico | 2.137.650 | 129.906 | 16.248 | 4.587 | 2.534 |
| P1 | 2_modo_A_ou_AF | 2.124.004 | 129.012 | 16.248 | 4.580 | 2.530 |
| P1 | 3_menor_preco | 2.106.560 | 127.626 | 16.248 | 4.562 | 2.520 |
| P1 | 4_data_abertura_valida | 2.106.560 | 127.626 | 16.248 | 4.562 | 2.520 |
| P1 | 5_homologado | 1.671.032 | 112.859 | 16.247 | 4.435 | 2.447 |
| P1 | 6_preco_positivo | 1.671.008 | 112.857 | 16.247 | 4.435 | 2.447 |
| P1 | 7_produto_no_conjunto_P1 | 735.091 | 75.756 | 4.122 | 4.089 | 2.261 |
| P1 | 8_referencia_A1_valida (amostra analítica) | 664.170 | 71.055 | 4.109 | 4.008 | 2.211 |
| cesta | 0_cesta_candidata | 2.137.650 | 129.906 | 16.248 | 4.587 | 2.534 |
| cesta | 1_compras_gov_pregao_eletronico | 2.137.650 | 129.906 | 16.248 | 4.587 | 2.534 |
| cesta | 2_modo_A_ou_AF | 2.124.004 | 129.012 | 16.248 | 4.580 | 2.530 |
| cesta | 3_menor_preco | 2.106.560 | 127.626 | 16.248 | 4.562 | 2.520 |
| cesta | 4_data_abertura_valida | 2.106.560 | 127.626 | 16.248 | 4.562 | 2.520 |
| cesta | 5_homologado | 1.671.032 | 112.859 | 16.247 | 4.435 | 2.447 |
| cesta | 6_preco_positivo | 1.671.008 | 112.857 | 16.247 | 4.435 | 2.447 |
| cesta | 7_produto_aprovado | 0 | 0 | 0 | 0 | 0 |
| cesta | 8_referencia_A1_valida (amostra analítica) | 1.308.331 | 98.774 | 15.732 | 4.315 | 2.378 |

Na cesta, a etapa 7 do estudo anterior exigia aprovação humana (0 itens); a amostra analítica dele foi a cesta candidata (etapa 6 + referência A1). Nas novas amostras, a etapa 7 é a pertença ao conjunto.

## 2. Tabela comparativa (amostras próprias)

| Amostra | Produtos | Itens / compras | UASGs | Órgãos efetivos (E3) | Trocas válidas | E3 (IC95) | E7 (IC95) | dCDH agregado (IC95) | p Holm (P) | Placebo −1 agregado (IC95) | HonestDiD RM M̄=0,5 | Sobreposição pré/pós | Peso maior CNPJ (dCDH) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 | 3.053 | 509.094 / 59.833 | 3.897 | 25,4 | 317 (99 em l=1) | -5,08 [-7,57; -2,59] | -2,16 [-4,67; 0,35] | -6,46 [-14,88; 1,95] | 0,397 | 11,69 [5,74; 17,63] | [-29,40; 10,99] inclui 0 | 3,5% | 20,6% |
| S1S2 | 3.159 | 542.607 / 61.748 | 3.929 | 25,5 | 317 (104 em l=1) | -5,26 [-7,77; -2,75] | -2,10 [-4,77; 0,58] | -6,30 [-14,61; 2,01] | 0,413 | 10,75 [4,58; 16,92] | [-28,19; 10,92] inclui 0 | 3,7% | 20,5% |
| P1 | 4.109 | 664.170 / 71.055 | 4.008 | 22,8 | 317 (115 em l=1) | -5,57 [-7,93; -3,21] | -2,52 [-5,12; 0,07] | -2,18 [-8,87; 4,51] | 1,000 | 15,17 [7,97; 22,36] | [-23,47; 15,39] inclui 0 | 3,4% | 23,1% |
| cesta | 15.732 | 1.308.331 / 98.774 | 4.315 | 23,5 | 317 (145 em l=1) | -5,96 [-8,39; -3,53] | -2,86 [-5,90; 0,17] | -4,58 [-9,15; -0,02] | 0,148 | 14,24 [5,71; 22,77] | [-22,35; 14,06] inclui 0 | 2,6% | 21,1% |

lp = log-pontos (100·Δln); % exato = 100(e^{β/100} − 1). Detalhes em `tabelas/comparacao_amostras.csv`.

### Adoção × abandono e placebos

| Amostra | Adoção | Holm P | Abandono | Holm P | Placebo −1 adoção | Holm F | Placebo −1 abandono | Holm F | HonestDiD SD M=0 (abandono) |
|---|---|---|---|---|---|---|---|---|---|
| S1 | -9,43 [-24,17; 5,32] | 0,397 | -3,10 [-7,82; 1,62] | 0,397 | 9,73 [0,20; 19,27] | 0,091 | 13,58 [6,27; 20,89] | 0,001 | [-0,02; 22,72] inclui 0 |
| S1S2 | -8,94 [-22,88; 5,00] | 0,413 | -3,26 [-8,31; 1,78] | 0,413 | 9,15 [0,36; 17,94] | 0,083 | 12,34 [3,67; 21,02] | 0,016 | [-4,75; 21,00] inclui 0 |
| P1 | -5,33 [-18,07; 7,41] | 1,000 | 1,28 [-3,75; 6,32] | 1,000 | 8,59 [0,14; 17,04] | 0,092 | 22,11 [9,26; 34,96] | 0,002 | [3,15; 25,99] exclui 0 |
| cesta | -5,05 [-12,30; 2,19] | 0,215 | -4,09 [-9,07; 0,89] | 0,215 | 7,29 [-2,46; 17,04] | 0,285 | 20,91 [10,57; 31,24] | 0,000 | [0,83; 25,17] exclui 0 |

### Ponderação, janela, órgão dominante e referências

| Amostra | dCDH célula | dCDH peso por evento | dCDH por compra | dCDH 12m | Maior CNPJ na variação de E3 | E3 sem ele | CNPJs efetivos (dCDH) | E3 nas 14 referências (comum) | menor p Holm das diferenças |
|---|---|---|---|---|---|---|---|---|---|
| S1 | -6,46 | -4,13 | -1,84 | -6,16 | 00394452000103 (17,2%) | -4,46 | 14,8 | -5,34 a -5,04 | 0,015 |
| S1S2 | -6,30 | -2,21 | -1,10 | -5,83 | 00394452000103 (17,1%) | -4,71 | 14,9 | -5,50 a -5,21 | 0,014 |
| P1 | -2,18 | 1,21 | -0,78 | -2,21 | 00394452000103 (18,6%) | -5,03 | 13,1 | -5,75 a -5,50 | 0,019 |
| cesta | -4,58 | -4,24 | -2,01 | -3,15 | 00394452000103 (18,3%) | -5,31 | 15,1 | -6,08 a -5,80 | 0,029 |

## 3. Decomposição: eventos comuns, seleção de produtos e órgãos

| Amostra | Eventos | dCDH agregado (IC95) | Placebo −1 (IC95) | Eventos l=1 | CNPJs | CNPJs efetivos | Peso maior CNPJ | Itens |
|---|---|---|---|---|---|---|---|---|
| S1 | propria | -6,46 [-14,88; 1,95] | 11,69 [5,74; 17,63] | 99 | 69 | 14,8 | 20,6% | 509.094 |
| S1S2 | propria | -6,30 [-14,61; 2,01] | 10,75 [4,58; 16,92] | 104 | 75 | 14,9 | 20,5% | 542.607 |
| S1S2 | eventos_S1 | -6,40 [-14,70; 1,90] | 10,83 [4,46; 17,20] | 99 | 69 | 14,8 | 20,6% | 542.607 |
| P1 | propria | -2,18 [-8,87; 4,51] | 15,17 [7,97; 22,36] | 115 | 79 | 13,1 | 23,1% | 664.170 |
| P1 | eventos_S1 | -3,16 [-10,90; 4,57] | 11,98 [5,03; 18,93] | 99 | 69 | 14,5 | 21,1% | 664.170 |
| cesta | propria | -4,58 [-9,15; -0,02] | 14,24 [5,71; 22,77] | 145 | 103 | 15,1 | 21,1% | 1.308.331 |
| cesta | eventos_S1 | -5,31 [-10,02; -0,60] | 9,12 [2,67; 15,58] | 102 | 69 | 15,5 | 20,3% | 1.308.331 |

'eventos_S1' = mesmos switchers (UASGs) com peso na S1; controles inalterados. A diferença cesta → S1 se decompõe em redução de eventos (cesta|eventos_S1 − cesta|propria) e seleção de produtos dentro dos mesmos eventos (S1|propria − cesta|eventos_S1).

## 4. Composição dos conjuntos (diagnóstico; não altera a classificação)

| Grupo | Produtos | Itens | Compras | UASGs | Compras/produto (mediana) | Quantidade (mediana) | Órgãos efetivos | Maior órgão | Fração de compras AF | Classe mais frequente |
|---|---|---|---|---|---|---|---|---|---|---|
| S1 | 3.065 | 708.964 | 74.167 | 4.141 | 134 | 351 | 33,7 | 13,9% | 35,8% | 6505 |
| S2 | 107 | 43.863 | 15.361 | 2.751 | 149 | 900 | 27,6 | 15,3% | 31,2% | 6505 |
| P1_inconclusivos | 950 | 180.650 | 40.312 | 3.454 | 122 | 150 | 23,4 | 17,0% | 34,7% | 6550 |
| P1 | 4.122 | 933.477 | 88.110 | 4.257 | 131 | 302 | 31,2 | 14,6% | 36,0% | 6505 |
| cesta | 16.248 | 2.137.650 | 129.906 | 4.587 | 69 | 200 | 34,4 | 14,3% | 37,1% | 6505 |

Classes, anos e categorias de risco por grupo: `tabelas/composicao_classes.csv`, `composicao_anos.csv`, `composicao_riscos.csv`.

## 5. Arquivos

- `amostras/<amostra>/`: saídas completas do código do estudo anterior para cada amostra (efeitos_fixos.csv, estudo_eventos.csv, honestdid.csv, referencias_alternativas.csv, robustez.csv, descritivas.csv, tabelas/, funil).
- `tabelas/`: comparação, decomposição, composição, conjuntos. `graficos/`: comparação e decomposição.
- Reprodução: `..\..\.venv\Scripts\python.exe executar.py tudo` (≈ horas; usa a amostra analítica do estudo anterior, congelada por SHA-256).

