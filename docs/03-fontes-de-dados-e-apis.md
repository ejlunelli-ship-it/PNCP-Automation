# 3. Fontes de dados e APIs

Todas as APIs abaixo são públicas, sem autenticação. Use `User-Agent` de navegador no PNCP;
alguns caminhos respondem 403 ou 301 sem ele.

## Glossário: base, PNCP e plataformas

**"Nossa base"** é o `dados/pncp.db`, coletado da API Dados Abertos do Compras.gov.br. Pelo que foi
verificado, ela traz só os pregões feitos no sistema Compras.gov.br, e não todos os do PNCP.

| Nome | O que é | Na nossa base? |
|---|---|---|
| **PNCP** | Portal nacional que reúne as contratações de todas as plataformas | É a fonte mais ampla, mas não é a origem da base |
| **Compras.gov.br** | Sistema do governo federal onde o pregão acontece; também usado por estados e municípios | Sim |
| **Portal de Compras Públicas** | Plataforma privada usada por vários municípios; no PNCP aparece como `ECustomize Consultoria em Software S.A` | Não |
| **BLL, Licitanet, Licitar Digital e outras** | Outras plataformas privadas ou estaduais | Não |

O pregão acontece em uma plataforma, e ela publica os dados no PNCP. O PNCP inclui os pregões do
Compras.gov.br e os das demais plataformas.

Pregões Eletrônicos publicados de 2022-11 a 2026-10, medidos em 2026-11-03 pelo `totalRegistros` de
`contratacoes/publicacao` e comparados com `compras`:

| Ano | PNCP | Base | Base / PNCP | AF no PNCP | AF na base | Base / PNCP (AF) |
|---|---|---|---|---|---|---|
| 2022 (nov–dez) | 806 | 162 | 20,1% | 196 | 45 | 23,0% |
| 2023 | 55.044 | 23.550 | 42,8% | 16.306 | 9.862 | 60,5% |
| 2024 | 329.671 | 103.987 | 31,5% | 84.162 | 37.697 | 44,8% |
| 2025 | 396.625 | 114.759 | 28,9% | 100.917 | 42.970 | 42,6% |
| 2026 (jan–out) | 315.685 | 85.092 | 27,0% | 81.099 | 33.120 | 40,8% |
| **Total** | **1.097.831** | **327.550** | **29,8%** | **282.680** | **123.694** | **43,8%** |

No modo Aberto, a base tem 202.057 de 805.219 (25,1%). O Aberto-Fechado é 37,8% da base e 25,7% do
PNCP, então a base **super-representa** esse modo. A base representa os pregões feitos no
Compras.gov.br, não todos os do país: isso é limitação do estudo (ver §3.4). A comparação é de
totais, não compra por compra.

Onde estão os lances em cada caso:

- **Compras.gov.br:** nos relatórios do zip protegido por captcha; poucos órgãos publicam no PNCP.
- **Portal de Compras Públicas:** a Ata Final costuma estar no PNCP, sem captcha, mas essas compras
  ainda não estão na base.

"Portal de compras" é ambíguo, porque há portais estaduais, como o de Minas Gerais. Nestes documentos,
**Portal de Compras Públicas** é sempre a plataforma específica.

## 3.1 API Dados Abertos do Compras.gov.br (usada por `get.py`, `orgaos.py`, `coleta_*`)

Base: `https://dadosabertos.compras.gov.br`

| Endpoint | Uso |
|---|---|
| `modulo-contratacoes/1_consultarContratacoes_PNCP_14133` | Contratações; params `orgaoEntidadeCnpj`, `dataPublicacaoPncpInicial/Final` (ISO), `codigoModalidade`, `pagina`, `tamanhoPagina` (≤ 500) |
| `modulo-contratacoes/2_consultarItensContratacoes_PNCP_14133` | Itens por período de inclusão; traz `valorUnitarioEstimado`, `valorUnitarioResultado`, `codItemCatalogo`, `orcamentoSigiloso`, `temResultado` |
| `modulo-arp/...` | Atas de registro de preços (**ainda não usado**) |

