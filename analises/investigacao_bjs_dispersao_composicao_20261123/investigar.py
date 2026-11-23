"""Investigação complementar (protocolo.md). EXPLORATÓRIA.

(1) BJS × estudo de eventos com os mesmos itens, eventos, controles e períodos; (2) dispersão histórica × contemporânea na
amostra comum; (3) composição das compras na troca de modo.

Uso (da pasta PNCP-Automation):
    python analises/investigacao_bjs_dispersao_composicao_20261123/investigar.py
Pré-requisitos: base de 23/11 (dados/testes_desenho_causal/) e dados/robustez_dispersao/descricoes_catmat.pkl
(../robustez_dispersao_20261123/preparar_descricoes.py). Não lê o pncp.db; não altera bases nem resultados anteriores.
"""
import hashlib, json, os, sys, time, traceback
from pathlib import Path

sys.dont_write_bytecode = True
AQUI = Path(__file__).resolve().parent
ROB = AQUI.parent / "robustez_dispersao_20261123"
sys.path.insert(0, str(ROB))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

import motor_robustez as MR  # noqa: E402
import comum as C  # noqa: E402
from preparar import norm_un  # noqa: E402

LIMITE = int(os.environ.get("INVESTIGACAO_LIMITE_EVENTOS", "0"))     # só para teste rápido do código
SAIDA = (C.RAIZ / "dados" / "investigacao_bjs_dispersao_composicao" / "teste_rapido") if LIMITE else AQUI
TAB = SAIDA / "tabelas"
TAB.mkdir(parents=True, exist_ok=True)
B_BOOT = 9999
CMIN = MR.CMIN
FIM_EVENTO = (2025 * 12 + 9) - C.M0                                   # 2025-10: último mês de evento usado
T0 = time.time()
REG = {"inicio": time.strftime("%Y-%m-%d %H:%M:%S"),
       "protocolo_sha256": hashlib.sha256((AQUI / "protocolo.md").read_bytes()).hexdigest(),
       "parametros": {"W": MR.W0, "cmin": CMIN, "limite_dispersao": MR.LIM, "B": B_BOOT, "var_a": MR.VAR_A, "var_b": MR.VAR_B},
       "etapas": {}, "exclusoes": {}, "conferencias": {}}
R, TODAS, S = {}, [], {}


def log(*a):
    print(f"[{time.time() - T0:6.0f}s]", *a, flush=True)


def executar(nome, fn):
    t = time.time()
    try:
        fn()
        REG["etapas"][nome] = {"status": "ok", "segundos": round(time.time() - t, 1)}
        log(nome, "ok")
    except Exception as e:
        REG["etapas"][nome] = {"status": "falha", "erro": repr(e), "traceback": traceback.format_exc(),
                               "segundos": round(time.time() - t, 1)}
        log(nome, "FALHA", repr(e))


def pesos_de(df):
    return dict(zip(df.k, MR.peso_precisao(df.h)))


def sub(df, ks):
    return df[df.k.isin(ks)].copy()


def influencia(df, pesos):
    """Retira os eventos de um órgão de cada vez: mínimo, máximo, maior |Δ| e órgão de maior peso."""
    w = MR._pesos(df, pesos)
    ok = np.isfinite(w) & df.did.notna().to_numpy()
    d, w = df[ok], w[ok]
    y = (d.sinal * d.did).to_numpy(float)
    tot = float((w * y).sum() / w.sum())
    sh = pd.Series(w, index=d.index).groupby(d.cnpj.astype(str)).sum() / w.sum()
    ests = {}
    for c in sh.index:
        mk = (d.cnpj.astype(str) != c).to_numpy()
        ests[c] = float((w[mk] * y[mk]).sum() / w[mk].sum())
    e = pd.Series(ests)
    dl = (e - tot).abs()
    return {"loo_min_lp": 100 * float(e.min()), "loo_max_lp": 100 * float(e.max()), "loo_maior_delta_lp": 100 * float(dl.max()),
            "orgao_mais_influente": str(dl.idxmax()), "orgao_maior_peso": str(sh.idxmax()), "peso_maior_orgao": float(sh.max())}


def relato(parte, modelo, df, pesos="precisao", ic=True, **extra):
    """Estimativa padrão + influência; acrescenta à tabela geral e devolve o dicionário."""
    if df is None or len(df) < 5:
        d = {"parte": parte, "modelo": modelo, "n_eventos": 0 if df is None else int(len(df)), "observacao": "sem eventos suficientes"}
        TODAS.append(d)
        return d
    est = MR.estimar(df, pesos=pesos, B=B_BOOT, ic=ic)
    inf = influencia(df, pesos)
    d = {"parte": parte, "modelo": modelo}
    for c in ["coef_lp", "ep_lp", "p_wcr", "p_t", "n_eventos", "n_A->AF", "n_AF->A", "itens_tratadas", "compras_tratadas",
              "uasgs_tratadas", "uasgs_controle", "orgaos", "orgaos_efetivos", "maior_orgao_peso", "pesos"]:
        d[c] = est.get(c)
    d["ic95_inf"], d["ic95_sup"] = (est.get("ic95_wcr") if ic else est.get("ic95_t")) or [np.nan, np.nan]
    d["ic95_tipo"] = "WCR" if ic else "t(G-1)"
    for t in ("A->AF", "AF->A"):
        if t in est:
            d[f"{t}_coef"], d[f"{t}_p"] = est[t]["coef_lp"], est[t]["p_wcr"]
    d["soma_sentidos"], d["soma_sentidos_p"] = est.get("simetria_soma_lp"), est.get("simetria_p_wcr")
    d.update(inf)
    d.update(extra)
    TODAS.append(d)
    return d


