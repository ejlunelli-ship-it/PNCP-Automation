"""Análises complementares por etapa na base completa 1.9.1 (Aberto-Fechado 2023-04 a 2026-10; Fechado-Aberto).

Refaz, na base inteira e nos dois modos, os estudos que em 18/11/2026 só cobriam 4 meses de 2026
(analises/etapas_pdf_af_20261118/: regressao_etapas.py, testes_grupos.py, estratos de analisar.py) e acrescenta
a comparação Aberto-Fechado × Fechado-Aberto. A amostra é a mesma do analise_etapas.py (importa ler_bancos,
ligar_pncp e preparar; regra do mês = primeiro mês do resultado), sempre com as duas medidas principais
(todos os fornecedores; só fornecedores válidos).

1. Regressão (primeira diferença de 100·ln(preço) entre as etapas = FE de item; EP por UASG) com as 13
   sensibilidades de 18/11 (S1..S13) e efeitos marginais por tipo × sigilo × nº de licitantes.
2. Testes de médias por grupo (material × serviço; orçamento aberto × sigiloso; 6 comparações): t com EP por UASG
   (principal), Welch, Mann-Whitney, Holm, e diferença ajustada por nº de licitantes (FE 1..20, 21-30, 31+).
3. Heterogeneidade: médias com EP por UASG por ano, faixa de licitantes, tipo × sigilo, esfera, região, SRP e quintil
   do valor total estimado.
4. Comparação AF × FA (itens dos dois modos empilhados): desconto da 1ª etapa, desconto ao fim da disputa e
   desconto final em uma dummy FA; bruta, com controles (mês, faixa de licitantes, tipo, sigilo, ln valor) e com
   FE de UASG (só UASGs que usaram os dois modos). Associação, não efeito causal (o órgão escolhe o modo).

Uso (da pasta PNCP-Automation):
    python analises/etapas_completo_20261122/complementares.py --db dados/extracao/aberto-fechado_parser-1.9.1.db \
        --pncp-db ../dados/pncp.db --saida dados/analise_etapas/completo_20261122
Lê os bancos só para leitura. Saídas: <saida>/<modo>/complementares.{json,xlsx}, <saida>/comparacao_af_fa.{json,xlsx}.
"""
import argparse, json, os, sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
import analise_etapas as ae  # noqa: E402

ae.COLS += ", cnpj_fornecedor_lance_aceito"
REGIAO = {**dict.fromkeys(["AC", "AM", "AP", "PA", "RO", "RR", "TO"], "Norte"),
          **dict.fromkeys(["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"], "Nordeste"),
          **dict.fromkeys(["DF", "GO", "MS", "MT"], "Centro-Oeste"),
          **dict.fromkeys(["ES", "MG", "RJ", "SP"], "Sudeste"), **dict.fromkeys(["PR", "RS", "SC"], "Sul")}
ESFERA = {"F": "Federal", "E": "Estadual", "M": "Municipal", "D": "Distrital", "N": "Não informada"}


def compras_pncp(ids, pncp_db):
    """Esfera, UF e registro de preços (SRP) da compra no pncp.db (vazios na base de extração)."""
    st = os.stat(pncp_db)
    con = ae.sqlite3.connect(f"file:{Path(pncp_db).resolve().as_posix()}?mode=ro", uri=True)
    con.execute("create temp table alvo(id_compra text primary key)")
    con.executemany("insert into temp.alvo values (?)", [(i,) for i in sorted(set(ids))])
    c = pd.read_sql_query("select c.id_compra, c.esfera, c.uf, c.srp from temp.alvo a join compras c "
                          "on c.id_compra = a.id_compra", con)
    con.close()
    assert os.stat(pncp_db).st_mtime_ns == st.st_mtime_ns, "pncp.db mudou durante a leitura"
    return c.drop_duplicates("id_compra")


def _json(o):
    return o.item() if hasattr(o, "item") else str(o)


MEDIDAS = [("todos os fornecedores", ""), ("só fornecedores válidos", "_v")]