**Códigos nesta API**: `codigoModalidade` 5 = Pregão (Eletrônico e Presencial), 6 = Dispensa,
7 = Inexigibilidade.

**Armadilhas**:
- A data final é **exclusiva**, exceto em `3_consultarResultadoItensContratacoes`, onde é **inclusiva**. Essa consulta aceita no máximo 365 dias.
- A paginação não é estável: perde-se menos de 1% das contratações e de 1% a 3% dos itens.
- A API de itens repete linhas idênticas, e o `totalRegistros` conta as repetições.
- O `idCompra` se repete entre contratações distintas. A chave única é o `numeroControlePNCP`.
- Antes de nov/2022 não há pregões. A API costuma estar cerca de um mês atrasada.

**Campos úteis do registro** (`get.py`): `idCompra`, `numeroControlePNCP`, `numeroCompra` (sem
ano, ex.: `90120`), `anoCompraPncp`, `orgaoEntidadeCnpj`, `unidadeOrgaoCodigoUnidade` (UASG),
`modoDisputaNomePncp`, `existeResultado`, `valorTotalHomologado`, `dataPublicacaoPncp`,
`dataAberturaPropostaPncp`.

**`idCompra`** = UASG (6) + modalidade (2) + número (5) + ano (4). Exemplo: `927744 05 90120 2025`
→ `92774405901202025`.

## 3.2 PNCP — API de consulta

Base: `https://pncp.gov.br/api/consulta` (swagger: `/api/consulta/swagger-ui/index.html`)

| Endpoint | Uso |
|---|---|
| `GET /v1/contratacoes/publicacao` | Por período: `dataInicial`, `dataFinal` (AAAAMMDD), `codigoModalidadeContratacao` (obrigatório), `codigoModoDisputa`, `cnpj`, `uf`, `pagina`, `tamanhoPagina` (≤ 50). Responde 204 quando vazio |
| `GET /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}` | **JSON completo da contratação** (o mesmo caminho em `/api/pncp/v1` responde 301) |
| `GET /v1/atas`, `/v1/atas/atualizacao` | Atas de registro de preços por período |

**Códigos no PNCP** (diferentes da API Dados Abertos!):
- Modalidade: **6 = Pregão Eletrônico**, 7 = Pregão Presencial, 8 = Dispensa.
- Modo de disputa: 1 = Aberto, 2 = Fechado, **3 = Aberto-Fechado**, 4 = Dispensa com disputa,
  5 = Não se aplica, 6 = Fechado-Aberto.

## 3.3 PNCP — API principal (arquivos)

Base: `https://pncp.gov.br/api/pncp` (swagger: `/api/pncp/swagger-ui/index.html`; spec em `/v3/api-docs`)

| Endpoint | Uso |
|---|---|
| `GET /v1/orgaos/{cnpj}/compras/{ano}/{seq}/arquivos` | Lista de documentos (`sequencialDocumento`, `tipoDocumentoId`, `tipoDocumentoNome`, `titulo`, `url`) |
| `GET {url}` (`/pncp-api/v1/.../arquivos/{n}`) | Download direto (`attachment`), **sem captcha** |
| `GET .../compras/{ano}/{seq}/itens`, `/itens/quantidade`, `/itens/{n}/resultados` | Itens e resultado (fornecedor e valor homologado; **sem lances**) |
| `GET .../compras/{ano}/{seq}/atas` → `/atas/{seqAta}/arquivos` | ARPs da compra e seus PDFs (204 se não for SRP) |
| `GET /v1/tipos-documentos` | Tabela de tipos |

**Tipos de documento relevantes**:
- 2 Edital;
- 11 Ata de Registro de Preços;
- **16 Outros Documentos** (onde os órgãos costumam pôr os termos);
- 26 Termo/Ato de Homologação;
- 27 e 28 Ata de sessão pública (eletrônica e presencial).

O `numeroControlePNCP` `CNPJ-1-SEQUENCIAL/ANO` se decompõe na URL. Exemplo:
`07954605000160-1-000350/2025` → `/orgaos/07954605000160/compras/2025/350`.

