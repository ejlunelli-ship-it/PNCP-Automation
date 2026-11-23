# Robustez do corte de dispersão no estudo de eventos A × AF: relatório técnico (23/11/2026)

**Todos os testes são exploratórios.** O corte de dispersão (referência G, dispersão ≤ 0,80) foi sugerido depois de ver os
resultados do estudo principal (`../testes_desenho_causal_20261123/relatorio.md` §12). Nenhuma especificação foi escolhida
pelo valor-p. As definições estão em `protocolo.md`, escrito antes da execução (hash conferido em
`registro_execucao.json`).

Base, eventos e motor são os de 23/11:
- Compras.gov.br, itens de material de 2022-01 a 2026-03;
- janela de 6 meses e cmin = 2;
- controles limpos da mesma esfera;
- pesos de precisão;
- inferência agrupada por órgão (CNPJ), com bootstrap selvagem restrito e pesos de Webb.

O motor novo, item a item, reproduz exatamente os dois modelos de referência:
- **M0:** −1,91 lp [−5,67; +1,93], 152 eventos;
- **M1:** −3,76 lp [−6,67; −0,89], 150 eventos, 144 deles também no M0.

## Resumo dos resultados verificados

1. **O corte por dispersão contemporânea muda a estimativa em cerca de −2 a −2,5 lp, mas essa diferença não é
   significativa.**
   - Nos 144 eventos comuns, M1 − M0 = −2,73 lp (EP 1,91; p = 0,14).
   - Com os mesmos controles, janelas e pesos, excluir as células dispersas muda −2,47 lp na referência A e −2,41 lp na G
     (p = 0,22 e 0,21).
   - A mudança não vem da troca de eventos, de controles nem de pesos: vem dos itens.
2. **O resultado de −3,76 lp depende de medir a dispersão no mesmo trimestre da compra.**
   - **Dispersão anterior à janela** (só preços de outras UASGs antes do evento): −1,40 lp [−5,58; +2,86], p = 0,50.
   - **Ponderação contínua** por essa dispersão: −0,57 lp, p = 0,76.
   - **Produtos de apresentação padronizada**, critério sem preço: −1,97 lp, p = 0,34.

   As três ficam perto do M0, não do M1.
3. **Não há heterogeneidade formal por dispersão histórica.** Baixa menos alta: −3,36 lp (EP 4,23; p = 0,44). Por faixa
   de dispersão: −2,33, −2,87, −0,45 e +1,79 lp, nenhuma significativa.
4. **Inferência e influência não explicam a diferença.**
   - Os sete métodos de inferência concordam: M1 tem p de 0,009 a 0,048 e M0 de 0,32 a 0,40.
   - Nenhum órgão domina: retirando um de cada vez, M1 fica entre −4,39 e −3,33 lp, e há 22 a 25 órgãos efetivos.
5. **Na troca para o AF, a composição muda um pouco.**
   - Cai a parcela de medicamentos: −3,2 p.p., p = 0,006, Holm 0,09.
   - Cai a sobreposição de produtos com a pré-janela: −3,7 p.p., p = 0,035.
   - O estimado sobe: +3,0 lp, p = 0,06.
   - Cai a parcela elegível ao filtro: −2,2 p.p. no M1 (p = 0,13) e −2,6 p.p. na amostra do teste 04 (p = 0,07).

   O filtro não é totalmente independente da troca.
6. **O método de estimação importa tanto quanto o filtro.** A imputação de Borusyak–Jaravel–Spiess dá estimativas mais
   negativas em todas as amostras:
   - −3,60 lp com a referência A e todas as células;
   - −5,27 lp no M1.

   Trocar o método acrescenta cerca de −1,7 lp; trocar a amostra, de −1,1 a −2,1 lp. O BJS só imputa itens de produtos
   que as unidades estáveis compram no mesmo trimestre: 16 a 22 mil itens tratados, contra 50 a 67 mil no empilhado.
7. **A validação futura terá pouco poder.** A especificação candidata, fixada antes dos resultados novos, é a
   dispersão pré-tratamento ≤ 0,80.
   - Com os eventos atuais, o efeito mínimo detectável é de 6,1 lp.
   - Com os eventos futuros já detectados (≈ 27 utilizáveis), sobe para 13,2 lp; somando mais 12 meses de trocas
     (≈ 64), fica em 8,5 lp.
   - Um teste só com dados novos não distingue efeitos de 2 a 4 lp.

**Leitura.** O −3,76 lp não é robusto. Ele aparece quando a dispersão é medida no mesmo trimestre e some quando a
classificação usa só informação anterior à troca, quando a dispersão vira peso contínuo ou quando os produtos são
escolhidos sem olhar preço. As estimativas pontuais seguem quase todas negativas, de 0 a −5 lp. O efeito do AF no preço
continua compatível com zero e com reduções de até ≈ 5%. A divergência entre o empilhado e o BJS merece investigação
própria.

## Comparação explícita com −1,91 e −3,76 lp

