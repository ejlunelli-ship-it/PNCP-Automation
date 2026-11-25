"""Replicação empírica adaptada de Athey, Levin e Seira (2011), Fase 1 (protocolo.md). EXPLORATÓRIO.

Comando único (da pasta PNCP-Automation):
    python analises/replicacao_athey_levin_seira_20261124/executar.py
Etapas: amostra; logit do modo (PS1–PS4); suporte comum; OLS 1–4; interações; matching (a, b, c) com conferência no
pacote R Matching; robustez (inclui a regressão mediana em R/quantreg); desfechos secundários; comparação com os estudos
anteriores; gráficos; registro_execucao.json.
Pré-requisitos: base de 23/11 em dados/testes_desenho_causal/; R com quantreg e Matching (opcionais: sem R, essas duas
partes ficam registradas como não executadas).
Não lê o pncp.db; não altera bases nem resultados anteriores; não usa nada posterior a 2025-10.
"""
import glob, hashlib, json, os, platform, shutil, subprocess, sys, time, traceback
from pathlib import Path

sys.dont_write_bytecode = True
AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import scipy  # noqa: E402
from scipy import stats  # noqa: E402

import amostra as AM  # noqa: E402
import matching as MT  # noqa: E402
import modelos as MD  # noqa: E402

TAB, GRA, DAD = AQUI / "tabelas", AQUI / "graficos", AM.SAIDA
TAB.mkdir(exist_ok=True)
GRA.mkdir(exist_ok=True)
REF = {"painel_16_11_pct": -4.5, "painel_16_11_lp": float(100 * np.log(1 - 0.045)), "estudo_eventos_lp": -1.91,
       "filtrado_lp": -3.76}
FAIXAS = {"completa": (0.0, 1.0), "[0,05; 0,95]": (0.05, 0.95), "[0,075; 0,925]": (0.075, 0.925),
          "[0,10; 0,90]": (0.10, 0.90)}
PRINCIPAL = "[0,075; 0,925]"
CAT1 = ["tri", "regiao", "esfera", "faixa_itens", "grupo_dom_x"]
CONT1 = ["med", "eq0", "eq_aus", "comp0", "comp_aus"]
PS = {"PS1": (CAT1, CONT1), "PS2": (CAT1 + ["hist_cat"], CONT1 + ["hist_log_n"]),
      "PS3": (CAT1 + ["hist_cat"], CONT1 + ["hist_log_n", "srp", "sig", "excl"]),
      "PS4": (CAT1 + ["hist_cat", "faixa_valor"], CONT1 + ["hist_log_n"])}
CAT_IT = ["tri", "regiao", "esfera", "faixa_itens", "hist_cat"]
CONT_IT = ["hist_log_n", "parc_med", "comp_i", "comp_i_aus", "eq_i", "eq_i_aus", "med_i"]
ESPECS = {"OLS 1": ([], [], []), "OLS 2": (CONT_IT, CAT_IT, ["grupo_x"]), "OLS 3": (CONT_IT, CAT_IT, ["grupo_x", "u"]),
          "OLS 4": (CONT_IT, CAT_IT, ["grupo_x", "u", ("prod", "tri")])}
T0 = time.time()
REG = {"inicio": time.strftime("%Y-%m-%d %H:%M:%S"), "classificacao": "replicação metodológica adaptada, exploratória",
       "protocolo_sha256": hashlib.sha256((AQUI / "protocolo.md").read_bytes()).hexdigest(),
       "parametros": {"faixas_suporte": FAIXAS, "faixa_principal": PRINCIPAL, "escore_principal": "PS2", "M": 4, "J_var": 4,
                      "caliper_sensibilidade": "0,2 DP do escore", "B_qr": 299, "semente": 20261124,
                      "especificacoes_escore": {k: {"categoricas": v[0], "continuas": v[1]} for k, v in PS.items()},
                      "controles_item": {"categoricas": CAT_IT, "continuas": CONT_IT, "absorvidos": ["grupo_x"]}},
       "versoes": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
                   "scipy": scipy.__version__},
       "etapas": {}, "conferencias": {}, "falhas": [], "nao_executado": [], "avisos": []}
S = {}


def log(*a):
    print(f"[{time.time() - T0:7.1f}s]", *a, flush=True)


def etapa(nome, f):
    t = time.time()
    try:
        r = f()
        REG["etapas"][nome] = {"status": "ok", "segundos": round(time.time() - t, 1)}
        log("ok", nome)
        return r
    except Exception as e:  # noqa: BLE001
        REG["etapas"][nome] = {"status": "falhou", "erro": repr(e), "segundos": round(time.time() - t, 1),
                               "traceback": traceback.format_exc()[-3000:]}
        REG["falhas"].append(f"{nome}: {e!r}")
        log("FALHOU", nome, repr(e))
        return None


def csv(nome, linhas):
    df = linhas if isinstance(linhas, pd.DataFrame) else pd.DataFrame(linhas)
    df.to_csv(TAB / f"{nome}.csv", index=False, lineterminator="\n")
    return df


def rscript():
    p = os.environ.get("ALS_RSCRIPT")
    if p and Path(p).exists():
        return p
    c = sorted(glob.glob("C:/Program Files/R/R-*/bin/Rscript.exe"))
    return c[-1] if c else shutil.which("Rscript")


# --------------------------------------------------------------------------------------------- relato padrão
def linha(r, especificacao, amostra, pesos, desfecho="índice de preço (lp)", extra=None):
    if "erro" in r:
        return {"especificacao": especificacao, "amostra": amostra, "pesos": pesos, "desfecho": desfecho, "erro": r["erro"]}
    o = {"especificacao": especificacao, "amostra": amostra, "pesos": pesos, "desfecho": desfecho, "coef_lp": r["b"]}
    for cl, rot in (("cnpj", ""), ("u", "_uasg")):
        if cl in r:
            x = r[cl]
            o[f"ep{rot}"] = x["ep"]
            o[f"ic95_inf{rot}"], o[f"ic95_sup{rot}"] = x["ic95"]
            o[f"p{rot}"] = x["p"]
            o[f"G{rot}"] = x["G"]
            o[f"G_efetivo_variacao{rot}"] = x["G_efetivo_variacao"]
            o[f"maior_grupo_variacao{rot}"] = x["maior_grupo_variacao"]
            o[f"top5_grupos_variacao{rot}"] = x["top5_grupos_variacao"]
    if desfecho.startswith("índice") or desfecho.startswith("log"):
        o["pct"] = float(MD.pct(r["b"]))
        o["pct_ic95_inf"], o["pct_ic95_sup"] = [float(v) for v in MD.pct(r["cnpj"]["ic95"])]
    o.update({"itens": r["n"], "compras": r["compras"], "uasgs": r["uasgs"], "cnpjs": r["cnpjs"],
              "iteracoes_fe": r["iteracoes_fe"]})
    if desfecho.startswith("índice"):
        o["dif_vs_estudo_eventos_-1,91"] = r["b"] - REF["estudo_eventos_lp"]
        o["dif_vs_filtrado_-3,76"] = r["b"] - REF["filtrado_lp"]
        o["dif_vs_painel_-4,60lp"] = r["b"] - REF["painel_16_11_lp"]
    if extra:
        o.update(extra)
    return o


