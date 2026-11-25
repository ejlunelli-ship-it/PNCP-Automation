# Validação técnica da cesta padronizada — relatório

Gerado em 2026-11-25T11:23:20 por `scripts/executar.py relatorio` (versão 1.0.0). Protocolo: [`protocolo_validacao.md`](protocolo_validacao.md); método: [`metodologia_validacao.md`](metodologia_validacao.md); conclusão: [`conclusao.md`](conclusao.md).

> **Nenhum produto está validado.** A auditoria automática examinou 100% das descrições dos candidatos P1 e preparou os formulários; nenhuma decisão humana documentada foi registrada, então `cesta_validada.csv` **não foi criada** e a prioridade P1 **não** equivale a aprovação. A auditoria não leu preço, valor, desconto, modo de disputa, licitantes nem resultado econométrico.

## Entradas e identificação dos produtos

| Conjunto | Produtos |
|---|---|
| Cesta candidata | 16.248 |
| Classe A | 10.424 |
| Classe B | 5.824 |
| Famílias do cenário rigoroso | 6.216 |
| Candidatos nessas famílias | 6.217 |
| **P1 = A ∩ rigoroso** | **4.122** |
| P2 = A fora do rigoroso | 6.302 |
| P3 = B ∩ rigoroso | 2.095 |
| P4 = B fora do rigoroso | 3.729 |
| P5 = demais | 0 |

- Chave do produto: `produto` = `catmat|unidade_norm` (com sufixo `#hash` em 3 subtipos já separados pela cesta); identificador estável: `id_candidato`. Descrição → produto: (`familia`, `descricao_original`) ↔ `desc_id` ↔ `produto_map` do banco de trabalho da cesta (mode=ro). A inspeção conferiu unicidade, cobertura nos dois sentidos e a soma dos itens por produto (`saidas/inspecao_entradas.json`).
- Colunas ignoradas por conterem informação econômica ou de resultado: `compras_homologadas`, `itens_homologados`. `diagnostico_por_produto.csv` (contagens por modo) e a pasta do estudo econométrico não são abertos.
- Bancos de origem (cesta e `pncp.db` em D:) conferidos antes e depois de cada etapa: inalterados.

## 1–3. Candidatos, variantes e frequências (P1)

| Medida | Valor |
|---|---|
| Candidatos P1 avaliados | 4.122 |
| Piloto (100 primeiros P1 por compras) | 100 |
| Descrições originais distintas examinadas (100%) | 8.324 |
| Variantes normalizadas (decisão por variante) | 6.282 |
| Itens cobertos | 933.477 |
| Produtos com 1 / 2 / 3+ variantes | 1.995 / 2.099 / 28 |
| Máximo de variantes num produto | 4 |
| Variantes com 1 item / com até 5 itens (raras, mantidas) | 53 / 65 |
| Variantes sem descrição (equivalência só pelo código) | 53 |
| Mediana de itens por variante | 98 |

As variantes normalizadas juntam descrições que diferem só em maiúsculas, acentos, espaços, ':' e grafia de unidades; a correspondência com cada descrição original está em `descricoes_originais.csv`.

## 4–8. Resultado da auditoria automática (P1)

| Status automático | Produtos | % |
|---|---|---|
| SEM_DIVERGENCIA_DETECTADA | 3.978 | 96,5% |
| DIVERGENCIA_A_EXAMINAR | 143 | 3,5% |
| CONFLITO_OBJETIVO_EXIGE_DESMEMBRAMENTO | 1 | 0,0% |

- **Atributos técnicos insuficientes** (status `ATRIBUTOS_INSUFICIENTES`): 0. Produtos sem nenhum atributo tipado (só pares 'ATRIBUTO VALOR' do catálogo): 896.
- **Conflitos objetivos:** 1 em 1 produto(s); por atributo: {'medida_linear': 1}.
  - `CP1860` 444251|UNIDADE — PARAFUSADEIRA, TIPO PROFISSIONAL, VELOCIDADE REVERSÍVEL, ROTAÇÃO MÍNIMA: 600RPM, MÁXIMA: 1…: [OBJETIVO] medida_linear: 12.7 MM (56 itens) vs 304.8 MM (103 itens); desmembrável: sim (CP1860.703d5630;CP1860.af150be5).
