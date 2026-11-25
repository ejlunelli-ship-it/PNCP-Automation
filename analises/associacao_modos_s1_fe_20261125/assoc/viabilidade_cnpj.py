"""Viabilidade de um desenho em painel CNPJ × trimestre (DESCRITIVO: só contagens; nenhum efeito estimado).

Fontes (somente leitura):
- participação AF: TODAS as compras A/AF do Pregão Eletrônico (dados abertos) do CNPJ, contadas por compra
  (`atividade.pkl.gz` do estudo risk-set, extraído do pncp_v2.db);
- preços S1: amostra compra × produto deste estudo (homologados, preço > 0, sem filtro A1);
- cobertura CATMAT: itens de todas as compras A/AF por CNPJ × mês (consulta somente leitura ao pncp_v2.db).
Limiares em config.json["viabilidade_cnpj"], fixados antes de olhar os resultados.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from . import comum
from .comum import RES, TAB

SQL_CATMAT = """SELECT substr(c.data_abertura_proposta,1,7) AS ym, c.orgao_cnpj AS cnpj, COUNT(*) AS itens,
 SUM(i.cod_item_catalogo IS NOT NULL AND i.cod_item_catalogo <> '') AS com_catmat,
 SUM(i.material_ou_servico = 'M') AS material, SUM(i.homologado) AS homologados
 FROM compras c JOIN itens i ON i.numero_controle_pncp = c.numero_controle_pncp AND i.registro_principal = 1
 WHERE c.fonte='dados_abertos' AND c.modalidade_nome='Pregão - Eletrônico' AND c.modo_disputa IN ('Aberto','Aberto-Fechado')
 GROUP BY 1, 2"""


def _tri_de_data(s):
    a = pd.to_datetime(s.astype(str).str[:10], errors="coerce", format="%Y-%m-%d")
    return a.dt.year * 4 + (a.dt.month - 1) // 3


def cobertura_catmat(c, banco):
    p = comum.trabalho(c, "catmat_cnpj_mes.pkl")
    if p.exists():
        return pd.read_pickle(p)
    from em.comum import conectar_ro
    con = conectar_ro(banco)
    d = pd.read_sql_query(SQL_CATMAT, con)
    con.close()
    d.to_pickle(p)
    return d


def maior_sequencia(ts):
    ts = sorted(ts)
    best = cur = 1 if ts else 0
    for a, b in zip(ts, ts[1:]):
        cur = cur + 1 if b == a + 1 else 1
        best = max(best, cur)
    return best


def eventos(share, n, t_ini, t_fim, lim, min_c):
    """Primeiro evento relevante por CNPJ. share, n: DataFrames CNPJ × trimestre."""
    out = []
    for g in share.index:
        s, k = share.loc[g], n.loc[g]
        for t0 in range(t_ini + 2, t_fim):
            q = [t0 - 2, t0 - 1, t0, t0 + 1]
            if not all(k.get(x, 0) >= min_c for x in q):
                continue
            pre = (s[t0 - 2] + s[t0 - 1]) / 2
            pos = (s[t0] + s[t0 + 1]) / 2
            dif = pos - pre
            if abs(dif) >= lim:
                sg = np.sign(dif)
                pers = all(sg * (s[x] - pre) >= lim / 2 for x in (t0, t0 + 1))
                out.append({"cnpj": g, "t0": t0, "pre": pre, "pos": pos, "mudanca": dif, "direcao": "aumento AF" if dif > 0 else "redução AF",
                            "persistente": bool(pers)})
                break
    return pd.DataFrame(out)


def decomposicao(ev, uq):
    """Δ participação AF do CNPJ entre pré (t0−2..t0−1) e pós (t0..t0+1): dentro das UASGs presentes nos dois
    períodos (mudança de prática) × composição (peso das UASGs) × entrada/saída de UASGs."""
    linhas = []
    for e in ev.itertuples():
        x = uq[uq.cnpj == e.cnpj]
        pre = x[x.tri.isin([e.t0 - 2, e.t0 - 1])].groupby("uasg").agg(n=("n", "sum"), af=("n_af", "sum"))
        pos = x[x.tri.isin([e.t0, e.t0 + 1])].groupby("uasg").agg(n=("n", "sum"), af=("n_af", "sum"))
        S0, S1 = pre.af.sum() / pre.n.sum(), pos.af.sum() / pos.n.sum()
        com = pre.index.intersection(pos.index)
        w0, w1 = pre.n / pre.n.sum(), pos.n / pos.n.sum()
        s0, s1 = pre.af / pre.n, pos.af / pos.n
        wbar = (w0.reindex(com) + w1.reindex(com)) / 2
        sbar = (s0.reindex(com) + s1.reindex(com)) / 2
        dentro = float((wbar * (s1.reindex(com) - s0.reindex(com))).sum())
        compos = float((sbar * (w1.reindex(com) - w0.reindex(com))).sum())
        entsai = float((S1 - S0) - dentro - compos)
        linhas.append({"cnpj": e.cnpj, "t0": comum.nome_tri(e.t0), "delta": S1 - S0, "dentro_uasgs": dentro, "composicao_uasgs": compos,
                       "entrada_saida_uasgs": entsai, "uasgs_pre": len(pre), "uasgs_pos": len(pos), "uasgs_comuns": len(com),
                       "fracao_dentro": dentro / (S1 - S0) if S1 != S0 else np.nan})
    return pd.DataFrame(linhas)


def executar(c, log):
    v = c["viabilidade_cnpj"]
    t_ini, t_fim = (comum.tri(x) for x in v["trimestres_completos"])
    A = comum.ler_pkl(comum.trabalho(c, "amostra_compra_produto.pkl.gz"))
    d, nomes = A["d"], A["nomes"]
    ativ = comum.ler_pkl(Path(comum.ler_json(comum.RISK / "config.json")["trabalho"]) / "atividade.pkl.gz")
    co = ativ["compras"].copy()
    co["tri"] = _tri_de_data(co.data_abertura)
    co = co[co.tri.notna()].copy()
    co["tri"] = co.tri.astype(int)
    co["cnpj"] = co.orgao_cnpj.astype(str)
    co["uasg"] = co.uasg.astype(str).str.strip().str.zfill(6)
    co["af"] = (co.modo_disputa == "Aberto-Fechado").astype(int)
    cq = co.groupby(["cnpj", "tri"]).agg(n=("chave", "size"), n_af=("af", "sum")).reset_index()
    uq = co.groupby(["cnpj", "uasg", "tri"]).agg(n=("chave", "size"), n_af=("af", "sum")).reset_index()
    cq["share"] = cq.n_af / cq.n
    jan = cq[cq.tri.between(t_ini, t_fim)]
    share = jan.pivot(index="cnpj", columns="tri", values="share")
    nmat = jan.pivot(index="cnpj", columns="tri", values="n").fillna(0)
    res = {"periodo": f"{v['trimestres_completos'][0]}–{v['trimestres_completos'][1]}", "cnpjs_com_compras_AAF": int(cq.cnpj.nunique())}
    # 1. cobertura de preços S1
    dp = d[d.tri.between(t_ini, t_fim)]
    cov = dp.groupby("cnpj").agg(trimestres=("tri", "nunique"), obs=("chave", "size"), compras=("chave", "nunique"))
    cov["maior_sequencia"] = dp.groupby("cnpj").tri.apply(lambda s: maior_sequencia(set(s)))
    res["cobertura_precos_S1"] = {f">= {k} trimestres": int((cov.trimestres >= k).sum()) for k in (1, 2, 4, 6, 8, 10, 12)} | \
        {f">= {k} trimestres consecutivos": int((cov.maior_sequencia >= k).sum()) for k in (4, 6, 8)} | {"cnpjs_com_preco_S1": int(len(cov))}
    # 2. variação do tratamento
    ev = eventos(share, nmat, t_ini, t_fim, v["mudanca_relevante"], v["min_compras_trimestre"])
    ev_s = eventos(share, nmat, t_ini, t_fim, v["mudanca_sensibilidade"], v["min_compras_trimestre"])
    obs4 = int(sum(any(all(nmat.loc[g].get(x, 0) >= v["min_compras_trimestre"] for x in (t - 2, t - 1, t, t + 1))
                       for t in range(t_ini + 2, t_fim)) for g in nmat.index))
    res["variacao_tratamento"] = {"cnpjs_com_4_trimestres_consecutivos_com_>=3_compras": obs4,
                                  f"eventos_|Δ|>={v['mudanca_relevante']}": int(len(ev)), "persistentes": int(ev.persistente.sum()) if len(ev) else 0,
                                  "por_direcao": ev.direcao.value_counts().to_dict() if len(ev) else {},
                                  f"eventos_|Δ|>={v['mudanca_sensibilidade']}": int(len(ev_s)),
                                  "persistentes_sens": int(ev_s.persistente.sum()) if len(ev_s) else 0}
    # 3. comparadores estáveis
    obs_ok = nmat >= v["min_compras_trimestre"]
    sh_ok = share.where(obs_ok)
    nq = obs_ok.sum(1)
    amp = sh_ok.max(1) - sh_ok.min(1)
    est = sh_ok[(nq >= v["estavel_min_trimestres"]) & (amp <= v["estavel_amplitude_max"])]
    nivel = est.mean(1)
    faixas = pd.cut(nivel, [-0.01, 0.1, 0.3, 0.7, 0.9, 1.0], labels=["0–10%", "10–30%", "30–70%", "70–90%", "90–100%"])
    res["comparadores_estaveis"] = {"cnpjs_estaveis": int(len(est)), "por_nivel_AF": faixas.value_counts().sort_index().to_dict()}
    evp = ev[ev.persistente] if len(ev) else ev
    comp = []
    for e in evp.itertuples():
        obs_e = sh_ok[[e.t0 - 2, e.t0 - 1, e.t0, e.t0 + 1]].notna().all(1)
        cands = est.index[(est.index != e.cnpj) & obs_e.reindex(est.index).fillna(False).to_numpy()]
        pre_c = sh_ok.loc[cands, [e.t0 - 2, e.t0 - 1]].mean(1)
        sim = pre_c[(pre_c - e.pre).abs() <= v["comparador_dif_inicial_max"]]
        precos = dp[dp.cnpj.isin(sim.index) & dp.tri.isin([e.t0 - 1, e.t0])].groupby("cnpj").tri.nunique()
        comp.append({"cnpj": e.cnpj, "t0": comum.nome_tri(e.t0), "pre": e.pre, "comparadores_similares_estaveis": len(sim),
                     "comparadores_com_preco_S1_t-1_e_t0": int((precos == 2).sum())})
    comp = pd.DataFrame(comp)
    # 4. composição
    dec = decomposicao(evp, uq) if len(evp) else pd.DataFrame()
    if len(dec):
        res["composicao"] = {"eventos": int(len(dec)), "mediana_fracao_dentro_uasgs": float(dec.fracao_dentro.median()),
                             "eventos_majoritariamente_dentro (>50%)": int((dec.fracao_dentro > 0.5).sum()),
                             "eventos_com_uma_so_uasg_pre": int((dec.uasgs_pre == 1).sum()),
                             "soma_dentro": float(dec.dentro_uasgs.abs().sum()), "soma_composicao": float(dec.composicao_uasgs.abs().sum()),
                             "soma_entrada_saida": float(dec.entrada_saida_uasgs.abs().sum())}
    # 5–7. produtos, concentração, falsificação
    linhas = []
    for e in evp.itertuples():
        x = dp[dp.cnpj == e.cnpj]
        P = lambda ts: set(x[x.tri.isin(ts)].produto)
        pre, pos, fal = P([e.t0 - 2, e.t0 - 1]), P([e.t0, e.t0 + 1]), P([e.t0 - 4, e.t0 - 3])
        tri_ok = {t: bool((x.tri == t).any()) for t in range(e.t0 - 4, e.t0 + 2)}
        linhas.append({"cnpj": e.cnpj, "orgao": nomes.get(e.cnpj, ""), "t0": comum.nome_tri(e.t0), "direcao": e.direcao, "mudanca": e.mudanca,
                       "produtos_pre": len(pre), "produtos_pos": len(pos), "produtos_comuns_pre_pos": len(pre & pos),
                       "obs_pos_em_produtos_comuns": int(x[x.tri.isin([e.t0, e.t0 + 1]) & x.produto.isin(pre)].shape[0]),
                       "precos_t-4_a_t+1_todos": all(tri_ok.values()), "precos_t-4_t-3": tri_ok[e.t0 - 4] and tri_ok[e.t0 - 3],
                       "produtos_comuns_falsificacao_e_pre": len(fal & pre),
                       "modo_estavel_t-4_a_t-1": bool(sh_ok.loc[e.cnpj, [t for t in range(e.t0 - 4, e.t0) if t >= t_ini]].dropna().pipe(
                           lambda s: (s.max() - s.min()) <= v["mudanca_relevante"] / 2 if len(s) else False))})
    pe = pd.DataFrame(linhas)
    if len(pe):
        ok = pe[pe.produtos_comuns_pre_pos >= 1]
        w = ok.set_index("cnpj").obs_pos_em_produtos_comuns
        s = w / w.sum() if w.sum() > 0 else w
        res["produtos"] = {"eventos_persistentes": int(len(pe)), "com_>=1_produto_comum": int((pe.produtos_comuns_pre_pos >= 1).sum()),
                           "com_>=5": int((pe.produtos_comuns_pre_pos >= 5).sum()), "com_>=10": int((pe.produtos_comuns_pre_pos >= 10).sum()),
                           "mediana_produtos_comuns": float(pe.produtos_comuns_pre_pos.median())}
        res["concentracao"] = {"cnpjs_com_produto_comum": int(len(ok)), "n_efetivo_cnpjs_por_obs_comuns": float(1 / np.sum(s ** 2)) if len(s) else 0,
                               "maior_cnpj": nomes.get(s.idxmax(), "") if len(s) else None, "share_maior": float(s.max()) if len(s) else None,
                               "com_comparador_e_produto_comum": int(len(set(ok.cnpj) & set(comp.loc[comp["comparadores_com_preco_S1_t-1_e_t0"] > 0, "cnpj"])))
                               if len(comp) else 0}
        res["pre_tendencias"] = {"com_precos_t-4_t-3": int(pe["precos_t-4_t-3"].sum()), "com_precos_t-4_a_t+1": int(pe["precos_t-4_a_t+1_todos"].sum()),
                                 "com_produto_comum_falsificacao_e_pre": int((pe.produtos_comuns_falsificacao_e_pre >= 1).sum()),
                                 "modo_estavel_antes": int(pe["modo_estavel_t-4_a_t-1"].sum()),
                                 "todos_os_requisitos": int(((pe.produtos_comuns_pre_pos >= 1) & pe["precos_t-4_t-3"] &
                                                             (pe.produtos_comuns_falsificacao_e_pre >= 1) & pe["modo_estavel_t-4_a_t-1"]).sum())}
    # 8. cobertura temporal: ausência real × censura CATMAT
    banco = A["agreg"]["banco"]["caminho"]
    cm = cobertura_catmat(c, banco)
    cm["tri"] = (cm.ym.str[:4].astype(int) * 4 + (cm.ym.str[5:7].astype(int) - 1) // 3)
    cm["cnpj"] = cm.cnpj.astype(str)
    ct = cm.groupby("tri")[["itens", "com_catmat", "material", "homologados"]].sum().reset_index()
    ct["fracao_com_catmat"] = ct.com_catmat / ct.itens
    ct["trimestre"] = ct.tri.map(comum.nome_tri)
    ct = ct.merge(cq.groupby("tri").agg(compras_AAF=("n", "sum"), cnpjs=("cnpj", "nunique")).reset_index(), on="tri", how="left")
    ct = ct.merge(d.groupby("tri").agg(obs_precos_S1=("chave", "size"), cnpjs_com_preco_S1=("cnpj", "nunique")).reset_index(), on="tri", how="left")
    # classificação de cada CNPJ-trimestre com compras A/AF
    cg = cm.groupby(["cnpj", "tri"])[["itens", "com_catmat"]].sum().reset_index()
    base = cq.merge(cg, on=["cnpj", "tri"], how="left").fillna({"itens": 0, "com_catmat": 0})
    s1 = d.groupby(["cnpj", "tri"]).size().rename("obs_s1").reset_index()
    base = base.merge(s1, on=["cnpj", "tri"], how="left").fillna({"obs_s1": 0})
    base["situacao"] = np.select([base.obs_s1 > 0, base.com_catmat == 0, base.com_catmat > 0],
                                 ["com preço S1", "sem item com CATMAT (censura ou serviço sem código)", "com CATMAT, sem preço S1 (ausência real de S1)"],
                                 "outro")
    sit = base.pivot_table(index="tri", columns="situacao", values="cnpj", aggfunc="size", fill_value=0).reset_index()
    sit["trimestre"] = sit.tri.map(comum.nome_tri)
    res["cobertura_temporal"] = {"fracao_itens_com_catmat_por_trimestre": dict(zip(ct.trimestre, ct.fracao_com_catmat.round(4)))}
    for nome_t, df in (("viab_cnpj_cobertura.csv", cov.reset_index().assign(orgao=lambda x: x.cnpj.map(nomes))),
                       ("viab_cnpj_eventos.csv", ev.assign(trimestre=ev.t0.map(comum.nome_tri), orgao=ev.cnpj.map(nomes)) if len(ev) else ev),
                       ("viab_cnpj_eventos_sens.csv", ev_s), ("viab_cnpj_comparadores.csv", comp), ("viab_cnpj_composicao.csv", dec),
                       ("viab_cnpj_produtos_falsificacao.csv", pe), ("viab_cnpj_catmat_trimestre.csv", ct), ("viab_cnpj_situacao_trimestre.csv", sit)):
        comum.escrever_csv(TAB / nome_t, df.to_dict("records") if len(df) else [])
    comum.escrever_json(RES / "viabilidade_cnpj.json", res)
    log(f"viabilidade CNPJ: {res}")
    return res
