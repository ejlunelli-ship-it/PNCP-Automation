"""Fase II — estimação (só depois do congelamento): DiD pareado, inferência, influência, composição, robustez e
comparação com o dCDH reestimado na S1 (rodada efeito_modos_cesta_auto_S1_20261125, resultados auditáveis)."""
import sys

import numpy as np
import pandas as pd

from . import comum
from . import inferencia as inf
from . import testar_composicao as tc
from .estimar_did import abrir_pos, montar_linhas
from .pipeline import RES, TAB
from .robustez import ESPECS


def _filtrar_pares(pares, desenho, metodo):
    return pares[(pares.desenho == desenho) & (pares.metodo == metodo) & pares.balanceado].copy()


def _ipw(P, pares, ev_info):
    """Peso 1/p̂ de o controle permanecer na origem em t0+1, com logit em covariáveis pré (M0) do desenho."""
    from . import construir_covariaveis as cv
    from . import estimar_propensao as ps
    from .construir_painel import A, AF
    d = comum.ler_pkl(comum.trabalho(comum.cfg(), "desenho_principal.pkl.gz"))
    pop = pd.concat(d["pop"].values(), ignore_index=True).set_index(["u", "t0"])
    st = P.arr["status"]
    rows = []
    for r in pares.itertuples():
        o = A if r.direcao == "A->AF" else AF
        j = P.j(r.t0) + 1
        if j >= P.T:
            continue
        rows.append({"id_evento": r.id_evento, "u": int(r.u_controle), "t0": int(r.t0), "y": int(st[int(r.u_controle), j] == o)})
    R = pd.DataFrame(rows)
    if len(R) < 10 or R.y.nunique() < 2:
        return None
    cols = [c for c in cv.M0_CONT]
    X = pop.loc[list(zip(R.u, R.t0)), cols].reset_index(drop=True)
    X = cv.imputar(X, cols)
    X["t0"] = R.t0.to_numpy()
    X["y"] = R.y.to_numpy()
    eta, p, *_ = ps.estimar(X, cols, 1.0)
    return {(i, u): 1.0 / max(pp, 0.05) for i, u, pp in zip(R.id_evento, R.u, p)}


def linhas_spec(spec, P_por_amostra, pares_all, ev, top_cnpjs):
    sid, desc, desenho, metodo, amostra, ycol, ncol, pesos, alvo, cens, filtro, tipo = spec
    Ppos = P_por_amostra[amostra]
    P = Ppos._p
    pr = _filtrar_pares(pares_all, desenho, metodo)
    if filtro == "persistentes":
        pers = set(ev.loc[ev["persistencia_t0+1"] == "persistente", "id_evento"])
        pr = pr[pr.id_evento.isin(pers)]
    if not len(pr):
        return pd.DataFrame(), {}
    if tipo in ("C2", "C3"):
        L, perdas = tc.montar_linhas_comp(P, pr, 0, tipo, comum.cfg()["composicao"]["C2_cobertura_min"])
        return L, perdas
    pc = _ipw(P, pr, ev) if filtro == "ipw" else None
    if filtro == "ipw" and pc is None:
        return pd.DataFrame(), {"ipw": "não estimável (poucas linhas ou sem variação na permanência)"}
    L = montar_linhas(lambda t0: Ppos, pr, alvo, -1, ycol, ncol, cens, pesos, status=Ppos, pesos_controle=pc)
    if filtro in ("adocao", "abandono") and len(L):
        L = L[L.grupo == filtro]
    if filtro in ("sem_top1", "sem_top3") and len(L):
        k = 1 if filtro == "sem_top1" else 3
        for g in top_cnpjs[:k]:
            L = inf.remover_cluster(L, "cnpj", g)
    return L, {}