def dif_relato(parte, modelo, df1, w1, df2, w2):
    dd = MR.diferenca(df1, w1, df2, w2, B=B_BOOT)
    d = {"parte": parte, "modelo": modelo, "coef_lp": dd["dif_lp"], "ep_lp": dd["ep_lp"], "ic95_inf": dd["ic95_wcu"][0],
         "ic95_sup": dd["ic95_wcu"][1], "ic95_tipo": "WCU (diferença pareada)", "p_wcr": dd["p_wcu"], "p_t": dd["p_t"],
         "n_eventos": dd["eventos"], "orgaos": dd["orgaos"], "coef_1": dd["coef1_lp"], "coef_2": dd["coef2_lp"]}
    TODAS.append(d)
    return d


def wv(df, pesos):
    """vetor de pesos alinhado a df (precisão, iguais ou dicionário congelado)."""
    return MR._pesos(df, pesos)


def salvar(nome, linhas):
    pd.DataFrame(linhas).to_csv(TAB / f"{nome}.csv", index=False, encoding="utf-8", lineterminator="\n")


# --------------------------------------------------------------------------------------------- base
def base():
    B = MR.Base(log=log)
    S["B"] = B
    E6 = B.eventos(6)
    if LIMITE:
        E6 = E6.head(LIMITE)
    assert (E6.m <= FIM_EVENTO).all(), "evento reservado para validação entrou na amostra"
    REG["conferencias"]["eventos_reservados_excluidos"] = {"ultimo_mes_evento_usado": C.mes_str(C.M0 + int(E6.m.max())),
                                                           "eventos_posteriores_a_2025_10": int((B.ev.m > FIM_EVENTO).sum()),
                                                           "algum_posterior_usado": False}
    S["E6"] = E6
    S["mask_f"] = (B.it.sd_G <= MR.LIM).to_numpy()
    S["M0"] = B.rodar(E6, "e_ok", bins=False)
    S["M1"] = B.rodar(E6, "e_G", mascara=S["mask_f"], bins=False)
    S["G_all"] = B.rodar(E6, "e_G", bins=False)
    r0, r1 = MR.estimar(S["M0"], B=B_BOOT), MR.estimar(S["M1"], B=B_BOOT)
    REG["conferencias"]["reproduz_M0"] = {"coef": r0["coef_lp"], "ic": r0["ic95_wcr"], "eventos": r0["n_eventos"],
                                          "ok": bool(abs(r0["coef_lp"] + 1.91) < 0.01) if not LIMITE else None}
    REG["conferencias"]["reproduz_M1"] = {"coef": r1["coef_lp"], "ic": r1["ic95_wcr"], "eventos": r1["n_eventos"],
                                          "ok": bool(abs(r1["coef_lp"] + 3.76) < 0.01) if not LIMITE else None}
    # colunas adicionais por item (só em memória)
    it = B.it
    for nome, chave in (("rep_catmat", "catmat"), ("rep_prod", "prod")):
        v = pd.DataFrame({"u": it.u.to_numpy(), "x": it[chave].to_numpy(), "m": it.m.to_numpy()})
        ok = pd.notna(v.x) & (v.x.astype(float) >= 0) if chave == "prod" else pd.notna(v.x)
        v = v[ok]
        z = v.drop_duplicates().sort_values(["u", "x", "m"])
        z["ant"] = z.groupby(["u", "x"]).m.shift(1)
        z["rep"] = ((z.m - z.ant) <= 12).astype(float)
        z.loc[z.m < 12, "rep"] = np.nan                         # sem 12 meses de histórico
        mp = z.set_index(["u", "x", "m"]).rep
        idx = pd.MultiIndex.from_arrays([v.u, v.x, v.m])
        col = np.full(len(it), np.nan)
        col[np.where(ok)[0]] = mp.reindex(idx).to_numpy()
        it[nome] = col
    ncat = it.groupby("cod").catmat.transform("nunique")
    it["n_catmat"] = np.log(ncat.where(ncat > 0))
    log("base pronta", {k: len(S[k]) for k in ("M0", "M1", "G_all")})


# --------------------------------------------------------------------------------------------- parte 1
def fe2(y, g1, g2, iters=2000, tol=1e-10):
    a = np.zeros(g1.max() + 1); b = np.zeros(g2.max() + 1)
    n1, n2 = np.bincount(g1), np.bincount(g2)
    for _ in range(iters):
        a_new = np.bincount(g1, y - b[g2]) / n1
        b_new = np.bincount(g2, y - a_new[g1]) / n2
        dmax = max(np.abs(a_new - a).max(), np.abs(b_new - b).max())
        a, b = a_new, b_new
        if dmax < tol:
            break
    return a, b


