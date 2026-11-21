"""Desconto por etapa (aberta × fechada) nos PDFs Aberto-Fechado ou Fechado-Aberto, com as DUAS medidas principais.

Uso (de qualquer máquina com a extração do mês feita pelo parser >= 1.8.0; Fechado-Aberto, >= 1.10.0):

    python analise_etapas.py --db dados/extracao/aberto-fechado_2026-02.db --meses 2026-02
    python analise_etapas.py --db dados/extracao/a.db --db dados/extracao/b.db          # vários bancos
    python analise_etapas.py --db ... --pncp-db dados/pncp.db                           # + material/serviço e sigilo
    python analise_etapas.py --modo fechado-aberto --db dados/extracao/fechado-aberto_2023-05_a_2026-10.db

Fechado-Aberto (--modo fechado-aberto): a ordem das etapas se inverte. A primeira é a fechada (melhor proposta
sigilosa) e a segunda a aberta; "após a aberta" = mín(melhor fechado, melhor aberto) e o ganho é o da etapa aberta.
As colunas de saída levam os nomes das etapas do modo (ex.: fechada_media, apos_aberta_media, regressor
"A (etapa aberta)"). As marcas A e B (líder sem lance fechado, fechada reiniciada) só existem no Aberto-Fechado.

Medidas principais (decisão de 2026-11-18, docs/05), sempre reportadas juntas:
  - TODOS os fornecedores: melhor lance de cada etapa como registrado na disputa, mesmo que o fornecedor caia depois
    (dinâmica da disputa);
  - SÓ FORNECEDORES VÁLIDOS: sem os desclassificados, recusados e inabilitados da tabela de propostas (desconto que o
    órgão efetivamente obtém de cada etapa). Colunas `_validos` do parser 1.8.0.
  Em ambas: após a fechada = mín(melhor aberto, melhor fechado); desconto = 1 − valor / estimado;
  desconto final = aberta + ganho da fechada + ajuste pós-disputa.

Amostra: status OK, Menor Preço, estimado > 0, lance aberto > 0, descontos (aberto, após, final) entre −100% e 99%.
Marcas do parser (sensibilidades): A líder da aberta sem lance fechado; A3 líder desclassificado; B etapa fechada
reiniciada; C lance aberto isolado (< 50% do melhor aberto de outro fornecedor); D fechado > 3 × aberto.
Regressão: 100·ln(preço) com efeito fixo de ITEM, estimada em primeira diferença (2 observações por item: aberta e
após a fechada; numericamente igual ao painel empilhado com FE de item), F × {ln licitantes, ln valor total, mês}
centrados e, com --pncp-db, F × {sigiloso, serviço}. A UASG é só o conglomerado do erro-padrão, NÃO um efeito fixo
(decisão de 2026-11-20, docs/05 e 07). IC 95% das médias por bootstrap de compra.
Lê os bancos só para leitura. Saídas em --saida: resultados.json, tabelas.xlsx, por_item.csv.gz.
"""
import argparse, json, os, sqlite3, sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from config import DADOS