def resultados_spec(spec, L, B, semente, margem):
    sid, desc, desenho, metodo, *_rest = spec
    filtro = spec[10]
    out = []
    if not len(L):
        return [{"spec": sid, "descricao": desc, "grupo": "agregado", "eventos": 0, "classificacao": "não estimável"}]
    grupos = [("agregado", None)] if filtro in ("adocao", "abandono") else [("agregado", None), ("adocao", "adocao"),
                                                                           ("abandono_AF", "abandono")]
    if filtro in ("adocao", "abandono"):
        L = L[L.grupo == filtro]
    for nome, g in grupos:
        r = inf.contraste(L, g, B=B, semente=semente, margem=margem)
        out.append({"spec": sid, "descricao": desc, "grupo": nome, **r})
        if nome == "abandono_AF" and r.get("eventos"):
            out.append({"spec": sid, "descricao": desc, "grupo": "abandono_sinal_original", "beta_lp": -r["beta_lp"],
                        "ep": r.get("ep"), "ic95_inf": -r["ic95_sup"] if "ic95_sup" in r else np.nan,
                        "ic95_sup": -r["ic95_inf"] if "ic95_inf" in r else np.nan, "p_t": r.get("p_t"), "eventos": r["eventos"]})
    if filtro is None and (L.grupo == "adocao").any() and (L.grupo == "abandono").any():
        s = inf.diferenca(L, "adocao", "abandono", B=B, semente=semente)
        out.append({"spec": sid, "descricao": desc, "grupo": "simetria_adocao_menos_abandono_AF", **s})
    return out


def dcdh_comparacao(c, ids_eventos_s1, log):
    """dCDH principal da S1 (resultados auditáveis da rodada S1) e dCDH restrito às UASGs/t0 comuns."""
    rod = comum.resolver(c["fontes"]["rodada_S1"])
    f = comum.ler_json(RES / "fontes.json")["resultados_rodada_S1_sha256"]
    for n, h in f.items():
        if comum.sha(rod / n) != h:
            raise comum.ErroDesenho(f"resultado da rodada S1 mudou: {n}")
    ee = pd.read_csv(rod / "amostras/S1/estudo_eventos.csv")
    pr = ee[ee.especificacao == "dcdh_6m_item_celula"]
    pega = lambda g, l: pr[(pr.grupo == g) & (pr.l.astype(str) == str(l))].iloc[0]
    diag = comum.ler_json(rod / "amostras/S1/tabelas/diagnosticos_identificacao.json")
    fe = pd.read_csv(rod / "amostras/S1/efeitos_fixos.csv").set_index("especificacao")
    linhas = [{"desenho": "dCDH original reestimado em S1 (amostra própria)", "eventos": diag["eventos_usados_l1"],
               "orgaos_efetivos": diag["n_efetivo_cnpjs"], "placebo_lp": pega("agregado", -1).beta_lp,
               "placebo_ic95": f"[{pega('agregado', -1).ic95_inf:.2f}; {pega('agregado', -1).ic95_sup:.2f}]",
               "efeito_af_lp": pega("agregado", "media").beta_lp,
               "ic95": f"[{pega('agregado', 'media').ic95_inf:.2f}; {pega('agregado', 'media').ic95_sup:.2f}]",
               "populacao": "trocas pela regra de maioria (≥ 0,5) com persistência 2; pesos por célula (itens); l = 1..2",
               "fonte": "efeito_modos_cesta_auto_S1_20261125/amostras/S1/estudo_eventos.csv"}]
    for e in ("E3", "E7"):
        r = fe.loc[e]
        linhas.append({"desenho": f"{e} (efeitos fixos, S1)", "eventos": None, "orgaos_efetivos": r.n_efetivo_orgaos,
                       "placebo_lp": None, "efeito_af_lp": r.beta_lp, "ic95": f"[{r.ic95_inf:.2f}; {r.ic95_sup:.2f}]",
                       "populacao": "todos os itens S1 (associação condicional)", "fonte": "efeitos_fixos.csv da rodada S1"})
    # amostra comum: switchers do dCDH cujo F coincide com o t0 de um evento risk-set estimável
    pop = pd.read_csv(rod / "amostras/S1/tabelas/populacao_eventos_pesos.csv", dtype={"uasg": str})
    E = pd.read_pickle(comum.resolver(c["fontes"]["dados_S1"]) / "eventos_info.pkl")
    pop["t0"] = E["tri_ini"] + pop.F.astype(int)
    alvo_ids = {f"{u}_{comum.nome_tri(t)}" for u, t in zip(pop.uasg, pop.t0)} & set(ids_eventos_s1)
    comuns = sorted(alvo_ids)
    out_comum = None
    if comuns:
        if str(rod) not in sys.path:
            sys.path.insert(0, str(rod))
        from rodada import analises as ra, base as rb
        cr = rb.cfg()
        cfg_ant = comum.ler_json(comum.ORIGINAL / "config.json")
        linhas_d, dg = ra.dcdh_restrito(cr, "S1", {x.split("_")[0] for x in comuns}, cfg_ant["eventos"]["bootstrap"],
                                        cfg_ant["semente"], cfg_ant["eventos"]["janelas_trimestres"]["6m"], log)
        ag = [l for l in linhas_d if l["grupo"] == "agregado"]
        g = {str(l["l"]): l for l in ag}
        out_comum = {"desenho": "dCDH restrito aos eventos comuns", "eventos": dg["eventos_l1"], "orgaos_efetivos": dg["n_efetivo_cnpjs"],
                     "placebo_lp": g.get("-1", {}).get("beta_lp"), "efeito_af_lp": g.get("media", {}).get("beta_lp"),
                     "ic95": f"[{g['media']['ic95_inf']:.2f}; {g['media']['ic95_sup']:.2f}]" if "media" in g else None,
                     "populacao": f"{len(comuns)} eventos (UASG, t0) presentes nos dois desenhos", "fonte": "dcdh_restrito (rodada S1)"}
    return linhas, out_comum, comuns