def bjs_evento(k, ev, ctrl, y, mask):
    """S1 (empilhado só com os itens imputáveis) e S2 (BJS do evento) com os mesmos itens, controles e janela."""
    B = S["B"]; it = B.it
    u, m = int(ev.u), int(ev.m)
    rows = B.linhas(k, u, m, ev.tipo, 6, unidades=np.r_[u, ctrl])
    yv, lp = it[y].to_numpy()[rows], it.logp.to_numpy()[rows]
    ok = np.isfinite(yv) & np.isfinite(lp)
    if mask is not None:
        ok &= mask[rows]
    rows, yv, lp = rows[ok], yv[ok], lp[ok]
    uu, mm, cod = B.u_arr[rows], B.m_arr[rows], it.cod.to_numpy()[rows]
    cel = it["prod"].to_numpy()[rows].astype(np.int64) * 1000 + it.tri.to_numpy()[rows]
    T = (uu == u) & (mm >= m)
    Un = ~T
    if T.sum() == 0 or ((uu == u) & (mm < m)).sum() == 0:
        return None
    g, gu = pd.factorize(uu[Un])
    c, cu = pd.factorize(cel[Un])
    a, b = fe2(lp[Un], g, c, iters=1000, tol=1e-9)
    cnt = np.bincount(c)
    gi = pd.Index(gu).get_loc(u)
    ci = pd.Index(cu).get_indexer(cel[T])
    imp = ci >= 0
    imp[imp] &= cnt[ci[imp]] >= 3
    if imp.sum() == 0:
        return None
    tau = lp[T][imp] - a[gi] - b[ci[imp]]
    cm = pd.Series(tau).groupby(cod[T][imp]).mean()
    c_pos = int(len(cm))
    c_pre = int(len(np.unique(cod[(uu == u) & (mm < m)])))
    if c_pos < CMIN or c_pre < CMIN:
        return None
    keep = np.ones(len(rows), bool)
    keep[np.where(T)[0][~imp]] = False
    df = pd.DataFrame({"u": uu[keep], "pos": mm[keep] >= m, "cod": cod[keep], "y": yv[keep]})
    cmean = df.groupby(["u", "pos", "cod"]).y.mean().reset_index()
    um = cmean.groupby(["u", "pos"]).y.agg(["mean", "size"]).unstack("pos")
    d = um[("mean", True)] - um[("mean", False)]
    okc = (um[("size", False)] >= CMIN) & (um[("size", True)] >= CMIN)
    okc[u] = False
    if okc.sum() < 5:
        return None
    base = {"k": k, "u": u, "m": m, "tipo": ev.tipo, "sinal": 1 if ev.tipo == "A->AF" else -1, "cnpj": B.cnpj[u],
            "h": 1 / c_pre + 1 / c_pos, "c_pre": c_pre, "c_pos": c_pos, "controles": np.asarray(d.index[okc]),
            "itens_tratada": int((~T & (uu == u)).sum() + imp.sum()), "compras_tratada": c_pre + c_pos,
            "itens_pos_imputaveis": int(imp.sum()), "itens_pos_total": int(T.sum())}
    s1 = dict(base, did=float(d[u] - d[okc].mean()))
    s2 = dict(base, did=float(cm.mean()))
    return s1, s2


def bjs_original(evs, mask):
    """BJS original: não tratados = compras no modo de partida das unidades estáveis (período todo) + pré-janelas."""
    B = S["B"]; it = B.it
    ok = mask & np.isfinite(it.logp.to_numpy())
    linhas = []
    for t, reg, modo in (("A->AF", "A estável", 0), ("AF->A", "AF estável", 1)):
        est = B.un.index[B.un.regime.eq(reg)].to_numpy()
        est = est[~np.isin(est, B.ev.u.to_numpy())]
        sel = ok & np.isin(B.u_arr, est) & (it.af.to_numpy() == modo)
        partes = [pd.DataFrame({"g": "u" + pd.Series(B.u_arr[sel]).astype(str), "y": it.logp.to_numpy()[sel],
                                "pm": it["prod"].to_numpy()[sel].astype(np.int64) * 1000 + it.tri.to_numpy()[sel],
                                "fase": "nt", "k": -1, "cod": it.cod.to_numpy()[sel]})]
        for _, r in evs[evs.tipo.eq(t)].iterrows():
            u, m = int(r.u), int(r.m)
            idx = np.arange(B.ini[u], B.fim[u])
            idx = idx[(B.m_arr[idx] >= m - 6) & (B.m_arr[idx] < m + 6) & ok[idx]]
            if len(idx) == 0:
                continue
            partes.append(pd.DataFrame({"g": f"k{r.k}", "y": it.logp.to_numpy()[idx],
                                        "pm": it["prod"].to_numpy()[idx].astype(np.int64) * 1000 + it.tri.to_numpy()[idx],
                                        "fase": np.where(B.m_arr[idx] >= m, "trat", "pre"), "k": r.k,
                                        "cod": it.cod.to_numpy()[idx]}))
        d = pd.concat(partes, ignore_index=True)
        und = d[d.fase.ne("trat")]
        g1, g1u = pd.factorize(und.g)
        pmc, pmu = pd.factorize(und.pm)
        a, b = fe2(und.y.to_numpy(float), g1, pmc, iters=500, tol=1e-9)
        cnt = np.bincount(pmc)
        tr = d[d.fase.eq("trat")].copy()
        gi = pd.Index(g1u).get_indexer(tr.g)
        pi = pd.Index(pmu).get_indexer(tr.pm)
        okt = (gi >= 0) & (pi >= 0)
        okt[okt] &= cnt[pi[okt]] >= 3
        tr = tr[okt]
        tr["tau"] = tr.y.to_numpy() - a[gi[okt]] - b[pi[okt]]
        for k, z in tr.groupby("k"):
            r = evs.loc[evs.k == k].iloc[0]
            cm = z.groupby("cod").tau.mean()
            linhas.append({"k": k, "u": r.u, "m": r.m, "tipo": t, "sinal": r.sinal, "cnpj": r.cnpj, "did": float(cm.mean()),
                           "h": r.h, "itens_tratada": int(len(z)), "compras_tratada": int(len(cm)), "controles": []})
    return pd.DataFrame(linhas)


