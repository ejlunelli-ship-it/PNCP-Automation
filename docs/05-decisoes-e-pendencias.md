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
| 2026-11-20 | **Bases separadas por versão do parser.** A base nova `dados/extracao/aberto-fechado_parser-1.9.1.db` reúne todos os meses extraídos na 1.9.1 (hoje 2024-01, 02, 11, 12; 2025-01, 02). A base antiga `aberto-fechado_2025-03_a_2026-10.db` mantém os meses em 1.8.0 e 1.9.0, sem itens 1.9.1 | Decisão do usuário: não misturar versões do parser na mesma base |
| — | Melhor lance da etapa conta mesmo se o fornecedor for desclassificado depois; propostas iniciais entram na etapa aberta | Medir a dinâmica da disputa, não só o resultado |
| 2026-11-18 | **Duas medidas principais** do desconto por etapa nos PDFs, sempre reportadas juntas: **todos os fornecedores** (melhor lance de cada etapa como na disputa) e **só fornecedores válidos** (sem desclassificados, recusados e inabilitados; colunas `_validos` do parser 1.8.0). Procedimento em `analise_etapas.py` ([07, Análise](07-metodologia-de-extracao.md)) | Decisão do usuário. A primeira descreve a dinâmica da disputa; a segunda, o desconto que o órgão obtém de cada etapa. O desconto final é o mesmo nas duas. Em 2026-02 o ganho da fechada é 14,8 e 13,2 p.p. |
| 2026-11-19 | **Layout antigo dos termos** (PDFs emitidos até fev/2025, ex.: compras de 2023): ler pelo texto refeito na ordem visual da página (parser 1.9.0, [04 §4.1](04-formato-dos-relatorios.md)). Onde o relatório não traz o dado: `valor_estimado_total` = estimado × quantidade e, com "Menor Preço / Maior Desconto" na compra, critério do item pelo formato dos valores (`P% (R$ V)` → Maior Desconto; só R$ → Menor Preço; sem valores → vazio). As duas inferências ficam anotadas em `fontes_extracao` | Pedido do usuário (extrair 2023). Sem o total, os itens saem da regressão do `analise_etapas.py` (filtro `valor_estimado_total > 0`); sem o critério, saem da amostra (só Menor Preço). No layout atual, total = unitário × quantidade, e os dois formatos de valor não se misturam num item |
| 2026-11-20 | **Regressão por etapa = efeito fixo de item, em primeira diferença** (`analise_etapas.py`): `100·[ln(após a fechada) − ln(aberto)]` do mesmo item sobre constante (β) e moderadores centrados (licitantes, valor, mês, sigilo, serviço). Erro-padrão agrupado por UASG, que é o conglomerado e não um efeito fixo. Especificação em [07, Análise](07-metodologia-de-extracao.md) | Pedido do usuário: a comparação entre etapas deve absorver tudo que é específico do item, e efeito fixo de UASG não faz isso. O script já estimava assim; o rótulo "efeitos fixos de UASG" usado ao apresentar os 31 meses estava errado. Conferido: o painel empilhado com efeito fixo de item dá os mesmos coeficientes. Nas entradas de análise abaixo, "Regressão (N UASGs)" é o número de conglomerados |
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
   - **Feito (19/11/2026):** download de 2023 concluído (2023-04 a 2023-12, sem pendentes; ver histórico em
     [07](07-metodologia-de-extracao.md)). Antes de 2023-04 não há compra
     Aberto-Fechado com item homologado (os itens com resultado estão "Em andamento"); decidir se vale tentar o zip
     dessas cerca de 77 compras por uma lista à parte.
   - **Feito (20/11/2026, segunda máquina):** download de 2025-02 a 2024-10 concluído com os 3 navegadores (uma janela
     por navegador, `--parte k/3`): 2025-02 com 2.119 de 2.675 compras com termos, 2025-01 1.961 de 2.500, 2024-12
     2.989 de 3.900, 2024-11 2.660 de 3.362 e 2024-10 2.948 de 3.633 (detalhe por motivo no histórico de
     [07](07-metodologia-de-extracao.md)). **Falta:** 2024-09 a 2024-06 (pausado a pedido; o segundo usuário sobe a partir
     de 2024-01 e tem 2024-03 parcial, combinar onde se encontram), repetir com `--repetir --motivo` as 19 "zip não
     recebido" e as 18 "sem botão de downloads" desses meses, e extrair os PDFs.
   - **Feito (20/11/2026):** 2023 extraído com o parser 1.9.0, que lê o layout antigo dos termos (99% dos PDFs de 2023;
     [04 §4.1](04-formato-dos-relatorios.md)), num banco próprio, `dados/extracao/aberto-fechado_2023-04_a_2023-12.db`:
     96.758 PDFs, OK 96.559, REVISAR 198, ERRO 1; 96.757 itens. Juntado à base `aberto-fechado_2025-03_a_2026-10.db`
     (nome mantido; backup `.antes-2023.db`): 96.754 itens novos (3 já estavam em 2025-09), 985.435 no total.
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
    - **Análise de fevereiro feita (18/11/2026):** `analises/etapas_pdf_af_20261118/fevereiro_campos_novos.py` e a
      seção "Fevereiro com os campos do parser 1.8.0" do `relatorio.md`. Só com fornecedores válidos, o ganho da fechada
      cai de 14,8 para 13,2 p.p. (β de −24,0 para −20,6 log-pontos), o ajuste pós-disputa vai de −4,1 para +0,8 p.p. e a
      moderação pelo nº de licitantes de −6,4 para −2,5. **Decidido (18/11/2026):** as duas medidas são principais
      (tabela de decisões); procedimento replicável em `analise_etapas.py`.
    - **Feito (18/11/2026):** 2025-11 extraído com o parser 1.8.0 (50.259 itens; OK 50.092 PDFs, REVISAR 265) numa nova
      versão da base, `dados/extracao/aberto-fechado_20261118.db` (base anterior + 2025-11, 231.168 itens). Use essa base
      daqui em diante; `aberto-fechado_2026-08.db` fica como versão anterior.
    - **Feito (18/11/2026):** 2025-10 extraído com o parser 1.8.0 na mesma base (60.464 itens; OK 60.150 PDFs, REVISAR 410);
      a base tem 291.632 itens (2025-10, 2025-11 e 2026-02 em 1.8.0; 2026-03, 04 e 08 em 1.7.x).
    - **Feito (18/11/2026):** nova versão da base, `dados/extracao/aberto-fechado_2025-10_a_2026-08.db` (487.848 itens),
      somando a base de outra máquina (`dados/filtrados/aberto-fechado_2025-12_a_2026-07.db`: 2025-12, 2026-01, 05, 06 e 07
      em 1.8.0). Itens repetidos: 1.8.0 substitui 1.7.x, mantendo o mês local (regra em docs/07, histórico). Use esta base
      daqui em diante. Ainda em 1.7.x: 117.319 itens de 2026-03, 04 e 08 (PDFs ausentes aqui). Juntar as duas bases com
      `--db` repetido não funciona: os 29.255 itens repetidos fazem o `analise_etapas.py` parar.
    - **Feito (18/11/2026):** 2025-09 extraído com o parser 1.8.0 na mesma base (55.841 itens; OK 55.469 PDFs, REVISAR 497).
      A base `aberto-fechado_2025-10_a_2026-08.db` (nome mantido) tem 543.689 itens, de 2025-09 a 2026-08.
      A análise dos 8 meses (abaixo) não inclui 2025-09; a dos 9 meses, sim.
    - **Feito (19/11/2026):** 2025-08 extraído com o parser 1.8.0 na mesma base (50.920 itens; OK 50.466 PDFs, REVISAR 769;
      315 PDFs ignorados sem uasg/compra/item, de 14 compras, ver pendência 15). A base (nome mantido) tem 594.609 itens,
      de 2025-08 a 2026-08; backup `aberto-fechado_2025-10_a_2026-08.antes-2025-08.db`. O download de 2025-08 está
      completo: das 3.372 compras, 2.915 completas (nesta pasta ou na de outro mês), 418 zip sem termos, 31 sem a opção
      no site e 8 sem acesso; nenhuma deixou de ser tentada.
    - **Análise dos 10 meses em 1.8.0 (19/11/2026, com `--pncp-db`):** 2025-08 a 2026-02 e 2026-05 a 07; saída em
      `dados/analise_etapas/2025-08_a_2026-07/`. 412.142 itens (todos) e 365.071 (válidos), 22.759 compras, 1.757 UASGs.
      Aberta 19,1% / 19,1%; após a fechada 34,3% / 32,9%; **ganho da fechada 15,2 p.p. (IC 14,9–15,5) e 13,8 p.p.
      (13,5–14,1)**; ganho relativo 18,5% / 16,5%; final 33,6% / 33,7%; final = melhor lance em 70% / 93%. Decomposição
      (360.269): todos 21,9 + 15,9 − 4,1; válidos 19,2 + 13,8 + 0,7 = 33,7. Regressão (1.755 / 1.752 UASGs): β −24,5 e
      −21,4; licitantes −4,8 e −0,8 (p = 0,010); sigilo +1,9 (p = 0,006) e +1,1 (p = 0,09); serviço −1,2 (n.s.) e −2,8
      (p = 0,022). 2025-08 sozinho: aberta 21,2 / 20,7, ganho 14,7 / 13,4 p.p. (o mês tem a etapa aberta mais forte,
      junto com 2026-05). Ganho por mês (todos) entre 14,5 (2025-12) e 16,2 (2025-09); válidos entre 13,1 e 14,9.
      Marcas: líder da aberta sem lance fechado 30%, líder desclassificado 28%, reiniciada 10%, aberto isolado 5%,
      fechado outlier 1,5%; fechado acima do aberto 8,7%.
    - **Feito (19/11/2026):** 2025-06 e 2025-07 (extraídos em 1.8.0 na segunda máquina, banco `junho2025.db`, copiado para
      `dados/filtrados/junho2025.db` e lido só para leitura) incorporados à base `aberto-fechado_2025-10_a_2026-08.db`
      (nome mantido): 2025-06 com 40.649 itens (OK 40.175, REVISAR 474, 2.589 compras) e 2025-07 com 48.917 (OK 48.383,
      REVISAR 534, 2.880 compras, o mês inteiro). Nenhum item repetido. A base tem 684.175 itens, de 2025-06 a 2026-08,
      12 meses completos em 1.8.0. Backup `aberto-fechado_2025-10_a_2026-08.antes-2025-06-07.db`.
    - **Feito (19/11/2026):** 2025-05 e 2025-04 extraídos com o parser 1.8.0 na mesma base (nome mantido; backup
      `aberto-fechado_2025-10_a_2026-08.antes-2025-05-04.db`). 2025-05: 46.523 PDFs (OK 43.962, REVISAR 2.561), 44.483 itens
      gravados (OK 43.962, REVISAR 521), 2.717 compras. 2025-04: 42.563 PDFs (OK 40.354, REVISAR 2.208, ERRO 1), 40.864 itens
      (OK 40.354, REVISAR 510), 2.449 compras. A base tem 769.522 itens, de 2025-04 a 2026-08; os outros meses não mudaram.
      O ERRO é um PDF vazio (`90001-2025_16038405900012025/...-item-101.pdf`, 0 byte, gravado quando o download foi
      encerrado às 14:26). **Resolvido** na extração de 2025-03: a compra também está na lista de março, foi baixada
      inteira lá (134 PDFs) e os itens passaram a ter `arquivo_origem` em 2025-03 (ver abaixo).
    - **Feito (19/11/2026):** 2025-03 extraído com o parser 1.8.0 na mesma base (backup
      `aberto-fechado_2025-10_a_2026-08.antes-2025-03.db`), em duas rodadas: a segunda, pelo cache, só leu os PDFs das
      repetições baixadas durante a primeira. 39.181 PDFs (OK 35.900, REVISAR 3.281), 36.190 itens gravados (OK 35.900,
      REVISAR 290), 2.071 compras; 2.991 PDFs de 133 compras sem bloco de item (pendência 15). A compra
      `16038405900012025` está nas listas de março e de abril: a cópia de março (134 itens) substituiu, pela chave
      (uasg, modalidade, compra, item), os 117 itens de abril, e 2025-04 passou de 40.864 para 40.747 itens. Nenhum item
      repetido. A base tem 805.595 itens, de 2025-03 a 2026-08.
    - **Análise dos 15 meses em 1.8.0 (19/11/2026, com `--pncp-db`):** 2025-03 a 2026-02 e 2026-05 a 07; saída em
      `dados/analise_etapas/2025-03_a_2026-07/`. 604.924 itens (todos) e 535.367 (válidos), 34.237 compras, 1.934 UASGs.
      Aberta 19,6% / 19,5%; após a fechada 34,7% / 33,2%; **ganho da fechada 15,1 p.p. (IC 14,9–15,3) e 13,7 p.p.
      (13,5–13,9)**; ganho relativo 18,4% / 16,5%; final 34,0% / 34,1%; final = melhor lance em 70% / 93%. Decomposição
      (527.801): todos 22,4 + 15,8 − 4,1; válidos 19,7 + 13,8 + 0,7 = 34,1. Regressão (1.932 / 1.927 UASGs): β −24,4 e
      −21,4; licitantes −4,8 e −0,8 (p = 0,007); sigilo +2,1 (p < 0,001) e +1,5 (p = 0,007); serviço −1,1 (n.s.) e −2,3
      (p = 0,007). 2025-03: aberta 20,3, ganho 14,7 / 13,5. Ganho por mês (todos) entre 14,2 (2025-04) e 16,2 (2025-09);
      válidos entre 12,8 e 14,9. Marcas: líder sem lance fechado 29,9%, líder desclassificado 27,7%, reiniciada 10,0%,
      aberto isolado 5,4%, outlier 1,6%; fechado acima do aberto 8,9%.
    - **Nova versão da base (19/11/2026):** `dados/extracao/aberto-fechado_2025-03_a_2026-10.db` = cópia de
      `aberto-fechado_2025-10_a_2026-08.db` (mantida como estava) + `dados/filtrados/aberto-fechado_2026-09_a_2026-10.db`
      (extraído em 1.8.0 em outra máquina, lido só para leitura, hash conferido antes e depois). 2026-09 com 44.068 itens
      e 2026-10 com 39.018 (todos 1.8.0; 84 REVISAR). 316 itens de 2 compras (`98028605900062025`, 309, e
      `92833305900072025`, 7), que estão nas listas de 2025-04 e de 2026-09, já estavam na base como 2025-04, com os
      mesmos PDFs (hash) e os mesmos valores: ficaram como estavam (`INSERT OR IGNORE`). A base tem 888.681 itens, de
      2025-03 a 2026-10, sem item repetido; `integrity_check` ok.
    - **Análise dos 17 meses em 1.8.0 (19/11/2026, com `--pncp-db`, base `aberto-fechado_2025-03_a_2026-10.db`):**
      2025-03 a 2026-02, 2026-05 a 07 e 2026-09 a 10; saída em `dados/analise_etapas/2025-03_a_2026-10/`. 679.977 itens
      (todos) e 601.186 (válidos), 38.602 compras, 2.099 UASGs. Aberta 19,2% / 19,2%; após a fechada 34,4% / 33,0%;
      **ganho da fechada 15,2 p.p. (IC 15,0–15,4) e 13,8 p.p. (13,6–14,0)**; ganho relativo 18,5% / 16,6%; final 33,8% /
      33,9%; final = melhor lance em 70% / 93%. Decomposição (592.998): todos 22,1 + 15,9 − 4,1; válidos 19,4 + 13,9 + 0,7
      = 33,9. Regressão (2.096 / 2.091 UASGs): β −24,5 e −21,5; licitantes −5,0 e −0,9 (p = 0,001); sigilo +2,0
      (p = 0,001) e +1,3 (p = 0,014); serviço −0,7 (n.s.) e −2,1 (p = 0,009). 2026-09: aberta 16,6, ganho 15,9 / 14,4;
      2026-10: aberta 16,7, ganho 16,2 / 14,8 (a etapa aberta desses dois meses é a mais fraca da série, ~3 p.p. abaixo
      da média). Ganho por mês (todos) entre 14,2 (2025-04) e 16,2 (2025-09 e 2026-10); válidos entre 12,8 e 14,9.
      Marcas: líder sem lance fechado 29,7%, líder desclassificado 27,8%, reiniciada 9,8%, aberto isolado 5,5%, outlier
      1,6%; fechado acima do aberto 8,8%.
    - **Feito (19/11/2026, segunda máquina):** 2026-09 e 2026-10 baixados (3 navegadores) e extraídos com o parser 1.8.0
      num banco próprio, `dados/extracao/aberto-fechado_2026-09_a_2026-10.db`: 2026-09 com 44.384 itens (OK 44.321,
      REVISAR 63, 2.265 compras) e 2026-10 com 39.018 (OK 38.997, REVISAR 21, 2.272 compras); nenhum ERRO.
      **Falta:** juntar à base `aberto-fechado_2025-10_a_2026-08.db` (como foi feito com `junho2025.db`) e refazer a
      análise com os 16 meses em 1.8.0. Continuam em 1.7.1: 2026-03, 04 e 08 (PDFs fora desta máquina).
    - **Feito (19/11/2026, segunda máquina):** 2026-03 e 2026-04 reextraídos com o parser 1.8.0 num banco novo,
      `dados/extracao/aberto-fechado_2026-03_04_08.db`: 2026-03 com 45.602 itens (OK 45.578, REVISAR 24) e 2026-04 com
      47.784 (OK 47.756, REVISAR 28); nenhum ERRO. 2026-08 extraído depois no mesmo banco (PDFs copiados da outra
      máquina): 52.543 itens (OK 52.501, REVISAR 42), o mesmo total da 1.7.1; o banco tem 145.929 itens. **Falta:** trocar
      os três meses 1.7.1 da base consolidada por estes e refazer a análise.
    - **Feito em parte (20/11/2026):** 2026-03 e 2026-04 incorporados à base `aberto-fechado_2025-03_a_2026-10.db` (backup
      `.antes-2026-03_04.db`) a partir de `dados/filtrados/aberto-fechado_2026-03_04_08.antes-2026-08.db`, a cópia da segunda
      máquina feita antes de 2026-08 entrar (só 03 e 04; lida só para leitura, hash conferido). Regra: 1.8.0 substitui 1.7.x
      e o que a base já tem em 1.8.0 fica. 76.655 itens 1.7.x substituídos, sem diferença em nenhuma das 34 colunas antigas
      (a 1.8.0 só preencheu as 8 colunas novas); 16.731 já em 1.8.0, idênticos; nenhum item novo; `arquivo_origem` igual em
      todos. Ficam em 1.7.1 47 itens de 6 compras que a reextração não tem (os PDFs não estavam na outra máquina):
      `90006-2026_98742705900062026` (24), `90522-2026_15815405905222026` (7), `90038-2025_92668105900382025` (5),
      `90227-2026_92500305902272026` (4), `91743-2025_94300105917432025` (4) e `90026-2026_98621905900262026` (3). Enquanto
      estiverem em 1.7.1, o `analise_etapas.py` recusa 2026-03 e 04. **Falta:** 2026-08 (o arquivo trazido não o tem) e
      decidir os 47 itens (reextrair as 6 compras ou tirá-las da base).
    - **Feito (20/11/2026):** 2026-08 em 1.8.0 incorporado a partir do banco completo da segunda máquina,
      `dados/filtrados/aberto-fechado_2026-03_04_08.db` (145.929 itens; só leitura, hash conferido; backup `.antes-2026-08.db`):
      40.617 itens 1.7.x substituídos (colunas antigas iguais, salvo `quantidade_fornecedores` em 1 item), 2026-03 e 04
      iguais aos já incorporados. A pedido do usuário, as 6 compras sem reextração (47 itens 1.7.1) foram tiradas da base
      (ficam nos backups). **Pendência 14 concluída:** a base tem 985.388 itens, todos em 1.8.0 ou 1.9.0.
    - **Feito (20/11/2026):** 2024-01 e 2024-02 (baixados pelo segundo usuário) extraídos com o parser 1.9.0, escolhido pelo
      usuário após teste em amostra (50 compras por mês: 1.8.0 gravou 2 de 1.756 itens, layout antigo; 1.9.0, 1.756), em
      `dados/extracao/aberto-fechado_2024-01_a_2024-02.db`: 2024-01 com 14.076 itens (REVISAR 38) e 2024-02 com 17.142
      (REVISAR 23). Juntados à base (backup `.antes-2024-01_02.db`), sem chave repetida: 1.016.606 itens. Ainda sem
      download: 2024-03 (parcial) a 2024-09 (ver pendência 7).
    - **Feito (20/11/2026):** 2024-12 (download completo, conferido no registro), 2025-01 e 2025-02 extraídos com o parser **1.9.1** (termos de
      transição, [04 §4.1](04-formato-dos-relatorios.md)) em `dados/extracao/aberto-fechado_2024-12_a_2025-02.db`: 53.551,
      38.401 e 40.931 itens; REVISAR 274, 269 e 267 (com a 1.9.0 foram 1.695, 2.583 e 1.409). Juntados à base às 16:50 e **retirados dela às 17:35** por decisão do
      usuário (bases separadas por versão, tabela de decisões): a base antiga voltou ao backup `.antes-2024-12_2025-02.db`
      e a versão com os três meses ficou em `.com-1.9.1_20261120.db`. 2024-01/02 também foram reextraídos em 1.9.1
      (só a compra `98600105008532023` muda: 11 itens com lance aberto diferente). Os cinco meses estão na base nova
      `dados/extracao/aberto-fechado_parser-1.9.1.db` (164.101 itens). 2024-11 (1.9.1, outra máquina; 45.775 itens, REVISAR 273) entrou
      na base nova em 20/11/2026 a partir de `dados/filtrados/aberto-fechado_2024-11_a_2024-12.db` (o 2024-12 desse arquivo é idêntico ao da base):
      agora 209.876 itens, seis meses. **Pendente:** ver se há termos de transição em 2023
      e reextrair na 1.9.1 os demais meses, se o usuário quiser a base nova completa.
    - **Feito (20/11/2026, segunda máquina):** 2024-12 e 2024-11 extraídos com o parser 1.9.1 num banco próprio,
      `dados/extracao/aberto-fechado_2024-11_a_2024-12.db` (99.326 itens; `integrity_check` ok): 2024-12 com 53.551
      (OK 53.277, REVISAR 274; igual à extração da outra máquina) e 2024-11 com 45.775 (OK 45.502, REVISAR 273); nenhum
      ERRO. **Feito (20/11/2026 19:00):** 2024-11 juntado à base `aberto-fechado_parser-1.9.1.db` (2024-12 já estava lá, idêntico).
    - **Feito (20/11/2026 20:35, máquina do primeiro usuário):** 2024-03 a 2024-09 (download manual concluído, Firefox) extraídos
      com o parser 1.9.1 num banco próprio, `dados/extracao/aberto-fechado_2024-03_a_2024-09.db` (257.156 itens, todos 1.9.1;
      `integrity_check` ok). Por mês (itens; REVISAR): 2024-03 19.911 (44), 04 28.379 (68), 05 32.208 (81), 06 37.658 (137),
      07 48.909 (213), 08 47.016 (161), 09 43.075 (159). Seis PDFs em ERRO, fora do banco: 4 vazios (0 bytes) em 2024-08
      (compras `08002405900012024`, `92656005900092024`, `98742505900542024`, `98756505900852024`; baixar de novo) e 2
      escaneados (OCR sem texto útil: `98591505900142024` em 07, `98233305900462024` em 09). **Pendente:** juntar à base
      `aberto-fechado_parser-1.9.1.db` (outra máquina) e repetir as "sem botão de downloads" de 2024-03 a 09 (1.070 compras).
    - **Análise dos 34 meses (20/11/2026, com `--pncp-db`; feita sobre a base mista, hoje `.com-1.9.1_20261120.db`):** 2023-04 a 2024-02, 2024-12 a 2026-10, todos; saída em
      `dados/analise_etapas/2023-04_a_2026-10_34meses/`. 1.048.923 itens (todos) e 931.983 (válidos), 57.676 compras,
      2.357 UASGs. Aberta 19,0% / 18,9%; após a fechada 34,4% / 32,9%; **ganho da fechada 15,4 p.p. (IC 15,2–15,6) e
      14,1 p.p. (13,9–14,2)**; ganho relativo 18,6% / 16,8%; final 33,8% / 33,9%; final = melhor lance em 71% / 92%.
      Decomposição (918.581): todos 21,7 + 16,1 − 3,9; válidos 19,0 + 14,1 + 0,8 = 33,9. Regressão (efeito fixo de item
      em primeira diferença; 2.356 / 2.349 UASGs como conglomerados): β −24,8 e −21,8; licitantes −5,2 e −1,3
      (p < 0,001); sigilo +2,4 (p < 0,001) e +1,7 (p = 0,001); serviço 0,0 (n.s.) e −1,4 (p = 0,079, deixou de ser
      significativo a 5%). Meses novos: 2024-12 aberta 17,9, ganho 15,1 / 14,1; 2025-01 aberta 17,5, ganho 15,0 / 13,9;
      2025-02 aberta 18,1, ganho 15,5 / 14,6. Marcas: líder sem lance fechado 29,5%, líder desclassificado 26,9%,
      reiniciada 9,4%, aberto isolado 5,4%, outlier 1,5%; fechado acima do aberto 8,6%.
    - **Análise dos 31 meses (20/11/2026, com `--pncp-db`):** 2023-04 a 2024-02 e 2025-03 a 2026-10, todos; saída em
      `dados/analise_etapas/2023-04_a_2026-10_31meses/`. 928.319 itens (todos) e 826.076 (válidos), 51.093 compras, 2.291
      UASGs. Aberta 19,1% / 19,0%; após a fechada 34,5% / 33,0%; **ganho da fechada 15,4 p.p. (IC 15,3–15,6) e 14,0 p.p.
      (13,9–14,2)**; ganho relativo 18,7% / 16,8%; final 33,9% / 34,0%; final = melhor lance em 71% / 93%. Decomposição
      (814.145): todos 21,8 + 16,1 − 4,0; válidos 19,1 + 14,1 + 0,8 = 34,0. Regressão (2.290 / 2.284 UASGs): β −24,9 e
      −21,8; licitantes −5,2 e −1,3 (p < 0,001); sigilo +2,4 (p < 0,001) e +1,7 (p = 0,001); serviço −0,3 (n.s.) e −1,6
      (p = 0,041). Meses novos: 2024-01 aberta 16,0, ganho 17,5 / 16,0 (12.000 itens, 603 compras); 2024-02 aberta 18,1,
      ganho 16,0 / 15,0. Marcas: líder sem lance fechado 29,4%, líder desclassificado 26,9%, reiniciada 9,4%, aberto
      isolado 5,4%, outlier 1,5%; fechado acima do aberto 8,5%.
    - **Análise dos 29 meses (20/11/2026, com `--pncp-db`):** 2023-04 a 2023-12 e 2025-03 a 2026-10, todos; saída em
      `dados/analise_etapas/2023-04_a_2026-10_29meses/`. 901.622 itens (todos) e 801.986 (válidos), 49.808 compras, 2.272
      UASGs. Aberta 19,2% / 19,0%; após a fechada 34,6% / 33,0%; **ganho da fechada 15,4 p.p. (IC 15,2–15,6) e 14,0 p.p.
      (13,8–14,2)**; ganho relativo 18,7% / 16,7%; final 33,9% / 33,9%; final = melhor lance em 71% / 93%. Decomposição
      (790.759): todos 21,9 + 16,1 − 4,0; válidos 19,1 + 14,0 + 0,8 = 33,9. Regressão (2.271 / 2.266 UASGs): β −24,8 e
      −21,8; licitantes −5,2 e −1,3 (p < 0,001); sigilo +2,4 (p < 0,001) e +1,7 (p = 0,001); serviço −0,4 (n.s.) e −1,7
      (p = 0,030). Meses novos: 2026-03 aberta 22,2, ganho 16,0 / 14,3; 2026-04 aberta 21,4, ganho 15,5 / 13,5; 2026-08
      aberta 18,1, ganho 15,3 / 14,0. Marcas: líder sem lance fechado 29,5%, líder desclassificado 27,0%, reiniciada 9,5%,
      aberto isolado 5,5%, outlier 1,5%; fechado acima do aberto 8,6%.
    - **Análise dos 26 meses (20/11/2026, com `--pncp-db`, base com 2023):** 2023-04 a 2023-12 (parser 1.9.0) e os 17 meses
      da análise anterior (2026-03, 04 e 08 de fora, ainda em 1.7.x quando rodou); saída em
      `dados/analise_etapas/2023-04_a_2026-10/`. 767.295 itens (todos) e 683.038 (válidos), 43.460 compras, 2.201 UASGs.
      Aberta 18,9% / 18,8%; após a fechada 34,3% / 32,9%; **ganho da fechada 15,4 p.p. (IC 15,2–15,6) e 14,0 p.p.
      (13,8–14,2)**; ganho relativo 18,6% / 16,7%; final 33,7% / 33,8%; final = melhor lance em 71% / 92%. Decomposição
      (673.763): todos 21,6 + 16,1 − 3,9; válidos 19,0 + 14,0 + 0,8 = 33,8. Regressão (2.199 / 2.195 UASGs): β −24,6 e
      −21,7; licitantes −5,2 e −1,4 (p < 0,001); sigilo +2,3 (p < 0,001) e +1,7 (p = 0,001); serviço −0,4 (n.s.) e −1,6
      (p = 0,045). Marcas: líder sem lance fechado 29,4%, líder desclassificado 26,7%, reiniciada 9,4%, aberto isolado 5,4%,
      outlier 1,5%; fechado acima do aberto 8,5%.
    - **Análise só de 2023 (20/11/2026, com `--pncp-db`):** saída em `dados/analise_etapas/2023-04_a_2023-12/`. 87.318 itens
      (todos) e 81.852 (válidos), 4.858 compras, 673 UASGs. Aberta 16,6% / 16,1%, a mais fraca da série; após a fechada
      33,2% / 31,5%; **ganho da fechada 16,6 p.p. (IC 15,9–17,2) e 15,4 p.p. (14,8–16,1)**, acima do de 2025-26; final
      32,8% / 32,9%; final = melhor lance em 74% / 90%. Decomposição (80.765): todos 18,3 + 17,0 − 2,4; válidos
      16,2 + 15,5 + 1,2 = 32,9. Regressão (673 UASGs): β −25,7 e −23,2; licitantes −6,8 e −4,5; sigilo +4,9 e +4,4
      (p < 0,001); serviço n.s. Ganho por mês (todos) de 10,4 (2023-04, 224 itens) a 18,1 (2023-10). Marcas: líder sem
      lance fechado 27,3%, líder desclassificado 18,6%, reiniciada 5,8%, aberto isolado 5,1%, outlier 0,9%; fechado acima
      do aberto 6,4%. Disputas mais ralas que em 2025-26 (itens OK de Menor Preço com lance aberto): 5,95 fornecedores por
      item (8,5), 26% com algum desclassificado (37%), etapa fechada reiniciada em 6,5% (11%); não conferido PDF a PDF.
    - **Análise dos 14 meses em 1.8.0 (19/11/2026, com `--pncp-db`):** 2025-04 a 2026-02 e 2026-05 a 07; saída em
      `dados/analise_etapas/2025-04_a_2026-07/`. 572.333 itens (todos) e 506.766 (válidos), 32.334 compras, 1.905 UASGs.
      Aberta 19,5% / 19,5%; após a fechada 34,6% / 33,2%; **ganho da fechada 15,1 p.p. (IC 14,9–15,4) e 13,7 p.p.
      (13,5–14,0)**; ganho relativo 18,4% / 16,5%; final 34,0% / 34,1%; final = melhor lance em 70% / 93%. Decomposição
      (499.654): todos 22,3 + 15,8 − 4,1; válidos 19,6 + 13,8 + 0,7 = 34,1. Regressão (1.902 / 1.897 UASGs): β −24,4 e
      −21,4; licitantes −4,8 e −0,8 (p = 0,007); sigilo +2,0 (p = 0,001) e +1,4 (p = 0,011); serviço −1,2 (n.s.) e −2,4
      (p = 0,007). 2025-04: aberta 22,0, ganho 14,2 / 12,8 (o menor dos 14 meses); 2025-05: aberta 20,6, ganho 14,4 / 13,1.
      Ganho por mês (todos) entre 14,2 (2025-04) e 16,2 (2025-09); válidos entre 12,8 e 14,9. Marcas: líder sem lance
      fechado 29,9%, líder desclassificado 27,7%, reiniciada 10,0%, aberto isolado 5,3%, outlier 1,6%; fechado acima do
      aberto 8,9%.
    - **Análise dos 12 meses em 1.8.0 (19/11/2026, com `--pncp-db`):** 2025-06 a 2026-02 e 2026-05 a 07; saída em
      `dados/analise_etapas/2025-06_a_2026-07/`. 494.069 itens (todos) e 438.012 (válidos), 27.674 compras, 1.833 UASGs.
      Aberta 19,2% / 19,2%; após a fechada 34,5% / 33,0%; **ganho da fechada 15,3 p.p. (IC 15,0–15,5) e 13,9 p.p.
      (13,6–14,1)**; ganho relativo 18,6% / 16,6%; final 33,8% / 33,9%; final = melhor lance em 70% / 93%. Decomposição
      (431.974): todos 22,0 + 16,0 − 4,1; válidos 19,3 + 13,9 + 0,7 = 33,9. Regressão (1.831 / 1.828 UASGs): β −24,6 e
      −21,6; licitantes −4,9 e −0,9 (p = 0,004); sigilo +2,3 (p < 0,001) e +1,5 (p = 0,008, agora significativo também
      com os válidos); serviço −1,0 (n.s.) e −2,3 (p = 0,033). 2025-06: ganho 14,9 / 13,6; 2025-07: 16,1 / 14,6. Ganho
      por mês (todos) entre 14,5 (2025-12) e 16,2 (2025-09); válidos entre 13,1 e 14,9. Marcas: líder sem lance fechado
      29,8%, líder desclassificado 27,5%, reiniciada 9,9%, aberto isolado 5,3%, outlier 1,5%; fechado acima do aberto 8,7%.
    - **Análise dos 9 meses em 1.8.0 (18/11/2026, com `--pncp-db`):** 2025-09 a 2026-02 e 2026-05 a 07; saída em
      `dados/analise_etapas/2025-09_a_2026-07/`. 365.489 itens (todos) e 323.216 (válidos). Aberta 18,9% / 18,9%; após a
      fechada 34,1% / 32,7%; **ganho da fechada 15,3 p.p. (IC 15,0–15,5) e 13,9 p.p. (13,6–14,1)**; ganho relativo
      18,5% / 16,5%; final = melhor lance em 70% / 93%. Decomposição (319.078): todos 21,6 + 16,0 − 4,1; válidos
      19,0 + 13,9 + 0,7 = 33,6. Regressão (1.701 UASGs): β −24,6 e −21,4; licitantes −4,9 e −0,8 (p = 0,013); sigilo
      +1,5 (p = 0,03) e +0,8 (n.s.); serviço −1,6 (n.s.) e −3,2 (p = 0,012). 2025-09 sozinho: ganho de 16,2 / 14,9 p.p.,
      o maior dos 9 meses.
    - **Análise dos 8 meses em 1.8.0 (18/11/2026, com `--pncp-db`):** 2025-10, 11, 12, 2026-01, 02, 05, 06 e 07 da base
      nova; saída em `dados/analise_etapas/2025-10_a_2026-07/`. 314.257 itens com todos os fornecedores e 277.704 só com
      os válidos. Aberta 19,0% / 18,9%; após a fechada 34,1% / 32,6%; **ganho da fechada 15,1 p.p. (IC 14,8–15,4) e
      13,7 p.p. (13,4–14,0)**; ganho relativo 18,4% / 16,3%; final = melhor lance em 70% / 93%. Decomposição (274.302
      itens): todos 21,7 + 15,8 − 4,1; válidos 19,0 + 13,7 + 0,7 = 33,4. Regressão (1.633 UASGs): β −24,4 e −21,2;
      licitantes −4,9 e −0,8 (p = 0,02); sigilo n.s. (+1,3, p = 0,10; +0,6); serviço −2,2 (n.s.) e −3,9 (p = 0,005).
      Ganho por mês (todos), entre 14,5 (2025-12) e 15,7 (2025-10); só válidos, entre 13,1 e 14,5. Isso cumpre o
      "repetir com `--pncp-db` e juntar" da análise da segunda máquina.
    - **Análise 2025-11 + 2026-02 (18/11/2026):** `analise_etapas.py --db dados/extracao/aberto-fechado_20261118.db --meses 2025-11 2026-02 --pncp-db ../dados/pncp.db`
      (saída em `dados/analise_etapas/2025-11_2026-02/`). 78.273 itens com todos os fornecedores e 68.931 só com os válidos.
      Ganho da fechada: 15,2 p.p. (todos) e 13,7 p.p. (válidos); β −24,4 e −21,1. A moderação pelo nº de licitantes
      (−4,7) some com só os válidos (−0,5, n.s.); sigilo e serviço n.s. Em 2025-11 sozinho: 15,5 e 14,0 p.p.; fevereiro
      igual à análise anterior.
    - **Feito (18/11/2026, segunda máquina):** 2025-12, 2026-01, 05, 06 e 07 extraídos com o parser 1.8.0 em
      `dados/extracao/aberto-fechado_2025-12_a_2026-07.db` (225.471 itens; OK 225.324, REVISAR 147). Colunas anteriores
      idênticas às da 1.7.2 nos meses de 2026 (ver [07, histórico](07-metodologia-de-extracao.md)).
    - **Análise 2025-12, 2026-01, 05, 06 e 07 (18/11/2026, segunda máquina):**
      `analise_etapas.py --db dados/extracao/aberto-fechado_2025-12_a_2026-07.db`, **sem `--pncp-db`** (o `pncp.db` não
      está nessa máquina: a regressão não tem sigilo nem serviço). Saída em `dados/analise_etapas/2025-12_a_2026-07/`.
      207.945 itens com todos os fornecedores e 183.786 só com os válidos. Aberta 19,1% / 18,9%; após a fechada 34,1% /
      32,4%; ganho da fechada 15,0 p.p. (IC 14,6–15,4) e 13,5 p.p. (13,1–13,8); final 33,2% / 33,3%. Decomposição
      (181.283 itens): todos 21,8 + 15,7 − 4,2; válidos 19,1 + 13,5 + 0,7. β −24,3 e −20,9; moderação pelo nº de
      licitantes −5,2 e −1,1 (p = 0,007, ainda significativa só com os válidos, ao contrário de 2025-11 + 2026-02).
      Ganho por mês (todos / válidos): 12: 14,5 / 13,2; 01: 15,2 / 14,1; 05: 15,0 / 13,2; 06: 15,2 / 13,8;
      07: 15,2 / 13,2. Marcas: líder da aberta sem lance fechado 30%, líder desclassificado 28%, etapa reiniciada 10%,
      aberto isolado 5%, fechado outlier 1%; fechado acima do aberto 8% (17.310 itens, todos com o líder sem lance
      fechado). Valor final = melhor lance da disputa em 70% (todos) e 93% (válidos). Falta repetir com `--pncp-db` e
      juntar com a base da outra máquina (`--db` repetido).
    - **Falta:** trazer de volta a `dados/filtrados/` os PDFs de 2026-03, 04 e 08 (ausentes em 18/11/2026) e rodar
      `python -m extrator_homologacao dados/filtrados/aberto-fechado_<mês>/relatorios --saida dados/extracao/aberto-fechado_<mês>.xlsx --db dados/extracao/aberto-fechado_2026-08.db --workers 7 --sem-separar`
      para cada mês (a versão nova invalida o cache; não precisa de `--reprocessar`). Depois, rodar
      `python analise_etapas.py --db dados/extracao/aberto-fechado_2026-08.db --pncp-db ../dados/pncp.db` com todos os
      meses em 1.8.0. Fazer o mesmo para 2026-01 e os meses de 2025 ao extraí-los (cada máquina com o seu banco).
    - **Primeiros números (fevereiro, 34.436 itens OK de Menor Preço):** nos 2.726 com fechado acima do aberto, o líder da
      aberta nunca deu lance fechado; em 1.560 deles o líder foi desclassificado e em 830 houve reinício. O líder foi
      desclassificado em 29% dos itens. Lance aberto isolado (< 50% do outro fornecedor): 1.837 itens, 1.109 com o líder
      desclassificado. Só com fornecedores válidos, o valor final é o melhor lance da disputa em 92,0% dos itens (69,8%
      com todos), fica acima em 0,1% e abaixo (negociação) em 7,8%.
