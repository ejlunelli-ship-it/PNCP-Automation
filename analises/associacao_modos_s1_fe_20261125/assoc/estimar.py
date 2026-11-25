"""Estimação com efeitos fixos de alta dimensão (projeções alternadas com verificação de convergência) e
diagnósticos de identificação e inferência.

y = 100 ln p = β AF + FE + γ ln q + ε. β por FWL; FE absorvidos sem matrizes de dummies. Singletons removidos
iterativamente (não identificam nada e distorcem graus de liberdade).

Inferência (sempre condicional; associação, não causalidade):
- CR1 por CNPJ, t(G−1) — referência;
- bootstrap selvagem restrito por CNPJ (WCR, pesos de Webb, H0: β = 0) e IC WCU percentil-t;
- CGM bidirecional CNPJ + produto; CR1 por UF (27 clusters) como sensibilidade;
- número efetivo de clusters de Carter, Schnepel e Steigerwald (2017): ρ = 0 (≡ 1/Σ s_g², s_g = participação
  do cluster em Σ x̃²) e ρ = 1 ((Σ_g x̃)², indefinido quando o FE está aninhado no cluster).
Contribuição de cada CNPJ/UF à variação identificadora: participação em Σ w x̃², com x̃ = AF residualizado nos FE
e em ln q.
"""
import numpy as np
import pandas as pd
from scipy import stats

from em.inferencia import codificar, remover_singletons, vcov_cluster, wild_cluster

CAMPOS = {"uf_prod_tri": ("uf", "produto", "tri"), "cnpj": ("cnpj",), "cnpj_prod": ("cnpj", "produto"),
          "cnpj_prod_tri": ("cnpj", "produto", "tri"), "uasg": ("uasg",), "uasg_prod_tri": ("uasg", "produto", "tri"),
          "uf_tri": ("uf", "tri"), "prod_tri": ("produto", "tri"), "uf": ("uf",), "produto": ("produto",)}


def codigos(d, nomes):
    return {n: codificar(*[d[c].to_numpy() for c in CAMPOS[n]]) for n in nomes}


def _medias_residuais(M, fes, w):
    r = 0.0
    for f in fes:
        sw = np.bincount(f, weights=w, minlength=f.max() + 1)
        for j in range(M.shape[1]):
            g = np.bincount(f, weights=w * M[:, j], minlength=sw.size) / np.where(sw > 0, sw, 1)
            r = max(r, float(np.abs(g).max()))
    return r


def absorver_map(M, fes, w, tol=1e-9, max_iter=50000):
    """Projeções alternadas (MAP) ponderadas; retorna (M residual, diagnóstico)."""
    M = np.array(M, dtype=float, copy=True)
    somas = [np.bincount(f, weights=w, minlength=f.max() + 1) for f in fes]
    it, delta = 0, 0.0
    for it in range(1, max_iter + 1):
        delta = 0.0
        for f, sw in zip(fes, somas):
            for j in range(M.shape[1]):
                g = np.bincount(f, weights=w * M[:, j], minlength=sw.size) / np.where(sw > 0, sw, 1)
                M[:, j] -= g[f]
                delta = max(delta, float(np.abs(g).max()))
        if len(fes) == 1:
            delta = 0.0
            break
        if delta < tol:
            break
    return M, {"metodo": "MAP", "iteracoes": it, "delta_final": delta, "convergiu": bool(delta < tol),
               "max_media_residual_grupos": _medias_residuais(M, fes, w)}


def absorver(M, fes, w, tol=1e-9, max_iter=50000):
    """Um FE: subtração exata das médias. Vários FE: LSMR esparso (mínimos quadrados nos dummies, sem densificar)
    seguido de polimento por MAP até a variação máxima < tol; a verificação final é a maior média ponderada
    residual em qualquer grupo de qualquer FE."""
    if len(fes) == 1:
        return absorver_map(M, fes, w, tol, max_iter)
    from scipy import sparse
    from scipy.sparse.linalg import lsmr
    n = M.shape[0]
    blocos, off = [], 0
    for f in fes:
        G = int(f.max()) + 1
        blocos.append(sparse.csr_matrix((np.ones(n), (np.arange(n), f)), shape=(n, G)))
    D = sparse.hstack(blocos, format="csr")
    sw = np.sqrt(w)
    A = sparse.diags(sw) @ D
    R = np.empty_like(np.asarray(M, float))
    its = []
    for j in range(M.shape[1]):
        r = lsmr(A, sw * M[:, j], atol=1e-14, btol=1e-14, maxiter=20000)
        R[:, j] = M[:, j] - D @ r[0]
        its.append(int(r[2]))
    R, pol = absorver_map(R, fes, w, tol, max_iter)
    return R, {"metodo": "LSMR + MAP", "iteracoes": int(max(its)), "iteracoes_polimento": pol["iteracoes"],
               "delta_final": pol["delta_final"], "convergiu": pol["convergiu"], "max_media_residual_grupos": pol["max_media_residual_grupos"]}


