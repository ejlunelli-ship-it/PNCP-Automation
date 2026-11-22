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
  `--auto`, `--modo`.
- **`--modo fechado-aberto`** (desde 20/11/2026): mesma seleção para os pregões Fechado-Aberto. A lista vem de
  `registro/compras_fechado-aberto/`, o registro vai para `registro/fechado-aberto_<mês>/` e os PDFs para
  `dados/filtrados/fechado-aberto_<mês>/relatorios/`. O padrão é `aberto-fechado`, com as pastas de sempre. Os dois
  modos não leem o registro um do outro. Passo a passo em [09](09-download-fechado-aberto.md).

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
  Dois navegadores no mesmo mês: um com `--parte 1/2`, outro com `--parte 2/2` (as compras não se cruzam).
- **Velocidade (desde 18/11/2026):** o registro é lido inteiro uma vez e depois só nos bytes novos de cada
  arquivo (até a última linha completa; antes, ~1 s de releitura por compra); a pasta Downloads é olhada a
  cada 0,25 s (antes 1 s); o arquivo é dado por gravado com o tamanho parado por 0,3 s (antes 1 s), sem
  `.part` ao lado e, no zip, com o diretório central legível; o zip recebido é movido para a pasta da compra
  e aberto/anotado numa fila de segundo plano (uma tarefa por vez) enquanto a próxima compra já carrega;
  ao sair, o script espera a fila esvaziar. Zip que falhar ao abrir não é anotado (volta numa próxima
  rodada). O userscript 1.3 confere a página a cada 150 ms (antes 500 ms). Medido com Chrome + Edge
  (`--parte 1/2` e `2/2`, `--intervalo 0`): 16,6 → 28,3 compras/min, sem mudança nos motivos.
  Com um terceiro navegador (Chrome `--parte 1/3`, Edge `2/3`, Firefox `3/3`): 31,2 compras/min (+10%),
  sem mudança nos motivos; cada navegador cai de ~14 para ~11/min, sinal de gargalo no site ou na rede.
  Ao mudar o número de partes, pare e relance todos juntos (senão dois processos abrem a mesma compra).
  No `--auto`, a espera pelo zip caiu de 5 para 2 min (`ESPERA_AUTO`, 18/11/2026): a cada ~15 min algum
  navegador ficava 5 min parado numa compra; o que passa de 2 min sai como `zip não recebido` e vai para o
  `--repetir --motivo "zip não recebido"` no fim do mês. O modo manual continua com 5 min.
  **Zip atrasado (19/11/2026):** o site às vezes entrega o zip depois dos 2 min, e ele ficava esquecido em
  Downloads (em 2026-09, 20 dos ~70 "zip não recebido" das primeiras horas). Antes de abrir uma compra ainda
  não completa, o script procura um zip dela já gravado em Downloads (não vazio, diretório central legível);
  se houver, move para a pasta da compra e processa como um zip recebido, sem abrir o site. Vale inclusive
  para compras já anotadas na passada manual, então o `--repetir --motivo "zip não recebido"` do fim do mês
  aproveita esses zips na hora.
  Não deixe a 1.2 e a 1.3 ativas juntas: as duas clicam no botão, o menu abre e fecha, e a compra sai
  como `sem botão de downloads no site`.
- **`--abas N`** (padrão 1): mantém N compras abertas ao mesmo tempo no mesmo navegador. Testado em
  18/11/2026 com 2 abas: 22% das compras saíram como `sem botão` (a aba em segundo plano não abre o menu de
  downloads) e o ritmo não subiu (29,4/min). **Não usar**; a opção fica para um teste futuro com janelas
  separadas ou o navegador sem suspensão de abas em segundo plano.
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
  Fechado-Aberto: `python registro.py compras --modo fechado-aberto` grava em `registro/compras_fechado-aberto/`.
  Mês sem compra do modo não tem arquivo; se a pasta da lista existe, o mês fica vazio, sem erro.
- **Migração:** `python registro.py migrar [AAAA-MM ...]` passa os antigos `motivos.csv`/`manual.csv` de
  `dados/filtrados/` para `registro/`, no nome do usuário atual, e deixa uma cópia `.migrado`. Enquanto não
  migrados, eles continuam sendo lidos. Janeiro/2026 foi migrado sem `data_hora`, `itens` e `sha256`.

## 6. Extração dos PDFs (`extrator_homologacao`)

Parser determinístico, com PyMuPDF e regex. Sem modelos de linguagem.

1. **Texto:** camada de texto do PDF; sem ela, OCR do PyMuPDF. Remove cabeçalho e rodapé repetidos.
   **Layout antigo** (PDFs emitidos até fev/2025, ex.: compras de 2023; parser 1.9.0): detectado pela data/hora
   sem "às" nas tabelas do item ou por `Porte MeEpp/Equiparada:`; o texto é refeito na ordem visual da página e
   normalizado para o formato atual. Ver [04 §4.1](04-formato-dos-relatorios.md), "Layout antigo". Nos termos de
   transição (listas de 2024-12 a 2025-02), o modo antigo também aceita valores de proposta com `(unitário)`
   (parser 1.9.1).
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
   - a etapa fechada usa só lances enviados na janela, inclusive em grupo;
   - **Fechado-Aberto (parser 1.10.0):** a etapa fechada é a proposta sigilosa de cada fornecedor
     (`Valor proposta`), que não aparece na tabela de lances: `melhor_lance_modo_fechado` é a melhor
     proposta e `melhor_lance_modo_fechado_validos` a melhor sem os desclassificados. Os convocados
     ("A etapa aberta foi iniciada para o item N. Fornecedores convocados apresentaram os lances entre…")
     partem da proposta na etapa aberta, que vai de "O item N foi aberto." em diante: todos os lances da
     tabela são da aberta, salvo os de uma janela de desempate, e `melhor_lance_modo_aberto` inclui as
     propostas, como no AF (sem lance, aberto = fechado). Lance antes da abertura vira REVISAR. As
     propostas não convocadas saem como "desclassificada por não atender aos critérios de classificação
     do modo de disputa fechado/aberto"; nunca são a melhor, então não mudam o valor válido.
     `lider_aberto_lance_fechado` e `reinicios_etapa_fechada` ficam vazios (só AF).
6. **Conferência:** compara com os valores da mensagem de encerramento. Em grupo, pela soma de
   valor × quantidade dos itens de cada convocado.
6a. **Liderança e quedas (parser 1.8.0),** para auditar os casos com lance fechado acima do aberto
   (docs/05, decisão de 2026-11-18). Não mudam nenhuma coluna anterior:
   - `cnpj_melhor_lance_aberto`: fornecedor do melhor valor da etapa aberta (propostas iniciais
     incluídas; em empate, o registrado primeiro, com a proposta antes dos lances);
   - `melhor_lance_modo_aberto_outro_fornecedor`: melhor valor aberto de um CNPJ diferente do líder.
     Serve para marcar o lance aberto isolado (líder muito abaixo do segundo) sem usar o valor final;
   - `lider_aberto_lance_fechado` (AF): o líder deu lance não excluído na janela fechada;
   - `reinicios_etapa_fechada` (AF): janelas fechadas abertas por "A etapa fechada foi reiniciada"
     (chat) ou "Retorno de item do Julgamento para a etapa fechada" (eventos);
   - `fornecedores_desclassificados` / `quantidade_desclassificados`: documentos com situação
     "Proposta desclassificada", "recusada" ou "Fornecedor inabilitado" na tabela de propostas;
   - `melhor_lance_modo_aberto_validos` / `melhor_lance_modo_fechado_validos`: melhores valores sem
     esses fornecedores (sensibilidade "só fornecedores válidos").
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
de outras plataformas não é lida; grupos foram testados em um único pregão; o layout antigo foi testado só em
PDFs de compras de 2023 (nenhum item em grupo entre eles).

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

### Desconto por etapa nos PDFs (`analise_etapas.py`)

Procedimento para qualquer máquina que extraiu os PDFs de um mês. Reporta **duas medidas principais**, sempre juntas
(decisão de 2026-11-18, docs/05):

- **todos os fornecedores:** melhor lance de cada etapa como registrado na disputa, mesmo que o fornecedor caia depois;
- **só fornecedores válidos:** sem os desclassificados, recusados e inabilitados da tabela de propostas (colunas
  `_validos` do parser 1.8.0).

Nas duas, após a fechada = mín(melhor aberto, melhor fechado), desconto = 1 − valor / estimado e desconto final =
aberta + ganho da fechada + ajuste pós-disputa. Amostra: `OK`, Menor Preço, estimado e lance aberto positivos, descontos
entre −100% e 99%.

