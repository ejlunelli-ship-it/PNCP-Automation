"""Análise de 2026-02 com os campos do parser 1.8.0 (só fevereiro foi reprocessado; docs/05, pendência 14).

Troca as marcas provisórias de decomposicao_marcas.py pelas do parser e acrescenta a sensibilidade "só fornecedores
válidos" (sem os desclassificados, recusados e inabilitados da tabela de propostas):
    C  aberto isolado      melhor aberto < 50% de melhor_lance_modo_aberto_outro_fornecedor   (antes: < 50% do final)
    B  etapa reiniciada    reinicios_etapa_fechada > 0                                       (antes: não identificável)
    A3 líder caiu          cnpj_melhor_lance_aberto em fornecedores_desclassificados          (antes: final > após)
    A  líder sem fechado   lider_aberto_lance_fechado = 0
    D  fechado outlier     melhor fechado > 3 × melhor aberto                                (igual)
Válidos: após_v = mín(melhor_lance_modo_aberto_validos, melhor_lance_modo_fechado_validos);
         d_final = d_aberto_v + ganho_v + ajuste_pós_v.
Mesmas regras e amostra de analisar.py (OK, Menor Preço, descontos entre −100% e 99%).
Saídas: fevereiro_campos_novos.json, fevereiro_campos_novos.xlsx.
"""
import json, os, sqlite3, sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analisar as an
import regressao_etapas as re_
from decomposicao_marcas import marcar, teste_direto

AQUI = Path(__file__).resolve().parent
MES, VERSAO = "2026-02", "1.8.0"
NOVOS = ["cnpj_melhor_lance_aberto", "melhor_lance_modo_aberto_outro_fornecedor", "lider_aberto_lance_fechado",
         "reinicios_etapa_fechada", "fornecedores_desclassificados", "quantidade_desclassificados",
         "melhor_lance_modo_aberto_validos", "melhor_lance_modo_fechado_validos"]
TOL = 1e-4


