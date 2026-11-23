# Pré-registro: testes do desenho causal A × AF (23/11/2026)

Este protocolo executa os testes recomendados no parecer de 23/11
(`analises/parecer_desenho_causal_20261123/parecer.md`). Foi escrito e versionado **antes** de estimar qualquer efeito das
unidades que mudaram de modo. O commit que o contém é o registro; mudanças posteriores entram como desvios (§11).

Antes deste registro, sem ler o desfecho das unidades que mudaram de modo, foram feitos:
- `preparar.py`: a base. Os eventos usam só o modo de disputa das compras.
- `poder.py`: poder calculado só com unidades estáveis, usadas como controles placebo. Das unidades que mudaram, entram
  apenas as contagens de compras.
- Depuração do código com eventos fictícios em unidades estáveis (`executar.py --depurar`) e com rótulos AF embaralhados
  (`item_descritivo.py --depurar`). As saídas ficam em `dados/` (fora do git) e não são resultados. Ela levou a duas
  escolhas registradas aqui:
  - pesos de precisão, que reduzem o EP placebo em 21%;
  - na imputação, célula produto × trimestre, com EP placebo 0,021 contra 0,025 por mês e mais itens imputados.

## 1. Hipótese e estimandos

H1: adotar o Aberto-Fechado (AF) em lugar do Aberto (A) muda o preço unitário homologado dos itens de material comprados
pela unidade (UASG). O modo é uma política da unidade, adotada em regimes (parecer §3.1). O estimando é o efeito da troca
de regime (intenção de tratar).

- **τ_in:** efeito médio nas unidades que passam de A para AF. Compara os 6 meses a partir da troca ([0, 5]) com os 6
  meses anteriores ([−6, −1]), contra controles.
- **τ_out:** o mesmo para as trocas AF → A. Se o efeito é causal e simétrico, τ_out = −τ_in.
- **τ_AF (principal):** média ponderada de s_k·DiD_k, com s_k = +1 nas trocas A → AF e −1 nas AF → A. É o efeito do AF.
- **Wald (secundário):** τ dividido pelo primeiro estágio. Dá o efeito por 100 p.p. de parcela de compras em AF.

## 2. Dados

- `pncp.db`, só leitura, fonte `dados_abertos` (Compras.gov.br): compras de Pregão Eletrônico em Aberto e em
  Aberto-Fechado.
  - O modo, usado para datar os eventos, vem das compras com abertura de 2022-01 a 2026-09.
  - Os desfechos vêm das compras com abertura de 2022-01 a **2026-03**. A partir de 2026-04 a API deixou de trazer o
    CATMAT: em 2026-05 só 6 mil de 167 mil itens o têm. Recuperar esse dado exige nova coleta e fica fora deste estudo.
- Base: 315.386 compras em 5.518 UASGs e 4.448.803 itens de material (registro principal). A UASG é `compras.uasg`.
- Produto = CATMAT + unidade de fornecimento padronizada. A padronização (`SINONIMOS` em `preparar.py`) só unifica
  grafias, como UN/UND/UNIDADE e CX/CAIXA, e reduz 4.239 grafias a 3.311.
- Itens de preço: critério Menor preço, homologados e com P > 0.

## 3. Eventos (definidos só pelo modo de disputa)

- Para cada mês j com compra, dif_j é a parcela de AF em [j, j+5] menos a parcela em [j−6, j−1]. Exigem-se pelo menos 5
  compras de cada lado.
- Candidatos: |dif_j| ≥ 0,5. Aceita-se o de maior |dif| e descartam-se os candidatos a menos de 6 meses dele (supressão
  de não máximos). O evento é datado no ponto de quebra.
- Há 178 eventos A → AF e 135 AF → A. São estritos (≤ 10% antes e ≥ 90% depois, ou o inverso) 25 e 21.
- A janela [m−6, m+5] precisa caber nos desfechos, o que limita os eventos a 2022-07 a 2025-10. A unidade precisa ter
  pelo menos 2 compras com índice em cada meia janela (§5). Com isso ficam **76 eventos A → AF (48 CNPJs) e 76 AF → A
  (43 CNPJs)**.

