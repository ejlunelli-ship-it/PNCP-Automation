"""Regime de modo por UASG, identificação de eventos e estudo de eventos (protocolo §8–10).

Estimador principal: de Chaisemartin e D'Haultfœuille (DID_l, "intertemporal treatment effects"), adequado a
tratamento reversível: cada UASG que muda de regime pela primeira vez (F_g) é comparada, entre F_g−1 e F_g−1+l,
com UASGs de mesmo regime inicial que ainda não mudaram até F_g−1+l. Adoção (A→AF) e abandono (AF→A) são
estimados separadamente; o sinal é normalizado para "efeito do AF" (abandono entra com sinal −1).
Sensibilidade: imputação de Borusyak–Jaravel–Spiess (BJS) só no subconjunto absorvente (adotantes sem volta e
nunca tratados), onde suas condições valem.
Inferência: bootstrap por CNPJ (reamostragem de órgãos com reposição), mesma semente.
"""
import numpy as np
import pandas as pd

from . import comum
from .comum import nome_trimestre

IRREGULAR, NUNCA, TROCA, SEM_PRE = "irregular", "nunca_troca", "troca", "troca_sem_pre_adjacente"


# ------------------------------------------------------------------------------------------- regime e eventos

def painel_regime(reg_c, tri_ini, tri_fim, limiar=0.5, puro=(0.10, 0.90)):
    """Fração AF por UASG × trimestre (todas as compras A/AF da fonte) e regime D (1 = AF, NaN sem compra)."""
    r = reg_c[(reg_c.tri >= tri_ini) & (reg_c.tri <= tri_fim)].copy()
    g = r.groupby(["uasg", "tri"], observed=True).agg(n=("af", "size"), n_af=("af", "sum")).reset_index()
    g["frac_af"] = g.n_af / g.n
    g["D"] = (g.frac_af >= limiar).astype(int)
    g["puro"] = ((g.frac_af <= puro[0]) | (g.frac_af >= puro[1])).astype(int)
    return g


def classificar_unidades(reg_tab, tri_ini, tri_fim, persist=2):
    """Para cada UASG: regime inicial d0, primeiro trimestre de mudança F (persistente), tipo e direção.
    Regras (protocolo §9): F = 1º trimestre observado com D ≠ d0; é troca válida se o trimestre F−1 é observado com
    D = d0 e os `persist` trimestres F..F+persist−1 são observados com D ≠ d0. Se a 1ª mudança não persiste, a
    UASG é irregular (fora de tratados e controles). Se F−1 não é observado, é troca sem pré adjacente (fora)."""
    T = tri_fim - tri_ini + 1
    linhas = []
    for u, s in reg_tab.groupby("uasg", observed=True):
        D = np.full(T, np.nan)
        D[(s.tri - tri_ini).to_numpy()] = s.D.to_numpy()
        P = np.full(T, np.nan)
        P[(s.tri - tri_ini).to_numpy()] = s.puro.to_numpy()
        obs = np.flatnonzero(~np.isnan(D))
        if obs.size == 0:
            continue
        d0 = D[obs[0]]
        dif = obs[D[obs] != d0]
        if dif.size == 0:
            linhas.append({"uasg": u, "d0": int(d0), "F": None, "tipo": NUNCA, "direcao": None, "puro": None})
            continue
        F = int(dif[0])
        pers = all(0 <= F + k < T and not np.isnan(D[F + k]) and D[F + k] != d0 for k in range(persist))
        if not pers:
            tipo = IRREGULAR
        elif F - 1 < 0 or np.isnan(D[F - 1]):
            tipo = SEM_PRE
        else:
            tipo = TROCA
        puro = int(tipo == TROCA and P[F - 1] == 1 and P[F] == 1)
        linhas.append({"uasg": u, "d0": int(d0), "F": F, "tipo": tipo,
                       "direcao": ("A->AF" if d0 == 0 else "AF->A") if tipo == TROCA else None, "puro": puro})
    return pd.DataFrame(linhas)


# ------------------------------------------------------------------------------------------- dCDH

