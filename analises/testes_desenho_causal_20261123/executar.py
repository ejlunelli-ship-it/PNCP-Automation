"""Executa os testes pré-registrados do estudo de eventos por unidade compradora (protocolo.md, especificacao.json).

Uso (da pasta PNCP-Automation): python analises/testes_desenho_causal_20261123/executar.py
Lê dados/testes_desenho_causal/ (gerado por preparar.py) e grava resultados.json, eventos_did.csv e perfil.csv.
"""
import hashlib, json, sys, time

import numpy as np
import pandas as pd
from scipy import stats

import comum as C
import motor as Mo
from poder import carregar, eventos_validos

ESP = json.loads((C.AQUI / "especificacao.json").read_text(encoding="utf-8"))
W, CMIN, B = ESP["W"], ESP["cmin"], ESP["B"]
R = {"especificacao": ESP}
T0 = time.time()


def log(*a):
    print(f"[{time.time() - T0:6.0f}s]", *a, flush=True)


def cl(res, un):
    return un.cnpj.reindex(res.u).astype(str).to_numpy()


VAR = json.loads((C.AQUI / "poder.json").read_text(encoding="utf-8"))[f"W{W}_cmin{CMIN}"]["var_modelo"]
WK = {}                                                    # peso de precisão de cada evento (estudo principal)


def pesos(z, modo):
    """Pesos de precisão w_k = 1/(a + b·h_k), h_k = 1/c_pré + 1/c_pós (modelo de poder.json); 'iguais' = 1."""
    if modo == "iguais":
        return None
    if "h" in z and z.h.notna().all():
        return 1 / np.maximum(VAR["a"] + VAR["b"] * z.h.to_numpy(float), 1e-6)
    if "k" in z:
        w = z.k.map(WK).to_numpy(float)
        return np.where(np.isfinite(w), w, np.nanmedian(list(WK.values())) if WK else 1.0)
    return None


def agrega(res, un, col="did", w=None, ic=True, modo=None):
    """Médias por sentido, agregado com sinal (efeito do AF) e teste de simetria (τ_in + τ_out = 0).
    Pesos: os do protocolo (ESP['pesos']), salvo modo='iguais'."""
    z = res[res[col].notna()].copy()
    if len(z) < 5:
        return {"n": int(len(z))}
    g = cl(z, un)
    modo = modo or ESP["pesos"]
    ww = z[w].to_numpy(float) if w is not None else pesos(z, modo)
    out = {"n": int(len(z)), "n_A->AF": int(z.tipo.eq("A->AF").sum()), "n_AF->A": int(z.tipo.eq("AF->A").sum()),
           "pesos": "iguais" if ww is None else "precisao"}
    X, y = Mo.matriz_eventos(z, col, pooled=True)
    out["efeito_AF"] = C.media_inferencia(y, g, ww, B, ic=ic)
    for t in ("A->AF", "AF->A"):
        m = z.tipo.eq(t).to_numpy()
        if m.sum() >= 5 and len(set(g[m])) >= 3:
            out[t] = C.media_inferencia(z[col].to_numpy(float)[m], g[m], None if ww is None else ww[m], B, ic=ic)
    if out.get("A->AF") and out.get("AF->A"):
        X2, y2 = Mo.matriz_eventos(z, col, pooled=False)
        out["simetria_soma"] = C.resumo_lin(X2, y2, g, [1.0, 1.0], ww, B, ic=False)
    return out


def holm(ps):
    k = sorted(ps, key=lambda x: ps[x])
    m, adj, mx = len(k), {}, 0.0
    for j, key in enumerate(k):
        mx = max(mx, min(1.0, (m - j) * ps[key]))
        adj[key] = mx
    return adj


def teste_conjunto(res, un, cols):
    """Wald CR1 por CNPJ para H0: médias (com sinal) de `cols` = 0; F(q, G-1)."""
    z = res.dropna(subset=cols)
    if len(z) < 10:
        return {"n": int(len(z))}
    Y = z[cols].to_numpy(float) * z.sinal.to_numpy()[:, None]
    g = pd.factorize(pd.Series(cl(z, un)))[0]
    G, n, q = g.max() + 1, len(z), len(cols)
    mu = Y.mean(0)
    S = np.zeros((G, q))
    np.add.at(S, g, (Y - mu) / n)
    V = G / (G - 1) * S.T @ S
    Fst = float(mu @ np.linalg.solve(V, mu) / q)
    return {"n": int(n), "G": int(G), "medias": mu.tolist(), "F": Fst, "p": float(stats.f.sf(Fst, q, G - 1))}


