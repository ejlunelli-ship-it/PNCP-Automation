# Metodologia da validação técnica automática (validador 2.0.0)

Este é um modo operacional **novo**, que funciona sem revisores humanos.

- Ele lê a auditoria congelada da rodada P1 (versão `40caddd4e39c2c6d`), sem regerá-la.
- Consulta o catálogo oficial e uma amostra de documentos de contratação.
- Atribui a cada família um status próprio, `AUTO_*`.
- Não preenche nem substitui os formulários de revisão humana: `preparar` / `concluir` continuam funcionando como antes.
- Não cria `cesta_validada.csv`.

> Princípio: aprovar automaticamente **só** quando a equivalência técnica for demonstrável por atributos objetivos e
> evidência verificável. Na falta disso, o resultado é `AUTO_INCONCLUSIVO`, sem intervenção humana e sem aprovação
> presumida. A ausência de conflito, sozinha, não prova homogeneidade.

## 1. Entradas e independência

Colunas lidas (lista branca em `config/validacao_automatica.json`, registro em `saidas/auto_P1_20261125/colunas_lidas.json`):
- **Base P1 congelada:** produtos, variantes e descrições originais.
- **Banco da cesta** (mode=ro):
  - `universo_produto`: `chave`, `numero_item`, `produto`, `desc_id`, `uasg`, `data_publicacao`, `ano`, `trimestre`, `n_descricoes_item`;
  - `compras_base`: `chave`, `uf`;
  - `unidades`: leitura da unidade de fornecimento.

O que fica de fora:
- **Nunca entram:** preço, valor estimado, desconto, modo de disputa, licitantes, coeficientes, valores-p, intervalos,
  DiD/HonestDiD e órgãos com efeito. As colunas descartadas também ficam registradas.
- **Critérios fora da decisão:** o número de eventos de troca de modo e o suporte econométrico.
- **APIs consultadas:** nenhum endpoint de itens ou resultados (que trazem valores).

## 2. Fontes documentais

| Nível | Fonte | Uso |
|---|---|---|
| 1 | API pública de dados abertos do Compras.gov.br: `4_consultarItemMaterial`, `7_consultarMaterialCaracteristicas`, `6_consultarMaterialUnidadeFornecimento` (endpoints conferidos na documentação OpenAPI `https://dadosabertos.compras.gov.br/v3/api-docs` e por consulta real) | descrição oficial, situação, PDM, classe; características estruturadas (nome, valor, unidade, códigos); unidades de fornecimento do PDM |
| 2 | API pública do PNCP `.../orgaos/{cnpj}/compras/{ano}/{seq}/arquivos` e os arquivos listados | Termo de Referência e Edital da compra; texto extraído (PDF, DOCX, ZIP) |
| 3 | normas, reguladores, fabricantes | **não usados**: nenhuma fonte desse nível foi tomada como prova |

**Acesso controlado** (`acesso_fontes.py`):
- só hosts permitidos, com 3 conexões e intervalo mínimo de 0,2 s;
- até 4 tentativas, respeitando `Retry-After`;
- respostas maiores que 30 MB não são baixadas.

**Cache imutável:**
- o conteúdo fica em `conteudo/<sha256>`, deduplicado;
- o histórico de cada URL guarda a data, o HTTP e o SHA-256 de cada consulta;
- uma consulta bem-sucedida é reutilizada, e a atualização cria uma versão nova sem apagar a antiga;
- falhas (HTTP 429 ou 5xx, rede) são registradas e consultadas de novo na passada seguinte;
- a validação usa o **snapshot** gravado em `estado/snapshot_catalogo.json`.

**Conteúdo externo:** é tratado como dado não confiável.
- Só é lido como texto e por expressões regulares.
- Nada é executado e nenhum link é seguido.
- Arquivos ZIP são lidos em memória.
- PDFs sem camada de texto ficam como "sem texto" (não há OCR).

## 3. Especificação canônica

A especificação canônica é construída a partir das **características oficiais do CATMAT**, nunca da descrição mais
frequente. Cada atributo carrega:
- a evidência: código da característica e do valor, URL e SHA-256 da resposta;
- as grandezas extraídas pelo Extrator 1.2.0 (as mesmas regras e regressões da auditoria);
- valor original, unidade original, valor normalizado, unidade canônica e regra de conversão (`atributos_extraidos.csv`).

## 4. Comparação de cada variante com o catálogo (`comparar_especificacoes.py`)

1. **Sem descrição** → `SEM_DESCRICAO`. Vira pendência e ressalva, nunca é aprovada como S1.
2. **Texto oficial a menos de espaços** → `CONFORME_TEXTO_OFICIAL`.
   - Toda a pontuação precisa coincidir: `1 2 ≠ 1/2` e `72, 8 ≠ 7, 28`. É assim que se resolvem as palavras coladas
     da fonte (`TIPOEMBALAGEM`).
   - Se o espaço removido estava **dentro** de um número oficial (`45~5 0` × `45~50`), o status é
     `CONFORME_COM_CORRECAO_TIPOGRAFICA` e a família cai para S2.
3. **Senão, atributo por atributo:**
   - **Característica com grandeza:** exige a mesma grandeza com o mesmo valor canônico. `500 ML` = `0,5 L`, mas `500 ML`
     ≠ `500 G` e ≠ `5 L`; o número solto não basta.
   - **Demais características:** exigem o valor oficial (chave compacta, que preserva `/`, `.` e `%`) no texto da variante.
   - **Divergência material:** grandezas disjuntas (concentração, dosagem, gramatura, quantidade por embalagem, polegada,
     forma farmacêutica, originalidade, compatibilidade…) ou, no atributo declarado com a mesma chave, números
     diferentes → `DIVERGENTE`.
   - **Divergência só de texto** no atributo declarado → `DIVERGENCIA_TEXTUAL`.
   - **Falta algum valor oficial** → `PARCIAL`.

