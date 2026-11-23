# Parecer técnico: desenho de inferência causal para o efeito do modo de disputa (Aberto × Aberto-Fechado)

23/11/2026. Hipótese: o modo de disputa Aberto-Fechado (AF), em lugar do Aberto (A), afeta o resultado da contratação em
pregões eletrônicos: preço, sucesso, competição e prazo.

Este parecer revisa todos os estudos do projeto, de 03/11 a 22/11, e acrescenta diagnósticos de viabilidade feitos só
com leitura das bases (`diagnosticos*.py`, números em `diagnosticos.json`). Nenhum efeito causal novo foi estimado. Em
particular, o desfecho das unidades que mudaram de modo **não** foi olhado, para que o desenho principal possa ser
pré-registrado. O `pncp.db` foi aberto só para leitura; tamanho e mtime continuam iguais.

Convenções:
- Diferenças em log aparecem em log-pontos (lp) ou em % = 100·[exp(b) − 1].
- "Desconto" é 1 − P/R, em que P é o preço homologado e R o preço estimado pelo órgão.

---

## 1. Pergunta, estimando e desfechos

**O modo é uma política da unidade compradora, não um atributo do item.** A UASG define o modo no edital, para a compra
inteira. A unidade explica 82–84% da variação do uso do AF, e a categoria do objeto explica 2%. A distribuição das unidades
tem dois picos: 49% quase nunca usam AF e 23% usam quase sempre (estudo de uso de 21/11). Daí três consequências:

1. **Estimando de política.** O efeito de interesse é o de uma unidade passar a adotar o AF:
   τ = E[Y_ut(AF) − Y_ut(A) | a unidade u muda para AF, t ≥ E_u], em que E_u é a data da mudança. É um ATT das unidades
   que mudam. Estender o resultado às unidades que sempre usam o Aberto exige hipótese explícita de homogeneidade.
2. **Estimando de compra** (o do matching). τ_ATT = E[Y_i(AF) − Y_i(A) | D_i = AF]. Só é identificado sob ignorabilidade
   condicional, o que exige condicionar a quem decide, a unidade. Como se vê abaixo, isso deixa o matching quase sem suporte.
3. **Desfechos.**
   - **Principal:** log do preço unitário, medido contra o mesmo produto no mesmo período em *outras* unidades.
   - **Secundários:** sucesso (fracasso/deserto), entrada (nº de propostas), prazo até a homologação, desclassificações e
     porte do vencedor (ME/EPP).
   - **Desconto sobre o estimado: só como secundário.** O estimado é escolhido pelo órgão e varia com o modo (§3.3).

## 2. O que os estudos já mostram

| Estudo | Desenho | Amostra | AF − A no preço | Leitura |
|---|---|---|---|---|
| Painel (16/11) | FE CNPJ×produto + produto×mês | 191 mil itens, 656 CNPJs | **−4,5%** [−6,9; −2,1] | Associação estável em várias sensibilidades |
| Painel (16/11) | FE CNPJ×UASG×produto | 111 mil itens | −3,2% [−7,9; +1,7] | Mais fraca ao controlar a unidade |
| Painel anual (17/11) | FE CNPJ×produto + produto×ano, sigilo | 240 mil itens, 718 CNPJs | −4,8% [−6,9; −2,7] | Sem diferença por sigilo (interação p = 0,60) |
| Médias anuais (17/11) | Estratos produto×ano×UF | 76 mil itens não sigilosos | −8,7% [−14,0; −3,1] | Sem controle do comprador |
| Matching mensal (13/11) | CNPJ+UASG×CATMAT×mês×SRP×benefício×faixa Q | 1.604 itens, 19 CNPJs | −1,1% [−6,6; +4,8] | 0,12% dos AF; um órgão com ~90% |
| Matching anual, principal (17/11) | CNPJ×produto×ano×sigilo×SRP×benefício×faixa Q | 39 mil itens | −3,5% (s0), −7,0% (s1) | ≈ 4 órgãos efetivos; IC não confiável (§3.4) |
| Matching anual, simples (17/11) | CNPJ×produto×ano×sigilo | 100 mil itens | −1,3% [−5,5; +3,0] (s0), −4,3% [−9,5; +1,2] (s1) | Não significativo |
| Matchings de 03/11 e 13/11 | UASG×CATMAT (±ano, trimestre) | 14–129 mil itens | desconto +3 a +5 p.p.; preço −5% a −10% | Problemas de unidade e homologação; não são confirmações independentes |
| DiD (16/11) | Eventos órgão×produto | 7 eventos | — | Inviável: sem suporte nem pré-tendências |
| Desfecho (21/11) | FE UASG + mês | 5,1 milhões de itens | Não homologado: −0,7 p.p. [−1,8; +0,4] | Nenhuma diferença em fracasso ou deserção |
| Etapas (22/11) | Dentro do AF, PDFs | 1,34 milhão de itens | Fechada: +15,4 p.p. sobre a aberta | Mecanismo interno; não é o efeito do AF (§3.6) |

