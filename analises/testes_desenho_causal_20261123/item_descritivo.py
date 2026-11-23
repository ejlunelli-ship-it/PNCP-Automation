"""Matching de itens só como descritivo (protocolo.md §6; parecer §4.3): AF × A no mesmo produto e trimestre (índice e),
com covariáveis do item e do "tipo do comprador" medidas em outros períodos; MQO, AIPW com aparamento por sobreposição,
balanceamento por entropia, teste de balanço no índice do estimado, Γ de Rosenbaum, valores de robustez de
Cinelli e Hazlett (2020), limites de Lee e fração dos AF com suporte. EP por CNPJ; bootstrap selvagem de escores.

Uso (da pasta PNCP-Automation): python analises/testes_desenho_causal_20261123/item_descritivo.py
Saída: resultados_item.json nesta pasta.
"""
import json, time

import numpy as np
import pandas as pd
from scipy import stats

import comum as C
import motor as Mo

T0 = time.time()
B = 9999


def log(*a):
    print(f"[{time.time() - T0:6.0f}s]", *a, flush=True)


def base():
    i = pd.read_pickle(C.DADOS / "itens.pkl")
    c = pd.read_pickle(C.DADOS / "compras.pkl")[["compra", "af", "srp", "esfera", "regiao"]]
    c["compra"] = c.compra.astype(str)
    i["compra"] = i.compra.astype(str)
    i = i.merge(c, on="compra", how="left")
    P = dict(np.load(C.DADOS / "paineis.npz"))
    mf = (int(C.FIM_ITENS[:4]) * 12 + int(C.FIM_ITENS[5:7]) - 1) - C.M0 + 1
    pn = Mo.Paineis(P, mf)
    return i, pn


def passado(pn, u, m, k, w=12):
    cs = pn.cs(k)
    a = np.clip(m - w, 0, None)
    return cs[u, m] - cs[u, a]


def montar(i, pn):
    d = i[i.e_ok.notna() & (i.m >= 12)].copy()                  # 2023-01 a 2026-03 (12 meses de histórico)
    u, m = d.u.to_numpy(), d.m.to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        d["tam"] = np.log1p(passado(pn, u, m, "N"))
        d["eR_passado"] = passado(pn, u, m, "S_eR") / passado(pn, u, m, "C_eR")
        d["e_passado"] = passado(pn, u, m, "S_e") / passado(pn, u, m, "C_e")
    d["mes_ano"] = d.m % 12
    d["ano"] = d.m // 12
    cols = {}
    def add(nome, v):
        cols[nome] = np.asarray(v, float)
    for nome in ["eq", "eR_passado", "e_passado", "comp"]:
        x = d[nome].to_numpy(float)
        add(nome + "_falta", ~np.isfinite(x))
        add(nome, np.where(np.isfinite(x), x, 0.0))
    for nome in ["srp", "excl", "sigilo", "mkt", "tam", "med"]:
        add(nome, d[nome].fillna(0).astype(float))
    for v in range(1, 12):
        add(f"mes{v}", d.mes_ano.eq(v))
    for v in sorted(d.ano.unique())[1:]:
        add(f"ano{v}", d.ano.eq(v))
    for v in ["E", "M", "N", "D"]:
        add(f"esf_{v}", d.esfera.eq(v))
    for v in ["NE", "CO", "SE", "S"]:
        add(f"reg_{v}", d.regiao.eq(v))
    X = pd.DataFrame(cols, index=d.index)
    X = X.loc[:, X.std() > 0]                                     # sem colunas constantes
    cc = np.corrcoef(X.to_numpy().T)
    fora = [c for j, c in enumerate(X.columns) if any(abs(cc[j, i]) > 0.9999 for i in range(j))]
    return d, X.drop(columns=fora)


def logit(X, y, iters=25):
    Xs = np.column_stack([np.ones(len(X)), X])
    b = np.zeros(Xs.shape[1])
    for _ in range(iters):
        eta = np.clip(Xs @ b, -30, 30)
        p = 1 / (1 + np.exp(-eta))
        W = p * (1 - p)
        g = Xs.T @ (y - p)
        H = (Xs * W[:, None]).T @ Xs + 1e-8 * np.eye(Xs.shape[1])
        st = np.linalg.solve(H, g)
        b += st
        if np.abs(st).max() < 1e-8:
            break
    return 1 / (1 + np.exp(-np.clip(Xs @ b, -30, 30)))