| Especificação | coef (lp) | IC95 | p | eventos | órgãos (efetivos) | Δ vs −1,91 | Δ vs −3,76 |
|---|---:|---|---:|---:|---:|---:|---:|
| M0 original | −1,91 | [−5,67; 1,93] | 0,321 | 152 | 70 (24,7) | 0,00 | 1,85 |
| M1 filtrado | −3,76 | [−6,67; −0,89] | 0,012 | 150 | 68 (23,0) | −1,85 | 0,00 |
| 01 · M0, 144 eventos comuns | −1,19 | [−4,94; 2,71] | 0,536 | 144 | 66 (23,9) | 0,72 | 2,57 |
| 01 · M1, 144 eventos comuns | −3,92 | [−6,83; −0,90] | 0,016 | 144 | 66 (22,9) | −2,01 | −0,16 |
| 02 · G ≤ 0,80, pesos de M0 | −3,74 | [−6,68; −0,67] | 0,019 | 143 | 66 (24,1) | −1,83 | 0,02 |
| 02 · G ≤ 0,80, pesos iguais | −2,95 | [−6,81; 0,62] | 0,100 | 143 | 66 (20,1) | −1,04 | 0,81 |
| 03 · A ≤ 0,80, controles idênticos | −4,38 | [−7,37; −1,20] | 0,010 | 152 | 70 (24,7) | −2,47 | −0,62 |
| 03 · G ≤ 0,80, controles idênticos | −4,03 | [−7,05; −1,14] | 0,007 | 161 | 75 (25,3) | −2,12 | −0,27 |
| **04 · dispersão pré-tratamento ≤ 0,80** | **−1,40** | [−5,58; 2,86] | 0,502 | 122 | 60 (22,4) | 0,51 | 2,36 |
| 07 · ponderação contínua | −0,57 | [−4,32; 3,42] | 0,764 | 132 | 63 (24,1) | 1,34 | 3,19 |
| 08 · H1, apresentação padronizada | −1,97 | [−6,46; 2,18] | 0,337 | 140 | 67 (22,8) | −0,06 | 1,79 |
| 08 · H1 ∩ dispersão ≤ 0,80 | −4,13 | [−7,98; −0,68] | 0,017 | 127 | 59 (20,7) | −2,22 | −0,37 |
| 14 · BJS, ref. A, todas as células | −3,60 | [−7,02; −0,17]¹ | 0,038 | 151 | 69 (24,6) | −1,69 | 0,16 |
| 14 · BJS, ≤ 0,80, pesos de precisão | −5,27 | [−7,93; −2,60]¹ | < 0,001 | 149 | 68 (23,0) | −3,36 | −1,51 |

O IC é do bootstrap selvagem restrito por órgão; o p também é do WCR. ¹ IC por t(G − 1) com EP agrupado por órgão.

![Estimativas dos testes](graficos/g1_coeficientes.svg)

## Resultados por teste

### 01. Amostra comum

Os 144 eventos presentes em M0 e M1: M0 dá −1,19 lp [−4,94; +2,71] e M1 dá −3,92 lp [−6,83; −0,90]. A diferença M1 − M0 é
−2,73 lp (EP 1,91), com IC95 do bootstrap selvagem não restrito de [−6,36; +0,90] e p = 0,14. Ficaram de fora 8 eventos
de M0 e 6 de M1. Restringir aos eventos comuns aumenta a distância, mas ela continua sem significância.

### 02. Pesos fixos

Em 143 eventos comuns às quatro combinações (diferença contra "A, todas" entre parênteses):

| Referência e células | Pesos de M0 congelados | Pesos iguais |
|---|---:|---:|
| A, todas | −1,13 (p 0,56) | −1,10 (p 0,67) |
| A, ≤ 0,80 | −3,68 (p 0,03); dif. −2,55, p 0,20 | −3,00 (p 0,15); dif. −1,90, p 0,41 |
| G, todas | −2,02 (p 0,32); dif. −0,88, p 0,42 | −1,75 (p 0,46); dif. −0,65, p 0,69 |
| G, ≤ 0,80 | −3,74 (p 0,02); dif. −2,61, p 0,17 | −2,95 (p 0,10); dif. −1,85, p 0,48 |

- Quase toda a mudança vem da exclusão das células dispersas. A troca de referência pesa pouco.
- Com pesos iguais, a mudança encolhe e a estimativa filtrada perde significância.
- Nenhuma diferença é significativa.

### 03. Controles idênticos

Mantidos os eventos, as janelas, as unidades de controle e os pesos do modelo com todas as células:

| Referência | Todas as células | Só ≤ 0,80 | Diferença | Controles mantidos | Eventos perdidos |
|---|---:|---:|---:|---:|---:|
| A | −1,91 | −4,38 [−7,37; −1,20] | −2,47 (EP 2,03; p 0,22) | 99,3% | 0 |
| G | −1,61 | −4,03 [−7,05; −1,14] | −2,41 (EP 1,92; p 0,21) | 99,5% | 0 |

O efeito da exclusão não vem de mudanças nos controles nem nos eventos. Vem de quais itens entram nas médias.

### 04. Dispersão pré-tratamento

Para cada item, D é a mediana, nos até 4 trimestres inteiros antes da janela, do desvio-padrão entre as outras UASGs do log
do preço médio. A própria UASG fica de fora, e cada trimestre precisa de pelo menos 3 outras UASGs.

| Medida | Valor |
|---|---|
| Efeito do AF | **−1,40 lp** [−5,58; +2,86], p = 0,50 |
| Eventos | 122 (59 A → AF, 63 AF → A), 119 deles no M0 |
| Órgãos | 60 (22,4 efetivos) |
| Itens G das tratadas com D | 75,5% (24,5% sem histórico suficiente) |
| Itens que passam (D ≤ 0,80) | 62% |
| Concordância com a classificação contemporânea | 81% |
| Diferença contra M1 nos eventos comuns | +2,36 lp (EP 1,74; p 0,16) |

Esta é a versão em que a classificação não usa nenhuma informação do período da troca. O efeito volta à magnitude do
original.

![Dispersão](graficos/g4_dispersao.svg)

### 05. Heterogeneidade formal

- **Pareada por evento:** são 92 eventos com itens nas duas faixas, com pesos de M0. D ≤ 0,80 dá −1,15 lp e D > 0,80 dá
  +2,21 lp. A diferença é −3,36 lp (EP 4,23; IC [−11,44; +4,72]; p = 0,44).