def parte1():
    B, E6 = S["B"], S["E6"]
    eg, ea = np.isfinite(B.it.e_G.to_numpy()), np.isfinite(B.it.e_ok.to_numpy())
    passos, difs, por_evento = [], [], []
    for nome, base, y, mask, mask_bjs in (("A (referência original, todas as células)", S["M0"], "e_ok", None, ea),
                                          ("G (referência G, dispersão ≤ 0,80)", S["M1"], "e_G", S["mask_f"], eg & S["mask_f"])):
        s1, s2 = [], []
        for _, r in base.iterrows():
            o = bjs_evento(r.k, S["E6"].loc[r.k], np.asarray(r.controles), y, mask)
            if o:
                s1.append(o[0]); s2.append(o[1])
        S1, S2 = pd.DataFrame(s1), pd.DataFrame(s2)
        S3 = bjs_original(base, mask_bjs)
        ks = sorted(set(base.k) & set(S1.k) & set(S2.k) & set(S3.k))
        w0 = pesos_de(base)
        REG["exclusoes"][f"parte1_{nome[:1]}"] = {"eventos_base": int(len(base)), "eventos_S1_S2": int(len(S1)),
                                                  "eventos_S3": int(len(S3)), "eventos_comuns": len(ks),
                                                  "itens_pos_imputaveis": int(S1.itens_pos_imputaveis.sum()),
                                                  "itens_pos_total": int(S1.itens_pos_total.sum())}
        frac_imp = float(S1.itens_pos_imputaveis.sum() / S1.itens_pos_total.sum())
        mods = {"S0 empilhado, modelo base": sub(base, ks), "S1 empilhado, só itens imputáveis": sub(S1, ks),
                "S2 BJS do evento (mesmos itens, controles e janela)": sub(S2, ks),
                "S3 BJS original (unidades estáveis, período todo)": sub(S3, ks)}
        for pnome, pesos in (("pesos de S0 congelados", w0), ("pesos iguais", "iguais")):
            for mn, df in mods.items():
                passos.append(relato("1", f"{nome} | {mn} | {pnome}", df, pesos, frac_itens_pos_imputaveis=frac_imp))
            for (a_, b_, rot) in (("S1 empilhado, só itens imputáveis", "S0 empilhado, modelo base", "amostra de itens (S1 − S0)"),
                                  ("S2 BJS do evento (mesmos itens, controles e janela)", "S1 empilhado, só itens imputáveis",
                                   "estimador, mesmos insumos (S2 − S1)"),
                                  ("S3 BJS original (unidades estáveis, período todo)", "S2 BJS do evento (mesmos itens, controles e janela)",
                                   "controles e períodos do BJS original (S3 − S2)"),
                                  ("S3 BJS original (unidades estáveis, período todo)", "S0 empilhado, modelo base", "total (S3 − S0)")):
                d1, d2 = mods[a_], mods[b_]
                difs.append(dif_relato("1", f"{nome} | {rot} | {pnome}", d1, wv(d1, pesos), d2, wv(d2, pesos)))
        # ponderação: precisão própria de cada passo (S1/S2 com h após a restrição; S3 usa h do modelo base)
        for mn, df in mods.items():
            passos.append(relato("1", f"{nome} | {mn} | precisão própria", df, "precisao"))
        m_ev = sub(S1, ks)[["k", "tipo", "c_pre", "c_pos", "itens_pos_imputaveis", "itens_pos_total"]].copy()
        for mn, df in mods.items():
            m_ev[mn[:2]] = df.set_index("k").did.reindex(m_ev.k).to_numpy()
        m_ev.insert(0, "especificacao", nome[:1])
        por_evento.append(m_ev)
    salvar("p1_passos", passos)
    salvar("p1_decomposicao", difs)
    pd.concat(por_evento).to_csv(TAB / "p1_eventos.csv", index=False, encoding="utf-8", lineterminator="\n")
    R["parte1"] = {"passos": passos, "decomposicao": difs}


