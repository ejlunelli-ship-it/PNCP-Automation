"""Traz do dados/pncp.db (somente leitura) material/serviço e orçamento sigiloso dos itens dos PDFs.

Chave (docs/07 §7): id_compra (17 dígitos do nome do PDF) + numero_item, registro_principal = 1.
Saída: ligacao_pncp.csv.gz (uma linha por id_compra × item; itens com mais de uma compra no banco são marcados).
"""
import json, os, sqlite3
from pathlib import Path
import pandas as pd

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
PNCP = RAIZ / "dados" / "pncp.db"
EXTR = RAIZ / "PNCP-Automation" / "dados" / "extracao" / "aberto-fechado_2026-08.db"

antes = os.stat(PNCP)
ex = sqlite3.connect(f"file:{EXTR.as_posix()}?mode=ro", uri=True)
ids = pd.read_sql_query("select arquivo_origem from itens", ex).arquivo_origem.str.extract(r"-(\d{17})-item-")[0]
ex.close()
ids = sorted(ids.dropna().unique())

con = sqlite3.connect(f"file:{PNCP.as_posix()}?mode=ro", uri=True)
con.execute("create temp table alvo(id_compra text primary key)")
con.executemany("insert into temp.alvo values (?)", [(i,) for i in ids])
lig = pd.read_sql_query(
    """select c.id_compra, i.numero_item as item, c.numero_controle_pncp, c.modo_disputa, c.esfera,
              i.material_ou_servico, i.orcamento_sigiloso, i.criterio_julgamento, i.situacao_item as situacao_api,
              i.valor_unitario_estimado as estimado_api
       from temp.alvo a join compras c on c.id_compra = a.id_compra
       join itens i on i.numero_controle_pncp = c.numero_controle_pncp and i.registro_principal = 1""", con)
con.close()
depois = os.stat(PNCP)
assert (antes.st_size, antes.st_mtime_ns) == (depois.st_size, depois.st_mtime_ns), "pncp.db mudou"

lig["n_registros"] = lig.groupby(["id_compra", "item"]).item.transform("size")
lig.to_csv(AQUI / "ligacao_pncp.csv.gz", index=False, compression="gzip")
meta = {"pncp_db": str(PNCP), "bytes": antes.st_size, "mtime_ns": antes.st_mtime_ns, "id_compras_pdf": len(ids),
        "id_compras_no_banco": int(lig.id_compra.nunique()), "linhas": len(lig),
        "itens_duplicados": int((lig.n_registros > 1).sum())}
(AQUI / "ligacao_pncp_meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
print(meta)
