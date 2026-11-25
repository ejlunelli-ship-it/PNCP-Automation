# Cesta padronizada de produtos (CATMAT × unidade) — PNCP

Gerado em 24/11/2026 19:57 pelo `executar.py` (código 1.0.0, regras de classificação 1.0.0). Protocolo: [`protocolo.md`](protocolo.md). Todos os números vêm de `saidas/`.

> **Escopo.** Construção e auditoria da cesta, sem estimar efeito de modo de disputa. Nenhuma etapa de seleção lê preço, desconto, valor estimado/homologado ou o modo de disputa: essas colunas nem são copiadas para o banco de trabalho (verificado por teste estático e por teste metamórfico: trocar preços e modos não muda a cesta).

## 1. Resultado em uma tabela

| Medida | Valor |
|---|---|
| Período coberto (data de publicação) | 2022-11-03 a 2026-04-17 |
| Universo: itens de material com CATMAT em pregão eletrônico | 4.471.621 |
| Universo: compras distintas / UASGs | 174.515 / 4.756 |
| Famílias CATMAT × unidade no universo | 273.330 |
| Famílias que passam os limiares iniciais | 18.103 |
| Produtos na cesta candidata (A + B) | 16248 (A = 10424, B = 5824) |
| Compras cobertas pela cesta | 129.906 (74,4% do universo; 39,7% dos pregões eletrônicos da fonte) |
| UASGs / CNPJs compradores na cesta | 4.587 / 2.534 |
| Cesta validada | PENDENTE: nenhuma revisão humana registrada |

A **cesta validada está vazia de propósito**: só um revisor humano pode aprovar produtos, preenchendo `saidas/formulario_revisao.csv` e rodando `validar_revisao.py`. A classe A indica apenas maior viabilidade de auditoria, não aprovação.

## 2. Base de dados e reprodutibilidade

| Item | Valor |
|---|---|
| Banco | `C:\Users\Absalão\Desktop\PNCP\PNCP(arquivos)\dados\pncp.db` |
| Tamanho | 16.048.373.760 bytes |
| Modificado em | 2026-11-10T17:03:45 |
| Contador de alterações SQLite | 151 |
| SHA-256 (64 MB iniciais + 64 MB finais) | `800e418245d8f21ddd1737ef20318b688e77846b2086c87a55c1388b223dc742` |
| Banco inalterado ao fim da leitura | sim (impressão digital idêntica) |
| Modo de abertura | `mode=ro` + `PRAGMA query_only`, uma transação de leitura (snapshot) por etapa |
| Python / SQLite | 3.13.17 / 3.50.4 |
| Banco de trabalho | `D:\cesta_padronizada_trabalho\trabalho.db` (fora do git; índices e tabelas intermediárias só nele) |
| Banco lido no diagnóstico | `D:\pncp.db` — o arquivo foi movido durante o estudo; tamanho, mtime, contador de alterações e SHA-256 iguais aos da extração (conferido pelo diagnóstico) |

Hashes de todos os arquivos de código e configuração: `registro_execucao.json`.

## 3. Esquema real e decisões de mapeamento

O mapeamento campo lógico → coluna está em `saidas/esquema/mapeamento_colunas.json`; a inspeção completa (tabelas, colunas, índices, chaves, amostras) em `saidas/esquema/esquema_inspecionado.json`. Decisões:

- **Compra** = `compras.numero_controle_pncp` (chave primária). `id_compra` não é único e **não** é usado para agrupar.
- **Item** = chave composta (`numero_controle_pncp`, `numero_item`). Os registros repetidos do mesmo item são colapsados; `registro_principal` não é usado, porque prioriza o valor do resultado (critério monetário).
- **UASG** = `compras.uasg` (unidade que realizou o pregão); `itens.uasg_item` é auditada contra ela. **CNPJ** (`orgao_cnpj`) é preservado, mas não define diversidade: várias UASGs compartilham CNPJ.
- **CATMAT** = `itens.cod_item_catalogo` com `material_ou_servico = 'M'`; códigos com `S` (CATSER) ficam fora.
- **Descrição**: no `pncp.db`, `descricao_resumida` da fonte `dados_abertos` é só o nome do item no catálogo (nível PDM). A descrição completa (`descricaodetalhada`) e o nome do PDM vêm dos CSVs brutos que originaram a carga (`dados/brutos/<ano>/itens_pregao_*.csv`, só leitura, SHA-256 por arquivo no banco de trabalho). A ligação é pela chave composta, com conferência de cardinalidade: 6.365.040 linhas nos brutos e no banco, divergências: nenhuma.
- **Data de referência** = `data_publicacao` (sempre presente); `data_abertura_proposta` só é auditada.
- **Fonte**: só `fonte = 'dados_abertos'` (Compras.gov.br) tem CATMAT e UASG. As compras `fonte = 'pncp'` (outras plataformas) entram só na contagem descritiva abaixo.

### Universo total do PNCP no banco (descritivo, não altera a cesta)