**Síntese.** Há uma **associação negativa, de poucos por cento, entre AF e o preço**, que mantém o sinal em painel,
médias e matching, sem diferença na chance de sucesso. Mas:

- ela enfraquece quando o desenho se aproxima da unidade que decide;
- nenhum desenho executado tem identificação causal crível;
- as análises reutilizam a mesma fonte e não são replicações independentes.

## 3. Diagnóstico do desenho de matching

### 3.1 A atribuição é por unidade e em regimes

Nas 727 UASGs mistas do Compras.gov.br (≥ 20 compras, de 5% a 95% de AF), as compras vêm em blocos no tempo. O número de
sequências de um mesmo modo é **0,74 vez o esperado** se a ordem fosse aleatória (mediana; 0,63 ponderando por compras),
e 54% das unidades rejeitam a ordem aleatória (Wald–Wolfowitz, z < −1,96). Nas outras plataformas o padrão é o mesmo
(0,68; 58%).

Ou seja, o modo muda por **regime da unidade**, e não compra a compra. Isso favorece desenhos de mudança no tempo (§4.1) e
desfavorece o pareamento transversal de itens.

### 3.2 O matching troca confundimento por suporte

Suporte dos desenhos de pareamento, na população do painel de 16/11 (97.350 itens AF, 330 órgãos):

| Estrato exato | Itens AF com par A | % dos AF | Órgãos | Maior órgão | Órgãos efetivos (1/HHI) |
|---|---:|---:|---:|---:|---:|
| CNPJ×produto×ano×sigilo (simples de 17/11) | 43.381 | 44,6% | 78 | 39% | 4,5 |
| + SRP×benefício×faixa Q (principal de 17/11) | 18.246 | 18,7% | 45 | 39% | 3,9 |
| UASG×produto, qualquer data | 6.087 | 6,3% | 102 | 24% | 11,4 |
| UASG×produto, ±365 dias | 2.064 | 2,1% | 59 | 15% | 12,4 |
| UASG×produto, ±180 dias | 581 | 0,6% | 38 | 26% | 8,2 |
| UASG×produto, ±90 dias | 233 | 0,24% | 27 | 38% | 5,5 |
| UASG×produto×sigilo×SRP×faixa Q, ±90 dias | 28 | 0,03% | 13 | 21% | 8,0 |

- **O suporte do matching atual vem de unidades diferentes.** Dentro do estrato por CNPJ, no máximo 14% dos itens AF
  (6.087 / 43.381) têm um par A na própria UASG, em qualquer data. Pelo menos 86% do contraste compara UASGs diferentes do
  mesmo órgão (comandos militares, secretarias estaduais), com equipes, fornecedores e logística distintos.
- **Na mesma unidade, o mesmo produto quase nunca é comprado nos dois modos em datas próximas.**

Não há, portanto, um matching de itens que seja ao mesmo tempo crível (mesma unidade e mesmo período) e com suporte.

### 3.3 Falha de balanço numa variável anterior à disputa: o preço estimado

O estimado R é fixado no planejamento, antes da disputa, e funciona como teste de balanço. No matching principal de
17/11 (sigilo = 0), os itens pareados por CNPJ×produto×ano×SRP×benefício×faixa Q têm:

| Grandeza, AF − A | Diferença |
|---|---|
| log R | **+0,131** (≈ +14%; IC +10,7 a +15,5 lp) |
| log P | −3,5% |
| Desconto | +8,3 p.p. |

No sigilo = 1, a diferença em log R é −5%: o sinal se inverte.

A diferença de 14% no estimado pode vir de três causas:
- as compras AF diferem em especificação ou condições de fornecimento não observadas;
- as unidades que usam AF pesquisam preço de outro jeito;
- o estimado responde ao modo.

