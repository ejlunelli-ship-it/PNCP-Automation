# Associação entre os modos Aberto e Aberto-Fechado e o preço homologado — cesta S1, efeitos fixos M1–M5

Gerado em 2026-11-25T20:09:48 por `python executar.py`. **Todas as estimativas são associações condicionais**; nenhuma tem interpretação causal automática (a escolha do modo é endógena). Testes automatizados: 24 executados, 0 falhas, 0 erros.

## 1. Dados e amostra

- **Banco:** `C:\Users\Absalão\Desktop\PNCP\PNCP(arquivos)\PNCP-Automation\dados\pncp_v2.db`, aberto só para leitura; a impressão digital confere com a registrada pelo estudo original.
- **Itens:** vêm da amostra S1 da rodada `efeito_modos_cesta_auto_S1_20261125`. Foram reconferidos compra a compra contra a tabela `compras` do banco:
  - 74.167 compras, todas de Compras.gov.br e Pregão Eletrônico;
  - 0 divergências de modo, UASG, CNPJ e UF.
- **Referência externa:** a amostra é **anterior** ao filtro A1 (sem exigência de referência e sem a máscara |Y| ≤ ln 10).
- **UF:** compras.uf = unidadeOrgaoUfSigla (UF administrativa da unidade compradora). Não há UF de entrega no banco (itens não têm local de entrega; extracao_parser.uf está vazio). **Limitação:** a dimensão geográfica é a da unidade compradora, não a do local de entrega.
- **Unidade de observação:** compra × produto S1, com 485.369 observações.
  - 43.110 observações reúnem 114.451 itens duplicados da mesma compra e produto, agregados por preço unitário médio ponderado pela quantidade.
  - Média simples por falta de quantidade: 0.
- **Modo:** é atributo da compra; um único modo por compra, verificado.
- **Período:** todo o período com preço (2023T2–2026T3), sem corte arbitrário. 2026T2 (CATMAT só até 17/04/2026) e 2026T3 (residual) são incompletos, com 10.582 observações; ficam na principal e saem numa sensibilidade.

| Etapa | Critério | Itens | Compras | Produtos | UASGs | CNPJs | UFs |
|---|---|---:|---:|---:|---:|---:|---:|
| 0_itens_S1 | itens licitados dos 3.065 produtos S1 | 708.964 | 74.167 | 3.065 | 4.141 | 2.307 | 27 |
| 1_compras_gov_pregao_eletronico | Compras.gov.br (dados abertos), Pregão Eletrônico — conferido no banco | 708.964 | 74.167 | 3.065 | 4.141 | 2.307 | 27 |
| 2_modo_A_ou_AF | modo Aberto ou Aberto-Fechado (igual ao da compra no banco) | 704.383 | 73.634 | 3.065 | 4.136 | 2.303 | 27 |
| 3_menor_preco | critério menor preço | 698.380 | 72.730 | 3.065 | 4.107 | 2.287 | 27 |
| 4_data_abertura_valida | data de abertura válida (trimestre) | 698.380 | 72.730 | 3.065 | 4.107 | 2.287 | 27 |
| 5_homologado | item homologado | 556.713 | 63.633 | 3.065 | 3.971 | 2.203 | 27 |
| 6_preco_positivo | preço unitário homologado positivo | 556.710 | 63.633 | 3.065 | 3.971 | 2.203 | 27 |
| 7_produto_S1 | produto S1 (nenhum S2) | 556.710 | 63.633 | 3.065 | 3.971 | 2.203 | 27 |
| 8_compra_x_produto | agregação compra × produto (itens duplicados ponderados pela quantidade) | 556.710 | 63.633 | 3.065 | 3.971 | 2.203 | 27 |

## 2. Controlar por CNPJ não é comparar só compras do mesmo CNPJ

- **M1** (UF × produto × trimestre + CNPJ) usa **todas** as observações elegíveis.
  - Compara cada compra com as demais do mesmo produto, na mesma UF e no mesmo trimestre, **de qualquer órgão**, depois de remover o nível médio de preço de cada CNPJ, estimado com todas as compras do órgão (todos os produtos e trimestres).
  - Uma compra AF do órgão g pode ser comparada com uma compra A do órgão h. Basta que o efeito fixo de g e o de h estejam identificados por outras compras, o que vale mesmo em células sem os dois modos. Não restringimos a amostra a células mistas.
  - A hipótese é aditiva: as diferenças de nível entre órgãos são as mesmas em todos os produtos e trimestres.
