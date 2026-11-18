"""Decomposição do desconto final e marcas provisórias dos casos em que o lance fechado supera o aberto.

Decomposição (itens da amostra com valor final):
    d_final = d_aberto + ganho_fechada + ajuste_pos_disputa
    ajuste_pos_disputa = d_final - d_apos  (< 0: o melhor lance da disputa não venceu — desclassificação,
                                            recusa, desistência; > 0: negociação abaixo do melhor lance)

Marcas provisórias (sem mudar o parser; ver relatorio.md, seção "Casos com lance fechado acima do aberto"):
    A3  vencedor_caiu       valor final > melhor após a fechada (o melhor lance da disputa não venceu)
        lider_aberto_caiu   idem e melhor fechado > melhor aberto (o líder da aberta não deu lance fechado e caiu)
    C   aberto_isolado      melhor aberto < 50% do valor final (variante: < 50% do melhor fechado)
    D   fechado_outlier     melhor fechado > 3 × melhor aberto
    B   etapa fechada reiniciada: só no chat do PDF; fica para o parser.
Usa por_item.csv.gz (analisar.py) e, nas regressões, as funções de regressao_etapas.py.
Saídas: decomposicao_marcas.json, decomposicao_marcas.xlsx, marcas_por_item.csv.gz.
"""
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))   # o Python portátil não inclui a pasta do script
from analisar import resumo
import regressao_etapas as re_

AQUI = Path(__file__).resolve().parent
TOL = 1e-4          # tolerância relativa para "igual" entre valores monetários


def marcar(d):
    a, f, fin, apos = d.melhor_lance_modo_aberto, d.melhor_lance_modo_fechado, d.valor_final, d.melhor_apos
    d["tem_final"] = fin.notna()
    d["vencedor_caiu"] = d.tem_final & (fin > apos * (1 + TOL))
    d["negociou_abaixo"] = d.tem_final & (fin < apos * (1 - TOL))
    d["lider_aberto_caiu"] = d.vencedor_caiu & (f > a * (1 + TOL))
    d["fechado_acima_aberto"] = f > a * (1 + TOL)
    d["aberto_isolado"] = d.tem_final & (a < 0.5 * fin)
    d["aberto_isolado_vs_fechado"] = f.notna() & (a < 0.5 * f)
    d["aberto_isolado_30"] = d.tem_final & (a < 0.3 * fin)
    d["aberto_isolado_10"] = d.tem_final & (a < 0.1 * fin)
    d["fechado_outlier"] = f > 3 * a
    d["fechado_outlier_estimado"] = f > 3 * d.valor_estimado
    d["ajuste_pos"] = d.d_final - d.d_apos
    return d


def decompor(d):
    x = d[d.tem_final]
    lin = {"itens": len(x), "compras": int(x.pasta.nunique())}
    for c in ["d_aberto", "ganho_pp", "ajuste_pos", "d_final"]:
        r = resumo(x, c); lin[c] = r["media"]; lin[c + "_ic_inf"] = r["ic95_inf"]; lin[c + "_ic_sup"] = r["ic95_sup"]
        lin[c + "_mediana"] = r["mediana"]
    lin["conferencia_soma"] = lin["d_aberto"] + lin["ganho_pp"] + lin["ajuste_pos"] - lin["d_final"]
    for k in ["vencedor_caiu", "negociou_abaixo"]:
        lin[f"prop_{k}"] = float(x[k].mean())
    lin["ajuste_pos_medio_se_caiu"] = float(x.loc[x.vencedor_caiu, "ajuste_pos"].mean())
    lin["ajuste_pos_medio_se_negociou"] = float(x.loc[x.negociou_abaixo, "ajuste_pos"].mean())
    return lin


def medidas(d, nome):
    lin = {"variante": nome, "itens": len(d), "compras": int(d.pasta.nunique())}
    for c in ["d_aberto", "d_apos", "ganho_pp", "ganho_rel", "d_final"]:
        r = resumo(d, c); lin[c] = r["media"]; lin[c + "_ic_inf"] = r["ic95_inf"]; lin[c + "_ic_sup"] = r["ic95_sup"]
        lin[c + "_mediana"] = r["mediana"]
    lin["prop_fechado_melhorou"] = float((d.ganho_pp > 1e-9).mean())
    return lin


def teste_direto(d, nome):
    t = d[d.melhor_lance_modo_fechado.notna() & d.d_fechado.between(-100, 99)]
    dif = (t.d_fechado - t.d_aberto).to_numpy()
    w = stats.wilcoxon(dif, zero_method="pratt")
    return {"variante": nome, "n": len(dif), "media_dif_pp": float(dif.mean()), "mediana_dif_pp": float(np.median(dif)),
            "media_aparada_5": float(stats.trim_mean(dif, 0.05)), "prop_fechado_melhor": float((dif > 0).mean()),
            "prop_fechado_pior": float((dif < 0).mean()), "wilcoxon_p": float(w.pvalue)}