def X_item(df, cont, cats):
    D, nm = MD.dummies(df, cats)
    return D, nm


def ols(df, espec, pesos, y="y", clusters=("cnpj", "u"), Xmais=None, nomes_mais=None, retorna=False, fes_extra=()):
    cont, cats, fes = ESPECS[espec]
    D, nm = X_item(df, cont, cats)
    if Xmais is not None:
        D = np.column_stack([D, Xmais]) if D.shape[1] else Xmais
        nm = nm + list(nomes_mais)
    w = None if pesos == "item" else df.w_compra.to_numpy(float)
    return MD.reg(df, y, cont, list(fes) + list(fes_extra), w, clusters, "af", D, nm, retorna=retorna)


def extra_amostra(df):
    return {"compras_AF": int(df.drop_duplicates("compra").af.sum()), "itens_AF": int(df.af.sum())}


# --------------------------------------------------------------------------------------------- 1. amostra
def e_amostra():
    info = AM.construir(log=log)
    csv("amostra_exclusoes", info["exclusoes"])
    REG["amostra"] = {k: v for k, v in info.items() if k != "exclusoes"}
    S["c"] = pd.read_pickle(DAD / "compras.pkl")
    z = pd.read_pickle(DAD / "itens.pkl")
    S["z_todos_e"] = z
    S["z"] = z[z.ok_ln10].reset_index(drop=True)
    S["zs"] = pd.read_pickle(DAD / "itens_status.pkl")
    REG["conferencias"]["periodo"] = {"primeiro_mes": AM.C.mes_str(AM.C.M0 + int(S["c"].m.min())),
                                      "ultimo_mes": AM.C.mes_str(AM.C.M0 + int(S["c"].m.max())),
                                      "nada_posterior_a_2025_10": bool(S["c"].m.max() <= AM.M_FIM)}


# --------------------------------------------------------------------------------------------- 2. logit
def desenho_ps(c, nome):
    cats, cont = PS[nome]
    D, nm = MD.dummies(c, cats)
    X = np.column_stack([np.ones(len(c)), D, c[cont].to_numpy(float)])
    return X, ["constante"] + nm + list(cont)


def e_logit():
    c = S["c"]
    coefs, desemp, calib = [], [], []
    for nome in PS:
        X, nm = desenho_ps(c, nome)
        r = MD.logit(c.af.to_numpy(float), X, c.cnpj.to_numpy(), nm)
        c[f"ps_{nome}"] = r["p"]
        se_hc, se_cl = np.sqrt(np.diag(r["V_hc"])), np.sqrt(np.diag(r["V_cl"]))
        for j, n_ in enumerate(nm):
            coefs.append({"escore": nome, "variavel": n_, "coef": r["b"][j], "ep_robusto": se_hc[j], "ep_agrupado_cnpj": se_cl[j],
                          "z_agrupado": r["b"][j] / se_cl[j] if se_cl[j] > 0 else np.nan})
        desemp.append({"escore": nome, "compras": r["n"], "compras_AF": int(c.af.sum()), "parametros": r["k"],
                       "convergiu": r["convergiu"], "iteracoes": r["iteracoes"], "log_veross": r["ll"],
                       "pseudo_r2_mcfadden": r["pseudo_r2"], "auc": r["auc"], "brier": r["brier"], "G_cnpj": r["G"],
                       "escore_max_A": float(r["p"][c.af == 0].max()), "escore_min_AF": float(r["p"][c.af == 1].min()),
                       **{f"compras_escore_{a}_{b}": int(((r["p"] >= a) & (r["p"] < b)).sum())
                          for a, b in ((0, .075), (.075, .925), (.925, 1.0001))}})
        dec = pd.qcut(pd.Series(r["p"]).rank(method="first"), 10, labels=False)
        for d_, g in pd.DataFrame({"d": dec, "p": r["p"], "y": c.af.to_numpy()}).groupby("d"):
            calib.append({"escore": nome, "decil": int(d_) + 1, "compras": len(g), "escore_medio": g.p.mean(), "taxa_AF": g.y.mean()})
        if not r["convergiu"]:
            REG["avisos"].append(f"logit {nome} não convergiu")
    csv("logit_coeficientes", coefs)
    csv("logit_desempenho", desemp)
    csv("logit_calibracao", calib)
    c["ps"] = c["ps_PS2"]
    S["c"] = c
    # distribuição do escore por modo (para o gráfico)
    hist = []
    bins = np.linspace(0, 1, 41)
    for nome in PS:
        for m_, rot in ((1, "AF"), (0, "A")):
            h, _ = np.histogram(c.loc[c.af == m_, f"ps_{nome}"], bins)
            for j in range(40):
                hist.append({"escore": nome, "modo": rot, "lim_inf": bins[j], "lim_sup": bins[j + 1], "compras": int(h[j])})
    csv("escore_distribuicao", hist)