class DCDH:
    """Estimador DID_l de dCDH sobre um painel UASG × trimestre (Y com NaN onde não há itens com índice).

    Y, N: matrizes U × T (N = peso da célula: nº de itens, nº de compras ou 1). info: DataFrame alinhado às linhas
    com d0, F (ou NaN), tipo. Pré-computa, para cada (d0, F, l), switchers e controles; `estimar(m)` aceita
    multiplicidades por UASG (bootstrap)."""

    def __init__(self, Y, N, info, L, Lpre, peso_switcher="celula", min_controles=5):
        self.Y, self.N, self.L, self.Lpre = Y, N, L, Lpre
        U, T = Y.shape
        d0 = info["d0"].to_numpy()
        F = info["F"].to_numpy(dtype=float)
        tipo = info["tipo"].to_numpy()
        valido = (tipo == TROCA) | (tipo == NUNCA)
        F_ctrl = np.where(tipo == NUNCA, np.inf, F)              # trimestre da 1ª troca (∞ se nunca)
        self.blocos = []                                         # (chave, s_idx, sinais, dY_s, w_s, c_idx, dY_c, N_c)
        sw = np.flatnonzero(tipo == TROCA)
        for l in list(range(1, L + 1)) + [-k for k in range(1, Lpre + 1)]:
            for (dd, ff), grp in pd.Series(sw).groupby([d0[sw], F[sw]]):
                ff = int(ff)
                base = ff - 1
                alvo = ff - 1 + l                                  # efeito: F−1+l; placebo (l = −k): F−1−k
                # controles: mesmo d0, válidos, sem troca até o último período usado (F−1+l nos efeitos; F−1+k
                # no placebo correspondente, para usar o mesmo grupo de controle do efeito l=k)
                ult = ff - 1 + (l if l > 0 else -l)
                if alvo < 0 or alvo >= T or ult >= T:
                    continue
                s_idx = grp.to_numpy()
                ok_s = ~np.isnan(Y[s_idx, base]) & ~np.isnan(Y[s_idx, alvo])
                s_idx = s_idx[ok_s]
                if s_idx.size == 0:
                    continue
                c_mask = valido & (d0 == dd) & (F_ctrl > ult) & ~np.isnan(Y[:, base]) & ~np.isnan(Y[:, alvo])
                c_idx = np.flatnonzero(c_mask)
                if c_idx.size < min_controles:
                    continue
                dY_s = Y[s_idx, alvo] - Y[s_idx, base]
                dY_c = Y[c_idx, alvo] - Y[c_idx, base]
                N_c = N[c_idx, alvo]
                w_s = N[s_idx, alvo] if peso_switcher == "celula" else np.ones(s_idx.size)
                sinal = np.where(dd == 0, 1.0, -1.0)
                self.blocos.append({"l": l, "d0": int(dd), "F": ff, "s": s_idx, "dY_s": dY_s, "w_s": w_s,
                                    "c": c_idx, "dY_c": dY_c, "N_c": N_c, "sinal": float(sinal)})

    def estimar(self, m=None):
        """Retorna dict {(grupo, l): estimativa} para grupo em adocao, abandono, agregado; e pesos."""
        U = self.Y.shape[0]
        m = np.ones(U) if m is None else m
        acc = {}
        for b in self.blocos:
            mc = m[b["c"]] * b["N_c"]
            if mc.sum() <= 0:
                continue
            ctrl = np.sum(mc * b["dY_c"]) / mc.sum()
            did = b["dY_s"] - ctrl
            ws = m[b["s"]] * b["w_s"]
            grupo = "adocao" if b["d0"] == 0 else "abandono"
            for gname in (grupo, "agregado"):
                k = (gname, b["l"])
                num, den = acc.get(k, (0.0, 0.0))
                acc[k] = (num + np.sum(ws * b["sinal"] * did), den + ws.sum())
        out = {k: (num / den if den > 0 else np.nan) for k, (num, den) in acc.items()}
        pesos = {k: den for k, (num, den) in acc.items()}
        for gname in ("adocao", "abandono", "agregado"):
            ls = [l for l in range(1, self.L + 1) if (gname, l) in out and np.isfinite(out[(gname, l)])]
            if ls:
                wl = np.array([pesos[(gname, l)] for l in ls])
                out[(gname, "media")] = float(np.sum(wl * np.array([out[(gname, l)] for l in ls])) / wl.sum())
        if ("adocao", "media") in out and ("abandono", "media") in out:
            out[("simetria", "media")] = out[("adocao", "media")] - out[("abandono", "media")]
        return out, pesos

    def populacao(self):
        """Switchers e controles usados em cada l (para o registro da população de eventos e dos pesos)."""
        linhas = []
        for b in self.blocos:
            for s, w in zip(b["s"], b["w_s"]):
                linhas.append({"linha": int(s), "l": b["l"], "d0": b["d0"], "F": b["F"], "peso": float(w),
                               "controles": int(b["c"].size)})
        return pd.DataFrame(linhas)


