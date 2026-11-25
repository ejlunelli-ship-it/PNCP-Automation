"""Etapa 1 do HonestDiD (protocolo.md). EXPLORATÓRIO.

Reproduz o M0 e o perfil por trimestre de 23/11; monta, para cada especificação, o vetor de coeficientes dinâmicos e a
matriz de covariância conjunta por órgão (CR1; jackknife e bootstrap de pares como verificação); grava
- entradas/beta.csv, entradas/sigma.csv e entradas/manifesto.csv (lidos por executar.R);
- tabelas de coeficientes, covariâncias, pré-tendência e poder, reprodução, diferença de estimando e influência;
- o conjunto identificado no ponto estimado por programação linear (conferência das funções internas do pacote).
Não lê o pncp.db; não altera bases nem resultados anteriores; não usa os eventos reservados (posteriores a 2025-10).
"""
import json, sys, time
from pathlib import Path

sys.dont_write_bytecode = True
AQUI = Path(__file__).resolve().parent
ROB = AQUI.parent / "robustez_dispersao_20261123"
T23 = AQUI.parent / "testes_desenho_causal_20261123"
sys.path.insert(0, str(ROB))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import optimize, stats  # noqa: E402

import motor_robustez as MR  # noqa: E402
import comum as C  # noqa: E402

ENT, TAB = AQUI / "entradas", AQUI / "tabelas"
B_BOOT, SEMENTE = 9999, 20261124
FIM_EVENTO = (2025 * 12 + 9) - C.M0                                    # 2025-10
REF_M0 = {"coef": -1.91, "ic": [-5.67, 1.93], "p": 0.32, "eventos": 152, "orgaos": 70}
REF_M1 = -3.76
MBAR = [0, 0.5, 1, 1.5, 2, 3]
MSD = [0, 0.25, 0.5, 1, 1.5, 2, 3]
MIN_EV, MIN_ORG = 30, 20