- **Por faixa** (95 a 98 eventos cada):

  | D ≤ 0,27 | 0,27 < D ≤ 0,46 | 0,46 < D ≤ 0,80 | D > 0,80 |
  |---:|---:|---:|---:|
  | −2,33 (p 0,34) | −2,87 (p 0,14) | −0,45 (p 0,87) | +1,79 (p 0,70) |

O sinal vai de negativo nas faixas de baixa dispersão a positivo na alta, mas não há evidência estatística de diferença.

![Faixas](graficos/g5_faixas.svg)

### 06. Composição

Efeito do AF sobre características das compras: eventos e controles do modelo, pesos congelados e Holm entre as 15
medidas.

| Característica | M1 | Amostra do teste 04 |
|---|---|---|
| Parcela de medicamentos (6505) | **−3,23 p.p. (p 0,006; Holm 0,09)** | **−3,07 p.p. (p 0,005; Holm 0,07)** |
| Sobreposição de produtos com a pré-janela | −3,73 p.p. (p 0,035) | −4,28 p.p. (p 0,053) |
| Dissimilaridade de classes (Duncan) | +7,30 p.p. (p 0,068) | +7,81 p.p. (p 0,083) |
| Índice do estimado (eR) | +2,98 lp (p 0,059) | +3,08 lp (p 0,064) |
| Parcela elegível ao filtro (contemporânea) | −2,23 p.p. (p 0,13) | −2,62 p.p. (p 0,074) |
| Parcela elegível pela dispersão histórica | −1,50 p.p. (p 0,20) | −1,53 p.p. (p 0,13) |
| log do nº de itens por compra | −7,2 lp (p 0,23) | −6,2 lp (p 0,26) |

Ficaram perto de zero (p ≥ 0,27): índice de quantidade, log da quantidade, parcela com índice G, unidade "UNIDADE", parcela
médica 65xx, nível de mercado do produto, ME/EPP exclusivo e sigilo.

Nenhuma medida resiste a Holm a 5%, mas há sinais consistentes nas duas amostras:
- o mix muda mais que nos controles, com menos medicamentos e menos produtos repetidos;
- o estimado sobe;
- cai um pouco a fração de itens que passam no filtro.

Selecionar itens por dispersão pode, portanto, interagir com a troca.

### 07. Ponderação contínua

Função fixada no protocolo: w = 1/D̃², com D̃ = min(max(D; 0,20); 1,50) e razão máxima/mínima entre pesos de 56. A
mediana do peso por item é 6,1.

| Versão | Efeito do AF | Eventos |
|---|---|---:|
| Contínua | −0,57 lp [−4,32; +3,42], p 0,76 | 132 |
| Corte D ≤ 0,80 | −1,40 lp | 122 |

A diferença entre as duas é +1,02 lp (EP 1,46; p 0,48).

### 08. Homogeneidade dos produtos

Critério sem preço: CATMAT com pelo menos 20 itens, sendo ≥ 90% deles na mesma unidade de fornecimento, e sem embalagem
genérica nem conteúdo zero. São 28.905 CATMATs, com 58% dos itens com índice G. A descrição resumida não serve como
critério: é o nome genérico do item no catálogo, constante dentro do CATMAT em 98,5% dos códigos.

| Subamostra | Efeito do AF | Eventos | Órgãos |
|---|---|---:|---:|
| H1, apresentação padronizada | −1,97 lp [−6,46; +2,18], p 0,34 | 140 | 67 |
| H2, medicamentos | −8,19 lp [−22,3; +3,0], p 0,10 | 17 | 9 (4,3 efetivos) |
| H1 ∩ dispersão ≤ 0,80 | −4,13 lp [−7,98; −0,68], p 0,017 | 127 | 59 |

H2 tem poucos eventos e não é informativo. Em H1, que não usa preço, o efeito é o do original. Ele só volta a −4 quando se
soma o filtro de dispersão contemporânea.

### 09. Influência dos órgãos

Retirando os eventos de um órgão de cada vez:

| Modelo | Mínimo | Mediana | Máximo | Maior influência | Peso dos 10 maiores | Órgãos efetivos |
|---|---:|---:|---:|---:|---:|---:|
| M0 | −2,52 | −1,92 | −1,40 | 0,6 lp | 55% | 24,7 |
| M1 | −4,39 | −3,74 | −3,33 | 0,6 lp | 56% | 23,0 |
| Teste 04 | −2,01 | −1,43 | −0,60 | 0,8 lp | 58% | 22,4 |

Nenhum órgão explica os resultados; as distribuições não se sobrepõem entre M1 e os outros. Detalhe por órgão em
`tabelas/t09_loo_*.csv`.

![Órgãos](graficos/g3_orgaos.svg)

### 10. Inferência robusta

| Modelo | EP CR1 | p t(G−1) | p WCR Webb | p WCR Rademacher | p WCU | p jackknife | p aleatorização |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 1,90 | 0,320 | 0,321 | 0,325 | 0,327 | 0,323 | 0,399 |
| M1 | 1,46 | 0,012 | 0,012 | 0,013 | 0,009 | 0,013 | 0,048 |
| Teste 04 | 2,08 | 0,503 | 0,502 | 0,505 | 0,497 | 0,510 | 0,520 |
| Teste 07 | 1,87 | 0,763 | 0,764 | 0,766 | 0,766 | 0,767 | 0,782 |

A aleatorização usa, para cada evento, os 20 controles de precisão mais parecida. Os ICs de todos os métodos estão em
`tabelas/t10_inferencia.csv`. A conclusão de cada modelo não depende do método. No M1, a aleatorização fica no limite
(p = 0,048; IC [−7,47; −0,05]).

### 11. Sentidos da troca

