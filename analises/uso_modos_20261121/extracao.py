"""Extração da base de compras para a análise de uso dos modos (protocolo.md).

Lê dados/pncp.db somente para leitura e grava em dados/analise_uso_modos/ (fora do git):
    compras.pkl     uma linha por compra, com as variáveis agregadas dos itens
    categorias.pkl  compra × categoria (classe CATMAT ou grupo CATSER) com nº de itens, só Compras.gov.br
    rotulos.pkl     descrições de item mais frequentes por categoria

    python analises/uso_modos_20261121/extracao.py
"""
import os
import sqlite3
import time
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
DADOS = Path(os.environ.get('PNCP_DADOS', RAIZ / 'dados'))
SAIDA = DADOS / 'analise_uso_modos'

FILTRO = """c.modalidade_nome LIKE 'Preg%Eletr%'
  AND c.modo_disputa IN ('Aberto', 'Aberto-Fechado', 'Fechado-Aberto')
  AND substr(c.data_publicacao, 1, 7) BETWEEN '2022-11' AND '2026-10'"""

SQL_COMPRAS = f"""
SELECT c.numero_controle_pncp AS compra, c.fonte, c.orgao_cnpj AS cnpj, c.orgao_nome AS orgao_nome,
       c.uasg, c.codigo_unidade, c.nome_unidade, c.usuario_nome AS plat, c.esfera, c.poder, c.uf,
       substr(c.data_publicacao, 1, 7) AS mes, c.modo_disputa AS modo, c.srp, c.situacao_compra,
       COUNT(i.id) AS n_itens,
       AVG(i.material_ou_servico = 'M') AS f_mat,
       AVG(i.criterio_julgamento = 'Maior desconto') AS f_desc,
       AVG(i.tipo_beneficio LIKE 'Participa%') AS f_excl,
       AVG(i.tipo_beneficio LIKE 'Cota%') AS f_cota,
       AVG(COALESCE(i.orcamento_sigiloso, 0)) AS f_sig,
       SUM(CASE WHEN i.quantidade * i.valor_unitario_estimado > 0
                THEN i.quantidade * i.valor_unitario_estimado END) AS valor
FROM compras c
LEFT JOIN itens i ON i.numero_controle_pncp = c.numero_controle_pncp AND i.registro_principal = 1
WHERE {FILTRO}
GROUP BY c.numero_controle_pncp
"""

CAT = """CASE WHEN i.material_ou_servico = 'M' AND i.codigo_classe IS NOT NULL THEN 'M' || i.codigo_classe
              WHEN i.material_ou_servico = 'S' AND i.codigo_grupo IS NOT NULL THEN 'S' || i.codigo_grupo END"""

SQL_CAT = f"""
SELECT i.numero_controle_pncp AS compra, {CAT} AS cat, COUNT(*) AS n
FROM itens i JOIN compras c ON c.numero_controle_pncp = i.numero_controle_pncp
WHERE c.fonte = 'dados_abertos' AND {FILTRO} AND i.registro_principal = 1 AND {CAT} IS NOT NULL
GROUP BY 1, 2
"""

SQL_ROT = f"""
SELECT {CAT} AS cat, i.descricao_resumida AS descricao, COUNT(*) AS n
FROM itens i JOIN compras c ON c.numero_controle_pncp = i.numero_controle_pncp
WHERE c.fonte = 'dados_abertos' AND {FILTRO} AND i.registro_principal = 1 AND {CAT} IS NOT NULL
GROUP BY 1, 2
"""


def main():
    SAIDA.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(f"file:{DADOS / 'pncp.db'}?mode=ro", uri=True)
    for nome, sql in [('compras', SQL_COMPRAS), ('categorias', SQL_CAT), ('rotulos', SQL_ROT)]:
        t = time.time()
        df = pd.read_sql_query(sql, con)
        if nome == 'rotulos':
            df = (df.sort_values(['cat', 'n'], ascending=[True, False]).groupby('cat').head(5)
                  .groupby('cat').agg(descricoes=('descricao', lambda s: ' | '.join(map(str, s))), n_top=('n', 'sum'))
                  .reset_index())
        df.to_pickle(SAIDA / f'{nome}.pkl')
        print(nome, len(df), f'{time.time() - t:.0f}s', flush=True)
    con.close()


if __name__ == '__main__':
    main()
