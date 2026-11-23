"""Exame do desconto no estudo de eventos. EXPLORATÓRIO: pedido do usuário depois dos resultados de 23/11.

O protocolo (§8) previa só o efeito agregado do desconto como desfecho secundário (+1,40 p.p. em resultados.json). Aqui
se acrescentam:
- perfil de evento e pré-tendência;
- simetria;
- pesos iguais e ponderação por item;
- aleatorização e placebo no tempo;
- retirada dos CNPJs de maior peso;
- decomposição do desconto em estimado (R), preço (P) e mix, numa amostra comum de itens (correção de 23/11: a
  versão anterior misturava amostras diferentes, e as parcelas não somavam).

Desconto d = 1 − P/R: itens não sigilosos, Menor preço, homologados, P > 0, R > 0, d entre −1 e 0,99.
Decomposição exata, nos itens que têm desconto e os dois índices: log(R/P) = eR − e + (refR − refP), em que eR e e
são log R e log P contra o mesmo produto e trimestre nas outras unidades, e refR − refP é o desconto de mercado do
produto (mix). Logo DiD[log(R/P)] = DiD[eR] − DiD[e] + DiD[mix], com as mesmas compras, controles e pesos.
Em pontos de desconto, Δd ≈ (P/R médio) × Δlog(R/P).

Uso (da pasta PNCP-Automation): python analises/testes_desenho_causal_20261123/exploratorio_desconto.py
Saída: exploratorio_desconto.json. Não lê o pncp.db; usa a base de dados/testes_desenho_causal/.
"""
import json

import numpy as np
import pandas as pd

import comum as C
import executar as E
import motor as Mo
from poder import carregar, eventos_validos

W, CMIN = E.W, E.CMIN


