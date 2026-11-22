# Desfecho dos itens e compras por modo de disputa — testes de 21/11/2026

Pergunta: a frequência de itens fracassados, desertos e não homologados, e de compras sem nenhum item
homologado ou com todos homologados, difere entre Aberto (A), Aberto-Fechado (AF) e Fechado-Aberto (FA)?
O desenho foi fixado antes das estimativas em [protocolo.md](protocolo.md).

## Resposta curta

- **AF × A: nenhuma diferença significativa.** A diferença bruta (AF com 1,4 p.p. a mais de itens não
  homologados) some quando se compara dentro do mesmo órgão (E3: −0,7 p.p., IC95 −1,8 a +0,4) e no
  pareamento UASG × CATMAT × ano (E4: −2,2 p.p., IC95 −5,0 a +0,6). Ela vem de quais órgãos usam cada modo.
- **FA × A: só um teste significativo na família principal.** As compras do Fechado-Aberto têm
  **5,2 p.p. menos chance de ter todos os itens decididos homologados** (E3: IC95 −8,0 a −2,5;
  p Holm = 0,002), sobre uma base de 66,7% no Aberto. No item, a diferença bruta de +5,6 p.p. em não
  homologados não resiste aos controles.
- Os outros 8 testes da família principal têm p Holm ≥ 0,44.

## Amostra

Compras.gov.br (`fonte = 'dados_abertos'`), Pregão Eletrônico, publicação de 2023-01 a 2026-06.

| | Aberto | Aberto-Fechado | Fechado-Aberto | Total |
|---|---|---|---|---|
| Itens decididos (E1–E3) | 3.080.489 | 1.975.316 | 28.391 | 5.084.196 |
| Itens no pareamento (E4) | 1.306.039 | 812.114 | 12.704 | 2.130.857 |
| Compras com item decidido | 163.019 | 98.675 | 1.518 | 263.212 |

Grupos: 2.889 CNPJs de órgão e 195.831 grupos de CATMAT nos itens (2.325 e 92.287 no E4).

## Taxas observadas (% dos itens decididos)

| Ano | Modo | Fracassado | Deserto | Não homologado | Itens |
|---|---|---|---|---|---|
| 2023 | Aberto | 11,90 | 8,39 | 20,29 | 256.675 |
| 2023 | Aberto-Fechado | 11,74 | 7,20 | 18,94 | 184.495 |
| 2023 | Fechado-Aberto | 15,40 | 4,85 | 20,26 | 3.051 |
| 2024 | Aberto | 9,87 | 3,41 | 13,28 | 1.138.630 |
| 2024 | Aberto-Fechado | 11,64 | 4,19 | 15,83 | 703.547 |
| 2024 | Fechado-Aberto | 12,76 | 5,14 | 17,90 | 10.978 |
| 2025 | Aberto | 11,74 | 2,48 | 14,21 | 1.227.533 |
| 2025 | Aberto-Fechado | 12,44 | 2,84 | 15,28 | 790.448 |
| 2025 | Fechado-Aberto | 22,23 | 2,76 | 24,99 | 11.377 |
| 2026 (jan–jun) | Aberto | 12,26 | 2,68 | 14,95 | 457.651 |
| 2026 (jan–jun) | Aberto-Fechado | 12,41 | 3,02 | 15,43 | 296.826 |
| 2026 (jan–jun) | Fechado-Aberto | 8,38 | 0,67 | 9,05 | 2.985 |

Compras (% das compras com item decidido):

| Ano | Modo | Sem item homologado | Todos homologados | Compras |
|---|---|---|---|---|
| 2024 | Aberto | 6,06 | 67,20 | 60.221 |
| 2024 | Aberto-Fechado | 7,32 | 63,91 | 34.846 |
| 2024 | Fechado-Aberto | 10,92 | 57,59 | 705 |
| 2025 | Aberto | 6,17 | 67,39 | 64.646 |
| 2025 | Aberto-Fechado | 7,55 | 63,86 | 39.303 |
| 2025 | Fechado-Aberto | 7,56 | 50,32 | 463 |

Os demais anos estão em `descritivas_compras.csv`.

## Família principal (E3: efeitos fixos de mês × material/serviço e de UASG, com controles)

Diferença em pontos percentuais em relação ao Aberto. IC95 e p com erro-padrão agrupado por CNPJ e
CATMAT (itens) ou por CNPJ (compras); Holm sobre os 10 testes.

