"""Matching pelo escore de propensão com M vizinhos (Abadie e Imbens, 2006), eq. (7) de Athey, Levin e Seira (2011).

- Vizinhos do outro modo por |p̂_i − p̂_j|, com reposição; empates na M-ésima distância entram todos (peso repartido).
- Estratos exatos opcionais (trimestre × grupo; UASG) e caliper opcional.
- Estimandos com pesos gerais a_i: efeito médio simétrico (eq. 7), nas AF e nas A.
- Variâncias (com pesos de casamento ω e empates):
    condicional (na amostra):  Σ_j c_j² σ̂_j²
    populacional (AI, 2006):   Σ_i a_i² (τ̂_i − τ̂)² + Σ_j σ̂_j² (c_j² − a_j² − ν_j)
  com σ̂_j² = (#J/(#J + 1)) (Y_j − média dos J vizinhos do mesmo modo)², J = 4.
  Sem empates e com a_i = 1/N, a fórmula populacional é a de Abadie e Imbens (2006, Teorema 7).
- Adaptação agrupada (não é estimador consagrado): Σ_g (Σ_{j∈g} c_j ε̂_j)², ε̂_j com vizinhos do mesmo modo de OUTROS
  grupos; a correção #J/(#J + 1) só na diagonal.
"""
import numpy as np
import pandas as pd

TOL_EMPATE = 1e-12


def _vizinhos_1(x, alvo_ord, alvo_idx, M, caliper=None, excluir=None):
    """Para o valor x, os índices (em alvo_idx) dos M mais próximos em alvo_ord (ordenado), com empates."""
    n = len(alvo_ord)
    if n == 0:
        return np.zeros(0, int), np.zeros(0)
    pos = np.searchsorted(alvo_ord, x)
    lo, hi = pos - 1, pos
    sel = []
    while len(sel) < M and (lo >= 0 or hi < n):
        dl = x - alvo_ord[lo] if lo >= 0 else np.inf
        dh = alvo_ord[hi] - x if hi < n else np.inf
        if dl <= dh:
            j, d, lo = lo, dl, lo - 1
        else:
            j, d, hi = hi, dh, hi + 1
        if excluir is not None and excluir(alvo_idx[j]):
            continue
        sel.append((j, d))
    if not sel:
        return np.zeros(0, int), np.zeros(0)
    dM = sel[-1][1]
    # empates na M-ésima distância
    while lo >= 0 and abs((x - alvo_ord[lo]) - dM) <= TOL_EMPATE:
        if excluir is None or not excluir(alvo_idx[lo]):
            sel.append((lo, x - alvo_ord[lo]))
        lo -= 1
    while hi < n and abs((alvo_ord[hi] - x) - dM) <= TOL_EMPATE:
        if excluir is None or not excluir(alvo_idx[hi]):
            sel.append((hi, alvo_ord[hi] - x))
        hi += 1
    j = np.array([s[0] for s in sel], int)
    d = np.array([s[1] for s in sel])
    if caliper is not None:
        ok = d <= caliper
        j, d = j[ok], d[ok]
    return alvo_idx[j], d


def casar(ps, W, M=4, estratos=None, caliper=None):
    """Para cada unidade, a lista de vizinhos do outro modo (no mesmo estrato). Devolve lista de arrays (índices globais)."""
    ps = np.asarray(ps, float)
    W = np.asarray(W, int)
    n = len(ps)
    est = np.zeros(n, int) if estratos is None else pd.factorize(pd.Series(estratos).astype(str))[0]
    J = [np.zeros(0, int)] * n
    for s in np.unique(est):
        ix = np.where(est == s)[0]
        for t in (0, 1):
            orig = ix[W[ix] == t]
            dest = ix[W[ix] == 1 - t]
            if len(orig) == 0 or len(dest) == 0:
                continue
            o = np.argsort(ps[dest], kind="stable")
            d_ord, d_idx = ps[dest][o], dest[o]
            for i in orig:
                J[i] = _vizinhos_1(ps[i], d_ord, d_idx, M, caliper)[0]
    return J


def vizinhos_mesmo_modo(ps, W, Jv=4, estratos=None, grupos=None):
    """J vizinhos do mesmo modo (sem a própria unidade), no mesmo estrato; com `grupos`, só de outros grupos (sem estratos)."""
    ps = np.asarray(ps, float)
    W = np.asarray(W, int)
    n = len(ps)
    out = [np.zeros(0, int)] * n
    if grupos is not None:
        g = pd.factorize(pd.Series(grupos).astype(str))[0]
        for t in (0, 1):
            ix = np.where(W == t)[0]
            o = np.argsort(ps[ix], kind="stable")
            d_ord, d_idx = ps[ix][o], ix[o]
            for i in ix:
                gi = g[i]
                out[i] = _vizinhos_1(ps[i], d_ord, d_idx, Jv, excluir=lambda j, gi=gi: g[j] == gi)[0]
        return out
    est = np.zeros(n, int) if estratos is None else pd.factorize(pd.Series(estratos).astype(str))[0]
    for s in np.unique(est):
        for t in (0, 1):
            ix = np.where((est == s) & (W == t))[0]
            if len(ix) < 2:
                continue
            o = np.argsort(ps[ix], kind="stable")
            d_ord, d_idx = ps[ix][o], ix[o]
            for i in ix:
                out[i] = _vizinhos_1(ps[i], d_ord, d_idx, Jv, excluir=lambda j, i=i: j == i)[0]
    # unidades sozinhas no estrato e modo: vizinhos globais do mesmo modo
    falta = [i for i in range(n) if len(out[i]) == 0]
    if falta:
        for t in (0, 1):
            ix = np.where(W == t)[0]
            o = np.argsort(ps[ix], kind="stable")
            d_ord, d_idx = ps[ix][o], ix[o]
            for i in [f for f in falta if W[f] == t]:
                out[i] = _vizinhos_1(ps[i], d_ord, d_idx, Jv, excluir=lambda j, i=i: j == i)[0]
    return out