def rr(theta, se_theta, pre, se_pre, fator):
    """Sensibilidade com magnitudes relativas (no espírito de Rambachan e Roth, 2023; versão simplificada):
    viés pós ≤ fator·M̄·m, m = maior |diferença pré| (pontual e, conservador, + 1,96 EP). IC = θ ± (viés + 1,96·EP)."""
    out = {}
    for nome, m in [("pontual", abs(pre)), ("conservador", abs(pre) + 1.96 * se_pre)]:
        lin = {}
        for Mb in (0, 0.5, 1, 1.5, 2):
            v = fator * Mb * m
            lin[str(Mb)] = [theta - v - 1.96 * se_theta, theta + v + 1.96 * se_theta]
        quebra = max(abs(theta) - 1.96 * se_theta, 0) / (fator * m) if m > 0 else float("inf")
        out[nome] = {"m": m, "IC_por_Mbarra": lin, "Mbarra_de_quebra": quebra}
    return out


# --------------------------------------------------------------------------------------------- execução
def pseudo_eventos(pn, un, n=150, seed=5):
    """Só para depurar o código antes do pré-registro: eventos fictícios em unidades estáveis (nada das que mudaram)."""
    rng = np.random.default_rng(seed)
    linhas = []
    Ce = pn.cs("C_e")
    for reg, tipo in (("A estável", "A->AF"), ("AF estável", "AF->A")):
        us = un.index[un.regime.eq(reg)].to_numpy().copy()
        rng.shuffle(us)
        for u in us[:n]:
            ms = [m for m in range(W, pn.mf - W + 1)
                  if Ce[u, m] - Ce[u, m - W] >= CMIN and Ce[u, m + W] - Ce[u, m] >= CMIN]
            if ms:
                linhas.append({"u": int(u), "m": int(rng.choice(ms)), "tipo": tipo, "esfera": un.esfera[u],
                               "cnpj": un.cnpj[u], "unidade": un.unidade[u], "estrito": True, "dist_vizinho": 999,
                               "af_antes_12": 0.0 if tipo == "A->AF" else 1.0, "af_depois_12": 1.0 if tipo == "A->AF" else 0.0})
    ev = pd.DataFrame(linhas)
    ev["m_pub0"] = ev.m
    return ev


