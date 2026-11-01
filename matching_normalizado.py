"""Preço unitário homologado normalizado pela mediana nacional do item no ano.

Pregão Eletrônico homologado, Aberto vs Aberto-Fechado. preco_rel = valorUnitarioResultado /
mediana(valorUnitarioResultado do mesmo codItemCatalogo e ano, todas as UASGs, os dois modos);
variável dependente = log(preco_rel). Mediana exige 5+ itens no item x ano.
Com pareamento por UASG x item x ano a mediana se cancela; a normalização serve para
(1) cortar preços absurdos (preco_rel fora de [0,1; 10]) e (2) parear de forma mais ampla
(UASG x ano, UASG x ano x classe/grupo), já que o preço relativo é comparável entre itens.
"""
import glob
import json
import sys

import numpy as np
import pandas as pd
from scipy import stats

from config import DADOS

BRUTOS = DADOS / "brutos"
sys.stdout.reconfigure(encoding="utf-8")

compra = {}
for f in glob.glob(str(BRUTOS) + r"/20*/contratacoes_pregao_*.json"):
    for x in json.load(open(f, encoding="utf-8")):
        if (x["modalidadeNome"] == "Pregão - Eletrônico"
                and x.get("modoDisputaNomePncp") in ("Aberto", "Aberto-Fechado")
                and ((x.get("valorTotalHomologado") or 0) > 0 or x.get("existeResultado"))):
            compra[x["numeroControlePNCP"]] = (x["modoDisputaNomePncp"], int(x["dataPublicacaoPncp"][:4]))

cols = ["numeroControlePNCPCompra", "unidadeOrgaoCodigoUnidade", "codItemCatalogo", "materialOuServico",
        "codigoClasse", "codigoGrupo", "temResultado", "valorUnitarioResultado"]
partes = []
for f in sorted(glob.glob(str(BRUTOS) + r"/20*/itens_pregao_*.csv")):
    d = pd.read_csv(f, usecols=cols, dtype={"numeroControlePNCPCompra": str, "unidadeOrgaoCodigoUnidade": str,
                                            "temResultado": str, "materialOuServico": str})
    info = d.numeroControlePNCPCompra.map(compra)
    d = d[info.notna() & (d.temResultado.str.lower() == "true") & (d.valorUnitarioResultado > 0)
          & d.codItemCatalogo.notna() & d.unidadeOrgaoCodigoUnidade.notna()].copy()
    info = info[d.index]
    d["modo"], d["ano"] = info.str[0], info.str[1]
    partes.append(d)
df = pd.concat(partes, ignore_index=True)
df["codItemCatalogo"] = df.codItemCatalogo.astype("int64")
df["af"] = (df.modo == "Aberto-Fechado").astype(int)

g = df.groupby(["codItemCatalogo", "ano"]).valorUnitarioResultado
df["n_item_ano"] = g.transform("size")
df["mediana"] = g.transform("median")
df = df[df.n_item_ano >= 5].copy()
df["preco_rel"] = df.valorUnitarioResultado / df.mediana
df["log_rel"] = np.log(df.preco_rel)
fora = ~df.preco_rel.between(0.1, 10)
print(f"Itens homologados com mediana nacional (item x ano com 5+ itens): {len(df):,}")
print(f"Preço fora de [0,1x; 10x] a mediana: {fora.sum():,} ({fora.mean():.2%}) -> excluídos")
df = df[~fora]
print(f"Base: {len(df):,} itens | Aberto {(df.af == 0).sum():,} | Aberto-Fechado {(df.af == 1).sum():,}")
print(f"Preço relativo mediano (sem pareamento): A {df[df.af == 0].preco_rel.median():.3f} | "
      f"AF {df[df.af == 1].preco_rel.median():.3f}")


def efeito_fixo(p, chave, y):
    g = p.groupby(chave)
    yy = p[y] - g[y].transform("mean")
    x = p.af - g.af.transform("mean")
    beta = (x * yy).sum() / (x * x).sum()
    e = yy - beta * x
    s = (x * e).groupby(p.unidadeOrgaoCodigoUnidade).sum()
    G, N, K = s.size, len(p), g.ngroups + 1
    se = np.sqrt((s ** 2).sum()) / (x * x).sum() * np.sqrt(G / (G - 1) * (N - 1) / (N - K))
    return beta, se, 2 * stats.norm.sf(abs(beta / se))


def pct(v):
    return f"{np.expm1(v):+.2%}"


def matching(chave, rotulo, y="log_rel", detalhe=False):
    cel = df.groupby(chave + ["af"])[y].agg(["mean", "size"]).unstack("af")
    cel.columns = [f"{a}_{b}" for a, b in cel.columns]
    cel = cel.dropna()
    dif = cel.mean_1 - cel.mean_0
    p = df[df.set_index(chave).index.isin(cel.index)]
    beta, se, pv = efeito_fixo(p, chave, y)
    w = stats.wilcoxon(dif)
    print(f"\n== {rotulo}")
    print(f"  células {len(cel):,} | UASGs {p.unidadeOrgaoCodigoUnidade.nunique():,} | itens pareados {len(p):,} "
          f"(A {int(cel.size_0.sum()):,}, AF {int(cel.size_1.sum()):,}) | {len(p) / len(df):.1%} da base")
    print(f"  dif. AF-A por célula: média {pct(dif.mean())} | mediana {pct(dif.median())} | "
          f"AF<A em {(dif < 0).mean():.1%}, AF>A em {(dif > 0).mean():.1%} | Wilcoxon p = {w.pvalue:.2e}")
    print(f"  efeito fixo, EP agrupado por UASG: {pct(beta)} (IC95% {pct(beta - 1.96 * se)} a "
          f"{pct(beta + 1.96 * se)}), p = {pv:.2e}")
    if detalhe:
        for tp, nome in (("M", "material"), ("S", "serviço")):
            pp = p[p.materialOuServico == tp]
            if pp.groupby(chave).af.nunique().eq(2).sum() > 10:
                b, s, pvt = efeito_fixo(pp, chave, y)
                print(f"    {nome}: {len(pp):,} itens | {pct(b)} (IC95% {pct(b - 1.96 * s)} a "
                      f"{pct(b + 1.96 * s)}), p = {pvt:.2e}")
        for a in sorted(p.ano.unique()):
            pa = p[p.ano == a]
            if pa.groupby(chave).af.nunique().eq(2).sum() > 10:
                b, s, pvt = efeito_fixo(pa, chave, y)
                print(f"    {a}: {len(pa):,} itens | {pct(b)} (EP {s:.3f}), p = {pvt:.2e}")


uasg = "unidadeOrgaoCodigoUnidade"
matching([uasg, "codItemCatalogo", "ano"], "(1) UASG x item x ano, sem preços absurdos", detalhe=True)
matching([uasg, "ano", "codigoClasse"], "(2a) UASG x ano x classe do item", detalhe=True)
matching([uasg, "ano"], "(2b) UASG x ano (qualquer item)", detalhe=True)
