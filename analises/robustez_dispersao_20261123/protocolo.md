# Protocolo dos testes de robustez da dispersão (23/11/2026). Todos exploratórios

Escrito antes de executar os testes. Os testes complementam o estudo de eventos A × AF
(`analises/testes_desenho_causal_20261123/`: pré-registro `protocolo.md`, resultados `relatorio.md` §3 e §12). Todos são
**exploratórios**: o corte de dispersão foi sugerido depois de ver os resultados do estudo principal. Nenhuma especificação
é escolhida pelo menor valor-p.

## Referências a reproduzir

| Modelo | Definição | Esperado |
|---|---|---|
| **M0, original** | referência A (média do log P dos itens das outras UASGs, ≥ 5 itens de ≥ 3 UASGs), todas as células | −1,91 lp [−5,67; +1,93], 152 eventos |
| **M1, filtrado** | referência G (média geométrica dos preços médios das outras UASGs, ≥ 3 itens de ≥ 3 UASGs), dispersão contemporânea ≤ 0,8033 ("0,80") | −3,76 lp [−6,67; −0,89], 150 eventos, 144 deles no M0 |

- **Dispersão contemporânea:** desvio-padrão, entre as outras UASGs da célula produto × trimestre, do log do preço médio da
  UASG. O valor de 0,8033 é o p75 dos itens, já fixado em 23/11.
- **Motor comum:** janela de 6 meses e cmin = 2 compras com índice em cada meia janela.
- **Controles limpos:**
  - da mesma esfera;
  - estáveis no modo de partida nas duas meias janelas (≤ 10% ou ≥ 90% de AF);
  - sem evento próprio a menos de 6 meses;
  - com cmin compras em cada meia janela;
  - pelo menos 5 por evento.
- **Agregação:** média por compra, depois média por meia janela.
- **Pesos de precisão:** w_k = 1/(a + b·h_k), com a = 0,009415, b = 0,23849 e h_k = 1/c_pré + 1/c_pós da tratada.
- **Inferência:** agrupada por órgão (CNPJ); CR1; bootstrap selvagem restrito (WCR) com pesos de Webb, B = 9.999; IC por
  inversão do teste.

O novo motor (`motor_robustez.py`, item a item e com filtros por evento) precisa reproduzir M0 e M1. Se não reproduzir, a
divergência é registrada e os testes seguem com o motor novo.

## Relato padrão de cada estimativa

- coeficiente em lp, EP CR1, IC95 (WCR e t(G−1)), p (WCR e t);
- itens e compras das tratadas nas janelas, eventos por sentido, UASGs tratadas e de controle;
- órgãos, órgãos efetivos (1/HHI dos pesos por CNPJ) e peso do maior órgão;
- tipo de peso.

## Testes

1. **Amostra comum.** M0 e M1 nos eventos presentes nas duas especificações. A diferença M1 − M0 tem EP pelas funções de
   influência somadas por órgão, com bootstrap selvagem (WCU, Webb) para o t.
2. **Pesos fixos.** Grade 2 × 2: referência (A, G) × células (todas, ≤ 0,80), nos eventos comuns às quatro. Duas versões:
   pesos de M0 congelados e pesos iguais.
3. **Controles idênticos.** Mesmos eventos, janelas, unidades de controle e pesos do modelo com todas as células (A e, à
   parte, G). Só se excluem os itens de células com dispersão > 0,80.
   - Um controle sem compra filtrada numa meia janela fica de fora, e isso é registrado.
   - Uma tratada sem compra filtrada numa meia janela tira o evento.
4. **Dispersão pré-tratamento.**
   - Para o item do produto p comprado pela UASG u no evento k, D = mediana, nos até 4 trimestres inteiros anteriores à
     janela, do desvio-padrão entre as outras UASGs (sem u) do log do preço médio.
   - Só entram trimestres com ≥ 3 outras UASGs. Sem nenhum, D fica vazio e o item é excluído.
   - Referência G, filtro D ≤ 0,8033 e motor M1.
5. **Heterogeneidade formal.**
   - No mesmo evento, DiD com os itens de D ≤ 0,80 e DiD com os de D > 0,80, cada um com cmin = 2.
   - Teste da diferença pareada por evento (pesos de M0 congelados, WCR por órgão).
   - Descritivo em 4 faixas de D: ≤ 0,27; 0,27–0,46; 0,46–0,80; > 0,80, nos limites p25, p50 e p75 de 23/11.
6. **Composição.** DiD com sinal (efeito do AF) de cada característica, com as mesmas regras de M1. Desfechos por compra:
   - índice de quantidade e log da quantidade bruta;
   - índice do estimado (eR);
   - log do nº de itens de material;
   - parcela de itens com índice G;
   - parcela elegível ao filtro (dispersão contemporânea ≤ 0,80, entre os itens com índice G);
   - parcela com unidade "UNIDADE";
   - parcela médica (classe 65xx); medicamentos (6505);
   - nível de mercado do produto;
   - ME/EPP exclusivo e sigilo.

   Por evento:
   - sobreposição de produtos, ou seja, a fração dos itens da pós-janela cujo produto a unidade comprou na pré-janela, na
     tratada menos nos controles;
   - dissimilaridade de Duncan entre as distribuições por classe CATMAT na pré e na pós-janela, na tratada menos nos
     controles;
   - parcela elegível pela dispersão histórica (teste 4).