def main(argv=None):
    global R
    depurar = "--depurar" in (argv if argv is not None else sys.argv[1:])
    pn, un, ev = carregar()
    if depurar:
        ev = pseudo_eventos(pn, un)
        R["AVISO"] = "DEPURAÇÃO: eventos fictícios em unidades estáveis; não são resultados"
    e_main = eventos_validos(ev, W)
    log("eventos candidatos", e_main.tipo.value_counts().to_dict())
    base = dict(W=W, cmin=CMIN, unid=un, ev_todos=ev)

    # 1. principal ------------------------------------------------------------------------------------------
    res, ctrl = Mo.did_eventos(pn, e_main, y="e", guardar_controles=True, **base)
    res["cnpj"] = cl(res, un)
    res["esfera"] = un.esfera.reindex(res.u).to_numpy()
    res["w_prec"] = 1 / np.maximum(VAR["a"] + VAR["b"] * res.h, 1e-6)
    WK.update(dict(zip(res.k, res.w_prec)))
    R["principal"] = agrega(res, un)
    R["principal_pesos_iguais"] = agrega(res, un, modo="iguais")
    log("principal", {k: (round(v["est"], 4), round(v["p_wild"], 4)) for k, v in R["principal"].items()
                      if isinstance(v, dict) and "est" in v})

    # 2. perfil (DID_ℓ por trimestre, base b = −1), pré-tendência, RR ---------------------------------------
    bins = [c for c in res.columns if c.startswith("b")]
    R["perfil"] = {c: agrega(res, un, c, ic=False) for c in bins}
    res["theta_perfil"] = res[[c for c in bins if int(c[1:]) >= 0]].mean(1, skipna=False)
    R["perfil_media_pos"] = agrega(res, un, "theta_perfil", ic=False)
    pre_cols = [c for c in bins if int(c[1:]) < -1]
    R["pre_tendencia"] = {"conjunto_com_sinal": teste_conjunto(res, un, pre_cols)}
    for c in pre_cols:
        R["pre_tendencia"][c] = R["perfil"][c]
    th = R["perfil_media_pos"]["efeito_AF"]
    if W == 6:
        pr = R["perfil"]["b-2"]["efeito_AF"]
        R["rambachan_roth"] = rr(th["est"], th["ep"], pr["est"], pr["ep"], fator=1.5)
    else:
        zz = res.dropna(subset=pre_cols)
        dif = np.column_stack([zz["b-4"] - zz["b-3"], zz["b-3"] - zz["b-2"], zz["b-2"]]) * zz.sinal.to_numpy()[:, None]
        mus = np.abs(dif.mean(0)); j = int(np.argmax(mus))
        se_j = float(dif[:, j].std(ddof=1) / np.sqrt(len(zz)))
        R["rambachan_roth"] = rr(th["est"], th["ep"], float(dif[:, j].mean()), se_j, fator=2.5)
    log("perfil", {c: round(R["perfil"][c]["efeito_AF"]["est"], 4) for c in bins if "efeito_AF" in R["perfil"][c]})

    # 3. inferência por aleatorização (placebo no espaço, nas datas reais) ---------------------------------
    rng = np.random.default_rng(20261123)
    ks = list(res.k)
    devs = [ctrl[k].dev.to_numpy() for k in ks]
    sig = res.sinal.to_numpy()
    tipo = res.tipo.to_numpy()
    draws = np.array([[d[rng.integers(len(d))] for d in devs] for _ in range(5000)])   # 5000 x eventos
    ri = {}
    wr = res.w_prec.to_numpy() if ESP["pesos"] == "precisao" else np.ones(len(ks))
    for nome, msk, s in [("efeito_AF", np.ones(len(ks), bool), sig), ("A->AF", tipo == "A->AF", np.ones(len(ks))),
                         ("AF->A", tipo == "AF->A", np.ones(len(ks)))]:
        ww = wr[msk] / wr[msk].sum()
        obs = float(((res.did.to_numpy() * s)[msk]) @ ww)
        nul = (draws[:, msk] * s[msk]) @ ww
        ri[nome] = {"obs": obs, "p_ri": float(np.mean(np.abs(nul) >= abs(obs))), "dp_nulo": float(nul.std()),
                    "q025": float(np.quantile(nul, .025)), "q975": float(np.quantile(nul, .975))}
    R["aleatorizacao"] = ri
    log("RI", {k: round(v["p_ri"], 4) for k, v in ri.items()})

    # 4. placebo no tempo: evento fictício 12 meses antes, com a unidade estável no modo de partida -------------
    fake = e_main.copy()
    fake["m"] = fake.m - 12
    Npre, Apre = [], []
    keep = []
    for _, r in fake.iterrows():
        m = int(r.m)
        if m - W < 0:
            keep.append(False); continue
        n1, a1 = pn.soma("N", m - W, m)[int(r.u)], pn.soma("A", m - W, m)[int(r.u)]
        n2, a2 = pn.soma("N", m, m + W)[int(r.u)], pn.soma("A", m, m + W)[int(r.u)]
        if n1 == 0 or n2 == 0:
            keep.append(False); continue
        s1, s2 = a1 / n1, a2 / n2
        keep.append((s1 <= .1 and s2 <= .1) if r.tipo == "A->AF" else (s1 >= .9 and s2 >= .9))
    fake = fake[np.array(keep, bool)]
    rf = Mo.did_eventos(pn, fake, y="e", perfil=False, **base)
    R["placebo_no_tempo_12m"] = agrega(rf, un) if len(rf) else {"n": 0}
    log("placebo no tempo", R["placebo_no_tempo_12m"].get("efeito_AF", {}).get("est"))

    # 5. desfechos placebo (não devem mudar na troca) -----------------------------------------------------
    plac = {}
    for y in ["eR", "n_itens", "srp", "excl", "sig", "eq", "mkt", "med"]:
        r = Mo.did_eventos(pn, e_main, y=y, perfil=False, **base)
        plac[y] = agrega(r, un, ic=False) if len(r) else {"n": 0}
    ps = {y: v["efeito_AF"]["p_wild"] for y, v in plac.items() if "efeito_AF" in v}
    for y, p in holm(ps).items():
        plac[y]["efeito_AF"]["p_holm"] = p
    R["desfechos_placebo"] = plac
    log("placebos", {y: (round(v["efeito_AF"]["est"], 4), round(v["efeito_AF"]["p_wild"], 3)) for y, v in plac.items()
                     if "efeito_AF" in v})

    # 6. sensibilidades do desfecho principal -----------------------------------------------------------------
    sens = {}
    W2 = 12 if W == 6 else 6
    r = Mo.did_eventos(pn, eventos_validos(ev, W2), y="e", W=W2, cmin=CMIN, unid=un, ev_todos=ev)
    sens[f"janela_{W2}m"] = agrega(r, un)
    if W2 == 12:
        b12 = [c for c in r.columns if c.startswith("b")]
        sens["janela_12m_perfil"] = {c: agrega(r, un, c, ic=False) for c in b12}
        sens["janela_12m_pre_conjunto"] = teste_conjunto(r, un, ["b-4", "b-3", "b-2"])
    sens["estritos"] = agrega(res[res.k.isin(e_main[e_main.estrito].index)], un)
    r = Mo.did_eventos(pn, e_main, y="e_c3", perfil=False, **base)
    sens["indice_truncado_3"] = agrega(r, un)
    r = Mo.did_eventos(pn, e_main, y="e", Sk="S_e_item", Ck="C_e_item", perfil=False, **base)
    sens["ponderado_por_item"] = agrega(r, un)
    sens["pesos_iguais"] = R["principal_pesos_iguais"]
    r = Mo.did_eventos(pn, e_main, y="e", W=W, cmin=3, unid=un, ev_todos=ev, perfil=False)
    sens["cmin_3"] = agrega(r, un)
    r = Mo.did_eventos(pn, e_main, y="e", controle="todos", perfil=False, **base)
    sens["controles_todas_esferas"] = agrega(r, un)
    rs = []
    for t, reg in (("A->AF", "A estável"), ("AF->A", "AF estável")):
        nunca = un.index[un.regime.eq(reg)].to_numpy()
        rs.append(Mo.did_eventos(pn, e_main[e_main.tipo.eq(t)], y="e", nunca=nunca, perfil=False, **base))
    sens["controles_nunca_mudam"] = agrega(pd.concat(rs, ignore_index=True), un)
    # antecipação: datado pela publicação do primeiro edital no novo modo
    ep = e_main[e_main.m_pub0 >= 0].copy()
    ep["m"] = ep.m_pub0
    r = Mo.did_eventos(pn, ep, y="e", Sk="S_e_pub", Ck="C_e_pub", reg=("N_pub", "A_pub"), perfil=False, **base)
    sens["antecipacao_data_publicacao"] = agrega(r, un)
    # composição: só produtos comprados nas duas meias janelas pela mesma unidade
    sens["composicao_mesmos_produtos"] = composicao(res, ctrl, un)
    # primeiro estágio e Wald (efeito por 100 p.p. de AF)
    R["primeiro_estagio"] = agrega(res, un, "primeiro_estagio", ic=False)
    R["wald"] = wald(res)
    R["sensibilidades"] = sens
    log("sensibilidades", {k: round(v["efeito_AF"]["est"], 4) for k, v in sens.items() if isinstance(v, dict) and "efeito_AF" in v})

    # 7. imputação (Borusyak, Jaravel e Spiess) no nível do item ---------------------------------------------
    R["imputacao_bjs"] = bjs(res, e_main, un, ESP.get("bjs_celula", "mes"))
    outra = "tri" if ESP.get("bjs_celula", "mes") == "mes" else "mes"
    R["imputacao_bjs_celula_" + outra] = bjs(res, e_main, un, outra)
    log("BJS", R["imputacao_bjs"].get("evento", {}).get("efeito_AF", {}).get("est"),
        R["imputacao_bjs_celula_" + outra].get("evento", {}).get("efeito_AF", {}).get("est"))

    # 8. matching de unidades + DiD (PanelMatch) e DiD sintético ------------------------------------------------
    R["panelmatch"] = panelmatch(pn, res, ctrl, un)
    R["sdid"] = {f"W{w_}": sdid_eventos(pn, ev, un, w_) for w_ in (6, 12)}
    log("PanelMatch/SDID", {k: v.get("efeito_AF", {}).get("est") for k, v in R["panelmatch"].items()},
        {k: v.get("efeito_AF", {}).get("est") for k, v in R["sdid"].items()})

    # 9. desfechos secundários e limites de Lee --------------------------------------------------------------
    sec = {}
    for y in ["suc", "fra", "des", "prazo", "desc", "novo"]:
        r = Mo.did_eventos(pn, e_main, y=y, perfil=False, **base)
        sec[y] = agrega(r, un) if len(r) else {"n": 0}
    ps = {y: v["efeito_AF"]["p_wild"] for y, v in sec.items() if "efeito_AF" in v}
    for y, p in holm(ps).items():
        sec[y]["efeito_AF"]["p_holm"] = p
    R["desfechos_secundarios"] = sec
    R["limites_lee"] = lee(res, e_main, un, sec)
    log("secundários", {y: (round(v["efeito_AF"]["est"], 4), round(v["efeito_AF"]["p_wild"], 3)) for y, v in sec.items()
                        if "efeito_AF" in v})

    # 10. heterogeneidade (exploratória) ----------------------------------------------------------------------
    het = {}
    with np.errstate(invalid="ignore", divide="ignore"):
        comp = np.array([pn.soma("S_comp", m - W, m)[u] / pn.soma("C_comp", m - W, m)[u] for u, m in zip(res.u, res.m)])
    res["comp_pre"] = comp
    med = np.nanmedian(comp)
    for nome, msk in [("competicao_esperada_baixa", res.comp_pre <= med), ("competicao_esperada_alta", res.comp_pre > med),
                      ("federal", res.esfera.eq("F")), ("nao_federal", ~res.esfera.eq("F"))]:
        het[nome] = agrega(res[msk], un, ic=False)
    res["alta"] = (res.comp_pre > med).astype(float)
    z = res.dropna(subset=["comp_pre"])
    X = np.column_stack([np.ones(len(z)), z.alta])
    het["diferenca_alta_menos_baixa"] = C.resumo_lin(X, (z.sinal * z.did).to_numpy(), cl(z, un), [0.0, 1.0],
                                                     pesos(z, ESP["pesos"]), B, ic=False)
    het["mediana_comp_log1p"] = float(med)
    R["heterogeneidade"] = het

    # saídas -------------------------------------------------------------------------------------------------------
    suf = "_depuracao" if depurar else ""
    pasta = C.DADOS if depurar else C.AQUI
    res.drop(columns=["w_prec"], errors="ignore").to_csv(pasta / f"eventos_did{suf}.csv", index=False)
    R["tempo_s"] = round(time.time() - T0)
    (pasta / f"resultados{suf}.json").write_text(json.dumps(R, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    log("FIM ok")


# --------------------------------------------------------------------------------------------- blocos
def itens_janela():
    i = pd.read_pickle(C.DADOS / "itens.pkl")[["compra", "u", "m", "prod", "e_ok", "logp", "hom", "final"]]
    return i


_ITENS = {}


def itens():
    if "i" not in _ITENS:
        _ITENS["i"] = itens_janela()
    return _ITENS["i"]


def composicao(res, ctrl, un):
    """Só itens de produtos que a unidade comprou nas duas meias janelas (≥ 2 compras em cada meia janela)."""
    i = itens()
    i = i[i.e_ok.notna()]
    linhas = []
    for _, r in res.iterrows():
        k, u, m = r.k, int(r.u), int(r.m)
        us = np.r_[u, ctrl[k].u.to_numpy()]
        z = i[(i.m >= m - W) & (i.m < m + W) & i.u.isin(us)].copy()
        z["pos"] = z.m >= m
        amb = z.groupby(["u", "prod"]).pos.agg(["min", "max"])
        amb = amb[(amb["min"] == False) & (amb["max"] == True)].index
        z = z.set_index(["u", "prod"]).loc[lambda x: x.index.isin(amb)].reset_index()
        cpm = z.groupby(["u", "pos", "compra"], observed=True).e_ok.mean().reset_index()
        um = cpm.groupby(["u", "pos"]).e_ok.agg(["mean", "size"]).unstack("pos")
        if u not in um.index:
            continue
        um = um.dropna()
        um = um[(um[("size", False)] >= 2) & (um[("size", True)] >= 2)]
        if u not in um.index or len(um) < 6:
            continue
        d = um[("mean", True)] - um[("mean", False)]
        linhas.append({"k": k, "u": u, "tipo": r.tipo, "sinal": r.sinal, "did": float(d[u] - d.drop(u).mean())})
    return agrega(pd.DataFrame(linhas), un) if linhas else {"n": 0}


def wald(res):
    """Efeito por 100 p.p. de AF: Σ sinal·DiD / Σ sinal·primeiro estágio; bootstrap por CNPJ (pares), B = 1999."""
    z = res.dropna(subset=["did", "primeiro_estagio"])
    num, den = (z.sinal * z.did).to_numpy(), (z.sinal * z.primeiro_estagio).to_numpy()
    g = pd.factorize(z.cnpj)[0]
    G = g.max() + 1
    est = num.mean() / den.mean()
    rng = np.random.default_rng(7)
    sn, sd_, cnt = np.bincount(g, num, G), np.bincount(g, den, G), np.bincount(g, minlength=G)
    bs = []
    for _ in range(1999):
        d = rng.integers(0, G, G)
        bs.append(sn[d].sum() / sd_[d].sum())
    bs = np.array(bs)
    out = {"est": float(est), "ep_boot": float(bs.std()), "ic95_percentil": [float(np.quantile(bs, .025)), float(np.quantile(bs, .975))],
           "primeiro_estagio_medio": float(den.mean())}
    for t in ("A->AF", "AF->A"):
        m = z.tipo.eq(t).to_numpy()
        out[t] = {"est": float(z.did[m].mean() / z.primeiro_estagio[m].mean()), "primeiro_estagio": float(z.primeiro_estagio[m].mean())}
    return out


def _fe2(y, g1, g2, iters=500, tol=1e-9):
    """y = a[g1] + b[g2] + e (projeções alternadas)."""
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


def bjs(res, e_main, un, celula="mes", min_cel=3):
    """Imputação: log P = α_g + γ_{produto, mês} estimados nos itens não tratados; g = unidade estável ou janela do evento.
    Não tratados (A->AF): itens das compras Aberto das unidades 'A estável' e pré-janela das unidades que mudam.
    Tratados: pós-janela das unidades que mudam (todas as compras: intenção de tratar). Idem com AF para AF->A."""
    i = itens()
    i = i[i.e_ok.notna()][["compra", "u", "m", "prod", "logp"]]
    comp = pd.read_pickle(C.DADOS / "compras.pkl")[["compra", "af"]]
    af = pd.Series(comp.af.to_numpy(), index=comp.compra.astype(str))
    i = i.assign(af=af.reindex(i.compra.astype(str)).to_numpy())
    out = {"por_sentido": {}}
    linhas = []
    for t, reg, modo in (("A->AF", "A estável", 0), ("AF->A", "AF estável", 1)):
        est = un.index[un.regime.eq(reg)].to_numpy()
        est = est[~np.isin(est, res.u.to_numpy())]            # unidades com evento nunca entram como estáveis
        nt = i[i.u.isin(est) & i.af.eq(modo)].assign(g=lambda x: "u" + x.u.astype(str), fase="nt")
        evs = res[res.tipo.eq(t)]
        partes = [nt]
        for _, r in evs.iterrows():
            m, u = int(r.m), int(r.u)
            z = i[(i.u == u) & (i.m >= m - W) & (i.m < m + W)].copy()
            z["g"] = f"k{r.k}"
            z["fase"] = np.where(z.m >= m, "trat", "pre")
            z["k"] = r.k
            z["bin"] = (z.m - m) // 3
            partes.append(z)
        d = pd.concat(partes, ignore_index=True)
        d["pm"] = d["prod"].astype(np.int64) * 100 + (d.m if celula == "mes" else d.m // 3)
        und = d[d.fase.ne("trat")]
        g1 = pd.factorize(und.g)[0]
        pm_cod, pm_uni = pd.factorize(und.pm)
        a, b = _fe2(und.logp.to_numpy(float), g1, pm_cod)
        cnt = np.bincount(pm_cod)
        tr = d[d.fase.eq("trat")].copy()
        gi = pd.Index(pd.factorize(und.g)[1]).get_indexer(tr.g)
        pi = pd.Index(pm_uni).get_indexer(tr.pm)
        okt = (gi >= 0) & (pi >= 0)
        okt[okt] &= cnt[pi[okt]] >= min_cel
        tr = tr[okt]
        tr["tau"] = tr.logp.to_numpy() - a[gi[okt]] - b[pi[okt]]
        # pré-tendência: resíduos dos itens pré-janela, bin −2 menos bin −1
        pre = und[und.fase.eq("pre")].copy()
        pre["res"] = pre.logp.to_numpy() - a[g1[und.fase.eq("pre").to_numpy()]] - b[pm_cod[und.fase.eq("pre").to_numpy()]]
        for k, z in tr.groupby("k"):
            cm = z.groupby("compra", observed=True).tau.mean()
            p = pre[pre.k == k]
            pb = p.groupby(["bin", "compra"], observed=True).res.mean().groupby("bin").mean()
            lead = float(pb.get(-2, np.nan) - pb.get(-1, np.nan)) if W == 6 else np.nan
            linhas.append({"k": k, "u": int(z.u.iloc[0]), "tipo": t, "sinal": 1 if t == "A->AF" else -1,
                           "did": float(cm.mean()), "did_item": float(z.tau.mean()), "lead": lead, "itens": len(z)})
        out["por_sentido"][t] = {"itens_nao_tratados": int(len(und)), "itens_tratados_imputados": int(len(tr)),
                                 "itens_tratados_sem_celula": int((~okt).sum())}
    df = pd.DataFrame(linhas)
    out["evento"] = agrega(df, un)
    out["ponderado_por_item"] = agrega(df.assign(did=df.did_item), un, ic=False)
    out["pre_tendencia_bin-2"] = agrega(df.assign(did=df.lead), un, ic=False)
    return out


def panelmatch(pn, res, ctrl, un, J=5):
    """Imai, Kim e Wang (2023): conjunto pareado = controles limpos (mesmo histórico de modo); refinamento pelos J
    vizinhos mais próximos (distância euclidiana padronizada) em covariáveis anteriores; mesma região se houver ≥ J."""
    reg = un.regiao.reindex(range(pn.U)).to_numpy()
    out = {}
    for nome, com_def in (("sem_defasagens_do_desfecho", False), ("com_defasagens_do_desfecho", True)):
        linhas = []
        for _, r in res.iterrows():
            k, u, m = r.k, int(r.u), int(r.m)
            cand = ctrl[k].u.to_numpy()
            with np.errstate(invalid="ignore", divide="ignore"):
                cov = [pn.soma("S_eR", m - W, m) / pn.soma("C_eR", m - W, m),
                       np.log1p(pn.soma("N", m - W, m)),
                       pn.soma("S_med", m - W, m) / pn.soma("C_med", m - W, m),
                       pn.soma("S_mkt", m - W, m) / pn.soma("C_mkt", m - W, m),
                       pn.soma("S_comp", m - W, m) / pn.soma("C_comp", m - W, m),
                       pn.soma("S_n_itens", m - W, m) / pn.soma("C_n_itens", m - W, m)]
                if com_def:
                    for b in range(-W // 3, 0):
                        cov.append(pn.soma("S_e", m + 3 * b, m + 3 * b + 3) / pn.soma("C_e", m + 3 * b, m + 3 * b + 3))
            Xc = np.column_stack([c[cand] for c in cov]); xt = np.array([c[u] for c in cov])
            usar = np.isfinite(xt)
            Xc, xt = Xc[:, usar], xt[usar]
            okc = np.isfinite(Xc).all(1)
            cand, Xc = cand[okc], Xc[okc]
            mr = reg[cand] == reg[u]
            if mr.sum() >= J:
                cand, Xc = cand[mr], Xc[mr]
            if len(cand) < J:
                continue
            sd = Xc.std(0); sd[sd == 0] = 1
            dist = np.sqrt((((Xc - xt) / sd) ** 2).sum(1))
            viz = cand[np.argsort(dist)[:J]]
            Spre, Cpre = pn.soma("S_e", m - W, m), pn.soma("C_e", m - W, m)
            Spos, Cpos = pn.soma("S_e", m, m + W), pn.soma("C_e", m, m + W)
            d = Spos / np.maximum(Cpos, 1) - Spre / np.maximum(Cpre, 1)
            linhas.append({"k": k, "u": u, "tipo": r.tipo, "sinal": r.sinal, "did": float(d[u] - d[viz].mean())})
        out[nome] = agrega(pd.DataFrame(linhas), un)
    return out


def sdid_eventos(pn, ev, un, Wq):
    """DiD sintético (Arkhangelsky et al., 2021) por evento, em trimestres de evento; unidades com compra em todos os
    trimestres da janela (unidades grandes). Doadores: controles limpos da mesma esfera, também completos."""
    e = eventos_validos(ev, Wq)
    base_res, ctrl = Mo.did_eventos(pn, e, y="e", W=Wq, cmin=CMIN, unid=un, ev_todos=ev, guardar_controles=True, perfil=False)
    nb = 2 * Wq // 3
    linhas = []
    for _, r in base_res.iterrows():
        k, u, m = r.k, int(r.u), int(r.m)
        Y, Cn = [], []
        for b in range(-nb // 2, nb // 2):
            a0 = m + 3 * b
            S_, C_ = pn.soma("S_e", a0, a0 + 3), pn.soma("C_e", a0, a0 + 3)
            with np.errstate(invalid="ignore", divide="ignore"):
                Y.append(S_ / C_)
            Cn.append(C_)
        Y, Cn = np.array(Y).T, np.array(Cn).T                 # U x T
        if (Cn[u] < 1).any():
            continue
        don = ctrl[k].u.to_numpy()
        don = don[(Cn[don] >= 1).all(1)]
        if len(don) < 10:
            continue
        tau, om, la = Mo.sdid(np.vstack([Y[don], Y[u]]), nb // 2)
        linhas.append({"k": k, "u": u, "tipo": r.tipo, "sinal": r.sinal, "did": tau, "doadores": len(don),
                       "peso_max": float(om.max())})
    df = pd.DataFrame(linhas)
    out = agrega(df, un) if len(df) else {"n": 0}
    if len(df):
        out["doadores_medios"] = float(df.doadores.mean())
        out["peso_maximo_medio"] = float(df.peso_max.mean())
    return out


def lee(res, e_main, un, sec):
    """Limites de Lee (2009) para a seleção por sucesso: se a troca muda a taxa de homologação em Δs (DiD de 'suc'),
    apara-se a fração p = |Δs|/s do lado com mais sucesso (pós-janela da tratada se Δs·sinal > 0) no topo ou na base da
    distribuição do índice de preço e recalcula-se o DiD."""
    i = itens()
    out = {}
    for t in ("A->AF", "AF->A"):
        if t not in sec["suc"] or "est" not in sec["suc"][t]:
            continue
        ds = sec["suc"][t]["est"]
        evs = res[res.tipo.eq(t)]
        linhas_lo, linhas_hi, srates = [], [], []
        for _, r in evs.iterrows():
            u, m = int(r.u), int(r.m)
            z = i[(i.u == u) & (i.m >= m - W) & (i.m < m + W)]
            pos = z.m >= m
            s_pos = z.loc[pos & z.final, "hom"].mean()
            s_pre = z.loc[~pos & z.final, "hom"].mean()
            srates.append((s_pre, s_pos))
        sp = np.nanmean([s[1] for s in srates]); sr = np.nanmean([s[0] for s in srates])
        lado_pos = ds > 0
        p = abs(ds) / (sp if lado_pos else sr)
        for _, r in evs.iterrows():
            u, m = int(r.u), int(r.m)
            z = i[(i.u == u) & (i.m >= m - W) & (i.m < m + W) & i.e_ok.notna()].copy()
            z["pos"] = z.m >= m
            alvo = z.pos if lado_pos else ~z.pos
            q_lo, q_hi = z.loc[alvo, "e_ok"].quantile([p, 1 - p]) if alvo.sum() > 3 else (np.nan, np.nan)
            res_lo, res_hi = [], []
            for nome, filtro in (("lo", ~alvo | (z.e_ok <= q_hi)), ("hi", ~alvo | (z.e_ok >= q_lo))):
                zz = z[filtro]
                cm = zz.groupby(["pos", "compra"], observed=True).e_ok.mean().groupby("pos").mean()
                if True in cm.index and False in cm.index:
                    dlt = cm[True] - cm[False]
                    (linhas_lo if nome == "lo" else linhas_hi).append(
                        {"k": r.k, "u": u, "tipo": t, "sinal": r.sinal, "did": float(dlt - r.delta_controles)})
        lo, hi = pd.DataFrame(linhas_lo), pd.DataFrame(linhas_hi)
        if len(lo) and len(hi):
            a_, b_ = float(lo.did.mean()), float(hi.did.mean())
            out[t] = {"delta_sucesso": ds, "fracao_aparada": float(p), "lado_aparado": "pós" if lado_pos else "pré",
                      "n": int(min(len(lo), len(hi))), "limites": [min(a_, b_), max(a_, b_)],
                      "estimativa_sem_aparar": float(evs.did.mean())}
    if "A->AF" in out and "AF->A" in out:
        ni, no = out["A->AF"]["n"], out["AF->A"]["n"]
        Li, Ui = out["A->AF"]["limites"]; Lo, Uo = out["AF->A"]["limites"]
        out["efeito_AF"] = {"limites": [(ni * Li - no * Uo) / (ni + no), (ni * Ui - no * Lo) / (ni + no)]}
    return out


if __name__ == "__main__":
    main()