- **M2** troca o nível do órgão pelo nível do órgão **em cada produto** (CNPJ × produto).
- **M3** (CNPJ × produto × trimestre) compara **apenas** compras do mesmo órgão, do mesmo produto e no mesmo trimestre, ou seja, UASGs diferentes do mesmo órgão ou a mesma UASG em compras distintas. Só identificam as células com os dois modos.
- **M4** acrescenta UASG. A variação passa a ser dentro do órgão e líquida do nível de cada UASG.
- **M5** (UASG × produto × trimestre) compara compras da **mesma UASG**, do mesmo produto e trimestre.

## 3. Resultados principais (com ln q, peso por observação, amostra própria)

| Modelo | Efeitos fixos | β (lp) | % exata | IC95 CR1 CNPJ | p CR1 | p WCR (Webb) | IC95 WCU | EP CGM CNPJ+produto | EP CR1 UF | γ ln q |
|---|---|---:|---:|---|---:|---:|---|---:|---:|---:|
| M1 | UF × produto × trimestre + CNPJ (PRINCIPAL) | **−4,65** | −4,54% | [−6,15; −3,15] | < 0,001 | < 0,001 | [−6,12; −3,17] | 0,79 | 0,52 | −14,35 |
| M2 | UF × produto × trimestre + CNPJ × produto | **−4,96** | −4,84% | [−6,49; −3,44] | < 0,001 | 0,001 | [−6,41; −3,52] | 0,79 | 0,82 | −11,08 |
| M3 | CNPJ × produto × trimestre | **−6,25** | −6,06% | [−7,40; −5,10] | < 0,001 | < 0,001 | [−7,14; −5,36] | 0,60 | 0,73 | −10,51 |
| M4 | CNPJ × produto × trimestre + UASG | **−4,24** | −4,15% | [−6,93; −1,55] | 0,002 | 0,185 | [−7,55; −0,96] | 1,36 | 1,54 | −12,47 |
| M5 | UASG × produto × trimestre (sensibilidade mais restrita) | **1,49** | 1,50% | [−11,23; 14,21] | 0,818 | 0,918 | [−19,37; 22,89] | 6,44 | 6,04 | −13,20 |

| Modelo | Obs. | Singletons removidos | Compras | Produtos | UASGs | CNPJs | UFs | Var. identificadora (% da var. de AF) | Nº ef. CNPJs (G*, ρ=0) | G* ρ=1 | Nº ef. UFs | CNPJ mais influente | UF mais influente |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| M1 | 319.336 | 166.033 | 50.811 | 3.061 | 3.547 | 1.841 | 27 | 30,2% | 15,0 | — | 8,5 | COMANDO DO EXERCITO (22,4%) | SP (21,9%) |
| M2 | 180.355 | 305.014 | 32.146 | 2.946 | 2.672 | 1.035 | 27 | 28,3% | 8,7 | — | 7,5 | COMANDO DO EXERCITO (29,1%) | SP (26,9%) |
| M3 | 178.720 | 306.649 | 25.577 | 3.026 | 2.263 | 462 | 27 | 55,4% | 3,4 | — | 15,7 | COMANDO DO EXERCITO (50,8%) | SP (12,9%) |
| M4 | 178.308 | 307.061 | 25.210 | 3.025 | 1.995 | 448 | 27 | 8,1% | 2,9 | — | 11,8 | COMANDO DO EXERCITO (56,3%) | SP (19,7%) |
| M5 | 23.354 | 462.015 | 6.379 | 1.991 | 838 | 445 | 27 | 9,7% | 5,1 | 5,9 | 3,9 | SECRETARIA DE ESTADO DA SEGURANCA PUBLICA (41,8%) | PR (44,6%) |

G* ρ = 1 não é definido quando o efeito fixo está aninhado no CNPJ (M3 e M4): o choque comum do órgão é absorvido.

## 4. Variantes

| Modelo | principal | sem ln q | peso igual por compra | sem trimestres incompletos |
|---|---|---|---|---|
| M1 | −4,65 [−6,15; −3,15] (n = 319.336) | −5,80 [−7,58; −4,02] (n = 319.336) | −3,93 [−7,13; −0,74] (n = 319.336) | −4,66 [−6,19; −3,13] (n = 315.321) |
| M2 | −4,96 [−6,49; −3,44] (n = 180.355) | −5,23 [−7,37; −3,10] (n = 180.355) | −6,70 [−9,54; −3,85] (n = 180.355) | −5,00 [−6,58; −3,42] (n = 177.000) |
| M3 | −6,25 [−7,40; −5,10] (n = 178.720) | −5,95 [−7,06; −4,85] (n = 178.720) | −6,93 [−8,74; −5,11] (n = 178.720) | −6,30 [−7,45; −5,14] (n = 175.304) |
| M4 | −4,24 [−6,93; −1,55] (n = 178.308) | −4,71 [−5,88; −3,54] (n = 178.308) | −8,12 [−11,58; −4,66] (n = 178.308) | −4,62 [−7,59; −1,64] (n = 174.894) |
| M5 | 1,49 [−11,23; 14,21] (n = 23.354) | −7,29 [−16,22; 1,64] (n = 23.354) | −3,09 [−23,44; 17,27] (n = 23.354) | 1,72 [−11,02; 14,46] (n = 23.268) |