def ols(X, y, cl=None):
    Xs = np.column_stack([np.ones(len(X)), X])
    A = np.linalg.pinv(Xs.T @ Xs)
    b = A @ (Xs.T @ y)
    u = y - Xs @ b
    n, k = Xs.shape
    s2 = u @ u / (n - k)
    se_cl = None
    Sg = None
    if cl is not None:
        g = pd.factorize(pd.Series(cl))[0]
        G = g.max() + 1
        Sg = np.column_stack([np.bincount(g, Xs[:, j] * u, minlength=G) for j in range(k)])
        V = G / (G - 1) * (n - 1) / (n - k) * A @ (Sg.T @ Sg) @ A
        se_cl = np.sqrt(np.diag(V))
    return b, np.sqrt(np.diag(A) * s2), se_cl, A, Sg, n - k


def wild_score(A, Sg, j, b_j, se_j, B=B, seed=1):
    rng = np.random.default_rng(seed)
    G = Sg.shape[0]
    v = Mo_webb(rng, B, G)
    proj = (A @ Sg.T)[j]                                         # G
    bs = v @ proj
    ses = se_j                                                   # EP fixo (aproximação do bootstrap de escores)
    return float(np.mean(np.abs(bs / ses) >= abs(b_j / se_j)))


def Mo_webb(rng, B, G):
    return C.WEBB[rng.integers(0, 6, size=(B, G))]


def aipw_att(y, D, p, m0, g, trim=(0.1, 0.9)):
    s = (p >= trim[0]) & (p <= trim[1])
    y, D, p, m0, g = y[s], D[s], p[s], m0[s], g[s]
    n1 = D.sum()
    w = p / (1 - p)
    r = y - m0
    tau = (np.sum(D * r) - np.sum((1 - D) * w * r)) / n1
    psi = (D * (r - tau) - (1 - D) * w * r) / n1
    gc = pd.factorize(pd.Series(g))[0]
    Psi = np.bincount(gc, psi)
    G = len(Psi)
    se = float(np.sqrt(G / (G - 1) * (Psi ** 2).sum()))
    rng = np.random.default_rng(11)
    v = Mo_webb(rng, B, G)
    bs = v @ Psi
    p_w = float(np.mean(np.abs(bs) >= abs(tau)))
    return {"est": float(tau), "ep": se, "p_wild": p_w, "ic95": [float(tau - 1.96 * se), float(tau + 1.96 * se)],
            "ic95_wild": [float(tau - np.quantile(np.abs(bs), .95)), float(tau + np.quantile(np.abs(bs), .95))],
            "itens_AF": int(n1), "itens_A": int((1 - D).sum()), "G": int(G)}


def entropia(X, D, iters=100):
    """Pesos dos controles que igualam as médias de X às dos tratados (Hainmueller, 2012)."""
    Xc = X[D == 0]
    mu1 = X[D == 1].mean(0)
    sd = Xc.std(0); sd[sd == 0] = 1
    Z = (Xc - mu1) / sd
    lam = np.zeros(Z.shape[1])
    for _ in range(iters):
        e = np.exp(np.clip(Z @ lam, -50, 50))
        w = e / e.sum()
        g = Z.T @ w
        H = (Z * w[:, None]).T @ Z - np.outer(g, g) + 1e-10 * np.eye(len(lam))
        st = np.linalg.solve(H, g)
        lam -= st
        if np.abs(g).max() < 1e-8:
            break
    e = np.exp(np.clip(Z @ lam, -50, 50))
    w = e / e.sum()
    return w, float(np.abs(Z.T @ w).max())


def eb_att(y, D, w, g):
    y1, y0 = y[D == 1], y[D == 0]
    n1 = len(y1)
    m1, m0 = y1.mean(), w @ y0
    psi = np.zeros(len(y))
    psi[D == 1] = (y1 - m1) / n1
    psi[D == 0] = -w * (y0 - m0)
    gc = pd.factorize(pd.Series(g))[0]
    Psi = np.bincount(gc, psi)
    G = len(Psi)
    se = float(np.sqrt(G / (G - 1) * (Psi ** 2).sum()))
    return {"est": float(m1 - m0), "ep": se, "ic95": [float(m1 - m0 - 1.96 * se), float(m1 - m0 + 1.96 * se)],
            "n_efetivo_controles": float(1 / (w ** 2).sum())}


def rosenbaum(dif, gammas=(1, 1.05, 1.1, 1.2, 1.3, 1.5, 2)):
    """Teste de postos sinalizados de Wilcoxon com limite superior do p sob viés Γ (alternativa: AF menor)."""
    d = dif[dif != 0]
    r = stats.rankdata(np.abs(d))
    Tm = r[d < 0].sum()
    out = {"pares": int(len(dif)), "media": float(dif.mean()), "mediana": float(np.median(dif)),
           "fracao_AF_menor": float((dif < 0).mean())}
    tab = {}
    for G_ in gammas:
        pp = G_ / (1 + G_)
        E, V = pp * r.sum(), pp * (1 - pp) * (r ** 2).sum()
        tab[str(G_)] = float(stats.norm.sf((Tm - E) / np.sqrt(V)))
    out["p_superior_por_gamma"] = tab
    lo, hi = 1.0, 50.0
    def pval(G_):
        pp = G_ / (1 + G_)
        return stats.norm.sf((Tm - pp * r.sum()) / np.sqrt(pp * (1 - pp) * (r ** 2).sum()))
    if pval(1.0) >= .05:
        out["gamma_critico"] = 1.0
    else:
        for _ in range(60):
            mid = (lo + hi) / 2
            if pval(mid) < .05:
                lo = mid
            else:
                hi = mid
        out["gamma_critico"] = float((lo + hi) / 2)
    return out