| Desfecho | Base no Aberto | Contraste | Diferença | IC95 | p | p Holm |
|---|---|---|---|---|---|---|
| Item fracassado | 11,1% | AF − A | −0,63 | −1,42 a +0,17 | 0,122 | 0,887 |
| | | FA − A | +0,38 | −1,03 a +1,79 | 0,599 | 1,000 |
| Item deserto | 3,3% | AF − A | −0,07 | −0,72 a +0,58 | 0,829 | 1,000 |
| | | FA − A | −0,79 | −1,57 a −0,01 | 0,048 | 0,436 |
| Item não homologado | 14,5% | AF − A | −0,70 | −1,75 a +0,36 | 0,197 | 1,000 |
| | | FA − A | −0,41 | −2,24 a +1,42 | 0,661 | 1,000 |
| Compra sem item homologado | 6,4% | AF − A | −0,24 | −1,09 a +0,62 | 0,587 | 1,000 |
| | | FA − A | +1,34 | −0,31 a +2,98 | 0,111 | 0,887 |
| **Compra com todos homologados** | 66,7% | AF − A | +0,11 | −1,20 a +1,42 | 0,868 | 1,000 |
| | | **FA − A** | **−5,23** | **−7,96 a −2,49** | **0,0002** | **0,002** |

## Sensibilidades (p bruto)

| Desfecho | Contraste | E1 bruta | E2 controles | E3 principal | E4 pareamento |
|---|---|---|---|---|---|
| Item fracassado | AF − A | +0,95 (p 0,15) | +0,66 (0,08) | −0,63 (0,12) | −2,37 (0,08) |
| | FA − A | **+5,24 (0,02)** | **+1,85 (0,0499)** | +0,38 (0,60) | −1,10 (0,68) |
| Item deserto | AF − A | +0,41 (0,19) | +0,40 (0,14) | −0,07 (0,83) | +0,17 (0,87) |
| | FA − A | +0,34 (0,61) | −0,30 (0,70) | **−0,79 (0,048)** | **−2,99 (0,04)** |
| Item não homologado | AF − A | +1,36 (0,13) | +1,06 (0,06) | −0,70 (0,20) | −2,20 (0,12) |
| | FA − A | **+5,58 (0,03)** | +1,55 (0,30) | −0,41 (0,66) | −4,09 (0,17) |
| Compra sem item homologado | AF − A | +1,18 (0,09) | +0,37 (0,16) | −0,24 (0,59) | — |
| | FA − A | **+3,32 (0,001)** | **+1,64 (0,04)** | +1,34 (0,11) | — |
| Compra com todos homologados | AF − A | **−3,23 (0,004)** | **−2,06 (0,007)** | +0,11 (0,87) | — |
| | FA − A | **−9,71 (0,001)** | **−4,60 (0,03)** | **−5,23 (0,0002)** | — |

Em negrito, p < 0,05.

## Leitura

1. **As diferenças descritivas entre AF e A são de composição.** Sem controles, o AF tem um pouco mais
   de fracasso e menos compras inteiramente homologadas. Isso já aparece com erro-padrão agrupado
   (E1: a diferença por compra tem p = 0,004). Mas, dentro do mesmo órgão, o AF fica igual ao Aberto ou
   ligeiramente melhor, e no pareamento por item o sinal é negativo (−2,2 p.p. em não homologados,
   p = 0,12). Os órgãos que usam mais o AF têm taxas de fracasso maiores em qualquer modo.
2. **O FA tem compras com mais "buracos".** No item, o FA não difere do Aberto depois dos controles, e a
   deserção até é menor (−0,8 p.p. em E3, sem significância depois de Holm). Mas a chance de a compra
   homologar todos os itens é 5 p.p. menor, e isso se mantém em E1, E2 e E3. Uma leitura compatível: as
   compras FA têm mais itens por compra (24 contra 19 no Aberto em 2025). O controle pelo log do nº de
   itens não elimina toda essa diferença: com mais itens, a chance de algum falhar aumenta. A amostra FA
   é pequena (1.513 compras em E3), e a taxa oscila muito entre anos (50% em 2025 e 67% em 2026).
3. **Sem significância não quer dizer equivalência.** Em E3, os intervalos de AF − A nos três desfechos
   de item ficam entre −1,75 e +0,58 p.p., e nos dois de compra entre −1,20 e +1,42 p.p. Diferenças menores
   que essas continuam possíveis; maiores ficam pouco plausíveis.

## Limitações

- Associativo: o modo é escolhido pelo órgão. E3 e E4 controlam o órgão e o item, mas não o momento nem o
  motivo da escolha.
- Só Compras.gov.br. Nas outras plataformas a situação do item não é atualizada (ver o painel).
- "Fracassado" mistura desclassificação, inabilitação e falta de proposta aceitável. A base não separa
  os motivos.
- O E4 usa só itens com CATMAT (42% dos itens decididos) e células UASG × item × ano com mais de um item.
- A situação é a do snapshot de 10/11/2026. Itens de 2026 ainda podem mudar.

## Reprodução

```powershell
.\.venv\Scripts\python.exe analises\desfecho_modos_20261121\testes_desfecho.py   # ~50 min
```

Lê `dados/pncp.db` somente para leitura e guarda a extração em `dados/analise_desfecho/base_itens.pkl`
(fora do git; `--reextrair` refaz). Saídas nesta pasta: `resultados.csv` (todas as estimativas, com
EP, IC95, p, p Holm, N e grupos), `descritivas_itens.csv` e `descritivas_compras.csv`.
