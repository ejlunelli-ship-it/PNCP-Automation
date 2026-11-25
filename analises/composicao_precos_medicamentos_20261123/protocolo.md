# Protocolo: composição dos produtos e efeito do AF no preço homologado (23/11/2026). Exploratório

Escrito antes de executar. Todos os testes são **exploratórios**. Nenhuma especificação é escolhida pelo valor-p, e a falta
de significância não é lida como falta de efeito.

**Objetivo.** Saber se as diferenças de preço associadas à troca de modo vêm de mudanças no preço de produtos comparáveis
ou de mudanças na composição das compras.

**Motivação.** Na investigação anterior, a parcela de medicamentos caiu na adoção do AF (−4,3 p.p.) e subiu no abandono
(+2,2), no trimestre da troca (`../investigacao_bjs_dispersao_composicao_20261123/relatorio.md` §3).

## Regras gerais

- **Base e motor:** a base de 23/11 e o motor item a item de `../robustez_dispersao_20261123/motor_robustez.py`, só
  importado. O motor reproduz M0 (−1,91 lp) e M1 (−3,76 lp). O `pncp.db` não é lido, e nenhuma base ou resultado anterior
  é alterado. Os gráficos reaproveitam as funções de `../robustez_dispersao_20261123/graficos.py`.
- **Eventos:** janela de 6 meses, com eventos até 2025-10. Os 56 eventos posteriores, reservados para a validação
  confirmatória, não entram; o script confere e registra isso. Não se executa teste confirmatório.
- **Duas especificações,** cada uma com eventos, controles e janelas do seu modelo base:
  - **A:** referência original (média do log P das outras UASGs no mesmo produto e trimestre); base M0, com 152 eventos.
  - **G:** referência G com dispersão contemporânea ≤ 0,8033; base M1, com 150 eventos.
- **Medicamentos:** itens da classe CATMAT 6505, pelo catálogo, sem uso de preço. Os demais materiais são todos os outros
  itens com índice.
- **Pesos:**
  - de precisão: w_k = 1/(a + b·h_k), com o (a, b) original e h_k = 1/c_pré + 1/c_pós da tratada no modelo;
  - congelados do modelo base, quando indicado;
  - iguais por evento.
- **Inferência:**
  - agrupada por órgão (CNPJ), com CR1 e t(G − 1);
  - bootstrap selvagem restrito (WCR, Webb, B = 9.999), com IC por inversão;
  - diferenças pareadas nos mesmos eventos com bootstrap selvagem não restrito do t.
- **Relato de cada modelo:**
  - efeito do AF em lp, EP, IC95 e p;
  - itens e compras das tratadas, eventos por sentido, UASGs tratadas e de controle;
  - órgãos e órgãos efetivos (1/HHI dos pesos);
  - pesos usados;
  - influência (retirando um órgão de cada vez: mínimo, máximo e maior |Δ|);
  - diferença contra −1,91 e −3,76 lp.
- **Não se faz:** controle pelo número de licitantes.

## Teste 1 — Medicamentos × demais materiais

Para A e G, três grupos de itens: todos, medicamentos e demais.

**Principal.**
- Eventos e controles do modelo base ficam fixos, assim como a referência de mercado e as janelas. Só os itens do grupo
  entram nas médias por compra.
- Exige-se pelo menos 1 compra com itens do grupo em cada meia janela, na tratada e em cada controle, e pelo menos 5
  controles.
- Pesos de precisão com o h do grupo.

**Sensibilidade.** Os controles são selecionados de novo para o grupo (motor padrão, cmin = 2).

## Teste 2 — Interação AF × medicamentos

- **Estimativa:** nos eventos com os dois grupos no teste 1 principal, d_k = DiD_med,k − DiD_demais,k. A interação é a
  média, com sinal do AF, de d_k.
- **Pesos:** de precisão para a diferença, w_k = 1/(2a + b·(h_med + h_demais)), e iguais.
- **Teste:** H0 é de efeitos iguais (interação = 0).
- **Identificação:** considera-se a interação identificável se houver pelo menos 30 eventos com os dois grupos, pelo menos
  10 em cada sentido e pelo menos 10 órgãos efetivos. Informa-se também o efeito mínimo detectável (2,8 × EP).

