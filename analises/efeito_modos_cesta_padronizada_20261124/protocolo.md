# Protocolo — efeito do modo de disputa (A × AF) na cesta padronizada

Fixado em 25/11/2026 às 03:20, **antes de qualquer estimação de preço**. Até aqui foram executadas só as etapas 1–3 da
ordem do pedido: validação da cesta, construção e auditoria da amostra, cobertura e identificação dos eventos. Mudanças
posteriores entram como desvios declarados no relatório.

| Arquivo | SHA-256 no registro |
|---|---|
| `config.json` | `a8f33b4f87d5591b08fa30da2be5e45cfa8c4fc02ca2d8076e70ac4b8ac01122` |
| `honestdid.R` | `bc735d5ce134910e4f45f8a2b48acc881719b15a8a44c8f91d910079da78a24b` |
| `em/eventos.py` | `4562f96f5465457e251958b362dcef4c17d02d16d7a4cf8c6a1b85dc0ad1f438` |
| `em/inferencia.py` | `2cee133826a74c188808532ed7c3799bbe5f29e3a2e552fdf1acad321b75c26c` |
| `em/referencias.py` | `b99ddf4fc5bcea8e041e9b269b15acfdce35dd50c8dc5964716070b90c8f8ae7` |
| `em/painel.py` | `8ff26e69daf9ba579a9f62d30eb5d2e4ad050030345700db8d0b0f6cfde71d10` |

## 1. Situação de partida que define o caráter do estudo

- A cesta validada (`cesta_padronizada_20261124/saidas/cesta_validada.csv`) **não tem nenhum produto aprovado**, e o
  formulário de revisão não tem nenhuma decisão.
- Consequência: a análise principal, que exige produtos com aprovação técnica documentada, **não é executável**.
- Tudo o que se estima aqui é **exploratório**, sobre a cesta candidata (16.248 produtos), e nenhum resultado será
  apresentado como confirmação causal.
- O código já implementa a análise principal: quando houver produtos aprovados, a amostra principal é
  `elegivel_principal` e o mesmo pipeline vale.

Interseções reais dos conjuntos da cesta (`tabelas/validacao_cesta.json`):

| Conjunto | Produtos |
|---|---|
| A | 10.424 |
| B | 5.824 |
| Famílias do cenário rigoroso | 6.216, que correspondem a 6.217 produtos (uma família tem subtipo) |
| A ∩ rigoroso | 4.122 |
| B ∩ rigoroso | 2.095 |
| A fora do rigoroso | 6.302 |
| Aprovados | 0 |

## 2. Dados

- **`pncp_v2.db`:** em `PNCP-Automation/dados/pncp_v2.db`, aberto em `mode=ro`, com impressão digital conferida antes e
  depois.
- **Mapeamento item → produto:** lido do banco congelado da cesta (`universo_produto` × `cesta_candidata_tab`), também
  só leitura.
- **Ligação item a item:** pela chave (`numero_controle_pncp`, `numero_item`, `registro_principal = 1`). Resultado:
  2.137.650 itens, nenhum sem item, sem compra ou com CATMAT divergente. As 490 divergências de UASG eram só o
  preenchimento com zeros à esquerda (`2300` × `002300`); a UASG foi normalizada para 6 dígitos.
- **Universo:**
  - Compras.gov.br (`fonte = dados_abertos`), Pregão Eletrônico, modos A e AF;
  - critério Menor preço, item homologado (situação = Homologado), preço homologado > 0.

### Período e censura

- **Trimestre de abertura (`data_abertura_proposta`):** toda a cobertura com CATMAT, sem corte em 2025.
- **Censura da fonte:** o CATMAT some depois de 17/04/2026. Por isso 2026T2 está incompleto, e 2026T3 e 2026T4 não estão
  observados. Isso **não** é ausência de compras e não será tratado como tal.
- **2022T4:** tem só nov–dez/2022.
- **2023T1:** não tem nenhum item com situação Homologado. A fonte mantém "Em andamento" em itens que já têm preço de
  resultado (status desatualizado na API).
- **Uso no estudo de eventos:**
  - o painel usa 2023T1–2026T1 para o regime de modo;
  - o desfecho de preço só existe a partir de 2023T2;
  - 2022T4 e 2026T2 ficam fora do painel;
  - o painel de efeitos fixos os mantém, com sensibilidade sem eles.