| Modelo | A → AF | AF → A | Simetria (soma = 0) |
|---|---|---|---|
| M0 | −0,71 (p 0,80) | +2,95 (p 0,34) | +2,24, p 0,62 |
| M1 | **−5,85 (p 0,007)** | +1,99 (p 0,40) | −3,87, p 0,25 |
| Teste 04 | −2,11 (p 0,48) | +0,85 (p 0,76) | −1,26, p 0,75 |
| Teste 07 | +1,97 (p 0,54) | +2,56 (p 0,23) | +4,52, p 0,23 |

A simetria passa em todos. No M1 o efeito se concentra na entrada no AF. No teste 07 o sinal de A → AF fica invertido,
outra indicação de que a direção do resultado depende da especificação.

### 12. Dinâmica temporal

Base no trimestre −1; IC por t(G − 1).

| Modelo | Pré (trim. −2) | Trim. 0 | Trim. +1 | p conjunto pré | p conjunto pós |
|---|---:|---:|---:|---:|---:|
| M0, 6 meses | +0,53 | −3,14 | −3,12 | 0,88 | 0,50 |
| M1, 6 meses | −1,92 | −4,15 | −5,46 (p 0,04) | 0,57 | 0,12 |
| Teste 04, 6 meses | +0,37 | −2,28 | −0,71 | 0,91 | 0,70 |

Na janela de 12 meses (78 eventos no M0 e 82 no M1):
- M0: pré-tendências com p conjunto 0,22; pós de −4,8 a −7,7 lp, com p conjunto 0,71.
- M1: pré com p 0,86; pós +0,35, −1,69, +2,81 e −5,30 lp, com p conjunto 0,52.

Com 12 meses, o filtro não reforça o efeito.

![Dinâmica](graficos/g2_dinamica.svg)

### 13. Placebos

| Placebo | M1 | Teste 04 |
|---|---|---|
| Pré-tendência (trim. −2) | −1,92 (p 0,57) | +0,37 (p 0,91) |
| Troca fictícia 12 meses antes | +4,06 (p 0,21; 19 eventos) | +2,65 (p 0,54; 14 eventos) |
| Aleatorização no espaço | p 0,048 | p 0,52 |
| Estimado (eR) | +2,98 lp (p 0,059) | +3,08 lp (p 0,064) |
| Quantidade (índice) | +0,30 (p 0,96) | −3,36 (p 0,59) |
| Sobreposição de produtos | −3,73 (p 0,035) | −4,28 (p 0,053) |
| Elegibilidade ao filtro (contemporânea) | −2,23 p.p. (p 0,13) | −2,62 p.p. (p 0,074) |

- A troca fictícia tem poucos eventos (39 válidos, 19 e 14 após os filtros): tem pouco poder.
- No estudo principal, o placebo do estimado dava +1,0 lp (p 0,55). Na amostra filtrada, chega a +3 lp, perto da
  significância, o que é sinal de alerta.

### 14. Estimadores alternativos

Cascata, com a variação a cada passo:

| Caminho 1 | lp | Δ | Caminho 2 | lp | Δ |
|---|---:|---:|---|---:|---:|
| M0 empilhado | −1,91 | | M0 empilhado | −1,91 | |
| + referência G | −1,61 | +0,30 | + método BJS (itens A, eventos de M0) | −3,60 | −1,69 |
| + amostra ≤ 0,80 (M1) | −3,76 | −2,15 | + itens G, todas as células | −4,13 | −0,54 |
| + pesos iguais | −3,01 | +0,74 | + amostra ≤ 0,80 | −5,27 | −1,13 |
| + método BJS | −4,69 | −1,68 | + pesos iguais | −4,69 | +0,58 |

- Nos dois caminhos, trocar o método acrescenta ≈ −1,7 lp, e o filtro de −1,1 a −2,1 lp.
- O BJS (efeitos fixos de unidade/janela e de produto × trimestre nas unidades estáveis no modo de partida) só imputa itens
  cuja célula tem pelo menos 3 itens não tratados: 16 a 22 mil itens tratados, contra 50 a 67 mil no empilhado.
- Parte da diferença de método pode ser de amostra de itens. Separar as duas exigiria rodar o empilhado nos mesmos itens
  imputáveis; isso não foi feito.

### 15. Preparação da validação

**Especificação candidata única**, fixada no protocolo antes de qualquer resultado novo:
- referência G e dispersão pré-tratamento D ≤ 0,80;
- DiD empilhado com janela de 6 meses e cmin = 2 após o filtro;
- controles limpos do protocolo de 23/11 e pesos de precisão;
- τ_AF agregado, bilateral, 5%, WCR por órgão;
- testes de falsificação F1–F4.

O teste confirmatório **não** foi executado.

Poder pelo modelo de variância dos controles placebo (a = 0,0095, b = 0,1646), sem desfecho das tratadas, com correlação
intraclasse por órgão de 0,003:

| Cenário | Eventos | Efeito mínimo detectável | Poder para −3,76 | Poder para −1,91 |
|---|---:|---:|---:|---:|
| Eventos atuais (referência) | 122 | 6,1 lp | 40% | 14% |
| Futuros já detectados × aproveitamento (47,5%) | ≈ 27 | 13,2 lp | 12% | 6% |
| + 12 meses de novas trocas | ≈ 64 | 8,5 lp | 24% | 9% |
| 150 eventos | 150 | 5,5 lp | 48% | 16% |

**Ainda não usados:**
- 56 eventos datados de 2025-11 a 2026-04 (41 A → AF e 15 AF → A), cujas janelas passam de 2026-03; lista em
  `tabelas/t15_eventos_nao_usados.csv`;
- os itens de 2026-04 a 2026-10, sem CATMAT na base, que exigem nova coleta;
- trocas posteriores a 2026-04;
- os PDFs do Aberto;
- as outras plataformas.

