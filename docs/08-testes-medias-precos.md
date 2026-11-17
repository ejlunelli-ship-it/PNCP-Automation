**Testes de médias de preços por modo de disputa — resultados de 17/11/2026**

Foram executados testes de diferença de médias de Aberto versus Aberto-Fechado em pregões eletrônicos de materiais homologados do Compras.gov.br. Variáveis: log do preço unitário homologado, desconto sobre o estimado e preço/mediana de compras públicas comparáveis. [Arquivo completo e reprodução](../analises/README.md).

O primeiro desenho usa produto/mês/UF e tem 15 especificações. A execução seguinte separa orçamento sigiloso e não sigiloso, usa produto/ano/UF e tem 30 especificações. O principal mantém as classes prioritárias 6505/7510/7530/7930/8540; a ampliação para todas as classes é uma sensibilidade. Os relatórios preservam todas as amostras e resultados.

| Orçamento no teste anual | Desfecho | Itens A / AF | Diferença AF−A | p Holm, seis testes |
|---|---|---|---|---|
| Não sigiloso | Preço, transformação do contraste em log | 46.044 / 29.886 | −8,72% | 0,0158 |
| Não sigiloso | Desconto | 46.044 / 29.886 | +3,29 p.p. | 0,0158 |
| Não sigiloso | Preço/mediana anual | 26.078 / 13.893 | −275,88 unidades do índice | 0,7174 |
| Sigiloso | Preço, transformação do contraste em log | 18.033 / 15.392 | −3,43% | 0,7174 |
| Sigiloso | Desconto | 17.791 / 15.105 | +1,69 p.p. | 0,7174 |
| Sigiloso | Preço/mediana anual | 9.993 / 6.939 | +928,87 unidades do índice | 0,7174 |

Médias, intervalos, erros-padrão, t, graus de liberdade, significância bruta/ajustada e sensibilidades: [relatório anual](../analises/testes_medias_sigilo_anual_20261117/relatorio_completo.md) e [planilha](../analises/testes_medias_sigilo_anual_20261117/resultados_completos.xlsx).

Os testes são bilaterais, com padronização da composição de produtos/períodos/UF, agrupamentos CNPJ e CATMAT e correção Holm. O bootstrap por CNPJ é complementar, pois perde estratos sem suporte. No anual não sigiloso, a diferença de preço não mantém significância no bootstrap (p Holm=0,370); desconto mantém (0,018). Os índices em nível são dominados por extremos confirmados no cadastro, ainda sem equivalência física certificada.

A flag de sigilo é do item, no snapshot. Estimados positivos dos sigilosos permitem calcular desconto, mas não revelam quando o valor se tornou público. O benchmark anual usa os dois grupos de sigilo como doadores, exclui todo o CNPJ-alvo e exige cinco pregões de dois outros órgãos. É referência de compras públicas, não preço externo certificado de mercado. O controle anual não elimina sazonalidade/inflacão intranual; 2026 termina em abril nesta coorte.

As diferenças são associativas. Não significância não prova equivalência; diferença de significância entre grupos não testa diferença entre seus efeitos. Persistem seleção por homologação, equivalência técnica aproximada, condições de fornecimento não observadas e limitações de resultados ativos/lotes. O código, protocolos anteriores às estimativas, emenda metodológica mensal e validações estão versionados; bases e reamostragens volumosas ficam fora do Git.