| Fonte | Modalidade | Situação | Compras | Publicação mín. | Publicação máx. |
|---|---|---|---|---|---|
| dados_abertos | Pregão - Eletrônico | — | 327.550 | 2022-11-03 | 2026-10-30 |
| dados_abertos | Pregão - Presencial | — | 619 | 2024-02-01 | 2026-10-28 |
| pncp | Pregão - Eletrônico | Anulada | 5.335 | 2023-01-31 | 2026-10-27 |
| pncp | Pregão - Eletrônico | Divulgada no PNCP | 719.093 | 2022-11-01 | 2026-10-31 |
| pncp | Pregão - Eletrônico | Revogada | 13.972 | 2022-11-07 | 2026-10-30 |
| pncp | Pregão - Eletrônico | Suspensa | 6.706 | 2022-11-21 | 2026-10-29 |
| pncp | Pregão - Presencial | Anulada | 122 | 2023-04-24 | 2026-10-05 |
| pncp | Pregão - Presencial | Divulgada no PNCP | 27.275 | 2022-11-04 | 2026-10-30 |
| pncp | Pregão - Presencial | Revogada | 332 | 2023-06-22 | 2026-10-20 |
| pncp | Pregão - Presencial | Suspensa | 59 | 2023-12-05 | 2026-10-14 |

| Fonte | Modalidade | M/S | Com código de catálogo | Linhas | Itens |
|---|---|---|---|---|---|
| dados_abertos | Pregão - Eletrônico | M | não | 1.062.130 | 1.061.224 |
| dados_abertos | Pregão - Eletrônico | M | sim | 4.473.215 | 4.472.791 |
| dados_abertos | Pregão - Eletrônico | S | não | 290.505 | 289.924 |
| dados_abertos | Pregão - Eletrônico | S | sim | 529.707 | 529.558 |
| dados_abertos | Pregão - Presencial | M | não | 5.843 | 5.843 |
| dados_abertos | Pregão - Presencial | M | sim | 1.522 | 1.522 |
| dados_abertos | Pregão - Presencial | S | não | 1.569 | 1.569 |
| dados_abertos | Pregão - Presencial | S | sim | 549 | 549 |
| pncp | Pregão - Eletrônico | M | não | 22.120.248 | 22.120.248 |
| pncp | Pregão - Eletrônico | S | não | 1.874.572 | 1.874.572 |
| pncp | Pregão - Presencial | M | não | 1.039.666 | 1.039.666 |
| pncp | Pregão - Presencial | S | não | 98.011 | 98.011 |

## 4. Cobertura temporal

Toda a cobertura disponível foi usada, inclusive 2026, sem corte em 2025: publicações de **2022-11-03** a **2026-04-17** (15 trimestres, 5 anos).

- Trimestres parcialmente observados: 2022T4 (2 meses: 2022-11, 2022-12), 2026T2 (1 meses: 2026-04).
- Anos parcialmente observados: 2022 (2 meses), 2026 (4 meses).
- Os meses mais recentes têm menos itens homologados (resultados ainda em andamento na data da carga).

### Ruptura da fonte em abril de 2026

O último item com CATMAT foi publicado em **2026-04-17**. A partir de meados de abril de 2026 a API Dados Abertos passou a entregar os itens **sem** `codItemCatalogo`, `codigoPdm`, `codigoClasse`, `nomePdm` e `descricaodetalhada` (conferido no banco, nos CSVs e nos JSONs brutos; o esquema dos arquivos não mudou e a `descricaoResumida` passou a trazer texto livre do órgão). Esses meses existem no banco, mas os itens não são identificáveis por CATMAT e ficam fora do universo pela etapa 3 do funil. A cobertura utilizável da cesta é, portanto, de 2022-11 a 2026-04; 2026 aparece só com 3,5 meses.

| Mês | Itens de material | Sem CATMAT | % sem CATMAT |
|---|---|---|---|
| 2025-10 | 194.229 | 5.269 | 2,7 |
| 2025-11 | 169.052 | 6.285 | 3,7 |
| 2025-12 | 124.794 | 6.207 | 5,0 |
| 2026-01 | 102.583 | 6.797 | 6,6 |
| 2026-02 | 104.812 | 6.980 | 6,7 |
| 2026-03 | 146.807 | 10.243 | 7,0 |
| 2026-04 | 136.326 | 55.431 | 40,7 |
| 2026-05 | 144.669 | 144.669 | 100,0 |
| 2026-06 | 133.401 | 133.401 | 100,0 |
| 2026-07 | 158.719 | 158.719 | 100,0 |
| 2026-08 | 162.933 | 162.933 | 100,0 |
| 2026-09 | 159.758 | 159.758 | 100,0 |
| 2026-10 | 147.453 | 147.453 | 100,0 |

Antes de 2026-04, 98.568 de 4.490.464 itens de material (2,2%) não têm CATMAT (itens não catalogados); o restante da perda da etapa 3 vem da ruptura.

## 5. Funil de seleção

