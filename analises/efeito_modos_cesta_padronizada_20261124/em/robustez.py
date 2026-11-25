"""Etapa 10: referências alternativas (§6) e robustez (§13). Tudo EXPLORATÓRIO (não há produtos aprovados).

Referências: (a) amostra comum (máscara A1 e as 14 referências definidas) — muda só a fórmula do índice;
(b) amostra própria de cada referência — muda fórmula e amostra. Diferenças pareadas β_k − β_A1:
no painel FE, regressão de (y_k − y_A1) nos mesmos regressores, efeitos fixos e agrupamento (mesma amostra);
no estudo de eventos, diferença draw a draw com a mesma reamostragem de CNPJs (mesma semente).
"""
import numpy as np
import pandas as pd

from . import comum
from .descritivas import base_principal
from .eventos import DCDH, TROCA, bootstrap, painel, resumir
from .inferencia import codificar, demean, holm, remover_singletons, vcov_cluster
from .painel import ESPECS, estimar, linha, preparar
from .referencias import VARIANTES


def _es(df_it, info, tri_ini, tri_fim, cnpj_cod, col, L, B, sem, estim="item", pesos="celula", filtro_sw=None):
    Y, N = painel(df_it, info.uasg.tolist(), tri_ini, tri_fim, col, estim)
    est = DCDH(Y, N, info, L, L, peso_switcher=pesos)
    return bootstrap(est, cnpj_cod, B, sem)


def _linhas_es(nome, res, extra):
    ponto, pw, chaves, draws = res
    out = []
    for l in resumir(ponto, chaves, draws, {"especificacao": nome, **extra}):
        if l["l"] == "media" and l["grupo"] in ("agregado", "adocao", "abandono", "simetria"):
            out.append(l)
    return out


def referencias_fe(d, cod, cfg, saidas, reg):
    """FE E3 para as 14 referências na amostra comum (um único demeaning) e nas amostras próprias."""
    ycols = [f"y_{k}" for k in VARIANTES]
    comuns = d[ycols].notna().all(1).to_numpy()
    e = ESPECS["E3"]
    fes = [cod[f][comuns] for f in e["fe"]]
    keep = remover_singletons(fes)
    sub = d[comuns][keep]
    fes = [codificar(f[keep]) for f in fes]
    X = np.column_stack([sub.af.to_numpy(float), sub.logq.to_numpy(float)])
    M = demean(np.column_stack([sub[ycols].to_numpy(float), X]), fes, None, cfg["efeitos_fixos"]["tolerancia"],
               cfg["efeitos_fixos"]["max_iter"])
    Yd, Xd = M[:, :len(ycols)], M[:, len(ycols):]
    cl = codificar(sub.orgao_cnpj.to_numpy())
    inv = np.linalg.pinv(Xd.T @ Xd)
    linhas = []
    b1 = None
    from scipy import stats
    for j, k in enumerate(VARIANTES):
        b = inv @ (Xd.T @ Yd[:, j])
        res = Yd[:, j] - Xd @ b
        V, G = vcov_cluster(Xd, res, cl)
        se = float(np.sqrt(V[0, 0]))
        if k == "A1":
            b1 = Yd[:, j]
        dy = Yd[:, j] - b1
        bd = inv @ (Xd.T @ dy)
        Vd, _ = vcov_cluster(Xd, dy - Xd @ bd, cl)
        sed = float(np.sqrt(max(Vd[0, 0], 0)))
        tc = stats.t.ppf(0.975, G - 1)
        linhas.append({"modelo": "FE E3", "amostra": "comum (14 referências)", "referencia": k, "beta_lp": float(b[0]),
                       "ep_cnpj": se, "ic95_inf": float(b[0] - tc * se), "ic95_sup": float(b[0] + tc * se),
                       "p": float(2 * stats.t.sf(abs(b[0] / se), G - 1)), "pct_exato": float(comum.pct_exato(b[0])),
                       "dif_vs_A1": float(bd[0]), "ep_dif": sed,
                       "dif_ic95_inf": float(bd[0] - tc * sed) if sed else np.nan,
                       "dif_ic95_sup": float(bd[0] + tc * sed) if sed else np.nan,
                       "p_dif": float(2 * stats.t.sf(abs(bd[0] / sed), G - 1)) if sed > 0 else np.nan,
                       "n_itens": len(sub), "n_orgaos": int(G), "mudanca": "fórmula do índice"})
    pd_ = [l["p_dif"] for l in linhas if l["referencia"] != "A1"]
    adj = holm(pd_)
    i = 0
    for l in linhas:
        if l["referencia"] != "A1":
            l["p_dif_holm"] = float(adj[i])
            i += 1
    for k in VARIANTES:
        with reg.etapa(f"FE E3 amostra própria {k}"):
            r = estimar(d, cod, "E3", y=f"y_{k}", mascara=d[f"propria_{k}"].to_numpy())
            l = linha("E3", r)
            linhas.append({"modelo": "FE E3", "amostra": "própria", "referencia": k, "beta_lp": l["beta_lp"], "ep_cnpj": l["ep_cnpj"],
                           "ic95_inf": l["ic95_inf"], "ic95_sup": l["ic95_sup"], "p": l["p"], "pct_exato": l["pct_exato"],
                           "n_itens": l["n_itens"], "n_orgaos": l["n_orgaos"], "mudanca": "fórmula e amostra"})
    return linhas


