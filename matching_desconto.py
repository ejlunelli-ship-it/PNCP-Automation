"""Matching exato (UASG x código do item): desconto no Pregão Eletrônico, Aberto vs Aberto-Fechado.

Desconto do item = 1 - valorUnitarioResultado / valorUnitarioEstimado (itens com resultado,
orçamento não sigiloso, valores > 0, desconto entre -100% e 99%).
Célula = (unidadeOrgaoCodigoUnidade, codItemCatalogo) com itens nos dois modos.
Em cada célula: desconto médio de cada modo; o teste compara as células pareadas.
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

modo = {}
for f in glob.glob(str(BRUTOS) + r"/20*/contratacoes_pregao_*.json"):
    for x in json.load(open(f, encoding="utf-8")):
        if x["modalidadeNome"] == "Pregão - Eletrônico" and x.get("modoDisputaNomePncp") in ("Aberto", "Aberto-Fechado"):
            modo[x["numeroControlePNCP"]] = x["modoDisputaNomePncp"]

cols = ["numeroControlePNCPCompra", "unidadeOrgaoCodigoUnidade", "codItemCatalogo", "materialOuServico",
        "temResultado", "orcamentoSigiloso", "valorUnitarioEstimado", "valorUnitarioResultado"]
partes = []
for f in sorted(glob.glob(str(BRUTOS) + r"/20*/itens_pregao_*.csv")):
    d = pd.read_csv(f, usecols=cols, dtype={"numeroControlePNCPCompra": str, "unidadeOrgaoCodigoUnidade": str,
                                            "temResultado": str, "orcamentoSigiloso": str, "materialOuServico": str})
    d["modo"] = d.numeroControlePNCPCompra.map(modo)
    d = d[d.modo.notna() & (d.temResultado.str.lower() == "true") & (d.orcamentoSigiloso.str.lower() != "true")
          & (d.valorUnitarioEstimado > 0) & (d.valorUnitarioResultado > 0) & d.codItemCatalogo.notna()
          & d.unidadeOrgaoCodigoUnidade.notna()]
    d = d.assign(desconto=1 - d.valorUnitarioResultado / d.valorUnitarioEstimado)
    partes.append(d[(d.desconto >= -1) & (d.desconto <= 0.99)])
df = pd.concat(partes, ignore_index=True)
df["codItemCatalogo"] = df.codItemCatalogo.astype("int64")
df["af"] = (df.modo == "Aberto-Fechado").astype(int)
df["desconto"] *= 100

print(f"Itens elegíveis: {len(df):,} | Aberto {(df.af == 0).sum():,} | Aberto-Fechado {(df.af == 1).sum():,}")
print(f"UASGs: {df.unidadeOrgaoCodigoUnidade.nunique():,} | códigos de item: {df.codItemCatalogo.nunique():,}")
print(f"Antes do pareamento: desconto médio Aberto {df[df.af == 0].desconto.mean():.2f}% | "
      f"Aberto-Fechado {df[df.af == 1].desconto.mean():.2f}%")

chave = ["unidadeOrgaoCodigoUnidade", "codItemCatalogo"]
cel = df.groupby(chave + ["af"]).desconto.agg(["mean", "size"]).unstack("af")
cel.columns = [f"{a}_{b}" for a, b in cel.columns]
cel = cel.dropna()  # células com os dois modos
cel["dif"] = cel.mean_1 - cel.mean_0
m = df.set_index(chave).index.isin(cel.index)
pareado = df[m]

print(f"\nCélulas pareadas (UASG x item com os dois modos): {len(cel):,}")
print(f"  UASGs: {cel.index.get_level_values(0).nunique():,} | códigos de item: {cel.index.get_level_values(1).nunique():,}")
print(f"  itens pareados: {m.sum():,} ({m.mean():.1%} dos elegíveis) | Aberto {int(cel.size_0.sum()):,} | "
      f"Aberto-Fechado {int(cel.size_1.sum()):,}")
mat = pareado.materialOuServico.value_counts(normalize=True)
print(f"  material {mat.get('M', 0):.1%} | serviço {mat.get('S', 0):.1%}")

print("\n== Desconto médio por célula (cada célula pesa igual)")
print(f"  Aberto:          média {cel.mean_0.mean():.2f}% | mediana {cel.mean_0.median():.2f}%")
print(f"  Aberto-Fechado:  média {cel.mean_1.mean():.2f}% | mediana {cel.mean_1.median():.2f}%")
d = cel.dif
ic = stats.t.interval(0.95, len(d) - 1, loc=d.mean(), scale=stats.sem(d))
t = stats.ttest_rel(cel.mean_1, cel.mean_0)
w = stats.wilcoxon(d)
print(f"  Diferença (AF - A): média {d.mean():.2f} p.p. (IC95% {ic[0]:.2f} a {ic[1]:.2f}) | mediana {d.median():.2f} p.p.")
print(f"  t pareado: t = {t.statistic:.2f}, p = {t.pvalue:.2e}")
print(f"  Wilcoxon (postos sinalizados): W = {w.statistic:.0f}, p = {w.pvalue:.2e}")
print(f"  AF > A em {(d > 0).mean():.1%} das células | AF < A em {(d < 0).mean():.1%} | empate {(d == 0).mean():.1%}")
cohen = d.mean() / d.std()
print(f"  tamanho do efeito (d de Cohen, pareado): {cohen:.3f}")

# ponderado pelo tamanho da célula (peso = média harmônica dos n de cada modo)
pw = 2 / (1 / cel.size_0 + 1 / cel.size_1)
dw = np.average(d, weights=pw)
print(f"\n== Ponderado pelo tamanho da célula: diferença {dw:.2f} p.p.")

# regressão com efeito fixo de célula (within), erro-padrão agrupado por UASG
g = pareado.groupby(chave)
y = pareado.desconto - g.desconto.transform("mean")
x = pareado.af - g.af.transform("mean")
beta = (x * y).sum() / (x * x).sum()
e = y - beta * x
uasg = pareado.unidadeOrgaoCodigoUnidade
s = (x * e).groupby(uasg).sum()
G, N, K = s.size, len(pareado), len(cel) + 1
se = np.sqrt((s ** 2).sum()) / (x * x).sum() * np.sqrt(G / (G - 1) * (N - 1) / (N - K))
print(f"== Efeito fixo UASG x item, EP agrupado por UASG: beta = {beta:.2f} p.p. "
      f"(EP {se:.2f}, IC95% {beta - 1.96 * se:.2f} a {beta + 1.96 * se:.2f}, p = {2 * stats.norm.sf(abs(beta / se)):.2e})")

# robustez: material e serviço separados
print("\n== Por tipo de item (células pareadas)")
tipo = pareado.groupby(chave).materialOuServico.first()
for tp, nome in (("M", "Material"), ("S", "Serviço")):
    dd = d[tipo.reindex(d.index) == tp]
    if len(dd) > 10:
        print(f"  {nome}: {len(dd):,} células | dif. média {dd.mean():.2f} p.p. | mediana {dd.median():.2f} | "
              f"Wilcoxon p = {stats.wilcoxon(dd).pvalue:.2e}")
