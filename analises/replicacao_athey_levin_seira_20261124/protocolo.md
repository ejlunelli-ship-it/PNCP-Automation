# Protocolo: replicação empírica adaptada de Athey, Levin e Seira (2011), Fase 1 (24/11/2026)

**Classificação:** replicação metodológica adaptada e exploratória. Não é identificação causal nova. Todas as estimativas
são associações ajustadas. Este protocolo foi escrito antes de qualquer estimativa; o hash SHA-256 vai para
`registro_execucao.json`. Nenhuma especificação é escolhida pelo valor-p. O modelo estrutural (Fase 2) não é executado.

**Referência:** Athey, Levin e Seira (2011), *QJE* 126: 207–257 (`dados/qje_2Fqjq001.pdf`).
- **Seção III.C:**
  - logit do formato com características do lote, dummies de ano, trimestre, área e espécie;
  - o tamanho da venda entra como escada de 10 degraus, perto dos decis;
  - descartam-se as vendas com escore fora de [0,075; 0,925].
- **Seção IV.A:**
  - eq. (5): Y = f(SEALED, X, N, ε), com τ = E[f(1,·) − f(0,·)] sob independência condicional;
  - eq. (6): OLS;
  - segunda abordagem: SEALED × covariáveis, com o efeito médio na amostra;
  - eq. (7): matching simétrico pelos M = 4 vizinhos mais próximos no escore, com EP robustos de Abadie e Imbens (2006);
  - nota 15: regressão mediana como robustez.

**Correspondência:**

| Artigo | Esta replicação |
|---|---|
| SEALED | AF (Aberto-Fechado) |
| Aberto (referência) | A (Aberto) |
| Venda | Compra (pregão) |
| Preço por unidade de volume | Índice de preço do item |

## 1. Dados (arquivos reais)

**Base de 23/11 em `dados/testes_desenho_causal/`**, gerada por `analises/testes_desenho_causal_20261123/preparar.py` a
partir do `pncp.db`, só leitura.

- **`compras.pkl`**, uma linha por compra:
  - chaves: `compra` (número de controle PNCP), `unidade` (UASG), `u` (índice da UASG), `cnpj` (órgão);
  - modo e características: `esfera`, `uf`, `regiao`, `af` (1 = AF, 0 = A), `srp`, `pub`, `abertura`, `m` (mês da
    abertura);
  - médias por compra: `med`, `excl`, `sig`, `comp`, `eq`, `suc`, `fra`, `des`, `n_itens` (log do nº de itens de material).
- **`itens.pkl`**, um item de material (registro principal) por linha:
  - identificação: `compra`, `item`, `catmat`, `classe`, `un_n` (unidade padronizada), `prod` (CATMAT × unidade);
  - período e situação: `tri` (trimestre da abertura), `criterio`, `menor`, `situacao`, `hom`, `final`, `fracassado`,
    `deserto`;
  - valores: `q`, `r` (valor unitário estimado), `p` (homologado);
  - flags: `sigilo`, `excl`, `med`;
  - índices: `logp`, `e`, `e_ok`, `e_c3`, `eq_ok`, `comp`, `desc`, `suc`, `fra`, `des`.
- **`unidades.pkl`** e **`paineis.npz`**: `N` e `A` = compras e compras AF por UASG × mês, de 2022-01 a 2026-09.
- **Dispersão contemporânea** (sensibilidade): `sd_G` da célula, calculado por `motor_robustez.tabela_uasg`
  (`../robustez_dispersao_20261123/`).

O `pncp.db` não é lido nem alterado, nada anterior é alterado, e as saídas grandes ficam em
`dados/replicacao_athey_levin_seira/`, fora do git.

## 2. Amostra

- **Compras:** Pregão Eletrônico do Compras.gov.br (`fonte = 'dados_abertos'`), modo Aberto ou Aberto-Fechado.
- **Período de estimação:** abertura de 2023-01 a 2025-10.
  - 2022 entra só para o histórico (ver X abaixo).
  - Nada posterior a 2025-10 entra, o que deixa fora os 56 eventos reservados para validação (mudanças de modo
    posteriores a 2025-10). O script confere isso.
  - O índice de um item de 2025-10 usa, como referência, outras UASGs no mesmo trimestre (out.–dez.). É a construção
    validada, sem informação de modo.
- **Itens do desfecho de preço:**
  - material, registro principal, julgamento por menor preço;
  - homologado, com preço unitário > 0;
  - CATMAT e unidade padronizada;
  - índice disponível: `e_ok` finito, isto é, referência com ≥ 5 itens de ≥ 3 outras UASGs e |e| ≤ ln 10;
  - UASG e CNPJ presentes.
