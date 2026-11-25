"""Referências leave-one-UASG-out por célula produto × trimestre de abertura (protocolo §5–6).

Para cada item i da UASG u na célula c: todos os itens de u saem da célula antes de qualquer cálculo
(contagem, ordenação, apara, mediana). Mínimos: 5 itens de ≥ 3 outras UASGs (iguais para todas as variantes).

A1 geométrica dos itens · A2 aritmética · A3 mediana · A4 aritmética aparada (floor(0,1n) por cauda, n ≥ 10)
A5 geométrica aparada · B1–B9: estatística dentro da UASG comparadora (aritmética, geométrica, mediana) × entre
UASGs (aritmética, geométrica, mediana), na ordem B1=(arit, arit), B2=(arit, geo) [= G anterior], B3=(arit, med),
B4=(geo, arit), B5=(geo, geo), B6=(geo, med), B7=(med, arit), B8=(med, geo), B9=(med, med).
EST_A1: A1 só com UASGs comparadoras estáveis (contaminação). SD: desvio-padrão dos log-preços das outras UASGs.
Índice: Y_k = 100 [ln P − ln R_k] (log-pontos).
"""
import numpy as np
import pandas as pd

from .inferencia import codificar

VARIANTES = ["A1", "A2", "A3", "A4", "A5", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9"]


def _aparada(x_ord, frac, nmin):
    n = x_ord.size
    k = int(np.floor(frac * n)) if n >= nmin else 0
    return x_ord[k:n - k].mean()


def calcular(pool, min_itens=5, min_uasgs=3, apara=0.10, apara_min_n=10, estaveis=None):
    """pool: DataFrame com colunas produto, tri, uasg, logp (todos > −inf). Retorna DataFrame alinhado ao índice
    de `pool` com log das referências (ref_*), n_outros, k_outros, sd_outros, ref_EST_A1."""
    n = len(pool)
    cell = codificar(pool["produto"].astype(str).to_numpy(), pool["tri"].to_numpy())
    unit = codificar(pool["uasg"].astype(str).to_numpy())
    cu = codificar(cell, unit)
    lp = pool["logp"].to_numpy(dtype=float)
    p = np.exp(lp)
    Gc, Gcu = cell.max() + 1, cu.max() + 1
    # totais por célula e por célula × UASG
    n_c = np.bincount(cell, minlength=Gc).astype(float)
    sl_c = np.bincount(cell, weights=lp, minlength=Gc)
    sp_c = np.bincount(cell, weights=p, minlength=Gc)
    s2_c = np.bincount(cell, weights=lp ** 2, minlength=Gc)
    n_cu = np.bincount(cu, minlength=Gcu).astype(float)
    sl_cu = np.bincount(cu, weights=lp, minlength=Gcu)
    sp_cu = np.bincount(cu, weights=p, minlength=Gcu)
    s2_cu = np.bincount(cu, weights=lp ** 2, minlength=Gcu)
    cell_of_cu = np.zeros(Gcu, dtype=np.int64)
    cell_of_cu[cu] = cell
    k_c = np.bincount(cell_of_cu, minlength=Gc).astype(float)          # UASGs por célula
    # estatísticas dentro da UASG (por célula × UASG)
    cell_tmp = np.zeros(Gcu, dtype=np.int64)
    cell_tmp[cu] = cell
    Mc_tmp = pd.Series(lp).groupby(cell).max().reindex(range(Gc)).to_numpy()
    a_cu = np.bincount(cu, weights=np.exp(lp - Mc_tmp[cell]), minlength=Gcu) / n_cu * np.exp(Mc_tmp[cell_tmp])  # aritmética
    g_cu = sl_cu / n_cu                                                 # log da geométrica
    med_cu = pd.Series(lp).groupby(cu).median().reindex(range(Gcu)).to_numpy()   # log da mediana
    # leave-one-UASG-out SEM subtração: soma das OUTRAS UASGs por somas acumuladas à frente e atrás dentro da célula
    # (evita cancelamento catastrófico quando a focal tem preços muito maiores). Os códigos cu já vêm ordenados por célula.
    lim_cu = np.flatnonzero(np.diff(cell_of_cu)) + 1
    seg = list(zip(np.concatenate([[0], lim_cu]), np.concatenate([lim_cu, [Gcu]])))

    def loo(vals):
        out = np.empty(Gcu)
        for a, b in seg:
            v = vals[a:b]
            pre = np.concatenate([[0.0], np.cumsum(v[:-1])])
            suf = np.concatenate([np.cumsum(v[::-1][:-1])[::-1], [0.0]])
            out[a:b] = pre + suf
        return out
    # escala por célula (máximo do log-preço) para as somas em nível, sem estouro nem perda de precisão
    M_c = pd.Series(lp).groupby(cell).max().reindex(range(Gc)).to_numpy()
    M_cu = M_c[cell_of_cu]
    sps_cu = np.bincount(cu, weights=np.exp(lp - M_c[cell]), minlength=Gcu)
    n_o = loo(n_cu)[cu]
    k_o = loo(np.ones(Gcu))[cu]
    ok = (n_o >= min_itens) & (k_o >= min_uasgs)
    out = pd.DataFrame(index=pool.index)
    out["n_outros"] = n_o
    out["k_outros"] = k_o
    out["ref_ok"] = ok
    with np.errstate(divide="ignore", invalid="ignore"):
        sl_o = loo(sl_cu)[cu]
        out["ref_A1"] = np.where(ok, sl_o / n_o, np.nan)
        out["ref_A2"] = np.where(ok, np.log(loo(sps_cu)[cu] / n_o) + M_c[cell], np.nan)
        m_o = sl_o / n_o
        var_o = (loo(s2_cu)[cu] / n_o - m_o ** 2) * n_o / (n_o - 1)
        out["sd_outros"] = np.where(ok, np.sqrt(np.maximum(var_o, 0)), np.nan)

        def entre(vals):
            return loo(vals)[cu] / k_o
        la = np.log(a_cu)
        out["ref_B1"] = np.where(ok, np.log(entre(np.exp(la - M_cu))) + M_c[cell], np.nan)
        out["ref_B2"] = np.where(ok, entre(la), np.nan)
        out["ref_B4"] = np.where(ok, np.log(entre(np.exp(g_cu - M_cu))) + M_c[cell], np.nan)
        out["ref_B5"] = np.where(ok, entre(g_cu), np.nan)
        out["ref_B7"] = np.where(ok, np.log(entre(np.exp(med_cu - M_cu))) + M_c[cell], np.nan)
        out["ref_B8"] = np.where(ok, entre(med_cu), np.nan)
    # variantes que exigem ordenação dos outros: A3, A4, A5 (itens) e B3, B6, B9 (estatísticas das UASGs)
    ref = {k: np.full(n, np.nan) for k in ("A3", "A4", "A5", "B3", "B6", "B9")}
    ordem = np.lexsort((unit, cell))
    cell_s, cu_s, lp_s = cell[ordem], cu[ordem], lp[ordem]
    ok_s = ok[ordem]
    lim = np.flatnonzero(np.diff(cell_s)) + 1
    ini = np.concatenate([[0], lim])
    fim = np.concatenate([lim, [n]])
    la_cu, lg_cu = np.log(a_cu), g_cu
    for a, b in zip(ini, fim):
        if not ok_s[a:b].any():
            continue
        lps = lp_s[a:b]
        cus = cu_s[a:b]
        ucu, pos_ini = np.unique(cus, return_index=True)
        # estatísticas por UASG da célula (para B3, B6, B9)
        ua, ug, ud = la_cu[ucu], lg_cu[ucu], med_cu[ucu]
        for j, c_u in enumerate(ucu):
            sel = cus == c_u
            if not ok_s[a:b][sel][0]:
                continue
            outros = lps[~sel]
            o = np.sort(outros)
            r_a3 = np.median(o)
            mx = o[-1]
            r_a4 = np.log(_aparada(np.exp(o - mx), apara, apara_min_n)) + mx
            r_a5 = _aparada(o, apara, apara_min_n)
            m = np.ones(ucu.size, dtype=bool)
            m[j] = False
            r_b3, r_b6, r_b9 = np.median(ua[m]), np.median(ug[m]), np.median(ud[m])
            idx = ordem[a:b][sel]
            ref["A3"][idx] = r_a3
            ref["A4"][idx] = r_a4
            ref["A5"][idx] = r_a5
            ref["B3"][idx] = r_b3
            ref["B6"][idx] = r_b6
            ref["B9"][idx] = r_b9
    for k, v in ref.items():
        out[f"ref_{k}"] = v
    # referência só com UASGs estáveis (comparadoras); a focal pode ser qualquer uma
    if estaveis is not None:
        est = pool["uasg"].astype(str).isin(estaveis).to_numpy()
        n_cs = np.bincount(cell, weights=est.astype(float), minlength=Gc)
        sl_cs = np.bincount(cell, weights=lp * est, minlength=Gc)
        n_cus = np.bincount(cu, weights=est.astype(float), minlength=Gcu)
        sl_cus = np.bincount(cu, weights=lp * est, minlength=Gcu)
        est_cu = np.zeros(Gcu)
        est_cu[cu] = est
        k_cs = np.bincount(cell_of_cu, weights=est_cu, minlength=Gc)
        n_os = n_cs[cell] - n_cus[cu]
        k_os = k_cs[cell] - est_cu[cu]
        oks = (n_os >= min_itens) & (k_os >= min_uasgs)
        with np.errstate(divide="ignore", invalid="ignore"):
            out["ref_EST_A1"] = np.where(oks, (sl_cs[cell] - sl_cus[cu]) / n_os, np.nan)
    return out


def executar(ctx, abrir, salvar):
    from . import comum
    cfg, reg = ctx["cfg"], ctx["reg"]
    r = cfg["referencia"]
    df = abrir(ctx, "amostra")
    unid = abrir(ctx, "unidades")
    pool = df.loc[df.elegivel_preco, ["produto", "tri", "uasg", "logp"]]
    with reg.etapa(f"referências leave-one-UASG-out ({len(pool):,} itens)"):
        refs = calcular(pool, r["min_itens"], r["min_outras_uasgs"], r["apara"], r["apara_min_n"],
                        estaveis=set(unid.loc[unid.estavel, "uasg"]))
    lp = pool["logp"].to_numpy()
    idx = pd.DataFrame(index=pool.index)
    for k in VARIANTES + ["EST_A1"]:
        idx[f"y_{k}"] = 100 * (lp - refs[f"ref_{k}"].to_numpy())
    idx["sd_outros"] = refs["sd_outros"]
    idx["n_outros"] = refs["n_outros"]
    idx["k_outros"] = refs["k_outros"]
    idx["ref_ok"] = refs["ref_ok"]
    lim = 100 * r["extremo_ln"]
    idx["mascara_A1"] = idx["ref_ok"] & (idx["y_A1"].abs() <= lim)
    for k in VARIANTES + ["EST_A1"]:
        idx[f"propria_{k}"] = idx[f"y_{k}"].notna() & (idx[f"y_{k}"].abs() <= lim)
    salvar(ctx, "indices", idx)
    resumo = []
    for k in VARIANTES + ["EST_A1"]:
        y = idx[f"y_{k}"]
        com = y[idx.mascara_A1]
        resumo.append({"variante": k, "itens_com_referencia": int(y.notna().sum()),
                       "extremos_fora_ln10": int((y.abs() > lim).sum()),
                       "amostra_propria": int(idx[f"propria_{k}"].sum()),
                       "amostra_comum_A1": int(com.notna().sum()), "media_comum": float(com.mean()),
                       "mediana_comum": float(com.median()), "dp_comum": float(com.std())})
    comum.escrever_csv(ctx["saidas"] / "tabelas" / "referencias_resumo.csv", resumo)
    reg.contar("referencias", {"pool": len(pool), "com_A1": int(idx.ref_ok.sum()), "mascara_A1": int(idx.mascara_A1.sum())})
