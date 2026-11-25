"""Diagnósticos de suporte (posteriores ao estudo; DESCRITIVOS — contagens e disponibilidade, nenhum efeito estimado).

Unidades institucionais: UASG, CNPJ (órgão) e UF (estado).

1. Coexistência de A e AF na mesma unidade × período e na mesma unidade × produto × período (trimestre, semestre,
   ano), em quatro níveis: todas as compras A/AF; compras com itens S1 elegíveis (modo A/AF, menor preço); itens S1
   com preço homologado; itens S1 com índice A1. Avalia se haveria suporte para um desenho no nível da licitação
   (A × AF dentro da instituição e do período), sem resolver a seleção do modo.
2. Origem da ausência de índice S1 nas unidade-trimestres com compras A/AF (2023T2–2026T1): cascata exclusiva
   (sem item S1 → fora de A/AF ou de menor preço → sem homologação → sem preço → sem referência externa → valor
   extremo) e potencial de recuperação de dados OBSERVÁVEIS: itens em andamento, preço alternativo no banco,
   referência em células mais largas (produto × semestre/ano, mesmos mínimos, leave-one-UASG-out) e cestas mais
   amplas (S1+S2, P1, cesta candidata). Nada disso altera o protocolo congelado; qualquer uso exigiria pré-registro.
"""
import numpy as np
import pandas as pd

from . import comum
from .comum import PASTA

TAB, RES = PASTA / "tabelas", PASTA / "resultados"
UNIDADES = {"uasg": "UASG", "cnpj": "CNPJ (órgão)", "uf": "UF (estado)"}
MODOS, CRIT = ["Aberto", "Aberto-Fechado"], "Menor preço"


