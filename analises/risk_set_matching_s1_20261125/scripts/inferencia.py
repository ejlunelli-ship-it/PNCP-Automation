"""Etapa 14: estimador DiD pareado e inferência CONDICIONAL ao pareamento.

Linhas = (evento e, unidade i, papel T/C), z_ie = s_e · ΔY_i (s_e = +1 adoção, −1 abandono, escala AF − A).
τ_e = z_T − Σ_v w_ev z_v (pesos dos controles disponíveis renormalizados para somar 1); τ̂ = Σ a_e τ_e / Σ a_e.
τ̂ é linear nos z: τ̂ = Σ_r c_r z_r, com Σ_{r∈e} c_r = 0. Resíduo de cada linha: ê_r = z_r − μ̂_cel − τ̂·T_r, onde μ̂_cel é a
média ponderada dos controles da mesma célula (direção × t0 × horizonte). O escore do cluster g (CNPJ) soma TODAS as
participações do órgão, como tratada e como controle, em qualquer evento: S_g = Σ_{r∈g} c_r ê_r, e
V = G/(G−1) Σ_g S_g² (CR1). Isso reconhece eventos repetidos, várias UASGs do mesmo CNPJ e reutilização de
controles. Valor-p de referência t(G−1); valor-p de bootstrap selvagem por cluster (pesos de Webb, hipótese nula
imposta) — também condicional aos pares: o pareamento NÃO é refeito (o bootstrap ingênuo de matching com número
fixo de vizinhos é inconsistente; Abadie e Imbens, 2008). A incerteza da etapa de pareamento não é capturada.
"""
import numpy as np
import pandas as pd
from scipy import stats

WEBB = np.array([-np.sqrt(1.5), -1.0, -np.sqrt(0.5), np.sqrt(0.5), 1.0, np.sqrt(1.5)])


def eventos_tau(linhas):
    """τ_e por evento (renormalizando os pesos dos controles presentes)."""
    T = linhas[linhas.papel == "T"].set_index("id_evento")
    C = linhas[linhas.papel == "C"]
    wsum = C.groupby("id_evento").w.sum()
    zc = (C.w * C.z).groupby(C.id_evento).sum() / wsum
    ids = T.index.intersection(zc.index)
    out = pd.DataFrame({"tau": T.loc[ids, "z"] - zc.loc[ids], "a": T.loc[ids, "a"], "grupo": T.loc[ids, "grupo"],
                        "cnpj": T.loc[ids, "cnpj"], "uasg": T.loc[ids, "uasg"], "celula": T.loc[ids, "celula"],
                        "n_controles": C.groupby("id_evento").size().loc[ids]})
    return out


def coeficientes(linhas, ev, filtro_grupo=None):
    """c_r para o estimador Σ a_e τ_e / Σ a_e restrito aos eventos `ev` (opcionalmente a um grupo)."""
    e = ev if filtro_grupo is None else ev[ev.grupo == filtro_grupo]
    A = e.a.sum()
    l = linhas[linhas.id_evento.isin(e.index)].copy()
    wsum = l[l.papel == "C"].groupby("id_evento").w.sum()
    a = l.id_evento.map(e.a) / A
    l["c"] = np.where(l.papel == "T", a, -a * l.w / l.id_evento.map(wsum))
    return l, float((e.a * e.tau).sum() / A)


def _residuos(l, tau_linha):
    C = l[l.papel == "C"]
    mu = (C.c.abs() * C.z).groupby(C.celula).sum() / C.c.abs().groupby(C.celula).sum()
    return l.z - l.celula.map(mu) - tau_linha * (l.papel == "T")


def contraste(linhas, filtro_grupo=None, B=9999, semente=0, margem=5.0, alfa=0.05, ev=None, tau_por_grupo=False):
    ev = eventos_tau(linhas) if ev is None else ev
    if filtro_grupo is not None:
        ev = ev[ev.grupo == filtro_grupo]
    if len(ev) == 0:
        return {"eventos": 0}
    l, tau = coeficientes(linhas, ev)
    if tau_por_grupo:
        tg = ev.groupby("grupo").apply(lambda g: (g.a * g.tau).sum() / g.a.sum(), include_groups=False)
        tl = l.id_evento.map(ev.grupo).map(tg)
    else:
        tl = tau
    l["e"] = _residuos(l, tl)
    return _inferir(l, tau, ev, B, semente, margem, alfa)


def diferenca(linhas, g1, g2, B=9999, semente=0, alfa=0.05):
    """τ̂(g1) − τ̂(g2) (ex.: simetria adoção − abandono na escala AF), mesma variância por cluster."""
    ev = eventos_tau(linhas)
    if (ev.grupo == g1).sum() == 0 or (ev.grupo == g2).sum() == 0:
        return {"eventos": 0}
    l1, t1 = coeficientes(linhas, ev, g1)
    l2, t2 = coeficientes(linhas, ev, g2)
    l2 = l2.assign(c=-l2.c)
    l = pd.concat([l1, l2])
    tg = {g1: t1, g2: t2}
    l["e"] = _residuos(l, l.id_evento.map(ev.grupo).map(tg))
    return _inferir(l, t1 - t2, ev[ev.grupo.isin([g1, g2])], B, semente, None, alfa)