# ---------------------------------------------------------------- dados
def amostra(db, pncp_db, modo):
    e = ae.MODOS[modo]
    df = ae.ler_bancos([db], None, e)
    df = ae.ligar_pncp(df, pncp_db)
    df, funil = ae.preparar(df, e)
    s = df[df.na_amostra].copy()
    del df
    n0 = len(s)
    s = s.merge(compras_pncp(s.id_compra, pncp_db), on="id_compra", how="left")
    assert len(s) == n0
    s["esfera"] = s.esfera.map(ESFERA)
    s["srp"] = s.srp.map({0: "Sem registro de preços", 1: "Registro de preços"})
    s["lic"] = s.quantidade_fornecedores.astype(float)
    s["tipo"] = s.material_ou_servico.map({"M": "Material", "S": "Serviço"})
    s["orcamento"] = s.orcamento_sigiloso.map({0: "Aberto", 1: "Sigiloso"})
    s["servico"] = (s.material_ou_servico == "S").astype(float)
    s["sigiloso"] = s.orcamento_sigiloso.astype(float)
    s["ano"] = s.mes.str[:4]
    s["regiao"] = s.uf.map(REGIAO)
    s["faixa_lic"] = pd.cut(s.lic, [0, 1, 2, 5, 10, 1e9], labels=["1", "2", "3-5", "6-10", ">10"]).astype(str)
    s["faixa_lic_fina"] = pd.cut(s.lic, list(np.arange(0.5, 20.6, 1)) + [30.5, 1e9], labels=False)
    vt = s.valor_estimado_total.astype(float)
    s["ln_valor"] = np.log(vt.where(vt > 0))
    s["quintil_valor"] = pd.qcut(vt.where(vt > 0), 5, labels=["Q1", "Q2", "Q3", "Q4", "Q5"]).astype(str)
    s["fornecedor"] = s.cnpj_fornecedor_lance_aceito.where(s.cnpj_fornecedor_lance_aceito.fillna("") != "",
                                                           "sem_" + s.id_compra + "_" + s.item.astype(str))
    s["adjudicado"] = s.situacao_item.str.startswith("Adjudicado", na=False)
    return s, e, funil


def por_medida(s, e, suf):
    """Amostra da medida (todos / só válidos) com as variáveis da regressão e dos testes."""
    d = s if suf == "" else s[s.validos_ok]
    d = d.copy()
    p1 = d[e["c1"]] if suf == "" else d[e["c1v"]]
    p2 = d[e["c2"]] if suf == "" else d[e["c2v"]]
    ap = d.melhor_apos if suf == "" else d.apos_v
    d["y1"], d["y2"] = 100 * np.log(p1), 100 * np.log(ap)
    d["dy"] = d.y2 - d.y1                              # <= 0 por construção (mínimo)
    d["dpp"] = d["ganho_pp" + suf]
    d["melhorou"] = 100.0 * (d.dy < -1e-9)
    d["teve_2"] = 100.0 * (p2.notna() & (p2 > 0))
    d["d1"], d["dap"], d["grel"] = d[e["d1"] + suf], d["d_apos" + suf], d["ganho_rel" + suf]
    return d


# ---------------------------------------------------------------- estimação
def codigos(*cols):
    """Inteiros 0..G-1 para um grupo (ou o cruzamento de vários)."""
    if len(cols) == 1:
        return pd.factorize(pd.Series(cols[0]))[0]
    return pd.MultiIndex.from_arrays([pd.factorize(pd.Series(c))[0] for c in cols]).factorize()[0]


def vcov_cluster(X, u, A, idx, w):
    G = idx.max() + 1; n, k = X.shape
    S = np.zeros((G, k)); np.add.at(S, idx, X * (w * u)[:, None])
    return A @ (S.T @ S) @ A * (G / (G - 1)) * ((n - 1) / (n - k)), G