## 4. Desfecho principal

- **Índice de preço do item:** e = log P − média de log P do mesmo produto, no mesmo trimestre, nas *outras* unidades.
  Exigem-se pelo menos 5 itens de pelo menos 3 outras unidades.
- **Truncagem:** itens com |e| > ln 10 são descartados como provável erro de unidade (fator > 10). Ficam 1.519.972
  itens em 106.051 compras.
- **Agregação:** cada compra recebe a média de e nos seus itens. Cada meia janela recebe a média entre as compras, porque
  o pregão é a unidade de decisão.

## 5. Estimador principal e inferência

- **Δ_u:** média de e nas compras de [m, m+5] menos a média em [m−6, m−1].
- **DiD_k:** Δ_{u_k} menos a média de Δ_j nos controles limpos C_k.
- **Controles limpos C_k:**
  - unidades da mesma esfera;
  - estáveis no modo de partida nas duas meias janelas (AF ≤ 10% nas trocas A → AF; ≥ 90% nas AF → A);
  - com pelo menos 2 compras com índice em cada meia janela;
  - sem evento próprio a menos de 6 meses;
  - pelo menos 5 por evento.

  O desenho é o das diferenças empilhadas com controles limpos. Separa quem entra e quem sai do AF, compara cada troca
  com unidades que, na janela, mantêm o status de partida, à maneira de de Chaisemartin e D'Haultfœuille, e não tem
  pesos negativos.
- **Pesos de precisão:** w_k = 1/(a + b·h_k), com h_k = 1/c_pré + 1/c_pós (compras com índice da unidade tratada),
  a = 0,009415 e b = 0,23849. É o modelo de variância dos placebos em `poder.json` (`W6_cmin2`). O estimando é uma média
  das DiD_k com pesos positivos conhecidos. A média com pesos iguais é a principal sensibilidade.
- **Inferência:**
  - agrupamento por CNPJ do órgão;
  - p do bootstrap selvagem restrito (WCR), com pesos de Webb e B = 9.999;
  - IC95 por inversão do teste;
  - α = 5%, bilateral.

  Ao lado, inferência por aleatorização: placebo no espaço, nas datas reais, sorteando para cada evento um controle limpo
  daquela janela (5.000 sorteios).
- **Poder** (`poder.json`, só placebos):
  - efeito mínimo detectável (80%, 5%) de **6,25 lp (≈ 6,1%)** com pesos de precisão;
  - 7,69 lp com pesos iguais;
  - poder de 54% para um efeito de −4,5% (o do painel), 77% para −6% e 95% para −8%;
  - correlação intraclasse dentro do CNPJ de 0,009.

  Um resultado nulo não demonstra ausência de efeito de 4–5%.
- **Escolha registrada da especificação:**
  - candidatas: janela de 6 ou 12 meses e mínimo de compras (cmin) de 1, 2, 3 ou 5;
  - entre as que ficam a até 0,2 lp do menor efeito mínimo detectável com pesos de precisão (6 meses com cmin 1, 2 ou 3),
    escolhe-se a de mais eventos cujo efeito mínimo com pesos iguais também fica a até 0,2 lp do mínimo;
  - resultado: **janela de 6 meses e cmin = 2**.

## 6. Testes de falsificação e regras de decisão

Todos usam o mesmo estimador e os mesmos pesos.

| Teste | Hipótese nula | Passa se |
|---|---|---|
| F1. Pré-tendência | DiD do trimestre de evento −2 contra o −1, agregado com sinal, = 0 | p ≥ 0,10 |
| F2. Simetria | τ_in + τ_out = 0 (a reversão à média dá o mesmo sinal nos dois sentidos) | p ≥ 0,10 |
| F3. Estimado | índice do estimado eR (log R contra outras unidades), agregado com sinal, = 0 | p ≥ 0,10 |
| F4. Placebo no tempo | evento fictício 12 meses antes, com a unidade estável no modo de partida, = 0 | p ≥ 0,10 |