def _per(tri, periodo):
    tri = tri.astype(int)
    if periodo == "trimestre":
        return tri
    if periodo == "semestre":
        return (tri // 4) * 2 + (tri % 4) // 2
    return tri // 4


def _neff(s):
    s = s / s.sum()
    return float(1 / np.sum(s ** 2)) if len(s) else 0.0


def coexistencia(niveis, periodos=("trimestre", "semestre", "ano")):
    """niveis: {nome: DataFrame com uasg, cnpj, uf, chave, af, tri[, produto]} (uma linha por item ou por compra)."""
    linhas, por_tri = [], []
    for nome, d in niveis.items():
        for periodo in periodos:
            x = d.assign(p=_per(d.tri, periodo), a=1 - d.af.astype(int), af=d.af.astype(int))
            for un, rot_un in UNIDADES.items():
                for com_prod in (False, True):
                    if com_prod and "produto" not in x:
                        continue
                    cel = [un] + (["produto"] if com_prod else []) + ["p"]
                    comp = x.drop_duplicates(cel + ["chave"])
                    g = comp.groupby(cel, observed=True).agg(n_A=("a", "sum"), n_AF=("af", "sum"))
                    amb = g[(g.n_A > 0) & (g.n_AF > 0)]
                    chaves_amb = pd.MultiIndex.from_frame(amb.reset_index()[cel])
                    sel = comp[pd.MultiIndex.from_frame(comp[cel]).isin(chaves_amb)]
                    it = x[pd.MultiIndex.from_frame(x[cel]).isin(chaves_amb)] if com_prod else None
                    unid_amb = amb.index.get_level_values(un) if len(amb) else pd.Index([])
                    linhas.append({
                        "nivel": nome, "periodo": periodo, "unidade": rot_un,
                        "celula": f"{rot_un} × produto × {periodo}" if com_prod else f"{rot_un} × {periodo}",
                        "celulas_observadas": int(len(g)), "celulas_com_A_e_AF": int(len(amb)),
                        "fracao_com_A_e_AF": float(len(amb) / len(g)) if len(g) else np.nan,
                        "compras_A_nessas_celulas": int(amb.n_A.sum()), "compras_AF_nessas_celulas": int(amb.n_AF.sum()),
                        "fracao_compras_em_celulas_mistas": float(sel.chave.nunique() / comp.chave.nunique()) if len(comp) else np.nan,
                        "itens_nessas_celulas": int(len(it)) if it is not None else None,
                        "unidades_distintas": int(unid_amb.nunique()),
                        "n_efetivo_unidades": _neff(pd.Series(unid_amb).value_counts()) if len(amb) else 0.0,
                        "share_top1_unidade": float(pd.Series(unid_amb).value_counts().iloc[0] / len(amb)) if len(amb) else np.nan,
                        "uasgs": int(sel.uasg.nunique()), "cnpjs": int(sel.cnpj.nunique()), "ufs": int(sel.uf.nunique()),
                        "produtos": int(amb.index.get_level_values("produto").nunique()) if com_prod and len(amb) else None,
                        "celulas_com_2+_compras_em_cada_modo": int(((amb.n_A >= 2) & (amb.n_AF >= 2)).sum()),
                        "mediana_compras_por_celula": float((amb.n_A + amb.n_AF).median()) if len(amb) else np.nan})
                    if periodo == "trimestre":
                        for p, gg in amb.groupby(level="p"):
                            por_tri.append({"nivel": nome, "unidade": rot_un, "com_produto": com_prod, "trimestre": comum.nome_tri(p),
                                            "celulas_com_A_e_AF": len(gg), "unidades": int(gg.index.get_level_values(un).nunique())})
    return pd.DataFrame(linhas), pd.DataFrame(por_tri)


def contagem_referencia(pool, celula, min_itens=5, min_uasgs=3):
    """Haveria referência leave-one-UASG-out numa célula produto × período mais larga? (mesmos mínimos; contagem)."""
    c = pool[["produto", "uasg"]].assign(cel=np.asarray(celula))
    n_c = c.groupby(["produto", "cel"], observed=True).uasg.transform("size")
    n_cu = c.groupby(["produto", "cel", "uasg"], observed=True).uasg.transform("size")
    k_c = c.groupby(["produto", "cel"], observed=True).uasg.transform("nunique")
    return ((n_c - n_cu) >= min_itens) & ((k_c - 1) >= min_uasgs)


def _causa(r):
    if r.com_indice:
        return "0_com_indice"
    if r.itens_s1 == 0:
        return "1_sem_item_de_produto_S1"
    if r.aaf == 0:
        return "2_itens_S1_so_fora_de_A_AF_ou_de_menor_preco"
    if r.hom == 0:
        if r.andamento > 0 and r.andamento >= max(r.fd, r.canc):
            return "3a_sem_homologacao_em_andamento"
        if r.fd >= r.canc:
            return "3b_sem_homologacao_fracassado_deserto"
        return "3c_sem_homologacao_anulado_cancelado"
    if r.preco == 0:
        return "4_homologado_sem_preco_unitario"
    if r.ref == 0:
        return "5_sem_referencia_externa"
    if r.idx == 0:
        return "6_valor_extremo_fora_de_ln10"
    return "7_outro"


def executar(c, log):
    d1 = comum.resolver(c["fontes"]["dados_S1"])
    am = pd.read_pickle(d1 / "amostra.pkl")
    idx = pd.read_pickle(d1 / "indices.pkl")
    reg = pd.read_pickle(d1 / "regime_compras.pkl")
    t_p0, t_p1 = comum.tri(c["periodo"]["preco_primeiro"]), comum.tri(c["periodo"]["preco_ultimo"])
    at = comum.ler_pkl(comum.trabalho(c, "atividade.pkl.gz"))["compras"][["chave", "uf"]]
    reg = reg[reg.tri.notna() & reg.tri.between(t_p0, t_p1)].copy()
    reg["tri"] = reg.tri.astype(int)
    reg["uasg"] = reg.uasg.astype(str).str.strip().str.zfill(6)
    reg = reg.merge(at, on="chave", how="left").rename(columns={"orgao_cnpj": "cnpj"})
    reg["uf"] = reg.uf.fillna("?")
    am = am[am.tri.notna()].copy()
    am["tri"] = am.tri.astype(int)
    am = am[am.tri.between(t_p0, t_p1)].join(idx[["ref_ok", "mascara_A1"]], how="left")
    for k in ("uasg", "orgao_cnpj", "uf", "produto"):
        am[k] = am[k].astype(str)
    am = am.rename(columns={"orgao_cnpj": "cnpj"})
    for k in ("ref_ok", "mascara_A1"):
        am[k] = am[k].astype("boolean").fillna(False).astype(bool)
    aaf = am.modo_disputa.isin(MODOS) & (am.criterio_julgamento == CRIT)
    hom = am.situacao_item == "Homologado"
    preco = hom & (am.p_hom > 0)
    cols = ["uasg", "cnpj", "uf", "chave", "af", "tri", "produto"]
    # ---------------------------------------------------------------- 1. coexistência
    log("diagnóstico 1: coexistência de A e AF (UASG, CNPJ, UF)")
    niveis = {"1_todas_as_compras_AAF": reg[["uasg", "cnpj", "uf", "chave", "af", "tri"]],
              "2_compras_com_item_S1_elegivel": am.loc[aaf, cols],
              "3_itens_S1_com_preco_homologado": am.loc[aaf & preco, cols],
              "4_itens_S1_com_indice_A1": am.loc[aaf & preco & am.mascara_A1, cols]}
    co, co_t = coexistencia(niveis)
    comum.escrever_csv(TAB / "diag_coexistencia_A_AF.csv", co.to_dict("records"))
    comum.escrever_csv(TAB / "diag_coexistencia_A_AF_por_trimestre.csv", co_t.to_dict("records"))
    # ---------------------------------------------------------------- 2. ausência de índice
    log("diagnóstico 2: origem da ausência de índice S1 (UASG, CNPJ, UF)")
    pool = am[aaf & preco][["produto", "uasg", "tri"]].copy()
    am["ref_semestre"] = False
    am["ref_ano"] = False
    am.loc[pool.index, "ref_semestre"] = contagem_referencia(pool, _per(pool.tri, "semestre")).to_numpy()
    am.loc[pool.index, "ref_ano"] = contagem_referencia(pool, _per(pool.tri, "ano")).to_numpy()
    g = am.assign(e_aaf=aaf, e_hom=aaf & hom, e_preco=aaf & preco, e_ref=aaf & preco & am.ref_ok, e_idx=aaf & preco & am.mascara_A1,
                  e_andamento=aaf & (am.situacao_item == "Em andamento"), e_fd=aaf & am.situacao_item.isin(["Fracassado", "Deserto"]),
                  e_canc=aaf & (am.situacao_item == "Anulado/Revogado/Cancelado"),
                  e_rsem=aaf & preco & (am.mascara_A1 | am.ref_semestre), e_rano=aaf & preco & (am.mascara_A1 | am.ref_ano))
    extras = {}
    for nome, pasta in (("S1S2", c["fontes"]["dados_S1S2"]), ("P1", "D:/efeito_modos_auto_S1/P1"), ("cesta", c["fontes"]["dados_cesta"])):
        a2 = pd.read_pickle(comum.resolver(pasta) / "amostra.pkl")[["uasg", "orgao_cnpj", "uf", "tri", "modo_disputa", "criterio_julgamento"]]
        a2 = a2.join(pd.read_pickle(comum.resolver(pasta) / "indices.pkl")[["mascara_A1"]], how="inner")
        a2 = a2[a2.mascara_A1 & a2.modo_disputa.isin(MODOS) & (a2.criterio_julgamento == CRIT) & a2.tri.notna()]
        extras[nome] = pd.DataFrame({"uasg": a2.uasg.astype(str).to_numpy(), "cnpj": a2.orgao_cnpj.astype(str).to_numpy(),
                                     "uf": a2.uf.astype(str).to_numpy(), "tri": a2.tri.astype(int).to_numpy()})
        del a2
    sem_preco = am[aaf & hom & ~(am.p_hom > 0)][["chave", "numero_item"]]
    alt = {"itens_homologados_sem_preco": int(len(sem_preco)), "com_valor_alternativo_no_banco": 0}
    if len(sem_preco):
        from em.comum import conectar_ro
        con = conectar_ro(comum.ler_json(RES / "fontes.json")["pncp_v2"]["caminho"])
        for ch, ni in zip(sem_preco.chave, sem_preco.numero_item):
            r = con.execute("""SELECT valor_negociado_aceito, lance_aceito, valor_total_resultado, quantidade_resultado FROM itens
                               WHERE numero_controle_pncp = ? AND numero_item = ? AND registro_principal = 1""", (ch, int(ni))).fetchone()
            if r and (any(v not in (None, "", 0) for v in r[:2]) or (r[2] and r[3])):
                alt["com_valor_alternativo_no_banco"] += 1
        con.close()
    cascatas, por_tri, resumo = [], [], {}
    uts = {}
    for un, rot in UNIDADES.items():
        obs = reg.groupby([un, "tri"]).chave.nunique().rename("n_compras_AAF").reset_index()
        agg = g.groupby([un, "tri"], observed=True).agg(
            itens_s1=("chave", "size"), aaf=("e_aaf", "sum"), hom=("e_hom", "sum"), preco=("e_preco", "sum"), ref=("e_ref", "sum"),
            idx=("e_idx", "sum"), andamento=("e_andamento", "sum"), fd=("e_fd", "sum"), canc=("e_canc", "sum"),
            rsem=("e_rsem", "sum"), rano=("e_rano", "sum")).reset_index()
        ut = obs.merge(agg, on=[un, "tri"], how="left")
        ut = ut.fillna({k: 0 for k in agg.columns if k not in (un, "tri")})
        ut["com_indice"] = ut.idx > 0
        for nome, e in extras.items():
            k = e.groupby([un, "tri"]).size().rename(f"idx_{nome}").reset_index()
            ut = ut.merge(k, on=[un, "tri"], how="left").fillna({f"idx_{nome}": 0})
        ut["causa"] = [_causa(r) for r in ut.itertuples()]
        uts[un] = ut
        tot, sem = len(ut), ut[~ut.com_indice]
        for k, gq in ut.groupby("causa"):
            s0 = k.startswith("0_")
            cascatas.append({"unidade": rot, "causa": k, "unidade_trimestres": int(len(gq)), "fracao_do_total": len(gq) / tot,
                             "fracao_dos_sem_indice": None if s0 else len(gq) / len(sem), "compras_AAF": int(gq.n_compras_AAF.sum()),
                             "unidades": int(gq[un].nunique()), "itens_S1_licitados": int(gq.itens_s1.sum()),
                             "recupera_ref_produto_semestre": None if s0 else int((gq.rsem > 0).sum()),
                             "recupera_ref_produto_ano": None if s0 else int((gq.rano > 0).sum()),
                             "teria_indice_S1S2": None if s0 else int((gq.idx_S1S2 > 0).sum()),
                             "teria_indice_P1": None if s0 else int((gq.idx_P1 > 0).sum()),
                             "teria_indice_cesta": None if s0 else int((gq.idx_cesta > 0).sum())})
        pt = ut.assign(trimestre=ut.tri.map(comum.nome_tri)).pivot_table(index="trimestre", columns="causa", values="tri",
                                                                         aggfunc="size", fill_value=0).reset_index()
        pt.insert(0, "unidade", rot)
        por_tri.append(pt)
        resumo[un] = {"unidade_trimestres": tot, "com_indice": int(ut.com_indice.sum()), "fracao_sem_indice": float(len(sem) / tot),
                      "com_indice_ref_semestre": int((ut.com_indice | (ut.rsem > 0)).sum()),
                      "com_indice_ref_ano": int((ut.com_indice | (ut.rano > 0)).sum()),
                      "com_indice_S1S2": int((ut.idx_S1S2 > 0).sum()), "com_indice_P1": int((ut.idx_P1 > 0).sum()),
                      "com_indice_cesta": int((ut.idx_cesta > 0).sum())}
    comum.escrever_csv(TAB / "diag_ausencia_indice_cascata.csv", cascatas)
    comum.escrever_csv(TAB / "diag_ausencia_indice_por_trimestre.csv", pd.concat(por_tri).fillna(0).to_dict("records"))
    # foco no desenho (eventos são de UASG): trimestres t0−2 e t0−1 dos 309 eventos da janela
    ut = uts["uasg"]
    ev = comum.ler_pkl(comum.trabalho(c, "eventos.pkl.gz"))
    ev = ev[ev.janela_principal_calendario]
    foco = pd.concat([ev[["uasg", "t0", "id_evento"]].assign(tri=ev.t0 + r, rel=r) for r in (-2, -1)]).merge(ut, on=["uasg", "tri"], how="left")
    foco["causa"] = foco.causa.fillna("sem_compras_AAF_no_trimestre")
    fc = foco.groupby(["rel", "causa"]).size().unstack(fill_value=0).reset_index()
    comum.escrever_csv(TAB / "diag_ausencia_indice_eventos_t-2_t-1.csv", fc.to_dict("records"))

    def n_ev(col):
        return int(foco.assign(ok=col(foco).fillna(False).astype(bool)).groupby("id_evento").ok.all().sum())
    ganhos = {"atual_A1_trimestre": n_ev(lambda f: f.com_indice), "ref_produto_semestre": n_ev(lambda f: f.rsem > 0),
              "ref_produto_ano": n_ev(lambda f: f.rano > 0), "cesta_S1S2": n_ev(lambda f: f.idx_S1S2 > 0),
              "cesta_P1": n_ev(lambda f: f.idx_P1 > 0), "cesta_candidata": n_ev(lambda f: f.idx_cesta > 0),
              "_nota": "eventos (dos 309 da janela) com índice em t0−2 E t0−1; só disponibilidade, sem as demais exigências do desenho"}
    res = {"gerado_em": comum.agora(), "por_unidade": resumo, "preco_alternativo": alt, "eventos_com_t-2_e_t-1_por_fonte": ganhos}
    comum.escrever_json(RES / "diagnosticos_suporte.json", res)
    log(f"diagnósticos: {res}")
    return [TAB / "diag_coexistencia_A_AF.csv", TAB / "diag_coexistencia_A_AF_por_trimestre.csv", TAB / "diag_ausencia_indice_cascata.csv",
            TAB / "diag_ausencia_indice_por_trimestre.csv", TAB / "diag_ausencia_indice_eventos_t-2_t-1.csv", RES / "diagnosticos_suporte.json"]