def main():
    todos = pd.read_csv(AQUI / "por_item.csv.gz", dtype={"id_compra": str, "uasg": str, "numero_compra": str})
    s = marcar(todos[todos.na_amostra].copy())
    R, T = {"itens_amostra": len(s)}, {}

    # 1. Contagens das marcas
    marcas = ["fechado_acima_aberto", "vencedor_caiu", "lider_aberto_caiu", "negociou_abaixo", "aberto_isolado",
              "aberto_isolado_vs_fechado", "aberto_isolado_30", "aberto_isolado_10", "fechado_outlier",
              "fechado_outlier_estimado"]
    cont = [{"marca": m, "itens": int(s[m].sum()), "prop_amostra": float(s[m].mean()),
             "ganho_pp_medio": float(s.loc[s[m], "ganho_pp"].mean()),
             "d_aberto_medio": float(s.loc[s[m], "d_aberto"].mean()),
             "d_final_medio": float(s.loc[s[m], "d_final"].mean())} for m in marcas]
    T["marcas"] = pd.DataFrame(cont); R["marcas"] = cont
    fa = s[s.fechado_acima_aberto]
    R["fechado_acima_aberto_desdobrado"] = {
        "itens": len(fa),
        "final_igual_aberto (A: líder manteve)": int((fa.tem_final & ~fa.vencedor_caiu & ~fa.negociou_abaixo).sum()),
        "final_acima (A3: líder caiu)": int(fa.vencedor_caiu.sum()),
        "final_abaixo (negociação)": int(fa.negociou_abaixo.sum()),
        "sem_final (fracassado, revogado etc.)": int((~fa.tem_final).sum()),
        "com_aberto_isolado (C)": int(fa.aberto_isolado.sum()),
        "com_fechado_outlier (D)": int(fa.fechado_outlier.sum())}

    # 2. Decomposição do desconto final
    dec = [{"recorte": "amostra (itens com valor final)", **decompor(s)},
           {"recorte": "sem aberto isolado (C)", **decompor(s[~s.aberto_isolado])}]
    s["faixa_lic"] = pd.cut(s.quantidade_fornecedores, [0, 1, 2, 5, 10, 1e9], labels=["1", "2", "3-5", "6-10", ">10"])
    for k, g in s.groupby("faixa_lic", observed=True):
        dec.append({"recorte": f"licitantes {k}", **decompor(g)})
    T["decomposicao"] = pd.DataFrame(dec); R["decomposicao"] = dec

    # 3. Sensibilidade das medidas principais
    var = [medidas(s, "principal"),
           medidas(s[~s.aberto_isolado], "sem C (aberto < 50% do final)"),
           medidas(s[~s.aberto_isolado_vs_fechado], "sem C' (aberto < 50% do fechado)"),
           medidas(s[~s.aberto_isolado_10], "sem C extremo (aberto < 10% do final)"),
           medidas(s[~s.vencedor_caiu], "sem A3 (vencedor da disputa caiu)"),
           medidas(s[~s.lider_aberto_caiu], "sem A3 restrito (líder da aberta caiu)"),
           medidas(s[~s.fechado_outlier], "sem D (fechado > 3× aberto)"),
           medidas(s[~(s.aberto_isolado | s.vencedor_caiu | s.fechado_outlier)], "sem A3, C e D")]
    T["sensibilidade"] = pd.DataFrame(var); R["sensibilidade"] = var

    # 4. Teste direto fechado × aberto com e sem D
    td = [teste_direto(s, "principal (fechado entre -100% e 99%)"),
          teste_direto(s[~s.fechado_outlier], "sem D (fechado > 3× aberto)"),
          teste_direto(s[~s.fechado_outlier_estimado], "sem fechado > 3× estimado"),
          teste_direto(s[~s.aberto_isolado_vs_fechado], "sem C' (aberto < 50% do fechado)")]
    T["teste_direto"] = pd.DataFrame(td); R["teste_direto"] = td

    # 5. Regressão principal (P de regressao_etapas.py) nos recortes
    d = re_.dados()
    m_ = s[s.id_compra.notna()][["id_compra", "item"] + marcas]   # sem id_compra não ligam ao pncp.db
    d = d.merge(m_, on=["id_compra", "item"], how="left", validate="one_to_one")
    assert d[marcas].notna().all().all()
    recortes = {"P principal": d,
                "P sem C": d[~d.aberto_isolado.astype(bool)],
                "P sem A3": d[~d.vencedor_caiu.astype(bool)],
                "P sem D": d[~d.fechado_outlier.astype(bool)],
                "P sem A3, C e D": d[~(d.aberto_isolado | d.vencedor_caiu | d.fechado_outlier).astype(bool)]}
    linhas = []
    for nome, dd in recortes.items():
        r = re_.ajusta(dd.reset_index(drop=True)); tb = re_.tabela(r)
        inter = [n for n in r["nomes"] if n[4:] in re_.PRINC]
        w = re_.wald(r, inter)
        for reg in ["F (etapa fechada)"] + inter:
            linhas.append({"recorte": nome, "regressor": reg, **tb.loc[reg].to_dict(), "n": r["n"], "grupos": r["G"],
                           "wald_p_interacoes": w["p"]})
    T["regressao"] = pd.DataFrame(linhas); R["regressao"] = linhas

    # 6. Marcas por item (para revisão manual dos PDFs)
    cols = ["mes", "id_compra", "pasta", "item", "situacao_item", "valor_estimado", "melhor_lance_modo_aberto",
            "melhor_lance_modo_fechado", "melhor_apos", "valor_final", "quantidade_fornecedores", "d_aberto",
            "ganho_pp", "ajuste_pos", "d_final"] + marcas
    s[cols].to_csv(AQUI / "marcas_por_item.csv.gz", index=False, compression="gzip")
    (AQUI / "decomposicao_marcas.json").write_text(json.dumps(R, ensure_ascii=False, indent=2, default=float), encoding="utf-8")
    with pd.ExcelWriter(AQUI / "decomposicao_marcas.xlsx") as xw:
        for k, v in T.items():
            v.to_excel(xw, sheet_name=k, index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    print(json.dumps(R["fechado_acima_aberto_desdobrado"], ensure_ascii=False, indent=1))
    for k in T:
        print("\n==", k); print(T[k].round(3).to_string())


if __name__ == "__main__":
    main()