# --------------------------------------------------------------------------------------------- 3. suporte
COV_EQ = [("log nº de itens", lambda c: np.log(c.n_itens_mat)), ("parcela de medicamentos", lambda c: c.med),
          ("quantidade prevista (eq)", lambda c: c.eq0), ("competição esperada", lambda c: c.comp0),
          ("parcela AF 12 meses", lambda c: (c.hist_a / c.hist_n).where(c.hist_n > 0, 0.0)),
          ("sem histórico 12 meses", lambda c: (c.hist_n == 0).astype(float)),
          ("log nº de compras 12 meses", lambda c: c.hist_log_n), ("trimestre", lambda c: c.tri.astype(float)),
          ("esfera federal", lambda c: (c.esfera == "F").astype(float)),
          ("esfera estadual", lambda c: (c.esfera == "E").astype(float)),
          ("esfera municipal", lambda c: (c.esfera == "M").astype(float)),
          ("região N", lambda c: (c.regiao == "N").astype(float)), ("região NE", lambda c: (c.regiao == "NE").astype(float)),
          ("região CO", lambda c: (c.regiao == "CO").astype(float)), ("região SE", lambda c: (c.regiao == "SE").astype(float)),
          ("região S", lambda c: (c.regiao == "S").astype(float)), ("SRP", lambda c: c.srp), ("sigilo", lambda c: c.sig),
          ("exclusiva ME/EPP", lambda c: c.excl),
          ("log valor estimado", lambda c: c.log_valor.fillna(c.log_valor.median())),
          ("valor estimado ausente", lambda c: c.log_valor.isna().astype(float))]


def dif_pad(c, w_af=None, w_a=None, ref=None):
    """Diferenças padronizadas: (média AF − média A) / DP agrupado (da amostra `ref`, sem pesos)."""
    ref = c if ref is None else ref
    out = {}
    for nome, f in COV_EQ:
        x, xr = f(c).to_numpy(float), f(ref).to_numpy(float)
        a, ar = c.af.to_numpy() == 1, ref.af.to_numpy() == 1
        sd = np.sqrt((np.nanvar(xr[ar]) + np.nanvar(xr[~ar])) / 2)
        m1 = np.average(x[a], weights=None if w_af is None else w_af[a])
        m0 = np.average(x[~a], weights=None if w_a is None else w_a[~a])
        out[nome] = (m1 - m0) / sd if sd > 0 else np.nan
    return out


def e_suporte():
    c, z = S["c"], S["z"]
    linhas, eq = [], []
    mista = c.groupby("u").af.agg(lambda s: s.nunique() == 2)
    for nome in PS:
        for fx, (lo, hi) in FAIXAS.items():
            ok = (c[f"ps_{nome}"] >= lo) & (c[f"ps_{nome}"] <= hi)
            cs = c[ok]
            zz = z[z.compra.isin(cs.compra)]
            sh = cs.cnpj.value_counts(normalize=True)
            mix = cs.groupby("u").af.agg(lambda s: s.nunique() == 2)
            o = {"escore": nome, "faixa": fx, "compras": int(len(cs)), "compras_AF": int(cs.af.sum()),
                 "compras_A": int((cs.af == 0).sum()), "compras_excluidas": int((~ok).sum()),
                 "compras_AF_excluidas": int(((~ok) & (c.af == 1)).sum()), "compras_A_excluidas": int(((~ok) & (c.af == 0)).sum()),
                 "itens": int(len(zz)), "itens_excluidos": int(len(z) - len(zz)), "uasgs": int(cs.u.nunique()),
                 "cnpjs": int(cs.cnpj.nunique()), "cnpjs_com_AF": int(cs[cs.af == 1].cnpj.nunique()),
                 "uasgs_com_os_dois_modos": int(mix.sum()), "parcela_compras_em_uasgs_mistas": float(cs.u.map(mix).mean()),
                 "maior_cnpj_parcela_compras": float(sh.max()), "top10_cnpjs_parcela_compras": float(sh.head(10).sum()),
                 "cnpjs_efetivos_compras": float(1 / (sh ** 2).sum()),
                 "identificavel_regra_protocolo": bool(((cs.af == 1).sum() >= 200) & ((cs.af == 0).sum() >= 200)
                                                       & (cs[cs.af == 1].cnpj.nunique() >= 30))}
            linhas.append(o)
            if nome == "PS2":
                d = dif_pad(cs)
                dw = dif_pad(cs, cs.n_itens_indice.to_numpy(float), cs.n_itens_indice.to_numpy(float))
                for k_ in d:
                    eq.append({"faixa": fx, "covariavel": k_, "dif_padronizada_compra": d[k_], "dif_padronizada_item": dw[k_]})
    csv("suporte_comum", linhas)
    csv("equilibrio_suporte", eq)
    # sobreposição nas UASGs (amostra completa) e nos maiores grupos
    sob = [{"recorte": "amostra completa", "uasgs": int(c.u.nunique()), "uasgs_com_os_dois_modos": int(mista.sum()),
            "parcela_compras_em_uasgs_mistas": float(c.u.map(mista).mean()),
            "parcela_itens_em_uasgs_mistas": float(z.u.map(mista).mean())}]
    grupos = c.grupo_dom_x.value_counts().head(6).index
    for g in grupos:
        cg = c[c.grupo_dom_x == g]
        for m_, rot in ((1, "AF"), (0, "A")):
            q = cg.loc[cg.af == m_, "ps"].quantile([.05, .25, .5, .75, .95]).to_numpy()
            sob.append({"recorte": f"grupo {g}", "modo": rot, "compras": int((cg.af == m_).sum()),
                        "escore_p05": q[0], "escore_p25": q[1], "escore_mediana": q[2], "escore_p75": q[3], "escore_p95": q[4],
                        "parcela_no_suporte": float(((cg.af == m_) & cg.ps.between(.075, .925)).sum() / max((cg.af == m_).sum(), 1))})
    csv("sobreposicao_uasgs_grupos", sob)
    c["sup"] = c.ps.between(*FAIXAS[PRINCIPAL])
    for fx, (lo, hi) in FAIXAS.items():
        c[f"sup_{fx}"] = c.ps.between(lo, hi)
    S["c"] = c
    sup = set(c.compra[c.sup])
    S["z"]["sup"] = S["z"].compra.isin(sup)
    S["z_todos_e"]["sup"] = S["z_todos_e"].compra.isin(sup)
    r = [x for x in linhas if x["escore"] == "PS2" and x["faixa"] == PRINCIPAL][0]
    REG["suporte_principal"] = r
    if not r["identificavel_regra_protocolo"]:
        REG["avisos"].append("faixa principal abaixo da regra de identificação do protocolo")


# --------------------------------------------------------------------------------------------- 4. OLS
def amostras_item():
    z = S["z"]
    return {"completa": z, "suporte": z[z.sup].reset_index(drop=True)}