def executar(c, log):
    from .construir_painel import Painel  # noqa: F401  (desserialização)
    inf_c = c["inferencia"]
    B, sem, margem = inf_c["wcr_B"], c["semente"], inf_c["margem_equivalencia_lp"]
    P1 = comum.ler_pkl(comum.trabalho(c, "painel_S1.pkl.gz"))
    Ppos, pares, prot = abrir_pos(P1, RES / "protocolo_congelado.json", RES / "pares_congelados.parquet")
    log(f"protocolo conferido ({prot['congelado_em']}); {prot['declaracao']}")
    P12 = comum.ler_pkl(comum.trabalho(c, "painel_S1S2.pkl.gz"))
    from .estimar_did import PainelPos
    Pa = {"S1": Ppos, "S1S2": PainelPos(P12)}
    ev = comum.ler_pkl(comum.trabalho(c, "eventos.pkl.gz"))
    pm = _filtrar_pares(pares, "principal", "M0")
    top = pm.drop_duplicates("id_evento").cnpj_tratada.value_counts()
    top_cnpjs = list(top.index)
    res, por_evento, perdas, eventos_spec = [], [], {}, {}
    for spec in ESPECS:
        L, pd_ = linhas_spec(spec, Pa, pares, ev, top_cnpjs)
        if pd_:
            perdas[spec[0]] = pd_
        res += resultados_spec(spec, L, B, sem, margem)
        if len(L):
            e = inf.eventos_tau(L)
            e = e.reset_index().assign(spec=spec[0])
            por_evento.append(e)
            eventos_spec[spec[0]] = set(e.id_evento)
        log(f"  {spec[0]}: {len(eventos_spec.get(spec[0], []))} eventos estimáveis")
    R = pd.DataFrame(res)
    R["classificacao"] = R.get("classificacao", pd.Series(index=R.index, dtype=object)).fillna(
        "descritivo (suporte insuficiente pelo protocolo)" if not prot["diagnostico_desenho"]["suporte_suficiente"] else "exploratório")
    # Holm na família principal (R1: agregado, adoção, abandono_AF)
    fam = R[(R.spec == "R1") & R.grupo.isin(["agregado", "adocao", "abandono_AF"]) & R.p_t.notna()] if "p_t" in R else R.iloc[:0]
    if len(fam):
        R.loc[fam.index, "p_holm_P"] = inf.holm(fam.p_t.to_numpy())
        if fam.p_wcr_webb.notna().all():
            R.loc[fam.index, "p_holm_P_wcr"] = inf.holm(fam.p_wcr_webb.to_numpy())
    # amostra comum com R1 para as especificações de pareamento/desfecho alternativos
    comum_linhas = []
    base_ids = eventos_spec.get("R1", set())
    for spec in ESPECS[1:]:
        ids = eventos_spec.get(spec[0], set()) & base_ids
        if not ids or spec[0] in ("R13", "R17", "R14", "R14m", "X4"):
            continue
        for sid in ("R1", spec[0]):
            sp = next(s for s in ESPECS if s[0] == sid)
            L, _ = linhas_spec(sp, Pa, pares, ev, top_cnpjs)
            L = L[L.id_evento.isin(ids)]
            r = inf.contraste(L, None, B=0, margem=None) if len(L) else {"eventos": 0}
            comum_linhas.append({"comparacao": f"R1 × {spec[0]}", "spec": sid, "eventos_comuns": len(ids), **r})
    comum.escrever_csv(TAB / "efeitos.csv", R.to_dict("records"))
    comum.escrever_csv(TAB / "robustez_amostra_comum.csv", comum_linhas)
    PE = pd.concat(por_evento, ignore_index=True) if por_evento else pd.DataFrame()
    comum.escrever_csv(TAB / "efeitos_por_evento.csv", PE.to_dict("records"))
    saidas = [TAB / "efeitos.csv", TAB / "robustez_amostra_comum.csv", TAB / "efeitos_por_evento.csv"]
    # influência (R1)
    L1, _ = linhas_spec(ESPECS[0], Pa, pares, ev, top_cnpjs)
    infl = {}
    if len(L1):
        for campo in ("cnpj", "uasg"):
            base, jk = inf.jackknife(L1, campo)
            comum.escrever_csv(TAB / f"influencia_sem_{campo}.csv", jk.to_dict("records"))
            saidas.append(TAB / f"influencia_sem_{campo}.csv")
            if len(jk):
                G = len(jk)
                infl[campo] = {"base": base, "min": float(jk.beta_sem.min()), "max": float(jk.beta_sem.max()),
                               "ep_jackknife": float(np.sqrt((G - 1) / G * np.sum((jk.beta_sem - jk.beta_sem.mean()) ** 2)))}
        lin_t = []
        e1 = inf.eventos_tau(L1)
        for campo in ("t0", "direcao"):
            for v in sorted(L1[campo].unique()):
                l = L1[L1[campo] != v]
                e = inf.eventos_tau(l) if len(l) else pd.DataFrame()
                lin_t.append({"excluido": f"{campo}={v}", "eventos_sem": len(e),
                              "beta_sem": float((e.a * e.tau).sum() / e.a.sum()) if len(e) else np.nan,
                              "eventos_no_grupo": int((L1[(L1.papel == 'T')][campo] == v).sum())})
        comum.escrever_csv(TAB / "influencia_trimestre_direcao.csv", lin_t)
        saidas.append(TAB / "influencia_trimestre_direcao.csv")
    # censura dos controles em t0+1 e reversões das tratadas
    st = P1.arr["status"]
    cens = []
    from .construir_painel import A, AF
    for r in pm.itertuples():
        o = A if r.direcao == "A->AF" else AF
        j = P1.j(r.t0) + 1
        s = int(st[int(r.u_controle), j]) if j < P1.T else -9
        cens.append({"id_evento": r.id_evento, "controle": r.uasg_controle, "status_t0+1": {A: "A", AF: "AF", 2: "misto", -1: "sem_compras", -9: "fora"}[s],
                     "permanece_na_origem": s == o})
    comum.escrever_csv(TAB / "censura_controles_t0+1.csv", cens)
    saidas.append(TAB / "censura_controles_t0+1.csv")
    # composição
    aud = tc.auditoria(P1, pm) if len(pm) else pd.DataFrame()
    comum.escrever_csv(TAB / "composicao_auditoria.csv", aud.to_dict("records"))
    saidas.append(TAB / "composicao_auditoria.csv")
    # comparação com o dCDH
    ids_r1 = eventos_spec.get("R1", set())
    lin_d, d_comum, comuns = dcdh_comparacao(c, ids_r1, log)
    tab = []
    for x in lin_d:
        tab.append(x)
    if d_comum:
        tab.append(d_comum)
    plc = pd.read_csv(TAB / "placebos_reservados.csv")
    for sid, rot, met in (("R1", "Risk-set DiD M0", "M0"), ("R2", "Risk-set DiD M1", "M1"), ("R3", "Matching por propensity score", "PS"),
                          ("R9", "Mesmo produto pré/pós (C3, pares M0; placebo = o de M0)", "M0")):
        r = R[(R.spec == sid) & (R.grupo == "agregado")]
        r = r.iloc[0] if len(r) else None
        p = plc[(plc.desenho == "principal") & (plc.metodo == met) & (plc.placebo == "reservado_t-2_t-1") & (plc.grupo == "agregado")]
        p = p.iloc[0] if len(p) else None
        tab.append({"desenho": rot, "eventos": int(r.eventos) if r is not None and r.eventos == r.eventos else 0,
                    "orgaos_efetivos": r.get("n_efetivo_cnpjs_tratados") if r is not None else None,
                    "placebo_lp": p.beta_lp if p is not None else None,
                    "placebo_ic95": f"[{p.ic95_inf:.2f}; {p.ic95_sup:.2f}]" if p is not None and p.ic95_inf == p.ic95_inf else None,
                    "efeito_af_lp": r.get("beta_lp") if r is not None else None,
                    "ic95": f"[{r.ic95_inf:.2f}; {r.ic95_sup:.2f}]" if r is not None and r.get("ic95_inf") == r.get("ic95_inf") else None,
                    "populacao": "eventos inequívocos pareados (h = 0, peso igual por evento)", "fonte": "tabelas/efeitos.csv"})
    if comuns and len(L1):
        l = L1[L1.id_evento.isin(comuns)]
        r = inf.contraste(l, None, B=B, semente=sem, margem=None) if len(l) else {}
        tab.append({"desenho": "Risk-set DiD M0 restrito aos eventos comuns", "eventos": r.get("eventos"),
                    "orgaos_efetivos": r.get("n_efetivo_cnpjs_tratados"), "efeito_af_lp": r.get("beta_lp"),
                    "ic95": f"[{r['ic95_inf']:.2f}; {r['ic95_sup']:.2f}]" if "ic95_inf" in r else None,
                    "populacao": f"{len(comuns)} eventos comuns", "fonte": "tabelas/efeitos_por_evento.csv"})
    comum.escrever_csv(TAB / "comparacao_desenhos.csv", tab)
    saidas.append(TAB / "comparacao_desenhos.csv")
    resumo = {"estimado_em": comum.agora(), "protocolo": prot["congelado_em"], "declaracao_suporte": prot["declaracao"],
              "perdas_composicao": perdas, "influencia": infl, "eventos_comuns_dcdh": comuns,
              "controles_censurados_t0+1": int(sum(1 for x in cens if not x["permanece_na_origem"])), "pares_M0": int(len(pm))}
    comum.escrever_json(RES / "fase2_resumo.json", resumo)
    return saidas + [RES / "fase2_resumo.json"]