## 3. Desfecho primário e referências

- **Desfecho:** `Y_i = 100 [ln P_i − ln R_{c,t,−u}]`, com c = produto da cesta e t = trimestre de abertura.
- **Referência:** calculada só com outras UASGs; a UASG focal sai inteira **antes** de contar, ordenar ou aparar.
- **Mínimos da referência:** 5 itens de ≥ 3 outras UASGs.
- **Regra de extremos:** o item fica se `|Y_A1| ≤ 100 ln 10`. É a máscara única da comparação principal, herdada do
  protocolo de 23–24/11.
- **Conversão:** os coeficientes estão em log-pontos; a diferença percentual exata é `100[exp(β/100) − 1]`.
- **A1–A5:**
  - A1: geométrica dos itens (principal);
  - A2: aritmética dos itens;
  - A3: mediana dos itens;
  - A4: aritmética aparada em `floor(0,1n)` por cauda, só com n ≥ 10;
  - A5: geométrica aparada pela mesma regra.
- **B1–B9:** estatística dentro da UASG comparadora × estatística entre UASGs, com peso igual por UASG comparadora:
  - B1 = (aritmética, aritmética); B2 = (aritmética, geométrica), igual à G anterior; B3 = (aritmética, mediana);
  - B4 = (geométrica, aritmética); B5 = (geométrica, geométrica); B6 = (geométrica, mediana);
  - B7 = (mediana, aritmética); B8 = (mediana, geométrica); B9 = (mediana, mediana).
- **Contaminação da referência:** EST_A1 é a A1 calculada só com comparadoras estáveis no período todo (AF < 5% ou
  > 95% das compras A/AF, com ≥ 20 compras).
- **Comparação das referências:**
  - amostra comum (as 14 definidas): muda só a fórmula;
  - amostra própria de cada referência: muda a fórmula e a amostra;
  - diferenças pareadas β_k − β_A1 com IC e Holm.
  - pesos (célula, evento, compra) e estimando (item, compra) são variados à parte, rotulados.

## 4. Descritivas (§7)

Por modo:
- itens, compras, produtos, UASGs e órgãos;
- média, mediana, DP e percentis 5/25/50/75/95 de Y_A1;
- cobertura, quantidades e taxas de homologação, fracasso e deserção (sobre os itens decididos);
- distribuição dos produtos por modo.

A diferença bruta usa EP agrupado por CNPJ, EP em duas vias (CNPJ e produto) e WCR de Webb (999 réplicas). A diferença
de medianas usa bootstrap por CNPJ. Nenhum teste supõe itens independentes.

## 5. Efeitos fixos (§8) — associação condicional

| Especificação | Conteúdo |
|---|---|
| E1 | bruto |
| E2 | UASG + produto × trimestre |
| **E3 (principal)** | E2 + log da quantidade prevista |
| E4 | E3 + SRP |
| E5 | E3 + sigilo |
| E6 | E3 + SRP + sigilo |
| E7 | UASG × produto + produto × trimestre + log quantidade |
| E8 | UASG + produto × mês + log quantidade |
| E9 | UASG + órgão × ano + produto × trimestre + log quantidade |
| E10 | E3 por tercil da quantidade dentro do produto |

- SRP e sigilo podem ser decididos junto com o modo, pela mesma autoridade e no mesmo edital, e por isso podem ser
  mediadores. Ficam fora da principal e aparecem como especificações adicionais.
- Número de licitantes e preço estimado **não** são controlados.
- Singletons são removidos, e a perda é registrada.
- Inferência: CR1 por CNPJ (unidade institucional independente); duas vias (CNPJ, produto) e WCR em E3.
- Contribuição de cada órgão para a variação identificadora, número efetivo de órgãos e exclusão exata dos 10 maiores
  contribuintes.

## 6. Estudo de eventos (§9) — análise causal exploratória

### Regime e eventos

- **Regime da UASG no trimestre:** AF se a fração AF das suas compras A/AF (todas as compras eletrônicas da fonte, não
  só as da cesta) for ≥ 0,5. O trimestre é puro se a fração for ≤ 0,10 ou ≥ 0,90.