- **Compras da análise:** as que têm pelo menos 1 item desse tipo.

Todas as exclusões são contadas, por etapa, em `tabelas/amostra_exclusoes.csv`.

**Unidade de decisão.** O modo é escolhido na compra:
- o escore é estimado com uma linha por compra, sem pesos;
- as regressões de item são agrupadas por órgão;
- o matching é feito entre compras.

## 3. Desfechos

**Principal:** Y_i = 100·`e_ok` = 100[ln P_i − ref_{c,t,−u}], em lp.
- c = CATMAT × unidade; t = trimestre da abertura; u = UASG.
- A referência é a média do log P do mesmo produto e trimestre nas outras UASGs, com a construção validada sem
  alteração.
- No nível da compra, o desfecho é a média de Y nos itens com índice (peso igual por compra).

**Secundários:**

| Nº | Desfecho | Amostra |
|---|---|---|
| 1 | Desconto: 100·`desc` = 100(1 − P/R) | Itens homologados não sigilosos, com desconto entre −100% e 99% |
| 2 | Log do preço: 100·`logp` | Com efeitos fixos de produto × trimestre |
| 3 | Homologação: `suc` | Itens de material, menor preço, com situação final (homologado, deserto, fracassado), com ou sem índice |
| 4 | Fracasso e deserção: `fra` e `des` | Separados, na mesma amostra de 3 |
| 5 | Número de propostas | **Não executado:** o número de licitantes só existe nos PDFs, baixados para AF e Fechado-Aberto, mas não para o Aberto; não há identificação comparável e nenhuma aproximação é usada |

**Nunca como controle:** o número de licitantes.

## 4. Covariáveis X (anteriores à escolha do modo)

Os campos são calculados na compra e usam só informação disponível antes da publicação do edital.

| Bloco | Variável |
|---|---|
| Período | Trimestre da abertura (dummies) |
| Localização e instituição | Região (5) e esfera |
| Tamanho | Decis do nº de itens de material da compra: escada de 10 degraus, como no artigo |
| Objeto | Grupo CATMAT dominante (2 primeiros dígitos da classe; grupos com < 1% das compras vão para "outros"); parcela de medicamentos (classe 65) |
| Quantidade prevista | Média de `eq_ok` (log da quantidade contra a mesma célula nas outras UASGs), com indicador de ausente |
| Competição esperada | Média de `comp`: log(1 + vencedores distintos do mesmo CATMAT na mesma UF nos 4 trimestres anteriores, em outras unidades) |
| Histórico institucional | Parcela AF das compras da UASG nos 12 meses anteriores ao mês da compra; categorias: sem histórico, 0, (0; 0,1], (0,1; 0,5], (0,5; 0,9], (0,9; 1), 1. E log(1 + nº de compras nesses 12 meses) |

**Decididas junto com o modo** (SRP, sigilo do orçamento, parcela de itens exclusivos ME/EPP): não são controles
exógenos por hipótese, porque saem no mesmo edital. Entram só como sensibilidade.

**Valor estimado:** decis do log do valor total estimado (Σ q·R dos itens de material), com categoria "ausente" (sigilo).
Entra como sensibilidade, conforme o pedido.

## 5. Modelo 1: logit do modo (compra)

Pr(AF_j = 1 | X_j) = Λ(X_j′γ), por máxima verossimilhança.

| Especificação | Conteúdo |
|---|---|
| PS1 | Período, região, esfera, tamanho, objeto, quantidade, competição |
| **PS2 (principal)** | PS1 + histórico institucional. É o análogo das dummies de área administrativa do artigo; dummies de UASG não são viáveis, porque UASGs de um modo só dão separação perfeita |
| PS3 | PS2 + SRP, sigilo e exclusividade ME/EPP |
| PS4 | PS2 + decis do valor estimado |

**Relato:**
- coeficientes, EP robusto e EP agrupado por CNPJ;
- probabilidades previstas;
- AUC, pseudo-R² de McFadden, Brier e calibração por decis;
- distribuição do escore por modo.

## 6. Suporte comum

**Restrição principal:** 0,075 ≤ p̂ ≤ 0,925, com o PS2 (artigo). **Sensibilidades:** amostra completa, [0,05; 0,95] e
[0,10; 0,90].

Para cada faixa:
- itens, compras, UASGs e CNPJs que ficam e que saem;
- UASGs que usam os dois modos;
- diferenças padronizadas das covariáveis;
- concentração por UASG e CNPJ;
- distribuição do escore por modo.

**Sobreposição dentro das UASGs:** parcela de compras e itens em UASGs com os dois modos no período. **Sobreposição nos
grupos:** distribuição do escore por modo nos 6 maiores grupos de material.

