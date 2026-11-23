"""Comando único dos 15 testes de robustez da dispersão (protocolo.md). Todos EXPLORATÓRIOS.

Uso (da pasta PNCP-Automation):
    python analises/robustez_dispersao_20261123/preparar_descricoes.py --pncp-db ../dados/pncp.db   # uma vez (teste 08)
    python analises/robustez_dispersao_20261123/executar_todos.py

Lê a base de 23/11 (dados/testes_desenho_causal/) e dados/robustez_dispersao/descricoes_catmat.pkl; não lê o pncp.db.
Grava tabelas/*.csv, resultados.json, registro_execucao.json e, ao final, chama graficos.py.
"""
import hashlib, json, os, sys, time, traceback
from pathlib import Path

sys.dont_write_bytecode = True
AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

import motor_robustez as MR  # noqa: E402  (coloca a pasta de 23/11 no caminho)
import comum as C  # noqa: E402
from preparar import norm_un  # noqa: E402

LIMITE = int(os.environ.get("ROBUSTEZ_LIMITE_EVENTOS", "0"))      # só para teste rápido do código
SAIDA = (MR.CACHE / "teste_rapido") if LIMITE else AQUI
TAB = SAIDA / "tabelas"
TAB.mkdir(parents=True, exist_ok=True)
T0 = time.time()
B_BOOT = 9999
REG = {"inicio": time.strftime("%Y-%m-%d %H:%M:%S"),
       "protocolo_sha256": hashlib.sha256((AQUI / "protocolo.md").read_bytes()).hexdigest(),
       "parametros": {"W": MR.W0, "cmin": MR.CMIN, "limite_dispersao": MR.LIM, "faixas": MR.FAIXAS,
                      "var_a": MR.VAR_A, "var_b": MR.VAR_B, "B": B_BOOT},
       "testes": {}, "exclusoes": {}, "conferencias": {}}
R = {}
TODAS = []
S = {}


def log(*a):
    print(f"[{time.time() - T0:6.0f}s]", *a, flush=True)


def linha(teste, modelo, est, **extra):
    """Linha padrão: coeficiente, EP, IC, p, itens, compras, eventos, UASGs, órgãos, órgãos efetivos, pesos."""
    d = {"teste": teste, "modelo": modelo}
    if est is None or est.get("n_eventos", 0) == 0:
        d["observacao"] = "sem eventos suficientes"
    else:
        for c in ["coef_lp", "ep_lp", "p_wcr", "p_t", "n_eventos", "n_A->AF", "n_AF->A", "itens_tratadas",
                  "compras_tratadas", "uasgs_tratadas", "uasgs_controle", "orgaos", "orgaos_efetivos", "maior_orgao_peso",
                  "maior_evento_peso", "pesos"]:
            d[c] = est.get(c)
        d["ic95_wcr_inf"], d["ic95_wcr_sup"] = (est.get("ic95_wcr") or [np.nan, np.nan])
        d["ic95_t_inf"], d["ic95_t_sup"] = (est.get("ic95_t") or [np.nan, np.nan])
        for t in ("A->AF", "AF->A"):
            if t in est:
                d[f"{t}_coef_lp"], d[f"{t}_p_wcr"] = est[t]["coef_lp"], est[t]["p_wcr"]
        d["simetria_soma_lp"], d["simetria_p_wcr"] = est.get("simetria_soma_lp"), est.get("simetria_p_wcr")
    d.update(extra)
    TODAS.append(d)
    return d


def salvar(nome, linhas):
    pd.DataFrame(linhas).to_csv(TAB / f"{nome}.csv", index=False, encoding="utf-8", lineterminator="\n")


def eventos_csv(nome, df):
    df.drop(columns=[c for c in ("controles", "dev", "h_ctrl") if c in df.columns]).to_csv(
        TAB / f"eventos_{nome}.csv", index=False, encoding="utf-8", lineterminator="\n")


def executar(nome, fn):
    t = time.time()
    try:
        fn()
        REG["testes"][nome] = {"status": "ok", "segundos": round(time.time() - t, 1)}
        log(nome, "ok")
    except Exception as e:  # registra e segue
        REG["testes"][nome] = {"status": "falha", "erro": repr(e), "traceback": traceback.format_exc(),
                               "segundos": round(time.time() - t, 1)}
        log(nome, "FALHA", repr(e))


def pesos_de(df):
    return dict(zip(df.k, MR.peso_precisao(df.h)))


def sub(df, ks):
    return df[df.k.isin(ks)].copy()


# --------------------------------------------------------------------------------------------- filtros
def f_hist_baixa(B, k, rows, m, W):
    D = B.D(k, rows, m, W)
    return np.nan_to_num(D, nan=np.inf) <= MR.LIM


def f_hist_alta(B, k, rows, m, W):
    D = B.D(k, rows, m, W)
    return np.isfinite(D) & (D > MR.LIM)


def f_hist_def(B, k, rows, m, W):
    return np.isfinite(B.D(k, rows, m, W))


def f_faixa(lo, hi):
    def f(B, k, rows, m, W):
        D = B.D(k, rows, m, W)
        return np.isfinite(D) & (D > lo) & (D <= hi)
    return f


def w_continuo(B, k, rows, m, W):
    """Peso do item (protocolo, teste 07): 1/D̃², D̃ = min(max(D, 0,20), 1,50)."""
    D = B.D(k, rows, m, W)
    Dt = np.clip(np.nan_to_num(D, nan=1.5), 0.20, 1.50)
    return 1 / Dt ** 2


# --------------------------------------------------------------------------------------------- testes
def t00():
    B = S["B"]
    S["E6"], S["E12"] = B.eventos(6), B.eventos(12)
    if LIMITE:
        S["E6"], S["E12"] = S["E6"].head(LIMITE), S["E12"].head(LIMITE)
    S["mask_f"] = (B.it.sd_G <= MR.LIM).to_numpy()
    S["M0"] = B.rodar(S["E6"], "e_ok", guardar_dev=True)
    S["M1"] = B.rodar(S["E6"], "e_G", mascara=S["mask_f"], guardar_dev=True)
    S["w0"], S["w1"] = pesos_de(S["M0"]), pesos_de(S["M1"])
    r0, r1 = MR.estimar(S["M0"], B=B_BOOT), MR.estimar(S["M1"], B=B_BOOT)
    S["r_M0"], S["r_M1"] = r0, r1
    ok0 = abs(r0["coef_lp"] + 1.91) < 0.01 and abs(r0["ic95_wcr"][0] + 5.67) < 0.01 and abs(r0["ic95_wcr"][1] - 1.93) < 0.01
    ok1 = abs(r1["coef_lp"] + 3.76) < 0.01 and abs(r1["ic95_wcr"][0] + 6.67) < 0.01 and abs(r1["ic95_wcr"][1] + 0.89) < 0.01
    REG["conferencias"]["reproduz_M0"] = {"ok": bool(ok0), "coef": r0["coef_lp"], "ic": r0["ic95_wcr"], "eventos": r0["n_eventos"]}
    REG["conferencias"]["reproduz_M1"] = {"ok": bool(ok1), "coef": r1["coef_lp"], "ic": r1["ic95_wcr"], "eventos": r1["n_eventos"],
                                          "eventos_tambem_no_M0": int(S["M1"].k.isin(S["M0"].k).sum())}
    rows = [linha("00", "M0 original (A, todas as células)", r0), linha("00", "M1 filtrado (G, dispersão ≤ 0,80)", r1)]
    salvar("t00_reproducao", rows)
    eventos_csv("M0", S["M0"]); eventos_csv("M1", S["M1"])
    R["t00"] = {"M0": r0, "M1": r1}