B, SEMENTE, TOL = 2000, 20261118, 1e-4
# ordem das etapas por modo de disputa: c1/c2 = colunas do melhor valor da 1ª e da 2ª etapa
MARCAS_AF = ["A_lider_sem_fechado", "A3_lider_desclassificado", "B_reiniciada", "C_aberto_isolado", "D_fechado_outlier"]
MODOS = {
    "aberto-fechado": dict(
        versao_minima=(1, 8, 0), prefixo="aberto-fechado",
        c1="melhor_lance_modo_aberto", c2="melhor_lance_modo_fechado",
        c1v="melhor_lance_modo_aberto_validos", c2v="melhor_lance_modo_fechado_validos",
        d1="d_aberto", d2="d_fechado", rot1="aberta", rot2="fechada", apos="apos_fechada", funil1="com_lance_aberto",
        prop2="prop_fechado", letra="F", coef="F (etapa fechada)",
        marcas=MARCAS_AF, sens=MARCAS_AF[1:], sem="sem A3, B, C e D", segunda_acima=True),
    "fechado-aberto": dict(
        versao_minima=(1, 10, 0), prefixo="fechado-aberto",
        c1="melhor_lance_modo_fechado", c2="melhor_lance_modo_aberto",
        c1v="melhor_lance_modo_fechado_validos", c2v="melhor_lance_modo_aberto_validos",
        d1="d_fechado", d2="d_aberto", rot1="fechada", rot2="aberta", apos="apos_aberta", funil1="com_proposta_fechada",
        prop2="prop_aberto", letra="A", coef="A (etapa aberta)",
        marcas=MARCAS_AF[1:2] + MARCAS_AF[3:], sens=MARCAS_AF[1:2] + MARCAS_AF[3:], sem="sem A3, C e D",
        segunda_acima=False),
}
COLS = """uasg, modalidade_compra, numero_compra, item, arquivo_origem, situacao_item, criterio_julgamento_item,
status_extracao, versao_parser, valor_estimado, valor_estimado_total, melhor_lance_modo_aberto,
melhor_lance_modo_fechado, lance_aceito, valor_negociado_aceito, quantidade_fornecedores,
cnpj_melhor_lance_aberto, melhor_lance_modo_aberto_outro_fornecedor, lider_aberto_lance_fechado,
reinicios_etapa_fechada, fornecedores_desclassificados, quantidade_desclassificados,
melhor_lance_modo_aberto_validos, melhor_lance_modo_fechado_validos"""
NUM = ["valor_estimado", "valor_estimado_total", "melhor_lance_modo_aberto", "melhor_lance_modo_fechado", "lance_aceito",
       "valor_negociado_aceito", "melhor_lance_modo_aberto_outro_fornecedor", "melhor_lance_modo_aberto_validos",
       "melhor_lance_modo_fechado_validos"]


# ---------------------------------------------------------------- dados
def ler_bancos(caminhos, meses, e):
    partes = []
    for c in caminhos:
        st = os.stat(c)
        con = sqlite3.connect(f"file:{Path(c).resolve().as_posix()}?mode=ro", uri=True)
        partes.append(pd.read_sql_query(f"select {COLS} from itens", con).assign(banco=str(c)))
        con.close()
        assert os.stat(c).st_mtime_ns == st.st_mtime_ns, f"{c} mudou durante a leitura"
    df = pd.concat(partes, ignore_index=True)
    df["mes"] = df.arquivo_origem.str.extract(e["prefixo"] + r"_(\d{4}-\d{2})")[0]
    if df.mes.isna().all():
        sys.exit(f"nenhum arquivo_origem em pasta {e['prefixo']}_<mês>: confira o --modo")
    df["id_compra"] = df.arquivo_origem.str.extract(r"-(\d{17})-(?:s\d+-)?item-")[0]  # homologação ou julgamento (-sN-)
    assert df.id_compra.notna().all(), "arquivo_origem sem id da compra: " + str(df.arquivo_origem[df.id_compra.isna()].head(3).tolist())
    if meses:
        df = df[df.mes.isin(meses)]
    if df.empty:
        sys.exit("nenhum item nos bancos/meses indicados")
    dup = df.duplicated(["uasg", "modalidade_compra", "numero_compra", "item"])
    if dup.any():
        sys.exit(f"{int(dup.sum())} itens repetidos entre os bancos: use --meses ou bancos sem sobreposição")
    versao = df.versao_parser.fillna("0").map(lambda v: tuple(int(x) for x in v.split(".")))
    velhos = df[versao < e["versao_minima"]]
    if len(velhos):
        por_mes = velhos.groupby("mes").size().to_dict()
        minima = ".".join(map(str, e["versao_minima"]))
        sys.exit(f"{len(velhos)} itens extraídos com parser < {minima} {por_mes}: reprocesse com "
                 "python -m extrator_homologacao (docs/07 §6)")
    for c in NUM:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def ligar_pncp(df, pncp_db):
    """Material/serviço e orçamento sigiloso do pncp.db (id_compra + numero_item, registro_principal = 1)."""
    st = os.stat(pncp_db)
    con = sqlite3.connect(f"file:{Path(pncp_db).resolve().as_posix()}?mode=ro", uri=True)
    con.execute("create temp table alvo(id_compra text primary key)")
    con.executemany("insert into temp.alvo values (?)", [(i,) for i in sorted(df.id_compra.dropna().unique())])
    lig = pd.read_sql_query(
        """select c.id_compra, i.numero_item as item, i.material_ou_servico, i.orcamento_sigiloso
           from temp.alvo a join compras c on c.id_compra = a.id_compra
           join itens i on i.numero_controle_pncp = c.numero_controle_pncp and i.registro_principal = 1""", con)
    con.close()
    assert os.stat(pncp_db).st_mtime_ns == st.st_mtime_ns, "pncp.db mudou durante a leitura"
    lig = lig[lig.groupby(["id_compra", "item"]).item.transform("size") == 1]
    return df.merge(lig, on=["id_compra", "item"], how="left")