def mqo(y, X, nomes, grupos, w=None):
    w = np.ones(len(y)) if w is None else w
    A = np.linalg.pinv(X.T @ (X * w[:, None])); b = A @ X.T @ (w * y); u = y - X @ b
    if len(grupos) == 1:
        V, G = vcov_cluster(X, u, A, codigos(grupos[0]), w)
    else:                                                   # Cameron-Gelbach-Miller, duas dimensões
        V1, G1 = vcov_cluster(X, u, A, codigos(grupos[0]), w)
        V2, G2 = vcov_cluster(X, u, A, codigos(grupos[1]), w)
        V12, _ = vcov_cluster(X, u, A, codigos(*grupos), w)
        ev, evec = np.linalg.eigh(V1 + V2 - V12)
        V = evec @ np.diag(np.clip(ev, 0, None)) @ evec.T; G = min(G1, G2)
    return {"b": b, "V": V, "G": int(G), "n": len(y), "nomes": nomes}


def tabela(r):
    se = np.sqrt(np.diag(r["V"])); p = 2 * stats.t.sf(np.abs(r["b"] / se), r["G"] - 1)
    return pd.DataFrame({"coef": r["b"], "ep": se, "ic95_inf": r["b"] - 1.96 * se, "ic95_sup": r["b"] + 1.96 * se,
                         "p": p}, index=r["nomes"])


def wald(r, quais):
    if not quais:
        return {}
    i = [r["nomes"].index(q) for q in quais]; b = r["b"][i]; V = r["V"][np.ix_(i, i)]
    F = float(b @ np.linalg.lstsq(V, b, rcond=None)[0]) / len(i)
    return {"regressores": quais, "F": F, "gl": [len(i), r["G"] - 1], "p": float(stats.f.sf(F, len(i), r["G"] - 1))}


PRINC = ["ln_lic", "sigiloso", "servico"]


def matriz(d, mods, L, coef):
    cols, nomes = [], []
    for m in mods:
        if m == "faixa_lic":
            for f in ["1", "2", "3-5", ">10"]:              # base 6-10
                cols.append((d.faixa_lic == f).astype(float).to_numpy()); nomes.append(f"{L}_x_lic_{f}")
        else:
            cols.append(d[m].to_numpy(float)); nomes.append(f"{L}_x_{m}")
    cols.append(d.ln_valor.to_numpy(float)); nomes.append(f"{L}_x_ln_valor")
    for m in sorted(d.mes.unique())[1:]:
        cols.append((d.mes == m).astype(float).to_numpy()); nomes.append(f"{L}_x_mes_{m}")
    Z = np.column_stack(cols); mu = Z.mean(axis=0)
    keep = Z.std(axis=0) > 0
    nomes = [n for n, k in zip(nomes, keep) if k]
    return np.column_stack([np.ones(len(d)), (Z - mu)[:, keep]]), [coef] + nomes, mu[keep]


def ajusta(d, e, y="dy", mods=PRINC, w=None, grupos=("uasg",), fe_uasg=False):
    d = d.reset_index(drop=True)
    X, nomes, _ = matriz(d, mods, e["letra"], e["coef"])
    yv = d[y].to_numpy(float)
    if fe_uasg:                                             # FE de UASG × etapa = FE de UASG na diferença
        g = codigos(d.uasg.to_numpy())
        yv = yv - pd.Series(yv).groupby(g).transform("mean").to_numpy()
        X = X[:, 1:] - pd.DataFrame(X[:, 1:]).groupby(g).transform("mean").to_numpy(); nomes = nomes[1:]
        keep = np.abs(X).sum(axis=0) > 1e-9
        X = X[:, keep]; nomes = [n for n, k in zip(nomes, keep) if k]
    gr = tuple(d[c].to_numpy() for c in grupos)
    return mqo(yv, X, nomes, gr, None if w is None else d[w].to_numpy(float))