def t01():
    M0, M1 = S["M0"], S["M1"]
    ks = sorted(set(M0.k) & set(M1.k))
    a, b = sub(M0, ks), sub(M1, ks)
    ra, rb = MR.estimar(a, B=B_BOOT), MR.estimar(b, B=B_BOOT)
    d = MR.diferenca(b, MR.peso_precisao(b.h), a, MR.peso_precisao(a.h), B=B_BOOT)
    rows = [linha("01", "M0 nos eventos comuns", ra), linha("01", "M1 nos eventos comuns", rb)]
    rows.append({"teste": "01", "modelo": "diferença M1 − M0 (eventos comuns)", "coef_lp": d["dif_lp"], "ep_lp": d["ep_lp"],
                 "ic95_wcu_inf": d["ic95_wcu"][0], "ic95_wcu_sup": d["ic95_wcu"][1], "p_wcu": d["p_wcu"], "p_t": d["p_t"],
                 "n_eventos": d["eventos"], "orgaos": d["orgaos"], "pesos": "precisão de cada modelo"})
    TODAS.append(rows[-1])
    REG["exclusoes"]["t01"] = {"M0_fora_da_comum": int((~M0.k.isin(ks)).sum()), "M1_fora_da_comum": int((~M1.k.isin(ks)).sum())}
    salvar("t01_amostra_comum", rows)
    R["t01"] = {"M0": ra, "M1": rb, "diferenca": d}


def t02():
    B, E6, mf = S["B"], S["E6"], S["mask_f"]
    S["A_f"] = B.rodar(E6, "e_ok", mascara=mf)
    S["G_all"] = B.rodar(E6, "e_G", guardar_dev=True)
    mods = {"A, todas": S["M0"], "A, ≤ 0,80": S["A_f"], "G, todas": S["G_all"], "G, ≤ 0,80": S["M1"]}
    ks = sorted(set.intersection(*[set(m.k) for m in mods.values()]))
    rows, out = [], {}
    for pnome, pesos in (("pesos congelados de M0", S["w0"]), ("pesos iguais", "iguais")):
        base = sub(mods["A, todas"], ks)
        wb = np.array([S["w0"][k] for k in base.k]) if pnome.startswith("pesos congelados") else np.ones(len(base))
        for nome, df in mods.items():
            z = sub(df, ks)
            r = MR.estimar(z, pesos=pesos, B=B_BOOT)
            wz = np.array([S["w0"][k] for k in z.k]) if pnome.startswith("pesos congelados") else np.ones(len(z))
            dif = MR.diferenca(z, wz, base, wb, B=B_BOOT) if nome != "A, todas" else None
            rows.append(linha("02", f"{nome} — {pnome}", r, dif_vs_original_lp=None if dif is None else dif["dif_lp"],
                              dif_ep_lp=None if dif is None else dif["ep_lp"], dif_p_wcu=None if dif is None else dif["p_wcu"]))
            out[f"{nome} — {pnome}"] = {"estimativa": r, "diferenca_vs_A_todas": dif}
    REG["exclusoes"]["t02"] = {"eventos_comuns_as_quatro": len(ks)}
    salvar("t02_pesos_fixos", rows)
    R["t02"] = out


def t03():
    B, E6, mf = S["B"], S["E6"], S["mask_f"]
    rows, out = [], {}
    for ref, base, y in (("A", S["M0"], "e_ok"), ("G", S["G_all"], "e_G")):
        filt, fr, perdidos = [], [], 0
        for _, r in base.iterrows():
            o = B.evento(r.k, E6.loc[r.k], y, mascara=mf, controles=np.asarray(r.controles), cmin=1, cmin_controle=1,
                         bins=False)
            if o is None:
                perdidos += 1
                continue
            o["frac_controles_mantidos"] = o["n_controles"] / r.n_controles
            filt.append(o)
        df_f = pd.DataFrame(filt)
        base_r = sub(base, df_f.k)
        w = {k: MR.peso_precisao([h])[0] for k, h in zip(base.k, base.h)}
        rb, rf = MR.estimar(base_r, pesos=w, B=B_BOOT), MR.estimar(df_f, pesos=w, B=B_BOOT)
        wv = np.array([w[k] for k in df_f.k])
        d = MR.diferenca(df_f, wv, base_r, np.array([w[k] for k in base_r.k]), B=B_BOOT)
        rows.append(linha("03", f"ref. {ref}: todas as células (controles e pesos do modelo base)", rb))
        rows.append(linha("03", f"ref. {ref}: só células ≤ 0,80, mesmos controles, janelas e pesos", rf,
                          frac_controles_mantidos_media=float(df_f.frac_controles_mantidos.mean()),
                          eventos_perdidos=perdidos, dif_lp=d["dif_lp"], dif_ep_lp=d["ep_lp"], dif_p_wcu=d["p_wcu"]))
        out[ref] = {"base": rb, "filtrado": rf, "diferenca": d, "eventos_perdidos": perdidos,
                    "frac_controles_mantidos_media": float(df_f.frac_controles_mantidos.mean())}
        REG["exclusoes"][f"t03_{ref}"] = {"eventos_perdidos": perdidos,
                                          "frac_controles_mantidos_media": float(df_f.frac_controles_mantidos.mean())}
    salvar("t03_controles_identicos", rows)
    R["t03"] = out


