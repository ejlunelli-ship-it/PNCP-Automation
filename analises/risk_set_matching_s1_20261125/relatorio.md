# Risk-set matching + DiD na cesta S1 — relatório

Gerado em 2026-11-25T18:32:04 por `python executar.py`. Protocolo congelado em 2026-11-25T17:48:37 (pares: SHA-256 de conteúdo `a37f3a5875a65b22…`). **SUPORTE INSUFICIENTE pelos critérios predefinidos: estimativas da Fase II são apenas descritivas.**

Integridade do código da Fase I depois do congelamento: todos os arquivos iguais. Testes: 40 executados, 0 falhas, 0 erros.

## A. Amostra

- Banco: `C:\Users\Absalão\Desktop\PNCP\PNCP(arquivos)\PNCP-Automation\dados\pncp_v2.db` (somente leitura; impressão digital idêntica à registrada pelo estudo original e à da cópia em `D:/pncp_v2.db`).
- Cesta S1 (validação automática de catálogo, validador 2.0.0): 3.065 produtos, 74.167 compras, 708.964 itens, 4.141 UASGs antes dos filtros. Nenhum produto S2 entra. S1 não equivale a conferência documental de cada item (S4: só 36 itens).
- Itens com índice A1 (máscara do estudo original, 2023T2–2026T1): 502.993; compras 59.069; produtos 3.053; UASGs 3.889; CNPJs 2.149.
- Regime: 42.436 UASG-trimestres com compras A/AF (2023T1–2026T4); 4.398 mistos (10,4%), com 74.583 das 325.595 compras. Só 52,6% dos UASG-trimestres com compras (2023T2–2026T1) têm índice S1.
- Eventos inequívocos (A→AF ou AF→A entre trimestres inequívocos consecutivos): 612 (A→AF 340, AF→A 272); 120 UASGs com mais de um evento. Situação em t0+1: sem_compras_em_t0+1 193, persistente 179, revertida 99, misto_em_t0+1 82, fora_dos_dados 59.
- Regra do estudo anterior (fração AF ≥ 0,5, persistência 2, painel 2023T1–2026T1): 317 trocas; só 92 são eventos inequívocos, 225 envolvem trimestre misto.

Cobertura do índice por trimestre:

| trimestre | itens | compras | UASGs | CNPJs | itens c/ ref. estáveis local |
|---|---|---|---|---|---|
| 2023T2 | 2014 | 322 | 148 | 65 | 226 |
| 2023T3 | 12479 | 1483 | 533 | 194 | 6937 |
| 2023T4 | 15942 | 1952 | 711 | 246 | 11146 |
| 2024T1 | 26349 | 2488 | 973 | 312 | 18656 |
| 2024T2 | 57071 | 6737 | 1829 | 786 | 50019 |
| 2024T3 | 63063 | 7883 | 2051 | 908 | 59627 |
| 2024T4 | 67964 | 8191 | 2217 | 1198 | 64265 |
| 2025T1 | 51211 | 5377 | 1672 | 957 | 47401 |
| 2025T2 | 50869 | 6375 | 1854 | 996 | 46907 |
| 2025T3 | 62120 | 7820 | 1971 | 1067 | 58695 |
| 2025T4 | 55582 | 6450 | 2041 | 1168 | 51248 |
| 2026T1 | 38329 | 3991 | 1445 | 842 | 32839 |

## B. Conjuntos de risco

Regras (as mesmas para tratadas e controles): regime inequívoco de origem em t0−1; sem trimestre misto ou no destino de t0−6 a t0−2; índice em t0−1 e t0−2 e em ≥ 2 dos 4 trimestres de formação; controles observados e inequívocos na origem em t0; mesma esfera; CNPJ diferente.

