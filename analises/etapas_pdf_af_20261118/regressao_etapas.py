"""Regressão empilhada: duas observações por item (melhor preço ao fim da etapa aberta e após a fechada).

Modelo:  y_ie = a_i + b*F_e + g'(F_e x Z_i) + e_ie,   e in {aberta, fechada}, F = 1 na observação "após a fechada".
  - a_i: efeito fixo de item (mesmo objeto, mesma disputa). Com T = 2 é idêntico à primeira diferença:
    b e g = MQO de dy_i = y_i,fechada - y_i,aberta em (1, Z_i). Estima-se pelas duas formas (conferência).
  - Z centrado na média da amostra: b = variação média entre etapas; g = quanto cada fator modifica o ganho.
  - y principal = 100 x ln(preço unitário)  (o ln do estimado é absorvido pelo FE de item);
    secundário = desconto em p.p. do estimado.
  - EP agrupado por UASG (CR1; FE de item aninhado nos grupos, logo fora da contagem de graus de liberdade).
Sensibilidades: ver ESPECIFICACOES. Saídas: regressao_etapas.json, regressao_etapas.xlsx.
"""
import json, os, sqlite3
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

AQUI = Path(__file__).resolve().parent
EXTR = AQUI.parents[1] / "PNCP-Automation" / "dados" / "extracao" / "aberto-fechado_2026-08.db"


# ---------------------------------------------------------------- dados
def dados():
    d = pd.read_csv(AQUI / "por_item.csv.gz", dtype={"id_compra": str, "uasg": str, "numero_compra": str})
    d = d[d.na_amostra].copy()
    lig = pd.read_csv(AQUI / "ligacao_pncp.csv.gz", dtype={"id_compra": str})
    lig = lig[lig.n_registros == 1][["id_compra", "item", "material_ou_servico", "orcamento_sigiloso"]]
    d = d.merge(lig, on=["id_compra", "item"], how="inner")
    d = d[d.material_ou_servico.isin(["M", "S"]) & d.orcamento_sigiloso.isin([0, 1])]
    st = os.stat(EXTR)
    con = sqlite3.connect(f"file:{EXTR.as_posix()}?mode=ro", uri=True)
    ex = pd.read_sql_query("select uasg, numero_compra, item, arquivo_origem, valor_estimado_total, "
                           "cnpj_fornecedor_lance_aceito as cnpj from itens where status_extracao = 'OK'", con)
    con.close()
    assert os.stat(EXTR).st_mtime_ns == st.st_mtime_ns
    ex["id_compra"] = ex.arquivo_origem.str.extract(r"-(\d{17})-item-")[0]
    ex = ex.drop(columns=["arquivo_origem", "uasg", "numero_compra"]).drop_duplicates(["id_compra", "item"])
    n0 = len(d)
    d = d.merge(ex, on=["id_compra", "item"], how="left", validate="one_to_one")
    assert len(d) == n0 and d.valor_estimado_total.notna().all()
    d["servico"] = (d.material_ou_servico == "S").astype(float)
    d["sigiloso"] = d.orcamento_sigiloso.astype(float)
    d["lic"] = d.quantidade_fornecedores.astype(float)
    d["ln_lic"] = np.log(d.lic)
    d["ln_valor"] = np.log(d.valor_estimado_total.astype(float))
    d["y_ab"] = 100 * np.log(d.melhor_lance_modo_aberto)
    d["y_fe"] = 100 * np.log(d.melhor_apos)
    d["dy"] = d.y_fe - d.y_ab                                   # <= 0 por construção (mínimo)
    d["dpp"] = d.d_apos - d.d_aberto                            # ganho em p.p. do estimado (>= 0)
    d["melhorou"] = 100.0 * (d.dy < -1e-9)
    d["fornecedor"] = d.cnpj.where(d.cnpj.notna() & (d.cnpj != ""), "sem_" + d.id_compra + "_" + d.item.astype(str))
    d["adjudicado"] = d.situacao_item.str.startswith("Adjudicado", na=False)
    d["faixa_lic"] = pd.cut(d.lic, [0, 1, 2, 5, 10, 1e9], labels=["1", "2", "3-5", "6-10", ">10"])
    return d.reset_index(drop=True)


