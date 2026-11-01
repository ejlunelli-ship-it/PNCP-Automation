"""Matching exato no Pregão Eletrônico homologado: Aberto vs Aberto-Fechado.

Pregões homologados: valorTotalHomologado > 0 ou existeResultado.
Itens: com resultado e valorUnitarioResultado > 0.
Variável dependente principal: valor unitário homologado (valorUnitarioResultado), em log
(diferença em log ~ diferença percentual de preço); também em R$.
Pareamento: UASG x código do item x ano (ano de publicação do pregão); comparação com
UASG x item (sem ano), com UASG x item x ano x unidade de medida (robustez) e com o
desconto sobre o estimado como variável dependente.
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
        "unidadeMedida", "temResultado", "orcamentoSigiloso", "valorUnitarioEstimado", "valorUnitarioResultado"]
partes = []
for f in sorted(glob.glob(str(BRUTOS) + r"/20*/itens_pregao_*.csv")):
    d = pd.read_csv(f, usecols=cols, dtype={"numeroControlePNCPCompra": str, "unidadeOrgaoCodigoUnidade": str,
                                            "temResultado": str, "orcamentoSigiloso": str,
                                            "materialOuServico": str, "unidadeMedida": str})
    info = d.numeroControlePNCPCompra.map(compra)
    d = d[info.notna() & (d.temResultado.str.lower() == "true") & (d.valorUnitarioResultado > 0)
          & d.codItemCatalogo.notna() & d.unidadeOrgaoCodigoUnidade.notna()].copy()
    info = info[d.index]
    d["modo"], d["ano"] = info.str[0], info.str[1]
    partes.append(d)
df = pd.concat(partes, ignore_index=True)
df["codItemCatalogo"] = df.codItemCatalogo.astype("int64")
df["unidadeMedida"] = df.unidadeMedida.fillna("").str.strip().str.upper()
df["af"] = (df.modo == "Aberto-Fechado").astype(int)
df["log_preco"] = np.log(df.valorUnitarioResultado)
desc = 1 - df.valorUnitarioResultado / df.valorUnitarioEstimado
ok_desc = (df.orcamentoSigiloso.str.lower() != "true") & (df.valorUnitarioEstimado > 0) & desc.between(-1, 0.99)
df["desconto"] = (desc * 100).where(ok_desc)

print(f"Pregões eletrônicos homologados (Aberto/Aberto-Fechado): {len(compra):,}")
print(f"Itens homologados elegíveis: {len(df):,} | Aberto {(df.af == 0).sum():,} | "
      f"Aberto-Fechado {(df.af == 1).sum():,}")


def efeito_fixo(p, chave, y):
    """Within (efeito fixo de célula), EP agrupado por UASG. Retorna beta, ep, p."""
    g = p.groupby(chave)
    yy = p[y] - g[y].transform("mean")
    x = p.af - g.af.transform("mean")
    beta = (x * yy).sum() / (x * x).sum()
    e = yy - beta * x
    s = (x * e).groupby(p.unidadeOrgaoCodigoUnidade).sum()
    G, N, K = s.size, len(p), g.ngroups + 1
    se = np.sqrt((s ** 2).sum()) / (x * x).sum() * np.sqrt(G / (G - 1) * (N - 1) / (N - K))
    return beta, se, 2 * stats.norm.sf(abs(beta / se))


def matching(chave, y, rotulo, detalhe=True):
    d = df.dropna(subset=[y])
    cel = d.groupby(chave + ["af"])[y].agg(["mean", "size"]).unstack("af")
    cel.columns = [f"{a}_{b}" for a, b in cel.columns]
    cel = cel.dropna()
    cel["dif"] = cel.mean_1 - cel.mean_0
    p = d[d.set_index(chave).index.isin(cel.index)]
    dif = cel.dif
    ic = stats.t.interval(0.95, len(dif) - 1, loc=dif.mean(), scale=stats.sem(dif))
    w = stats.wilcoxon(dif)
    beta, se, pv = efeito_fixo(p, chave, y)
    pw = 2 / (1 / cel.size_0 + 1 / cel.size_1)
    print(f"\n== {rotulo}")
    print(f"  células: {len(cel):,} | UASGs {p.unidadeOrgaoCodigoUnidade.nunique():,} | "
          f"itens de catálogo {p.codItemCatalogo.nunique():,} | itens pareados {len(p):,} "
          f"(A {int(cel.size_0.sum()):,}, AF {int(cel.size_1.sum()):,})")
    print(f"  média por célula: A {cel.mean_0.mean():.4f} | AF {cel.mean_1.mean():.4f}")
    print(f"  dif. AF-A: média {dif.mean():.4f} (IC95% {ic[0]:.4f} a {ic[1]:.4f}) | mediana {dif.median():.4f} | "
          f"ponderada {np.average(dif, weights=pw):.4f}")
    print(f"  Wilcoxon p = {w.pvalue:.2e} | AF>A {(dif > 0).mean():.1%}, AF<A {(dif < 0).mean():.1%} | "
          f"d de Cohen {dif.mean() / dif.std():.3f}")
    print(f"  efeito fixo, EP agrupado por UASG: beta {beta:.4f} (EP {se:.4f}, "
          f"IC95% {beta - 1.96 * se:.4f} a {beta + 1.96 * se:.4f}), p = {pv:.2e}")
    if detalhe:
        tipo = p.groupby(chave).materialOuServico.first().reindex(cel.index)
        for tp, nome in (("M", "material"), ("S", "serviço")):
            dd, pp = dif[tipo == tp], p[p.materialOuServico == tp]
            if len(dd) > 10:
                b, s, pvt = efeito_fixo(pp, chave, y)
                print(f"    {nome}: {len(dd):,} células | dif. média {dd.mean():.4f} | mediana {dd.median():.4f} | "
                      f"EF beta {b:.4f} (EP {s:.4f}), p = {pvt:.2e}")
        anos = cel.index.get_level_values("ano") if "ano" in chave else None
        if anos is not None:
            print("    por ano: " + " | ".join(f"{a}: {dif[anos == a].mean():.4f} ({(anos == a).sum():,})"
                                            for a in sorted(set(anos))))
    return beta, se


base = ["unidadeOrgaoCodigoUnidade", "codItemCatalogo"]
print("\n######## Variável dependente: log do valor unitário homologado")
b, s = matching(base + ["ano"], "log_preco", "log(preço) | UASG x item x ano  [PRINCIPAL]")
print(f"  => AF vs A: {np.expm1(b):+.2%} no preço homologado (IC95% {np.expm1(b - 1.96 * s):+.2%} a "
      f"{np.expm1(b + 1.96 * s):+.2%})")
b, s = matching(base, "log_preco", "log(preço) | UASG x item (sem ano)", detalhe=False)
print(f"  => {np.expm1(b):+.2%}")
b, s = matching(base + ["ano", "unidadeMedida"], "log_preco", "log(preço) | UASG x item x ano x unidade de medida",
                detalhe=False)
print(f"  => {np.expm1(b):+.2%}")

print("\n######## Variável dependente: valor unitário homologado em R$")
matching(base + ["ano"], "valorUnitarioResultado", "R$ | UASG x item x ano", detalhe=False)

print("\n######## Variável dependente: desconto sobre o estimado (p.p.), só homologados")
matching(base + ["ano"], "desconto", "desconto | UASG x item x ano", detalhe=False)
matching(base, "desconto", "desconto | UASG x item (sem ano)", detalhe=False)