def _neff(sh):
    sh = sh[sh > 0]
    return float(1 / np.sum(sh ** 2)) if sh.size else np.nan


def css_rho1(x1, cl, w):
    s = np.bincount(cl, weights=w * x1, minlength=cl.max() + 1)
    gam = s ** 2
    if gam.sum() <= 1e-12 * max(1.0, float(np.sum(w * x1 ** 2))):
        return np.nan
    G = np.unique(cl).size
    gam = gam[np.unique(cl)]
    Gam = np.mean((gam - gam.mean()) ** 2) / gam.mean() ** 2
    return float(G / (1 + Gam))


def celulas_dois_modos(sub, celula):
    cod = codificar(*[sub[c].to_numpy() for c in CAMPOS[celula]])
    s = pd.DataFrame({"g": cod, "af": sub.af.to_numpy(), "chave": sub.chave.to_numpy(), "cnpj": sub.cnpj.to_numpy()})
    v = s.groupby("g").af.agg(["min", "max"])
    var = v.index[v["min"] != v["max"]]
    sv = s[s.g.isin(var)]
    cc = sv.drop_duplicates("g").cnpj.value_counts(normalize=True)
    return {"celula": celula, "celulas": int(len(v)), "celulas_com_A_e_AF": int(len(var)),
            "obs_em_celulas_com_A_e_AF": int(len(sv)), "compras_em_celulas_com_A_e_AF": int(sv.chave.nunique()),
            "obs_em_celulas_de_um_so_modo": int(len(s) - len(sv)),
            "compras_so_em_celulas_de_um_so_modo": int(s.chave.nunique() - sv.chave.nunique()),
            "cnpjs_com_celulas_mistas": int(sv.cnpj.nunique()), "n_efetivo_cnpjs_celulas": float(1 / np.sum(cc ** 2)) if len(cc) else np.nan,
            "share_top1_cnpj_celulas": float(cc.iloc[0]) if len(cc) else np.nan, "top1_cnpj_celulas": cc.index[0] if len(cc) else None}


