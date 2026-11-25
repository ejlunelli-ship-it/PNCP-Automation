# Risk-set matching + DiD na cesta S1 (25/11/2026)

Avalia o efeito do modo Aberto-Fechado (AF), frente ao Aberto (A), sobre o preço relativo homologado. O método pareia,
evento a evento, as UASGs que trocam de modo com UASGs comparáveis do mesmo trimestre e do mesmo modo de origem, e
estima um DiD com peso igual por evento. Usa só a cesta S1 da validação automática de catálogo.

**Resultado:** o desenho principal **não tem suporte** (4 eventos pareados, 2 estimáveis). A insuficiência foi declarada
no protocolo antes da Fase II, e as estimativas são descritivas. Ver [`conclusao.md`](conclusao.md).

## Execução

```powershell
..\..\.venv\Scripts\python.exe executar.py                      # tudo; etapas válidas são puladas (hashes)
..\..\.venv\Scripts\python.exe executar.py --etapas testes      # só os 40 testes
..\..\.venv\Scripts\python.exe executar.py --refazer estimacao  # força uma etapa
```

**Etapas:**
- `fontes`
- `painel`
- `eventos`
- `desenho`: Fase I e congelamento
- `estimacao`: Fase II
- `testes`
- `relatorio`

**Dados e intermediários:**
- Os intermediários volumosos ficam em `D:/risk_set_matching_s1_trabalho/` (painel, eventos, desenhos e atividade
  agregada do banco, cerca de 40 MB).
- Fontes, somente leitura: `dados/pncp_v2.db` e `D:/efeito_modos_auto_S1/`.
- Requer `pyarrow`, instalado no `.venv` para o parquet dos pares.

## Estrutura

**Documentos:**

| Arquivo | Conteúdo |
|---|---|
| `protocolo.md` | protocolo |
| `metodologia.md` | métodos |
| `relatorio.md` | relatório (gerado) |
| `conclusao.md` | respostas às 15 perguntas |
| `config.json` | parâmetros, todos fixados antes da Fase II |

**Pastas:**
- `scripts/`:
  - `verificar_fontes.py`, `construir_painel.py`, `identificar_eventos.py`, `construir_risk_sets.py`,
    `construir_covariaveis.py`, `estimar_propensao.py`, `realizar_matching.py`, `diagnosticar_balanceamento.py`,
    `executar_placebos.py`, `desenho.py` (Fase I), `estimar_did.py`, `inferencia.py`, `testar_composicao.py`,
    `robustez.py`, `fase2.py` (Fase II), `gerar_relatorio.py`, `pipeline.py`, `executar_testes.py`, `comum.py`.
- `resultados/`:
  - `protocolo_congelado.json`
  - `pares_congelados.parquet`
  - `manifesto_matching.json`
  - `diagnostico_desenho.json`
  - `fontes.json`
  - resumos
  - `resultado_testes.json`
- `tabelas/`:
  - funil de suporte
  - viabilidade
  - conjuntos de risco
  - balanceamento (geral e por trimestre)
  - propensity score
  - placebos
  - efeitos (R1–R17, X1–X4)
  - amostra comum
  - influência
  - censura
  - composição
  - comparação com o dCDH
  - integridade do código
- `graficos/`: funil, viabilidade, balanceamento (love plot), PS, placebos, comparação de desenhos, trajetórias.
- `testes/`: `test_risk_set.py` (40 testes) e `sintetico.py`.
- `manifesto.json`: SHA-256 de todos os arquivos.

## Diagnósticos de suporte (posteriores, descritivos)

[`diagnosticos_suporte.md`](diagnosticos_suporte.md) traz contagens, sem estimar efeitos
(`python executar.py --etapas diagnosticos`).

- **Coexistência:** compras em A e AF na mesma UASG, CNPJ e UF, por período e por produto × período.
- **Ausência de índice:** decomposição dos UASG/CNPJ-trimestres sem índice S1 e potencial de recuperação.