Um teste confirmatório só com dados novos, nos próximos 1–2 anos, terá efeito mínimo detectável de 8 a 13 lp. Ele não
distingue −1,9 de −3,8. Para isso é preciso reduzir o ruído (desenho intraleilão com os PDFs do Aberto) ou acumular vários
anos de trocas.

## Testes não executados, limitações e desvios

- **Executados:** os 15 testes, sem nenhuma falha (`registro_execucao.json`).
- **Não executados:**
  - o teste confirmatório (teste 15), por definição;
  - a janela de 12 meses do teste 04, fora do protocolo;
  - o empilhado restrito aos itens imputáveis pelo BJS, que separaria método de amostra no teste 14 (não previsto no
    protocolo).
- **Teste 08:** o critério por descrição não discrimina (descrição constante no CATMAT). Usou-se a consistência da
  apresentação, também sem preço.
- **Teste 04:**
  - 24,5% dos itens das tratadas não têm dispersão histórica e saem;
  - a amostra fica com 122 eventos, contra 150 no M1;
  - parte da diferença pode ser composição, mas nos eventos comuns a diferença continua em +2,4 lp.
- **Inferência:** os IC por trimestre (teste 12) e os da cascata (teste 14) são por t(G − 1) com EP agrupado. Nos outros
  testes, IC e p vêm do bootstrap selvagem.
- **Teste 13:** a troca fictícia tem poucos eventos.
- **Gráficos:** SVG com dica nativa em cada marca, interativa só quando o arquivo é aberto direto no navegador. Os
  gráficos foram conferidos renderizados (Edge sem interface) e por checagem automática de texto. A versão em tabela de
  cada um está em `tabelas/`.
- **Desvio do protocolo:** nenhum.

## Registro de execução

- **Execução:** 23/11/2026, das 16:24 às 16:40 (962 s), com `python analises/robustez_dispersao_20261123/executar_todos.py`.
- **Status:** os 16 passos (reprodução + 15 testes) terminaram com "ok".
- **Conferências:**
  - M0 e M1 reproduzidos com tolerância de 0,01 lp;
  - todos os CSV gravados, com as linhas esperadas;
  - identidade da diferença no teste 01;
  - hash do protocolo conferido.
- **Exclusões registradas:**
  - teste 01: 8 eventos de M0 e 6 de M1 fora da amostra comum;
  - teste 02: 143 eventos comuns;
  - teste 03: nenhum evento perdido;
  - teste 04: 14.676 itens sem histórico;
  - teste 08: 42 CATMATs excluídos por unidade genérica e 12 por conteúdo zero;
  - teste 13: 39 trocas fictícias válidas.
- O `pncp.db` só foi lido por `preparar_descricoes.py`, com tamanho e mtime iguais. A base e os resultados de 23/11 não
  foram alterados.

## Reprodução

```
python analises/robustez_dispersao_20261123/preparar_descricoes.py --pncp-db ../dados/pncp.db   # uma vez
python analises/robustez_dispersao_20261123/executar_todos.py                                   # comando único
```

## Apêndice: todas as estimativas com os campos padrão

Gerado de `tabelas/todas_estimativas.csv`:
- itens e compras: das unidades tratadas nas janelas;
- UASGs: tratadas / controles distintos;
- órgãos: CNPJs das tratadas;
- efetivos = 1/HHI dos pesos por órgão;
- "—" = não se aplica, como nas medidas por evento e nos controles do BJS.