**Regra:** se a faixa principal deixar menos de 200 compras de cada modo ou menos de 30 CNPJs com AF, o problema é
registrado, e as estimativas nessa faixa são relatadas como não identificadas, sem forçar.

## 7. Modelo 2: OLS (eq. 6), item

| Especificação | Conteúdo |
|---|---|
| OLS 1 | Y = α + βAF |
| OLS 2 | + X. No item: grupo de 2 dígitos do próprio item, `comp` e `eq_ok` do item (com indicador de ausente). Da compra: trimestre, região, esfera, decis de tamanho, histórico e parcela de medicamentos |
| OLS 3 | + efeitos fixos de UASG |
| OLS 4 | + efeitos fixos de UASG e de produto × trimestre (identificação: o produto × trimestre precisa ter itens dos dois modos) |

- **Estimação:** efeitos fixos absorvidos por projeções alternadas (tolerância de 10⁻¹⁰), seguidas de MQ ponderados nos
  resíduos (Frisch–Waugh–Lovell).
- **Pesos:**
  - **por item** (w = 1): parâmetro = diferença média entre itens;
  - **igual por compra** (w = 1/nº de itens da compra na amostra): parâmetro = diferença média entre compras.
- **Inferência:**
  - EP CR1 agrupado por CNPJ (principal) e por UASG (sensibilidade);
  - p e IC95 pela t(G − 1);
  - os efeitos fixos aninhados no grupo não entram na correção de graus de liberdade (como no reghdfe).
- **Amostras:** completa e suporte principal.
- **Relato:**
  - β em lp, EP, IC95, p e conversão percentual exata 100(e^{β/100} − 1);
  - itens, compras, UASGs e CNPJs;
  - observações no suporte;
  - G e nº efetivo de grupos da variação identificadora, 1/Σ s_g², com s_g = parcela de Σ w x̃² do grupo (x̃ = AF depois de
    retirar X e os efeitos fixos);
  - parcela dos maiores órgãos nessa variação.

## 8. Modelo 3: efeitos heterogêneos

Y = α + βAF + X′γ + (AF × D)′δ + ε, sobre a base OLS 2. A base OLS 3 é sensibilidade.

**Dimensões e faixas** (fixadas aqui):

| Dimensão | Faixas |
|---|---|
| Valor estimado | Terços + ausente |
| Quantidade prevista (`eq_ok` do item) | Terços + ausente |
| Classe de produto | Medicamentos, os 5 maiores grupos restantes e outros |
| Esfera | As que existirem |
| Competição esperada (`comp` do item) | Terços |

Os efeitos principais das faixas também entram.

- **Suporte por faixa:** ≥ 50 compras de cada modo e ≥ 10 CNPJs com AF. Abaixo disso, a faixa se junta à vizinha (ou a
  "outros").
- **Efeito médio ajustado na população de análise:** média ponderada de ŷ(AF = 1) − ŷ(AF = 0) = β + δ′D̄, com EP pelo método
  delta e a matriz agrupada.
  - O coeficiente de AF sozinho não é lido como efeito médio.
- **Teste de heterogeneidade:** Wald de δ = 0 por dimensão, com F(q, G − 1). Holm nas 5 dimensões.
- **Modelo conjunto:** com as 5 interações, dá efeito médio e Wald conjunto.

## 9. Modelo 4: matching pelo escore (eq. 7), compra

- **Desfecho:** média do índice da compra. Variante ponderada pelo nº de itens com índice.
- **Escore:** PS2. **Amostra:** suporte principal.
- **Vizinhos:** M = 4, por |p̂_i − p̂_j|, com reposição. Empates: entram todas as unidades à mesma distância do 4º vizinho,
  com o peso repartido (Abadie e Imbens).
- **Simetria (eq. 7):** cada AF casa com 4 A, e vice-versa. Saem o efeito médio (eq. 7), o efeito nas AF e o efeito nas A.
- **Distância máxima:** sem limite no principal, como no artigo. Na sensibilidade, caliper de 0,2 DP do escore; as
  compras sem par saem e são contadas.

**Variantes:**

| Variante | Regra |
|---|---|
| (a) | Só o escore |
| (b) | Exato no trimestre e no grupo dominante + vizinho no escore |
| (c) | Exato na UASG + vizinho no escore; só UASGs com os dois modos no suporte. As compras sem par na UASG saem e são contadas |

**Inferência:**
1. EP de Abadie e Imbens (2006) do efeito populacional, com σ² estimado por J = 4 vizinhos do mesmo modo. Com empates,
   a fórmula usa os pesos de casamento.
