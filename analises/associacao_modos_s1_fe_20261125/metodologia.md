# Metodologia

**Classificação:** associação condicional. Nenhum coeficiente tem interpretação causal automática.

## Amostra

**Fonte dos itens:** os 708.964 itens dos 3.065 produtos S1 (`AUTO_VALIDADO_CATALOGO`, validador 2.0.0).
- Ligação 1:1 ao `pncp_v2.db` (`registro_principal = 1`), feita pela rodada `efeito_modos_cesta_auto_S1_20261125`.
- A lista S1 é conferida contra o congelamento daquela rodada.
- Cada compra é reconferida na tabela `compras` do banco, aberto só para leitura: fonte, modalidade, modo, UASG, CNPJ e UF.

**Filtros:**
1. Compras.gov.br (dados abertos), Pregão Eletrônico;
2. modo A ou AF;
3. menor preço;
4. data de abertura válida;
5. homologado;
6. preço unitário homologado positivo;
7. produto S1 (nenhum S2).

**Não** se exige referência externa A1 nem se aplica o corte |Y| ≤ ln 10.

**Unidade de observação:** compra × produto.
- Preço = Σ pᵢqᵢ / Σ qᵢ, ponderado pela quantidade licitada; média simples se faltar quantidade, caso não observado.
- Desfecho: y = 100 ln preço, em log-pontos.
- ln q = ln Σ qᵢ.
- Modo, UASG, CNPJ, UF e trimestre são atributos da compra, verificados como únicos.

**UF:** `compras.uf` = `unidadeOrgaoUfSigla`, a UF administrativa da unidade compradora. Não há UF de entrega no banco.

**Período:** trimestre de abertura, de 2023T2 a 2026T3.
- Os trimestres incompletos (2026T2 e 2026T3, depois do fim do CATMAT em 17/04/2026) ficam na amostra principal.
- Uma sensibilidade os exclui.

## Modelos

y = β·AF + FE + γ·ln q + ε:

| Modelo | Efeitos fixos |
|---|---|
| M1 | UF × produto × trimestre + CNPJ (**principal**) |
| M2 | UF × produto × trimestre + CNPJ × produto |
| M3 | CNPJ × produto × trimestre |
| M4 | M3 + UASG |
| M5 | UASG × produto × trimestre |

**Variantes:**
- sem ln q;
- peso igual por compra (cada compra soma 1 entre os seus produtos);
- sem trimestres incompletos;
- amostras comuns: a de M5, contida em todas, e a de M3, contida em M1–M4.

**Absorção dos efeitos fixos:**
- Singletons removidos iterativamente.
- Um único FE: subtração exata das médias.
- Vários FE: LSMR esparso nos dummies, seguido de projeções alternadas até a variação máxima ficar abaixo de 10⁻⁹.
- Verificação: maior média ponderada residual por grupo ≤ 10⁻⁹. Há também uma reestimação de M1, M2 e M4 por projeções
  alternadas puras.

## Diagnósticos de identificação

- **x̃:** AF residualizado nos FE e em ln q.
- **Contribuição de cada CNPJ e de cada UF:** a sua participação em Σ x̃².
- **Número efetivo:** 1/Σ s². Coincide com o G* de Carter, Schnepel e Steigerwald (2017) para ρ = 0. O G* para ρ = 1 é
  indefinido quando o FE está aninhado no CNPJ.
- **Células com os dois modos:** UF × produto × trimestre, CNPJ × produto, CNPJ × produto × trimestre e
  UASG × produto × trimestre, cada uma na amostra do modelo.
- **Exclusão de órgãos:** cada um dos 10 CNPJs mais influentes é retirado, com reestimação integral (singletons e
  absorção refeitos).

## Inferência

- CR1 por CNPJ, com t(G−1).
- Bootstrap selvagem restrito por CNPJ (WCR, pesos de Webb, H0: β = 0, 9.999 réplicas) e IC WCU percentil-t.
- CGM bidirecional CNPJ + produto.
- CR1 por UF.

**Regra predefinida:** só se chama de robusta a significância em que CR1 e WCR rejeitam a 5% e G* ≥ 20.

Com poucos órgãos efetivos, mesmo o WCR pode errar o tamanho do teste (MacKinnon e Webb, 2017). As exclusões de CNPJ
servem como checagem adicional.