| Etapa | Critério | Itens | Compras | UASGs | Itens perdidos | % perdido |
|---|---|---|---|---|---|---|
| 0_fonte_dados_abertos | Itens de compras da fonte dados_abertos (Compras.gov.br), todas as modalidades | 6.362.668 | 328.077 | 5.543 | — | — |
| 1_pregao_eletronico | Modalidade Pregão Eletrônico (qualquer modo de disputa) | 6.353.185 | 327.459 | 5.533 | 9.483 | 0,15 |
| 2_material | Item de material (M); serviços CATSER ficam de fora | 5.533.723 | 222.986 | 4.931 | 819.462 | 12,90 |
| 3_catmat_valido | Código de catálogo presente e numérico | 4.472.791 | 174.569 | 4.756 | 1.060.932 | 19,17 |
| 4_atributos_constantes | Registros repetidos do item com o mesmo CATMAT, natureza e unidade | 4.472.499 | 174.563 | 4.756 | 292 | 0,01 |
| 5_uasg_valida | UASG da compra presente e numérica (até 6 dígitos) | 4.471.621 | 174.515 | 4.756 | 878 | 0,02 |
| 6_data_valida | Data de publicação válida | 4.471.621 | 174.515 | 4.756 | 0 | 0,00 |
| 7_unidade_presente | Unidade de fornecimento presente | 4.471.621 | 174.515 | 4.756 | 0 | 0,00 |

Depois do funil: 273.330 famílias; 37.998 na triagem ampla (cenário mais brando da grade, classificadas por completo); 18.103 passam os limiares iniciais; 1 destas falham a qualidade cadastral; 16.248 produtos candidatos.

## 6. Critérios de triagem (registrados antes da seleção)

| Critério | Valor inicial |
|---|---|
| Compras distintas | ≥ 40 |
| UASGs distintas | ≥ 15 |
| Trimestres com compras | ≥ 6 |
| Anos com compras | ≥ 2 |
| Participação da UASG dominante | ≤ 25% |
| HHI institucional | ≤ 0,12 |
| Descrição completa (qualidade cadastral) | ≥ 95% dos itens |

São parâmetros de triagem, não limiares validados. A frequência é contada em **compras distintas**: várias linhas do mesmo produto na mesma compra contam uma compra (o número de itens é guardado à parte). HHI = soma dos quadrados das participações das UASGs nas compras da família; número efetivo de UASGs = 1/HHI.

## 7. Auditoria de homogeneidade das descrições

Todas as variantes de descrição das famílias da triagem ampla foram examinadas: **78.182 variantes** em `saidas/descricoes_variantes.csv` (100%: descrição original e normalizada, frequência, UASGs, período, frequência acumulada, expressões numéricas, unidades físicas, embalagem, indicadores, campos ausentes). Atributos extraídos por expressões regulares (`cesta/atributos.py`); nenhum modelo de linguagem ou classificador probabilístico foi usado.

Constatação central: a `descricaodetalhada` da API é, na quase totalidade, o **texto do próprio item do catálogo CATMAT** (PDM + atributos), com variações de formatação (`MATERIAL: METAL ,` × `MATERIAL METAL,`). Portanto a auditoria mede a especificidade e a estabilidade da descrição de catálogo, não as exigências adicionais que cada termo de referência possa ter feito — que não estão na base. Isso limita o significado da classe A.

| Classe | Passa limiares iniciais | Qualidade cadastral OK | Famílias |
|---|---|---|---|
| A | não | sim | 10.423 |
| A | sim | sim | 10.424 |
| B | não | não | 5 |
| B | não | sim | 7.220 |
| B | sim | não | 1 |
| B | sim | sim | 5.830 |
| C | não | sim | 2.247 |
| C | sim | sim | 1.848 |

Regras (determinísticas, `cesta/classificacao.py`, parâmetros em `parametros.json → homogeneidade`):

- **C (inadequado)**: descrição completa em < 50% dos itens; unidade ausente/irreconhecível; descrição dominante sem atributos além do nome do PDM; descrição genérica na maioria; nenhuma assinatura de atributos majoritária; peça cuja referência/aplicação define o objeto.
- **A (alta padronização observável)**: descrição dominante (por chave textual) em ≥ 90% dos itens; uma única assinatura de atributos; ≥ 2 atributos declarados; descrição completa ≥ 95%; sem indício de embalagem distinta, marca/modelo, compatibilidade ou aplicação; unidade sem alerta.
- **B (revisão especializada)**: os demais. Subtipos separados automaticamente por assinatura de atributos (só quando todas as variantes têm assinatura inequívoca com o mesmo conjunto de atributos) ficam no máximo em B.
- Categorias de cautela (`config/cautela.json`: medicamentos, combustíveis, toners, eletrônicos, informática, peças, químicos, perecíveis, logística, certificação) **não excluem**: geram alerta e pendência de revisão especializada.

## 8. Cesta candidata

`saidas/cesta_candidata.csv`: 16248 produtos (congelada em 2026-11-24T17:19:58, SHA-256 `80cd46a7bac29464…`). Os 40 com mais compras:

| ID | CATMAT | Unidade | Descrição representativa | Compras | UASGs | Trim. | HHI | Classe |
|---|---|---|---|---|---|---|---|---|
| CP10425 | 463770 | QUILOGRAMA | LEGUME IN NATURA, TIPO CENOURA | 2.974 | 1.137 | 15 | 0,0015 | B |
| CP0001 | 464393 | QUILOGRAMA | FRUTA, TIPO LARANJA PERA, APRESENTAÇÃO NATURAL | 2.796 | 1.035 | 15 | 0,0027 | A |
| CP10426 | 463754 | QUILOGRAMA | LEGUME IN NATURA, TIPO BATATA INGLESA | 2.759 | 1.048 | 14 | 0,0017 | B |
| CP0002 | 463938 | QUILOGRAMA | CONDIMENTO, TIPO ALHO, APRESENTAÇÃO NATURAL, ADICIONAL CABEÇA | 2.751 | 1.044 | 14 | 0,0029 | A |
| CP0003 | 463692 | EMBALAGEM 900 MILILITRO | ÓLEO VEGETAL COMESTÍVEL, TIPO PURO, ESPÉCIE VEGETAL SOJA, TIPO QUALIDADE TIPO1 | 2.720 | 922 | 14 | 0,0020 | A |
| CP10427 | 463767 | QUILOGRAMA | LEGUME IN NATURA, TIPO BETERRABA | 2.299 | 888 | 15 | 0,0021 | B |
| CP10428 | 463778 | QUILOGRAMA | LEGUME IN NATURA, TIPO CHUCHU VERDE | 2.084 | 793 | 15 | 0,0024 | B |
| CP0004 | 464401 | QUILOGRAMA | FRUTA, TIPO MAÇÃ FUJI, APRESENTAÇÃO NATURAL | 2.073 | 866 | 14 | 0,0022 | A |
| CP10429 | 463806 | QUILOGRAMA | LEGUME IN NATURA, TIPO TOMATE SALADA | 2.061 | 851 | 15 | 0,0020 | B |
| CP0005 | 464553 | EMBALAGEM 1 QUILOGRAMA | LEGUMINOSA, VARIEDADE FEIJÃO CARIOCA, TIPO TIPO 1 | 2.010 | 692 | 14 | 0,0039 | A |
| CP0006 | 464398 | QUILOGRAMA | FRUTA, TIPO LIMÃO TAITI, APRESENTAÇÃO NATURAL | 1.931 | 793 | 14 | 0,0045 | A |
| CP0007 | 464418 | QUILOGRAMA | FRUTA, TIPO MELANCIA VERMELHA, APRESENTAÇÃO NATURAL | 1.920 | 867 | 15 | 0,0021 | A |
| CP10430 | 463839 | QUILOGRAMA | VERDURA IN NATURA, TIPO REPOLHO BRANCO/ VERDE | 1.903 | 843 | 14 | 0,0020 | B |
| CP10431 | 463781 | QUILOGRAMA | LEGUME IN NATURA, TIPO CEBOLA BRANCA | 1.748 | 792 | 14 | 0,0025 | B |
| CP0008 | 447702 | QUILOGRAMA | EMBUTIDO, TIPO LINGUIÇA CALABRESA, TAMANHO GROSSA, TIPO PREPARAÇÃO DEFUMADA,ESTADO DE CONS | 1.747 | 551 | 13 | 0,0059 | A |
| CP0009 | 446633 | QUILOGRAMA | QUEIJO, ORIGEM DE VACA, VARIEDADE MUÇARELA, APRESENTAÇÃO PEÇA | 1.697 | 563 | 14 | 0,0032 | A |
| CP0010 | 445995 | CAIXA 1 LITRO | LEITE FLUIDO, ORIGEM DE VACA, TIPO A, TEOR GORDURA INTEGRAL, PROCESSAMENTO UHT | 1.652 | 707 | 15 | 0,0031 | A |
| CP0011 | 445485 | GARRAFAO 20 LITRO | ÁGUA MINERAL NATURAL, TIPO SEM GÁS, MATERIAL EMBALAGEM PLÁSTICO, TIPOEMBALAGEM RETORNÁVEL | 1.557 | 835 | 15 | 0,0030 | A |
| CP10432 | 484679 | UNIDADE | INSETICIDA, TIPO LÍQUIDO, APLICAÇÃO USO DOMÉSTICO | 1.548 | 929 | 13 | 0,0016 | B |
| CP10433 | 463809 | QUILOGRAMA | LEGUME IN NATURA, TIPO PIMENTÃO VERDE | 1.540 | 700 | 14 | 0,0028 | B |
| CP0012 | 458904 | EMBALAGEM 5 QUILOGRAMA | ARROZ BENEFICIADO, TIPO AGULHINHA/BRANCO, SUBGRUPO POLIDO, CLASSE LONGO FINO,QUALIDADE TIP | 1.539 | 489 | 14 | 0,0038 | A |
| CP0013 | 464552 | EMBALAGEM 1 QUILOGRAMA | LEGUMINOSA, VARIEDADE FEIJÃO PRETO, TIPO TIPO 1 | 1.527 | 544 | 14 | 0,0040 | A |
| CP10434 | 463753 | QUILOGRAMA | LEGUME IN NATURA, TIPO BATATA DOCE | 1.481 | 676 | 15 | 0,0025 | B |
| CP0014 | 447666 | QUILOGRAMA | CARNE DEFUMADA, TIPO CORTE TOUCINHO (BACON), TIPO ANIMAL SUÍNA, APRESENTAÇÃOEM MANTAS, EST | 1.469 | 541 | 14 | 0,0054 | A |
| CP10435 | 463796 | QUILOGRAMA | LEGUME IN NATURA, TIPO PEPINO | 1.466 | 631 | 14 | 0,0027 | B |
| CP0015 | 447636 | QUILOGRAMA | CARNE DE AVE IN NATURA, TIPO ANIMAL FRANGO, TIPO CORTE COXA E SOBRECOXA,APRESENTAÇÃO INTEI | 1.461 | 495 | 14 | 0,0037 | A |
| CP0016 | 460380 | QUILOGRAMA | PÃO, BASE DE FARINHA DE TRIGO REFINADA, TIPO TIPO FRANÇÊS/BRANCO/DE SAL | 1.455 | 654 | 14 | 0,0068 | A |
| CP10436 | 463782 | QUILOGRAMA | LEGUME IN NATURA, TIPO CEBOLA AMARELA | 1.436 | 494 | 14 | 0,0032 | B |
| CP0017 | 463937 | QUILOGRAMA | CONDIMENTO, TIPO URUCUM, APRESENTAÇÃO PÓ | 1.372 | 587 | 14 | 0,0030 | A |
| CP0018 | 464381 | QUILOGRAMA | FRUTA, TIPO BANANA PRATA/ BANANA BRANCA, APRESENTAÇÃO NATURAL | 1.368 | 701 | 15 | 0,0021 | A |
| CP0019 | 464405 | QUILOGRAMA | FRUTA, TIPO MAMÃO FORMOSA, APRESENTAÇÃO NATURAL | 1.350 | 669 | 15 | 0,0027 | A |
| CP0020 | 459670 | QUILOGRAMA | MASSA DE TOMATE, TIPO EXTRATO CONCENTRADO, COMPOSIÇÃO TRADICIONAL,APRESENTAÇÃO CREME | 1.347 | 589 | 14 | 0,0029 | A |
| CP10437 | 463795 | QUILOGRAMA | LEGUME IN NATURA, TIPO MANDIOCA/ AIPIM | 1.345 | 632 | 15 | 0,0027 | B |
| CP0021 | 447720 | QUILOGRAMA | EMBUTIDO, TIPO SALSICHA HOT DOG, TIPO PREPARAÇÃO COZIDA, ESTADO DE CONSERVAÇÃORESFRIADO(A) | 1.334 | 545 | 14 | 0,0077 | A |
| CP0022 | 445484 | GARRAFA 500 MILILITRO | ÁGUA MINERAL NATURAL, TIPO SEM GÁS, MATERIAL EMBALAGEM PLÁSTICO, TIPOEMBALAGEM DESCARTÁVEL | 1.271 | 677 | 14 | 0,0041 | A |
| CP0023 | 464380 | QUILOGRAMA | FRUTA, TIPO BANANA NANICA/ BANANA D'ÁGUA, APRESENTAÇÃO NATURAL | 1.269 | 452 | 14 | 0,0082 | A |
| CP0024 | 459586 | EMBALAGEM 100 GRAMA | FERMENTO, TIPO QUÍMICO, APRESENTAÇÃO PÓ | 1.238 | 494 | 14 | 0,0078 | A |
| CP0025 | 464374 | QUILOGRAMA | FRUTA, TIPO ABACAXI PÉROLA, APRESENTAÇÃO NATURAL | 1.223 | 595 | 15 | 0,0032 | A |
| CP0026 | 464400 | QUILOGRAMA | FRUTA, TIPO MAÇÃ GALA, APRESENTAÇÃO NATURAL | 1.151 | 462 | 13 | 0,0074 | A |
| CP0027 | 464553 | QUILOGRAMA | LEGUMINOSA, VARIEDADE FEIJÃO CARIOCA, TIPO TIPO 1 | 1.149 | 606 | 14 | 0,0033 | A |