def preparar(df, e):
    """1ª etapa (c1) e 2ª (c2) conforme o modo; após a 2ª = mín(1ª, 2ª). No AF: aberta → fechada; no FA, o inverso."""
    funil = {"total": len(df)}
    df = df[df.status_extracao == "OK"]; funil["status_OK"] = len(df)
    df = df[df.criterio_julgamento_item.str.startswith("Menor Pre", na=False)]; funil["menor_preco"] = len(df)
    df = df[df.valor_estimado > 0]; funil["estimado_positivo"] = len(df)
    df = df[df[e["c1"]] > 0].copy(); funil[e["funil1"]] = len(df)
    ve, p1, p2 = df.valor_estimado, df[e["c1"]], df[e["c2"]]
    df["melhor_apos"] = np.where(p2.notna() & (p2 > 0), np.minimum(p1, p2.fillna(np.inf)), p1)
    final = df.valor_negociado_aceito.where(df.valor_negociado_aceito > 0, df.lance_aceito)
    df["valor_final"] = final.where(final > 0)
    df["d_final"] = 100 * (1 - df.valor_final / ve)
    p1v, p2v = df[e["c1v"]], df[e["c2v"]]
    df["apos_v"] = np.where(p2v.notna() & (p2v > 0), np.minimum(p1v, p2v.fillna(np.inf)), p1v)
    d1, d2 = e["d1"], e["d2"]
    for suf, pri, ap in [("", p1, df.melhor_apos), ("_v", p1v, df.apos_v)]:
        df[d1 + suf] = 100 * (1 - pri / ve)
        df["d_apos" + suf] = 100 * (1 - ap / ve)
        df["ganho_pp" + suf] = df["d_apos" + suf] - df[d1 + suf]
        df["ganho_rel" + suf] = 100 * (1 - ap / pri)
        df["ajuste_pos" + suf] = df.d_final - df["d_apos" + suf]
    df[d2] = 100 * (1 - p2 / ve)
    df[d2 + "_v"] = 100 * (1 - p2v / ve)
    ok_final = df.d_final.isna() | df.d_final.between(-100, 99)
    df["na_amostra"] = df[d1].between(-100, 99) & df.d_apos.between(-100, 99) & ok_final
    df["validos_ok"] = df.na_amostra & (p1v > 0) & df[d1 + "_v"].between(-100, 99) & df.d_apos_v.between(-100, 99)
    funil["amostra_todos"] = int(df.na_amostra.sum()); funil["amostra_validos"] = int(df.validos_ok.sum())
    # marcas do parser (A e B só fazem sentido no AF; no FA as colunas vêm vazias)
    a, f = df.melhor_lance_modo_aberto, df.melhor_lance_modo_fechado
    o = df.melhor_lance_modo_aberto_outro_fornecedor
    df["fechado_acima_aberto"] = f > a * (1 + TOL)
    df["A_lider_sem_fechado"] = df.lider_aberto_lance_fechado == 0
    df["A3_lider_desclassificado"] = [bool(l) and l in d for l, d in
                                      zip(df.cnpj_melhor_lance_aberto.fillna(""), df.fornecedores_desclassificados.fillna(""))]
    df["B_reiniciada"] = df.reinicios_etapa_fechada.fillna(0) > 0
    df["C_aberto_isolado"] = o.notna() & (a < 0.5 * o)
    df["D_fechado_outlier"] = f > 3 * a
    return df, funil


