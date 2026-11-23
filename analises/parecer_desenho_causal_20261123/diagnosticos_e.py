"""Diagnóstico E: poder de um estudo de eventos por unidade compradora (A→AF), calculado SEM olhar o desfecho das
unidades que mudaram de modo. Só leitura do pncp.db.

1. Itens de material homologados com preço e CATMAT, Compras.gov.br, Pregão Eletrônico A/AF, abertura 2023-01 a 2026-06.
2. Índice de preço do item: e = log(P) − média de log(P) do mesmo produto (CATMAT + unidade de fornecimento) no mesmo
   trimestre nas OUTRAS unidades (deixa a unidade de fora; ≥ 5 itens de ≥ 3 outras unidades), truncado em ±3.
3. Placebos: em unidades que não mudam de modo (< 5% ou > 95% de AF, ≥ 20 compras), uma data fictícia por unidade com
   ≥ 5 compras nos 6 meses antes e nos 6 depois; Δ = média de e depois − média antes. O desvio-padrão de Δ entre
   unidades dá o ruído de um contraste antes/depois por unidade, e daí o efeito mínimo detectável (80%, 5%, bilateral):
   MDE ≈ 2,8 × dp(Δ) × raiz(1/G_tratadas + 1/G_controles).
4. Nas unidades que mudaram (eventos_regime*.csv), só se contam itens com índice nas janelas; o Δ delas NÃO é calculado.

Uso: python analises/parecer_desenho_causal_20261123/diagnosticos_e.py --pncp-db ../dados/pncp.db
Guarda a extração em dados/parecer_desenho_causal/itens_material.pkl (fora do git) e acrescenta "E" ao diagnosticos.json.
"""
import argparse, json, os, sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
CACHE = RAIZ / "dados" / "parecer_desenho_causal" / "itens_material.pkl"

SQL = """SELECT c.numero_controle_pncp AS compra, c.uasg AS unidade, c.orgao_cnpj AS cnpj,
       c.modo_disputa = 'Aberto-Fechado' AS af, substr(c.data_abertura_proposta, 1, 7) AS mes,
       i.cod_item_catalogo AS catmat, upper(trim(i.unidade_medida)) AS un, i.valor_unitario_resultado AS p
FROM compras c JOIN itens i ON i.numero_controle_pncp = c.numero_controle_pncp
WHERE c.fonte = 'dados_abertos' AND c.modalidade_nome LIKE 'Preg%Eletr%'
  AND c.modo_disputa IN ('Aberto', 'Aberto-Fechado')
  AND substr(c.data_abertura_proposta, 1, 7) BETWEEN '2023-01' AND '2026-06'
  AND i.registro_principal = 1 AND i.material_ou_servico = 'M' AND i.homologado = 1
  AND i.valor_unitario_resultado > 0 AND i.cod_item_catalogo IS NOT NULL"""


def extrair(pncp_db):
    if CACHE.exists():
        return pd.read_pickle(CACHE)
    st = os.stat(pncp_db)
    con = sqlite3.connect(f"file:{Path(pncp_db).resolve().as_posix()}?mode=ro", uri=True)
    partes = [p for p in pd.read_sql_query(SQL, con, chunksize=500_000)]
    con.close()
    assert os.stat(pncp_db).st_mtime_ns == st.st_mtime_ns and os.stat(pncp_db).st_size == st.st_size
    d = pd.concat(partes, ignore_index=True)
    for col in ["unidade", "cnpj", "un"]:
        d[col] = d[col].astype("category")
    d["catmat"] = pd.to_numeric(d.catmat, errors="coerce")
    d = d[d.catmat.notna() & d.mes.notna()]
    d["m"] = d.mes.str[:4].astype(int) * 12 + d.mes.str[5:7].astype(int) - 1
    d["logp"] = np.log(d.p.astype(float))
    d = d.drop(columns=["p", "mes"])
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    d.to_pickle(CACHE)
    return d