| Teste | Modelo | coef (lp) | EP | IC95 | p | itens | compras | eventos (A→AF + AF→A) | UASGs trat./ctrl. | órgãos (efetivos) | maior órgão | pesos |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 00 | M0 original (A, todas as células) | −1,91 | 1,90 | [−5,67; 1,93] | 0,321 | 55.617 | 3.671 | 152 (76 + 76) | 133 / 2.142 | 70 (24,7) | 10,1% | precisão |
| 00 | M1 filtrado (G, dispersão ≤ 0,80) | −3,76 | 1,46 | [−6,67; −0,89] | 0,012 | 50.179 | 3.507 | 150 (73 + 77) | 131 / 2.079 | 68 (23,0) | 10,5% | precisão |
| 01 | M0 nos eventos comuns | −1,19 | 1,91 | [−4,94; 2,71] | 0,536 | 55.245 | 3.630 | 144 (71 + 73) | 126 / 2.134 | 66 (23,9) | 10,2% | precisão |
| 01 | M1 nos eventos comuns | −3,92 | 1,48 | [−6,83; −0,90] | 0,016 | 49.706 | 3.436 | 144 (71 + 73) | 126 / 2.076 | 66 (22,9) | 10,7% | precisão |
| 01 | diferença M1 − M0 (eventos comuns) | −2,73 | 1,91 | [−6,36; 0,90] | 0,144 | — | — | 144 | — | 66 | — | precisão de cada modelo |
| 02 | A, todas — pesos congelados de M0 | −1,13 | 1,91 | [−4,87; 2,75] | 0,556 | 55.129 | 3.625 | 143 (70 + 73) | 125 / 2.134 | 66 (24,1) | 10,0% | congelados |
| 02 | A, ≤ 0,80 — pesos congelados de M0 | −3,68 | 1,57 | [−6,76; −0,44] | 0,030 | 41.685 | 3.137 | 143 (70 + 73) | 125 / 2.014 | 66 (24,1) | 10,0% | congelados |
| 02 | G, todas — pesos congelados de M0 | −2,02 | 1,98 | [−6,08; 1,98] | 0,319 | 65.455 | 3.926 | 143 (70 + 73) | 125 / 2.186 | 66 (24,1) | 10,0% | congelados |
| 02 | G, ≤ 0,80 — pesos congelados de M0 | −3,74 | 1,49 | [−6,68; −0,67] | 0,019 | 49.596 | 3.431 | 143 (70 + 73) | 125 / 2.076 | 66 (24,1) | 10,0% | congelados |
| 02 | A, todas — pesos iguais | −1,10 | 2,59 | [−6,07; 4,45] | 0,674 | 55.129 | 3.625 | 143 (70 + 73) | 125 / 2.134 | 66 (20,1) | 17,5% | iguais |
| 02 | A, ≤ 0,80 — pesos iguais | −3,00 | 2,07 | [−7,41; 1,04] | 0,145 | 41.685 | 3.137 | 143 (70 + 73) | 125 / 2.014 | 66 (20,1) | 17,5% | iguais |
| 02 | G, todas — pesos iguais | −1,75 | 2,35 | [−6,50; 3,05] | 0,460 | 65.455 | 3.926 | 143 (70 + 73) | 125 / 2.186 | 66 (20,1) | 17,5% | iguais |
| 02 | G, ≤ 0,80 — pesos iguais | −2,95 | 1,81 | [−6,81; 0,62] | 0,100 | 49.596 | 3.431 | 143 (70 + 73) | 125 / 2.076 | 66 (20,1) | 17,5% | iguais |
| 03 | ref. A: todas as células (controles e pesos do modelo base) | −1,91 | 1,90 | [−5,67; 1,93] | 0,321 | 55.617 | 3.671 | 152 (76 + 76) | 133 / 2.142 | 70 (24,7) | 10,1% | congelados |
| 03 | ref. A: só células ≤ 0,80, mesmos controles, janelas e pesos | −4,38 | 1,55 | [−7,37; −1,20] | 0,010 | 41.974 | 3.169 | 152 (76 + 76) | 133 / 2.134 | 70 (24,7) | 10,1% | congelados |
| 03 | ref. G: todas as células (controles e pesos do modelo base) | −1,61 | 2,03 | [−5,81; 2,50] | 0,425 | 66.729 | 4.068 | 161 (80 + 81) | 141 / 2.197 | 75 (25,3) | 9,6% | congelados |
| 03 | ref. G: só células ≤ 0,80, mesmos controles, janelas e pesos | −4,03 | 1,49 | [−7,05; −1,14] | 0,007 | 50.446 | 3.547 | 161 (80 + 81) | 141 / 2.191 | 75 (25,3) | 9,6% | congelados |
| 04 | G, dispersão pré-tratamento ≤ 0,80 | −1,40 | 2,08 | [−5,58; 2,86] | 0,502 | 37.156 | 2.764 | 122 (59 + 63) | 111 / 1.967 | 60 (22,4) | 11,1% | precisão |
| 05 | D ≤ 0,80 (eventos com as duas faixas; pesos de M0) | −1,15 | 1,98 | [−5,22; 2,95] | 0,573 | 34.070 | 2.480 | 92 (39 + 53) | 83 / 1.916 | 45 (21,4) | 10,7% | congelados |
| 05 | D > 0,80 (mesmos eventos; pesos de M0) | 2,21 | 4,60 | [−6,80; 12,50] | 0,629 | 7.567 | 1.525 | 92 (39 + 53) | 83 / 1.627 | 45 (21,4) | 10,7% | congelados |
| 05 | diferença baixa − alta dispersão (pareada por evento) | −3,36 | 4,23 | [−11,44; 4,72] | 0,436 | — | — | 92 | — | 45 | — | congelados de M0 |
| 05 | faixa D ≤ 0,27 (pesos de precisão próprios) | −2,33 | 2,40 | [−7,11; 2,87] | 0,343 | 11.721 | 1.700 | 95 (44 + 51) | 86 / 1.633 | 44 (19,0) | 11,4% | precisão |
| 05 | faixa 0,27 < D ≤ 0,46 (pesos de precisão próprios) | −2,87 | 1,84 | [−6,44; 1,16] | 0,139 | 12.769 | 1.647 | 94 (42 + 52) | 86 / 1.634 | 47 (19,2) | 11,6% | precisão |
| 05 | faixa 0,46 < D ≤ 0,80 (pesos de precisão próprios) | −0,45 | 2,66 | [−5,87; 4,87] | 0,869 | 10.092 | 1.628 | 97 (44 + 53) | 89 / 1.666 | 48 (20,3) | 12,0% | precisão |
| 05 | faixa D > 0,80 (pesos de precisão próprios) | 1,79 | 4,55 | [−7,26; 11,94] | 0,704 | 7.679 | 1.554 | 98 (42 + 56) | 89 / 1.639 | 49 (21,1) | 12,5% | precisão |
| 06 | M1: índice de quantidade | 0,30 | 5,82 | [−11,32; 11,92] | 0,960 | 83.926 | 4.610 | 150 (73 + 77) | 131 / 2.079 | 68 (23,0) | 10,5% | congelados |
| 06 | M1: log da quantidade | −2,01 | 12,75 | [−27,47; 23,44] | 0,881 | 158.135 | 5.877 | 150 (73 + 77) | 131 / 2.079 | 68 (23,0) | 10,5% | congelados |
| 06 | M1: índice do estimado (eR) | 2,98 | 1,60 | [−0,22; 6,18] | 0,059 | 70.378 | 4.011 | 149 (73 + 76) | 130 / 2.077 | 68 (23,2) | 10,6% | congelados |
| 06 | M1: log do nº de itens | −7,22 | 5,69 | [−18,57; 4,13] | 0,229 | 160.473 | 6.042 | 150 (73 + 77) | 131 / 2.079 | 68 (23,0) | 10,5% | congelados |
| 06 | M1: parcela com índice G | −0,72 | 1,45 | [−3,63; 2,18] | 0,633 | 160.473 | 6.042 | 150 (73 + 77) | 131 / 2.079 | 68 (23,0) | 10,5% | congelados |
| 06 | M1: parcela elegível (contemporânea) | −2,23 | 1,38 | [−4,97; 0,52] | 0,132 | 66.231 | 4.011 | 150 (73 + 77) | 131 / 2.079 | 68 (23,0) | 10,5% | congelados |
| 06 | M1: parcela em UNIDADE | 0,93 | 1,72 | [−2,50; 4,36] | 0,603 | 160.473 | 6.042 | 150 (73 + 77) | 131 / 2.079 | 68 (23,0) | 10,5% | congelados |
| 06 | M1: parcela médica (65xx) | 0,67 | 1,63 | [−2,59; 3,93] | 0,705 | 160.473 | 6.042 | 150 (73 + 77) | 131 / 2.079 | 68 (23,0) | 10,5% | congelados |
| 06 | M1: parcela de medicamentos (6505) | −3,23 | 1,07 | [−5,35; −1,10] | 0,006 | 160.473 | 6.042 | 150 (73 + 77) | 131 / 2.079 | 68 (23,0) | 10,5% | congelados |
| 06 | M1: nível de mercado do produto | −4,56 | 9,79 | [−24,11; 14,98] | 0,649 | 66.231 | 4.011 | 150 (73 + 77) | 131 / 2.079 | 68 (23,0) | 10,5% | congelados |
| 06 | M1: ME/EPP exclusivo | 0,04 | 1,68 | [−3,32; 3,40] | 0,979 | 160.473 | 6.042 | 150 (73 + 77) | 131 / 2.079 | 68 (23,0) | 10,5% | congelados |
| 06 | M1: sigilo | 2,73 | 2,09 | [−1,44; 6,91] | 0,274 | 160.473 | 6.042 | 150 (73 + 77) | 131 / 2.079 | 68 (23,0) | 10,5% | congelados |
| 06 | M1: sobreposicao_produtos | −3,73 | 1,68 | [−7,09; −0,37] | 0,035 | — | — | 150 (73 + 77) | 131 / 2.079 | 68 (23,0) | 10,5% | congelados |
| 06 | M1: duncan_classes | 7,30 | 3,42 | [0,48; 14,13] | 0,068 | — | — | 150 (73 + 77) | 131 / 2.079 | 68 (23,0) | 10,5% | congelados |
| 06 | M1: elegivel_historica | −1,50 | 1,14 | [−3,77; 0,78] | 0,200 | — | — | 133 (65 + 68) | 118 / 2.070 | 63 (24,1) | 10,6% | congelados |
| 06 | teste 04: índice de quantidade | −3,36 | 6,02 | [−15,41; 8,69] | 0,592 | 75.116 | 4.116 | 122 (59 + 63) | 111 / 1.967 | 60 (22,4) | 11,1% | congelados |
| 06 | teste 04: log da quantidade | −4,73 | 12,57 | [−29,88; 20,42] | 0,716 | 136.111 | 5.222 | 122 (59 + 63) | 111 / 1.967 | 60 (22,4) | 11,1% | congelados |
| 06 | teste 04: índice do estimado (eR) | 3,08 | 1,69 | [−0,30; 6,46] | 0,064 | 64.853 | 3.623 | 122 (59 + 63) | 111 / 1.967 | 60 (22,4) | 11,1% | congelados |
| 06 | teste 04: log do nº de itens | −6,24 | 5,43 | [−17,11; 4,62] | 0,260 | 138.366 | 5.380 | 122 (59 + 63) | 111 / 1.967 | 60 (22,4) | 11,1% | congelados |
| 06 | teste 04: parcela com índice G | −1,34 | 1,66 | [−4,66; 1,98] | 0,434 | 138.366 | 5.380 | 122 (59 + 63) | 111 / 1.967 | 60 (22,4) | 11,1% | congelados |
| 06 | teste 04: parcela elegível (contemporânea) | −2,62 | 1,37 | [−5,36; 0,12] | 0,074 | 59.920 | 3.574 | 122 (59 + 63) | 111 / 1.967 | 60 (22,4) | 11,1% | congelados |
| 06 | teste 04: parcela em UNIDADE | 1,38 | 1,68 | [−1,98; 4,74] | 0,433 | 138.366 | 5.380 | 122 (59 + 63) | 111 / 1.967 | 60 (22,4) | 11,1% | congelados |
| 06 | teste 04: parcela médica (65xx) | 1,20 | 1,52 | [−1,83; 4,23] | 0,469 | 138.366 | 5.380 | 122 (59 + 63) | 111 / 1.967 | 60 (22,4) | 11,1% | congelados |
| 06 | teste 04: parcela de medicamentos (6505) | −3,07 | 1,01 | [−5,08; −1,06] | 0,005 | 138.366 | 5.380 | 122 (59 + 63) | 111 / 1.967 | 60 (22,4) | 11,1% | congelados |
| 06 | teste 04: nível de mercado do produto | 0,37 | 10,40 | [−20,44; 21,18] | 0,971 | 59.920 | 3.574 | 122 (59 + 63) | 111 / 1.967 | 60 (22,4) | 11,1% | congelados |
| 06 | teste 04: ME/EPP exclusivo | 0,25 | 1,73 | [−3,21; 3,71] | 0,886 | 138.366 | 5.380 | 122 (59 + 63) | 111 / 1.967 | 60 (22,4) | 11,1% | congelados |
| 06 | teste 04: sigilo | 3,65 | 2,37 | [−1,08; 8,39] | 0,173 | 138.366 | 5.380 | 122 (59 + 63) | 111 / 1.967 | 60 (22,4) | 11,1% | congelados |
| 06 | teste 04: sobreposicao_produtos | −4,28 | 2,06 | [−8,40; −0,15] | 0,053 | — | — | 122 (59 + 63) | 111 / 1.967 | 60 (22,4) | 11,1% | congelados |
| 06 | teste 04: duncan_classes | 7,81 | 4,11 | [−0,42; 16,04] | 0,083 | — | — | 122 (59 + 63) | 111 / 1.967 | 60 (22,4) | 11,1% | congelados |
| 06 | teste 04: elegivel_historica | −1,53 | 0,93 | [−3,40; 0,33] | 0,125 | — | — | 122 (59 + 63) | 111 / 1.967 | 60 (22,4) | 11,1% | congelados |
| 07 | corte D ≤ 0,80 (= teste 04) | −1,40 | 2,08 | [−5,58; 2,86] | 0,502 | 37.156 | 2.764 | 122 (59 + 63) | 111 / 1.967 | 60 (22,4) | 11,1% | precisão |
| 07 | ponderação contínua 1/D̃², D̃ ∈ [0,20; 1,50] | −0,57 | 1,87 | [−4,32; 3,42] | 0,764 | 45.783 | 3.221 | 132 (63 + 69) | 118 / 2.072 | 63 (24,1) | 10,3% | precisão |
| 08 | H1: apresentação padronizada | −1,97 | 2,03 | [−6,46; 2,18] | 0,337 | 37.365 | 3.192 | 140 (70 + 70) | 123 / 2.045 | 67 (22,8) | 11,1% | precisão |
| 08 | H2: H1 ∩ medicamentos (6505) | −8,19 | 4,32 | [−22,26; 2,99] | 0,097 | 2.449 | 351 | 17 (8 + 9) | 15 / 202 | 9 (4,3) | 40,3% | precisão |
| 08 | H1 ∩ dispersão ≤ 0,80 | −4,13 | 1,76 | [−7,98; −0,68] | 0,017 | 27.077 | 2.650 | 127 (62 + 65) | 113 / 1.926 | 59 (20,7) | 11,9% | precisão |
| 09 | M0 | −1,91 | — | [—; —] | — | — | — | — | — | 70 (24,7) | — | — |
| 09 | M1 | −3,76 | — | [—; —] | — | — | — | — | — | 68 (23,0) | — | — |
| 09 | T4 | −1,40 | — | [—; —] | — | — | — | — | — | 60 (22,4) | — | — |
| 13 | M1: troca fictícia 12 meses antes (unidade estável) | 4,06 | 3,14 | [−2,66; 11,69] | 0,214 | 6.159 | 613 | 19 (14 + 5) | 19 / 1.199 | 15 (7,6) | 23,5% | precisão |
| 13 | T4: troca fictícia 12 meses antes (unidade estável) | 2,65 | 4,23 | [−8,71; 16,83] | 0,535 | 3.840 | 470 | 14 (10 + 4) | 14 / 1.013 | 12 (5,9) | 28,0% | precisão |
| 14 | caminho 1: S0 M0: empilhado, ref. A, todas as células, precisão | −1,91 | 1,90 | [−5,71; 1,89] | 0,321 | 55.617 | 3.671 | 152 (76 + 76) | 133 / 2.142 | 70 (24,7) | 10,1% | precisão |
| 14 | caminho 1: S1 troca a referência (A → G) | −1,61 | 2,03 | [−5,67; 2,44] | 0,425 | 66.729 | 4.068 | 161 (80 + 81) | 141 / 2.197 | 75 (25,3) | 9,6% | precisão |
| 14 | caminho 1: S2 troca a amostra (todas → ≤ 0,80) = M1 | −3,76 | 1,46 | [−6,67; −0,84] | 0,012 | 50.179 | 3.507 | 150 (73 + 77) | 131 / 2.079 | 68 (23,0) | 10,5% | precisão |
| 14 | caminho 1: S3 troca os pesos (precisão → iguais) | −3,01 | 1,77 | [−6,55; 0,53] | 0,091 | 50.179 | 3.507 | 150 (73 + 77) | 131 / 2.079 | 68 (20,3) | 17,3% | iguais |
| 14 | caminho 1: S4 troca o método (empilhado → BJS), pesos iguais | −4,69 | 1,96 | [−8,61; −0,77] | 0,010 | 16.311 | 1.540 | 149 (72 + 77) | 130 / — | 68 (20,1) | 17,4% | iguais |
| 14 | caminho 1: S4b BJS com pesos de precisão | −5,27 | 1,34 | [−7,93; −2,60] | < 0,001 | 16.311 | 1.540 | 149 (72 + 77) | 130 / — | 68 (23,0) | 10,6% | precisão |
| 14 | caminho 2: P0 M0: empilhado, ref. A, todas, precisão | −1,91 | 1,90 | [−5,71; 1,89] | 0,321 | 55.617 | 3.671 | 152 (76 + 76) | 133 / 2.142 | 70 (24,7) | 10,1% | precisão |
| 14 | caminho 2: P1 troca o método (BJS nos itens com índice A, eventos de M0) | −3,60 | 1,72 | [−7,02; −0,17] | 0,038 | 20.789 | 1.715 | 151 (76 + 75) | 132 / — | 69 (24,6) | 10,1% | precisão |
| 14 | caminho 2: P2 itens com índice G, todas as células (eventos de G, todas) | −4,13 | 1,70 | [−7,53; −0,74] | 0,019 | 21.771 | 1.809 | 160 (80 + 80) | 140 / — | 74 (25,2) | 9,7% | precisão |
| 14 | caminho 2: P3 troca a amostra (≤ 0,80; eventos de M1) | −5,27 | 1,34 | [−7,93; −2,60] | < 0,001 | 16.311 | 1.540 | 149 (72 + 77) | 130 / — | 68 (23,0) | 10,6% | precisão |
| 14 | caminho 2: P4 troca os pesos (iguais) | −4,69 | 1,96 | [−8,61; −0,77] | 0,010 | 16.311 | 1.540 | 149 (72 + 77) | 130 / — | 68 (20,1) | 17,4% | iguais |
