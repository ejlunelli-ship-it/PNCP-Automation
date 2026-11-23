"""Diagnósticos de viabilidade para o parecer sobre o desenho causal A × AF (23/11/2026). Só leitura; nada é estimado
como efeito causal.

A. Como o modo varia dentro da unidade (pncp.db, compras de Pregão Eletrônico A/AF, nov/2022 a out/2026):
   A1. sequência das compras nas unidades mistas: nº de trocas de modo observado ÷ esperado sob ordem aleatória
       (Wald–Wolfowitz). Razão ≪ 1 = regimes (blocos no tempo); ≈ 1 = escolha intercalada compra a compra;
   A2. episódios de mudança de regime na unidade (A→AF e AF→A): ≤ 10% de AF nos 6 meses antes e ≥ 90% nos 6 meses
       depois (ou o inverso), com ≥ 5 compras de cada lado; simultaneidade dentro do mesmo CNPJ.
B. Suporte de desenhos de pareamento alternativos (painel_principal.pkl de 16/11, 5 classes de consumo):
   itens AF com ao menos um item A comparável, órgãos, concentração.
C. Mecanismo: no AF, o desconto da etapa aberta (PDF) é comparável ao desconto final do Aberto? Estratos
   CNPJ × produto × ano × sigilo (o "simples" de 17/11), pesos AF = 1 e A = n_AF/n_A, EP por CNPJ.

Uso (da pasta PNCP-Automation):
    python analises/parecer_desenho_causal_20261123/diagnosticos.py --pncp-db ../dados/pncp.db \
        --extracao dados/extracao/aberto-fechado_parser-1.9.1.db
Saída: diagnosticos.json nesta pasta.
"""
import argparse, json, os, sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

AQUI = Path(__file__).resolve().parent
ANALISE = AQUI.parents[2] / "analise"
R = {}


def salvar():
    (AQUI / "diagnosticos.json").write_text(json.dumps(R, ensure_ascii=False, indent=1, default=float), encoding="utf-8")


def ro(p):
    return sqlite3.connect(f"file:{Path(p).resolve().as_posix()}?mode=ro", uri=True)


# ----------------------------------------------------------------------------------------------------------- A
SQL = """SELECT c.fonte, c.orgao_cnpj AS cnpj,
       CASE WHEN c.fonte = 'dados_abertos' THEN c.uasg ELSE c.orgao_cnpj || '-' || COALESCE(c.codigo_unidade, '') END AS unidade,
       c.esfera, c.uf, substr(COALESCE(c.data_abertura_proposta, c.data_publicacao), 1, 10) AS dia,
       c.numero_controle_pncp AS compra, c.modo_disputa = 'Aberto-Fechado' AS af
FROM compras c
WHERE c.modalidade_nome LIKE 'Preg%Eletr%' AND c.modo_disputa IN ('Aberto', 'Aberto-Fechado')
  AND substr(c.data_publicacao, 1, 7) BETWEEN '2022-11' AND '2026-10'"""


