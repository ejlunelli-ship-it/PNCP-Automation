"""Motor item a item do estudo de eventos A × AF, para os testes de robustez da dispersão (protocolo.md).

Reproduz o motor de 23/11 (`testes_desenho_causal_20261123/motor.py`) e acrescenta:
- filtros de itens por evento (ex.: dispersão anterior à janela);
- pesos por item dentro da compra;
- conjunto de controles fixo;
- funções de influência para comparar especificações nos mesmos eventos.

Sem efeito colateral ao importar: não escreve `__pycache__` na pasta de 23/11.
"""
import json, sys
from pathlib import Path

sys.dont_write_bytecode = True
AQUI = Path(__file__).resolve().parent
T23 = AQUI.parent / "testes_desenho_causal_20261123"
if str(T23) not in sys.path:
    sys.path.insert(0, str(T23))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

import comum as C  # noqa: E402
import motor as Mo  # noqa: E402

CACHE = C.RAIZ / "dados" / "robustez_dispersao"
W0, CMIN = 6, 2
_poder = json.loads((T23 / "poder.json").read_text(encoding="utf-8"))["W6_cmin2"]["var_modelo"]
VAR_A, VAR_B = float(_poder["a"]), float(_poder["b"])
LIM = float(json.loads((T23 / "exploratorio_referencia.json").read_text(encoding="utf-8"))["limiares_dispersao_sd_log"]["p75"])
FAIXAS = json.loads((T23 / "exploratorio_referencia.json").read_text(encoding="utf-8"))["limiares_dispersao_sd_log"]
GENERICAS = {"CONJUNTO", "JOGO", "KIT", "ROLO", "ENVELOPE", "MOLHO", "CAIXA", "PACOTE", "EMBALAGEM", "FARDO", "SACO", "PECA",
             "VOLUME", "CARTELA", "BLOCO", "TUBO", "LATA", "BALDE", "BOMBONA", "GALAO", "POTE", "BISNAGA", "FRASCO"}


def peso_precisao(h):
    return 1 / np.maximum(VAR_A + VAR_B * np.asarray(h, float), 1e-6)


# --------------------------------------------------------------------------------------------- referências
def tabela_uasg(x):
    """Por célula (produto × trimestre) e UASG: nº de itens, soma do log P, preço médio (aritmético) e seu log;
    e estatísticas da célula para as fórmulas sem a própria UASG."""
    x = x.assign(p=np.exp(x.logp))
    gu = x.groupby(["prod", "tri", "u"], observed=True).agg(n=("logp", "size"), sl=("logp", "sum"), mp=("p", "mean"))
    gu = gu.reset_index()
    gu["lm"] = np.log(gu.mp)
    gu["lm2"] = gu.lm ** 2
    gc = gu.groupby(["prod", "tri"], observed=True).agg(K=("u", "size"), N=("n", "sum"), S1=("lm", "sum"),
                                                        S2=("lm2", "sum"), SL=("sl", "sum")).reset_index()
    gu = gu.merge(gc, on=["prod", "tri"])
    k1, n1 = gu.K - 1, gu.N - gu.n
    ok3 = (k1 >= 3) & (n1 >= 3)
    s1, s2 = gu.S1 - gu.lm, gu.S2 - gu.lm ** 2
    gu["ref_G"] = (s1 / k1).where(ok3)
    var = (s2 - s1 ** 2 / k1) / (k1 - 1)
    gu["sd_G"] = np.sqrt(np.clip(var, 0, None)).where(ok3)
    # desvio-padrão da célula inteira (para uma UASG que não comprou o produto naquele trimestre)
    gc["sd_cel"] = np.sqrt(np.clip((gc.S2 - gc.S1 ** 2 / gc.K) / (gc.K - 1), 0, None)).where(gc.K >= 3)
    return gu, gc


