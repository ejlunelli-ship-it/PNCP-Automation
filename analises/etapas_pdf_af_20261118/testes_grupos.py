"""Testes de diferença de médias entre grupos (material × serviço; orçamento aberto × sigiloso).

Entrada: por_item.csv.gz (analisar.py) + ligacao_pncp.csv.gz (ligar_pncp.py). Mesma amostra do relatório.
Para cada comparação e variável:
  - Welch (t de duas amostras com variâncias diferentes, item como unidade);
  - t com EP agrupado por UASG (MQO de y numa dummy do grupo, CR1) -- inferência principal,
    pois itens da mesma UASG/compra não são independentes;
  - Mann-Whitney (diferença de distribuição/mediana);
  - Holm sobre todos os p agrupados da tabela;
  - diferença AJUSTADA pelo número de licitantes (quantidade_fornecedores do PDF): MQO de y na dummy do grupo
    com efeito fixo por número de licitantes (1..20, 21-30, 31+), EP por UASG; sensibilidade com log(licitantes).
Saídas: testes_grupos.csv, testes_grupos.xlsx, estatisticas_grupos.csv.
"""
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

AQUI = Path(__file__).resolve().parent
VARS = {"d_aberto": "Desconto etapa aberta (%)", "d_apos": "Desconto após a fechada (%)",
        "ganho_pp": "Ganho da fechada (p.p.)", "ganho_rel": "Ganho relativo (% do melhor aberto)",
        "d_final": "Desconto final (%)", "teve_fechado": "Teve lance fechado (%)",
        "fechado_melhorou": "Fechada melhorou o preço (%)", "licitantes": "Número de licitantes"}


def dados():
    d = pd.read_csv(AQUI / "por_item.csv.gz", dtype={"id_compra": str, "uasg": str})
    d = d[d.na_amostra].copy()
    lig = pd.read_csv(AQUI / "ligacao_pncp.csv.gz", dtype={"id_compra": str})
    lig = lig[lig.n_registros == 1][["id_compra", "item", "material_ou_servico", "orcamento_sigiloso"]]
    d = d.merge(lig, on=["id_compra", "item"], how="inner")
    d = d[d.material_ou_servico.isin(["M", "S"]) & d.orcamento_sigiloso.isin([0, 1])]
    d["tipo"] = d.material_ou_servico.map({"M": "Material", "S": "Serviço"})
    d["orcamento"] = d.orcamento_sigiloso.map({0: "Aberto", 1: "Sigiloso"})
    f = d.melhor_lance_modo_fechado
    d["teve_fechado"] = 100.0 * (f.notna() & (f > 0))
    d["fechado_melhorou"] = 100.0 * (f.notna() & (f > 0) & (f < d.melhor_lance_modo_aberto))
    d["licitantes"] = d.quantidade_fornecedores.astype(float)
    d["faixa_lic"] = pd.cut(d.licitantes, list(np.arange(0.5, 20.6, 1)) + [30.5, 1e9], labels=False)
    return d


def t_cluster_ctrl(y, g, Z, cl):
    """Coeficiente da dummy g em y ~ 1 + g + Z, EP agrupado (CR1)."""
    X = np.column_stack([np.ones(len(y)), g, Z])
    XtX = np.linalg.pinv(X.T @ X); b = XtX @ X.T @ y; u = y - X @ b
    cod, idx = np.unique(cl, return_inverse=True); G = len(cod); n, k = X.shape
    S = np.zeros((G, k)); np.add.at(S, idx, X * u[:, None])
    V = XtX @ (S.T @ S) @ XtX * (G / (G - 1)) * ((n - 1) / (n - k))
    se = np.sqrt(V[1, 1])
    return b[1], se, 2 * stats.t.sf(abs(b[1] / se), G - 1)


def t_cluster(y, g, cl):
    X = np.column_stack([np.ones(len(y)), g])
    XtX = np.linalg.inv(X.T @ X); b = XtX @ X.T @ y; u = y - X @ b
    cod, idx = np.unique(cl, return_inverse=True); G = len(cod); n = len(y)
    S = np.zeros((G, 2)); np.add.at(S, idx, X * u[:, None])
    V = XtX @ (S.T @ S) @ XtX * (G / (G - 1)) * ((n - 1) / (n - 2))
    se = np.sqrt(V[1, 1])
    return b[1], se, 2 * stats.t.sf(abs(b[1] / se), G - 1)


def holm(p):
    p = np.asarray(p); o = np.argsort(p); m = len(p); adj = np.empty(m)
    adj[o] = np.minimum(1, np.maximum.accumulate((m - np.arange(m)) * p[o]))
    return adj


