"""Poder do estudo de eventos para o pré-registro, SEM olhar o desfecho das unidades que mudaram de modo.

Para cada evento real (data, esfera e sentido) usam-se só os controles limpos daquela janela: o desvio
Δ_p − média(Δ) de cada controle p é um "DiD placebo" de uma unidade que não mudou. Ajusta-se a variância desse desvio
como função do nº de compras nas meias janelas (h = 1/c_pre + 1/c_pós) e projeta-se a variância de cada evento real com
as contagens da unidade tratada (contagens não são desfecho). Efeito mínimo detectável (80% de poder, 5% bilateral):
EMD = 2,8 × EP. Correção de agrupamento por CNPJ pela correlação intraclasse dos desvios de unidades do mesmo CNPJ.

Uso (da pasta PNCP-Automation): python analises/testes_desenho_causal_20261123/poder.py
Saída: poder.json nesta pasta.
"""
import json

import numpy as np
import pandas as pd

import comum as C
import motor as Mo


def carregar():
    P = dict(np.load(C.DADOS / "paineis.npz"))
    un = pd.read_pickle(C.DADOS / "unidades.pkl")
    ev = pd.read_csv(C.AQUI / "eventos.csv", dtype={"unidade": str, "cnpj": str})
    mf = (int(C.FIM_ITENS[:4]) * 12 + int(C.FIM_ITENS[5:7]) - 1) - C.M0 + 1
    return Mo.Paineis(P, mf), un, ev


def eventos_validos(ev, W):
    e = ev.copy()
    if W == 12:
        e = e[(e.dist_vizinho >= 12) & ((e.af_depois_12 - e.af_antes_12).abs() >= .5)]
    return e


def emd(pn, un, ev, W, cmin, y="e"):
    e = eventos_validos(ev, W)
    res, ctrl = Mo.did_eventos(pn, e, y=y, W=W, cmin=cmin, unid=un, ev_todos=ev, guardar_controles=True, cego=True)
    if res.empty:
        return None
    dev = pd.concat([c.assign(k=k) for k, c in ctrl.items()], ignore_index=True)
    dev["cnpj"] = un.cnpj.reindex(dev.u).to_numpy()
    # variância do DiD placebo em função de h (MQO de dev² em h), e versão robusta (escala MAD)
    X = np.column_stack([np.ones(len(dev)), dev.h])
    a, b = np.linalg.lstsq(X, dev.dev ** 2, rcond=None)[0]
    escala_rob = (1.4826 * np.median(np.abs(dev.dev - np.median(dev.dev))) / dev.dev.std()) ** 2
    res["var"] = np.maximum(a + b * res.h, 1e-6)
    # correlação intraclasse: pares de controles do mesmo CNPJ no mesmo evento
    num = den = 0.0
    for (k, g), z in dev.groupby(["k", "cnpj"]):
        if len(z) > 1:
            s = z.dev.sum()
            num += s ** 2 - (z.dev ** 2).sum()
            den += (len(z) - 1) * (z.dev ** 2).sum()
    icc = num / den if den > 0 else 0.0
    res["cnpj"] = un.cnpj.reindex(res.u).to_numpy()
    out = {"W": W, "cmin": cmin, "eventos": res.groupby("tipo").size().to_dict(),
           "cnpjs": res.groupby("tipo").cnpj.nunique().to_dict(), "controles_medios": float(res.n_controles.mean()),
           "compras_medias_janela": float((res.c_pre + res.c_pos).mean()),
           "var_modelo": {"a": float(a), "b": float(b)}, "dp_placebo": float(dev.dev.std()),
           "fator_robusto": float(escala_rob), "icc_cnpj": float(icc)}
    for nome, z in [("A->AF", res[res.tipo.eq("A->AF")]), ("AF->A", res[res.tipo.eq("AF->A")]), ("agregado", res)]:
        n = len(z)
        if n == 0:
            continue
        ng = z.groupby("cnpj").size()
        deff = 1 + icc * ((ng ** 2).sum() / n - 1)
        ep = np.sqrt(z["var"].sum()) / n
        ep_w = np.sqrt(1 / (1 / z["var"]).sum())                 # pesos de precisão w_k = 1/var_k
        out[nome] = {"n": n, "EP": float(ep), "EMD_lp": float(2.8 * ep), "EMD_lp_robusto": float(2.8 * ep * np.sqrt(escala_rob)),
                     "deff": float(deff), "EMD_lp_agrupado": float(2.8 * ep * np.sqrt(deff)),
                     "EMD_pct_agrupado": C.pct(-2.8 * ep * np.sqrt(deff)),
                     "EP_precisao": float(ep_w), "EMD_lp_precisao_agrupado": float(2.8 * ep_w * np.sqrt(deff)),
                     "EMD_pct_precisao_agrupado": C.pct(-2.8 * ep_w * np.sqrt(deff))}
    return out


def main():
    pn, un, ev = carregar()
    R = {"nota": "calculado só com controles (unidades estáveis); o desfecho das unidades que mudaram não é lido"}
    for W in (6, 12):
        for cmin in (1, 2, 3, 5):
            r = emd(pn, un, ev, W, cmin)
            R[f"W{W}_cmin{cmin}"] = r
            if r:
                print(W, cmin, r["eventos"], "EMD agregado (lp):", round(r["agregado"]["EMD_lp"] * 100, 2),
                      "agrupado:", round(r["agregado"]["EMD_lp_agrupado"] * 100, 2),
                      "precisão agrupado:", round(r["agregado"]["EMD_lp_precisao_agrupado"] * 100, 2),
                      "ICC", round(r["icc_cnpj"], 3), flush=True)
    # índice do item ponderado por item e índice truncado em ±3 (sensibilidades), na especificação W=6, cmin=3
    for y in ("e_c3",):
        r = emd(pn, un, ev, 6, 3, y=y)
        R[f"W6_cmin3_{y}"] = r
    (C.AQUI / "poder.json").write_text(json.dumps(R, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    print("FIM ok")


if __name__ == "__main__":
    main()
