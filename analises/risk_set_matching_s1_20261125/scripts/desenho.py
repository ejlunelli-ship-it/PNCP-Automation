"""Fase I — desenho: conjuntos de risco, propensity score, pareamento, balanceamento, placebos reservados e funil.

Usa apenas: regime de modo (até t0), covariáveis pré-evento e preços de t0−6..t0−1 através de PainelPre(t0).
Nenhum desfecho de t >= t0 (nem a sua disponibilidade) é lido aqui.
"""
import numpy as np
import pandas as pd

from . import construir_covariaveis as cv
from . import construir_risk_sets as rs
from . import diagnosticar_balanceamento as bal
from . import estimar_propensao as ps
from . import executar_placebos as plc
from . import realizar_matching as rm
from .construir_painel import A, AF

METODOS_PRINCIPAL = [("M0", None), ("M1", None), ("PS", None), ("PSM", None), ("M0_k1", 1), ("M0_k3", 3)]


def _base_metodo(m):
    return m.split("_k")[0]


def executar(c, P, ev, nome, curta=False, metodos=None, log=print):
    d = c["desenho"]
    jan = d["janela_curta"] if curta else d
    form, falsif, min_form = jan["formacao"], jan["falsificacao"], jan["min_trimestres_formacao_com_preco"]
    col_cal = "janela_curta_calendario" if curta else "janela_principal_calendario"
    col_hist = "historico_curto_compativel" if curta else "historico_modo_compativel"
    metodos = metodos or METODOS_PRINCIPAL
    classes_top = P.attr["_classes_top"]
    cm = dict(c["matching"])
    funil_ev = ev[ev[col_cal]].copy()
    saida = {"nome": nome, "curta": curta, "col_hist": col_hist, "pop": {}, "ps": {}, "pares": [], "status": [], "eventos": None, "funil": None}
    eventos_ok = []
    for direcao, origem in (("A->AF", A), ("AF->A", AF)):
        evd = funil_ev[funil_ev.direcao == direcao]
        pops = []
        for t0, g in evd.groupby("t0"):
            pops.append(rs.populacao_t0(P, int(t0), origem, form, falsif, min_form, classes_top, g))
        if not pops:
            continue
        pop = pd.concat(pops, ignore_index=True)
        elig = evd[evd[col_hist]]
        key_trat = set(zip(elig.u.astype(int), elig.t0.astype(int)))
        pop["evento_elegivel"] = [bool(t) and (int(u), int(t0)) in key_trat for u, t0, t in zip(pop.u, pop.t0, pop.tratada)]
        risco = pop[pop.completo & (pop.candidata | pop.evento_elegivel)].reset_index(drop=True)
        risco["y"] = risco.evento_elegivel.astype(int)
        # eventos com histórico de modo e de preços suficiente
        comp = set(zip(risco.loc[risco.evento_elegivel, "u"], risco.loc[risco.evento_elegivel, "t0"]))
        evd = evd.assign(historico_suficiente=[bool(h) and (int(u), int(t)) in comp
                                               for u, t, h in zip(evd.u, evd.t0, evd[col_hist])])
        evs = evd[evd.historico_suficiente]
        cand, tab_rs = rs.conjuntos(risco, evs, d["excluir_mesmo_cnpj"], tuple(d["exato"]))
        # propensity score de mudança
        cols0 = cv.colunas_m0(risco)
        rimp = cv.imputar(risco, cols0)
        eta, p, diag, calib, coefs = ps.estimar(rimp, cols0, cm["ps_penalidade_l2"])
        risco["logit_ps"], risco["ps"] = eta, p
        lg = {(int(u), int(t)): float(e) for u, t, e in zip(risco.u, risco.t0, eta)}
        cm["_dp_logit_direcao"] = diag["dp_logit_populacao"]
        diag["caliper_logit"] = cm["caliper_ps_dp_logit"] * diag["dp_logit_populacao"]
        # suporte comum: logit da tratada dentro do intervalo dos logits das suas candidatas
        sup = {}
        for e in evs.itertuples():
            cl = [lg[(int(v), int(e.t0))] for v in cand.get(e.id_evento, [])]
            le = lg.get((int(e.u), int(e.t0)), np.nan)
            sup[e.id_evento] = bool(cl) and np.isfinite(le) and min(cl) <= le <= max(cl)
        diag["tratadas_fora_do_suporte"] = int(sum(1 for e in evs.itertuples() if cand.get(e.id_evento) is not None
                                                   and len(cand[e.id_evento]) and not sup[e.id_evento]))
        diag["fracao_tratadas_fora_do_suporte"] = diag["tratadas_fora_do_suporte"] / max(1, sum(
            1 for e in evs.itertuples() if len(cand.get(e.id_evento, []))))
        evd = evd.assign(com_controles=evd.id_evento.map(lambda i: len(cand.get(i, [])) > 0),
                         ps_valido=[bool(np.isfinite(lg.get((int(u), int(t)), np.nan))) for u, t in zip(evd.u, evd.t0)],
                         suporte_comum=evd.id_evento.map(lambda i: sup.get(i, False)))
        evs_sup = evd[evd.historico_suficiente & evd.com_controles & evd.suporte_comum]
        # pareamento
        sd_ref = cv.imputar(risco, cols0)[cv.M0_CONT].std().to_numpy()
        for metodo, k in metodos:
            mb = _base_metodo(metodo)
            pr, st = rm.executar_metodo(mb, risco, evs_sup, cand, lg, cm, P.unidades, k=k)
            if len(pr):
                pr["metodo"] = metodo
                be = bal.balanco_evento(risco, pr, cv.M0_CONT, sd_ref)
                lim = cm["balanceamento_evento_max_media_abs_dif_padronizada"]
                pr["balanco_evento"] = pr.id_evento.map(be)
                pr["balanceado"] = pr.balanco_evento <= lim
                pr["desenho"] = nome
            if len(st):
                st["metodo"] = metodo
                st["desenho"] = nome
            saida["pares"].append(pr)
            saida["status"].append(st)
        saida["pop"][direcao] = risco
        saida["ps"][direcao] = {"diag": diag, "calibracao": calib, "coeficientes": coefs}
        saida.setdefault("cand", {}).update(cand)
        saida.setdefault("tab_risco", []).append(tab_rs)
        eventos_ok.append(evd)
    saida["eventos"] = pd.concat(eventos_ok, ignore_index=True) if eventos_ok else pd.DataFrame()
    saida["pares"] = pd.concat([x for x in saida["pares"] if len(x)], ignore_index=True) if saida["pares"] else pd.DataFrame()
    saida["status"] = pd.concat([x for x in saida["status"] if len(x)], ignore_index=True) if saida["status"] else pd.DataFrame()
    saida["tab_risco"] = pd.concat(saida.get("tab_risco", []), ignore_index=True) if saida.get("tab_risco") else pd.DataFrame()
    return saida