def bootstrap(est, cnpj_cod, B, semente, jackknife=False):
    """Bootstrap por CNPJ: multiplicidade m_u = nº de vezes que o CNPJ da UASG foi sorteado."""
    rng = np.random.default_rng(semente)
    G = cnpj_cod.max() + 1
    ponto, pesos = est.estimar()
    chaves = sorted(ponto, key=str)
    draws = np.full((B, len(chaves)), np.nan)
    for b in range(B):
        cont = np.bincount(rng.integers(0, G, G), minlength=G).astype(float)
        e, _ = est.estimar(cont[cnpj_cod])
        draws[b] = [e.get(k, np.nan) for k in chaves]
    return ponto, pesos, chaves, draws


def jackknife_cnpj(est, cnpj_cod, alvo=("agregado", "media"), cnpjs=None):
    G = cnpj_cod.max() + 1
    res = []
    for g in (range(G) if cnpjs is None else cnpjs):
        m = np.ones(len(cnpj_cod))
        m[cnpj_cod == g] = 0.0
        e, _ = est.estimar(m)
        res.append((g, e.get(alvo, np.nan)))
    return res


def resumir(ponto, chaves, draws, extra=None):
    from scipy import stats
    linhas = []
    for j, k in enumerate(chaves):
        d = draws[:, j]
        d = d[np.isfinite(d)]
        b = ponto[k]
        se = float(np.std(d, ddof=1)) if d.size > 10 else np.nan
        lo, hi = (np.quantile(d, [0.025, 0.975]) if d.size > 10 else (np.nan, np.nan))
        p = float(2 * stats.norm.sf(abs(b / se))) if se and np.isfinite(se) and se > 0 else np.nan
        linhas.append({"grupo": k[0], "l": k[1], "beta_lp": b, "ep": se, "ic95_inf": b - 1.96 * se, "ic95_sup": b + 1.96 * se,
                       "ic95_perc_inf": lo, "ic95_perc_sup": hi, "p": p, "pct_exato": float(comum.pct_exato(b)),
                       "pct_ic_inf": float(comum.pct_exato(b - 1.96 * se)), "pct_ic_sup": float(comum.pct_exato(b + 1.96 * se)),
                       "mde_80": 2.8016 * se if np.isfinite(se) else np.nan, "B_validos": int(d.size), **(extra or {})})
    return linhas


# ------------------------------------------------------------------------------------------- BJS