# ---------------------------------------------------------------- estimação
def vcov_cluster(X, u, A, g, w):
    """CR1 'sanduíche' para MQO ponderado; A = (X'WX)^-1."""
    cod, idx = np.unique(g, return_inverse=True); G = len(cod); n, k = X.shape
    S = np.zeros((G, k)); np.add.at(S, idx, X * (w * u)[:, None])
    return A @ (S.T @ S) @ A * (G / (G - 1)) * ((n - 1) / (n - k)), G


def mqo(y, X, w=None, grupos=(), nomes=None):
    w = np.ones(len(y)) if w is None else w
    A = np.linalg.inv(X.T @ (X * w[:, None])); b = A @ X.T @ (w * y); u = y - X @ b
    if len(grupos) == 1:
        V, G = vcov_cluster(X, u, A, grupos[0], w)
    else:                                                       # Cameron-Gelbach-Miller, duas dimensões
        g1, g2 = grupos
        V1, G1 = vcov_cluster(X, u, A, g1, w); V2, G2 = vcov_cluster(X, u, A, g2, w)
        V12, _ = vcov_cluster(X, u, A, np.char.add(np.char.add(g1.astype(str), "|"), g2.astype(str)), w)
        V = V1 + V2 - V12
        ev, evec = np.linalg.eigh(V)                            # garante semidefinida positiva
        V = evec @ np.diag(np.clip(ev, 0, None)) @ evec.T; G = min(G1, G2)
    return {"b": b, "V": V, "G": G, "n": len(y), "nomes": nomes}


def tabela(r):
    se = np.sqrt(np.diag(r["V"])); t = r["b"] / se; p = 2 * stats.t.sf(np.abs(t), r["G"] - 1)
    return pd.DataFrame({"coef": r["b"], "ep": se, "ic95_inf": r["b"] - 1.96 * se, "ic95_sup": r["b"] + 1.96 * se,
                         "p": p}, index=r["nomes"])


def wald(r, quais):
    i = [r["nomes"].index(q) for q in quais]; b = r["b"][i]; V = r["V"][np.ix_(i, i)]
    F = float(b @ np.linalg.solve(V, b)) / len(i)
    return {"regressores": quais, "F": F, "gl": [len(i), r["G"] - 1], "p": float(stats.f.sf(F, len(i), r["G"] - 1))}


def matriz(d, mods, ctrl_mes=True, ctrl_valor=True, centro=None):
    """Colunas de F x Z (centradas), na forma de primeira diferença: [1, Z - média]."""
    cols, nomes = [], []
    for m in mods:
        if m == "faixa_lic":
            for f in ["1", "2", "3-5", ">10"]:                  # base 6-10
                cols.append((d.faixa_lic == f).astype(float).to_numpy()); nomes.append(f"F_x_lic_{f}")
        else:
            cols.append(d[m].to_numpy(float)); nomes.append(f"F_x_{m}")
    if ctrl_valor:
        cols.append(d.ln_valor.to_numpy()); nomes.append("F_x_ln_valor")
    if ctrl_mes:
        for m in sorted(d.mes.unique())[1:]:
            cols.append((d.mes == m).astype(float).to_numpy()); nomes.append(f"F_x_mes_{m}")
    Z = np.column_stack(cols)
    mu = Z.mean(axis=0) if centro is None else centro
    return np.column_stack([np.ones(len(d)), Z - mu]), ["F (etapa fechada)"] + nomes, mu


PRINC = ["ln_lic", "sigiloso", "servico"]


def ajusta(d, y="dy", mods=PRINC, w=None, grupos=("uasg",), ctrl_mes=True, fe_uasg=False):
    X, nomes, _ = matriz(d, mods, ctrl_mes)
    yv = d[y].to_numpy(float)
    if fe_uasg:                                                 # FE de UASG x etapa = FE de UASG na diferença
        g = d.uasg.to_numpy()
        yv = yv - pd.Series(yv).groupby(g).transform("mean").to_numpy()
        Xd = pd.DataFrame(X[:, 1:]).groupby(g).transform("mean").to_numpy()
        X = X[:, 1:] - Xd; nomes = nomes[1:]
        keep = np.abs(X).sum(axis=0) > 1e-9                     # remove colunas sem variação dentro da UASG
        X = X[:, keep]; nomes = [n for n, k in zip(nomes, keep) if k]
    gr = tuple(d[c].to_numpy() for c in grupos)
    return mqo(yv, X, None if w is None else d[w].to_numpy(float), gr, nomes)


