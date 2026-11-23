"""Descrições e unidades de fornecimento por CATMAT (para o teste 08, homogeneidade dos produtos). Não usa preço.

Lê o pncp.db só para leitura (mesmo recorte da base de 23/11: Compras.gov.br, Pregão Eletrônico, Aberto/Aberto-Fechado,
abertura de 2022-01 a 2026-03, itens de material, registro principal), conferindo tamanho e mtime ao final.

Uso (da pasta PNCP-Automation):
    python analises/robustez_dispersao_20261123/preparar_descricoes.py --pncp-db ../dados/pncp.db
Saída: dados/robustez_dispersao/descricoes_catmat.pkl (contagens por CATMAT × unidade bruta × descrição).
"""
import argparse, sys
from pathlib import Path

sys.dont_write_bytecode = True
AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent / "testes_desenho_causal_20261123"))
import pandas as pd  # noqa: E402

import comum as C  # noqa: E402

SAIDA = C.RAIZ / "dados" / "robustez_dispersao"

SQL = f"""SELECT i.cod_item_catalogo AS catmat, i.unidade_medida AS un, i.descricao_resumida AS descricao, COUNT(*) AS n
FROM compras c JOIN itens i ON i.numero_controle_pncp = c.numero_controle_pncp
WHERE c.fonte = 'dados_abertos' AND c.modalidade_nome LIKE 'Preg%Eletr%' AND c.modo_disputa IN ('Aberto', 'Aberto-Fechado')
  AND substr(c.data_abertura_proposta, 1, 7) BETWEEN '{C.INI}' AND '{C.FIM_ITENS}'
  AND i.registro_principal = 1 AND i.material_ou_servico = 'M' AND i.cod_item_catalogo IS NOT NULL
GROUP BY 1, 2, 3"""


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pncp-db", type=Path, required=True)
    a = ap.parse_args(argv)
    SAIDA.mkdir(parents=True, exist_ok=True)
    sig = C.assinatura(a.pncp_db)
    con = C.ro(a.pncp_db)
    d = pd.read_sql_query(SQL, con)
    con.close()
    assert C.assinatura(a.pncp_db) == sig, "pncp.db mudou durante a leitura"
    d["catmat"] = pd.to_numeric(d.catmat, errors="coerce")
    d.to_pickle(SAIDA / "descricoes_catmat.pkl")
    print("linhas", len(d), "CATMATs", d.catmat.nunique(), "itens", int(d.n.sum()))
    print("FIM ok")


if __name__ == "__main__":
    main()
