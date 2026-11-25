# Conclusão — validação técnica da cesta padronizada

25/11/2026. Números de [`relatorio.md`](relatorio.md); esta nota só interpreta.

## Estado

**Nenhum produto está tecnicamente validado e não existe `cesta_validada.csv`.** O sistema fez tudo o que pode fazer sem
especialistas:

- inspecionou as entradas reais e confirmou as chaves;
- auditou 100% das 8.324 descrições originais dos 4.122 candidatos P1 (classe A ∩ cenário rigoroso), agrupadas em 6.282
  variantes normalizadas e cobrindo 933.477 itens;
- preparou os formulários de revisão do piloto (100 produtos) e de todo o P1;
- deixou pronta a etapa que gera a cesta validada a partir de decisões documentadas.

Os 39 testes passam. Nenhuma etapa leu preço, valor, desconto, modo de disputa, licitantes ou resultado econométrico, e
os bancos de origem ficaram inalterados.

## O que a auditoria mostra

- **96,5% dos P1 não têm divergência detectada entre as descrições do catálogo.** Na maioria das famílias, as variantes
  são o mesmo texto do CATMAT em dois formatos (com e sem `ATRIBUTO:`) ou com espaços perdidos. Isso é evidência a favor da
  homogeneidade do *texto*, não prova de que todas as compras contrataram o mesmo objeto.
- **1 produto tem conflito objetivo:** a parafusadeira `CP1860`, com mandril `12 POL` × `1/2 POL`. Ele é desmembrável em dois
  subprodutos reproduzíveis. Os outros 17 conflitos da primeira execução eram erros das regras: `CX` lido como caixa,
  separador de milhar, fração de polegada, palavras coladas. Foram corrigidos com teste e estão registrados em
  `metodologia_validacao.md`.
- **143 produtos (3,5%) pedem exame:**
  - informação parcial ou texto colado na fonte (por exemplo, `ARAMEACO`, `SOLUCAOINJETAVEL`);
  - números partidos por quebra de linha;
  - nome do item diferente entre variantes;
  - 53 variantes sem descrição (1 item cada), que só se ligam ao produto pelo código.
- **Avaliação especializada e editais:** 2.478 produtos caem em categorias de risco (material médico, medicamento,
  eletrônico, peça, compatibilidade, químico). Para 919, a auditoria recomenda consultar edital ou termo de referência.
  A homogeneidade do catálogo não basta nesses casos.

## Leitura

A cesta P1 é, no texto do catálogo, muito mais homogênea do que o número de variantes sugere. O obstáculo à validação
não é técnico-automático, é documental: falta quem decida e assine. O sistema não aprova nada por pertencer à classe A,
por estar em P1 ou por não ter divergência detectada.

## Próximos passos

1. Cadastrar os revisores em `config/revisores.csv`, com qualificação compatível com as categorias de risco.
2. Revisar o piloto (`saidas/piloto_P1_100/`) com dupla revisão, ajustar o processo e seguir para `saidas/P1/`.
3. Rodar `concluir --exigir-dupla-revisao` e `relatorio`.
4. Com produtos aprovados, rodar o estudo econométrico de novo pela pasta `integracao_econometria/`, sem alterá-lo.

Mesmo então, a validação técnica só melhora a comparabilidade do objeto. Ela não resolve a endogeneidade da escolha do
modo nem as falhas de pré-tendência já documentadas. Como ocorre depois de resultados exploratórios já vistos, também
não torna o estudo inteiramente confirmatório.
