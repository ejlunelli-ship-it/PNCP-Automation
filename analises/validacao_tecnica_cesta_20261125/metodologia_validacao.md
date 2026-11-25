# Metodologia da validação técnica

Validação da cesta padronizada (`analises/cesta_padronizada_20261124/`). O critério central: **nenhuma família é
tecnicamente homogênea sem evidência verificável de que todas as suas observações representam o mesmo objeto de
contratação.** O sistema automático produz só evidências e formulários; a aprovação é sempre humana e documentada.

## 1. Entradas e chaves

| Entrada | Uso | Colunas lidas |
|---|---|---|
| `saidas/cesta_candidata.csv` (cesta) | produtos, classe A/B, frequência | as 16 de `config/mapa_colunas.json` (`id_candidato`, `produto`, `catmat`, `unidade_norm`, `classe_tecnica`, `classe`, `pdm`, `compras`, `itens`, `uasgs`, `orgaos`, …) |
| `saidas/descricoes_variantes.csv` | 100% das descrições originais | `familia`, `catmat`, `unidade_norm`, `descricao_original`, `itens`, `compras`, `uasgs`, `primeira`, `ultima`, `nome_pdm` |
| `saidas/sensibilidade_pertinencia.csv` | indicador do cenário rigoroso | `familia`, `rigoroso` |
| `saidas/formulario_revisao.csv` | só contagem de decisões anteriores (0) | `id_candidato`, coluna de decisão |
| `D:\cesta_padronizada_trabalho\trabalho.db` (mode=ro) | `desc_id`, descrição → produto, itens | `variantes`, `produto_map`, `universo_produto` (`chave`, `numero_item`, `produto`, `desc_id`, `uasg`, `n_descricoes_item`, `data_publicacao`) |
| `D:\pncp.db` | só impressão digital (não é aberto) | — |

- **Produto:** `produto` = `catmat|unidade_norm`; três candidatos têm sufixo `#hash` (subtipos separados pela cesta).
  Identificador estável: `id_candidato`. O CATMAT sozinho nunca é a chave.
- **Descrição → produto:** (`familia`, `descricao_original`) do CSV ↔ (`familia`, `descricao_original`) → `desc_id` do banco
  ↔ `produto_map (familia, desc_id) → produto`. A etapa `inspect` exige correspondência 1:1 nos dois sentidos, a mesma
  frequência de itens no CSV e no banco e a soma dos itens das variantes igual aos itens do produto; qualquer
  divergência interrompe a execução.
- **Proibido:** colunas cujo nome casa com `valor`, `preco`, `desconto`, `modo`, `disputa`, `licitante`, `lance`, `estimad`,
  `homolog`, `compras_A/AF/FA`, coeficientes, p-valores, intervalos, HonestDiD, dCDH; os arquivos
  `diagnostico_por_produto.csv`, `diagnostico_viabilidade.json` e a pasta do estudo econométrico. `compras_homologadas` e
  `itens_homologados` ficam fora por serem resultado do processo. Testes provam que mudar preços e modos não muda nada.

## 2. Priorização (ordem de revisão, não amostra)

P1 = classe A ∩ cenário rigoroso; P2 = A fora; P3 = B ∩ rigoroso; P4 = B fora; P5 = demais. Dentro da prioridade:
compras distintas (desc) e `id_candidato` (asc). Piloto = 100 primeiros P1. A relação integral dos 16.248 candidatos com
prioridade e ordem fica em `saidas/priorizacao_candidatos.csv`.

## 3. Normalização (conservadora)

Maiúsculas; acentos removidos; `²`→2, `×`→X, `Ø`→DIÂMETRO; espaços colapsados; `:` e `;` tratados como pontuação
irrelevante; milhar pt-BR (`1.000` → `1000`, inclusive antes de vírgula-separador) e vírgula decimal (`0,5` → `0.5`);
`40X 30` → `40 X 30`; número colado à unidade separado (`500ML` → `500 ML`); grafias de unidade **só depois de número**
(`LITROS`→`L`, `GRAMAS`→`G`, `MILÍMETROS`→`MM`, `"`→`POL`…); abreviações inequívocas (`C/`→COM, `S/`→SEM, `P/`→PARA,
`PCT`→PACOTE, `APROX`, `DIAM`, `LARG`, `COMPR`, `QTDE`, `REF`). **Nenhuma grandeza é convertida no texto e nenhum
número é removido**: `1 L` continua `1 L`. A chave compacta (sem espaços e pontuação, com `|` entre grupos de dígitos)
detecta diferenças só de espaçamento sem confundir `7, 28` com `72, 8`.