def efeitos_marginais(r, d, e):
    X, nomes, mu = matriz(d.reset_index(drop=True), PRINC, e["letra"], e["coef"])
    L, linhas = e["letra"], []
    for srv in [0, 1]:
        for sig in [0, 1]:
            for nl in [2, 5, 10, 20]:
                z = mu.copy()
                z[nomes.index(f"{L}_x_ln_lic") - 1] = np.log(nl); z[nomes.index(f"{L}_x_servico") - 1] = srv
                z[nomes.index(f"{L}_x_sigiloso") - 1] = sig
                a = np.concatenate([[1], z - mu]); est = float(a @ r["b"]); se = float(np.sqrt(a @ r["V"] @ a))
                linhas.append({"tipo": "Serviço" if srv else "Material", "orcamento": "Sigiloso" if sig else "Aberto",
                               "licitantes": nl, "dlog_x100": est, "ep": se, "ic95_inf": est - 1.96 * se,
                               "ic95_sup": est + 1.96 * se, "variacao_preco_%": 100 * (np.exp(est / 100) - 1)})
    return pd.DataFrame(linhas)


def regressoes(d, e, nome_medida):
    d = d[d.material_ou_servico.isin(["M", "S"]) & d.orcamento_sigiloso.isin([0, 1]) & (d.lic > 0)
          & d.ln_valor.notna()].reset_index(drop=True)
    d["ln_lic"] = np.log(d.lic)
    d["srv_x_sig"] = d.servico * d.sigiloso
    d["peso_compra"] = 1.0 / d.groupby("id_compra").item.transform("size")
    lo, hi = d.dy.quantile([0.01, 0.99])
    pc = d.groupby("id_compra").agg(dy=("dy", "mean"), ln_lic=("ln_lic", "mean"), sigiloso=("sigiloso", "mean"),
                                    servico=("servico", "mean"), ln_valor=("ln_valor", "mean"),
                                    uasg=("uasg", "first"), mes=("mes", "first")).reset_index()
    rot = e["rot2"]
    esp = {
        "P  principal: 100·ln(preço), EP por UASG": lambda: ajusta(d, e),
        "S1 ganho em p.p. do estimado": lambda: ajusta(d, e, y="dpp"),
        "S2 licitantes em faixas (base 6-10)": lambda: ajusta(d, e, mods=["faixa_lic", "sigiloso", "servico"]),
        "S3 + serviço × sigiloso": lambda: ajusta(d, e, mods=PRINC + ["srv_x_sig"]),
        "S4 EP por compra": lambda: ajusta(d, e, grupos=("id_compra",)),
        "S5 EP duas dimensões UASG + fornecedor": lambda: ajusta(d, e, grupos=("uasg", "fornecedor")),
        "S6 peso igual por compra": lambda: ajusta(d, e, w="peso_compra"),
        "S7 FE UASG × etapa (dentro da UASG)": lambda: ajusta(d, e, fe_uasg=True),
        f"S8 parte extensiva: P(a {rot} melhora), MLP": lambda: ajusta(d, e, y="melhorou"),
        "S9 parte intensiva: só itens que melhoraram": lambda: ajusta(d[d.melhorou > 0], e),
        "S10 só adjudicados": lambda: ajusta(d[d.adjudicado], e),
        "S11 corte 1%/99% de dy": lambda: ajusta(d[d.dy.between(lo, hi)], e),
        "S12 agregado por compra (médias)": lambda: ajusta(pc, e),
        "S13 sem itens de 1 licitante": lambda: ajusta(d[d.lic >= 2], e),
    }
    L = e["letra"]
    linhas, walds, em = [], [], None
    for nome, f in esp.items():
        r = f(); tb = tabela(r)
        inter = [n for n in r["nomes"] if n.startswith(f"{L}_x_") and
                 (n[len(L) + 3:] in PRINC + ["srv_x_sig"] or n.startswith(f"{L}_x_lic_"))]
        walds.append({"medida": nome_medida, "especificacao": nome, **wald(r, inter)})
        for reg, row in tb.iterrows():
            linhas.append({"medida": nome_medida, "especificacao": nome, "regressor": reg, **row.to_dict(),
                           "n": r["n"], "grupos": r["G"]})
        if nome.startswith("P "):
            em = efeitos_marginais(r, d, e).assign(medida=nome_medida)
        print(f"  {nome_medida} | {nome}: n={r['n']}", flush=True)
    return linhas, walds, em


