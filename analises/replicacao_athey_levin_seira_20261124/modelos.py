"""Estimadores da replicação de Athey, Levin e Seira (2011), Fase 1 (protocolo.md, seções 5–8 e 12).

- logit: máxima verossimilhança (Newton–Raphson), EP robusto (HC1) e agrupado (CR1).
- reg: MQ ponderados com efeitos fixos absorvidos por projeções alternadas (Frisch–Waugh–Lovell), EP CR1 agrupado;
  os efeitos fixos aninhados no grupo não entram na correção de graus de liberdade (como no reghdfe); concentração da
  variação identificadora (parcela de Σ w x̃² por grupo, x̃ = AF depois de retirar X e os efeitos fixos).
- combinação linear (efeito médio com interações) e Wald com F(q, G − 1).
"""
import numpy as np
import pandas as pd
import scipy.sparse as sp
from scipy import stats


# --------------------------------------------------------------------------------------------- utilidades
def dummies(df, cols, prefixo=True):
    """Dummies das colunas categóricas, sem a primeira categoria (ordenada) de cada uma."""
    mats, nomes = [], []
    for col in cols:
        v = df[col].astype(str).to_numpy()
        cats = np.array(sorted(pd.unique(v)))
        codes = np.searchsorted(cats, v)
        for j in range(1, len(cats)):
            mats.append((codes == j).astype(float))
            nomes.append(f"{col}={cats[j]}" if prefixo else str(cats[j]))
    return (np.column_stack(mats) if mats else np.zeros((len(df), 0))), nomes


def codigos(df, fe):
    if isinstance(fe, str):
        return pd.factorize(df[fe])[0]
    return df.groupby(list(fe), sort=False, observed=True).ngroup().to_numpy()


def pct(b):
    return 100 * (np.exp(np.asarray(b, float) / 100) - 1)


def holm(p):
    p = np.asarray(p, float)
    ordem = np.argsort(p)
    m = len(p)
    adj = np.empty(m)
    mx = 0.0
    for j, k in enumerate(ordem):
        mx = max(mx, min(1.0, (m - j) * p[k]))
        adj[k] = mx
    return adj


# --------------------------------------------------------------------------------------------- logit
def logit(y, X, cl=None, nomes=None, maxit=100, tol=1e-10):
    y = np.asarray(y, float)
    X = np.asarray(X, float)
    n, k = X.shape
    b = np.zeros(k)
    conv = False
    for it in range(maxit):
        eta = np.clip(X @ b, -35, 35)
        p = 1 / (1 + np.exp(-eta))
        W = p * (1 - p)
        g = X.T @ (y - p)
        H = (X * W[:, None]).T @ X
        step = np.linalg.lstsq(H, g, rcond=None)[0]
        b += step
        if np.max(np.abs(step)) < tol:
            conv = True
            break
    eta = np.clip(X @ b, -35, 35)
    p = 1 / (1 + np.exp(-eta))
    H = (X * (p * (1 - p))[:, None]).T @ X
    A = np.linalg.pinv(H)
    s = X * (y - p)[:, None]
    V_hc = n / (n - k) * A @ (s.T @ s) @ A
    out = {"b": b, "p": p, "V_hc": V_hc, "convergiu": conv, "iteracoes": it + 1, "n": n, "k": k,
           "nomes": nomes or [f"x{j}" for j in range(k)]}
    if cl is not None:
        g_ = pd.factorize(pd.Series(cl).astype(str))[0]
        G = g_.max() + 1
        S = np.zeros((G, k))
        np.add.at(S, g_, s)
        out["V_cl"] = G / (G - 1) * (n - 1) / (n - k) * A @ (S.T @ S) @ A
        out["G"] = int(G)
    ll = float(np.sum(y * np.log(np.clip(p, 1e-15, 1)) + (1 - y) * np.log(np.clip(1 - p, 1e-15, 1))))
    p0 = y.mean()
    ll0 = float(n * (p0 * np.log(p0) + (1 - p0) * np.log(1 - p0)))
    out.update({"ll": ll, "ll0": ll0, "pseudo_r2": 1 - ll / ll0, "brier": float(np.mean((y - p) ** 2)), "auc": auc(y, p)})
    return out