Em qualquer caso, os grupos pareados não são comparáveis. Além disso, **o desconto maior do AF vem sobretudo do estimado
maior**, e não do preço menor. O mesmo se vê no painel: +4,3 p.p. de desconto com R +6,1% (não significativo).

### 3.4 A inferência depende de poucos órgãos

Nos matchings anuais, os 10 maiores órgãos têm 95–100% do peso, e o número efetivo de órgãos fica entre 3,9 e 4,5. O erro
padrão agrupado (CR1, com t(G − 1)) supõe muitos grupos de tamanho parecido. Com cerca de 4 grupos efetivos, ele é otimista.
Por isso o IC de −3,5% [−4,7; −2,4] no matching principal não é crível.

Correções possíveis:
- bootstrap selvagem restrito por grupo, com pesos de Webb;
- inferência por aleatorização entre unidades;
- relato com cada órgão retirado por vez.

Ver MacKinnon e Webb (2017) e Carter, Schnepel e Steigerwald (2017).

### 3.5 Número de licitantes: mediador, não controle

O modo é anunciado no edital antes da entrega das propostas, e as empresas decidem entrar já sabendo qual é. O número de
licitantes é, portanto, **posterior ao tratamento**. Controlar por ele estima um efeito direto controlado (Acharya,
Blackwell e Sen, 2016), que só é válido se nada confundir a relação entre licitantes e preço. É o "mau controle" de
Angrist e Pischke (2009). Há ainda um problema prático: no matching mensal, só 9% dos itens AF têm o número de licitantes
na base, porque as compras dominantes ficaram sem PDF.

Recomendação:
- tratar o número de licitantes como **desfecho** (efeito sobre a entrada) e como canal;
- como moderador ou controle, usar uma medida **anterior ao tratamento**: a competição esperada. Por exemplo, o número de
  fornecedores distintos que venceram o mesmo CATMAT na UF nos 12 meses anteriores, em outras unidades
  (`resultados.ni_fornecedor`), e, com os PDFs, o número médio de propostas em compras anteriores do produto.

### 3.6 O ganho da etapa fechada não é o efeito do AF

Na regra do AF (Decreto 10.024/2019 e IN SEGES/ME 73/2022):
- a etapa aberta termina em hora aleatória;
- seguem para o lance fechado o melhor lance e os que estão até 10% acima dele (no mínimo três).

Por isso o licitante não precisa competir na etapa aberta; basta ficar dentro da margem. O formato é um leilão
"anglo-holandês" (Klemperer, 2002). No Aberto, a disputa só termina quando ninguém mais dá lance: prorroga-se enquanto
houver lance nos 2 minutos finais.

Um caso concreto (pregão 1914/2023, UASG 943001, item 1): nenhum lance foi dado na etapa aberta. Todos os lances
(R$ 2.300, R$ 2.990 e R$ 3.450) vieram na etapa fechada, contra uma melhor proposta de R$ 3.700.

Nos mesmos estratos CNPJ×produto×ano×sigilo (38.486 itens AF ligados ao PDF e 53.221 itens A, 67 órgãos):

| Comparação, em log do preço unitário | AF − A final | IC95 | Sem o maior órgão |
|---|---:|---|---:|
| AF, fim da etapa aberta | **+11,8 lp (+12,5%)** | [+5,5; +18,0] | +7,2 lp |
| AF, após a etapa fechada | −8,2 lp (−7,9%) | [−12,0; −4,3] | — |
| AF, preço final (PDF = API; mediana da diferença 0) | **−3,8 lp (−3,7%)** | [−7,8; +0,3] | −6,1 lp [−10,8; −1,4] |

Em desconto, o resultado é o mesmo:
- a etapa aberta do AF dá 22,3%, contra 29,3% de desconto final no Aberto: −7,0 p.p. [−9,9; −4,2];
- o AF termina em 33,9%: +4,6 p.p. [+2,3; +6,9].

**Leitura.** A diferença entre a etapa aberta e o preço final do AF é medida no mesmo item, portanto sem confundimento:
são cerca de 15,5 lp. Se a etapa aberta do AF representasse o que o Aberto teria produzido, o efeito do AF seria de
cerca de −14%. Mas toda comparação entre modos dá algo entre −1% e −9%.

Logo, a etapa aberta do AF **não** é o contrafactual do Aberto. Os licitantes guardam o lance para a fechada. Entre 60%
(em desconto) e 75% (em log) do "ganho da fechada" é competição deslocada da etapa aberta. A decomposição por etapa
descreve o mecanismo dentro do AF; não mede o efeito do modo.