7. **Ponderação contínua.** Função definida aqui, antes de estimar:
   - itens com D definido (teste 4) e índice G;
   - peso do item w_i = 1/D̃_i², com D̃_i = min(max(D_i, 0,20), 1,50), o que limita a razão entre o maior e o menor peso
     a 56;
   - média da compra = Σ w_i e_i / Σ w_i; peso da compra na meia janela = média dos w_i dos seus itens;
   - comparação com o corte D ≤ 0,80 na mesma base de itens.
8. **Homogeneidade dos produtos,** sem usar preço. A descrição resumida do Compras.gov.br é o nome genérico do item no
   catálogo e é constante dentro do CATMAT em 98,5% dos códigos, por isso não discrimina. O critério usa a apresentação:
   - **H1:** CATMAT com pelo menos 20 itens no período, sendo ≥ 90% deles na unidade padronizada modal. A unidade modal
     não pode ser embalagem genérica sem conteúdo (CONJUNTO, JOGO, KIT, ROLO, ENVELOPE, MOLHO, CAIXA, PACOTE, EMBALAGEM,
     FARDO, SACO, PECA, VOLUME, CARTELA, BLOCO, TUBO, LATA, BALDE, BOMBONA, GALAO, POTE, BISNAGA ou FRASCO sozinhos) nem ter
     conteúdo zero ("0 00"). Produto homogêneo = (CATMAT, unidade modal).
   - **H2:** H1 restrito a medicamentos (classe 6505), padronizados por princípio ativo, concentração e forma.
   - Estimam-se H1 e H2 com a referência G e todas as células. Informa-se também quanto de H1 cai na dispersão ≤ 0,80.
9. **Influência dos órgãos.**
   - Retira-se um órgão de cada vez (os eventos tratados dele), para M0 e M1;
   - distribuição dos coeficientes;
   - os 10 órgãos de maior peso e de maior influência (|Δ| ao retirar);
   - número efetivo de órgãos.
10. **Inferência robusta,** para M0, M1, o teste 4 e o teste 7:
    - CR1 com t(G − 1);
    - WCR com pesos de Webb e de Rademacher;
    - WCU com Webb;
    - jackknife por órgão;
    - aleatorização com controles de precisão parecida (os 20 de h mais próximo; 5.000 sorteios).
11. **Sentidos.** A → AF e AF → A em separado e teste de simetria (soma = 0, WCR), para M0, M1, o teste 4 e o teste 7.
12. **Dinâmica.**
    - Trimestres de evento com base −1: janela de 6 meses (−2, 0, +1) e de 12 meses (−4 a +3; eventos válidos para 12
      meses, como no protocolo de 23/11), para M0 e M1. O teste 4 só com 6 meses.
    - IC por bin e testes conjuntos (Wald, F(q, G − 1)) das defasagens e dos efeitos posteriores, com covariância entre
      bins pelas funções de influência por órgão, admitindo painel desbalanceado.
13. **Placebos** de M1 e do teste 4:
    - pré-tendência;
    - troca fictícia 12 meses antes (unidade estável);
    - aleatorização no espaço;
    - estimado (eR), quantidade, composição (sobreposição, Duncan);
    - elegibilidade ao filtro.
14. **Estimadores alternativos.** Cascata do M0 até a imputação BJS no M1:
    - M0;
    - troca da referência A → G;
    - troca da amostra (todas → ≤ 0,80);
    - troca dos pesos (precisão → iguais);
    - troca do método (empilhado → BJS: efeitos fixos de unidade/janela + produto × trimestre nos não tratados, mesmos
      itens e eventos).

    Também a ordem inversa (método antes da referência), para mostrar a dependência do caminho.
15. **Preparação da validação.** Especificação candidata única, fixada aqui antes de qualquer resultado novo:
    - referência G, dispersão pré-tratamento D ≤ 0,8033 (teste 4);
    - DiD empilhado com janela de 6 meses, cmin = 2 após o filtro e controles limpos do protocolo;
    - pesos de precisão com o (a, b) original;
    - estimando τ_AF agregado, bilateral, α = 5%, WCR por órgão;
    - testes de falsificação F1–F4 do protocolo de 23/11.

    Poder pelo modelo de variância dos controles placebo (sem desfecho das tratadas), para os eventos futuros esperados.
    Períodos e eventos não usados: eventos datados depois de 2025-10, itens de 2026-04 em diante (sem CATMAT na base),
    PDFs do Aberto e outras plataformas. Não se executa o teste confirmatório.

## Regras

- Não se alteram o `pncp.db`, a base de 23/11 (`dados/testes_desenho_causal/`) nem os resultados anteriores. Os scripts de
  23/11 são só importados, sem escrever `__pycache__`.
- Erros e exclusões vão para `registro_execucao.json`.
- Comando único: `python analises/robustez_dispersao_20261123/executar_todos.py`.
