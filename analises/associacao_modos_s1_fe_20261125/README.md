# Associação A × AF na cesta S1 com efeitos fixos (M1–M5) — 25/11/2026

Estudo associativo, não causal, entre os modos Aberto e Aberto-Fechado e o preço unitário homologado. Usa a cesta S1
(3.065 produtos validados automaticamente no nível do catálogo), com observações compra × produto e efeitos fixos de
alta dimensão.

**Especificação principal (M1):**

100 ln p = β AF + FE(UF × produto × trimestre) + FE(CNPJ) + γ ln q + ε

## Execução

```powershell
..\..\.venv\Scripts\python.exe executar.py                         # amostra, modelos, loo, verificacao, testes, relatorio
..\..\.venv\Scripts\python.exe executar.py --etapas testes,relatorio
```

- **Intermediários:** `D:/associacao_modos_s1_trabalho/`, com a amostra compra × produto e os resultados.
- **Fontes, somente leitura:** `dados/pncp_v2.db` e `D:/efeito_modos_auto_S1/S1`.
- **Duração:** cerca de 45 minutos.

## Arquivos

**Documentos:**

| Arquivo | Conteúdo |
|---|---|
| `relatorio.md` | relatório completo (gerado) |
| `conclusao.md` | leitura dos resultados |
| `metodologia.md` | métodos |

**Código:**
- `assoc/amostra.py`: amostra e agregação compra × produto, com conferência no banco.
- `assoc/estimar.py`: absorção dos efeitos fixos (LSMR + MAP) com verificação de convergência, inferência e
  diagnósticos.
- `assoc/pipeline.py`: as etapas.
- `assoc/relatorio.py`: relatório, gráficos e manifesto.

**Tabelas** (`tabelas/`):
- `modelos.csv`: todas as estimativas e variantes;
- `celulas_dois_modos.csv`;
- `contribuicao_cnpj.csv` e `contribuicao_uf.csv`;
- `loo_top10_cnpj.csv`;
- `verificacao_convergencia.csv`;
- `funil_amostra.csv`;
- `cobertura_trimestres.csv`.

**Demais saídas:**
- `graficos/`: coeficientes M1–M5, amostras comuns, exclusão de CNPJs.
- `testes/test_assoc.py`: 24 testes, sintéticos e de integração.
- `manifesto.json`: SHA-256 dos arquivos.

## Viabilidade de um painel CNPJ × trimestre (diagnóstico descritivo)

[`viabilidade_cnpj.md`](viabilidade_cnpj.md) traz contagens (`python executar.py --etapas viabilidade`):
- cobertura de preços S1;
- mudanças persistentes da participação AF;
- comparadores estáveis;
- decomposição dentro das UASGs × composição;
- produtos comuns, concentração e falsificação;
- censura do CATMAT.
