# Alterações de código depois do registro do protocolo (25/11/2026 03:20)

Só correções de execução; nenhuma muda critério, amostra, especificação ou parâmetro registrado.

| Hora | Arquivo | Alteração | Efeito metodológico |
|---|---|---|---|
| 03:23 | `em/referencias.py` | nome da chave do config (`min_uasgs` → `min_outras_uasgs`); a execução parava com KeyError | nenhum (o valor registrado, 3, é o usado) |
| 03:25 | `em/referencias.py` | somas leave-one-out passam a ser calculadas como soma das OUTRAS UASGs (acumuladas à frente e atrás), sem subtrair a focal do total, e as somas em nível ficam em escala do máximo da célula | nenhum na definição; corrige perda de precisão numérica (cancelamento) quando a focal tem preços muito maiores que as demais, detectada pelo teste `test_uasg_focal_completamente_excluida` antes de qualquer resultado ser lido |
| 04:10 | `em/honest.py` | `l_vec` gravado com `repr` de NumPy (`np.float64(0.5)`) e ilegível no R; passa a ser gravado como número | nenhum (mesmos pesos 1/L registrados) |
| 04:31 | `em/comum.py` | `escrever_csv` passou a usar a união das colunas de todas as linhas; antes usava só as da 1ª linha e descartava colunas de linhas heterogêneas (ex.: EP em duas vias do E3, coluna `grupo` do dCDH nas referências). Etapas efeitos_fixos, robustez e secundarios reexecutadas | nenhum nos cálculos; só a gravação dos CSVs. Teste novo `test_csv_linhas_heterogeneas_nao_perdem_colunas` |
| 05:20 | `em/robustez.py` | removida uma cópia da amostra criada e nunca usada (`d_comum_all`, ~1 GB), depois que a execução foi interrompida por falta de memória | nenhum |