def auc(y, s):
    y = np.asarray(y, bool)
    r = stats.rankdata(s)
    n1, n0 = y.sum(), (~y).sum()
    return float((r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


# --------------------------------------------------------------------------------------------- efeitos fixos
def demean(Z, cods, w, tol=1e-9, maxit=5000):
    """Retira, por projeções alternadas ponderadas, as médias de cada conjunto de efeitos fixos (com a constante)."""
    Z = np.array(Z, float, copy=True)
    w = np.asarray(w, float)
    Z -= (w @ Z) / w.sum()
    if not cods:
        return Z, 0
    n = len(w)
    Ds = []
    for c in cods:
        L = int(c.max()) + 1
        D = sp.csr_matrix((w, (np.arange(n), c)), shape=(n, L))
        Ds.append((D.T.tocsr(), c, np.bincount(c, w, L)))
    escala = np.maximum(np.sqrt((w @ Z ** 2) / w.sum()), 1e-12)
    for it in range(maxit):
        mx = 0.0
        for DT, c, sw in Ds:
            M = (DT @ Z) / np.maximum(sw, 1e-300)[:, None]
            Z -= M[c]
            mx = max(mx, float(np.max(np.abs(M) / escala)))
        if mx < tol or len(Ds) == 1:
            return Z, it + 1
    return Z, -maxit                                    # não convergiu


def aninhado(c_fe, c_cl):
    s = pd.DataFrame({"f": c_fe, "g": c_cl}).groupby("f").g.nunique()
    return bool((s <= 1).all())


def reg(df, y, xcols, fes=(), w=None, clusters=("cnpj",), alvo="af", Xextra=None, nomes_extra=None, tol=1e-9,
        retorna=False):
    """y ~ alvo + xcols (+ Xextra) | fes. Devolve dict com β do alvo e, por agrupamento, EP CR1, IC95 e p da t(G − 1)."""
    n = len(df)
    w = np.ones(n) if w is None else np.asarray(w, float)
    cols = [df[y].to_numpy(float), df[alvo].to_numpy(float)] + [df[c].to_numpy(float) for c in xcols]
    nomes = [alvo] + list(xcols)
    if Xextra is not None and Xextra.shape[1]:
        cols += [Xextra[:, j] for j in range(Xextra.shape[1])]
        nomes += list(nomes_extra)
    Z = np.column_stack(cols)
    cods = [codigos(df, f) for f in fes]
    Zt, iters = demean(Z, cods, w, tol)
    yt, Xt = Zt[:, 0], Zt[:, 1:]
    # colunas sem variação depois dos efeitos fixos saem (ex.: dummies absorvidas)
    var = (w @ Xt ** 2) / w.sum()
    keep = var > 1e-12 * np.maximum((w @ Z[:, 1:] ** 2) / w.sum(), 1e-12)
    if not keep[0]:
        return {"erro": "AF absorvido pelos efeitos fixos", "n": n}
    Xt, nomes_k = Xt[:, keep], [nm for nm, k in zip(nomes, keep) if k]
    XtW = Xt.T * w
    A = np.linalg.pinv(XtW @ Xt)
    b = A @ (XtW @ yt)
    u = yt - Xt @ b
    k = Xt.shape[1]
    # x̃ do alvo: resíduo de AF nas demais colunas (já sem os efeitos fixos)
    if k > 1:
        O = Xt[:, 1:]
        gam = np.linalg.lstsq(O.T * w @ O, (O.T * w) @ Xt[:, 0], rcond=None)[0]
        xr = Xt[:, 0] - O @ gam
    else:
        xr = Xt[:, 0]
    out = {"b": float(b[0]), "n": int(n), "k": int(k), "iteracoes_fe": int(iters), "nomes": nomes_k, "beta": b,
           "compras": int(df.compra.nunique()) if "compra" in df else None,
           "uasgs": int(df.u.nunique()) if "u" in df else None, "cnpjs": int(df.cnpj.nunique()) if "cnpj" in df else None,
           "soma_pesos": float(w.sum())}
    for cl in clusters:
        g = pd.factorize(df[cl].astype(str))[0]
        G = int(g.max()) + 1
        S = np.zeros((G, k))
        np.add.at(S, g, Xt * (w * u)[:, None])
        k_abs = sum(int(c.max()) for c in cods if not aninhado(c, g))      # níveis − 1 de cada efeito fixo não aninhado
        cfac = G / (G - 1) * (n - 1) / max(n - k - k_abs - 1, 1)
        V = cfac * A @ (S.T @ S) @ A
        se = float(np.sqrt(V[0, 0]))
        tq = stats.t.ppf(.975, G - 1)
        sx = pd.Series(w * xr ** 2).groupby(g).sum()
        sx = sx / sx.sum()
        out[cl] = {"ep": se, "ic95": [out["b"] - tq * se, out["b"] + tq * se], "p": float(2 * stats.t.sf(abs(out["b"] / se), G - 1)),
                   "G": G, "G_efetivo_variacao": float(1 / (sx ** 2).sum()), "maior_grupo_variacao": float(sx.max()),
                   "top5_grupos_variacao": float(sx.sort_values(ascending=False).head(5).sum()),
                   "top10_grupos_variacao": float(sx.sort_values(ascending=False).head(10).sum()), "V": V,
                   "k_absorvidos_contados": int(k_abs)}
        if retorna:
            out[cl]["S"] = S
            out[cl]["A"] = A
            out[cl]["g"] = g
    if retorna:
        out["residuos"] = u                              # não usar "u": é o nome do agrupamento por UASG
        out["Xt"] = Xt
    return out


def comb_linear(r, L, cl="cnpj"):
    """θ = L′β, com EP pelo método delta e p da t(G − 1)."""
    V = r[cl]["V"]
    th = float(L @ r["beta"])
    se = float(np.sqrt(L @ V @ L))
    G = r[cl]["G"]
    tq = stats.t.ppf(.975, G - 1)
    return {"est": th, "ep": se, "ic95": [th - tq * se, th + tq * se], "p": float(2 * stats.t.sf(abs(th / se), G - 1)), "G": G}


def wald(r, idx, cl="cnpj"):
    V = r[cl]["V"][np.ix_(idx, idx)]
    b = r["beta"][idx]
    q = len(idx)
    F = float(b @ np.linalg.pinv(V) @ b / q)
    G = r[cl]["G"]
    return {"F": F, "gl1": q, "gl2": G - 1, "p": float(stats.f.sf(F, q, G - 1))}


def influencia_grupos(r, cl="cnpj"):
    """Contribuição de cada grupo para β do alvo (aprox. de 1ª ordem): ψ_g = [A Σ_{i∈g} x̃_i w_i û_i]_alvo."""
    A, S, g = r[cl]["A"], r[cl]["S"], r[cl]["g"]
    psi = (S @ A.T)[:, 0]
    return psi, g
