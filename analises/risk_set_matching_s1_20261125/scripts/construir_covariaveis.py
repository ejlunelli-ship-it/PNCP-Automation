"""Etapa 5: covariáveis anteriores ao evento, calculadas SOMENTE a partir de uma visão PainelPre (t < t0).

M0 (institucional): atividade de compras, escala, composição CATMAT, práticas administrativas e histórico de modo,
na janela t0−6..t0−1 (atividade não é preço). M1 = M0 + nível, tendência, dispersão e disponibilidade do índice de
preços SOMENTE em t0−6..t0−3; t0−2 e t0−1 ficam reservados para a falsificação e nunca entram no pareamento.
Número de licitantes NÃO entra (pode responder ao modo de disputa).
"""
import numpy as np
import pandas as pd

from .construir_painel import NAO_OBS

REGIOES = {"N": "AC AP AM PA RO RR TO", "NE": "AL BA CE MA PB PE PI RN SE", "CO": "DF GO MT MS",
           "SE": "ES MG RJ SP", "S": "PR RS SC"}
UF_REGIAO = {uf: r for r, s in REGIOES.items() for uf in s.split()}

M0_CONT = ["log_compras", "log_itens", "freq_trimestral", "log_itens_por_compra", "log_valor_medio_compra",
           "var_log_itens", "log_itens_s1", "logq_s1", "log_produtos_s1", "recorrencia_s1", "log_classes",
           "hhi_classes", "srp", "sigilo", "homologacao", "fracasso", "desercao", "trimestres_no_regime"]
M0_DUMMIES_PREFIXOS = ("poder_", "regiao_")
M1_PRECO = ["y_nivel", "y_tendencia", "y_dp", "y_trimestres"]


def _razao(num, den):
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(den > 0, num / np.where(den > 0, den, 1), np.nan)


def completude(pre, idx, form, falsif, min_form, ycol="Yc"):
    """Índice observado em t−1 e t−2 e em >= min_form trimestres de formação (regra idêntica p/ tratadas e controles)."""
    Yf = pre.janela(ycol, form[0], form[-1])[idx]
    Yp = pre.janela(ycol, falsif[0], falsif[-1])[idx]
    n_form = np.isfinite(Yf).sum(1)
    ok_fals = np.isfinite(Yp).all(1)
    return ok_fals & (n_form >= min_form), n_form, ok_fals


def calcular(pre, idx, origem, form, falsif, classes_top, ycol="Yc"):
    """Covariáveis das unidades `idx` (índices de linha do painel) na visão `pre`. Janela de atividade: form[0]..−1."""
    w0 = form[0]
    J = lambda n: pre.janela(n, w0, -1)[idx]
    nc, ni = J("n_compras"), J("it_n")
    out = pd.DataFrame({"u": idx})
    out["log_compras"] = np.log1p(nc.sum(1))
    out["log_itens"] = np.log1p(ni.sum(1))
    out["freq_trimestral"] = (nc > 0).mean(1)
    out["log_itens_por_compra"] = np.log((ni.sum(1) + 1) / (nc.sum(1) + 1))
    out["log_valor_medio_compra"] = _razao(J("lv_soma").sum(1), J("lv_n").sum(1))
    with np.errstate(invalid="ignore"):
        out["var_log_itens"] = np.nanstd(np.log1p(ni), axis=1)
    out["log_itens_s1"] = np.log1p(J("n_itens_s1").sum(1))
    out["logq_s1"] = _razao(J("logq_soma").sum(1), J("logq_n").sum(1))
    out["srp"] = _razao(J("n_srp").sum(1), nc.sum(1))
    out["sigilo"] = _razao(J("it_sig").sum(1), ni.sum(1))
    dec = J("it_decid").sum(1)
    out["homologacao"] = _razao(J("it_hom").sum(1), dec)
    out["fracasso"] = _razao(J("it_frac").sum(1), dec)
    out["desercao"] = _razao(J("it_des").sum(1), dec)
    st = pre.janela("status", w0, -1)[idx]
    out["trimestres_no_regime"] = (st == origem).sum(1)
    # composição de produtos S1 licitados e classes CATMAT (todas as compras) na janela
    t_lo = pre.t0 + w0
    pl = pre.longo["produtos_licitados"]
    pl = pl[(pl.t >= t_lo) & pl.u.isin(idx)]
    nprod = pl.groupby("u").produto.nunique()
    rec = pl.groupby(["u", "produto"]).t.nunique().gt(1).groupby("u").mean()
    out["log_produtos_s1"] = np.log1p(out.u.map(nprod).fillna(0).to_numpy())
    out["recorrencia_s1"] = out.u.map(rec).to_numpy()
    cl = pre.longo["classes"]
    cl = cl[(cl.t >= t_lo) & cl.u.isin(idx)]
    tot = cl.groupby("u").n.sum()
    sh = cl.groupby(["u", "classe"]).n.sum().div(tot, level="u")
    hhi = (sh ** 2).groupby("u").sum()
    out["log_classes"] = np.log1p(out.u.map(cl.groupby("u").classe.nunique()).fillna(0).to_numpy())
    out["hhi_classes"] = out.u.map(hhi).to_numpy()
    shw = sh.unstack(fill_value=0.0)
    for k in classes_top:
        out[f"classe_{int(k)}"] = out.u.map(shw[k]).fillna(0).to_numpy() if k in shw.columns else 0.0
    out["classe_outras"] = 1 - out[[f"classe_{int(k)}" for k in classes_top]].sum(1)
    # institucionais
    poder = pre.attr["poder"][idx]
    uf = pre.attr["uf"][idx]
    out["esfera"] = pre.attr["esfera"][idx]
    out["cnpj"] = pre.attr["cnpj"][idx]
    for p in ("E", "L", "J", "N"):
        out[f"poder_{p}"] = (poder == p).astype(float)
    for r in REGIOES:
        out[f"regiao_{r}"] = np.array([UF_REGIAO.get(x, "") == r for x in uf], dtype=float)
    # preços: SOMENTE trimestres de formação
    Yf = pre.janela(ycol, form[0], form[-1])[idx]
    x = np.arange(Yf.shape[1], dtype=float)
    ok = np.isfinite(Yf)
    n = ok.sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        m = np.where(n > 0, np.nansum(Yf, 1) / np.maximum(n, 1), np.nan)
        xm = np.where(n > 0, (ok * x).sum(1) / np.maximum(n, 1), np.nan)
        sxx = (ok * (x - xm[:, None]) ** 2).sum(1)
        sxy = np.nansum(np.where(ok, (x - xm[:, None]) * (Yf - m[:, None]), 0), 1)
        out["y_nivel"] = m
        out["y_tendencia"] = np.where((n >= 2) & (sxx > 0), sxy / np.where(sxx > 0, sxx, 1), np.nan)
        out["y_dp"] = np.where(n >= 2, np.sqrt(np.nansum(np.where(ok, (Yf - m[:, None]) ** 2, 0), 1) / np.maximum(n - 1, 1)), np.nan)
    out["y_trimestres"] = n.astype(float)
    return out


def colunas_m0(df):
    return M0_CONT + [c for c in df.columns if c.startswith("classe_")] + [c for c in df.columns if c.startswith(M0_DUMMIES_PREFIXOS)]


def colunas_m1(df):
    return colunas_m0(df) + M1_PRECO


def imputar(df, cols):
    """Razões sem denominador (ex.: nenhum item decidido) recebem a média da população de risco; sem indicador."""
    d = df.copy()
    for c in cols:
        if d[c].isna().any():
            d[c] = d[c].fillna(d[c].mean() if d[c].notna().any() else 0.0)
    return d
