# PNCP-Automation — contexto para o Claude

Responda sempre em **português**. Código, comentários e mensagens do projeto também são em português.

## Objetivo em uma frase

Medir o **desconto obtido em cada modo de disputa** do Pregão Eletrônico (Lei 14.133/2021) —
**Aberto** vs **Aberto-Fechado**, e dentro do Aberto-Fechado a **etapa aberta** vs a **etapa
fechada** — com e sem pareamento UASG × item. O desconto por etapa só existe nos PDFs de
relatório da compra (termos de homologação/julgamento); por isso o projeto coleta e lê esses PDFs.

Detalhes: [docs/README.md](docs/README.md) (índice). Comece por
[docs/01-objetivo-e-metodologia.md](docs/01-objetivo-e-metodologia.md).

## Mapa rápido

| Etapa | Script | Saída |
|---|---|---|
| Listar órgãos (opcional) | `orgaos.py` | `dados/orgaos/` |
| Coletar pregões de órgãos | `get.py` | `dados/brutos/`, `dados/filtrados/pregao_<modo>/` |
| Baixar PDFs (PNCP automático → navegador manual) | `relatorios.py` + `pncp_arquivos.py` | `dados/filtrados/<pasta>/relatorios/`, `pendentes.csv` |
| Extrair campos dos PDFs | `python -m extrator_homologacao` | `dados/extracao/homologacoes.{xlsx,db}` |
| Base nacional (API, sem PDF) | `coleta_anos.py`, `coleta_itens.py` | `dados/brutos/<ano>/` |
| Banco unificado da base nacional | `banco_unificado.py` | `dados/pncp.db` |
| Análises | `matching_*.py` | terminal |

## Ambiente (máquina do usuário, Windows)

- Python 3.13 em `.venv` (`.\.venv\Scripts\python.exe`); dependências em `requirements.txt`.
- Git em `C:\Program Files\Git\cmd\git.exe` (pode não estar no PATH de sessões antigas).
- Dados em `dados/` (não versionado) ou na pasta da variável `PNCP_DADOS`. Para testes, use
  `PNCP_DADOS` apontando para uma pasta temporária para não misturar com os dados reais.
- Sem OCR instalado (OCRmyPDF/Tesseract); use `--sem-ocr` no extrator.

## Regras

- **Não contornar o hCaptcha** do Compras.gov.br (sem solvers, sem chamar endpoints internos sem o
  token). Automação permitida: PNCP (público) e abrir a página para o usuário clicar.
- Valores monetários são unitários, em `Decimal`; ausente = vazio, nunca zero.
- Ao mudar o parser, incremente `VERSAO_PARSER` em `extrator_homologacao/__init__.py`.
- Decisões em aberto e próximos passos: [docs/05-decisoes-e-pendencias.md](docs/05-decisoes-e-pendencias.md).
  Atualize esse arquivo quando uma decisão for tomada ou um passo concluído.
