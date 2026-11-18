# 7. Metodologia de extração

Como os dados são obtidos e transformados, dos brutos até a base de análise. **Este documento é
atualizado sempre que algo muda**: altere a etapa afetada e acrescente uma linha ao
[histórico](#histórico-de-mudanças).

Definições de desconto e estratégia estatística: [01](01-objetivo-e-metodologia.md). Colunas do
banco: [06](06-banco-de-dados.md). Formato dos PDFs: [04](04-formato-dos-relatorios.md).

## Visão geral

```
1. Contratações (API Dados Abertos)  ─┐
2. Itens (API Dados Abertos)         ─┴─> dados/brutos/ ─> 3. Banco dados/pncp.db
2.2 Demais plataformas (API do PNCP) ───> dados/brutos_pncp/ ──────────┤
                                                                   │ 4. seleção
                                                                   ▼
                5. Download dos relatórios (PNCP; depois zip manual)
                                                                   │
                                                                   ▼
                6. Extração dos PDFs ─> 7. Carga no banco (ainda não feita)
```

## 1. Coleta das contratações (`coleta_anos.py`)

- **Fonte:** API Dados Abertos do Compras.gov.br, `1_consultarContratacoes_PNCP_14133`.
- **Recorte:** `codigoModalidade = 5` (Pregão, Eletrônico e Presencial), todos os órgãos e modos.
- **Período:** de 2022-11, primeiro mês com pregões na API, até o mês corrente.
- **Corte temporal:** mês de `dataPublicacaoPncp`; a data final da API é exclusiva.
- **Duplicados:** removidos por `numeroControlePNCP`, porque `idCompra` se repete.
- **Conferência:** compara o total salvo com `totalRegistros`, com até 3 tentativas por mês.
- **Saída:** `dados/brutos/<ano>/contratacoes_pregao_<ano>-<mês>.{json,csv}`.

## 2. Coleta dos itens (`coleta_itens.py`)

- **Fonte:** `2_consultarItensContratacoes_PNCP_14133`, dia a dia pela data de inclusão.
- **Recorte:** mantém só os itens das compras coletadas na etapa 1.
- **Duplicados:** chave `numeroControlePNCPCompra` + `numeroItemPncp` + `idCompraItem` + fornecedor +
  valor do resultado. Os meses coletados antes de 2026-11-03 usaram a chave sem fornecedor e valor.
- **Conferência:** pelas linhas recebidas, porque `totalRegistros` conta repetições.
- **Retomada:** meses gravados são pulados, exceto o corrente; para atualizar um mês, apague o arquivo.
- **Saída:** `dados/brutos/<ano>/itens_pregao_<ano>-<mês>.{json,csv}`.

Também existem `itens_pregao_adicional_correspondencias_<ano>`, que entram no banco e não repetem
itens dos mensais. **Nenhum script do repositório os gera, e a origem deles não está documentada.**

**Limitações conhecidas:** a paginação perde menos de 1% das contratações e de 1% a 3% dos itens; a
API costuma atrasar cerca de um mês; os meses recentes têm poucos valores homologados.

### 2.1 Coleta dos resultados (`coleta_resultados.py`)

- **Fonte:** `3_consultarResultadoItensContratacoes_PNCP_14133`, dia a dia pela data de resultado.
- **Por quê:** `itens` não separa resultado ativo de cancelado, e o valor diferiu em cerca de 1% dos
  itens (pendência 8).
- **Recorte:** só as compras de `pncp.db`; duplicados por compra, item e `sequencialResultado`.
- **Retomada:** mês com falha não é gravado e é refeito ao rodar de novo.
- **Saída:** `dados/brutos/<ano>/resultados_pregao_<ano>-<mês>.json`, depois tabela `resultados`.

### 2.2 Coleta das demais plataformas (`coleta_pncp.py`)

- **Fonte:** API do PNCP. `contratacoes/publicacao` para a lista; `/itens` e `/itens/{n}/resultados`
  compra a compra.
- **Recorte:** modalidades 6 e 7 (Pregão Eletrônico e Presencial), todos os modos, de 2022-11 a 2026-10.
- **Corte temporal:** mês de `dataPublicacaoPncp`.
- **Duplicados:** descarta o `numeroControlePNCP` já presente e a irmã com mesmo CNPJ, ano, número e
  abertura, comparando com todo o banco. A irmã fica em `compras_duplicadas`, sem baixar itens. Entre
  irmãs novas, fica a de menor `numeroControlePNCP`. Compra sem número ou abertura não é comparada.
- **Lista dia a dia:** cada dia é uma consulta, porque a página funda é lenta (ver docs/03, item 17).
- **Conferência:** a lista de cada dia é repetida uma vez se vier menos que `totalRegistros`, e o log registra a
  diferença. Depois de 3 tentativas, até 50 compras com falha entram sem itens, contadas em
  `coleta_pncp_meses.sem_itens`; acima disso, o mês não é carregado.
- **Velocidade:** 2 s entre páginas da lista e 8 threads nos itens (`--threads`). Um 429 pausa todas as
  threads. Só um processo pode listar por vez: dois juntos levam a 429 seguidos.
- **Retomada:** compra baixada não se repete, e mês carregado é pulado.
- **Saída:** `dados/brutos_pncp/<ano>/contratacoes_<mês>.json.gz` e `itens_<mês>.jsonl.gz`, depois o
  banco, numa transação por mês. `itens_<mês>.completo` marca o mês baixado por inteiro.

**Limitações conhecidas:** o PNCP não traz o item do catálogo (`catalogoCodigoItem` existe, é opcional
no envio e vem sempre vazio), então `cod_item_catalogo` fica vazio e a compra fica fora do pareamento UASG × item; os
meses recentes têm poucos resultados e não são atualizados depois de carregados; `orcamento_sigiloso`
não equivale ao da API Dados Abertos (ver [06](06-banco-de-dados.md)); a chave de irmãs foi conferida
em poucos casos.

## 3. Banco unificado (`banco_unificado.py`)

Carrega os brutos em `dados/pncp.db`, sem filtrar modos. Marca `registro_principal` (uma linha por
item) e `homologado`. Regras completas em [06](06-banco-de-dados.md). Depois de uma nova coleta da API
Dados Abertos, o banco precisa ser recriado. A coleta do PNCP entra direto no banco existente, e
`--recriar` a recarrega de `dados/brutos_pncp/`.

## 4. Seleção das compras para download

Só pregões **Aberto-Fechado com item homologado**: `modo_disputa = 'Aberto-Fechado'`,
`homologado = 1`, `registro_principal = 1`, com o mês definido por `data_resultado`. Compras sem
`id_compra`, que são as vindas do PNCP, ainda ficam de fora.

- **Motivo:** o melhor lance de cada etapa só existe no relatório.
- **Pregão Aberto:** usa o resultado da API, que é o valor homologado e pode diferir do melhor lance
  por negociação ou desclassificação. Isso é limitação do estudo.

## 5. Download dos relatórios

### 5.1 Pelo PNCP (`baixar_api.py`, `pncp_arquivos.py`)

Automático, pela API pública, sem navegador e sem tocar no captcha.

Varredura mês a mês: `python baixar_api.py <mês>`, e o mês seguinte só roda por comando do usuário.

1. **Índice de publicações:** `dados/pncp_publicadas/<AAAA-MM>.json` lista os pregões Aberto-Fechado
   publicados no mês, de todos os órgãos, uma única vez. Respeita o limite do PNCP, com 2 s entre
   páginas. Cada compra usa o mês da publicação e os vizinhos.
2. **Por compra:** olha a própria contratação e as irmãs do índice, com mesmo CNPJ, ano, número e
   abertura.
3. **Sem repetição:** compra já buscada em qualquer mês, por qualquer usuário, não é buscada de novo.
4. **Registro:** cada compra vai para o registro compartilhado (5.4); no fim, `inventario_pdfs.py` atualiza `relatorios_pdf`, `busca_pdf` e
   `dados/pendentes_manual.csv`, que é a lista do download manual.

Opções: `--parte k/n`, `--sem-irmas`, `--cnpj`, `--amostra-orgaos N`, `--limite N`.

**Limitação do índice:** uma irmã cadastrada com outro modo de disputa não é encontrada. As 3 irmãs
conferidas de Fortaleza têm o mesmo modo.

Para cada arquivo:

| Passo | Regra |
|---|---|
| Candidato | Tipos 26, 27 e 28 sempre; tipos ignorados nunca, como edital; os demais só se o título lembrar termo, ata, relatório, sessão ou lance |
| Termo reconhecido | Conteúdo é termo de homologação ou julgamento, com itens e com UASG e número da compra certos. Vai para `relatorios/`, um arquivo por item, com o nome do padrão do zip |
| Outro formato | Candidato não reconhecido é guardado em `outros_formatos/` se mencionar lances, não tiver texto, for ilegível ou não for PDF. Todos entram em `manifesto.csv` |

Cada compra grava no registro (`<usuario>_api.csv`, ver 5.4):

| Motivo | Significado |
|---|---|
| `termos encontrados` | Ao menos um item coberto; `situacao` diz se é completo ou parcial |
| `outros formatos guardados` | Há arquivo para adaptar o leitor depois |
| `candidatos sem lances` | Candidatos legíveis, sem menção a lances |
| `nenhum candidato` | Há arquivos publicados, mas nenhum passou no filtro |
| `nenhum arquivo publicado` | A consulta funcionou e não há arquivos |
| `erro na API` | Falhou; é refeita ao retomar a rodada |

Nenhum motivo prova que o PDF não existe. Ver [03 §3.4](03-fontes-de-dados-e-apis.md).

### 5.2 Manual (`relatorios.py`)

O que não estiver no PNCP só existe no zip do Compras.gov.br. O script abre a compra no navegador, e
a pessoa resolve o captcha e clica no download. **O hCaptcha não é contornado.**

### Seleção do relatório por item (`selecao.py`)

Mantém o termo de homologação; sem ele, o termo de julgamento da última sessão.

### 5.3 Manual em paralelo (`baixar_manual.py`)

Abre a página de cada compra no navegador; o usuário clica em Downloads > "Todos os relatórios e
termos", e o script pega o zip na pasta Downloads, move para a pasta da compra e deixa um termo por
item (`manter_selecionados`). Mesmas compras do 5.1, do mês mais recente para o mais antigo
(`--de`, `--ate`), para rodar junto com o `baixar_api.py`, que anda no sentido contrário.

- **Anotação compartilhada:** compra com termos na pasta (sem `.pncp_parcial`) ou com `completo` no
  registro (5.4) está resolvida para os dois scripts. O `baixar_api.py` confere o disco antes de cada
  compra; o manual relê o registro antes de cada uma.
- **Registro** em `<usuario>_manual.csv` (passada `manual`; motivos `zip baixado à mão`, `zip baixado (auto)`,
  `zip sem termos`, `pulada no site`, `zip não recebido` e, no `--auto`, `sem a opção no site`,
  `sem botão de downloads no site`, `acesso não autorizado no site`, `compra não encontrada no site`,
  `erro do site no download`).
  Entra em `busca_pdf` e no `pendentes_manual.csv`.
- Compra pulada ([p]) ou sem zip no tempo-limite não é reaberta, salvo com `--repetir`. O `--repetir` sozinho
  reabre todas as não completas (inclusive "zip sem termos" e "sem a opção no site"); com
  `--motivo "zip não recebido"` reabre só as que têm esse último motivo no registro (filtradas antes do laço).
- Não consulta o PNCP nem grava no `pncp.db`. Opções: `--de`, `--ate`, `--parte k/n`, `--repetir`, `--motivo`,
  `--auto`.

**Modo `--auto`** (`python baixar_manual.py --auto [--intervalo 20-60] [--max-falhas 3]`): o clique em
Downloads > "Todos os relatórios e termos" é feito pelo userscript `navegador/compras_auto.user.js`.

- **Instalação, uma vez:** instale a extensão Tampermonkey no navegador padrão (é o que o `webbrowser.open`
  abre; no Chrome, ative também "Permitir scripts de usuário" ou o modo de desenvolvedor). Depois crie um
  script novo com o conteúdo do arquivo. A cada versão nova (`@version`), cole o arquivo de novo: o
  Tampermonkey guarda a própria cópia. Desligue a pergunta de onde salvar cada arquivo (Firefox:
  Configurações > Geral > Arquivos e aplicativos; Chrome: Configurações > Downloads).
- O userscript só age em abas abertas com `&pncpauto=1` na URL, que o `--auto` acrescenta. Ele espera o
  botão de downloads, abre o menu, clica na opção e fecha a aba quando o site entrega o arquivo.
- **hCaptcha:** não é contornado. O site gera o token do hCaptcha invisível como num clique feito à mão.
  Se aparecer um desafio, o título da aba muda para `[PNCP auto] resolva o captcha` e você o resolve ali.
  Depois de 60 s sem zip, o terminal lembra de olhar a aba.
- **Sem zip:** o userscript baixa um aviso `pncp-auto-<idCompra>-<motivo>.txt` na pasta Downloads. O
  script lê o aviso, move o arquivo para `dados/avisos_auto/` e anota o motivo. Os códigos são `sem-opcao`,
  `sem-botao`, `acesso-nao-autorizado`, `compra-nao-encontrada` e `erro-download` (só `sem-opcao` e
  `compra-nao-encontrada` não contam como falha). O aviso traz um diagnóstico da página (botões,
  iframes e começo do texto) para ajustar os seletores.
- **Ritmo:** espera aleatória de `--intervalo` segundos entre compras (padrão 20 a 60). Depois de
  `--max-falhas` compras seguidas sem zip (padrão 3; `sem a opção no site` não conta), o script pausa e
  pergunta se continua, porque isso pode indicar bloqueio.
- **Meses em paralelo:** `--navegador chrome|edge|firefox` abre as compras naquele navegador, e não no
  padrão do sistema. Um terminal por mês, um navegador por terminal, cada um com o userscript instalado.
  Todos baixam em Downloads; cada processo só reconhece os arquivos das próprias compras (pelo `idCompra`).
- `idCompra` fora do formato de 17 dígitos (UASG, modalidade, número e ano) não é aberto: fica anotado como
  `idCompra inválido`.
- Sem o userscript instalado, o `--auto` funciona como o modo manual: você clica e o zip é recolhido igual.
- **Teste de 17/11/2026** (agosto de 2026, Firefox, uma pessoa), com `--intervalo 0`, ou seja, a próxima
  compra abre assim que o zip chega:
  - cerca de 6 s por compra, perto de 600 compras por hora. Mais de 800 zips sem nenhum desafio do hCaptcha.
    Com o padrão de 20 a 60 s, eram cerca de 80 por hora;
  - cerca de 12% dos zips só têm relatórios por grupo (`...-grupoN.pdf`). O `selecao.py` ainda não os
    escolhe, então saem como `zip sem termos`, com o zip guardado inteiro na pasta da compra (ver
    [05](05-decisoes-e-pendencias.md), pendência 1);
  - casos raros: compra que o site não encontra (UASGs `000xxx` e 180211, por exemplo); página que fica
    só no cabeçalho, sem carregar a compra, e volta ao normal na seguinte; compra ainda "aguardando
    julgamento" no site (`sem a opção no site`).
- Rodando sem terminal (em segundo plano), a pausa de `--max-falhas` não consegue ler a tecla: encerre o
  processo e rode de novo. As compras já anotadas não são reabertas.
- Seletores usados: o botão dentro de `app-botao-relatorios-compra` (na falta dele, botão com `aria-label`
  começando por "Downloads" ou com o ícone `fa-download`) e o item do menu com o texto
  "Todos os relatórios e termos". Se o site mudar, ajuste as constantes no topo do userscript.

### 5.4 Registro compartilhado (`registro.py`, pasta `registro/`, versionada)

O que já foi buscado e baixado fica no git, para mais de um usuário dividir o download; os PDFs e o
`pncp.db` ficam em `dados/`, fora do git.

```
registro/aberto-fechado_<AAAA-MM>/<usuario>_api.csv      baixar_api.py
registro/aberto-fechado_<AAAA-MM>/<usuario>_manual.csv   baixar_manual.py
```

- **Sem conflito de merge:** cada usuário só acrescenta linhas aos próprios arquivos. O usuário é o
  `git config user.name` em minúsculas, sem acento, com hífens (ou a variável `PNCP_USUARIO`).
- **Estado = união de todos os arquivos.** Depois de `git pull`, os scripts pulam o que qualquer usuário
  resolveu; `inventario_pdfs.py` monta `busca_pdf` e `pendentes_manual.csv` a partir dele. Entre usuários,
  a ordem das linhas é a `data_hora`; `completo` prevalece sobre as demais.
- **Colunas:** `numeroControlePNCP`, `idCompra`, `usuario`, `data_hora`, `passada`, `situacao`, `motivo`,
  `itens_cobertos`, `itens` (ex.: `1;2;5`), `sha256` (do conjunto de termos: nome + hash de cada arquivo,
  para conferir PDFs trocados por outro meio), `publicados`, `candidatos`, `outros_guardados`, `erros`.
- **Divisão do trabalho:** o git não é tempo real, então dois usuários podem pegar a mesma compra entre
  um push e um pull. Com `--parte k/n` nos dois scripts, cada compra cai sempre na mesma parte (SHA-1 do
  `numeroControlePNCP`), e cada pessoa fica com a sua.
- **Lista de compras:** `registro/compras/<AAAA-MM>.csv` (mês do resultado do item) traz as compras
  Aberto-Fechado com item homologado e com `idCompra`, com os campos que os scripts usam (objeto cortado em
  100 caracteres). Sem `dados/pncp.db`, `baixar_api.py` e `baixar_manual.py` usam essa lista, e
  `inventario_pdfs.py` só gera os CSVs. Quem tem o banco regera com `python registro.py compras` e faz commit.
- **Migração:** `python registro.py migrar [AAAA-MM ...]` passa os antigos `motivos.csv`/`manual.csv` de
  `dados/filtrados/` para `registro/`, no nome do usuário atual, e deixa uma cópia `.migrado`. Enquanto não
  migrados, eles continuam sendo lidos. Janeiro/2026 foi migrado sem `data_hora`, `itens` e `sha256`.

## 6. Extração dos PDFs (`extrator_homologacao`)

Parser determinístico, com PyMuPDF e regex. Sem modelos de linguagem.

1. **Texto:** camada de texto do PDF; sem ela, OCR do PyMuPDF. Remove cabeçalho e rodapé repetidos.
2. **Segmentação:** cabeçalho da compra e, por item, propostas, lances, chat e eventos. Grupos têm
   bloco próprio.
3. **Etapas:** a tabela de lances não indica a etapa, então ela é deduzida pelos marcos de tempo no
   chat, ou nos eventos. Em grupo, os marcos vêm do bloco do grupo.
4. **Classificação:** lance antes do início da fechada é da etapa aberta; dentro da janela, da
   fechada; em janela de desempate, vai à parte.
5. **Melhor lance por etapa:**
   - menor valor em R$ nos dois critérios: em Maior Desconto o relatório traz `P% (R$ V)` (lance,
     proposta, situação, eventos e chat), com V = estimado × (1 − P), então o maior desconto é o
     menor V. Grava-se V nas colunas de valor e P em `<campo>_percentual` (aberto, fechado,
     desempate, aceito, negociado), lido do par do próprio item; os pares `(total)` não entram. Se um
     V aparece com dois P, o percentual fica vazio; se V / (1 − P) difere do estimado em mais de 1%,
     há aviso (parser 1.7.0);
   - valores da proposta quebrados em duas linhas (`... (R$ V)` + `(unitário)`, ou `(R$` + `V) ...`)
     e o parágrafo de situação do item com uma palavra por linha (texto justificado) são juntados
     antes da leitura (parser 1.7.1);
   - conta mesmo que o fornecedor seja desclassificado depois;
   - lances excluídos (`*`) não contam;
   - a etapa aberta inclui as propostas iniciais;
   - a etapa fechada usa só lances enviados na janela, inclusive em grupo.
6. **Conferência:** compara com os valores da mensagem de encerramento. Em grupo, pela soma de
   valor × quantidade dos itens de cada convocado.
7. **Status:** `OK`, `REVISAR` (com motivos) ou `ERRO`.

Cache por hash do arquivo, item e `VERSAO_PARSER`. Ao mudar o parser, incremente a versão.

**Extração por mês:** um banco por mês, para carga posterior no `pncp.db`:

```
python -m extrator_homologacao dados/filtrados/aberto-fechado_<mês>/relatorios ^
    --saida dados/extracao/aberto-fechado_<mês>.xlsx --workers 7 --sem-separar
```

Gera `aberto-fechado_<mês>.db` (tabela `itens`, uma linha por item), `.xlsx`, `.log` e
`.cache.json`. Use `--sem-separar`: com a pasta `relatorios/` como raiz, cada compra seria uma
"subpasta" e geraria um Excel próprio. `esfera`/`uf` saem vazias (a pasta não tem os
`contratacoes_*.json`); vêm do `pncp.db` na carga. No Excel, caracteres de controle do texto do PDF
são removidos (o openpyxl os recusa); o SQLite guarda o texto original.

**Limitações:** OCR lê o texto, mas o parser ainda não o entende, e o PDF sai como `ERRO`; Ata Final
de outras plataformas não é lida; grupos foram testados em um único pregão.

## 7. Carga no banco (ainda não feita)

As colunas de lance de `itens` estão vazias. A carga deve ligar os bancos da extração
(`dados/extracao/*.db`) ao `pncp.db`, validando a ligação, porque há contratações irmãs.

**Chave recomendada:** `compras.id_compra` (os 17 dígitos no nome do PDF,
`relatorio-termo-homologacao-<id_compra>-item-<N>.pdf`, extraídos de `arquivo_origem`) +
`itens.numero_item` = `item`, com `registro_principal = 1`. Em 2026-08 ligou 51.143 de 52.543 itens
(97,3%), com uma duplicidade. Por UASG + número + ano ligou só 48.968: `compras.numero_compra` tem
zeros à esquerda (`00141`) e o extrator grava `1/2026`. Dos 1.400 sem ligação, 1.397 têm a compra
no banco, mas não o item (a investigar).

## Análise

Regras em [01](01-objetivo-e-metodologia.md). Filtro `elegivel`, `homologado = 1` e, por recomendação
ainda não decidida, só Menor Preço.

## Histórico de mudanças

**Análise anual por sigilo de 17/11/2026:** [documentação, resultados e reprodução](08-testes-medias-precos.md). As extrações anteriores foram preservadas por hash; 305 registros foram conferidos novamente no SQLite. Mês foi substituído por ano nos estratos e referências, com análises separadas para sigilo 0/1 e desconto calculado quando o estimado é positivo em cada grupo. Metodologia, 30 testes e validações estão versionados em `analises/`; os arquivos volumosos permanecem locais.

**Análise de médias de 17/11/2026:** nova leitura somente leitura deste `dados/pncp.db`, registrada em [testes de médias](../analises/testes_medias_20261117/relatorio_completo.md). Mantém pregão eletrônico, materiais homologados, Menor preço, identidade de catálogo/apresentação e coorte madura; compara A/AF por produto×mês×UF. A recorrência foi novamente verificada somente nesses dois modos. Há desfechos separados para log do preço, desconto e razão para mediana contemporânea de outros órgãos. Protocolo, emenda anterior à estimação, consulta, amostras, validação direta no SQLite e inferência com agrupamentos estão na pasta da análise. Não altera coleta, parser ou banco.

| Data | Etapa | Mudança |
|---|---|---|
| 2026-11-18 | 4 | `baixar_manual.py --repetir --motivo TEXTO`: repete só as compras com aquele último motivo; usado nas 12 "zip não recebido" de 2026-02 a 04 |
| 2026-11-17 | Análise | Nova extração somente leitura para testes de médias A/AF; três desfechos, padronização de produto/mês/UF, testes com agrupamentos CNPJ/CATMAT e Holm; benchmark fora do órgão e bootstrap complementar com recálculo; protocolo e auditorias em `analise/testes_medias_20261117` no workspace |
| 2026-11-03 | 3 | Banco unificado criado; valores em `REAL` depois de erro de divisão inteira na primeira carga |
| 2026-11-03 | 4 | Download restrito a Aberto-Fechado com item homologado |
| 2026-11-03 | 5 | `baixar_api.py`: seleção pelo banco, duas passadas, motivo por compra e retomada |
| 2026-11-03 | 5 | Candidatos não reconhecidos passam a ser guardados em `outros_formatos/` |
| 2026-11-03 | 5 | Filtro de título passa a reconhecer `AtaTotal_<n>`, `Ata_Final` e títulos com "lance" |
| 2026-11-03 | 6 | Parser 1.6.0: itens em grupo; cache passa a considerar o item |
| 2026-11-03 | 6 | OCR pelo PyMuPDF no lugar de OCRmyPDF; extração de escaneados ainda não funciona |
| 2026-11-03 | 2 | Chave de duplicados dos itens inclui fornecedor e valor; nova coleta de resultados e tabela `resultados` |
| 2026-11-03 | 5 | Irmãs pelo índice mensal de publicações, só Aberto-Fechado, no lugar da consulta por órgão; compra já buscada não repete; `busca_pdf` e `pendentes_manual.csv` |
| 2026-11-03 | 5 | `--cnpj`, `--amostra-orgaos` e inventário dos PDFs em `relatorios_pdf` |
| 2026-11-03 | 5 | Lista de órgão que falhou não é repetida na mesma rodada; as compras seguem como `erro na API` |
| 2026-11-03 | 5 | Irmãs de janeiro/2026: Fortaleza 25 de 26 compras com termos; amostra de 40 órgãos (359 compras), nenhuma |
| 2026-11-03 | 5 | Passada própria de janeiro/2026: 2.364 compras, nenhum candidato. A busca de termos depende da passada das irmãs |
| 2026-11-06 | 2.2 e 3 | `coleta_pncp.py`: pregões fora da API Dados Abertos entram pelo PNCP, com `compras.fonte`, `compras_duplicadas`, `coleta_pncp_meses` e brutos em `dados/brutos_pncp/`; `--pncp`; `--recriar` recarrega esses brutos; `--resultados` preserva os do PNCP |
| 2026-11-06 | 4 | `baixar_api.py` ignora compras sem `id_compra` |
| 2026-11-07 | 2.2 | `coleta_pncp.py` lista o mês dia a dia, e não mais o mês inteiro de uma vez: mesmas compras, cerca de 40% menos tempo |
| 2026-11-16 | 5 | `baixar_manual.py`: download manual do mais recente para o mais antigo, em paralelo ao `baixar_api.py`, anotado em `manual.csv`; o `baixar_api.py` pula compra já baixada à mão |
| 2026-11-16 | 5 | Registro compartilhado em `registro/` (versionado), um arquivo por usuário, mês e origem, no lugar de `motivos.csv`/`manual.csv` em `dados/`; `--parte k/n` nos dois scripts; janeiro/2026 migrado |
| 2026-11-16 | 5 | Lista de compras a baixar em `registro/compras/<mês>.csv` (`registro.py compras`), usada quando não há `dados/pncp.db` |
| 2026-11-17 | 5.3 | `baixar_manual.py --auto`: o userscript `navegador/compras_auto.user.js` clica no download do zip e avisa quando a compra não o tem; intervalo aleatório entre compras e pausa após falhas seguidas; hCaptcha não contornado. Testado em 2026-08 com `--intervalo 0`: cerca de 6 s por compra, sem desafios; `idCompra` inválido é pulado |
| 2026-11-17 | 6 e 7 | Extração de 2026-08 em `dados/extracao/aberto-fechado_2026-08.db` (52.543 itens; Menor Preço 99,9% OK); Excel remove caracteres de controle; chave de carga por `id_compra` + item |
| 2026-11-17 | 6 | Parser 1.7.0: lê os valores `P% (R$ V)` de Maior Desconto (antes REVISAR sem lances); melhor lance = menor R$ nos dois critérios; colunas `*_percentual`; `criterio_julgamento_item` passa para o bloco principal; 2026-08 reprocessado |
| 2026-11-17 | 6 | Parser 1.7.1: junta valores da proposta quebrados em duas linhas e o parágrafo de situação quebrado palavra a palavra (corrige lance aceito, valor negociado e propostas iniciais não lidos); 2026-08 reprocessado |
