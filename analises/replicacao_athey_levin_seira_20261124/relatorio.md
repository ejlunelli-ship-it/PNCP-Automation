# Replicação empírica adaptada de Athey, Levin e Seira (2011), Fase 1: relatório (24/11/2026)

**Classificação:** replicação metodológica adaptada e exploratória. **Todas as estimativas são associações ajustadas, não
efeitos causais.**
- O protocolo (`protocolo.md`) foi escrito antes de estimar; o hash está em `registro_execucao.json`.
- Nenhuma especificação foi escolhida pelo valor-p.
- Nada posterior a 2025-10 entrou, o que deixa fora os 56 eventos reservados.
- O `pncp.db` não foi lido, e nada anterior foi alterado.
- O modelo estrutural (Fase 2) não foi executado.

## Resumo objetivo

Diferença AF − Aberto no índice de preço, em lp (negativo = preço menor no AF). EP agrupado por órgão.

| Estimador | Peso por item | Peso igual por compra |
|---|---|---|
| OLS 1–4, amostra completa | −4,2 a −6,2, todos com IC sem zero | −1,4 a −4,2; só OLS 1 e OLS 4 com IC sem zero |
| OLS 1–4, suporte [0,075; 0,925] | −4,0 a −5,5, todos com IC sem zero | −0,2 a −3,4; nenhum com IC sem zero |
| Interações (efeito médio ajustado) | −3,7 a −5,6, todos com IC sem zero | −0,2 a −2,1; nenhum com IC sem zero |
| Matching pelo escore (eq. 7), suporte | −3,1 em (a) | −0,7 a −2,0; nenhum com IC sem zero |
| Regressão mediana na compra | — | −3,0 (suporte) e −3,5 (completa), com IC sem zero |

1. **O que separa os estimadores é a ponderação, não o método.**
   - Com peso por item, OLS e interações concordam: −4 a −6 lp.
   - Com peso igual por compra, OLS e matching concordam: entre 0 e −2,5 lp, sem significância depois dos controles.
   - A associação por item vem sobretudo das compras grandes.
2. **O suporte comum quase não muda as estimativas, mas tira 84% das compras.**
   - Com o histórico da UASG, o escore prevê o modo quase perfeitamente (AUC 0,98), e só 15.014 das 91.897 compras ficam
     em [0,075; 0,925].
   - As faixas 0,05 e 0,10 dão praticamente a mesma amostra.
3. **Depois de controlar a UASG:**
   - por item, a diferença continua: −4,8 lp na amostra completa e −5,4 no suporte;
   - por compra, ela some: −1,6 e −0,2 lp.
4. **Comparação dentro das mesmas UASGs:**
   - só 731 das 4.233 UASGs (17%) usam os dois modos;
   - o matching dentro da UASG casa 9.982 compras de 254 órgãos;
   - o efeito nas AF e o efeito nas A têm sinais opostos (−4,8 e +3,2 lp).

   É uma base fraca e instável.
5. **Concentração da identificação:** a variação de AF que identifica os OLS equivale a 16–22 órgãos efetivos no peso por
   item e a 32–50 no peso por compra, entre 978 e 2.270 CNPJs. Os 5 maiores órgãos têm de 26% a 39% dela.
6. **Seleção dos homologados:** nas compras em que todos os itens com situação final foram homologados, a diferença por
   item some: −0,5 e +1,8 lp, sem significância.
7. **Desfechos secundários:**
   - o desconto sobre o estimado é 3,5 a 5,4 p.p. maior no AF, todos com IC sem zero;
   - log P com efeitos fixos de produto × trimestre: −4,2 a −6,4 lp;
   - homologação, fracasso e deserção: sem diferença depois dos controles.
8. **Comparação com os estudos anteriores:**
   - a especificação do painel de 16/11, nesta amostra, dá −6,2 lp (−6,0%), perto dos −4,5% publicados;
   - nas janelas do estudo de eventos, a comparação antes × depois dentro das UASGs tratadas dá −4,6 lp por compra. O
     estudo de eventos dá −1,91 porque desconta a tendência dos controles.

**Leitura.** É tudo descritivo, e nada recebe interpretação causal. A associação negativa entre AF e preço aparece quando
cada item pesa igual, e é sensível à unidade de análise, à comparação dentro da UASG e à seleção dos itens homologados. O
desenho mais próximo de identificação continua sendo o estudo de eventos: −1,91 lp, sem significância.

## 1. O artigo e a adaptação

**O que o artigo faz** (seções III.C e IV.A, `dados/qje_2Fqjq001.pdf`):
- **Escore:** logit do formato (selado × aberto) com características do lote, preço de reserva e estimativas do serviço
  florestal, dummies de ano, trimestre, área e espécie, e o tamanho da venda como escada de 10 degraus (decis).
- **Suporte:** saem as vendas com escore fora de [0,075; 0,925].
- **Efeito médio**, por três caminhos:
  - (6) OLS;
  - OLS com SEALED × covariáveis e o efeito médio da amostra;
  - (7) matching simétrico pelos 4 vizinhos mais próximos no escore, com EP robustos de Abadie e Imbens (2006).
- **Robustez:** regressão mediana no apêndice.
- **Identificação:** parte da amostra teve formato sorteado (Schuster e Niccolucci, 1994), e o restante se apoia em
  independência condicional.

**Adaptação:**

| Artigo | Esta replicação | Observação |
|---|---|---|
| Venda (leilão) | Compra (pregão), com muitos itens | Escore na compra; desfecho no item (peso por item) ou na média da compra (peso igual por compra) |
| SEALED × aberto | AF × Aberto | Os modos híbridos brasileiros não são os leilões do artigo |
| Preço por unidade de volume | Índice 100[ln P − ref_{c,t,−u}] | Construção validada do projeto, sem alteração |
| Preço de reserva e estimativas | Valor estimado só como sensibilidade (PS4) | Conforme o pedido |
| Tamanho em decis | Decis do nº de itens de material da compra | |
| Área administrativa (dummies) | Histórico AF da UASG nos 12 meses anteriores, esfera e região | Dummies de UASG dão separação perfeita |
| Formato sorteado em parte da amostra | Não há | Toda a identificação depende de independência condicional |
| EP robustos | EP agrupados por órgão (CNPJ); matching também com EP de Abadie e Imbens | Itens e compras do mesmo órgão não são independentes |

## 2. Amostra

| Etapa | Itens | Compras | Compras AF | UASGs | CNPJs |
|---|---:|---:|---:|---:|---:|
| itens de material (registro principal) de pregões eletrônicos A ou AF, base de 23/11 | 4.448.803 | 177.545 | 67.194 | 4.768 | 2.618 |
| abertura de 2023-01 a 2025-10 (sem o período dos eventos reservados) | 3.800.655 | 150.285 | 56.967 | 4.628 | 2.459 |
| julgamento por menor preço | 3.764.487 | 148.415 | 56.166 | 4.604 | 2.453 |
| homologado com preço unitário > 0 | 2.902.803 | 129.949 | 48.850 | 4.470 | 2.384 |
| CATMAT e unidade de fornecimento padronizada | 2.889.059 | 128.584 | 48.318 | 4.463 | 2.384 |
| referência disponível (≥ 5 itens de ≥ 3 outras UASGs no produto × trimestre) | 1.376.437 | 95.143 | 34.891 | 4.285 | 2.295 |
| |índice| ≤ ln 10 (tratamento de extremos validado) | 1.312.671 | 91.897 | 33.681 | 4.233 | 2.270 |
| UASG e CNPJ presentes | 1.312.671 | 91.897 | 33.681 | 4.233 | 2.270 |

- **Período efetivo: 2023-04 a 2025-10.** Antes de 2023-04, a base de 23/11 tem poucas compras (80 a 300 por mês) e
  nenhuma com resultado de item. É um limite de cobertura da fonte, não um filtro.
  - O histórico de 12 meses das primeiras compras usa um 2022 com poucas compras; a categoria "sem histórico" absorve isso.
- **Maior perda:** a cobertura da referência. De 2,89 milhões de itens homologados com produto identificado, 1,38 milhão
  tem produto × trimestre com ≥ 5 itens de ≥ 3 outras UASGs.
- **Itens com índice fora de ±ln 10:** 57.074, nas compras da análise. Só entram na sensibilidade com truncamento em ±3.
- **Amostra de situação final:** 3,41 milhões de itens em 135.549 compras, com 84,8% homologados.

## 3. Modelo 1: logit da escolha do modo (compra)

| Escore | Compras (AF) | Parâmetros | Convergiu | AUC | Pseudo-R² | Brier | escore < 0,075 | 0,075–0,925 | > 0,925 |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| PS1 | 91.897 (33.681) | 54 | sim | 0,660 | 0,056 | 0,216 | 88 | 91.809 | 0 |
| PS2 | 91.897 (33.681) | 61 | sim | 0,981 | 0,769 | 0,042 | 49.873 | 15.014 | 27.010 |
| PS3 | 91.897 (33.681) | 64 | sim | 0,981 | 0,770 | 0,042 | 49.873 | 15.018 | 27.006 |
| PS4 | 91.897 (33.681) | 71 | sim | 0,981 | 0,770 | 0,042 | 49.873 | 15.015 | 27.009 |

Coeficientes do PS2, sem as dummies de trimestre e de grupo, que estão em `tabelas/logit_coeficientes.csv`:

| Variável (PS2) | Coeficiente | EP robusto | EP agrupado (CNPJ) |
|---|---:|---:|---:|
| constante | −0,429 | 0,247 | 0,391 |
| regiao=N | −0,103 | 0,089 | 0,166 |
| regiao=NE | 0,227 | 0,079 | 0,154 |
| regiao=S | 0,036 | 0,084 | 0,211 |
| regiao=SE | 0,124 | 0,077 | 0,186 |
| esfera=E | −0,761 | 0,206 | 0,296 |
| esfera=F | −0,394 | 0,203 | 0,269 |
| esfera=M | −0,443 | 0,206 | 0,291 |
| esfera=N | −0,758 | 0,218 | 0,279 |
| faixa_itens=1 | −0,021 | 0,075 | 0,072 |
| faixa_itens=2 | 0,021 | 0,075 | 0,089 |
| faixa_itens=3 | −0,030 | 0,075 | 0,106 |
| faixa_itens=4 | −0,005 | 0,074 | 0,136 |
| faixa_itens=5 | 0,034 | 0,075 | 0,156 |
| faixa_itens=6 | −0,015 | 0,075 | 0,140 |
| faixa_itens=7 | 0,054 | 0,076 | 0,136 |
| faixa_itens=8 | 0,061 | 0,078 | 0,127 |
| faixa_itens=9 | 0,047 | 0,081 | 0,126 |
| hist_cat=(0,5; 0,9] | 2,306 | 0,045 | 0,180 |
| hist_cat=(0,9; 1) | 4,754 | 0,072 | 0,339 |
| hist_cat=(0; 0,1] | −2,603 | 0,080 | 0,162 |
| hist_cat=0 | −3,456 | 0,058 | 0,137 |
| hist_cat=1 | 5,433 | 0,074 | 0,203 |
| hist_cat=sem histórico | −0,070 | 0,083 | 0,287 |
| med | 0,014 | 0,151 | 0,229 |
| eq0 | 0,057 | 0,010 | 0,029 |
| eq_aus | −0,000 | — | — |
| comp0 | −0,177 | 0,027 | 0,056 |
| comp_aus | 0,000 | 0,000 | 0,000 |
| hist_log_n | −0,098 | 0,017 | 0,074 |