| etapa | direção | eventos | UASGs trat. | CNPJs trat. | CNPJs efetivos | UASGs controle | CNPJs controle |
|---|---|---|---|---|---|---|---|
| 1_identificados_na_janela | todas | 309 | 259 | 166 | 31,48 | — | — |
| 1_identificados_na_janela | A->AF | 163 | 161 | 105 | 23,49 | — | — |
| 1_identificados_na_janela | AF->A | 146 | 143 | 99 | 38,76 | — | — |
| 2_historico_suficiente | todas | 9 | 9 | 8 | 7,36 | — | — |
| 2_historico_suficiente | A->AF | 8 | 8 | 7 | 6,40 | — | — |
| 2_historico_suficiente | AF->A | 1 | 1 | 1 | 1,00 | — | — |
| 3_com_controles_no_risco | todas | 9 | 9 | 8 | 7,36 | — | — |
| 3_com_controles_no_risco | A->AF | 8 | 8 | 7 | 6,40 | — | — |
| 3_com_controles_no_risco | AF->A | 1 | 1 | 1 | 1,00 | — | — |
| 4_ps_valido | todas | 9 | 9 | 8 | 7,36 | — | — |
| 4_ps_valido | A->AF | 8 | 8 | 7 | 6,40 | — | — |
| 4_ps_valido | AF->A | 1 | 1 | 1 | 1,00 | — | — |
| 5_suporte_comum | todas | 5 | 5 | 5 | 5,00 | — | — |
| 5_suporte_comum | A->AF | 5 | 5 | 5 | 5,00 | — | — |
| 5_suporte_comum | AF->A | 0 | 0 | 0 | 0,00 | — | — |
| 6_matching_aceito | todas | 5 | 5 | 5 | 5,00 | 15,00 | 12,00 |
| 6_matching_aceito | A->AF | 5 | 5 | 5 | 5,00 | 15,00 | 12,00 |
| 6_matching_aceito | AF->A | 0 | 0 | 0 | 0,00 | 0,00 | 0,00 |
| 7_balanceamento_satisfatorio | todas | 4 | 4 | 4 | 4,00 | 10,00 | 10,00 |
| 7_balanceamento_satisfatorio | A->AF | 4 | 4 | 4 | 4,00 | 10,00 | 10,00 |
| 7_balanceamento_satisfatorio | AF->A | 0 | 0 | 0 | 0,00 | 0,00 | 0,00 |
| 8_placebo_disponivel | todas | 4 | 4 | 4 | 4,00 | 10,00 | 10,00 |
| 8_placebo_disponivel | A->AF | 4 | 4 | 4 | 4,00 | 10,00 | 10,00 |
| 8_placebo_disponivel | AF->A | 0 | 0 | 0 | 0,00 | 0,00 | 0,00 |

Motivos de descarte (desenho principal, M0):

| motivo | eventos |
|---|---|
| histórico de modo incompatível (misto/destino antes de t−1) | 182 |
| preços pré insuficientes (t−1, t−2 ou < mín. trimestres de formação) | 118 |
| fora do suporte comum do propensity score | 4 |
| mantido | 4 |
| balanceamento do evento insatisfatório | 1 |

**Diagnóstico de inviabilidade (só contagens, nada estimado):**

| regime | regra | eventos | cnpjs | adocoes | abandonos |
|---|---|---|---|---|---|
| inequívoco (principal) | principal: histórico de modo + Y(t−1,t−2) + ≥2 de 4 formação | 9 | 8 | 8 | 1 |
| inequívoco (principal) | histórico de modo + Y(t−1,t−2), sem formação | 18 | 16 | 14 | 4 |
| inequívoco (principal) | histórico de modo + Y(t−1) | 45 | 37 | 33 | 12 |
| inequívoco (principal) | sem exigir histórico de modo + Y(t−1,t−2) + ≥2 formação | 17 | 12 | 13 | 4 |
| inequívoco (principal) | sem exigir histórico de modo + Y(t−1,t−2) | 40 | 29 | 24 | 16 |
| inequívoco (principal) | sem exigir histórico de modo + Y(t−1) | 94 | 61 | 56 | 38 |
| inequívoco (principal) | somente histórico de modo compatível | 127 | 94 | 71 | 56 |
| inequívoco (principal) | todos os eventos inequívocos na janela | 309 | 166 | 163 | 146 |
| regra anterior | regra anterior (maioria ≥ 0,5, persistência 2): todos na janela | 119 | 92 | 74 | 45 |
| regra anterior | regra anterior + Y(t−1,t−2) + ≥2 formação | 25 | 23 | 14 | 11 |
| regra anterior | regra anterior + Y(t−1) | 56 | 45 | 38 | 18 |