def bjs(Y, N, info, L, m=None, max_iter=200, tol=1e-9):
    """Imputação BJS no subconjunto absorvente: nunca-tratados em A (d0=0, nunca trocam) + adotantes A→AF que
    não voltam a A. Ajusta Y = α_u + λ_t nas células não tratadas (pesos N·m) e imputa Y(0) nas tratadas.
    Retorna efeitos por tempo de evento e=0..L−1 e média ponderada."""
    U, T = Y.shape
    m = np.ones(U) if m is None else m
    tipo = info["tipo"].to_numpy()
    d0 = info["d0"].to_numpy()
    F = info["F"].to_numpy(dtype=float)
    absorv = info["absorvente"].to_numpy() if "absorvente" in info else np.zeros(U, bool)
    nunca_A = (tipo == NUNCA) & (d0 == 0)
    adot = (tipo == TROCA) & (d0 == 0) & absorv
    obs = ~np.isnan(Y)
    t_idx = np.arange(T)[None, :]
    tratado = adot[:, None] & (t_idx >= F[:, None])
    nao_trat = obs & (nunca_A[:, None] | (adot[:, None] & (t_idx < F[:, None])))
    W = np.where(nao_trat, N * m[:, None], 0.0)
    Yz = np.where(nao_trat, Y, 0.0)
    a = np.zeros(U)
    lam = np.zeros(T)
    for _ in range(max_iter):
        sw_u = W.sum(1)
        a_new = np.where(sw_u > 0, ((Yz - lam[None, :]) * W).sum(1) / np.where(sw_u > 0, sw_u, 1), np.nan)
        sw_t = W.sum(0)
        lam_new = np.where(sw_t > 0, ((Yz - np.nan_to_num(a_new)[:, None]) * W).sum(0) / np.where(sw_t > 0, sw_t, 1), np.nan)
        lam_new = lam_new - np.nanmean(lam_new)
        conv = np.nanmax(np.abs(np.nan_to_num(lam_new) - lam)) < tol
        a, lam = a_new, np.nan_to_num(lam_new)
        if conv:
            break
    ident_t = W.sum(0) > 0
    res = {}
    for e in range(L):
        sel = tratado & obs & (t_idx == F[:, None] + e) & ident_t[None, :] & np.isfinite(a)[:, None]
        if not sel.any():
            continue
        uu, tt = np.nonzero(sel)
        tau = Y[uu, tt] - (a[uu] + lam[tt])
        w = N[uu, tt] * m[uu]
        if w.sum() > 0:
            res[e] = (float(np.sum(w * tau) / w.sum()), float(w.sum()))
    if res:
        ws = np.array([v[1] for v in res.values()])
        res["media"] = (float(np.sum(ws * np.array([v[0] for v in res.values()])) / ws.sum()), float(ws.sum()))
    return res


# ------------------------------------------------------------------------------------------- painéis de desfecho

def painel(df_itens, unidades, tri_ini, tri_fim, col, estimando="item"):
    """Matriz U × T do desfecho médio por UASG × trimestre. estimando='item': média dos itens (N = itens);
    'compra': média das médias por compra (N = compras)."""
    T = tri_fim - tri_ini + 1
    pos = {u: i for i, u in enumerate(unidades)}
    d = df_itens[(df_itens.tri >= tri_ini) & (df_itens.tri <= tri_fim) & df_itens[col].notna()]
    d = d[d.uasg.astype(str).isin(pos)]
    if estimando == "compra":
        d = d.groupby(["uasg", "tri", "chave"], observed=True)[col].mean().reset_index()
    g = d.groupby(["uasg", "tri"], observed=True)[col].agg(["mean", "size"]).reset_index()
    Y = np.full((len(unidades), T), np.nan)
    N = np.zeros((len(unidades), T))
    r = g.uasg.astype(str).map(pos).to_numpy()
    c = (g.tri.astype(int) - tri_ini).to_numpy()
    Y[r, c] = g["mean"].to_numpy()
    N[r, c] = g["size"].to_numpy()
    return Y, N