def e_ols():
    linhas = []
    for am, df in amostras_item().items():
        # pesos por compra recalculados na amostra
        df = df.assign(w_compra=1.0 / df.groupby("compra").compra.transform("size"))
        for esp in ESPECS:
            for pesos in ("item", "compra"):
                r = ols(df, esp, pesos)
                linhas.append(linha(r, esp, am, pesos, extra=extra_amostra(df)))
                log(esp, am, pesos, round(r.get("b", np.nan), 3))
    S["ols"] = csv("ols", linhas)


# --------------------------------------------------------------------------------------------- 5. interações
def faixas_dim(df, dim):
    if dim == "valor estimado":
        return np.where(df.terco_valor < 0, "ausente", "T" + (df.terco_valor + 1).astype(str)), ["T1", "T2", "T3", "ausente"], True
    if dim == "quantidade prevista":
        q = df.eq_i.where(df.eq_i_aus == 0)
        t = pd.qcut(q.rank(method="first"), 3, labels=["T1", "T2", "T3"]).astype(object)
        return np.where(q.isna(), "ausente", t), ["T1", "T2", "T3", "ausente"], True
    if dim == "competição esperada":
        q = df.comp_i.where(df.comp_i_aus == 0)
        t = pd.qcut(q.rank(method="first"), 3, labels=["T1", "T2", "T3"]).astype(object)
        return np.where(q.isna(), "ausente", t), ["T1", "T2", "T3", "ausente"], True
    if dim == "classe de produto":
        top = df[df.med_i == 0].grupo.value_counts().head(5).index
        v = np.where(df.med_i == 1, "medicamentos", np.where(df.grupo.isin(top), "grupo " + df.grupo.astype(str), "outros"))
        return v, None, False
    if dim == "esfera":
        return df.esfera.astype(str).to_numpy(), None, False
    raise ValueError(dim)


def junta_faixas(df, v, ordem):
    """Regra do protocolo: faixa com < 50 compras de algum modo ou < 10 CNPJs com AF junta-se à vizinha (ou a 'outros')."""
    v = np.asarray(v, dtype=object).copy()
    for _ in range(10):
        t = pd.DataFrame({"f": v, "compra": df.compra.to_numpy(), "af": df.af.to_numpy(), "cnpj": df.cnpj.to_numpy()})
        k = t.drop_duplicates(["f", "compra"]).groupby("f").agg(af=("af", "sum"), n=("af", "size"))
        k["a"] = k.n - k.af
        caf = t[t.af == 1].groupby("f").cnpj.nunique()
        k["cnpj_af"] = caf.reindex(k.index).fillna(0)
        ruins = k[(k.af < 50) | (k.a < 50) | (k.cnpj_af < 10)].index.tolist()
        if not ruins or len(k) <= 1:
            break
        f = ruins[0]
        if ordem is not None:
            presentes = [o for o in ordem if o in k.index]
            j = presentes.index(f)
            alvo = presentes[j + 1] if j + 1 < len(presentes) and presentes[j + 1] != "ausente" else presentes[max(j - 1, 0)]
            if alvo == f:
                alvo = [o for o in presentes if o != f][0]
        else:
            alvo = "outros" if f != "outros" else k.drop(index=f).n.idxmax()
        v[v == f] = alvo
    return v


DIMS = ["valor estimado", "quantidade prevista", "classe de produto", "esfera", "competição esperada"]


def interacoes_modelo(df, dims, espec, pesos):
    blocos, nomes, idx_int, medias = [], [], {}, {}
    w = np.ones(len(df)) if pesos == "item" else df.w_compra.to_numpy(float)
    for dim in dims:
        v, ordem, principal = faixas_dim(df, dim)
        v = junta_faixas(df, v, ordem)
        cats = pd.Series(v).value_counts().index.tolist()             # base = maior faixa
        base, outras = cats[0], cats[1:]
        idx_int[dim] = []
        for f in outras:
            ind = (v == f).astype(float)
            if principal:
                blocos.append(ind); nomes.append(f"{dim}={f}")
            blocos.append(ind * df.af.to_numpy(float)); nomes.append(f"AF×{dim}={f}")
            idx_int[dim].append(f"AF×{dim}={f}")
            medias[f"AF×{dim}={f}"] = float(np.average(ind, weights=w))
        medias[f"_faixas_{dim}"] = {"base": base, "outras": outras}
    Xm = np.column_stack(blocos) if blocos else None
    r = ols(df, espec, pesos, Xmais=Xm, nomes_mais=nomes)
    return r, idx_int, medias


def e_interacoes():
    linhas, testes = [], []
    for am, df in amostras_item().items():
        df = df.assign(w_compra=1.0 / df.groupby("compra").compra.transform("size"))
        for espec in ("OLS 2", "OLS 3"):
            for pesos in ("item", "compra"):
                for dims in [[d] for d in DIMS] + [DIMS]:
                    rot = dims[0] if len(dims) == 1 else "conjunto (5 dimensões)"
                    r, idx_int, medias = interacoes_modelo(df, dims, espec, pesos)
                    if "erro" in r:
                        continue
                    nm = r["nomes"]
                    L = np.zeros(len(nm))
                    L[0] = 1.0
                    todos = []
                    for dim in dims:
                        for nome_i in idx_int[dim]:
                            if nome_i in nm:
                                L[nm.index(nome_i)] = medias[nome_i]
                                todos.append(nm.index(nome_i))
                    ame = MD.comb_linear(r, L)
                    wd = MD.wald(r, todos) if todos else {"F": np.nan, "p": np.nan, "gl1": 0, "gl2": np.nan}
                    linhas.append({"amostra": am, "base": espec, "pesos": pesos, "dimensao": rot,
                                   "efeito_medio_ajustado_lp": ame["est"], "ep": ame["ep"], "ic95_inf": ame["ic95"][0],
                                   "ic95_sup": ame["ic95"][1], "p": ame["p"], "pct": float(MD.pct(ame["est"])),
                                   "coef_AF_faixa_base": r["b"], "wald_F": wd["F"], "wald_gl": wd["gl1"], "wald_p": wd["p"],
                                   "G": ame["G"], "itens": r["n"], "compras": r["compras"], "uasgs": r["uasgs"],
                                   "cnpjs": r["cnpjs"], "faixas": json.dumps({d: medias[f"_faixas_{d}"] for d in dims},
                                                                              ensure_ascii=False)})
                    se = np.sqrt(np.diag(r["cnpj"]["V"]))
                    for dim in dims:
                        for nome_i in idx_int[dim]:
                            if nome_i in nm:
                                j = nm.index(nome_i)
                                testes.append({"amostra": am, "base": espec, "pesos": pesos, "modelo": rot, "termo": nome_i,
                                               "coef_lp": r["beta"][j], "ep": se[j], "media_da_faixa": medias[nome_i]})
    df = pd.DataFrame(linhas)
    df["wald_p_holm"] = np.nan
    for (am, b, p_), g in df[df.dimensao != "conjunto (5 dimensões)"].groupby(["amostra", "base", "pesos"]):
        df.loc[g.index, "wald_p_holm"] = MD.holm(g.wald_p.to_numpy())
    S["inter"] = csv("interacoes", df)
    csv("interacoes_termos", testes)


