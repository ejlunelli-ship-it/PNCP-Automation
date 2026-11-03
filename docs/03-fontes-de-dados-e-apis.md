# 3. Fontes de dados e APIs

Todas as APIs abaixo são públicas, sem autenticação. Use `User-Agent` de navegador no PNCP;
alguns caminhos respondem 403 ou 301 sem ele.

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
- A data final é **exclusiva**.
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
