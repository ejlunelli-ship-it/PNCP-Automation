# Conclusão — validação técnica automática da cesta P1 (validador 2.0.0)

25/11/2026. Números de [`relatorio.md`](relatorio.md). Esta validação é **automática**, não é revisão humana: nenhum
formulário de revisor foi preenchido e nenhuma assinatura foi criada.

## Resultado

| Status / conjunto | Produtos | Compras | Itens | UASGs |
|---|---|---|---|---|
| S1 — `AUTO_VALIDADO_CATALOGO` | 3.065 | 74.167 | 708.964 | 4.141 |
| S2 — validado com ressalva (não é validação sem qualificação) | 107 | 15.361 | 43.863 | 2.751 |
| `AUTO_INCONCLUSIVO` | 949 | | | |
| `AUTO_DESMEMBRAR` (CP1860) | 1 | | | |
| S4 — `AUTO_VALIDADO_ITEM` | 29 compras | | 36 | 29 |
| S3 — candidatos P1 | 4.122 | 88.110 | 933.477 | 4.257 |

## Como ler

1. **S1 valida o catálogo, não as compras.**
   - A homogeneidade é demonstrada no nível do catálogo: cada uma das 6.282 variantes foi comparada atributo por atributo
     com as características oficiais do CATMAT. As variantes de S1 são o texto oficial do item, a menos de espaçamento,
     ou trazem todos os valores oficiais sem divergência de grandeza.
   - Isso mostra que as descrições ligadas às compras coincidem com o item oficial do catálogo. **Não** mostra que cada
     compra contratou exatamente esse objeto: marca, prazo, embalagem e exigências do edital ficam fora.
2. **A conformidade das contratações foi pouco verificada.**
   - Dos 400 termos de referência e editais lidos, só 38 traziam o CATMAT com todos os valores oficiais na vizinhança
     do código. Disso resultam 36 itens S4.
   - Os itens de famílias S1 sem documento examinado estão em `itens_sem_validacao_documental.csv.gz`.
   - Uma análise econométrica com S1 deve ser declarada como **baseada em equivalência de catálogo**, com risco residual
     de divergência nas contratações.
3. **Os inconclusivos vêm da exigência de atributos críticos por categoria de risco** (compatibilidade, material médico,
   peça, químico, eletrônico, medicamento).
   - As marcas de risco herdadas da auditoria 1.2.0 são ruidosas, então parte desses casos pode ser homogênea.
   - O erro, quando houver, é conservador: nada foi aprovado sem demonstração.
4. **CP1860:** o catálogo oficial diz «mandril de 1/2″»; 103 itens trazem «12″». A família foi desmembrada, e os dois
   subprodutos ficaram inconclusivos:
   - o subproduto divergente, porque não há documentação independente que sustente «12″»;
   - o subproduto conforme, porque o perfil de peça/compatibilidade exige um atributo que o catálogo não tem.
5. **Os 143 pendentes da auditoria:** em 72 deles, todas as variantes são o texto oficial; as divergências apontadas
   eram falhas da extração antiga. O resultado:
   - 56 viraram S1 e 47 viraram S2;
   - 40 seguem inconclusivos.

## Limitações

- Validação automática não garante ausência de erro.
- Equivalência textual não prova equivalência material.
- Equivalência de catálogo não prova conformidade individual.
- PDFs sem texto não foram lidos (sem OCR).
- A amostra documental é pequena.
- Nenhuma fonte técnica de nível 3 (normas, fabricantes) foi usada.
- A cesta não resolve a endogeneidade da escolha do modo nem as falhas de pré-tendência. O estudo econométrico
  continua exploratório.
- A integração em `integracao_econometria_automatica/` exige configuração própria no estudo; não há `cesta_validada.csv`.
