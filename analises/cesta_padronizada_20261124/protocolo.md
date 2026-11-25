# Protocolo — cesta padronizada de produtos (CATMAT × unidade)

Registrado em 24/11/2026, **antes** da execução definitiva da etapa `selecionar` e antes de qualquer leitura do modo de
disputa. Mudanças posteriores nos critérios exigem nova versão deste protocolo e de `versao_regras`.

Configuração registrada (SHA-256):

| Arquivo | SHA-256 |
|---|---|
| `config/parametros.json` | `cda6ac0e2cd9c7933301182a91439e4561bbf0a3597ec22502c527213b3632a4` |
| `config/aliases_unidades.csv` | `ad9ce441c5ef2a52748e3f1755c18aca595115e6341f5ccd8694db60cc5772ab` |
| `config/cautela.json` | `a9a7be77bf46f5cbb11997837a8e1c347d249107c78781bf5a9475902d834e09` |

## 1. Objetivo

Construir uma cesta fixa, auditável e tecnicamente defensável de produtos padronizados, comprados com frequência por
muitas UASGs, para uso futuro na comparação de preços homologados entre os modos Aberto (A) e Aberto-Fechado (AF).
**Este estudo não estima efeito de modo de disputa.**

## 2. Princípio de independência

A seleção usa somente: CATMAT, unidade de fornecimento, descrição e atributos do produto, número de compras distintas,
de UASGs e de órgãos, recorrência temporal, dispersão institucional, consistência das especificações e qualidade
cadastral. É proibido usar preço homologado ou estimado, desconto, diferença A × AF, coeficientes, valores-p ou o modo de
disputa. Garantias:

1. A extração não copia colunas monetárias nem `modo_disputa` para o banco de trabalho.
2. Teste estático: os módulos de seleção não mencionam essas colunas.
3. Teste metamórfico: alterar só preços e modos no banco sintético não altera nenhuma saída da seleção.
4. O modo de disputa só é lido na etapa `diagnostico`, que exige a cesta congelada (hash) e confere que ela não mudou.

## 3. Fonte e universo

- Banco: `dados/pncp.db` (raiz da pasta de trabalho), aberto com `mode=ro` e `query_only`, numa transação de leitura por
  etapa; impressão digital (tamanho, mtime, contador de alterações do SQLite, SHA-256 do início e do fim) conferida no
  início e no fim. Nenhum índice ou tabela é criado no banco de origem.
- Descrição detalhada: `descricaodetalhada` e `nomePdm` dos CSVs brutos que deram origem à carga
  (`dados/brutos/<ano>/itens_pregao_*.csv`), porque o banco guarda só o nome do item no catálogo. A ligação usa a chave
  composta do item; diferença de cardinalidade ou de CATMAT interrompe a execução.
- **Universo principal:** itens de **material** (`material_ou_servico = 'M'`) com código de catálogo válido, em compras
  da modalidade **Pregão - Eletrônico**, em **qualquer modo de disputa**, da fonte `dados_abertos` (Compras.gov.br, a única
  com CATMAT e UASG). As demais fontes e modalidades entram só na contagem descritiva.
- **Cobertura temporal:** toda a disponível, inclusive 2026, sem corte em 2025. Data de referência: `data_publicacao`.
- Exclusões, aplicadas em sequência e contadas: modalidade, natureza (serviço), CATMAT ausente/inválido, item cujos
  registros divergem em CATMAT/natureza/unidade, UASG ausente/inválida, data inválida e unidade ausente.

## 4. Unidades de contagem

- **Compra** = `numero_controle_pncp`. `id_compra` repetido não agrupa compras.
- **Item** = (`numero_controle_pncp`, `numero_item`). Registros repetidos são colapsados; `registro_principal` não é usado,
  porque escolhe o registro pelo valor do resultado.
- **UASG** = UASG da compra (`compras.uasg`); a UASG do item é auditada. O CNPJ é preservado, mas não define diversidade.
- **Família candidata** = CATMAT × unidade normalizada. A normalização trata grafia, por exemplo
  `UN`/`UND`/`UNIDADE` → `UNIDADE` e `Caixa 100,00 UN` → `CAIXA 100 UNIDADE`. Ela **não** converte grandezas: 1000 ML ≠ 1 L,
  caixa ≠ unidade, e `UNIDADE 0` ≠ `UNIDADE`.