def cinelli_hazlett(Xd, y, D, nomes_bench, ks=(1, 2, 3)):
    """Valores de robustez e limites por covariáveis de referência (fórmulas do pacote sensemakr)."""
    XX = np.column_stack([D, Xd])
    b, se, _, _, _, df = ols(XX, y)
    t = b[1] / se[1]
    f = t / np.sqrt(df)
    r2yd = t ** 2 / (t ** 2 + df)
    def rv(fq):
        return 0.0 if fq <= 0 else 0.5 * (np.sqrt(fq ** 4 + 4 * fq ** 2) - fq ** 2)
    tcrit = stats.t.ppf(.975, df - 1)
    out = {"est": float(b[1]), "ep_classico": float(se[1]), "t": float(t), "gl": int(df), "R2_parcial_YD": float(r2yd),
           "RV_q1": float(rv(abs(f))), "RV_q1_alfa05": float(rv(abs(f) - tcrit / np.sqrt(df - 1)))}
    # regressão de D em X para R² parciais das referências
    bD, seD, _, _, _, dfD = ols(Xd, D.astype(float))
    lim = {}
    for nome, j in nomes_bench.items():
        tDj = bD[1 + j] / seD[1 + j]
        r2dxj = tDj ** 2 / (tDj ** 2 + dfD)
        tYj = b[2 + j] / se[2 + j]
        r2yxj = tYj ** 2 / (tYj ** 2 + df)
        for k in ks:
            r2dz = k * r2dxj / (1 - r2dxj)
            if r2dz >= 1:
                lim[f"{nome}_x{k}"] = None
                continue
            r2zxj = k * r2dxj ** 2 / ((1 - k * r2dxj) * (1 - r2dxj))
            r2yz = min(((np.sqrt(k) + np.sqrt(r2zxj)) / np.sqrt(1 - r2zxj)) ** 2 * (r2yxj / (1 - r2yxj)), 1.0)
            vies = se[1] * np.sqrt(r2yz * r2dz / (1 - r2dz)) * np.sqrt(df)
            adj = b[1] - np.sign(b[1]) * vies
            se_adj = se[1] * np.sqrt((1 - r2yz) / (1 - r2dz)) * np.sqrt(df / (df - 1))
            lim[f"{nome}_x{k}"] = {"R2_DZ": float(r2dz), "R2_YZ": float(r2yz), "estimativa_ajustada": float(adj),
                                   "t_ajustado": float(adj / se_adj)}
    out["limites_por_referencia"] = lim
    return out


def lee_bruto(i):
    """Limites de Lee na diferença bruta do índice: apara-se o grupo com maior taxa de homologação."""
    q = i[(i.m >= 12) & i["prod"].ge(0) & i.menor & i.final].copy()
    s = q.groupby("af").hom.mean()
    y = i[i.e_ok.notna() & (i.m >= 12)]
    y1, y0 = y.loc[y.af.eq(1), "e_ok"], y.loc[y.af.eq(0), "e_ok"]
    alto = 1 if s[1] > s[0] else 0
    p = abs(s[1] - s[0]) / max(s[1], s[0])
    ya = y1 if alto == 1 else y0
    lo_q, hi_q = ya.quantile([p, 1 - p])
    corte_hi, corte_lo = ya[ya <= hi_q], ya[ya >= lo_q]
    outro = y0 if alto == 1 else y1
    sinal = 1 if alto == 1 else -1
    b1 = sinal * (corte_hi.mean() - outro.mean())
    b2 = sinal * (corte_lo.mean() - outro.mean())
    return {"taxa_homologacao_AF": float(s[1]), "taxa_homologacao_A": float(s[0]), "fracao_aparada": float(p),
            "diferenca_bruta": float(y1.mean() - y0.mean()), "limites": [float(min(b1, b2)), float(max(b1, b2))]}


