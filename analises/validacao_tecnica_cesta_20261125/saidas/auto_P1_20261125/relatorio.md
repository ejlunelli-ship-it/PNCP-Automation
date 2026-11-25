# Validação técnica automática — cesta P1

Gerado em 2026-11-25T13:39:34 (execução `b83d3184-118d-5b9b-b732-7e310ff1c631`), validador 2.0.0, regras automáticas 2.0.0, sobre a auditoria congelada `40caddd4e39c2c6d`. **Modalidade automática: não é revisão humana**; nenhum formulário de revisor foi preenchido e nenhuma assinatura foi criada.

> Aprovação só quando a equivalência técnica é demonstrável por atributos objetivos e evidência verificável (catálogo oficial CATMAT). A ausência de conflito, sozinha, não aprova nada. AUTO_VALIDADO_CATALOGO valida a família de catálogo, **não** cada contratação; itens só são AUTO_VALIDADO_ITEM com documento da própria compra.

## Resultados gerais

| Status automático da família | Produtos | % |
|---|---|---|
| AUTO_VALIDADO_CATALOGO | 3.065 | 74,4% |
| AUTO_INCONCLUSIVO | 949 | 23,0% |
| AUTO_VALIDADO_CATALOGO_COM_RESSALVA | 107 | 2,6% |
| AUTO_DESMEMBRAR | 1 | 0,0% |

| Conjunto | Produtos | Compras | Itens | UASGs |
|---|---|---|---|---|
| S3_candidato_P1 | 4.122 | 88.110 | 933.477 | 4.257 |
| S1_catalogo_alta_seguranca | 3.065 | 74.167 | 708.964 | 4.141 |
| S2_catalogo_intermediaria | 107 | 15.361 | 43.863 | 2.751 |
| S4_itens_verificados | 29 | 29 | 36 | 29 |

- Subprodutos identificados: 2 (0 S1, 2 inconclusivos).
- Itens: AUTO_VALIDADO_ITEM 36; ITEM_NAO_ELEGIVEL 180.650; ITEM_SEM_CLASSIFICACAO 1; ITEM_SEM_VALIDACAO_DOCUMENTAL 752.790.
- S1 = catálogo com atributos essenciais completos e equivalência demonstrada (validação automática rigorosa); S2 = catálogo consistente com ressalva documental não crítica (**não** é validação sem qualificação); S3 = os 4.122 candidatos, sem validação presumida; S4 = itens com compatibilidade demonstrada pelo documento da contratação.

## Qualidade da documentação

- **Catálogo oficial (nível 1):** API pública de dados abertos do Compras.gov.br — `4_consultarItemMaterial`, `7_consultarMaterialCaracteristicas`, `6_consultarMaterialUnidadeFornecimento` (endpoints conferidos na documentação OpenAPI). 8.420 de 8.420 consultas com resposta; período 2026-11-25T11:43:45 a 2026-11-25T13:35:12. Respostas guardadas com SHA-256 (`catalogo_fontes.csv`).
- **Contratações (nível 2):** API pública do PNCP (`/compras/{ano}/{seq}/arquivos`), amostra documental de 400 compras (uma por família, sorteio por SHA-256, independente da classificação). 400 documentos (TR/edital) localizados, 400 com texto. Resultado por compra: SEM_ANCORA 278; INSUFICIENTE 58; COMPATIVEL 38; POSSIVEL_DIVERGENCIA 26.
- **Nível 3 (normas, fabricantes):** não consultado automaticamente — nenhuma fonte desse tipo foi usada como prova.
- **Indisponibilidades registradas:** 0 (`documentos_indisponiveis.csv`).

## Qualidade da classificação

| Status da variante × catálogo oficial | Variantes |
|---|---|
| CONFORME_TEXTO_OFICIAL | 6.198 |
| SEM_DESCRICAO | 53 |
| CONFORME_ATRIBUTOS | 17 |
| DIVERGENCIA_TEXTUAL | 11 |
| CONFORME_COM_CORRECAO_TIPOGRAFICA | 2 |
| DIVERGENTE | 1 |

**Motivos das decisões inconclusivas** (um produto pode ter mais de um):

| Motivo | Produtos |
|---|---|
| compatibilidade | 402 |
| material_medico | 395 |
| peca_reposicao | 350 |
| produto_quimico | 183 |
| equipamento_eletronico | 148 |
| medicamento | 76 |
| equivalência não demonstrável | 11 |
| geral | 4 |

**Ressalvas de S2:**

| Ressalva | Produtos |
|---|---|
| 1 variante(s) sem descrição | 44 |
| característica/valor inativo no catálogo | 32 |
| item inativo no catálogo oficial | 22 |
| unidade FRASCO 120 DOSE S não consta das unidades oficiais do PDM | 4 |
| unidade FRASCO 200 DOSE S não consta das unidades oficiais do PDM | 1 |
| unidade FRASCO 60 DOSE S não consta das unidades oficiais do PDM | 1 |
| 1 item(ns) com mais de uma descrição bruta | 1 |
| equivalência com correção tipográfica (espaço dentro de número) | 1 |
| unidade EMBALAGEM 120 DOSE S não consta das unidades oficiais do PDM | 1 |

Regras aplicadas (todas em `metodologia_automatica.md`): especificação canônica = características oficiais do CATMAT; variante conforme só se for o texto oficial a menos de espaços ou contiver todos os valores oficiais sem divergência de grandeza; '1/2' nunca casa com '12'; espaço dentro de número só é aceito quando o número oficial é contíguo, com ressalva S2; perfis por categoria de risco exigem atributos críticos no catálogo; unidade conferida com as unidades oficiais do PDM.