Calibração:

| Decil do escore (PS2) | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| escore médio | 0,006 | 0,008 | 0,010 | 0,012 | 0,017 | 0,131 | 0,546 | 0,960 | 0,984 | 0,990 |
| taxa de AF observada | 0,007 | 0,007 | 0,007 | 0,011 | 0,020 | 0,128 | 0,552 | 0,959 | 0,988 | 0,985 |

- **PS1, sem o histórico da UASG:** o modo é pouco previsível (AUC 0,66; pseudo-R² 0,06).
  - Período, região, esfera, tamanho, objeto, quantidade e competição esperada explicam pouco.
  - Quase todas as compras ficam no suporte.
- **PS2 e seguintes, com o histórico AF da UASG nos 12 meses anteriores:** AUC 0,98 e pseudo-R² 0,77.
  - O histórico domina. Contra UASGs com 10% a 50% de AF no ano anterior, as que usaram só AF têm coeficiente +5,4, e as
    que nunca usaram têm −3,5 (EP agrupado de 0,1 a 0,3).
  - É a persistência institucional do modo.
- **SRP, sigilo e exclusividade (PS3) e o valor estimado (PS4):** quase não acrescentam.
- **Calibração:** boa nos decis (tabela).
- **Variâncias sem raiz:** os indicadores `eq_aus` e `comp_aus` são constantes (nenhuma compra sem quantidade nem sem
  competição), por isso não têm EP.

## 4. Suporte comum

| Escore | Faixa | Compras (AF / A) | Compras excluídas (AF / A) | Itens (excluídos) | UASGs | CNPJs (com AF) | UASGs com os dois modos | compras em UASGs mistas | maior CNPJ | CNPJs efetivos | regra do protocolo |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| PS1 | completa | 91.897 (33.681 / 58.216) | 0 / 0 | 1.312.671 (0) | 4.233 | 2.270 (948) | 731 | 33,5% | 9,1% | 49,6 | ok |
| PS1 | [0,05; 0,95] | 91.897 (33.681 / 58.216) | 0 / 0 | 1.312.671 (0) | 4.233 | 2.270 (948) | 731 | 33,5% | 9,1% | 49,6 | ok |
| PS1 | [0,075; 0,925] | 91.809 (33.674 / 58.135) | 7 / 81 | 1.309.281 (3.390) | 4.216 | 2.235 (943) | 727 | 33,5% | 9,1% | 49,5 | ok |
| PS1 | [0,10; 0,90] | 91.402 (33.636 / 57.766) | 45 / 450 | 1.291.602 (21.069) | 4.095 | 2.101 (913) | 698 | 33,5% | 9,1% | 49,1 | ok |
| PS2 | completa | 91.897 (33.681 / 58.216) | 0 / 0 | 1.312.671 (0) | 4.233 | 2.270 (948) | 731 | 33,5% | 9,1% | 49,6 | ok |
| PS2 | [0,05; 0,95] | 15.464 (6.920 / 8.544) | 26.761 / 49.672 | 255.502 (1.057.169) | 2.524 | 985 (473) | 395 | 65,9% | 8,7% | 37,8 | ok |
| PS2 | [0,075; 0,925] | 15.014 (6.588 / 8.426) | 27.093 / 49.790 | 253.951 (1.058.720) | 2.511 | 978 (468) | 393 | 66,5% | 8,0% | 39,6 | ok |
| PS2 | [0,10; 0,90] | 15.007 (6.583 / 8.424) | 27.098 / 49.792 | 253.927 (1.058.744) | 2.510 | 978 (468) | 393 | 66,5% | 8,0% | 39,6 | ok |
| PS3 | completa | 91.897 (33.681 / 58.216) | 0 / 0 | 1.312.671 (0) | 4.233 | 2.270 (948) | 731 | 33,5% | 9,1% | 49,6 | ok |
| PS3 | [0,05; 0,95] | 15.705 (7.156 / 8.549) | 26.525 / 49.667 | 256.504 (1.056.167) | 2.529 | 987 (475) | 395 | 65,2% | 9,8% | 35,8 | ok |
| PS3 | [0,075; 0,925] | 15.018 (6.591 / 8.427) | 27.090 / 49.789 | 253.955 (1.058.716) | 2.512 | 978 (468) | 393 | 66,5% | 8,0% | 39,6 | ok |
| PS3 | [0,10; 0,90] | 15.008 (6.584 / 8.424) | 27.097 / 49.792 | 253.939 (1.058.732) | 2.511 | 978 (468) | 393 | 66,5% | 8,0% | 39,6 | ok |
| PS4 | completa | 91.897 (33.681 / 58.216) | 0 / 0 | 1.312.671 (0) | 4.233 | 2.270 (948) | 731 | 33,5% | 9,1% | 49,6 | ok |
| PS4 | [0,05; 0,95] | 15.589 (7.041 / 8.548) | 26.640 / 49.668 | 255.866 (1.056.805) | 2.528 | 987 (474) | 395 | 65,7% | 9,1% | 37,1 | ok |
| PS4 | [0,075; 0,925] | 15.015 (6.588 / 8.427) | 27.093 / 49.789 | 253.952 (1.058.719) | 2.511 | 978 (468) | 393 | 66,5% | 8,0% | 39,6 | ok |
| PS4 | [0,10; 0,90] | 15.006 (6.582 / 8.424) | 27.099 / 49.792 | 253.925 (1.058.746) | 2.510 | 978 (468) | 393 | 66,5% | 8,0% | 39,6 | ok |

Diferenças padronizadas AF − A nas faixas do PS2. A coluna "compra" é sem pesos; a coluna "item" pondera pelo nº de itens
com índice:

| Covariável | completa: compra | [0,05; 0,95]: compra | [0,075; 0,925]: compra | [0,10; 0,90]: compra | completa: item | [0,05; 0,95]: item | [0,075; 0,925]: item | [0,10; 0,90]: item |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| log nº de itens | −0,01 | −0,04 | 0,00 | 0,00 | 0,08 | 0,17 | 0,18 | 0,18 |
| parcela de medicamentos | 0,23 | 0,17 | 0,17 | 0,16 | 0,08 | 0,09 | 0,09 | 0,09 |
| quantidade prevista (eq) | 0,16 | 0,16 | 0,20 | 0,20 | 0,12 | 0,12 | 0,13 | 0,13 |
| competição esperada | −0,28 | −0,10 | −0,19 | −0,19 | −0,26 | −0,09 | −0,11 | −0,11 |
| parcela AF 12 meses | 4,11 | 1,18 | 1,16 | 1,16 | 3,94 | 1,12 | 1,14 | 1,14 |
| sem histórico 12 meses | −0,09 | −0,40 | −0,39 | −0,39 | −0,14 | −0,51 | −0,50 | −0,50 |
| log nº de compras 12 meses | 0,25 | 0,40 | 0,38 | 0,38 | 0,09 | 0,39 | 0,39 | 0,39 |
| trimestre | −0,02 | 0,12 | 0,09 | 0,09 | −0,01 | 0,18 | 0,17 | 0,17 |
| esfera federal | 0,21 | 0,09 | 0,12 | 0,12 | 0,44 | 0,25 | 0,26 | 0,26 |
| esfera estadual | −0,23 | −0,20 | −0,27 | −0,27 | −0,27 | −0,29 | −0,31 | −0,31 |
| esfera municipal | 0,05 | 0,15 | 0,18 | 0,18 | −0,09 | 0,14 | 0,14 | 0,14 |
| região N | −0,16 | −0,17 | −0,16 | −0,16 | −0,19 | −0,35 | −0,34 | −0,34 |
| região NE | 0,28 | 0,07 | 0,08 | 0,08 | 0,30 | 0,16 | 0,17 | 0,17 |
| região CO | 0,12 | 0,01 | 0,03 | 0,03 | 0,10 | −0,02 | −0,01 | −0,01 |
| região SE | −0,06 | 0,10 | 0,07 | 0,07 | −0,10 | 0,04 | 0,03 | 0,03 |
| região S | −0,16 | −0,07 | −0,06 | −0,06 | −0,10 | 0,10 | 0,10 | 0,10 |
| SRP | 0,24 | 0,17 | 0,23 | 0,23 | 0,27 | 0,18 | 0,19 | 0,19 |
| sigilo | 0,02 | 0,06 | 0,01 | 0,01 | −0,04 | −0,10 | −0,12 | −0,12 |
| exclusiva ME/EPP | −0,06 | −0,09 | −0,11 | −0,11 | 0,01 | −0,11 | −0,11 | −0,11 |
| log valor estimado | 0,14 | 0,11 | 0,18 | 0,18 | 0,19 | 0,25 | 0,28 | 0,28 |
| valor estimado ausente | 0,02 | 0,05 | 0,06 | 0,06 | 0,01 | 0,04 | 0,04 | 0,04 |

Sobreposição dentro das UASGs e dos maiores grupos de material:

Amostra completa: 4.233 UASGs, das quais 731 usam os dois modos; essas UASGs têm 33,5% das compras e 33,6% dos itens.

| Grupo dominante | Modo | Compras | escore p05 | p25 | mediana | p75 | p95 | no suporte |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| grupo 65 | AF | 13.892 | 0,640 | 0,961 | 0,976 | 0,986 | 0,991 | 16,1% |
| grupo 65 | A | 18.093 | 0,006 | 0,008 | 0,012 | 0,021 | 0,315 | 12,4% |
| grupo 89 | AF | 3.397 | 0,184 | 0,824 | 0,982 | 0,988 | 0,992 | 23,3% |
| grupo 89 | A | 8.931 | 0,006 | 0,007 | 0,009 | 0,018 | 0,276 | 18,6% |
| grupo outros | AF | 3.934 | 0,234 | 0,953 | 0,982 | 0,988 | 0,991 | 21,0% |
| grupo outros | A | 7.681 | 0,006 | 0,008 | 0,011 | 0,018 | 0,295 | 14,3% |
| grupo 75 | AF | 1.322 | 0,232 | 0,848 | 0,986 | 0,990 | 0,993 | 23,1% |
| grupo 75 | A | 2.686 | 0,007 | 0,009 | 0,013 | 0,020 | 0,327 | 14,9% |
| grupo 70 | AF | 1.319 | 0,241 | 0,831 | 0,986 | 0,990 | 0,992 | 25,1% |
| grupo 70 | A | 2.463 | 0,007 | 0,010 | 0,013 | 0,021 | 0,358 | 15,5% |
| grupo 71 | AF | 1.087 | 0,278 | 0,867 | 0,987 | 0,990 | 0,993 | 23,1% |
| grupo 71 | A | 1.800 | 0,008 | 0,010 | 0,013 | 0,023 | 0,335 | 15,2% |

- **Com o PS2:**
  - 49.873 compras têm escore < 0,075, quase todas do Aberto em UASGs que só usam Aberto;
  - 27.010 têm escore > 0,925, quase todas AF em UASGs que só usam AF;
  - ficam 15.014 compras (6.588 AF e 8.426 A), em 2.511 UASGs e 978 CNPJs (468 com AF).
- **Faixas:** 0,05 e 0,10 dão quase a mesma amostra (15.464 e 15.007), porque os escores se concentram perto de 0, de 1 e
  de uma faixa intermediária. A faixa do artigo não é sensível aqui.