def balanceamento(saida, metodo):
    """Tabelas antes/depois (covariáveis M1 = M0 + preços de formação) por direção."""
    out = []
    pr = saida["pares"]
    for direcao, risco in saida["pop"].items():
        evs = saida["eventos"]
        evs = evs[(evs.direcao == direcao) & evs.historico_suficiente & evs.com_controles & evs.suporte_comum]
        p = pr[(pr.metodo == metodo) & (pr.direcao == direcao) & pr.balanceado] if len(pr) else pr
        cols = cv.colunas_m1(risco)
        t = bal.tabela(risco, evs, saida["cand"], p, cols)
        t.insert(0, "direcao", direcao)
        t.insert(0, "metodo", metodo)
        out.append(t)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def balanceamento_por_t0(saida, metodo, cols=("log_itens", "log_compras", "srp", "y_nivel", "y_tendencia")):
    linhas = []
    pr = saida["pares"]
    for direcao, risco in saida["pop"].items():
        for t0, rt in risco.groupby("t0"):
            evs = saida["eventos"]
            evs = evs[(evs.direcao == direcao) & (evs.t0 == t0) & evs.historico_suficiente & evs.com_controles & evs.suporte_comum]
            p = pr[(pr.metodo == metodo) & (pr.direcao == direcao) & (pr.t0 == t0) & pr.balanceado]
            if not len(evs) or not len(p):
                continue
            t = bal.tabela(risco, evs, saida["cand"], p, list(cols))
            for r in t.itertuples():
                linhas.append({"metodo": metodo, "direcao": direcao, "t0": int(t0), "covariavel": r.covariavel,
                               "smd_antes": r.smd_antes, "smd_depois": getattr(r, "smd_depois", np.nan), "eventos": len(evs)})
    return pd.DataFrame(linhas)


