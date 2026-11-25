"""Etapas: amostra → modelos (M1–M5 × variantes, amostras comuns, células) → loo (10 CNPJs mais influentes) →
verificacao (convergência MAP × LSMR) → relatorio. Resultados intermediários em D:; tabelas no repositório."""
import time

import numpy as np
import pandas as pd

from . import comum, estimar
from .comum import RES, TAB

CELULAS = ["uf_prod_tri", "cnpj_prod", "cnpj_prod_tri", "uasg_prod_tri"]


def _limpo(r):
    return {k: v for k, v in r.items() if not k.startswith("_")}


def etapa_amostra(c, log):
    from . import amostra
    d, funil, agreg, nomes = amostra.construir(c, log)
    comum.salvar_pkl(comum.trabalho(c, "amostra_compra_produto.pkl.gz"), {"d": d, "funil": funil, "agreg": agreg, "nomes": nomes})
    comum.escrever_csv(TAB / "funil_amostra.csv", funil.to_dict("records"))
    comum.escrever_json(RES / "amostra_resumo.json", agreg)
    tri = d.groupby("trimestre").agg(obs=("chave", "size"), compras=("chave", "nunique"), fracao_af=("af", "mean"),
                                     incompleto=("trimestre_incompleto", "first")).reset_index()
    comum.escrever_csv(TAB / "cobertura_trimestres.csv", tri.to_dict("records"))
    return d


def carregar(c):
    return comum.ler_pkl(comum.trabalho(c, "amostra_compra_produto.pkl.gz"))


def etapa_modelos(c, log):
    A = carregar(c)
    d, nomes = A["d"], A["nomes"]
    e = c["estimacao"]
    B, sem = c["inferencia"]["wcr_B"], c["semente"]
    cod = estimar.codigos(d, set(estimar.CAMPOS))
    wc = estimar.peso_por_compra(d)
    inc = d.trimestre_incompleto.to_numpy()
    linhas, contrib, celulas, amostras = [], {}, [], {}
    variantes = [("principal", True, None, None), ("sem_lnq", False, None, None), ("peso_igual_por_compra", True, wc, None),
                 ("sem_trimestres_incompletos", True, None, ~inc)]
    for M, spec in c["modelos"].items():
        for var, com_q, peso, masc in variantes:
            t = time.time()
            r = estimar.estimar(d, spec["fe"], com_q, peso, masc, cod, B, sem, e["tol"], e["max_iter"], True)
            log(f"  {M} {var}: β = {r['beta_lp']:.3f} lp (EP {r['ep_cr1_cnpj']:.3f}); n = {r['obs']:,}; {time.time() - t:.0f}s")
            linhas.append({"modelo": M, "descricao": spec["desc"], "variante": var, **_limpo(r)})
            if var == "principal":
                amostras[M] = r["_sub_idx"]
                contrib[M] = (r["_contrib_cnpj"], r["_contrib_uf"])
                sub = d.iloc[r["_sub_idx"]]
                for cel in CELULAS:
                    celulas.append({"modelo": M, **estimar.celulas_dois_modos(sub, cel)})
    # amostras comuns: a de M5 (mais restrita; comum a todos) e a de M3 (comum a M1–M4)
    for base in ("M5", "M3"):
        masc = np.zeros(len(d), bool)
        masc[amostras[base]] = True
        for M, spec in c["modelos"].items():
            if base == "M3" and M == "M5":
                continue
            r = estimar.estimar(d, spec["fe"], True, None, masc, cod, B, sem, e["tol"], e["max_iter"], True)
            log(f"  {M} amostra comum {base}: β = {r['beta_lp']:.3f}; n = {r['obs']:,}")
            linhas.append({"modelo": M, "descricao": spec["desc"], "variante": f"amostra_comum_{base}", **_limpo(r)})
    R = pd.DataFrame(linhas)
    R["nome_top1_cnpj"] = R.top1_cnpj.map(nomes)
    comum.escrever_csv(TAB / "modelos.csv", R.to_dict("records"))
    comum.escrever_csv(TAB / "celulas_dois_modos.csv", celulas)
    lc, lu = [], []
    for M, (sc, su) in contrib.items():
        for k, (g, v) in enumerate(sc.head(30).items(), 1):
            lc.append({"modelo": M, "ordem": k, "cnpj": g, "orgao": nomes.get(g, ""), "participacao": float(v), "acumulada": float(sc.head(k).sum())})
        for k, (g, v) in enumerate(su.items(), 1):
            lu.append({"modelo": M, "ordem": k, "uf": g, "participacao": float(v), "acumulada": float(su.head(k).sum())})
    comum.escrever_csv(TAB / "contribuicao_cnpj.csv", lc)
    comum.escrever_csv(TAB / "contribuicao_uf.csv", lu)
    comum.salvar_pkl(comum.trabalho(c, "modelos.pkl.gz"), {"R": R, "amostras": amostras, "contrib": contrib})
    return R


