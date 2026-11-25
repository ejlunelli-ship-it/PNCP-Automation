# Sensibilidade HonestDiD do estudo de eventos A × AF (24/11/2026). Exploratório

Este estudo aplica o método de Rambachan e Roth (2023), com o pacote oficial `HonestDiD` em R. A pergunta é que violações
das tendências paralelas são compatíveis com os dados e quanto elas alargam o intervalo do efeito do AF sobre o preço
homologado.

- `protocolo.md`: definições, grades e parâmetros, escritos antes de estimar.
- `relatorio.md`: resultados e interpretação.

## Reprodução (da pasta `PNCP-Automation`)

```
python analises/honestdid_sensibilidade_20261124/executar.py
```

O comando único leva cerca de 35 minutos.
1. `coeficientes.py`:
   - reproduz o M0 (−1,91 lp) e o perfil por trimestre de 23/11;
   - monta os vetores dinâmicos e as matrizes de covariância conjuntas por órgão (CR1, jackknife e bootstrap);
   - grava `entradas/`.
2. `executar.R`, pelo `Rscript`, com 3 núcleos: o HonestDiD.
3. Conferências, tabelas-resumo, gráficos e `registro_execucao.json`.

**Pré-requisitos:**
- a base de 23/11 em `dados/testes_desenho_causal/` (`../testes_desenho_causal_20261123/preparar.py`);
- R ≥ 4.2 com o pacote `HonestDiD`: `install.packages("HonestDiD")`. Este estudo usou o R 4.6.2 e o `HonestDiD` 0.2.8.

**Garantias:**
- o `pncp.db` não é lido;
- os 56 eventos reservados para validação não entram;
- nada anterior é alterado.

**Variáveis opcionais:**
- `HONESTDID_RSCRIPT`: caminho do `Rscript`;
- `HONESTDID_NUCLEOS`: núcleos do R; o padrão é 3;
- `HONESTDID_SO_PRINCIPAL=1`: no R, só a especificação principal, como teste rápido.

**No RStudio:** abra a pasta `PNCP-Automation` como diretório de trabalho e rode
`source("analises/honestdid_sensibilidade_20261124/executar.R")`. Ele lê as entradas já gravadas pelo Python.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `coeficientes.py` | Reprodução, coeficientes por trimestre, matrizes, pré-tendência e poder, influência por órgão, conjunto identificado por programação linear |
| `executar.R` | HonestDiD: `constructOriginalCS`; Δ^RM (C-LF) e Δ^SD (FLCI); Δ^SDRM com ≥ 2 pré-períodos; conjunto identificado (funções internas do pacote); pontos de quebra |
| `executar.py` | Comando único, conferências, tabelas-resumo e registro |
| `graficos_honestdid.py` | Gráficos SVG |
| `entradas/` | β (lp), V (lp²) e manifesto (especificação, parâmetro, l, pré/pós, grade) |
| `tabelas/reproducao.csv` | M0, M1, janela de 12 e perfil de 23/11 reproduzidos |
| `tabelas/coeficientes_dinamicos.csv` | Coeficientes por trimestre, EP, IC, p WCR, eventos, órgãos, UASGs, compras e itens |
| `tabelas/covariancias.csv`, `verificacao_covariancia.csv` | Matrizes CR1, jackknife e bootstrap, com autovalores, condição e correlações |
| `tabelas/pre_tendencia_e_poder.csv` | Wald dos pré-coeficientes e poder contra tendências lineares (Roth, 2022) |
| `tabelas/diferenca_estimando.csv` | Perfil dinâmico × estimando do M0 |
| `tabelas/honestdid_resultados.csv`, `honestdid_resumo.csv` | IC robusto por especificação, parâmetro, restrição e valor; faixas compatíveis; conjunto identificado |
| `tabelas/honestdid_quebras.csv` | Pontos de quebra, só onde o IC no menor valor exclui zero |
| `tabelas/honestdid_influencia_orgaos.csv`, `influencia_orgaos_coeficientes.csv` | Retirando um órgão por vez |
| `tabelas/eventos_trimestres_*.csv` | Valores por evento e trimestre |
| `tabelas/*_refeitos.csv` | Reexecução das linhas F1\|a e P1_BOOT\|b, valor a valor, depois de uma falha numérica do FLCI do pacote. Já mescladas em `honestdid_resultados.csv` e documentadas no registro; uma rodada completa apaga esses arquivos |
| `graficos/*.svg` | Perfil, sensibilidade Δ^RM e Δ^SD, direções, sensibilidades e influência |