def funil(saida, metodo="M0"):
    ev = saida["eventos"]
    pr = saida["pares"]
    st = saida["status"]
    pm = pr[pr.metodo == metodo] if len(pr) else pr
    aceitos = set(pm.id_evento) if len(pm) else set()
    balanc = set(pm.loc[pm.balanceado, "id_evento"]) if len(pm) else set()
    etapas = [("1_identificados_na_janela", pd.Series(True, index=ev.index), "eventos inequívocos com t0 na janela de calendário"),
              ("2_historico_suficiente", ev.historico_suficiente, "histórico de modo compatível + completude de preços pré"),
              ("3_com_controles_no_risco", ev.com_controles, "ao menos 1 candidata (mesmo t0, origem, esfera; outro CNPJ)"),
              ("4_ps_valido", ev.ps_valido, "propensity score calculado (logit finito)"),
              ("5_suporte_comum", ev.suporte_comum, "logit da tratada no intervalo das candidatas"),
              ("6_matching_aceito", ev.id_evento.isin(aceitos), f"≥ 1 controle dentro dos calipers ({metodo})"),
              ("7_balanceamento_satisfatorio", ev.id_evento.isin(balanc), "média |dif. padronizada| ≤ 0,5 no evento"),
              ("8_placebo_disponivel", ev.id_evento.isin(balanc), "t−2 e t−1 observados (garantido pela completude)")]
    linhas = []
    m = pd.Series(True, index=ev.index)
    for nome, cond, desc in etapas:
        m = m & cond.astype(bool)
        for (direcao, t0), g in [(("todas", "todos"), ev[m])] + [((d, "todos"), ev[m & (ev.direcao == d)]) for d in ("A->AF", "AF->A")] + \
                [((d, t), ev[m & (ev.direcao == d) & (ev.t0 == t)]) for d in ("A->AF", "AF->A") for t in sorted(ev.t0.unique())]:
            ids = set(g.id_evento)
            ctr = pm[pm.id_evento.isin(ids)] if len(pm) and nome >= "6" else None
            cnt = g.cnpj.value_counts(normalize=True)
            linhas.append({"etapa": nome, "criterio": desc, "direcao": direcao,
                           "t0": t0 if t0 == "todos" else f"{int(t0) // 4}T{int(t0) % 4 + 1}",
                           "eventos": int(len(g)), "uasgs_tratadas": int(g.uasg.nunique()), "cnpjs_tratados": int(g.cnpj.nunique()),
                           "n_efetivo_cnpjs_tratados": float(1 / np.sum(cnt ** 2)) if len(cnt) else 0.0,
                           "uasgs_controle": int(ctr.uasg_controle.nunique()) if ctr is not None else None,
                           "cnpjs_controle": int(ctr.cnpj_controle.nunique()) if ctr is not None else None})
    return pd.DataFrame(linhas)


def motivos_descarte(saida, metodo="M0"):
    ev = saida["eventos"].copy()
    pr = saida["pares"]
    pm = pr[pr.metodo == metodo] if len(pr) else pr
    st = saida["status"]
    stm = st[st.metodo == metodo].set_index("id_evento") if len(st) else pd.DataFrame()
    bal_ok = set(pm.loc[pm.balanceado, "id_evento"]) if len(pm) else set()

    def motivo(r):
        if not r.historico_suficiente:
            return "histórico de modo incompatível (misto/destino antes de t−1)" if not getattr(r, saida["col_hist"]) \
                else "preços pré insuficientes (t−1, t−2 ou < mín. trimestres de formação)"
        if not r.com_controles:
            return "sem candidata no conjunto de risco (mesma esfera, outro CNPJ, completa)"
        if not r.suporte_comum:
            return "fora do suporte comum do propensity score"
        if r.id_evento in stm.index and not stm.loc[r.id_evento, "aceito"]:
            return "nenhuma candidata dentro dos calipers"
        if r.id_evento not in bal_ok:
            return "balanceamento do evento insatisfatório"
        return "mantido"
    ev["motivo"] = [motivo(r) for r in ev.itertuples()]
    return ev