# --------------------------------------------------------------------------------------------- base
class Base:
    def __init__(self, log=print):
        self.log = log
        P = dict(np.load(C.DADOS / "paineis.npz"))
        mf = (int(C.FIM_ITENS[:4]) * 12 + int(C.FIM_ITENS[5:7]) - 1) - C.M0 + 1
        self.pn = Mo.Paineis({"N": P["N"], "A": P["A"]}, mf)
        self.mf, self.U = mf, P["N"].shape[0]
        self.un = pd.read_pickle(C.DADOS / "unidades.pkl")
        self.esf = self.un.esfera.reindex(range(self.U)).to_numpy()
        self.cnpj = self.un.cnpj.reindex(range(self.U)).astype(str).to_numpy()
        self.ev = pd.read_csv(T23 / "eventos.csv", dtype={"unidade": str, "cnpj": str})
        cols = ["compra", "u", "m", "tri", "prod", "catmat", "un_n", "classe", "logp", "logr", "logq", "e_ok", "eR_ok",
                "eq", "excl", "sigilo", "med"]
        it = pd.read_pickle(C.DADOS / "itens.pkl")[cols]
        it["cod"] = it.compra.cat.codes.astype(np.int64)
        comp = pd.read_pickle(C.DADOS / "compras.pkl")[["compra", "af"]]
        af = pd.Series(comp.af.to_numpy(), index=comp.compra.astype(str))
        it["af"] = af.reindex(pd.Index(it.compra.cat.categories.astype(str))).to_numpy()[it.cod.to_numpy()]
        it = it.drop(columns=["compra"])
        x = it.loc[it.logp.notna(), ["prod", "tri", "u", "logp"]]
        self.gu, self.gc = tabela_uasg(x)
        it = it.merge(self.gu[["prod", "tri", "u", "ref_G", "sd_G"]], on=["prod", "tri", "u"], how="left")
        e = it.logp - it.ref_G
        it["e_G"] = e.where(e.abs() <= C.LN10)
        it["eq_ok"] = it["eq"].clip(-5, 5)
        # desfechos de composição por item (a média por compra vira parcela ou nível)
        n_it = it.groupby("cod").cod.transform("size")
        it["n_itens"] = np.log(n_it)
        it["com_G"] = it.e_G.notna().astype(float)
        it["elegivel"] = np.where(it.e_G.notna(), (it.sd_G <= LIM).astype(float), np.nan)
        it["un_unidade"] = (it.un_n.astype(str) == "UNIDADE").astype(float)
        cl4 = it.classe.astype(str).str[:4]
        it["med65"] = it.med.astype(float)
        it["med6505"] = (cl4 == "6505").astype(float)
        it["classe4"] = pd.factorize(cl4)[0]
        it["ref_G_nivel"] = it.ref_G.where(it.e_G.notna())
        it["excl"] = it.excl.astype(float)
        it["sig"] = it.sigilo.astype(float)
        it = it.sort_values(["u", "m"], kind="stable").reset_index(drop=True)
        self.it = it
        self.u_arr, self.m_arr = it.u.to_numpy(), it.m.to_numpy()
        self.ini = np.searchsorted(self.u_arr, np.arange(self.U), "left")
        self.fim = np.searchsorted(self.u_arr, np.arange(self.U), "right")
        self._cand, self._rows, self._D = {}, {}, {}
        log("base", len(it), "itens de material;", int(it.e_G.notna().sum()), "com índice G;",
            int(it.e_ok.notna().sum()), "com índice A")

    # ----------------------------------------------------------------------------------- eventos e controles
    def eventos(self, W):
        e = self.ev.copy()
        if W == 12:
            e = e[(e.dist_vizinho >= 12) & ((e.af_depois_12 - e.af_antes_12).abs() >= .5)]
        e = e[[(m - W >= 0) and (m + W <= self.mf) for m in e.m]]
        return e

    def candidatos(self, k, u, m, tipo, W):
        """Controles possíveis, sem olhar desfecho: mesma esfera, estáveis no modo de partida nas duas meias janelas,
        sem evento próprio a menos de W meses."""
        ch = (k, W)
        if ch not in self._cand:
            Npre, Apre = self.pn.soma("N", m - W, m), self.pn.soma("A", m - W, m)
            Npos, Apos = self.pn.soma("N", m, m + W), self.pn.soma("A", m, m + W)
            with np.errstate(invalid="ignore", divide="ignore"):
                spre, spos = Apre / Npre, Apos / Npos
            ok = ((spre <= .1) & (spos <= .1)) if tipo == "A->AF" else ((spre >= .9) & (spos >= .9))
            ok &= self.esf == self.esf[u]
            ok[u] = False
            for v, mm in zip(self.ev.u, self.ev.m):
                if abs(mm - m) < W:
                    ok[v] = False
            self._cand[ch] = np.where(ok)[0]
        return self._cand[ch]

    def linhas(self, k, u, m, tipo, W, unidades=None):
        """Índices dos itens da tratada e dos candidatos na janela [m−W, m+W)."""
        ch = (k, W)
        if unidades is None and ch in self._rows:
            return self._rows[ch]
        us = np.r_[u, self.candidatos(k, u, m, tipo, W)] if unidades is None else np.asarray(unidades)
        partes = []
        for v in us:
            a, b = self.ini[v], self.fim[v]
            if a == b:
                continue
            mm = self.m_arr[a:b]
            lo, hi = a + np.searchsorted(mm, m - W, "left"), a + np.searchsorted(mm, m + W, "left")
            if hi > lo:
                partes.append(np.arange(lo, hi))
        r = np.concatenate(partes) if partes else np.zeros(0, int)
        if unidades is None:
            self._rows[ch] = r
        return r

    # ----------------------------------------------------------------------------------- dispersão histórica
    def D(self, k, rows, m, W):
        """Dispersão histórica dos itens `rows` do evento k (guardada por evento, janela e mês)."""
        ch = (k, W, m)
        rows = np.asarray(rows)
        s = self._D.get(ch)
        if s is None or not np.isin(rows, s.index.to_numpy()).all():
            novos = rows if s is None else rows[~np.isin(rows, s.index.to_numpy())]
            add = pd.Series(self.disp_historica(novos, m, W).to_numpy(float), index=novos)
            s = add if s is None else pd.concat([s, add])
            self._D[ch] = s
        return s.reindex(rows).to_numpy(float)

    def disp_historica(self, rows, m, W):
        """D por item: mediana, nos até 4 trimestres inteiros anteriores a m−W, do desvio-padrão entre as outras UASGs
        (sem a do item) do log do preço médio; só trimestres com ≥ 3 outras UASGs."""
        s = m - W
        t_ult = s // 3 - 1
        tri = np.arange(t_ult - 3, t_ult + 1)
        z = self.it.loc[rows, ["u", "prod"]]
        par = z.drop_duplicates()
        par = par[par["prod"] >= 0]
        if par.empty:
            return pd.Series(np.nan, index=rows)
        grade = par.loc[par.index.repeat(len(tri))].assign(tri=np.tile(tri, len(par)))
        g1 = grade.merge(self.gu[["prod", "tri", "u", "sd_G"]], on=["prod", "tri", "u"], how="left")
        g2 = grade.merge(self.gc[["prod", "tri", "sd_cel"]], on=["prod", "tri"], how="left")
        presente = grade.merge(self.gu[["prod", "tri", "u", "n"]], on=["prod", "tri", "u"], how="left").n.notna().to_numpy()
        sd = np.where(presente, g1.sd_G.to_numpy(), g2.sd_cel.to_numpy())
        grade = grade.assign(sd=sd)
        D = grade.groupby(["u", "prod"]).sd.median()
        out = z.join(D.rename("D"), on=["u", "prod"]).D
        return out

    # ----------------------------------------------------------------------------------- um evento
    def evento(self, k, r, y, W=W0, cmin=CMIN, mascara=None, filtro_evento=None, peso_item=None, controles=None,
               bins=True, guardar_dev=False, cmin_controle=None):
        """DiD do evento k. y: coluna do desfecho do item. mascara: vetor booleano global de itens elegíveis.
        filtro_evento(base, k, rows, m, W) -> booleano por linha. peso_item(base, k, rows, m, W) -> peso por linha.
        controles: lista fixa de unidades de controle (senão, candidatos com dados suficientes)."""
        u, m, tipo = int(r.u), int(r.m), r.tipo
        cmin_c = cmin if cmin_controle is None else cmin_controle
        if controles is None:
            rows = self.linhas(k, u, m, tipo, W)
        else:
            rows = self.linhas(k, u, m, tipo, W, unidades=np.r_[u, controles])
        if len(rows) == 0:
            return None
        yv = self.it[y].to_numpy()[rows]
        ok = np.isfinite(yv)
        if mascara is not None:
            ok &= mascara[rows]
        if filtro_evento is not None:
            ok &= filtro_evento(self, k, rows, m, W)
        rows, yv = rows[ok], yv[ok]
        if len(rows) == 0:
            return None
        wi = np.ones(len(rows)) if peso_item is None else peso_item(self, k, rows, m, W)
        uu, mm, cod = self.u_arr[rows], self.m_arr[rows], self.it.cod.to_numpy()[rows]
        # médias por compra (ponderadas pelos pesos dos itens) e peso da compra = média dos pesos dos itens
        cu, inv = np.unique(cod, return_inverse=True)
        sw = np.bincount(inv, wi)
        swy = np.bincount(inv, wi * yv)
        nit = np.bincount(inv)
        yc, wc = swy / sw, sw / nit
        ucomp = np.zeros(len(cu), int); ucomp[inv] = uu
        mcomp = np.zeros(len(cu), int); mcomp[inv] = mm
        pos = (mcomp >= m).astype(int)
        uni, uinv = np.unique(ucomp, return_inverse=True)
        chave = uinv * 2 + pos
        nk = 2 * len(uni)
        S = np.bincount(chave, wc * yc, nk).reshape(-1, 2)
        Wt = np.bincount(chave, wc, nk).reshape(-1, 2)
        Ct = np.bincount(chave, None, nk).reshape(-1, 2)
        it_ct = np.bincount(np.repeat(chave, nit), None, nk).reshape(-1, 2)
        with np.errstate(invalid="ignore", divide="ignore"):
            ym = S / Wt
        d = ym[:, 1] - ym[:, 0]
        jt = np.searchsorted(uni, u)
        if jt >= len(uni) or uni[jt] != u or Ct[jt, 0] < cmin or Ct[jt, 1] < cmin:
            return None
        okc = (Ct[:, 0] >= cmin_c) & (Ct[:, 1] >= cmin_c)
        okc[jt] = False
        if controles is not None:
            okc &= np.isin(uni, controles)
        jc = np.where(okc)[0]
        if len(jc) < 5:
            return None
        out = {"k": k, "u": u, "m": m, "tipo": tipo, "sinal": 1 if tipo == "A->AF" else -1, "cnpj": self.cnpj[u],
               "delta_tratada": float(d[jt]), "delta_controles": float(d[jc].mean()), "did": float(d[jt] - d[jc].mean()),
               "n_controles": int(len(jc)), "c_pre": int(Ct[jt, 0]), "c_pos": int(Ct[jt, 1]),
               "h": float(1 / Ct[jt, 0] + 1 / Ct[jt, 1]), "itens_tratada": int(it_ct[jt].sum()),
               "compras_tratada": int(Ct[jt].sum()), "controles": uni[jc]}
        if guardar_dev:
            out["dev"] = d[jc] - d[jc].mean()
            out["h_ctrl"] = 1 / Ct[jc, 0] + 1 / Ct[jc, 1]
        if bins:
            nb = 2 * W // 3
            b = (mcomp - m) // 3
            for bb in range(-nb // 2, nb // 2):
                out[f"b{bb}"] = np.nan
            ch = uinv * nb + (b + nb // 2)
            Sb = np.bincount(ch, wc * yc, len(uni) * nb).reshape(-1, nb)
            Wb = np.bincount(ch, wc, len(uni) * nb).reshape(-1, nb)
            with np.errstate(invalid="ignore", divide="ignore"):
                yb = Sb / Wb
            iref = nb // 2 - 1
            for jb, bb in enumerate(range(-nb // 2, nb // 2)):
                if bb == -1:
                    continue
                okb = okc & np.isfinite(yb[:, jb]) & np.isfinite(yb[:, iref])
                if np.isfinite(yb[jt, jb]) and np.isfinite(yb[jt, iref]) and okb.sum() >= 5:
                    db = yb[:, jb] - yb[:, iref]
                    out[f"b{bb}"] = float(db[jt] - db[okb].mean())
        return out

    def rodar(self, eventos, y, **kw):
        res = []
        for k, r in eventos.iterrows():
            o = self.evento(k, r, y, **kw)
            if o is not None:
                res.append(o)
        return pd.DataFrame(res)


# --------------------------------------------------------------------------------------------- inferência e relato
def _pesos(df, pesos):
    if isinstance(pesos, str):
        if pesos == "iguais":
            return np.ones(len(df))
        if pesos == "precisao":
            return peso_precisao(df.h)
    w = df.k.map(pesos).to_numpy(float)                     # dict k -> peso (pesos congelados)
    return w


def estimar(df, pesos="precisao", B=9999, ic=True, base_cont=None):
    """Relato padrão: efeito do AF (média ponderada de sinal·DiD), por sentido, simetria, contagens, órgãos e pesos."""
    if df is None or len(df) < 5:
        return {"n_eventos": 0 if df is None else int(len(df))}
    df = df.copy()
    df["w"] = _pesos(df, pesos)
    df = df[np.isfinite(df.w) & df.did.notna()]
    g = df.cnpj.astype(str).to_numpy()
    y = (df.sinal * df.did).to_numpy(float)
    w = df.w.to_numpy(float)
    r = C.media_inferencia(y, g, w, B, ic=ic)
    sh = pd.Series(w).groupby(g).sum() / w.sum()
    ctrl = set()
    for c in df.controles:
        ctrl.update(np.asarray(c).tolist())
    out = {"coef_lp": 100 * r["est"], "ep_lp": 100 * r["ep"], "ic95_wcr": [100 * v for v in r.get("ic95_wild", [np.nan, np.nan])],
           "ic95_t": [100 * v for v in r["ic95_t"]], "p_wcr": r["p_wild"], "p_t": r["p_t"],
           "n_eventos": int(len(df)), "n_A->AF": int(df.tipo.eq("A->AF").sum()), "n_AF->A": int(df.tipo.eq("AF->A").sum()),
           "itens_tratadas": int(df.itens_tratada.sum()), "compras_tratadas": int(df.compras_tratada.sum()),
           "uasgs_tratadas": int(df.u.nunique()), "uasgs_controle": int(len(ctrl)), "orgaos": int(len(sh)),
           "orgaos_efetivos": float(1 / (sh ** 2).sum()), "maior_orgao_peso": float(sh.max()),
           "pesos": pesos if isinstance(pesos, str) else "congelados", "maior_evento_peso": float(w.max() / w.sum())}
    for t in ("A->AF", "AF->A"):
        mk = df.tipo.eq(t).to_numpy()
        if mk.sum() >= 5 and len(set(g[mk])) >= 3:
            rt = C.media_inferencia(df.did.to_numpy(float)[mk], g[mk], w[mk], B, ic=ic)
            out[t] = {"coef_lp": 100 * rt["est"], "ep_lp": 100 * rt["ep"], "p_wcr": rt["p_wild"],
                      "ic95_wcr": [100 * v for v in rt.get("ic95_wild", [np.nan, np.nan])]}
    if "A->AF" in out and "AF->A" in out:
        X = np.column_stack([df.tipo.eq("A->AF").astype(float), df.tipo.eq("AF->A").astype(float)])
        s = C.resumo_lin(X, df.did.to_numpy(float), g, [1.0, 1.0], w, B, ic=False)
        out["simetria_soma_lp"], out["simetria_p_wcr"] = 100 * s["est"], s["p_wild"]
    return out


def influencia(df, w):
    """Contribuições de influência por evento do estimador média ponderada de sinal·DiD."""
    y = (df.sinal * df.did).to_numpy(float)
    w = np.asarray(w, float)
    t = (w * y).sum() / w.sum()
    return t, w * (y - t) / w.sum()


def diferenca(df1, w1, df2, w2, B=9999, seed=11):
    """θ = τ(df1) − τ(df2) nos mesmos eventos (alinhados por k). EP CR1 por órgão das influências somadas; bootstrap
    selvagem não restrito (Webb) do t."""
    a = df1.set_index("k"); b = df2.set_index("k")
    ks = a.index.intersection(b.index)
    a, b = a.loc[ks], b.loc[ks]
    w1 = pd.Series(w1, index=df1.k).loc[ks].to_numpy(); w2 = pd.Series(w2, index=df2.k).loc[ks].to_numpy()
    t1, i1 = influencia(a.reset_index(), w1)
    t2, i2 = influencia(b.reset_index(), w2)
    psi = i1 - i2
    g = pd.factorize(a.cnpj.astype(str))[0]
    G = g.max() + 1
    Psi = np.bincount(g, psi, G)
    se = float(np.sqrt(G / (G - 1) * (Psi ** 2).sum()))
    th = t1 - t2
    rng = np.random.default_rng(seed)
    v = C.WEBB[rng.integers(0, 6, size=(B, G))]
    num = v @ Psi
    den = np.sqrt(G / (G - 1) * ((v * Psi) ** 2).sum(1))
    tstar = num / den
    tobs = th / se
    q = float(np.quantile(np.abs(tstar), .95))
    return {"eventos": int(len(ks)), "coef1_lp": 100 * t1, "coef2_lp": 100 * t2, "dif_lp": 100 * th, "ep_lp": 100 * se,
            "p_wcu": float(np.mean(np.abs(tstar) >= abs(tobs))), "p_t": float(2 * stats.t.sf(abs(tobs), G - 1)),
            "ic95_wcu": [100 * (th - q * se), 100 * (th + q * se)], "orgaos": int(G)}


def bins_conjunto(df, cols, pesos="precisao"):
    """Estimativas por bin e Wald conjunto com covariância por órgão (painel desbalanceado), F(q, G−1)."""
    w_all = _pesos(df, pesos)
    g = pd.factorize(df.cnpj.astype(str))[0]
    G = g.max() + 1
    est, Psi = [], []
    linhas = {}
    for c in cols:
        mk = df[c].notna().to_numpy()
        y = (df.sinal * df[c]).to_numpy(float)
        w = np.where(mk, w_all, 0.0)
        if w.sum() == 0:
            est.append(np.nan); Psi.append(np.zeros(G)); continue
        t = (w * np.nan_to_num(y)).sum() / w.sum()
        psi = np.where(mk, w * (np.nan_to_num(y) - t) / w.sum(), 0.0)
        P = np.bincount(g, psi, G)
        est.append(t); Psi.append(P)
        se = float(np.sqrt(G / (G - 1) * (P ** 2).sum()))
        tt = stats.t.ppf(.975, G - 1)
        linhas[c] = {"coef_lp": 100 * t, "ep_lp": 100 * se, "ic95_t": [100 * (t - tt * se), 100 * (t + tt * se)],
                     "p_t": float(2 * stats.t.sf(abs(t / se), G - 1)), "n_eventos": int(mk.sum())}
    Psi = np.array(Psi)
    V = G / (G - 1) * Psi @ Psi.T
    est = np.array(est)
    q = len(cols)
    try:
        F = float(est @ np.linalg.solve(V, est) / q)
        p = float(stats.f.sf(F, q, G - 1))
    except np.linalg.LinAlgError:
        F, p = np.nan, np.nan
    return {"bins": linhas, "F": F, "p": p, "q": q, "G": int(G)}
