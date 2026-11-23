"""Diagnóstico D (complementa diagnosticos.py): episódios de mudança de modo com critério flexível e cobertura de preço
homologado por fonte, para avaliar o poder de um estudo de eventos por unidade compradora. Só leitura.

D1. Mudança ≥ 50 p.p. na parcela de AF entre os 6 meses antes e os 6 meses depois (≥ 5 compras de cada lado),
    um episódio por unidade a cada 6 meses; e o número de itens de material com preço nessas janelas.
D2. Parcela dos itens (registro principal) com preço homologado positivo, por fonte e ano, numa amostra de compras.

Uso: python analises/parecer_desenho_causal_20261123/diagnosticos_d.py --pncp-db ../dados/pncp.db
Saída: acrescenta "D" ao diagnosticos.json.
"""
import argparse, json, os, sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
import importlib.util
spec = importlib.util.spec_from_file_location("diag", AQUI / "diagnosticos.py")
diag = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diag)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pncp-db", type=Path, required=True)
    a = ap.parse_args(argv)
    st = os.stat(a.pncp_db)
    con = diag.ro(a.pncp_db)
    c = pd.read_sql_query(diag.SQL, con)
    c["fonte"] = np.where(c.fonte.eq("dados_abertos"), "Compras.gov.br", "outras")
    c["dia"] = pd.to_datetime(c.dia, errors="coerce")
    c = c[c.dia.notna()]
    c["mes"] = c.dia.dt.year * 12 + c.dia.dt.month - 1
    mm = c.groupby(["unidade", "mes"]).agg(n=("af", "size"), naf=("af", "sum")).reset_index()
    ev = []
    for un, x in mm.groupby("unidade", sort=False):
        if len(x) < 4:
            continue
        idx = np.arange(x.mes.min(), x.mes.max() + 1)
        n_ = x.set_index("mes").n.reindex(idx, fill_value=0).to_numpy()
        a_ = x.set_index("mes").naf.reindex(idx, fill_value=0).to_numpy()
        cn, ca = np.concatenate([[0], n_.cumsum()]), np.concatenate([[0], a_.cumsum()])
        ultimo, melhor = -99, None
        for j in range(6, len(idx) - 5):
            nb, na = cn[j] - cn[j - 6], cn[j + 6] - cn[j]
            if nb < 5 or na < 5 or n_[j] == 0:
                continue
            dif = (ca[j + 6] - ca[j]) / na - (ca[j] - ca[j - 6]) / nb
            if abs(dif) >= .5 and j - ultimo > 6:
                ev.append({"unidade": un, "mes": int(idx[j]), "dif": float(dif), "n_antes": int(nb), "n_depois": int(na)})
                ultimo = j
    ev = pd.DataFrame(ev)
    info = c.drop_duplicates("unidade").set_index("unidade")[["fonte", "cnpj", "esfera"]]
    ev = ev.join(info, on="unidade")
    ev["tipo"] = np.where(ev.dif > 0, "A->AF", "AF->A")
    d1 = {}
    for (f, t), x in ev.groupby(["fonte", "tipo"]):
        d1[f"{f} {t}"] = {"eventos": len(x), "unidades": int(x.unidade.nunique()), "cnpjs": int(x.cnpj.nunique()),
                          "compras_6m_antes": int(x.n_antes.sum()), "compras_6m_depois": int(x.n_depois.sum()),
                          "mudanca_media_pp": 100 * float(x.dif.mean())}
    # itens de material com preço homologado nas janelas de ±6 meses dos eventos
    jan = c.merge(ev[["unidade", "mes"]].rename(columns={"mes": "m0"}), on="unidade")
    jan = jan[(jan.mes >= jan.m0 - 6) & (jan.mes < jan.m0 + 6)].drop_duplicates("compra")
    con.execute("create temp table alvo(numero_controle_pncp text primary key)")
    con.executemany("insert into temp.alvo values (?)", [(x,) for x in jan.compra.unique()])
    q = pd.read_sql_query("""select i.numero_controle_pncp as compra, count(*) as itens,
                                    sum(i.material_ou_servico = 'M') as itens_material,
                                    sum(i.material_ou_servico = 'M' and i.homologado = 1 and i.valor_unitario_resultado > 0) as material_com_preco
                             from temp.alvo a join itens i on i.numero_controle_pncp = a.numero_controle_pncp
                             where i.registro_principal = 1 group by 1""", con)
    q = q.merge(jan[["compra", "fonte"]], on="compra")
    d1["itens_nas_janelas"] = q.groupby("fonte")[["itens", "itens_material", "material_com_preco"]].sum().to_dict("index")
    ev.to_csv(AQUI / "eventos_regime_flexivel.csv", index=False)

    # D2: cobertura de preço homologado por fonte e ano (amostra de 4.000 compras por fonte e ano)
    c["ano"] = c.dia.dt.year
    amostra = c[c.ano.between(2023, 2026)].sample(frac=1, random_state=1).groupby(["fonte", "ano"]).head(4000)
    con.execute("create temp table am(numero_controle_pncp text primary key)")
    con.executemany("insert into temp.am values (?)", [(x,) for x in amostra.compra.unique()])
    w = pd.read_sql_query("""select i.numero_controle_pncp as compra, i.material_ou_servico as ms, i.homologado,
                                    i.situacao_item, i.valor_unitario_resultado > 0 as tem_preco, i.cod_item_catalogo is not null as tem_catalogo
                             from temp.am a join itens i on i.numero_controle_pncp = a.numero_controle_pncp
                             where i.registro_principal = 1""", con)
    con.close()
    assert os.stat(a.pncp_db).st_mtime_ns == st.st_mtime_ns and os.stat(a.pncp_db).st_size == st.st_size
    w = w.merge(amostra[["compra", "fonte", "ano"]], on="compra")
    d2 = {}
    for (f, ano), x in w.groupby(["fonte", "ano"]):
        d2[f"{f} {ano}"] = {"itens": len(x), "pct_homologado": 100 * float(x.homologado.fillna(0).eq(1).mean()),
                            "pct_com_preco": 100 * float(x.tem_preco.fillna(0).eq(1).mean()),
                            "pct_material_com_preco": 100 * float(x[x.ms.eq("M")].tem_preco.fillna(0).eq(1).mean()),
                            "pct_com_catalogo": 100 * float(x.tem_catalogo.mean())}
    R = json.loads((AQUI / "diagnosticos.json").read_text(encoding="utf-8"))
    R["D"] = {"D1_mudancas_flexiveis_50pp": d1, "D2_cobertura_preco": d2}
    (AQUI / "diagnosticos.json").write_text(json.dumps(R, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    print(json.dumps(R["D"], ensure_ascii=False, indent=1, default=float))
    print("FIM ok")


if __name__ == "__main__":
    main()