def executar(ctx, abrir, salvar):
    cfg, reg, saidas = ctx["cfg"], ctx["reg"], ctx["saidas"]
    ev = cfg["eventos"]
    B, sem = ev["bootstrap"], cfg["semente"]
    am = abrir(ctx, "amostra")
    idx = abrir(ctx, "indices")
    E = abrir(ctx, "eventos_info")
    info, tri_ini, tri_fim = E["info"], E["tri_ini"], E["tri_fim"]
    cnpj_cod = pd.factorize(info.cnpj.fillna("?"))[0]
    L = ev["janelas_trimestres"][ev["janela_principal"]]
    linhas_ref, linhas_rob = [], []
    # ---------------------------------------------------------------- referências alternativas
    base_A1 = base_principal(am, idx)
    with reg.etapa("referências alternativas: FE (amostra comum e própria)"):
        d, cod = preparar(base_A1)
        linhas_ref += referencias_fe(d, cod, cfg, saidas, reg)
    with reg.etapa("referências alternativas: estudo de eventos (amostra comum e própria)"):
        ycols = [f"y_{k}" for k in VARIANTES]
        comum_mask = base_A1[ycols].notna().all(1)
        res_A1 = None
        for k in VARIANTES:
            for amostra in ("comum", "própria"):
                if amostra == "comum":
                    dd = base_A1[comum_mask]
                else:
                    dd = base_principal(am, idx, mascara=f"propria_{k}")
                res = _es(dd, info, tri_ini, tri_fim, cnpj_cod, f"y_{k}", L, B, sem)
                ponto, pw, chaves, draws = res
                if k == "A1" and amostra == "comum":
                    res_A1 = res
                for l in _linhas_es(f"dcdh_{ev['janela_principal']}_item_{k}_{amostra}", res,
                                    {"referencia": k, "amostra": amostra, "modelo": "dCDH",
                                     "mudanca": "fórmula do índice" if amostra == "comum" else "fórmula e amostra"}):
                    if amostra == "comum" and res_A1 is not None:
                        j = chaves.index((l["grupo"], "media"))
                        j1 = res_A1[2].index((l["grupo"], "media"))
                        dif = draws[:, j] - res_A1[3][:, j1]
                        dif = dif[np.isfinite(dif)]
                        l["dif_vs_A1"] = float(ponto[(l["grupo"], "media")] - res_A1[0][(l["grupo"], "media")])
                        l["ep_dif"] = float(np.std(dif, ddof=1)) if dif.size > 10 else np.nan
                        l["dif_ic95_inf"] = l["dif_vs_A1"] - 1.96 * l["ep_dif"]
                        l["dif_ic95_sup"] = l["dif_vs_A1"] + 1.96 * l["ep_dif"]
                    linhas_ref.append(l)
    comum.escrever_csv(saidas / "referencias_alternativas.csv", linhas_ref)
    # ---------------------------------------------------------------- robustez
    linhas_rob.append({"verificacao": "R01 produtos tecnicamente validados", "situacao": "não estimável",
                       "motivo": "cesta_validada.csv vazia: nenhum produto aprovado", "classificacao": "—"})

    def rob(nome, dd, col="y_A1", estim="item", pesos="celula", Ljan=L, fe=True, desc=""):
        out = []
        with reg.etapa(f"robustez {nome}"):
            res = _es(dd, info, tri_ini, tri_fim, cnpj_cod, col, Ljan, B, sem, estim, pesos)
            for l in _linhas_es(nome, res, {"modelo": "dCDH", "descricao": desc}):
                l["verificacao"] = nome
                out.append(l)
            if fe:
                d2, cod2 = preparar(dd)
                r = estimar(d2, cod2, "E3", y=col)
                l = linha("E3", r)
                out.append({"verificacao": nome, "modelo": "FE E3", "grupo": "associacao", "beta_lp": l["beta_lp"],
                            "ep": l["ep_cnpj"], "ic95_inf": l["ic95_inf"], "ic95_sup": l["ic95_sup"], "p": l["p"],
                            "pct_exato": l["pct_exato"], "n_itens": l["n_itens"], "n_orgaos": l["n_orgaos"], "descricao": desc})
        return out

    b = base_A1
    linhas_rob += rob("R02 classe A ∩ cenário rigoroso", b[(b.classe_tecnica == "A") & (b.rigoroso == 1)],
                      desc="sensibilidade exploratória (não é validação)")
    linhas_rob += rob("R03 cesta candidata completa (base)", b, desc="amostra exploratória de referência")
    linhas_rob += rob("R04 referência mediana (A3), amostra própria", base_principal(am, idx, "propria_A3"), col="y_A3")
    linhas_rob += rob("R05 referência aritmética (A2), amostra própria", base_principal(am, idx, "propria_A2"), col="y_A2")
    linhas_rob += rob("R06 peso igual por compra (estimando por compra)", b, estim="compra", fe=False)
    linhas_rob += rob("R07 peso igual por evento", b, pesos="evento", fe=False)
    linhas_rob += rob("R09 sem produtos com inconsistências técnicas", b[b.inconsistencia_tecnica == 0])
    # mesmo produto antes e depois da troca (só para as UASGs que trocam; controles inalterados)
    trocas = info[info.tipo == TROCA].set_index("uasg")
    keep = np.ones(len(b), dtype=bool)
    bb = b.reset_index(drop=True)
    for u, s in bb[bb.uasg.isin(trocas.index)].groupby("uasg"):
        Fq = tri_ini + int(trocas.loc[u, "F"])
        pre = set(s.loc[s.tri < Fq, "produto"])
        pos = set(s.loc[s.tri >= Fq, "produto"])
        ambos = pre & pos
        keep[s.index.to_numpy()] = s.produto.isin(ambos).to_numpy()
    linhas_rob += rob("R10 mesmo produto antes e depois da troca", bb[keep], fe=False,
                      desc="nas UASGs que trocam, só produtos comprados antes e depois de F")
    linhas_rob += rob("R11 referência só com UASGs estáveis", base_principal(am, idx, "propria_EST_A1"), col="y_EST_A1",
                      desc="comparadoras com AF < 5% ou > 95% no período, ≥ 20 compras")
    lim_sd = float(np.nanmedian(b.sd_outros))
    linhas_rob += rob("R12 células de menor dispersão", b[b.sd_outros <= lim_sd],
                      desc=f"desvio-padrão dos log-preços das outras UASGs ≤ mediana ({lim_sd:.3f})")
    linhas_rob += rob("R13 janela de 12 meses", b, Ljan=ev["janelas_trimestres"]["12m"], fe=False)
    linhas_rob += rob("R14 produtos recorrentes em todas as janelas", b[b.recorrente == 1])
    linhas_rob += rob("R15 produtos não recorrentes em todas as janelas", b[b.recorrente == 0])
    # exclusão de um órgão por vez (jackknife do estudo de eventos principal e LOO exato no FE, já calculados)
    P = abrir(ctx, "dcdh_principal")
    jk = np.array([v for _, v in P["jackknife"] if np.isfinite(v)])
    linhas_rob.append({"verificacao": "R08 exclusão de um órgão por vez (dCDH)", "modelo": "dCDH", "grupo": "agregado",
                       "beta_lp": P["ponto"].get(("agregado", "media")), "jackknife_min": float(jk.min()) if jk.size else None,
                       "jackknife_max": float(jk.max()) if jk.size else None, "n_orgaos_excluidos": int(jk.size)})
    comum.escrever_csv(saidas / "robustez.csv", linhas_rob)
