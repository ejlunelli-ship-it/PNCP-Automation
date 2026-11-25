"""Etapa 11 (Fase I): falsificação pré-tratamento com os períodos RESERVADOS t0−2 → t0−1.

Os preços de t0−2 e t0−1 nunca entram no pareamento (nem em M1). O acesso é feito exclusivamente pela visão
PainelPre(t0), que recusa qualquer t >= t0. Além do placebo reservado:
- data fictícia t0−4 → t0−3 (sem mudança real; em M1 é mecânico porque esses preços foram usados no pareamento);
- características institucionais (SRP, sigilo, nº de compras, itens, quantidade) entre t0−2 e t0−1;
- regressão à média: relação, entre eventos, entre o desvio pré-placebo da tratada e o placebo.
Ausência de significância NÃO é tratada como paralelismo: reporta-se IC, poder, MDE e teste de equivalência (±5 lp).
"""
import numpy as np
import pandas as pd

from . import inferencia
from .estimar_did import montar_linhas

DERIVADAS = {"srp_tri": ("n_srp", "n_compras"), "sigilo_tri": ("it_sig", "it_n"), "logq_tri": ("logq_soma", "logq_n")}


def adicionar_derivadas(P):
    for nome, (a, b) in DERIVADAS.items():
        with np.errstate(divide="ignore", invalid="ignore"):
            P.arr[nome] = np.where(P.arr[b] > 0, P.arr[a] / np.where(P.arr[b] > 0, P.arr[b], 1), np.nan)
    P.arr["log_compras_tri"] = np.where(P.arr["n_compras"] > 0, np.log(np.maximum(P.arr["n_compras"], 1)), np.nan)
    P.arr["log_itens_tri"] = np.where(P.arr["it_n"] > 0, np.log(np.maximum(P.arr["it_n"], 1)), np.nan)


def placebo(P, pares, rel_alvo=-1, rel_base=-2, ycol="Yc", ncol="nC", B=9999, semente=0, margem=5.0):
    L = montar_linhas(P.ate, pares, rel_alvo, rel_base, ycol, ncol)
    if not len(L):
        return L, []
    out = []
    for g in (None, "adocao", "abandono"):
        r = inferencia.contraste(L, g, B=B, semente=semente, margem=margem)
        out.append({"grupo": g or "agregado", **r})
    s = inferencia.diferenca(L, "adocao", "abandono", B=B, semente=semente)
    out.append({"grupo": "simetria_adocao_menos_abandono", **s})
    return L, out


def regressao_media(P, pares, pop, ycol="Yc"):
    """Para cada evento: desvio da tratada em t−2 e t−1 em relação ao seu nível de formação, contra os controles."""
    key = pop.set_index(["u", "t0"])
    linhas = []
    for (ide, t0), g in pares.groupby(["id_evento", "t0"]):
        V = P.ate(int(t0))
        u = int(g.u_tratada.iat[0])
        y1, y2 = V.col(ycol, t0 - 1), V.col(ycol, t0 - 2)
        nivel_u = key.loc[(u, t0), "y_nivel"]
        nc = np.array([key.loc[(int(v), t0), "y_nivel"] for v in g.u_controle])
        w = g.peso.to_numpy()
        s = int(g.sinal_af.iat[0])
        linhas.append({"id_evento": ide, "t0": int(t0), "direcao": g.direcao.iat[0],
                       "gap_formacao": s * (nivel_u - np.nansum(w * nc) / np.sum(w[np.isfinite(nc)]) if np.isfinite(nc).any() else np.nan),
                       "desvio_t2_tratada": s * (y2[u] - nivel_u), "desvio_t1_tratada": s * (y1[u] - nivel_u),
                       "placebo_evento": s * ((y1[u] - y2[u]) - np.sum(w * (y1[g.u_controle.to_numpy()] - y2[g.u_controle.to_numpy()]))
                                              / np.sum(w))})
    d = pd.DataFrame(linhas)
    ok = d[["gap_formacao", "placebo_evento"]].dropna()
    res = {"eventos": int(len(d)), "corr_gap_formacao_placebo": float(ok.corr().iat[0, 1]) if len(ok) > 2 else None,
           "media_desvio_t2_tratada": float(d.desvio_t2_tratada.mean()), "media_desvio_t1_tratada": float(d.desvio_t1_tratada.mean()),
           "media_gap_formacao": float(d.gap_formacao.mean())}
    return d, res