def empilhado(d, mods=PRINC):
    """Forma literal: 2 linhas por item, FE de item por transformação within. Conferência da equivalência."""
    X1, nomes, _ = matriz(d, mods)
    n = len(d); Z = X1                                          # colunas: 1 (F) e Z centrado
    # linha aberta: F = 0 ; linha fechada: F = 1. Regressores F*Z. Within: subtrai a média do item (F*Z)/2.
    Xa = -0.5 * Z; Xf = 0.5 * Z
    ya = d.y_ab.to_numpy(); yf = d.y_fe.to_numpy(); ym = (ya + yf) / 2
    Y = np.concatenate([ya - ym, yf - ym]); X = np.vstack([Xa, Xf])
    g = np.concatenate([d.uasg.to_numpy()] * 2)
    A = np.linalg.inv(X.T @ X); b = A @ X.T @ Y; u = Y - X @ b
    cod, idx = np.unique(g, return_inverse=True); G = len(cod); k = X.shape[1]; N = len(Y)
    S = np.zeros((G, k)); np.add.at(S, idx, X * u[:, None])
    # FE de item aninhado em UASG: não entra em k (xtreg). A versão "areg" incluiria n FE e inflaria o EP.
    V = A @ (S.T @ S) @ A * (G / (G - 1)) * ((N - 1) / (N - k))
    V_areg = V * (N - k) / (N - k - n)
    return {"b": b, "V": V, "G": G, "n": N, "nomes": nomes}, np.sqrt(np.diag(V_areg))


def efeitos_marginais(r, d, mu_nomes):
    """Ganho previsto (log-pontos e %) por tipo x sigilo x nº de licitantes, demais em média."""
    X, nomes, mu = matriz(d, PRINC)
    linhas = []
    for srv in [0, 1]:
        for sig in [0, 1]:
            for L in [2, 5, 10, 20]:
                z = mu.copy()
                z[nomes.index("F_x_ln_lic") - 1] = np.log(L); z[nomes.index("F_x_servico") - 1] = srv
                z[nomes.index("F_x_sigiloso") - 1] = sig
                a = np.concatenate([[1], z - mu]); e = float(a @ r["b"]); se = float(np.sqrt(a @ r["V"] @ a))
                linhas.append({"tipo": "Serviço" if srv else "Material", "orcamento": "Sigiloso" if sig else "Aberto",
                               "licitantes": L, "dlog_x100": e, "ep": se, "ic95_inf": e - 1.96 * se,
                               "ic95_sup": e + 1.96 * se, "variacao_preco_%": 100 * (np.exp(e / 100) - 1)})
    return pd.DataFrame(linhas)