## 4. Extração de atributos

Regras em `config/regras_atributos.json`, aplicadas ao texto normalizado, cada atributo com valor canônico e trecho de
origem (`auditoria_atributos.csv`):

- **Grandezas, sempre separadas:** volume (mL), massa (mg), dosagem (mg, só em medicamento), dosagem em UI/U/mEq,
  concentração % / massa-volume (mg/mL; `250 MG/5 ML` = 50 mg/mL) / massa-massa / UI-volume / outras (mEq/mL, mcg/dose,
  sem conversão), gramatura (g/m²), comprimento, largura, altura, diâmetro, espessura, profundidade (mm; polegada = 25,4 mm,
  com frações), dimensões AxB(xC), medida linear sem rótulo, capacidade por grandeza, potência (W), tensão, número de folhas,
  quantidade por embalagem, número de unidades, formato de papel. Conversão só entre unidades da mesma grandeza, por fator
  exato (`0,5 L` = `500 ML`; `1 L` ≠ `500 ML`).
- **Categóricos:** cor (só em segmento com COR), material, composição, forma farmacêutica (só em medicamento, com
  hierarquia: `SUSPENSAO_INJETAVEL` implica `INJETAVEL` e `SUSPENSAO`), esterilidade, tipo de uso, originalidade
  (original/remanufaturado/compatível, só em toner/peça/eletrônico), classe de qualidade, certificação, norma técnica,
  compatibilidade, modelo, referência técnica, tipo de embalagem.
- **Atributos declarados do catálogo:** pares `ATRIBUTO VALOR`. As chaves são aprendidas das descrições que trazem
  `ATRIBUTO:` (1.184 chaves com ≥ 3 ocorrências; `vocabulario_chaves_declaradas.json`); o mesmo texto sem `:` é segmentado
  pelas chaves do próprio produto e depois pelas globais (vence a mais longa); valores comparados pela chave compacta.
- **Riscos** (avaliação especializada): medicamento, material médico, produto químico, toner/cartucho, peça de
  reposição, equipamento eletrônico, compatibilidade, certificação regulada — por palavra inteira, cautela da cesta ou
  classe do catálogo. Só sinalizam.

## 5. Auditoria de homogeneidade (100% das variantes)

Para cada produto, compara os conjuntos de valores de cada atributo entre as variantes com descrição:

- valores **disjuntos** (ex.: 100 × 500 unidades; 70% × 96%; 75 × 90 g/m²; comprimido × solução injetável; azul × vermelho;
  12″ × ½″) → **conflito OBJETIVO**; certificação e norma técnica divergentes → a examinar;
- um conjunto contido no outro (informação parcial, texto colado na fonte) → **a examinar**;
- atributo declarado com valores que diferem só por espaço dentro de número (`45~5 0` × `45~50`) → **a examinar**;
- números do texto que diferem entre variantes, nome do item diferente, notas de catálogo (`VER NOVO PDM`), variantes
  sem descrição, itens com mais de uma descrição bruta → alertas.

Status automático (precedência): `CHAVE_INVALIDA` > `CONFLITO_OBJETIVO_EXIGE_DESMEMBRAMENTO` > `ATRIBUTOS_INSUFICIENTES`
> `DIVERGENCIA_A_EXAMINAR` > `SEM_DIVERGENCIA_DETECTADA`. **Todos saem `PENDENTE`.** "Atributos de consenso" (valor
único comum às variantes) viram os atributos essenciais que a especificação canônica precisa conter.

**Desmembramento:** só quando cada variante tem exatamente um valor em cada atributo em conflito, nenhuma variante é
sem descrição e nenhum item tem descrição ambígua. Cada grupo de valores vira um subproduto com identificador estável
`id_candidato.<hash dos valores>`, revisado à parte. Nunca se separa por preço.

## 6. Formulários e conclusão

`revisao_produtos.csv` (produtos e subprodutos) e `revisao_variantes.csv` (uma linha por variante normalizada) têm
colunas imutáveis copiadas dos arquivos-base e colunas editáveis. `concluir`:

1. confere SHA-256 dos arquivos-base, das entradas e da configuração contra `manifesto.json` (mudança → nova versão);
2. rejeita cabeçalho alterado, ID duplicado/ausente/novo, campo imutável alterado, decisão fora da lista, versão diferente;
3. avalia cada registro. `VALIDADO` exige: APROVAR; especificação `NOME | ATRIBUTO: VALOR | …` com os atributos
   essenciais; fundamentação ≥ 40 caracteres e não genérica; fonte verificável (`TERMO_REFERENCIA`/`EDITAL`/
   `DOCUMENTO_COMPRA` com número de controle PNCP ou URL, `CATMAT` = código do produto, `PDM` = código do produto,
   `NORMA`, `FABRICANTE`/`CATALOGO` com URL); revisor do cadastro `config/revisores.csv`; data ISO entre a preparação e
   hoje; **todas** as variantes revisadas e EQUIVALENTE, cada uma documentada; nenhum conflito objetivo (produto em
   conflito só pode ser DESMEMBRADO ou REJEITADO); alertas/riscos com resolução documentada; consulta a edital indicada →
   edital, termo de referência ou documento de compra entre as fontes; atributos insuficientes → ≥ 2 atributos e fonte
   além do CATMAT/PDM; subproduto só com o produto de origem DESMEMBRADO; com `--exigir-dupla-revisao`, aprovador final
   diferente dos revisores das variantes.
4. grava `resultado_revisao.csv`, `resultado_validacao.json` e, **só se houver VALIDADO**, `cesta_validada.csv` e
   `integracao_econometria/`. Sem aprovações, nenhum CSV de cesta é criado.

A assinatura textual do revisor não é certificação digital; a identificação e a qualificação são controladas pelo
cadastro da pesquisa.

## 7. Registro de alterações das regras

Todas feitas em 25/11/2026, depois de examinar, um a um, os 18 conflitos objetivos da primeira execução do P1 (só o
texto das descrições; nenhum preço ou modo foi consultado). Cada correção tem teste de regressão (`Regras.test_R1…R6`).
Nenhum dado de base foi editado.

| Versão | Mudança | Motivo (caso examinado) | P1: conflitos / a examinar / sem divergência |
|---|---|---|---|
| 1.0.0 | primeira execução | — | 18 / 188 / 3.916 |
| 1.1.0 | `CX` deixa de virar `CAIXA` | `TAMANHO (CX L) 297 X 210 MM` × `(C X L)`: comprimento × largura (8 papéis) | |
| 1.1.0 | milhar reconhecido antes de vírgula-separador; `1.000,5` = 1000.5 | `EPINEFRINA 1:100.000,` × `1:100000` (5 anestésicos); `NBR 14.865` × `14865` | |
| 1.1.0 | frações de polegada (`1/2 POL` = 12,7 mm) | `1/2 POL` era lido como `2 POL` | |
| 1.1.0 | chave declarada colada ao valor é separada antes da extração (chaves ≥ 7 letras e `TIPO`) | `FORMA FARMACEUTICASUSPENSAO INJETAVEL` | |
| 1.1.0 | hierarquia de formas farmacêuticas (`INJETAVEL` genérico ⊂ `SUSPENSAO_INJETAVEL`) | `INJETAVEL` sozinho virava `SOLUCAO_INJETAVEL` | |
| 1.1.0 | valor declarado que difere só por espaço dentro de número → a examinar | `VERTICAL 45~5 0` × `45~50`; `POE4 8` × `POE48` | 1 / 143 / 3.978 |
| 1.2.0 | riscos por palavra inteira; `medicamento` só por termos farmacêuticos ou classe 6505 (a cautela `medicamentos_materiais_medicos` da cesta só marca material médico) | `MONITOR` em MONITORAÇÃO, `ISO` em `ISOL.SR`, materiais médicos tratados como fármacos | 1 / 143 / 3.978 |
| 1.2.0 | concentrações em mEq/mL, U, mcg/dose (sem conversão) | `2 MEQ/ML`, `15 U`, `32 MCG/DOSE` | 1 / 143 / 3.978 |

O conflito que restou (`CP1860`, parafusadeira, mandril `12 POL` × `1/2 POL`) é uma divergência real do texto: fica
como conflito objetivo, desmembrável em dois subprodutos.