Alertas mais frequentes na cesta candidata:

| Alerta | Produtos |
|---|---|
| cautela: medicamentos_materiais_medicos | 5615 |
| indicador 'aplicacao_variavel' | 3205 |
| cautela: alimentos_pereciveis | 2124 |
| indicador 'marca_modelo' | 1929 |
| cautela: equipamentos_eletronicos | 1625 |
| cautela: pecas_referencia_determinante | 1464 |
| cautela: certificacao_qualidade_variavel | 558 |
| cautela: produtos_quimicos | 538 |
| cautela: equipamentos_informatica | 496 |
| indicador 'compatibilidade' | 262 |
| cautela: logistica_relevante | 253 |
| indicador 'certificacao' | 217 |
| cautela: combustiveis_lubrificantes | 162 |
| 2 assinaturas de atributos distintas | 95 |
| descrição só com o nome do PDM | 92 |

Famílias que passaram os limiares iniciais mas ficaram fora (`familias_triadas_descartadas.csv`, 1868): principais motivos — classe C (1847); compras 25 < 40 (3); compras 26 < 40 (2); compras 22 < 40 (2); compras 21 < 40 (2); compras 17 < 40 (2); descrição completa em 93.9% < 95% (1); compras 38 < 40 (1).

**Tamanho da cesta.** Os limiares iniciais deixam passar muitos produtos porque cada CATMAT do Compras.gov.br já é um item de catálogo específico (PDM + atributos) e o universo tem 174 mil compras. A revisão humana de 16248 produtos é inviável em bloco. Uma priorização da revisão (por exemplo, começar pela classe A do cenário rigoroso, ou por grupos de material) é uma decisão de desenho que deve ser tomada e registrada antes de qualquer análise de preços; ela não foi aplicada aqui, e os limiares não foram alterados depois de ver a cesta.