## 5. Amostras comuns

- A amostra de M5 (observações identificáveis em UASG × produto × trimestre) está contida na de todos os outros modelos.
- A amostra de M3 está contida nas de M1, M2 e M4.
- Cada modelo é reestimado nessas amostras, com ln q.

| Modelo | própria | comum M3 | comum M5 |
|---|---|---|---|
| M1 | −4,65 [−6,15; −3,15] (n = 319.336; G* = 15,0) | −5,67 [−7,21; −4,12] (n = 109.609; G* = 6,6) | 0,12 [−10,17; 10,41] (n = 23.345; G* = 6,2) |
| M2 | −4,96 [−6,49; −3,44] (n = 180.355; G* = 8,7) | −5,69 [−7,44; −3,95] (n = 108.274; G* = 6,4) | −0,42 [−11,22; 10,38] (n = 23.110; G* = 6,0) |
| M3 | −6,25 [−7,40; −5,10] (n = 178.720; G* = 3,4) | −6,25 [−7,40; −5,10] (n = 178.720; G* = 3,4) | −1,14 [−12,09; 9,82] (n = 23.090; G* = 6,1) |
| M4 | −4,24 [−6,93; −1,55] (n = 178.308; G* = 2,9) | −4,24 [−6,93; −1,55] (n = 178.308; G* = 2,9) | 1,34 [−10,86; 13,55] (n = 23.088; G* = 5,2) |
| M5 | 1,49 [−11,23; 14,21] (n = 23.354; G* = 5,1) | — | 1,49 [−11,23; 14,21] (n = 23.354; G* = 5,1) |

## 6. Células com os dois modos e suporte de M3, M4 e M5

| Modelo | Célula | Células | Com A e AF | Obs. nelas | Compras nelas | Obs. em células de um só modo | Compras só em células de um modo | CNPJs com células mistas | Nº ef. CNPJs (células) | Maior CNPJ (células) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M1 | uf_prod_tri | 86.233 | 49.940 | 216.707 | 40.993 | 102.629 | 9.818 | 1.793 | 10,0 | 29,8% (COMANDO DO EXERCITO) |
| M1 | cnpj_prod | 154.018 | 12.871 | 123.257 | 21.239 | 196.079 | 29.572 | 253 | 22,6 | 14,9% (COMANDO DO EXERCITO) |
| M1 | cnpj_prod_tri | 227.592 | 13.666 | 67.997 | 13.674 | 251.339 | 37.137 | 94 | 5,8 | 37,3% (COMANDO DO EXERCITO) |
| M1 | uasg_prod_tri | 305.861 | 568 | 1.646 | 301 | 317.690 | 50.510 | 48 | 7,7 | 31,2% (SECRETARIA DE ESTADO DA SEGU) |
| M2 | uf_prod_tri | 44.879 | 24.444 | 116.629 | 24.691 | 63.726 | 7.455 | 963 | 5,9 | 38,8% (COMANDO DO EXERCITO) |
| M2 | cnpj_prod | 38.469 | 10.657 | 105.639 | 19.143 | 74.716 | 13.003 | 236 | 24,2 | 14,0% (COMANDO DO EXERCITO) |
| M2 | cnpj_prod_tri | 95.927 | 11.809 | 59.791 | 12.748 | 120.564 | 19.398 | 92 | 6,5 | 34,6% (COMANDO DO EXERCITO) |
| M2 | uasg_prod_tri | 166.975 | 566 | 1.642 | 301 | 178.713 | 31.845 | 48 | 7,6 | 31,3% (SECRETARIA DE ESTADO DA SEGU) |
| M3 | uf_prod_tri | 97.890 | 13.089 | 59.245 | 14.303 | 119.475 | 11.274 | 262 | 3,7 | 49,8% (COMANDO DO EXERCITO) |
| M3 | cnpj_prod | 16.938 | 8.844 | 149.731 | 20.172 | 28.989 | 5.405 | 98 | 9,7 | 25,2% (COMANDO DO EXERCITO) |
| M3 | cnpj_prod_tri | 43.682 | 23.693 | 115.389 | 16.947 | 63.331 | 8.630 | 97 | 4,4 | 44,1% (COMANDO DO EXERCITO) |
| M3 | uasg_prod_tri | 165.391 | 564 | 1.638 | 297 | 177.082 | 25.280 | 44 | 7,6 | 31,4% (SECRETARIA DE ESTADO DA SEGU) |
| M4 | uf_prod_tri | 97.671 | 13.031 | 59.053 | 14.147 | 119.255 | 11.063 | 254 | 3,7 | 49,9% (COMANDO DO EXERCITO) |
| M4 | cnpj_prod | 16.801 | 8.778 | 149.490 | 19.956 | 28.818 | 5.254 | 89 | 9,6 | 25,4% (COMANDO DO EXERCITO) |
| M4 | cnpj_prod_tri | 43.503 | 23.616 | 115.206 | 16.779 | 63.102 | 8.431 | 88 | 4,3 | 44,2% (COMANDO DO EXERCITO) |
| M4 | uasg_prod_tri | 164.979 | 564 | 1.638 | 297 | 176.670 | 24.913 | 44 | 7,6 | 31,4% (SECRETARIA DE ESTADO DA SEGU) |
| M5 | uf_prod_tri | 6.985 | 666 | 4.512 | 1.420 | 18.842 | 4.959 | 110 | 11,7 | 23,4% (SECRETARIA DE ESTADO DA SEGU) |
| M5 | cnpj_prod | 5.791 | 520 | 6.997 | 1.935 | 16.357 | 4.444 | 52 | 17,6 | 11,2% (SECRETARIA DE ESTADO DA SEGU) |
| M5 | cnpj_prod_tri | 7.511 | 616 | 3.910 | 1.079 | 19.444 | 5.300 | 44 | 8,4 | 28,7% (SECRETARIA DE ESTADO DA SEGU) |
| M5 | uasg_prod_tri | 9.879 | 568 | 1.646 | 301 | 21.708 | 6.078 | 48 | 7,7 | 31,2% (SECRETARIA DE ESTADO DA SEGU) |

