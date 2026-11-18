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
| 2026-11-03 | Guardar candidatos que o extrator não lê em `outros_formatos/`, com manifesto; registrar o motivo por compra em `motivos.csv` | O objetivo é ter todo formato com lances e adaptar o leitor depois; "sem termos" misturava ausência real com falha |
| 2026-11-06 | Trazer do PNCP os pregões fora da API Dados Abertos (`coleta_pncp.py`), de 2022-11 a 2026-10, Eletrônico e Presencial, todos os modos, com `compras.fonte = 'pncp'` | Pedido do usuário: a base tinha 29,8% dos Pregões Eletrônicos do PNCP (43,8% no Aberto-Fechado) |
| 2026-11-06 | Duplicado é o mesmo `numeroControlePNCP` ou a irmã com mesmo CNPJ, ano, número e abertura. A irmã não entra em `compras` e fica em `compras_duplicadas` | O mesmo pregão publicado por dois sistemas contaria duas vezes |
| 2026-11-06 | Brutos do PNCP em `dados/brutos_pncp/` (JSON com gzip, sem CSV), recarregados por `--recriar` | A coleta leva dias; sem os brutos, recriar o banco a perderia |
| 2026-11-16 | Varrer o PNCP de 2026-03 a 2026-10 (`baixar_api.py`) e, em paralelo, baixar os zips à mão de 2026-10 para trás (`baixar_manual.py`), com o que já foi feito anotado em disco e em `manual.csv` | Pedido do usuário: as duas frentes andam juntas sem repetir compra |
| 2026-11-16 | Registro do que foi buscado/baixado versionado em `registro/`, um CSV por usuário, mês e origem (`api`/`manual`), só com acréscimo de linhas; divisão entre usuários por `--parte k/n`; inclui as buscas do PNCP sem resultado | Download colaborativo com mais de um usuário sem conflito de merge e sem repetir busca; os PDFs ficam fora do git |
| 2026-11-16 | Lista das compras a baixar versionada em `registro/compras/<mês>.csv`, usada quando não há `pncp.db` | Quem só baixa não precisa copiar os 16 GB do banco |
| 2026-11-17 | Automatizar o clique do download do zip com userscript no navegador real (`baixar_manual.py --auto`, `navegador/compras_auto.user.js`) em vez de Playwright; chamar a URL do zip direto foi descartado | A URL exige um token novo do hCaptcha a cada requisição; o userscript usa o token gerado pelo próprio site, sem marcas de automação, e o usuário resolve os desafios |
| 2026-11-18 | Itens REVISAR da extração: **ficam fora da análise** (filtrar `status_extracao = 'OK'`) os de etapa fechada com lances na tabela mas sem lances na mensagem de encerramento, os sem proposta identificada e os de etapa/desempate sem registro de encerramento. Fornecedor estrangeiro (`Identificador ESTRANG…`) passa a ser lido (parser 1.7.2); participante com lance sem proposta listada vira aviso e o item fica OK, sem conferência manual | Decisão do usuário: na dúvida sobre a etapa, excluir; os valores do participante sem proposta são confiáveis. Na base de 2026-02/03/04/08, 110 itens de 180.909 ficam de fora |
| — | Melhor lance da etapa conta mesmo se o fornecedor for desclassificado depois; propostas iniciais entram na etapa aberta | Medir a dinâmica da disputa, não só o resultado |
| 2026-11-18 | Itens com lance fechado acima do aberto: manter `após a fechada = mín(aberto, fechado)` (líder sem lance fechado e etapa reiniciada são o funcionamento normal). Desconto final decomposto em **aberta + ganho da fechada + ajuste pós-disputa** (desclassificação/negociação). Lance aberto absurdo, fechado absurdo e "vencedor caiu" viram marcas com sensibilidade, sem corrigir valores | Decisão do usuário a partir da revisão de PDFs de 2026-02. Ver `analise/etapas_pdf_af_20261118/relatorio.md` (seção "Casos com lance fechado acima do aberto") |

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
   - extração de 2026-08 feita em `dados/extracao/aberto-fechado_2026-08.db` (17/11/2026); falta a carga
     no `pncp.db` e os demais meses;
   - chave `id_compra` (do nome do PDF) + `numero_item`, `registro_principal = 1`: liga 97,3% em 2026-08
     (UASG + número dá menos, por zeros à esquerda); ver [07 §7](07-metodologia-de-extracao.md);
   - 1.397 itens de 2026-08 com a compra no banco, mas sem o item: investigar antes da carga;
   - 97 PDFs de 2026-08 sem bloco de item reconhecido (formato a examinar);
   - criar uma análise (`matching_etapas.py`?) com o desconto da etapa aberta, o desconto da etapa
     fechada e o ganho da fechada, com e sem pareamento UASG × item.