# ---------------------------------------------------------------- execução
def main():
    d = dados()
    d["peso_pregao"] = 1.0 / d.groupby("pasta").item.transform("size")
    R, T = {"n_itens": len(d), "n_pregoes": int(d.pasta.nunique()), "n_uasgs": int(d.uasg.nunique()),
            "n_fornecedores": int(d.fornecedor.nunique())}, {}

    # conferência: empilhado (within) == primeira diferença
    emp, se_areg = empilhado(d)
    fd = ajusta(d)
    R["equivalencia"] = {"max_dif_coef": float(np.abs(emp["b"] - fd["b"]).max()),
                         "ep_empilhado": np.sqrt(np.diag(emp["V"])).tolist(), "ep_primeira_dif": np.sqrt(np.diag(fd["V"])).tolist(),
                         "ep_areg_inflado": se_areg.tolist(), "n_obs_empilhado": emp["n"]}

    lo, hi = d.dy.quantile([0.01, 0.99])
    pc = d.groupby("pasta").agg(dy=("dy", "mean"), ln_lic=("ln_lic", "mean"), sigiloso=("sigiloso", "mean"),
                                servico=("servico", "mean"), ln_valor=("ln_valor", "mean"), uasg=("uasg", "first"),
                                mes=("mes", "first")).reset_index()
    d["srv_x_sig"] = d.servico * d.sigiloso
    ESPECIFICACOES = {
        "P  principal: 100·ln(preço), EP por UASG": lambda: ajusta(d),
        "S1 desconto em p.p. do estimado": lambda: ajusta(d, y="dpp"),
        "S2 licitantes em faixas (base 6-10)": lambda: ajusta(d, mods=["faixa_lic", "sigiloso", "servico"]),
        "S3 + serviço × sigiloso": lambda: ajusta(d, mods=PRINC + ["srv_x_sig"]),
        "S4 EP por pregão": lambda: ajusta(d, grupos=("pasta",)),
        "S5 EP duas dimensões UASG + fornecedor": lambda: ajusta(d, grupos=("uasg", "fornecedor")),
        "S6 peso igual por pregão": lambda: ajusta(d, w="peso_pregao"),
        "S7 FE UASG × etapa (identificação dentro da UASG)": lambda: ajusta(d, fe_uasg=True),
        "S8 parte extensiva: P(fechada melhora), MLP": lambda: ajusta(d, y="melhorou"),
        "S9 parte intensiva: dy só nos itens que melhoraram": lambda: ajusta(d[d.melhorou > 0].reset_index(drop=True)),
        "S10 só adjudicados": lambda: ajusta(d[d.adjudicado].reset_index(drop=True)),
        "S11 corte 1%/99% de dy": lambda: ajusta(d[d.dy.between(lo, hi)].reset_index(drop=True)),
        "S12 agregado por pregão (médias)": lambda: ajusta(pc),
        "S13 sem itens de 1 licitante": lambda: ajusta(d[d.lic >= 2].reset_index(drop=True)),
    }
    res, linhas = {}, []
    for nome, f in ESPECIFICACOES.items():
        r = f(); tb = tabela(r)
        inter = [n for n in r["nomes"] if n.startswith("F_x_") and (n[4:] in PRINC + ["srv_x_sig"] or n.startswith("F_x_lic_"))]
        res[nome] = {"n": r["n"], "G": r["G"], "coefs": tb.to_dict("index"), "wald_interacoes": wald(r, inter)}
        for reg, row in tb.iterrows():
            linhas.append({"especificacao": nome, "regressor": reg, **row.to_dict(), "n": r["n"], "grupos": r["G"]})
        if nome.startswith("P "):
            T["efeitos_marginais"] = efeitos_marginais(r, d, None)
    R["especificacoes"] = res
    T["coeficientes"] = pd.DataFrame(linhas)
    T["wald"] = pd.DataFrame([{"especificacao": k, **v["wald_interacoes"]} for k, v in res.items()])
    R["efeitos_marginais"] = T["efeitos_marginais"].to_dict("records")
    R["descritivo"] = {"media_dy": float(d.dy.mean()), "prop_zero": float((d.dy == 0).mean()),
                       "media_dpp": float(d.dpp.mean()), "sigilo_uasgs_com_ambos":
                       int((d.groupby("uasg").sigiloso.agg(["min", "max"]).pipe(lambda x: (x["min"] == 0) & (x["max"] == 1))).sum()),
                       "servico_uasgs_com_ambos":
                       int((d.groupby("uasg").servico.agg(["min", "max"]).pipe(lambda x: (x["min"] == 0) & (x["max"] == 1))).sum())}
    (AQUI / "regressao_etapas.json").write_text(json.dumps(R, ensure_ascii=False, indent=2, default=float), encoding="utf-8")
    with pd.ExcelWriter(AQUI / "regressao_etapas.xlsx") as xw:
        for k, v in T.items():
            v.to_excel(xw, sheet_name=k, index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_rows", 300)
    print(json.dumps({k: R[k] for k in ["n_itens", "n_pregoes", "n_uasgs", "n_fornecedores", "descritivo"]}, ensure_ascii=False))
    print(json.dumps(R["equivalencia"], default=float)[:900])
    c = T["coeficientes"]; c = c[c.regressor.str.match(r"F \(|F_x_(ln_lic|sigiloso|servico|srv|lic_)")]
    print(c[["especificacao", "regressor", "coef", "ep", "p", "n", "grupos"]].round(4).to_string())
    print(T["wald"][["especificacao", "F", "p"]].round(4).to_string())
    print(T["efeitos_marginais"].round(2).to_string())


if __name__ == "__main__":
    main()
