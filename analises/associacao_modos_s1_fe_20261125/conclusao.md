# Conclusão — associação A × AF na cesta S1 com efeitos fixos (M1–M5)

25/11/2026. Os números vêm de [`relatorio.md`](relatorio.md) e `tabelas/`. **São associações condicionais, não efeitos causais.**

## Coeficientes

Amostra própria de cada modelo, com ln q:

| Modelo | Comparação | β (lp) | % | IC95 CR1 CNPJ | p WCR | Nº ef. CNPJs | Obs. |
|---|---|---:|---:|---|---:|---:|---:|
| **M1** | UF × produto × trimestre + CNPJ | **−4,65** | −4,5% | [−6,15; −3,15] | < 0,001 | 15,0 | 319.336 |
| M2 | UF × produto × trimestre + CNPJ × produto | −4,96 | −4,8% | [−6,49; −3,44] | 0,001 | 8,7 | 180.355 |
| M3 | CNPJ × produto × trimestre | −6,25 | −6,1% | [−7,40; −5,10] | < 0,001 | 3,4 | 178.720 |
| M4 | M3 + UASG | −4,24 | −4,1% | [−6,93; −1,55] | 0,185 | 2,9 | 178.308 |
| M5 | UASG × produto × trimestre | +1,49 | +1,5% | [−11,23; 14,21] | 0,918 | 5,1 | 23.354 |

## O que muda ao apertar o controle institucional

1. **De CNPJ (M1) para CNPJ × produto (M2):** o coeficiente quase não muda (−4,65 para −4,96).
   - Tirar o nível de preço específico de cada órgão em cada produto não elimina a associação.
   - Perdem-se 44% das observações (singletons em CNPJ × produto), e o número efetivo de órgãos cai de 15 para 8,7.
2. **Para a comparação só dentro do órgão (M3):** o coeficiente fica mais negativo (−6,25), mas a identificação se
   concentra.
   - Só 26,6% das compras estão em células CNPJ × produto × trimestre com os dois modos.
   - O Comando do Exército responde por 51% da variação identificadora, e o número efetivo de órgãos é 3,4.
   - Na amostra comum de M1–M4 (a de M3), M1 e M2 dão −5,7: parte da diferença entre M1 e M3 vem da amostra, não do
     controle.
3. **Acrescentando UASG (M4):** o coeficiente volta a −4,24, e a variação identificadora cai para 8% da variação de AF.
   - O que sobra é a mesma UASG alternando modos ao longo do tempo dentro de um órgão: Exército com 56% e 2,9 órgãos
     efetivos.
   - Sem o Exército, o coeficiente vai a −1,94 (EP 2,35).
   - O WCR não rejeita (p = 0,19).
4. **Mesma UASG, mesmo produto e mesmo trimestre (M5):** +1,5 lp, com IC de ±13 lp.
   - Há só 568 células com os dois modos, 301 compras (0,5% das compras) e uma secretaria estadual com 42% da variação.
   - Na **mesma** amostra de M5, os outros modelos também dão perto de zero (M1: +0,1; M3: −1,1).
   - O resultado nulo de M5 é, portanto, um efeito de **amostra e de poder**, e não evidência de que o controle por UASG
     elimine a associação. A amostra é minúscula e diferente; nela nenhum modelo detecta nada.

## Controlar por CNPJ ≠ comparar só compras do mesmo CNPJ

- **Em M1**, uma compra AF do órgão g é comparada com compras A de **outros** órgãos do mesmo produto, UF e trimestre.
  - Remove-se de cada lado o nível médio de preço de cada órgão, estimado com todas as suas compras.
  - Todas as observações contribuem, inclusive as de células sem os dois modos, sob a hipótese aditiva de que as
    diferenças entre órgãos são constantes entre produtos e trimestres.
- **Em M3–M5**, só identificam as compras em células com os dois modos dentro do mesmo órgão ou da mesma UASG.

M1 tem por isso muito mais suporte (15 órgãos efetivos e 27 UFs, com SP em 22%). Em compensação, depende mais da
hipótese aditiva.

## Inferência

Pela regra predefinida (CR1 e WCR rejeitando a 5% e G* ≥ 20), **nenhum** modelo tem significância robusta.
- **M1:** CR1 e WCR rejeitam com folga, mas G* = 15.
  - As exclusões dos 10 órgãos mais influentes mantêm β entre −4,84 e −4,21.
  - Com CGM (CNPJ + produto), o EP é de 0,79; com cluster por UF, de 0,52.
  - A associação de cerca de −4,5% é estável, mas os erros-padrão por CNPJ não devem ser lidos como definitivos.
- **M2 e M3:** p muito pequenos, mas com 8,7 e 3,4 órgãos efetivos. A precisão aparente reflete poucos órgãos.
- **M4 e M5:** não há evidência estatística.

## Robustez

| Variante | M1 | M2 | M3 | M4 | M5 |
|---|---:|---:|---:|---:|---:|
| sem ln q | −5,80 | −5,23 | −5,95 | −4,71 | −7,29 |
| peso igual por compra | −3,93 | −6,70 | −6,93 | −8,12 | −3,09 |
| sem os trimestres incompletos (2026T2–T3) | −4,66 | −5,00 | −6,30 | −4,62 | +1,72 |

- **ln q:** compras maiores têm preço menor (γ de −10 a −14 lp por log-unidade). Controlar pela quantidade reduz
  ligeiramente a associação em M1.
- **Convergência:** verificada, com β idêntico por LSMR e por projeções alternadas puras e médias residuais por grupo
  ≤ 10⁻⁹.

## Leitura

A associação negativa de cerca de −4% a −6% entre AF e preço homologado persiste:
- com controles de UF × produto × trimestre e de órgão, nos níveis CNPJ e CNPJ × produto;
- nas comparações dentro do órgão.

À medida que a comparação fica mais restrita, ela passa a depender de pouquíssimas instituições, com o Exército no
centro. Na comparação dentro da mesma UASG e do mesmo período, a amostra é pequena demais para concluir qualquer coisa.

Nada disso identifica efeito causal: a escolha do modo continua endógena, e os estudos de eventos anteriores mostram
seleção antes das trocas.

**Limitações:**
- A UF é a administrativa da unidade compradora, pois não há UF de entrega no banco.
- A validação S1 é de catálogo, não de cada item.
