"""Etapa 15 (Fase II): composição dos produtos.

C1  índice médio das compras observadas (desfecho principal; admite mudança de composição — NÃO é cesta fixa).
C2  cesta de classes CATMAT fixada com dados PRÉ (t0−6..t0−1) da própria UASG: em t0−1 e t0+h, média do índice por
    classe reponderada pelas participações pré, só nas classes observadas nos dois períodos e só se cobrirem >= 50%
    do peso pré. Sem cobertura: não estimável (nada imputado).
C3  mesmo produto S1 (CATMAT × unidade): produtos com índice em t0−2..t0−1 E em t0+h; ΔY = média, entre produtos
    comuns, de (Ȳ_p,pós − Ȳ_p,pré). Sensibilidade condicional à recompra (seleção registrada), não efeito total.
Auditoria: sobreposição, Jaccard, produtos que entram/saem, distância entre distribuições de classes, escala e
frequência, para tratadas e controles pareados.
"""
import numpy as np
import pandas as pd


def _indice_produto(P):
    it = P.longo["itens_y"]
    return it.groupby(["u", "t", "produto"]).y_A1.mean(), it.groupby(["u", "t", "classe"]).y_A1.agg(["mean", "size"])


def delta_c3(prod, u, t0, h, pre=(-2, -1)):
    try:
        post = prod.loc[(u, t0 + h)]
    except KeyError:
        return np.nan, 0
    pre_v = []
    for r in range(pre[0], pre[1] + 1):
        try:
            pre_v.append(prod.loc[(u, t0 + r)])
        except KeyError:
            pass
    if not pre_v:
        return np.nan, 0
    pm = pd.concat(pre_v).groupby(level=0).mean()
    com = post.index.intersection(pm.index)
    if not len(com):
        return np.nan, 0
    return float((post.loc[com] - pm.loc[com]).mean()), len(com)


def delta_c2(cls, P, u, t0, h, cobertura_min=0.5):
    it = P.longo["itens_y"]
    pre = it[(it.u == u) & (it.t >= t0 - 6) & (it.t <= t0 - 1)]
    if not len(pre):
        return np.nan, 0.0
    pi = pre.groupby("classe").size()
    pi = pi / pi.sum()
    try:
        b = cls.loc[(u, t0 - 1)]["mean"]
        a = cls.loc[(u, t0 + h)]["mean"]
    except KeyError:
        return np.nan, 0.0
    K = pi.index.intersection(b.index).intersection(a.index)
    cob = float(pi.loc[K].sum()) if len(K) else 0.0
    if cob < cobertura_min:
        return np.nan, cob
    w = pi.loc[K] / pi.loc[K].sum()
    return float((w * (a.loc[K] - b.loc[K])).sum()), cob


def montar_linhas_comp(P, pares, h, tipo, cobertura_min=0.5):
    prod, cls = _indice_produto(P)
    linhas, perdas = [], {"eventos": 0, "tratada_sem_suporte": 0, "sem_controle_com_suporte": 0}
    for ide, ge in pares.groupby("id_evento"):
        perdas["eventos"] += 1
        r0 = ge.iloc[0]
        t0, u, s = int(r0.t0), int(r0.u_tratada), int(r0.sinal_af)
        f = (lambda v: delta_c3(prod, v, t0, h)) if tipo == "C3" else (lambda v: delta_c2(cls, P, v, t0, h, cobertura_min))
        dT, sup = f(u)
        if not np.isfinite(dT):
            perdas["tratada_sem_suporte"] += 1
            continue
        ctr = [(r, f(int(r.u_controle))) for r in ge.itertuples()]
        ctr = [(r, d) for r, (d, _) in ctr if np.isfinite(d)]
        if not ctr:
            perdas["sem_controle_com_suporte"] += 1
            continue
        grupo = "adocao" if r0.direcao == "A->AF" else "abandono"
        cel = f"{r0.direcao}|{t0}|{h}"
        linhas.append({"id_evento": ide, "papel": "T", "u": u, "uasg": r0.uasg_tratada, "cnpj": r0.cnpj_tratada, "z": s * dT,
                       "w": 1.0, "a": 1.0, "grupo": grupo, "celula": cel, "t0": t0, "direcao": r0.direcao, "suporte": sup})
        for r, d in ctr:
            linhas.append({"id_evento": ide, "papel": "C", "u": int(r.u_controle), "uasg": r.uasg_controle, "cnpj": r.cnpj_controle,
                           "z": s * d, "w": 1.0, "a": np.nan, "grupo": grupo, "celula": cel, "t0": t0, "direcao": r0.direcao})
    return pd.DataFrame(linhas), perdas


def auditoria(P, pares):
    pl = P.longo["produtos_licitados"]
    cl = P.longo["classes"]
    it = P.longo["itens_y"]
    psets = pl.groupby(["u", "t"]).produto.apply(set)
    csh = cl.groupby(["u", "t", "classe"]).n.sum()
    nI = P.arr["it_n"]
    nC = P.arr["n_compras"]

    def medidas(u, t0):
        pre = set().union(*[psets.get((u, t), set()) for t in range(t0 - 6, t0)])
        pos = psets.get((u, t0), set())
        itp = it[(it.u == u) & (it.t == t0)]
        sob = float(itp.produto.isin(pre).mean()) if len(itp) else np.nan
        jac = len(pre & pos) / len(pre | pos) if (pre | pos) else np.nan
        def dist(ts):
            parts = [csh.loc[(u, t)] for t in ts if (u, t) in csh.index.droplevel(2)]
            if not parts:
                return None
            s = pd.concat(parts).groupby(level=0).sum()
            return s / s.sum()
        d0, d1 = dist(range(t0 - 6, t0)), dist([t0])
        tvd = 0.5 * float(d0.sub(d1, fill_value=0).abs().sum()) if d0 is not None and d1 is not None else np.nan
        j0 = P.j(t0)
        pre_i = nI[u, j0 - 6:j0]
        pre_c = nC[u, j0 - 6:j0]
        return {"sobreposicao_itens_pos_com_produto_pre": sob, "jaccard_produtos": jac, "produtos_entram": len(pos - pre),
                "produtos_saem": len(pre - pos), "produtos_comuns": len(pre & pos), "tvd_classes": tvd,
                "dlog_itens": float(np.log1p(nI[u, j0]) - np.log1p(pre_i.mean())),
                "dlog_compras": float(np.log1p(nC[u, j0]) - np.log1p(pre_c.mean())),
                "c3_produto_comum_t0": bool(len(itp) and itp.produto.isin(
                    set(it[(it.u == u) & it.t.isin([t0 - 2, t0 - 1])].produto)).any())}
    linhas = []
    for ide, ge in pares.groupby("id_evento"):
        r0 = ge.iloc[0]
        t0 = int(r0.t0)
        mt = medidas(int(r0.u_tratada), t0)
        mc = pd.DataFrame([medidas(int(v), t0) for v in ge.u_controle]).astype(float)
        w = ge.peso.to_numpy()
        lin = {"id_evento": ide, "t0": t0, "direcao": r0.direcao}
        for k, v in mt.items():
            lin[f"{k}_tratada"] = float(v)
            x = mc[k].to_numpy()
            ok = np.isfinite(x)
            lin[f"{k}_controles"] = float(np.sum(w[ok] * x[ok]) / np.sum(w[ok])) if ok.any() else np.nan
        linhas.append(lin)
    return pd.DataFrame(linhas)
