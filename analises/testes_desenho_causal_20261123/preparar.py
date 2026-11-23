"""Base dos testes do desenho causal A × AF (pré-registro: protocolo.md). Só leitura do pncp.db.

Uso (da pasta PNCP-Automation):
    python analises/testes_desenho_causal_20261123/preparar.py --pncp-db ../dados/pncp.db

Etapa 1 (extrair, ~20 min; guarda cache): compras de Pregão Eletrônico Aberto/Aberto-Fechado do Compras.gov.br
(`fonte = 'dados_abertos'`), abertura de 2022-01 a 2026-09, e os itens de material (registro principal) das compras
com abertura até 2026-03. De 2026-04 em diante a API deixou de trazer o CATMAT (6 mil de 167 mil itens em 2026-05).

Etapa 2 (derivar): índices do item contra o mesmo produto (CATMAT + unidade de fornecimento padronizada) no mesmo
trimestre nas OUTRAS unidades (>= 5 itens de >= 3 unidades): preço (e), estimado (eR), quantidade (eq); competição
esperada; fornecedor novo; desfechos por compra; painéis unidade × mês; eventos de mudança de regime.

Saídas em dados/testes_desenho_causal/ (fora do git): compras_brutas.pkl, itens_brutos.pkl, itens.pkl, compras.pkl,
paineis.npz. Nesta pasta: eventos.csv (só modo de disputa, sem desfecho) e base.json (contagens).
"""
import argparse, json, re, unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

import comum as C

SQL_COMPRAS = f"""SELECT c.numero_controle_pncp AS compra, c.uasg AS unidade, c.orgao_cnpj AS cnpj, c.esfera, c.uf,
  c.modo_disputa = 'Aberto-Fechado' AS af, c.srp, substr(c.data_publicacao, 1, 10) AS pub,
  substr(c.data_abertura_proposta, 1, 10) AS abertura
FROM compras c
WHERE c.fonte = 'dados_abertos' AND c.modalidade_nome LIKE 'Preg%Eletr%' AND c.modo_disputa IN ('Aberto', 'Aberto-Fechado')
  AND substr(c.data_abertura_proposta, 1, 7) BETWEEN '{C.INI}' AND '{C.FIM_MODOS}'"""

SQL_ITENS = f"""SELECT i.numero_controle_pncp AS compra, i.numero_item AS item, i.cod_item_catalogo AS catmat,
  i.codigo_classe AS classe, i.unidade_medida AS un, i.criterio_julgamento AS criterio, i.tipo_beneficio AS beneficio,
  i.orcamento_sigiloso AS sigilo, i.situacao_item AS situacao, i.quantidade AS q, i.valor_unitario_estimado AS r,
  i.valor_unitario_resultado AS p, substr(i.data_resultado, 1, 10) AS data_resultado, i.cod_fornecedor AS fornecedor
FROM compras c JOIN itens i ON i.numero_controle_pncp = c.numero_controle_pncp
WHERE c.fonte = 'dados_abertos' AND c.modalidade_nome LIKE 'Preg%Eletr%' AND c.modo_disputa IN ('Aberto', 'Aberto-Fechado')
  AND substr(c.data_abertura_proposta, 1, 7) BETWEEN '{C.INI}' AND '{C.FIM_ITENS}'
  AND i.registro_principal = 1 AND i.material_ou_servico = 'M'"""