## C. Matching

| desenho | direção | linhas | tratadas | AUC (diag.) | dp logit | caliper | fora do suporte |
|---|---|---|---|---|---|---|---|
| principal | A->AF | 1971 | 8 | 0,99 | 10,08 | 2,02 | 3 |
| principal | AF->A | 933 | 1 | 1,00 | 9,17 | 1,83 | 1 |
| curta | A->AF | 2813 | 7 | 0,99 | 15,39 | 3,08 | 3 |
| curta | AF->A | 1357 | 1 | 1,00 | 8,66 | 1,73 | 1 |
| S1S2 | A->AF | 2039 | 8 | 0,99 | 9,76 | 1,95 | 3 |
| S1S2 | AF->A | 962 | 1 | 1,00 | 9,11 | 1,82 | 1 |

AUC ≈ 1 com tão poucas tratadas indica separação quase perfeita: o PS não oferece suporte comum confiável.

| desenho | método | eventos | pares | controles | reuso máx. | nº ef. controles | nº ef. CNPJs trat. |
|---|---|---|---|---|---|---|---|
| principal | M0 | 4 | 20 | 10 | 2 | 10,00 | 4,00 |
| principal | M0_k1 | 4 | 4 | 4 | 1 | 4,00 | 4,00 |
| principal | M0_k3 | 4 | 12 | 8 | 2 | 7,20 | 4,00 |
| principal | M1 | 4 | 20 | 11 | 2 | 10,53 | 4,00 |
| principal | PS | 4 | 18 | 9 | 2 | 8,89 | 4,00 |
| principal | PSM | 4 | 18 | 9 | 2 | 8,89 | 4,00 |
| curta | M0 | 2 | 10 | 6 | 2 | 5,56 | 2,00 |
| S1S2 | M0 | 4 | 20 | 11 | 2 | 10,53 | 4,00 |

Balanceamento (adoções, M0; y_* são preços de formação, não usados em M0):

| covariável | SMD antes | SMD depois | razão var. | KS depois |
|---|---|---|---|---|
| log_compras | −1,11 | −0,33 | 0,03 | 0,40 |
| log_itens | −1,27 | −0,22 | 0,33 | 0,35 |
| freq_trimestral | −0,94 | −0,20 | 1,00 | 0,10 |
| log_valor_medio_compra | −1,20 | 0,15 | 0,13 | 0,30 |
| var_log_itens | 1,55 | 0,48 | 0,21 | 0,30 |
| recorrencia_s1 | 0,29 | 0,82 | 0,27 | 0,70 |
| srp | 0,62 | 0,15 | 0,00 | 0,20 |
| sigilo | −0,28 | −0,30 | 0,07 | 0,30 |
| homologacao | 0,33 | 0,14 | 0,03 | 0,40 |
| fracasso | −0,61 | −0,23 | 0,02 | 0,50 |
| y_nivel | 0,29 | 0,23 | 0,52 | 0,30 |
| y_tendencia | 0,25 | −0,08 | 0,04 | 0,40 |
| y_dp | −0,71 | −0,87 | 0,14 | 0,75 |

Covariáveis M0 com |SMD| ≥ 0,10 depois do pareamento: log_compras, log_itens, freq_trimestral, log_itens_por_compra, log_valor_medio_compra, var_log_itens, log_itens_s1, recorrencia_s1, hhi_classes, srp, sigilo, homologacao, fracasso, trimestres_no_regime. Máximo |SMD| = 0,82. O balanceamento NÃO é satisfatório.

## D. Placebos (Fase I, períodos reservados)