def t04():
    B, E6 = S["B"], S["E6"]
    S["T4"] = B.rodar(E6, "e_G", filtro_evento=f_hist_baixa, guardar_dev=True)
    r = MR.estimar(S["T4"], B=B_BOOT)
    S["r_T4"] = r
    # cobertura da dispersão histórica nas janelas das tratadas
    cob, todos_D, todos_c = [], [], []
    for _, ev in S["T4"].iterrows():
        rows = B.linhas(ev.k, ev.u, ev.m, ev.tipo, 6)
        rt = rows[B.u_arr[rows] == ev.u]
        rt = rt[np.isfinite(B.it.e_G.to_numpy()[rt])]
        D = B.D(ev.k, rt, ev.m, 6)
        sdc = B.it.sd_G.to_numpy()[rt]
        todos_D.append(D)
        todos_c.append(sdc)
        cob.append({"k": ev.k, "itens_G": len(rt), "com_D": int(np.isfinite(D).sum()), "D_ate_lim": int((D <= MR.LIM).sum()),
                    "contemp_ate_lim": int((sdc <= MR.LIM).sum()),
                    "concordancia": float(np.mean((D <= MR.LIM)[np.isfinite(D) & np.isfinite(sdc)] ==
                                                  (sdc <= MR.LIM)[np.isfinite(D) & np.isfinite(sdc)])) if np.isfinite(D).any() else np.nan})
    cob = pd.DataFrame(cob)
    cob.to_csv(TAB / "t04_cobertura_dispersao_historica.csv", index=False, encoding="utf-8", lineterminator="\n")
    Dh, Dc = np.concatenate(todos_D), np.concatenate(todos_c)
    bordas = np.r_[np.arange(0, 2.51, 0.1), np.inf]
    hist = pd.DataFrame({"faixa_ini": bordas[:-1], "faixa_fim": bordas[1:],
                         "contemporanea": np.histogram(Dc[np.isfinite(Dc)], bordas)[0],
                         "historica": np.histogram(Dh[np.isfinite(Dh)], bordas)[0]})
    hist.to_csv(TAB / "t04_histograma_dispersao.csv", index=False, encoding="utf-8", lineterminator="\n")
    REG["exclusoes"]["t04_itens_tratadas_sem_dispersao"] = {"sem_historica": int((~np.isfinite(Dh)).sum()),
                                                           "sem_contemporanea": int((~np.isfinite(Dc)).sum())}
    ks = sorted(set(S["T4"].k) & set(S["M1"].k))
    d = MR.diferenca(sub(S["T4"], ks), MR.peso_precisao(sub(S["T4"], ks).h), sub(S["M1"], ks),
                     MR.peso_precisao(sub(S["M1"], ks).h), B=B_BOOT)
    rows = [linha("04", "G, dispersão pré-tratamento ≤ 0,80", r, dif_vs_M1_lp=d["dif_lp"], dif_ep_lp=d["ep_lp"],
                  dif_p_wcu=d["p_wcu"], eventos_tambem_no_M0=int(S["T4"].k.isin(S["M0"].k).sum()),
                  itens_G_tratadas=int(cob.itens_G.sum()), frac_com_D=float(cob.com_D.sum() / cob.itens_G.sum()),
                  frac_D_ate_lim=float(cob.D_ate_lim.sum() / cob.itens_G.sum()),
                  concordancia_com_contemporanea=float(np.nanmean(cob.concordancia)))]
    REG["exclusoes"]["t04"] = {"itens_G_tratadas": int(cob.itens_G.sum()), "sem_D": int(cob.itens_G.sum() - cob.com_D.sum()),
                               "com_D_acima_do_limite": int(cob.com_D.sum() - cob.D_ate_lim.sum())}
    salvar("t04_dispersao_pre_tratamento", rows)
    eventos_csv("T4", S["T4"])
    R["t04"] = {"estimativa": r, "diferenca_vs_M1": d}


def t05():
    B, E6 = S["B"], S["E6"]
    alta = B.rodar(E6, "e_G", filtro_evento=f_hist_alta, bins=False)
    baixa = S["T4"]
    ks = sorted(set(alta.k) & set(baixa.k) & set(S["M0"].k))
    w = S["w0"]
    a, b = sub(baixa, ks), sub(alta, ks)
    d = MR.diferenca(a, np.array([w[k] for k in a.k]), b, np.array([w[k] for k in b.k]), B=B_BOOT)
    ra, rb = MR.estimar(a, pesos=w, B=B_BOOT), MR.estimar(b, pesos=w, B=B_BOOT)
    rows = [linha("05", "D ≤ 0,80 (eventos com as duas faixas; pesos de M0)", ra),
            linha("05", "D > 0,80 (mesmos eventos; pesos de M0)", rb)]
    rows.append({"teste": "05", "modelo": "diferença baixa − alta dispersão (pareada por evento)", "coef_lp": d["dif_lp"],
                 "ep_lp": d["ep_lp"], "ic95_wcu_inf": d["ic95_wcu"][0], "ic95_wcu_sup": d["ic95_wcu"][1],
                 "p_wcu": d["p_wcu"], "p_t": d["p_t"], "n_eventos": d["eventos"], "orgaos": d["orgaos"],
                 "pesos": "congelados de M0"})
    TODAS.append(rows[-1])
    fx = MR.FAIXAS
    lim = [(-np.inf, fx["p25"]), (fx["p25"], fx["p50"]), (fx["p50"], MR.LIM), (MR.LIM, np.inf)]
    nomes = ["D ≤ 0,27", "0,27 < D ≤ 0,46", "0,46 < D ≤ 0,80", "D > 0,80"]
    faixas = {}
    for nome, (lo, hi) in zip(nomes, lim):
        df = B.rodar(E6, "e_G", filtro_evento=f_faixa(lo, hi), bins=False)
        rf = MR.estimar(df, B=B_BOOT)
        rows.append(linha("05", f"faixa {nome} (pesos de precisão próprios)", rf))
        faixas[nome] = rf
    salvar("t05_heterogeneidade", rows)
    R["t05"] = {"baixa": ra, "alta": rb, "diferenca": d, "faixas": faixas}


