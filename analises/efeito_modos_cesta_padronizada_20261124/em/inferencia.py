"""Regressão com efeitos fixos de alta dimensão e inferência agrupada.

- `remover_singletons`: elimina, iterativamente, observações sozinhas em algum grupo de efeito fixo.
- `demean`: projeções alternadas (MAP) com pesos; converge até `tol` na variação máxima.
- `ols_fe`: β por FWL, CR1 agrupado em uma dimensão e CGM em duas; WCR (Webb) para o 1º coeficiente.
Tudo em NumPy, sem carregar matrizes densas de dummies.
"""
import numpy as np
from scipy import stats

WEBB = np.array([-np.sqrt(1.5), -1.0, -np.sqrt(0.5), np.sqrt(0.5), 1.0, np.sqrt(1.5)])


def codificar(*arrays):
    """Combina uma ou mais colunas em um código inteiro denso 0..G-1."""
    if len(arrays) == 1:
        _, cod = np.unique(np.asarray(arrays[0]), return_inverse=True)
        return cod.astype(np.int64)
    base = np.zeros(len(arrays[0]), dtype=np.int64)
    for a in arrays:
        _, c = np.unique(np.asarray(a), return_inverse=True)
        base = base * (c.max() + 1) + c
    _, cod = np.unique(base, return_inverse=True)
    return cod.astype(np.int64)


def remover_singletons(fes, max_iter=100):
    """Máscara booleana das observações mantidas (grupos com ≥ 2 obs em todas as dimensões)."""
    n = len(fes[0]) if fes else 0
    keep = np.ones(n, dtype=bool)
    for _ in range(max_iter):
        mudou = False
        for f in fes:
            cont = np.bincount(f[keep], minlength=f.max() + 1)
            sing = keep & (cont[f] < 2)
            if sing.any():
                keep &= ~sing
                mudou = True
        if not mudou:
            break
    return keep


def demean(M, fes, w=None, tol=1e-8, max_iter=5000):
    """Resíduos de M (n × k) após projetar fora os efeitos fixos `fes` (lista de códigos), pesos w."""
    M = np.array(M, dtype=float, copy=True)
    if M.ndim == 1:
        M = M[:, None]
    if not fes:
        if w is None:
            return M - M.mean(0)
        return M - (w[:, None] * M).sum(0) / w.sum()
    w = np.ones(M.shape[0]) if w is None else np.asarray(w, dtype=float)
    somas_w = [np.bincount(f, weights=w, minlength=f.max() + 1) for f in fes]
    for it in range(max_iter):
        delta = 0.0
        for f, sw in zip(fes, somas_w):
            for j in range(M.shape[1]):
                g = np.bincount(f, weights=w * M[:, j], minlength=sw.size) / np.where(sw > 0, sw, 1)
                M[:, j] -= g[f]
                delta = max(delta, np.abs(g).max())
        if len(fes) == 1 or delta < tol:
            break
    return M


def _cr1(Xd, e, cl, w):
    n, k = Xd.shape
    G = cl.max() + 1
    XtX_inv = np.linalg.pinv((Xd * w[:, None]).T @ Xd)
    S = np.zeros((G, k))
    for j in range(k):
        S[:, j] = np.bincount(cl, weights=w * Xd[:, j] * e, minlength=G)
    g_eff = np.unique(cl).size
    c = g_eff / (g_eff - 1) * (n - 1) / max(n - k, 1)
    return c * XtX_inv @ (S.T @ S) @ XtX_inv, g_eff


def vcov_cluster(Xd, e, clusters, w=None):
    """CR1 em uma dimensão (clusters = array) ou CGM em duas (clusters = (c1, c2))."""
    w = np.ones(len(e)) if w is None else w
    if isinstance(clusters, tuple):
        c1, c2 = clusters
        c12 = codificar(c1, c2)
        V1, g1 = _cr1(Xd, e, c1, w)
        V2, g2 = _cr1(Xd, e, c2, w)
        V12, _ = _cr1(Xd, e, c12, w)
        V = V1 + V2 - V12
        # garante semidefinição positiva (correção usual de autovalores)
        ev, evec = np.linalg.eigh((V + V.T) / 2)
        V = evec @ np.diag(np.maximum(ev, 0)) @ evec.T
        return V, min(g1, g2)
    return _cr1(Xd, e, clusters, w)