def main(argv=None):
    import sys
    depurar = "--depurar" in (argv if argv is not None else sys.argv[1:])
    i, pn = base()
    if depurar:                                   # rótulos AF embaralhados numa amostra de 25%: só testa o código
        rng = np.random.default_rng(3)
        i = i.sample(frac=.25, random_state=3)
        i["af"] = rng.permutation(i.af.to_numpy())
    d, X = montar(i, pn)
    log("itens", len(d), "AF", int(d.af.sum()))
    y, yR, D = d.e_ok.to_numpy(float), d.eR_ok.to_numpy(float), d.af.to_numpy(float)
    g = d.cnpj.astype(str).to_numpy()
    out = {"itens": int(len(d)), "itens_AF": int(D.sum()), "cnpjs": int(pd.Series(g).nunique()),
           "unidades": int(d.u.nunique())}
    # diferença bruta e MQO (com e sem o índice passado da unidade)
    b, se, sec, A, Sg, _ = ols(D[:, None], y, g)
    out["bruta"] = {"est": float(b[1]), "ep_cnpj": float(sec[1])}
    semA = [c for c in X.columns if not c.startswith("e_passado")]
    for nome, cols in (("A_sem_indice_passado", semA), ("B_com_indice_passado", list(X.columns))):
        XX = np.column_stack([D, X[cols].to_numpy()])
        b, se, sec, A, Sg, _ = ols(XX, y, g)
        r = {"est": float(b[1]), "ep_cnpj": float(sec[1]), "p_wild": wild_score(A, Sg, 1, b[1], sec[1])}
        okR = np.isfinite(yR)
        bR, _, secR, AR, SgR, _ = ols(XX[okR], yR[okR], g[okR])
        r["balanco_indice_estimado"] = {"est": float(bR[1]), "ep_cnpj": float(secR[1]),
                                        "p_wild": wild_score(AR, SgR, 1, bR[1], secR[1])}
        out[f"mqo_{nome}"] = r
        log("MQO", nome, r["est"], r["balanco_indice_estimado"]["est"])
    # AIPW e entropia (especificação A)
    XA = X[semA].to_numpy()
    p = logit((XA - XA.mean(0)) / np.where(XA.std(0) > 0, XA.std(0), 1), D)
    out["suporte"] = {"fracao_AF_em_0.1_0.9": float(((p >= .1) & (p <= .9))[D == 1].mean()),
                      "fracao_A_em_0.1_0.9": float(((p >= .1) & (p <= .9))[D == 0].mean())}
    Xs = np.column_stack([np.ones(len(XA)), XA])
    m0 = Xs @ np.linalg.lstsq(Xs[D == 0], y[D == 0], rcond=None)[0]
    out["aipw"] = aipw_att(y, D, p, m0, g)
    okR = np.isfinite(yR)
    m0R = Xs @ np.linalg.lstsq(Xs[(D == 0) & okR], yR[(D == 0) & okR], rcond=None)[0]
    out["aipw_balanco_indice_estimado"] = aipw_att(yR[okR], D[okR], p[okR], m0R[okR], g[okR])
    log("AIPW", out["aipw"]["est"], "balanço R", out["aipw_balanco_indice_estimado"]["est"])
    s = (p >= .1) & (p <= .9)
    w, desb = entropia(XA[s], D[s])
    out["entropia"] = eb_att(y[s], D[s], w, g[s]) | {"desbalanco_max_padronizado": desb}
    log("EB", out["entropia"]["est"])
    # Rosenbaum: pares no mesmo produto e trimestre, vizinho mais próximo no logit do escore (calibre 0,2 dp)
    lp = np.log(p / (1 - p))
    dd = d.assign(lp=lp, logp=d.logp.to_numpy(float))
    t1 = dd[dd.af.eq(1)][["prod", "tri", "u", "lp", "logp"]].sort_values("lp")
    t0 = dd[dd.af.eq(0)][["prod", "tri", "u", "lp", "logp"]].sort_values("lp")
    par = pd.merge_asof(t1, t0, on="lp", by=["prod", "tri"], direction="nearest", tolerance=0.2 * float(np.std(lp)),
                        suffixes=("_1", "_0"))
    par = par[par.logp_0.notna() & (par.u_1 != par.u_0)]
    out["rosenbaum"] = rosenbaum((par.logp_1 - par.logp_0).to_numpy()) | {
        "fracao_AF_com_par": float(len(par) / len(t1))}
    log("Rosenbaum Γ crítico", out["rosenbaum"]["gamma_critico"])
    # Cinelli e Hazlett, especificação A
    nomes = {"tamanho_unidade": semA.index("tam"), "estimado_passado_unidade": semA.index("eR_passado"),
             "competicao_esperada": semA.index("comp")}
    out["cinelli_hazlett"] = cinelli_hazlett(XA, y, D, nomes)
    log("CH RV", out["cinelli_hazlett"]["RV_q1"])
    out["lee"] = lee_bruto(i)
    out["tempo_s"] = round(time.time() - T0)
    destino = C.DADOS / "resultados_item_depuracao.json" if depurar else C.AQUI / "resultados_item.json"
    destino.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    log("FIM ok")


if __name__ == "__main__":
    main()
