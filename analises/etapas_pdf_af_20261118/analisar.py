"""Análise estatística das etapas aberta e fechada nos PDFs Aberto-Fechado (2026-02, 03, 04, 08).

Fonte: PNCP-Automation/dados/extracao/aberto-fechado_2026-08.db (tabela itens), aberta só para leitura.
Regras (docs/01 e docs/05 do projeto):
  - só status_extracao = 'OK' e critério Menor Preço;
  - desconto = 1 - valor / valor_estimado;
  - melhor após a fechada = min(melhor aberto, melhor fechado); item sem lance fechado tem ganho zero;
  - filtro de qualidade igual ao matching_desconto.py: descontos entre -100% e 99%.
Saídas nesta pasta: resultados.json, tabelas.xlsx, por_item.csv.gz.
"""
import hashlib, json, os, sqlite3, sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

AQUI = Path(__file__).resolve().parent
BANCO = AQUI.parents[1] / "PNCP-Automation" / "dados" / "extracao" / "aberto-fechado_2026-08.db"
RNG = np.random.default_rng(20261118)
B = 2000


def carregar():
    st = os.stat(BANCO)
    con = sqlite3.connect(f"file:{BANCO.as_posix()}?mode=ro", uri=True)
    df = pd.read_sql_query(
        """select uasg, numero_compra, item, pasta, arquivo_origem, situacao_item, criterio_julgamento_item,
                  status_extracao, versao_parser, valor_estimado, valor_estimado_total,
                  melhor_lance_modo_aberto, melhor_lance_modo_fechado, melhor_lance_desempate,
                  lance_aceito, valor_negociado_aceito, quantidade_fornecedores, resultado
           from itens""", con)
    con.close()
    meta = {"banco": str(BANCO), "bytes": st.st_size, "mtime_ns": st.st_mtime_ns, "linhas": len(df)}
    df["mes"] = df["arquivo_origem"].str.extract(r"aberto-fechado_(\d{4}-\d{2})")[0]
    df["id_compra"] = df["arquivo_origem"].str.extract(r"-(\d{17})-item-")[0]
    return df, meta