- **Composição do suporte:** 66,5% das compras estão em UASGs que usam os dois modos, contra 33,5% na amostra completa.
  A regra mínima do protocolo foi atendida.
- **Equilíbrio:** o suporte reduz o desequilíbrio do histórico AF (diferença padronizada de 4,1 para 1,2), mas não o
  elimina. Região e esfera ficam abaixo de 0,3.
- **Sobreposição nos grupos:** nos maiores grupos de material, as distribuições do escore por modo se sobrepõem no
  suporte, mas a maior parte de cada grupo fica fora dele.

## 5. Modelo 2: OLS (eq. 6)

**Desfecho:** índice do item, em lp.
- **OLS 1:** bruto.
- **OLS 2:** com X.
- **OLS 3:** com X + efeitos fixos de UASG.
- **OLS 4:** com X + efeitos fixos de UASG e produto × trimestre.

**Estimação:** EP CR1 agrupado por CNPJ (principal) e por UASG; p e IC pela t(G − 1). O "G efetivo da variação" é
1/Σ s_g², em que s_g é a parcela do órgão g na variação de AF que resta depois dos controles e dos efeitos fixos.

| Especificação | Amostra | Pesos | coef (lp) | EP (CNPJ) | IC95 | p | % (IC95) | EP (UASG) | p (UASG) | itens | compras (AF) | UASGs | CNPJs | G efetivo da variação (top 5) |
|---|---|---|---:|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| OLS 1 | completa | item | −4,68 | 1,85 | [−8,31; −1,05] | 0,011 | −4,57 (−7,97; −1,05) | 1,03 | < 0,001 | 1.312.671 | 91.897 (33.681) | 4.233 | 2.270 | 29,5 (29%) |
| OLS 1 | completa | compra | −4,16 | 1,84 | [−7,77; −0,55] | 0,024 | −4,08 (−7,48; −0,55) | 0,91 | < 0,001 | 1.312.671 | 91.897 (33.681) | 4.233 | 2.270 | 49,6 (26%) |
| OLS 2 | completa | item | −4,24 | 1,04 | [−6,27; −2,21] | < 0,001 | −4,15 (−6,08; −2,18) | 1,04 | < 0,001 | 1.312.671 | 91.897 (33.681) | 4.233 | 2.270 | 19,0 (33%) |
| OLS 2 | completa | compra | −1,35 | 1,60 | [−4,49; 1,79] | 0,399 | −1,34 (−4,39; 1,81) | 1,32 | 0,306 | 1.312.671 | 91.897 (33.681) | 4.233 | 2.270 | 44,9 (27%) |
| OLS 3 | completa | item | −4,83 | 1,39 | [−7,56; −2,10] | < 0,001 | −4,71 (−7,28; −2,08) | 1,46 | < 0,001 | 1.312.671 | 91.897 (33.681) | 4.233 | 2.270 | 21,5 (33%) |
| OLS 3 | completa | compra | −1,58 | 1,68 | [−4,87; 1,71] | 0,345 | −1,57 (−4,75; 1,72) | 1,77 | 0,372 | 1.312.671 | 91.897 (33.681) | 4.233 | 2.270 | 42,9 (28%) |
| OLS 4 | completa | item | −6,22 | 1,25 | [−8,67; −3,76] | < 0,001 | −6,03 (−8,30; −3,69) | 1,36 | < 0,001 | 1.312.671 | 91.897 (33.681) | 4.233 | 2.270 | 21,7 (34%) |
| OLS 4 | completa | compra | −2,54 | 1,24 | [−4,98; −0,10] | 0,041 | −2,51 (−4,86; −0,10) | 1,34 | 0,057 | 1.312.671 | 91.897 (33.681) | 4.233 | 2.270 | 45,1 (26%) |
| OLS 1 | suporte | item | −5,54 | 1,90 | [−9,28; −1,80] | 0,004 | −5,39 (−8,86; −1,79) | 1,43 | < 0,001 | 253.951 | 15.014 (6.588) | 2.511 | 978 | 21,7 (34%) |
| OLS 1 | suporte | compra | −3,42 | 1,79 | [−6,94; 0,10] | 0,057 | −3,36 (−6,70; 0,10) | 1,36 | 0,012 | 253.951 | 15.014 (6.588) | 2.511 | 978 | 38,8 (30%) |
| OLS 2 | suporte | item | −4,02 | 1,19 | [−6,37; −1,68] | < 0,001 | −3,94 (−6,17; −1,67) | 1,12 | < 0,001 | 253.951 | 15.014 (6.588) | 2.511 | 978 | 16,4 (35%) |
| OLS 2 | suporte | compra | −1,17 | 1,63 | [−4,36; 2,02] | 0,471 | −1,17 (−4,27; 2,04) | 1,56 | 0,451 | 253.951 | 15.014 (6.588) | 2.511 | 978 | 41,8 (29%) |
| OLS 3 | suporte | item | −5,35 | 1,60 | [−8,49; −2,21] | < 0,001 | −5,21 (−8,14; −2,18) | 1,68 | 0,001 | 253.951 | 15.014 (6.588) | 2.511 | 978 | 18,2 (36%) |
| OLS 3 | suporte | compra | −0,19 | 2,18 | [−4,48; 4,09] | 0,930 | −0,19 (−4,38; 4,18) | 2,28 | 0,933 | 253.951 | 15.014 (6.588) | 2.511 | 978 | 34,5 (33%) |
| OLS 4 | suporte | item | −5,33 | 1,56 | [−8,40; −2,27] | < 0,001 | −5,19 (−8,05; −2,24) | 1,68 | 0,002 | 253.951 | 15.014 (6.588) | 2.511 | 978 | 17,5 (39%) |
| OLS 4 | suporte | compra | −2,43 | 1,51 | [−5,40; 0,53] | 0,107 | −2,40 (−5,25; 0,53) | 1,56 | 0,119 | 253.951 | 15.014 (6.588) | 2.511 | 978 | 31,7 (30%) |

- **Peso por item.** Todas as especificações dão de −4,0 a −6,2 lp, com IC sem zero e o mesmo resultado agrupando por
  UASG.
  - O efeito fixo de UASG não reduz a diferença (−4,8 completa; −5,4 suporte), e o de produto × trimestre a aumenta um pouco.
- **Peso igual por compra.**
  - A diferença bruta (OLS 1) é de −4,2 lp. Com controles, cai para −1,2 a −1,6.
  - Com efeito fixo de UASG no suporte, fica em −0,2.
  - O OLS 4 dá −2,5 (completa, p = 0,04) e −2,4 (suporte, p = 0,11).
- **Parâmetros:** o peso por item estima a diferença média entre itens; o peso por compra, entre pregões. A distância
  entre eles indica que a associação está nas compras com muitos itens.
- **Concentração:** o nº efetivo de órgãos na variação de AF é de 16 a 22 com peso por item e de 32 a 50 com peso por
  compra. Os 5 maiores órgãos respondem por 26% a 39% dessa variação.

## 6. Modelo 3: efeitos heterogêneos

**Efeito médio ajustado:** média, na população de análise, de ŷ(AF = 1) − ŷ(AF = 0) = β + δ′D̄, com EP pelo método delta.
O coeficiente de AF sozinho (última coluna) é o efeito na faixa-base, e não o efeito médio.

**Testes de heterogeneidade:** Wald de δ = 0 por dimensão, com F(q, G − 1) e Holm nas 5 dimensões (por amostra, base e
peso).