2. Variância condicional (efeito na amostra), de Abadie e Imbens.
3. **Adaptação agrupada por CNPJ**, que não é um estimador consagrado e é relatada como tal:
   - variância condicional Σ_g (Σ_{j∈g} c_j ε̂_j)²;
   - ε̂_j vem do casamento com J = 4 compras do mesmo modo de outros órgãos;
   - a correção J/(J + 1) vale só na diagonal.

**Não usado:** o bootstrap ingênuo, que não é válido para vizinho mais próximo com reposição (Abadie e Imbens, 2008).

**Conferência:** o estimador e os EP 1 e 2 são comparados com o pacote R `Matching` (Sekhon), função `Match`, com
`M = 4`, `ties = TRUE`, `replace = TRUE` e `Var.calc = 4`, na variante (a).

## 10. Equilíbrio

Antes e depois do matching:
- diferenças padronizadas das covariáveis (incluindo as de sensibilidade), com os pesos do matching;
- distribuição dos escores;
- cobertura do suporte;
- tamanho efetivo (Kish);
- UASGs e órgãos;
- parcela sem par;
- concentração dos pesos (máximo e parcela do 1% maior).

Uma diferença padronizada acima de 0,1 em valor absoluto é marcada como desequilíbrio. Equilíbrio observado não é
evidência de validade causal.

## 11. Comparação com estudos anteriores

**Referências:**
- associação do painel de 16/11: −4,5% [−6,9; −2,1], com efeitos fixos CNPJ × produto + produto × mês, 191 mil itens e 656
  CNPJs;
- estudo de eventos: −1,91 lp [−5,67; 1,93], p = 0,32;
- filtrado: −3,76 lp [−6,67; −0,89].

São amostras e parâmetros distintos. **Comparações em amostra comum:**
1. a especificação do painel (log P, efeitos fixos CNPJ × produto + produto × mês) na amostra desta replicação;
2. os itens das 152 UASGs tratadas do estudo de eventos, na janela [m − 6, m + 6), com OLS 3 (comparação dentro das mesmas
   UASGs, sem controles de tendência).

**Decomposição descritiva das diferenças:** amostra, suporte, ponderação, controles e método.

## 12. Robustez

Nenhuma variante é escolhida pelo valor-p.

1. Faixas de suporte: a completa, 0,05, 0,075 e 0,10, para OLS 1–4 e para o matching (a).
2. Pesos por item × por compra (em todos os OLS).
3. Exclusão sucessiva dos 5 órgãos mais influentes, pela função de influência do β no OLS 3 e no OLS 2 (suporte, peso por
   item).
4. EP agrupado por CNPJ × UASG.
5. Escore PS1, PS3 e PS4: novo corte, OLS 2 e 3 e matching (a).
6. Medicamentos × demais materiais: OLS 2 e 3 por grupo, se houver ≥ 200 compras de cada modo e ≥ 30 CNPJs com AF.
7. Qualidade do índice e dispersão:
   - células de baixa dispersão contemporânea (`sd_G` ≤ 0,8033, o p75);
   - outro tratamento de extremos (`e_c3`, com e truncado em ±3 em vez de descartar |e| > ln 10).
8. Regressão mediana, na compra (média do índice), sem controles e com X do PS2:
   - suporte e amostra completa;
   - R `quantreg::rq`;
   - IC por bootstrap de pares por CNPJ (B = 299, semente fixa).
9. Mesma UASG × UASGs diferentes:
   - OLS 3 e 4 e matching (c), dentro;
   - OLS 2 e matching (a), juntando dentro e entre;
   - regressão de Mundlak (AF + média de AF da UASG + X): efeito dentro e associação entre UASGs.
10. Seleção dos homologados:
    - desfechos 3 e 4;
    - OLS 2 e 3 de preço nas compras em que todos os itens com situação final foram homologados.

**Múltiplos testes:** Holm nas famílias "5 dimensões de heterogeneidade" (por amostra) e "5 desfechos secundários" (no
OLS 3, suporte). O β principal não é corrigido.

## 13. Limitações (registradas desde já)

- A escolha do modo não é aleatória.
- Há forte persistência institucional por UASG.
- O matching não elimina confundimento não observado.
- As UASGs que usam os dois modos podem não representar as demais.
- O índice pode conter heterogeneidade técnica dentro do CATMAT.
- O preço homologado só existe quando a contratação dá certo.
- Não há o subconjunto aleatorizado do artigo.
- Os modos híbridos brasileiros não são os leilões do artigo.

A concordância entre OLS, interações e matching não prova identificação causal.

## 14. Saídas

- `tabelas/*.csv` e `graficos/*.svg`: sobreposição, equilíbrio e efeitos com IC.
- `registro_execucao.json` e `relatorio.md`.

Comando único: `python analises/replicacao_athey_levin_seira_20261124/executar.py`.