- **Troca válida:** é a primeira mudança em relação ao regime inicial, observada em F. Exige:
  - persistência no trimestre seguinte (F e F+1 no novo regime);
  - trimestre F−1 observado no regime antigo.
- **Exclusões:**
  - 1ª mudança sem persistência: a UASG é irregular e sai de tratados e controles;
  - F−1 não observado: troca sem pré adjacente, também excluída.
- **Contagens no registro:** 317 trocas (172 A→AF, 145 AF→A), 187 CNPJs, 96 puras, 212 absorventes; 610 UASGs irregulares
  e 4.308 que nunca trocam.

### Estimadores

- **Principal: dCDH DID_l** (de Chaisemartin e D'Haultfœuille, efeitos intertemporais), adequado a tratamento reversível.
  - Cada troca é comparada, entre F−1 e F−1+l, com UASGs de mesmo regime inicial que não trocaram até F−1+l, com Y
    observado nos dois períodos e pelo menos 5 controles.
  - Adoção e abandono são estimados separadamente.
  - O sinal é normalizado para "efeito do AF": o abandono entra com −1.
  - Agregado: média dos DID_l ponderada pelo peso dos switchers.
  - Placebos l = −k usam o mesmo grupo de controle do efeito k.
  - Simetria: adoção − abandono = 0.
- **Janelas:** 6 meses (L = 2 trimestres, a principal) e 12 meses (L = 4). Só se usam períodos observados; nada é
  preenchido.
- **Estimandos e pesos:**
  - por item (principal: Y da UASG × trimestre é a média dos itens, com peso igual ao nº de itens);
  - por compra (média das médias por compra);
  - peso igual por evento.
- **Sensibilidade BJS:** só no subconjunto absorvente, que são as adoções sem volta e as UASGs sempre em A. O BJS não é
  aplicado a quem alterna entre os modos.
- **Inferência:** bootstrap por CNPJ (999 réplicas, semente 20261123) e jackknife por CNPJ.
- **Diagnósticos:**
  - balanço das covariáveis pelo mesmo estimador: quantidade, SRP, sigilo e taxa de homologação;
  - sobreposição de produtos, pré-períodos, calendário, número efetivo de órgãos, concentração dos pesos;
  - diferença mínima detectável dos placebos.
- A ausência de pré-tendência significativa **não** prova tendências paralelas.

## 7. HonestDiD (§11)

- Aplicado às trajetórias dinâmicas dCDH por item, com referência A1, nas janelas de 6 e 12 meses, para agregado,
  adoção e abandono.
- Covariância: a dos draws do bootstrap da própria especificação.
- Δ^RM com M̄ ∈ {0; 0,5; 1; 1,5; 2}; Δ^SD com M ∈ {0; 0,5; 1; 2} log-pontos, só com ≥ 2 períodos prévios.
- Alvo: média simples dos efeitos pós.
- As restrições que não puderem ser calculadas são registradas à parte. Nenhum valor é escolhido pela significância.

## 8. Famílias de Holm (definidas agora)

- **P (principal, exploratória):** dCDH, 6 meses, por item, A1 — agregado, adoção e abandono.
- **F (falsificação):** placebo l = −1 da adoção e do abandono; simetria.
- **S (secundários, dCDH 6 meses):** desconto, homologação, fracasso, deserção.

## 9. Robustez (§13) e secundários (§14)

- **Robustez:**
  - validados (não estimável);
  - A ∩ rigoroso (exploratório);
  - cesta completa;
  - A3 e A2 × A1;
  - pesos por compra, por item e por evento;
  - exclusão de um órgão por vez;
  - sem inconsistências técnicas (alertas que não são de cautela);
  - mesmo produto antes e depois da troca;
  - referência só com UASGs estáveis;
  - células de menor dispersão: DP leave-one-out dos log-preços ≤ mediana, regra fixa;
  - janela de 12 meses;
  - produtos recorrentes × não recorrentes.
- **Secundários:**
  - desconto `100(1 − P/E)`, com E > 0 e orçamento não sigiloso;
  - índices com A3 (mediana externa) e A1 (geométrica externa);
  - homologação, fracasso e deserção sobre os itens decididos (exclui "Em andamento");
  - seleção: as mesmas regressões na taxa de homologação.
- Desconto maior não basta como evidência de preço menor. Ausência de significância não é equivalência.
