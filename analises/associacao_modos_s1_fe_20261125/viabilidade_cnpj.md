# Viabilidade de um desenho em painel CNPJ × trimestre (diagnóstico descritivo)

25/11/2026.
- **Comando:** `python executar.py --etapas viabilidade`.
- **Código:** `assoc/viabilidade_cnpj.py`.
- **Tabelas:** `tabelas/viab_cnpj_*.csv` e `resultados/viabilidade_cnpj.json`.
- **Alcance:** só contagens; nenhum efeito estimado.
- **Limiares:** fixados em `config.json["viabilidade_cnpj"]` antes de rodar.
- **Participação AF:** fração das compras A/AF do Pregão Eletrônico de cada CNPJ, contando todas as compras, não só S1.
- **Preços S1:** compra × produto homologado, sem filtro A1.
- **Período completo:** 2023T2–2026T1.

## 1. Cobertura de preços S1

Dos 3.032 CNPJs com compras A/AF, 2.192 têm algum preço S1.

| Trimestres com preço S1 | CNPJs | Desses, consecutivos |
|---|---:|---:|
| ≥ 4 | **1.023** | 707 |
| ≥ 6 | **653** | 463 |
| ≥ 8 | 363 | 303 |
| ≥ 12 (todos) | 31 | — |

## 2. Variação do tratamento

- **Elegíveis:** 955 CNPJs têm 4 trimestres consecutivos com ≥ 3 compras A/AF em cada um, o mínimo para observar uma mudança.
- **Definição de evento:** a média de t0 e t0+1 difere da média de t0−2 e t0−1.
  - Com |Δ| ≥ 0,5: **54 CNPJs**, dos quais **49 persistentes** (os dois trimestres pós do mesmo lado); 26 aumentos e 28
    reduções.
  - Com |Δ| ≥ 0,3: 108 CNPJs, 90 persistentes.

## 3. Comparadores

**CNPJs estáveis:** amplitude da participação AF ≤ 0,2 em ≥ 6 trimestres com ≥ 3 compras. São 627, distribuídos assim:

| Participação AF | CNPJs estáveis |
|---|---:|
| 0–10% | 427 |
| 10–30% | 2 |
| 30–70% | 5 |
| 70–90% | 0 |
| 90–100% | 193 |

**Para cada evento persistente** (comparadores com participação pré a ±0,1 da do evento, observados em t0−2..t0+1):
- mediana de 43 comparadores, dos quais 29 com preço S1 em t0−1 e t0;
- mínimo de 1.

**Limitação:** quase não existem CNPJs estáveis em níveis intermediários. Eventos que partem de participações mistas têm
poucos comparadores semelhantes; os demais são comparados com órgãos sempre A ou sempre AF.

## 4. Composição

Decomposição de Δ entre o pré e o pós em três partes: dentro das UASGs presentes nos dois períodos, peso das UASGs e
entrada ou saída de UASGs.

- **39 dos 49 eventos** têm uma única UASG no pré: o CNPJ é, na prática, uma UASG.
- Em 42 dos 49, mais da metade da mudança vem de dentro das UASGs. A mediana da fração "dentro" é 1,0.
- Em módulo, os componentes somam:

  | Componente | Soma |
  |---|---:|
  | dentro das UASGs | 26,9 |
  | composição | 3,4 |
  | entrada/saída | 0,9 |

- **Conclusão:** a participação AF muda porque o próprio órgão (quase sempre uma única unidade) mudou de prática, não pela
  composição.

## 5. Produtos antes e depois dentro do CNPJ

Produtos S1 comprados em t0−2..t0−1 **e** em t0..t0+1, nos 49 eventos persistentes:

| Produtos comuns | Eventos |
|---|---:|
| ≥ 1 | 16 |
| ≥ 5 | 9 |
| ≥ 10 | 6 |

A mediana é 0. Nos 33 eventos restantes, as cestas pré e pós não têm nenhum produto em comum.

## 6. Concentração

- **Órgãos que sustentariam a comparação no mesmo produto:** 16 CNPJs, com número efetivo de **6,6**, ponderado pelas
  observações pós em produtos comuns.
- **Maiores pesos:** Município de Flexeiras (25%), IAMSPE (19%), Estado do Maranhão (13%), Município de Candiba (12%),
  Município de Salgado Filho (11%).
- Todos os 16 têm algum comparador semelhante com preço.

## 7. Falsificação independente

Exigências: t0−4..t0−3, separados da janela pré.

| Exigência | Eventos (de 49) |
|---|---:|
| preço S1 em t0−4 e t0−3 | 8 |
| preço em todos os trimestres de t0−4 a t0+1 | 6 |
| produto comum entre a falsificação e o pré | 9 |
| modo estável de t0−4 a t0−1 (amplitude ≤ 0,25) | 29 |
| **todas as exigências** (produto comum pré/pós, preços em t0−4 e t0−3, produto comum na falsificação, modo estável antes) | **3** |

**Conclusão:** não há observações suficientes para um placebo independente.

## 8. Cobertura temporal: ausência real × censura do CATMAT

Fração dos itens de todas as compras A/AF com código CATMAT, e CNPJ-trimestres por situação:

| Trimestre | Itens com CATMAT | Com preço S1 | Com CATMAT, sem S1 (ausência real) | Nenhum item com CATMAT |
|---|---:|---:|---:|---:|
| 2023T2–2025T3 | 95–98% | 111–1.208 | 173–768 | 1–35 |
| 2025T4 | 92% | 1.189 | 768 | 60 |
| 2026T1 | 86% | 881 | 649 | **204** |
| 2026T2 | 21% | 406 | 525 | **843** |
| 2026T3 | 0,4% | 14 | 75 | **1.692** |
| 2026T4 | 0,2% | 0 | 16 | **1.288** |

- **Até 2025T3:** um CNPJ-trimestre com compras e sem preço S1 é quase sempre ausência real (ele comprou itens com
  CATMAT, mas não produtos S1).
- **A censura começa antes de 17/04/2026:** já em 2025T4 (92%) e sobretudo em 2026T1 (86%, com 204 CNPJ-trimestres sem
  nenhum item com código).
- **De 2026T2 em diante:** não se distingue ausência de censura. Os modos continuam observados, mas os produtos não.
- **Recomendação:** um desenho futuro deveria tratar 2026T1 como parcialmente censurado e excluir 2026T2–T4 dos
  desfechos.

## Síntese

**Cobertura e tratamento:**
- Há 653 CNPJs com seis ou mais trimestres de preço S1.
- Há 49 mudanças persistentes e relevantes de participação AF. São mudanças reais de prática, quase sempre em órgãos de
  uma única UASG, com comparadores estáveis disponíveis sobretudo nos extremos (sempre A ou sempre AF).

**O que impede o desenho:**
- Só 16 desses 49 órgãos compram algum produto S1 em comum antes e depois, com 6,6 órgãos efetivos.
- Só 3 cumprem também as exigências de um placebo independente.

**Conclusão:**
- Um painel CNPJ × trimestre tem tratamento e comparadores, mas não tem produtos comuns nem pré-períodos suficientes para
  um desenho de mesmo produto com falsificação.
- O desfecho teria de ser o índice médio das compras (cesta variável) e, mesmo assim, com poucos órgãos efetivos.