# ---------------------------------------------------------------- estatística
def media_ic(x, grupos, rng):
    """Média e IC 95% por bootstrap de conglomerados."""
    m = ~np.isnan(x); x, g = x[m], grupos[m]
    if not len(x):
        return {}
    _, idx = np.unique(g, return_inverse=True)
    s, c = np.bincount(idx, weights=x), np.bincount(idx).astype(float)
    k = len(s); reps = np.empty(B)
    for b in range(B):
        w = np.bincount(rng.integers(0, k, k), minlength=k)
        reps[b] = (w * s).sum() / (w * c).sum()
    lo, hi = np.percentile(reps, [2.5, 97.5])
    return {"n": int(len(x)), "media": float(x.mean()), "ic95_inf": float(lo), "ic95_sup": float(hi),
            "mediana": float(np.median(x))}


def resumo_medida(d, suf, nome, rng, e):
    lin = {"medida": nome, "itens": len(d), "compras": int(d.id_compra.nunique())}
    for rot, c in [(e["rot1"], e["d1"]), (e["apos"], "d_apos"), ("ganho_pp", "ganho_pp"),
                   ("ganho_rel", "ganho_rel"), ("final", "d_final")]:
        r = media_ic(d[c + (suf if c != "d_final" else "")].to_numpy(float), d.id_compra.to_numpy(), rng)
        for k, v in r.items():
            if k != "n":
                lin[f"{rot}_{k}"] = v
    ap = d.melhor_apos if suf == "" else d.apos_v
    lin[f"prop_{e['rot2']}_melhorou"] = float((d["ganho_pp" + suf] > 1e-9).mean())
    tf = d.valor_final.notna()
    lin["prop_final_igual_melhor"] = float(np.isclose(d.valor_final[tf], ap[tf]).mean())
    lin["prop_final_acima"] = float((d.valor_final[tf] > ap[tf] * (1 + TOL)).mean())
    lin["prop_final_abaixo"] = float((d.valor_final[tf] < ap[tf] * (1 - TOL)).mean())
    return lin


def decomposicao(d, suf, nome, rng, e):
    x = d[d.valor_final.notna()]
    lin = {"medida": nome, "itens": len(x)}
    for rot, c in [(e["rot1"], e["d1"] + suf), (e["rot2"], "ganho_pp" + suf), ("pos_disputa", "ajuste_pos" + suf),
                   ("final", "d_final")]:
        r = media_ic(x[c].to_numpy(float), x.id_compra.to_numpy(), rng)
        lin[rot], lin[rot + "_ic_inf"], lin[rot + "_ic_sup"] = r["media"], r["ic95_inf"], r["ic95_sup"]
    return lin


def teste_direto(d, suf, nome, e):
    """Melhor valor da 2ª etapa contra o da 1ª, item a item (no FA o aberto já inclui as propostas: dif ≥ 0)."""
    t = d[d[e["d2"] + suf].between(-100, 99)]
    dif = (t[e["d2"] + suf] - t[e["d1"] + suf]).to_numpy()
    if len(dif) < 2:
        return {"medida": nome, "n": len(dif)}
    return {"medida": nome, "n": len(dif), "media_dif_pp": float(dif.mean()), "mediana_dif_pp": float(np.median(dif)),
            f"{e['prop2']}_melhor": float((dif > 0).mean()), f"{e['prop2']}_pior": float((dif < 0).mean()),
            "wilcoxon_p": float(stats.wilcoxon(dif, zero_method="pratt").pvalue)}