# ---------------------------------------------------------------- testes de médias
def t_cluster(y, g, cl, Z=None):
    X = np.column_stack([np.ones(len(y)), g] + ([] if Z is None else [Z]))
    A = np.linalg.pinv(X.T @ X); b = A @ X.T @ y; u = y - X @ b
    V, G = vcov_cluster(X, u, A, codigos(cl), np.ones(len(y)))
    se = np.sqrt(V[1, 1])
    return b[1], se, 2 * stats.t.sf(abs(b[1] / se), G - 1)


def holm(p):
    p = np.asarray(p, float); o = np.argsort(p); m = len(p); adj = np.empty(m)
    adj[o] = np.minimum(1, np.maximum.accumulate((m - np.arange(m)) * p[o]))
    return adj


def testes_grupos(d, e, nome_medida):
    r1, r2 = e["rot1"], e["rot2"]
    VARS = {"d1": f"Desconto etapa {r1} (%)", "dap": f"Desconto após a {r2} (%)", "dpp": f"Ganho da {r2} (p.p.)",
            "grel": f"Ganho relativo (% do melhor {r1[:-1]}o)", "d_final": "Desconto final (%)",
            "teve_2": f"Teve lance na etapa {r2} (%)", "melhorou": f"A {r2} melhorou o preço (%)",
            "lic": "Número de licitantes"}
    d = d[d.tipo.notna() & d.orcamento.notna()]
    comps = [("Material × Serviço (todos)", None, "tipo", "Material", "Serviço"),
             ("Aberto × Sigiloso (todos)", None, "orcamento", "Aberto", "Sigiloso"),
             ("Material: aberto × sigiloso", ("tipo", "Material"), "orcamento", "Aberto", "Sigiloso"),
             ("Serviço: aberto × sigiloso", ("tipo", "Serviço"), "orcamento", "Aberto", "Sigiloso"),
             ("Orç. aberto: material × serviço", ("orcamento", "Aberto"), "tipo", "Material", "Serviço"),
             ("Orç. sigiloso: material × serviço", ("orcamento", "Sigiloso"), "tipo", "Material", "Serviço")]
    linhas = []
    for nome, filt, col, a, b in comps:
        s = d if filt is None else d[d[filt[0]] == filt[1]]
        for v, rot in VARS.items():
            x = s[list(dict.fromkeys([v, col, "uasg", "faixa_lic_fina", "lic"]))].dropna()
            x = x[x.lic > 0]
            ya, yb = x.loc[x[col] == a, v], x.loc[x[col] == b, v]
            yv, g, cl = x[v].to_numpy(float), (x[col] == b).to_numpy(float), x.uasg.to_numpy()
            dif, se, pc = t_cluster(yv, g, cl)
            lin = {"medida": nome_medida, "comparacao": nome, "variavel": rot, "grupo_A": a, "grupo_B": b,
                   "n_A": len(ya), "n_B": len(yb), "media_A": ya.mean(), "media_B": yb.mean(),
                   "mediana_A": ya.median(), "mediana_B": yb.median(), "dif_B_menos_A": dif, "ep_cluster_uasg": se,
                   "ic95_inf": dif - 1.96 * se, "ic95_sup": dif + 1.96 * se, "p_cluster_uasg": pc,
                   "p_welch": stats.ttest_ind(yb, ya, equal_var=False).pvalue,
                   "p_mann_whitney": stats.mannwhitneyu(yb, ya).pvalue}
            if v != "lic":
                fe = pd.get_dummies(x.faixa_lic_fina.astype(int)).to_numpy(float)[:, 1:]
                da, sa, pa = t_cluster(yv, g, cl, fe)
                dl, _, pl = t_cluster(yv, g, cl, np.log(x.lic.to_numpy(float))[:, None])
                lin.update({"dif_ajust_licitantes": da, "ep_ajust": sa, "ic95_inf_ajust": da - 1.96 * sa,
                            "ic95_sup_ajust": da + 1.96 * sa, "p_ajust": pa, "dif_ajust_log_licitantes": dl,
                            "p_ajust_log": pl})
            linhas.append(lin)
    t = pd.DataFrame(linhas)
    m0 = t.variavel != VARS["lic"]
    t.loc[m0, "p_cluster_holm"] = holm(t.loc[m0, "p_cluster_uasg"])
    t.loc[m0, "p_ajust_holm"] = holm(t.loc[m0, "p_ajust"])
    return t