## 9. Controle de qualidade e integridade

| Verificação | Afetados | Base | % | Excluídos | Produtos candidatos afetados | Critério |
|---|---|---|---|---|---|---|
| chaves de compra duplicadas | 0 | 328.169 compras | 0,000 | 0 | — | numero_controle_pncp é chave primária no banco; conferido de novo na extração (erro se > 0) |
| itens com mais de um registro (mesma chave composta) | 2.321 | 6.362.668 itens | 0,036 | 0 | — | colapsados em um item pela chave (numero_controle_pncp, numero_item); não se usa registro_principal |
| itens cujos registros divergem em CATMAT, natureza ou unidade | 312 | 6.362.668 itens | 0,005 | 312 | — | excluídos do universo (etapa 4 do funil): o produto do item não é identificável |
| junção item -> compra (N:1) | 0 | 6.362.668 itens | 0,000 | 0 | — | cada item tem exatamente uma compra; erro explícito se não |
| junção banco -> brutos (descrição detalhada) | 0 | 6.362.668 itens | 0,000 | 0 | — | mesmo número de registros por item, mesmo CATMAT; divergência de cardinalidade/CATMAT interrompe a execução; divergência só de unidade é auditada |
| itens com descrições detalhadas diferentes entre registros | 317 | 6.362.668 itens | 0,005 | 0 | 2 | mantida a menor (ordem lexicográfica); todas as variantes ficam em brutos_itens |
| itens sem compra correspondente (banco inteiro) | 0 | 6.365.040 linhas de item | 0,000 | 0 | — | contados na varredura do banco de origem; não entram no universo |
| compras sem itens (fonte do universo) | 92 | 328.169 compras | 0,028 | 0 | — | não geram itens; ficam fora naturalmente |
| CATMAT nulo em item de material (pregão eletrônico) | 1.060.932 | 5.533.723 itens | 19,172 | 1.060.932 | — | excluídos (etapa 3): sem código não há família |
| CATMAT presente mas inválido (não numérico/zero) | 0 | 5.533.723 itens | 0,000 | 0 | — | excluídos com os nulos |
| unidade de fornecimento ausente | 0 | 5.533.723 itens | 0,000 | 0 | — | excluídos (etapa 7) |
| unidade com alerta 'conteudo_zero' | 99.006 | 6.362.668 itens | 1,556 | 0 | 0 | mantidos como família própria, sem fusão; alerta na classificação |
| unidade com alerta 'formato_nao_reconhecido' | 148 | 6.362.668 itens | 0,002 | 0 | 0 | mantidos como família própria, sem fusão; alerta na classificação |
| descrição detalhada ausente (universo) | 225 | 4.471.621 itens | 0,005 | 0 | 89 | mantidos; reduzem share_desc_completa da família |
| descrição sem atributos além do nome do PDM (universo) | 236 | 4.471.621 itens | 0,005 | 0 | 92 | mantidos; contam como descrição incompleta |
| UASG da compra ausente ou inválida | 101 | 328.169 compras | 0,031 | 101 | — | excluídas (etapa 5) |
| data de publicação inválida | 0 | 328.169 compras | 0,000 | 0 | — | excluídas (etapa 6) |
| data de abertura incoerente com a publicação (> 1 ano depois ou > 30 dias antes) | 89 | 328.169 compras | 0,027 | 0 | — | mantidas; a referência temporal é a data de publicação |
| data de abertura inválida | 0 | 328.169 compras | 0,000 | 0 | — | mantidas (campo não usado na seleção) |
| quantidade nula, zero ou negativa (universo) | 2 | 4.471.621 itens | 0,000 | 0 | 0 | mantidos: a seleção conta compras, não quantidades |
| quantidade diferente entre registros do mesmo item | 32 | 6.362.668 itens | 0,001 | 0 | — | mantidos (quantidade não entra na seleção) |
| registros de item idênticos (todos os campos não monetários) | 347 | 6.362.668 itens | 0,005 | 0 | — | colapsados pela chave composta |
| CATMAT com grafias diferentes da mesma unidade normalizada | 90.996 | 143.666 CATMATs | 63,339 | 0 | — | unificadas pela normalização textual/aliases (sem conversão) |
| CATMAT com 'UNIDADE 0' e 'UNIDADE' (provável mudança de codificação) | 25.187 | 143.666 CATMATs | 17,532 | 0 | — | NÃO fundidas; famílias separadas e alerta |
| CATMAT com mais de uma descrição textual distinta | 2.599 | 143.666 CATMATs | 1,809 | 0 | — | auditadas uma a uma nas famílias triadas (descricoes_variantes.csv) |
| mesmo CATMAT e mesma embalagem com conteúdos diferentes (ex.: CAIXA 50 × CAIXA 100) | 17.332 | 143.666 CATMATs | 12,064 | 0 | — | mantidas como famílias distintas; nenhuma conversão |
| mesmo código de catálogo como material e como serviço | 39 | 145.891 códigos | 0,027 | 0 | — | regra: só material_ou_servico = 'M' entra; códigos coincidentes de CATSER ficam fora |
| UASG do item diferente da UASG da compra (universo) | 879 | 4.471.621 itens | 0,020 | 0 | 311 | mantidos; vale a UASG da compra (unidade que realizou o pregão) |
| UASG associada a mais de um CNPJ | 1.833 | 5.543 UASGs | 33,069 | 0 | — | mantidas; a UASG é a unidade de diversidade |
| CNPJ compartilhado por mais de uma UASG | 219 | 3.049 CNPJs | 7,183 | 0 | — | esperado (ex.: Justiça Eleitoral); UASGs preservadas como unidades distintas |
| id_compra repetido em mais de um numero_controle_pncp | 55 | 328.169 compras | 0,017 | 0 | — | NÃO agrupadas: a compra é o numero_controle_pncp (chave completa); ver contagem de itens idênticos |
| id_compra repetido com conjunto de itens idêntico (possível publicação duplicada) | 15 | 328.169 compras | 0,005 | 0 | 54 | NÃO deduplicadas (falta prova de que são o mesmo pregão; numero_controle_pncp distintos); impacto conferido |