# --------------------------------------------------------------------------------------------- trimestres por evento
def painel(B, k, r, y, W, mascara=None):
    """Média por compra do índice por unidade × trimestre relativo, com as mesmas regras de Base.evento (motor de 23/11):
    tratada com ≥ CMIN compras em cada meia janela, controles candidatos com ≥ CMIN em cada meia janela, ≥ 5 controles."""
    u, m = int(r.u), int(r.m)
    rows = B.linhas(k, u, m, r.tipo, W)
    if len(rows) == 0:
        return None
    yv = B.it[y].to_numpy()[rows]
    ok = np.isfinite(yv)
    if mascara is not None:
        ok &= mascara[rows]
    rows, yv = rows[ok], yv[ok]
    if len(rows) == 0:
        return None
    uu, mm, cod = B.u_arr[rows], B.m_arr[rows], B.it.cod.to_numpy()[rows]
    cu, inv = np.unique(cod, return_inverse=True)
    nit = np.bincount(inv)
    yc = np.bincount(inv, yv) / nit
    ucomp = np.zeros(len(cu), int); ucomp[inv] = uu
    mcomp = np.zeros(len(cu), int); mcomp[inv] = mm
    pos = (mcomp >= m).astype(int)
    uni, uinv = np.unique(ucomp, return_inverse=True)
    Ct = np.bincount(uinv * 2 + pos, None, 2 * len(uni)).reshape(-1, 2)
    jt = np.searchsorted(uni, u)
    if jt >= len(uni) or uni[jt] != u or Ct[jt, 0] < MR.CMIN or Ct[jt, 1] < MR.CMIN:
        return None
    okc = (Ct[:, 0] >= MR.CMIN) & (Ct[:, 1] >= MR.CMIN)
    okc[jt] = False
    if okc.sum() < 5:
        return None
    nb = 2 * W // 3
    ch = uinv * nb + ((mcomp - m) // 3 + nb // 2)
    Nb = np.bincount(ch, None, len(uni) * nb).reshape(-1, nb)
    Ib = np.bincount(ch, nit, len(uni) * nb).reshape(-1, nb)
    with np.errstate(invalid="ignore", divide="ignore"):
        yb = np.bincount(ch, yc, len(uni) * nb).reshape(-1, nb) / Nb
    return {"uni": uni, "jt": jt, "okc": okc, "yb": yb, "Nb": Nb, "Ib": Ib, "nb": nb}


def dids(P, ref):
    """DiD de cada trimestre q contra o trimestre de referência: tratada com compra em q e na referência; controles com
    compra nos dois; ≥ 5 controles. Igual ao bloco `bins` de Base.evento quando ref = −1."""
    nb = P["nb"]
    rot = list(range(-nb // 2, nb // 2))
    iref = rot.index(ref)
    yb, jt, okc, Nb, Ib = P["yb"], P["jt"], P["okc"], P["Nb"], P["Ib"]
    out = {}
    for jb, q in enumerate(rot):
        if q == ref:
            continue
        okb = okc & np.isfinite(yb[:, jb]) & np.isfinite(yb[:, iref])
        if np.isfinite(yb[jt, jb]) and np.isfinite(yb[jt, iref]) and okb.sum() >= 5:
            db = yb[:, jb] - yb[:, iref]
            out[q] = {"d": float(db[jt] - db[okb].mean()), "nc": int(okb.sum()),
                      "cp": int(Nb[jt, jb] + Nb[jt, iref]), "it": int(Ib[jt, jb] + Ib[jt, iref]), "ctrl": P["uni"][okb]}
    return out


def tabela_eventos(B, E, base_df, y, W, ref, mascara=None):
    """Uma linha por evento do modelo (saída de Base.rodar), com o DiD por trimestre contra `ref`. Com ref = −1, confere
    cada valor com as colunas b* do motor."""
    linhas, ctrl, dif, n_conf = [], {}, 0.0, 0
    for _, r in base_df.iterrows():
        k = int(r.k)
        P = painel(B, k, E.loc[k], y, W, mascara)
        if P is None:
            raise RuntimeError(f"evento {k}: o painel não reproduz a elegibilidade do motor")
        D = dids(P, ref)
        z = {"k": k, "u": int(r.u), "cnpj": str(r.cnpj), "tipo": r.tipo, "sinal": int(r.sinal), "h": float(r.h),
             "did": float(r.did), "itens_tratada": int(r.itens_tratada), "compras_tratada": int(r.compras_tratada),
             "n_controles": int(r.n_controles)}
        for q, v in D.items():
            z[f"q{q}"], z[f"nc{q}"], z[f"cp{q}"], z[f"it{q}"] = v["d"], v["nc"], v["cp"], v["it"]
            ctrl[(k, q)] = v["ctrl"]
        if ref == -1:
            for c in [c for c in base_df.columns if c.startswith("b") and c[1:].lstrip("-").isdigit()]:
                q = int(c[1:])
                a, b = r[c], z.get(f"q{q}", np.nan)
                if np.isfinite(a) != np.isfinite(b):
                    raise RuntimeError(f"evento {k}, trimestre {q}: disponibilidade difere do motor")
                if np.isfinite(a):
                    dif = max(dif, abs(a - b)); n_conf += 1
        linhas.append(z)
    return pd.DataFrame(linhas), ctrl, {"max_dif_motor": dif, "valores_conferidos": n_conf}


# --------------------------------------------------------------------------------------------- vetor e covariâncias
def montar(T, cols, pesos="precisao", filtro=None):
    z = T if filtro is None else T[filtro(T)]
    Y = z.reindex(columns=cols).to_numpy(float) * z.sinal.to_numpy()[:, None]          # sinal do efeito do AF
    keep = np.isfinite(Y).any(1)
    z, Y = z[keep].reset_index(drop=True), Y[keep]
    w = MR.peso_precisao(z.h) if pesos == "precisao" else np.ones(len(z))
    g, orgs = pd.factorize(z.cnpj.astype(str))
    return {"z": z, "Y": Y, "w": np.asarray(w, float), "g": g, "orgs": np.asarray(orgs), "cols": cols}


def vetor(S, boot=True):
    """β_q = média ponderada dos eventos com dado em q. V CR1 conjunta por órgão: D^½ (Σ_g Ψ_g Ψ_g′) D^½,
    D = diag(G_q/(G_q − 1)); a diagonal é o EP CR1 de cada coeficiente (comum.ols_cr1 com X = 1)."""
    Y, w, g = S["Y"], S["w"], S["g"]
    G, Q = int(g.max()) + 1, Y.shape[1]
    M = np.isfinite(Y)
    A, Wt = np.zeros((G, Q)), np.zeros((G, Q))
    np.add.at(A, g, np.where(M, Y, 0.0) * w[:, None])
    np.add.at(Wt, g, M * w[:, None])
    At, Wtt = A.sum(0), Wt.sum(0)
    beta = At / Wtt
    Psi = (A - beta * Wt) / Wtt
    Gq = (Wt > 0).sum(0)
    c = Gq / (Gq - 1)
    V = np.sqrt(np.outer(c, c)) * (Psi.T @ Psi)
    out = {"beta": beta, "V": V, "Gq": Gq, "nq": M.sum(0), "G": G, "A": A, "Wt": Wt}
    with np.errstate(invalid="ignore", divide="ignore"):
        bj = (At - A) / (Wtt - Wt)
    okj = np.isfinite(bj).all(1)
    d = bj[okj] - bj[okj].mean(0)
    out["V_jack"] = (okj.sum() - 1) / okj.sum() * d.T @ d
    out["jack"] = bj
    out["jack_validos"] = int(okj.sum())
    if boot:
        rng = np.random.default_rng(SEMENTE)
        cnt = rng.multinomial(G, np.full(G, 1 / G), size=B_BOOT).astype(float)
        with np.errstate(invalid="ignore", divide="ignore"):
            bb = (cnt @ A) / (cnt @ Wt)
        okb = np.isfinite(bb).all(1)
        out["V_boot"] = np.atleast_2d(np.cov(bb[okb].T, ddof=1))
        out["boot_validos"] = int(okb.sum())
    return out


def contagens(S, ctrl):
    z, Y, w = S["z"], S["Y"], S["w"]
    M = np.isfinite(Y)
    linhas = []
    for j, c in enumerate(S["cols"]):
        mk = M[:, j]
        q = int(c[1:])
        sh = pd.Series(w[mk]).groupby(z.cnpj.to_numpy()[mk]).sum()
        sh = sh / sh.sum()
        cc = set()
        for k in z.k[mk]:
            cc.update(np.asarray(ctrl[(int(k), q)]).tolist())
        linhas.append({"trimestre": q, "eventos": int(mk.sum()), "n_A->AF": int((z.tipo[mk] == "A->AF").sum()),
                       "n_AF->A": int((z.tipo[mk] == "AF->A").sum()), "orgaos": int(len(sh)),
                       "orgaos_efetivos": float(1 / (sh ** 2).sum()), "maior_orgao_peso": float(sh.max()),
                       "maior_evento_peso": float(w[mk].max() / w[mk].sum()), "uasgs_tratadas": int(z.u[mk].nunique()),
                       "uasgs_controle": int(len(cc)), "compras_tratadas_q_e_ref": int(z[f"cp{q}"][mk].sum()),
                       "itens_tratadas_q_e_ref": int(z[f"it{q}"][mk].sum())})
    return linhas


def resumo_espec(S):
    z, w = S["z"], S["w"]
    sh = pd.Series(w).groupby(z.cnpj.to_numpy()).sum()
    sh = sh / sh.sum()
    return {"eventos": int(len(z)), "n_A->AF": int((z.tipo == "A->AF").sum()), "n_AF->A": int((z.tipo == "AF->A").sum()),
            "orgaos": int(len(sh)), "orgaos_efetivos": float(1 / (sh ** 2).sum()), "uasgs_tratadas": int(z.u.nunique()),
            "itens_tratadas_janela": int(z.itens_tratada.sum()), "compras_tratadas_janela": int(z.compras_tratada.sum()),
            "maior_orgao_peso": float(sh.max()), "maior_evento_peso": float(w.max() / w.sum())}


# --------------------------------------------------------------------------------------------- pré-tendência e poder
def pre_teste(beta, V, nPre, Gpre, ls):
    """Wald dos pré-coeficientes com a matriz conjunta e poder contra tendência linear δ_t = γ·t (Roth, 2022)."""
    b, Vp = beta[:nPre], V[:nPre, :nPre]
    Wst = float(b @ np.linalg.solve(Vp, b))
    t = np.arange(-nPre, 0, dtype=float)
    a = float(t @ np.linalg.solve(Vp, t))
    crit = stats.chi2.ppf(0.95, nPre)

    def lam(pw):
        return optimize.brentq(lambda L: stats.ncx2.sf(crit, nPre, L) - pw, 1e-9, 1e4)

    out = {"wald": Wst, "gl": nPre, "p_qui2": float(stats.chi2.sf(Wst, nPre)), "F": Wst / nPre,
           "p_F": float(stats.f.sf(Wst / nPre, nPre, Gpre - 1)), "G_pre": int(Gpre)}
    nPost = len(beta) - nPre
    tp = np.arange(1, nPost + 1, dtype=float)
    for pw in (0.5, 0.8):
        gam = float(np.sqrt(lam(pw) / a))
        out[f"gama_poder_{int(pw * 100)}"] = gam
        for nome, l in ls.items():
            out[f"vies_{nome}_poder_{int(pw * 100)}"] = float(gam * (np.asarray(l) @ tp))
    return out


# --------------------------------------------------------------------------------------------- conjunto identificado
def conjunto_identificado(beta, nPre, nPost, l, familia, valor):
    """Conjunto de θ = l′(β_pós − δ_pós) com δ_pré = β̂_pré e δ ∈ Δ (sem erro amostral). Programação linear."""
    l = np.asarray(l, float)
    dpre = np.r_[beta[:nPre], 0.0]                                    # δ_{−T}, …, δ_{−1}, δ_0 = 0
    th = float(l @ beta[nPre:])
    Aub, bub = [], []
    if familia == "RM":
        cap = valor * float(np.max(np.abs(np.diff(dpre))))
        for t in range(nPost):
            row = np.zeros(nPost); row[t] = 1.0
            if t > 0:
                row[t - 1] = -1.0
            Aub += [row, -row]; bub += [cap, cap]
    else:                                                              # SD
        n = nPre + 1 + nPost
        for i in range(1, n - 1):
            cf = np.zeros(n); cf[i - 1] += 1; cf[i] -= 2; cf[i + 1] += 1
            fixo, row = float(cf[:nPre + 1] @ dpre), cf[nPre + 1:]
            if not row.any():
                if abs(fixo) > valor + 1e-12:
                    return np.nan, np.nan                              # vazio: os pré-períodos violam Δ^SD(M)
                continue
            Aub += [row, -row]; bub += [valor - fixo, valor + fixo]
    Aub, bub = np.array(Aub), np.array(bub)
    bd = [(None, None)] * nPost
    lo = optimize.linprog(l, A_ub=Aub, b_ub=bub, bounds=bd, method="highs")
    hi = optimize.linprog(-l, A_ub=Aub, b_ub=bub, bounds=bd, method="highs")
    if not (lo.success and hi.success):
        return np.nan, np.nan
    return th + hi.fun, th - lo.fun


# --------------------------------------------------------------------------------------------- execução
def main(log=print):
    t0 = time.time()
    ENT.mkdir(parents=True, exist_ok=True)
    TAB.mkdir(parents=True, exist_ok=True)
    reg = {"conferencias": {}, "exclusoes": {}, "avisos": []}
    B = MR.Base(log=log)
    E6, E12 = B.eventos(6), B.eventos(12)
    for nome, E in (("janela_6", E6), ("janela_12", E12)):
        if not (E.m <= FIM_EVENTO).all():
            raise RuntimeError(f"evento reservado para validação entrou em {nome}")
    reg["conferencias"]["eventos_reservados"] = {
        "ultimo_mes_evento_janela_6": C.mes_str(C.M0 + int(E6.m.max())),
        "ultimo_mes_evento_janela_12": C.mes_str(C.M0 + int(E12.m.max())),
        "reservados_posteriores_a_2025_10": int((B.ev.m > FIM_EVENTO).sum()), "algum_reservado_usado": False}
    mask_f = (B.it.sd_G <= MR.LIM).to_numpy()
    M0 = B.rodar(E6, "e_ok")
    M1 = B.rodar(E6, "e_G", mascara=mask_f)
    M12 = B.rodar(E12, "e_ok", W=12)
    log("modelos", len(M0), len(M1), len(M12), round(time.time() - t0, 1), "s")

    # ---- reprodução
    R23 = json.loads((T23 / "resultados.json").read_text(encoding="utf-8"))
    rep = []
    r0, r1, r12 = MR.estimar(M0, B=B_BOOT), MR.estimar(M1, B=B_BOOT), MR.estimar(M12, B=B_BOOT)

    def add(item, obtido, referencia, tol):
        rep.append({"item": item, "obtido": obtido, "referencia": referencia, "dif": obtido - referencia,
                    "ok": bool(abs(obtido - referencia) <= tol)})

    add("M0 coef (lp)", r0["coef_lp"], REF_M0["coef"], 0.005)
    add("M0 IC95 WCR inf", r0["ic95_wcr"][0], REF_M0["ic"][0], 0.005)
    add("M0 IC95 WCR sup", r0["ic95_wcr"][1], REF_M0["ic"][1], 0.005)
    add("M0 p WCR", r0["p_wcr"], REF_M0["p"], 0.005)
    add("M0 eventos", r0["n_eventos"], REF_M0["eventos"], 0)
    add("M0 órgãos", r0["orgaos"], REF_M0["orgaos"], 0)
    add("M1 coef (lp)", r1["coef_lp"], REF_M1, 0.005)
    j12 = R23["sensibilidades"]["janela_12m"]
    add("janela 12 coef (lp)", r12["coef_lp"], 100 * j12["efeito_AF"]["est"], 1e-6)
    add("janela 12 eventos", r12["n_eventos"], j12["n"], 0)

    # ---- tabelas de eventos por trimestre
    T6, c6, v6 = tabela_eventos(B, E6, M0, "e_ok", 6, -1)
    T6a, c6a, _ = tabela_eventos(B, E6, M0, "e_ok", 6, -2)
    TF, cF, vF = tabela_eventos(B, E6, M1, "e_G", 6, -1, mascara=mask_f)
    T12, c12, v12 = tabela_eventos(B, E12, M12, "e_ok", 12, -1)
    T12a, c12a, _ = tabela_eventos(B, E12, M12, "e_ok", 12, -2)
    reg["conferencias"]["trimestres_iguais_ao_motor"] = {"janela_6": v6, "filtrado": vF, "janela_12": v12,
                                                         "ok": bool(max(v6["max_dif_motor"], vF["max_dif_motor"],
                                                                        v12["max_dif_motor"]) < 1e-12)}
    for nome, T in (("janela_6_ref-1", T6), ("janela_6_ref-2", T6a), ("filtrado_ref-1", TF), ("janela_12_ref-1", T12),
                    ("janela_12_ref-2", T12a)):
        T.assign(w_precisao=MR.peso_precisao(T.h)).to_csv(TAB / f"eventos_trimestres_{nome}.csv", index=False,
                                                          lineterminator="\n")
    log("trimestres", round(time.time() - t0, 1), "s")

    # ---- especificações
    pre6, pos6 = ["q-2"], ["q0", "q1"]
    pre12, pos12 = ["q-4", "q-3", "q-2"], ["q0", "q1", "q2", "q3"]
    tudo = lambda T: np.isfinite(T.reindex(columns=pre6 + pos6).to_numpy(float)).all(1)  # noqa: E731
    E = {   # id: (tabela, controles, colunas, nPre, pesos, filtro, descrição, amostra)
        "P1": (T6, c6, pre6 + pos6, 1, "precisao", None, "principal: janela de 6, ref. −1, combinado com sinal",
               "152 eventos do M0"),
        "D_AAF": (T6, c6, pre6 + pos6, 1, "precisao", lambda T: T.tipo.eq("A->AF"), "só A → AF", "eventos A → AF do M0"),
        "D_AFA": (T6, c6, pre6 + pos6, 1, "precisao", lambda T: T.tipo.eq("AF->A"),
                  "só AF → A, sinal do efeito do AF (× −1)", "eventos AF → A do M0"),
        "S_IGUAIS": (T6, c6, pre6 + pos6, 1, "iguais", None, "pesos iguais por evento", "152 eventos do M0"),
        "S_BAL": (T6, c6, pre6 + pos6, 1, "precisao", tudo, "balanceado: eventos com os três trimestres",
                  "subconjunto do M0"),
        "F1": (TF, cF, pre6 + pos6, 1, "precisao", None, "filtrado: referência G, dispersão ≤ 0,80 (exploratório)",
               "150 eventos do M1"),
        "ANT12": (T12a, c12a, ["q-4", "q-3", "q-1", "q0", "q1"], 2, "precisao", None,
                  "antecipação: janela de 12, ref. −2; pós = −1, 0, +1", "78 eventos da janela de 12"),
    }
    for p in (1, 2, 3):
        for s in (2, 4):
            E[f"J12_pre{p}_pos{s}"] = (T12, c12, pre12[3 - p:] + pos12[:s], p, "precisao", None,
                                      f"janela de 12, ref. −1, {p} pré e {s} pós", "78 eventos da janela de 12")
    ESP, coef, cov, verif, pre, manif, betas, sigmas, ident = {}, [], [], [], [], [], [], [], []

    def params(id_, nPost):
        if id_ == "ANT12":
            return {"a": [0, 1, 0], "b": [0, .5, .5], "antecipacao": [1, 0, 0]}
        return {"a": [1.0] + [0.0] * (nPost - 1), "b": [1.0 / nPost] * nPost}

    def gravar(id_, beta, V, cols, nPre, grade, par, sdrm):
        for i, (c, b) in enumerate(zip(cols, beta), 1):
            betas.append({"id": id_, "ordem": i, "trimestre": int(c[1:]), "beta_lp": 100 * b})
        for i in range(len(cols)):
            for j in range(len(cols)):
                sigmas.append({"id": id_, "i": i + 1, "j": j + 1, "valor_lp2": 1e4 * V[i, j]})
        for nome, l in par.items():
            manif.append({"id": f"{id_}|{nome}", "espec": id_, "parametro": nome, "numPre": nPre,
                          "numPost": len(cols) - nPre, "l_vec": ";".join(f"{x:g}" for x in l), "grade": grade,
                          "sdrm": int(sdrm)})

    for id_, (T, ctrl, cols, nPre, pesos, filtro, desc, amostra) in E.items():
        S = montar(T, cols, pesos, filtro)
        res = vetor(S)
        ESP[id_] = (S, res)
        cnt = contagens(S, ctrl)
        beta, V = res["beta"], res["V"]
        par = params(id_, len(cols) - nPre)
        Gpre = int((res["Wt"][:, :nPre] > 0).any(1).sum())
        for j, (c, n) in enumerate(zip(cols, cnt)):
            mk = np.isfinite(S["Y"][:, j])
            mi = C.media_inferencia(S["Y"][mk, j], S["z"].cnpj.to_numpy()[mk], S["w"][mk], B_BOOT, ic=False)
            se = float(np.sqrt(V[j, j]))
            tq = stats.t.ppf(.975, res["Gq"][j] - 1)
            coef.append({"espec": id_, "descricao": desc, "amostra": amostra, "pesos": pesos,
                         "periodo": "pré" if j < nPre else "pós", **n, "coef_lp": 100 * beta[j], "ep_lp": 100 * se,
                         "ic95_normal_inf": 100 * (beta[j] - 1.96 * se), "ic95_normal_sup": 100 * (beta[j] + 1.96 * se),
                         "ic95_t_inf": 100 * (beta[j] - tq * se), "ic95_t_sup": 100 * (beta[j] + tq * se),
                         "p_normal": float(2 * stats.norm.sf(abs(beta[j] / se))), "p_t": mi["p_t"], "p_wcr": mi["p_wild"],
                         "conf_media_inferencia_dif": abs(mi["est"] - beta[j]) + abs(mi["ep"] - se),
                         "baixa_precisao": bool(n["eventos"] < MIN_EV or n["orgaos"] < MIN_ORG)})
        for nomeV in ("V", "V_jack", "V_boot"):
            Vx = res[nomeV]
            ev_ = np.linalg.eigvalsh(Vx)
            d = np.sqrt(np.diag(Vx))
            corr = Vx / np.outer(d, d)
            verif.append({"espec": id_, "estimador": {"V": "CR1", "V_jack": "jackknife", "V_boot": "bootstrap"}[nomeV],
                          "autovalor_min_lp2": 1e4 * ev_.min(), "autovalor_max_lp2": 1e4 * ev_.max(),
                          "numero_condicao": float(ev_.max() / ev_.min()) if ev_.min() > 0 else np.inf,
                          "semidefinida_positiva": bool(ev_.min() > -1e-14),
                          "ep_lp": ";".join(f"{100 * x:.3f}" for x in d),
                          "razao_ep_vs_CR1": ";".join(f"{x:.3f}" for x in d / np.sqrt(np.diag(res["V"]))),
                          "correlacoes": ";".join(f"{corr[i, j]:.3f}" for i in range(len(d)) for j in range(i + 1, len(d))),
                          "replicas_validas": res.get("boot_validos") if nomeV == "V_boot" else
                          (res["jack_validos"] if nomeV == "V_jack" else res["G"])})
            for i in range(len(cols)):
                for j in range(len(cols)):
                    cov.append({"espec": id_, "estimador": verif[-1]["estimador"], "trimestre_i": int(cols[i][1:]),
                                "trimestre_j": int(cols[j][1:]), "valor_lp2": 1e4 * Vx[i, j]})
        pre.append({"espec": id_, "descricao": desc, **pre_teste(100 * beta, 1e4 * V, nPre, Gpre, par),
                    "pre_coefs_lp": ";".join(f"{100 * b:.3f}" for b in beta[:nPre])})
        resumo = resumo_espec(S)
        ESP[id_] = (S, res, resumo, desc, amostra, nPre, cols)
        gravar(id_, beta, V, cols, nPre, "completa", par, sdrm=(nPre >= 2))
        for nome, l in par.items():
            for fam, grade in (("RM", MBAR), ("SD", MSD)):
                for v in grade:
                    lb, ub = conjunto_identificado(100 * beta, nPre, len(cols) - nPre, l, fam, v)
                    ident.append({"id": f"{id_}|{nome}", "familia": fam, "valor": v, "id_lb_py": lb, "id_ub_py": ub})
        if id_ == "P1":
            for nomeV, sufixo in (("V_jack", "P1_JACK"), ("V_boot", "P1_BOOT")):
                gravar(sufixo, beta, res[nomeV], cols, nPre, "completa", par, sdrm=False)
                ESP[sufixo] = (S, {**res, "V": res[nomeV]}, resumo, f"principal com matriz {nomeV[2:]}", amostra, nPre,
                               cols)
    log("especificações", round(time.time() - t0, 1), "s")

    # ---- diagnóstico de antecipação na janela de 6 (ref. −2; sem pré-período: HonestDiD não se aplica)
    Sa = montar(T6a, ["q-1", "q0", "q1"])
    ra = vetor(Sa, boot=False)
    for j, (c, n) in enumerate(zip(Sa["cols"], contagens(Sa, c6a))):
        se = float(np.sqrt(ra["V"][j, j]))
        mk = np.isfinite(Sa["Y"][:, j])
        mi = C.media_inferencia(Sa["Y"][mk, j], Sa["z"].cnpj.to_numpy()[mk], Sa["w"][mk], B_BOOT, ic=False)
        coef.append({"espec": "ANT6", "descricao": "antecipação: janela de 6, ref. −2 (diagnóstico; sem pré-período)",
                     "amostra": "152 eventos do M0", "pesos": "precisao", "periodo": "pós/antecipação", **n,
                     "coef_lp": 100 * ra["beta"][j], "ep_lp": 100 * se,
                     "ic95_normal_inf": 100 * (ra["beta"][j] - 1.96 * se), "ic95_normal_sup": 100 * (ra["beta"][j] + 1.96 * se),
                     "ic95_t_inf": np.nan, "ic95_t_sup": np.nan, "p_normal": float(2 * stats.norm.sf(abs(ra["beta"][j] / se))),
                     "p_t": mi["p_t"], "p_wcr": mi["p_wild"], "conf_media_inferencia_dif": abs(mi["est"] - ra["beta"][j]),
                     "baixa_precisao": bool(n["eventos"] < MIN_EV or n["orgaos"] < MIN_ORG)})

    # ---- reprodução do perfil de 23/11
    for c, (nome, ref) in {"q-2": ("b-2", -2), "q0": ("b0", 0), "q1": ("b1", 1)}.items():
        v = R23["perfil"][nome]["efeito_AF"]
        x = [r for r in coef if r["espec"] == "P1" and r["trimestre"] == ref][0]
        add(f"perfil 23/11 {nome} coef (lp)", x["coef_lp"], 100 * v["est"], 1e-6)
        add(f"perfil 23/11 {nome} EP (lp)", x["ep_lp"], 100 * v["ep"], 1e-6)
        add(f"perfil 23/11 {nome} p WCR", x["p_wcr"], v["p_wild"], 1e-9)
        add(f"perfil 23/11 {nome} eventos", x["eventos"], R23["perfil"][nome]["n"], 0)
    for nome, v in R23["sensibilidades"]["janela_12m_perfil"].items():
        if "efeito_AF" not in v:
            continue
        x = [r for r in coef if r["espec"] == "J12_pre3_pos4" and r["trimestre"] == int(nome[1:])][0]
        add(f"janela 12 {nome} coef (lp)", x["coef_lp"], 100 * v["efeito_AF"]["est"], 1e-6)
        add(f"janela 12 {nome} eventos", x["eventos"], v["n"], 0)
    reg["conferencias"]["reproducao_ok"] = bool(all(r["ok"] for r in rep))

    # ---- diferença de estimando (P1 × M0)
    S1, res1 = ESP["P1"][0], ESP["P1"][1]
    z1 = S1["z"]
    w1 = S1["w"]
    y_did = (z1.sinal * z1.did).to_numpy(float)
    Y1 = S1["Y"]
    def wm(v, mk):  # noqa: E306
        return float(100 * np.sum(w1[mk] * v[mk]) / np.sum(w1[mk]))
    ambos = np.isfinite(Y1[:, 1]) & np.isfinite(Y1[:, 2])
    bal = np.isfinite(Y1).all(1)
    tod = np.ones(len(z1), bool)
    w_all = MR.peso_precisao(T6.h)
    dif_est = [
        {"medida": "M0: meia janela pós − pré, todos os eventos do M0", "eventos": int(len(T6)),
         "valor_lp": float(100 * np.sum(w_all * T6.sinal * T6.did) / np.sum(w_all))},
        {"medida": "M0 nos eventos do perfil (tratada com compra no trimestre −1)", "eventos": int(tod.sum()),
         "valor_lp": wm(y_did, tod)},
        {"medida": "M0 nos eventos com trimestres 0 e +1", "eventos": int(ambos.sum()), "valor_lp": wm(y_did, ambos)},
        {"medida": "M0 nos eventos balanceados (−2, 0, +1)", "eventos": int(bal.sum()), "valor_lp": wm(y_did, bal)},
        {"medida": "parâmetro (b): (β0 + β+1)/2, cada trimestre com seus eventos", "eventos": int(np.isfinite(Y1[:, 1:]).any(1).sum()),
         "valor_lp": float(100 * res1["beta"][1:].mean())},
        {"medida": "média por evento de (q0 + q+1)/2, eventos com os dois", "eventos": int(ambos.sum()),
         "valor_lp": wm((Y1[:, 1] + Y1[:, 2]) / 2, ambos)},
        {"medida": "balanceados: (q0 + q+1)/2 − q−2/2 (análogo do M0 em trimestres)", "eventos": int(bal.sum()),
         "valor_lp": wm((Y1[:, 1] + Y1[:, 2]) / 2 - Y1[:, 0] / 2, bal)},
    ]

    # ---- influência: retirar um órgão por vez (P1)
    loo = []
    for gi, org in enumerate(S1["orgs"]):
        keep = S1["g"] != gi
        Sl = {**S1, "z": S1["z"][keep].reset_index(drop=True), "Y": S1["Y"][keep], "w": S1["w"][keep]}
        Sl["g"] = pd.factorize(Sl["z"].cnpj.astype(str))[0]
        rl = vetor(Sl, boot=False)
        lid = f"LOO{gi + 1:02d}"
        gravar(lid, rl["beta"], rl["V"], S1["cols"], 1, "loo", params("P1", 2), sdrm=False)
        loo.append({"id": lid, "orgao_retirado": org, "eventos_retirados": int((~keep).sum()),
                    "peso_do_orgao": float(S1["w"][~keep].sum() / S1["w"].sum()),
                    **{f"coef_{c}": 100 * b for c, b in zip(S1["cols"], rl["beta"])},
                    **{f"ep_{c}": 100 * np.sqrt(rl["V"][i, i]) for i, c in enumerate(S1["cols"])},
                    "eventos_restantes": int(keep.sum())})

    # ---- gravação
    def csv(nome, linhas):
        pd.DataFrame(linhas).to_csv(TAB / f"{nome}.csv", index=False, lineterminator="\n")

    pd.DataFrame(betas).to_csv(ENT / "beta.csv", index=False, lineterminator="\n")
    pd.DataFrame(sigmas).to_csv(ENT / "sigma.csv", index=False, lineterminator="\n", float_format="%.12g")
    pd.DataFrame(manif).to_csv(ENT / "manifesto.csv", index=False, lineterminator="\n")
    csv("reproducao", rep)
    csv("coeficientes_dinamicos", coef)
    csv("covariancias", cov)
    csv("verificacao_covariancia", verif)
    csv("pre_tendencia_e_poder", pre)
    csv("diferenca_estimando", dif_est)
    csv("influencia_orgaos_coeficientes", loo)
    csv("conjunto_identificado_python", ident)
    resumo = [{"espec": k, "descricao": v[3], "amostra": v[4], "numPre": v[5], "numPost": len(v[6]) - v[5],
               "trimestres": ";".join(c[1:] for c in v[6]), **v[2]} for k, v in ESP.items()]
    csv("especificacoes", resumo)
    reg["especificacoes"] = {r["espec"]: {k: r[k] for k in ("eventos", "orgaos", "orgaos_efetivos", "numPre", "numPost")}
                             for r in resumo}
    reg["reproducao"] = rep
    reg["M0"] = {k: r0[k] for k in ("coef_lp", "ep_lp", "ic95_wcr", "p_wcr", "n_eventos", "orgaos", "orgaos_efetivos",
                                    "itens_tratadas", "compras_tratadas", "uasgs_tratadas", "uasgs_controle")}
    reg["M1"] = {k: r1[k] for k in ("coef_lp", "ep_lp", "ic95_wcr", "p_wcr", "n_eventos", "orgaos", "orgaos_efetivos")}
    reg["janela_12"] = {k: r12[k] for k in ("coef_lp", "ep_lp", "ic95_wcr", "p_wcr", "n_eventos", "orgaos")}
    reg["exclusoes"] = {
        "M0_eventos_sem_trimestre_-2": int((~np.isfinite(T6.get("q-2", pd.Series(np.nan, index=T6.index)))).sum()),
        "M0_eventos_sem_trimestre_0": int((~np.isfinite(T6.get("q0", pd.Series(np.nan, index=T6.index)))).sum()),
        "M0_eventos_sem_trimestre_+1": int((~np.isfinite(T6.get("q1", pd.Series(np.nan, index=T6.index)))).sum()),
        "janela_12_candidatos": int(len(E12)), "janela_12_com_estimativa": int(len(M12)),
        "janela_6_candidatos": int(len(E6)), "janela_6_com_estimativa": int(len(M0))}
    reg["segundos"] = round(time.time() - t0, 1)
    log("etapa Python concluída", reg["segundos"], "s; reprodução ok:", reg["conferencias"]["reproducao_ok"])
    return reg


if __name__ == "__main__":
    r = main()
    print(json.dumps({k: r[k] for k in ("conferencias", "exclusoes")}, ensure_ascii=False, indent=1, default=str))