def comp_evento(B, k, r, controles, W=6):
    """Por evento: sobreposição de produtos e Duncan por classe (tratada − controles) e elegibilidade histórica (DiD)."""
    u, m = int(r.u), int(r.m)
    rows = B.linhas(k, u, m, r.tipo, W, unidades=np.r_[u, controles])
    eg = np.isfinite(B.it.e_G.to_numpy()[rows])
    rows = rows[eg]
    uu, mm = B.u_arr[rows], B.m_arr[rows]
    prod, cls = B.it["prod"].to_numpy()[rows], B.it.classe4.to_numpy()[rows]
    D = B.D(k, rows, m, W)
    pos = mm >= m
    out = {}
    df = pd.DataFrame({"u": uu, "pos": pos, "prod": prod, "cls": cls, "D": D})
    sobre, dunc, eleg = {}, {}, {}
    for v, z in df.groupby("u"):
        pre, po = z[~z.pos], z[z.pos]
        if len(pre) == 0 or len(po) == 0:
            continue
        sobre[v] = float(po["prod"].isin(set(pre["prod"])).mean())
        a = pre.cls.value_counts(normalize=True); b = po.cls.value_counts(normalize=True)
        dunc[v] = float(0.5 * a.subtract(b, fill_value=0).abs().sum())
        zd_pre, zd_pos = pre[np.isfinite(pre.D)], po[np.isfinite(po.D)]
        if len(zd_pre) and len(zd_pos):
            eleg[v] = float((zd_pos.D <= MR.LIM).mean() - (zd_pre.D <= MR.LIM).mean())
    for nome, dd in (("sobreposicao_produtos", sobre), ("duncan_classes", dunc), ("elegivel_historica", eleg)):
        if u in dd and sum(1 for v in controles if v in dd) >= 5:
            out[nome] = dd[u] - np.mean([dd[v] for v in controles if v in dd])
    return out


def composicao(nome_mod, mod, rows_out):
    B, E6 = S["B"], S["E6"]
    w = pesos_de(mod)
    ys = {"índice de quantidade": "eq_ok", "log da quantidade": "logq", "índice do estimado (eR)": "eR_ok",
          "log do nº de itens": "n_itens", "parcela com índice G": "com_G", "parcela elegível (contemporânea)": "elegivel",
          "parcela em UNIDADE": "un_unidade", "parcela médica (65xx)": "med65", "parcela de medicamentos (6505)": "med6505",
          "nível de mercado do produto": "ref_G_nivel", "ME/EPP exclusivo": "excl", "sigilo": "sig"}
    res = {}
    for rotulo, y in ys.items():
        lst = []
        for _, r in mod.iterrows():
            o = B.evento(r.k, E6.loc[r.k], y, controles=np.asarray(r.controles), cmin=1, cmin_controle=1, bins=False)
            if o is not None:
                lst.append(o)
        res[rotulo] = MR.estimar(pd.DataFrame(lst), pesos=w, B=B_BOOT, ic=False)
    ev_spec = {"sobreposicao_produtos": [], "duncan_classes": [], "elegivel_historica": []}
    for _, r in mod.iterrows():
        o = comp_evento(B, r.k, E6.loc[r.k], np.asarray(r.controles))
        for kk, v in o.items():
            ev_spec[kk].append({"k": r.k, "u": r.u, "m": r.m, "tipo": r.tipo, "sinal": r.sinal, "cnpj": r.cnpj, "did": v,
                                "h": r.h, "itens_tratada": 0, "compras_tratada": 0, "controles": r.controles})
    for kk, lst in ev_spec.items():
        res[kk] = MR.estimar(pd.DataFrame(lst), pesos=w, B=B_BOOT, ic=False)
    ps = {k: v["p_wcr"] for k, v in res.items() if v.get("n_eventos", 0) > 0}
    m_ = len(ps); ordem = sorted(ps, key=ps.get); acc, holm = 0.0, {}
    for j, k in enumerate(ordem):
        acc = max(acc, min(1.0, (m_ - j) * ps[k])); holm[k] = acc
    for rotulo, v in res.items():
        rows_out.append(linha("06", f"{nome_mod}: {rotulo}", v, p_holm=holm.get(rotulo)))
    return res


def t06():
    rows = []
    R["t06"] = {"M1": composicao("M1", S["M1"], rows), "T4": composicao("teste 04", S["T4"], rows)}
    salvar("t06_composicao", rows)


def t07():
    B, E6 = S["B"], S["E6"]
    S["T7"] = B.rodar(E6, "e_G", filtro_evento=f_hist_def, peso_item=w_continuo, guardar_dev=True)
    rc = MR.estimar(S["T7"], B=B_BOOT)
    S["r_T7"] = rc
    ks = sorted(set(S["T7"].k) & set(S["T4"].k))
    d = MR.diferenca(sub(S["T7"], ks), MR.peso_precisao(sub(S["T7"], ks).h), sub(S["T4"], ks),
                     MR.peso_precisao(sub(S["T4"], ks).h), B=B_BOOT)
    # distribuição dos pesos de item nas janelas das tratadas
    ws = []
    for _, ev in S["T7"].iterrows():
        rows = B.linhas(ev.k, ev.u, ev.m, ev.tipo, 6)
        rt = rows[(B.u_arr[rows] == ev.u) & np.isfinite(B.it.e_G.to_numpy()[rows])]
        rt = rt[np.isfinite(B.D(ev.k, rt, ev.m, 6))]
        ws.append(w_continuo(B, ev.k, rt, ev.m, 6))
    ws = np.concatenate(ws)
    rows = [linha("07", "corte D ≤ 0,80 (= teste 04)", S["r_T4"]),
            linha("07", "ponderação contínua 1/D̃², D̃ ∈ [0,20; 1,50]", rc, dif_vs_corte_lp=d["dif_lp"], dif_ep_lp=d["ep_lp"],
                  dif_p_wcu=d["p_wcu"], peso_item_p05=float(np.quantile(ws, .05)), peso_item_p50=float(np.median(ws)),
                  peso_item_p95=float(np.quantile(ws, .95)), peso_item_max_min=float(ws.max() / ws.min()))]
    salvar("t07_ponderacao_continua", rows)
    eventos_csv("T7", S["T7"])
    R["t07"] = {"continua": rc, "diferenca_vs_corte": d}


