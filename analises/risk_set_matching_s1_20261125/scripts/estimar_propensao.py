"""Etapa 8: propensity score de MUDANÇA (probabilidade de trocar de modo em t0, dado o histórico anterior).

Estimado separadamente para A→AF e AF→A, na população de risco de cada direção (todas as UASGs elegíveis em cada
t0: tratadas + candidatas completas), com efeitos de calendário (dummies de t0) e as covariáveis M0. Logit com
penalidade L2 (coeficientes padronizados; intercepto e calendário sem penalidade). Não é a probabilidade geral de
usar AF. AUC é só diagnóstico; separação quase perfeita indica falta de suporte comum.
"""
import numpy as np
import pandas as pd
from scipy import optimize, special, stats


def logit_l2(X, y, lam, nao_penalizar):
    n, k = X.shape
    pen = np.full(k, lam)
    pen[nao_penalizar] = 0.0

    def f(b):
        eta = X @ b
        ll = np.sum(y * eta - np.logaddexp(0, eta))
        return -ll + 0.5 * np.sum(pen * b ** 2), -(X.T @ (y - special.expit(eta))) + pen * b
    r = optimize.minimize(f, np.zeros(k), jac=True, method="L-BFGS-B", options={"maxiter": 5000, "gtol": 1e-8})
    return r.x, bool(r.success)


def auc(score, y):
    y = np.asarray(y, bool)
    if y.all() or (~y).all():
        return np.nan
    r = stats.rankdata(score)
    n1, n0 = y.sum(), (~y).sum()
    return float((r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def estimar(pop, cols, lam=1.0):
    """pop: linhas (u, t0) completas da direção com coluna `y` (1 = trocou em t0). Retorna logit do PS e diagnósticos."""
    Z = pop[cols].to_numpy(float)
    mu, sd = Z.mean(0), Z.std(0)
    usar = sd > 0
    Z = (Z[:, usar] - mu[usar]) / sd[usar]
    t0s = sorted(pop.t0.unique())
    D = np.column_stack([(pop.t0 == t).to_numpy(float) for t in t0s[1:]]) if len(t0s) > 1 else np.zeros((len(pop), 0))
    X = np.column_stack([np.ones(len(pop)), D, Z])
    nao_pen = list(range(1 + D.shape[1]))
    b, conv = logit_l2(X, pop.y.to_numpy(float), lam, nao_pen)
    eta = X @ b
    p = special.expit(eta)
    y = pop.y.to_numpy(int)
    q = pd.qcut(pd.Series(p).rank(method="first"), 10, labels=False) if len(p) >= 10 else pd.Series(0, index=range(len(p)))
    calib = (pd.DataFrame({"decil": q.to_numpy(), "p": p, "y": y}).groupby("decil")
             .agg(n=("y", "size"), p_medio=("p", "mean"), taxa_observada=("y", "mean")).reset_index())
    coefs = dict(zip(["intercepto"] + [f"t0_{t}" for t in t0s[1:]] + [c for c, u in zip(cols, usar) if u], b))
    diag = {"linhas": int(len(pop)), "tratadas": int(y.sum()), "convergiu": conv, "auc_diagnostico": auc(eta, y),
            "dp_logit_populacao": float(np.std(eta)), "covariaveis_constantes_removidas": [c for c, u in zip(cols, usar) if not u],
            "p_tratadas_quantis": np.quantile(p[y == 1], [0, .05, .25, .5, .75, .95, 1]).tolist() if y.sum() else None,
            "p_controles_quantis": np.quantile(p[y == 0], [0, .05, .25, .5, .75, .95, 1]).tolist() if (y == 0).sum() else None}
    return eta, p, diag, calib, coefs
