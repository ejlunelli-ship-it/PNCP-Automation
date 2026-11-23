# Testes do desenho causal A × AF: resultados (23/11/2026)

Execução dos testes recomendados no parecer de 23/11 (`analises/parecer_desenho_causal_20261123/parecer.md`), conforme o
pré-registro `protocolo.md`. O protocolo foi commitado e enviado em `ff8b2d2` **antes** de qualquer estimativa com as
unidades que mudaram de modo. Números em `resultados.json`, `resultados_item.json`, `eventos_did.csv`, `poder.json` e
`exploratorio.json`. O `pncp.db` foi aberto só para leitura; tamanho e mtime continuam iguais.

Convenções:
- lp = diferença em log × 100; % = 100·[exp(lp/100) − 1].
- Sinal negativo = o AF reduz o preço.
- "Efeito do AF" agrega as trocas A → AF com as AF → A de sinal invertido.

## Resumo

1. **O desenho principal passou em todos os testes de falsificação:** pré-tendência, simetria, preço estimado e placebo
   no tempo. É, até aqui, o desenho mais crível do projeto.
2. **O efeito estimado do AF no preço é pequeno e não significativo:** −1,9 lp, IC95 [−5,7; +1,9], p = 0,32, nos 152
   episódios de mudança de regime (76 A → AF e 76 AF → A). Isso equivale a −1,9%, com IC de −5,5% a +1,9%.
   - Reduções acima de ≈ 5,5% e aumentos acima de ≈ 2% ficam improváveis.
   - O IC contém o zero e também a associação de −4,5% do painel. O poder para detectar −4,5% era de 54%.
3. **Os estimadores alternativos dão o mesmo sinal,** entre 0 e −4,5 lp. Só a imputação de Borusyak–Jaravel–Spiess
   rejeita a 5% (−3,6 lp, p = 0,04), e só com a célula produto × trimestre; com produto × mês dá −0,6 lp. Nenhuma
   sensibilidade tem regra de decisão.
4. **Sucesso, prazo e fornecedores:** nenhum efeito significativo depois da correção de Holm. Há indícios fracos de mais
   itens homologados (+1,9 p.p.) e de menos itens desertos (−0,9 p.p.).
5. **Matching de itens (descritivo):** reproduz a associação entre unidades, −4,5 lp por AIPW e entropia, mas é frágil a
   confundimento não observado. O Γ de Rosenbaum é 1,25 e o valor de robustez é de 3,2%. Como a unidade explica
   82–84% da escolha do modo, um confundidor desse tamanho é plausível.
6. **Leitura.** Dentro da mesma unidade, a troca de modo não muda o preço de forma detectável. A diferença de ≈ 4,5%
   entre unidades AF e A é compatível com um efeito pequeno, de até uns 5%, e também com seleção das unidades. Para
   separar as duas é preciso mais precisão; o caminho é o desenho intraleilão com os PDFs do Aberto (§9).

## 1. O que foi executado

| Recomendação do parecer | Execução | Onde |
|---|---|---|
| Pré-registro (§5.1) | `protocolo.md`, commit `ff8b2d2` antes das estimativas | protocolo |
| Base unidade × mês, CATMAT e unidade de fornecimento (§5.2) | Base de 2022-01 a 2026-03, unidade padronizada; lacuna de CATMAT a partir de 2026-04 documentada | §2 |
| Competição esperada (§5.3) | Vencedores distintos do CATMAT na UF nos 4 trimestres anteriores, em outras unidades | §6, §8 |
| Estudo de eventos com estimadores robustos (§4.1) | DiD empilhado com controles limpos (principal); perfil DID_ℓ; imputação BJS; controles nunca/ainda não tratados | §3–§5 |
| Pré-tendência, Rambachan–Roth, simetria, placebos, composição, antecipação (§4.1) | Todos | §4, §5 |
| Bootstrap selvagem por CNPJ e aleatorização (§4.1) | WCR com pesos de Webb, B = 9.999; placebo no espaço | §3 |
| Matching de unidades + DiD; DiD sintético (§4.3) | PanelMatch, com e sem defasagens; SDID | §5 |
| Matching de itens descritivo: AIPW, entropia, Rosenbaum, Cinelli–Hazlett, balanço em log R, suporte (§4.3) | Todos | §8 |
| Limites de Lee (§3.7) | No estudo de eventos e no descritivo | §6, §8 |
| Desenho intraleilão com PDFs do Aberto (§4.2) | **Não executável**: só 6 compras do Aberto têm PDF; download manual (hCaptcha) e parser pendentes. Lista gerada | §9 |
| VI e experimentos naturais (§4.4) | **Não executável**: sem ato normativo datado; agente só nos PDFs | §9 |

