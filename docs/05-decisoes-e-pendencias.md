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
| 2026-11-03 | Banco SQLite unificado (ainda não criado): carregar **todos os modos de disputa** e filtrar na view; guardar o fornecedor vencedor do item | Evita recarregar a base; a análise escolhe os modos depois |
| 2026-11-03 | `melhor_lance_modo_fechado` em grupo = **só lances enviados na janela** da etapa fechada, igual ao item avulso. Na view do banco, `melhor_lance_apos_fechada` = melhor valor entre etapa aberta e fechada, e `ganho_fechada` parte dele (item AF sem melhora entra com ganho zero) | A coluna guarda o que aconteceu; calcular o ganho só com ela excluiria os itens sem lance fechado e superestimaria a média |
| 2026-11-03 | `dados/pncp.db` criado por `banco_unificado.py`: `id` próprio e `registro_principal` (uma linha por item), `homologado` = situação do item "Homologado", valores em `REAL`, descontos por etapa só em Menor preço | Um item pode ter mais de um registro na API; `NUMERIC` causava divisão inteira; em Maior desconto o lance do PDF pode ser percentual |
| 2026-11-03 | OCR pelo PyMuPDF com `por.traineddata`, no lugar de OCRmyPDF + Tesseract + Ghostscript | Não exige instalar nada no sistema |
| 2026-11-03 | Baixar relatórios **só de pregões Aberto-Fechado com item homologado** (98.461 pregões e 1.779.542 itens na base de 2026-11-03) | No Aberto-Fechado o melhor lance de cada etapa só existe no PDF. No Aberto, usa-se o resultado da API, que é o valor homologado e pode diferir do melhor lance (negociação ou desclassificação) |
| — | Melhor lance da etapa conta mesmo se o fornecedor for desclassificado depois; propostas iniciais entram na etapa aberta | Medir a dinâmica da disputa, não só o resultado |

## Pendências e próximos passos (por prioridade)

1. **Fechar o suporte a itens em grupo** (parser 1.6.0 lê os PDFs de grupo; ver [04 §4.2](04-formato-dos-relatorios.md)):
   - `melhor_lance_modo_fechado` em grupo = só lances enviados na janela (decidido em 2026-11-03,
     ver tabela acima);
   - testado só em Fortaleza 90119/2025 (Aberto-Fechado, um grupo). Falta testar em outros órgãos e
     em grupo no modo Aberto;
   - o nome do arquivo de grupo dentro do zip do Compras.gov.br é desconhecido, e `selecao.py` só
     aceita `...-item-N.pdf`;
   - verificar se os "parciais" de Fortaleza (90122, 90124, 90128) também são grupos.
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
8. **Revisar a chave de dedup do `coleta_itens.py`**: `(compra, item, idCompraItem)` guarda um só registro quando o item tem mais de um resultado, e isso aparece nos arquivos `adicional_correspondencias`, que não têm script no repositório. Verificar se os meses perdem o segundo resultado.
9. **Registrar o motivo por compra em `pncp_arquivos.py`** (a fazer depois do piloto de janeiro/2026): separar erro na API,
   nenhum arquivo publicado, nenhum candidato e candidato rejeitado (grupo, sem texto, outra compra).
   Sem isso, "sem termos no PNCP" mistura ausência real com falha. Ver [03 §3.4](03-fontes-de-dados-e-apis.md).
10. **OCR de PDF escaneado**: o PyMuPDF lê o texto, mas perde a linha do título e muda as quebras de linha
    (130 de 427 linhas idênticas num teste com páginas convertidas em imagem), e o parser depende
    delas. O resultado é `ERRO`, sem dado errado. Falta adaptar o parser, de preferência com um PDF
    escaneado real, e aplicar OCR em `pncp_arquivos._identificar`.

## Questões em aberto

- Proposta inicial de fornecedor depois inabilitado deve definir o melhor lance aberto? Em Fortaleza
  90119/2025, item 1, ela dá 0,53 contra 0,74 dos lances, e o `ganho_fechada` zera.
- Quanto do desconto do AF vem da etapa fechada (ganho médio da fechada sobre a aberta)?
- O efeito Aberto vs AF difere entre material e serviço, e por esfera?
- A amostra com PDF (órgãos que publicam ou zips baixados à mão) é representativa da base nacional?
