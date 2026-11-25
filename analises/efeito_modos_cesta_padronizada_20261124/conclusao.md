# Conclusão — efeito do modo de disputa (Aberto × Aberto-Fechado) na cesta padronizada

25/11/2026. Números de [`relatorio.md`](relatorio.md), gerado por `executar.py` a partir das saídas. Esta conclusão é a
única parte escrita à mão; ela interpreta, não acrescenta resultados.

## Estatuto dos resultados

**Tudo é exploratório.** A cesta validada (`cesta_validada.csv`) não tem nenhum produto aprovado — o formulário de
revisão técnica não recebeu decisões. A análise principal do protocolo exige produtos tecnicamente validados e, por
isso, **não foi executada** (funil, etapa 7: 0 itens; robustez R01: não estimável). As estimativas usam a cesta
candidata (16.248 produtos), que foi selecionada sem olhar preço, desconto ou modo, mas cuja padronização não foi
conferida por especialista. Nenhum número abaixo deve ser citado como efeito causal confirmado.

## O que os dados mostram

1. **Diferença descritiva.** Nos 1.308.331 itens homologados com referência leave-one-UASG-out (A1), o AF fica
   −4,95 lp (−4,8%) abaixo do Aberto em relação ao preço das outras UASGs no mesmo produto e trimestre, IC95
   [−9,13; −0,78], erros agrupados por órgão (CNPJ). O preço homologado sem referência não difere (+2,3 lp, IC inclui
   zero): o AF é mais usado em produtos/períodos de preço absoluto diferente, e a referência corrige isso.

2. **Associação condicional.** Com efeitos fixos de UASG e produto × trimestre e controle de quantidade (E3), a
   diferença é −5,96 lp (−5,8%), IC95 [−8,39; −3,53], WCR p = 0,001. É estável a SRP, orçamento sigiloso, produto × mês,
   órgão × ano, exclusão dos trimestres incompletos, às 14 referências alternativas (amostra comum: −5,8 a −6,1 lp;
   diferenças pareadas desprezíveis) e à exclusão de cada um dos 10 órgãos com mais peso (−5,3 a −7,3 lp). O maior órgão
   concentra 18% da variação identificadora. A associação é maior em compras de pouca quantidade (tercil 1: −7,6 lp;
   tercil 3: −4,3 lp).

3. **A associação encolhe quando se compara a mesma UASG no mesmo produto.** Com efeito fixo UASG × produto (E7), cai
   para −2,86 lp, IC95 [−5,90; 0,17], WCR p = 0,19. Parte relevante da diferença entre modos vem de *quais* UASGs usam
   AF para *quais* produtos, não de uma mudança de preço dentro da mesma relação UASG–produto.

4. **Estudo de eventos (dCDH, tratamento reversível).** 317 trocas persistentes de modo (172 adoções, 145 abandonos)
   em 187 órgãos. Na janela de 6 meses, ponderação por item:
   - agregado −4,58 lp, IC95 [−9,15; −0,02], p = 0,049 — **p de Holm na família principal 0,148**;
   - adoção −5,05 lp (p = 0,17); abandono −4,09 lp (p = 0,11); simetria −0,96 lp (sem evidência de assimetria);
   - a estimativa depende do estimando: por compra −2,0 lp (p = 0,36), peso igual por evento −4,2 lp (p = 0,27),
     janela de 12 meses −3,2 lp (p = 0,16), mesmo produto antes e depois −0,7 lp (p = 0,88), células de menor
     dispersão −2,4 lp (p = 0,17);
   - a identificação é estreita: 145 eventos em l = 1, 15 órgãos efetivos, o maior órgão com 21% do peso, e só 2,6% de
     sobreposição de produtos entre os períodos pré e pós.

5. **Os placebos falham.** No trimestre anterior à troca, o placebo agregado é +14,2 lp (p = 0,001), puxado pelo
   abandono do AF (+20,9 lp, p < 0,001); na adoção é +7,3 lp (p = 0,14). As UASGs que trocam de modo já estavam numa
   trajetória de preço relativo diferente das que não trocam, justamente no período imediatamente anterior. O padrão é
   compatível com trocas motivadas por choques de preço e com reversão à média depois delas — e não com tendências
   paralelas. As características observáveis (quantidade, SRP, sigilo, taxa de homologação) não mudam de forma
   significativa na troca, mas isso não descarta seleção em preços.

6. **HonestDiD.** Com restrição de magnitude relativa, todos os intervalos incluem zero para M̄ ≥ 0,5 (e a maioria já
   em M̄ = 0). Com restrição de suavidade, só o abandono com M = 0 e 0,5 exclui zero — e com sinal **positivo**
   ([0,8; 25] lp): extrapolando linearmente a pré-tendência, nem o sinal do efeito é robusto.

7. **Desfechos secundários.** O desconto sobre o valor estimado é 3,8 p.p. maior no AF na associação (E3), coerente
   com o preço relativo menor; no estudo de eventos, +2,6 p.p. (p = 0,10; Holm 0,41). Homologação, fracasso e deserção
   não diferem entre modos em nenhum dos modelos (todos os IC incluem zero; Holm = 1).

8. **BJS (só adoções absorventes).** −10,4 lp, IC95 [−18,5; −2,3]. É um subconjunto selecionado (212 trocas absorventes
   sem retorno), sujeito ao mesmo problema de pré-tendência, e não altera a leitura.

## Resposta

Na cesta candidata, **compras em modo Aberto-Fechado estão associadas a preços relativos cerca de 6% menores** do que
compras em modo Aberto, de forma estável entre referências, especificações de efeitos fixos e exclusões de órgãos.
**Essa associação não tem identificação causal convincente:** ela se reduz à metade dentro de UASG × produto, o estudo
de eventos dá estimativas menores e sensíveis ao estimando, cuja significância não sobrevive à correção de Holm, os
placebos pré-troca falham de forma forte, e os intervalos do HonestDiD incluem zero sob qualquer desvio plausível das
tendências paralelas. O modo de disputa não altera de forma detectável a homologação, o fracasso ou a deserção.

## O que falta para uma análise confirmatória

1. **Revisão técnica da cesta.** Preencher `formulario_revisao.csv` da cesta padronizada e rodar
   `validar_revisao.py`. Com produtos aprovados, `executar.py` roda a análise principal sem alterar código; o
   protocolo é o mesmo.
2. **Lidar com a seleção da troca.** A falha de placebo é o obstáculo central. Opções a registrar antes de
   reestimar: condicionar a trajetória pré-troca (matching em Y defasado), restringir a trocas induzidas por mudanças
   normativas ou de sistema (variação exógena de calendário) e janelas mais longas de pré-tratamento.
3. **Mais eventos.** Com 15 órgãos efetivos, o efeito mínimo detectável a 80% de poder é de ~6,5 lp no agregado; a
   extensão do período (o CATMAT some da fonte depois de 17/04/2026) aumentaria a potência.

## Limitações de dados

- O CATMAT some da fonte depois de 17/04/2026: 2026T2 é incompleto e 2026T3–T4 não são observados (censura, não
  ausência de compras).
- Em 2023T1 a API mantém "Em andamento" em itens já com preço; o preço só é usável a partir de 2023T2.
- A amostra analítica (79 MB, `amostra_analitica.csv.gz`) e os intermediários ficam fora do git, em
  `D:\efeito_modos_trabalho\`; `executar.py` os recria a partir de `pncp_v2.db` (somente leitura) e da cesta.
- As alterações feitas depois do registro do protocolo — todas correções de implementação, nenhuma mudança de
  especificação — estão em [`desvios_registro.md`](desvios_registro.md).