def t08():
    B, E6 = S["B"], S["E6"]
    d = pd.read_pickle(MR.CACHE / "descricoes_catmat.pkl")
    d["un_n"] = d.un.map({u: norm_un(u) for u in d.un.dropna().unique()})
    tot = d.groupby("catmat").n.sum()
    mu = (d.groupby(["catmat", "un_n"]).n.sum().reset_index().sort_values(["catmat", "n"], ascending=[True, False])
          .drop_duplicates("catmat").set_index("catmat"))
    cat = pd.DataFrame({"itens": tot, "un_modal": mu.un_n, "share": mu.n / tot}).dropna()
    zero = cat.un_modal.astype(str).str.contains(r"(?:^| )0 00(?: |$)")
    gen = cat.un_modal.astype(str).isin(MR.GENERICAS)
    h1 = cat[(cat.itens >= 20) & (cat.share >= .9) & ~zero & ~gen]
    cc = B.it.loc[B.it.catmat.notna(), ["catmat", "classe"]].assign(c4=lambda x: x.classe.astype(str).str[:4])
    cl = (cc.groupby(["catmat", "c4"]).size().reset_index(name="n").sort_values(["catmat", "n"], ascending=[True, False])
          .drop_duplicates("catmat").set_index("catmat").c4)
    h2 = h1[cl.reindex(h1.index).eq("6505").to_numpy()]
    chave = pd.MultiIndex.from_arrays([B.it.catmat, B.it.un_n.astype(str)])
    m1 = chave.isin(pd.MultiIndex.from_arrays([h1.index.astype(float), h1.un_modal.astype(str)]))
    m2 = chave.isin(pd.MultiIndex.from_arrays([h2.index.astype(float), h2.un_modal.astype(str)]))
    S["mask_H1"], S["mask_H2"] = m1, m2
    eg = np.isfinite(B.it.e_G.to_numpy())
    rows, out = [], {}
    for nome, mk in (("H1: apresentação padronizada", m1), ("H2: H1 ∩ medicamentos (6505)", m2),
                     ("H1 ∩ dispersão ≤ 0,80", m1 & S["mask_f"])):
        df = B.rodar(E6, "e_G", mascara=mk, bins=False)
        r = MR.estimar(df, B=B_BOOT)
        rows.append(linha("08", nome, r, catmats=int(len(h1) if nome.startswith("H1") else len(h2)),
                          itens_G=int((mk & eg).sum()), frac_itens_G=float((mk & eg).sum() / eg.sum()),
                          frac_com_disp_ate_lim=float(((B.it.sd_G <= MR.LIM).to_numpy() & mk & eg).sum() / max((mk & eg).sum(), 1))))
        out[nome] = r
    REG["exclusoes"]["t08"] = {"catmats_com_20_itens": int((cat.itens >= 20).sum()), "H1": int(len(h1)), "H2": int(len(h2)),
                               "excluidos_unidade_generica": int(((cat.itens >= 20) & (cat.share >= .9) & gen).sum()),
                               "excluidos_conteudo_zero": int(((cat.itens >= 20) & (cat.share >= .9) & zero).sum()),
                               "frac_itens_G_com_disp_ate_lim_geral": float(((B.it.sd_G <= MR.LIM).to_numpy() & eg).sum() / eg.sum())}
    salvar("t08_homogeneidade", rows)
    R["t08"] = out


def loo(df):
    w = MR.peso_precisao(df.h)
    y = (df.sinal * df.did).to_numpy()
    tot = float((w * y).sum() / w.sum())
    sh = pd.Series(w, index=df.index).groupby(df.cnpj).sum() / w.sum()
    linhas = []
    for c in sh.index:
        mk = (df.cnpj != c).to_numpy()
        est = float((w[mk] * y[mk]).sum() / w[mk].sum())
        linhas.append({"cnpj": c, "peso": float(sh[c]), "eventos": int((~mk).sum()), "coef_sem_orgao_lp": 100 * est,
                       "influencia_lp": 100 * (est - tot)})
    return tot, pd.DataFrame(linhas), sh


def t09():
    rows, out = [], {}
    for nome, df in (("M0", S["M0"]), ("M1", S["M1"]), ("T4", S["T4"])):
        tot, L, sh = loo(df)
        L.sort_values("peso", ascending=False).to_csv(TAB / f"t09_loo_{nome}.csv", index=False, encoding="utf-8",
                                                      lineterminator="\n")
        q = L.coef_sem_orgao_lp.quantile([0, .05, .25, .5, .75, .95, 1]).to_dict()
        top_p = L.nlargest(10, "peso")
        top_i = L.reindex(L.influencia_lp.abs().sort_values(ascending=False).index).head(10)
        r = {"coef_lp": 100 * tot, "orgaos": int(len(sh)), "orgaos_efetivos": float(1 / (sh ** 2).sum()),
             "dist_sem_um_orgao": {f"q{int(100 * k)}": v for k, v in q.items()},
             "peso_10_maiores": float(top_p.peso.sum()), "influentes": top_i[["cnpj", "peso", "influencia_lp"]].to_dict("records")}
        S[f"loo_{nome}"] = L
        rows.append({"teste": "09", "modelo": nome, "coef_lp": r["coef_lp"], "orgaos": r["orgaos"],
                     "orgaos_efetivos": r["orgaos_efetivos"], "peso_10_maiores_por_peso": r["peso_10_maiores"],
                     "peso_10_mais_influentes": float(top_i.peso.sum()),
                     **{f"sem_um_orgao_{k}": v for k, v in r["dist_sem_um_orgao"].items()},
                     "maior_influencia_lp": float(top_i.influencia_lp.iloc[0])})
        out[nome] = r
    TODAS.extend(rows)
    salvar("t09_influencia_orgaos", rows)
    R["t09"] = out


def wcr_media(y, g, w, pesos="rademacher", B=B_BOOT, seed=3):
    """Bootstrap selvagem restrito (H0: média ponderada = 0) para média ponderada; Rademacher ou Webb."""
    y, w = np.asarray(y, float), np.asarray(w, float)
    gc = pd.factorize(pd.Series(g))[0]
    G = gc.max() + 1
    def tstat(yy):
        ww = w[:, None] if yy.ndim == 2 else w
        t = (ww * yy).sum(0) / w.sum()
        u = yy - t
        Sg = np.zeros((G,) + yy.shape[1:])
        np.add.at(Sg, gc, ww * u)
        se = np.sqrt(G / (G - 1) * (Sg ** 2).sum(0)) / w.sum()
        return t / se
    t0 = tstat(y)
    rng = np.random.default_rng(seed)
    v = rng.choice([-1.0, 1.0], size=(G, B)) if pesos == "rademacher" else C.WEBB[rng.integers(0, 6, size=(G, B))]
    ys = y[:, None] * v[gc]
    ts = tstat(ys)
    return float(np.mean(np.abs(ts) >= abs(t0)))


def wcu_media(y, g, w, B=B_BOOT, seed=5):
    y, w = np.asarray(y, float), np.asarray(w, float)
    t = (w * y).sum() / w.sum()
    psi = w * (y - t) / w.sum()
    gc = pd.factorize(pd.Series(g))[0]
    G = gc.max() + 1
    Psi = np.bincount(gc, psi, G)
    se = np.sqrt(G / (G - 1) * (Psi ** 2).sum())
    rng = np.random.default_rng(seed)
    v = C.WEBB[rng.integers(0, 6, size=(B, G))]
    ts = (v @ Psi) / np.sqrt(G / (G - 1) * ((v * Psi) ** 2).sum(1))
    q = float(np.quantile(np.abs(ts), .95))
    return float(np.mean(np.abs(ts) >= abs(t / se))), [100 * (t - q * se), 100 * (t + q * se)]