def viabilidade(c, P, ev, tr_anterior=None):
    """DIAGNÓSTICO (só contagens de eventos tratados; nada é estimado): quantos eventos sobreviveriam sob regras
    de completude e de histórico alternativas. Usa apenas dados anteriores a t0. Não substitui o protocolo — serve
    para documentar a inviabilidade e orientar um eventual desenho futuro pré-registrado."""
    Y = P.arr["Yc"]
    w = ev[ev.janela_principal_calendario].copy()

    def disp(u, t0, rels):
        j = P.j(t0)
        return np.array([np.isfinite(Y[u, j + r]) if 0 <= j + r < P.T else False for r in rels])
    w["y_t1"] = [disp(u, t, [-1])[0] for u, t in zip(w.u, w.t0)]
    w["y_t1_t2"] = [disp(u, t, [-2, -1]).all() for u, t in zip(w.u, w.t0)]
    w["n_form"] = [disp(u, t, [-6, -5, -4, -3]).sum() for u, t in zip(w.u, w.t0)]
    regras = [("principal: histórico de modo + Y(t−1,t−2) + ≥2 de 4 formação", w.historico_modo_compativel & w.y_t1_t2 & (w.n_form >= 2)),
              ("histórico de modo + Y(t−1,t−2), sem formação", w.historico_modo_compativel & w.y_t1_t2),
              ("histórico de modo + Y(t−1)", w.historico_modo_compativel & w.y_t1),
              ("sem exigir histórico de modo + Y(t−1,t−2) + ≥2 formação", w.y_t1_t2 & (w.n_form >= 2)),
              ("sem exigir histórico de modo + Y(t−1,t−2)", w.y_t1_t2),
              ("sem exigir histórico de modo + Y(t−1)", w.y_t1),
              ("somente histórico de modo compatível", w.historico_modo_compativel),
              ("todos os eventos inequívocos na janela", pd.Series(True, index=w.index))]
    linhas = []
    for nome, m in regras:
        g = w[m]
        linhas.append({"regime": "inequívoco (principal)", "regra": nome, "eventos": int(len(g)), "uasgs": int(g.uasg.nunique()),
                       "cnpjs": int(g.cnpj.nunique()), "adocoes": int((g.direcao == "A->AF").sum()), "abandonos": int((g.direcao == "AF->A").sum())})
    if tr_anterior is not None:
        t0_min = comum_tri(c["periodo"]["preco_primeiro"]) + 6
        t0_max = comum_tri(c["periodo"]["preco_ultimo"])
        ta = tr_anterior[(tr_anterior.t0 >= t0_min) & (tr_anterior.t0 <= t0_max)].copy()
        ta["u"] = ta.uasg.map(P.pos)
        ta = ta[ta.u.notna()]
        ta["u"] = ta.u.astype(int)
        y12 = [disp(u, t, [-2, -1]).all() for u, t in zip(ta.u, ta.t0)]
        nf = [disp(u, t, [-6, -5, -4, -3]).sum() for u, t in zip(ta.u, ta.t0)]
        y1 = [disp(u, t, [-1])[0] for u, t in zip(ta.u, ta.t0)]
        for nome, m in (("regra anterior (maioria ≥ 0,5, persistência 2): todos na janela", np.ones(len(ta), bool)),
                        ("regra anterior + Y(t−1,t−2) + ≥2 formação", np.array(y12) & (np.array(nf) >= 2)),
                        ("regra anterior + Y(t−1)", np.array(y1))):
            g = ta[m]
            linhas.append({"regime": "regra anterior", "regra": nome, "eventos": int(len(g)), "uasgs": int(g.uasg.nunique()),
                           "cnpjs": int(g.cnpj.nunique()), "adocoes": int((g.direcao == "A->AF").sum()),
                           "abandonos": int((g.direcao == "AF->A").sum())})
    # densidade do índice: UASG-trimestres com compras A/AF que têm índice S1
    st = P.arr["status"]
    jp0, jp1 = P.j(comum_tri(c["periodo"]["preco_primeiro"])), P.j(comum_tri(c["periodo"]["preco_ultimo"]))
    obs = st[:, jp0:jp1 + 1] >= 0
    dens = {"uasg_trimestres_com_compras_A_AF": int(obs.sum()),
            "com_indice_S1": int((obs & np.isfinite(Y[:, jp0:jp1 + 1])).sum()),
            "fracao_com_indice": float((obs & np.isfinite(Y[:, jp0:jp1 + 1])).sum() / obs.sum())}
    return pd.DataFrame(linhas), dens


def comum_tri(n):
    return int(n[:4]) * 4 + int(n[-1]) - 1
