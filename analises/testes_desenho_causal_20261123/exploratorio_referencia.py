"""Referências de preço alternativas para o índice do item e células de menor dispersão. EXPLORATÓRIO: pedido do
usuário em 23/11, depois dos resultados pré-registrados.

Índice do item: e = log P − log(referência); descartam-se os itens com |e| > ln 10. Célula = produto (CATMAT +
unidade) × trimestre; a própria UASG nunca entra na sua referência.
  A. original (protocolo): média do log P dos itens das outras UASGs, >= 5 itens de >= 3 outras UASGs;
  B. a mesma média de itens, com o mínimo novo: >= 3 itens de >= 3 outras UASGs;
  G. média geométrica dos preços médios por UASG, peso igual para cada outra UASG. O preço médio da UASG é a média
     aritmética dos seus preços na célula, e a referência é exp(média de log(preço médio) nas outras UASGs).
     Mínimo: >= 3 itens de >= 3 outras UASGs;
  M. mediana, entre as outras UASGs, dos mesmos preços médios por UASG (sensibilidade), com o mesmo mínimo.
Dispersão da célula: desvio-padrão, entre as OUTRAS UASGs, do log do preço médio. O comprador fica de fora para a
seleção não depender do seu próprio preço. Restrições: itens com dispersão até os percentis 75, 50 e 25; e o
complemento, acima do percentil 75 (referências A e G).
Estudo de eventos idêntico ao principal: janela de 6 meses, cmin = 2, pesos de precisão, WCR por CNPJ.

Uso (da pasta PNCP-Automation): python analises/testes_desenho_causal_20261123/exploratorio_referencia.py
Saída: exploratorio_referencia.json. Não lê o pncp.db; usa a base de dados/testes_desenho_causal/.
"""
import json, time

import numpy as np
import pandas as pd

import comum as C
import executar as E
import motor as Mo
from poder import carregar, eventos_validos

W, CMIN = E.W, E.CMIN
T0 = time.time()


def log(*a):
    print(f"[{time.time() - T0:5.0f}s]", *a, flush=True)


