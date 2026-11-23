"""Compras do modo Aberto usadas nos matchings, a baixar para ter o número de licitantes (quantidade_fornecedores).

O número de licitantes só existe nos PDFs de relatório; foram baixados os do Aberto-Fechado (AF) e do Fechado-Aberto,
não os do Aberto (A). Este script refaz a seleção dos itens A que entram nos dois matchings já estimados e lista as
compras correspondentes, no formato de registro/compras/<mês>.csv.

Matchings considerados (nenhum é reestimado; só se reconstrói quem está nos estratos com os dois modos):
  - mensal corrigido de 13/11 (analise/materiais_corrigido_20261113/, o principal do parecer de 17/11): as amostras
    pareadas amostra_mensal_{A_desconto,B_preco_mediana_historica}.csv.gz já trazem os itens (t = 0 é Aberto);
  - anual com sigilo de 17/11 (analise/ajuste_sigilo_painel_matching_20261117/): estratos
    CNPJ×produto×ano×sigilo×SRP×benefício×faixa de quantidade ("principal") e CNPJ×produto×ano×sigilo ("simples"),
    reconstruídos de analise/painel_efeitos_fixos_20261116/painel_principal.pkl e conferidos com o resultados.json.
Para o lado AF dos mesmos estratos, mede-se quantos itens já têm o número de licitantes na base de extração.

Mês da compra = primeiro mês de resultado dos itens homologados (registro_principal = 1), a mesma regra das análises.

Uso (da pasta PNCP-Automation):
    python analises/aberto_licitantes_matching_20261123/listar.py --pncp-db ../dados/pncp.db \
        --extracao dados/extracao/aberto-fechado_parser-1.9.1.db
Saída nesta pasta: itens_aberto.csv.gz, compras_aberto.csv, compras_por_mes/<AAAA-MM>.csv, resumo.json.
"""
import argparse, json, os, sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
ANALISE = AQUI.parents[2] / "analise"
CAMPOS_COMPRA = ["numeroControlePNCP", "idCompra", "numeroCompra", "anoCompraPncp", "objetoCompra",
                 "dataPublicacaoPncp", "dataAberturaPropostaPncp", "orgaoEntidadeCnpj"]
TAMANHO_OBJETO = 100


def ro(caminho):
    return sqlite3.connect(f"file:{Path(caminho).resolve().as_posix()}?mode=ro", uri=True)


def mensal():
    """Itens dos dois matchings mensais (A: desconto; B: preço/mediana histórica), com t (1 = AF)."""
    partes = []
    for nome, rot in [("A_desconto", "mensal_desconto"), ("B_preco_mediana_historica", "mensal_preco")]:
        d = pd.read_csv(ANALISE / "materiais_corrigido_20261113" / f"amostra_mensal_{nome}.csv.gz",
                        dtype={"compra": str, "orgao": str, "uasg": str}, usecols=["compra", "item", "t"])
        partes.append(d.assign(matching=rot, af=d.t.eq(1)).drop(columns="t"))
    return pd.concat(partes, ignore_index=True)


def anual(ref):
    """Itens nos estratos com os dois modos do matching anual com sigilo (principal e simples), conferidos com ref."""
    pasta = ANALISE / "painel_efeitos_fixos_20261116"
    d = pd.read_pickle(pasta / "painel_principal.pkl")
    d = d[d.sigilo.isin([0, 1]) & d.modo.isin([0, 1]) & np.isfinite(d.logp)].copy()
    d["faixa_q"] = np.floor(np.log2(d.q)).astype("int32")
    mapas = json.loads((pasta / "mapas.json").read_text(encoding="utf-8"))
    inv = {k: pd.Series(list(mapas[k].keys()), index=list(mapas[k].values())) for k in ["compra"]}
    k0 = ["orgao", "produto", "ano"]
    k1 = k0 + ["srp", "beneficio", "faixa_q"]
    def pareados(base, chave, sig):
        z = base[base.sigilo.eq(sig)]
        return z[z.groupby(chave, observed=True).modo.transform("nunique").eq(2)]

    # Conferência com o resultados.json. No executar.py de 17/11 o matching principal em log(P) roda duas vezes com o
    # mesmo nome (amostra toda e subamostra com R válido) e a segunda sobrescreve a primeira: a chave
    # principal_condicoes_ano_logp guarda a subamostra com R válido. Confere-se o simples na amostra toda, o principal
    # na subamostra com R, e a lista usa o principal na amostra toda (que contém a subamostra).
    com_r = d[np.isfinite(d.r) & d.r.gt(0)]
    for base, chave, nome_ref in [(com_r, k1, "principal_condicoes_ano_logp"), (d, k0, "simples_ano_logp")]:
        for sig in (0, 1):
            z, r = pareados(base, chave, sig), ref["matching"][nome_ref][str(sig)]
            obs = (z.groupby(chave, observed=True).ngroups, int(z.modo.eq(0).sum()), int(z.modo.eq(1).sum()))
            assert obs == (r["celulas"], r["itens_A"], r["itens_AF"]), (nome_ref, sig, obs)
    partes = []
    for rot, chave in [("anual_principal", k1), ("anual_simples", k0)]:
        for sig in (0, 1):
            z = pareados(d, chave, sig)
            partes.append(pd.DataFrame({"compra": inv["compra"].loc[z.compra].to_numpy(), "item": z["item"].to_numpy(),
                                        "matching": rot, "af": z.modo.eq(1).to_numpy()}))
    return pd.concat(partes, ignore_index=True)


