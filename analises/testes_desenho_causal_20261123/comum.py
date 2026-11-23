"""Funções comuns aos testes do desenho causal A × AF (protocolo.md). Sem efeito colateral ao importar."""
import os, sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]                                   # PNCP-Automation
DADOS = RAIZ / "dados" / "testes_desenho_causal"         # fora do git
INI, FIM_ITENS, FIM_MODOS = "2022-01", "2026-03", "2026-09"
M0 = 2022 * 12                                           # índice de 2022-01
LN10 = float(np.log(10))

REGIAO = {**{u: "N" for u in "AC AM AP PA RO RR TO".split()},
          **{u: "NE" for u in "AL BA CE MA PB PE PI RN SE".split()},
          **{u: "CO" for u in "DF GO MS MT".split()},
          **{u: "SE" for u in "ES MG RJ SP".split()},
          **{u: "S" for u in "PR RS SC".split()}}


def ro(p):
    return sqlite3.connect(f"file:{Path(p).resolve().as_posix()}?mode=ro", uri=True)


def assinatura(p):
    st = os.stat(p)
    return st.st_size, st.st_mtime_ns


def mes_de(s):
    """'AAAA-MM...' -> índice de mês (ano*12 + mês-1); vazio -> <NA>."""
    s = pd.Series(s, copy=False).astype("string")
    return s.str[:4].astype("Int64") * 12 + s.str[5:7].astype("Int64") - 1


def mes_str(m):
    m = int(m)
    return f"{m // 12}-{m % 12 + 1:02d}"


def loo(d, col, cel, un="u", min_n=5, min_u=3):
    """Média de `col` na célula `cel` nas OUTRAS unidades (deixa a unidade de fora).
    Exige >= min_n observações de >= min_u outras unidades; senão NaN."""
    ok0 = d[col].notna()
    z = d.loc[ok0, cel + [un]].copy()
    z["x"] = d.loc[ok0, col].astype(float)
    g = z.groupby(cel, observed=True)["x"]
    S, N = g.transform("sum"), g.transform("size")
    U = z.groupby(cel, observed=True)[un].transform("nunique")
    gu = z.groupby(cel + [un], observed=True)["x"]
    Su, Nu = gu.transform("sum"), gu.transform("size")
    ok = ((N - Nu) >= min_n) & ((U - 1) >= min_u)
    ref = ((S - Su) / (N - Nu).where(ok)).where(ok)
    out = pd.Series(np.nan, index=d.index)
    out.loc[ref.index] = ref.to_numpy()
    return out


# ------------------------------------------------------------------------------------------------ inferência
WEBB = np.array([-np.sqrt(1.5), -1.0, -np.sqrt(0.5), np.sqrt(0.5), 1.0, np.sqrt(1.5)])


def _codigos(g):
    return pd.factorize(pd.Series(g).astype(str))[0]


def ols_cr1(X, y, cl, w=None):
    """MQO/MQP com variância CR1 por cluster. Devolve beta, V, G."""
    X = np.asarray(X, float); y = np.asarray(y, float)
    w = np.ones(len(y)) if w is None else np.asarray(w, float)
    g = _codigos(cl); G = g.max() + 1
    XtW = X.T * w
    A = np.linalg.pinv(XtW @ X)
    b = A @ (XtW @ y)
    u = y - X @ b
    S = np.zeros((G, X.shape[1]))
    np.add.at(S, g, (X * (w * u)[:, None]))
    n, k = X.shape
    c = G / (G - 1) * (n - 1) / max(n - k, 1)
    V = c * A @ (S.T @ S) @ A
    return b, V, G