3. **Ampliar a amostra de PDFs**:
   - mapear quais órgãos publicam termos no PNCP: varrer AF/Aberto por mês e contar por CNPJ os
     que têm termo (tipo 16/26 com conteúdo válido);
   - priorizá-los no `get.py --orgaos`.
4. **Parser da "Ata Final" do Portal de Compras Públicas** (ver [04 §4.3](04-formato-dos-relatorios.md)).
   Essas compras já estão na base (`fonte = 'pncp'`, `usuario_nome` = "ECustomize Consultoria em Software S.A"),
   mas o `baixar_api.py` não as seleciona (sem `id_compra`) e `_identificar` só reconhece termos do
   Compras.gov.br. Estudar primeiro o exemplo AF de Vitória 123/2025. O modo vem da API; a etapa de cada
   lance precisa de marcos no chat dessa plataforma.

   **Amostra de 2026-11-16** (3 compras AF com resultado de cada uma das 10 plataformas com mais compras na
   base `fonte = 'pncp'`): no período de nov/2025 a out/2026 são ~32 mil compras AF homologadas fora do
   Compras.gov.br, contra ~36 mil dentro.
   - ECustomize (Portal de Compras Públicas, a maior): as 3 com `Ata_Final_*.zip` e `Ata_Parcial_*.zip`.
     É a fonte mais promissora; medir numa amostra maior quantas trazem os lances por etapa.
   - Licitações-e (BB): "Ata do Processo" em PDF com texto, com proposta e melhor lance por fornecedor,
     sem separar etapa aberta e fechada (o histórico de lances só fica no site). Não serve para a etapa.
   - BLL: termos de adjudicação e homologação, sem lances.
   - IPM, Licitanet, Licitar Digital, Betha, Governançabrasil, Portal MG, Bahia: só o edital.
5. **Atas de registro de preços** (PNCP `/atas`, Dados Abertos `modulo-arp`): o usuário perguntou;
   ainda não implementado nem priorizado.
6. Compra marcada `.pncp_parcial` não é reconsultada no PNCP. Se o órgão publicar depois, só o zip
   resolve. Avaliar uma opção `--reconsultar-pncp`.
7. **`baixar_manual.py --auto`** (userscript, desde 2026-11-17). Primeiro teste em 2026-08, com
   `--intervalo 0`: cerca de 6 s por compra e nenhum desafio do hCaptcha em mais de 800 zips. Falta ver
   se o ritmo se mantém em rodadas longas e com mais de um usuário (`--parte`). O Playwright com perfil
   persistente fica como alternativa se o userscript deixar de bastar (risco: mais desafios do hCaptcha).
   Os zips só com relatórios por grupo (cerca de 12%) dependem da pendência 1.
8. **Usar a tabela `resultados` na análise** (coleta interrompida em 2026-11-03 a pedido do usuário; retoma com `python coleta_resultados.py`): o valor de `itens` diferiu do resultado ativo em 118 de 11.639 itens (1,0%) em dois dias testados.
   Depois da coleta (`coleta_resultados.py`) e da carga (`banco_unificado.py --resultados`), medir a diferença na base toda e decidir
   se `desconto_final` passa a usar o resultado ativo. Os meses de itens já coletados não foram refeitos com a nova chave.
10. **OCR de PDF escaneado**: o PyMuPDF lê o texto, mas perde a linha do título e muda as quebras de linha
    (130 de 427 linhas idênticas num teste com páginas convertidas em imagem), e o parser depende
    delas. O resultado é `ERRO`, sem dado errado. Falta adaptar o parser, de preferência com um PDF
    escaneado real, e aplicar OCR em `pncp_arquivos._identificar`.