## Teste 3 — Índice de composição fixa

Para cada unidade (tratada e controles) e evento:
- **Cesta:** a cesta da pré-janela, em que produto = CATMAT + unidade de fornecimento padronizada.
- **Pesos:** s_p,pré = parcela de itens do produto na pré-janela. São só informação anterior à troca, sem preço.
- **Produtos continuados (C):** comprados nas duas meias janelas.
- **Índice:** Δ_fixa = Σ_{p∈C} w̃_p · (ē_p,pós − ē_p,pré), com w̃_p = s_p,pré / Σ_{C} s_p,pré e ē = média do índice do item
  (log P contra o mesmo produto e trimestre em outras UASGs).
- **Produtos que somem:**
  - principal: saem, e os pesos são renormalizados;
  - sensibilidade: entram com variação zero, ou seja, Δ_imputada = S_C,pré · Δ_fixa.
- **Produtos novos:** ficam fora do índice fixo e entram na decomposição (teste 4).
- **Exclusões:** unidade sem nenhum produto continuado sai (registrada).
- **DiD:** tratada menos a média dos controles do modelo base que têm produtos continuados.
- **Comparação:** com o índice original (DiD das médias por compra) calculado nos mesmos eventos e controles, com os pesos
  do modelo base congelados e com pesos iguais. Diferença pareada testada.

## Teste 4 — Decomposição preço × composição

Para cada unidade, Ē_t é a média do índice nos itens do período t, igual a Σ_p s_p,t · ē_p,t. Identidade exata:

ΔĒ = Ē_pós − Ē_pré = A + B1 + B2, em que

| Componente | Fórmula | Significado |
|---|---|---|
| A | Σ_C w̃_p (ē_p,pós − ē_p,pré) | preço dos produtos comparáveis, com pesos pré (= teste 3) |
| B1 | Ē^C_pós (pesos pós) − Σ_C w̃_p ē_p,pós | recomposição entre produtos continuados |
| B2 | (Ē_pós − Ē^C_pós) − (Ē_pré − Ē^C_pré) | entrada e saída de produtos |

- Cada componente vira um DiD (tratada menos a média dos mesmos controles); a soma reproduz o DiD de ΔĒ.
- A identidade é verificada numericamente, por unidade e no agregado (desvio máximo).
- IC95 e p para cada componente.
- Os componentes não recebem leitura causal isolada: B1 e B2 refletem escolhas de compra que podem responder ao modo.

## Teste 5 — Validade e robustez (para os modelos dos testes 1 a 4)

- **Pré-tendência:**
  - teste 1: trimestre −2 contra −1 (perfil do motor);
  - testes 3 e 4: as mesmas contas numa pseudojanela pré, [m−6, m−3) contra [m−3, m), com os mesmos controles. Devem dar
    zero.
- **Sentidos:** A → AF e AF → A em separado, com teste de simetria (soma = 0, WCR).
- **Influência:** retirada de um órgão de cada vez.
- **Inferência:** CR1 por órgão e WCR.
- **Pesos:** de precisão contra iguais.
- **Cobertura de produtos:** S_C,pré (itens pré em produtos continuados), S_C,pós (itens pós em produtos continuados) e
  parcela de medicamentos, em DiD tratada menos controles.

## Hipóteses (exploratórias)

- **H1:** o efeito do AF é igual em medicamentos e nos demais materiais (interação = 0).
- **H2:** o efeito no índice de composição fixa é igual ao do índice original (diferença = 0). Se não for, a composição
  contribui.
- **H3:** na decomposição, o componente de composição (B1 + B2) é zero.

## Saídas

- `tabelas/*.csv`, `graficos/*.svg`, `resultados.json`, `registro_execucao.json` e `relatorio.md`.
- Comando único: `python analises/composicao_precos_medicamentos_20261123/executar.py`.