- **Frequência principal** = compras distintas com itens **licitados**, em qualquer situação. A frequência de homologados
  é reportada ao lado e serve de cenário de sensibilidade.

## 5. Triagem quantitativa (parâmetros iniciais)

Compras ≥ 40; UASGs ≥ 15; trimestres ≥ 6; anos ≥ 2; participação da UASG dominante ≤ 25%; HHI ≤ 0,12 (HHI sobre compras
por UASG; número efetivo de UASGs = 1/HHI). Qualidade cadastral: unidade reconhecível e descrição completa em pelo menos
95% dos itens. "Completa" significa descrição presente e com conteúdo além do nome do PDM.

São parâmetros de triagem, não limiares validados, e não serão ajustados em função de preços ou efeitos.

## 6. Auditoria de homogeneidade e classificação

São examinadas todas as variantes de descrição de todas as famílias da triagem ampla, que é o cenário mais brando da
grade. As saídas trazem o texto original e o normalizado, frequências, UASGs, período, frequência acumulada, atributos
extraídos por regex (formato, gramatura, folhas, %, concentração, dosagem, volume, peso, dimensões, medidas,
capacidades, unidades por embalagem), indicadores (marca/modelo, aplicação, termos genéricos, compatibilidade,
certificação) e alertas. Nenhum modelo probabilístico aprova homogeneidade.

- **C:** descrição completa em menos de 50% dos itens; unidade ausente ou irreconhecível; descrição dominante sem atributos
  além do PDM; descrição genérica na maioria dos itens; nenhuma assinatura de atributos com pelo menos 50%; peça cuja
  referência ou aplicação define o objeto.
- **A:** descrição dominante (chave textual) em pelo menos 90% dos itens; uma única assinatura de atributos; pelo menos 2
  atributos declarados; descrição completa em pelo menos 95%; nenhum indício de embalagem divergente, marca/modelo,
  compatibilidade, aplicação ou termo genérico; unidade sem alerta.
- **B:** os demais casos.
- **Subtipos** são separados só quando todas as variantes têm assinatura não vazia e inequívoca, com o mesmo conjunto de
  atributos. Ficam no máximo em B e passam de novo pelos limiares.
- As categorias de cautela (`config/cautela.json`) geram alerta e pendência de revisão especializada, nunca exclusão
  automática.

## 7. Saídas principais

- `cesta_candidata.csv`: produtos A e B que passam a triagem e a qualidade cadastral, congelada com hash em
  `congelamento_cesta.json`.
- `formulario_revisao.csv`: campos de aprovação em branco.
- `cesta_validada.csv`: **vazia até haver revisão humana** (`validar_revisao.py`).
- Auditoria de qualidade, cobertura, funil, variantes de descrição (100%) e sensibilidade.

## 8. Sensibilidade (pré-especificada)

A grade fatorial de `parametros.json → sensibilidade` tem compras {20, 30, 40, 60, 80}, UASGs {10, 15, 20, 30}, trimestres
{4, 6, 8, 10}, anos {2, 3}, UASG dominante {15%, 25%, 35%} e HHI {0,06; 0,12; 0,20}. Há também os cenários nomeados
brando, inicial, rigoroso e inicial em homologados, com interseções e índice de Jaccard. O cenário inicial continua sendo o
principal, mesmo que outro cubra mais observações.

## 9. Tempo e risco de viés

A cesta descritiva usa todo o período. Uma eventual cesta causal deverá ser re-formada num período de formação definido
e documentado **antes** da análise de preços (`temporal.periodo_formacao`, hoje `null`). A recorrência por janelas
(`recorrencia_temporal.csv`) mostra se os produtos já eram comuns no início do período.

## 10. Diagnóstico posterior (não seletivo)

Depois do congelamento são medidos: compras por modo, UASGs que usaram A e AF, produtos nos dois modos, células
produto × trimestre comparáveis, trocas de modo dentro da UASG e eventos potenciais. O evento potencial foi definido
antes: pelo menos 3 compras da cesta só em A antes da primeira AF e pelo menos 3 em AF depois. Também é medida a
cobertura de referência interna: pelo menos 3 outras UASGs comprando o mesmo produto no trimestre. Nenhum produto é
removido ou incluído por esses indicadores, e nenhuma regressão de preço é estimada.