### 3.7 Seleção por homologação

O AF não altera fracasso nem deserção dentro do mesmo órgão. A diferença em itens não homologados é −0,7 p.p.
[−1,8; +0,4]. A seleção diferencial por sucesso é, portanto, de segunda ordem. Ainda assim, convém reportar limites de Lee
(2009), que aqui devem sair estreitos.

### 3.8 Produto e dados

- **Unidade de fornecimento.** CATMAT + unidade não garante o mesmo produto: 26% das células do teste revisado em 13/11
  tinham mais de uma unidade registrada. Erros de unidade geram contrastes extremos (o caso da sertralina no DiD) e exigem truncagem
  definida antes de estimar.
- **Catálogo em 2026.** No Compras.gov.br, os itens de 2026 têm CATMAT em só 29% dos casos, contra 95–98% em 2023–2025.
  É preciso investigar essa lacuna, ou cortar em 2025.
- **Outras plataformas.** Não têm CATMAT (0%) e têm preço homologado em só 41–47% dos itens. O desenho principal fica no
  Compras.gov.br.
- **Defeito no estudo de 17/11.** No `resultados.json`, o matching principal em log do preço foi sobrescrito pela
  subamostra com estimado válido. Com sigilo = 0 as duas amostras coincidem; com sigilo = 1, a diferença é pequena
  (β −0,0725 contra −0,0733).

## 4. Desenhos recomendados

### 4.1 Principal: estudo de eventos na unidade compradora (DiD com adoção escalonada, que liga e desliga)

**Variação usada.** Mudanças de regime de modo na mesma UASG do Compras.gov.br. Com um critério de variação de pelo menos
50 p.p. na parcela de AF entre os 6 meses antes e os 6 depois, e pelo menos 5 compras de cada lado, há:

| Mudança | Episódios | UASGs | CNPJs | Itens com índice de preço nas janelas |
|---|---:|---:|---:|---:|
| A → AF | 164 | 160 | 87 | 31.529 |
| AF → A | 108 | 107 | 68 | 30.688 |
| Estritas (≤ 10% → ≥ 90%, ou o inverso) | 21 + 12 | | | 7.394 |

Como controles, há 1.300 UASGs que sempre usam o Aberto e 619 que sempre usam o AF (≥ 20 compras). Também servem as
unidades que ainda não mudaram.

**Desfecho.** O índice de preço do item: e_iut = log P − média de log P do mesmo produto (CATMAT + unidade), no mesmo
trimestre, nas outras unidades. Exige-se pelo menos 5 itens de pelo menos 3 outras unidades. No Compras.gov.br, entre
2023 e jun/2026, há 1,63 milhão de itens com índice em 4.445 UASGs.

**Estimadores robustos a efeitos heterogêneos.** Como o tratamento liga e desliga:
- de Chaisemartin e D'Haultfœuille (2020; 2024; `did_multiplegt_dyn`), separando quem entra e quem sai do AF;
- imputação de Borusyak, Jaravel e Spiess (2024), com efeitos fixos de unidade e de produto × mês estimados nas
  observações não tratadas;
- Callaway e Sant'Anna (2021) com controles ainda não tratados, como sensibilidade.

O TWFE comum não deve ser usado: ele produz pesos negativos, e no painel de 16/11 já se encontraram 24% dos itens AF
com peso implícito negativo.

**Testes que tornam o desenho falsificável:**
1. **Pré-tendências** em 6 a 12 meses antes da mudança, com a sensibilidade de Rambachan e Roth (2023) para violações
   limitadas das tendências paralelas.
2. **Simetria.** Se o AF baixa o preço, A → AF e AF → A têm sinais opostos. Já a reversão à média (unidades que mudam
   depois de um período ruim) gera o mesmo sinal nos dois sentidos. É o melhor teste disponível contra o "Ashenfelter dip".
3. **Desfechos placebo.** No momento da mudança, não devem mudar:
   - o índice do estimado (log R contra o mesmo produto em outras unidades): se mudar, houve mudança simultânea de equipe
     ou de pesquisa de preço;
   - o mix de categorias, o nº de itens por compra, a parcela SRP e a faixa de quantidade.
4. **Composição.** Restringir aos produtos comprados antes e depois na mesma unidade.
5. **Antecipação.** Datar o evento pela publicação do primeiro edital no novo modo.