# Unidade de fornecimento: sinônimos frequentes (definidos antes de estimar; só a grafia, nunca o conteúdo)
SINONIMOS = {
    "UN": "UNIDADE", "UND": "UNIDADE", "UNID": "UNIDADE", "UNIDADES": "UNIDADE", "UNIT": "UNIDADE", "UNITARIO": "UNIDADE",
    "UNIDADE 1": "UNIDADE", "1 UNIDADE": "UNIDADE", "U": "UNIDADE", "UNI": "UNIDADE", "UNIDADE UN": "UNIDADE",
    "CX": "CAIXA", "CXA": "CAIXA", "PCT": "PACOTE", "PC": "PECA", "PCA": "PECA", "PECAS": "PECA",
    "KG": "QUILOGRAMA", "QUILO": "QUILOGRAMA", "KILO": "QUILOGRAMA", "KILOGRAMA": "QUILOGRAMA", "QUILOGRAMAS": "QUILOGRAMA",
    "L": "LITRO", "LT": "LITRO", "LTS": "LITRO", "LITROS": "LITRO", "G": "GRAMA", "GR": "GRAMA", "GRAMAS": "GRAMA",
    "ML": "MILILITRO", "M": "METRO", "MT": "METRO", "MTS": "METRO", "METROS": "METRO", "M2": "METRO QUADRADO",
    "M3": "METRO CUBICO", "FR": "FRASCO", "FRS": "FRASCO", "CP": "COMPRIMIDO", "COMP": "COMPRIMIDO", "CPR": "COMPRIMIDO",
    "AMP": "AMPOLA", "RL": "ROLO", "GL": "GALAO", "FD": "FARDO", "DZ": "DUZIA", "CJ": "CONJUNTO", "JG": "JOGO",
    "SC": "SACO", "TB": "TUBO", "BL": "BLOCO", "RS": "RESMA", "PR": "PAR", "FL": "FOLHA", "CT": "CARTELA",
    "BD": "BALDE", "BB": "BOMBONA", "LATA 1": "LATA", "ENV": "ENVELOPE", "SACHE": "SACHE", "FA": "FRASCO AMPOLA",
}