def ols_fe(y, X, fes, cluster, w=None, cluster2=None, tol=1e-8, max_iter=5000, nomes=None, wcr=0, semente=0):
    """β de y ~ X + FE. Retorna dict com coeficientes, EP CR1 (e CGM se cluster2), IC95, valor-p (t com G−1 gl),
    n, número de clusters e, se wcr > 0, valor-p WCR (Webb) e IC WCU percentil-t para o 1º coeficiente."""
    y = np.asarray(y, dtype=float)
    X = np.asarray(X, dtype=float)
    if X.ndim == 1:
        X = X[:, None]
    w = np.ones(len(y)) if w is None else np.asarray(w, dtype=float)
    D = demean(np.column_stack([y, X]), fes, w, tol, max_iter)
    yd, Xd = D[:, 0], D[:, 1:]
    XtWX = (Xd * w[:, None]).T @ Xd
    b = np.linalg.pinv(XtWX) @ ((Xd * w[:, None]).T @ yd)
    e = yd - Xd @ b
    V, G = vcov_cluster(Xd, e, cluster, w)
    se = np.sqrt(np.maximum(np.diag(V), 0))
    tcrit = stats.t.ppf(0.975, G - 1)
    out = {"beta": b, "se": se, "ic_inf": b - tcrit * se, "ic_sup": b + tcrit * se,
           "p": 2 * stats.t.sf(np.abs(b / np.where(se > 0, se, np.nan)), G - 1), "n": len(y), "clusters": G,
           "nomes": nomes or [f"x{j}" for j in range(X.shape[1])]}
    if cluster2 is not None:
        V2, G2 = vcov_cluster(Xd, e, (cluster, cluster2), w)
        se2 = np.sqrt(np.maximum(np.diag(V2), 0))
        t2 = stats.t.ppf(0.975, G2 - 1)
        out.update({"se_2vias": se2, "ic_inf_2vias": b - t2 * se2, "ic_sup_2vias": b + t2 * se2,
                    "p_2vias": 2 * stats.t.sf(np.abs(b / np.where(se2 > 0, se2, np.nan)), G2 - 1), "clusters2": G2})
    if wcr:
        out.update(wild_cluster(yd, Xd, cluster, w, wcr, semente))
    # contribuição de cada cluster para a variação identificadora do 1º coeficiente (após FWL nos demais)
    x1 = Xd[:, 0]
    if Xd.shape[1] > 1:
        Z = Xd[:, 1:]
        g = np.linalg.pinv((Z * w[:, None]).T @ Z) @ ((Z * w[:, None]).T @ x1)
        x1 = x1 - Z @ g
    contrib = np.bincount(cluster, weights=w * x1 ** 2, minlength=cluster.max() + 1)
    sh = contrib / contrib.sum() if contrib.sum() > 0 else contrib
    out["contribuicao_cluster"] = sh
    out["n_efetivo_clusters"] = 1.0 / np.sum(sh ** 2) if sh.sum() > 0 else np.nan
    out["_x1"] = x1
    out["_resid"] = e
    return out


def wild_cluster(yd, Xd, cluster, w, B, semente):
    """WCR (restrito, H0: β1 = 0) e WCU percentil-t para o 1º coeficiente, pesos de Webb por cluster.
    Usa FWL: x1 residualizado nos demais regressores; tudo em somas por cluster (B × G)."""
    rng = np.random.default_rng(semente)
    G = cluster.max() + 1
    x1 = Xd[:, 0]
    Z = Xd[:, 1:]
    if Z.shape[1]:
        g = np.linalg.pinv((Z * w[:, None]).T @ Z) @ ((Z * w[:, None]).T @ x1)
        x1 = x1 - Z @ g
        gy = np.linalg.pinv((Z * w[:, None]).T @ Z) @ ((Z * w[:, None]).T @ yd)
        y_r = yd - Z @ gy                     # resíduo restrito (sem x1)
    else:
        y_r = yd.copy()
    q = np.sum(w * x1 ** 2)
    b = np.sum(w * x1 * y_r) / q
    e_u = y_r - x1 * b
    s_r = np.bincount(cluster, weights=w * x1 * y_r, minlength=G)      # Σ x1 ε_r por cluster
    s_u = np.bincount(cluster, weights=w * x1 * e_u, minlength=G)
    qg = np.bincount(cluster, weights=w * x1 ** 2, minlength=G)
    g_eff = np.unique(cluster).size
    n = len(yd)
    c = g_eff / (g_eff - 1) * (n - 1) / max(n - Xd.shape[1], 1)
    se = np.sqrt(c * np.sum(s_u ** 2)) / q
    t0 = b / se
    W = WEBB[rng.integers(0, 6, size=(B, G))]
    # WCR: y* = w_g ε_r ⇒ β* = Σ w_g s_r / q; resíduo* por cluster = w_g s_r − β* q_g
    bs = W @ s_r / q
    res = W * s_r[None, :] - bs[:, None] * qg[None, :]
    ses = np.sqrt(c * np.sum(res ** 2, axis=1)) / q
    ts = bs / ses
    p_wcr = float(np.mean(np.abs(ts) >= np.abs(t0)))
    # WCU percentil-t: y* = x1 b + w_g ε_u
    bu = b + W @ s_u / q
    resu = W * s_u[None, :] - (bu - b)[:, None] * qg[None, :]
    seu = np.sqrt(c * np.sum(resu ** 2, axis=1)) / q
    tu = (bu - b) / seu
    lo, hi = np.quantile(tu, [0.025, 0.975])
    return {"p_wcr": p_wcr, "ic_wcu_inf": b - hi * se, "ic_wcu_sup": b - lo * se, "B": B}


def holm(pvals):
    p = np.asarray(pvals, dtype=float)
    ordem = np.argsort(p)
    m = len(p)
    adj = np.empty(m)
    acum = 0.0
    for r, i in enumerate(ordem):
        acum = max(acum, (m - r) * p[i])
        adj[i] = min(1.0, acum)
    return adj


def mde(se, alfa=0.05, poder=0.80):
    """Diferença mínima detectável (teste bicaudal) para um EP dado."""
    return (stats.norm.ppf(1 - alfa / 2) + stats.norm.ppf(poder)) * se
