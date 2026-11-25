# Validação técnica da cesta padronizada (25/11/2026)

Auditoria automática integral e formulários de revisão humana para decidir quais produtos da cesta candidata
(`../cesta_padronizada_20261124/`) têm especificação técnica homogênea. **Nenhum produto está aprovado:** a cesta
validada só nasce de decisões humanas documentadas. Protocolo: [`protocolo_validacao.md`](protocolo_validacao.md);
método: [`metodologia_validacao.md`](metodologia_validacao.md); resultados: [`relatorio.md`](relatorio.md);
leitura: [`conclusao.md`](conclusao.md).

## Comandos

```powershell
cd PNCP-Automation\analises\validacao_tecnica_cesta_20261125
..\..\.venv\Scripts\python.exe scripts\executar.py inspect                              # cabeçalhos, chaves, ligação
..\..\.venv\Scripts\python.exe scripts\executar.py preparar --prioridade P1 --limite 100 # piloto  -> saidas\piloto_P1_100\
..\..\.venv\Scripts\python.exe scripts\executar.py preparar --prioridade P1              # P1      -> saidas\P1\
..\..\.venv\Scripts\python.exe scripts\executar.py concluir --rodada piloto_P1_100 --exigir-dupla-revisao
..\..\.venv\Scripts\python.exe scripts\executar.py concluir --exigir-dupla-revisao       # rodada padrão P1
..\..\.venv\Scripts\python.exe scripts\executar.py testes                                # 39 testes -> saidas\resultado_testes.json
..\..\.venv\Scripts\python.exe scripts\executar.py relatorio                             # relatorio.md e manifesto.json
```

Só biblioteca-padrão do Python (≥ 3.10). As entradas são lidas como CSV ou em SQLite `mode=ro`:
- os CSV da cesta;
- o banco de trabalho da cesta em `D:\cesta_padronizada_trabalho\trabalho.db`;
- `D:\pncp.db`, do qual só se tira a impressão digital.

O banco de trabalho desta validação fica em `D:\validacao_tecnica_trabalho\`. Os caminhos estão em
`config/parametros.json`.

## Estrutura

| Caminho | Conteúdo |
|---|---|
| `config/mapa_colunas.json` | colunas reais usadas de cada entrada e padrões proibidos (preço, modo, desconto…) |
| `config/regras_atributos.json` | regras de extração, conversões exatas, vocabulários, riscos (versão 1.2.0) |
| `config/parametros.json` | caminhos, prioridades, requisitos de documentação, tipos de fonte |
| `config/revisores.csv` | **cadastro de revisores (vazio)**: só quem estiver aqui pode decidir |
| `scripts/` | `executar.py` (interface), `inspecionar_entradas.py`, `normalizar_especificacoes.py`, `extrair_atributos.py`, `auditar_homogeneidade.py`, `preparar_revisao.py`, `validar_revisao.py`, `relatorio.py`, `comum.py` |
| `testes/` | `test_validacao.py` (25 testes obrigatórios + 14 extras) e `mundo_sintetico.py` |
| `saidas/inspecao_entradas.json` | relatório da inspeção (cabeçalhos, cardinalidades, ligação, bancos) |
| `saidas/priorizacao_candidatos.csv` | os 16.248 candidatos com prioridade e ordem de revisão |
| `saidas/<rodada>/` | `base_produtos.csv`, `base_variantes.csv`, `descricoes_originais.csv`, `auditoria_atributos.csv`, `auditoria_conflitos.csv`, `vocabulario_chaves_declaradas.json` (arquivos-base imutáveis); `revisao_produtos.csv`, `revisao_variantes.csv` (formulários); `manifesto.json`; `resultado_revisao.csv`, `resultado_validacao.json`; `cesta_validada.csv` e `integracao_econometria/` só quando houver aprovações |
| `manifesto.json`, `relatorio.md` | índice das rodadas com hashes; relatório gerado das saídas |

A estrutura do pedido foi adaptada em um ponto: os arquivos de `saidas/` ficam numa subpasta por rodada. Assim o
piloto e o P1 não se sobrescrevem.

## Como revisar

1. Cadastre os revisores em `config/revisores.csv`: `id_revisor`, `nome`, `qualificacao`, `funcoes`.
2. Em `saidas/<rodada>/revisao_variantes.csv`, preencha cada variante:
   - `decisao_variante`: EQUIVALENTE, DIVERGENTE ou INDETERMINADA;
   - `fundamentacao`, `fonte_evidencia`, `revisor` e `data_revisao` (AAAA-MM-DD).
3. Em `revisao_produtos.csv`, preencha cada produto:
   - `decisao_produto`: APROVAR, REJEITAR, DESMEMBRAR ou PENDENTE;
   - `especificacao_canonica` no formato `NOME | ATRIBUTO: VALOR | …`, incluindo os `atributos_consenso`;
   - `fundamentacao`, `fonte_evidencia`, `resolucao_alertas` (obrigatória quando houver alertas ou riscos), `revisor` e
     `data_revisao`.
4. Escreva as fontes como `TIPO:identificador`, separadas por ` | `. Exemplos:
   - `EDITAL:00394452000103-1-000123/2024`;
   - `CATMAT:464393`;
   - `NORMA:NBR 14865`;
   - `FABRICANTE:https://…`.
5. Não altere as colunas não editáveis nem os arquivos-base: `concluir` recusa o formulário inteiro.
6. Rode `concluir --exigir-dupla-revisao` e depois `relatorio`.

## Modo automático (validador 2.0.0, sem revisores humanos)

Novo modo operacional, independente dos formulários manuais. O fluxo humano acima continua intacto. Método em
[`metodologia_automatica.md`](metodologia_automatica.md); resultados em `saidas/auto_P1_20261125/`
(`relatorio.md`, `conclusao.md`, `manifesto.json`).

```powershell
..\..\.venv\Scripts\python.exe scripts\executar.py auto-preparar   --prioridade P1   # base P1 congelada + itens (lista branca de colunas)
..\..\.venv\Scripts\python.exe scripts\executar.py auto-documentos --prioridade P1   # catálogo oficial CATMAT/PDM + documentos PNCP (cache)
..\..\.venv\Scripts\python.exe scripts\executar.py auto-validar    --prioridade P1   # classificação AUTO_* (famílias, subprodutos, itens)
..\..\.venv\Scripts\python.exe scripts\executar.py auto-auditar    --prioridade P1   # integridade, cobertura, integração, relatório
..\..\.venv\Scripts\python.exe scripts\executar.py auto-executar   --prioridade P1   # tudo, retomando do cache e dos checkpoints
```

**O que cada saída significa:**
- `AUTO_VALIDADO_CATALOGO` (S1) valida a homogeneidade de **catálogo**. Só ela entra em
  `cesta_catalogo_validada_automaticamente.csv`.
- `AUTO_VALIDADO_ITEM` (S4) exige o documento da própria contratação. É o conteúdo de `itens_validados_automaticamente.csv`.
- `AUTO_VALIDADO_CATALOGO_COM_RESSALVA` (S2) não é validação sem qualificação.

**Onde ficam os arquivos:**
- Cache, snapshot e checkpoints: `D:\validacao_tecnica_trabalho\auto\`.
- Código: `scripts/validacao_automatica/`.
- Testes: `testes/test_validacao_automatica.py`.
