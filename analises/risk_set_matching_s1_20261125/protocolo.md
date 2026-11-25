# Protocolo — risk-set matching + DiD na cesta S1

**Registro vinculante:** `resultados/protocolo_congelado.json` (congelado em 25/11/2026 17:48:37, ao fim da Fase I).
Ele guarda o SHA-256 de `config.json`, de todo o código, de `resultados/fontes.json` e do conteúdo dos pares
(`resultados/pares_congelados.parquet`), além do diagnóstico de suporte. Este texto descreve o protocolo e foi redigido
depois do congelamento. Não acrescenta regra nem altera nenhuma.

## Histórico da execução

- **17:43–17:44:** fontes, painel e eventos.
- **17:45:30:** primeira execução da Fase I. Já declarava *suporte insuficiente*, com 4 eventos.
- **17:48:37:** Fase I reexecutada só para incluir uma tabela de viabilidade (contagens, sem estimação) e corrigir uma expressão
  de exportação. Os pares são determinísticos e não mudaram; `testes/test_risk_set.py::test_40` os reproduz a partir
  do painel.
- **17:48:38:** primeira execução da Fase II. Nenhum desfecho com t ≥ t0 foi acessado antes disso. O acesso é feito por
  `estimar_did.abrir_pos`, que confere os pares e o `config.json` contra o protocolo.
- **Depois do congelamento:** só mudou código da Fase II e do relatório (`fase2.py`, `gerar_relatorio.py`,
  `executar_testes.py`, `executar.py`) e dos testes. `tabelas/integridade_codigo_fase_I.csv` confirma que o código
  da Fase I continua idêntico ao congelado.

## Fase I — desenho (sem desfechos pós-tratamento)

1. **Regime:** por UASG × trimestre de abertura, com todas as compras A/AF do Pregão Eletrônico (dados abertos).
   - A ou AF só se todas as compras do trimestre estiverem no mesmo modo.
   - Trimestre com os dois modos é *misto* e não é classificado.
   - Trimestre sem compras é *não observado*.
2. **Evento (u, t0):** regime inequívoco o em t0−1 e d ≠ o em t0.
   - A persistência em t0+1 é só classificada; não entra na elegibilidade.
3. **Janela de calendário:** t0−6 ≥ 2023T2 (primeiro trimestre com preços) e t0 ≤ 2026T1.
   - 2026T2 fica de fora: só tem CATMAT até 17/04/2026 (censura da fonte).
   - 2026T3–T4 têm compras e servem apenas ao regime.
4. **Histórico suficiente** (mesma regra para tratadas e controles):
   - nenhum trimestre misto ou no destino entre t0−6 e t0−2;
   - índice observado em t0−1 e t0−2;
   - índice em pelo menos 2 dos 4 trimestres de formação (t0−6..t0−3).
5. **Conjunto de risco:** UASGs observadas e inequívocas na origem em t0 e em t0−1, com histórico compatível e
   completas, da mesma esfera e de outro CNPJ.
6. **Propensity score de mudança**, por direção:
   - logit L2 (λ = 1) com covariáveis M0 padronizadas e dummies de t0;
   - suporte comum: o logit da tratada deve estar entre o mínimo e o máximo das suas candidatas.
7. **Pareamento:** até 5 controles, com reposição entre eventos e desempate pelo código da UASG.
   - M0: Mahalanobis regularizada (Σ + 0,01 I) com caliper d²/2 ≤ χ²₀,₉₅(k) e razão de escala de itens entre 1/3 e 3.
   - M1: M0 mais nível, tendência, dispersão e disponibilidade do índice em t0−6..t0−3.
   - PS: vizinho mais próximo no logit, com caliper de 0,2 dp.
   - PSM: M0 dentro do caliper do PS.
   - Variações de M0 com k = 1 e k = 3.
   - Janela curta: formação em t0−4..t0−3, com ≥ 1 trimestre com preço.
   - Desenho S1+S2.
8. **Balanceamento do evento:** a média de |diferença padronizada| nas covariáveis contínuas M0 deve ser ≤ 0,5. A
   referência agregada é |SMD| < 0,10.
9. **Placebos reservados:**
   - principal: t0−2 → t0−1;
   - data fictícia: t0−4 → t0−3 (em M1 é mecânico);
   - características institucionais;
   - regressão à média.
10. **Suporte mínimo:** 30 eventos e 10 CNPJs tratados efetivos no desenho principal. Abaixo disso, as estimativas
    da Fase II são **descritivas**.

## Fase II — estimação

- **Principal (R1):** M0, h = 0, índice C1 (item → compra → UASG-trimestre, com pesos iguais), referência A1 da S1 e
  peso igual por evento.
- **Robustez:** R1–R17 e X1–X4, listadas em `scripts/robustez.py`.
- **Inferência:** condicional aos pares.
  - CR1 por CNPJ, somando as participações como tratada e como controle, com t(G−1).
  - Bootstrap selvagem por CNPJ (Webb, 9.999 réplicas, nulidade imposta).
  - Holm na família {agregado, adoção, abandono}.
  - TOST com margem de ±5 lp.
  - Jackknife por CNPJ e por UASG (diagnóstico).
- **Censura:** um controle que sai da origem em t0+1 deixa só aquele horizonte. A sensibilidade com IPW (X4) é
  predefinida.

**Proibições cumpridas:**
- não usar preços de t ≥ t0 (nem a sua disponibilidade) no desenho;
- não usar t0−2 e t0−1 no pareamento;
- não relaxar calipers, margens ou regras de completude depois de observar os resultados;
- não fazer commit.