def paineis_extra(pn):
    """Painéis unidade × mês só com os itens que entram no desconto: log(R/P), log P, log R e os índices e, eR."""
    i = pd.read_pickle(C.DADOS / "itens.pkl")[["compra", "u", "m", "desc", "logp", "logr", "e_ok", "eR_ok"]]
    i = i[i.desc.notna()].copy()
    i["ld"] = i.logr - i.logp
    cp = i.groupby("compra", observed=True).agg(u=("u", "first"), m=("m", "first"), ld=("ld", "mean"),
                                                 lp=("logp", "mean"), lr=("logr", "mean"),
                                                 e_d=("e_ok", "mean"), eR_d=("eR_ok", "mean"))
    novos = {}
    for col in ["ld", "lp", "lr", "e_d", "eR_d"]:
        x = cp[cp[col].notna()]
        S, Cn = np.zeros((pn.U, pn.M)), np.zeros((pn.U, pn.M))
        np.add.at(S, (x.u.to_numpy(int), x.m.to_numpy(int)), x[col].to_numpy(float))
        np.add.at(Cn, (x.u.to_numpy(int), x.m.to_numpy(int)), 1)
        novos[f"S_{col}"], novos[f"C_{col}"] = S, Cn
    S, Cn = np.zeros((pn.U, pn.M)), np.zeros((pn.U, pn.M))
    np.add.at(S, (i.u.to_numpy(int), i.m.to_numpy(int)), i.desc.to_numpy(float))
    np.add.at(Cn, (i.u.to_numpy(int), i.m.to_numpy(int)), 1)
    novos["S_desc_item"], novos["C_desc_item"] = S, Cn
    # amostra comum da decomposição: itens com desconto E com os dois índices (preço e estimado).
    # log(R/P) = eR − e + mix, com mix = refR − refP (desconto de mercado do produto no trimestre, nas outras unidades):
    # a identidade vale item a item, logo também nas médias por compra, nas janelas e no DiD (mesmas compras e controles).
    z = i[i.e_ok.notna() & i.eR_ok.notna()].copy()
    z["cmix"] = z.ld - z.eR_ok + z.e_ok
    cz = z.groupby("compra", observed=True).agg(u=("u", "first"), m=("m", "first"), cdesc=("desc", "mean"), cld=("ld", "mean"),
                                                 ceR=("eR_ok", "mean"), ce=("e_ok", "mean"), cmix=("cmix", "mean"))
    for col in ["cdesc", "cld", "ceR", "ce", "cmix"]:
        S, Cn = np.zeros((pn.U, pn.M)), np.zeros((pn.U, pn.M))
        np.add.at(S, (cz.u.to_numpy(int), cz.m.to_numpy(int)), cz[col].to_numpy(float))
        np.add.at(Cn, (cz.u.to_numpy(int), cz.m.to_numpy(int)), 1)
        novos[f"S_{col}"], novos[f"C_{col}"] = S, Cn
    comum = {"itens": int(len(z)), "P_sobre_R_medio": float((1 - z.desc).mean())}
    return novos, float((1 - i.desc).mean()), int(len(i)), comum


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
    extra, pr_medio, n_itens, comum_ = paineis_extra(pn)
    pn.P.update(extra)
    out = {"AVISO": "exploratório: feito a pedido do usuário depois de ver os resultados pré-registrados",
           "itens_no_desconto": n_itens, "P_sobre_R_medio": pr_medio}

    # 1. estimativa pré-registrada (repetida) com perfil de evento ------------------------------------------
    res, ctrl = Mo.did_eventos(pn, e_main, y="desc", guardar_controles=True, **base)
    res["cnpj"] = E.cl(res, un)
    res["w"] = 1 / np.maximum(E.VAR["a"] + E.VAR["b"] * res.h, 1e-6)
    ag = E.agrega(res, un)
    out["principal"] = {k: resumo(ag, k) for k in ("efeito_AF", "A->AF", "AF->A")}
    out["principal"]["simetria_soma"] = {k: ag["simetria_soma"][k] for k in ("est", "ep", "p_wild")}
    out["principal"]["eventos"] = {"A->AF": ag["n_A->AF"], "AF->A": ag["n_AF->A"], "cnpjs": int(res.cnpj.nunique())}
    out["pesos_iguais"] = {k: resumo(E.agrega(res, un, modo="iguais"), k) for k in ("efeito_AF", "A->AF", "AF->A")}
    bins = [c for c in res.columns if c.startswith("b")]
    out["perfil"] = {c: resumo(E.agrega(res, un, c, ic=True)) for c in bins}
    res["theta"] = res[[c for c in bins if int(c[1:]) >= 0]].mean(axis=1, skipna=False)
    out["perfil_media_pos"] = resumo(E.agrega(res, un, "theta"))

    # 2. aleatorização (placebo no espaço, nas datas reais) -------------------------------------------------------
    rng = np.random.default_rng(20261123)
    devs = [ctrl[k].dev.to_numpy() for k in res.k]
    draws = np.array([[d[rng.integers(len(d))] for d in devs] for _ in range(5000)])
    w = res.w.to_numpy() / res.w.sum()
    s = res.sinal.to_numpy()
    obs = float((res.did.to_numpy() * s) @ w)
    nul = (draws * s) @ w
    out["aleatorizacao"] = {"obs": obs, "p_ri": float(np.mean(np.abs(nul) >= abs(obs))),
                            "q025": float(np.quantile(nul, .025)), "q975": float(np.quantile(nul, .975))}

    # 2b. aleatorização com controles de precisão parecida (os 20 controles de h mais próximo do da tratada), para o
    #     desconto e para o índice de preço; IC por inversão (efeito aditivo constante): obs ± quantil 95% de |nulo|
    out["h_tratadas_vs_controles"] = {"h_mediano_tratadas": float(res.h.median()),
                                      "h_mediano_controles": float(np.median(np.concatenate([ctrl[k].h.to_numpy() for k in res.k])))}
    ri2 = {}
    for nome, y in (("desconto", "desc"), ("indice_preco", "e")):
        rr_, cc_ = (res, ctrl) if y == "desc" else Mo.did_eventos(pn, e_main, y=y, guardar_controles=True, perfil=False, **base)
        ww = 1 / np.maximum(E.VAR["a"] + E.VAR["b"] * rr_.h.to_numpy(), 1e-6)
        ww = ww / ww.sum()
        ss = rr_.sinal.to_numpy()
        ob = float((rr_.did.to_numpy() * ss) @ ww)
        rng2 = np.random.default_rng(7)
        pools = []
        for k, hk in zip(rr_.k, rr_.h):
            c = cc_[k]
            pools.append(c.dev.to_numpy()[np.argsort(np.abs(c.h.to_numpy() - hk))[:20]])
        sorteio = np.array([[pl[rng2.integers(len(pl))] for pl in pools] for _ in range(5000)])
        nul2 = (sorteio * ss) @ ww
        q = float(np.quantile(np.abs(nul2), .95))
        ri2[nome] = {"obs": ob, "p_ri": float(np.mean(np.abs(nul2) >= abs(ob))), "ic95_inversao": [ob - q, ob + q],
                     "dp_nulo": float(nul2.std())}
    out["aleatorizacao_controles_semelhantes"] = ri2

    # 3. placebo no tempo: evento fictício 12 meses antes, unidade estável no modo de partida -----------------------
    fake = e_main.copy()
    fake["m"] = fake.m - 12
    keep = []
    for _, r in fake.iterrows():
        m, u = int(r.m), int(r.u)
        if m - W < 0:
            keep.append(False)
            continue
        n1, a1 = pn.soma("N", m - W, m)[u], pn.soma("A", m - W, m)[u]
        n2, a2 = pn.soma("N", m, m + W)[u], pn.soma("A", m, m + W)[u]
        if n1 == 0 or n2 == 0:
            keep.append(False)
            continue
        keep.append((a1 / n1 <= .1 and a2 / n2 <= .1) if r.tipo == "A->AF" else (a1 / n1 >= .9 and a2 / n2 >= .9))
    rf = Mo.did_eventos(pn, fake[np.array(keep, bool)], y="desc", perfil=False, **base)
    out["placebo_no_tempo_12m"] = resumo(E.agrega(rf, un)) if len(rf) >= 5 else {"n": int(len(rf))}

    # 4. outras ponderações ---------------------------------------------------------------------------------------------
    r = Mo.did_eventos(pn, e_main, y="desc", Sk="S_desc_item", Ck="C_desc_item", perfil=False, **base)
    out["ponderado_por_item"] = resumo(E.agrega(r, un))
    r = Mo.did_eventos(pn, e_main, y="desc", W=W, cmin=3, unid=un, ev_todos=ev, perfil=False)
    out["cmin_3"] = resumo(E.agrega(r, un))
    r = Mo.did_eventos(pn, eventos_validos(ev, 12), y="desc", W=12, cmin=CMIN, unid=un, ev_todos=ev, perfil=False)
    out["janela_12m"] = resumo(E.agrega(r, un))

    # 5. retirada dos CNPJs de maior peso ---------------------------------------------------------------------------------
    ordem = res.groupby("cnpj").w.sum().sort_values(ascending=False)
    out["maior_cnpj_peso"] = float(ordem.iloc[0] / res.w.sum())
    out["sem_cnpj"] = {}
    for k, c in enumerate(ordem.index[:5], 1):
        z = res[res.cnpj != c]
        out["sem_cnpj"][f"{k}º maior peso"] = float(np.average(z.sinal * z.did, weights=z.w))

    # 6. decomposição exata numa AMOSTRA COMUM (itens com desconto e com os dois índices; mesmas compras, eventos,
    #    controles e pesos): DiD[log(R/P)] = DiD[eR] − DiD[e] + DiD[mix]
    dec = {"amostra_comum": comum_}
    for modo in ("precisao", "iguais"):
        bloco = {}
        for nome, y in [("desconto_pp", "cdesc"), ("log_R_sobre_P", "cld"), ("estimado_eR", "ceR"), ("preco_e", "ce"),
                        ("mix_desconto_de_mercado", "cmix")]:
            r = Mo.did_eventos(pn, e_main, y=y, perfil=False, **base)
            bloco[nome] = {k: resumo(E.agrega(r, un, modo=modo), k) for k in ("efeito_AF", "A->AF", "AF->A")}
            bloco[nome]["eventos"] = int(len(r))
        est = {k: v["efeito_AF"]["est"] for k, v in bloco.items()}
        bloco["identidade"] = {"log_R_sobre_P": est["log_R_sobre_P"],
                               "eR_menos_e_mais_mix": est["estimado_eR"] - est["preco_e"] + est["mix_desconto_de_mercado"]}
        tot = est["log_R_sobre_P"]
        bloco["participacoes_no_log_R_sobre_P"] = {"estimado": est["estimado_eR"] / tot, "preco": -est["preco_e"] / tot,
                                                  "mix": est["mix_desconto_de_mercado"] / tot}
        dec[modo] = bloco
    # amostra toda do desconto (sem exigir índice): log(R/P) e logs brutos (variam com o mix; só para a identidade)
    toda = {}
    for nome, y in [("log_R_sobre_P", "ld"), ("log_R_bruto", "lr"), ("log_P_bruto", "lp")]:
        r = Mo.did_eventos(pn, e_main, y=y, perfil=False, **base)
        toda[nome] = {k: resumo(E.agrega(r, un), k) for k in ("efeito_AF", "A->AF", "AF->A")}
        toda[nome]["eventos"] = int(len(r))
    toda["identidade"] = {"log_R_menos_log_P": toda["log_R_bruto"]["efeito_AF"]["est"] - toda["log_P_bruto"]["efeito_AF"]["est"],
                          "log_R_sobre_P": toda["log_R_sobre_P"]["efeito_AF"]["est"]}
    toda["log_R_sobre_P_em_pp_de_desconto"] = 100 * pr_medio * toda["log_R_sobre_P"]["efeito_AF"]["est"]
    dec["amostra_toda_do_desconto"] = toda
    out["decomposicao"] = dec
    (C.AQUI / "exploratorio_desconto.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float),
                                                       encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1, default=float))
    print("FIM ok")


if __name__ == "__main__":
    main()