def main():
    d = dados()
    comps = [  # (nome, filtro, coluna do grupo, grupo A, grupo B)
        ("Material × Serviço (todos)", None, "tipo", "Material", "Serviço"),
        ("Aberto × Sigiloso (todos)", None, "orcamento", "Aberto", "Sigiloso"),
        ("Material: aberto × sigiloso", ("tipo", "Material"), "orcamento", "Aberto", "Sigiloso"),
        ("Serviço: aberto × sigiloso", ("tipo", "Serviço"), "orcamento", "Aberto", "Sigiloso"),
        ("Orç. aberto: material × serviço", ("orcamento", "Aberto"), "tipo", "Material", "Serviço"),
        ("Orç. sigiloso: material × serviço", ("orcamento", "Sigiloso"), "tipo", "Material", "Serviço"),
    ]
    linhas = []
    for nome, filt, col, a, b in comps:
        s = d if filt is None else d[d[filt[0]] == filt[1]]
        for v, rot in VARS.items():
            x = s[[v, col, "uasg"]].dropna()
            ya, yb = x.loc[x[col] == a, v], x.loc[x[col] == b, v]
            w = stats.ttest_ind(yb, ya, equal_var=False)
            diff, se, pc = t_cluster(x[v].to_numpy(float), (x[col] == b).to_numpy(float), x.uasg.to_numpy())
            mw = stats.mannwhitneyu(yb, ya)
            xa = s.loc[x.index]; gdum = (x[col] == b).to_numpy(float); yv = x[v].to_numpy(float)
            fe = pd.get_dummies(xa.faixa_lic).to_numpy(float)[:, 1:]          # efeito fixo por nº de licitantes
            da, sa, pa = (np.nan, np.nan, np.nan) if v == "licitantes" else t_cluster_ctrl(yv, gdum, fe, x.uasg.to_numpy())
            dl, sl, pl = (np.nan, np.nan, np.nan) if v == "licitantes" else                 t_cluster_ctrl(yv, gdum, np.log(xa.licitantes.to_numpy())[:, None], x.uasg.to_numpy())
            linhas.append({"comparacao": nome, "variavel": rot, "grupo_A": a, "grupo_B": b,
                           "n_A": len(ya), "n_B": len(yb), "media_A": ya.mean(), "media_B": yb.mean(),
                           "mediana_A": ya.median(), "mediana_B": yb.median(), "dif_B_menos_A": diff,
                           "ep_cluster_uasg": se, "ic95_inf": diff - 1.96 * se, "ic95_sup": diff + 1.96 * se,
                           "p_cluster_uasg": pc, "p_welch": w.pvalue, "p_mann_whitney": mw.pvalue,
                           "dif_ajust_licitantes": da, "ep_ajust": sa, "ic95_inf_ajust": da - 1.96 * sa,
                           "ic95_sup_ajust": da + 1.96 * sa, "p_ajust": pa,
                           "dif_ajust_log_licitantes": dl, "p_ajust_log": pl})
    t = pd.DataFrame(linhas)
    m0 = t.variavel != VARS["licitantes"]
    t.loc[m0, "p_cluster_holm"] = holm(t.loc[m0, "p_cluster_uasg"])
    m = t.p_ajust.notna(); t.loc[m, "p_ajust_holm"] = holm(t.loc[m, "p_ajust"])
    t["sig_ajust"] = pd.cut(t.p_ajust, [-1, 0.001, 0.01, 0.05, 0.1, 2], labels=["***", "**", "*", "†", ""])
    t["sig"] = pd.cut(t.p_cluster_uasg, [-1, 0.001, 0.01, 0.05, 0.1, 2], labels=["***", "**", "*", "†", ""])
    t.to_csv(AQUI / "testes_grupos.csv", index=False)

    est = []
    for chave in [["tipo"], ["orcamento"], ["tipo", "orcamento"]]:
        for k, g in d.groupby(chave):
            k = k if isinstance(k, tuple) else (k,)
            lin = {"tipo": "todos", "orcamento": "todos", **dict(zip(chave, k)), "itens": len(g),
                   "compras": g.pasta.nunique(), "uasgs": g.uasg.nunique()}
            for v in VARS:
                lin[f"{v}_media"] = g[v].mean(); lin[f"{v}_dp"] = g[v].std()
            est.append(lin)
    est = pd.DataFrame(est); est.to_csv(AQUI / "estatisticas_grupos.csv", index=False)
    with pd.ExcelWriter(AQUI / "testes_grupos.xlsx") as xw:
        est.to_excel(xw, sheet_name="medias_por_grupo", index=False)
        t.to_excel(xw, sheet_name="testes_diferenca", index=False)
    pd.set_option("display.width", 300); pd.set_option("display.max_rows", 200)
    print(est.round(2).to_string())
    print(t[["comparacao", "variavel", "n_A", "n_B", "media_A", "media_B", "dif_B_menos_A", "ic95_inf", "ic95_sup",
             "p_cluster_uasg", "p_cluster_holm", "sig", "dif_ajust_licitantes", "p_ajust", "p_ajust_holm", "sig_ajust",
             "dif_ajust_log_licitantes", "p_ajust_log"]].round(4).to_string())


if __name__ == "__main__":
    main()