# --------------------------------------------------------------------------------------------- parte 2
def produtos_h1():
    B = S["B"]
    d = pd.read_pickle(MR.CACHE / "descricoes_catmat.pkl")
    d["un_n"] = d.un.map({u: norm_un(u) for u in d.un.dropna().unique()})
    tot = d.groupby("catmat").n.sum()
    mu = (d.groupby(["catmat", "un_n"]).n.sum().reset_index().sort_values(["catmat", "n"], ascending=[True, False])
          .drop_duplicates("catmat").set_index("catmat"))
    cat = pd.DataFrame({"itens": tot, "un_modal": mu.un_n, "share": mu.n / tot}).dropna()
    zero = cat.un_modal.astype(str).str.contains(r"(?:^| )0 00(?: |$)")
    gen = cat.un_modal.astype(str).isin(MR.GENERICAS)
    h1 = cat[(cat.itens >= 20) & (cat.share >= .9) & ~zero & ~gen]
    chave = pd.MultiIndex.from_arrays([B.it.catmat, B.it.un_n.astype(str)])
    return chave.isin(pd.MultiIndex.from_arrays([h1.index.astype(float), h1.un_modal.astype(str)]))


def ols_fe(y, X, grupo, cl):
    """MQO com efeito fixo de grupo (desvio da média do grupo); EP CR1 por cluster; p por bootstrap selvagem de escores."""
    y = np.asarray(y, float); X = np.asarray(X, float)
    gcod = pd.factorize(pd.Series(grupo))[0]
    def demean(v):
        mu = np.bincount(gcod, v) / np.bincount(gcod)
        return v - mu[gcod]
    yd = demean(y); Xd = np.column_stack([demean(X[:, j]) for j in range(X.shape[1])])
    A = np.linalg.pinv(Xd.T @ Xd)
    b = A @ (Xd.T @ yd)
    u = yd - Xd @ b
    g = pd.factorize(pd.Series(cl))[0]
    G = g.max() + 1
    Sg = np.column_stack([np.bincount(g, Xd[:, j] * u, G) for j in range(Xd.shape[1])])
    n, k = Xd.shape
    V = G / (G - 1) * (n - 1) / max(n - k - gcod.max(), 1) * A @ (Sg.T @ Sg) @ A
    se = np.sqrt(np.diag(V))
    rng = np.random.default_rng(13)
    v = C.WEBB[rng.integers(0, 6, size=(B_BOOT, G))]
    bs = v @ (Sg @ A.T)                                          # B x k
    p_w = [float(np.mean(np.abs(bs[:, j]) >= abs(b[j]))) for j in range(k)]
    tt = stats.t.ppf(.975, G - 1)
    return [{"coef": float(b[j]), "ep": float(se[j]), "ic95": [float(b[j] - tt * se[j]), float(b[j] + tt * se[j])],
             "p_wild": p_w[j], "p_t": float(2 * stats.t.sf(abs(b[j] / se[j]), G - 1)), "G": int(G), "n": int(n)} for j in range(k)]


def f_def(B, k, rows, m, W):
    return np.isfinite(B.D(k, rows, m, W))


def f_def_contemp(B, k, rows, m, W):
    return np.isfinite(B.D(k, rows, m, W)) & (B.it.sd_G.to_numpy()[rows] <= MR.LIM)


def f_hist(B, k, rows, m, W):
    return np.nan_to_num(B.D(k, rows, m, W), nan=np.inf) <= MR.LIM