## 2. Base e eventos

- **Compras.gov.br, Pregão Eletrônico, A e AF:**
  - 315.386 compras em 5.518 UASGs;
  - 4,45 milhões de itens de material;
  - 1,52 milhão de itens com índice de preço em 106 mil compras.
- **Índice:** e = log P menos a média de log P do mesmo CATMAT + unidade, no mesmo trimestre, em outras unidades.
- **Período:** desfechos até 2026-03. A partir de 2026-04 a API deixou de trazer o CATMAT; recuperá-lo exige nova coleta.
- **Eventos de mudança de regime:** 178 A → AF e 135 AF → A, datados só pelo modo. Na especificação principal entram
  152:

| | A → AF | AF → A |
|---|---:|---:|
| Eventos / CNPJs | 76 / 48 | 76 / 43 |
| Parcela de AF antes → depois | 11% → 81% | 84% → 12% |
| Compras com índice (mediana pré / pós) | 5 / 6 | 6 / 7 |
| Controles limpos por evento (mediana) | 213 | 158 |
| Ano do evento (2023 / 2024 / 2025) | 6 / 44 / 26 | 6 / 29 / 41 |

**Concentração.** Os 152 eventos vêm de 70 CNPJs, com cerca de 25 CNPJs efetivos (1/HHI). O maior CNPJ tem 10% do peso,
contra cerca de 4 órgãos efetivos no matching de 17/11.

## 3. Resultado principal

Estimador:
- DiD_k = (média de e nos 6 meses após a troca − média nos 6 meses antes) na unidade, menos a mesma diferença nos
  controles limpos da mesma esfera;
- pesos de precisão;
- inferência por CNPJ.

| Estimativa | lp | IC95 (WCR) | p (WCR) | p (aleatorização) |
|---|---:|---|---:|---:|
| **Efeito do AF (agregado)** | **−1,91** | [−5,67; +1,93] | 0,32 | 0,58 |
| A → AF | −0,71 | [−6,05; +4,70] | 0,80 | 0,88 |
| AF → A | +2,95 | [−3,18; +9,07] | 0,34 | 0,54 |
| Pesos iguais: efeito do AF | −3,10 | [−8,32; +2,26] | 0,25 | |
| Wald: efeito por 100 p.p. de AF | −4,37 | [−12,3; +3,5] (bootstrap de pares) | | |

- **Leitura (b) do protocolo:** os testes passam e p ≥ 0,05, logo não há evidência de efeito.
- **Sinais.** A troca A → AF baixa o preço e a AF → A o sobe, ambas pouco, o que é coerente com um efeito pequeno do AF.
- **Primeiro estágio:** 71,6 p.p. de variação na parcela de compras em AF.
- **Exploratório** (feito depois de ver os resultados): sem cada um dos 5 CNPJs de maior peso, o efeito fica entre −1,4 e
  −2,3 lp.

## 4. Testes de falsificação

| Teste | Estimativa | p (WCR) | Passa (p ≥ 0,10)? |
|---|---:|---:|---|
| F1. Pré-tendência: trimestre −2 contra −1 | +0,52 lp | 0,89 | sim |
| F2. Simetria: τ(A → AF) + τ(AF → A) = 0 | +2,24 lp | 0,62 | sim |
| F3. Índice do estimado (log R contra outras unidades) | +1,01 lp | 0,55 | sim |
| F4. Placebo no tempo: evento fictício 12 meses antes (40 eventos) | −2,21 lp | 0,46 | sim |

Desfechos placebo, com p de Holm entre os 8:

| Desfecho | Efeito do AF | p | p Holm |
|---|---:|---:|---:|
| Parcela SRP | −2,75 p.p. | 0,035 | 0,28 |
| Exclusividade ME/EPP | −1,25 p.p. | 0,56 | 1 |
| Sigilo | +1,23 p.p. | 0,51 | 1 |
| Índice de quantidade | +3,6 lp | 0,57 | 1 |
| Nível de mercado do produto (mix) | −6,0 lp | 0,61 | 1 |
| Parcela de itens médicos | +0,15 p.p. | 0,92 | 1 |
| log do nº de itens por compra | −0,8 lp | 0,89 | 1 |

Só a parcela SRP passa do limiar nominal, sem resistir a Holm. Pela regra do protocolo, não há alerta.

**O que esses testes mostram.** Não há sinal de pré-tendência nem de reversão à média: a simetria passa. O preço
estimado não muda na troca, então não há sinal de mudança simultânea de equipe ou de pesquisa de preços. A composição das
compras também não muda de forma detectável. Nenhum teste desmente o desenho; o limite é a precisão.

## 5. Perfil de evento e estimadores alternativos

**Perfil por trimestre de evento** (base: trimestre −1), no estilo de de Chaisemartin–D'Haultfœuille e de
Callaway–Sant'Anna com controles ainda não tratados:

| Trimestre | −2 | 0 | +1 | Média 0 e +1 |
|---|---:|---:|---:|---:|
| Efeito do AF (lp) | +0,5 | −3,1 | −3,1 | −3,2 [−8,8; +2,4] |
| p (WCR) | 0,89 | 0,33 | 0,28 | 0,26 |

**Rambachan–Roth, versão simplificada.** O IC já contém o zero sem violação nenhuma (M̄ = 0), então não há conclusão a
proteger.

**Janela de 12 meses:** 78 eventos, −2,0 lp (p = 0,48), com trimestres pós de −4,7 a −7,7 lp, todos não significativos.
O teste conjunto das pré-tendências −4, −3 e −2 não é computável: só 9 eventos têm os três trimestres. O placebo no tempo
(F4) cumpre esse papel.

| Estimador ou sensibilidade | Eventos | lp | IC95 | p |
|---|---:|---:|---|---:|
| Principal | 152 | −1,91 | [−5,67; +1,93] | 0,32 |
| cmin = 3 | 117 | −1,02 | [−5,13; +3,35] | 0,63 |
| Janela de 12 meses | 78 | −1,97 | [−7,98; +3,55] | 0,48 |
| Só estritos (≤ 10% → ≥ 90%) | 23 | +1,78 | [−4,80; +8,85] | 0,60 |
| Índice truncado em ±3 | 158 | −2,52 | [−9,64; +5,48] | 0,51 |
| Ponderado por item | 182 | −4,00 | [−7,86; +0,93] | 0,10 |
| Controles de todas as esferas | 152 | −2,19 | [−6,12; +1,73] | 0,26 |
| Controles que nunca mudam | 151 | −1,90 | [−5,68; +2,01] | 0,34 |
| Antecipação (datado pela publicação) | 153 | −2,13 | [−5,67; +1,60] | 0,25 |
| Composição (mesmos produtos antes e depois) | 45 | −4,48 | [−12,62; +2,18] | 0,20 |
| Imputação BJS, produto × trimestre | 151 | **−3,56** | [−6,95; −0,15] | **0,04** |
| Imputação BJS, produto × mês | 144 | −0,62 | [−4,94; +3,99] | 0,78 |
| PanelMatch sem defasagens do desfecho | 152 | −0,01 | [−4,33; +4,13] | 0,99 |
| PanelMatch com defasagens | 152 | −0,87 | [−4,71; +3,04] | 0,65 |
| DiD sintético, 6 meses (unidades completas) | 84 | −3,48 | [−9,05; +2,12] | 0,21 |
| DiD sintético, 12 meses | 6 | −5,61 | [−19,5; +4,45] | 0,17 |

**Imputação BJS.** A pré-tendência pelos resíduos é −0,5 lp (p = 0,82). A célula produto × trimestre imputa 20.828 itens
tratados; a por mês, 10.079. A divergência entre as duas (−3,6 contra −0,6) mostra que o resultado depende de como se
estima o contrafactual. Uma rejeição isolada entre 16 variantes, sem regra de decisão, não muda a leitura.