Similaridade lexical não aprova nada, e nenhum escore supera um conflito.

## 5. Perfis por categoria (`avaliar_evidencias.py`)

As categorias de risco vêm da auditoria 1.2.0 congelada: medicamento, material médico, químico, eletrônico, peça,
compatibilidade, toner, certificação. Cada uma exige grupos de atributos críticos no catálogo **oficial** (pelo nome da
característica ou por grandeza extraída):

| Categoria | Grupos críticos |
|---|---|
| medicamento | concentração/dosagem; forma/apresentação |
| material médico | material/tipo; medida/capacidade |
| químico | composição/concentração/pureza |
| eletrônico | parâmetro elétrico/capacidade |
| peça | aplicação/referência/medida |
| compatibilidade e toner | compatibilidade/modelo |
| geral | ≥ 2 características oficiais com valor |

Duas regras de aplicabilidade:
- quando o produto é medicamento, o perfil de material médico não se aplica;
- no medicamento, o PDM (princípio ativo) conta no mínimo geral, e a unidade de fornecimento **oficial** do PDM
  (COMPRIMIDO, AMPOLA…) informa a apresentação.

Sem o grupo crítico, o produto fica `AUTO_INCONCLUSIVO`. As marcas de risco herdadas são ruidosas (por exemplo,
"XAROPE" num refrigerante). O efeito disso é só conservador: inconclusivo, nunca aprovação.

A unidade de fornecimento é conferida com as unidades oficiais do PDM: nome e, quando houver, capacidade e unidade de
medida. Quando não é reconhecida, vira ressalva (S2).

## 6. Decisão da família (`decidir_validacao.py`)

**Critérios cumulativos** (`auditoria_decisoes.csv`, colunas `c01`…`c12`):
1. identificação inequívoca;
2. CATMAT existente no catálogo;
3. unidade interpretável;
4. especificação oficial suficiente e não contraditória: toda característica oficial precisa aparecer na descrição
   oficial do item; se não aparecer, há **fontes contraditórias**;
5. atributos essenciais da categoria;
6. evidências com SHA-256;
7. 100% das variantes comparadas e conformes;
8. nenhum conflito material;
9. nenhuma ambiguidade crítica (variante parcial ou com divergência textual);
10. regras versionadas;
11. rastreabilidade;
12. fontes preservadas em cache.

**Status:**

| Status | Quando |
|---|---|
| `AUTO_ERRO_DADOS` | chave inválida, CATMAT inexistente ou sem variantes |
| `AUTO_DESMEMBRAR` | variantes conformes e divergentes, separáveis pela própria descrição. O subproduto conforme é avaliado como uma família; os divergentes ficam inconclusivos (divergem do catálogo e não há documentação independente que os sustente) |
| `AUTO_DIVERGENTE` | variantes materialmente incompatíveis entre si, sem grupo conforme ao catálogo |
| `AUTO_INCONCLUSIVO` | qualquer critério não demonstrado, inclusive fonte indisponível, ou todas as variantes divergentes do catálogo de um mesmo modo (dados × catálogo contraditórios) |
| `AUTO_VALIDADO_CATALOGO` (**S1**) | todos os critérios, sem ressalvas |
| `AUTO_VALIDADO_CATALOGO_COM_RESSALVA` (**S2**) | todos os critérios, com ressalva não crítica: variante sem descrição, correção tipográfica, unidade não reconhecida no PDM, item ou característica inativo, item com descrição bruta ambígua, PDM divergente |

S2 **não** é validação sem qualificação.

## 7. Itens (nível da contratação)

O item é ligado à variante pela **própria** descrição (`desc_id`). Status:

| Status do item | Quando |
|---|---|
| `AUTO_VALIDADO_ITEM` (S4) | a família ou o subproduto está validado e o Termo de Referência ou Edital da compra traz o CATMAT com **todos** os valores oficiais na janela de ±1.500 caracteres, sem grandeza divergente na janela de ±300 |
| `ITEM_SEM_VALIDACAO_DOCUMENTAL` | família aprovada, mas sem documento examinado ou com documento insuficiente |
| `ITEM_SEM_CLASSIFICACAO` | variante não atribuível no desmembramento, ou item com mais de uma descrição bruta |
| `ITEM_NAO_ELEGIVEL` | família não aprovada |

A aprovação do catálogo **não** aprova as contratações.

**Amostra documental:**
- uma compra por família, para 400 famílias;
- famílias e compras ordenadas por SHA-256 com semente fixa;
- independente da classificação e de qualquer variável econômica.

## 8. Saídas, reprodução e limites

As saídas ficam em `saidas/auto_P1_20261125/`; o relatório lista cada uma. A integração com o estudo econométrico é
separada, em `integracao_econometria_automatica/`, sem `cesta_validada.csv`.

```powershell
cd PNCP-Automation\analises\validacao_tecnica_cesta_20261125
..\..\.venv\Scripts\python.exe scripts\executar.py auto-executar --prioridade P1    # retoma do cache e dos checkpoints
..\..\.venv\Scripts\python.exe scripts\executar.py testes                            # 39 testes antigos + testes do modo automático
```

**Limites:**
- a validação automática não garante ausência de erro;
- equivalência textual não prova equivalência material;
- equivalência de catálogo não prova a conformidade de cada contratação;
- a falta de documentação impede a aprovação;
- a cesta não resolve a endogeneidade da escolha do modo nem as falhas de pré-tendência do estudo econométrico, que
  continua exploratório.
