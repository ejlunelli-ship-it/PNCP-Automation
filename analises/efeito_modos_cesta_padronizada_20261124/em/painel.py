"""Etapa 7: painel de efeitos fixos (associação condicional, não efeito causal) — protocolo §8."""
import numpy as np
import pandas as pd

from . import comum
from .descritivas import base_principal
from .inferencia import codificar, ols_fe, remover_singletons

ESPECS = {
    "E1": {"fe": [], "x": [], "desc": "bruto (sem efeitos fixos)"},
    "E2": {"fe": ["uasg", "prod_tri"], "x": [], "desc": "UASG + produto×trimestre"},
    "E3": {"fe": ["uasg", "prod_tri"], "x": ["logq"], "desc": "UASG + produto×trimestre + log quantidade (PRINCIPAL)"},
    "E4": {"fe": ["uasg", "prod_tri"], "x": ["logq", "srp"], "desc": "E3 + SRP (decisão possivelmente conjunta)"},
    "E5": {"fe": ["uasg", "prod_tri"], "x": ["logq", "sigilo"], "desc": "E3 + orçamento sigiloso (decisão possivelmente conjunta)"},
    "E6": {"fe": ["uasg", "prod_tri"], "x": ["logq", "srp", "sigilo"], "desc": "E3 + SRP + sigilo"},
    "E7": {"fe": ["uasg_prod", "prod_tri"], "x": ["logq"], "desc": "UASG×produto + produto×trimestre + log quantidade"},
    "E8": {"fe": ["uasg", "prod_mes"], "x": ["logq"], "desc": "UASG + produto×mês + log quantidade"},
    "E9": {"fe": ["uasg", "orgao_ano", "prod_tri"], "x": ["logq"], "desc": "UASG + órgão×ano + produto×trimestre + log quantidade"},
}


def preparar(d):
    d = d[d.logq.notna()].copy()
    d["srp"] = d.srp.astype(float)
    d["sigilo"] = d.orcamento_sigiloso.astype(float)
    cod = {"uasg": codificar(d.uasg.to_numpy()),
           "prod_tri": codificar(d.produto.to_numpy(), d.tri.to_numpy()),
           "prod_mes": codificar(d.produto.to_numpy(), d.mes.astype(int).to_numpy()),
           "uasg_prod": codificar(d.uasg.to_numpy(), d.produto.to_numpy()),
           "orgao_ano": codificar(d.orgao_cnpj.to_numpy(), d.ano.astype(int).to_numpy())}
    # tercil da quantidade dentro do produto (definido antes dos resultados)
    d["faixa_qtd"] = d.groupby("produto").logq.transform(lambda s: pd.qcut(s.rank(method="first"), 3, labels=False)
                                                        if s.size >= 3 else pd.Series(1, index=s.index)).astype(int)
    return d, cod


def estimar(d, cod, spec, y="y_A1", wcr=0, semente=0, cluster2=False, mascara=None):
    e = ESPECS[spec]
    m = np.ones(len(d), dtype=bool) if mascara is None else mascara
    fes = [cod[f][m] for f in e["fe"]]
    keep = remover_singletons(fes) if fes else np.ones(m.sum(), dtype=bool)
    sub = d[m][keep]
    fes = [codificar(f[keep]) for f in fes]
    X = np.column_stack([sub.af.to_numpy(float)] + [sub[c].to_numpy(float) for c in e["x"]])
    cl = codificar(sub.orgao_cnpj.to_numpy())
    r = ols_fe(sub[y].to_numpy(float), X, fes, cl, cluster2=codificar(sub.produto.to_numpy()) if cluster2 else None,
               nomes=["AF"] + e["x"], wcr=wcr, semente=semente)
    r["sub"] = sub
    r["n_inicial"] = int(m.sum())
    r["singletons"] = int((~keep).sum())
    return r