## 6. Desfechos secundários e limites de Lee

| Desfecho | Efeito do AF | IC95 | p | p Holm |
|---|---:|---|---:|---:|
| Sucesso (homologado entre itens com situação final) | +1,92 p.p. | [−0,24; +4,10] | 0,08 | 0,32 |
| Fracassado | −1,04 p.p. | [−3,20; +1,21] | 0,37 | 0,45 |
| Deserto | −0,87 p.p. | [−1,68; −0,07] | 0,03 | 0,21 |
| Prazo até o resultado | +3,3% | [−1,2; +8,0] | 0,15 | 0,45 |
| Desconto 1 − P/R (não sigiloso) | +1,40 p.p. | [+0,02; +2,66] | 0,05 | 0,24 |
| Vencedor novo na unidade (12 meses) | +2,02 p.p. | [−1,13; +5,10] | 0,20 | 0,45 |

- **Nenhum efeito significativo depois de Holm.** O desconto maior (+1,4 p.p.) vem em parte do estimado mais alto (F3:
  +1,0 lp, não significativo), como já se via no parecer (§3.3).
- **Limites de Lee:**
  - na troca A → AF, a taxa de sucesso sobe 3,0 p.p., e apara-se 3,5% dos itens da pós-janela;
  - limites para o efeito do AF: **[−11,1; +3,7] lp**, com pesos iguais;
  - são largos porque o índice tem caudas pesadas. Mesmo assim, a seleção por sucesso não cria um efeito que não
    existe.

## 7. Heterogeneidade (exploratória)

| Grupo | Eventos | Efeito do AF | p |
|---|---:|---:|---:|
| Competição esperada baixa (≤ mediana) | 76 | −4,98 lp | 0,13 |
| Competição esperada alta | 76 | +0,37 lp | 0,89 |
| Diferença alta − baixa | | +5,35 lp | 0,20 |
| Federal | 72 | −0,67 lp | 0,83 |
| Não federal | 80 | −2,69 lp | 0,29 |

O sinal é o que prevê o argumento do leilão anglo-holandês: o lance fechado ajuda mais quando há pouca competição
(Klemperer, 2002). Mas a diferença não é significativa. É uma hipótese a confirmar, não um resultado.

## 8. Matching de itens (só descritivo)

**Amostra.** 1.519.972 itens, dos quais 542.174 AF, em 2.403 CNPJs e 4.359 UASGs, de 2023-01 a 2026-03. Mesmo produto e
trimestre, pelo índice.

**Covariáveis:**
- do item: quantidade, SRP, ME/EPP, sigilo, competição esperada, mix, mês e ano;
- do comprador, nos 12 meses anteriores: porte, índice do estimado, esfera e região.

| Estimador | AF − A (lp) | IC95 | Balanço: índice do estimado |
|---|---:|---|---:|
| Diferença bruta | −4,65 | ± 3,8 | |
| MQO | −4,34 | [−6,4; −2,3] | +1,16 (p = 0,17) |
| MQO + índice de preço passado da unidade | −3,88 | [−5,9; −1,8] | +0,76 (p = 0,37) |
| AIPW (aparamento 0,1–0,9) | −4,52 | [−6,52; −2,51] (selvagem) | +1,23 (p = 0,12) |
| Balanceamento por entropia | −4,54 | [−6,95; −2,14] | |

**Suporte.** 99,99% dos itens AF ficam em [0,1; 0,9]. As covariáveis observadas quase não preveem o modo, que é decidido
pela unidade.

**Sensibilidade a confundimento não observado:**
- **Γ de Rosenbaum:** 322.171 pares (59% dos AF) no mesmo produto e trimestre, de UASGs diferentes. Diferença média
  −5,2 lp e mediana −3,8 lp; o AF é mais barato em 54% dos pares. **Γ crítico = 1,25**: um confundidor que mude em 25%
  a chance de AF dentro do par anula o resultado. Os pares não são independentes, porque o mesmo comprador aparece
  várias vezes, o que torna o Γ otimista.
