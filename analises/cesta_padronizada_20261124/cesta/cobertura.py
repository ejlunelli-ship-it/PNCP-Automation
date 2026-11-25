"""Cobertura da cesta candidata (seção 13). Sem valores monetários."""
from . import comum
from .metricas import hhi


def _q(dst, sql):
    return dst.execute(sql).fetchall()


def _dist(valores):
    v = sorted(valores)
    if not v:
        return {}
    pct = lambda p: v[min(len(v) - 1, int(round(p * (len(v) - 1))))]
    return {"n": len(v), "min": v[0], "p25": pct(0.25), "mediana": pct(0.5), "p75": pct(0.75), "p90": pct(0.9),
            "max": v[-1], "media": round(sum(v) / len(v), 3)}


def calcular(dst, saidas, funil, tabela="cesta_candidata_tab", prefixo=""):
    cesta = f"SELECT u.* FROM universo_produto u JOIN {tabela} k USING (produto)"
    dst.executescript(f"DROP TABLE IF EXISTS _cob; CREATE TEMP TABLE _cob AS {cesta};"
                      "CREATE INDEX _ix_cob ON _cob (chave);")
    tot = _q(dst, "SELECT COUNT(DISTINCT produto), COUNT(DISTINCT chave), COUNT(*), COUNT(DISTINCT uasg), "
                  "COUNT(DISTINCT orgao_cnpj), SUM(homologado), COUNT(DISTINCT CASE WHEN homologado = 1 THEN chave END) FROM _cob")[0]
    pe = next(f for f in funil if f["etapa"] == "1_pregao_eletronico")
    univ = funil[-1]
    por_ano = _q(dst, "SELECT ano, COUNT(DISTINCT chave), COUNT(*), COUNT(DISTINCT uasg), COUNT(DISTINCT produto) FROM _cob GROUP BY 1 ORDER BY 1")
    por_ano_base = dict(_q(dst, "SELECT ano, COUNT(DISTINCT chave) FROM universo GROUP BY 1"))
    por_tri = _q(dst, "SELECT trimestre, COUNT(DISTINCT chave), COUNT(*), COUNT(DISTINCT uasg), COUNT(DISTINCT produto) FROM _cob GROUP BY 1 ORDER BY 1")
    por_tri_base = dict(_q(dst, "SELECT trimestre, COUNT(DISTINCT chave) FROM universo GROUP BY 1"))
    prod_por_uasg = [r[0] for r in _q(dst, "SELECT COUNT(DISTINCT produto) FROM _cob GROUP BY uasg")]
    uasg_por_prod = [r[0] for r in _q(dst, "SELECT COUNT(DISTINCT uasg) FROM _cob GROUP BY produto")]
    tri_por_prod = [r[0] for r in _q(dst, "SELECT COUNT(DISTINCT trimestre) FROM _cob GROUP BY produto")]
    compras_por_uasg = [r[0] for r in _q(dst, "SELECT COUNT(DISTINCT chave) FROM _cob GROUP BY uasg")]
    h = hhi(compras_por_uasg)
    grupos = _q(dst, "SELECT CASE WHEN classe >= 1000 THEN classe / 100 END AS grupo, COUNT(DISTINCT produto), "
                     "COUNT(DISTINCT chave), COUNT(DISTINCT uasg) FROM _cob GROUP BY 1 ORDER BY 3 DESC")
    classes = _q(dst, f"SELECT k.classe_tecnica, COUNT(DISTINCT c.produto), COUNT(DISTINCT c.chave), COUNT(DISTINCT c.uasg) "
                      f"FROM _cob c JOIN {tabela} k USING (produto) GROUP BY 1 ORDER BY 1")
    comum.escrever_csv(saidas / f"{prefixo}cobertura_por_ano.csv",
                       [{"ano": a, "compras_cesta": c, "itens_cesta": i, "uasgs": u, "produtos": p,
                         "compras_universo": por_ano_base.get(a), "pct_compras_universo": round(100 * c / por_ano_base[a], 3) if por_ano_base.get(a) else None}
                        for a, c, i, u, p in por_ano],
                       ["ano", "compras_cesta", "itens_cesta", "uasgs", "produtos", "compras_universo", "pct_compras_universo"])
    comum.escrever_csv(saidas / f"{prefixo}cobertura_por_trimestre.csv",
                       [{"trimestre": t, "compras_cesta": c, "itens_cesta": i, "uasgs": u, "produtos": p,
                         "compras_universo": por_tri_base.get(t), "pct_compras_universo": round(100 * c / por_tri_base[t], 3) if por_tri_base.get(t) else None}
                        for t, c, i, u, p in por_tri],
                       ["trimestre", "compras_cesta", "itens_cesta", "uasgs", "produtos", "compras_universo", "pct_compras_universo"])
    comum.escrever_csv(saidas / f"{prefixo}cobertura_por_grupo_material.csv",
                       [{"grupo_catalogo": g, "produtos": p, "compras": c, "uasgs": u} for g, p, c, u in grupos],
                       ["grupo_catalogo", "produtos", "compras", "uasgs"])
    return {
        "produtos": tot[0], "compras": tot[1], "itens": tot[2], "uasgs": tot[3], "orgaos_cnpj": tot[4],
        "itens_homologados": tot[5], "compras_com_item_homologado": tot[6],
        "pct_compras_pregao_eletronico": round(100 * tot[1] / pe["compras"], 3) if pe["compras"] else None,
        "pct_compras_universo_catmat": round(100 * tot[1] / univ["compras"], 3) if univ["compras"] else None,
        "pct_itens_universo_catmat": round(100 * tot[2] / univ["itens"], 3) if univ["itens"] else None,
        "compras_pregao_eletronico_fonte": pe["compras"], "compras_universo_catmat": univ["compras"],
        "itens_universo_catmat": univ["itens"],
        "hhi_compras_por_uasg_cesta": h, "n_efetivo_uasgs_cesta": (1 / h) if h else None,
        "produtos_por_uasg": _dist(prod_por_uasg), "uasgs_por_produto": _dist(uasg_por_prod),
        "trimestres_por_produto": _dist(tri_por_prod), "compras_por_uasg": _dist(compras_por_uasg),
        "por_classe_tecnica": [{"classe": c, "produtos": p, "compras": n, "uasgs": u} for c, p, n, u in classes],
        "por_ano": [{"ano": a, "compras": c, "itens": i, "uasgs": u, "produtos": p} for a, c, i, u, p in por_ano],
        "por_trimestre": [{"trimestre": t, "compras": c, "itens": i, "uasgs": u, "produtos": p} for t, c, i, u, p in por_tri],
    }
