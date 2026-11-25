# Protocolo da validação técnica da cesta padronizada

25/11/2026. Fixado antes de qualquer revisão humana. Os SHA-256 da configuração e do código de cada rodada estão no
`manifesto.json` da rodada; mudar regra, parâmetro ou entrada exige nova preparação (nova `versao_auditoria`).

## Objetivo

Identificar, entre os 16.248 produtos da cesta candidata, os que têm especificação técnica homogênea o bastante para
comparar preços unitários homologados entre pregões eletrônicos. **Priorizar a revisão não é aprovar**: a ordem P1…P5
só organiza o trabalho dos revisores e não seleciona a amostra do estudo causal.

## Independência em relação a resultados econômicos

1. A classificação técnica usa só descrições, atributos do catálogo, frequências (itens, compras, UASGs) e metadados
   técnicos (classe e PDM do catálogo, cautelas técnicas da cesta).
2. Não são lidos preços, valores estimados, descontos, modo de disputa, número de licitantes, coeficientes, valores-p,
   intervalos, estudo de eventos ou HonestDiD. O mapeamento de colunas (`config/mapa_colunas.json`) é explícito; a etapa
   `inspect` interrompe se uma coluna usada casar com um padrão proibido; arquivos com contagens por modo e a pasta do
   estudo econométrico não são abertos.
3. Os formulários não trazem preço nem modo. Os revisores não devem consultar o estudo econométrico nem os preços
   durante a revisão.
4. Testes automáticos provam que mudar preços e modos nas entradas não muda nenhum arquivo-base, formulário ou versão.
5. **Limite reconhecido:** esta revisão ocorre depois de resultados econométricos exploratórios já terem sido vistos
   (`analises/efeito_modos_cesta_padronizada_20261124/`). As salvaguardas protegem o procedimento, mas não tornam o estudo
   retrospectivamente confirmatório e independente.

## Prioridades e piloto

P1 = classe A ∩ cenário rigoroso (4.122); P2 = A fora do rigoroso; P3 = B ∩ rigoroso; P4 = B fora; P5 = demais. Dentro
de cada prioridade, compras distintas decrescentes e `id_candidato` crescente. Piloto: os 100 primeiros P1
(`saidas/piloto_P1_100/`); depois todos os P1 (`saidas/P1/`).

## Procedimento

1. `inspect`: confere cabeçalhos, mapeamento, chaves e ligação cesta ↔ variantes ↔ banco da cesta.
2. `preparar`: arquivos-base imutáveis com SHA-256, auditoria automática de 100% das descrições, formulários com todos os
   produtos PENDENTE e todas as variantes sem decisão. Nunca sobrescreve formulários com revisões preenchidas.
3. Revisão humana: uma decisão por variante (EQUIVALENTE / DIVERGENTE / INDETERMINADA) e uma por produto ou subproduto
   (APROVAR / REJEITAR / DESMEMBRAR / PENDENTE), cada uma com fundamentação, fonte documental verificável, revisor
   cadastrado e data. Recomenda-se a dupla revisão: quem aprova o produto não decide as variantes.
4. `concluir --exigir-dupla-revisao`: confere a integridade e emite o resultado. Falha de forma conservadora: na dúvida
   documental, não aprova.

## Regra de aprovação

Um registro só recebe `VALIDADO` quando todas as condições abaixo valem:

- decisão APROVAR;
- especificação canônica completa, com os atributos essenciais;
- fundamentação específica;
- fonte verificável;
- revisor identificado no cadastro;
- data válida;
- **todas** as variantes examinadas e declaradas EQUIVALENTE, cada decisão documentada;
- nenhum conflito objetivo não resolvido;
- alertas e riscos resolvidos por escrito;
- atributos essenciais documentados.

Uma família com conflito objetivo não pode ser aprovada como especificação única. Nesse caso:

- ela é REJEITADA ou DESMEMBRADA;
- se DESMEMBRADA, cada subproduto é revisto e aprovado à parte;
- se o conflito vier de erro de regra, corrige-se a regra, acrescenta-se um teste, registra-se a mudança em
  `metodologia_validacao.md` e prepara-se nova versão.

Os dados de base nunca são editados.

## Saídas e integração

Com aprovações, `concluir` grava `cesta_validada.csv` na rodada. Também grava `integracao_econometria/`: uma cópia dos
arquivos congelados da cesta com `cesta_validada.csv` no formato original e só produtos inteiros. Assim o estudo
econométrico pode rodar de novo sem alterar código, modelos ou protocolo.

Subprodutos exigem adaptar a ligação item × especificação atômica (`ligacao_itens_especificacoes.csv`). O CATMAT
original não basta para presumir equivalência.

## Limites de interpretação

A homogeneidade técnica do objeto não elimina outras fontes de diferença de preço:

- quantidade, frete e destino;
- prazo, garantia e marca;
- condições logísticas, qualidade contratual e mercado regional.

Ela também não resolve a endogeneidade da escolha do modo de disputa nem as falhas de pré-tendência já identificadas no
estudo econométrico.