def parte2():
    B, E6, Gall = S["B"], S["E6"], S["G_all"]
    wG = pesos_de(Gall)
    var = {"(a) todos os itens G": {}, "(b) amostra comum (as duas dispersões definidas)": {"filtro_evento": f_def},
           "(c) amostra comum, contemporânea ≤ 0,80": {"filtro_evento": f_def_contemp},
           "(d) amostra comum, histórica ≤ 0,80": {"filtro_evento": f_hist},
           "(e) todos os itens, contemporânea ≤ 0,80": {"mascara": S["mask_f"]}}
    res, linhas = {}, []
    for nome, kw in var.items():
        lst = []
        for _, r in Gall.iterrows():
            o = B.evento(r.k, E6.loc[r.k], "e_G", controles=np.asarray(r.controles), cmin=1, cmin_controle=1, bins=False, **kw)
            if o is not None:
                lst.append(o)
        res[nome] = pd.DataFrame(lst)
        linhas.append(relato("2", nome, res[nome], wG))
    S["p2"] = res
    for a_, b_, rot in (("(c) amostra comum, contemporânea ≤ 0,80", "(d) amostra comum, histórica ≤ 0,80",
                         "definição do filtro, mesmos itens: (c) − (d)"),
                        ("(e) todos os itens, contemporânea ≤ 0,80", "(c) amostra comum, contemporânea ≤ 0,80",
                         "retirar itens sem histórico, filtro contemporâneo: (e) − (c)"),
                        ("(b) amostra comum (as duas dispersões definidas)", "(a) todos os itens G",
                         "retirar itens sem histórico, sem filtro: (b) − (a)"),
                        ("(d) amostra comum, histórica ≤ 0,80", "(a) todos os itens G", "filtro histórico contra todos: (d) − (a)"),
                        ("(e) todos os itens, contemporânea ≤ 0,80", "(a) todos os itens G",
                         "filtro contemporâneo contra todos: (e) − (a)")):
        d1, d2 = res[a_], res[b_]
        linhas.append(dif_relato("2", rot, d1, wv(d1, wG), d2, wv(d2, wG)))
    salvar("p2_filtros", linhas)
    # exclusões por falta de histórico
    H1 = produtos_h1()
    S["H1"] = H1
    freq = B.it.loc[B.it.logp.notna() & (B.it["prod"] >= 0)].groupby("prod").u.nunique()
    it = B.it
    tab, did_noD, dif_car, trat_itens = [], [], [], []
    for _, r in Gall.iterrows():
        u, m, k = int(r.u), int(r.m), r.k
        ctrl = np.asarray(r.controles)
        rows = B.linhas(k, u, m, r.tipo, 6, unidades=np.r_[u, ctrl])
        rows = rows[np.isfinite(it.e_G.to_numpy()[rows])]
        D = B.D(k, rows, m, 6)
        sem = ~np.isfinite(D)
        uu, mm = B.u_arr[rows], B.m_arr[rows]
        trat, pos = uu == u, mm >= m
        af = it.af.to_numpy()[rows]
        z = pd.DataFrame({"grupo": np.where(trat, "tratada", "controle"), "periodo": np.where(pos, "pós", "pré"),
                          "modo_compra": np.where(af == 1, "AF", "A"), "sem_D": sem})
        z["sentido"] = r.tipo
        tab.append(z.groupby(["sentido", "grupo", "periodo", "modo_compra"]).sem_D.agg(["size", "sum"]).reset_index())
        # DiD da parcela sem D (tratada pós − pré, menos controles)
        q = pd.DataFrame({"u": uu, "pos": pos, "semD": sem.astype(float)})
        sh = q.groupby(["u", "pos"]).semD.mean().unstack()
        sh = sh.dropna()
        if u in sh.index and (sh.index != u).sum() >= 5:
            dd = sh[True] - sh[False]
            did_noD.append({"k": k, "u": u, "m": m, "tipo": r.tipo, "sinal": r.sinal, "cnpj": r.cnpj, "did": float(dd[u] - dd.drop(u).mean()),
                            "h": r.h, "itens_tratada": int(trat.sum()), "compras_tratada": 0, "controles": ctrl})
        # características: sem D − com D, no evento (tratada + controles)
        car = pd.DataFrame({"semD": sem, "med6505": it.med6505.to_numpy()[rows], "H1": H1[rows].astype(float),
                            "nivel_mercado": it.ref_G.to_numpy()[rows], "indice_quantidade": it.eq_ok.to_numpy()[rows],
                            "log_freq_produto": np.log(freq.reindex(it["prod"].to_numpy()[rows]).to_numpy())})
        if car.semD.sum() >= 5 and (~car.semD).sum() >= 5:
            diffs = car[car.semD].mean() - car[~car.semD].mean()
            dif_car.append({"k": k, "cnpj": r.cnpj, "tipo": r.tipo, "w": wG[k], **{c: float(diffs[c]) for c in diffs.index if c != "semD"}})
        # itens das tratadas para o modelo de probabilidade linear
        mt = trat
        trat_itens.append(pd.DataFrame({"k": k, "cnpj": r.cnpj, "semD": sem[mt].astype(float), "af": (af[mt] == 1).astype(float),
                                        "pos": pos[mt].astype(float), "med6505": car.med6505.to_numpy()[mt], "H1": car.H1.to_numpy()[mt],
                                        "nivel_mercado": car.nivel_mercado.to_numpy()[mt],
                                        "indice_quantidade": car.indice_quantidade.to_numpy()[mt],
                                        "log_freq_produto": car.log_freq_produto.to_numpy()[mt]}))
    T = pd.concat(tab).groupby(["sentido", "grupo", "periodo", "modo_compra"])[["size", "sum"]].sum().reset_index()
    T["parcela_sem_D"] = T["sum"] / T["size"]
    T.rename(columns={"size": "itens", "sum": "itens_sem_D"}).to_csv(TAB / "p2_exclusoes_por_grupo.csv", index=False,
                                                                     encoding="utf-8", lineterminator="\n")
    linhas2 = [relato("2", "DiD da parcela de itens sem histórico (tratada pós − pré − controles)", pd.DataFrame(did_noD), wG)]
    ti = pd.concat(trat_itens, ignore_index=True)
    lpm = []
    r1 = ols_fe(ti.semD, ti[["af"]], ti.k, ti.cnpj)[0]
    lpm.append({"modelo": "sem D ~ compra AF | efeito fixo de evento (itens das tratadas)", **r1})
    cols = ["af", "med6505", "H1", "nivel_mercado", "indice_quantidade", "log_freq_produto"]
    z = ti.dropna(subset=cols)
    r2 = ols_fe(z.semD, z[cols], z.k, z.cnpj)
    for c, rr in zip(cols, r2):
        lpm.append({"modelo": f"sem D ~ compra AF + características | efeito fixo de evento: coef. de {c}", **rr})
    r3 = ols_fe(ti.semD, ti[["pos"]], ti.k, ti.cnpj)[0]
    lpm.append({"modelo": "sem D ~ pós-troca | efeito fixo de evento (itens das tratadas)", **r3})
    pd.DataFrame(lpm).to_csv(TAB / "p2_exclusoes_lpm.csv", index=False, encoding="utf-8", lineterminator="\n")
    dc = pd.DataFrame(dif_car)
    car_l = []
    for c in ["med6505", "H1", "nivel_mercado", "indice_quantidade", "log_freq_produto"]:
        zz = dc.dropna(subset=[c])
        X = np.ones((len(zz), 1))
        rr = C.media_inferencia(zz[c].to_numpy(), zz.cnpj.astype(str).to_numpy(), zz.w.to_numpy(), B_BOOT, ic=True)
        car_l.append({"caracteristica": c, "dif_sem_menos_com_D": rr["est"], "ep": rr["ep"], "ic95": rr.get("ic95_wild"),
                      "p_wild": rr["p_wild"], "eventos": rr["n"], "orgaos": rr["G"]})
    pd.DataFrame(car_l).to_csv(TAB / "p2_exclusoes_caracteristicas.csv", index=False, encoding="utf-8", lineterminator="\n")
    tot_it = T["size"].sum(); tot_sem = T["sum"].sum()
    REG["exclusoes"]["parte2"] = {"itens_G_nas_janelas": int(tot_it), "sem_historico": int(tot_sem),
                                  "parcela_sem_historico": float(tot_sem / tot_it)}
    salvar("p2_exclusoes_did", linhas2)
    R["parte2"] = {"filtros": linhas, "did_sem_D": linhas2, "lpm": lpm, "caracteristicas": car_l,
                   "parcela_sem_historico": float(tot_sem / tot_it)}