| Amostra | Base | Pesos | Dimensão | efeito médio ajustado (lp) | EP | IC95 | p | Wald F (gl) | p Wald | p Holm | coef AF na faixa-base |
|---|---|---|---|---:|---:|---|---:|---:|---:|---:|---:|
| completa | OLS 2 | item | valor estimado | −4,58 | 0,99 | [−6,53; −2,63] | < 0,001 | 0,48 (2) | 0,619 | 0,619 | −4,97 |
| completa | OLS 2 | item | quantidade prevista | −4,20 | 1,03 | [−6,23; −2,17] | < 0,001 | 3,03 (2) | 0,048 | 0,194 | −4,78 |
| completa | OLS 2 | item | classe de produto | −4,38 | 0,96 | [−6,27; −2,50] | < 0,001 | 2,23 (6) | 0,038 | 0,190 | −5,50 |
| completa | OLS 2 | item | esfera | −3,85 | 1,00 | [−5,81; −1,89] | < 0,001 | 2,10 (4) | 0,078 | 0,233 | −5,54 |
| completa | OLS 2 | item | competição esperada | −4,22 | 1,02 | [−6,22; −2,23] | < 0,001 | 1,81 (2) | 0,164 | 0,329 | −4,02 |
| completa | OLS 2 | item | conjunto (5 dimensões) | −4,31 | 0,97 | [−6,22; −2,40] | < 0,001 | 3,15 (16) | < 0,001 | — | −7,53 |
| completa | OLS 2 | compra | valor estimado | −1,94 | 1,46 | [−4,80; 0,92] | 0,184 | 0,23 (2) | 0,796 | 1,000 | −1,59 |
| completa | OLS 2 | compra | quantidade prevista | −1,36 | 1,56 | [−4,42; 1,71] | 0,385 | 1,27 (2) | 0,280 | 0,841 | −2,23 |
| completa | OLS 2 | compra | classe de produto | −1,37 | 1,56 | [−4,43; 1,70] | 0,383 | 1,86 (6) | 0,085 | 0,424 | −1,78 |
| completa | OLS 2 | compra | esfera | −1,34 | 1,72 | [−4,71; 2,03] | 0,436 | 0,21 (4) | 0,932 | 1,000 | −1,87 |
| completa | OLS 2 | compra | competição esperada | −1,43 | 1,65 | [−4,67; 1,81] | 0,387 | 1,99 (2) | 0,137 | 0,548 | −0,18 |
| completa | OLS 2 | compra | conjunto (5 dimensões) | −2,02 | 1,48 | [−4,93; 0,88] | 0,173 | 1,99 (16) | 0,011 | — | −3,20 |
| completa | OLS 3 | item | valor estimado | −5,19 | 1,28 | [−7,70; −2,68] | < 0,001 | 1,54 (2) | 0,214 | 0,428 | −4,47 |
| completa | OLS 3 | item | quantidade prevista | −4,77 | 1,40 | [−7,53; −2,02] | < 0,001 | 4,90 (2) | 0,007 | 0,037 | −5,22 |
| completa | OLS 3 | item | classe de produto | −4,89 | 1,33 | [−7,50; −2,28] | < 0,001 | 1,77 (6) | 0,102 | 0,306 | −4,61 |
| completa | OLS 3 | item | esfera | −4,59 | 1,22 | [−6,98; −2,20] | < 0,001 | 2,47 (4) | 0,043 | 0,172 | −5,95 |
| completa | OLS 3 | item | competição esperada | −4,84 | 1,36 | [−7,51; −2,17] | < 0,001 | 0,49 (2) | 0,613 | 0,613 | −5,27 |
| completa | OLS 3 | item | conjunto (5 dimensões) | −4,97 | 1,12 | [−7,16; −2,77] | < 0,001 | 2,66 (16) | < 0,001 | — | −5,86 |
| completa | OLS 3 | compra | valor estimado | −1,91 | 1,52 | [−4,88; 1,07] | 0,209 | 0,19 (2) | 0,825 | 1,000 | −1,95 |
| completa | OLS 3 | compra | quantidade prevista | −1,58 | 1,66 | [−4,83; 1,68] | 0,342 | 1,44 (2) | 0,238 | 0,713 | −2,51 |
| completa | OLS 3 | compra | classe de produto | −1,60 | 1,67 | [−4,88; 1,67] | 0,336 | 1,82 (6) | 0,092 | 0,461 | −1,61 |
| completa | OLS 3 | compra | esfera | −1,82 | 1,71 | [−5,17; 1,52] | 0,285 | 1,95 (4) | 0,100 | 0,461 | −0,45 |
| completa | OLS 3 | compra | competição esperada | −1,60 | 1,69 | [−4,90; 1,71] | 0,343 | 0,17 (2) | 0,840 | 1,000 | −1,22 |
| completa | OLS 3 | compra | conjunto (5 dimensões) | −2,13 | 1,51 | [−5,10; 0,84] | 0,159 | 1,79 (16) | 0,028 | — | −1,89 |
| suporte | OLS 2 | item | valor estimado | −4,34 | 1,15 | [−6,61; −2,08] | < 0,001 | 0,60 (2) | 0,550 | 0,904 | −3,55 |
| suporte | OLS 2 | item | quantidade prevista | −4,06 | 1,20 | [−6,43; −1,70] | < 0,001 | 3,81 (2) | 0,022 | 0,112 | −6,23 |
| suporte | OLS 2 | item | classe de produto | −3,97 | 1,18 | [−6,28; −1,67] | < 0,001 | 2,43 (6) | 0,024 | 0,112 | −7,25 |
| suporte | OLS 2 | item | esfera | −3,71 | 1,04 | [−5,74; −1,68] | < 0,001 | 2,24 (3) | 0,082 | 0,246 | −5,49 |
| suporte | OLS 2 | item | competição esperada | −4,03 | 1,20 | [−6,37; −1,68] | < 0,001 | 0,79 (2) | 0,452 | 0,904 | −3,25 |
| suporte | OLS 2 | item | conjunto (5 dimensões) | −4,01 | 0,98 | [−5,93; −2,09] | < 0,001 | 2,93 (15) | < 0,001 | — | −9,82 |
| suporte | OLS 2 | compra | valor estimado | −1,65 | 1,46 | [−4,51; 1,20] | 0,257 | 1,82 (2) | 0,162 | 0,486 | 1,32 |
| suporte | OLS 2 | compra | quantidade prevista | −1,25 | 1,49 | [−4,19; 1,68] | 0,402 | 7,50 (2) | < 0,001 | 0,003 | −4,03 |
| suporte | OLS 2 | compra | classe de produto | −1,19 | 1,65 | [−4,44; 2,06] | 0,472 | 2,05 (6) | 0,056 | 0,226 | −1,38 |
| suporte | OLS 2 | compra | esfera | −1,20 | 1,45 | [−4,05; 1,66] | 0,411 | 1,04 (3) | 0,373 | 0,746 | −1,08 |
| suporte | OLS 2 | compra | competição esperada | −1,18 | 1,66 | [−4,43; 2,07] | 0,477 | 0,51 (2) | 0,602 | 0,746 | −0,97 |
| suporte | OLS 2 | compra | conjunto (5 dimensões) | −1,71 | 1,27 | [−4,20; 0,77] | 0,177 | 2,12 (15) | 0,008 | — | −4,37 |
| suporte | OLS 3 | item | valor estimado | −5,55 | 1,54 | [−8,56; −2,54] | < 0,001 | 1,05 (2) | 0,350 | 0,700 | −4,87 |
| suporte | OLS 3 | item | quantidade prevista | −5,37 | 1,62 | [−8,55; −2,20] | < 0,001 | 2,69 (2) | 0,068 | 0,273 | −7,41 |
| suporte | OLS 3 | item | classe de produto | −5,40 | 1,46 | [−8,26; −2,53] | < 0,001 | 2,41 (6) | 0,026 | 0,128 | −9,13 |
| suporte | OLS 3 | item | esfera | −4,90 | 1,36 | [−7,58; −2,22] | < 0,001 | 2,11 (3) | 0,097 | 0,292 | −7,12 |
| suporte | OLS 3 | item | competição esperada | −5,32 | 1,62 | [−8,51; −2,14] | 0,001 | 0,56 (2) | 0,572 | 0,700 | −4,55 |
| suporte | OLS 3 | item | conjunto (5 dimensões) | −5,03 | 1,30 | [−7,58; −2,47] | < 0,001 | 2,46 (15) | 0,001 | — | −10,92 |
| suporte | OLS 3 | compra | valor estimado | −0,46 | 1,92 | [−4,23; 3,31] | 0,810 | 1,39 (2) | 0,250 | 0,750 | 1,28 |
| suporte | OLS 3 | compra | quantidade prevista | −0,30 | 2,05 | [−4,31; 3,71] | 0,883 | 5,61 (2) | 0,004 | 0,019 | −3,15 |
| suporte | OLS 3 | compra | classe de produto | −0,28 | 2,25 | [−4,69; 4,14] | 0,902 | 1,14 (6) | 0,339 | 0,750 | −1,91 |
| suporte | OLS 3 | compra | esfera | −1,21 | 1,78 | [−4,71; 2,29] | 0,498 | 3,22 (3) | 0,022 | 0,089 | 0,19 |
| suporte | OLS 3 | compra | competição esperada | −0,18 | 2,18 | [−4,46; 4,10] | 0,934 | 0,13 (2) | 0,875 | 0,875 | 0,13 |
| suporte | OLS 3 | compra | conjunto (5 dimensões) | −1,36 | 1,60 | [−4,51; 1,78] | 0,395 | 1,73 (15) | 0,041 | — | −3,17 |

Termos de interação (suporte, OLS 2, peso por item):

| Termo (suporte, OLS 2, peso por item) | coef (lp) | EP | parcela da faixa |
|---|---:|---:|---:|
| AF×valor estimado=T2 | −1,58 | 1,95 | 27,7% |
| AF×valor estimado=T1 | −2,52 | 2,36 | 14,0% |
| AF×quantidade prevista=T2 | 1,22 | 1,10 | 33,3% |
| AF×quantidade prevista=T3 | 5,29 | 1,95 | 33,3% |
| AF×classe de produto=grupo 89 | 5,66 | 3,52 | 29,7% |
| AF×classe de produto=outros | 4,54 | 2,23 | 28,1% |
| AF×classe de produto=grupo 75 | 3,67 | 3,81 | 3,9% |
| AF×classe de produto=grupo 79 | 0,95 | 4,00 | 2,3% |
| AF×classe de produto=grupo 73 | −1,97 | 3,31 | 2,3% |
| AF×classe de produto=grupo 84 | 11,26 | 6,61 | 1,8% |
| AF×esfera=M | 0,80 | 2,80 | 28,1% |
| AF×esfera=E | 5,88 | 2,77 | 21,1% |
| AF×esfera=N | 6,12 | 3,77 | 5,3% |
| AF×competição esperada=T2 | −1,62 | 1,43 | 33,3% |
| AF×competição esperada=T3 | −0,70 | 2,18 | 33,3% |

- **Efeito médio ajustado:** fica perto do OLS correspondente em todas as dimensões.
  - Por item: −3,7 a −5,6 lp, todos com IC sem zero.
  - Por compra: −0,2 a −2,1, nenhum com IC sem zero.
- **Heterogeneidade:**
  - depois de Holm nas 5 dimensões, só a **quantidade prevista** fica abaixo de 0,05, em três combinações:
    - completa, OLS 3, por item: p = 0,04;
    - suporte, OLS 2, por compra: p = 0,003;
    - suporte, OLS 3, por compra: p = 0,02;
  - classe de produto e esfera ficam nominalmente abaixo de 0,05 em algumas combinações, mas não depois de Holm;
  - o modelo conjunto rejeita a homogeneidade na maioria das combinações, o que é esperado com 5 dimensões juntas.
- **Leitura:** o coeficiente de AF na faixa-base não é o efeito médio e não deve ser lido sozinho.

## 7. Modelo 4: matching pelo escore (eq. 7)

**Desenho:** compras no suporte principal; desfecho = média do índice da compra; M = 4, com reposição; empates incluídos
(peso repartido).

**Variantes:**
- (a) só o escore;
- (b) exato no trimestre e no grupo dominante;
- (c) exato na UASG;
- (a) com caliper de 0,2 DP do escore.

**Erros-padrão:**
- **EP AI pop.:** Abadie e Imbens (2006), efeito populacional, com σ² por 4 vizinhos do mesmo modo.
- **EP AI cond.:** o mesmo para o efeito na amostra.
- **EP agrupado:** adaptação por CNPJ, que não é um estimador consagrado. Os IC e p da tabela usam esse EP, o mais
  conservador diante da dependência entre compras do mesmo órgão.