Outros desfechos placebo são reportados com correção de Holm:
- log do nº de itens por compra;
- parcela SRP;
- exclusividade ME/EPP;
- sigilo;
- índice de quantidade;
- nível de preço de mercado do produto (mix);
- parcela de itens médicos (classe 65xx).

Um p de Holm < 0,05 nesses placebos é alerta de mudança simultânea de composição, mas sozinho não invalida o desenho.

Leitura:
- **(a)** F1–F4 passam e p < 0,05: há efeito causal da troca de regime, estimado em τ_AF.
- **(b)** F1–F4 passam e p ≥ 0,05: não há evidência de efeito. O IC delimita os efeitos compatíveis com os dados.
- **(c)** Algum F falha: o desenho não sustenta leitura causal. As estimativas ficam como descritivas, com o diagnóstico.
- Se a aleatorização discordar do WCR na decisão a 5%, a divergência é reportada e vale o maior p.

## 7. Sensibilidades e estimadores alternativos (pré-especificados, sem regra de decisão)

1. Pesos iguais.
2. cmin = 3.
3. Janela de 12 meses: eventos sem outro evento a menos de 12 meses e com |Δ AF| ≥ 0,5 nas meias janelas de 12 meses.
   Inclui o teste conjunto das pré-tendências −4, −3 e −2.
4. Só eventos estritos.
5. Índice truncado em ±3, sem descarte.
6. Ponderação por item.
7. Controles de todas as esferas.
8. Controles que nunca mudam: "A estável" ou "AF estável" no período todo, ≥ 20 compras, AF < 5% ou > 95%.
9. Antecipação: evento datado pela publicação do primeiro edital no novo modo, com cada compra datada pela publicação.
10. Composição: só produtos que a unidade comprou nas duas meias janelas, com pelo menos 2 compras em cada.
11. Wald: τ dividido pelo primeiro estágio, com bootstrap de pares por CNPJ.
12. **Imputação de Borusyak, Jaravel e Spiess:**
    - modelo log P = α_g + γ_{produto, trimestre}, estimado nos itens não tratados;
    - g é a unidade estável ou a pré-janela do evento;
    - não tratados: compras no modo de partida das unidades estáveis (sem as unidades com evento) e as pré-janelas;
    - tratados: as pós-janelas;
    - imputa-se só com pelo menos 3 itens não tratados na célula;
    - variantes: célula produto × mês e ponderação por item; pré-tendência pelos resíduos (bin −2 contra −1).
13. **Perfil de evento**, no estilo de de Chaisemartin–D'Haultfœuille e de Callaway–Sant'Anna com controles ainda não
    tratados:
    - DID_ℓ por trimestre de evento, com base no trimestre −1;
    - θ = média dos trimestres 0 e 1;
    - sensibilidade a violações das tendências paralelas por **magnitudes relativas**, no espírito de Rambachan e Roth
      (2023), em versão simplificada: viés ≤ 1,5·M̄·m, com m = |DID_{−2}| pontual ou m + 1,96 EP;
    - reporta-se o M̄ de quebra.
14. **PanelMatch** (Imai, Kim e Wang, 2023):
    - conjunto pareado = controles limpos;
    - refinamento pelos 5 vizinhos mais próximos (distância euclidiana padronizada) no índice do estimado, porte, parcela
      médica, nível de mercado, competição esperada e nº de itens, todos na pré-janela;
    - mesma região, se houver pelo menos 5;
    - duas versões: sem as defasagens do desfecho e com elas (trimestres −2 e −1).
15. **DiD sintético** (Arkhangelsky et al., 2021):
    - por evento, em trimestres de evento;
    - unidades com compra em todos os trimestres da janela, tratada e doadores (controles limpos);
    - janelas de 6 e de 12 meses.

## 8. Desfechos secundários, limites de Lee e heterogeneidade

- **Secundários**, com Holm dentro da família:
  - sucesso: parcela homologada entre os itens com situação final;
  - fracassado;
  - deserto;
  - prazo: log(1 + dias da abertura ao resultado);
  - desconto 1 − P/R, nos itens não sigilosos;
  - fornecedor novo: vencedor sem vitória na unidade nos 12 meses anteriores.

  O nº de propostas não existe para o Aberto sem os PDFs (§10).