## Os 143 casos pendentes da auditoria 1.2.0

Os 143 produtos com divergência a examinar foram reexaminados contra o catálogo oficial (`pendencias_143_classificadas.csv`); um produto pode ter mais de um problema:

| Problema | Produtos |
|---|---|
| palavra concatenada / espaçamento (resolvida pelo texto oficial) | 94 |
| falha de extração da auditoria 1.2.0 (todas as variantes conformes ao texto oficial) | 72 |
| descrição ausente | 53 |
| divergência lexical sem diferença material (todos os valores oficiais presentes) | 11 |
| divergência textual de atributo não demonstrada como equivalente | 11 |
| número quebrado por quebra de linha (correção tipográfica, S2) | 2 |

Status automático resultante: AUTO_VALIDADO_CATALOGO 56; AUTO_VALIDADO_CATALOGO_COM_RESSALVA 47; AUTO_INCONCLUSIVO 40. Nenhuma regra foi ajustada para aprová-los; as únicas correções são as inequívocas (espaçamento conferido no texto oficial).

## Caso CP1860 (parafusadeira: mandril 12″ × 1/2″)

- Catálogo oficial do CATMAT 444251 (consultado em 2026-11-25T12:29:58, SHA-256 `c601eedd4c981feb…`): «PARAFUSADEIRA, TIPO: PROFISSIONAL , VELOCIDADE: REVERSÍVEL , ROTAÇÃO: MÍNIMA: 600 RPM, MÁXIMA: 1900 RPM, VOLTAGEM: 9,6 V, CARACTERÍSTICAS ADICIONAIS: MANDRIL DE 1/2", CONTROLE DE TORQUE , COMPONENTES: COM MALETA, ACESSÓRIOS, BATERIA, CARREGADOR BIVOLT , TIPO ALIMENTAÇÃO: BATERIA».
- Descrições originais preservadas (itens por descrição):
  - 103 itens — «PARAFUSADEIRA, TIPO PROFISSIONAL, VELOCIDADE REVERSÍVEL, ROTAÇÃO MÍNIMA: 600RPM, MÁXIMA: 1900 RPM, VOLTAGEM 9,6 V, CARACTERÍSTICAS ADICIONAIS MANDRIL DE 12", CONTROLE DE »
  - 56 itens — «PARAFUSADEIRA, TIPO: PROFISSIONAL , VELOCIDADE: REVERSÍVEL , ROTAÇÃO: MÍNIMA: 600 RPM, MÁXIMA: 1900 RPM, VOLTAGEM: 9,6 V, CARACTERÍSTICAS ADICIONAIS: MANDRIL DE 1/2", CON»
- Variante `V97b5c5a59170d48a` (103 itens): **DIVERGENTE** — medida_linear: oficial 12.7 MM × variante 304.8 MM | CARACTERÍSTICAS ADICIONAIS: oficial «MANDRIL DE 1/2", CONTROLE DE TORQUE» × variante «MANDRILDE12POL» → subproduto `CP1860.Aa27dfe0f`
- Variante `V40e417c610b6858c` (56 itens): **CONFORME_TEXTO_OFICIAL** → subproduto `CP1860.A6fb2f55f`
- Decisão da família: **AUTO_DESMEMBRAR**. compatibilidade: falta compatibilidade ou modelo no catálogo oficial | peca_reposicao: falta aplicacao ou referencia no catálogo oficial | variantes conformes e variantes divergentes do catálogo oficial, separáveis pela própria descrição
  - subproduto `CP1860.A6fb2f55f`: AUTO_INCONCLUSIVO  — critérios de catálogo não atendidos: compatibilidade: falta compatibilidade ou modelo no catálogo oficial; peca_reposicao: falta aplicacao ou referencia no catálogo oficial
  - subproduto `CP1860.Aa27dfe0f`: AUTO_INCONCLUSIVO  — diverge da especificação oficial; sem documentação independente que a sustente
- A(s) descrição(ões) divergente(s) (103 itens) não são tratadas como erro de digitação: divergem da especificação oficial e, sem documentação independente que as sustente, ficam inconclusivas; a família inteira não é aprovada.

## Reprodutibilidade

- Testes: 78 executados, 78 aprovados, 0 falhas, 0 erros (2026-11-25T13:35:05).
- Hash da cesta original `80cd46a7bac29464…`; variantes `6e58b570e4b97baa…`; snapshot do catálogo `c6127105dae24667…`; documentos `739f8d3107d0cccf…`; configuração `5cb31dbebd7b6734…`. Hashes completos em `manifesto.json`.
- Reprodução: `..\..\.venv\Scripts\python.exe scripts\executar.py auto-executar --prioridade P1` (reutiliza o cache; etapas com hashes válidos não são refeitas).

## Limitações

- Validação automática não garante ausência absoluta de erro.
- Equivalência textual não prova equivalência material.
- Equivalência de catálogo não prova conformidade individual das contratações; para isso só os itens S4.
- Ausência de documentação impede a aprovação (inconclusivo, nunca aprovação presumida).
- A amostra documental cobre poucas compras; PDFs sem camada de texto não são lidos (sem OCR).
- A seleção da cesta não resolve a endogeneidade na escolha do modo de disputa.
- A validação não elimina as falhas de pré-tendência identificadas no estudo econométrico, que permanece exploratório.