- **Divergências a examinar** (não objetivas: informação parcial, texto colado, espaço dentro de número, nome do item): 143 produtos; tipos mais frequentes: material (45), forma_farmaceutica (18), declarado (15), medida_linear (4), numeros_no_texto (3), cor (2), tensao (2).
- **Desmembramento:** 1 produto(s) com subprodutos reproduzíveis propostos (2 subprodutos). Nenhum subproduto é aprovado sem revisão própria.
- **Consulta a editais/termos de referência indicada:** 919 produtos (22,3%); motivos: risco (822), medicamento sem concentração/dosagem identificada (64), variantes sem descrição (53), números divergentes no texto (3).
- **Avaliação especializada indicada:** 2.478 produtos; categorias: material_medico (1714), medicamento (859), equipamento_eletronico (456), peca_reposicao (420), compatibilidade (406), produto_quimico (307), certificacao_regulada (97).

Regras na versão 1.2.0 (normalização 1.1.0, extração 1.2.0, auditoria 1.2.0). As correções feitas depois do exame dos falsos conflitos da primeira execução, cada uma com teste de regressão, estão em `metodologia_validacao.md` (Registro de alterações das regras).


## 9–11. Aprovação e cobertura

| Medida | Valor |
|---|---|
| Produtos aprovados (VALIDADO) | 0 |
| Subprodutos aprovados | 0 |
| Rejeitados | 0 |
| Pendentes | 4.122 |
| Bloqueados (tentativa de aprovação sem requisitos) | 0 |
| Variantes com decisão | 0 de 6.282 |
| Revisores cadastrados | 0 |
| Cobertura dos aprovados em compras | — |
| `cesta_validada.csv` | não criada (nenhum VALIDADO) |

Para referência, os 4.122 candidatos P1 somam 796.598 pares produto × compra; a cobertura dos aprovados será calculada pelo mesmo relatório quando houver aprovações.

## 12. Testes

`python scripts/executar.py testes` em 2026-11-25T11:23:15: **39 testes executados, 39 aprovados, 0 falhas, 0 erros** (Python 3.13.17). Os 25 testes obrigatórios são `test_01`…`test_25` de `testes/test_validacao.py`; os demais são regressões das correções de regra e verificações extras (decisão inválida, não sobrescrita, mudança de entrada, mapeamento com coluna econômica, código sem campos econômicos, rejeição documentada, especificação sem atributo essencial).

## 13. Limitações do sistema automático

- A extração é por regras sobre o texto do catálogo; texto colado na fonte ('ARAMEACO', 'SOLUCAOINJETAVEL') ou números partidos por quebra de linha ('5 0') não são corrigidos: viram divergência **a examinar**, nunca equivalência automática.
- Atributos ausentes numa variante (informação parcial) não são conflito objetivo; a revisão humana decide se a variante é equivalente.
- 'Sem divergência detectada' só quer dizer que as descrições do catálogo coincidem; não prova que todas as compras contrataram o mesmo objeto (o edital pode exigir marca, prazo, garantia, embalagem ou entrega diferentes).
- Variantes sem descrição (item sem `descricaodetalhada` na fonte) só podem ser ligadas pelo código CATMAT.
- Os riscos (medicamento, peça, compatibilidade…) são sinalizações por palavras, cautelas da cesta e classe do catálogo; não substituem avaliação especializada.
- A revisão técnica ocorre depois de resultados econométricos exploratórios já terem sido vistos; o procedimento protege a independência (formulários sem preço/modo, ordem só por compras), mas isso não torna o estudo retrospectivamente confirmatório.
- Mesmo um produto homogêneo pode ter preços diferentes por quantidade, frete, prazo, garantia, marca, logística, qualidade contratual e mercado regional; a validação técnica melhora a comparabilidade do objeto, mas não resolve a endogeneidade da escolha do modo nem as falhas de pré-tendência do estudo econométrico.

## 14. Pendências da revisão humana

- Cadastrar os revisores em `config/revisores.csv` (identificação e qualificação controladas pela pesquisa).
- Decidir as 6.282 variantes P1 em `saidas/P1/revisao_variantes.csv` (EQUIVALENTE/DIVERGENTE/INDETERMINADA, com fundamentação, fonte, revisor e data).
- Decidir os 4.122 produtos e 2 subprodutos em `saidas/P1/revisao_produtos.csv`, começando pelo piloto (`saidas/piloto_P1_100/`), com especificação canônica `NOME | ATRIBUTO: VALOR | …` que inclua os atributos essenciais (coluna `atributos_consenso`).
- Produto com conflito objetivo: decidir DESMEMBRAR (e então revisar os subprodutos) ou REJEITAR.
- Consultar editais/termos de referência nos 919 produtos indicados.

## 15. Continuidade