# --------------------------------------------------------------------------------------------- 6. matching
COV_MATCH = COV_EQ


def roda_matching(cs, variante, estratos=None, caliper=None, cache=None):
    ps, W, Y = cs.ps.to_numpy(float), cs.af.to_numpy(int), cs.y.to_numpy(float)
    chave = (variante, caliper)
    if cache is not None and chave in cache:
        Jm, sv, svc = cache[chave]
    else:
        Jm = MT.casar(ps, W, 4, estratos, caliper)
        sv = MT.vizinhos_mesmo_modo(ps, W, 4, estratos)
        svc = MT.vizinhos_mesmo_modo(ps, W, 4, grupos=cs.cnpj.to_numpy())
        if cache is not None:
            cache[chave] = (Jm, sv, svc)
    saidas = {}
    for pesos in ("compra", "item"):
        a = None if pesos == "compra" else cs.n_itens_indice.to_numpy(float)
        saidas[pesos] = MT.estimar(Y, W, Jm, a, sv, svc, cs.cnpj.to_numpy())
    return saidas, Jm


def e_matching():
    c = S["c"]
    cs = c[c.sup].reset_index(drop=True)
    linhas, eq, cache = [], [], {}
    variantes = [("(a) só o escore", None, None), ("(b) exato trimestre × grupo dominante", cs.tri.astype(str) + "|" + cs.grupo_dom_x.astype(str), None),
                 ("(c) exato na UASG", cs.u.astype(str), None),
                 ("(a) com caliper de 0,2 DP", None, 0.2 * float(cs.ps.std()))]
    for nome, est, cal in variantes:
        sai, Jm = roda_matching(cs, nome, est, cal, cache)
        tem = np.array([len(j) > 0 for j in Jm])
        for pesos, r in sai.items():
            for estd in ("efeito_medio_eq7", "efeito_nas_AF", "efeito_nas_A"):
                if estd not in r:
                    continue
                o = r[estd]
                pop = tem if estd == "efeito_medio_eq7" else (tem & (cs.af.to_numpy() == (1 if estd == "efeito_nas_AF" else 0)))
                usadas = np.abs(o["c"]) > 0
                linhas.append({"variante": nome, "pesos": pesos, "estimando": estd, "coef_lp": o["est"],
                               "ep_AI_populacional": o.get("ep_AI_populacional"), "ep_AI_condicional": o.get("ep_AI_condicional"),
                               "ep_agrupado_adaptado": o.get("ep_agrupado_adaptado"),
                               "ic95_inf_AI": o["est"] - 1.96 * o.get("ep_AI_populacional", np.nan),
                               "ic95_sup_AI": o["est"] + 1.96 * o.get("ep_AI_populacional", np.nan),
                               "p_AI": float(2 * stats.norm.sf(abs(o["est"] / o["ep_AI_populacional"]))),
                               "ic95_inf_agrupado": o["est"] - 1.96 * o.get("ep_agrupado_adaptado", np.nan),
                               "ic95_sup_agrupado": o["est"] + 1.96 * o.get("ep_agrupado_adaptado", np.nan),
                               "p_agrupado": float(2 * stats.norm.sf(abs(o["est"] / o["ep_agrupado_adaptado"]))),
                               "pct": float(MD.pct(o["est"])), "compras_no_estimando": o["unidades"],
                               "compras_AF": o["unidades_AF"], "compras_A": o["unidades_A"], "compras_sem_par": o["sem_par"],
                               "parcela_sem_par": o["sem_par"] / len(cs), "compras_usadas": int(usadas.sum()),
                               "uasgs_usadas": int(cs.u[usadas].nunique()), "cnpjs_usados": int(cs.cnpj[usadas].nunique()),
                               "itens_usados": int(cs.n_itens_indice[usadas].sum()),
                               "ess_AF": o.get("ess_AF"), "ess_A": o.get("ess_A"), "peso_max_AF": o.get("peso_max_AF"),
                               "peso_max_A": o.get("peso_max_A"), "peso_top1pct_AF": o.get("peso_top1pct_AF"),
                               "peso_top1pct_A": o.get("peso_top1pct_A"), "v_agrupada_negativa": o.get("v_agrupada_negativa"),
                               "dif_vs_estudo_eventos_-1,91": o["est"] - REF["estudo_eventos_lp"],
                               "dif_vs_filtrado_-3,76": o["est"] - REF["filtrado_lp"]})
                if estd == "efeito_medio_eq7" and pesos == "compra":
                    wabs = np.abs(o["c"])
                    d = dif_pad(cs, wabs, wabs, ref=cs)
                    for k_ in d:
                        eq.append({"variante": nome, "covariavel": k_, "dif_padronizada_depois": d[k_]})
        log("matching", nome, round(sai["compra"]["efeito_medio_eq7"]["est"], 3))
    antes = dif_pad(cs)
    completa = dif_pad(c)
    for e_ in eq:
        e_["dif_padronizada_suporte_antes"] = antes[e_["covariavel"]]
        e_["dif_padronizada_amostra_completa"] = completa[e_["covariavel"]]
        e_["desequilibrio_acima_0,1"] = bool(abs(e_["dif_padronizada_depois"]) > 0.1)
    S["match"] = csv("matching", linhas)
    csv("equilibrio_matching", eq)
    S["cs"] = cs
    # conferência no pacote R Matching (variante a)
    rs = rscript()
    if rs is None:
        REG["nao_executado"].append("conferência no pacote R Matching: Rscript não encontrado")
        return
    ent = DAD / "matching_entrada.csv"
    sai_r = DAD / "matching_R.csv"
    cs[["y", "af", "ps", "n_itens_indice"]].rename(columns={"n_itens_indice": "peso"}).to_csv(ent, index=False)
    p = subprocess.run([rs, str(AQUI / "validar_matching.R"), str(ent), str(sai_r)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    (DAD / "validar_matching.log").write_text(p.stdout + "\n" + p.stderr, encoding="utf-8")
    if p.returncode != 0:
        REG["falhas"].append("validar_matching.R falhou (ver dados/replicacao_athey_levin_seira/validar_matching.log)")
        return
    rr = pd.read_csv(sai_r)
    mapa = {"ATE": "efeito_medio_eq7", "ATT": "efeito_nas_AF", "ATC": "efeito_nas_A"}
    conf = []
    py = S["match"][S["match"].variante == "(a) só o escore"]
    for _, x in rr.iterrows():
        q = py[(py.estimando == mapa[x.estimando]) & (py.pesos == ("compra" if x.pesos == "iguais" else "item"))].iloc[0]
        col = "ep_AI_condicional" if x.variancia.startswith("condicional") else "ep_AI_populacional"
        conf.append({"estimando": x.estimando, "pesos": x.pesos, "variancia": x.variancia, "est_R": x.est, "est_python": q.coef_lp,
                     "dif_est": x.est - q.coef_lp, "se_R": x.se, "se_python": q[col], "razao_se": q[col] / x.se,
                     "Matching": x.Matching})
    cf = csv("matching_conferencia_R", conf)
    REG["conferencias"]["matching_vs_pacote_R"] = {"max_dif_est": float(cf.dif_est.abs().max()),
                                                   "razao_se_min_max": [float(cf.razao_se.min()), float(cf.razao_se.max())],
                                                   "Matching": str(cf.Matching.iloc[0])}


# --------------------------------------------------------------------------------------------- 7. robustez
def e_robustez():
    c, z = S["c"], S["z"]
    lin = []

    def add(rot, grupo, r, df, pesos="item", esp="OLS", desfecho="índice de preço (lp)"):
        o = linha(r, esp, rot, pesos, desfecho, extra=extra_amostra(df) if df is not None else None)
        o["teste"] = grupo
        lin.append(o)

    # 1. faixas de suporte (OLS 2 e 3) e matching (a)
    for fx in FAIXAS:
        comp_ok = set(c.compra[c[f"sup_{fx}"]])
        df = z[z.compra.isin(comp_ok)]
        df = df.assign(w_compra=1.0 / df.groupby("compra").compra.transform("size"))
        for esp in ("OLS 2", "OLS 3"):
            for pesos in ("item", "compra"):
                add(f"suporte {fx}", "1. faixa de suporte", ols(df, esp, pesos), df, pesos, esp)
        cs = c[c[f"sup_{fx}"]].reset_index(drop=True)
        sai, _ = roda_matching(cs, f"a-{fx}")
        o = sai["compra"]["efeito_medio_eq7"]
        lin.append({"teste": "1. faixa de suporte", "especificacao": "matching (a)", "amostra": f"suporte {fx}", "pesos": "compra",
                    "desfecho": "índice de preço (lp)", "coef_lp": o["est"], "ep": o["ep_agrupado_adaptado"],
                    "ep_AI": o["ep_AI_populacional"], "ic95_inf": o["est"] - 1.96 * o["ep_agrupado_adaptado"],
                    "ic95_sup": o["est"] + 1.96 * o["ep_agrupado_adaptado"], "compras": o["unidades"],
                    "cnpjs": int(cs.cnpj.nunique()), "uasgs": int(cs.u.nunique())})
    zs_ = z[z.sup].reset_index(drop=True)
    zs_ = zs_.assign(w_compra=1.0 / zs_.groupby("compra").compra.transform("size"))
    # 3. exclusão sucessiva dos órgãos mais influentes (OLS 2 e 3, suporte, peso por item)
    for esp in ("OLS 2", "OLS 3"):
        df = zs_
        fora = []
        for passo in range(6):
            r = ols(df, esp, "item", clusters=("cnpj",), retorna=True)
            o = linha(r, esp, f"suporte sem {passo} órgão(s) mais influente(s)", "item", extra=extra_amostra(df))
            o["teste"] = "3. órgãos influentes"
            o["orgaos_retirados"] = ";".join(fora)
            lin.append(o)
            if passo == 5:
                break
            psi, g = MD.influencia_grupos(r)
            nomes_g = pd.factorize(df.cnpj.astype(str))[1]
            alvo = str(nomes_g[int(np.argmax(np.abs(psi)))])
            fora.append(alvo)
            df = df[df.cnpj.astype(str) != alvo].reset_index(drop=True)
    # 5. outras especificações do escore
    for nome in ("PS1", "PS3", "PS4"):
        ok = c[f"ps_{nome}"].between(*FAIXAS[PRINCIPAL])
        df = z[z.compra.isin(set(c.compra[ok]))]
        for esp in ("OLS 2", "OLS 3"):
            add(f"suporte {PRINCIPAL} com {nome}", "5. especificação do escore", ols(df, esp, "item"), df, "item", esp)
        cs = c[ok].reset_index(drop=True).assign(ps=lambda d: d[f"ps_{nome}"])
        sai, _ = roda_matching(cs, f"a-{nome}")
        o = sai["compra"]["efeito_medio_eq7"]
        lin.append({"teste": "5. especificação do escore", "especificacao": "matching (a)", "amostra": f"suporte com {nome}",
                    "pesos": "compra", "desfecho": "índice de preço (lp)", "coef_lp": o["est"], "ep": o["ep_agrupado_adaptado"],
                    "ep_AI": o["ep_AI_populacional"], "ic95_inf": o["est"] - 1.96 * o["ep_agrupado_adaptado"],
                    "ic95_sup": o["est"] + 1.96 * o["ep_agrupado_adaptado"], "compras": o["unidades"],
                    "cnpjs": int(cs.cnpj.nunique()), "uasgs": int(cs.u.nunique())})
    # 6. medicamentos × demais
    for rot, mk in (("medicamentos", zs_.med_i == 1), ("demais materiais", zs_.med_i == 0)):
        df = zs_[mk]
        k = df.drop_duplicates("compra")
        suporte_ok = (k.af.sum() >= 200) and ((k.af == 0).sum() >= 200) and (k[k.af == 1].cnpj.nunique() >= 30)
        for esp in ("OLS 2", "OLS 3"):
            add(f"suporte, {rot}" + ("" if suporte_ok else " (abaixo da regra de suporte)"), "6. medicamentos × demais",
                ols(df, esp, "item"), df, "item", esp)
    # 7. dispersão e tratamento de extremos
    df = zs_[zs_.baixa_disp == 1]
    for esp in ("OLS 2", "OLS 3"):
        add("suporte, células de baixa dispersão (sd_G ≤ 0,8033)", "7. índice e dispersão", ols(df, esp, "item"), df, "item", esp)
    zt = S["z_todos_e"]
    df = zt[zt.sup & zt.y_c3.notna()].reset_index(drop=True)
    for esp in ("OLS 2", "OLS 3"):
        add("suporte, índice truncado em ±3 (e_c3), inclui |e| > ln 10", "7. índice e dispersão", ols(df, esp, "item", y="y_c3"),
            df, "item", esp)
    # 9. Mundlak: dentro × entre UASGs
    for am, df in amostras_item().items():
        for pesos in ("item", "compra"):
            df = df.assign(w_compra=1.0 / df.groupby("compra").compra.transform("size"))
            w = np.ones(len(df)) if pesos == "item" else df.w_compra.to_numpy()
            afbar = pd.Series(w * df.af.to_numpy()).groupby(df.u.to_numpy()).transform("sum") / \
                pd.Series(w).groupby(df.u.to_numpy()).transform("sum")
            r = ols(df, "OLS 2", pesos, Xmais=afbar.to_numpy()[:, None], nomes_mais=["af_media_uasg"])
            nm = r["nomes"]
            L = np.zeros(len(nm)); L[0] = 1.0; L[nm.index("af_media_uasg")] = 1.0
            ent = MD.comb_linear(r, L)
            o = linha(r, "Mundlak (OLS 2 + média de AF da UASG)", am, pesos, extra=extra_amostra(df))
            o.update({"teste": "9. mesma UASG × UASGs diferentes", "efeito_dentro_lp": r["b"], "associacao_entre_lp": ent["est"],
                      "associacao_entre_ep": ent["ep"], "associacao_entre_p": ent["p"]})
            lin.append(o)
    # 10. seleção: compras com todos os itens de situação final homologados
    ok = set(c.compra[(c.suc == 1) & c.sup])
    df = zs_[zs_.compra.isin(ok)]
    for esp in ("OLS 2", "OLS 3"):
        add("suporte, compras com 100% dos itens finais homologados", "10. seleção dos homologados", ols(df, esp, "item"), df,
            "item", esp)
    S["rob"] = csv("robustez", lin)


def e_qr():
    rs = rscript()
    if rs is None:
        REG["nao_executado"].append("regressão mediana: Rscript não encontrado")
        return
    c = S["c"]
    cats, cont = PS["PS2"]
    D, nm = MD.dummies(c, cats)
    X = pd.DataFrame(np.column_stack([D, c[cont].to_numpy(float)]), columns=[f"x_{j}" for j in range(D.shape[1] + len(cont))])
    base = pd.concat([c[["y", "af", "cnpj"]].reset_index(drop=True), X], axis=1)
    ent = pd.concat([base[c.sup.to_numpy()].assign(amostra="suporte"), base.assign(amostra="completa")], ignore_index=True)
    f_ent, f_sai = DAD / "qr_entrada.csv", DAD / "qr_saida.csv"
    ent.to_csv(f_ent, index=False)
    p = subprocess.run([rs, str(AQUI / "qr_mediana.R"), str(f_ent), str(f_sai), "299", "3"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    (DAD / "qr_mediana.log").write_text(p.stdout + "\n" + p.stderr, encoding="utf-8")
    if p.returncode != 0:
        raise RuntimeError("qr_mediana.R falhou (ver dados/replicacao_athey_levin_seira/qr_mediana.log)")
    q = pd.read_csv(f_sai)
    q["pct"] = MD.pct(q.coef_lp)
    q["dif_vs_estudo_eventos_-1,91"] = q.coef_lp - REF["estudo_eventos_lp"]
    S["qr"] = csv("regressao_mediana", q)
    REG["versoes"]["quantreg"] = str(q.quantreg.iloc[0])
    REG["versoes"]["R"] = str(q.R.iloc[0])


# --------------------------------------------------------------------------------------------- 8. secundários
def e_secundarios():
    c, z, zs = S["c"], S["z"], S["zs"]
    lin = []
    for am, df in amostras_item().items():
        df = df.assign(w_compra=1.0 / df.groupby("compra").compra.transform("size"))
        d1 = df[df.y_desc.notna()].reset_index(drop=True)
        d1 = d1.assign(w_compra=1.0 / d1.groupby("compra").compra.transform("size"))
        for esp in ESPECS:
            lin.append(linha(ols(d1, esp, "item", y="y_desc"), esp, am, "item", "desconto sobre o estimado (p.p.)",
                             extra_amostra(d1)))
        for esp, fes in (("log P | produto × trimestre", []), ("log P | produto × trimestre + X", None),
                         ("log P | produto × trimestre + X + UASG", ["u"])):
            if fes == []:
                r = MD.reg(df, "y_logp", [], [("prod", "tri")], None, ("cnpj", "u"), "af")
            else:
                cont, cats, _ = ESPECS["OLS 2"]
                D, nm = MD.dummies(df, cats)
                r = MD.reg(df, "y_logp", cont, [("prod", "tri")] + (fes or []), None, ("cnpj", "u"), "af", D, nm)
            lin.append(linha(r, esp, am, "item", "log do preço (lp)", extra_amostra(df)))
    sup = set(c.compra[c.sup])
    zs = zs.assign(sup=zs.compra.isin(sup))
    for am, df in (("todos os itens com situação final", zs), ("itens das compras da análise no suporte", zs[zs.sup])):
        df = df.reset_index(drop=True)
        for y, rot in (("suc", "homologação (prob.)"), ("fra", "fracasso (prob.)"), ("des", "deserção (prob.)")):
            df2 = df.assign(yy=100 * df[y].astype(float))
            for esp in ("OLS 1", "OLS 2", "OLS 3"):
                cont, cats, fes = ESPECS[esp]
                D, nm = MD.dummies(df2, cats) if cats else (np.zeros((len(df2), 0)), [])
                r = MD.reg(df2, "yy", cont, fes, None, ("cnpj", "u"), "af", D, nm)
                lin.append(linha(r, esp, am, "item", rot + " (p.p.)", extra_amostra(df2)))
    sec = pd.DataFrame(lin)
    # Holm nos 5 desfechos secundários, OLS 3 (suporte)
    sel = sec[((sec.especificacao == "OLS 3") & (sec.amostra.isin(["suporte", "itens das compras da análise no suporte"])) &
               (sec.desfecho.str.startswith("desconto") | sec.desfecho.str.contains("prob"))) |
              ((sec.especificacao == "log P | produto × trimestre + X + UASG") & (sec.amostra == "suporte"))]
    sec["p_holm_familia_secundarios"] = np.nan
    sec.loc[sel.index, "p_holm_familia_secundarios"] = MD.holm(sel.p.to_numpy())
    S["sec"] = csv("desfechos_secundarios", sec)
    REG["nao_executado"].append("número de propostas: o nº de licitantes só existe nos PDFs, baixados para AF e "
                                "Fechado-Aberto, não para o Aberto; sem identificação comparável (nenhuma aproximação usada)")


# --------------------------------------------------------------------------------------------- 9. comparação
def e_comparacao():
    c, z = S["c"], S["z"]
    lin = []
    # (i) especificação do painel de 16/11 na amostra desta replicação
    for am, df in amostras_item().items():
        r = MD.reg(df, "y_logp", [], [("cnpj", "prod"), ("prod", "m")], None, ("cnpj", "u"), "af")
        o = linha(r, "painel de 16/11: log P | CNPJ × produto + produto × mês", am, "item", "log do preço (lp)", extra_amostra(df))
        o["referencia"] = "−4,5% [−6,9; −2,1] (191 mil itens, 656 CNPJs)"
        lin.append(o)
    # (ii) itens das UASGs tratadas do estudo de eventos, na janela [m − 6, m + 6)
    ev = pd.read_csv(AM.T23 / "eventos_did.csv")
    it = pd.read_pickle(DAD / "itens_eventos.pkl")
    partes = []
    for _, e in ev.iterrows():
        x = it[(it.u == e.u) & (it.m >= e.m - 6) & (it.m < e.m + 6)]
        partes.append(x.assign(k=int(e.k)))
    J = pd.concat(partes, ignore_index=True)
    J["y"] = 100 * J.e_ok
    J["w_compra"] = 1.0 / J.groupby(["k", "compra"]).compra.transform("size")
    for fes, rot in ((["k"], "dentro do evento (UASG tratada antes × depois)"),
                     (["k", "tri"], "dentro do evento + trimestre calendário")):
        for pesos in ("item", "compra"):
            r = MD.reg(J, "y", [], fes, None if pesos == "item" else J.w_compra.to_numpy(), ("cnpj", "u"), "af")
            o = linha(r, f"152 eventos: {rot}", "janelas do estudo de eventos (itens até 2026-04)", pesos)
            o["referencia"] = "estudo de eventos −1,91 lp [−5,67; 1,93] (diferença contra controles)"
            o["eventos"] = int(J.k.nunique())
            lin.append(o)
    S["comp"] = csv("comparacao_estudos_anteriores", lin)


def e_graficos():
    import graficos_als as G
    return G.main(AQUI)


ETAPAS = [("4_ols", e_ols), ("5_interacoes", e_interacoes), ("6_matching", e_matching), ("7_robustez", e_robustez),
          ("7b_regressao_mediana_R", e_qr), ("8_desfechos_secundarios", e_secundarios), ("9_comparacao", e_comparacao)]
PEDIDAS = None                                            # --etapas=7_robustez,10_graficos retoma só essas etapas


def main():
    global PEDIDAS
    for a in sys.argv[1:]:
        if a.startswith("--etapas="):
            PEDIDAS = set(a.split("=", 1)[1].split(","))
    # amostra, escore e suporte sempre rodam: são o estado das demais etapas (determinísticos)
    if etapa("1_amostra", e_amostra) is None and "c" not in S:
        return fim()
    etapa("2_logit_escore", e_logit)
    etapa("3_suporte_comum", e_suporte)
    for nome, f in ETAPAS:
        if PEDIDAS is None or nome in PEDIDAS:
            etapa(nome, f)
    if PEDIDAS is None or "10_graficos" in PEDIDAS:
        g = etapa("10_graficos", e_graficos)
        if g:
            REG["graficos"] = g.get("graficos")
    fim()


def fim():
    arq = AQUI / "registro_execucao.json"
    if PEDIDAS is not None and arq.exists():             # retomada: mantém o registro das etapas não refeitas
        antigo = json.loads(arq.read_text(encoding="utf-8"))
        etapas = {**antigo.get("etapas", {}), **REG["etapas"]}
        falhas = [f for f in antigo.get("falhas", []) if f.split(":")[0] not in REG["etapas"]] + REG["falhas"]
        for k, v in antigo.items():
            if k not in REG:
                REG[k] = v
        for k in ("conferencias", "versoes"):
            REG[k] = {**antigo.get(k, {}), **REG.get(k, {})}
        REG["nao_executado"] = list(dict.fromkeys(antigo.get("nao_executado", []) + REG["nao_executado"]))
        REG["etapas"], REG["falhas"] = etapas, falhas
        REG.setdefault("retomadas", list(antigo.get("retomadas", [])))
        REG["retomadas"].append({"etapas": sorted(PEDIDAS), "inicio": REG["inicio"]})
        REG["inicio"] = antigo.get("inicio", REG["inicio"])
    REG["limitacoes"] = [
        "A escolha do modo não foi aleatorizada; o modo tem forte persistência institucional por UASG.",
        "O matching não elimina confundimento não observado; equilíbrio observado não é validade causal.",
        "As UASGs que usam os dois modos podem não representar as demais.",
        "O índice pode conter heterogeneidade técnica dentro do CATMAT.",
        "O preço homologado só existe para itens com contratação bem-sucedida.",
        "Não há o subconjunto aleatorizado do artigo; os modos híbridos brasileiros não são os leilões do artigo.",
        "A variância agrupada do matching é uma adaptação (não é estimador consagrado)."]
    REG["fim"] = time.strftime("%Y-%m-%d %H:%M:%S")
    REG["segundos_total" if PEDIDAS is None else "segundos_ultima_retomada"] = round(time.time() - T0, 1)
    (AQUI / "registro_execucao.json").write_text(json.dumps(REG, ensure_ascii=False, indent=1, default=str),
                                                 encoding="utf-8", newline="\n")
    log("fim", {k: v["status"] for k, v in REG["etapas"].items()})


if __name__ == "__main__":
    main()