def compras_pncp(controles, pncp_db):
    """Campos de registro/compras e primeiro mês de resultado, do pncp.db (somente leitura)."""
    st = os.stat(pncp_db)
    con = ro(pncp_db)
    con.execute("create temp table alvo(numero_controle_pncp text primary key)")
    con.executemany("insert into temp.alvo values (?)", [(c,) for c in sorted(controles)])
    c = pd.read_sql_query(
        """select c.numero_controle_pncp as numeroControlePNCP, c.id_compra as idCompra, c.numero_compra as numeroCompra,
                  c.ano_compra as anoCompraPncp, c.objeto_compra as objetoCompra, c.data_publicacao as dataPublicacaoPncp,
                  c.data_abertura_proposta as dataAberturaPropostaPncp, c.orgao_cnpj as orgaoEntidadeCnpj,
                  c.modo_disputa, c.uasg, c.orgao_nome
           from temp.alvo a join compras c on c.numero_controle_pncp = a.numero_controle_pncp""", con)
    m = pd.read_sql_query(
        """select i.numero_controle_pncp as numeroControlePNCP, min(substr(i.data_resultado, 1, 7)) as mes,
                  count(*) as itens_homologados
           from temp.alvo a join itens i on i.numero_controle_pncp = a.numero_controle_pncp
           where i.registro_principal = 1 and i.homologado = 1 group by 1""", con)
    con.close()
    assert os.stat(pncp_db).st_mtime_ns == st.st_mtime_ns and os.stat(pncp_db).st_size == st.st_size, "pncp.db mudou"
    assert c.numeroControlePNCP.is_unique
    return c.merge(m, on="numeroControlePNCP", how="left")