def linha(spec, r, extra=None):
    b, se = float(r["beta"][0]), float(r["se"][0])
    sub = r["sub"]
    out = {"especificacao": spec, "descricao": ESPECS[spec]["desc"], "beta_lp": b, "ep_cnpj": se,
           "ic95_inf": float(r["ic_inf"][0]), "ic95_sup": float(r["ic_sup"][0]), "p": float(r["p"][0]),
           "pct_exato": float(comum.pct_exato(b)), "pct_ic_inf": float(comum.pct_exato(r["ic_inf"][0])),
           "pct_ic_sup": float(comum.pct_exato(r["ic_sup"][0])),
           "n_itens": r["n"], "n_compras": int(sub.chave.nunique()), "n_produtos": int(sub.produto.nunique()),
           "n_uasgs": int(sub.uasg.nunique()), "n_orgaos": r["clusters"], "n_efetivo_orgaos": float(r["n_efetivo_clusters"]),
           "perda_singletons": r["singletons"], "n_antes_singletons": r["n_inicial"],
           "classificacao": "associação condicional (exploratório)"}
    if "se_2vias" in r:
        out.update({"ep_2vias": float(r["se_2vias"][0]), "p_2vias": float(r["p_2vias"][0])})
    if "p_wcr" in r:
        out.update({"p_wcr_webb": r["p_wcr"], "ic_wcu_inf": r["ic_wcu_inf"], "ic_wcu_sup": r["ic_wcu_sup"], "B_wcr": r["B"]})
    for j, nm in enumerate(r["nomes"][1:], 1):
        out[f"coef_{nm}"] = float(r["beta"][j])
    out.update(extra or {})
    return out


def executar(ctx, abrir, salvar):
    cfg, reg, saidas = ctx["cfg"], ctx["reg"], ctx["saidas"]
    fe = cfg["efeitos_fixos"]
    d = base_principal(abrir(ctx, "amostra"), abrir(ctx, "indices"))
    d, cod = preparar(d)
    linhas = []
    for spec in ESPECS:
        with reg.etapa(f"efeitos fixos {spec}"):
            principal = spec == fe["principal"]
            r = estimar(d, cod, spec, wcr=fe["bootstrap_wcr"] if spec in ("E1", "E3", "E7") else 0,
                        semente=cfg["semente"], cluster2=principal)
            linhas.append(linha(spec, r))
            if principal:
                sub = r["sub"]
                cl = codificar(sub.orgao_cnpj.to_numpy())
                nomes_cl = pd.Series(sub.orgao_cnpj.to_numpy()).groupby(cl).first()
                sh = pd.Series(r["contribuicao_cluster"], index=nomes_cl.values).sort_values(ascending=False)
                contrib = [{"orgao_cnpj": k, "participacao_variacao_identificadora": float(v)} for k, v in sh.head(30).items()]
                # exclusão exata de cada um dos maiores contribuintes (re-estimando os efeitos fixos)
                for c in contrib[: fe["loo_orgaos_top"]]:
                    rr = estimar(d, cod, spec, mascara=(d.orgao_cnpj != c["orgao_cnpj"]).to_numpy())
                    c["beta_sem_orgao"] = float(rr["beta"][0])
                    c["ep_sem_orgao"] = float(rr["se"][0])
                comum.escrever_csv(saidas / "tabelas" / "contribuicao_orgaos_E3.csv", contrib)
                salvar(ctx, "fe_principal", {"beta": float(r["beta"][0]), "se": float(r["se"][0]), "n": r["n"]})
    for k in (0, 1, 2):
        with reg.etapa(f"efeitos fixos E3 — tercil de quantidade {k + 1}"):
            r = estimar(d, cod, "E3", mascara=(d.faixa_qtd == k).to_numpy())
            linhas.append(linha("E3", r, {"especificacao": f"E10_tercil{k + 1}",
                                          "descricao": f"E3 restrito ao tercil {k + 1} da quantidade dentro do produto"}))
    # sem os trimestres incompletos (2022T4 e 2026T2)
    inc = [int(x[:4]) * 4 + int(x[-1]) - 1 for x in cfg["amostra"]["trimestres_incompletos"]]
    r = estimar(d, cod, "E3", mascara=(~d.tri.isin(inc)).to_numpy())
    linhas.append(linha("E3", r, {"especificacao": "E3_sem_trimestres_incompletos", "descricao": "E3 sem 2022T4 e 2026T2"}))
    comum.escrever_csv(saidas / "efeitos_fixos.csv", linhas)
    reg.contar("efeitos_fixos_principal", next(l for l in linhas if l["especificacao"] == fe["principal"]))