## 3.4 Descobertas importantes sobre o PNCP

1. **Na maioria dos órgãos, as compras do Compras.gov.br têm só o Edital no PNCP.** Os termos com
   a tabela de lances só existem no zip do Comprasnet, que é protegido por hCaptcha.
2. **Alguns órgãos publicam os termos do Compras.gov.br no PNCP.** Exemplo: Prefeitura de
   Fortaleza, CNPJ `07954605000160`, UASG 927744. Numa varredura de 241 pregões AF de 01–10/08/2025,
   cerca de 2% tinham os termos no PNCP.
3. **Contratação duplicada ("irmã")**: esses órgãos têm **duas** contratações para o mesmo pregão.
   - A do Compras.gov.br (`usuarioNome = "Compras.gov.br"`) é a que o `get.py` encontra e tem só o
     Edital.
   - A do sistema do próprio órgão (ex.: `compras.sepog.fortaleza.ce.gov.br`) tem os termos, com
     outro `codigoUnidade`.
   - Ligação entre as duas: mesmo CNPJ, mesmo ano, mesmo número de compra (`90120` ≡ `90120/2025`)
     e mesma `dataAberturaProposta`.
   - Exemplos: 90120/2025 → 355 (Compras.gov.br) e 350 (Fortaleza); 90118 → 349/348;
     90119 → 354/351.
4. Os títulos variam por órgão ("TERMO DE HOMOLOGAÇÃO-item-1",
   "termo-homologacao-<idCompra>-item-5", "relatorio-julg-hab-…-s1-item-3"). Por isso a validação
   é pelo **conteúdo** do PDF (tipo + UASG + número), não pelo título.
5. Pregões de **outras plataformas** (ex.: Portal de Compras Públicas, usado por João Pessoa e
   Vitória) publicam `AtaTotal_<n>.pdf` / "Ata Final". Esse arquivo também tem propostas, lances
   com status e chat, mas o layout é outro e **o parser atual não lê**. Ver
   [04](04-formato-dos-relatorios.md).

6. **A API Dados Abertos parece cobrir só compras feitas no Compras.gov.br.** Vitória não tem nenhuma compra na base, e João Pessoa só aparece a partir de 2025-12, com UASG própria. Logo, as Atas Finais de outras plataformas ficam fora da base nacional. Verificado nesses dois órgãos.
7. **Em 2026-11-03, nenhuma das 2.364 compras Aberto-Fechado com resultado em janeiro/2026 tinha termos na própria contratação**: 2.343 tinham um único arquivo, e as demais, edital, TR, ETP e afins. Sem as irmãs, o PNCP não acrescenta nada nesse recorte.

8. **Em 2026-11-03, a busca nas irmãs achou termos em 25 de 26 compras de Fortaleza e em nenhuma das 359 compras de uma amostra de 40 órgãos** (39 com busca completa; o Estado do Ceará teve 7 falhas da API). Publicar termos no PNCP parece ser exceção de poucos órgãos.

9. **A base cobre só parte dos pregões do PNCP.** Nas 400 primeiras contratações de 05–09/01/2026 (amostra
   não aleatória), 283 estão fora da base, publicadas por BLL, Licitanet, Licitar Digital, Betha, IPM e
   outras plataformas. Essas compras são consultáveis pelo PNCP e podem ter atas com lances.
10. **Limite de requisições:** `contratacoes/publicacao` responde 429 depois de umas 9 requisições seguidas,
    sem `Retry-After`. `codigoModoDisputa=3` reduz o mês a cerca de 1/4 das páginas (534 para 136).

11. **Medição de 2026-11-03 (pregões Aberto-Fechado publicados em 2025-12):** 6.785 no PNCP, 2.737 na base (40%) e 4.048 fora (60%). Numa amostra aleatória de 300 entre os 2.269 fora da base com valor homologado, 47 (15,7%) têm PDF com indício de tabela de lances, por critério automático (5 ou mais menções a lance e 10 ou mais valores). Dos 12 exemplos abertos, todos têm tabela de lances com data e hora. O Portal de Compras Públicas (usuário `ECustomize Consultoria em Software S.A`) concentra 34 dos 47: 34 de 38 compras dele (89%).