def wild_teste(X, y, cl, R, r0=0.0, w=None, B=9999, seed=20261123):
    """Bootstrap selvagem restrito por cluster (WCR, pesos de Webb) para H0: R·beta = r0.
    Devolve estatística t, p bootstrap e p da t(G-1)."""
    from scipy import stats
    X = np.asarray(X, float); y = np.asarray(y, float); R = np.asarray(R, float).ravel()
    w = np.ones(len(y)) if w is None else np.asarray(w, float)
    b, V, G = ols_cr1(X, y, cl, w)
    se = float(np.sqrt(R @ V @ R))
    t = (float(R @ b) - r0) / se
    # estimativa restrita (MQP com restrição linear)
    XtW = X.T * w
    A = np.linalg.pinv(XtW @ X)
    bt = b - A @ R * ((R @ b - r0) / (R @ A @ R))
    ut = y - X @ bt
    g = _codigos(cl)
    rng = np.random.default_rng(seed)
    v = WEBB[rng.integers(0, 6, size=(B, G))]           # B x G
    ys = (X @ bt)[:, None] + ut[:, None] * v[:, g].T    # n x B
    bs = A @ (XtW @ ys)                                  # k x B
    us = ys - X @ bs
    n, k = X.shape
    c = G / (G - 1) * (n - 1) / max(n - k, 1)
    # escores agregados por cluster: G x k x B
    sc = np.zeros((G, k, B))
    for j in range(k):
        np.add.at(sc[:, j, :], g, (X[:, j] * w)[:, None] * us)
    ra = R @ A                                           # k
    proj = np.einsum("k,gkb->gb", ra, sc)                # G x B
    ses = np.sqrt(c * (proj ** 2).sum(0))
    ts = (R @ bs - r0) / ses
    p_boot = float(np.mean(np.abs(ts) >= abs(t)))
    p_t = float(2 * stats.t.sf(abs(t), G - 1))
    return {"t": t, "p_wild": p_boot, "p_t": p_t, "G": int(G)}


def media_inferencia(y, cl, w=None, B=9999, seed=20261123, ic=True):
    """Média (ponderada) de y com EP CR1 por cluster, p do bootstrap selvagem restrito e IC95 por inversão."""
    from scipy import stats
    y = np.asarray(y, float)
    X = np.ones((len(y), 1))
    b, V, G = ols_cr1(X, y, cl, w)
    est, se = float(b[0]), float(np.sqrt(V[0, 0]))
    tst = wild_teste(X, y, cl, [1.0], 0.0, w, B, seed)
    out = {"est": est, "ep": se, "n": int(len(y)), "G": int(G), "p_wild": tst["p_wild"], "p_t": tst["p_t"],
           "ic95_t": [est - stats.t.ppf(.975, G - 1) * se, est + stats.t.ppf(.975, G - 1) * se]}
    if ic:
        out["ic95_wild"] = ic_inversao(X, y, cl, [1.0], est, se, w, B, seed)
    return out


def ic_inversao(X, y, cl, R, est, se, w=None, B=1999, seed=20261123, alfa=0.05):
    """IC por inversão do teste WCR (bissecção em cada lado)."""
    def p(r0):
        return wild_teste(X, y, cl, R, r0, w, B, seed)["p_wild"]
    lados = []
    for sinal in (-1, 1):
        a, bnd = est, est + sinal * 4 * se                 # a: aceita; bnd: deve rejeitar
        k = 0
        while p(bnd) > alfa and k < 6:
            bnd = est + sinal * (abs(bnd - est) * 2)
            k += 1
        for _ in range(18):
            mid = (a + bnd) / 2
            if p(mid) > alfa:
                a = mid
            else:
                bnd = mid
        lados.append((a + bnd) / 2)
    return [min(lados), max(lados)]


def resumo_lin(X, y, cl, R, w=None, B=9999, seed=20261123, ic=True):
    """Combinação linear R·beta com EP CR1, p WCR e IC por inversão."""
    from scipy import stats
    b, V, G = ols_cr1(X, y, cl, w)
    R = np.asarray(R, float).ravel()
    est, se = float(R @ b), float(np.sqrt(R @ V @ R))
    tst = wild_teste(X, y, cl, R, 0.0, w, B, seed)
    out = {"est": est, "ep": se, "G": int(G), "p_wild": tst["p_wild"], "p_t": tst["p_t"],
           "ic95_t": [est - stats.t.ppf(.975, G - 1) * se, est + stats.t.ppf(.975, G - 1) * se]}
    if ic:
        out["ic95_wild"] = ic_inversao(X, y, cl, R, est, se, w, min(B, 1999), seed)
    return out


def pct(b):
    """log-pontos -> % (100·(exp(b)-1))."""
    return 100 * float(np.expm1(b))