**Inferência.** Agrupamento por UASG ou CNPJ (87 CNPJs nas mudanças A → AF e 68 nas AF → A), com bootstrap selvagem, e inferência por aleatorização
das datas de evento.

**Poder** (calculado só com placebos em 1.104 unidades que não mudam, sem olhar quem mudou). O ruído de um contraste
antes/depois de ±6 meses por unidade é de 0,36 log (0,28 robusto). Daí o efeito mínimo detectável, com 80% de poder e 5%
de significância:

| Episódios usados | Efeito mínimo detectável | Versão robusta |
|---|---:|---:|
| A → AF (164) | 8,5 lp (≈ 8%) | 6,5 lp |
| Os dois sentidos com sinal invertido (272; supõe simetria) | 6,9 lp (≈ 7%) | 5,3 lp |
| Só os estritos (33) | 18 lp | 14 lp |

**O desenho só detecta efeitos de cerca de 6–8%, acima dos −4,5% do painel.** Para chegar a 4–5%, é preciso reduzir o
ruído:
- janelas de ±12 meses;
- estimador de imputação no nível do item, em vez da média simples;
- truncagem e peso por precisão definidos antes de estimar;
- produtos bem identificados;
- combinação com o desenho intraleilão (§4.2), que normaliza o preço pela proposta inicial.

O efeito mínimo detectável deve constar do pré-registro. Um resultado nulo com esse poder não demonstra ausência de efeito.

### 4.2 Complementar: desenho intraleilão comparado, com os PDFs do Aberto

O relatório de cada item traz:
- todas as **propostas iniciais**, entregues em sigilo antes da sessão nos dois modos, com marca, fabricante, modelo e
  ME/EPP;
- o **registro dos lances com horário**;
- o chat, que marca o início e o fim da etapa fechada;
- as desclassificações e a negociação.

Com isso dá para estimar:
- **Ganho da disputa.** log(preço final) − log(melhor proposta inicial válida), comparado entre A e AF. A proposta inicial
  absorve a heterogeneidade do item: especificação, quantidade, logística, risco de pagamento e base local de fornecedores.
  O ganho não depende do estimado R. Pode ser estimado dentro das unidades que mudam de modo, ou seja, dentro do §4.1, que
  é o mais crível, ou em células unidade × produto × período.
- **Hipótese a testar.** O modo não altera a distribuição das propostas iniciais nem a entrada. Compara-se o índice da
  melhor proposta inicial e o nº de propostas antes e depois da mudança. Se a entrada mudar, efeito total = efeito sobre a
  entrada + efeito na disputa, cada um reportado separadamente.
- **Mecanismo.** Parcela de itens AF sem lance na etapa aberta; nº e momento dos lances. Previsões do leilão
  anglo-holandês: maior ganho com poucos licitantes fortes ou assimétricos, e menor espaço para conluio.
- **Equivalência do produto.** Restringir a itens cujas propostas oferecem a mesma marca e o mesmo modelo.

Para isso é preciso:
- o modo `aberto` em `registro.py` e `baixar_manual.py`;
- estender o parser para o Aberto e para os campos novos;
- baixar primeiro as compras do Aberto das unidades que mudaram de modo, nas janelas do evento (≈ 4–5 mil compras em
  ±6 meses; cerca do dobro em ±12). A lista de 23/11 (células do matching) fica em segundo lugar.

### 4.3 Matching: refeito no nível da unidade; no item, só descritivo

- **Matching de unidades com diferenças em diferenças.** Cada unidade que muda é pareada a unidades estáveis com o mesmo
  histórico de modo, trajetória pré-evento parecida no índice de preço e no do estimado, e mesmo porte, esfera, região e
  mix de categorias. Depois aplica-se o DiD (PanelMatch de Imai, Kim e Wang, 2023) ou o DiD sintético (Arkhangelsky et al.,
  2021) para as unidades grandes. Esta é a forma de manter o espírito do matching respeitando a atribuição por unidade.
- **Matching de itens**, se mantido, só como descritivo:
  - janela de datas (±90/180 dias) no lugar do ano civil;
  - covariáveis de "tipo do comprador" medidas em outros itens ou períodos (índice de preço e índice do estimado da
    unidade, porte, esfera, região, plataforma);
  - competição esperada anterior ao tratamento, quantidade, SRP, benefício e sigilo;
  - estimador duplamente robusto (AIPW ou balanceamento por entropia), com aparamento por sobreposição;
  - sensibilidade a confundimento não observado (Γ de Rosenbaum; valores de robustez de Cinelli e Hazlett, 2020);
  - bootstrap selvagem;
  - log P como desfecho principal e log R como teste de balanço;
  - relato da fração dos AF com suporte (validade externa).

