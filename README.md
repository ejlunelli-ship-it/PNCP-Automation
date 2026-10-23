# Contratações PNCP – Prefeitura de João Pessoa

Scripts para coletar as contratações (Lei 14.133/2021) da Prefeitura Municipal de João Pessoa
(CNPJ 08.778.326/0001-56) na API de Dados Abertos do Compras.gov.br, filtrar os pregões com modo
de disputa **Aberto-Fechado** e organizar o zip "Todos os relatórios e termos" de cada compra.

## Requisitos

- Python 3.10+
- `pip install -r requirements.txt`

## Uso

### 1. Coletar e filtrar — `get.py`

```bash
python get.py
```

- Consulta a API `modulo-contratacoes/1_consultarContratacoes_PNCP_14133` para as modalidades
  1 a 19, com paginação e retry em erros temporários (429/5xx/timeout).
- Período: últimos 365 dias até a data da execução.
- Filtro: `amparoLegalDescricao` contém "pregão" (sem diferenciar acento/maiúsculas) **e**
  `modoDisputaNomePncp` = "Aberto-Fechado".

Para coletar e já baixar os relatórios em seguida:

```bash
python get.py --relatorios
```

### 2. Baixar os relatórios — `relatorios.py`

```bash
python relatorios.py [caminho/para/filtrados.json]
```

O download no Compras.gov.br é protegido por hCaptcha, por isso ele é feito **manualmente**:

1. O script abre cada compra no navegador padrão.
2. Você clica em **Downloads → Todos os relatórios e termos**.
3. O script detecta `relatorios-compra-<idCompra>.zip` na pasta Downloads, move para a pasta da
   compra, extrai e abre a próxima.

Detalhes:

- Compras ainda não homologadas (sem `existeResultado`/`valorTotalHomologado`) são puladas, pois
  o site não oferece os relatórios para elas.
- Compras que já têm zip na pasta são puladas, então pode rodar de novo para baixar só o que falta.
- Se o download não acontecer em 5 minutos, a compra é pulada.

## Saída

```
dados/
├── brutos/
│   └── contratacoes_joao_pessoa.{json,csv}            # todas as contratações do período
└── filtrados/
    └── pregao_aberto-fechado/
        ├── contratacoes_pregao_aberto-fechado.{json,csv}
        └── relatorios/
            └── <numeroCompra>-<ano>_<idCompra>/       # zip + arquivos extraídos
```

Os CSVs são gravados em UTF-8 com BOM (abrem direto no Excel). A pasta `dados/` não é versionada.

## Novos filtros

Crie outra função no molde de `filtrar` em `get.py` e salve o resultado com
`salvar(registros, BASE / "filtrados" / "<nome>", "<arquivo>")`.