- **Cinelli e Hazlett:**
  - R² parcial do AF de 0,11%;
  - **RV(q = 1) = 3,2%** e RV(q = 1, α = 5%) = 3,1%: basta um confundidor que explique 3,2% da variação residual do modo
    e do preço;
  - referências: um confundidor 3 vezes tão forte quanto o porte deixaria −3,7 lp. As covariáveis observadas são fracas,
    e o confundidor relevante, a unidade, é muito mais forte.
- **Limites de Lee:**
  - a taxa de homologação é 83,5% no AF e 85,5% no A, e apara-se 2,4% do Aberto;
  - limites de [−9,1; −0,0] lp.

**Leitura.** Entre unidades diferentes, o AF está associado a preços cerca de 4,4% menores, e isso resiste às covariáveis
observadas. O balanço do estimado é aceitável: +1,2 lp, contra +14% no matching por CNPJ. Mas o resultado não resiste a
um confundidor modesto, e o estudo de eventos dentro da unidade não o confirma com a precisão disponível.

## 9. Não executados e próximos passos

- **Desenho intraleilão** (parecer §4.2). Normaliza o preço pela melhor proposta inicial; é a forma mais eficaz de
  reduzir o ruído. Requisitos:
  - baixar os PDFs do Aberto (o usuário clica; o hCaptcha não é contornado);
  - criar o `--modo aberto` no download;
  - estender o parser.

  A lista está em `lista_aberto/`, no formato de `registro/compras/`:

  | Prioridade | Critério | Compras do Aberto | Unidades |
  |---|---|---:|---:|
  | 1 | unidades que mudaram de modo, ±6 meses do evento | 3.466 | 133 |
  | 2 | as mesmas, de 7 a 12 meses do evento | 2.371 | 113 |
  | 3 | controles estáveis no Aberto (2 por evento A → AF), ±6 meses | 6.195 | 141 |

- **CATMAT de 2026-04 em diante.** Uma nova coleta, se a API voltar a trazer o campo, acrescenta eventos de 2025-11 a
  2026-03 e janelas de 12 meses.
- **VI ou experimentos naturais** (§4.4). Só com fonte documental de normas datadas.
- **Hipóteses para um próximo pré-registro:** heterogeneidade por competição esperada (§7) e efeito sobre sucesso e
  deserção.

## 10. Desvios e notas

- **Exploratório.** `exploratorio.py` (concentração e retirada dos 5 CNPJs de maior peso) foi feito depois de ver os
  resultados.
- **Não computáveis com os dados:** o teste conjunto de pré-tendência na janela de 12 meses (só 9 eventos completos) e o
  DiD sintético de 12 meses (6 eventos), que não deve ser interpretado.
- **Rambachan–Roth.** Versão simplificada: limite por magnitudes relativas com m pontual ou conservador, sem o IC
  condicional do método original.
- **Escores dos estimadores de item.** O bootstrap selvagem usa o EP fixo, uma aproximação.
- **Depuração.** Rodou com eventos fictícios e rótulos embaralhados (fora do git). Levou às escolhas registradas no
  protocolo antes dos resultados: pesos de precisão e célula por trimestre na imputação.

## Reprodução (da pasta `PNCP-Automation`)

| Script | O que faz | Tempo |
|---|---|---|
| `preparar.py --pncp-db ../dados/pncp.db` | Base, índices, eventos (cache em `dados/testes_desenho_causal/`) | ~10 min |
| `poder.py` | Poder com placebos (pré-registro) | ~1 min |
| `executar.py` | Estudo de eventos: todos os testes do §3 ao §7 | ~3 min |
| `item_descritivo.py` | Matching de itens descritivo (§8) | ~1 min |
| `lista_aberto.py --pncp-db ../dados/pncp.db` | Lista do Aberto (§9) | ~1 min |
| `exploratorio.py` | Verificações exploratórias | segundos |

## Referências

Arkhangelsky et al. (2021); Borusyak, Jaravel e Spiess (2024); Callaway e Sant'Anna (2021); Cengiz, Dube, Lindner e
Zipperer (2019), DiD empilhado; Cinelli e Hazlett (2020); de Chaisemartin e D'Haultfœuille (2020, 2024); Hainmueller
(2012), entropia; Imai, Kim e Wang (2023); Klemperer (2002); Lee (2009); MacKinnon e Webb (2017); Rambachan e Roth (2023);
Rosenbaum (2002). Detalhes no parecer.
