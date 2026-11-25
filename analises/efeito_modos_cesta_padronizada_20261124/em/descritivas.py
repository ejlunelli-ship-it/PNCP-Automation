"""Etapa 6: estatísticas descritivas por modo e diferença bruta com inferência agrupada (protocolo §7)."""
import numpy as np
import pandas as pd

from . import comum
from .inferencia import codificar, ols_fe

COLS_BASE = ["chave", "numero_item", "produto", "classe_tecnica", "uasg", "orgao_cnpj", "tri", "mes", "ano", "af",
             "logq", "quantidade", "srp", "orcamento_sigiloso", "p_est", "p_hom", "logp", "modo_disputa", "uf", "esfera",
             "rigoroso", "recorrente", "inconsistencia_tecnica", "aprovado"]


def base_principal(df, idx, mascara="mascara_A1"):
    """Itens com preço válido e referência A1 (|Y| ≤ ln 10). Sem produtos aprovados, é a amostra EXPLORATÓRIA da
    cesta candidata (a principal, df.elegivel_principal, está vazia)."""
    d = df.loc[idx.index, COLS_BASE].join(idx)
    d = d[d[mascara]].copy()
    d["uasg"] = d.uasg.astype(str)
    d["orgao_cnpj"] = d.orgao_cnpj.astype(str)
    d["produto"] = d.produto.astype(str)
    d["tri"] = d.tri.astype(int)
    return d


def _q(x, p):
    return float(np.nanquantile(x, p)) if len(x) else np.nan


def por_modo(d, pop):
    linhas = []
    for af, nome in ((0, "Aberto"), (1, "Aberto-Fechado")):
        s = d[d.af == af]
        y = s.y_A1.to_numpy()
        pp = pop[pop.af == af]
        fin = pp[pp.situacao_item != "Em andamento"]
        linhas.append({
            "modo": nome, "itens": len(s), "compras": s.chave.nunique(), "produtos": s.produto.nunique(),
            "uasgs": s.uasg.nunique(), "orgaos_cnpj": s.orgao_cnpj.nunique(),
            "media_Y": float(np.mean(y)), "mediana_Y": _q(y, .5), "dp_Y": float(np.std(y, ddof=1)),
            "p05": _q(y, .05), "p25": _q(y, .25), "p50": _q(y, .5), "p75": _q(y, .75), "p95": _q(y, .95),
            "primeiro_trimestre": comum.nome_trimestre(int(s.tri.min())), "ultimo_trimestre": comum.nome_trimestre(int(s.tri.max())),
            "trimestres": s.tri.nunique(), "quantidade_mediana": float(s.quantidade.median()),
            "log_quantidade_media": float(s.logq.mean()), "srp_media": float(s.srp.astype(float).mean()),
            "sigilo_media": float(s.orcamento_sigiloso.astype(float).mean()),
            "itens_populacao": len(pp), "itens_decididos": len(fin),
            "taxa_homologacao_decididos": float((fin.situacao_item == "Homologado").mean()) if len(fin) else np.nan,
            "taxa_fracasso_decididos": float((fin.situacao_item == "Fracassado").mean()) if len(fin) else np.nan,
            "taxa_desercao_decididos": float((fin.situacao_item == "Deserto").mean()) if len(fin) else np.nan,
        })
    return linhas


def executar(ctx, abrir):
    cfg, reg, saidas = ctx["cfg"], ctx["reg"], ctx["saidas"]
    am = abrir(ctx, "amostra")
    d = base_principal(am, abrir(ctx, "indices"))
    a = cfg["amostra"]
    pop = am[am.populacao_desfecho & am.modo_disputa.isin(a["modos"]) & (am.criterio_julgamento == a["criterio"])]
    with reg.etapa("descritivas por modo"):
        linhas = por_modo(d, pop)
        # distribuição dos produtos por modo
        pm = d.groupby("produto").af.agg(["size", "mean"])
        ambos = pm[(pm["mean"] > 0) & (pm["mean"] < 1)]
        dist = {"produtos": len(pm), "produtos_nos_dois_modos": len(ambos),
                "itens_em_produtos_nos_dois_modos": float(d.produto.isin(ambos.index).mean()),
                "produtos_so_A": int((pm["mean"] == 0).sum()), "produtos_so_AF": int((pm["mean"] == 1).sum())}
        comum.escrever_csv(saidas / "descritivas.csv", linhas)
        comum.escrever_json(saidas / "tabelas" / "distribuicao_produtos_modo.json", dist)
    with reg.etapa("diferença bruta com inferência agrupada"):
        cl = codificar(d.orgao_cnpj.to_numpy())
        cl2 = codificar(d.produto.to_numpy())
        bruta = []
        for nome, col in (("Y_A1 (log-pontos)", "y_A1"), ("log preço homologado ×100 (sem referência)", None)):
            y = d[col].to_numpy() if col else 100 * d.logp.to_numpy()
            r = ols_fe(y, d.af.to_numpy(float), [], cl, cluster2=cl2, nomes=["AF"],
                       wcr=cfg["efeitos_fixos"]["bootstrap_wcr"], semente=cfg["semente"])
            bruta.append({"desfecho": nome, "diferenca_AF_menos_A_lp": float(r["beta"][0]), "ep_cnpj": float(r["se"][0]),
                          "ic95_inf": float(r["ic_inf"][0]), "ic95_sup": float(r["ic_sup"][0]), "p_cnpj": float(r["p"][0]),
                          "ep_2vias_cnpj_produto": float(r["se_2vias"][0]), "p_2vias": float(r["p_2vias"][0]),
                          "p_wcr_webb": r["p_wcr"], "ic_wcu_inf": r["ic_wcu_inf"], "ic_wcu_sup": r["ic_wcu_sup"],
                          "pct_exato": float(comum.pct_exato(r["beta"][0])), "n_itens": r["n"], "cnpjs": r["clusters"],
                          "n_efetivo_cnpjs": float(r["n_efetivo_clusters"]), "classificacao": "descritivo (exploratório)"})
        # diferença de medianas com bootstrap por CNPJ
        rng = np.random.default_rng(cfg["semente"])
        G = cl.max() + 1
        y = d.y_A1.to_numpy()
        af = d.af.to_numpy()
        med0 = np.median(y[af == 1]) - np.median(y[af == 0])
        ordem = np.argsort(cl, kind="stable")
        lim = np.searchsorted(cl[ordem], np.arange(G + 1))
        dr = []
        for _ in range(199):
            g = rng.integers(0, G, G)
            idx = np.concatenate([ordem[lim[k]:lim[k + 1]] for k in g])
            yy, aa = y[idx], af[idx]
            if (aa == 1).any() and (aa == 0).any():
                dr.append(np.median(yy[aa == 1]) - np.median(yy[aa == 0]))
        se = float(np.std(dr, ddof=1))
        bruta.append({"desfecho": "diferença de medianas de Y_A1", "diferenca_AF_menos_A_lp": float(med0), "ep_cnpj": se,
                      "ic95_inf": float(med0 - 1.96 * se), "ic95_sup": float(med0 + 1.96 * se),
                      "pct_exato": float(comum.pct_exato(med0)), "n_itens": len(d), "cnpjs": int(G),
                      "classificacao": "descritivo (exploratório); bootstrap por CNPJ, 199 réplicas"})
        comum.escrever_csv(saidas / "tabelas" / "diferenca_bruta.csv", bruta)
        reg.contar("diferenca_bruta", bruta[0])