### 4.4 Exploratórios: variáveis instrumentais e experimentos naturais

- **Normas que mudam o modo.** Decretos estaduais e municipais, orientações de tribunais de contas, padrões de plataforma.
  Não houve mudança simultânea de várias UASGs do mesmo CNPJ no Compras.gov.br (0 de 33 episódios estritos), o que indica
  ausência de reformas de cima para baixo em 2023–2026. As políticas estaduais fortes (Ceará 98% AF, Paraíba 82%) aparecem
  como níveis estáveis, sem mudança datada na janela. Nas outras plataformas, 5 e 8 episódios simultâneos, sobretudo
  municipais, merecem busca documental. Só um ato
  normativo datado sustentaria uma variável instrumental ou um DiD por esfera.
- **Desenho de examinador.** O PDF identifica quem adjudica e homologa ("Adjudicado e Homologado por CPF … – nome"). Seria
  viável se houvesse vários agentes por UASG, distribuição quase aleatória dentro de unidade × categoria × mês e propensão
  ao AF diferente entre eles (Frandsen, Lefgren e Leslie, 2023). Mas há dois obstáculos:
  - o modo é fixado no edital, possivelmente por outra pessoa, o que deixa a primeira etapa fraca;
  - o agente também julga, negocia e desclassifica, o que viola a exclusão. Nesse caso, o desfecho seria o melhor lance
    antes da negociação.
- **Regressão descontínua.** Não se aplica: não há limiar que determine o modo.

### 4.5 Não recomendados

- Tratar o ganho intraleilão da etapa fechada (15 p.p.) como efeito do AF.
- Usar o matching transversal por CNPJ como desenho principal.
- Controlar pelo número de licitantes ou pelo vencedor na especificação principal.
- Usar o desconto sobre o estimado como desfecho principal.
- Fazer DiD por órgão × produto, que não tem suporte.
- Misturar as outras plataformas sem código de catálogo.
- Acrescentar sensibilidades depois de ver os resultados sem registrá-las como exploratórias.

## 5. Próximos passos, em ordem

1. **Pré-registro do §4.1.** Definir:
   - o evento (limiar, janelas e data pelo edital) e o desfecho (índice, truncagem e produtos);
   - os estimadores, a inferência e o efeito mínimo detectável;
   - os testes de falsificação (pré-tendências, simetria e placebos) e as regras de decisão.
2. **Base unidade × mês do índice.** O protótipo está em `diagnosticos_e.py`; a extração fica em
   `dados/parecer_desenho_causal/`. Antes, corrigir a lacuna de CATMAT em 2026 e padronizar a unidade de fornecimento.
3. **Competição esperada** a partir de `resultados`, como moderador anterior ao tratamento.
4. **PDFs do Aberto.**
   - Gerar a lista das compras das unidades que mudaram de modo (±12 meses) e de uma amostra de unidades estáveis.
   - Criar o `--modo aberto` no download.
   - Estender o parser: propostas iniciais, marca, ME/EPP e lances com horário, nos dois modos.
5. Rodar o §4.1 e depois o §4.2. O §4.3 entra como corroboração; o §4.4 só se aparecer uma fonte documental.

## 6. Parecer técnico (resumo)

1. **A hipótese ainda não foi testada de forma causal.** Os estudos mostram uma associação negativa e estável, de poucos
   por cento, entre AF e o preço unitário (painel: −4,5%, IC −6,9 a −2,1), sem efeito sobre fracasso ou deserção. Nenhum
   desenho executado identifica efeito causal.
2. **O matching atual não deve ser o desenho principal.** O modo é uma política da unidade, adotada em regimes. Para ter
   suporte, o matching compara UASGs diferentes: pelo menos 86% do contraste. Na mesma UASG, só 0,24% dos itens AF têm par
   do Aberto a até 90 dias. O estimado, fixado antes da disputa, difere 14% entre os pareados (falha de balanço), e a
   inferência depende de cerca de 4 órgãos efetivos.