def ri_pareada(df, n_viz=20, R_=5000, seed=7):
    w = MR.peso_precisao(df.h); w = w / w.sum()
    s = df.sinal.to_numpy()
    obs = float((df.did.to_numpy() * s) @ w)
    rng = np.random.default_rng(seed)
    pools = [dv[np.argsort(np.abs(hc - h))[:n_viz]] for dv, hc, h in zip(df.dev, df.h_ctrl, df.h)]
    sor = np.array([[p[rng.integers(len(p))] for p in pools] for _ in range(R_)])
    nul = (sor * s) @ w
    q = float(np.quantile(np.abs(nul), .95))
    return float(np.mean(np.abs(nul) >= abs(obs))), [100 * (obs - q), 100 * (obs + q)]


def t10():
    rows, out = [], {}
    for nome, df, r in (("M0", S["M0"], S["r_M0"]), ("M1", S["M1"], S["r_M1"]), ("T4", S["T4"], S["r_T4"]),
                        ("T7", S["T7"], S["r_T7"])):
        y = (df.sinal * df.did).to_numpy()
        w = MR.peso_precisao(df.h)
        g = df.cnpj.astype(str).to_numpy()
        p_rad = wcr_media(y, g, w, "rademacher")
        p_wcu, ic_wcu = wcu_media(y, g, w)
        _, L, _ = loo(df)
        th = L.coef_sem_orgao_lp.to_numpy() / 100
        G = len(th)
        se_j = float(np.sqrt((G - 1) / G * ((th - th.mean()) ** 2).sum()))
        tt = stats.t.ppf(.975, G - 1)
        est = r["coef_lp"] / 100
        p_ri, ic_ri = ri_pareada(df)
        lin = {"teste": "10", "modelo": nome, "coef_lp": r["coef_lp"], "ep_cr1_lp": r["ep_lp"], "p_t_G-1": r["p_t"],
               "ic95_t_inf": r["ic95_t"][0], "ic95_t_sup": r["ic95_t"][1], "p_wcr_webb": r["p_wcr"],
               "ic95_wcr_webb_inf": r["ic95_wcr"][0], "ic95_wcr_webb_sup": r["ic95_wcr"][1], "p_wcr_rademacher": p_rad,
               "p_wcu_webb": p_wcu, "ic95_wcu_inf": ic_wcu[0], "ic95_wcu_sup": ic_wcu[1], "ep_jackknife_lp": 100 * se_j,
               "p_jackknife": float(2 * stats.t.sf(abs(est / se_j), G - 1)),
               "ic95_jackknife_inf": 100 * (est - tt * se_j), "ic95_jackknife_sup": 100 * (est + tt * se_j),
               "p_aleatorizacao": p_ri, "ic95_aleatorizacao_inf": ic_ri[0], "ic95_aleatorizacao_sup": ic_ri[1],
               "orgaos": r["orgaos"], "n_eventos": r["n_eventos"]}
        rows.append(lin)
        out[nome] = lin
    salvar("t10_inferencia", rows)
    R["t10"] = out


def t11():
    rows = []
    for nome, r in (("M0", S["r_M0"]), ("M1", S["r_M1"]), ("T4", S["r_T4"]), ("T7", S["r_T7"])):
        for t in ("A->AF", "AF->A"):
            e = r.get(t, {})
            rows.append({"teste": "11", "modelo": nome, "sentido": t, "coef_lp": e.get("coef_lp"), "ep_lp": e.get("ep_lp"),
                         "ic95_wcr_inf": (e.get("ic95_wcr") or [np.nan])[0], "ic95_wcr_sup": (e.get("ic95_wcr") or [np.nan, np.nan])[1],
                         "p_wcr": e.get("p_wcr"), "n_eventos": r.get(f"n_{t}")})
        rows.append({"teste": "11", "modelo": nome, "sentido": "simetria: soma = 0", "coef_lp": r.get("simetria_soma_lp"),
                     "p_wcr": r.get("simetria_p_wcr"), "n_eventos": r.get("n_eventos")})
    salvar("t11_sentidos", rows)
    R["t11"] = rows


def t12():
    B, E12, mf = S["B"], S["E12"], S["mask_f"]
    S["M0_12"] = B.rodar(E12, "e_ok", W=12)
    S["M1_12"] = B.rodar(E12, "e_G", mascara=mf, W=12)
    rows, out = [], {}
    especs = [("M0", "6 meses", S["M0"], ["b-2"], ["b0", "b1"]), ("M1", "6 meses", S["M1"], ["b-2"], ["b0", "b1"]),
              ("T4", "6 meses", S["T4"], ["b-2"], ["b0", "b1"]),
              ("M0", "12 meses", S["M0_12"], ["b-4", "b-3", "b-2"], ["b0", "b1", "b2", "b3"]),
              ("M1", "12 meses", S["M1_12"], ["b-4", "b-3", "b-2"], ["b0", "b1", "b2", "b3"])]
    for nome, jan, df, pre, pos in especs:
        jp, jo = MR.bins_conjunto(df, pre), MR.bins_conjunto(df, pos)
        for c, v in {**jp["bins"], **jo["bins"]}.items():
            rows.append({"teste": "12", "modelo": nome, "janela": jan, "trimestre": int(c[1:]), "coef_lp": v["coef_lp"],
                         "ep_lp": v["ep_lp"], "ic95_t_inf": v["ic95_t"][0], "ic95_t_sup": v["ic95_t"][1], "p_t": v["p_t"],
                         "n_eventos": v["n_eventos"], "orgaos": jp["G"]})
        rows.append({"teste": "12", "modelo": nome, "janela": jan, "trimestre": "conjunto pré", "F": jp["F"], "p_t": jp["p"],
                     "q": jp["q"], "orgaos": jp["G"]})
        rows.append({"teste": "12", "modelo": nome, "janela": jan, "trimestre": "conjunto pós", "F": jo["F"], "p_t": jo["p"],
                     "q": jo["q"], "orgaos": jo["G"]})
        out[f"{nome} {jan}"] = {"pre": jp, "pos": jo, "eventos": int(len(df))}
    salvar("t12_dinamica", rows)
    R["t12"] = out


