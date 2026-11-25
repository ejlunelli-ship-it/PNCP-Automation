"""Composição dos produtos e efeito do AF no preço homologado (protocolo.md). EXPLORATÓRIO.

Testes: (1) medicamentos × demais; (2) interação AF × medicamentos; (3) índice de composição fixa; (4) decomposição preço ×
composição; (5) validade e robustez. Comando único (da pasta PNCP-Automation):
    python analises/composicao_precos_medicamentos_20261123/executar.py
Pré-requisito: base de 23/11 em dados/testes_desenho_causal/ (../testes_desenho_causal_20261123/preparar.py).
Não lê o pncp.db; não altera bases nem resultados anteriores; não usa os eventos reservados (posteriores a 2025-10).
"""
import hashlib, json, os, sys, time, traceback
from pathlib import Path

sys.dont_write_bytecode = True
AQUI = Path(__file__).resolve().parent
ROB = AQUI.parent / "robustez_dispersao_20261123"
sys.path.insert(0, str(AQUI))
sys.path.insert(0, str(ROB))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import motor_robustez as MR  # noqa: E402
import comum as C  # noqa: E402

LIMITE = int(os.environ.get("COMPOSICAO_LIMITE_EVENTOS", "0"))        # só para teste rápido do código
SAIDA = (C.RAIZ / "dados" / "composicao_precos_medicamentos" / "teste_rapido") if LIMITE else AQUI
TAB = SAIDA / "tabelas"
TAB.mkdir(parents=True, exist_ok=True)
B_BOOT = 9999
FIM_EVENTO = (2025 * 12 + 9) - C.M0                                    # 2025-10
REF = {"original": -1.91, "filtrado": -3.76}
T0 = time.time()
REG = {"inicio": time.strftime("%Y-%m-%d %H:%M:%S"),
       "protocolo_sha256": hashlib.sha256((AQUI / "protocolo.md").read_bytes()).hexdigest(),
       "parametros": {"W": MR.W0, "cmin_base": MR.CMIN, "limite_dispersao": MR.LIM, "B": B_BOOT,
                      "var_a": MR.VAR_A, "var_b": MR.VAR_B, "medicamentos": "classe CATMAT 6505"},
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


def influencia(df, pesos):
    w = MR._pesos(df, pesos)
    ok = np.isfinite(w) & df.did.notna().to_numpy()
    d, w = df[ok], w[ok]
    y = (d.sinal * d.did).to_numpy(float)
    tot = float((w * y).sum() / w.sum())
    sh = pd.Series(w, index=d.index).groupby(d.cnpj.astype(str)).sum() / w.sum()
    ests = {c: float((w[(d.cnpj.astype(str) != c).to_numpy()] * y[(d.cnpj.astype(str) != c).to_numpy()]).sum()
                     / w[(d.cnpj.astype(str) != c).to_numpy()].sum()) for c in sh.index}
    e = pd.Series(ests)
    dl = (e - tot).abs()
    return {"loo_min_lp": 100 * float(e.min()), "loo_max_lp": 100 * float(e.max()), "loo_maior_delta_lp": 100 * float(dl.max()),
            "orgao_mais_influente": str(dl.idxmax()), "peso_maior_orgao": float(sh.max())}


def relato(teste, modelo, df, pesos="precisao", ic=True, nome_pesos=None, **extra):
    """Estimativa padrão (MR.estimar) + influência + comparação com −1,91 e −3,76 lp."""
    d = {"teste": teste, "modelo": modelo}
    if df is None or len(df) < 5:
        d.update({"n_eventos": 0 if df is None else int(len(df)), "observacao": "sem eventos suficientes"}, **extra)
        TODAS.append(d)
        return d
    est = MR.estimar(df, pesos=pesos, B=B_BOOT, ic=ic)
    for c in ["coef_lp", "ep_lp", "p_wcr", "p_t", "n_eventos", "n_A->AF", "n_AF->A", "itens_tratadas", "compras_tratadas",
              "uasgs_tratadas", "uasgs_controle", "orgaos", "orgaos_efetivos", "maior_orgao_peso"]:
        d[c] = est.get(c)
    d["pesos"] = nome_pesos or (pesos if isinstance(pesos, str) else "congelados")
    d["ic95_inf"], d["ic95_sup"] = (est.get("ic95_wcr") if ic else est.get("ic95_t")) or [np.nan, np.nan]
    d["ic95_tipo"] = "WCR" if ic else "t(G-1)"
    for t in ("A->AF", "AF->A"):
        if t in est:
            d[f"{t}_coef"], d[f"{t}_p"] = est[t]["coef_lp"], est[t]["p_wcr"]
    d["soma_sentidos"], d["soma_sentidos_p"] = est.get("simetria_soma_lp"), est.get("simetria_p_wcr")
    d["dif_vs_-1,91"] = d["coef_lp"] - REF["original"]
    d["dif_vs_-3,76"] = d["coef_lp"] - REF["filtrado"]
    d.update(influencia(df, pesos))
    d.update(extra)
    TODAS.append(d)
    return d


def dif_relato(teste, modelo, df1, w1, df2, w2):
    dd = MR.diferenca(df1, w1, df2, w2, B=B_BOOT)
    d = {"teste": teste, "modelo": modelo, "coef_lp": dd["dif_lp"], "ep_lp": dd["ep_lp"], "ic95_inf": dd["ic95_wcu"][0],
         "ic95_sup": dd["ic95_wcu"][1], "ic95_tipo": "WCU (diferença pareada)", "p_wcr": dd["p_wcu"], "p_t": dd["p_t"],
         "n_eventos": dd["eventos"], "orgaos": dd["orgaos"], "coef_1": dd["coef1_lp"], "coef_2": dd["coef2_lp"]}
    TODAS.append(d)
    return d


def salvar(nome, linhas):
    pd.DataFrame(linhas).to_csv(TAB / f"{nome}.csv", index=False, encoding="utf-8", lineterminator="\n")


def eventos_csv(nome, df):
    df.drop(columns=[c for c in ("controles", "dev", "h_ctrl") if c in df.columns]).to_csv(
        TAB / f"eventos_{nome}.csv", index=False, encoding="utf-8", lineterminator="\n")


# --------------------------------------------------------------------------------------------- base
def base():
    B = MR.Base(log=log)
    S["B"] = B
    E6 = B.eventos(6)
    if LIMITE:
        E6 = E6.head(LIMITE)
    assert (E6.m <= FIM_EVENTO).all(), "evento reservado para validação entrou na amostra"
    REG["conferencias"]["eventos_reservados"] = {"ultimo_mes_evento_usado": C.mes_str(C.M0 + int(E6.m.max())),
                                                 "reservados_posteriores_a_2025_10": int((B.ev.m > FIM_EVENTO).sum()),
                                                 "algum_reservado_usado": False}
    S["E6"] = E6
    S["mask_f"] = (B.it.sd_G <= MR.LIM).to_numpy()
    S["med"] = (B.it.med6505.to_numpy() == 1)
    S["M0"] = B.rodar(E6, "e_ok")
    S["M1"] = B.rodar(E6, "e_G", mascara=S["mask_f"])
    for nome, df, ref in (("M0", S["M0"], REF["original"]), ("M1", S["M1"], REF["filtrado"])):
        r = MR.estimar(df, B=B_BOOT)
        REG["conferencias"][f"reproduz_{nome}"] = {"coef": r["coef_lp"], "ic": r["ic95_wcr"], "eventos": r["n_eventos"],
                                                   "ok": bool(abs(r["coef_lp"] - ref) < 0.01) if not LIMITE else None}
    it = B.it
    eg = np.isfinite(it.e_G.to_numpy()); ea = np.isfinite(it.e_ok.to_numpy())
    REG["conferencias"]["parcela_medicamentos_itens_com_indice"] = {"A": float(S["med"][ea].mean()),
                                                                    "G_filtrado": float(S["med"][eg & S["mask_f"]].mean())}
    S["especs"] = [("A", "referência original, todas as células", S["M0"], "e_ok", None),
                   ("G", "referência G, dispersão ≤ 0,80", S["M1"], "e_G", S["mask_f"])]
    log("base pronta", len(S["M0"]), len(S["M1"]))


def combina(a, b):
    if a is None:
        return b
    if b is None:
        return a
    return a & b


# --------------------------------------------------------------------------------------------- teste 1 e 2
def teste1():
    B, E6 = S["B"], S["E6"]
    linhas, perfil = [], []
    S["t1"] = {}
    for sigla, nome, base_m, y, mask in S["especs"]:
        for grupo, gm in (("todos", None), ("medicamentos", S["med"]), ("demais materiais", ~S["med"])):
            lst = []
            for _, r in base_m.iterrows():
                o = B.evento(r.k, E6.loc[r.k], y, mascara=combina(mask, gm), controles=np.asarray(r.controles),
                             cmin=1, cmin_controle=1, bins=True)
                if o is not None:
                    lst.append(o)
            df = pd.DataFrame(lst)
            S["t1"][(sigla, grupo)] = df
            eventos_csv(f"t1_{sigla}_{grupo.split()[0]}", df)
            for pn in ("precisao", "iguais"):
                linhas.append(relato("1", f"{sigla} ({nome}) | {grupo} | controles do modelo base", df, pn,
                                     nome_pesos="precisão (h do grupo)" if pn == "precisao" else "iguais"))
            for nm, cols in (("pré (trim. −2)", ["b-2"]), ("pós (trim. 0 e +1)", ["b0", "b1"])):
                if len(df) >= 5:
                    j = MR.bins_conjunto(df, cols)
                    for c, v in j["bins"].items():
                        perfil.append({"especificacao": sigla, "grupo": grupo, "trimestre": int(c[1:]), "coef_lp": v["coef_lp"],
                                       "ep_lp": v["ep_lp"], "ic95_inf": v["ic95_t"][0], "ic95_sup": v["ic95_t"][1], "p_t": v["p_t"],
                                       "n_eventos": v["n_eventos"]})
                    perfil.append({"especificacao": sigla, "grupo": grupo, "trimestre": f"conjunto {nm}", "F": j["F"], "p_t": j["p"]})
            if grupo != "todos":
                dfr = B.rodar(E6, y, mascara=combina(mask, gm), bins=False)
                linhas.append(relato("1", f"{sigla} ({nome}) | {grupo} | controles selecionados de novo (sensibilidade)", dfr,
                                     "precisao", nome_pesos="precisão (h do grupo)"))
        # conferência: "todos" com controles fixos reproduz o modelo base
        a = S["t1"][(sigla, "todos")].set_index("k").did
        b = base_m.set_index("k").did.reindex(a.index)
        REG["conferencias"][f"t1_todos_reproduz_base_{sigla}"] = float(np.nanmax(np.abs(a - b)))
    salvar("t1_grupos", linhas)
    salvar("t1_perfil", perfil)
    R["teste1"] = {"modelos": linhas, "perfil": perfil}


def teste2():
    linhas = []
    for sigla, nome, base_m, y, mask in S["especs"]:
        med, oth = S["t1"][(sigla, "medicamentos")], S["t1"][(sigla, "demais materiais")]
        j = med.set_index("k")[["u", "m", "tipo", "sinal", "cnpj", "did", "h", "itens_tratada", "compras_tratada", "controles"]].join(
            oth.set_index("k")[["did", "h", "itens_tratada", "compras_tratada"]], rsuffix="_dem", how="inner")
        j = j.reset_index()
        d = j.assign(did=j.did - j.did_dem, itens_tratada=j.itens_tratada + j.itens_tratada_dem,
                     compras_tratada=j.compras_tratada + j.compras_tratada_dem)
        w = dict(zip(d.k, 1 / np.maximum(2 * MR.VAR_A + MR.VAR_B * (d.h + d.h_dem), 1e-6)))
        r1 = relato("2", f"{sigla} ({nome}) | interação: medicamentos − demais", d, w, nome_pesos="precisão da diferença")
        r2 = relato("2", f"{sigla} ({nome}) | interação: medicamentos − demais", d, "iguais", nome_pesos="iguais")
        ndir = d.tipo.value_counts().to_dict()
        ident = bool(len(d) >= 30 and min(ndir.get("A->AF", 0), ndir.get("AF->A", 0)) >= 10 and (r1.get("orgaos_efetivos") or 0) >= 10)
        for r in (r1, r2):
            r["identificavel_criterio_protocolo"] = ident
            r["efeito_minimo_detectavel_lp"] = 2.8 * r["ep_lp"] if r.get("ep_lp") is not None else None
        linhas += [r1, r2]
        REG["exclusoes"][f"t2_{sigla}"] = {"eventos_com_os_dois_grupos": int(len(d)), "por_sentido": ndir,
                                           "eventos_so_medicamentos": int((~med.k.isin(oth.k)).sum()),
                                           "eventos_so_demais": int((~oth.k.isin(med.k)).sum()), "identificavel": ident}
    salvar("t2_interacao", linhas)
    R["teste2"] = linhas


# --------------------------------------------------------------------------------------------- teste 3 e 4
def decompor(k, ev, ctrl, y, mask, pseudo=False):
    """Por evento: DiD do índice original (médias por compra), da média por item (ΔĒ) e dos componentes A, B1, B2;
    índice fixo com produtos que somem imputados (A_imp); cobertura S_C,pré e S_C,pós. Mesmos controles para tudo."""
    B = S["B"]; it = B.it
    u, m = int(ev.u), int(ev.m)
    rows = B.linhas(k, u, m, ev.tipo, 6, unidades=np.r_[u, ctrl])
    yv = it[y].to_numpy()[rows]
    ok = np.isfinite(yv)
    if mask is not None:
        ok &= mask[rows]
    rows, yv = rows[ok], yv[ok]
    mm = B.m_arr[rows]
    corte = m
    if pseudo:                                                         # pseudojanela pré: [m−6, m−3) × [m−3, m)
        sel = mm < m
        rows, yv, mm = rows[sel], yv[sel], mm[sel]
        corte = m - 3
    if len(rows) == 0:
        return None
    df = pd.DataFrame({"u": B.u_arr[rows], "pos": mm >= corte, "prod": it["prod"].to_numpy()[rows],
                       "cod": it.cod.to_numpy()[rows], "e": yv})
    cm = df.groupby(["u", "pos", "cod"]).e.mean().groupby(["u", "pos"]).agg(["mean", "size"]).unstack("pos")
    if ("mean", False) not in cm.columns or ("mean", True) not in cm.columns:
        return None                                                     # nenhuma unidade com os dois períodos
    pp = df.groupby(["u", "pos", "prod"]).e.agg(["mean", "size"]).reset_index()
    pre = pp[~pp.pos].set_index(["u", "prod"])[["mean", "size"]]
    pos = pp[pp.pos].set_index(["u", "prod"])[["mean", "size"]]
    J = pre.join(pos, how="outer", lsuffix="_pre", rsuffix="_pos").reset_index()
    J[["size_pre", "size_pos"]] = J[["size_pre", "size_pos"]].fillna(0)
    J["N_pre"] = J.groupby("u").size_pre.transform("sum")
    J["N_pos"] = J.groupby("u").size_pos.transform("sum")
    J = J[(J.N_pre > 0) & (J.N_pos > 0)].copy()
    J["s_pre"], J["s_pos"] = J.size_pre / J.N_pre, J.size_pos / J.N_pos
    J["x_pre"], J["x_pos"] = J.s_pre * J.mean_pre.fillna(0), J.s_pos * J.mean_pos.fillna(0)
    J["C"] = (J.size_pre > 0) & (J.size_pos > 0)
    g = J.groupby("u")
    Eb_pre, Eb_pos = g.x_pre.sum(), g.x_pos.sum()
    JC = J[J.C]
    gc = JC.groupby("u")
    SC_pre, SC_pos = gc.s_pre.sum(), gc.s_pos.sum()
    EC_pre, EC_pos = gc.x_pre.sum() / SC_pre, gc.x_pos.sum() / SC_pos
    A = (JC.s_pre * (JC.mean_pos - JC.mean_pre)).groupby(JC.u).sum() / SC_pre
    ECpos_wpre = (JC.s_pre * JC.mean_pos).groupby(JC.u).sum() / SC_pre
    Q = pd.DataFrame({"total": Eb_pos - Eb_pre}).join(pd.DataFrame({
        "A": A, "B1": EC_pos - ECpos_wpre, "SC_pre": SC_pre, "SC_pos": SC_pos, "EC_pre": EC_pre, "EC_pos": EC_pos}), how="inner")
    Q["B2"] = (Eb_pos.reindex(Q.index) - Q.EC_pos) - (Eb_pre.reindex(Q.index) - Q.EC_pre)
    Q["A_imp"] = Q.SC_pre * Q.A
    Q["orig"] = (cm[("mean", True)] - cm[("mean", False)]).reindex(Q.index)
    Q["n_C"] = gc.size().reindex(Q.index)
    Q = Q.dropna(subset=["orig", "A", "B1", "B2", "total"])
    resid = (Q.total - (Q.A + Q.B1 + Q.B2)).abs().max()
    if u not in Q.index:
        return None
    cs = [v for v in ctrl if v in Q.index]
    if len(cs) < 5:
        return None
    t_ = df[df.u == u]
    c_pre = int(t_[~t_.pos].cod.nunique()); c_pos = int(t_[t_.pos].cod.nunique())
    out = {"k": k, "u": u, "m": m, "tipo": ev.tipo, "sinal": 1 if ev.tipo == "A->AF" else -1, "cnpj": B.cnpj[u],
           "h": 1 / max(c_pre, 1) + 1 / max(c_pos, 1), "itens_tratada": int(len(t_)), "compras_tratada": c_pre + c_pos,
           "controles": np.asarray(cs), "n_controles": len(cs), "produtos_continuados_tratada": int(Q.n_C[u]),
           "residuo_identidade": float(resid)}
    for q in ("orig", "total", "A", "B1", "B2", "A_imp", "SC_pre", "SC_pos"):
        out[f"did_{q}"] = float(Q[q][u] - Q[q][cs].mean())
    out.update({"SC_pre_tratada": float(Q.SC_pre[u]), "SC_pos_tratada": float(Q.SC_pos[u]),
                "SC_pre_controles": float(Q.SC_pre[cs].mean()), "SC_pos_controles": float(Q.SC_pos[cs].mean())})
    return out


ROTULOS = {"orig": "índice original (médias por compra)", "total": "ΔĒ, média por item", "A": "A: preço de produtos comparáveis (composição fixa)",
           "A_imp": "índice fixo com produtos que somem imputados (variação zero)", "B1": "B1: recomposição entre produtos continuados",
           "B2": "B2: entrada e saída de produtos", "SC_pre": "cobertura: itens pré em produtos continuados",
           "SC_pos": "cobertura: itens pós em produtos continuados"}


def teste34():
    E6 = S["E6"]
    t3, t4, t5 = [], [], []
    for sigla, nome, base_m, y, mask in S["especs"]:
        w0 = pesos_de(base_m)
        for janela, pseudo in (("principal", False), ("pseudojanela pré (pré-tendência)", True)):
            lst = []
            for _, r in base_m.iterrows():
                o = decompor(r.k, E6.loc[r.k], np.asarray(r.controles), y, mask, pseudo)
                if o is not None:
                    lst.append(o)
            df = pd.DataFrame(lst)
            eventos_csv(f"t34_{sigla}_{'principal' if not pseudo else 'pseudo'}", df)
            REG["exclusoes"][f"t34_{sigla}_{'principal' if not pseudo else 'pseudo'}"] = {
                "eventos_base": int(len(base_m)), "eventos_com_decomposicao": int(len(df))}
            if len(df) == 0:
                continue
            ident = float((df.did_total - (df.did_A + df.did_B1 + df.did_B2)).abs().max())
            REG["conferencias"][f"cobertura_niveis_{sigla}_{'principal' if not pseudo else 'pseudo'}"] = {
                c: float(df[c].mean()) for c in ("SC_pre_tratada", "SC_pos_tratada", "SC_pre_controles", "SC_pos_controles")}
            REG["conferencias"][f"identidade_{sigla}_{'principal' if not pseudo else 'pseudo'}"] = {
                "max_residuo_por_unidade": float(df.residuo_identidade.max()), "max_residuo_did_evento": ident}
            for q in ("orig", "total", "A", "A_imp", "B1", "B2", "SC_pre", "SC_pos"):
                if pseudo and q in ("SC_pre", "SC_pos", "A_imp"):
                    continue
                dq = df.assign(did=df[f"did_{q}"])
                for pn, pv in (("pesos do modelo base", w0), ("iguais", "iguais")):
                    r = relato("3/4" if not pseudo else "5", f"{sigla} ({nome}) | {janela} | {ROTULOS[q]}", dq, pv, nome_pesos=pn,
                               produtos_continuados_mediana=float(df.produtos_continuados_tratada.median()))
                    if pseudo or q in ("SC_pre", "SC_pos"):
                        t5.append(r)
                    else:
                        if q in ("orig", "A", "A_imp"):
                            t3.append(r)
                        if q in ("total", "A", "B1", "B2"):
                            t4.append(r)
            if not pseudo:
                S[f"t34_{sigla}"] = df
                for pn, pv in (("pesos do modelo base", w0), ("iguais", "iguais")):
                    for q1, q2 in (("A", "orig"), ("A_imp", "orig"), ("total", "orig"), ("A", "total")):
                        d1, d2 = df.assign(did=df[f"did_{q1}"]), df.assign(did=df[f"did_{q2}"])
                        wv1 = MR._pesos(d1, pv); wv2 = MR._pesos(d2, pv)
                        t3.append(dif_relato("3", f"{sigla} ({nome}) | diferença: {ROTULOS[q1]} − {ROTULOS[q2]} | {pn}",
                                             d1, wv1, d2, wv2))
    salvar("t3_composicao_fixa", t3)
    salvar("t4_decomposicao", t4)
    salvar("t5_pre_tendencia_e_cobertura", t5)
    R["teste3"], R["teste4"], R["teste5_decomp"] = t3, t4, t5


def teste5_medicamentos():
    """Cobertura: parcela de medicamentos (todos os itens de material) com os eventos e controles de cada modelo base."""
    B, E6 = S["B"], S["E6"]
    linhas = []
    for sigla, nome, base_m, y, mask in S["especs"]:
        lst = []
        for _, r in base_m.iterrows():
            o = B.evento(r.k, E6.loc[r.k], "med6505", controles=np.asarray(r.controles), cmin=1, cmin_controle=1, bins=False)
            if o is not None:
                lst.append(o)
        linhas.append(relato("5", f"{sigla} ({nome}) | cobertura: parcela de medicamentos nas compras", pd.DataFrame(lst),
                             pesos_de(base_m), nome_pesos="pesos do modelo base"))
    salvar("t5_parcela_medicamentos", linhas)
    R["teste5_medicamentos"] = linhas


def main():
    executar("base", base)
    if REG["etapas"]["base"]["status"] == "ok":
        executar("teste1_grupos", teste1)
        if REG["etapas"]["teste1_grupos"]["status"] == "ok":
            executar("teste2_interacao", teste2)
        executar("teste3_4_composicao_fixa_e_decomposicao", teste34)
        executar("teste5_parcela_medicamentos", teste5_medicamentos)
    pd.DataFrame(TODAS).to_csv(TAB / "todas_estimativas.csv", index=False, encoding="utf-8", lineterminator="\n")
    REG["conferencias"]["arquivos"] = {p.name: int(len(pd.read_csv(p))) for p in sorted(TAB.glob("*.csv"))}
    REG["fim"] = time.strftime("%Y-%m-%d %H:%M:%S")
    REG["segundos"] = round(time.time() - T0)
    conv = lambda o: o.tolist() if hasattr(o, "tolist") else (bool(o) if isinstance(o, np.bool_) else float(o))  # noqa: E731
    (SAIDA / "resultados.json").write_text(json.dumps(R, ensure_ascii=False, indent=1, default=conv), encoding="utf-8",
                                           newline="\n")
    try:
        import graficos_composicao
        REG["graficos"] = graficos_composicao.main(SAIDA)
    except Exception as e:
        REG["graficos"] = {"status": "falha", "erro": repr(e), "traceback": traceback.format_exc()}
    (SAIDA / "registro_execucao.json").write_text(json.dumps(REG, ensure_ascii=False, indent=1, default=conv),
                                                  encoding="utf-8", newline="\n")
    log("falhas:", [k for k, v in REG["etapas"].items() if v["status"] != "ok"] or "nenhuma")
    log("FIM")


if __name__ == "__main__":
    main()
