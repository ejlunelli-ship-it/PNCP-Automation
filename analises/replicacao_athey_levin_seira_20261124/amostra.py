"""Amostra e covariáveis da replicação de Athey, Levin e Seira (2011), Fase 1 (protocolo.md, seções 1–4). EXPLORATÓRIO.

Lê a base de 23/11 (dados/testes_desenho_causal/: compras.pkl, itens.pkl, paineis.npz) e grava em
dados/replicacao_athey_levin_seira/ (fora do git):
  compras.pkl       uma linha por compra da análise (≥ 1 item com índice), com as covariáveis X anteriores ao modo
  itens.pkl         itens com índice (desfecho principal) e covariáveis do item e da compra
  itens_status.pkl  itens com situação final (homologação, fracasso, deserção)
Devolve as contagens de exclusão. Não lê o pncp.db; não usa nada posterior a 2025-10.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
AQUI = Path(__file__).resolve().parent
T23 = AQUI.parent / "testes_desenho_causal_20261123"
ROB = AQUI.parent / "robustez_dispersao_20261123"
for p in (str(ROB), str(T23)):
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import comum as C  # noqa: E402

SAIDA = C.RAIZ / "dados" / "replicacao_athey_levin_seira"
M_INI = (2023 * 12 + 0) - C.M0                       # 2023-01
M_FIM = (2025 * 12 + 9) - C.M0                       # 2025-10 (último mês antes dos eventos reservados)
COLS_IT = ["compra", "item", "u", "m", "tri", "cnpj", "prod", "catmat", "classe", "menor", "hom", "final", "sigilo",
           "excl", "med", "q", "logp", "logr", "e", "e_ok", "eq", "comp", "desc"]     # colunas gravadas por preparar.py
CAT_HIST = ["sem histórico", "0", "(0; 0,1]", "(0,1; 0,5]", "(0,5; 0,9]", "(0,9; 1)", "1"]


def hist_cat(n, a):
    s = np.where(n > 0, a / np.maximum(n, 1), np.nan)
    out = np.full(len(n), "sem histórico", dtype=object)
    out[(n > 0) & (s == 0)] = "0"
    out[(s > 0) & (s <= .1)] = "(0; 0,1]"
    out[(s > .1) & (s <= .5)] = "(0,1; 0,5]"
    out[(s > .5) & (s <= .9)] = "(0,5; 0,9]"
    out[(s > .9) & (s < 1)] = "(0,9; 1)"
    out[(n > 0) & (s == 1)] = "1"
    return pd.Categorical(out, categories=CAT_HIST)


def construir(log=print):
    SAIDA.mkdir(parents=True, exist_ok=True)
    exc = []
    cp = pd.read_pickle(C.DADOS / "compras.pkl")
    it = pd.read_pickle(C.DADOS / "itens.pkl")[COLS_IT]
    it["compra"] = it.compra.astype(str)
    cp["compra"] = cp.compra.astype(str)
    # situação, preço e estimado do item: da extração (itens_brutos.pkl), pela chave (compra, item)
    br = pd.read_pickle(C.DADOS / "itens_brutos.pkl")[["compra", "item", "situacao", "r", "p"]]
    br["compra"] = br.compra.astype(str)
    dup = int(br.duplicated(["compra", "item"]).sum())
    br = br.drop_duplicates(["compra", "item"])
    it = it.merge(br, on=["compra", "item"], how="left", validate="many_to_one")
    del br
    # derivações idênticas às de preparar.py.derivar()
    it["prod_ok"] = it["prod"] >= 0
    sit = it.situacao.astype(str)
    it["fracassado"], it["deserto"] = sit.eq("Fracassado"), sit.eq("Deserto")
    it["suc"] = np.where(it.final, it.hom.astype(float), np.nan)
    it["fra"] = np.where(it.final, it.fracassado.astype(float), np.nan)
    it["des"] = np.where(it.final, it.deserto.astype(float), np.nan)
    it["e_c3"] = it.e.clip(-3, 3)
    it["eq_ok"] = it["eq"].clip(-5, 5)
    log("base", len(cp), "compras;", len(it), "itens de material;", dup, "chaves duplicadas na extração;",
        int(it.situacao.isna().sum()), "itens sem situação na extração")

    def conta(etapa, z):
        exc.append({"etapa": etapa, "itens": int(len(z)), "compras": int(z.compra.nunique()),
                    "compras_AF": int(z.drop_duplicates("compra").af.sum()) if "af" in z else None,
                    "uasgs": int(z.u.nunique()), "cnpjs": int(z.cnpj.nunique())})

    af = cp.set_index("compra").af
    it["af"] = af.reindex(it.compra).to_numpy()
    # itens das UASGs tratadas do estudo de eventos (comparação em amostra comum; janelas até 2026-04, dados já usados)
    ev = pd.read_csv(T23 / "eventos_did.csv")
    it.loc[it.e_ok.notna() & it.u.isin(ev.u), ["compra", "u", "m", "tri", "cnpj", "e_ok", "af"]].reset_index(drop=True)         .to_pickle(SAIDA / "itens_eventos.pkl")
    conta("itens de material (registro principal) de pregões eletrônicos A ou AF, base de 23/11", it)
    # ------------------------------------------------------------- covariáveis da compra (todos os itens de material)
    it["grupo"] = it.classe.astype(str).str[:2]
    it.loc[~it.grupo.str.fullmatch(r"\d\d"), "grupo"] = "NA"
    dom = it.groupby(["compra", "grupo"]).size().rename("n").reset_index()
    dom = dom.sort_values(["compra", "n", "grupo"], ascending=[True, False, True]).drop_duplicates("compra")
    vt = (it.q * it.r).where((it.q > 0) & (it.r > 0))
    val = vt.groupby(it.compra).sum(min_count=1)
    P = np.load(C.DADOS / "paineis.npz")
    N, A = P["N"], P["A"]
    cN = np.concatenate([np.zeros((N.shape[0], 1)), np.cumsum(N, 1)], 1)
    cA = np.concatenate([np.zeros((A.shape[0], 1)), np.cumsum(A, 1)], 1)
    u, m = cp.u.to_numpy(int), cp.m.to_numpy(int)
    lo = np.maximum(m - 12, 0)
    cp["hist_n"] = cN[u, m] - cN[u, lo]
    cp["hist_a"] = cA[u, m] - cA[u, lo]
    cp["hist_cat"] = hist_cat(cp.hist_n.to_numpy(), cp.hist_a.to_numpy())
    cp["hist_log_n"] = np.log1p(cp.hist_n)
    cp["grupo_dom"] = dom.set_index("compra").grupo.reindex(cp.compra).to_numpy()
    cp["log_valor"] = np.log(val.reindex(cp.compra).to_numpy())
    cp["n_itens_mat"] = np.exp(cp.n_itens)
    cp["tri"] = cp.m // 3
    cp["eq_aus"] = cp["eq"].isna().astype(float)
    cp["eq0"] = cp["eq"].fillna(0.0)
    cp["comp_aus"] = cp.comp.isna().astype(float)
    cp["comp0"] = cp.comp.fillna(cp.comp.median())
    cp["srp"] = cp.srp.fillna(0).astype(float)
    cp["sig"] = cp.sig.fillna(0).astype(float)
    cp["excl"] = cp.excl.fillna(0).astype(float)
    cp["med"] = cp.med.fillna(0).astype(float)
    # ------------------------------------------------------------- filtros dos itens do desfecho principal
    z = it[(it.m >= M_INI) & (it.m <= M_FIM)]
    conta("abertura de 2023-01 a 2025-10 (sem o período dos eventos reservados)", z)
    z = z[z.menor]
    conta("julgamento por menor preço", z)
    z_status = z[z.final & z.prod_ok].copy()
    z = z[z.hom & (z.p > 0)]
    conta("homologado com preço unitário > 0", z)
    z = z[z.prod_ok]
    conta("CATMAT e unidade de fornecimento padronizada", z)
    z = z[np.isfinite(z.e)]
    conta("referência disponível (≥ 5 itens de ≥ 3 outras UASGs no produto × trimestre)", z)
    z = z.assign(ok_ln10=np.isfinite(z.e_ok))
    conta("|índice| ≤ ln 10 (tratamento de extremos validado)", z[z.ok_ln10])
    z = z[z.cnpj.notna() & (z.cnpj.astype(str).str.len() > 0)]
    conta("UASG e CNPJ presentes", z[z.ok_ln10])
    # ------------------------------------------------------------- dispersão contemporânea (sensibilidade 7)
    import motor_robustez as MR
    x = it.loc[it.logp.notna(), ["prod", "tri", "u", "logp"]]
    gu, _ = MR.tabela_uasg(x)
    z = z.merge(gu[["prod", "tri", "u", "sd_G"]], on=["prod", "tri", "u"], how="left")
    z["baixa_disp"] = (z.sd_G <= MR.LIM).astype(float).where(z.sd_G.notna())
    # ------------------------------------------------------------- compras da análise
    zk = z[z.ok_ln10]
    comp_ids = zk.compra.unique()
    z = z[z.compra.isin(comp_ids)]                       # itens com |e| > ln 10 só nas compras da análise (sensibilidade)
    c = cp[cp.compra.isin(comp_ids)].copy()
    n_idx = zk.groupby("compra").size()
    c["n_itens_indice"] = n_idx.reindex(c.compra).to_numpy()
    c["y"] = (100 * zk.groupby("compra").e_ok.mean()).reindex(c.compra).to_numpy()
    c["y_c3"] = (100 * z.groupby("compra").e_c3.mean()).reindex(c.compra).to_numpy()
    c["faixa_itens"] = pd.qcut(c.n_itens_mat.rank(method="first"), 10, labels=False).astype(int)
    lim_itens = c.groupby("faixa_itens").n_itens_mat.agg(["min", "max"])
    c["faixa_valor"] = -1
    ok = c.log_valor.notna()
    c.loc[ok, "faixa_valor"] = pd.qcut(c.loc[ok, "log_valor"].rank(method="first"), 10, labels=False).astype(int)
    c["terco_valor"] = -1
    c.loc[ok, "terco_valor"] = pd.qcut(c.loc[ok, "log_valor"].rank(method="first"), 3, labels=False).astype(int)
    freq = c.grupo_dom.value_counts(normalize=True)
    c["grupo_dom_x"] = np.where(c.grupo_dom.map(freq).fillna(0) >= .01, c.grupo_dom, "outros")
    # todos os itens com dados da compra
    cols_c = ["compra", "regiao", "esfera", "uf", "faixa_itens", "faixa_valor", "terco_valor", "hist_cat", "hist_log_n",
              "hist_n", "hist_a", "grupo_dom_x", "med", "eq0", "eq_aus", "comp0", "comp_aus", "srp", "sig", "excl",
              "n_itens_indice", "unidade"]
    z = z.merge(c[cols_c].rename(columns={"med": "parc_med", "eq0": "eq_c", "eq_aus": "eq_c_aus", "comp0": "comp_c",
                                          "comp_aus": "comp_c_aus", "sig": "sig_c", "excl": "excl_c"}), on="compra", how="left")
    z["y"] = 100 * z.e_ok
    z["y_c3"] = 100 * z.e_c3
    z["y_logp"] = 100 * z.logp
    z["y_desc"] = 100 * z.desc
    z["w_compra"] = 1.0 / z.n_itens_indice
    z["eq_i"] = z.eq_ok.fillna(0.0)
    z["eq_i_aus"] = z.eq_ok.isna().astype(float)
    z["comp_i"] = z.comp.fillna(z.comp.median())
    z["comp_i_aus"] = z.comp.isna().astype(float)
    z["med_i"] = z.med.astype(float)
    freq_g = z.grupo.value_counts(normalize=True)
    z["grupo_x"] = np.where(z.grupo.map(freq_g).fillna(0) >= .005, z.grupo, "outros")
    # ------------------------------------------------------------- itens com situação final (homologação)
    z_status = z_status[z_status.compra.isin(cp.compra)]
    z_status = z_status.merge(cp[["compra", "regiao", "esfera", "hist_cat", "hist_log_n", "unidade"]], on="compra",
                              how="left")
    fx = cp.set_index("compra")
    cs = fx.loc[z_status.compra.unique(), ["n_itens_mat"]].copy()
    cs["faixa_itens"] = pd.qcut(cs.n_itens_mat.rank(method="first"), 10, labels=False).astype(int)
    z_status["faixa_itens"] = cs.faixa_itens.reindex(z_status.compra).to_numpy()
    z_status["parc_med"] = fx.med.reindex(z_status.compra).to_numpy()
    z_status["grupo"] = z_status.classe.astype(str).str[:2]
    z_status["grupo_x"] = np.where(z_status.grupo.map(z_status.grupo.value_counts(normalize=True)).fillna(0) >= .005,
                                   z_status.grupo, "outros")
    z_status["eq_i"] = z_status.eq_ok.fillna(0.0)
    z_status["eq_i_aus"] = z_status.eq_ok.isna().astype(float)
    z_status["comp_i"] = z_status.comp.fillna(z_status.comp.median())
    z_status["comp_i_aus"] = z_status.comp.isna().astype(float)
    z_status["med_i"] = z_status.med.astype(float)
    z_status["fra_ou_des"] = 1 - z_status.suc
    conta_status = {"itens_situacao_final": int(len(z_status)), "compras": int(z_status.compra.nunique()),
                    "homologados": float(z_status.suc.mean())}
    keep = ["compra", "u", "unidade", "cnpj", "m", "tri", "prod", "catmat", "grupo", "grupo_x", "af", "ok_ln10", "y", "y_c3",
            "y_logp", "y_desc", "w_compra", "eq_i", "eq_i_aus", "comp_i", "comp_i_aus", "med_i", "regiao", "esfera",
            "faixa_itens", "faixa_valor", "terco_valor", "hist_cat", "hist_log_n", "grupo_dom_x", "parc_med", "eq_c",
            "eq_c_aus", "comp_c", "comp_c_aus", "srp", "sig_c", "excl_c", "n_itens_indice", "sd_G", "baixa_disp"]
    z = z[keep].reset_index(drop=True)
    z.to_pickle(SAIDA / "itens.pkl")
    c.reset_index(drop=True).to_pickle(SAIDA / "compras.pkl")
    z_status.reset_index(drop=True).to_pickle(SAIDA / "itens_status.pkl")
    if not ((c.m >= M_INI) & (c.m <= M_FIM)).all():
        raise RuntimeError("compra fora do período entrou na amostra")
    info = {"exclusoes": exc, "status": conta_status, "periodo": [C.mes_str(C.M0 + M_INI), C.mes_str(C.M0 + M_FIM)],
            "limites_faixa_itens": {int(k): [float(a), float(b)] for k, (a, b) in lim_itens.iterrows()},
            "compras_analise": int(len(c)), "compras_AF": int(c.af.sum()), "itens_analise": int(z.ok_ln10.sum()),
            "itens_com_indice_fora_de_ln10_nas_compras": int((~z.ok_ln10).sum()),
            "ultimo_mes": C.mes_str(C.M0 + int(c.m.max()))}
    log("amostra", info["compras_analise"], "compras;", info["itens_analise"], "itens")
    return info


if __name__ == "__main__":
    import json
    print(json.dumps(construir(), ensure_ascii=False, indent=1, default=str))