# ---------------------------------------------------------------- heterogeneidade
def media_ep(y, cl):
    m = ~np.isnan(y); y, cl = y[m], cl[m]
    if len(y) < 2:
        return np.nan, np.nan
    idx = codigos(cl); G = idx.max() + 1
    u = np.bincount(idx, weights=y - y.mean(), minlength=G)
    return float(y.mean()), float(np.sqrt((u ** 2).sum() * G / (G - 1)) / len(y))


def heterogeneidade(d, e, nome_medida):
    linhas = []
    for dim in ["ano", "faixa_lic", "tipo_orcamento", "esfera", "regiao", "srp", "quintil_valor"]:
        x = d.assign(tipo_orcamento=d.tipo + " / " + d.orcamento) if dim == "tipo_orcamento" else d
        for k, g in x.groupby(dim):
            if k in ("nan", "") or pd.isna(k):
                continue
            lin = {"medida": nome_medida, "dimensao": dim, "grupo": k, "itens": len(g),
                   "compras": int(g.id_compra.nunique()), "uasgs": int(g.uasg.nunique()), "lic_media": g.lic.mean()}
            for v, rot in [("d1", e["rot1"]), ("dap", e["apos"]), ("dpp", "ganho_pp"), ("grel", "ganho_rel"),
                           ("melhorou", "prop_melhorou"), ("d_final", "final")]:
                mu, se = media_ep(g[v].to_numpy(float), g.uasg.to_numpy())
                lin[rot] = mu; lin[rot + "_ep"] = se
            linhas.append(lin)
    return pd.DataFrame(linhas)


# ---------------------------------------------------------------- comparação AF × FA
def comparacao(af, fa):
    cols = ["d1", "dap", "d_final", "dpp", "uasg", "id_compra", "mes", "lic", "faixa_lic_fina", "servico", "sigiloso",
            "ln_valor", "material_ou_servico", "orcamento_sigiloso"]
    x = pd.concat([af[cols].assign(fa=0.0), fa[cols].assign(fa=1.0)], ignore_index=True)
    x = x[x.material_ou_servico.isin(["M", "S"]) & x.orcamento_sigiloso.isin([0, 1]) & (x.lic > 0)
          & x.ln_valor.notna()].reset_index(drop=True)
    uasg_ambos = x.groupby("uasg").fa.agg(["min", "max"]).pipe(lambda t: t.index[(t["min"] == 0) & (t["max"] == 1)])
    linhas = []
    Y = {"d1": "Desconto da 1ª etapa (AF: aberta; FA: fechada)", "dap": "Desconto ao fim da disputa (mín. das etapas)",
         "d_final": "Desconto final (aceito/negociado)", "dpp": "Ganho da 2ª etapa (p.p.)", "lic": "Número de licitantes"}
    for v, rot in Y.items():
        for esp in ["bruta", "controles", "FE de UASG (UASGs com os dois modos)"]:
            z = x[x[v].notna()]
            if esp.startswith("FE"):
                z = z[z.uasg.isin(uasg_ambos)]
            z = z.reset_index(drop=True)
            Xc = [z.fa.to_numpy()]
            nomes = ["FA"]
            if esp != "bruta":
                ctrl = [pd.get_dummies(z.mes).to_numpy(float)[:, 1:], z[["servico", "sigiloso", "ln_valor"]].to_numpy(float)]
                if v != "lic":
                    ctrl.append(pd.get_dummies(z.faixa_lic_fina.astype(int)).to_numpy(float)[:, 1:])
                Xc += [np.column_stack(ctrl)]
            X = np.column_stack(Xc); y = z[v].to_numpy(float)
            if esp.startswith("FE"):
                g = codigos(z.uasg.to_numpy())
                y = y - pd.Series(y).groupby(g).transform("mean").to_numpy()
                X = X - pd.DataFrame(X).groupby(g).transform("mean").to_numpy()
                keep = np.abs(X).sum(axis=0) > 1e-9; keep[0] = True; X = X[:, keep]
            else:
                X = np.column_stack([np.ones(len(y)), X]); nomes = ["const"] + nomes
            r = mqo(y, X, nomes + [f"c{i}" for i in range(X.shape[1] - len(nomes))], (z.uasg.to_numpy(),))
            tb = tabela(r).loc["FA"]
            linhas.append({"variavel": rot, "especificacao": esp, "media_AF": z.loc[z.fa == 0, v].mean(),
                           "media_FA": z.loc[z.fa == 1, v].mean(), "n_AF": int((z.fa == 0).sum()),
                           "n_FA": int((z.fa == 1).sum()), "uasgs": int(z.uasg.nunique()), "dif_FA_menos_AF": tb.coef,
                           "ep": tb.ep, "ic95_inf": tb.ic95_inf, "ic95_sup": tb.ic95_sup, "p": tb.p})
    t = pd.DataFrame(linhas)
    return t, {"uasgs_com_os_dois_modos": int(len(uasg_ambos)),
               "itens_AF_nessas_uasgs": int(x[(x.fa == 0) & x.uasg.isin(uasg_ambos)].shape[0]),
               "itens_FA_nessas_uasgs": int(x[(x.fa == 1) & x.uasg.isin(uasg_ambos)].shape[0])}