**Perdas até a célula identificadora** (das 485.369 observações e 63.633 compras da amostra):

| Modelo | Obs. após singletons | Obs. em células com A e AF | % da amostra | Compras em células com A e AF | % das compras |
|---|---:|---:|---:|---:|---:|
| M3 | 178.720 | 115.389 | 23,8% | 16.947 | 26,6% |
| M4 | 178.308 | 115.206 | 23,7% | 16.779 | 26,4% |
| M5 | 23.354 | 1.646 | 0,3% | 301 | 0,5% |

## 7. Contribuição à variação identificadora

Participação de cada CNPJ em Σ x̃², onde x̃ é AF residualizado nos efeitos fixos e em ln q:

| Modelo | 1º | 2º | 3º | 4º | 5º | top 5 | top 10 |
|---|---|---|---|---|---|---:|---:|
| M1 | COMANDO DO EXERCITO 22,4% | SECRETARIA DE ESTADO DA SA 6,6% | COMANDO DA MARINHA 5,9% | EMPRESA BRASILEIRA DE SERV 4,4% | SAO PAULO SECRETARIA DA AD 4,0% | 43,2% | 57,0% |
| M2 | COMANDO DO EXERCITO 29,1% | SECRETARIA DE ESTADO DA SA 10,3% | SAO PAULO SECRETARIA DA AD 7,3% | COMANDO DA MARINHA 7,1% | EMPRESA BRASILEIRA DE SERV 5,1% | 58,9% | 74,7% |
| M3 | COMANDO DO EXERCITO 50,8% | EMPRESA BRASILEIRA DE SERV 13,6% | EMPRESA BRASILEIRA DE SERV 8,5% | COMANDO DA MARINHA 4,6% | SECRETARIA DE ESTADO DA SA 4,3% | 81,7% | 93,7% |
| M4 | COMANDO DO EXERCITO 56,3% | SAO PAULO SECRETARIA DA AD 10,3% | EMPRESA BRASILEIRA DE SERV 8,2% | SECRETARIA DE ESTADO DA SE 4,6% | COMANDO DA MARINHA 4,3% | 83,7% | 92,9% |
| M5 | SECRETARIA DE ESTADO DA SE 41,8% | INSTITUTO FEDERAL DE EDUCA 8,1% | MUNICIPIO DE RIO DE JANEIR 5,8% | SAO PAULO SECRETARIA DA AD 5,4% | INSTITUTO FEDERAL DE EDUCA 5,1% | 66,1% | 83,6% |