def carregar():
    bruto, meta = an.carregar()
    st = os.stat(an.BANCO)
    con = sqlite3.connect(f"file:{an.BANCO.as_posix()}?mode=ro", uri=True)
    nv = pd.read_sql_query(f"select arquivo_origem, versao_parser as versao, {', '.join(NOVOS)} from itens", con)
    con.close()
    assert os.stat(an.BANCO).st_mtime_ns == st.st_mtime_ns
    bruto = bruto[bruto.mes == MES]
    assert (bruto.versao_parser == VERSAO).all(), "fevereiro não está todo na versão 1.8.0"
    df, funil = an.preparar(bruto)
    df = df.merge(nv, on="arquivo_origem", how="left", validate="one_to_one")
    for c in ["melhor_lance_modo_aberto_outro_fornecedor", "melhor_lance_modo_aberto_validos",
              "melhor_lance_modo_fechado_validos"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df, funil, meta


def marcas_parser(s):
    a, f, o = s.melhor_lance_modo_aberto, s.melhor_lance_modo_fechado, s.melhor_lance_modo_aberto_outro_fornecedor
    desc = s.fornecedores_desclassificados.fillna("")
    s["lider_desclassificado"] = [bool(l) and l in d for l, d in zip(s.cnpj_melhor_lance_aberto.fillna(""), desc)]
    s["p_aberto_isolado"] = o.notna() & (a < 0.5 * o)
    s["p_aberto_isolado_30"] = o.notna() & (a < 0.3 * o)
    s["p_reiniciada"] = s.reinicios_etapa_fechada.fillna(0) > 0
    s["p_lider_sem_fechado"] = s.lider_aberto_lance_fechado == 0
    s["p_fechado_outlier"] = f > 3 * a
    # medidas só com fornecedores válidos
    ve, av, fv = s.valor_estimado, s.melhor_lance_modo_aberto_validos, s.melhor_lance_modo_fechado_validos
    s["apos_v"] = np.where(fv.notna(), np.minimum(av, fv.fillna(np.inf)), av)
    s["d_aberto_v"] = 100 * (1 - av / ve)
    s["d_apos_v"] = 100 * (1 - s.apos_v / ve)
    s["ganho_pp_v"] = s.d_apos_v - s.d_aberto_v
    s["ganho_rel_v"] = 100 * (1 - s.apos_v / av)
    s["ajuste_pos_v"] = s.d_final - s.d_apos_v
    s["tem_validos"] = av.notna() & (av > 0) & s.d_aberto_v.between(-100, 99) & s.d_apos_v.between(-100, 99)
    return s


def linha(d, nome, cols):
    out = {"variante": nome, "itens": len(d), "compras": int(d.pasta.nunique())}
    for c in cols:
        r = an.resumo(d, c)
        if r:
            out[c] = r["media"]; out[c + "_ic_inf"] = r["ic95_inf"]; out[c + "_ic_sup"] = r["ic95_sup"]
            out[c + "_mediana"] = r["mediana"]
    return out


def main():
    df, funil, meta = carregar()
    s = df[df.na_amostra].copy()
    s = marcar(s)                      # marcas provisórias, para comparar
    s = marcas_parser(s)
    R, T = {"mes": MES, "versao_parser": VERSAO, "funil": funil, "itens_amostra": len(s),
            "compras": int(s.pasta.nunique()), "uasgs": int(s.uasg.nunique())}, {}

    # 1. Casos com fechado acima do aberto, pelas marcas do parser
    fa = s[s.fechado_acima_aberto]
    cl = {"itens": len(fa),
          "lider sem lance fechado (A)": int(fa.p_lider_sem_fechado.sum()),
          "lider com lance fechado": int((fa.lider_aberto_lance_fechado == 1).sum()),
          "lider desclassificado (A3)": int(fa.lider_desclassificado.sum()),
          "etapa reiniciada (B)": int(fa.p_reiniciada.sum()),
          "aberto isolado (C)": int(fa.p_aberto_isolado.sum()),
          "fechado > 3x aberto (D)": int(fa.p_fechado_outlier.sum()),
          "lider venceu (A puro: sem desclassificação, final = aberto)": int(
              (fa.p_lider_sem_fechado & ~fa.lider_desclassificado & fa.tem_final & ~fa.vencedor_caiu & ~fa.negociou_abaixo).sum())}
    R["fechado_acima_aberto"] = cl
    T["fechado_acima_aberto"] = pd.DataFrame(list(cl.items()), columns=["caso", "itens"])

    # 2. Contagens na amostra e concordância provisória × parser
    marcas = ["lider_desclassificado", "p_aberto_isolado", "p_aberto_isolado_30", "p_reiniciada", "p_lider_sem_fechado",
              "p_fechado_outlier", "vencedor_caiu", "aberto_isolado", "fechado_acima_aberto"]
    cont = [{"marca": m, "itens": int(s[m].sum()), "prop": float(s[m].mean()),
             "ganho_pp_medio": float(s.loc[s[m], "ganho_pp"].mean()), "d_aberto_medio": float(s.loc[s[m], "d_aberto"].mean()),
             "d_final_medio": float(s.loc[s[m], "d_final"].mean())} for m in marcas]
    T["marcas"] = pd.DataFrame(cont); R["marcas"] = cont
    conc = {}
    for prov, par in [("aberto_isolado", "p_aberto_isolado"), ("vencedor_caiu", "lider_desclassificado")]:
        ct = pd.crosstab(s[prov], s[par])
        conc[f"{prov} x {par}"] = {f"{i}|{j}": int(ct.loc[i, j]) for i in ct.index for j in ct.columns}
    R["concordancia"] = conc

    # 3. Sensibilidades das medidas principais
    cols = ["d_aberto", "d_apos", "ganho_pp", "ganho_rel", "d_final"]
    var = [linha(s, "principal (fevereiro)", cols),
           linha(s[~s.p_aberto_isolado], "sem C do parser (aberto < 50% do outro fornecedor)", cols),
           linha(s[~s.aberto_isolado], "sem C provisório (aberto < 50% do final)", cols),
           linha(s[~s.p_reiniciada], "sem B (etapa reiniciada)", cols),
           linha(s[~s.lider_desclassificado], "sem A3 do parser (líder desclassificado)", cols),
           linha(s[~s.p_fechado_outlier], "sem D (fechado > 3× aberto)", cols),
           linha(s[~(s.p_aberto_isolado | s.p_reiniciada | s.lider_desclassificado | s.p_fechado_outlier)],
                 "sem A3, B, C e D (parser)", cols)]
    v = s[s.tem_validos]
    lv = linha(v, "só fornecedores válidos", ["d_aberto_v", "d_apos_v", "ganho_pp_v", "ganho_rel_v", "d_final"])
    lv = {k.replace("_v", "") if k.startswith(("d_aberto_v", "d_apos_v", "ganho_pp_v", "ganho_rel_v")) else k: x
          for k, x in lv.items()}
    var.append(lv)
    T["sensibilidade"] = pd.DataFrame(var); R["sensibilidade"] = var

    # 4. Decomposição: todos os fornecedores × só válidos (itens com valor final e medidas válidas)
    x = s[s.tem_final & s.tem_validos]
    dec = []
    for nome, ab, ga, aj in [("todos os fornecedores", "d_aberto", "ganho_pp", "ajuste_pos"),
                             ("só fornecedores válidos", "d_aberto_v", "ganho_pp_v", "ajuste_pos_v")]:
        lin = {"medida": nome, "itens": len(x)}
        for rot, c in [("aberta", ab), ("fechada", ga), ("pos_disputa", aj), ("final", "d_final")]:
            r = an.resumo(x, c); lin[rot] = r["media"]; lin[rot + "_ic_inf"] = r["ic95_inf"]; lin[rot + "_ic_sup"] = r["ic95_sup"]
        apos = x.melhor_apos if ab == "d_aberto" else x.apos_v
        lin["prop_final_igual_melhor"] = float(np.isclose(x.valor_final, apos).mean())
        lin["prop_final_acima"] = float((x.valor_final > apos * (1 + TOL)).mean())
        lin["prop_final_abaixo"] = float((x.valor_final < apos * (1 - TOL)).mean())
        dec.append(lin)
    T["decomposicao"] = pd.DataFrame(dec); R["decomposicao"] = dec

    # 5. Teste direto fechado × aberto
    td = [teste_direto(s, "principal"), teste_direto(s[~s.p_aberto_isolado], "sem C do parser"),
          teste_direto(s[~s.p_fechado_outlier], "sem D")]
    tv = v[v.melhor_lance_modo_fechado_validos.notna()].copy()
    tv["d_fechado"] = 100 * (1 - tv.melhor_lance_modo_fechado_validos / tv.valor_estimado)
    tv["d_aberto"] = tv.d_aberto_v
    td.append(teste_direto(tv, "só fornecedores válidos"))
    T["teste_direto"] = pd.DataFrame(td); R["teste_direto"] = td

    # 6. Regressão principal P (regressao_etapas.py) em fevereiro
    d = re_.dados()
    d = d[d.mes == MES].reset_index(drop=True)
    cols_m = ["id_compra", "item", "p_aberto_isolado", "p_reiniciada", "lider_desclassificado", "p_fechado_outlier",
              "tem_validos", "apos_v", "melhor_lance_modo_aberto_validos"]
    d = d.merge(s[s.id_compra.notna()][cols_m], on=["id_compra", "item"], how="left", validate="one_to_one")
    assert d.p_aberto_isolado.notna().all()
    for c in ["p_aberto_isolado", "p_reiniciada", "lider_desclassificado", "p_fechado_outlier", "tem_validos"]:
        d[c] = d[c].astype(bool)
    dv = d[d.tem_validos].copy()
    dv["dy"] = 100 * np.log(dv.apos_v) - 100 * np.log(dv.melhor_lance_modo_aberto_validos)
    recortes = {"P fevereiro": d, "P sem C (parser)": d[~d.p_aberto_isolado], "P sem B": d[~d.p_reiniciada],
                "P sem A3 (parser)": d[~d.lider_desclassificado], "P sem D": d[~d.p_fechado_outlier],
                "P sem A3, B, C e D": d[~(d.p_aberto_isolado | d.p_reiniciada | d.lider_desclassificado | d.p_fechado_outlier)],
                "P só fornecedores válidos": dv}
    linhas = []
    for nome, dd in recortes.items():
        r = re_.ajusta(dd.reset_index(drop=True)); tb = re_.tabela(r)
        inter = [n for n in r["nomes"] if n[4:] in re_.PRINC]
        w = re_.wald(r, inter)
        for reg in ["F (etapa fechada)"] + inter:
            linhas.append({"recorte": nome, "regressor": reg, **tb.loc[reg].to_dict(), "n": r["n"], "grupos": r["G"],
                           "wald_p_interacoes": w["p"]})
    T["regressao"] = pd.DataFrame(linhas); R["regressao"] = linhas

    (AQUI / "fevereiro_campos_novos.json").write_text(json.dumps(R, ensure_ascii=False, indent=2, default=float), encoding="utf-8")
    with pd.ExcelWriter(AQUI / "fevereiro_campos_novos.xlsx") as xw:
        for k, t in T.items():
            t.to_excel(xw, sheet_name=k, index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    print(json.dumps({k: R[k] for k in ["itens_amostra", "compras", "uasgs", "fechado_acima_aberto", "concordancia"]},
                     ensure_ascii=False, indent=1))
    for k in ["marcas", "sensibilidade", "decomposicao", "teste_direto", "regressao"]:
        print("\n==", k); print(T[k].round(3).to_string())


if __name__ == "__main__":
    main()