| desenho | método | placebo | lp | IC95 | p (t) | p (WCR) | p TOST ±5 | MDE 80% | poder vs ±5 | eventos | clusters |
|---|---|---|---|---|---|---|---|---|---|---|---|
| principal | M0 | reservado_t-2_t-1 | −50,95 | [−118,08; 16,18] | 0,13 | 0,12 | 0,92 | 94,17 | 0,05 | 4 | 14,00 |
| principal | M0 | caracteristica_srp_tri_t-2_t-1 | 0,06 | [−0,03; 0,15] | 0,15 | — | — | 0,12 | — | 4 | 14,00 |
| principal | M0 | caracteristica_sigilo_tri_t-2_t-1 | 0,10 | [−0,13; 0,32] | 0,38 | — | — | 0,32 | — | 4 | 14,00 |
| principal | M0 | caracteristica_logq_tri_t-2_t-1 | 1,80 | [−0,37; 3,96] | 0,10 | — | — | 3,04 | — | 4 | 14,00 |
| principal | M0 | caracteristica_log_compras_tri_t-2_t-1 | −0,80 | [−1,38; −0,23] | 0,01 | — | — | 0,81 | — | 4 | 14,00 |
| principal | M0 | caracteristica_log_itens_tri_t-2_t-1 | −0,75 | [−1,64; 0,14] | 0,09 | — | — | 1,25 | — | 4 | 14,00 |
| principal | M0_k1 | reservado_t-2_t-1 | −39,03 | [−84,65; 6,59] | 0,08 | 0,07 | 0,94 | 62,90 | 0,06 | 4 | 8,00 |
| principal | M0_k1 | caracteristica_srp_tri_t-2_t-1 | 0,00 | [0,00; 0,00] | — | — | — | 0,00 | — | 4 | 8,00 |
| principal | M0_k1 | caracteristica_sigilo_tri_t-2_t-1 | 0,25 | [−0,30; 0,79] | 0,32 | — | — | 0,75 | — | 4 | 8,00 |
| principal | M0_k1 | caracteristica_logq_tri_t-2_t-1 | 0,85 | [−0,88; 2,59] | 0,28 | — | — | 2,39 | — | 4 | 8,00 |
| principal | M0_k1 | caracteristica_log_compras_tri_t-2_t-1 | −0,52 | [−0,90; −0,14] | 0,01 | — | — | 0,52 | — | 4 | 8,00 |
| principal | M0_k1 | caracteristica_log_itens_tri_t-2_t-1 | −0,02 | [−0,70; 0,65] | 0,94 | — | — | 0,93 | — | 4 | 8,00 |
| principal | M0_k3 | reservado_t-2_t-1 | −27,25 | [−65,83; 11,33] | 0,15 | 0,19 | 0,88 | 53,93 | 0,06 | 4 | 12,00 |
| principal | M0_k3 | caracteristica_srp_tri_t-2_t-1 | 0,00 | [0,00; 0,00] | — | — | — | 0,00 | — | 4 | 12,00 |
| principal | M0_k3 | caracteristica_sigilo_tri_t-2_t-1 | 0,08 | [−0,13; 0,29] | 0,41 | — | — | 0,29 | — | 4 | 12,00 |
| principal | M0_k3 | caracteristica_logq_tri_t-2_t-1 | 0,84 | [−0,89; 2,57] | 0,31 | — | — | 2,42 | — | 4 | 12,00 |
| principal | M0_k3 | caracteristica_log_compras_tri_t-2_t-1 | −0,70 | [−1,30; −0,11] | 0,02 | — | — | 0,83 | — | 4 | 12,00 |
| principal | M0_k3 | caracteristica_log_itens_tri_t-2_t-1 | −0,65 | [−1,49; 0,19] | 0,12 | — | — | 1,17 | — | 4 | 12,00 |
| principal | M1 | reservado_t-2_t-1 | −27,61 | [−63,93; 8,72] | 0,13 | 0,15 | 0,90 | 51,02 | 0,06 | 4 | 15,00 |
| principal | M1 | caracteristica_srp_tri_t-2_t-1 | 0,06 | [−0,02; 0,13] | 0,13 | — | — | 0,11 | — | 4 | 15,00 |
| principal | M1 | caracteristica_sigilo_tri_t-2_t-1 | 0,10 | [−0,13; 0,32] | 0,37 | — | — | 0,31 | — | 4 | 15,00 |
| principal | M1 | caracteristica_logq_tri_t-2_t-1 | 1,37 | [−0,26; 3,00] | 0,09 | — | — | 2,29 | — | 4 | 15,00 |
| principal | M1 | caracteristica_log_compras_tri_t-2_t-1 | −0,71 | [−1,18; −0,24] | 0,01 | — | — | 0,66 | — | 4 | 15,00 |
| principal | M1 | caracteristica_log_itens_tri_t-2_t-1 | −0,57 | [−1,40; 0,26] | 0,16 | — | — | 1,17 | — | 4 | 15,00 |
| principal | PS | reservado_t-2_t-1 | −27,10 | [−64,73; 10,54] | 0,14 | 0,17 | 0,89 | 52,71 | 0,06 | 4 | 13,00 |
| principal | PS | caracteristica_srp_tri_t-2_t-1 | 0,00 | [0,00; 0,00] | — | — | — | 0,00 | — | 4 | 13,00 |
| principal | PS | caracteristica_sigilo_tri_t-2_t-1 | 0,12 | [−0,16; 0,40] | 0,37 | — | — | 0,39 | — | 4 | 13,00 |
| principal | PS | caracteristica_logq_tri_t-2_t-1 | 0,85 | [−0,94; 2,64] | 0,32 | — | — | 2,51 | — | 4 | 13,00 |
| principal | PS | caracteristica_log_compras_tri_t-2_t-1 | −0,59 | [−1,18; 0,01] | 0,05 | — | — | 0,83 | — | 4 | 13,00 |
| principal | PS | caracteristica_log_itens_tri_t-2_t-1 | −0,48 | [−1,49; 0,53] | 0,32 | — | — | 1,41 | — | 4 | 13,00 |
| principal | PSM | reservado_t-2_t-1 | −27,10 | [−64,73; 10,54] | 0,14 | 0,17 | 0,89 | 52,71 | 0,06 | 4 | 13,00 |
| principal | PSM | caracteristica_srp_tri_t-2_t-1 | 0,00 | [0,00; 0,00] | — | — | — | 0,00 | — | 4 | 13,00 |
| principal | PSM | caracteristica_sigilo_tri_t-2_t-1 | 0,12 | [−0,16; 0,40] | 0,37 | — | — | 0,39 | — | 4 | 13,00 |
| principal | PSM | caracteristica_logq_tri_t-2_t-1 | 0,85 | [−0,94; 2,64] | 0,32 | — | — | 2,51 | — | 4 | 13,00 |
| principal | PSM | caracteristica_log_compras_tri_t-2_t-1 | −0,59 | [−1,18; 0,01] | 0,05 | — | — | 0,83 | — | 4 | 13,00 |
| principal | PSM | caracteristica_log_itens_tri_t-2_t-1 | −0,48 | [−1,49; 0,53] | 0,32 | — | — | 1,41 | — | 4 | 13,00 |
| curta | M0 | reservado_t-2_t-1 | −23,96 | [−68,04; 20,13] | 0,24 | 0,25 | 0,83 | 60,78 | 0,06 | 2 | 8,00 |
| S1S2 | M0 | reservado_t-2_t-1 | −48,29 | [−116,36; 19,79] | 0,15 | 0,15 | 0,90 | 95,63 | 0,05 | 4 | 15,00 |