def estimar(d, fes_nomes, com_q=True, peso=None, mascara=None, cod=None, B=0, semente=0, tol=1e-9, max_iter=50000,
            diagnosticos=True, celula=None):
    """Estima um modelo. d: DataFrame compra × produto. Retorna dict (sem os vetores grandes salvo `_sub`)."""
    m = np.ones(len(d), bool) if mascara is None else np.asarray(mascara, bool).copy()
    if com_q:
        m &= d.lnq.notna().to_numpy()
    cod = cod or codigos(d, set(fes_nomes) | {"cnpj", "uf", "cnpj_prod"})
    fes0 = [cod[f][m] for f in fes_nomes]
    keep = remover_singletons(fes0)
    idx = np.flatnonzero(m)[keep]
    sub = d.iloc[idx]
    fes = [codificar(f[keep]) for f in fes0]
    w = np.ones(len(sub)) if peso is None else np.asarray(peso, float)[idx]
    cols = [sub.y.to_numpy(float), sub.af.to_numpy(float)] + ([sub.lnq.to_numpy(float)] if com_q else [])
    D, conv = absorver(np.column_stack(cols), fes, w, tol, max_iter)
    yd, Xd = D[:, 0], D[:, 1:]
    XtX = (Xd * w[:, None]).T @ Xd
    b = np.linalg.pinv(XtX) @ ((Xd * w[:, None]).T @ yd)
    e = yd - Xd @ b
    cl = codificar(sub.cnpj.to_numpy())
    V, G = vcov_cluster(Xd, e, cl, w)
    se = float(np.sqrt(max(V[0, 0], 0)))
    beta = float(b[0])
    tc = stats.t.ppf(0.975, G - 1)
    x1 = Xd[:, 0].copy()
    if Xd.shape[1] > 1:
        Z = Xd[:, 1:]
        x1 -= Z @ (np.linalg.pinv((Z * w[:, None]).T @ Z) @ ((Z * w[:, None]).T @ x1))
    var_id = float(np.sum(w * x1 ** 2))
    out = {"fe": "+".join(fes_nomes), "com_lnq": com_q, "peso": "compra" if peso is not None else "observação",
           "beta_lp": beta, "pct_exato": float(100 * np.expm1(beta / 100)), "ep_cr1_cnpj": se, "ic95_inf": beta - tc * se,
           "ic95_sup": beta + tc * se, "p_cr1": float(2 * stats.t.sf(abs(beta / se), G - 1)) if se > 0 else np.nan,
           "gamma_lnq": float(b[1]) if com_q else None, "clusters_cnpj": int(G),
           "n_antes_singletons": int(m.sum()), "singletons_removidos": int((~keep).sum()), "obs": int(len(sub)),
           "compras": int(sub.chave.nunique()), "produtos": int(sub.produto.nunique()), "uasgs": int(sub.uasg.nunique()),
           "cnpjs": int(sub.cnpj.nunique()), "ufs": int(sub.uf.nunique()), "fracao_af": float(np.average(sub.af, weights=w)),
           "variancia_identificadora": var_id, "variancia_identificadora_relativa": var_id / float(np.sum(w * (sub.af - np.average(sub.af, weights=w)) ** 2)),
           **{f"conv_{k}": v for k, v in conv.items()}}
    if not diagnosticos or var_id <= 0:
        out["_sub_idx"] = idx
        return out
    # contribuições à variação identificadora (CNPJ e UF)
    for nome, codg in (("cnpj", cl), ("uf", codificar(sub.uf.to_numpy()))):
        sh = np.bincount(codg, weights=w * x1 ** 2, minlength=codg.max() + 1) / var_id
        rot = pd.Series(sub[nome].to_numpy()).groupby(codg).first()
        s = pd.Series(sh, index=rot.reindex(range(len(sh))).to_numpy()).sort_values(ascending=False)
        out[f"n_efetivo_{nome}s"] = _neff(sh)
        out[f"top1_{nome}"] = s.index[0]
        out[f"share_top1_{nome}"] = float(s.iloc[0])
        out[f"share_top5_{nome}"] = float(s.head(5).sum())
        out[f"_contrib_{nome}"] = s
    out["G_css_rho0"] = out["n_efetivo_cnpjs"]
    out["G_css_rho1"] = css_rho1(x1, cl, w)
    # inferência adicional
    if B:
        wb = wild_cluster(yd, Xd, cl, w, B, semente)
        out.update({"p_wcr_webb": wb["p_wcr"], "ic_wcu_inf": wb["ic_wcu_inf"], "ic_wcu_sup": wb["ic_wcu_sup"], "B": wb["B"]})
    V2, G2 = vcov_cluster(Xd, e, (cl, codificar(sub.produto.to_numpy())), w)
    se2 = float(np.sqrt(max(V2[0, 0], 0)))
    out.update({"ep_cgm_cnpj_produto": se2, "p_cgm": float(2 * stats.t.sf(abs(beta / se2), G2 - 1)) if se2 > 0 else np.nan})
    clu = codificar(sub.uf.to_numpy())
    Vu, Gu = vcov_cluster(Xd, e, clu, w)
    seu = float(np.sqrt(max(Vu[0, 0], 0)))
    out.update({"ep_cr1_uf": seu, "p_cr1_uf": float(2 * stats.t.sf(abs(beta / seu), Gu - 1)) if seu > 0 else np.nan, "clusters_uf": int(Gu)})
    if celula:
        out.update({f"cel_{k}": v for k, v in celulas_dois_modos(sub, celula).items()})
    out["_sub_idx"] = idx
    return out


def peso_por_compra(d):
    """Peso igual por compra: cada compra soma 1 entre os seus produtos S1."""
    n = d.groupby("chave").produto.transform("size")
    return (1.0 / n).to_numpy()