def cobertura_e_eventos(ctx, df, reg_c, salvar):
    """Etapa 3: cobertura temporal e identificação dos eventos (antes de qualquer estimação)."""
    cfg, reg, saidas = ctx["cfg"], ctx["reg"], ctx["saidas"]
    ev = cfg["eventos"]
    incompletos = {int(x[:4]) * 4 + int(x[-1]) - 1 for x in cfg["amostra"]["trimestres_incompletos"]}
    tri_validos = sorted(set(df.tri.dropna().astype(int)))
    tri_ini = min(t for t in tri_validos if t not in incompletos and t >= 2022 * 4 + 3)
    tri_fim = max(t for t in tri_validos if t not in incompletos and t <= 2026 * 4 + 1)
    with reg.etapa("cobertura temporal por trimestre de abertura"):
        cob = (df.groupby("tri", observed=True)
                 .agg(itens=("chave", "size"), compras=("chave", "nunique"), homologados=("homologado", "sum"),
                      com_preco=("elegivel_preco", "sum"))
                 .reset_index())
        cob["trimestre"] = cob.tri.astype(int).map(nome_trimestre)
        cob["no_painel_eventos"] = cob.tri.between(tri_ini, tri_fim).astype(int)
        cob["situacao"] = np.where(cob.tri.isin(incompletos), "incompleto (censura/fonte)",
                                   np.where(cob.tri.between(tri_ini, tri_fim), "completo", "fora da cobertura do CATMAT"))
        comum.escrever_csv(saidas / "tabelas" / "cobertura_trimestres.csv", cob.to_dict("records"))
    with reg.etapa("regime de modo por UASG × trimestre e eventos"):
        rt = painel_regime(reg_c, tri_ini, tri_fim, 0.5, tuple(ev["trimestre_puro"]))
        info = classificar_unidades(rt, tri_ini, tri_fim, ev["persistencia_trimestres"])
        cnpj = reg_c.groupby("uasg", observed=True).orgao_cnpj.agg(lambda s: s.mode().iat[0]).rename("cnpj")
        info = info.merge(cnpj, left_on="uasg", right_index=True, how="left")
        # absorvente: depois de F, todos os trimestres observados ficam no novo regime
        Dpiv = rt.pivot(index="uasg", columns="tri", values="D")
        def absorvente(r):
            if r.tipo != TROCA:
                return False
            s = Dpiv.loc[r.uasg]
            s = s[s.index >= tri_ini + r.F].dropna()
            return bool((s == 1 - r.d0).all())
        info["absorvente"] = info.apply(absorvente, axis=1)
        # unidades estáveis no período todo (para a referência alternativa)
        tot = reg_c.groupby("uasg", observed=True).af.agg(["size", "mean"]).reset_index()
        e = cfg["referencia"]["unidades_estaveis"]
        tot["estavel"] = (tot["size"] >= e["min_compras"]) & ((tot["mean"] <= e["af_max"]) | (tot["mean"] >= e["af_min"]))
        tot["uasg"] = tot.uasg.astype(str)
        salvar(ctx, "unidades", tot)
        info["uasg"] = info.uasg.astype(str)
        info["F_trimestre"] = info.F.map(lambda f: nome_trimestre(tri_ini + int(f)) if pd.notna(f) else None)
        salvar(ctx, "eventos_info", {"info": info, "tri_ini": tri_ini, "tri_fim": tri_fim, "regime": rt})
        ti = info.tipo.value_counts().to_dict()
        di = info.direcao.value_counts().to_dict()
        res = {"painel": f"{nome_trimestre(tri_ini)}–{nome_trimestre(tri_fim)}", "uasgs": len(info), "tipos": ti,
               "trocas_por_direcao": di, "trocas_puras": int(info.puro.fillna(0).sum()),
               "trocas_absorventes": int(info.absorvente.sum()),
               "cnpjs_com_troca": int(info.loc[info.tipo == TROCA, "cnpj"].nunique()),
               "uasgs_estaveis": int(tot.estavel.sum()),
               "trimestres_excluidos_incompletos": sorted(nome_trimestre(t) for t in incompletos)}
        comum.escrever_json(saidas / "tabelas" / "identificacao_eventos.json", res)
        comum.escrever_csv(saidas / "tabelas" / "eventos_unidades.csv", info.to_dict("records"))
        reg.contar("eventos", res)