def etapa_loo(c, log):
    A = carregar(c)
    d, nomes = A["d"], A["nomes"]
    e = c["estimacao"]
    S = comum.ler_pkl(comum.trabalho(c, "modelos.pkl.gz"))
    R = S["R"]
    cod = estimar.codigos(d, set(estimar.CAMPOS))
    linhas = []
    for M, spec in c["modelos"].items():
        base = R[(R.modelo == M) & (R.variante == "principal")].iloc[0]
        for k, g in enumerate(S["contrib"][M][0].head(c["inferencia"]["loo_top"]).index, 1):
            r = estimar.estimar(d, spec["fe"], True, None, (d.cnpj != g).to_numpy(), cod, 0, 0, e["tol"], e["max_iter"], False)
            linhas.append({"modelo": M, "ordem": k, "cnpj_excluido": g, "orgao": nomes.get(g, ""),
                           "participacao": float(S["contrib"][M][0][g]), "beta_base": float(base.beta_lp),
                           "beta_sem": r["beta_lp"], "ep_sem": r["ep_cr1_cnpj"], "mudanca": r["beta_lp"] - float(base.beta_lp),
                           "obs_sem": r["obs"], "compras_sem": r["compras"], "convergiu": r["conv_convergiu"]})
            log(f"  {M} sem {g} ({nomes.get(g, '')[:30]}): β = {r['beta_lp']:.3f}")
    comum.escrever_csv(TAB / "loo_top10_cnpj.csv", linhas)
    return linhas


def etapa_verificacao(c, log):
    """Convergência: M1 e M2 também por MAP puro (tolerância 1e-9) e comparação com LSMR + MAP."""
    A = carregar(c)
    d = A["d"]
    e = c["estimacao"]
    R = comum.ler_pkl(comum.trabalho(c, "modelos.pkl.gz"))["R"]
    orig = estimar.absorver
    linhas = []
    try:
        estimar.absorver = estimar.absorver_map
        for M in ("M1", "M2", "M4"):
            r = estimar.estimar(d, c["modelos"][M]["fe"], True, None, None, None, 0, 0, e["tol"], e["max_iter"], False)
            b = R[(R.modelo == M) & (R.variante == "principal")].iloc[0]
            linhas.append({"modelo": M, "beta_lsmr_map": float(b.beta_lp), "beta_map": r["beta_lp"], "diferenca": r["beta_lp"] - float(b.beta_lp),
                           "iteracoes_map": r["conv_iteracoes"], "convergiu_map": r["conv_convergiu"],
                           "max_media_residual_map": r["conv_max_media_residual_grupos"],
                           "max_media_residual_lsmr": float(b.conv_max_media_residual_grupos)})
            log(f"  verificação {M}: LSMR {b.beta_lp:.6f} × MAP {r['beta_lp']:.6f}")
    finally:
        estimar.absorver = orig
    comum.escrever_csv(TAB / "verificacao_convergencia.csv", linhas)
    return linhas