def norm_un(s):
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return None
    t = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().upper()
    t = re.sub(r"[^A-Z0-9 ]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return SINONIMOS.get(t, t) or None


def extrair(pncp_db):
    fc, fi = C.DADOS / "compras_brutas.pkl", C.DADOS / "itens_brutos.pkl"
    if fc.exists() and fi.exists():
        return pd.read_pickle(fc), pd.read_pickle(fi)
    sig = C.assinatura(pncp_db)
    con = C.ro(pncp_db)
    c = pd.read_sql_query(SQL_COMPRAS, con)
    print("compras", len(c), flush=True)
    partes = []
    for k, x in enumerate(pd.read_sql_query(SQL_ITENS, con, chunksize=400_000)):
        for col in ["compra", "classe", "un", "criterio", "beneficio", "situacao", "fornecedor", "data_resultado"]:
            x[col] = x[col].astype("string").astype("category")
        x["catmat"] = pd.to_numeric(x.catmat, errors="coerce").astype("float64")
        for col in ["q", "r", "p"]:
            x[col] = pd.to_numeric(x[col], errors="coerce").astype("float64")
        x["item"] = pd.to_numeric(x.item, errors="coerce").astype("int32")
        x["sigilo"] = pd.to_numeric(x.sigilo, errors="coerce").astype("float32")
        partes.append(x)
        print("itens lote", k, len(x), flush=True)
    con.close()
    assert C.assinatura(pncp_db) == sig, "pncp.db mudou durante a leitura"
    from pandas.api.types import union_categoricals
    cats = ["compra", "classe", "un", "criterio", "beneficio", "situacao", "fornecedor", "data_resultado"]
    for col in cats:
        uc = union_categoricals([p[col] for p in partes]).categories
        for p in partes:
            p[col] = pd.Categorical(p[col].astype(object), categories=uc)
    i = pd.concat(partes, ignore_index=True)
    C.DADOS.mkdir(parents=True, exist_ok=True)
    c.to_pickle(fc)
    i.to_pickle(fi)
    return c, i


def eventos_regime(N, A, unidades, W=6, lim=0.5, nmin=5, sep=6):
    """Mudanças de regime datadas pelo ponto de quebra: para cada mês j com compra, dif_j = parcela de AF em
    [j, j+W-1] - parcela em [j-W, j-1] (>= nmin compras de cada lado). Candidatos |dif| >= lim; aceita-se o maior
    |dif| e suprimem-se os candidatos a menos de `sep` meses (supressão de não máximos)."""
    U, M = N.shape
    cn = np.concatenate([np.zeros((U, 1)), N.cumsum(1)], 1)
    ca = np.concatenate([np.zeros((U, 1)), A.cumsum(1)], 1)
    dif = np.full((U, M), np.nan)
    for j in range(W, M - W + 1):
        nb, na = cn[:, j] - cn[:, j - W], cn[:, j + W] - cn[:, j]
        ok = (nb >= nmin) & (na >= nmin) & (N[:, j] > 0)
        with np.errstate(invalid="ignore", divide="ignore"):
            d = (ca[:, j + W] - ca[:, j]) / na - (ca[:, j] - ca[:, j - W]) / nb
        dif[ok, j] = d[ok]
    ev = []
    for u in np.where(np.nanmax(np.abs(np.nan_to_num(dif, nan=0)), 1) >= lim)[0]:
        x = dif[u]
        cand = [(abs(x[j]), j) for j in range(M) if np.isfinite(x[j]) and abs(x[j]) >= lim]
        aceitos = []
        for _, j in sorted(cand, reverse=True):
            if all(abs(j - k) >= sep for k in aceitos):
                aceitos.append(j)
        for j in sorted(aceitos):
            nb, na = cn[u, j] - cn[u, j - W], cn[u, j + W] - cn[u, j]
            sa, sb = (ca[u, j + W] - ca[u, j]) / na, (ca[u, j] - ca[u, j - W]) / nb
            ev.append({"u": int(u), "unidade": unidades[u], "m": int(j), "dif": float(x[j]), "n_antes": int(nb),
                       "n_depois": int(na), "af_antes": float(sb), "af_depois": float(sa)})
    ev = pd.DataFrame(ev)
    ev["tipo"] = np.where(ev.dif > 0, "A->AF", "AF->A")
    ev["estrito"] = ((ev.tipo.eq("A->AF") & (ev.af_antes <= .1) & (ev.af_depois >= .9)) |
                     (ev.tipo.eq("AF->A") & (ev.af_antes >= .9) & (ev.af_depois <= .1)))
    # distância ao evento vizinho da mesma unidade
    ev = ev.sort_values(["u", "m"]).reset_index(drop=True)
    prev = ev.groupby("u").m.shift(1)
    nxt = ev.groupby("u").m.shift(-1)
    ev["dist_vizinho"] = np.fmin((ev.m - prev).fillna(999), (nxt - ev.m).fillna(999)).astype(int)
    # janela de 12 meses: parcela de AF em [j-12, j-1] e [j, j+11]
    for W2 in (12,):
        nb = np.array([cn[u, max(j - W2, 0)] for u, j in zip(ev.u, ev.m)])
        nb = np.array([cn[u, j] for u, j in zip(ev.u, ev.m)]) - nb
        na = np.array([cn[u, min(j + W2, M)] - cn[u, j] for u, j in zip(ev.u, ev.m)])
        ab = np.array([ca[u, j] - ca[u, max(j - W2, 0)] for u, j in zip(ev.u, ev.m)])
        aa = np.array([ca[u, min(j + W2, M)] - ca[u, j] for u, j in zip(ev.u, ev.m)])
        with np.errstate(invalid="ignore", divide="ignore"):
            ev[f"af_antes_{W2}"], ev[f"af_depois_{W2}"] = ab / nb, aa / na
        ev[f"n_antes_{W2}"], ev[f"n_depois_{W2}"] = nb.astype(int), na.astype(int)
    return ev


def derivar(c, i):
    out = {}
    # ---------------------------------------------------------------- compras
    c = c.copy()
    c["m"] = C.mes_de(c.abertura) - C.M0
    c["m_pub"] = C.mes_de(c.pub) - C.M0
    c = c[c.m.notna()].copy()
    c["m"] = c.m.astype(int)
    c["af"] = c.af.astype(int)
    c["srp"] = pd.to_numeric(c.srp, errors="coerce")
    c["regiao"] = c.uf.map(C.REGIAO).fillna("NA")
    c["abertura_dt"] = pd.to_datetime(c.abertura, errors="coerce")
    uni = np.array(sorted(c.unidade.astype(str).unique()))
    c["u"] = np.searchsorted(uni, c.unidade.astype(str))
    M = int(c.m.max()) + 1
    U = len(uni)
    out["compras"] = int(len(c)); out["unidades"] = int(U); out["meses"] = [C.mes_str(C.M0), C.mes_str(C.M0 + M - 1)]

    # ---------------------------------------------------------------- itens
    cats = pd.Index(i.compra.cat.categories.astype(str))
    cc = c.set_index(c.compra.astype(str))[["u", "m", "uf", "cnpj", "abertura_dt"]].reindex(cats)
    cod = i.compra.cat.codes.to_numpy()
    for col in cc.columns:
        i[col] = cc[col].to_numpy()[cod]
    i = i[pd.notna(i.m)].copy()
    i["u"], i["m"] = i.u.astype(int), i.m.astype(int)
    out["itens_material"] = int(len(i))
    cats_un = pd.Series(i.un.cat.categories)
    mapa = {k: norm_un(k) for k in cats_un}
    i["un_n"] = pd.Categorical(i.un.astype(object).map(mapa))
    i["prod_ok"] = i.catmat.notna() & i.un_n.notna()
    i["prod"] = -1
    i.loc[i.prod_ok, "prod"] = i[i.prod_ok].groupby(["catmat", "un_n"], observed=True).ngroup()
    i["tri"] = i.m // 3
    i["menor"] = i.criterio.astype(str).str.startswith("Menor")
    i["hom"] = i.situacao.astype(str).eq("Homologado")
    i["final"] = i.situacao.astype(str).isin(["Homologado", "Deserto", "Fracassado"])
    i["fracassado"] = i.situacao.astype(str).eq("Fracassado")
    i["deserto"] = i.situacao.astype(str).eq("Deserto")
    i["excl"] = i.beneficio.astype(str).str.startswith("Particip")
    i["med"] = i.classe.astype(str).str.startswith("65")
    base = i.prod_ok & i.menor
    i["logp"] = np.where(base & i.hom & (i.p > 0), np.log(i.p.where(i.p > 0)), np.nan)
    i["logr"] = np.where(base & (i.r > 0), np.log(i.r.where(i.r > 0)), np.nan)
    i["logq"] = np.where(i.prod_ok & (i.q > 0), np.log(i.q.where(i.q > 0)), np.nan)
    print("índices...", flush=True)
    ref_p = C.loo(i, "logp", ["prod", "tri"])
    i["e"] = i.logp - ref_p
    i["mkt"] = ref_p.where(i.e.notna())
    i["eR"] = i.logr - C.loo(i, "logr", ["prod", "tri"])
    i["eq"] = i.logq - C.loo(i, "logq", ["prod", "tri"])
    # desconto (secundário): itens não sigilosos, menor preço, homologados
    with np.errstate(invalid="ignore", divide="ignore"):
        dsc = 1 - i.p / i.r
    i["desc"] = np.where(base & i.hom & (i.p > 0) & (i.r > 0) & i.sigilo.eq(0) & dsc.between(-1, .99), dsc, np.nan)
    dias = (pd.to_datetime(i.data_resultado.astype(str), errors="coerce") - i.abertura_dt).dt.days
    i["prazo"] = np.where(i.hom & dias.between(0, 730), np.log1p(dias), np.nan)

    # ---------------------------------------------------------------- competição esperada (moderador anterior)
    # nº de fornecedores distintos que venceram o mesmo CATMAT na mesma UF nos 4 trimestres anteriores, em OUTRAS unidades
    print("competição esperada...", flush=True)
    msk = i.hom & i.fornecedor.notna() & i.catmat.notna()
    cm_cod, cm_uni = pd.factorize(i.catmat)               # -1 para CATMAT vazio
    uf_cod, _ = pd.factorize(i.uf)
    i["cm"], i["ufc"] = cm_cod, uf_cod
    w = pd.DataFrame({"cm": cm_cod[msk.to_numpy()], "ufc": uf_cod[msk.to_numpy()], "tri": i.tri[msk].to_numpy(),
                      "u": i.u[msk].to_numpy(), "f": i.fornecedor[msk].cat.codes.to_numpy()}).drop_duplicates()
    ex = pd.concat([w.assign(tt=w.tri + k) for k in (1, 2, 3, 4)], ignore_index=True)[["cm", "ufc", "tt", "u", "f"]]
    ex = ex.drop_duplicates()
    porf = ex.groupby(["cm", "ufc", "tt", "f"]).agg(nu=("u", "nunique"), u1=("u", "first")).reset_index()
    def k3(cm, ufc, tt):
        return (np.asarray(cm, np.int64) * 64 + np.asarray(ufc, np.int64)) * 64 + np.asarray(tt, np.int64)
    d_all = porf.groupby(k3(porf.cm, porf.ufc, porf.tt)).size()
    so = porf[porf.nu.eq(1)]
    d_only = so.groupby(k3(so.cm, so.ufc, so.tt) * 16384 + so.u1.to_numpy(np.int64)).size()
    key3 = k3(i.cm, i.ufc, i.tri)
    da = pd.Series(key3).map(d_all).fillna(0).to_numpy()
    do = pd.Series(key3 * 16384 + i.u.to_numpy(np.int64)).map(d_only).fillna(0).to_numpy()
    i["comp"] = np.where(i.cm.to_numpy() >= 0, np.log1p(da - do), np.nan)
    i = i.drop(columns=["cm", "ufc"])
    del w, ex, porf, so

    # ---------------------------------------------------------------- fornecedor novo na unidade (12 meses)
    mv = (i.hom & i.fornecedor.notna()).to_numpy()
    v = pd.DataFrame({"u": i.u.to_numpy()[mv], "f": i.fornecedor.cat.codes.to_numpy()[mv], "m": i.m.to_numpy()[mv]})
    v = v.drop_duplicates().sort_values(["u", "f", "m"])
    v["ant"] = v.groupby(["u", "f"]).m.shift(1)
    v["novo"] = (v.ant.isna() | ((v.m - v.ant) > 12)).astype(float)
    v.loc[v.m < 12, "novo"] = np.nan                 # sem 12 meses de histórico (2022)
    def k4(u, f, m):
        return (np.asarray(u, np.int64) * 1_048_576 + np.asarray(f, np.int64)) * 128 + np.asarray(m, np.int64)
    mapa_novo = pd.Series(v.novo.to_numpy(), index=k4(v.u, v.f, v.m))
    kk = k4(i.u, i.fornecedor.cat.codes, i.m)
    i["novo"] = np.where(mv, pd.Series(kk).map(mapa_novo).to_numpy(), np.nan)
    del v, mapa_novo

    # ---------------------------------------------------------------- desfechos por compra
    print("desfechos por compra...", flush=True)
    i["e_ok"] = i.e.where(i.e.abs() <= C.LN10)
    i["e_c3"] = i.e.clip(-3, 3)
    i["eR_ok"] = i.eR.where(i.eR.abs() <= C.LN10)
    i["eq_ok"] = i["eq"].clip(-5, 5)
    i["suc"] = np.where(i.final, i.hom.astype(float), np.nan)
    i["fra"] = np.where(i.final, i.fracassado.astype(float), np.nan)
    i["des"] = np.where(i.final, i.deserto.astype(float), np.nan)
    i["mkt_ok"] = i.mkt.where(i.e_ok.notna())
    g = i.groupby("compra", observed=True)
    cp = pd.DataFrame({
        "e": g.e_ok.mean(), "e_c3": g.e_c3.mean(), "eR": g.eR_ok.mean(), "eq": g.eq_ok.mean(), "mkt": g.mkt_ok.mean(),
        "med": g.med.mean(), "excl": g.excl.mean(), "sig": g.sigilo.mean(), "suc": g.suc.mean(), "fra": g.fra.mean(),
        "des": g.des.mean(), "prazo": g.prazo.mean(), "desc": g.desc.mean(), "novo": g.novo.mean(), "comp": g.comp.mean(),
        "n_itens": np.log(g.size()), "e_soma": g.e_ok.sum(min_count=1), "e_n": g.e_ok.count()})
    cp.index = cp.index.astype(str)
    c["compra"] = c.compra.astype(str)
    c = c.join(cp, on="compra")
    out["compras_com_indice"] = int(c.e.notna().sum())
    out["itens_com_indice_ok"] = int(i.e_ok.notna().sum())
    out["itens_com_e"] = int(i.e.notna().sum())
    out["itens_menor_preco"] = float(i.menor.mean())
    out["cobertura_un_padronizada"] = {"un_distintas_antes": int(len(cats_un)), "depois": int(pd.Series(list(mapa.values())).nunique())}

    # ---------------------------------------------------------------- painéis unidade × mês
    print("painéis...", flush=True)
    def painel(col, mes="m"):
        x = c[c[col].notna()]
        S = np.zeros((U, M)); Cn = np.zeros((U, M))
        np.add.at(S, (x.u.to_numpy(), x[mes].astype(int).to_numpy()), x[col].to_numpy(float))
        np.add.at(Cn, (x.u.to_numpy(), x[mes].astype(int).to_numpy()), 1)
        return S, Cn
    P = {}
    N = np.zeros((U, M)); A = np.zeros((U, M))
    np.add.at(N, (c.u.to_numpy(), c.m.to_numpy()), 1)
    np.add.at(A, (c.u.to_numpy(), c.m.to_numpy()), c.af.to_numpy())
    P["N"], P["A"] = N, A
    for col in ["e", "e_c3", "eR", "eq", "mkt", "med", "excl", "sig", "srp", "suc", "fra", "des", "prazo", "desc", "novo",
                "comp", "n_itens"]:
        P[f"S_{col}"], P[f"C_{col}"] = painel(col)
    # ponderado por item: soma e contagem de itens
    x = c[c.e_n.fillna(0) > 0]
    S = np.zeros((U, M)); Cn = np.zeros((U, M))
    np.add.at(S, (x.u.to_numpy(), x.m.to_numpy()), x.e_soma.to_numpy(float))
    np.add.at(Cn, (x.u.to_numpy(), x.m.to_numpy()), x.e_n.to_numpy(float))
    P["S_e_item"], P["C_e_item"] = S, Cn
    # datado pela publicação (teste de antecipação)
    cpub = c[c.m_pub.notna()].copy()
    cpub["m_pub"] = cpub.m_pub.astype(int).clip(0, M - 1)
    x = cpub[cpub.e.notna()]
    S = np.zeros((U, M)); Cn = np.zeros((U, M))
    np.add.at(S, (x.u.to_numpy(), x.m_pub.to_numpy()), x.e.to_numpy(float))
    np.add.at(Cn, (x.u.to_numpy(), x.m_pub.to_numpy()), 1)
    P["S_e_pub"], P["C_e_pub"] = S, Cn
    Np = np.zeros((U, M)); Ap = np.zeros((U, M))
    np.add.at(Np, (cpub.u.to_numpy(), cpub.m_pub.to_numpy()), 1)
    np.add.at(Ap, (cpub.u.to_numpy(), cpub.m_pub.to_numpy()), cpub.af.to_numpy())
    P["N_pub"], P["A_pub"] = Np, Ap

    # ---------------------------------------------------------------- unidades e eventos
    un = c.groupby("u").agg(unidade=("unidade", "first"), cnpj=("cnpj", "first"), esfera=("esfera", "first"),
                            uf=("uf", "first"), regiao=("regiao", "first"), n=("af", "size"), s=("af", "mean"))
    un["regime"] = np.where((un.n >= 20) & (un.s < .05), "A estável",
                            np.where((un.n >= 20) & (un.s > .95), "AF estável", "outra"))
    ev = eventos_regime(N, A, uni)
    ev = ev.join(un[["cnpj", "esfera", "uf", "regiao"]], on="u")
    ev["mes"] = [C.mes_str(C.M0 + m) for m in ev.m]
    # data do primeiro edital no novo modo (publicação), entre as compras do novo modo abertas em [m, m+5]
    novo_af = ev.tipo.eq("A->AF").astype(int).to_numpy()
    pubs = []
    cc = c[["u", "m", "m_pub", "af", "pub"]]
    grp = {u: x for u, x in cc[cc.u.isin(ev.u)].groupby("u")}
    for u, m, naf in zip(ev.u, ev.m, novo_af):
        x = grp[u]
        x = x[(x.m >= m) & (x.m < m + 6) & x.af.eq(naf)]
        pubs.append(int(x.m_pub.min()) if len(x) and x.m_pub.notna().any() else -1)
    ev["m_pub0"] = pubs
    ev["mes_pub0"] = [C.mes_str(C.M0 + m) if m >= 0 else "" for m in ev.m_pub0]
    out["eventos"] = ev.groupby("tipo").size().to_dict()
    out["eventos_estritos"] = ev[ev.estrito].groupby("tipo").size().to_dict()
    out["unidades_por_regime"] = un.regime.value_counts().to_dict()
    return c, i, un, ev, P, out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pncp-db", type=Path, required=True)
    a = ap.parse_args(argv)
    c, i = extrair(a.pncp_db)
    print("extraído", len(c), len(i), flush=True)
    c, i, un, ev, P, out = derivar(c, i)
    keep = ["compra", "item", "u", "m", "tri", "cnpj", "uf", "prod", "catmat", "un_n", "classe", "menor", "hom", "final",
            "sigilo", "excl", "med", "q", "logp", "logr", "logq", "e", "eR", "eq", "mkt", "e_ok", "eR_ok", "comp", "novo",
            "desc", "prazo"]
    i[keep].to_pickle(C.DADOS / "itens.pkl")
    c.drop(columns=["abertura_dt"]).to_pickle(C.DADOS / "compras.pkl")
    un.to_pickle(C.DADOS / "unidades.pkl")
    np.savez_compressed(C.DADOS / "paineis.npz", **P)
    ev.to_csv(C.AQUI / "eventos.csv", index=False)
    (C.AQUI / "base.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1, default=float))
    print("FIM ok")


if __name__ == "__main__":
    main()