| Variante | Pesos | Estimando | coef (lp) | EP AI pop. | EP AI cond. | EP agrupado (adapt.) | IC95 agrupado | p agrupado | compras no estimando (AF / A) | sem par | usadas: compras / UASGs / CNPJs | ESS AF / A | peso máx. AF / A |
|---|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|
| (a) só o escore | compra | efeito_medio_eq7 | −1,36 | 1,09 | 1,09 | 1,82 | [−4,92; 2,19] | 0,453 | 15.014 (6.588 / 8.426) | 0 | 15.014 / 2.511 / 978 | 4179 / 5519 | 0,11% / 0,13% |
| (a) só o escore | compra | efeito_nas_AF | −1,61 | 1,31 | 1,31 | 2,08 | [−5,69; 2,47] | 0,440 | 6.588 (6.588 / 0) | 0 | 12.740 / 2.174 / 858 | 6588 / 2256 | 0,02% / 0,28% |
| (a) só o escore | compra | efeito_nas_A | −1,17 | 1,23 | 1,23 | 2,02 | [−5,13; 2,78] | 0,561 | 8.426 (0 / 8.426) | 0 | 13.640 / 2.496 / 967 | 2328 / 8426 | 0,18% / 0,01% |
| (a) só o escore | item | efeito_medio_eq7 | −3,14 | 1,09 | 1,16 | 2,05 | [−7,16; 0,87] | 0,125 | 15.014 (6.588 / 8.426) | 0 | 15.014 / 2.511 / 978 | 1989 / 2584 | 0,87% / 0,30% |
| (a) só o escore | item | efeito_nas_AF | −6,05 | 1,51 | 1,68 | 3,05 | [−12,03; −0,06] | 0,048 | 6.588 (6.588 / 0) | 0 | 12.740 / 2.174 / 858 | 812 / 1398 | 1,95% / 0,51% |
| (a) só o escore | item | efeito_nas_A | −0,82 | 1,31 | 1,38 | 2,25 | [−5,24; 3,59] | 0,715 | 8.426 (0 / 8.426) | 0 | 13.640 / 2.496 / 967 | 1861 / 1782 | 0,29% / 0,53% |
| (b) exato trimestre × grupo dominante | compra | efeito_medio_eq7 | −1,98 | 1,12 | 1,12 | 1,76 | [−5,43; 1,47] | 0,260 | 15.003 (6.585 / 8.418) | 11 | 15.003 / 2.506 / 978 | 3641 / 5112 | 0,17% / 0,15% |
| (b) exato trimestre × grupo dominante | compra | efeito_nas_AF | −2,53 | 1,33 | 1,32 | 2,41 | [−7,25; 2,20] | 0,294 | 6.585 (6.585 / 0) | 11 | 12.443 / 2.133 / 850 | 6585 / 1932 | 0,02% / 0,32% |
| (b) exato trimestre × grupo dominante | compra | efeito_nas_A | −1,55 | 1,32 | 1,32 | 1,78 | [−5,04; 1,94] | 0,383 | 8.418 (0 / 8.418) | 11 | 13.355 / 2.486 / 967 | 1845 / 8418 | 0,29% / 0,01% |
| (b) exato trimestre × grupo dominante | item | efeito_medio_eq7 | −2,97 | 1,20 | 1,37 | 1,99 | [−6,88; 0,94] | 0,136 | 15.003 (6.585 / 8.418) | 11 | 15.003 / 2.506 / 978 | 1557 / 2161 | 0,87% / 0,32% |
| (b) exato trimestre × grupo dominante | item | efeito_nas_AF | −4,57 | 1,70 | 2,20 | 3,44 | [−11,32; 2,17] | 0,184 | 6.585 (6.585 / 0) | 11 | 12.443 / 2.133 / 850 | 812 / 1076 | 1,95% / 0,53% |
| (b) exato trimestre × grupo dominante | item | efeito_nas_A | −1,69 | 1,45 | 1,50 | 2,47 | [−6,54; 3,16] | 0,495 | 8.418 (0 / 8.418) | 11 | 13.355 / 2.486 / 967 | 1168 / 1781 | 0,52% / 0,53% |
| (c) exato na UASG | compra | efeito_medio_eq7 | −0,74 | 1,90 | 1,89 | 1,84 | [−4,35; 2,86] | 0,686 | 9.982 (4.905 / 5.077) | 5.032 | 9.982 / 393 / 254 | 1875 / 1443 | 0,45% / 0,60% |
| (c) exato na UASG | compra | efeito_nas_AF | −4,81 | 2,92 | 2,92 | 3,35 | [−11,36; 1,75] | 0,151 | 4.905 (4.905 / 0) | 5.032 | 8.026 / 393 / 254 | 4905 / 444 | 0,02% / 1,21% |
| (c) exato na UASG | compra | efeito_nas_A | 3,18 | 1,93 | 1,91 | 3,36 | [−3,42; 9,77] | 0,345 | 5.077 (0 / 5.077) | 5.032 | 7.981 / 393 / 253 | 677 / 5077 | 0,87% / 0,02% |
| (c) exato na UASG | item | efeito_medio_eq7 | −0,56 | 1,80 | 1,80 | 2,56 | [−5,58; 4,47] | 0,828 | 9.982 (4.905 / 5.077) | 5.032 | 9.982 / 393 / 254 | 824 / 964 | 1,32% / 0,60% |
| (c) exato na UASG | item | efeito_nas_AF | −10,15 | 2,39 | 2,45 | 4,20 | [−18,37; −1,93] | 0,016 | 4.905 (4.905 / 0) | 5.032 | 8.026 / 393 / 254 | 549 / 414 | 2,65% / 1,19% |
| (c) exato na UASG | item | efeito_nas_A | 8,95 | 2,45 | 2,35 | 4,91 | [−0,68; 18,58] | 0,069 | 5.077 (0 / 5.077) | 5.032 | 7.981 / 393 / 253 | 458 / 919 | 1,57% / 0,89% |
| (a) com caliper de 0,2 DP | compra | efeito_medio_eq7 | −1,36 | 1,09 | 1,09 | 1,82 | [−4,92; 2,19] | 0,453 | 15.014 (6.588 / 8.426) | 0 | 15.014 / 2.511 / 978 | 4179 / 5519 | 0,11% / 0,13% |
| (a) com caliper de 0,2 DP | compra | efeito_nas_AF | −1,61 | 1,31 | 1,31 | 2,08 | [−5,69; 2,47] | 0,440 | 6.588 (6.588 / 0) | 0 | 12.740 / 2.174 / 858 | 6588 / 2256 | 0,02% / 0,28% |
| (a) com caliper de 0,2 DP | compra | efeito_nas_A | −1,17 | 1,23 | 1,23 | 2,02 | [−5,13; 2,78] | 0,561 | 8.426 (0 / 8.426) | 0 | 13.640 / 2.496 / 967 | 2328 / 8426 | 0,18% / 0,01% |
| (a) com caliper de 0,2 DP | item | efeito_medio_eq7 | −3,14 | 1,09 | 1,16 | 2,05 | [−7,16; 0,87] | 0,125 | 15.014 (6.588 / 8.426) | 0 | 15.014 / 2.511 / 978 | 1989 / 2584 | 0,87% / 0,30% |
| (a) com caliper de 0,2 DP | item | efeito_nas_AF | −6,05 | 1,51 | 1,68 | 3,05 | [−12,03; −0,06] | 0,048 | 6.588 (6.588 / 0) | 0 | 12.740 / 2.174 / 858 | 812 / 1398 | 1,95% / 0,51% |
| (a) com caliper de 0,2 DP | item | efeito_nas_A | −0,82 | 1,31 | 1,38 | 2,25 | [−5,24; 3,59] | 0,715 | 8.426 (0 / 8.426) | 0 | 13.640 / 2.496 / 967 | 1861 / 1782 | 0,29% / 0,53% |

Conferência no pacote R `Matching` (variante a):

| Estimando | Pesos | Variância | est. R | est. Python | dif. | EP R | EP Python | razão |
|---|---|---|---:|---:|---:|---:|---:|---:|
| ATE | iguais | populacional | −1,3614 | −1,3638 | 0,002333 | 1,0864 | 1,0892 | 1,0026 |
| ATE | iguais | condicional (sample = TRUE) | −1,3614 | −1,3638 | 0,002333 | 1,0870 | 1,0896 | 1,0024 |
| ATE | itens | populacional | −3,0057 | −3,1438 | 0,138168 | 0,6948 | 1,0925 | 1,5724 |
| ATE | itens | condicional (sample = TRUE) | −3,0057 | −3,1438 | 0,138168 | 0,7947 | 1,1623 | 1,4625 |
| ATT | iguais | populacional | −1,6046 | −1,6083 | 0,003725 | 1,3072 | 1,3118 | 1,0035 |
| ATT | iguais | condicional (sample = TRUE) | −1,6046 | −1,6083 | 0,003725 | 1,3092 | 1,3142 | 1,0038 |
| ATT | itens | populacional | −4,7694 | −6,0487 | 1,279358 | 0,9551 | 1,5064 | 1,5772 |
| ATT | itens | condicional (sample = TRUE) | −4,7694 | −6,0487 | 1,279358 | 1,0343 | 1,6828 | 1,6271 |
| ATC | iguais | populacional | −1,1713 | −1,1726 | 0,001244 | 1,2264 | 1,2319 | 1,0045 |
| ATC | iguais | condicional (sample = TRUE) | −1,1713 | −1,1726 | 0,001244 | 1,2270 | 1,2315 | 1,0036 |
| ATC | itens | populacional | −1,5965 | −0,8228 | −0,773663 | 0,9786 | 1,3140 | 1,3427 |
| ATC | itens | condicional (sample = TRUE) | −1,5965 | −0,8228 | −0,773663 | 1,0343 | 1,3806 | 1,3349 |

Equilíbrio depois do matching (diferença padronizada, pesos do casamento; ✱ = |dif.| > 0,1):

| Covariável | amostra completa | suporte, antes | depois: (a) só o escore | depois: (b) exato trimestre × grupo dominante | depois: (c) exato na UASG | depois: (a) com caliper de 0,2 DP |
|---|---:|---:|---:|---:|---:|---:|
| log nº de itens | −0,01 | 0,00 | −0,03 | −0,01 | 0,05 | −0,03 |
| parcela de medicamentos | 0,23 | 0,17 | 0,02 | 0,00 | −0,01 | 0,02 |
| quantidade prevista (eq) | 0,16 | 0,20 | 0,03 | 0,05 | 0,03 | 0,03 |
| competição esperada | −0,28 | −0,19 | −0,03 | −0,03 | 0,04 | −0,03 |
| parcela AF 12 meses | 4,11 | 1,16 | 0,23 ✱ | 0,30 ✱ | 0,01 | 0,23 ✱ |
| sem histórico 12 meses | −0,09 | −0,39 | −0,05 | −0,05 | 0,07 | −0,05 |
| log nº de compras 12 meses | 0,25 | 0,38 | 0,08 | 0,06 | −0,06 | 0,08 |
| trimestre | −0,02 | 0,09 | 0,01 | −0,00 | 0,05 | 0,01 |
| esfera federal | 0,21 | 0,12 | −0,01 | −0,03 | −0,01 | −0,01 |
| esfera estadual | −0,23 | −0,27 | −0,03 | −0,00 | 0,01 | −0,03 |
| esfera municipal | 0,05 | 0,18 | 0,06 | 0,04 | −0,01 | 0,06 |
| região N | −0,16 | −0,16 | −0,03 | −0,02 | 0,00 | −0,03 |
| região NE | 0,28 | 0,08 | 0,02 | −0,00 | −0,00 | 0,02 |
| região CO | 0,12 | 0,03 | −0,01 | 0,00 | 0,00 | −0,01 |
| região SE | −0,06 | 0,07 | 0,00 | 0,03 | 0,00 | 0,00 |
| região S | −0,16 | −0,06 | 0,02 | −0,03 | −0,00 | 0,02 |
| SRP | 0,24 | 0,23 | 0,11 ✱ | 0,11 ✱ | 0,11 ✱ | 0,11 ✱ |
| sigilo | 0,02 | 0,01 | −0,05 | −0,03 | −0,00 | −0,05 |
| exclusiva ME/EPP | −0,06 | −0,11 | −0,05 | −0,04 | −0,01 | −0,05 |
| log valor estimado | 0,14 | 0,18 | 0,04 | 0,05 | 0,04 | 0,04 |
| valor estimado ausente | 0,02 | 0,06 | 0,02 | 0,01 | 0,03 | 0,02 |

- **(a) só o escore, peso igual por compra:** −1,36 lp.
  - EP de Abadie e Imbens 1,09; EP agrupado 1,82; IC agrupado [−4,9; 2,2].
  - Nas AF: −1,6. Nas A: −1,2.
  - Todas as 15.014 compras têm par.
  - **Caliper de 0,2 DP:** não exclui nenhuma compra, porque todos os vizinhos já estão dentro do limite.
- **(b) exato no trimestre e no grupo:** −1,98, com 11 compras sem par.
- **(c) exato na UASG:** −0,75.
  - 5.032 compras (33,5%) não têm par na própria UASG.
  - Sobram 254 órgãos.
  - Os efeitos nas AF (−4,8) e nas A (+3,2) têm sinais opostos.
  - É uma comparação estreita e instável.
- **Peso por item:**
  - em (a), −3,1 no efeito médio e −6,0 nas AF (p agrupado 0,048);
  - de novo, a ponderação por item puxa para valores mais negativos.