def referencias(x):
    """x: itens com log P (prod, tri, u, logp). Devolve, por item, as referências B, G, M e a dispersão sd_G."""
    x = x.assign(p=np.exp(x.logp))
    gu = x.groupby(["prod", "tri", "u"], observed=True).agg(n=("logp", "size"), sl=("logp", "sum"), mp=("p", "mean"))
    gu = gu.reset_index()
    gu["lm"] = np.log(gu.mp)                                   # log do preço médio da UASG na célula
    gu["lm2"] = gu.lm ** 2
    gu["cel"] = gu.groupby(["prod", "tri"], observed=True).ngroup()
    gc = gu.groupby("cel").agg(K=("u", "size"), N=("n", "sum"), S1=("lm", "sum"), S2=("lm2", "sum"), SL=("sl", "sum"))
    gu = gu.join(gc, on="cel")
    k1, n1 = gu.K - 1, gu.N - gu.n                             # outras UASGs e itens delas
    ok3 = (k1 >= 3) & (n1 >= 3)
    gu["ref_B"] = ((gu.SL - gu.sl) / n1).where(ok3)
    s1, s2 = gu.S1 - gu.lm, gu.S2 - gu.lm ** 2
    gu["ref_G"] = (s1 / k1).where(ok3)
    var = (s2 - s1 ** 2 / k1) / (k1 - 1)
    gu["sd_G"] = np.sqrt(np.clip(var, 0, None)).where(ok3)
    # mediana sem a própria UASG: ordena os preços médios em cada célula e usa a posição de cada UASG
    gu = gu.sort_values(["cel", "lm"]).reset_index(drop=True)
    a = gu.lm.to_numpy()
    r = gu.groupby("cel").cumcount().to_numpy()                # posto da UASG dentro da célula
    o = np.arange(len(gu)) - r                                  # início da célula no vetor ordenado
    K1 = (gu.K - 1).to_numpy()
    okm = (K1 >= 3) & ((gu.N - gu.n).to_numpy() >= 3)
    r_, o_, k1 = r[okm], o[okm], K1[okm]

    def pega(pos):                                              # posição `pos` na lista das OUTRAS UASGs
        return a[o_ + np.where(pos < r_, pos, pos + 1)]
    impar = k1 % 2 == 1
    med = np.where(impar, pega((k1 - 1) // 2), (pega(k1 // 2 - 1) + pega(k1 // 2)) / 2)
    gu["ref_M"] = np.nan
    gu.loc[okm, "ref_M"] = med
    cols = ["prod", "tri", "u", "ref_B", "ref_G", "ref_M", "sd_G"]
    return x.merge(gu[cols], on=["prod", "tri", "u"], how="left")


def painel(pn, z, col):
    """Médias por compra do índice `col` nos itens de z e painéis unidade × mês (soma e contagem de compras)."""
    cp = z.groupby("compra", observed=True).agg(u=("u", "first"), m=("m", "first"), y=(col, "mean"))
    S, Cn = np.zeros((pn.U, pn.M)), np.zeros((pn.U, pn.M))
    np.add.at(S, (cp.u.to_numpy(int), cp.m.to_numpy(int)), cp.y.to_numpy(float))
    np.add.at(Cn, (cp.u.to_numpy(int), cp.m.to_numpy(int)), 1)
    return S, Cn, int(len(cp))


def resumo(x, chave="efeito_AF"):
    e = x.get(chave, {})
    if not e:
        return None
    return {"est": e["est"], "ep": e["ep"], "p_wild": e["p_wild"], "ic95": e.get("ic95_wild") or e.get("ic95_t"),
            "n": e.get("n", x.get("n"))}


def main():
    pn, un, ev = carregar()
    e_main = eventos_validos(ev, W)
    base = dict(W=W, cmin=CMIN, unid=un, ev_todos=ev)
    i = pd.read_pickle(C.DADOS / "itens.pkl")[["compra", "u", "m", "tri", "prod", "logp", "e_ok"]]
    x = i[i.logp.notna()].copy()
    del i
    log("itens com preço", len(x))
    x = referencias(x)
    for k in ("B", "G", "M"):
        e = x.logp - x[f"ref_{k}"]
        x[f"e_{k}"] = e.where(e.abs() <= C.LN10)
    x["e_A"] = x.e_ok
    log("referências prontas")
    q = {f"p{int(100 * p)}": float(x.loc[x.e_G.notna(), "sd_G"].quantile(p)) for p in (.25, .5, .75)}
    out = {"AVISO": "exploratório: pedido do usuário depois dos resultados pré-registrados",
           "itens_com_preco": int(len(x)), "limiares_dispersao_sd_log": q,
           "dispersao_mediana_por_metodo": {}, "variantes": {}}
    main_ev = set(pd.read_csv(C.AQUI / "eventos_did.csv").k)
    restr = {"todas": None, "disp<=p75": q["p75"], "disp<=p50": q["p50"], "disp<=p25": q["p25"], "disp>p75": -q["p75"]}
    for met in ("A", "B", "G", "M"):
        col = f"e_{met}"
        out["dispersao_mediana_por_metodo"][met] = float(x.loc[x[col].notna(), "sd_G"].median())
        for nome, lim in restr.items():
            if nome == "disp>p75" and met not in ("A", "G"):
                continue                                    # complemento: as células que saem (só A e G)
            if lim is None:
                filtro = x[col].notna()
            elif lim < 0:
                filtro = x[col].notna() & (x.sd_G > -lim)
            else:
                filtro = x[col].notna() & (x.sd_G <= lim)
            z = x[filtro]
            tag = f"{met}_{nome}"
            S, Cn, ncomp = painel(pn, z, col)
            pn.P[f"S_{tag}"], pn.P[f"C_{tag}"] = S, Cn
            res = Mo.did_eventos(pn, e_main, y=tag, **base)
            res["cnpj"] = E.cl(res, un)
            w = 1 / np.maximum(E.VAR["a"] + E.VAR["b"] * res.h, 1e-6)
            sh = pd.Series(w).groupby(res.cnpj.to_numpy()).sum() / w.sum()
            ag = E.agrega(res, un)
            v = {"itens": int(len(z)), "compras": ncomp, "eventos": {"A->AF": int(res.tipo.eq("A->AF").sum()),
                                                                     "AF->A": int(res.tipo.eq("AF->A").sum())},
                 "eventos_tambem_no_principal": int(res.k.isin(main_ev).sum()),
                 "cnpjs": int(res.cnpj.nunique()), "cnpjs_efetivos": float(1 / (sh ** 2).sum()),
                 "maior_cnpj_peso": float(sh.max()), "dp_did": float(res.did.std()),
                 "efeito_AF": resumo(ag), "A->AF": resumo(ag, "A->AF"), "AF->A": resumo(ag, "AF->A"),
                 "simetria_p": ag.get("simetria_soma", {}).get("p_wild"),
                 "pre_tendencia_b-2": resumo(E.agrega(res, un, "b-2", ic=False)),
                 "pesos_iguais": resumo(E.agrega(res, un, modo="iguais", ic=False))}
            out["variantes"][tag] = v
            ef = v["efeito_AF"]
            log(tag, v["eventos"], "CNPJs", v["cnpjs"], "efeito", round(100 * ef["est"], 2), "p", round(ef["p_wild"], 3))
    (C.AQUI / "exploratorio_referencia.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float),
                                                         encoding="utf-8")
    log("FIM ok")


if __name__ == "__main__":
    main()