def t13():
    B, E6, mf = S["B"], S["E6"], S["mask_f"]
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
    fake.index = fake.index + 100000                            # chaves próprias (cache de controles e de D)
    rows = []
    for nome, kw in (("M1", {"mascara": mf}), ("T4", {"filtro_evento": f_hist_baixa})):
        df = B.rodar(fake, "e_G", bins=False, **kw)
        r = MR.estimar(df, B=B_BOOT)
        rows.append(linha("13", f"{nome}: troca fictícia 12 meses antes (unidade estável)", r))
        t12 = R.get("t12", {}).get(f"{nome} 6 meses", {})
        if t12:
            b = t12["pre"]["bins"].get("b-2", {})
            rows.append({"teste": "13", "modelo": f"{nome}: pré-tendência (trimestre −2 contra −1)", "coef_lp": b.get("coef_lp"),
                         "ep_lp": b.get("ep_lp"), "p_t": b.get("p_t"), "n_eventos": b.get("n_eventos")})
        t10 = R.get("t10", {}).get(nome, {})
        if t10:
            rows.append({"teste": "13", "modelo": f"{nome}: aleatorização no espaço (controles de precisão parecida)",
                         "coef_lp": t10["coef_lp"], "p_t": t10["p_aleatorizacao"],
                         "ic95_t_inf": t10["ic95_aleatorizacao_inf"], "ic95_t_sup": t10["ic95_aleatorizacao_sup"]})
        comp = R.get("t06", {}).get(nome, {})
        for rot in ("índice do estimado (eR)", "índice de quantidade", "log da quantidade", "sobreposicao_produtos",
                    "duncan_classes", "parcela elegível (contemporânea)", "elegivel_historica"):
            if rot in comp and comp[rot].get("n_eventos", 0):
                rows.append({"teste": "13", "modelo": f"{nome}: placebo {rot}", "coef_lp": comp[rot]["coef_lp"],
                             "ep_lp": comp[rot]["ep_lp"], "p_wcr": comp[rot]["p_wcr"], "n_eventos": comp[rot]["n_eventos"]})
    REG["exclusoes"]["t13"] = {"trocas_ficticias_validas_antes_dos_dados": int(len(fake))}
    salvar("t13_placebos", rows)
    R["t13"] = rows


def _fe2(y, g1, g2, iters=500, tol=1e-9):
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


def bjs(evs, mask, W=6):
    """Imputação (Borusyak, Jaravel e Spiess) nos itens `mask` (log P): efeitos fixos de grupo (unidade estável ou
    janela do evento) + produto × trimestre, estimados nos não tratados; mesmos eventos de `evs`."""
    B = S["B"]
    it = B.it
    ok = mask & np.isfinite(it.logp.to_numpy())
    linhas = []
    for t, reg, modo in (("A->AF", "A estável", 0), ("AF->A", "AF estável", 1)):
        est = B.un.index[B.un.regime.eq(reg)].to_numpy()
        est = est[~np.isin(est, B.ev.u.to_numpy())]
        sel = ok & np.isin(B.u_arr, est) & (it.af.to_numpy() == modo)
        nt = pd.DataFrame({"g": "u" + pd.Series(B.u_arr[sel]).astype(str), "y": it.logp.to_numpy()[sel],
                           "pm": it["prod"].to_numpy()[sel].astype(np.int64) * 100 + it.tri.to_numpy()[sel],
                           "fase": "nt", "k": -1, "cod": it.cod.to_numpy()[sel]})
        partes = [nt]
        e = evs[evs.tipo.eq(t)]
        for _, r in e.iterrows():
            u, m = int(r.u), int(r.m)
            a_, b_ = B.ini[u], B.fim[u]
            idx = np.arange(a_, b_)
            idx = idx[(B.m_arr[idx] >= m - W) & (B.m_arr[idx] < m + W) & ok[idx]]
            if len(idx) == 0:
                continue
            partes.append(pd.DataFrame({"g": f"k{r.k}", "y": it.logp.to_numpy()[idx],
                                        "pm": it["prod"].to_numpy()[idx].astype(np.int64) * 100 + it.tri.to_numpy()[idx],
                                        "fase": np.where(B.m_arr[idx] >= m, "trat", "pre"), "k": r.k,
                                        "cod": it.cod.to_numpy()[idx]}))
        d = pd.concat(partes, ignore_index=True)
        und = d[d.fase.ne("trat")]
        g1, g1u = pd.factorize(und.g)
        pmc, pmu = pd.factorize(und.pm)
        a, b = _fe2(und.y.to_numpy(float), g1, pmc)
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


def t14():
    it = S["B"].it
    eg, ea = np.isfinite(it.e_G.to_numpy()), np.isfinite(it.e_ok.to_numpy())
    mf = S["mask_f"]
    passos = []
    def passo(cam, nome, df, pesos="precisao"):
        r = MR.estimar(df, pesos=pesos, B=B_BOOT, ic=False)
        passos.append({"caminho": cam, "passo": nome, "r": r})
    # caminho 1: referência → amostra → pesos → método
    passo(1, "S0 M0: empilhado, ref. A, todas as células, precisão", S["M0"])
    passo(1, "S1 troca a referência (A → G)", S["G_all"])
    passo(1, "S2 troca a amostra (todas → ≤ 0,80) = M1", S["M1"])
    passo(1, "S3 troca os pesos (precisão → iguais)", S["M1"], "iguais")
    bj_f = bjs(S["M1"], mf & eg)
    passo(1, "S4 troca o método (empilhado → BJS), pesos iguais", bj_f, "iguais")
    passo(1, "S4b BJS com pesos de precisão", bj_f)
    # caminho 2: método → referência/itens → amostra → pesos
    passo(2, "P0 M0: empilhado, ref. A, todas, precisão", S["M0"])
    bj_a = bjs(S["M0"], ea)
    passo(2, "P1 troca o método (BJS nos itens com índice A, eventos de M0)", bj_a)
    bj_g = bjs(S["G_all"], eg)
    passo(2, "P2 itens com índice G, todas as células (eventos de G, todas)", bj_g)
    passo(2, "P3 troca a amostra (≤ 0,80; eventos de M1)", bj_f)
    passo(2, "P4 troca os pesos (iguais)", bj_f, "iguais")
    rows, ant = [], {}
    for p in passos:
        c = p["r"].get("coef_lp")
        d = None if p["caminho"] not in ant else c - ant[p["caminho"]]
        ant[p["caminho"]] = c
        rows.append(linha("14", f"caminho {p['caminho']}: {p['passo']}", p["r"], variacao_no_passo_lp=d))
    salvar("t14_estimadores", rows)
    R["t14"] = rows