def licitantes_af(extracao):
    """(id_compra, item) com número de licitantes na base de extração do AF."""
    con = ro(extracao)
    e = pd.read_sql_query("select arquivo_origem, item, status_extracao, quantidade_fornecedores from itens", con)
    con.close()
    e["id_compra"] = e.arquivo_origem.str.extract(r"-(\d{17})-(?:s\d+-)?item-")[0]
    e["item"] = pd.to_numeric(e["item"], errors="coerce")
    e["lic"] = pd.to_numeric(e.quantidade_fornecedores, errors="coerce")
    e = e[e.status_extracao.eq("OK") & e.lic.gt(0) & e.id_compra.notna() & e["item"].notna()]
    return set(zip(e.id_compra, e["item"].astype(int)))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pncp-db", type=Path, required=True)
    ap.add_argument("--extracao", type=Path, required=True)
    a = ap.parse_args(argv)
    ref = json.loads((ANALISE / "ajuste_sigilo_painel_matching_20261117" / "resultados.json").read_text(encoding="utf-8"))
    it = pd.concat([mensal(), anual(ref)], ignore_index=True)
    it["item"] = it["item"].astype(int)
    comp = compras_pncp(set(it.compra), a.pncp_db)
    it = it.merge(comp[["numeroControlePNCP", "idCompra", "modo_disputa"]], left_on="compra",
                  right_on="numeroControlePNCP", how="left").drop(columns="numeroControlePNCP")
    assert it.modo_disputa.notna().all()
    assert (it.modo_disputa.eq("Aberto-Fechado") == it.af).all() and it.loc[~it.af, "modo_disputa"].eq("Aberto").all()
    tem = licitantes_af(a.extracao)
    it["licitantes_na_base"] = [(i, n) in tem for i, n in zip(it.idCompra, it["item"])]
    it.loc[~it.af, "licitantes_na_base"] = False  # nenhum PDF do Aberto foi baixado

    R = {"matchings": {}}
    for mt, g in it.groupby("matching", sort=False):
        ga, gf = g[~g.af], g[g.af]
        R["matchings"][mt] = {
            "itens_A": len(ga), "compras_A": ga.compra.nunique(), "orgaos_A": ga.compra.str[:14].nunique(),
            "itens_AF": len(gf), "compras_AF": gf.compra.nunique(),
            "itens_AF_com_licitantes": int(gf.licitantes_na_base.sum()),
            "pct_itens_AF_com_licitantes": 100 * float(gf.licitantes_na_base.mean()),
            "compras_AF_com_algum_item_com_licitantes": int(gf[gf.licitantes_na_base].compra.nunique())}

    A = it[~it.af]
    flags = (A.assign(v=True).drop_duplicates(["compra", "matching"])
             .pivot(index="compra", columns="matching", values="v").fillna(False).astype(bool))
    flags.columns = [f"em_{c}" for c in flags.columns]
    nitens = A.drop_duplicates(["compra", "item"]).groupby("compra").item.agg(
        itens_pareados="size", lista_itens=lambda s: " ".join(map(str, sorted(s))))
    lista = comp[comp.modo_disputa.eq("Aberto")].set_index("numeroControlePNCP").join(nitens).join(flags).reset_index()
    lista["objetoCompra"] = lista.objetoCompra.fillna("").map(lambda x: " ".join(x.split())[:TAMANHO_OBJETO])
    em_mensal = lista.filter(like="em_mensal").any(axis=1)
    lista["prioridade"] = np.select([em_mensal, lista.em_anual_principal], [1, 2], 3)
    lista = lista.sort_values(["prioridade", "mes", "numeroControlePNCP"])
    cols = ["prioridade", "mes"] + CAMPOS_COMPRA + ["uasg", "orgao_nome", "itens_homologados", "itens_pareados",
                                                     "lista_itens"] + list(flags.columns)
    lista[cols].to_csv(AQUI / "compras_aberto.csv", index=False, encoding="utf-8")
    it.sort_values(["matching", "compra", "item"]).to_csv(AQUI / "itens_aberto.csv.gz", index=False, compression="gzip")
    pm = AQUI / "compras_por_mes"
    pm.mkdir(exist_ok=True)
    for f in pm.glob("*.csv"):
        f.unlink()
    for mes, g in lista.groupby("mes"):
        g.sort_values("numeroControlePNCP")[CAMPOS_COMPRA].to_csv(pm / f"{mes}.csv", index=False, encoding="utf-8",
                                                                   lineterminator="\n")

    def cum(mask):
        s = lista[mask]
        return {"compras": len(s), "sem_idCompra": int(s.idCompra.isna().sum()), "orgaos": s.orgaoEntidadeCnpj.nunique(),
                "itens_pareados": int(s.itens_pareados.sum()), "itens_homologados_nas_compras": int(s.itens_homologados.sum()),
                "meses": s.mes.nunique(), "primeiro_mes": s.mes.min(), "ultimo_mes": s.mes.max()}
    R["lista_A"] = {"prioridade_1_mensal": cum(lista.prioridade.eq(1)),
                    "prioridades_1_2_mensal_ou_anual_principal": cum(lista.prioridade.le(2)),
                    "todas_1_2_3_inclui_anual_simples": cum(lista.prioridade.le(3)),
                    "por_ano_todas": lista.groupby(lista.mes.str[:4]).size().to_dict(),
                    "por_ano_prioridades_1_2": lista[lista.prioridade.le(2)].groupby(lista.mes.str[:4]).size().to_dict(),
                    "top10_orgaos_todas": lista.groupby(["orgaoEntidadeCnpj"]).size().nlargest(10).to_dict()}
    (AQUI / "resumo.json").write_text(json.dumps(R, ensure_ascii=False, indent=1, default=int), encoding="utf-8")
    print(json.dumps(R, ensure_ascii=False, indent=1, default=int))
    print("FIM ok")


if __name__ == "__main__":
    main()
