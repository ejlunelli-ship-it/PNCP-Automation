"""Etapa 4: conjuntos de risco por evento (Fase I; só a visão PainelPre(t0) e o regime em t0).

Para e = (u, t0, o → d), controles v:
 1. observados em t0 (com compras) e em regime inequívoco o em t0 (não fizeram a troca em t0);
 2. em regime inequívoco o em t0−1;
 3. histórico de modo compatível de t0−6 a t0−2 (só o ou sem compras) — a MESMA regra exigida da tratada;
 4. completude de preços pré-evento idêntica à da tratada (t−1, t−2 e >= 2 trimestres de formação);
 5. v ≠ u; CNPJ(v) ≠ CNPJ(u) (análise principal); mesma esfera (correspondência exata institucional).
Nada depois de t0 é consultado: um controle que muda de modo em t0+1 continua no conjunto de risco de t0 (a
mudança posterior é tratada como censura por horizonte na Fase II).
"""
import numpy as np
import pandas as pd

from . import construir_covariaveis as cv
from .construir_painel import A, AF, NAO_OBS


def populacao_t0(P, t0, origem, form, falsif, min_form, classes_top, eventos_t0, ycol="Yc"):
    """População de risco (tratadas + candidatas) de uma direção em t0, com covariáveis e completude."""
    pre = P.ate(t0)
    s_tm1 = pre.col("status", t0 - 1)
    s_t0 = pre.status_t0
    hist = pre.janela("status", form[0], falsif[0])          # t0−6 .. t0−2
    compat = np.all((hist == origem) | (hist == NAO_OBS), axis=1)
    base = (s_tm1 == origem) & compat
    destino = AF if origem == A else A
    trat_u = np.array(sorted(eventos_t0.u.astype(int)), dtype=int)
    cand = np.flatnonzero(base & (s_t0 == origem))
    idx = np.union1d(cand, trat_u)
    ok_c, n_form, ok_f = cv.completude(pre, idx, form, falsif, min_form, ycol)
    cov = cv.calcular(pre, idx, origem, form, falsif, classes_top, ycol)
    cov["completo"] = ok_c
    cov["n_formacao_com_preco"] = n_form
    cov["falsificacao_completa"] = ok_f
    cov["tratada"] = np.isin(idx, trat_u)
    cov["candidata"] = np.isin(idx, cand)
    cov["t0"] = t0
    # coerência: tratadas têm de estar no destino em t0 e na origem em t0−1
    assert (s_t0[trat_u] == destino).all() and (s_tm1[trat_u] == origem).all()
    return cov


def conjuntos(pop, eventos_dir, excluir_mesmo_cnpj=True, exato=("esfera",)):
    """Candidatos de cada evento: candidatas completas da mesma população (t0, direção), filtradas por CNPJ e esfera."""
    cand = pop[pop.candidata & pop.completo]
    linhas, por_evento = [], {}
    for e in eventos_dir.itertuples():
        t = pop[(pop.u == e.u) & (pop.t0 == e.t0) & pop.tratada].iloc[0]
        c = cand[(cand.t0 == e.t0) & (cand.u != e.u)]
        n0 = len(c)
        if excluir_mesmo_cnpj:
            c = c[c.cnpj != t.cnpj]
        n1 = len(c)
        for x in exato:
            c = c[c[x] == t[x]]
        por_evento[e.id_evento] = c.u.to_numpy()
        linhas.append({"id_evento": e.id_evento, "candidatas_mesmo_t0_origem": n0, "apos_excluir_mesmo_cnpj": n1,
                       "apos_exato_esfera": len(c), "tratada_completa": bool(t.completo)})
    return por_evento, pd.DataFrame(linhas)