def t15():
    B, T4 = S["B"], S["T4"]
    dev = np.concatenate(T4.dev.to_numpy()); hc = np.concatenate(T4.h_ctrl.to_numpy())
    X = np.column_stack([np.ones(len(dev)), hc])
    a, b = np.linalg.lstsq(X, dev ** 2, rcond=None)[0]
    var_k = np.maximum(a + b * T4.h.to_numpy(), 1e-6)
    # correlação intraclasse entre controles do mesmo órgão no mesmo evento
    num = den = 0.0
    for dv, us in zip(T4.dev, T4.controles):
        z = pd.DataFrame({"d": dv, "c": B.cnpj[np.asarray(us)]})
        for _, q in z.groupby("c"):
            if len(q) > 1:
                s = q.d.sum(); num += s ** 2 - (q.d ** 2).sum(); den += (len(q) - 1) * (q.d ** 2).sum()
    icc = num / den if den > 0 else 0.0
    ng = T4.groupby("cnpj").size()
    deff = 1 + icc * ((ng ** 2).sum() / len(T4) - 1)
    ep_atual = float(np.sqrt(1 / (1 / var_k).sum()))
    media_inv = float((1 / var_k).mean())
    ev = B.ev.copy()
    fim = (2025 * 12 + 9) - C.M0
    fut = ev[ev.m > fim]
    em_janela = len(S["E6"])
    taxa = len(T4) / em_janela
    cen = []
    for nome, N in (("eventos atuais (referência)", len(T4)),
                    ("futuros já detectados (2025-11 a 2026-04) × taxa de aproveitamento", taxa * len(fut)),
                    ("+ 12 meses de novas trocas (ritmo médio) × taxa", taxa * (len(fut) + len(B.eventos(6)) / 3.3)),
                    ("100 eventos", 100), ("150 eventos", 150)):
        ep = np.sqrt(1 / (N * media_inv)) if N > 0 else np.nan
        cen.append({"cenario": nome, "eventos": float(N), "ep_lp": 100 * ep, "emd_lp": 100 * 2.8 * ep * np.sqrt(deff),
                    "emd_pct": C.pct(-2.8 * ep * np.sqrt(deff)),
                    "poder_para_-3,76lp": float(stats.norm.cdf(0.0376 / (ep * np.sqrt(deff)) - 1.96)),
                    "poder_para_-1,91lp": float(stats.norm.cdf(0.0191 / (ep * np.sqrt(deff)) - 1.96))})
    pd.DataFrame(cen).to_csv(TAB / "t15_poder.csv", index=False, encoding="utf-8", lineterminator="\n")
    fut[["unidade", "cnpj", "esfera", "uf", "mes", "tipo", "dif", "estrito"]].to_csv(
        TAB / "t15_eventos_nao_usados.csv", index=False, encoding="utf-8", lineterminator="\n")
    R["t15"] = {"especificacao_candidata": "referência G; dispersão pré-tratamento D ≤ 0,8033 (teste 04); DiD empilhado, "
                                           "janela de 6 meses, cmin = 2 após o filtro; controles limpos do protocolo; pesos de "
                                           "precisão (a, b originais); τ_AF agregado, bilateral, 5%, WCR por órgão; F1–F4",
                "modelo_variancia_placebo": {"a": float(a), "b": float(b)}, "icc_orgao": float(icc), "deff": float(deff),
                "ep_atual_lp": 100 * ep_atual, "taxa_aproveitamento": taxa,
                "eventos_futuros_detectados": fut.groupby("tipo").size().to_dict(),
                "eventos_futuros_por_mes": fut.groupby("mes").size().to_dict(), "cenarios": cen,
                "nao_usados": ["eventos datados de 2025-11 a 2026-04 (janelas passam de 2026-03)",
                               "itens com abertura de 2026-04 a 2026-10: sem CATMAT na base (exige nova coleta)",
                               "trocas de modo depois de 2026-04 (ainda não observáveis com 6 meses de modos)",
                               "PDFs do Aberto (desenho intraleilão)", "outras plataformas (sem CATMAT)"]}


# --------------------------------------------------------------------------------------------- execução
def conferir():
    ok = {}
    for f in ["t00_reproducao", "t01_amostra_comum", "t02_pesos_fixos", "t03_controles_identicos", "t04_dispersao_pre_tratamento",
              "t05_heterogeneidade", "t06_composicao", "t07_ponderacao_continua", "t08_homogeneidade", "t09_influencia_orgaos",
              "t10_inferencia", "t11_sentidos", "t12_dinamica", "t13_placebos", "t14_estimadores", "t15_poder"]:
        p = TAB / f"{f}.csv"
        ok[f] = {"existe": p.exists(), "linhas": int(len(pd.read_csv(p))) if p.exists() else 0}
    REG["conferencias"]["arquivos"] = ok
    d = R.get("t01", {}).get("diferenca")
    if d:
        REG["conferencias"]["t01_identidade_diferenca"] = abs(d["dif_lp"] - (d["coef1_lp"] - d["coef2_lp"])) < 1e-9


def main():
    S["B"] = MR.Base(log=log)
    for nome, fn in [("t00_reproducao", t00), ("t01_amostra_comum", t01), ("t02_pesos_fixos", t02),
                     ("t03_controles_identicos", t03), ("t04_dispersao_pre_tratamento", t04), ("t05_heterogeneidade", t05),
                     ("t06_composicao", t06), ("t07_ponderacao_continua", t07), ("t08_homogeneidade", t08),
                     ("t09_influencia_orgaos", t09), ("t10_inferencia", t10), ("t11_sentidos", t11), ("t12_dinamica", t12),
                     ("t13_placebos", t13), ("t14_estimadores", t14), ("t15_validacao", t15)]:
        executar(nome, fn)
    pd.DataFrame(TODAS).to_csv(TAB / "todas_estimativas.csv", index=False, encoding="utf-8", lineterminator="\n")
    conferir()
    REG["fim"] = time.strftime("%Y-%m-%d %H:%M:%S")
    REG["segundos"] = round(time.time() - T0)
    (SAIDA / "resultados.json").write_text(json.dumps(R, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    (SAIDA / "registro_execucao.json").write_text(json.dumps(REG, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    falhas = [k for k, v in REG["testes"].items() if v["status"] != "ok"]
    log("falhas:", falhas or "nenhuma")
    try:
        import graficos
        graficos.main(SAIDA)
        log("gráficos ok")
    except Exception as e:
        REG["graficos"] = {"status": "falha", "erro": repr(e), "traceback": traceback.format_exc()}
        (SAIDA / "registro_execucao.json").write_text(json.dumps(REG, ensure_ascii=False, indent=1, default=float),
                                                      encoding="utf-8")
        log("gráficos FALHA", repr(e))
    log("FIM")


if __name__ == "__main__":
    main()