def indice(d):
    d = d.copy()
    d["prod"] = d.groupby(["catmat", "un"], observed=True).ngroup()
    d["tri"] = d.m // 3
    g = d.groupby(["prod", "tri"], observed=True).logp
    S, N = g.transform("sum"), g.transform("size")
    U = d.groupby(["prod", "tri"], observed=True).unidade.transform("nunique")
    gu = d.groupby(["prod", "tri", "unidade"], observed=True).logp
    Su, Nu = gu.transform("sum"), gu.transform("size")
    ok = ((N - Nu) >= 5) & ((U - 1) >= 3)
    d["e"] = np.where(ok, d.logp - (S - Su) / (N - Nu).where(ok), np.nan)
    d["e"] = d.e.clip(-3, 3)
    return d[d.e.notna()]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pncp-db", type=Path, required=True)
    a = ap.parse_args(argv)
    d = extrair(a.pncp_db)
    print("itens extraídos", len(d), flush=True)
    x = indice(d)
    print("itens com índice", len(x), flush=True)
    out = {"itens_extraidos": int(len(d)), "itens_com_indice": int(len(x)), "dp_item_e": float(x.e.std()),
           "unidades_com_indice": int(x.unidade.nunique())}

    # regime das unidades por compra (todas as compras da extração de itens, A/AF)
    cu = d.drop_duplicates("compra").groupby("unidade", observed=True).agg(n=("af", "size"), s=("af", "mean"))
    estaveis = cu[(cu.n >= 20) & ((cu.s < .05) | (cu.s > .95))]
    rng = np.random.default_rng(20261123)
    deltas = []
    for un, z in x[x.unidade.isin(estaveis.index)].groupby("unidade", observed=True):
        comp = z.drop_duplicates("compra")
        meses = np.sort(comp.m.unique())
        cand = [m0 for m0 in meses if ((comp.m >= m0 - 6) & (comp.m < m0)).sum() >= 5 and ((comp.m >= m0) & (comp.m < m0 + 6)).sum() >= 5]
        if not cand:
            continue
        m0 = rng.choice(cand)
        pre, pos = z[(z.m >= m0 - 6) & (z.m < m0)], z[(z.m >= m0) & (z.m < m0 + 6)]
        # média por compra e depois entre compras (o pregão é a unidade de decisão)
        dp = pos.groupby("compra").e.mean().mean() - pre.groupby("compra").e.mean().mean()
        deltas.append({"unidade": un, "regime": "AF" if estaveis.s[un] > .95 else "A", "delta": dp,
                       "itens": len(pre) + len(pos), "compras": pre.compra.nunique() + pos.compra.nunique()})
    pl = pd.DataFrame(deltas)
    sd = float(pl.delta.std())
    sd_rob = float(1.4826 * (pl.delta - pl.delta.median()).abs().median())
    out["placebo"] = {"unidades": len(pl), "por_regime": pl.regime.value_counts().to_dict(),
                      "media_delta": float(pl.delta.mean()), "dp_delta": sd, "dp_robusto_MAD": sd_rob,
                      "itens_medios_por_janela": float(pl.itens.mean()), "compras_medias_por_janela": float(pl.compras.mean())}
    Gc = len(pl)
    mde = {}
    for nome, Gt in [("A->AF flexível (Compras.gov.br, 164)", 164), ("AF->A flexível (108)", 108),
                     ("ambos os sentidos, sinal invertido (272)", 272), ("A->AF estrito (21)", 21), ("estritos, ambos (33)", 33)]:
        f = np.sqrt(1 / Gt + 1 / Gc)
        mde[nome] = {"MDE_log_dp": 2.8 * sd * f, "MDE_pct_dp": 100 * np.expm1(-2.8 * sd * f),
                     "MDE_log_dp_robusto": 2.8 * sd_rob * f}
    out["MDE_80pct_5pct"] = mde

    # disponibilidade nas unidades que mudaram (sem calcular Δ)
    disp = {}
    for arq in ["eventos_regime.csv", "eventos_regime_flexivel.csv"]:
        ev = pd.read_csv(AQUI / arq, dtype={"unidade": str, "cnpj": str})
        ev = ev[ev.fonte.eq("Compras.gov.br")]
        j = x[["unidade", "m", "compra"]].assign(unidade=x.unidade.astype(str)).merge(ev[["unidade", "mes", "tipo"]], on="unidade")
        j = j[(j.m >= j.mes - 6) & (j.m < j.mes + 6)]
        disp[arq] = {t: {"eventos_com_itens": int(z.unidade.nunique()), "itens_com_indice": len(z), "compras": int(z.compra.nunique())}
                     for t, z in j.groupby("tipo")}
    out["switchers_itens_nas_janelas"] = disp
    R = json.loads((AQUI / "diagnosticos.json").read_text(encoding="utf-8"))
    R["E_poder_evento_unidade"] = out
    (AQUI / "diagnosticos.json").write_text(json.dumps(R, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    pl.to_csv(AQUI / "placebos_unidades_estaveis.csv", index=False)
    print(json.dumps(out, ensure_ascii=False, indent=1, default=float))
    print("FIM ok")


if __name__ == "__main__":
    main()