Exemplos auditáveis de cada verificação: `saidas/auditoria_qualidade.json`. Inconsistências estruturais (chave de compra duplicada, item sem compra no universo, cardinalidade ou CATMAT divergente entre banco e brutos) interrompem a execução com `ErroEstrutural`; nenhuma ocorreu.

## 10. Cobertura da cesta candidata

| Medida | Valor |
|---|---|
| Produtos | 16248 |
| Compras | 129.906 |
| Itens | 2.137.650 |
| % das compras do universo CATMAT | 74,44 |
| % dos pregões eletrônicos da fonte | 39,67 |
| % dos itens do universo | 47,80 |
| UASGs / CNPJs | 4.587 / 2.534 |
| HHI das compras da cesta entre UASGs (nº efetivo) | 0,00189 (530) |
| Produtos por UASG (mediana; p90; máx.) | 83; 774; 4428 |
| UASGs por produto (mín.; mediana; máx.) | 15; 51; 1137 |
| Trimestres por produto (mín.; mediana; máx.) | 6; 12; 15 |

| Ano | Compras | Itens | UASGs | Produtos |
|---|---|---|---|---|
| 2022 | 50 | 340 | 32 | 294 |
| 2023 | 10.720 | 194.326 | 1.385 | 14986 |
| 2024 | 52.824 | 860.588 | 3.799 | 16167 |
| 2025 | 55.404 | 890.674 | 3.778 | 16194 |
| 2026 | 10.908 | 191.722 | 2.153 | 15794 |

Por trimestre e por grupo do catálogo: `cobertura_por_trimestre.csv`, `cobertura_por_grupo_material.csv`.

## 11. Sensibilidade da seleção

Grade fatorial pré-especificada (1.440 combinações) em `sensibilidade_grade.csv`; nível da família (sem a divisão em subtipos), classe técnica da triagem ampla. Nenhum cenário foi escolhido por maximizar observações; o inicial foi fixado antes.

| Cenário | Base | Compras≥ | UASGs≥ | Trim.≥ | Anos≥ | Dom.≤ | HHI≤ | Produtos | Compras | UASGs | Nº efetivo | Trim. médios |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| brando | licitados | 20 | 10 | 4 | 2 | 0.35 | 0.2 | 33897 | 146.609 | 4.663 | 501.5 | 10.74 |
| inicial | licitados | 40 | 15 | 6 | 2 | 0.25 | 0.12 | 16254 | 129.915 | 4.587 | 530.3 | 11.79 |
| rigoroso | licitados | 80 | 30 | 10 | 3 | 0.15 | 0.06 | 6216 | 104.151 | 4.375 | 573.6 | 12.66 |
| inicial_homologados | homologados | 40 | 15 | 6 | 2 | 0.25 | 0.12 | 12293 | 122.524 | 4.554 | 552.8 | 12.0 |

| A | B | Produtos A | Produtos B | Comuns | Só A | Só B | Jaccard |
|---|---|---|---|---|---|---|---|
| brando | inicial | 33897 | 16254 | 16254 | 17643 | 0 | 0.4795 |
| brando | rigoroso | 33897 | 6216 | 6216 | 27681 | 0 | 0.1834 |
| brando | inicial_homologados | 33897 | 12293 | 12293 | 21604 | 0 | 0.3627 |
| inicial | rigoroso | 16254 | 6216 | 6216 | 10038 | 0 | 0.3824 |
| inicial | inicial_homologados | 16254 | 12293 | 12290 | 3964 | 3 | 0.756 |
| rigoroso | inicial_homologados | 6216 | 12293 | 6170 | 46 | 6123 | 0.5 |

Variação de uma dimensão por vez em torno do cenário inicial:

| Dimensão alterada | Compras≥ | UASGs≥ | Trim.≥ | Anos≥ | Dom.≤ | HHI≤ | Produtos | Compras | UASGs |
|---|---|---|---|---|---|---|---|---|---|
| compras_min | 20 | 15 | 6 | 2 | 0.25 | 0.12 | 31685 | 144.294 | 4.658 |
| compras_min | 30 | 15 | 6 | 2 | 0.25 | 0.12 | 22209 | 137.155 | 4.622 |
| uasgs_min | 40 | 10 | 6 | 2 | 0.25 | 0.12 | 16260 | 129.936 | 4.587 |
| trimestres_min | 40 | 15 | 4 | 2 | 0.25 | 0.12 | 16426 | 130.476 | 4.592 |
| share_uasg_dominante_max | 40 | 15 | 6 | 2 | 0.15 | 0.12 | 15953 | 129.305 | 4.587 |
| hhi_max | 40 | 15 | 6 | 2 | 0.25 | 0.06 | 15913 | 129.016 | 4.587 |
| (inicial) | 40 | 15 | 6 | 2 | 0.25 | 0.12 | 16254 | 129.915 | 4.587 |
| hhi_max | 40 | 15 | 6 | 2 | 0.25 | 0.2 | 16254 | 129.915 | 4.587 |
| share_uasg_dominante_max | 40 | 15 | 6 | 2 | 0.35 | 0.12 | 16290 | 129.921 | 4.587 |
| anos_min | 40 | 15 | 6 | 3 | 0.25 | 0.12 | 16108 | 129.552 | 4.586 |
| trimestres_min | 40 | 15 | 8 | 2 | 0.25 | 0.12 | 15883 | 128.728 | 4.580 |
| trimestres_min | 40 | 15 | 10 | 2 | 0.25 | 0.12 | 14999 | 125.302 | 4.520 |
| uasgs_min | 40 | 20 | 6 | 2 | 0.25 | 0.12 | 16182 | 129.754 | 4.587 |
| uasgs_min | 40 | 30 | 6 | 2 | 0.25 | 0.12 | 15110 | 127.443 | 4.583 |
| compras_min | 60 | 15 | 6 | 2 | 0.25 | 0.12 | 9862 | 117.362 | 4.526 |
| compras_min | 80 | 15 | 6 | 2 | 0.25 | 0.12 | 6668 | 107.435 | 4.446 |

## 12. Seleção temporal e risco de viés

A cesta descritiva usa toda a cobertura. Selecionar pela frequência de todo o período pode condicionar a cesta a compras posteriores a mudanças de modo; para uma análise causal futura, a cesta deve ser re-formada num período de formação definido **antes** de olhar resultados (`sensibilidade.cesta_periodo_formacao`, parâmetro `temporal.periodo_formacao`, hoje `null` e não aplicado).

Recorrência (`recorrencia_temporal.csv`): dos 16248 produtos, 5260 já eram comuns na primeira janela (2022-11-01 a 2023-12-31; critério {'compras_min': 10, 'uasgs_min': 5}) e 14544 aparecem em todas as janelas.

## 13. Diagnóstico posterior de viabilidade causal (não seletivo)

Executado depois do congelamento (hash da cesta conferido antes e depois). Lê o modo de disputa só aqui; nenhum produto foi removido ou incluído por causa dele.

| Indicador | Valor |
|---|---|
| Compras da cesta: Aberto / Aberto-Fechado / Fechado-Aberto / outro | 80.862 / 48.150 / 894 / — |
| UASGs que usaram A e AF (compras da cesta) | 995 de 4.587 |
| Produtos comprados nos dois modos (≥ 5 compras em cada) | 16244 (16198) |
| Células produto × trimestre com A e AF (com ≥ 2 UASGs) | 149.279 de 191.636 (149.273) |
| Trocas de modo dentro da UASG (UASGs com alguma troca) | 5.173 (995) |
| Eventos potenciais (>= 3 compras da cesta só em A antes da primeira AF e >= 3 compras AF a partir dela) | 160 UASGs; por ano: {'2023': 21, '2024': 88, '2025': 46, '2026': 5} |
| Referência interna (item da cesta com >= 3 outras UASGs comprando o mesmo produto no mesmo trimestre) | 93,3% dos itens |
| Referência externa de preços | Não há fonte externa de preços no pncp.db (ex.: Painel de Preços); cobertura não avaliável aqui. |

## 14. Limitações

- Só o Compras.gov.br (fonte `dados_abertos`) entra: as demais plataformas não informam CATMAT no PNCP.
- Ruptura da fonte: depois de 2026-04-17 a API deixou de informar CATMAT; os meses de 2026-05 a 2026-10 não entram. Recuperá-los exige nova coleta de uma fonte que traga o código do catálogo.
- 1.060.932 itens de material sem código de catálogo ficam fora.
- A descrição disponível é a do catálogo; especificações adicionais dos termos de referência não estão na base. Equivalência material só pode ser confirmada na revisão humana.
- `UNIDADE 0` e `QUILOGRAMA 0` (provável codificação antiga) não foram fundidas com `UNIDADE`/`QUILOGRAMA`: famílias separadas.
- Frequência medida em itens **licitados** (qualquer situação); a frequência de **homologados** é reportada ao lado e como cenário de sensibilidade.
- Os limiares são de triagem; a sensibilidade mostra quanto a cesta depende deles.

## 15. Reprodução

```powershell
cd PNCP-Automation\analises\cesta_padronizada_20261124
..\..\.venv\Scripts\python.exe executar.py            # tudo (~1 h; lê o pncp.db só em mode=ro)
..\..\.venv\Scripts\python.exe -m unittest discover -s testes -v
..\..\.venv\Scripts\python.exe validar_revisao.py     # depois de preencher o formulário
```