No dCDH reestimado na S1 (população e janela diferentes: maioria ≥ 0,5, pesos por item), o placebo l = −1 é 11,69 lp [5,74; 17,63].

| método | eventos | desvio t−2 (trat.) | desvio t−1 (trat.) | gap formação | corr(gap, placebo) |
|---|---|---|---|---|---|
| M0 | 4 | 5,10 | −17,31 | 4,89 | −0,34 |
| M0_k1 | 4 | 5,10 | −17,31 | 6,66 | −0,35 |
| M0_k3 | 4 | 5,10 | −17,31 | −1,17 | 0,08 |
| M1 | 4 | 5,10 | −17,31 | 1,53 | −0,57 |
| PS | 4 | 5,10 | −17,31 | 4,84 | −0,36 |
| PSM | 4 | 5,10 | −17,31 | 4,84 | −0,36 |

## E. Efeitos (Fase II — descritivos)

| spec | grupo | lp | IC95 | p (t) | p (WCR) | eventos | clusters |
|---|---|---|---|---|---|---|---|
| R1 | agregado | 16,21 | [−53,11; 85,53] | 0,57 | 0,54 | 2 | 6,00 |
| R1 | adocao | 16,21 | [−53,11; 85,53] | 0,57 | 0,54 | 2 | 6,00 |
| R1 | abandono_AF | — | — | — | — | 0 | — |
| R2 | agregado | 16,21 | [−53,11; 85,53] | 0,57 | 0,54 | 2 | 6,00 |
| R2 | adocao | 16,21 | [−53,11; 85,53] | 0,57 | 0,54 | 2 | 6,00 |
| R2 | abandono_AF | — | — | — | — | 0 | — |
| R3 | agregado | 17,34 | [−37,98; 72,65] | 0,47 | 0,48 | 2 | 7,00 |
| R3 | adocao | 17,34 | [−37,98; 72,65] | 0,47 | 0,48 | 2 | 7,00 |
| R3 | abandono_AF | — | — | — | — | 0 | — |
| R4 | agregado | 17,34 | [−37,98; 72,65] | 0,47 | 0,48 | 2 | 7,00 |
| R4 | adocao | 17,34 | [−37,98; 72,65] | 0,47 | 0,48 | 2 | 7,00 |
| R4 | abandono_AF | — | — | — | — | 0 | — |