def estimar(Y, W, Jm, a=None, sig_viz=None, sig_viz_cl=None, grupos=None):
    """Estimandos e variâncias. Jm: vizinhos do outro modo (vazio = sem par: a unidade sai do estimando)."""
    Y = np.asarray(Y, float)
    W = np.asarray(W, int)
    n = len(Y)
    tem = np.array([len(j) > 0 for j in Jm])
    a0 = np.ones(n) if a is None else np.asarray(a, float)
    yh = np.array([Y[j].mean() if len(j) else np.nan for j in Jm])           # potencial imputado
    tau_i = np.where(W == 1, Y - yh, yh - Y)
    sig2 = None
    if sig_viz is not None:
        sig2 = np.array([(len(v) / (len(v) + 1)) * (Y[i] - Y[v].mean()) ** 2 if len(v) else np.nan
                         for i, v in enumerate(sig_viz)])
    eps_cl = None
    if sig_viz_cl is not None:
        eps_cl = np.array([(Y[i] - Y[v].mean()) if len(v) else np.nan for i, v in enumerate(sig_viz_cl)])
        sig2_cl = np.array([(len(v) / (len(v) + 1)) * e ** 2 if len(v) else np.nan for v, e in zip(sig_viz_cl, eps_cl)])
    res = {}
    for est, pop in (("efeito_medio_eq7", tem), ("efeito_nas_AF", tem & (W == 1)), ("efeito_nas_A", tem & (W == 0))):
        if pop.sum() == 0:
            continue
        a = np.where(pop, a0, 0.0)
        a = a / a.sum()
        tau = float(np.sum(a[pop] * tau_i[pop]))
        c = np.where(W == 1, 1.0, -1.0) * a                       # termo próprio
        nu = np.zeros(n)
        for l in np.where(pop)[0]:
            jl = Jm[l]
            if len(jl) == 0:
                continue
            k = len(jl)
            # l AF: −a_l/k para cada A casado; l A: +a_l/k para cada AF casado
            c[jl] += (-1.0 if W[l] == 1 else 1.0) * a[l] / k
            nu[jl] += a[l] ** 2 / k ** 2
        o = {"est": tau, "unidades": int(pop.sum()), "unidades_AF": int((pop & (W == 1)).sum()),
             "unidades_A": int((pop & (W == 0)).sum()), "sem_par": int((~tem).sum())}
        if sig2 is not None:
            s2 = np.nan_to_num(sig2)
            v_cond = float(np.sum(c ** 2 * s2))
            v_pop = float(np.sum(a[pop] ** 2 * (tau_i[pop] - tau) ** 2) + np.sum(s2 * (c ** 2 - a ** 2 - nu)))
            o.update({"ep_AI_populacional": float(np.sqrt(max(v_pop, 0))), "ep_AI_condicional": float(np.sqrt(v_cond))})
        if eps_cl is not None and grupos is not None:
            g = pd.factorize(pd.Series(grupos).astype(str))[0]
            e = np.nan_to_num(eps_cl)
            soma = pd.Series(c * e).groupby(g).sum().to_numpy()
            v_cl = float(np.sum(soma ** 2) - np.sum((c * e) ** 2) + np.sum(c ** 2 * np.nan_to_num(sig2_cl)))
            o["ep_agrupado_adaptado"] = float(np.sqrt(max(v_cl, 0)))
            o["v_agrupada_negativa"] = bool(v_cl < 0)
        # concentração dos pesos de casamento
        ab = np.abs(c)
        for lado, mk in (("AF", W == 1), ("A", W == 0)):
            x = ab[mk & (ab > 0)]
            if len(x):
                o[f"ess_{lado}"] = float(x.sum() ** 2 / (x ** 2).sum())
                o[f"peso_max_{lado}"] = float(x.max() / x.sum())
                o[f"peso_top1pct_{lado}"] = float(np.sort(x)[::-1][:max(1, int(np.ceil(.01 * len(x))))].sum() / x.sum())
                o[f"usadas_{lado}"] = int(len(x))
        o["c"] = c
        res[est] = o
    res["_tau_i"] = tau_i
    res["_tem_par"] = tem
    res["_tamanho_J"] = np.array([len(j) for j in Jm])
    return res