def parte_a(pncp_db):
    st = os.stat(pncp_db)
    con = ro(pncp_db)
    c = pd.read_sql_query(SQL, con)
    con.close()
    assert os.stat(pncp_db).st_mtime_ns == st.st_mtime_ns and os.stat(pncp_db).st_size == st.st_size
    c["fonte"] = np.where(c.fonte.eq("dados_abertos"), "Compras.gov.br", "outras")
    c["dia"] = pd.to_datetime(c.dia, errors="coerce")
    c = c[c.dia.notna()].sort_values(["unidade", "dia", "compra"])
    c["mes"] = c.dia.dt.year * 12 + c.dia.dt.month - 1
    out = {"compras": len(c), "unidades": c.unidade.nunique()}

    # A1: trocas na sequência das unidades mistas
    g = c.groupby("unidade")
    u = g.agg(n=("af", "size"), naf=("af", "sum"), fonte=("fonte", "first"))
    u["s"] = u.naf / u.n
    mistas = u[(u.n >= 20) & u.s.between(0.05, 0.95)].index
    m = c[c.unidade.isin(mistas)]
    trocas = m.groupby("unidade").af.apply(lambda x: int((x.to_numpy()[1:] != x.to_numpy()[:-1]).sum()))
    uu = u.loc[mistas].assign(trocas=trocas)
    n1, n2, n = uu.naf, uu.n - uu.naf, uu.n
    # Wald–Wolfowitz: sequências (runs) = trocas + 1; E[runs] = 1 + 2·n1·n2/n
    uu["runs"] = uu.trocas + 1
    esp = 1 + 2 * n1 * n2 / n
    var = 2 * n1 * n2 * (2 * n1 * n2 - n) / (n ** 2 * (n - 1))
    uu["razao"] = uu.runs / esp
    uu["z"] = (uu.runs - esp) / np.sqrt(var)
    a1 = {}
    for fonte, x in uu.groupby("fonte"):
        a1[fonte] = {"unidades_mistas": len(x), "compras": int(x.n.sum()),
                     "razao_sequencias_obs_esp_mediana": float(x.razao.median()),
                     "razao_p25": float(x.razao.quantile(.25)), "razao_p75": float(x.razao.quantile(.75)),
                     "razao_ponderada_compras": float((x.runs.sum()) / esp[x.index].sum()),
                     "pct_unidades_regime_z_menor_-1.96": 100 * float((x.z < -1.96).mean()),
                     "pct_unidades_razao_menor_0.5": 100 * float((x.razao < .5).mean())}
    out["A1_sequencia_unidades_mistas"] = a1
    base = u[u.n >= 20]
    out["A1_unidades_20mais"] = {f: {"unidades": len(x), "pct_quase_so_A(<5%AF)": 100 * float((x.s < .05).mean()),
                                     "pct_mistas": 100 * float(x.s.between(.05, .95).mean()),
                                     "pct_quase_so_AF(>95%)": 100 * float((x.s > .95).mean())}
                                 for f, x in base.groupby("fonte")}

    # A2: episódios de mudança de regime (mensal, janelas de 6 meses)
    mm = c.groupby(["unidade", "mes"]).agg(n=("af", "size"), naf=("af", "sum")).reset_index()
    eventos = []
    for un, x in mm.groupby("unidade", sort=False):
        if len(x) < 4:
            continue
        idx = np.arange(x.mes.min(), x.mes.max() + 1)
        n_ = x.set_index("mes").n.reindex(idx, fill_value=0).to_numpy()
        a_ = x.set_index("mes").naf.reindex(idx, fill_value=0).to_numpy()
        cn, ca = np.concatenate([[0], n_.cumsum()]), np.concatenate([[0], a_.cumsum()])
        ultimo = -99
        for j in range(6, len(idx) - 5):
            nb, ab = cn[j] - cn[j - 6], ca[j] - ca[j - 6]
            na, aa = cn[j + 6] - cn[j], ca[j + 6] - ca[j]
            if nb < 5 or na < 5 or n_[j] == 0:
                continue
            sb, sa = ab / nb, aa / na
            tipo = "A->AF" if (sb <= .10 and sa >= .90) else "AF->A" if (sb >= .90 and sa <= .10) else None
            if tipo and j - ultimo > 6:
                eventos.append({"unidade": un, "mes": int(idx[j]), "tipo": tipo, "n_antes": int(nb), "n_depois": int(na)})
                ultimo = j
    ev = pd.DataFrame(eventos)
    info = c.drop_duplicates("unidade").set_index("unidade")[["fonte", "cnpj", "esfera", "uf"]]
    ev = ev.join(info, on="unidade")
    a2 = {}
    for (fonte, tipo), x in ev.groupby(["fonte", "tipo"]):
        # simultaneidade: outra unidade do mesmo CNPJ com evento do mesmo tipo a até 1 mês
        sim = x.groupby("cnpj").apply(lambda y: int(sum(((y.mes.to_numpy()[:, None] - y.mes.to_numpy()[None, :]).__abs__() <= 1).sum(1) > 1)))
        a2[f"{fonte} {tipo}"] = {"eventos": len(x), "unidades": x.unidade.nunique(), "cnpjs": x.cnpj.nunique(),
                                 "compras_6m_antes": int(x.n_antes.sum()), "compras_6m_depois": int(x.n_depois.sum()),
                                 "eventos_com_outra_unidade_do_cnpj_no_mesmo_mes_ou_vizinho": int(sim.sum()),
                                 "por_esfera": x.esfera.value_counts().to_dict(),
                                 "por_ano": (x.mes // 12).value_counts().sort_index().to_dict()}
    out["A2_mudancas_de_regime"] = a2
    out["A2_unidades_controle_20mais"] = {f: {"sempre_A(<5%AF)": int((x.s < .05).sum()), "sempre_AF(>95%)": int((x.s > .95).sum())}
                                          for f, x in base.groupby("fonte")}
    ev.to_csv(AQUI / "eventos_regime.csv", index=False)
    R["A"] = out
    salvar()
    return ev


# ----------------------------------------------------------------------------------------------------------- B
def carregar_painel():
    pasta = ANALISE / "painel_efeitos_fixos_20261116"
    d = pd.read_pickle(pasta / "painel_principal.pkl")
    d = d[d.modo.isin([0, 1]) & d.sigilo.isin([0, 1])].copy()
    d["faixa_q"] = np.floor(np.log2(d.q)).astype("int32")
    return d, json.loads((pasta / "mapas.json").read_text(encoding="utf-8"))


def suporte(d, chave, janela=None):
    """Itens AF com pelo menos um A no mesmo estrato (e a até `janela` dias, se dada)."""
    nm = d.groupby(chave, observed=True).modo.transform("nunique")
    z = d[nm.eq(2)]
    if janela is None:
        return z[z.modo.eq(1)]
    ok = []
    for _, g in z.groupby(chave, observed=True, sort=False):
        da = np.sort(g.abertura[g.modo.eq(0)].to_numpy())
        f = g[g.modo.eq(1)]
        pos = np.searchsorted(da, f.abertura.to_numpy())
        esq = np.abs(f.abertura.to_numpy() - da[np.clip(pos - 1, 0, len(da) - 1)])
        dir_ = np.abs(da[np.clip(pos, 0, len(da) - 1)] - f.abertura.to_numpy())
        ok.append(f[np.minimum(esq, dir_) <= janela])
    return pd.concat(ok) if ok else z.iloc[:0]


def resumo_suporte(af, total_af):
    s = af.orgao.value_counts(normalize=True)
    return {"itens_AF": len(af), "pct_dos_AF": 100 * len(af) / total_af, "compras_AF": af.compra.nunique(),
            "orgaos": af.orgao.nunique(), "uasgs": af.uasg.nunique(), "produtos": af.produto.nunique(),
            "maior_orgao_pct": 100 * float(s.iloc[0]) if len(s) else None,
            "orgaos_efetivos_1_sobre_HHI": float(1 / (s ** 2).sum()) if len(s) else None}


def parte_b(d):
    tot = int(d.modo.eq(1).sum())
    k = {"CNPJ×produto×ano×sigilo (simples 17/11)": (["orgao", "produto", "ano", "sigilo"], None),
         "CNPJ×produto×ano×sigilo×SRP×benef×faixaQ (principal 17/11)": (["orgao", "produto", "ano", "sigilo", "srp", "beneficio", "faixa_q"], None),
         "UASG×produto (qualquer data)": (["uasg", "produto"], None),
         "UASG×produto, ±365 dias": (["uasg", "produto"], 365),
         "UASG×produto, ±180 dias": (["uasg", "produto"], 180),
         "UASG×produto, ±90 dias": (["uasg", "produto"], 90),
         "UASG×produto×sigilo×SRP×faixaQ, ±180 dias": (["uasg", "produto", "sigilo", "srp", "faixa_q"], 180),
         "UASG×produto×sigilo×SRP×faixaQ, ±90 dias": (["uasg", "produto", "sigilo", "srp", "faixa_q"], 90)}
    out = {"itens_AF_no_painel": tot, "itens_A_no_painel": int(d.modo.eq(0).sum()),
           "orgaos_com_AF": int(d[d.modo.eq(1)].orgao.nunique())}
    for nome, (chave, jan) in k.items():
        out[nome] = resumo_suporte(suporte(d, chave, jan), tot)
        print("B", nome, out[nome]["itens_AF"], flush=True)
    R["B_suporte_pareamento"] = out
    salvar()


# ----------------------------------------------------------------------------------------------------------- C
def parte_c(d, mapas, extracao):
    con = ro(extracao)
    e = pd.read_sql_query("""select arquivo_origem, item, status_extracao, valor_estimado, melhor_lance_modo_aberto,
                                    melhor_lance_modo_fechado, lance_aceito, valor_negociado_aceito, quantidade_fornecedores,
                                    criterio_julgamento_item
                             from itens where modo_disputa = 'Aberto/Fechado'""", con)
    con.close()
    e["id_compra"] = e.arquivo_origem.str.extract(r"-(\d{17})-(?:s\d+-)?item-")[0]
    for col in ["item", "valor_estimado", "melhor_lance_modo_aberto", "melhor_lance_modo_fechado", "lance_aceito",
                "valor_negociado_aceito", "quantidade_fornecedores"]:
        e[col] = pd.to_numeric(e[col], errors="coerce")
    e = e[e.status_extracao.eq("OK") & e.valor_estimado.gt(0) & e.melhor_lance_modo_aberto.gt(0)
          & e.criterio_julgamento_item.str.startswith("Menor Pre", na=False)]
    e = e[~e.duplicated(["id_compra", "item"], keep=False)]
    ab, fe = e.melhor_lance_modo_aberto, e.melhor_lance_modo_fechado
    e["apos"] = np.where(fe.gt(0), np.minimum(ab, fe.fillna(np.inf)), ab)
    fin = e.valor_negociado_aceito.where(e.valor_negociado_aceito > 0, e.lance_aceito)
    e["d_aberta_pdf"] = 100 * (1 - ab / e.valor_estimado)
    e["d_apos_fechada_pdf"] = 100 * (1 - e.apos / e.valor_estimado)
    e["d_final_pdf"] = 100 * (1 - fin.where(fin > 0) / e.valor_estimado)
    # mesmas grandezas em log do preço unitário (não dependem do preço estimado)
    e["l_aberta_pdf"] = np.log(ab)
    e["l_apos_fechada_pdf"] = np.log(e.apos)
    e["l_final_pdf"] = np.log(fin.where(fin > 0))
    inv = pd.Series(list(mapas["id_compra"].keys()), index=list(mapas["id_compra"].values()))
    d = d.copy()
    d["id17"] = inv.loc[d.id_compra].to_numpy()
    d = d[np.isfinite(d.r) & d.r.gt(0)]
    d["d_final_api"] = 100 * (1 - d.p / d.r)
    d = d.merge(e[["id_compra", "item", "d_aberta_pdf", "d_apos_fechada_pdf", "d_final_pdf", "quantidade_fornecedores",
                   "l_aberta_pdf", "l_apos_fechada_pdf", "l_final_pdf"]]
                .rename(columns={"id_compra": "id17"}), on=["id17", "item"], how="left")
    af_ok = d.modo.eq(1) & d.d_aberta_pdf.notna() & d.d_final_pdf.notna()
    z = d[d.modo.eq(0) | af_ok]
    z = z[z.d_final_api.between(-100, 100) & (z.modo.eq(0) | (z.d_aberta_pdf.between(-100, 100) & z.d_final_pdf.between(-100, 100)))]
    chave = ["orgao", "produto", "ano", "sigilo"]
    z = z[z.groupby(chave, observed=True).modo.transform("nunique").eq(2)].copy()
    z["cel"] = z.groupby(chave, observed=True).ngroup()
    nAF = z[z.modo.eq(1)].groupby("cel").size()
    nA = z[z.modo.eq(0)].groupby("cel").size()
    z["w"] = np.where(z.modo.eq(1), 1.0, (nAF / nA).reindex(z.cel).to_numpy())
    out = {"itens_AF_ligados_ao_PDF": int(af_ok.sum()), "itens_AF": int(z.modo.eq(1).sum()), "itens_A": int(z.modo.eq(0).sum()),
           "celulas": int(z.cel.nunique()), "orgaos": int(z.orgao.nunique())}

    def media(col, modo):
        x = z[z.modo.eq(modo)]
        return float(np.average(x[col], weights=x.w))

    top = z[z.modo.eq(1)].orgao.value_counts().index[0]
    out["maior_orgao_pct_AF"] = 100 * float(z[z.modo.eq(1)].orgao.eq(top).mean())

    def contraste(col_af, col_a, sem_top=False):
        """média ponderada (AF: col_af) − (A pareado: col_a), EP por CNPJ via scores de célula."""
        zz = z[z.orgao.ne(top)] if sem_top else z
        a = zz[zz.modo.eq(1)].groupby("cel").agg(mAF=(col_af, "mean"), n=(col_af, "size"), orgao=("orgao", "first"))
        b = zz[zz.modo.eq(0)].groupby("cel")[col_a].mean().rename("mA")
        c = a.join(b)
        c["delta"] = c.mAF - c.mA
        p = c.n / c.n.sum()
        beta = float((p * c.delta).sum())
        sc = (c.n * (c.delta - beta) / c.n.sum()).groupby(c.orgao).sum().to_numpy()
        G = len(sc)
        se = float(np.sqrt(G / (G - 1) * (sc ** 2).sum()))
        t = stats.t.ppf(.975, G - 1)
        por_org = c.assign(wd=c.n * c.delta).groupby("orgao")[["wd", "n"]].sum()
        por_org = por_org.wd / por_org.n
        return {"diferenca": beta, "ep": se, "ic95": [beta - t * se, beta + t * se], "orgaos": G,
                "pct_orgaos_com_diferenca_negativa": 100 * float((por_org < 0).mean())}

    out["medias_pp"] = {"A: desconto final (API)": media("d_final_api", 0),
                        "AF: desconto da etapa aberta (PDF)": media("d_aberta_pdf", 1),
                        "AF: desconto após a fechada (PDF)": media("d_apos_fechada_pdf", 1),
                        "AF: desconto final (PDF)": media("d_final_pdf", 1),
                        "AF: desconto final (API)": media("d_final_api", 1)}
    out["contrastes"] = {"AF aberta (PDF) − A final (API)": contraste("d_aberta_pdf", "d_final_api"),
                         "AF final (API) − A final (API)": contraste("d_final_api", "d_final_api"),
                         "AF final (PDF) − A final (API)": contraste("d_final_pdf", "d_final_api")}
    out["contrastes_sem_maior_orgao"] = {"AF aberta (PDF) − A final (API)": contraste("d_aberta_pdf", "d_final_api", True),
                                         "AF final (API) − A final (API)": contraste("d_final_api", "d_final_api", True)}
    # em log do preço unitário (log-pontos; negativo = AF mais barato)
    z["l_api"] = np.log(z.p)
    out["contrastes_log_preco"] = {"AF aberta (PDF) − A final (API)": contraste("l_aberta_pdf", "l_api"),
                                   "AF após a fechada (PDF) − A final (API)": contraste("l_apos_fechada_pdf", "l_api"),
                                   "AF final (PDF) − A final (API)": contraste("l_final_pdf", "l_api"),
                                   "AF final (API) − A final (API)": contraste("l_api", "l_api"),
                                   "AF aberta (PDF) − A final (API), sem o maior órgão": contraste("l_aberta_pdf", "l_api", True),
                                   "AF final (API) − A final (API), sem o maior órgão": contraste("l_api", "l_api", True)}
    xa = z[z.modo.eq(1)]
    out["checagem_AF_final_PDF_menos_API_log_mediana"] = float((xa.l_final_pdf - xa.l_api).median())
    out["medianas_pp"] = {"A final (API)": float(z[z.modo.eq(0)].d_final_api.median()),
                          "AF aberta (PDF)": float(z[z.modo.eq(1)].d_aberta_pdf.median()),
                          "AF final (API)": float(z[z.modo.eq(1)].d_final_api.median())}
    x = z[z.modo.eq(1)]
    out["AF_pct_aberta_igual_final_pdf"] = 100 * float((x.d_aberta_pdf.round(6) == x.d_final_pdf.round(6)).mean())
    R["C_etapa_aberta_vs_aberto"] = out
    salvar()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pncp-db", type=Path, required=True)
    ap.add_argument("--extracao", type=Path, required=True)
    ap.add_argument("--partes", default="ABC")
    a = ap.parse_args(argv)
    if (AQUI / "diagnosticos.json").exists():
        R.update(json.loads((AQUI / "diagnosticos.json").read_text(encoding="utf-8")))
    if "A" in a.partes:
        parte_a(a.pncp_db)
        print("A ok", flush=True)
    if "B" in a.partes or "C" in a.partes:
        d, mapas = carregar_painel()
        if "B" in a.partes:
            parte_b(d)
            print("B ok", flush=True)
        if "C" in a.partes:
            parte_c(d, mapas, a.extracao)
            print("C ok", flush=True)
    print(json.dumps(R, ensure_ascii=False, indent=1, default=float))
    print("FIM ok")


if __name__ == "__main__":
    main()