**Fechado-Aberto (`--modo fechado-aberto`, parser ≥ 1.10.0):** a ordem se inverte. A 1ª etapa é a fechada (melhor
proposta sigilosa) e a 2ª a aberta: após a aberta = mín(melhor fechado, melhor aberto), desconto final = fechada +
ganho da aberta + ajuste pós-disputa, e a regressão estima `A (etapa aberta)` com interações `A_x_…`. A amostra exige
proposta fechada positiva (`com_proposta_fechada` no funil). As colunas levam os nomes do modo (`fechada_media`,
`apos_aberta_media`, `prop_aberta_melhorou`, `prop_aberto_melhor`). Marcas: só A3, C e D (A e B são da fechada do
AF); não há a linha `fechado_acima_aberto`, porque o aberto inclui as propostas e nunca fica acima. Saída padrão:
`dados/analise_etapas/fechado-aberto_<meses>/`. O padrão continua `--modo aberto-fechado`, com resultado idêntico ao
de antes da opção.

**Mês do item (regra de 2026-11-22, docs/05):** é o **primeiro mês do resultado da compra**, isto é, o primeiro
`registro/compras/<mês>.csv` em que ela aparece (`registro/compras_fechado-aberto/` no Fechado-Aberto; as listas têm as
compras com item homologado no mês, e o script lê os arquivos versionados, sem precisar do `pncp.db`). O mês da pasta do
PDF fica em `mes_pasta`, e `--meses` filtra pelo mês da regra. A pasta pode ser um mês posterior porque o download, feito
do mês mais recente ao mais antigo, pulava a compra já completa em outro mês. Na base 1.9.1, 189.573 itens AF (13,7%) e
2.752 FA mudam de mês. As médias do período não mudam; mudam `por_mes` e as interações `F_x_mes`/`A_x_mes`. Uma compra
cujo primeiro mês não foi extraído (2024-10, 2026-10) entra nesse mês com os itens baixados em outra pasta.
`--mes-da-pasta` volta à regra antiga e reproduz exatamente as rodadas anteriores. `resultados.json` registra a regra
em `regra_mes`.

1. `git pull` (parser ≥ 1.8.0 e o script).
2. Extrair o mês (§6): `python -m extrator_homologacao dados/filtrados/aberto-fechado_<mês>/relatorios --saida
   dados/extracao/aberto-fechado_<mês>.xlsx --workers 7 --sem-separar` (gera `aberto-fechado_<mês>.db`). Um banco
   extraído com versão anterior é recusado pelo script.
3. Rodar: `python analise_etapas.py --db dados/extracao/aberto-fechado_<mês>.db`. Opções: `--meses AAAA-MM ...`
   (filtra um banco com vários meses), `--db` repetido (junta bancos; itens repetidos são recusados) e
   `--pncp-db dados/pncp.db` (acrescenta sigiloso e serviço na regressão; sem ele, a regressão usa só licitantes,
   valor e mês).
4. Saídas em `dados/analise_etapas/<meses>/` (fora do git): `resultados.json`, `tabelas.xlsx` (abas `principais`,
   `decomposicao`, `teste_direto`, `regressao`, `marcas`, `sensibilidade_todos`, `por_mes`) e `por_item.csv.gz`.

**Especificação da regressão (padrão; decisão de 2026-11-20, docs/05).** A comparação entre etapas é **dentro do item**:
efeito fixo de item, estimado em **primeira diferença**. Cada item tem duas observações, o melhor lance da etapa aberta
(`F = 0`) e o melhor após a fechada (`F = 1`). Com efeito fixo de item, o modelo
`100·ln(preço_it) = α_i + β·F_t + Σ γ_k·(F_t × Z_ik) + ε_it` é numericamente igual à regressão da diferença
`Δy_i = 100·[ln(após_i) − ln(aberto_i)] = β + Σ γ_k·(Z_ik − Z̄_k) + Δε_i`. O efeito fixo `α_i` absorve tudo que é fixo no
item: produto, quantidade, estimado, órgão, UASG, data, plataforma e o número de licitantes. Por isso:

- **β** = variação média em pontos de log entre as etapas no mesmo item, com os moderadores na média (os `Z` são
  centrados). Não há efeitos principais de `Z`: eles são absorvidos por `α_i`. Só as interações `F × Z` são identificadas.
- **Moderadores `Z`:** ln(licitantes), ln(valor estimado total), dummies de mês e, com `--pncp-db`, orçamento sigiloso e
  serviço.
- **Erro-padrão** agrupado por **UASG**: a UASG é o conglomerado, não um efeito fixo. Os efeitos fixos de UASG
  ficariam redundantes, porque cada item pertence a uma só UASG.
- **Graus de liberdade:** pelo painel empilhado (*within*), não descontar os efeitos fixos de item, que estão aninhados
  nos conglomerados (convenção de `reghdfe` e Cameron–Miller). Descontá-los infla o erro-padrão em √2 com
  duas observações por item. A primeira diferença já sai correta.
- Não usar efeito fixo de UASG (nem de órgão) no lugar do de item para comparar as etapas: ele deixa variação entre itens
  da mesma UASG no estimador. Efeitos fixos de UASG, órgão ou produto só entram se a pergunta for **entre itens** (ex.:
  Aberto × Aberto-Fechado), que não é a desta regressão.
- **Conferência (20/11/2026, 31 meses):** o painel empilhado com efeito fixo de item reproduz os coeficientes da
  primeira diferença do script, com diferença < 1e-11 (β −24,850 todos / −21,810 válidos). Script e saída em
  `analises/conferencia_fe_item_20261120/` (`fe_item.py`, `resultado.txt`). Rodar de novo ao mudar a especificação.
  O erro-padrão coincide quando os efeitos de item não são descontados.

Conferência: com 2026-02 e `--pncp-db`, o script reproduz exatamente `analises/etapas_pdf_af_20261118/fevereiro_campos_novos.py`
(ganho de 14,8 p.p. com todos e 13,2 só com válidos; β −23,99 e −20,58). Leva ~3 min por mês (bootstrap de 2.000 réplicas).

## Histórico de mudanças

**Análise anual por sigilo de 17/11/2026:** [documentação, resultados e reprodução](08-testes-medias-precos.md). As extrações anteriores foram preservadas por hash; 305 registros foram conferidos novamente no SQLite. Mês foi substituído por ano nos estratos e referências, com análises separadas para sigilo 0/1 e desconto calculado quando o estimado é positivo em cada grupo. Metodologia, 30 testes e validações estão versionados em `analises/`; os arquivos volumosos permanecem locais.

**Análise de médias de 17/11/2026:** nova leitura somente leitura deste `dados/pncp.db`, registrada em [testes de médias](../analises/testes_medias_20261117/relatorio_completo.md). Mantém pregão eletrônico, materiais homologados, Menor preço, identidade de catálogo/apresentação e coorte madura; compara A/AF por produto×mês×UF. A recorrência foi novamente verificada somente nesses dois modos. Há desfechos separados para log do preço, desconto e razão para mediana contemporânea de outros órgãos. Protocolo, emenda anterior à estimação, consulta, amostras, validação direta no SQLite e inferência com agrupamentos estão na pasta da análise. Não altera coleta, parser ou banco.