11. **Decidir como as análises tratam `fonte = 'pncp'`.** `analise_itens` agora mistura as duas fontes: filtre `fonte` para repetir os números antigos. Ver os cuidados em [06](06-banco-de-dados.md).
12. **Atualizar compras recentes do PNCP.** A coleta de 2022-11 a 2026-10 terminou em 2026-11-10: 772.894 compras novas, 25,1 milhões de itens e 12,5 milhões de resultados, com 20 compras sem itens. A base passou a ter 97,7% dos Pregões Eletrônicos do PNCP (ver [03](03-fontes-de-dados-e-apis.md) e [06](06-banco-de-dados.md)). `coleta_pncp.py` não recarrega mês já carregado, e os meses recentes têm poucos resultados: 2026-10 tem 112 mil resultados para 714 mil itens, contra 425 mil para 714 mil em 2026-06. Falta uma opção para refazê-los, por exemplo de 2026-06 a 2026-10, daqui a alguns meses.
13. **Medir falsos positivos das irmãs.** A chave foi conferida em 2 pares de Fortaleza; falta conferir uma amostra de `compras_duplicadas`, por exemplo pelo objeto.
14. **Reprocessar 2026-03, 04 e 08 com o parser 1.8.0 e refazer a análise com os campos novos.** Os campos para os
    casos com lance fechado acima do aberto (decisão de 2026-11-18) estão no parser 1.8.0 ([07 §6](07-metodologia-de-extracao.md)):
    `cnpj_melhor_lance_aberto`, `melhor_lance_modo_aberto_outro_fornecedor`, `lider_aberto_lance_fechado`,
    `reinicios_etapa_fechada`, `fornecedores_desclassificados`, `quantidade_desclassificados`,
    `melhor_lance_modo_aberto_validos` e `melhor_lance_modo_fechado_validos`.
    - **Feito (18/11/2026):** 2026-02 reprocessado em `dados/extracao/aberto-fechado_2026-08.db` (34.933 itens, OK 34.917);
      as colunas anteriores ficaram idênticas às da 1.7.x. O banco hoje mistura 1.8.0 (fevereiro) e 1.7.x (demais meses,
      com as colunas novas vazias): filtre por `versao_parser` ao usar os campos novos.
    - **Falta:** trazer de volta a `dados/filtrados/` os PDFs de 2026-03, 04 e 08 (ausentes em 18/11/2026) e rodar
      `python -m extrator_homologacao dados/filtrados/aberto-fechado_<mês>/relatorios --saida dados/extracao/aberto-fechado_<mês>.xlsx --db dados/extracao/aberto-fechado_2026-08.db --workers 7 --sem-separar`
      para cada mês (a versão nova invalida o cache; não precisa de `--reprocessar`). Depois, refazer
      `analise/etapas_pdf_af_20261118/decomposicao_marcas.py` trocando as marcas provisórias pelas do parser: aberto isolado =
      melhor aberto < 50% de `melhor_lance_modo_aberto_outro_fornecedor`; etapa reiniciada = `reinicios_etapa_fechada > 0`;
      sensibilidade "só fornecedores válidos" com os campos `_validos`. Fazer o mesmo para 2026-01 e os meses de 2025 ao
      extraí-los.
    - **Primeiros números (fevereiro, 34.436 itens OK de Menor Preço):** nos 2.726 com fechado acima do aberto, o líder da
      aberta nunca deu lance fechado; em 1.560 deles o líder foi desclassificado e em 830 houve reinício. O líder foi
      desclassificado em 29% dos itens. Lance aberto isolado (< 50% do outro fornecedor): 1.837 itens, 1.109 com o líder
      desclassificado. Só com fornecedores válidos, o valor final é o melhor lance da disputa em 92,0% dos itens (69,8%
      com todos), fica acima em 0,1% e abaixo (negociação) em 7,8%.

## Questões em aberto

- **17/11/2026 — comparação anual por sigilo concluída:** [testes e documentação versionados](08-testes-medias-precos.md), com 30 especificações, seis testes principais, Holm e bootstrap complementar. O desconto dos sigilosos utiliza apenas estimados positivos disponíveis no snapshot. Resultados e limitações não identificam efeito causal. A auditoria dos índices extremos continua pendente de documentação física do fornecimento.

- **17/11/2026 — testes de médias concluídos:** [relatório e arquivos](../analises/testes_medias_20261117/relatorio_completo.md). Log do preço: associação negativa no teste principal, com sensibilidade à inferência; desconto e razão preço/mediana sem diferença significativa no principal após Holm. A razão em nível é dominada por extremos confirmados no cadastro, ainda sem certificação de equivalência física. Prioridade de auditoria: CATMAT 268493, item `id=1114157`, preço registrado 16.100, quantidade 1 e apresentação COMPRIMIDO versus mediana 0,068; não corrigido por conjectura. Banco preservado; testes não identificam efeito causal.

- Proposta inicial de fornecedor depois inabilitado deve definir o melhor lance aberto? Em Fortaleza
  90119/2025, item 1, ela dá 0,53 contra 0,74 dos lances, e o `ganho_fechada` zera.
- Quanto do desconto do AF vem da etapa fechada (ganho médio da fechada sobre a aberta)?
- O efeito Aberto vs AF difere entre material e serviço, e por esfera?
- A amostra com PDF (órgãos que publicam ou zips baixados à mão) é representativa da base nacional?