- **Conferência no pacote `Matching`:**
  - **com peso igual:** estimativas e EP iguais até a 3ª casa (diferença ≤ 0,004 lp; razão de EP ≤ 1,005). A pequena
    diferença deve vir do tratamento de empates do pacote;
  - **com peso por item:** o pacote também pondera a média dos vizinhos imputados; este estudo, como no protocolo, só
    pondera a média final. Os dois estimadores diferem, e o do pacote fica entre −1,6 e −4,8, contra −0,8 a −6,0. É uma
    diferença de definição, não um erro, e a variante por item deve ser lida como sensibilidade.
- **EP agrupado:** fica de 1,5 a 2 vezes o EP de Abadie e Imbens. A dependência entre compras do mesmo órgão é
  importante.
- **Equilíbrio depois do matching (a):**
  - a parcela AF da UASG nos 12 meses anteriores continua desequilibrada (0,23);
  - o SRP fica no limite (0,11);
  - as demais covariáveis ficam abaixo de 0,1;
  - equilíbrio observado não implica validade causal.

## 8. Desfechos secundários

| Desfecho | Especificação | Amostra | coef | EP (CNPJ) | IC95 | p | p Holm | itens | compras (AF) | CNPJs |
|---|---|---|---:|---:|---|---:|---:|---:|---:|---:|
| desconto sobre o estimado (p.p.) | OLS 1 | completa | 3,48 | 1,00 | [1,52; 5,43] | < 0,001 | — | 1.031.493 | 61.672 (22.422) | 2.070 |
| desconto sobre o estimado (p.p.) | OLS 2 | completa | 3,94 | 0,63 | [2,70; 5,19] | < 0,001 | — | 1.031.493 | 61.672 (22.422) | 2.070 |
| desconto sobre o estimado (p.p.) | OLS 3 | completa | 4,05 | 0,64 | [2,79; 5,31] | < 0,001 | — | 1.031.493 | 61.672 (22.422) | 2.070 |
| desconto sobre o estimado (p.p.) | OLS 4 | completa | 4,04 | 0,58 | [2,91; 5,17] | < 0,001 | — | 1.031.493 | 61.672 (22.422) | 2.070 |
| log do preço (lp) | log P | produto × trimestre | completa | −5,53 | 1,50 | [−8,47; −2,59] | < 0,001 | — | 1.312.671 | 91.897 (33.681) | 2.270 |
| log do preço (lp) | log P | produto × trimestre + X | completa | −4,68 | 0,81 | [−6,27; −3,09] | < 0,001 | — | 1.312.671 | 91.897 (33.681) | 2.270 |
| log do preço (lp) | log P | produto × trimestre + X + UASG | completa | −5,54 | 1,06 | [−7,62; −3,46] | < 0,001 | — | 1.312.671 | 91.897 (33.681) | 2.270 |
| desconto sobre o estimado (p.p.) | OLS 1 | suporte | 3,82 | 1,13 | [1,61; 6,03] | < 0,001 | — | 199.592 | 10.323 (4.513) | 867 |
| desconto sobre o estimado (p.p.) | OLS 2 | suporte | 4,32 | 0,69 | [2,96; 5,67] | < 0,001 | — | 199.592 | 10.323 (4.513) | 867 |
| desconto sobre o estimado (p.p.) | OLS 3 | suporte | 4,49 | 0,87 | [2,77; 6,20] | < 0,001 | < 0,001 | 199.592 | 10.323 (4.513) | 867 |
| desconto sobre o estimado (p.p.) | OLS 4 | suporte | 5,39 | 0,90 | [3,63; 7,15] | < 0,001 | — | 199.592 | 10.323 (4.513) | 867 |
| log do preço (lp) | log P | produto × trimestre | suporte | −6,45 | 1,65 | [−9,69; −3,20] | < 0,001 | — | 253.951 | 15.014 (6.588) | 978 |
| log do preço (lp) | log P | produto × trimestre + X | suporte | −4,16 | 1,11 | [−6,33; −1,99] | < 0,001 | — | 253.951 | 15.014 (6.588) | 978 |
| log do preço (lp) | log P | produto × trimestre + X + UASG | suporte | −4,88 | 1,36 | [−7,55; −2,21] | < 0,001 | 0,001 | 253.951 | 15.014 (6.588) | 978 |
| homologação (prob.) (p.p.) | OLS 1 | todos os itens com situação final | −2,21 | 0,99 | [−4,14; −0,27] | 0,026 | — | 3.408.422 | 135.549 (51.543) | 2.404 |
| homologação (prob.) (p.p.) | OLS 2 | todos os itens com situação final | −0,46 | 0,71 | [−1,85; 0,93] | 0,519 | — | 3.408.422 | 135.549 (51.543) | 2.404 |
| homologação (prob.) (p.p.) | OLS 3 | todos os itens com situação final | −0,59 | 0,77 | [−2,10; 0,91] | 0,440 | — | 3.408.422 | 135.549 (51.543) | 2.404 |
| fracasso (prob.) (p.p.) | OLS 1 | todos os itens com situação final | 1,63 | 0,74 | [0,17; 3,08] | 0,028 | — | 3.408.422 | 135.549 (51.543) | 2.404 |
| fracasso (prob.) (p.p.) | OLS 2 | todos os itens com situação final | 0,13 | 0,55 | [−0,94; 1,20] | 0,807 | — | 3.408.422 | 135.549 (51.543) | 2.404 |
| fracasso (prob.) (p.p.) | OLS 3 | todos os itens com situação final | 0,25 | 0,61 | [−0,94; 1,44] | 0,678 | — | 3.408.422 | 135.549 (51.543) | 2.404 |
| deserção (prob.) (p.p.) | OLS 1 | todos os itens com situação final | 0,58 | 0,34 | [−0,08; 1,24] | 0,084 | — | 3.408.422 | 135.549 (51.543) | 2.404 |
| deserção (prob.) (p.p.) | OLS 2 | todos os itens com situação final | 0,32 | 0,36 | [−0,38; 1,03] | 0,367 | — | 3.408.422 | 135.549 (51.543) | 2.404 |
| deserção (prob.) (p.p.) | OLS 3 | todos os itens com situação final | 0,34 | 0,39 | [−0,43; 1,11] | 0,388 | — | 3.408.422 | 135.549 (51.543) | 2.404 |
| homologação (prob.) (p.p.) | OLS 1 | itens das compras da análise no suporte | −1,10 | 1,07 | [−3,19; 1,00] | 0,305 | — | 581.582 | 15.014 (6.588) | 978 |
| homologação (prob.) (p.p.) | OLS 2 | itens das compras da análise no suporte | −0,20 | 1,00 | [−2,17; 1,76] | 0,841 | — | 581.582 | 15.014 (6.588) | 978 |
| homologação (prob.) (p.p.) | OLS 3 | itens das compras da análise no suporte | −0,94 | 1,13 | [−3,16; 1,28] | 0,408 | 0,815 | 581.582 | 15.014 (6.588) | 978 |
| fracasso (prob.) (p.p.) | OLS 1 | itens das compras da análise no suporte | 0,25 | 0,82 | [−1,36; 1,85] | 0,765 | — | 581.582 | 15.014 (6.588) | 978 |
| fracasso (prob.) (p.p.) | OLS 2 | itens das compras da análise no suporte | −0,56 | 0,82 | [−2,17; 1,04] | 0,493 | — | 581.582 | 15.014 (6.588) | 978 |
| fracasso (prob.) (p.p.) | OLS 3 | itens das compras da análise no suporte | −0,44 | 0,84 | [−2,10; 1,21] | 0,601 | 0,815 | 581.582 | 15.014 (6.588) | 978 |
| deserção (prob.) (p.p.) | OLS 1 | itens das compras da análise no suporte | 0,85 | 0,50 | [−0,13; 1,83] | 0,089 | — | 581.582 | 15.014 (6.588) | 978 |
| deserção (prob.) (p.p.) | OLS 2 | itens das compras da análise no suporte | 0,76 | 0,47 | [−0,16; 1,68] | 0,105 | — | 581.582 | 15.014 (6.588) | 978 |
| deserção (prob.) (p.p.) | OLS 3 | itens das compras da análise no suporte | 1,38 | 0,69 | [0,02; 2,74] | 0,047 | 0,141 | 581.582 | 15.014 (6.588) | 978 |

- **Desconto sobre o valor estimado:** 3,5 a 5,4 p.p. maior no AF em todas as especificações; p de Holm < 0,001 no
  OLS 3, suporte. O desconto depende do estimado, que também varia por modo, e não substitui o índice.
- **Log do preço com efeitos fixos de produto × trimestre:** −4,2 a −6,4 lp, perto do índice com peso por item. A
  construção do índice não é o que gera o resultado.
- **Homologação, fracasso e deserção:**
  - as diferenças brutas (−2,2 p.p. de homologação; +1,6 de fracasso) somem com controles;
  - a deserção no suporte, com OLS 3, é +1,4 p.p. (p = 0,047), mas não sobrevive a Holm (p = 0,14).
- **Número de propostas:** não estimado, sem identificação comparável entre os modos.

## 9. Comparação com os estudos anteriores

| Especificação | Amostra | Pesos | coef (lp) | EP (CNPJ) | IC95 | p | % | itens | compras | CNPJs | referência |
|---|---|---|---:|---:|---|---:|---:|---:|---:|---:|---|
| painel de 16/11: log P | CNPJ × produto + produto × mês | completa | item | −6,24 | 0,56 | [−7,34; −5,14] | < 0,001 | −6,05 | 1.312.671 | 91.897 | 2.270 | −4,5% [−6,9; −2,1] (191 mil itens, 656 CNPJs) |
| painel de 16/11: log P | CNPJ × produto + produto × mês | suporte | item | −7,65 | 2,27 | [−12,10; −3,19] | < 0,001 | −7,36 | 253.951 | 15.014 | 978 | −4,5% [−6,9; −2,1] (191 mil itens, 656 CNPJs) |
| 152 eventos: dentro do evento (UASG tratada antes × depois) | janelas do estudo de eventos (itens até 2026-04) | item | −8,42 | 1,86 | [−12,10; −4,73] | < 0,001 | −8,07 | 55.617 | 3.518 | 97 | estudo de eventos −1,91 lp [−5,67; 1,93] (diferença contra controles) |
| 152 eventos: dentro do evento (UASG tratada antes × depois) | janelas do estudo de eventos (itens até 2026-04) | compra | −4,57 | 1,54 | [−7,63; −1,51] | 0,004 | −4,47 | 55.617 | 3.518 | 97 | estudo de eventos −1,91 lp [−5,67; 1,93] (diferença contra controles) |
| 152 eventos: dentro do evento + trimestre calendário | janelas do estudo de eventos (itens até 2026-04) | item | −8,68 | 1,76 | [−12,18; −5,18] | < 0,001 | −8,31 | 55.617 | 3.518 | 97 | estudo de eventos −1,91 lp [−5,67; 1,93] (diferença contra controles) |
| 152 eventos: dentro do evento + trimestre calendário | janelas do estudo de eventos (itens até 2026-04) | compra | −4,56 | 1,71 | [−7,96; −1,17] | 0,009 | −4,46 | 55.617 | 3.518 | 97 | estudo de eventos −1,91 lp [−5,67; 1,93] (diferença contra controles) |

**Referências publicadas:**
- painel de 16/11: −4,5% [−6,9; −2,1], ≈ −4,6 lp, com 191 mil itens e 656 CNPJs;
- estudo de eventos: −1,91 lp [−5,67; 1,93];
- filtrado: −3,76 lp [−6,67; −0,89].