# --------------------------------------------------------------------------------------------- parte 3
YS = {"repetição de CATMAT (12 meses)": "rep_catmat", "repetição de produto (12 meses)": "rep_prod",
      "parcela de medicamentos (6505)": "med6505", "log do nº de CATMATs distintos": "n_catmat",
      "índice de quantidade": "eq_ok", "log da quantidade": "logq", "índice do estimado (eR)": "eR_ok",
      "parcela com índice G": "com_G", "parcela elegível (contemporânea)": "elegivel", "log do nº de itens": "n_itens"}


def por_evento(k, r, ctrl):
    """Sobreposição de produtos e de CATMAT com a pré-janela, Duncan por classe (tratada − controles) e DiD das parcelas
    com dispersão histórica definida e com histórica ≤ 0,80."""
    B = S["B"]; it = B.it
    u, m = int(r.u), int(r.m)
    rows = B.linhas(k, u, m, r.tipo, 6, unidades=np.r_[u, ctrl])
    rows = rows[np.isfinite(it.e_G.to_numpy()[rows])]
    D = B.D(k, rows, m, 6)
    df = pd.DataFrame({"u": B.u_arr[rows], "pos": B.m_arr[rows] >= m, "prod": it["prod"].to_numpy()[rows],
                       "cat": it.catmat.to_numpy()[rows], "cls": it.classe4.to_numpy()[rows], "D": D})
    med = {"sobreposição de produtos": {}, "sobreposição de CATMAT": {}, "Duncan (classes)": {},
           "parcela com dispersão histórica (DiD)": {}, "parcela histórica ≤ 0,80 (DiD)": {}}
    for v, z in df.groupby("u"):
        pre, po = z[~z.pos], z[z.pos]
        if len(pre) == 0 or len(po) == 0:
            continue
        med["sobreposição de produtos"][v] = float(po["prod"].isin(set(pre["prod"])).mean())
        med["sobreposição de CATMAT"][v] = float(po.cat.isin(set(pre.cat)).mean())
        a = pre.cls.value_counts(normalize=True); b = po.cls.value_counts(normalize=True)
        med["Duncan (classes)"][v] = float(0.5 * a.subtract(b, fill_value=0).abs().sum())
        med["parcela com dispersão histórica (DiD)"][v] = float(np.isfinite(po.D).mean() - np.isfinite(pre.D).mean())
        pd_, pp_ = pre[np.isfinite(pre.D)], po[np.isfinite(po.D)]
        if len(pd_) and len(pp_):
            med["parcela histórica ≤ 0,80 (DiD)"][v] = float((pp_.D <= MR.LIM).mean() - (pd_.D <= MR.LIM).mean())
    out = {}
    for nome, dd in med.items():
        cs = [v for v in ctrl if v in dd]
        if u in dd and len(cs) >= 5:
            out[nome] = dd[u] - np.mean([dd[v] for v in cs])
    return out