15. **Termos de homologação só com o chat (2025-06).** Na extração de 2025-06 (19/11/2026, `dados/extracao/junho2025.db`,
    segunda máquina), 1.465 PDFs de 49 compras saíram como "nenhum bloco de item encontrado no relatório" e não foram
    gravados no banco (nos meses de 2025-09 em diante eram ~100 por mês). São termos de homologação que trazem só o chat
    da compra (ex.: `90012-2024_16008205900122024`, 270 PDFs, compra de 2024 homologada em 2025). Falta ver se o zip
    traz outro relatório com o item (termo de julgamento) e ensinar o `selecao.py` ou o parser a usá-lo.
    - Em 2025-08 (19/11/2026, esta máquina): 315 PDFs de 14 compras com o mesmo motivo, a maior
      `90025-2024_92796905900252024` (179 PDFs).
    - Em 2025-05 (19/11/2026): 2.040 PDFs de 65 compras, a maior `90055-2024_98991305900552024` (469 PDFs); em 2025-04:
      1.698 PDFs de 88 compras, a maior `90008-2024_78270005900082024` (186). São quase todo o REVISAR desses meses
      (5,5% e 5,2% dos PDFs, contra 1,5% em 2025-08); as três maiores de cada mês são compras de 2024.
    - Em 2025-03: 2.991 PDFs de 133 compras (7,6% dos PDFs), a maior `90023-2024_78882005900232024` (319 PDFs).
    - **Provável causa (19/11/2026):** nos PDFs de 2023, o mesmo motivo vinha do **layout antigo** (termos emitidos até
      fev/2025), lido desde o parser 1.9.0 ([04 §4.1](04-formato-dos-relatorios.md)): o bloco do item existe, mas fora
      da ordem de leitura, e o parser via só o chat da compra. Estes PDFs são de compras de 2024 e devem ser do mesmo
      layout. **Próximo passo:** reextrair 2025-03 a 2025-08 com o parser 1.9.0 na máquina que tem os PDFs (não estão
      nesta) e conferir se os itens passam a ser gravados.