| Modelo | UFs mais influentes |
|---|---|
| M1 | SP 21,9%, PR 15,6%, RJ 15,5%, RS 8,0%, MG 7,6% |
| M2 | SP 26,9%, RJ 15,5%, RS 11,3%, PR 10,1%, TO 7,1% |
| M3 | SP 12,9%, RS 11,5%, RJ 9,4%, MG 7,7%, PR 5,8% |
| M4 | SP 19,7%, PR 10,8%, RS 10,0%, RJ 6,9%, AM 6,0% |
| M5 | PR 44,6%, SP 14,2%, RJ 13,3%, MT 11,4%, MG 3,4% |

## 8. Exclusão de cada um dos 10 CNPJs mais influentes (reestimação integral)

| Modelo | β completo | β mín. sem 1 CNPJ | β máx. sem 1 CNPJ | CNPJ cuja exclusão mais muda β | mudança |
|---|---:|---:|---:|---|---:|
| M1 | −4,65 | −4,84 | −4,21 | COMANDO DO EXERCITO | 0,44 |
| M2 | −4,96 | −5,30 | −4,77 | ESTADO DO PARANA | −0,34 |
| M3 | −6,25 | −6,43 | −5,79 | EMPRESA BRASILEIRA DE SERVIÇOS HOSPITALA | 0,46 |
| M4 | −4,24 | −5,16 | −1,94 | COMANDO DO EXERCITO | 2,30 |
| M5 | 1,49 | −8,71 | 3,19 | SECRETARIA DE ESTADO DA SEGURANCA PUBLIC | −10,20 |

Tabela completa: `tabelas/loo_top10_cnpj.csv`.

## 9. Inferência

- **Regra predefinida (config.json):** significância só é tratada como robusta se CR1 t(G−1) e o bootstrap selvagem restrito (Webb) rejeitarem a 5% e o número efetivo de clusters (Carter–Schnepel–Steigerwald; ρ = 1 quando definido, senão ρ = 0, que coincide com o inverso do Herfindahl das contribuições) não for pequeno (< 20).
- **CR1 por CNPJ:** agrupa todas as compras e UASGs do mesmo órgão. É apresentado como referência, não como definitivo.
- **WCR:** bootstrap selvagem restrito por CNPJ (Webb, 9.999 réplicas), com IC WCU percentil-t.
- **CGM:** variância bidirecional CNPJ + produto. Também há CR1 por UF (27 clusters).
- **Número efetivo de clusters:** de Carter, Schnepel e Steigerwald (2017).
- **Limites do bootstrap:** quando poucos órgãos concentram a variação, o WCR também pode ter tamanho incorreto (MacKinnon e Webb, 2017). Por isso as exclusões de CNPJ entram na avaliação.

| Modelo | p CR1 | p WCR | G* usado | Significância robusta pela regra? | Motivo |
|---|---:|---:|---:|---|---|
| M1 | < 0,001 | < 0,001 | 15,0 | não | G* = 15,0 < 20 |
| M2 | < 0,001 | 0,001 | 8,7 | não | G* = 8,7 < 20 |
| M3 | < 0,001 | < 0,001 | 3,4 | não | G* = 3,4 < 20 |
| M4 | 0,002 | 0,185 | 2,9 | não | WCR não rejeita; G* = 2,9 < 20 |
| M5 | 0,818 | 0,918 | 5,9 | não | CR1 não rejeita; WCR não rejeita; G* = 5,9 < 20 |

## 10. Convergência numérica

- Efeitos fixos múltiplos: LSMR esparso seguido de projeções alternadas até a variação máxima ficar abaixo de 10⁻⁹. Verificação: maior média ponderada residual em qualquer grupo de qualquer efeito fixo.
- Conferência independente por projeções alternadas puras:

| Modelo | β LSMR+MAP | β MAP | diferença | iterações MAP | média residual máx. (LSMR / MAP) |
|---|---:|---:|---:|---:|---|
| M1 | -4.647862 | -4.647862 | 0.00e+00 | 3.998 | 8.0e-10 / 1.0e-09 |
| M2 | -4.963615 | -4.963615 | -0.00e+00 | 8.815 | 1.0e-09 / 1.0e-09 |
| M4 | -4.237666 | -4.237666 | -0.00e+00 | 2.988 | 1.0e-09 / 1.0e-09 |

## 11. Leitura

Ver `conclusao.md`. Gráficos em `graficos/`; tabelas completas em `tabelas/`.