def _inferir(l, tau, ev, B, semente, margem, alfa):
    S = (l.c * l.e).groupby(l.cnpj).sum()
    G = int((l.groupby("cnpj").c.apply(lambda s: np.abs(s).sum()) > 0).sum())
    if G < 2:
        return {"beta_lp": tau, "eventos": int(len(ev)), "clusters": G}
    V = G / (G - 1) * float(np.sum(S.to_numpy() ** 2))
    se = np.sqrt(V)
    df = G - 1
    tcrit = stats.t.ppf(1 - alfa / 2, df)
    tstat = tau / se if se > 0 else np.nan
    p = float(2 * stats.t.sf(abs(tstat), df)) if se > 0 else np.nan
    # bootstrap selvagem por cluster com nulidade imposta (resíduos restritos ê^R = z − μ̂)
    p_wcr = np.nan
    if B and se > 0:
        lr = l.copy()
        C = lr[lr.papel == "C"]
        mu = (C.c.abs() * C.z).groupby(C.celula).sum() / C.c.abs().groupby(C.celula).sum()
        lr["eR"] = lr.z - lr.celula.map(mu)
        SR = (lr.c * lr.eR).groupby(lr.cnpj).sum()
        CT = (lr.c * (lr.papel == "T")).groupby(lr.cnpj).sum().reindex(SR.index)
        rng = np.random.default_rng(semente)
        v = rng.choice(WEBB, size=(B, len(SR)))
        tau_b = v @ SR.to_numpy()
        Sb = v * SR.to_numpy()[None, :] - tau_b[:, None] * CT.to_numpy()[None, :]
        se_b = np.sqrt(G / (G - 1) * (Sb ** 2).sum(1))
        t_b = tau_b / se_b
        p_wcr = float(np.mean(np.abs(t_b) >= abs(tstat)))
    # pesos por cluster (contribuição absoluta) e órgãos efetivos
    sh = (l.c.abs()).groupby(l.cnpj).sum()
    sh = sh / sh.sum()
    ev_sh = ev.groupby("cnpj").a.sum() / ev.a.sum()
    out = {"beta_lp": float(tau), "ep": float(se), "ic95_inf": float(tau - tcrit * se), "ic95_sup": float(tau + tcrit * se),
           "p_t": p, "gl": df, "p_wcr_webb": p_wcr, "B_wcr": int(B), "eventos": int(len(ev)), "clusters": G,
           "n_efetivo_cnpjs_peso_total": float(1 / np.sum(sh ** 2)), "n_efetivo_cnpjs_tratados": float(1 / np.sum(ev_sh ** 2)),
           "share_top1_cnpj_tratado": float(ev_sh.max()), "share_top5_cnpj_tratado": float(ev_sh.sort_values(ascending=False).head(5).sum()),
           "uasgs_tratadas": int(ev.uasg.nunique()), "cnpjs_tratados": int(ev.cnpj.nunique()),
           "controles_distintos": int(l[l.papel == "C"].uasg.nunique()), "cnpjs_controle": int(l[l.papel == "C"].cnpj.nunique()),
           "mde_80": float((stats.t.ppf(1 - alfa / 2, df) + stats.t.ppf(0.80, df)) * se), "pct_exato": float(100 * np.expm1(tau / 100))}
    if margem is not None:
        t90 = stats.t.ppf(1 - alfa, df)
        p_inf = stats.t.sf((tau + margem) / se, df)      # H0: τ <= −m
        p_sup = stats.t.cdf((tau - margem) / se, df)     # H0: τ >= +m
        out.update({"ic90_inf": float(tau - t90 * se), "ic90_sup": float(tau + t90 * se), "margem_equivalencia": margem,
                    "p_tost": float(max(p_inf, p_sup)), "equivalente_5pct": bool(max(p_inf, p_sup) < alfa),
                    "poder_contra_margem": float(stats.norm.cdf(margem / se - stats.norm.ppf(1 - alfa / 2))
                                                + stats.norm.cdf(-margem / se - stats.norm.ppf(1 - alfa / 2)))})
    return out


def remover_cluster(linhas, campo, valor):
    """Exclui TODAS as participações (tratada e controle) de um órgão/UASG; eventos sem tratada ou sem controle saem."""
    l = linhas[linhas[campo] != valor]
    ids_T = set(l.loc[l.papel == "T", "id_evento"])
    ids_C = set(l.loc[l.papel == "C", "id_evento"])
    return l[l.id_evento.isin(ids_T & ids_C)]


def jackknife(linhas, campo="cnpj", alvo=None):
    ev = eventos_tau(linhas)
    base = float((ev.a * ev.tau).sum() / ev.a.sum())
    valores = sorted(set(linhas[campo]) if alvo is None else alvo)
    res = []
    for v in valores:
        l = remover_cluster(linhas, campo, v)
        e = eventos_tau(l)
        if len(e) == 0:
            continue
        res.append({campo: v, "beta_sem": float((e.a * e.tau).sum() / e.a.sum()), "eventos_sem": int(len(e)),
                    "eventos_perdidos": int(len(ev) - len(e)), "mudanca": float((e.a * e.tau).sum() / e.a.sum() - base)})
    return base, pd.DataFrame(res)


def holm(p):
    p = np.asarray(p, float)
    o = np.argsort(p)
    m = len(p)
    adj = np.empty(m)
    run = 0.0
    for k, i in enumerate(o):
        run = max(run, (m - k) * p[i])
        adj[i] = min(1.0, run)
    return adj