def preparar(df):
    funil = {"total": len(df)}
    df = df[df.status_extracao == "OK"]; funil["status_OK"] = len(df)
    df = df[df.criterio_julgamento_item.str.startswith("Menor Pre", na=False)]; funil["menor_preco"] = len(df)
    for c in ["valor_estimado", "valor_estimado_total", "melhor_lance_modo_aberto", "melhor_lance_modo_fechado",
              "lance_aceito", "valor_negociado_aceito", "melhor_lance_desempate"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df[df.valor_estimado > 0]; funil["estimado_positivo"] = len(df)
    df = df[df.melhor_lance_modo_aberto > 0].copy(); funil["com_lance_aberto"] = len(df)
    ve, a, f = df.valor_estimado, df.melhor_lance_modo_aberto, df.melhor_lance_modo_fechado
    df["teve_fechado"] = f.notna() & (f > 0)
    df["melhor_apos"] = np.where(df.teve_fechado, np.minimum(a, f.fillna(np.inf)), a)
    df["fechado_melhorou"] = df.teve_fechado & (f < a)
    df["d_aberto"] = 100 * (1 - a / ve)
    df["d_fechado"] = np.where(df.teve_fechado, 100 * (1 - f / ve), np.nan)
    df["d_apos"] = 100 * (1 - df.melhor_apos / ve)
    df["ganho_pp"] = df.d_apos - df.d_aberto                       # pontos percentuais do estimado
    df["ganho_rel"] = 100 * (1 - df.melhor_apos / a)                # % de redução sobre o melhor aberto
    final = df.valor_negociado_aceito.where(df.valor_negociado_aceito > 0, df.lance_aceito)
    df["valor_final"] = final.where(final > 0)
    df["d_final"] = 100 * (1 - df.valor_final / ve)
    df["quantidade"] = (df.valor_estimado_total / ve).where(df.valor_estimado_total > 0)
    df["economia_fechada_R$"] = (a - df.melhor_apos) * df.quantidade
    ok = df.d_aberto.between(-100, 99) & df.d_apos.between(-100, 99) & (df.d_final.isna() | df.d_final.between(-100, 99))
    funil["filtro_desconto_-100_99"] = int(ok.sum())
    df["na_amostra"] = ok
    n = df.quantidade_fornecedores
    df["faixa_fornec"] = pd.cut(n, [0, 1, 2, 5, 10, 1e9], labels=["1", "2", "3-5", "6-10", ">10"])
    df["faixa_valor"] = pd.qcut(df.valor_estimado_total, 5, labels=["Q1 (menor)", "Q2", "Q3", "Q4", "Q5 (maior)"])
    return df, funil


def boot_media(x, cl):
    """IC 95% bootstrap por conglomerado (compra) para a média de x."""
    m = ~np.isnan(x); x, cl = x[m], cl[m]
    cod, idx = np.unique(cl, return_inverse=True)
    s = np.bincount(idx, weights=x); c = np.bincount(idx).astype(float)
    k = len(cod); est = s.sum() / c.sum()
    reps = np.empty(B)
    for b in range(B):
        w = np.bincount(RNG.integers(0, k, k), minlength=k)
        reps[b] = (w * s).sum() / (w * c).sum()
    return est, *np.percentile(reps, [2.5, 97.5])


def resumo(d, col, cl="pasta"):
    x = d[col].to_numpy(float); x = x[~np.isnan(x)]
    if len(x) == 0:
        return {}
    est, lo, hi = boot_media(d[col].to_numpy(float), d[cl].to_numpy())
    return {"n": int(len(x)), "media": est, "ic95_inf": lo, "ic95_sup": hi, "mediana": float(np.median(x)),
            "p25": float(np.percentile(x, 25)), "p75": float(np.percentile(x, 75)),
            "media_aparada_5": float(stats.trim_mean(x, 0.05)), "dp": float(x.std(ddof=1))}


def ols_cluster(y, X, g):
    """MQO com erro-padrão agrupado (CR1)."""
    XtX_inv = np.linalg.inv(X.T @ X); b = XtX_inv @ X.T @ y; u = y - X @ b
    cod, idx = np.unique(g, return_inverse=True); G = len(cod); n, k = X.shape
    S = np.zeros((G, k)); np.add.at(S, idx, X * u[:, None])
    V = XtX_inv @ (S.T @ S) @ XtX_inv * (G / (G - 1)) * ((n - 1) / (n - k))
    se = np.sqrt(np.diag(V)); t = b / se
    return b, se, 2 * stats.t.sf(np.abs(t), G - 1)


def main():
    bruto, meta = carregar()
    df, funil = preparar(bruto)
    s = df[df.na_amostra].copy()
    R = {"meta": meta, "funil": funil, "versoes_parser": bruto.versao_parser.value_counts().to_dict()}

    # 1. Descritivo geral
    R["compras"] = int(s.pasta.nunique()); R["uasgs"] = int(s.uasg.nunique()); R["itens"] = len(s)
    R["prop_teve_fechado"] = float(s.teve_fechado.mean())
    R["prop_fechado_melhorou"] = float(s.fechado_melhorou.mean())
    R["prop_fechado_melhorou_dado_lance"] = float(s.loc[s.teve_fechado, "fechado_melhorou"].mean())
    R["geral"] = {c: resumo(s if c != "d_fechado" else s[s.d_fechado.between(-100, 99)], c) for c in ["d_aberto", "d_fechado", "d_apos", "ganho_pp", "ganho_rel", "d_final"]}

    # 2. Testes pareados
    t = s[s.teve_fechado & s.d_fechado.between(-100, 99)]   # lances fechados absurdos fora (não afetam o mínimo)
    R["fechado_fora_da_faixa"] = int((s.teve_fechado & ~s.d_fechado.between(-100, 99)).sum())
    dif = (t.d_fechado - t.d_aberto).to_numpy()
    w = stats.wilcoxon(dif, zero_method="pratt")
    tt = stats.ttest_1samp(dif, 0)
    R["teste_fechado_vs_aberto"] = {
        "n": len(dif), "media_dif_pp": float(dif.mean()), "mediana_dif_pp": float(np.median(dif)),
        "prop_fechado_melhor": float((dif > 0).mean()), "prop_igual": float((dif == 0).mean()),
        "prop_fechado_pior": float((dif < 0).mean()),
        "wilcoxon_p": float(w.pvalue), "t_p": float(tt.pvalue),
        "boot_cluster": resumo(t.assign(dif=dif), "dif")}
    # ganho_pp >= 0 por construção; testa-se a magnitude (IC) e não o sinal
    g = s.ganho_pp.to_numpy()
    R["teste_ganho_apos"] = {"wilcoxon_p": float(stats.wilcoxon(g, zero_method="pratt").pvalue),
                             "prop_ganho_positivo": float((g > 0).mean())}
    # resultado final vs melhor lance (negociação/desclassificação)
    f = s[s.d_final.notna()]
    R["final_vs_melhor"] = {"n": len(f), "media_final_menos_apos_pp": float((f.d_final - f.d_apos).mean()),
                            "prop_final_igual_melhor": float(np.isclose(f.valor_final, f.melhor_apos).mean()),
                            "prop_final_pior": float((f.valor_final > f.melhor_apos + 1e-9).mean()),
                            "prop_final_melhor": float((f.valor_final < f.melhor_apos - 1e-9).mean())}

    # 3. Economia em R$ atribuível à etapa fechada
    e = s[s.quantidade.notna()]
    tot_ab = float((e.melhor_lance_modo_aberto * e.quantidade).sum())
    eco = float(e["economia_fechada_R$"].sum())
    R["economia"] = {"itens": len(e), "valor_estimado_total": float(e.valor_estimado_total.sum()),
                     "total_melhor_aberto": tot_ab, "economia_fechada": eco,
                     "economia_pct_do_aberto": 100 * eco / tot_ab,
                     "desconto_ponderado_aberto": 100 * (1 - tot_ab / e.valor_estimado_total.sum()),
                     "desconto_ponderado_apos": 100 * (1 - (e.melhor_apos * e.quantidade).sum() / e.valor_estimado_total.sum())}

    # 4. Heterogeneidade
    tab = {}
    for por in ["mes", "faixa_fornec", "faixa_valor"]:
        linhas = []
        for k, d in s.groupby(por, observed=True):
            r1, r2, r3 = resumo(d, "d_aberto"), resumo(d, "d_apos"), resumo(d, "ganho_rel")
            linhas.append({por: str(k), "itens": len(d), "compras": d.pasta.nunique(),
                           "prop_teve_fechado": d.teve_fechado.mean(), "prop_fechado_melhorou": d.fechado_melhorou.mean(),
                           "d_aberto_media": r1["media"], "d_apos_media": r2["media"], "d_aberto_mediana": r1["mediana"],
                           "d_apos_mediana": r2["mediana"], "ganho_pp_media": d.ganho_pp.mean(),
                           "ganho_rel_media": r3["media"], "ganho_rel_ic_inf": r3["ic95_inf"], "ganho_rel_ic_sup": r3["ic95_sup"],
                           "ganho_rel_mediana": r3["mediana"]})
        tab[por] = pd.DataFrame(linhas)
    R["heterogeneidade"] = {k: v.to_dict("records") for k, v in tab.items()}
    # teste de diferença entre meses (Kruskal-Wallis) no ganho relativo
    R["kruskal_mes_ganho_rel"] = float(stats.kruskal(*[d.ganho_rel for _, d in s.groupby("mes")]).pvalue)

    # 5. Regressão: ganho relativo ~ log(fornecedores) + log(valor total) + efeitos de mês, EP por UASG
    r = s[s.quantidade_fornecedores.notna() & (s.valor_estimado_total > 0)]
    meses = sorted(r.mes.unique())
    X = np.column_stack([np.ones(len(r)), np.log(r.quantidade_fornecedores.clip(lower=1)),
                         np.log(r.valor_estimado_total)] + [(r.mes == m).astype(float) for m in meses[1:]])
    nomes = ["const", "log_fornecedores", "log_valor_total"] + [f"mes_{m}" for m in meses[1:]]
    reg = {}
    for y in ["ganho_rel", "d_aberto", "d_apos"]:
        b, se, p = ols_cluster(r[y].to_numpy(float), X, r.uasg.to_numpy())
        reg[y] = {n: {"coef": float(b[i]), "ep": float(se[i]), "p": float(p[i])} for i, n in enumerate(nomes)}
    reg["n"] = len(r); reg["uasgs"] = int(r.uasg.nunique()); reg["mes_base"] = meses[0]
    R["regressao"] = reg

    # 6. Sensibilidade: sem o filtro de desconto, só homologados/adjudicados, um item por compra (média por compra)
    sen = {}
    sen["sem_filtro"] = {c: resumo(df, c) for c in ["d_aberto", "d_apos", "ganho_rel"]}
    h = s[s.situacao_item.str.startswith("Adjudicado", na=False)]
    sen["so_adjudicados"] = {c: resumo(h, c) for c in ["d_aberto", "d_apos", "ganho_rel", "d_final"]}
    pc = s.groupby("pasta")[["d_aberto", "d_apos", "ganho_rel"]].mean()
    sen["media_por_compra"] = {c: {"n": len(pc), "media": float(pc[c].mean()), "mediana": float(pc[c].median())} for c in pc}
    sen["fornec_ge_2"] = {c: resumo(s[s.quantidade_fornecedores >= 2], c) for c in ["d_aberto", "d_apos", "ganho_rel"]}
    so_apos = df[df.d_apos.between(-100, 99)]
    sen["filtro_so_no_d_apos"] = {c: resumo(so_apos, c) for c in ["d_aberto", "d_apos", "ganho_rel"]}
    sen["filtro_so_no_d_apos"]["n_itens"] = len(so_apos)
    R["sensibilidade"] = sen

    # 7. Controles: material x serviço e orçamento aberto x sigiloso (do pncp.db, via ligar_pncp.py)
    lig = pd.read_csv(AQUI / "ligacao_pncp.csv.gz", dtype={"id_compra": str})
    lig = lig[lig.n_registros == 1][["id_compra", "item", "material_ou_servico", "orcamento_sigiloso"]]
    s = s.merge(lig, on=["id_compra", "item"], how="left")
    R["ligacao"] = {"itens_amostra": len(s), "ligados": int(s.material_ou_servico.notna().sum())}
    c = s[s.material_ou_servico.isin(["M", "S"]) & s.orcamento_sigiloso.isin([0, 1])].copy()
    c["tipo"] = c.material_ou_servico.map({"M": "Material", "S": "Serviço"})
    c["orcamento"] = c.orcamento_sigiloso.map({0: "Aberto", 1: "Sigiloso"})
    estr = []
    for chave in [["tipo"], ["orcamento"], ["tipo", "orcamento"]]:
        for k, d in c.groupby(chave):
            k = k if isinstance(k, tuple) else (k,)
            lin = dict(zip(chave, k)); lin["itens"] = len(d); lin["compras"] = d.pasta.nunique()
            lin["prop_teve_fechado"] = d.teve_fechado.mean(); lin["prop_fechado_melhorou"] = d.fechado_melhorou.mean()
            for v in ["d_aberto", "d_apos", "ganho_pp", "ganho_rel", "d_final"]:
                r_ = resumo(d, v); lin[f"{v}_media"] = r_["media"]; lin[f"{v}_ic_inf"] = r_["ic95_inf"]
                lin[f"{v}_ic_sup"] = r_["ic95_sup"]; lin[f"{v}_mediana"] = r_["mediana"]
            estr.append(lin)
    estr = pd.DataFrame(estr); tab["estratos_tipo_orcamento"] = estr
    R["estratos"] = estr.to_dict("records")
    # regressão com controles: serviço, sigiloso, interação, log fornecedores, log valor, mês; EP por UASG
    c = c[c.quantidade_fornecedores.notna() & (c.valor_estimado_total > 0)]
    srv = (c.tipo == "Serviço").astype(float); sig = (c.orcamento == "Sigiloso").astype(float)
    base = [np.ones(len(c)), np.log(c.quantidade_fornecedores.clip(lower=1)), np.log(c.valor_estimado_total)] +            [(c.mes == m).astype(float) for m in meses[1:]]
    nb = ["const", "log_fornecedores", "log_valor_total"] + [f"mes_{m}" for m in meses[1:]]
    modelos = {"sem_controles_novos": (base, nb),
               "com_tipo_sigilo": (base + [srv, sig], nb + ["servico", "sigiloso"]),
               "com_interacao": (base + [srv, sig, srv * sig], nb + ["servico", "sigiloso", "servico_x_sigiloso"])}
    regc = {"n": len(c), "uasgs": int(c.uasg.nunique())}
    for nome_m, (cols_, nomes_) in modelos.items():
        Xc = np.column_stack(cols_); regc[nome_m] = {}
        for y in ["ganho_rel", "ganho_pp", "d_aberto", "d_apos", "d_final"]:
            m_ = c[y].notna().to_numpy()
            b, se, p = ols_cluster(c[y].to_numpy(float)[m_], Xc[m_], c.uasg.to_numpy()[m_])
            regc[nome_m][y] = {n_: {"coef": float(b[i]), "ep": float(se[i]), "p": float(p[i])} for i, n_ in enumerate(nomes_)}
    R["regressao_controles"] = regc
    linhas = []
    for nome_m in modelos:
        for y, d_ in regc[nome_m].items():
            for v, e_ in d_.items():
                linhas.append({"modelo": nome_m, "variavel_dependente": y, "regressor": v, **e_})
    tab["regressao_controles"] = pd.DataFrame(linhas)

    (AQUI / "resultados.json").write_text(json.dumps(R, ensure_ascii=False, indent=2, default=float), encoding="utf-8")
    with pd.ExcelWriter(AQUI / "tabelas.xlsx") as xw:
        pd.DataFrame(list(funil.items()), columns=["etapa_do_filtro", "itens"]).to_excel(xw, sheet_name="funil", index=False)
        pd.DataFrame(R["geral"]).T.to_excel(xw, sheet_name="geral")
        for k, v in tab.items():
            v.to_excel(xw, sheet_name=f"por_{k}", index=False)
        pd.DataFrame({y: {n: reg[y][n]["coef"] for n in nomes} for y in ["ganho_rel", "d_aberto", "d_apos"]}).to_excel(xw, sheet_name="regressao_coef")
    cols = ["mes", "id_compra", "uasg", "numero_compra", "item", "pasta", "situacao_item", "valor_estimado", "melhor_lance_modo_aberto",
            "melhor_lance_modo_fechado", "melhor_apos", "valor_final", "quantidade_fornecedores", "d_aberto", "d_fechado",
            "d_apos", "ganho_pp", "ganho_rel", "d_final", "na_amostra"]
    df[cols].to_csv(AQUI / "por_item.csv.gz", index=False, compression="gzip")
    assert os.stat(BANCO).st_mtime_ns == meta["mtime_ns"], "banco mudou durante a análise"
    print(json.dumps({k: R[k] for k in ["funil", "itens", "compras", "uasgs"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