def regressao(d, suf, nome, com_pncp, e):
    """Primeira diferença de 100·ln(preço) entre as etapas (= FE de item com 2 observações), EP por UASG."""
    pri = d[e["c1"]] if suf == "" else d[e["c1v"]]
    ap = d.melhor_apos if suf == "" else d.apos_v
    r = d.assign(dy=100 * np.log(ap) - 100 * np.log(pri)).copy()
    r = r[r.quantidade_fornecedores.notna() & (r.quantidade_fornecedores > 0) & (r.valor_estimado_total > 0)]
    mods = ["ln_lic"]
    r["ln_lic"] = np.log(r.quantidade_fornecedores.astype(float))
    if com_pncp:
        r = r[r.material_ou_servico.isin(["M", "S"]) & r.orcamento_sigiloso.isin([0, 1])]
        r["sigiloso"] = r.orcamento_sigiloso.astype(float); r["servico"] = (r.material_ou_servico == "S").astype(float)
        mods += ["sigiloso", "servico"]
    cols = [r[m].to_numpy(float) for m in mods] + [np.log(r.valor_estimado_total.astype(float)).to_numpy()]
    L = e["letra"]
    nomes = [f"{L}_x_{m}" for m in mods] + [f"{L}_x_ln_valor"]
    for m in sorted(r.mes.unique())[1:]:
        cols.append((r.mes == m).astype(float).to_numpy()); nomes.append(f"{L}_x_mes_{m}")
    Z = np.column_stack(cols); X = np.column_stack([np.ones(len(r)), Z - Z.mean(axis=0)])
    keep = np.r_[True, Z.std(axis=0) > 0]; X = X[:, keep]; nomes = [e["coef"]] + [n for n, k in zip(nomes, keep[1:]) if k]
    y = r.dy.to_numpy(); A = np.linalg.inv(X.T @ X); b = A @ X.T @ y; u = y - X @ b
    _, idx = np.unique(r.uasg.to_numpy(), return_inverse=True); G = idx.max() + 1; n, k = X.shape
    S = np.zeros((G, k)); np.add.at(S, idx, X * u[:, None])
    V = A @ (S.T @ S) @ A * (G / (G - 1)) * ((n - 1) / (n - k)); se = np.sqrt(np.diag(V))
    p = 2 * stats.t.sf(np.abs(b / se), G - 1)
    return [{"medida": nome, "regressor": nm, "coef": float(b[i]), "ep": float(se[i]), "p": float(p[i]), "n": n,
             "uasgs": int(G)} for i, nm in enumerate(nomes)]