**Decomposição descritiva das diferenças:**
1. **Especificação × amostra:** a mesma especificação do painel (efeitos fixos CNPJ × produto e produto × mês) nesta
   amostra dá −6,2 lp (−6,0%). Com 1,31 milhão de itens e 2.270 CNPJs, contra 191 mil e 656, ela fica um pouco mais
   negativa que a publicada. A associação do painel se reproduz, e a diferença vem da amostra.
2. **Ponderação:** por item, os OLS ficam entre −4 e −6 lp, a mesma ordem do painel. Por compra, que é a ponderação do
   estudo de eventos (média por compra), ficam entre 0 e −2,5, a ordem do −1,91.
3. **Controles e tendência:** nas janelas dos 152 eventos, comparar só a UASG tratada antes × depois dá −4,6 lp por compra
   (−8,4 por item). O estudo de eventos dá −1,91 porque subtrai a variação das UASGs de controle no mesmo período. Cerca
   de 2,7 lp da comparação antes × depois é tendência comum, não troca de modo.
4. **Suporte:** muda pouco (seção 4).
5. **Método:** com a mesma ponderação, OLS, interações e matching dão valores parecidos.

**Conclusão:** amostras e parâmetros distintos não são equivalentes. O −4,5% do painel é uma associação entre itens; o
−1,91 é uma diferença em diferenças entre compras com controle de tendência.

## 10. Robustez

| Teste | Especificação | Amostra | Pesos | coef (lp) | EP | IC95 | p | itens | compras | CNPJs | nota |
|---|---|---|---|---:|---:|---|---:|---:|---:|---:|---|
| 1. faixa de suporte | OLS 2 | suporte completa | item | −4,24 | 1,04 | [−6,27; −2,21] | < 0,001 | 1.312.671 | 91.897 | 2.270 |  |
| 1. faixa de suporte | OLS 2 | suporte completa | compra | −1,35 | 1,60 | [−4,49; 1,79] | 0,399 | 1.312.671 | 91.897 | 2.270 |  |
| 1. faixa de suporte | OLS 3 | suporte completa | item | −4,83 | 1,39 | [−7,56; −2,10] | < 0,001 | 1.312.671 | 91.897 | 2.270 |  |
| 1. faixa de suporte | OLS 3 | suporte completa | compra | −1,58 | 1,68 | [−4,87; 1,71] | 0,345 | 1.312.671 | 91.897 | 2.270 |  |
| 1. faixa de suporte | matching (a) | suporte completa | compra | −1,44 | 2,53 | [−6,39; 3,51] | — | — | 91.897 | 2.270 | EP agrupado (adapt.); EP AI 1,86 |
| 1. faixa de suporte | OLS 2 | suporte [0,05; 0,95] | item | −3,96 | 1,20 | [−6,32; −1,61] | 0,001 | 255.502 | 15.464 | 985 |  |
| 1. faixa de suporte | OLS 2 | suporte [0,05; 0,95] | compra | −1,02 | 1,58 | [−4,13; 2,08] | 0,518 | 255.502 | 15.464 | 985 |  |
| 1. faixa de suporte | OLS 3 | suporte [0,05; 0,95] | item | −5,41 | 1,60 | [−8,54; −2,28] | < 0,001 | 255.502 | 15.464 | 985 |  |
| 1. faixa de suporte | OLS 3 | suporte [0,05; 0,95] | compra | −0,75 | 2,22 | [−5,10; 3,60] | 0,736 | 255.502 | 15.464 | 985 |  |
| 1. faixa de suporte | matching (a) | suporte [0,05; 0,95] | compra | −0,85 | 1,74 | [−4,26; 2,56] | — | — | 15.464 | 985 | EP agrupado (adapt.); EP AI 1,07 |
| 1. faixa de suporte | OLS 2 | suporte [0,075; 0,925] | item | −4,02 | 1,19 | [−6,37; −1,68] | < 0,001 | 253.951 | 15.014 | 978 |  |
| 1. faixa de suporte | OLS 2 | suporte [0,075; 0,925] | compra | −1,17 | 1,63 | [−4,36; 2,02] | 0,471 | 253.951 | 15.014 | 978 |  |
| 1. faixa de suporte | OLS 3 | suporte [0,075; 0,925] | item | −5,35 | 1,60 | [−8,49; −2,21] | < 0,001 | 253.951 | 15.014 | 978 |  |
| 1. faixa de suporte | OLS 3 | suporte [0,075; 0,925] | compra | −0,19 | 2,18 | [−4,48; 4,09] | 0,930 | 253.951 | 15.014 | 978 |  |
| 1. faixa de suporte | matching (a) | suporte [0,075; 0,925] | compra | −1,36 | 1,82 | [−4,92; 2,19] | — | — | 15.014 | 978 | EP agrupado (adapt.); EP AI 1,09 |
| 1. faixa de suporte | OLS 2 | suporte [0,10; 0,90] | item | −4,02 | 1,20 | [−6,37; −1,68] | < 0,001 | 253.927 | 15.007 | 978 |  |
| 1. faixa de suporte | OLS 2 | suporte [0,10; 0,90] | compra | −1,17 | 1,63 | [−4,36; 2,02] | 0,472 | 253.927 | 15.007 | 978 |  |
| 1. faixa de suporte | OLS 3 | suporte [0,10; 0,90] | item | −5,35 | 1,60 | [−8,49; −2,21] | < 0,001 | 253.927 | 15.007 | 978 |  |
| 1. faixa de suporte | OLS 3 | suporte [0,10; 0,90] | compra | −0,19 | 2,18 | [−4,48; 4,09] | 0,931 | 253.927 | 15.007 | 978 |  |
| 1. faixa de suporte | matching (a) | suporte [0,10; 0,90] | compra | −1,37 | 1,82 | [−4,93; 2,19] | — | — | 15.007 | 978 | EP agrupado (adapt.); EP AI 1,09 |
| 3. órgãos influentes | OLS 2 | suporte sem 0 órgão(s) mais influente(s) | item | −4,02 | 1,19 | [−6,37; −1,68] | < 0,001 | 253.951 | 15.014 | 978 |  |
| 3. órgãos influentes | OLS 2 | suporte sem 1 órgão(s) mais influente(s) | item | −3,13 | 1,30 | [−5,67; −0,58] | 0,016 | 208.593 | 13.809 | 977 | retirados: 1 |
| 3. órgãos influentes | OLS 2 | suporte sem 2 órgão(s) mais influente(s) | item | −3,70 | 1,26 | [−6,16; −1,23] | 0,003 | 202.545 | 13.770 | 976 | retirados: 2 |
| 3. órgãos influentes | OLS 2 | suporte sem 3 órgão(s) mais influente(s) | item | −3,26 | 1,20 | [−5,63; −0,90] | 0,007 | 200.792 | 13.733 | 975 | retirados: 3 |
| 3. órgãos influentes | OLS 2 | suporte sem 4 órgão(s) mais influente(s) | item | −2,98 | 1,19 | [−5,31; −0,65] | 0,012 | 199.133 | 13.687 | 974 | retirados: 4 |
| 3. órgãos influentes | OLS 2 | suporte sem 5 órgão(s) mais influente(s) | item | −3,27 | 1,17 | [−5,57; −0,97] | 0,005 | 197.628 | 13.613 | 973 | retirados: 5 |
| 3. órgãos influentes | OLS 3 | suporte sem 0 órgão(s) mais influente(s) | item | −5,35 | 1,60 | [−8,49; −2,21] | < 0,001 | 253.951 | 15.014 | 978 |  |
| 3. órgãos influentes | OLS 3 | suporte sem 1 órgão(s) mais influente(s) | item | −6,46 | 1,37 | [−9,14; −3,77] | < 0,001 | 247.903 | 14.975 | 977 | retirados: 1 |
| 3. órgãos influentes | OLS 3 | suporte sem 2 órgão(s) mais influente(s) | item | −6,97 | 1,26 | [−9,43; −4,50] | < 0,001 | 243.676 | 14.764 | 976 | retirados: 2 |
| 3. órgãos influentes | OLS 3 | suporte sem 3 órgão(s) mais influente(s) | item | −6,47 | 1,21 | [−8,85; −4,09] | < 0,001 | 242.017 | 14.718 | 975 | retirados: 3 |
| 3. órgãos influentes | OLS 3 | suporte sem 4 órgão(s) mais influente(s) | item | −5,80 | 1,46 | [−8,66; −2,94] | < 0,001 | 196.659 | 13.513 | 974 | retirados: 4 |
| 3. órgãos influentes | OLS 3 | suporte sem 5 órgão(s) mais influente(s) | item | −5,29 | 1,41 | [−8,05; −2,52] | < 0,001 | 194.906 | 13.476 | 973 | retirados: 5 |
| 5. especificação do escore | OLS 2 | suporte [0,075; 0,925] com PS1 | item | −4,26 | 1,04 | [−6,29; −2,23] | < 0,001 | 1.309.281 | 91.809 | 2.235 |  |
| 5. especificação do escore | OLS 3 | suporte [0,075; 0,925] com PS1 | item | −4,88 | 1,40 | [−7,62; −2,14] | < 0,001 | 1.309.281 | 91.809 | 2.235 |  |
| 5. especificação do escore | matching (a) | suporte com PS1 | compra | −2,91 | 1,86 | [−6,55; 0,73] | — | — | 91.809 | 2.235 | EP agrupado (adapt.); EP AI 0,43 |
| 5. especificação do escore | OLS 2 | suporte [0,075; 0,925] com PS3 | item | −4,02 | 1,19 | [−6,37; −1,68] | < 0,001 | 253.955 | 15.018 | 978 |  |
| 5. especificação do escore | OLS 3 | suporte [0,075; 0,925] com PS3 | item | −5,35 | 1,60 | [−8,49; −2,21] | < 0,001 | 253.955 | 15.018 | 978 |  |
| 5. especificação do escore | matching (a) | suporte com PS3 | compra | −1,17 | 2,05 | [−5,18; 2,84] | — | — | 15.018 | 978 | EP agrupado (adapt.); EP AI 1,08 |
| 5. especificação do escore | OLS 2 | suporte [0,075; 0,925] com PS4 | item | −4,02 | 1,19 | [−6,37; −1,68] | < 0,001 | 253.952 | 15.015 | 978 |  |
| 5. especificação do escore | OLS 3 | suporte [0,075; 0,925] com PS4 | item | −5,35 | 1,60 | [−8,49; −2,21] | < 0,001 | 253.952 | 15.015 | 978 |  |
| 5. especificação do escore | matching (a) | suporte com PS4 | compra | −1,59 | 2,12 | [−5,74; 2,56] | — | — | 15.015 | 978 | EP agrupado (adapt.); EP AI 1,07 |
| 6. medicamentos × demais | OLS 2 | suporte, medicamentos | item | −6,34 | 1,53 | [−9,34; −3,33] | < 0,001 | 80.925 | 5.339 | 350 |  |
| 6. medicamentos × demais | OLS 3 | suporte, medicamentos | item | −7,29 | 2,80 | [−12,80; −1,79] | 0,010 | 80.925 | 5.339 | 350 |  |
| 6. medicamentos × demais | OLS 2 | suporte, demais materiais | item | −3,08 | 1,47 | [−5,96; −0,20] | 0,036 | 173.026 | 11.510 | 959 |  |
| 6. medicamentos × demais | OLS 3 | suporte, demais materiais | item | −4,13 | 1,98 | [−8,02; −0,24] | 0,037 | 173.026 | 11.510 | 959 |  |
| 7. índice e dispersão | OLS 2 | suporte, células de baixa dispersão (sd_G ≤ 0,8033) | item | −4,37 | 1,14 | [−6,61; −2,13] | < 0,001 | 194.938 | 13.101 | 929 |  |
| 7. índice e dispersão | OLS 3 | suporte, células de baixa dispersão (sd_G ≤ 0,8033) | item | −4,49 | 1,36 | [−7,15; −1,83] | < 0,001 | 194.938 | 13.101 | 929 |  |
| 7. índice e dispersão | OLS 2 | suporte, índice truncado em ±3 (e_c3), inclui |e| > ln 10 | item | −3,70 | 1,64 | [−6,92; −0,49] | 0,024 | 262.507 | 15.014 | 978 |  |
| 7. índice e dispersão | OLS 3 | suporte, índice truncado em ±3 (e_c3), inclui |e| > ln 10 | item | −5,87 | 2,49 | [−10,74; −0,99] | 0,018 | 262.507 | 15.014 | 978 |  |
| 9. mesma UASG × UASGs diferentes | Mundlak (OLS 2 + média de AF da UASG) | completa | item | −4,66 | 1,34 | [−7,29; −2,03] | < 0,001 | 1.312.671 | 91.897 | 2.270 | entre UASGs: −3,73 (EP 1,38; p 0,007) |
| 9. mesma UASG × UASGs diferentes | Mundlak (OLS 2 + média de AF da UASG) | completa | compra | −1,16 | 1,60 | [−4,30; 1,98] | 0,469 | 1.312.671 | 91.897 | 2.270 | entre UASGs: −1,65 (EP 2,65; p 0,533) |
| 9. mesma UASG × UASGs diferentes | Mundlak (OLS 2 + média de AF da UASG) | suporte | item | −5,32 | 1,53 | [−8,32; −2,32] | < 0,001 | 253.951 | 15.014 | 978 | entre UASGs: −2,87 (EP 1,53; p 0,060) |
| 9. mesma UASG × UASGs diferentes | Mundlak (OLS 2 + média de AF da UASG) | suporte | compra | −0,13 | 2,10 | [−4,25; 3,98] | 0,950 | 253.951 | 15.014 | 978 | entre UASGs: −2,35 (EP 2,18; p 0,280) |
| 10. seleção dos homologados | OLS 2 | suporte, compras com 100% dos itens finais homologados | item | −0,46 | 1,66 | [−3,71; 2,80] | 0,784 | 85.704 | 7.701 | 831 |  |
| 10. seleção dos homologados | OLS 3 | suporte, compras com 100% dos itens finais homologados | item | 1,78 | 2,42 | [−2,97; 6,53] | 0,463 | 85.704 | 7.701 | 831 |  |