16. **Download e extração dos pregões Fechado-Aberto (2023-04 a 2026-10).** Pedido do usuário em 20/11/2026. A amostra usa
    a mesma seleção do Aberto-Fechado: item principal homologado, mês da `data_resultado`, compra com `id_compra`. São
    **1.479 compras** (1.415 Pregão Eletrônico e 64 Presencial), 1.576 compra-mês em 42 meses e 24.749 itens homologados.
    Ficam de fora 4.788 compras Fechado-Aberto de outras plataformas (`fonte = 'pncp'`, sem `id_compra`). Lista em
    `registro/compras_fechado-aberto/`; download com `baixar_manual.py --modo fechado-aberto`; passo a passo em
    [09](09-download-fechado-aberto.md). **Próximos passos:** (a) baixar (dividido entre máquinas com `--parte k/n`);
    (b) testar o parser numa amostra de termos Fechado-Aberto, em que a etapa fechada vem antes da aberta, e só depois
    extrair num banco próprio; (c) decidir se os presenciais entram na análise.

## Questões em aberto

- **17/11/2026 — comparação anual por sigilo concluída:** [testes e documentação versionados](08-testes-medias-precos.md), com 30 especificações, seis testes principais, Holm e bootstrap complementar. O desconto dos sigilosos utiliza apenas estimados positivos disponíveis no snapshot. Resultados e limitações não identificam efeito causal. A auditoria dos índices extremos continua pendente de documentação física do fornecimento.

- **17/11/2026 — testes de médias concluídos:** [relatório e arquivos](../analises/testes_medias_20261117/relatorio_completo.md). Log do preço: associação negativa no teste principal, com sensibilidade à inferência; desconto e razão preço/mediana sem diferença significativa no principal após Holm. A razão em nível é dominada por extremos confirmados no cadastro, ainda sem certificação de equivalência física. Prioridade de auditoria: CATMAT 268493, item `id=1114157`, preço registrado 16.100, quantidade 1 e apresentação COMPRIMIDO versus mediana 0,068; não corrigido por conjectura. Banco preservado; testes não identificam efeito causal.

- Proposta inicial de fornecedor depois inabilitado deve definir o melhor lance aberto? Em Fortaleza
  90119/2025, item 1, ela dá 0,53 contra 0,74 dos lances, e o `ganho_fechada` zera.
- Quanto do desconto do AF vem da etapa fechada (ganho médio da fechada sobre a aberta)?
- O efeito Aberto vs AF difere entre material e serviço, e por esfera?
- A amostra com PDF (órgãos que publicam ou zips baixados à mão) é representativa da base nacional?