# ---------------------------------------------------------------- execução
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db", action="append", type=Path, required=True, help="banco da extração (repita para vários)")
    ap.add_argument("--meses", nargs="*", help="meses AAAA-MM (padrão: todos os dos bancos)")
    ap.add_argument("--pncp-db", type=Path, help="dados/pncp.db para material/serviço e sigilo (opcional)")
    ap.add_argument("--saida", type=Path, help="pasta de saída (padrão: <dados>/analise_etapas/<meses>; "
                                               "no Fechado-Aberto, fechado-aberto_<meses>)")
    ap.add_argument("--modo", choices=list(MODOS), default="aberto-fechado",
                    help="modo de disputa dos bancos (padrão aberto-fechado); define a ordem das etapas")
    args = ap.parse_args(argv)
    e = MODOS[args.modo]

    df = ler_bancos(args.db, args.meses, e)
    com_pncp = bool(args.pncp_db)
    if com_pncp:
        df = ligar_pncp(df, args.pncp_db)
    df, funil = preparar(df, e)
    meses = sorted(df.mes.dropna().unique())
    nome_saida = "_".join(meses) if len(meses) <= 3 else f"{meses[0]}_a_{meses[-1]}"
    if args.modo != "aberto-fechado":
        nome_saida = f"{e['prefixo']}_{nome_saida}"
    saida = args.saida or DADOS / "analise_etapas" / nome_saida
    saida.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEMENTE)

    s = df[df.na_amostra].copy()
    v = s[s.validos_ok].copy()
    R = {"modo": args.modo, "ordem_etapas": [e["rot1"], e["rot2"]],
         "bancos": [str(p) for p in args.db], "meses": meses, "funil": funil, "com_pncp_db": com_pncp,
         "versoes_parser": df.versao_parser.value_counts().to_dict(), "compras": int(s.id_compra.nunique()),
         "uasgs": int(s.uasg.nunique())}
    T = {}
    medidas = [("todos os fornecedores", "", s), ("só fornecedores válidos", "_v", v)]
    T["principais"] = pd.DataFrame([resumo_medida(d, suf, nome, rng, e) for nome, suf, d in medidas])
    comum = s[s.validos_ok & s.valor_final.notna()]
    T["decomposicao"] = pd.DataFrame([decomposicao(comum, suf, nome, rng, e) for nome, suf, _ in medidas])
    T["teste_direto"] = pd.DataFrame([teste_direto(d, suf, nome, e) for nome, suf, d in medidas])
    reg = []
    for nome, suf, d in medidas:
        reg += regressao(d, suf, nome, com_pncp, e)
    T["regressao"] = pd.DataFrame(reg)

    marcas = e["marcas"]
    if e["segunda_acima"]:
        # AF: lance fechado acima do aberto (a fechada piorou); no FA o aberto inclui as propostas e nunca fica acima
        fa = s[s.fechado_acima_aberto]
        T["marcas"] = pd.DataFrame([{"marca": m, "itens_amostra": int(s[m].sum()), "prop_amostra": float(s[m].mean()),
                                     "itens_fechado_acima_aberto": int(fa[m].sum())} for m in marcas]
                                   + [{"marca": "fechado_acima_aberto", "itens_amostra": len(fa),
                                       "prop_amostra": float(s.fechado_acima_aberto.mean())}])
    else:
        T["marcas"] = pd.DataFrame([{"marca": m, "itens_amostra": int(s[m].sum()), "prop_amostra": float(s[m].mean())}
                                    for m in marcas])
    sens = []
    for m in e["sens"] + [e["sem"]]:
        fora = s[e["sens"]].any(axis=1) if m.startswith("sem") else s[m]
        sens.append({**resumo_medida(s[~fora], "", "todos os fornecedores", rng, e), "recorte": m if m.startswith("sem") else f"sem {m}"})
    T["sensibilidade_todos"] = pd.DataFrame(sens)
    por_mes = []
    for mes, d in s.groupby("mes"):
        for nome, suf, dd in [("todos os fornecedores", "", d), ("só fornecedores válidos", "_v", d[d.validos_ok])]:
            por_mes.append({"mes": mes, **resumo_medida(dd, suf, nome, rng, e)})
    T["por_mes"] = pd.DataFrame(por_mes)

    for k, t in T.items():
        R[k] = t.to_dict("records")
    (saida / "resultados.json").write_text(json.dumps(R, ensure_ascii=False, indent=2, default=float), encoding="utf-8")
    with pd.ExcelWriter(saida / "tabelas.xlsx") as xw:
        pd.DataFrame(list(funil.items()), columns=["etapa_do_filtro", "itens"]).to_excel(xw, sheet_name="funil", index=False)
        for k, t in T.items():
            t.to_excel(xw, sheet_name=k[:31], index=False)
    cols = ["mes", "id_compra", "uasg", "numero_compra", "item", "valor_estimado", "melhor_lance_modo_aberto",
            "melhor_lance_modo_fechado", "melhor_apos", "melhor_lance_modo_aberto_validos",
            "melhor_lance_modo_fechado_validos", "apos_v", "valor_final", "quantidade_fornecedores", e["d1"], "d_apos",
            "ganho_pp", e["d1"] + "_v", "d_apos_v", "ganho_pp_v", "d_final", "na_amostra", "validos_ok"] + marcas
    df[cols].to_csv(saida / "por_item.csv.gz", index=False, compression="gzip")

    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(f"modo {args.modo} (etapas: {e['rot1']} -> {e['rot2']}); meses {meses}; amostra: {funil['amostra_todos']} itens "
          f"(todos), {funil['amostra_validos']} (válidos); saída: {saida}")
    p = T["principais"]
    print(p[["medida", "itens", f"{e['rot1']}_media", f"{e['apos']}_media", "ganho_pp_media", "ganho_pp_ic95_inf",
             "ganho_pp_ic95_sup", "ganho_rel_media", "final_media", "prop_final_igual_melhor"]].round(2).to_string(index=False))
    print(T["decomposicao"][["medida", "itens", e["rot1"], e["rot2"], "pos_disputa", "final"]].round(2).to_string(index=False))
    L = e["letra"]
    rr = T["regressao"]; print(rr[rr.regressor.eq(e["coef"]) | rr.regressor.str.match(rf"{L}_x_(ln_lic|sigiloso|servico)")].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