# ---------------------------------------------------------------- execução
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db", type=Path, required=True)
    ap.add_argument("--pncp-db", type=Path, required=True)
    ap.add_argument("--saida", type=Path, required=True)
    a = ap.parse_args(argv)
    st = {p: os.stat(p) for p in [a.db, a.pncp_db]}
    guardados = {}
    for modo in ["aberto-fechado", "fechado-aberto"]:
        print(f"== {modo}", flush=True)
        s, e, funil = amostra(a.db, a.pncp_db, modo)
        T = {"regressao": [], "wald": [], "efeitos_marginais": [], "testes_grupos": [], "heterogeneidade": []}
        for nome, suf in MEDIDAS:
            d = por_medida(s, e, suf)
            lin, wl, em = regressoes(d, e, nome)
            T["regressao"] += lin; T["wald"] += wl; T["efeitos_marginais"].append(em)
            T["testes_grupos"].append(testes_grupos(d, e, nome)); print(f"  {nome} | testes ok", flush=True)
            T["heterogeneidade"].append(heterogeneidade(d, e, nome)); print(f"  {nome} | heterogeneidade ok", flush=True)
            if suf == "":
                guardados[modo] = d
        T = {k: pd.DataFrame(v) if isinstance(v[0], dict) else pd.concat(v, ignore_index=True) for k, v in T.items()}
        out = a.saida / modo; out.mkdir(parents=True, exist_ok=True)
        R = {"modo": modo, "funil": funil, "itens_amostra": len(s), "compras": int(s.id_compra.nunique()),
             "uasgs": int(s.uasg.nunique()), **{k: t.to_dict("records") for k, t in T.items()}}
        (out / "complementares.json").write_text(json.dumps(R, ensure_ascii=False, indent=1, default=_json), encoding="utf-8")
        with pd.ExcelWriter(out / "complementares.xlsx") as xw:
            for k, t in T.items():
                t.to_excel(xw, sheet_name=k[:31], index=False)
        del s
    t, meta = comparacao(guardados["aberto-fechado"], guardados["fechado-aberto"])
    (a.saida / "comparacao_af_fa.json").write_text(
        json.dumps({**meta, "estimativas": t.to_dict("records")}, ensure_ascii=False, indent=1, default=_json), encoding="utf-8")
    t.to_excel(a.saida / "comparacao_af_fa.xlsx", index=False)
    for p, s0 in st.items():
        s1 = os.stat(p)
        assert (s1.st_size, s1.st_mtime_ns) == (s0.st_size, s0.st_mtime_ns), f"{p} mudou"
    print("FIM ok", flush=True)


if __name__ == "__main__":
    main()
