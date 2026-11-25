# Protocolo — nova rodada exploratória A × AF na cesta P1 validada automaticamente

Fixado em 25/11/2026, depois do congelamento (`congelamento.json`, 14:02:51) e **antes** de acessar preços ou modos de
disputa. A rodada não altera nenhum arquivo do estudo anterior (`analises/efeito_modos_cesta_padronizada_20261124/`), da
cesta, da validação técnica ou do banco PNCP.

## 1. Caráter e compatibilidade com o protocolo anterior

- O protocolo do estudo anterior previa a análise **principal** só sobre produtos com **aprovação técnica humana
  documentada** (`cesta_validada.csv`). Essa cesta continua vazia.
- Esta rodada usa outra população: a **S1 da validação automática** (validador 2.0.0, execução
  `b83d3184-118d-5b9b-b732-7e310ff1c631`). São 3.065 produtos `AUTO_VALIDADO_CATALOGO`, ou seja, homogêneos **no nível
  do catálogo** (descrições conformes às características oficiais do CATMAT).
- Portanto **não** é a execução confirmatória do protocolo anterior. É uma nova rodada **exploratória**, com população e
  método de validação diferentes, registrados aqui.
- S1 não equivale a validação documental individual. Os itens S4 (36) não são misturados com S1.
- A rodada ocorre depois de os resultados exploratórios anteriores já terem sido vistos.

## 2. Amostras (definidas no congelamento, sem olhar preços)

| Amostra | Produtos | Definição |
|---|---|---|
| **S1** (principal desta rodada) | 3.065 | `AUTO_VALIDADO_CATALOGO` |
| S1S2 | 3.172 | S1 + `AUTO_VALIDADO_CATALOGO_COM_RESSALVA` (107) |
| P1 | 4.122 | classe A ∩ cenário rigoroso, sem filtro de validação |
| cesta | 16.248 | cesta candidata (resultados do estudo anterior, reutilizados sem reestimação) |

Cada amostra é a amostra analítica do estudo anterior restrita aos produtos do conjunto. As referências
leave-one-UASG-out são calculadas dentro de produto × trimestre, então os índices dos produtos mantidos não mudam. O
regime de modo por UASG vem de todas as compras eletrônicas da UASG, logo é o mesmo em todas as amostras. Os eventos
utilizáveis mudam com os produtos.

## 3. Especificações (idênticas às do estudo anterior, sem alteração)

Configuração: `analises/efeito_modos_cesta_padronizada_20261124/config.json`, com o SHA-256 em `congelamento.json`.

- **Desfecho:** Y_A1 = 100·(ln P − ln R_A1), com |Y| ≤ ln 10.
- **E3:** efeitos fixos de UASG e produto × trimestre, mais log da quantidade.
- **E7:** efeitos fixos de UASG × produto e produto × trimestre, mais log da quantidade.
- **Inferência dos efeitos fixos:** CR1 por CNPJ, duas vias e WCR Webb com 999 réplicas.
- **dCDH reversível:** janelas de 6 meses (principal) e 12 meses; estimandos por item e por compra; pesos por célula
  (principal) e por evento.
- **Placebos e famílias:** placebos l = −1 e −2, separados em adoção e abandono. Bootstrap por CNPJ, 999 réplicas,
  semente 20261123. Holm na família P (agregado, adoção, abandono) e na família F (placebo −1 adoção, placebo −1
  abandono, simetria).
- **BJS:** só no subconjunto absorvente.
- **HonestDiD:** RM com M̄ ∈ {0; 0,5; 1; 1,5; 2} e SD com M ∈ {0; 0,5; 1; 2} lp. Cada especificação usa a covariância das
  réplicas da própria amostra.
- **Robustez:** as 14 referências A1–B9, em amostra comum e própria, com diferenças pareadas e Holm; também as
  verificações R01–R15 do estudo anterior.

## 4. Comparações e decomposições (pré-especificadas)

1. **Amostras próprias:** S1, S1S2, P1 e cesta lado a lado. Para cada uma:
   - produtos, itens, compras, UASGs e órgãos efetivos;
   - eventos válidos e usados;
   - E3 e E7;
   - dCDH agregado, adoção e abandono, com Holm;
   - placebo −1 e HonestDiD;
   - sobreposição de produtos pré/pós e peso do maior CNPJ.
2. **Amostra comum de eventos:**
   - dCDH de S1S2, P1 e cesta restrito às trocas (UASGs) com peso na S1, para isolar a composição de produtos dada a
     mesma população de eventos;
   - a diferença cesta → S1 é decomposta em: (a) redução de eventos (cesta com os eventos da S1 − cesta completa) e
     (b) seleção de produtos dentro dos mesmos eventos (S1 − cesta com os eventos da S1).
3. **Ponderação:** S1 com pesos por célula × por evento × por compra.
4. **Órgãos:**
   - número efetivo de CNPJs;
   - participação do maior CNPJ na variação identificadora (E3) e no peso do dCDH;
   - jackknife por CNPJ (do estudo anterior).
5. **Composição da S1** × S2, inconclusivos e P1:
   - frequência de compras;
   - classe de material;
   - quantidade;
   - concentração institucional;
   - cobertura anual e trimestral;
   - fração de compras AF.

   É só diagnóstico: não altera a classificação.

Nenhuma especificação, janela, peso, referência ou critério de amostra é escolhido depois de observar significância. A
escolha da referência não depende do valor-p.

## 5. Interpretação

A rodada é **exploratória**. Se os placebos pré-troca continuarem rejeitando tendências paralelas, ou se as estimativas
dependerem da composição institucional, nenhuma conclusão causal é afirmada.