| Data | Etapa | Mudança |
|---|---|---|
| 2026-11-22 | Análise | `analise_etapas.py --db dados/extracao/aberto-fechado_parser-1.9.1.db --pncp-db ../dados/pncp.db --saida dados/analise_etapas/2023-04_a_2026-10_parser-1.9.1` (43 meses, base completa, regra do primeiro mês: 196.872 itens mudam de mês). `pncp.db` só leitura, tamanho e mtime iguais. Funil: 1.469.565 → OK 1.463.292 → Menor Preço com estimado 1.415.856 → com lance aberto 1.393.103 → amostra 1.337.832 / 1.196.727; 73.464 compras, 2.501 UASGs. Ganho da fechada 15,37 (15,22–15,52) / 14,07 (13,91–14,22); `F` −24,81 / −21,96; `F_x_sigiloso` +3,05 / +2,23; `F_x_servico` −0,43 (p = 0,60) / −1,62 (p = 0,047). Fechado-Aberto não refeito (itens iguais). Números em [05](05-decisoes-e-pendencias.md) |
| 2026-11-22 | 5 | 2026-10 e 2024-10 (AF, cópia do usuário em `D:\PNCP - BACKUP`) extraídos com o parser 1.9.1 direto na base nova (backup `.antes-2024-10_2026-10.db`; progresso em `dados/extracao/2024-10_2026-10_parser-1.9.1_progresso.log`). 2026-10: 39.020 PDFs, OK 38.997, REVISAR 23, 39.018 itens; 2024-10: 56.932 PDFs, OK 56.747, REVISAR 184, ERRO 1 (escaneado), 56.931 itens. Conferido com o backup: nenhuma linha perdida; 5.991 linhas com outra pasta e todas as demais colunas iguais (compras baixadas em dois meses); 89.958 novas. Base: 1.491.783 itens, `integrity_check` ok; AF nos 43 meses (2023-04 a 2026-10) |
| 2026-11-22 | Análise | **Mês = primeiro mês do resultado** (decisão do usuário; seção *Desconto por etapa nos PDFs*). `analise_etapas.py` lê `registro/compras*/<mês>.csv`, guarda o mês da pasta em `mes_pasta` e registra a regra em `regra_mes`; `--mes-da-pasta` volta à regra antiga. Conferido: com `--mes-da-pasta`, o Fechado-Aberto sem `--pncp-db` reproduz `fechado-aberto_2023-05_a_2026-10_sem-pncp/resultados.json` em todas as chaves (só muda o caminho do banco). Refeitas com `--pncp-db ../dados/pncp.db` (tamanho e mtime iguais): AF em `dados/analise_etapas/2023-04_a_2026-09_parser-1.9.1/` (189.573 itens mudam de mês; 42 meses com o 2024-10 parcial, 6.652 itens) e FA em `fechado-aberto_2023-05_a_2026-10/` (2.752 itens); as rodadas pelo mês da pasta ficaram em `..._mes-da-pasta/`. Mudam só `por_mes` e a regressão (AF: `F` −24,791 igual, `F_x_sigiloso` +3,076 / +2,239; FA: `A_x_sigiloso` +4,636 com p = 0,001 / +2,449 com p = 0,064). Números em [05](05-decisoes-e-pendencias.md) |
| 2026-11-22 | Análise | `analise_etapas.py --db dados/extracao/aberto-fechado_parser-1.9.1.db --pncp-db ../dados/pncp.db --saida dados/analise_etapas/2023-04_a_2026-09_41meses_parser-1.9.1` (pasta renomeada depois para `2023-04_a_2026-09_parser-1.9.1_mes-da-pasta`; todos os 41 meses AF da base nova, só 1.9.1; o script ignorou os 22.218 itens Fechado-Aberto). `pncp.db` só leitura, tamanho e mtime iguais antes e depois. Funil: 1.379.607 itens → OK 1.373.517 → Menor Preço com estimado 1.329.552 → com lance aberto 1.308.519 → amostra 1.256.422 (todos) / 1.123.630 (válidos); 68.604 compras, 2.431 UASGs. Ganho da fechada 15,35 p.p. (IC 15,20–15,51) / 14,05 (13,89–14,20); `F` −24,79 (EP 0,27) / −21,94 (0,26); `F_x_sigiloso` +3,05 / +2,22; `F_x_servico` −0,70 (p = 0,40) / −1,81 (p = 0,028). Números e leitura em [05](05-decisoes-e-pendencias.md) |
| 2026-11-22 | 5 | **Base nova completa em 1.9.1.** 28 meses AF (2023-04 a 12, 2025-03 a 12, 2026-01 a 09) extraídos com o parser 1.9.1 (código de `ab2347e`), PDFs lidos de `D:\PNCP - BACKUP` (só leitura), um mês por execução (`--workers 4 --sem-separar --db` na base; backup `.antes-restantes.db`; progresso em `dados/extracao/restantes_parser-1.9.1_progresso.log`). 944.802 PDFs: OK 940.630, REVISAR 4.170, ERRO 2 (1 vazio, 1 escaneado). Base: 1.401.825 itens, `integrity_check` ok; AF 1.379.607 em 41 meses (faltam 2024-10 e 2026-10), Fechado-Aberto 22.218 inalterado; linhas do backup todas presentes (3 com outra pasta, colunas iguais). 505 compras estão em pastas de dois meses, com PDFs idênticos (amostra de 1.687 PDFs); com o `INSERT OR REPLACE` por item, cada item ficou no mês extraído por último (29.379 itens). Por falta de memória (8 GB), a extração parou 4 vezes no meio de um mês (sempre antes de gravar no SQLite, que vem depois do Excel); a retomada pula os meses concluídos e reaproveita o cache. No fim rodou fora do Claude Code, com um vigia que relança o script com menos processos |
| 2026-11-20 | Análise | Análise Fechado-Aberto refeita na primeira máquina sobre a base juntada. `analise_etapas.py --modo fechado-aberto --db dados/extracao/aberto-fechado_parser-1.9.1.db` sem `--pncp-db` (saída `..._sem-pncp/`) reproduz exatamente a rodada da segunda máquina (20.177 / 17.470 itens; ganho da aberta 9,94 e 10,52 p.p.; `A` −14,646 e −15,281). Com `--pncp-db ../dados/pncp.db` (só leitura; tamanho e mtime iguais antes e depois), saída `dados/analise_etapas/fechado-aberto_2023-05_a_2026-10/`: 19.681 / 17.042 itens na regressão (97,5% ligados), 232 / 231 UASGs. `A (etapa aberta)` −14,643 (EP 0,686) / −15,264 (0,714); `A_x_ln_lic` −5,140 / −3,978; `A_x_sigiloso` +5,012 (p < 0,001) / +2,791 (p = 0,042); `A_x_servico` +1,534 (p = 0,61) / +1,483 (p = 0,55). Números em [05](05-decisoes-e-pendencias.md), pendência 16 |
| 2026-11-20 | Análise | `analise_etapas.py`: cada `--modo` usa só os itens das pastas `<modo>_<mês>` e avisa quantos ignorou. Antes, sem `--meses`, os itens do outro modo entravam com o mês vazio, e isso aconteceria na base nova, que agora tem os dois modos. Conferido: nas bases `aberto-fechado_2025-03_a_2026-10.db` e `.com-1.9.1_20261120.db` não há item fora de `aberto-fechado_<mês>`, então as análises anteriores não mudam. Na base nova, o modo aberto-fechado lê 464.240 itens (1.9.1) e o fechado-aberto 22.218 (1.10.0) |
| 2026-11-20 | 5 | **Fechado-Aberto juntado à base nova** `dados/extracao/aberto-fechado_parser-1.9.1.db`, por decisão do usuário (exceção à regra de uma versão por base; docs/05). Backup `.antes-fechado-aberto.db`. Origem `dados/filtrados/fechado-aberto_2023-05_a_2026-10.db` (cópia do banco da segunda máquina, sha256 `4f9430e1…`, só leitura, hash igual antes e depois): 22.218 itens, parser 1.10.0, `modo_disputa` "Fechado/Aberto", 41 meses (2023-05 a 2026-10), mesmas 48 colunas, nenhuma chave em comum com a base. Inserção por nome de coluna, sem `OR IGNORE`. Base: 486.458 itens (Aberto/Fechado 1.9.1: 464.240, REVISAR 1.993; Fechado/Aberto 1.10.0: 22.218, REVISAR 21), `integrity_check` ok, linhas antigas iguais ao backup, Fechado-Aberto igual à origem nos dois sentidos; sha256 `78f61035…`. O nome do arquivo foi mantido |
| 2026-11-20 | 5 | 2024-03 a 2024-09 (1.9.1, primeiro usuário) juntados à base nova `dados/extracao/aberto-fechado_parser-1.9.1.db` (backup `.antes-2024-03_09.db`) a partir de `dados/filtrados/aberto-fechado_2024-03_a_2024-09.db` (só leitura, hash igual antes e depois; mesmas 48 colunas, 257.156 itens, todos 1.9.1). 2.792 itens de 70 compras já estavam na base em 2024-11 a 2025-02, com o mesmo hash do PDF e todas as colunas iguais fora `arquivo_origem`/`pasta`/`processado_em` (compras nas listas de dois meses, inteiras dos dois lados). Seguindo a regra anterior, ficaram no mês da base (`INSERT OR IGNORE` por nome de coluna). Entraram 254.364 itens novos. Base: 464.240 itens, todos 1.9.1, REVISAR 1.993, `integrity_check` ok. Por mês: 2024-03 19.911; 04 28.199; 05 32.208; 06 37.506; 07 48.432; 08 46.264; 09 41.844 (os outros meses iguais). Linhas antigas iguais ao backup (`EXCEPT`), linhas novas iguais à origem; sha256 `f2823700…` |
| 2026-11-20 | Análise | `analise_etapas.py --modo fechado-aberto` (ordem fechada → aberta; ver seção *Desconto por etapa nos PDFs*). Aberto-Fechado sem mudança: `resultados.json` e `por_item.csv.gz` de 2024-11/12 idênticos antes e depois. Primeira rodada: `--modo fechado-aberto --db dados/extracao/fechado-aberto_2023-05_a_2026-10.db` (sem `--pncp-db`, que não está nesta máquina; saída `dados/analise_etapas/fechado-aberto_2023-05_a_2026-10/`): 20.177 itens (todos) e 17.470 (válidos), 1.149 compras, 232 UASGs. Fechada 15,9% / 15,8%; após a aberta 25,8% / 26,3%; **ganho da aberta 9,9 p.p. (IC 9,0–10,9) e 10,5 p.p. (9,5–11,6)**; ganho relativo 11,1% / 11,7%; final 27,8% / 27,9%; a aberta melhora 63% / 64% dos itens e nunca piora; final = melhor lance em 67% / 87%. Decomposição (17.303): todos 19,1 + 10,7 − 1,8; válidos 15,8 + 10,5 + 1,6 = 27,9. Regressão: `A (etapa aberta)` −14,6 e −15,3 (EP 0,8); licitantes −5,3 e −4,1 (p < 0,001). Marcas: líder desclassificado 33,4%, aberto isolado 6,6%, fechado > 3 × aberto 1,5% |
| 2026-11-20 | 6 | Fechado-Aberto extraído inteiro com o parser 1.10.0 num banco próprio, `dados/extracao/fechado-aberto_2023-05_a_2026-10.db` (um mês por execução, de 2026-10 a 2023-05, `--workers 4 --sem-separar`; Excel/log/cache em `dados/extracao/fechado-aberto/`; 20:40–21:10). 22.220 PDFs de 1.204 compras: OK 22.197, REVISAR 21 (10 desempate ME/EPP sem encerramento, 7 valor negociado divergente, 3 sem proposta identificada, 1 evento de aceitação de outro fornecedor); nenhum ERRO. 22.218 itens gravados (2 sem uasg/compra/item), `integrity_check` ok, sha256 `4f9430e1…`. Etapas preenchidas em 21.537 itens; aberto abaixo do fechado em 13.077 e igual em 8.460 (sem lance na aberta), nunca acima. Resultado: homologado 17.464, fracassado 3.533, deserto 678, em andamento 347, revogado 173, anulado 18. Critério: Menor Preço 21.516, Maior Desconto 176 |
| 2026-11-20 | 6 | **Parser 1.10.0:** regra de etapas do Fechado-Aberto (seção 6, item 5). Até a 1.9.1 o modo saía com etapas vazias e REVISAR "sem regra de separação de lances por etapa" (983 de 1.494 PDFs na amostra). Teste em 50 compras sorteadas (semente 20261120; 1.494 PDFs de 2023 a 2026): OK 1.493, REVISAR 1 (item sem proposta identificada); fechado e aberto preenchidos em 1.359 itens (os demais são desertos ou fracassados sem proposta); aberto ≤ fechado em todos (igual em 578, sem lance na aberta); lance aceito acima do melhor final em 205 (líder desclassificado) e abaixo em 112 (todos com valor negociado). Conferência independente pelo texto dos 1.359 itens Menor Preço: fechado e aberto iguais em todos, depois de tirar do conferidor o "Intervalo mínimo entre lances" e os lances com `*`. Aberto-Fechado sem mudança: 600 PDFs de 2024-11 reextraídos iguais à base 1.9.1 em todas as colunas de etapa |
| 2026-11-20 | 5.3 | Download Fechado-Aberto concluído numa só máquina (`baixar_manual.py --modo fechado-aberto --auto --intervalo 0 --max-falhas 0 --de 2026-10 --ate 2023-04`, Chrome `1/3`, Edge `2/3`, Firefox `3/3`, 19:22–20:30): as 1.479 compras da lista têm registro; 1.204 completas, 190 zip sem termos, 65 compra não encontrada no site, 19 sem a opção no site, 1 acesso não autorizado. A única "zip não recebido" (2025-07) foi repetida com `--repetir --motivo` e se resolveu. 22.220 PDFs em `dados/filtrados/fechado-aberto_<mês>/relatorios/` |
| 2026-11-20 | 5, 5.3 | Download manual (`baixar_manual.py --auto --intervalo 0 --abas 2 --max-falhas 10`, Firefox, um mês por vez) de 2024-03 a 2024-09 concluído; `--max-falhas 10` porque, rodando sem terminal, a pausa após 3 falhas seguidas ("acesso não autorizado", "zip não recebido") travava a fila. Extraídos com o parser 1.9.1 em `dados/extracao/aberto-fechado_2024-03_a_2024-09.db` (257.156 itens; REVISAR 863; 6 PDFs em ERRO: 4 vazios e 2 escaneados). Ver docs/05 |
| 2026-11-20 | 5.3, 5.4 | **Opção `--modo fechado-aberto`** no `registro.py` e no `baixar_manual.py`. A `SELECAO` recebe o modo de disputa como parâmetro; as pastas usam o prefixo do modo (`registro/fechado-aberto_<mês>/`, `dados/filtrados/fechado-aberto_<mês>/`), e a lista fica em `registro/compras_fechado-aberto/`. O padrão `aberto-fechado` não muda nada: conferido que `registro.py compras` regera `registro/compras/` idêntico, 105.360 compra-mês em 43 meses. Lista Fechado-Aberto exportada do `pncp.db`: 1.576 compra-mês em 42 meses (2023-05 a 2026-10), 1.479 compras distintas, todas com `idCompra` válido. Teste sem navegador: `pendentes()` percorre as 1.576, e `--parte k/3` divide em 505, 481 e 493. Mês sem arquivo com a pasta da lista presente passa a ser mês vazio (2023-04 não tem Fechado-Aberto). `baixar_api.py` e `inventario_pdfs.py` seguem só Aberto-Fechado. Guia em [09](09-download-fechado-aberto.md) |
| 2026-11-20 | 5 | 2024-11 (extraído com o parser 1.9.1 em outra máquina) juntado à base nova `dados/extracao/aberto-fechado_parser-1.9.1.db` (backup `.antes-2024-11.db`) a partir de `dados/filtrados/aberto-fechado_2024-11_a_2024-12.db` (só leitura, hash `577bbf41…` igual antes e depois; mesmas 48 colunas, tudo em 1.9.1). O 2024-12 desse arquivo é idêntico ao da base (53.551 chaves, mesmo hash do PDF, nenhuma coluna diferente fora `processado_em`/`pasta`) e ficou como estava. Inseridos por nome de coluna, sem `OR IGNORE`, os 45.775 itens de 2024-11 (OK 45.502, REVISAR 273; nenhuma chave repetida). Base: 209.876 itens (2024-01 14.076; 02 17.142; 11 45.775; 12 53.551; 2025-01 38.401; 02 40.931), REVISAR 1.143, `integrity_check` ok; linhas anteriores iguais ao backup (`EXCEPT`) e 2024-11 igual à origem nos dois sentidos; sha256 `30004ad5…` |
| 2026-11-20 | 5 | Segunda máquina: 2024-12 e depois 2024-11 extraídos com o parser 1.9.1 num banco próprio, `dados/extracao/aberto-fechado_2024-11_a_2024-12.db` (`--workers 4 --sem-separar`, um mês por execução; Excel/log/cache `aberto-fechado_2024-1{1,2}.*`). 2024-12 (17:47–18:19): 53.551 PDFs, OK 53.277, REVISAR 274, igual à extração 1.9.1 da outra máquina; 2024-11 (18:19–18:45): 45.775 PDFs, OK 45.502, REVISAR 273; nenhum ERRO. 99.326 itens, `integrity_check` ok, sha256 `577bbf41…` |
| 2026-11-20 | 5.3 | Download manual (`baixar_manual.py --auto --intervalo 0 --max-falhas 0`, 3 navegadores com `--parte k/3`, uma janela por navegador) de 2025-02 a 2024-10 concluído (2025-03 já estava baixado na outra máquina). Compras com termos / da lista: 2025-02 2.119 / 2.675 (328 zip sem termos, 30 sem a opção no site, 2 sem botão de downloads, 1 não encontrada); 2025-01 1.961 / 2.500 (328, 24, 2 sem botão, 2 zip não recebido, 1 não encontrada, 1 idCompra inválido); 2024-12 2.989 / 3.900 (478 zip sem termos, 49 não encontradas, 38 acesso não autorizado, 36 sem a opção, 7 sem botão, 3 zip não recebido); 2024-11 2.660 / 3.362 (438, 21 sem a opção, 11 zip não recebido, 7 acesso não autorizado, 3 não encontradas, 1 sem botão); 2024-10 2.948 / 3.633 (463, 26, 6 acesso não autorizado, 6 sem botão, 3 não encontradas, 1 zip não recebido, 1 idCompra inválido). As compras da lista sem linha no registro já estavam resolvidas na pasta e foram puladas. Quando um navegador termina antes, o resto da parte k/3 de outro é dividido pelas partes k/6 e (k+3)/6, sem sobreposição. Pausado a pedido no fim de 2024-10; faltam 2024-09 a 2024-06 (o segundo usuário baixa de 2024-01 para cima, já com 2024-03 parcial) e repetir as "zip não recebido" e "sem botão de downloads" com `--repetir --motivo` |
| 2026-11-20 | Análise | `analise_etapas.py --db dados/extracao/aberto-fechado_2025-03_a_2026-10.db --meses 2023-04 … 2024-02 2024-12 … 2026-10 --pncp-db ../dados/pncp.db --saida dados/analise_etapas/2023-04_a_2026-10_34meses` (34 meses, todos os da base; 2023 e 2024-01/02 em 1.9.0, 2024-12 a 2025-02 em 1.9.1, demais em 1.8.0). Números em [05](05-decisoes-e-pendencias.md), pendência 14 |
| 2026-11-20 | 5 | 2024-12 (download completo), 2025-01 e 2025-02 reextraídos com o parser 1.9.1 em `dados/extracao/aberto-fechado_2024-12_a_2025-02.db` (15:58–16:50, `--workers 7 --sem-separar`; a extração 1.9.0 ficou em `.v190.db`): 2024-12 com 53.551 itens (OK 53.277, REVISAR 274), 2025-01 com 38.401 (38.132 / 269), 2025-02 com 40.931 (40.664 / 267); nenhum ERRO. REVISAR caiu de 5.687 (1.9.0) para 810. Juntado à base `aberto-fechado_2025-03_a_2026-10.db` (nome mantido; backup `.antes-2024-12_2025-02.db`) com `INSERT OR IGNORE` por nome de coluna: 132.880 itens novos; 3 itens com a mesma chave e o mesmo hash de itens de 2025-03 ficaram como 2025-03. Base: 1.149.486 itens (1.8.0: 888.634; 1.9.0: 127.972; 1.9.1: 132.880), `integrity_check` ok, hash do banco dos 3 meses igual antes e depois |
| 2026-11-20 | 5 | **Bases por versão (decisão do usuário):** a base antiga `aberto-fechado_2025-03_a_2026-10.db` foi restaurada do backup `.antes-2024-12_2025-02.db` (antes conferido: igual à base com 1.9.1 menos as 132.880 linhas 1.9.1, por `EXCEPT` em todas as colunas, nos dois sentidos); tem 1.016.606 itens (1.8.0: 888.634; 1.9.0: 127.972), `quick_check` ok. A versão com 2024-12 a 2025-02 em 1.9.1 foi renomeada para `.com-1.9.1_20261120.db` (a análise dos 34 meses foi feita sobre ela). Os meses em 1.9.1 ficam só na base nova `aberto-fechado_parser-1.9.1.db` |
| 2026-11-20 | 5 | Banco separado só com os meses em 1.9.1, a pedido do usuário: `dados/extracao/aberto-fechado_parser-1.9.1.db` = `aberto-fechado_2024-01_a_2024-02.db` + `aberto-fechado_2024-12_a_2025-02.db` (cópia por nome de coluna, sem `OR IGNORE`: nenhuma chave repetida; origens com hash igual antes e depois). 164.101 itens: 2024-01 14.076, 2024-02 17.142, 2024-12 53.551, 2025-01 38.401, 2025-02 40.931; REVISAR 870; `integrity_check` ok; sha256 `94deb975…`. Na base `aberto-fechado_2025-03_a_2026-10.db`, 2024-01/02 seguem em 1.9.0; 2024-12 a 2025-02 já estão lá em 1.9.1 (junção feita por outra sessão às 16:50); 3 itens de 2025-02 também estão na base como 2025-03 (mesmo hash) |
| 2026-11-20 | 5 | 2024-01 e 2024-02 reextraídos inteiros com o parser 1.9.1 no mesmo banco `dados/extracao/aberto-fechado_2024-01_a_2024-02.db` (`--workers 7 --sem-separar`; backup da versão 1.9.0 em `.v190.db`). Motivo: um dos 8 REVISAR "valor negociado diverge" de 2024-01 era termo de transição. Comparação item a item: mesmas 31.218 chaves; só uma compra muda (`98600105008532023`, 2024-01): 11 itens com melhor lance aberto diferente (7 antes vazios, 4 menores), 1 REVISAR → OK. Etapa fechada, estimado, situação e nº de fornecedores sem mudança. OK 31.158, REVISAR 60. Ainda não juntado à base |
| 2026-11-20 | 6 | **Parser 1.9.1: termos de transição** (propostas com `Porte MeEpp/Equiparada:` e valores com `(unitário)`): o modo antigo aceita o valor com ou sem `(unitário)` nas propostas (`tabelas.RE_VALOR_ANTIGO`) e na inferência do critério (`campos.RE_VALOR_EM_REAIS`). Antes, nesses termos, o valor e a situação das propostas não eram lidos ([04 §4.1](04-formato-dos-relatorios.md)). Amostra de 210 compras (4.281 PDFs): 2024-01/02 sem mudança; em 2024-12 a 2025-02, 180 REVISAR → OK, 738 itens com desclassificado identificado, 383 com lance aberto antes vazio e 347 com lance aberto menor (sempre a proposta inicial) |
| 2026-11-20 | 5 | 2024-12 (download parcial), 2025-01 e 2025-02 extraídos com o parser 1.9.0 em `dados/extracao/aberto-fechado_2024-12_a_2025-02.db` (`--workers 7 --sem-separar`): 53.551, 38.401 e 40.931 itens (REVISAR 1.695, 2.583 e 1.409; nenhum ERRO). O REVISAR alto ("valor negociado diverge … tabela de propostas None", 4.877 itens) levou à 1.9.1; essa extração não foi juntada à base |
| 2026-11-20 | Análise | Especificação da regressão registrada como padrão (seção *Desconto por etapa nos PDFs*): efeito fixo de item em primeira diferença, erro-padrão agrupado por UASG (conglomerado, não efeito fixo). O código não mudou (só a docstring). Conferido nos 31 meses: o painel empilhado com efeito fixo de item dá os mesmos coeficientes (β −24,850 / −21,810) |
| 2026-11-20 | Análise | `analise_etapas.py --db dados/extracao/aberto-fechado_2025-03_a_2026-10.db --meses 2023-04 … 2023-12 2024-01 2024-02 2025-03 … 2026-10 --pncp-db ../dados/pncp.db --saida dados/analise_etapas/2023-04_a_2026-10_31meses` (31 meses, todos os da base; 2023 e 2024 em 1.9.0, demais em 1.8.0). Números em [05](05-decisoes-e-pendencias.md), pendência 14 |
| 2026-11-20 | 5 | 2024-01 e 2024-02 (PDFs baixados pelo segundo usuário, em `dados/filtrados/aberto-fechado_2024-0{1,2}/relatorios`) extraídos com o parser 1.9.0 num banco próprio, `dados/extracao/aberto-fechado_2024-01_a_2024-02.db` (`--workers 6 --sem-separar`; Excel/log/cache `aberto-fechado_2024-<mês>.*`). Antes, teste em amostra de 50 compras por mês (1.756 PDFs): 1.8.0 (código de `fc02441^`) gravou 2 itens (todo o resto "nenhum bloco de item", layout antigo); 1.9.0 gravou 1.756 (OK 1.754). Extração completa: 2024-01 com 14.076 PDFs (OK 14.038, REVISAR 38) e 2024-02 com 17.142 (OK 17.119, REVISAR 23), nenhum ERRO; 31.218 itens, 1.370 compras; esfera/UF vazias como em 2023 (compras fora dos `contratacoes_*.json`). Juntado à base `aberto-fechado_2025-03_a_2026-10.db` (nome mantido; backup `.antes-2024-01_02.db`) com `INSERT OR IGNORE` por nome de coluna: nenhuma chave repetida, 31.218 itens novos; base com 1.016.606 itens, `integrity_check` ok; banco de 2024 com hash igual antes e depois |
| 2026-11-20 | Análise | `analise_etapas.py --db dados/extracao/aberto-fechado_2025-03_a_2026-10.db --meses 2023-04 … 2023-12 2025-03 … 2026-10 --pncp-db ../dados/pncp.db --saida dados/analise_etapas/2023-04_a_2026-10_29meses` (29 meses, todos os da base; 2023 em 1.9.0, demais em 1.8.0). Números em [05](05-decisoes-e-pendencias.md), pendência 14 |
| 2026-11-20 | 5 | 2026-08 em 1.8.0 incorporado à base a partir de `dados/filtrados/aberto-fechado_2026-03_04_08.db` (banco completo da segunda máquina, 145.929 itens; só leitura, hash conferido; backup `.antes-2026-08.db`): 40.617 itens 1.7.x substituídos pela regra de 2026-11-18, 105.312 já em 1.8.0 mantidos (2026-03 e 04 iguais), nenhum novo; colunas antigas iguais, salvo `quantidade_fornecedores` em 1 item. A pedido do usuário, removidos os 47 itens 1.7.1 das 6 compras ausentes da reextração. Base: 985.388 itens, nenhum em 1.7.x, `integrity_check` ok |
| 2026-11-20 | 5 | 2026-03 e 2026-04 em 1.8.0 (reextraídos na segunda máquina) incorporados à base `dados/extracao/aberto-fechado_2025-03_a_2026-10.db` (nome mantido; backup `.antes-2026-03_04.db`) a partir de `dados/filtrados/aberto-fechado_2026-03_04_08.antes-2026-08.db` (93.386 itens, só 03 e 04; só leitura, hash conferido antes e depois). Regra de 2026-11-18: 1.8.0 substitui 1.7.x (`INSERT OR REPLACE` pela chave, por nome de coluna; 76.655 itens, com as 34 colunas antigas idênticas nos dois) e o que a base já tem em 1.8.0 fica (16.731, idênticos); nenhum item novo. Ficam em 1.7.1 47 itens de 6 compras ausentes da reextração (docs/05, pendência 14). Base: 985.435 itens, só 03 e 04 mudaram, `integrity_check` ok. 2026-08 continua em 1.7.x (40.617 itens) |
| 2026-11-20 | Análise | `analise_etapas.py --db dados/extracao/aberto-fechado_2025-03_a_2026-10.db --meses 2023-04 … 2023-12 2025-03 … 2026-02 2026-05 2026-06 2026-07 2026-09 2026-10 --pncp-db ../dados/pncp.db --saida dados/analise_etapas/2023-04_a_2026-10` (26 meses; 2023 em 1.9.0, os demais em 1.8.0) e `--meses 2023-04 … 2023-12 --saida dados/analise_etapas/2023-04_a_2023-12`. Rodadas antes da incorporação de 2026-03 e 04. Números em [05](05-decisoes-e-pendencias.md), pendência 14 |
| 2026-11-20 | 5 | 2023-04 a 2023-12 extraídos com o parser 1.9.0 num banco próprio, `dados/extracao/aberto-fechado_2023-04_a_2023-12.db` (`--db`, um mês por execução, de 2023-12 para trás, `--workers 7 --sem-separar`; Excel/log/cache `aberto-fechado_2023-<mês>.*`; 33 min no total). 96.758 PDFs (95.796 no layout antigo): OK 96.559, REVISAR 198, ERRO 1 (PDF escaneado, sem camada de texto); 96.757 itens gravados, nenhum repetido entre os meses. Por mês (PDFs / OK / REVISAR): 12: 30.323 / 30.221 / 102; 11: 18.850 / 18.818 / 32; 10: 15.186 / 15.170 / 16; 09: 9.921 / 9.899 / 21 (+1 ERRO); 08: 10.042 / 10.034 / 8; 07: 6.719 / 6.714 / 5; 06: 4.037 / 4.026 / 11; 05: 1.451 / 1.448 / 3; 04: 229 / 229 / 0. Juntado à base `dados/extracao/aberto-fechado_2025-03_a_2026-10.db` (nome mantido; backup `.antes-2023.db`) com `INSERT OR IGNORE` por nome de coluna: 96.754 itens novos; 3 itens de 2023-09 com a mesma chave e o mesmo hash de itens de 2025-09 ficaram como 2025-09. A base tem 985.435 itens (2023-04 a 2023-12 e 2025-03 a 2026-10), os outros meses iguais, `integrity_check` ok. Uma primeira extração de 2023 com o parser 1.8.0 (19/11) gravou só 961 itens (os PDFs do layout atual; o resto saiu "nenhum bloco de item") e foi desfeita restaurando o backup |
| 2026-11-19 | 6 | **Parser 1.9.0: layout antigo** dos termos (PDFs emitidos até fev/2025), em `extrator_homologacao/layouts.py` ([04 §4.1](04-formato-dos-relatorios.md)): detecção pela data/hora sem "às" nas tabelas de eventos/lances do item ou por `Porte MeEpp/Equiparada:`; texto refeito na ordem visual da página (`texto.paginas_em_ordem_visual`) e normalizado; valores sem `(unitário)`; `valor_estimado_total` = estimado × quantidade e critério do item inferido pelo formato dos valores, anotados em `fontes_extracao` (docs/05, decisão de 2026-11-19); continuação de mensagem/evento na página seguinte juntada; janelas chat × eventos com folga de 2 s; "Adjucado e Homologado". Nos dois layouts: fim do desempate ME/EPP também por "O item N teve o 1º desempate encerrado às … O tempo expirou". Amostra de 3.000 PDFs de 2023: 2.963 de 2.964 OK no layout antigo; melhor lance aberto = valor da mensagem "lance entre R$ X e …" em 470 de 471; nos 962 PDFs do layout atual das pastas de 2023, só 4 REVISAR (desempate ME/EPP) mudaram, para OK |
| 2026-11-19 | 5.3 | Download manual (`baixar_manual.py --auto --intervalo 0 --abas 2`) de 2023 concluído: nenhuma compra pendente de 2023-04 a 2023-12. Nesta rodada, 2023-09 (100 pendentes) e 2023-08 (820): 2023-08 com 715 de 872 compras com termos (109 zip sem termos, 42 sem a opção no site, 5 acesso não autorizado, 1 não encontrada); 2023-09 com 728 de 880 (108, 41, 1 e 2). As 35 "sem botão de downloads" e 1 "zip não recebido" foram repetidas com `--repetir --motivo` e todas se resolveram. Não há lista antes de 2023-04: os itens Aberto-Fechado com resultado até 2023-03 (cerca de 77 compras, publicadas de 2022-11 a 2023-03) estão todos "Em andamento" nos brutos, nenhum "Homologado", e ficam fora da seleção do `registro.py` |
| 2026-11-19 | Análise | `analise_etapas.py --db dados/extracao/aberto-fechado_2025-03_a_2026-10.db --meses 2025-03 … 2026-02 2026-05 2026-06 2026-07 2026-09 2026-10 --pncp-db ../dados/pncp.db --saida dados/analise_etapas/2025-03_a_2026-10` (17 meses em 1.8.0; 2026-03, 04 e 08 de fora). Números em [05](05-decisoes-e-pendencias.md), pendência 14 |
| 2026-11-19 | 5 | **Nova versão da base**, `dados/extracao/aberto-fechado_2025-03_a_2026-10.db` = cópia de `aberto-fechado_2025-10_a_2026-08.db` (mantida) + `dados/filtrados/aberto-fechado_2026-09_a_2026-10.db` (outra máquina, parser 1.8.0, só leitura, hash conferido antes e depois). Mesmas colunas e chave, em outra ordem: inserção por nome de coluna com `INSERT OR IGNORE`. 83.086 itens novos (2026-09: 44.068; 2026-10: 39.018); 316 itens de 2 compras presentes nas listas de 2025-04 e 2026-09, com o mesmo hash e os mesmos valores, mantidos como 2025-04. Resultado: 888.681 itens, 2025-03 a 2026-10, sem item repetido, `integrity_check` ok |
| 2026-11-19 | Análise | `analise_etapas.py --db dados/extracao/aberto-fechado_2025-10_a_2026-08.db --meses 2025-03 … 2026-02 2026-05 2026-06 2026-07 --pncp-db ../dados/pncp.db --saida dados/analise_etapas/2025-03_a_2026-07` (15 meses em 1.8.0; 2026-03, 04 e 08 de fora). Números em [05](05-decisoes-e-pendencias.md), pendência 14 |
| 2026-11-19 | 5 | 2025-03 extraído com o parser 1.8.0 na base `dados/extracao/aberto-fechado_2025-10_a_2026-08.db` (backup `.antes-2025-03.db`; Excel/log/cache `aberto-fechado_2025-03.*`; `--sem-separar`), em duas rodadas (`--workers 5`, 21 min; depois `--workers 7`, 9 min, que pelo cache só leu os PDFs das repetições baixadas no intervalo). 39.181 PDFs: OK 35.900, REVISAR 3.281 (2.991 "nenhum bloco de item" de 133 compras, 271 sem etapa fechada); 36.190 itens. A compra `16038405900012025`, nas listas de 2025-03 e 2025-04, foi regravada pela chave com a cópia de março (134 itens no lugar de 117; resolve o PDF vazio de 2025-04, que passou a 40.747 itens). Base: 805.595 itens, sem item repetido, `integrity_check` ok |
| 2026-11-19 | Análise | `analise_etapas.py --db dados/extracao/aberto-fechado_2025-10_a_2026-08.db --meses 2025-04 … 2026-02 2026-05 2026-06 2026-07 --pncp-db ../dados/pncp.db --saida dados/analise_etapas/2025-04_a_2026-07` (14 meses em 1.8.0; 2026-03, 04 e 08 de fora). Números em [05](05-decisoes-e-pendencias.md), pendência 14 |
| 2026-11-19 | 5 | 2025-05 e depois 2025-04 extraídos com o parser 1.8.0 na base `dados/extracao/aberto-fechado_2025-10_a_2026-08.db` (nome mantido; backup `.antes-2025-05-04.db`; Excel/log/cache `aberto-fechado_2025-05.*` e `_2025-04.*`; `--workers 7 --sem-separar`, 18 e 23 min). 2025-05: 46.523 PDFs, OK 43.962, REVISAR 2.561 (2.040 "nenhum bloco de item" de 65 compras, 490 "não foi possível identificar a etapa fechada"); 44.483 itens gravados. 2025-04: 42.563 PDFs, OK 40.354, REVISAR 2.208 (1.698 de 88 compras sem bloco de item, 486 sem etapa fechada), ERRO 1 (PDF vazio do download interrompido); 40.864 itens. Nada anterior sobrescrito: a base passou de 684.175 para 769.522 itens, com os outros meses iguais; `integrity_check` ok. Ver [05](05-decisoes-e-pendencias.md), pendência 15 |
| 2026-11-19 | Análise | `analise_etapas.py` com `--pncp-db` sobre os 12 meses em 1.8.0 (2025-06 a 2026-02, 2026-05 a 07) da base `aberto-fechado_2025-10_a_2026-08.db`; saída em `dados/analise_etapas/2025-06_a_2026-07/`; números em [05](05-decisoes-e-pendencias.md), pendência 14 |
| 2026-11-19 | 5 | Base `dados/extracao/aberto-fechado_2025-10_a_2026-08.db` (nome mantido) + `dados/filtrados/junho2025.db` (segunda máquina, parser 1.8.0: 2025-06 com 40.649 itens e 2025-07 com 48.917), lida só para leitura (hash conferido antes e depois). Mesmas colunas em outra ordem: inserção por nome de coluna. Nenhum item com a mesma chave (uasg, modalidade, compra, item) nas duas, então os 89.566 entraram como novos; `integrity_check` ok. Resultado: 684.175 itens, 2025-06 a 2026-08. Backup `.antes-2025-06-07.db` |
| 2026-11-19 | Análise | `analise_etapas.py --db dados/extracao/aberto-fechado_2025-10_a_2026-08.db --meses 2025-08 … 2026-02 2026-05 2026-06 2026-07 --pncp-db ../dados/pncp.db` (10 meses em 1.8.0; 2026-03, 04 e 08 de fora por estarem em 1.7.x). Saída em `dados/analise_etapas/2025-08_a_2026-07/`; números em [05](05-decisoes-e-pendencias.md), pendência 14 |
| 2026-11-19 | 5 | 2025-08 extraído com o parser 1.8.0 na base `dados/extracao/aberto-fechado_2025-10_a_2026-08.db` (nome mantido; backup `.antes-2025-08.db`; Excel/log/cache `aberto-fechado_2025-08.*`; `--workers 7 --sem-separar`, 24 min). 51.235 PDFs: OK 50.466, REVISAR 769 (405 "não foi possível identificar a etapa fechada"); 50.920 itens gravados (OK 50.466, REVISAR 454), 315 sem uasg/compra/item ignorados (14 compras, termos só com o chat, ver [05](05-decisoes-e-pendencias.md), pendência 15). Nada anterior sobrescrito: a base passou de 543.689 para 594.609 itens, com as contagens dos outros meses iguais. As 213 compras da lista de 2025-08 sem linha no registro do mês estão resolvidas no registro de outros meses (o `baixar_manual.py` lê todos os meses), por isso o download do mês está completo |
| 2026-11-19 | 5 | Segunda máquina: 2025-07 extraído com o parser 1.8.0 no mesmo banco de junho, `dados/extracao/junho2025.db` (`--db`; Excel do mês em `julho2025.xlsx`; `--workers 3 --sem-separar`, 26 min). 49.505 PDFs de 3.262 compras: OK 48.383, REVISAR 1.122; 48.917 itens gravados (OK 48.383, REVISAR 534), 588 sem uasg/compra/item ignorados. O banco passa a ter 89.566 itens (2025-06: 40.649; 2025-07: 48.917), nenhum de junho sobrescrito; backup em `junho2025.antes-2025-07.db`. As 2.880 compras com itens gravados equivalem às 2.881 completas do registro: o mês inteiro está nesta máquina |
| 2026-11-19 | 5 | Segunda máquina: 2025-06 extraído com o parser 1.8.0 num banco próprio, `dados/extracao/junho2025.db` (Excel `junho2025.xlsx`; `--workers 3 --sem-separar`, 22 min). 42.114 PDFs de 2.905 compras: OK 40.175, REVISAR 1.939; 40.649 itens gravados (OK 40.175, REVISAR 474, quase todos "não foi possível identificar a etapa fechada"), 1.465 sem uasg/compra/item ignorados. Os ignorados vêm de só 49 compras (a maior com 270 PDFs) e são termos de homologação só com o chat da compra, sem o bloco do item ("nenhum bloco de item encontrado no relatório"); ficam para o parser (ver [05](05-decisoes-e-pendencias.md)) |
| 2026-11-18 | 5 | Segunda máquina: 2025-12, 2026-01, 05, 06 e 07 extraídos com o parser 1.8.0 num banco próprio, `dados/extracao/aberto-fechado_2025-12_a_2026-07.db` (`--db`, um mês por execução, `--workers` 2 a 4 por falta de memória; os meses de 2026 tinham sido extraídos antes com a 1.7.2, cujos caches foram descartados). 225.471 itens, todos 1.8.0: 2025-12 OK 42.658 / REVISAR 22; 01: 38.556 / 21; 05: 43.309 / 32; 06: 46.304 / 29; 07: 54.497 / 43 (PDFs sem uasg/compra/item ignorados: 104, 13, 4, 6, 0). Conferido contra o banco 1.7.2 (backup `aberto-fechado_2025-12_a_2026-07.antes-1.8.0_20261118.db`): nos 182.791 itens dos meses de 2026 só `processado_em` mudou; nenhum status mudou. Um PDF (`98998505900362025-item-32`) está em duas pastas de mês com o mesmo hash e ficou uma vez, atribuído a 2026-06 (último a rodar) |
| 2026-11-18 | 5 | 2025-11 extraído com o parser 1.8.0 (50.357 PDFs; OK 50.092, REVISAR 265; 50.259 itens gravados, 98 sem uasg/compra/item) numa **nova versão da base**, `dados/extracao/aberto-fechado_20261118.db` = cópia de `aberto-fechado_2026-08.db` (2026-02 em 1.8.0; 03, 04 e 08 em 1.7.x) + 2025-11; 231.168 itens, nenhum item anterior sobrescrito. A base anterior ficou intacta. Excel do mês em `dados/extracao/aberto-fechado_2025-11.xlsx`. Esfera/UF vazias: as compras de 2025-11 não estão nos `contratacoes_*.json` do `get.py` |
| 2026-11-18 | 5 | 2025-09 extraído com o parser 1.8.0 na base `dados/extracao/aberto-fechado_2025-10_a_2026-08.db` (55.966 PDFs; OK 55.469, REVISAR 497; 55.841 itens gravados, 125 sem uasg/compra/item; `--workers 3`). A base passa a ter 543.689 itens, de 2025-09 a 2026-08, nenhum anterior sobrescrito; o nome do arquivo foi mantido. Backup em `aberto-fechado_2025-10_a_2026-08.antes-2025-09.db`; Excel do mês em `dados/extracao/aberto-fechado_2025-09.xlsx` |
| 2026-11-18 | 5 | **Nova versão da base:** `dados/extracao/aberto-fechado_2025-10_a_2026-08.db` (487.848 itens) = `aberto-fechado_20261118.db` (291.632) + a base de outra máquina `dados/filtrados/aberto-fechado_2025-12_a_2026-07.db` (225.471 itens, parser 1.8.0: 2025-12, 2026-01, 05, 06 e 07), lida só para leitura. 29.255 itens estavam nas duas (mesma chave e mesmo hash do PDF, em pasta de outro mês) e tinham as colunas antigas idênticas. Regra: 1.8.0 substitui 1.7.x (28.657 itens de 2026-02 a 08 ganharam os campos novos), e o `arquivo_origem` da base local é mantido para o mês do item não mudar; quando os dois estavam em 1.8.0 (598), fica o local; os demais 196.216 entram como novos. Por isso 2026-05, 06 e 07 têm menos itens aqui que na base de origem. As bases de origem ficaram intactas. Restam em 1.7.x: 42.656 itens de 2026-03, 34.046 de 04 e 40.617 de 08 |
| 2026-11-18 | 5 | 2025-10 extraído com o parser 1.8.0 na mesma base `dados/extracao/aberto-fechado_20261118.db` (60.560 PDFs; OK 60.150, REVISAR 410; 60.464 itens gravados, 96 sem uasg/compra/item; `--workers 3` por causa do download em paralelo). A base passa a ter 291.632 itens, nenhum anterior sobrescrito; backup em `aberto-fechado_20261118.antes-2025-10.db`. Excel do mês em `dados/extracao/aberto-fechado_2025-10.xlsx` |
| 2026-11-18 | Análise | `analise_etapas.py`: o id da compra passa a ser lido também dos relatórios de julgamento (`relatorio-julg-hab-<id>-sN-item-N.pdf`; 148 itens em 2025-11), e o script para se algum `arquivo_origem` não tiver o id. Fevereiro não muda. Primeira rodada com 2025-11 + 2026-02 em `dados/analise_etapas/2025-11_2026-02/` (docs/05, pendência 14) |
| 2026-11-18 | Análise | `analise_etapas.py`: procedimento replicável do desconto por etapa nos PDFs, com as duas medidas principais (todos os fornecedores e só válidos), decomposição, marcas do parser, regressão e resultados por mês. Exige parser ≥ 1.8.0. Ver seção "Análise" |
| 2026-11-18 | 5 | Parser 1.8.0: colunas novas de liderança da etapa aberta e quedas (`cnpj_melhor_lance_aberto`, `melhor_lance_modo_aberto_outro_fornecedor`, `lider_aberto_lance_fechado`, `reinicios_etapa_fechada`, `fornecedores_desclassificados`, `quantidade_desclassificados`, `melhor_lance_modo_aberto_validos`, `melhor_lance_modo_fechado_validos`; ver §6, item 6a). Só 2026-02 reprocessado no `aberto-fechado_2026-08.db` (backup em `aberto-fechado_2026-08.antes-1.8.0_20261118.db`) e no Excel do mês; conferido contra a versão anterior: nenhuma coluna antiga nem status mudou (1 item com fornecedor `ESTRANG` passou a contar 20 fornecedores, efeito da 1.7.2). 2026-03, 04 e 08 seguem em 1.7.x com as colunas novas vazias até serem reprocessados (docs/05, pendência 14) |
| 2026-11-18 | 4 | `baixar_manual.py` mais rápido, sem mudar o que é baixado nem o registro: leitura incremental do registro, Downloads olhado a cada 0,25 s, arquivo firme em 0,3 s (com teste do zip), zip aberto e anotado em segundo plano; userscript 1.3 (passo de 150 ms); `--abas N` testado e não recomendado (abas em segundo plano saem como "sem botão"). Ver §5.3 |
| 2026-11-18 | 5 | Parser 1.7.2: aceita `Identificador ESTRANG…` (fornecedor estrangeiro) onde se esperava CNPJ/CPF (`RE_DOCUMENTO` e os padrões "para X, CNPJ…"/"Fornecedor X, CNPJ…"); "participante com lance sem proposta listada" passa de problema a aviso. Reprocessados só os 28 itens REVISAR afetados no `aberto-fechado_2026-08.db` (todos viraram OK; backup em `aberto-fechado_2026-08.antes-1.7.2_20261118.db`); o Excel por mês não foi refeito. Restam 110 REVISAR, excluídos da análise (ver docs/05, decisão de 2026-11-18) |
| 2026-11-18 | 5 | Extração (parser 1.7.1) de 2026-02, 03 e 04 gravada no mesmo `dados/extracao/aberto-fechado_2026-08.db` (`--db`), e 2026-08 reprocessado com `--reprocessar`: 180.909 itens, todos em 1.7.1 (02: 34.933; 03: 45.625; 04: 47.808; 08: 52.543); o mês sai do caminho em `arquivo_origem`. Backup do banco anterior em `aberto-fechado_2026-08.antes-fev-abr_20261118.db`. 2026-01 fica de fora (download incompleto) |
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
| 2026-11-19 | 5 | `baixar_manual.py`: antes de abrir uma compra, usa o zip dela que chegou atrasado em Downloads (depois do `ESPERA_AUTO`) em vez de baixar de novo |
| 2026-11-19 | 6 | `extrator_homologacao/lote.py`: SHA-256 dos PDFs calculado em 8 threads (`HASH_THREADS`) antes da extração; a fase antes do parser caiu de ~10 para ~2 min num mês de ~45 mil PDFs. Não muda nenhum resultado (`VERSAO_PARSER` mantida) |
| 2026-11-19 | 5 | 2026-09 e 2026-10 extraídos com o parser 1.8.0 num banco próprio, `dados/extracao/aberto-fechado_2026-09_a_2026-10.db` (`--db`, um mês por execução, `--workers 4 --sem-separar`; Excel/log/cache `aberto-fechado_2026-09.*` e `_2026-10.*`; 17 e 19 min). 2026-09: 44.389 PDFs, OK 44.321, REVISAR 68; 44.384 itens gravados (OK 44.321, REVISAR 63; 2.265 compras com item OK), 5 sem uasg/compra/item ignorados. 2026-10: 39.020 PDFs, OK 38.997, REVISAR 23; 39.018 itens (OK 38.997, REVISAR 21; 2.272 compras), 2 ignorados. Nenhum ERRO; 83.402 itens; `integrity_check` ok. Falta juntar à base `aberto-fechado_2025-10_a_2026-08.db` (outra máquina) |
| 2026-11-19 | 5 | 2026-03 e 2026-04 reextraídos com o parser 1.8.0 num banco novo, `dados/extracao/aberto-fechado_2026-03_04_08.db` (`--db`, um mês por execução, `--workers 4 --sem-separar`; Excel/log/cache `aberto-fechado_2026-03.*` e `_2026-04.*`; 32 e 31 min). 2026-03: 45.606 PDFs, OK 45.578, REVISAR 28; 45.602 itens (OK 45.578, REVISAR 24; 2.203 compras com item OK), 4 ignorados (em 1.7.1: 45.625 itens). 2026-04: 47.827 PDFs, OK 47.756, REVISAR 71; 47.784 itens (OK 47.756, REVISAR 28; 2.076 compras), 43 ignorados (em 1.7.1: 47.808). Nenhum ERRO; 93.386 itens; `integrity_check` ok. 2026-08 fica para quando os PDFs estiverem nesta máquina (mesmo banco). Não comparado item a item com a 1.7.1 (a base 1.7.1 está na outra máquina) |
| 2026-11-19 | 5 | 2026-08 reextraído com o parser 1.8.0 no mesmo banco `dados/extracao/aberto-fechado_2026-03_04_08.db` (PDFs copiados da outra máquina; backup `.antes-2026-08.db`; Excel/log/cache `aberto-fechado_2026-08.*`; `--workers 4 --sem-separar`, 20 min). 52.640 PDFs, OK 52.501, REVISAR 139; 52.543 itens (OK 52.501, REVISAR 42; 2.317 compras com item OK; o mesmo total da 1.7.1), 97 ignorados. 2026-03 e 04 não mudaram. O banco tem 145.929 itens, os três meses em 1.8.0, nenhum ERRO; `integrity_check` ok |