R1 (principal): 16,21 lp, IC95 [−53,11; 85,53], com 2 eventos (dos 4 pareados, 2 têm índice em t0 para a tratada e para ao menos um controle). Nenhum abandono sobreviveu; o segundo horizonte não é estimável. 10 dos 20 pares saem do regime de origem (ou ficam mistos/sem compras) em t0+1.

Inferência: CR1 por CNPJ somando todas as participações (tratada e controle) e t(G−1); bootstrap selvagem por CNPJ (Webb, 9999 réplicas, nulidade imposta), condicional aos pares. O pareamento não é refeito: o bootstrap ingênuo de matching com k fixo é inconsistente (Abadie e Imbens, 2008). Com 2 eventos, nenhum desses procedimentos é confiável.

## F. Composição

| id_evento | sobreposicao_itens_pos_com_produto_pre_tratada | jaccard_produtos_tratada | jaccard_produtos_controles | produtos_comuns_tratada | tvd_classes_tratada | tvd_classes_controles | c3_produto_comum_t0_tratada |
|---|---|---|---|---|---|---|---|
| 928737_2026T1 | — | 0,00 | 0,12 | 0,00 | 1,00 | 0,73 | 0,00 |
| 928789_2025T4 | 0,48 | 0,12 | 0,23 | 10,00 | 0,91 | 0,70 | 0,00 |
| 928822_2026T1 | — | 0,00 | 0,12 | 0,00 | 0,97 | 0,73 | 0,00 |
| 928931_2025T4 | 0,78 | 0,27 | 0,23 | 25,00 | 0,86 | 0,70 | 0,00 |

C2 e C3 não são estimáveis: {'R9': {'eventos': 4, 'tratada_sem_suporte': 4, 'sem_controle_com_suporte': 0}, 'R10': {'eventos': 4, 'tratada_sem_suporte': 4, 'sem_controle_com_suporte': 0}}.

## G. Robustez

