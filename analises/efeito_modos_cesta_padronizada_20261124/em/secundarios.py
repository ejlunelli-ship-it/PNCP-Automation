"""Etapa 11: desfechos secundários (protocolo §9/§14). EXPLORATÓRIO.

Desconto 100(1 − P/E) (E > 0, orçamento não sigiloso, desconto em [−100, 99]); índices com mediana externa (A3) e
geométrica externa (A1); homologação, fracasso e deserção sobre os itens DECIDIDOS (exclui 'Em andamento'), com o
mesmo denominador para os três. Painel FE E3 (associação) e dCDH 6 meses por item (exploratório causal).
"""
import numpy as np
import pandas as pd

from . import comum
from .descritivas import base_principal
from .eventos import DCDH, bootstrap, painel, resumir
from .inferencia import holm
from .painel import estimar, linha, preparar


def _populacao(am, cfg):
    a = cfg["amostra"]
    p = am[am.populacao_desfecho & am.modo_disputa.isin(a["modos"]) & (am.criterio_julgamento == a["criterio"])].copy()
    p = p[p.situacao_item != "Em andamento"]
    for c in ("uasg", "orgao_cnpj", "produto"):
        p[c] = p[c].astype(str)
    p["tri"] = p.tri.astype(int)
    p["homologacao"] = 100.0 * (p.situacao_item == "Homologado")
    p["fracasso"] = 100.0 * (p.situacao_item == "Fracassado")
    p["desercao"] = 100.0 * (p.situacao_item == "Deserto")
    return p


def executar(ctx, abrir, salvar):
    cfg, reg, saidas = ctx["cfg"], ctx["reg"], ctx["saidas"]
    ev = cfg["eventos"]
    B, sem = ev["bootstrap"], cfg["semente"]
    am = abrir(ctx, "amostra")
    idx = abrir(ctx, "indices")
    E = abrir(ctx, "eventos_info")
    info, tri_ini, tri_fim = E["info"], E["tri_ini"], E["tri_fim"]
    cnpj_cod = pd.factorize(info.cnpj.fillna("?"))[0]
    L = ev["janelas_trimestres"][ev["janela_principal"]]
    linhas = []

    def rodar(nome, dd, col, desc):
        with reg.etapa(f"secundário {nome}"):
            d2, cod2 = preparar(dd)
            r = estimar(d2, cod2, "E3", y=col)
            l = linha("E3", r)
            linhas.append({"desfecho": nome, "modelo": "FE E3 (associação)", "grupo": "—", "beta": l["beta_lp"], "ep": l["ep_cnpj"],
                           "ic95_inf": l["ic95_inf"], "ic95_sup": l["ic95_sup"], "p": l["p"], "n_itens": l["n_itens"],
                           "n_orgaos": l["n_orgaos"], "unidade": desc, "classificacao": "associação condicional (exploratório)"})
            Y, N = painel(dd, info.uasg.tolist(), tri_ini, tri_fim, col, "item")
            est = DCDH(Y, N, info, L, L)
            ponto, pw, chaves, draws = bootstrap(est, cnpj_cod, B, sem)
            for x in resumir(ponto, chaves, draws):
                if x["l"] == "media" and x["grupo"] in ("agregado", "adocao", "abandono"):
                    linhas.append({"desfecho": nome, "modelo": "dCDH 6m por item", "grupo": x["grupo"], "beta": x["beta_lp"],
                                   "ep": x["ep"], "ic95_inf": x["ic95_inf"], "ic95_sup": x["ic95_sup"], "p": x["p"],
                                   "unidade": desc, "classificacao": "exploratório"})

    # desconto sobre o valor estimado
    d = am.loc[am.elegivel_preco].copy()
    d = d[(d.p_est > 0) & (d.orcamento_sigiloso.fillna(0) == 0)]
    d["desconto"] = 100 * (1 - d.p_hom / d.p_est)
    d = d[d.desconto.between(-100, 99)]
    for c in ("uasg", "orgao_cnpj", "produto"):
        d[c] = d[c].astype(str)
    d["tri"] = d.tri.astype(int)
    rodar("desconto", d, "desconto", "pontos percentuais do valor estimado")
    # índices com mediana (A3) e geométrica (A1) externas
    rodar("preco_rel_mediana_externa_A3", base_principal(am, idx, "propria_A3"), "y_A3", "log-pontos")
    rodar("preco_rel_geometrica_externa_A1", base_principal(am, idx), "y_A1", "log-pontos")
    # homologação, fracasso, deserção (itens decididos; mesmo denominador)
    pop = _populacao(am, cfg)
    for c in ("homologacao", "fracasso", "desercao"):
        rodar(c, pop, c, "pontos percentuais (itens decididos)")
    # Holm na família S (dCDH agregado: desconto, homologação, fracasso, deserção)
    fam = [l for l in linhas if l["modelo"].startswith("dCDH") and l["grupo"] == "agregado"
           and l["desfecho"] in ("desconto", "homologacao", "fracasso", "desercao")]
    adj = holm([l["p"] for l in fam])
    for l, a in zip(fam, adj):
        l["p_holm_familia_S"] = float(a)
    comum.escrever_csv(saidas / "resultados_secundarios.csv", linhas)