def executar(ctx, abrir, salvar):
    """Etapa 8: dCDH (principal), BJS (sensibilidade), diagnósticos de identificação."""
    from .descritivas import base_principal
    cfg, reg, saidas = ctx["cfg"], ctx["reg"], ctx["saidas"]
    ev = cfg["eventos"]
    E = abrir(ctx, "eventos_info")
    info, tri_ini, tri_fim = E["info"], E["tri_ini"], E["tri_fim"]
    df = base_principal(abrir(ctx, "amostra"), abrir(ctx, "indices"))
    unidades = info.uasg.tolist()
    cnpj_cod = pd.factorize(info.cnpj.fillna("?"))[0]
    B, sem = ev["bootstrap"], cfg["semente"]
    linhas, draws_all = [], {}
    specs = []
    for jan, L in ev["janelas_trimestres"].items():
        for estim in ("item", "compra"):
            for pesos in ("celula", "evento"):
                if estim == "compra" and pesos == "evento":
                    continue
                specs.append((jan, L, estim, pesos))
    for jan, L, estim, pesos in specs:
        nome = f"dcdh_{jan}_{estim}_{pesos}"
        with reg.etapa(f"estudo de eventos {nome}"):
            Y, N = painel(df, unidades, tri_ini, tri_fim, "y_A1", estim)
            est = DCDH(Y, N, info, L, L, peso_switcher=pesos)
            ponto, pw, chaves, draws = bootstrap(est, cnpj_cod, B, sem)
            linhas += resumir(ponto, chaves, draws, {"especificacao": nome, "janela": jan, "estimando": estim,
                                                    "pesos": pesos, "referencia": "A1", "classificacao": "exploratório"})
            draws_all[nome] = (chaves, draws, ponto)
            if (jan, estim, pesos) == (ev["janela_principal"], ev["estimando_principal"], "celula"):
                pop = est.populacao()
                pop["uasg"] = pop.linha.map(lambda i: unidades[i])
                pop["cnpj"] = pop.linha.map(lambda i: info.cnpj.iat[i])
                comum.escrever_csv(saidas / "tabelas" / "populacao_eventos_pesos.csv", pop.to_dict("records"))
                jk = jackknife_cnpj(est, cnpj_cod, cnpjs=sorted(set(cnpj_cod[info.tipo.to_numpy() == TROCA])))
                vals = np.array([v for _, v in jk if np.isfinite(v)])
                reg.contar("jackknife_cnpj_principal", {"n": len(vals), "min": float(vals.min()), "max": float(vals.max()),
                                                        "ponto": ponto.get(("agregado", "media"))})
                salvar(ctx, "dcdh_principal", {"est": est, "Y": Y, "N": N, "ponto": ponto, "chaves": chaves, "draws": draws,
                                               "jackknife": jk, "cnpj_cod": cnpj_cod})
    # BJS no subconjunto absorvente (janela principal, item)
    L = ev["janelas_trimestres"][ev["janela_principal"]]
    with reg.etapa("BJS (subconjunto absorvente)"):
        Y, N = painel(df, unidades, tri_ini, tri_fim, "y_A1", "item")
        p0 = bjs(Y, N, info, L)
        rng = np.random.default_rng(sem)
        G = cnpj_cod.max() + 1
        dr = []
        for _ in range(B):
            cont = np.bincount(rng.integers(0, G, G), minlength=G).astype(float)
            r = bjs(Y, N, info, L, cont[cnpj_cod])
            dr.append([r.get(k, (np.nan,))[0] for k in list(range(L)) + ["media"]])
        dr = np.array(dr)
        for j, k in enumerate(list(range(L)) + ["media"]):
            if k not in p0:
                continue
            d = dr[:, j][np.isfinite(dr[:, j])]
            se = float(np.std(d, ddof=1)) if d.size > 10 else np.nan
            b = p0[k][0]
            from scipy import stats
            linhas.append({"grupo": "adocao_absorvente", "l": k if k == "media" else k + 1, "beta_lp": b, "ep": se,
                           "ic95_inf": b - 1.96 * se, "ic95_sup": b + 1.96 * se, "p": float(2 * stats.norm.sf(abs(b / se))) if se else np.nan,
                           "pct_exato": float(comum.pct_exato(b)), "especificacao": f"bjs_{ev['janela_principal']}_item",
                           "janela": ev["janela_principal"], "estimando": "item", "pesos": "celula", "referencia": "A1",
                           "classificacao": "exploratório (sensibilidade)", "B_validos": int(d.size)})
    comum.escrever_csv(saidas / "estudo_eventos.csv", linhas)
    salvar(ctx, "eventos_draws", draws_all)
    diagnosticos(ctx, df, info, unidades, tri_ini, tri_fim, cnpj_cod, abrir)


