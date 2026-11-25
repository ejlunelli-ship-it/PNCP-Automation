"""Etapas 6–7: pareamento por evento dentro do conjunto de risco (Fase I).

Métodos (todos fixados antes de qualquer desfecho pós-tratamento):
  M0   Mahalanobis regularizada nas covariáveis institucionais/atividade/composição (sem preço);
  M1   M0 + nível, tendência, dispersão e disponibilidade do índice em t0−6..t0−3 (sensibilidade);
  PS   vizinho mais próximo no logit do propensity score de mudança, caliper 0,2 dp;
  PSM  Mahalanobis M0 entre os controles dentro do caliper do PS.
Regras comuns: mesmo t0 e mesma origem (por construção do conjunto de risco), mesma esfera, CNPJ diferente,
1 a k controles (prioridade a k), reposição entre eventos e não dentro do evento, desempate determinístico pelo
código da UASG, pesos iguais 1/k_e. Sem controle aceitável o evento fica SEM SUPORTE (nada é extrapolado).
"""
import numpy as np
import pandas as pd
from scipy import stats

from . import construir_covariaveis as cv


def padronizar(pop_t, cols):
    """Padroniza com a população de risco pertinente (direção × t0) e remove colunas constantes."""
    Z = pop_t[cols].to_numpy(float)
    mu, sd = Z.mean(0), Z.std(0)
    usar = np.isfinite(sd) & (sd > 1e-12)
    return (Z[:, usar] - mu[usar]) / sd[usar], [c for c, u in zip(cols, usar) if u]


def inversa_regularizada(Z, reg):
    """Σ + reg·I (Z padronizado, diagonal ~1); pseudo-inversa para matriz singular ou mal condicionada."""
    S = np.cov(Z, rowvar=False) if Z.shape[0] > 1 else np.eye(Z.shape[1])
    S = np.atleast_2d(S) + reg * np.eye(Z.shape[1])
    return np.linalg.pinv(S, hermitian=True), float(np.linalg.cond(S))


def parear_evento(u, cand, Zmap, Sinv, k, caliper_d2, logit=None, caliper_ps=None, escala=None, razao_max=None,
                  usar_ps_distancia=False, uasg=None):
    """Retorna (lista de (v, d2, dps)), motivos de exclusão. Zmap: u -> vetor padronizado."""
    motivos = {"fora_caliper_mahalanobis": 0, "fora_caliper_ps": 0, "fora_razao_escala": 0}
    res = []
    for v in cand:
        dps = abs(logit[v] - logit[u]) if logit is not None else np.nan
        if caliper_ps is not None and not dps <= caliper_ps:
            motivos["fora_caliper_ps"] += 1
            continue
        if escala is not None:
            r = np.exp(escala[v] - escala[u])
            if not (1 / razao_max <= r <= razao_max):
                motivos["fora_razao_escala"] += 1
                continue
        if usar_ps_distancia:
            d2 = dps ** 2
        else:
            dz = Zmap[v] - Zmap[u]
            d2 = float(dz @ Sinv @ dz)
            if caliper_d2 is not None and d2 / 2 > caliper_d2:
                motivos["fora_caliper_mahalanobis"] += 1
                continue
        res.append((v, d2, dps))
    res.sort(key=lambda x: (round(x[1], 10), uasg[x[0]]))
    return res[:k], motivos


def executar_metodo(metodo, pop, eventos, cand_por_evento, ps_logit, cfg_m, unidades, k=None):
    """pop: população de risco de UMA direção (todas as t0), linhas únicas por (u, t0). Retorna pares e status."""
    k = k or cfg_m["k_max"]
    reg = cfg_m["regularizacao_mahalanobis"]
    pares, status = [], []
    for t0, pt in pop.groupby("t0"):
        pt = pt[pt.completo & (pt.tratada | pt.candidata)].reset_index(drop=True)
        cols = cv.colunas_m1(pt) if metodo == "M1" else cv.colunas_m0(pt)
        pti = cv.imputar(pt, cols)
        Z, usadas = padronizar(pti, cols)
        Sinv, cond = inversa_regularizada(Z, reg)
        Zmap = {int(u): Z[i] for i, u in enumerate(pt.u)}
        c2 = stats.chi2.ppf(cfg_m["caliper_mahalanobis_quantil_chi2"], len(usadas))
        lg = {int(u): ps_logit.get((int(u), int(t0)), np.nan) for u in pt.u}
        escala = dict(zip(pt.u.astype(int), pt.log_itens))
        cal_ps = cfg_m["caliper_ps_dp_logit"] * cfg_m["_dp_logit_direcao"]
        uasg = {int(u): unidades[int(u)] for u in pt.u}
        for e in eventos[eventos.t0 == t0].itertuples():
            cand = [int(v) for v in cand_por_evento.get(e.id_evento, []) if int(v) in Zmap]
            u = int(e.u)
            if u not in Zmap:
                status.append({"id_evento": e.id_evento, "metodo": metodo, "aceito": False, "n_controles": 0,
                               "motivo": "tratada fora da população completa", "candidatas": len(cand)})
                continue
            if metodo == "M0" or metodo == "M1":
                sel, mot = parear_evento(u, cand, Zmap, Sinv, k, c2, logit=lg, escala=escala,
                                         razao_max=cfg_m["razao_escala_max"], uasg=uasg)
            elif metodo == "PS":
                sel, mot = parear_evento(u, cand, Zmap, Sinv, k, None, logit=lg, caliper_ps=cal_ps, usar_ps_distancia=True,
                                         uasg=uasg)
            elif metodo == "PSM":
                sel, mot = parear_evento(u, cand, Zmap, Sinv, k, c2, logit=lg, caliper_ps=cal_ps, escala=escala,
                                         razao_max=cfg_m["razao_escala_max"], uasg=uasg)
            else:
                raise ValueError(metodo)
            st = {"id_evento": e.id_evento, "metodo": metodo, "aceito": len(sel) > 0, "n_controles": len(sel),
                  "candidatas": len(cand), "covariaveis": len(usadas), "condicao_sigma": cond,
                  "motivo": "pareado" if sel else ("sem candidatas no conjunto de risco" if not cand else
                                                    "nenhuma candidata dentro dos calipers"), **mot}
            status.append(st)
            for ordem, (v, d2, dps) in enumerate(sel, 1):
                pares.append({"metodo": metodo, "id_evento": e.id_evento, "t0": int(t0), "direcao": e.direcao,
                              "sinal_af": int(e.sinal_af), "u_tratada": u, "uasg_tratada": unidades[u], "cnpj_tratada": e.cnpj,
                              "u_controle": v, "uasg_controle": unidades[v], "cnpj_controle": pt.cnpj[pt.u == v].iat[0],
                              "ordem": ordem, "distancia_mahalanobis": float(np.sqrt(d2)) if metodo != "PS" else np.nan,
                              "logit_ps_tratada": lg[u], "logit_ps_controle": lg[v], "dif_logit_ps": dps,
                              "peso": 1.0 / len(sel), "covariaveis": "|".join(usadas),
                              "motivo_inclusao": f"{ordem}º vizinho ({metodo}) dentro dos calipers; mesma esfera, CNPJ distinto"})
    return pd.DataFrame(pares), pd.DataFrame(status)