### Nem toda compra tem PDF na API

Publicar os termos no PNCP é opcional. Na maioria das compras eles só existem no zip do
Compras.gov.br, protegido por hCaptcha. A cobertura pela API é parcial e depende do órgão.

"Sem termos no PNCP" significa que **nenhum arquivo passou pela busca**, não que o PDF não exista.
Causas conhecidas de falso negativo em `pncp_arquivos.py`:

- falha da API depois das tentativas, tratada hoje como se não houvesse arquivo;
- PDF escaneado, sem texto (`pncp_arquivos.py` não aplica OCR);
- termo em "Outros Documentos" com título genérico, que nem é baixado;
- contratação irmã fora da janela de busca ou com número ou abertura diferentes;
- arquivo acima de 50 MB;
- Ata Final de outra plataforma, que tem lances mas não é lida pelo parser.

### Outras fontes de lances investigadas (2026-11-03)

Busca nas especificações públicas (`/v3/api-docs`) das três APIs: **nenhum endpoint público traz os
lances por etapa**. Só os PDFs de relatório têm essa informação.

| Endpoint | O que traz | Serve para lances por etapa? |
|---|---|---|
| Dados Abertos `modulo-legado/4_consultarItensPregoes` | `menor_lance`, `valor_negociado`, `valor_homologado_item` | Não: um valor só, sem etapa. Sistema antigo: nenhum dado nas datas testadas de 2025 e 2026, e nenhuma das 42 compras de um lote de janeiro/2024 estava na base |
| Dados Abertos `modulo-ocds/1_releases` | `tender` e `awards` | Não pelo esquema, que não tem `bids`. As consultas de teste deram erro 400, então o conteúdo real não foi visto |
| Dados Abertos `modulo-contratacoes/3_consultarResultadoItensContratacoes_PNCP_14133` | Um registro por resultado (`sequencialResultado`), valor homologado | Não; é a fonte da tabela `resultados` |
| Dados Abertos `alice/*` e `usuarios/*` | Restritos (autenticação `bearerAuth`) | Não testados; fora do acesso público |
| PNCP `.../itens/{n}/resultados` | Fornecedor e valor homologado | Não |

## 3.5 Compras.gov.br (Comprasnet) — download manual

- Página da compra:
  `https://cnetmobile.estaleiro.serpro.gov.br/comprasnet-web/public/compras/acompanhamento-compra/item/1?compra=<idCompra>`
- Menu **Downloads → Todos os relatórios e termos** → `relatorios-compra-<idCompra>.zip`.
- Protegido por **hCaptcha**. Decisão do projeto: **não contornar** (ver [05](05-decisoes-e-pendencias.md)).
- O zip só existe para compras com resultado (homologadas).

## Exemplos para teste

| Caso | Links |
|---|---|
| AF completo no PNCP (Fortaleza 90118/2025) | `/api/consulta/v1/orgaos/07954605000160/compras/2025/349` (Compras.gov.br) e `/348` (irmã com os termos) |
| AF com itens em grupo (Fortaleza 90119/2025) | irmã 351, arquivo 5 = "TERMO DE HOMOLOGAÇÃO-grupo1" (itens 1–6) |
| AF de 1 item (Fortaleza 90120/2025) | `https://pncp.gov.br/pncp-api/v1/orgaos/07954605000160/compras/2025/350/arquivos/11` |
| Aberto, Portal de Compras Públicas (João Pessoa 08002/2025) | `https://pncp.gov.br/pncp-api/v1/orgaos/08778326000156/compras/2025/9/arquivos/2` |
| AF, Portal de Compras Públicas (Vitória 123/2025) | `https://pncp.gov.br/pncp-api/v1/orgaos/27142058000126/compras/2025/393/arquivos/4` |