Regressão mediana na compra (média do índice; `quantreg`; bootstrap de pares por CNPJ):

| Amostra | Especificação | coef (lp) | EP bootstrap | IC95 percentil | p (normal) | réplicas | compras (AF) | CNPJs |
|---|---|---:|---:|---|---:|---:|---:|---:|
| suporte | sem controles | −4,43 | 2,01 | [−8,13; −0,81] | 0,027 | 299 | 15.014 (6.588) | 978 |
| suporte | com X do PS2 | −2,98 | 1,26 | [−5,51; −0,50] | 0,018 | 299 | 15.014 (6.588) | 978 |
| completa | sem controles | −3,63 | 1,95 | [−7,08; 0,58] | 0,063 | 299 | 91.897 (33.681) | 2.270 |
| completa | com X do PS2 | −3,53 | 1,11 | [−5,40; −0,95] | 0,002 | 299 | 91.897 (33.681) | 2.270 |

1. **Faixas de suporte:** estáveis. A faixa completa e as de 0,05, 0,075 e 0,10 dão a mesma ordem.
2. **Pesos:** a diferença entre item e compra se repete em todos os testes.
3. **Órgãos influentes:** retirar os 5 mais influentes, um a um, deixa o OLS 2 por item entre −3,0 e −4,0 lp e o OLS 3
   entre −5,3 e −7,0, todos com IC sem zero.
4. **Agrupamento por UASG:** as mesmas conclusões (tabela da seção 5).
5. **Escore:**
   - PS3 e PS4 dão os mesmos suportes e estimativas;
   - o PS1 inclui quase todas as compras, e o matching com ele dá −2,9 (IC agrupado [−6,5; 0,7]).
6. **Medicamentos × demais materiais:** −6,3 e −7,3 lp nos medicamentos (5.339 compras) e −3,1 e −4,1 nos demais
   (11.510), todos com IC sem zero. Ambos acima da regra de suporte.
7. **Índice:** células de baixa dispersão dão −4,4 e −4,5; o truncamento em ±3 dá −3,7 e −5,9.
8. **Regressão mediana na compra:** −3,0 (suporte) e −3,5 (completa) com X, IC de bootstrap sem zero; sem controles,
   −4,4 e −3,6. A mediana entre compras fica entre o OLS por compra e o OLS por item.
9. **Mesma UASG × entre UASGs (Mundlak):**
   - por item: dentro −4,7 lp e entre −3,7 (p = 0,007);
   - por compra: dentro −1,2 e entre −1,7, sem significância.
10. **Seleção dos homologados:** nas compras com 100% dos itens finais homologados (7.701 compras no suporte), a
    diferença por item é −0,5 (OLS 2) e +1,8 (OLS 3), sem significância.
    - A associação está nas compras em que algum item não foi homologado.
    - Pode ser seleção ou composição, e esta análise não separa as duas.

## 11. Os padrões do artigo se reproduzem?

**Padrões do artigo:**
- (i) nas florestas do Norte, o leilão selado tem receita ~10% maior, de forma estável em OLS, interações e matching;
- (ii) na Califórnia, não há diferença;
- (iii) os resultados resistem ao corte de suporte;
- (iv) parte da amostra foi sorteada, e as estimativas nela são parecidas.

Em leilão de compra, preço menor equivale a receita maior para o vendedor do artigo.

**Nesta base:**
- **(i) parcialmente.** O AF, que tem etapa fechada, está associado a preços menores por item (−4 a −6 lp), na direção do
  artigo. Porém, a concordância entre os três estimadores só ocorre com o peso por item. Com peso por compra, o OLS e o
  matching ficam perto de zero.
- **(iii) sim.** O corte de suporte muda pouco.
- **Ao contrário do artigo:** o suporte tira 84% das compras. Aqui, o modo é quase determinado pela UASG; no artigo, ele
  variava sobretudo com o tamanho e o local da venda.
- **(iv) não há equivalente.** A identificação depende só de independência condicional, que os testes de seleção e de
  ponderação colocam em dúvida.

A concordância parcial entre métodos não prova identificação.

## 12. Limitações causais

- A escolha do modo no Brasil não foi aleatorizada.
- **Persistência institucional:** o modo tem forte persistência por UASG. O escore com histórico tem AUC de 0,98, e só uma
  minoria das compras tem escore intermediário.
- O matching e o suporte comum não eliminam confundimento não observado. Equilíbrio nas covariáveis observadas não é
  validade causal.
- **Representatividade:** as UASGs que usam os dois modos, que identificam os efeitos fixos e o matching dentro da UASG,
  podem não representar as demais.
- O índice pode conter heterogeneidade técnica dentro do CATMAT, e a referência só existe para produtos comprados por ≥ 3
  outras UASGs no trimestre.
- O preço homologado só existe para itens com contratação bem-sucedida (seção 8).
- **Diferenças em relação ao artigo:**
  - não há o subconjunto aleatorizado;
  - os modos híbridos brasileiros não são os leilões abertos e selados do artigo;
  - o número de propostas não é comparável entre os modos e não foi estimado.
- A concordância entre OLS, interações e matching, quando ocorre, não prova identificação causal: os três usam a mesma
  hipótese de independência condicional.

**Falhas e reexecuções:**
- **Robustez:** falhou na primeira rodada (chave "u" dos resíduos colidia com o agrupamento por UASG). Foi corrigida e
  refeita com `--etapas=7_robustez,10_graficos`; o registro guarda a retomada.
- **Desfecho não executado:** número de propostas.
- **Matching por item:** diverge do pacote `Matching` por diferença de definição dos pesos (seção 7).

## 13. Respostas às perguntas

1. **OLS, interações e matching concordam?**
   - Com a mesma ponderação, sim. Por compra, todos ficam entre 0 e −2,5 lp, sem significância. Por item, OLS e
     interações ficam entre −4 e −6, e o matching (a), em −3,1.
   - O que divide os resultados é peso por item × por compra, não o método.
2. **Quanto mudam com o suporte comum?** Pouco nas estimativas: OLS 3 por item vai de −4,8 a −5,4 e por compra de −1,6 a
   −0,2. Mas a amostra cai de 91.897 para 15.014 compras.
3. **A diferença permanece depois de controlar a UASG?**
   - Por item, sim: −4,8 e −5,4 lp, com IC sem zero.
   - Por compra, não: −1,6 e −0,2.
4. **Há comparação suficiente dentro das mesmas unidades?** Não muita.
   - 731 UASGs (17%) usam os dois modos.
   - O matching na UASG perde 33,5% das compras do suporte e dá efeitos de sinais opostos nas AF e nas A.
   - Os efeitos fixos de UASG se identificam por essas unidades.
5. **Concentração das observações que identificam os coeficientes:**
   - 16–22 órgãos efetivos (peso por item) e 32–50 (por compra);
   - os 5 maiores órgãos têm de 26% a 39% da variação identificadora;
   - retirá-los, um a um, não muda o sinal.
6. **Os padrões do artigo se reproduzem?**
   - Em parte. A direção "etapa fechada → preço melhor para quem compra" aparece por item, e o corte de suporte não
     altera muito.
   - Diferem a dependência da ponderação e da seleção dos homologados, a escolha do modo quase determinística por UASG e a
     ausência de subconjunto aleatorizado.
7. **Descritivo ou causal?**
   - Todas as estimativas são associações descritivas ajustadas.
   - Nenhuma recebe interpretação causal: a escolha do modo não é aleatória, é muito persistente por UASG e depende de
     não observáveis.
   - O resultado mais próximo de causal no projeto continua sendo o estudo de eventos (−1,91 lp, sem significância), e
     esta replicação não o substitui.

## Gráficos

`graficos/`:

| Arquivo | Conteúdo |
|---|---|
| `g1_escore_por_modo.svg` | Sobreposição |
| `g2_equilibrio.svg` | Equilíbrio |
| `g3_efeitos.svg` | Efeitos e IC |
| `g4_robustez.svg` | Robustez |
| `g5_comparacao.svg` | Comparação com os estudos anteriores |

![Escore por modo](graficos/g1_escore_por_modo.svg)
![Equilíbrio](graficos/g2_equilibrio.svg)
![Efeitos](graficos/g3_efeitos.svg)
![Robustez](graficos/g4_robustez.svg)
![Comparação](graficos/g5_comparacao.svg)

## Reprodução

```
python analises/replicacao_athey_levin_seira_20261124/executar.py
```

**Pré-requisitos:**
- a base de 23/11;
- R com `quantreg` e `Matching`.

Versões, conferências, exclusões e falhas ficam em `registro_execucao.json`.