def parte3():
    B, E6, Gall = S["B"], S["E6"], S["G_all"]
    wG = pesos_de(Gall)
    linhas, perfil, res = [], [], {}
    for rot, y in YS.items():
        lst = []
        for _, r in Gall.iterrows():
            o = B.evento(r.k, E6.loc[r.k], y, controles=np.asarray(r.controles), cmin=1, cmin_controle=1, bins=True)
            if o is not None:
                lst.append(o)
        df = pd.DataFrame(lst)
        res[rot] = df
        linhas.append(relato("3", rot, df, wG))
        for nome, cols in (("pré (trim. −2)", ["b-2"]), ("pós (trim. 0 e +1)", ["b0", "b1"])):
            j = MR.bins_conjunto(df, cols, pesos=wG)
            for c, v in j["bins"].items():
                perfil.append({"caracteristica": rot, "trimestre": int(c[1:]), **{kk: v[kk] for kk in ("coef_lp", "ep_lp", "p_t", "n_eventos")},
                               "ic95_inf": v["ic95_t"][0], "ic95_sup": v["ic95_t"][1]})
            perfil.append({"caracteristica": rot, "trimestre": f"conjunto {nome}", "F": j["F"], "p_t": j["p"], "q": j["q"]})
    ev_spec = {}
    for _, r in Gall.iterrows():
        for nome, v in por_evento(r.k, E6.loc[r.k], np.asarray(r.controles)).items():
            ev_spec.setdefault(nome, []).append({"k": r.k, "u": r.u, "m": r.m, "tipo": r.tipo, "sinal": r.sinal, "cnpj": r.cnpj,
                                                 "did": v, "h": r.h, "itens_tratada": 0, "compras_tratada": 0,
                                                 "controles": r.controles})
    for nome, lst in ev_spec.items():
        linhas.append(relato("3", nome, pd.DataFrame(lst), wG))
    # Holm entre as características: efeito com sinal e soma dos sentidos
    for chave, col in (("p_holm_efeito_AF", "p_wcr"), ("p_holm_soma_sentidos", "soma_sentidos_p")):
        ps = {i: l[col] for i, l in enumerate(linhas) if l.get(col) is not None and np.isfinite(l.get(col))}
        ordem = sorted(ps, key=ps.get); acc = 0.0
        for j, i in enumerate(ordem):
            acc = max(acc, min(1.0, (len(ps) - j) * ps[i])); linhas[i][chave] = acc
    salvar("p3_composicao", linhas)
    salvar("p3_perfil", perfil)
    # troca fictícia 12 meses antes (unidade estável no modo de partida)
    fake, keep = E6.copy(), []
    fake["m"] = fake.m - 12
    for _, r in fake.iterrows():
        m, u = int(r.m), int(r.u)
        if m - 6 < 0:
            keep.append(False); continue
        n1, a1 = B.pn.soma("N", m - 6, m)[u], B.pn.soma("A", m - 6, m)[u]
        n2, a2 = B.pn.soma("N", m, m + 6)[u], B.pn.soma("A", m, m + 6)[u]
        if n1 == 0 or n2 == 0:
            keep.append(False); continue
        keep.append((a1 / n1 <= .1 and a2 / n2 <= .1) if r.tipo == "A->AF" else (a1 / n1 >= .9 and a2 / n2 >= .9))
    fake = fake[np.array(keep, bool)]
    fake.index = fake.index + 200000
    plac = []
    for rot, y in YS.items():
        df = B.rodar(fake, y, cmin=1, bins=False)
        plac.append(relato("3", f"placebo (troca fictícia 12 meses antes): {rot}", df, "precisao"))
    salvar("p3_placebo", plac)
    REG["exclusoes"]["parte3"] = {"trocas_ficticias_validas": int(len(fake))}
    R["parte3"] = {"composicao": linhas, "perfil": perfil, "placebo": plac}


def main():
    executar("base", base)
    if REG["etapas"]["base"]["status"] == "ok":
        executar("parte1_bjs_estudo_eventos", parte1)
        executar("parte2_dispersao", parte2)
        executar("parte3_composicao", parte3)
    pd.DataFrame(TODAS).to_csv(TAB / "todas_estimativas.csv", index=False, encoding="utf-8", lineterminator="\n")
    REG["conferencias"]["arquivos"] = {p.name: int(len(pd.read_csv(p))) for p in sorted(TAB.glob("*.csv"))}
    REG["fim"] = time.strftime("%Y-%m-%d %H:%M:%S")
    REG["segundos"] = round(time.time() - T0)
    (SAIDA / "resultados.json").write_text(json.dumps(R, ensure_ascii=False, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else float(o)), encoding="utf-8")
    (SAIDA / "registro_execucao.json").write_text(json.dumps(REG, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    log("falhas:", [k for k, v in REG["etapas"].items() if v["status"] != "ok"] or "nenhuma")
    log("FIM")


if __name__ == "__main__":
    main()