def diagnosticos(ctx, df, info, unidades, tri_ini, tri_fim, cnpj_cod, abrir):
    """§10: contagens, órgãos efetivos, pesos, sobreposição de produtos, pré-períodos e balanço de covariáveis
    (mesmo estimador aplicado às características: quantidade, SRP, sigilo, preço estimado relativo, mês do ano)."""
    cfg, saidas, reg = ctx["cfg"], ctx["saidas"], ctx["reg"]
    ev = cfg["eventos"]
    L = ev["janelas_trimestres"][ev["janela_principal"]]
    P = abrir(ctx, "dcdh_principal")
    est = P["est"]
    pop = est.populacao()
    efe = pop[pop.l > 0]
    w_cnpj = efe.assign(cnpj=efe.linha.map(lambda i: cnpj_cod[i])).groupby("cnpj").peso.sum()
    sh = w_cnpj / w_cnpj.sum()
    w_u = efe.groupby("linha").peso.sum().sort_values(ascending=False)
    trocas = info[info.tipo == TROCA]
    diag = {"eventos_validos": int(len(trocas)), "por_direcao": trocas.direcao.value_counts().to_dict(),
            "eventos_usados_l1": int(pop[pop.l == 1].linha.nunique()), "eventos_usados_algum_l": int(efe.linha.nunique()),
            "uasgs_trocaram": int(len(trocas)), "cnpjs_trocaram": int(trocas.cnpj.nunique()),
            "cnpjs_usados": int(len(w_cnpj)), "n_efetivo_cnpjs": float(1 / np.sum(sh ** 2)) if len(sh) else None,
            "share_top5_uasgs_peso": float(w_u.head(5).sum() / w_u.sum()) if len(w_u) else None,
            "share_top1_cnpj_peso": float(sh.max()) if len(sh) else None,
            "eventos_com_placebo1": int(pop[pop.l == -1].linha.nunique()),
            "eventos_com_placebo2": int(pop[pop.l == -2].linha.nunique()),
            "calendario_F": trocas.F_trimestre.value_counts().sort_index().to_dict(),
            "trimestre_do_ano_F": trocas.F.map(lambda f: (tri_ini + int(f)) % 4 + 1).value_counts().sort_index().to_dict()}
    # sobreposição de produtos: itens pós (F..F+L−1) cujo produto a UASG comprou no pré (F−L..F−1)
    sob = []
    d_it = df[["uasg", "tri", "produto"]].copy()
    d_it["uasg"] = d_it.uasg.astype(str)
    for _, r in trocas.iterrows():
        Fq = tri_ini + int(r.F)
        s = d_it[d_it.uasg == r.uasg]
        pre = set(s.loc[s.tri.between(Fq - L, Fq - 1), "produto"])
        pos = s.loc[s.tri.between(Fq, Fq + L - 1), "produto"]
        if len(pos):
            sob.append(pos.isin(pre).mean())
    diag["sobreposicao_produtos_media"] = float(np.mean(sob)) if sob else None
    # balanço: mesmo dCDH nas covariáveis (mudança associada à troca, relativa aos controles)
    am = abrir(ctx, "amostra")
    base = am[am.populacao_desfecho & am.modo_disputa.isin(cfg["amostra"]["modos"]) & (am.criterio_julgamento == cfg["amostra"]["criterio"])].copy()
    base["srp_f"] = base.srp.astype(float)
    base["sigilo_f"] = base.orcamento_sigiloso.astype(float)
    base["homolog_f"] = (base.situacao_item == "Homologado").astype(float)
    bal = []
    for col in ("logq", "srp_f", "sigilo_f", "homolog_f"):
        Y, N = painel(base, info.uasg.tolist(), tri_ini, tri_fim, col, "item")
        e = DCDH(Y, N, info, L, L)
        pt, pw, ch, dr = bootstrap(e, cnpj_cod, max(199, cfg["eventos"]["bootstrap"] // 5), cfg["semente"])
        for linha in resumir(pt, ch, dr, {"covariavel": col}):
            if linha["l"] in ("media", -1):
                bal.append(linha)
    comum.escrever_csv(saidas / "tabelas" / "balanco_covariaveis_eventos.csv", bal)
    comum.escrever_json(saidas / "tabelas" / "diagnosticos_identificacao.json", diag)
    reg.contar("diagnosticos_identificacao", diag)
