# Protocolo da investigação complementar (23/11/2026). Exploratória

Escrito antes de executar. A investigação complementa os testes de robustez (`../robustez_dispersao_20261123/`) e o estudo
de eventos de 23/11 (`../testes_desenho_causal_20261123/`). Todos os resultados são **exploratórios**. Nenhuma
especificação é escolhida pela significância.

## Regras gerais

- **Bases:** a de 23/11 (`dados/testes_desenho_causal/`) e as descrições do cache de robustez. Nada é alterado. O
  `pncp.db` não é lido.
- **Motor:** `../robustez_dispersao_20261123/motor_robustez.py`, só importado. Já reproduziu M0 (−1,91 lp) e M1 (−3,76 lp).
- **Eventos:** os da janela de 6 meses com desfecho completo (evento até 2025-10). Os eventos reservados para a
  validação confirmatória (2025-11 em diante) não entram; o script confere e registra isso.
- **Pesos:** de precisão w_k = 1/(a + b·h_k), com o (a, b) original. Quando indicado, os pesos do modelo base ficam
  congelados.
- **Relato de cada estimativa:**
  - coeficiente (lp ou p.p.), EP agrupado por órgão (CNPJ), IC95 e p (bootstrap selvagem restrito, Webb, B = 9.999);
  - eventos por sentido, itens e compras, órgãos e órgãos efetivos (1/HHI);
  - influência: retirando os eventos de um órgão de cada vez, mínimo, máximo e maior |Δ|, além do órgão de maior peso.
- **Diferenças entre especificações nos mesmos eventos:** influências somadas por órgão, com bootstrap selvagem não
  restrito do t (Webb).

## 1. BJS × estudo de eventos com os mesmos insumos

Feito para as duas especificações de referência:
- **A:** referência original, todas as células; modelo base M0;
- **G:** referência G, dispersão contemporânea ≤ 0,8033; modelo base M1.

Em cada evento do modelo base ficam fixos:
- a unidade tratada, a janela [m−6, m+6) e os controles limpos do modelo base;
- os itens: com índice, no filtro da especificação e com log P.

| Passo | Definição |
|---|---|
| S0 | DiD empilhado do modelo base (todos os itens) |
| S1 | DiD empilhado só com os itens pós-troca da tratada que o BJS do evento consegue imputar. Os itens pré da tratada e todos os itens dos controles ficam iguais aos de S0 |
| S2 | BJS por evento, com exatamente os itens de S1 (detalhe abaixo) |
| S3 | BJS original: não tratados = compras no modo de partida das unidades estáveis no período todo, mais as pré-janelas das unidades que mudam; mesmos eventos e itens elegíveis |

**BJS por evento (S2).**
- Não tratados: todos os itens dos controles na janela e os itens pré-troca da tratada.
- Modelo: log P = α_unidade + γ_{produto × trimestre}, estimado nos não tratados.
- Imputa-se o item pós-troca da tratada cuja célula tem pelo menos 3 itens não tratados.
- O efeito do evento é a média das médias por compra de log P − imputado.

**Decomposição**, nos eventos presentes em S0 a S3 e com os pesos de S0 congelados:
- amostra de itens = S1 − S0;
- estimador, com mesmos itens, eventos, controles, períodos e elegibilidade = S2 − S1;
- conjunto de controles e períodos do BJS original = S3 − S2.

O mesmo se repete com pesos iguais. O efeito da ponderação é a comparação de precisão própria, pesos de S0 e pesos
iguais em cada passo. Exige-se cmin = 2 compras pré e pós na tratada depois da restrição.

## 2. Dispersão histórica × contemporânea na amostra comum

- **Base:** o modelo com referência G e todas as células (G-todas). Eventos, controles e pesos (precisão de G-todas)
  ficam fixos.
- **Dispersões:**
  - contemporânea = desvio-padrão, entre as outras UASGs, do log do preço médio no mesmo trimestre;
  - histórica (D) = mediana desse desvio nos até 4 trimestres inteiros antes da janela, sem a própria UASG e com ≥ 3
    outras UASGs.
- **Variantes,** com cmin = 1 compra por meia janela e os controles fixos:

  | Variante | Itens |
  |---|---|
  | (a) | todos os itens G |
  | (b) | amostra comum: itens com as duas dispersões definidas |
  | (c) | amostra comum, contemporânea ≤ 0,80 |
  | (d) | amostra comum, histórica ≤ 0,80 |
  | (e) | todos os itens, contemporânea ≤ 0,80 |

- **Comparações pareadas:**
  - (c) − (d): definição do filtro, mesmos itens;
  - (e) − (c): retirar os itens sem histórico, sob o filtro contemporâneo;
  - (b) − (a): retirar os itens sem histórico, sem filtro.
- **Exclusões por falta de histórico:**
  - parcela sem D por sentido, período (pré/pós), grupo (tratada/controle) e modo da compra (AF/A);
  - DiD da parcela sem D, ou seja, se a falta de histórico muda na troca;
  - modelo de probabilidade linear, nos itens das tratadas, para "sem D": efeito do item ser de compra AF, com efeito
    fixo de evento; sem e com as características do produto (medicamento, apresentação padronizada H1, nível de preço de
    mercado, índice de quantidade, frequência do produto);
  - comparação das características dos itens sem e com D, com efeito fixo de evento.

## 3. Composição das compras na troca de modo

- **Base:** eventos, controles e pesos de G-todas (fixos), com cmin = 1.
- **Para cada característica:**
  - efeito com sinal (componente específico do AF: sinais opostos na entrada e na saída);
  - A → AF e AF → A em separado;
  - soma dos dois sentidos (componente comum a qualquer troca, mesmo sinal), com teste = 0;
  - perfil por trimestre (−2, 0, +1) com testes conjuntos;
  - troca fictícia 12 meses antes;
  - influência;
  - Holm entre as características, para o efeito com sinal e para a soma.
- **Características por compra** (média dos itens):
  - repetição de CATMAT: o item é de um CATMAT que a unidade comprou nos 12 meses anteriores;
  - repetição de produto (CATMAT + unidade), no mesmo critério;
  - parcela de medicamentos (6505);
  - log do nº de CATMATs distintos;
  - índice de quantidade e log da quantidade;
  - índice do estimado (eR);
  - parcela com índice G;
  - parcela elegível ao filtro contemporâneo;
  - log do nº de itens.
- **Características por evento,** tratada menos controles:
  - sobreposição de produtos e de CATMAT com a pré-janela;
  - dissimilaridade de Duncan entre as classes CATMAT da pré e da pós-janela;
  - DiD da parcela com dispersão histórica definida e da parcela com histórica ≤ 0,80.

## Saídas

- `tabelas/*.csv`, `resultados.json`, `registro_execucao.json` e `relatorio.md`.
- Comando único: `python analises/investigacao_bjs_dispersao_composicao_20261123/investigar.py`.