3. **O ganho da etapa fechada (≈ 15 p.p.) não é o efeito do AF.** A etapa aberta do AF fica 12% acima do preço final do
   Aberto, porque os licitantes guardam o lance para a fechada. Entre 60% e 75% desse ganho é competição deslocada. O que
   se compara entre modos é o preço final: cerca de −4% (associação).
4. **Número de licitantes não deve ser controle.** É posterior à escolha do modo. Use-o como desfecho (entrada) e como
   canal, e controle pela competição esperada medida antes da compra.
5. **Desenho recomendado: estudo de eventos na unidade compradora.** São 164 mudanças A → AF e 108 AF → A no
   Compras.gov.br. O desfecho é um índice de preço contra o mesmo produto em outras unidades, com estimadores robustos a
   efeitos heterogêneos (de Chaisemartin–D'Haultfœuille; Borusyak–Jaravel–Spiess) e testes de pré-tendência, de simetria
   entre entrar e sair do AF e com desfechos placebo. Com o poder atual ele detecta efeitos de 6–8%; reduzir o ruído (§4.1)
   e pré-registrar antes de estimar.
6. **Desenho complementar: comparação intraleilão com os PDFs do Aberto.** Mede o ganho da disputa a partir da melhor
   proposta inicial, o que neutraliza a heterogeneidade do item e o estimado, e o efeito sobre a entrada. Exige baixar os
   PDFs do Aberto, começando pelas unidades que mudaram de modo, e estender o parser.
7. **Matching só como corroboração.** No nível da unidade (matching com DiD ou DiD sintético) ou, no item, como
   descritivo, com covariáveis de tipo do comprador, estimador duplamente robusto, análise de sensibilidade e bootstrap
   selvagem.
8. **Formulação sustentada hoje:** "Na amostra de pregões eletrônicos de materiais do Compras.gov.br, o Aberto-Fechado
   está associado a preços unitários alguns por cento menores, sem diferença na chance de sucesso. O efeito causal da troca
   do modo ainda não foi estabelecido. A etapa fechada concentra competição que, no Aberto, ocorreria na própria disputa
   aberta."

---

## Diagnósticos produzidos (reprodução)

Os scripts rodam da pasta `PNCP-Automation`. O `pncp.db` é aberto só para leitura, com tamanho e mtime conferidos ao final.

| Script | O que faz | Tempo |
|---|---|---|
| `diagnosticos.py --pncp-db ../dados/pncp.db --extracao dados/extracao/aberto-fechado_parser-1.9.1.db` | A: sequência e mudanças de regime; B: suporte dos pareamentos; C: etapa aberta do AF × Aberto | ~2 min |
| `diagnosticos_d.py --pncp-db ../dados/pncp.db` | Mudanças com critério flexível; cobertura de preço por fonte | ~7 min |
| `diagnosticos_e.py --pncp-db ../dados/pncp.db` | Índice de preço e poder por placebos | ~20 min na primeira vez |

Saídas: `diagnosticos.json`, `eventos_regime.csv`, `eventos_regime_flexivel.csv` e `placebos_unidades_estaveis.csv`.

## Referências

- Acharya, Blackwell e Sen (2016), *APSR*: efeitos diretos controlados.
- Angrist e Pischke (2009), *Mostly Harmless Econometrics*: maus controles.
- Arkhangelsky, Athey, Hirshberg, Imbens e Wager (2021), *AER*: DiD sintético.
- Borusyak, Jaravel e Spiess (2024), *REStud*: estimador de imputação.
- Callaway e Sant'Anna (2021), *J. Econometrics*.
- Carter, Schnepel e Steigerwald (2017), *REStat*: número efetivo de grupos.
- Cinelli e Hazlett (2020), *JRSS-B*.
- de Chaisemartin e D'Haultfœuille (2020), *AER*; (2024), *REStat*.
- Frandsen, Lefgren e Leslie (2023), *AER*: desenhos de examinador.
- Imai, Kim e Wang (2023), *AJPS*: PanelMatch.
- Klemperer (2002), *J. Economic Perspectives*: leilão anglo-holandês.
- Lee (2009), *REStud*: limites sob seleção.
- MacKinnon e Webb (2017), *J. Applied Econometrics*: bootstrap selvagem com poucos grupos tratados.
- Rambachan e Roth (2023), *REStud*.
- Rosenbaum (2002), *Observational Studies*.
- Roth, Sant'Anna, Bilinski e Poe (2023), *J. Econometrics*.