```powershell
cd PNCP-Automation\analises\validacao_tecnica_cesta_20261125
..\..\.venv\Scripts\python.exe scripts\executar.py concluir --rodada piloto_P1_100 --exigir-dupla-revisao
..\..\.venv\Scripts\python.exe scripts\executar.py concluir --exigir-dupla-revisao        # rodada P1
..\..\.venv\Scripts\python.exe scripts\executar.py relatorio
```

Com aprovações, `concluir` grava `saidas/<rodada>/cesta_validada.csv` e `saidas/<rodada>/integracao_econometria/` (cópia dos arquivos congelados da cesta + `cesta_validada.csv` no formato original, só com produtos inteiros). O estudo econométrico roda de novo sem mudar código, com um `config.json` cujo `caminhos.cesta_pasta` aponte para essa pasta. Subprodutos exigem adaptar a ligação item × especificação atômica (`ligacao_itens_especificacoes.csv`); o CATMAT original não basta para presumir equivalência. Qualquer mudança de entrada, regra ou configuração exige nova preparação (nova `versao_auditoria`); aprovações de outra versão nunca são reaproveitadas.

## Hashes

| Arquivo | SHA-256 |
|---|---|
| saidas/piloto_P1_100/base_produtos.csv | `a91e801fdb139aa556c66240d5ee0050c7b3d4edd5303dea492914c2ef4dfd42` |
| saidas/piloto_P1_100/base_variantes.csv | `592fe807b6a5a9ea9f0bb273e13564d87e82493806f8f8eb018b08d8e6b4fca4` |
| saidas/piloto_P1_100/descricoes_originais.csv | `ec61eb9a564d18321a51b24cdea823d4680e9bb19bb27a852b02fcf48630ca80` |
| saidas/piloto_P1_100/auditoria_atributos.csv | `3687338f4c9bdac9f723ea03030f2f969ece70a5088fa00e604d5a7cfa75b6f9` |
| saidas/piloto_P1_100/auditoria_conflitos.csv | `893dc65703b2134206cf8af57b198338d3e8bda4a1cc6c8bb9f5e15a4520a89a` |
| saidas/piloto_P1_100/vocabulario_chaves_declaradas.json | `baab94c8b20f86a3274d15c88f7df2a27d7f2b28376ef74ecdaf363022432c25` |
| saidas/piloto_P1_100/revisao_produtos.csv (inicial) | `a13598359f2a350494588b23b08be8be1d404d990bb624392d0132b29e4f6e81` |
| saidas/piloto_P1_100/revisao_variantes.csv (inicial) | `44458aefb6f2e1203ad12085c13ed452ea6941c1d95184449db60d648154b415` |
| saidas/piloto_P1_100 — versão da auditoria | `41b7f182d9cb09f8` |
| saidas/P1/base_produtos.csv | `448c39a788b2f23141b6fa6e8bd8c862b407c8c693b93251630c671679d90346` |
| saidas/P1/base_variantes.csv | `6e58b570e4b97baa14a4fe3515b0a537b3bef872b9f38ae3c90da71ae1e2d9f6` |
| saidas/P1/descricoes_originais.csv | `cb8241d902026971d1426a60dece063cd90694a8deea6b375be5c837b25b5745` |
| saidas/P1/auditoria_atributos.csv | `60df5deb27965cbd2e9214781eeb4cb0d97eb762e31d9d94f0a39c21c4252067` |
| saidas/P1/auditoria_conflitos.csv | `74846ed37aab533e1eb77900898af63a00211120de85ce2554ced25bf6f41561` |
| saidas/P1/vocabulario_chaves_declaradas.json | `baab94c8b20f86a3274d15c88f7df2a27d7f2b28376ef74ecdaf363022432c25` |
| saidas/P1/revisao_produtos.csv (inicial) | `bb83e38169032e941e033ccc7ce18691fb9d468a1f92b16d47b1cf356cf8870d` |
| saidas/P1/revisao_variantes.csv (inicial) | `2d2286af8c45f22d78ffa67b7e9524f282f3c7cb95176d0a31c0948a04397565` |
| saidas/P1 — versão da auditoria | `40caddd4e39c2c6d` |
| entrada: cesta_candidata.csv | `80cd46a7bac29464209a4dea4b668d2bfd35915ee8c694c51692b659a21d59eb` |
| entrada: descricoes_variantes.csv | `a20612a940ee5dfb82e653246df0f0f042929e8317ec21373420ae9ce2968cc9` |
| entrada: sensibilidade_pertinencia.csv | `3c35b94e8296357cea9fa6441c4840a8ced0dc027c81623f2bf29897545c1c4e` |
| entrada: formulario_revisao.csv | `78c42b7b246b68e6c40026511e3780b7b579626be37aa08f8a1c947a853c7a64` |