| spec | descrição | lp | IC95 | eventos | clusters |
|---|---|---|---|---|---|
| R1 | M0 institucional, peso igual por evento (PRINCIPAL) | 16,21 | [−53,11; 85,53] | 2 | 6,00 |
| R2 | M1 (M0 + nível/tendência/dispersão do índice em t−6..t−3) | 16,21 | [−53,11; 85,53] | 2 | 6,00 |
| R3 | propensity score de mudança (caliper 0,2 dp do logit) | 17,34 | [−37,98; 72,65] | 2 | 7,00 |
| R4 | Mahalanobis M0 dentro do caliper do PS | 17,34 | [−37,98; 72,65] | 2 | 7,00 |
| R5 | M0, peso igual por compra (eventos ∝ compras da tratada no horizonte) | 16,21 | [−53,11; 85,53] | 2 | 6,00 |
| R6 | M0, peso igual por item (índice média de itens; eventos ∝ itens) | 34,54 | [−23,15; 92,22] | 2 | 6,00 |
| R7 | M0, somente adoções | 16,21 | [−53,11; 85,53] | 2 | 6,00 |
| R8 | M0, somente abandonos (escala AF − A) | — | — | 0 | — |
| R9 | M0, mesmo produto pré (t−2..t−1) e pós (C3) | — | — | 0 | — |
| R10 | M0, cesta de classes CATMAT fixada no pré (C2) | — | — | 0 | — |
| R11 | M0, referência A1 original da cesta candidata | 16,21 | [−53,11; 85,53] | 2 | 6,00 |
| R12 | M0, referência A1 só com UASGs de regime local estável | 6,99 | [−58,53; 72,51] | 2 | 6,00 |
| R12b | M0, referência EST_A1 do estudo original (estáveis no período todo) | 14,41 | [−56,84; 85,66] | 2 | 6,00 |
| R13 | janela histórica curta (formação t−4..t−3), M0 | 16,77 | [−43,33; 76,88] | 2 | 7,00 |
| R14 | M0, segundo horizonte (t0+1), controles censurados ao sair da origem | — | — | 0 | — |
| R14m | M0, média de t0 e t0+1 (eventos com os dois horizontes) | — | — | 0 | — |
| R15a | M0 sem o CNPJ tratado dominante (todas as participações) | 16,21 | [−53,11; 85,53] | 2 | 6,00 |
| R15b | M0 sem os 3 CNPJs tratados dominantes | 32,75 | [−34,50; 99,99] | 1 | 5,00 |
| R16a | M0 com 1 controle por evento | 9,67 | [−129,69; 149,04] | 2 | 4,00 |
| R16b | M0 com até 3 controles por evento | 14,03 | [−64,75; 92,82] | 2 | 6,00 |
| R17 | cesta S1+S2, M0 (só sensibilidade de classificação técnica) | 17,33 | [−46,63; 81,30] | 2 | 6,00 |
| X1 | M0, só trocas persistentes em t0+1 (selecionado pela trajetória) | — | — | 0 | — |
| X2 | M0, peso inverso ao nº de eventos da mesma UASG | 16,21 | [−53,11; 85,53] | 2 | 6,00 |
| X3 | M0, peso igual por órgão (CNPJ) | 16,21 | [−53,11; 85,53] | 2 | 6,00 |
| X4 | M0, t0+1 com IPW de permanência dos controles (sensibilidade) | — | — | 0 | — |

## Comparação com o estudo anterior na S1

| desenho | eventos | órgãos efetivos | placebo | efeito AF | IC95 | população |
|---|---|---|---|---|---|---|
| dCDH original reestimado em S1 (amostra própria) | 99,00 | 14,84 | 11,69 | −6,46 | [−14,88; 1,95] | trocas pela regra de maioria (≥ 0,5) com persistência 2; pesos por célula (itens); l = 1..2 |
| E3 (efeitos fixos, S1) | — | 25,39 | — | −5,08 | [−7,57; −2,59] | todos os itens S1 (associação condicional) |
| E7 (efeitos fixos, S1) | — | 16,75 | — | −2,16 | [−4,67; 0,35] | todos os itens S1 (associação condicional) |
| Risk-set DiD M0 | 2,00 | 2,00 | −50,95 | 16,21 | [−53,11; 85,53] | eventos inequívocos pareados (h = 0, peso igual por evento) |
| Risk-set DiD M1 | 2,00 | 2,00 | −27,61 | 16,21 | [−53,11; 85,53] | eventos inequívocos pareados (h = 0, peso igual por evento) |
| Matching por propensity score | 2,00 | 2,00 | −27,10 | 17,34 | [−37,98; 72,65] | eventos inequívocos pareados (h = 0, peso igual por evento) |
| Mesmo produto pré/pós (C3, pares M0; placebo = o de M0) | 0,00 | — | −50,95 | — | — | eventos inequívocos pareados (h = 0, peso igual por evento) |

Eventos comuns entre o dCDH e o risk-set estimável: 0. Sem amostra comum, as diferenças não podem ser atribuídas ao estimador.

## H. Identificação causal

Ver `conclusao.md`. Gráficos: `graficos/`. Tabelas completas: `tabelas/`. Pares e protocolo: `resultados/`.

