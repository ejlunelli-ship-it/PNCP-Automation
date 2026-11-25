"""Etapa 10: balanceamento antes e depois do pareamento (Fase I, só covariáveis pré-evento).

Antes: tratadas × todas as candidatas do conjunto de risco de cada evento (cada evento com peso total 1 nos dois
grupos). Depois: tratadas × controles pareados (pesos w_ev / E). Denominador das diferenças padronizadas: desvio
das amostras ANTES do pareamento (fixo entre antes e depois). Referência |SMD| < 0,10, que não prova causalidade.
"""
import numpy as np
import pandas as pd

from . import construir_covariaveis as cv


def _wmean(x, w):
    return float(np.sum(w * x) / np.sum(w))


def _wvar(x, w):
    m = _wmean(x, w)
    return float(np.sum(w * (x - m) ** 2) / np.sum(w))


def _wquant(x, w, q):
    o = np.argsort(x)
    x, w = x[o], w[o]
    cw = np.cumsum(w) / w.sum()
    return float(x[np.searchsorted(cw, q)])


def _ks(x1, w1, x0, w0):
    g = np.unique(np.concatenate([x1, x0]))
    F1 = np.array([w1[x1 <= v].sum() for v in g]) / w1.sum()
    F0 = np.array([w0[x0 <= v].sum() for v in g]) / w0.sum()
    return float(np.max(np.abs(F1 - F0)))


def smd(xt, wt, xc, wc, sd_ref):
    return (_wmean(xt, wt) - _wmean(xc, wc)) / sd_ref if sd_ref > 0 else np.nan


def amostras(pop, eventos, cand_por_evento, pares):
    """Linhas de covariáveis com pesos para tratadas, candidatas (antes) e controles (depois)."""
    key = pop.set_index(["u", "t0"])
    E = len(eventos)
    T, C0, C1 = [], [], []
    ev_ok = set(pares.id_evento) if len(pares) else set()
    for e in eventos.itertuples():
        T.append(((e.u, e.t0), 1.0, e.id_evento in ev_ok))
        cand = cand_por_evento.get(e.id_evento, [])
        for v in cand:
            C0.append(((int(v), e.t0), 1.0 / len(cand)))
    for r in pares.itertuples():
        C1.append(((r.u_controle, r.t0), r.peso))
    return key, T, C0, C1


def tabela(pop, eventos, cand_por_evento, pares, cols):
    pop = cv.imputar(pop, cols)
    key, T, C0, C1 = amostras(pop, eventos, cand_por_evento, pares)
    def X(lista):
        if not lista:
            return np.zeros((0, len(cols))), np.zeros(0)
        idx = [k for k, *_ in lista]
        return key.loc[idx, cols].to_numpy(float), np.array([w for _, w, *_ in lista])
    Xt, wt = X(T)
    Xt_m, wt_m = X([t for t in T if t[2]])
    Xc0, wc0 = X(C0)
    Xc1, wc1 = X(C1)
    linhas = []
    for j, c in enumerate(cols):
        if not len(Xc0) or not len(Xt):
            continue
        sd = np.sqrt((_wvar(Xt[:, j], wt) + _wvar(Xc0[:, j], wc0)) / 2)
        l = {"covariavel": c, "media_tratadas": _wmean(Xt[:, j], wt), "media_candidatas": _wmean(Xc0[:, j], wc0),
             "smd_antes": smd(Xt[:, j], wt, Xc0[:, j], wc0, sd), "dp_referencia": sd,
             "dif_mediana_antes": _wquant(Xt[:, j], wt, .5) - _wquant(Xc0[:, j], wc0, .5),
             "razao_var_antes": _wvar(Xt[:, j], wt) / _wvar(Xc0[:, j], wc0) if _wvar(Xc0[:, j], wc0) > 0 else np.nan,
             "ks_antes": _ks(Xt[:, j], wt, Xc0[:, j], wc0)}
        if len(Xc1) and len(Xt_m):
            l.update({"media_tratadas_pareadas": _wmean(Xt_m[:, j], wt_m), "media_controles": _wmean(Xc1[:, j], wc1),
                      "smd_depois": smd(Xt_m[:, j], wt_m, Xc1[:, j], wc1, sd),
                      "dif_mediana_depois": _wquant(Xt_m[:, j], wt_m, .5) - _wquant(Xc1[:, j], wc1, .5),
                      "razao_var_depois": _wvar(Xt_m[:, j], wt_m) / _wvar(Xc1[:, j], wc1) if _wvar(Xc1[:, j], wc1) > 0 else np.nan,
                      "ks_depois": _ks(Xt_m[:, j], wt_m, Xc1[:, j], wc1)})
            l["desbalanceada_depois"] = bool(abs(l["smd_depois"]) >= 0.10) if np.isfinite(l["smd_depois"]) else None
        linhas.append(l)
    return pd.DataFrame(linhas)


def balanco_evento(pop, pares, cols, sd_ref):
    """Média de |x_u − Σ w x_v| / dp_ref nas covariáveis contínuas M0, por evento."""
    pop = cv.imputar(pop, cols)
    key = pop.set_index(["u", "t0"])
    out = {}
    for ide, g in pares.groupby("id_evento"):
        u, t0 = int(g.u_tratada.iat[0]), int(g.t0.iat[0])
        xu = key.loc[(u, t0), cols].to_numpy(float)
        xc = key.loc[list(zip(g.u_controle, g.t0)), cols].to_numpy(float)
        dif = np.abs(xu - (g.peso.to_numpy()[:, None] * xc).sum(0)) / np.where(sd_ref > 0, sd_ref, np.nan)
        out[ide] = float(np.nanmean(dif))
    return out


def concentracao(pares):
    """Reutilização de controles, número efetivo de controles e de órgãos (pesos de controle agregados)."""
    if not len(pares):
        return {}
    E = pares.id_evento.nunique()
    wv = pares.assign(w=pares.peso / E).groupby("uasg_controle").w.sum()
    wg = pares.assign(w=pares.peso / E).groupby("cnpj_controle").w.sum()
    reuso = pares.groupby("uasg_controle").id_evento.nunique()
    tg = pares.drop_duplicates("id_evento").groupby("cnpj_tratada").size() / E
    return {"eventos": int(E), "pares": int(len(pares)), "controles_distintos": int(pares.uasg_controle.nunique()),
            "cnpjs_controle_distintos": int(pares.cnpj_controle.nunique()),
            "reuso_max": int(reuso.max()), "reuso_medio": float(reuso.mean()),
            "controles_usados_em_mais_de_um_evento": int((reuso > 1).sum()),
            "n_efetivo_controles": float(1 / np.sum(wv ** 2)), "n_efetivo_cnpjs_controle": float(1 / np.sum(wg ** 2)),
            "n_efetivo_cnpjs_tratados": float(1 / np.sum(tg ** 2)), "share_top1_cnpj_tratado": float(tg.max()),
            "share_top5_cnpj_tratado": float(tg.sort_values(ascending=False).head(5).sum()),
            "controles_por_evento_medio": float(pares.groupby("id_evento").size().mean())}
