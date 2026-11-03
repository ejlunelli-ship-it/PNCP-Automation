# 5. Decisões e pendências

Atualize este arquivo ao tomar uma decisão ou concluir um passo (com data).

## Decisões tomadas

| Data | Decisão | Motivo |
|---|---|---|
| 2026-11-02 | **Não contornar o hCaptcha** do Compras.gov.br (sem solvers, sem tokens, sem endpoints internos) | Controle de acesso deliberado de sistema público |
| 2026-11-02 | Download em duas camadas: PNCP automático (`pncp_arquivos.py`) e depois o navegador com clique manual | O PNCP é público e cobre alguns órgãos; o resto exige o zip |
| 2026-11-02 | Validar os PDFs do PNCP pelo **conteúdo** (tipo + UASG + número), não pelo título | Cada órgão nomeia de um jeito |
| 2026-11-02 | Procurar contratações "irmãs" no PNCP (mesmo CNPJ, número e abertura) | Órgãos como Fortaleza publicam o mesmo pregão duas vezes; os termos ficam na do órgão |
| 2026-11-02 | `pendentes.csv` por pasta, refeito a cada rodada | Saber o que falta baixar à mão |
| — | Melhor lance da etapa conta mesmo se o fornecedor for desclassificado depois; propostas iniciais entram na etapa aberta | Medir a dinâmica da disputa, não só o resultado |

## Pendências e próximos passos (por prioridade)

1. **Suporte a itens em grupo no extrator** (ver [04 §4.2](04-formato-dos-relatorios.md)):
   - reconhecer `Item N do Grupo GX - …` em `secoes.py`;
   - herdar do bloco do grupo a janela da etapa fechada e, se preciso, o fornecedor aceito;
   - conferir a lista do encerramento pela **soma do grupo** (último valor de cada convocado por
     item × quantidade);
   - nova coluna `grupo` (ex.: `G1`), vazia para item avulso;
   - **decidir**: `melhor_lance_modo_fechado` em grupo = só lances enviados na janela (recomendado,
     coerente com item avulso) **ou** valor efetivo de cada convocado (incluindo o que ficou do
     aberto)?
   - `pncp_arquivos._identificar` também deve aceitar grupos. Hoje Fortaleza 90119 aparece como
     "parcial 3/9", mas o PNCP tem os 9 itens.
   - Verificar se os outros "parciais" de Fortaleza (90122, 90124, 90128) também são grupos.
   - Incrementar `VERSAO_PARSER`.
2. **Juntar a base do PDF com a base da API** para o matching por etapa:
   - chave `uasg` + `numero_compra` + `item`; via `idCompra`, chega-se ao `numeroControlePNCP` e
     ao `codItemCatalogo`;
   - criar uma análise (`matching_etapas.py`?) com o desconto da etapa aberta, o desconto da etapa
     fechada e o ganho da fechada, com e sem pareamento UASG × item.
3. **Ampliar a amostra de PDFs**:
   - mapear quais órgãos publicam termos no PNCP: varrer AF/Aberto por mês e contar por CNPJ os
     que têm termo (tipo 16/26 com conteúdo válido);
   - priorizá-los no `get.py --orgaos`.
4. **Parser da "Ata Final" do Portal de Compras Públicas** (ver [04 §4.3](04-formato-dos-relatorios.md)).
   Estudar primeiro o exemplo AF de Vitória 123/2025. O modo vem da API; a etapa de cada lance
   precisa de marcos no chat dessa plataforma.
5. **Atas de registro de preços** (PNCP `/atas`, Dados Abertos `modulo-arp`): o usuário perguntou;
   ainda não implementado nem priorizado.
6. Compra marcada `.pncp_parcial` não é reconsultada no PNCP. Se o órgão publicar depois, só o zip
   resolve. Avaliar uma opção `--reconsultar-pncp`.
7. Prototipar o Playwright com perfil persistente para abrir a compra e clicar no menu, com o
   captcha resolvido pelo usuário. Risco: a automação pode aumentar os desafios do hCaptcha.

## Questões em aberto

- Quanto do desconto do AF vem da etapa fechada (ganho médio da fechada sobre a aberta)?
- O efeito Aberto vs AF difere entre material e serviço, e por esfera?
- A amostra com PDF (órgãos que publicam ou zips baixados à mão) é representativa da base nacional?