- **Limites de Lee (2009):**
  - se a troca muda a taxa de sucesso em Δs (o DiD de "sucesso"), apara-se a fração |Δs|/s do lado com mais sucesso;
  - o lado é a pós-janela da tratada se Δs > 0; senão, a pré-janela;
  - corta-se no topo e na base da distribuição de e, e recalcula-se o DiD.
- **Heterogeneidade (exploratória):**
  - competição esperada: log(1 + nº de fornecedores distintos que venceram o mesmo CATMAT na mesma UF nos 4 trimestres
    anteriores, em outras unidades), medida na pré-janela da tratada e cortada na mediana dos eventos;
  - esfera federal contra não federal.

## 9. Matching de itens (só descritivo; parecer §4.3)

- **Amostra:** itens com índice e abertura de 2023-01 a 2026-03, para haver 12 meses de histórico da unidade. Todas as
  UASGs do Compras.gov.br. Tratamento: compra em AF. O índice já compara o mesmo produto no mesmo trimestre.
- **Covariáveis:**
  - do item: índice de quantidade, SRP, exclusividade ME/EPP, sigilo, competição esperada, nível de mercado do produto,
    parcela médica, mês do ano e ano;
  - do comprador, medidas nos 12 meses anteriores: porte (log de compras), índice do estimado da unidade, esfera e região;
  - variante B: inclui também o índice de preço passado da unidade. Pode absorver parte de um efeito persistente
    (controle excessivo).
- **Estimadores:**
  - MQO;
  - AIPW-ATT, com logit e aparamento por sobreposição em [0,1; 0,9];
  - balanceamento por entropia (médias), na mesma região de sobreposição.
- **Inferência:** EP por CNPJ e bootstrap selvagem de escores (Webb).
- **Teste de balanço:** os mesmos estimadores aplicados a eR.
- **Γ de Rosenbaum:** pares no mesmo produto e trimestre, de UASGs diferentes, pelo vizinho mais próximo no logit do
  escore (calibre de 0,2 dp), teste de postos sinalizados.
- **Cinelli e Hazlett (2020):**
  - RV_{q=1} e RV_{q=1, α=0,05};
  - limites com confundidores 1, 2 e 3 vezes tão fortes quanto o porte, o estimado passado e a competição esperada.
- **Também se reportam:** limites de Lee da diferença bruta e a fração dos AF com suporte.
- **Leitura:** descritiva. Nenhum resultado desta seção decide H1.

## 10. O que não se executa agora, e por quê

- **Desenho intraleilão** (parecer §4.2):
  - exige os PDFs do Aberto, e só há 6 compras do Aberto com PDF (`dados/filtrados/pregao_aberto/`);
  - o download é manual, porque o hCaptcha não é contornado, e o parser ainda não lê o relatório do Aberto nem as
    propostas iniciais;
  - `lista_aberto.py` gera a lista de download: compras do Aberto das unidades que mudaram de modo e uma amostra de
    controles estáveis.
- **Variáveis instrumentais e experimentos naturais** (parecer §4.4):
  - não há ato normativo datado;
  - a identidade do agente que adjudica só está nos PDFs, que faltam no Aberto.

## 11. Desvios

Qualquer mudança feita depois de ver resultados entra no relatório como **exploratória**, com data e motivo.

## 12. Reprodução (da pasta `PNCP-Automation`)

```
python analises/testes_desenho_causal_20261123/preparar.py --pncp-db ../dados/pncp.db   # ~10 min, cache em dados/
python analises/testes_desenho_causal_20261123/poder.py
python analises/testes_desenho_causal_20261123/executar.py                               # ~5 min
python analises/testes_desenho_causal_20261123/item_descritivo.py
python analises/testes_desenho_causal_20261123/lista_aberto.py --pncp-db ../dados/pncp.db
```

Especificação lida pelos scripts: `especificacao.json` (W = 6, cmin = 2, pesos de precisão, imputação por
produto × trimestre, B = 9.999).
