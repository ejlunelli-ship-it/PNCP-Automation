"""Decomposição das diferenças entre amostras (eventos, seleção de produtos, ponderação, órgãos) e composição da S1.

Usa as classes e funções do estudo anterior (importadas, não modificadas). A população comum de eventos é fixada
filtrando os SWITCHERS dos blocos do dCDH; os controles (não tratados ou ainda não tratados) ficam inalterados.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from . import base


def _abrir(pasta, nome):
    return pd.read_pickle(Path(pasta) / f"{nome}.pkl")


def _dados(c, nome):
    return Path(c["dados_base"]) if nome == "cesta" else Path(c["trabalho"]) / nome


def _saida(c, nome):
    return base.resolver(c["estudo_anterior"]) if nome == "cesta" else base.PASTA / "amostras" / nome


def switchers_com_peso(c, nome):
    pop = base.ler_csv(_saida(c, nome) / "tabelas" / "populacao_eventos_pesos.csv")
    return sorted({r["uasg"] for r in pop if int(float(r["l"])) >= 1 and float(r["peso"]) > 0})


def dcdh_restrito(c, nome, uasgs_alvo, B, semente, L, log):
    """dCDH principal (janela principal, por item, pesos por célula) da amostra `nome` com switchers restritos a
    `uasgs_alvo` (None = todos). Devolve linhas resumidas e diagnósticos de eventos e órgãos."""
    base.estudo_anterior(c)
    from em.descritivas import base_principal
    from em.eventos import DCDH, TROCA, bootstrap, painel, resumir
    d = _dados(c, nome)
    E = _abrir(d, "eventos_info")
    info, tri_ini, tri_fim = E["info"], E["tri_ini"], E["tri_fim"]
    df = base_principal(_abrir(d, "amostra"), _abrir(d, "indices"))
    unidades = info.uasg.tolist()
    cnpj_cod = pd.factorize(info.cnpj.fillna("?"))[0]
    Y, N = painel(df, unidades, tri_ini, tri_fim, "y_A1", "item")
    est = DCDH(Y, N, info, L, L, peso_switcher="celula")
    if uasgs_alvo is not None:
        alvo = np.flatnonzero(info.uasg.astype(str).isin(set(uasgs_alvo)).to_numpy() & (info.tipo.to_numpy() == TROCA))
        novos = []
        for b in est.blocos:
            k = np.isin(b["s"], alvo)
            if k.any():
                novos.append({**b, "s": b["s"][k], "dY_s": b["dY_s"][k], "w_s": b["w_s"][k]})
        est.blocos = novos
    ponto, pesos, chaves, draws = bootstrap(est, cnpj_cod, B, semente)
    linhas = resumir(ponto, chaves, draws)
    pop = est.populacao()
    pop = pop[pop.l >= 1]
    w = pop.groupby(pop.linha.map(lambda i: info.cnpj.iat[i]))["peso"].sum()
    s = w / w.sum() if w.sum() > 0 else w
    diag = {"eventos_l1": int(pop[pop.l == 1].linha.nunique()), "eventos_algum_l": int(pop.linha.nunique()),
            "cnpjs": int(len(w)), "n_efetivo_cnpjs": float(1 / np.sum(s ** 2)) if len(s) else np.nan,
            "peso_maior_cnpj": float(s.max()) if len(s) else np.nan, "itens_amostra": int(len(df))}
    log(f"  {nome} ({'eventos da S1' if uasgs_alvo is not None else 'todos os eventos'}): "
        f"agregado {ponto.get(('agregado', 'media'), np.nan):.2f} lp; {diag['eventos_l1']} eventos em l=1")
    return linhas, diag


def decompor(c, nomes, log=print, bootstrap=None):
    base.verificar_congelamento(c)
    base.estudo_anterior(c)
    from em import comum as em_comum
    cfg_ant = em_comum.carregar_config(base.resolver(c["estudo_anterior"]) / "config.json")
    ev = cfg_ant["eventos"]
    L = ev["janelas_trimestres"][ev["janela_principal"]]
    B = bootstrap or ev["bootstrap"]
    sem = cfg_ant["semente"]
    alvo = switchers_com_peso(c, "S1")
    log(f"população de eventos da S1: {len(alvo)} UASGs com troca e peso em l ≥ 1")
    out, diags = [], []
    for nome in ["S1"] + [n for n in ("S1S2", "P1", "cesta") if n in nomes + ["cesta"]]:
        for rotulo, u in (("propria", None), ("eventos_S1", alvo)):
            if nome == "S1" and rotulo == "eventos_S1":
                continue
            linhas, diag = dcdh_restrito(c, nome, u, B, sem, L, log)
            for l in linhas:
                l.update({"amostra": nome, "populacao_eventos": rotulo})
            out += linhas
            diags.append({"amostra": nome, "populacao_eventos": rotulo, **diag})
    base.escrever_csv(base.PASTA / "tabelas" / "decomposicao_dcdh.csv", out)
    base.escrever_csv(base.PASTA / "tabelas" / "decomposicao_eventos_orgaos.csv", diags)
    return out, diags


# ------------------------------------------------------------------------------------------------ composição
def _hhi(s):
    p = s / s.sum()
    return float((p ** 2).sum())


def composicao(c, log=print):
    """Composição dos conjuntos (diagnóstico; não altera a classificação)."""
    base.verificar_congelamento(c)
    conj, st, _ = base.conjuntos(c)
    auto = base.resolver(c["validacao_automatica"])
    p1base = {r["produto"]: r for r in base.ler_csv(base.resolver(c["validacao_automatica"]).parent / "P1" / "base_produtos.csv")
              if r["tipo_registro"] == "PRODUTO"}
    grupos = {"S1": set(conj["S1"]), "S2": set(conj["S1S2"]) - set(conj["S1"]),
              "P1_inconclusivos": {p for p, s in st.items() if s in ("AUTO_INCONCLUSIVO", "AUTO_ERRO_DADOS", "AUTO_DIVERGENTE", "AUTO_DESMEMBRAR")},
              "P1": set(conj["P1"]), "cesta": set(conj["cesta"])}
    df = pd.read_pickle(Path(c["dados_base"]) / "amostra.pkl")
    cols = [x for x in ("produto", "chave", "uasg", "orgao_cnpj", "ano", "tri", "quantidade", "modo_disputa", "elegivel_preco") if x in df.columns]
    df = df[cols]
    linhas, classes, anos = [], [], []
    for g, prods in grupos.items():
        d = df[df.produto.isin(prods)]
        dp = d[d.elegivel_preco] if "elegivel_preco" in d else d
        comp = d.groupby("produto").chave.nunique()
        org = dp.groupby("orgao_cnpj").size()
        af = d.drop_duplicates("chave")
        q = pd.to_numeric(dp.get("quantidade"), errors="coerce") if "quantidade" in dp else pd.Series(dtype=float)
        linhas.append({"grupo": g, "produtos": len(prods), "itens": len(d), "itens_preco_positivo": len(dp), "compras": d.chave.nunique(),
                       "uasgs": d.uasg.nunique(), "orgaos": d.orgao_cnpj.nunique(),
                       "compras_por_produto_mediana": float(comp.median()) if len(comp) else np.nan,
                       "compras_por_produto_media": float(comp.mean()) if len(comp) else np.nan,
                       "quantidade_mediana": float(q.median()) if len(q) else np.nan,
                       "log10_quantidade_media": float(np.log10(q[q > 0]).mean()) if len(q) else np.nan,
                       "hhi_orgaos_itens": _hhi(org) if len(org) else np.nan,
                       "participacao_maior_orgao": float(org.max() / org.sum()) if len(org) else np.nan,
                       "n_efetivo_orgaos": float(1 / _hhi(org)) if len(org) else np.nan,
                       "fracao_compras_AF": float((af.modo_disputa == "Aberto-Fechado").mean()) if "modo_disputa" in af else np.nan,
                       "classe_catalogo_mais_frequente": pd.Series([p1base[p]["classe_catalogo"] for p in prods if p in p1base]).mode().iat[0]
                       if any(p in p1base for p in prods) else ""})
        if g in ("S1", "S2", "P1_inconclusivos", "P1"):
            cl = pd.Series([p1base[p]["classe_catalogo"] for p in prods if p in p1base]).value_counts()
            for k, v in cl.head(15).items():
                classes.append({"grupo": g, "classe_catalogo": k, "produtos": int(v), "fracao": float(v / cl.sum())})
            for k, v in d.groupby("ano").size().items():
                anos.append({"grupo": g, "ano": int(k), "itens": int(v), "fracao": float(v / len(d))})
    # riscos (marcas da auditoria) por status
    riscos = []
    for g in ("S1", "S2", "P1_inconclusivos"):
        ps = [p1base[p] for p in grupos[g] if p in p1base]
        cont = pd.Series([r for p in ps for r in (p["requer_especialista"] or "sem_risco").split(";")]).value_counts()
        for k, v in cont.items():
            riscos.append({"grupo": g, "categoria": k, "produtos": int(v), "fracao_do_grupo": float(v / len(ps))})
    base.escrever_csv(base.PASTA / "tabelas" / "composicao_conjuntos.csv", linhas)
    base.escrever_csv(base.PASTA / "tabelas" / "composicao_classes.csv", classes)
    base.escrever_csv(base.PASTA / "tabelas" / "composicao_anos.csv", anos)
    base.escrever_csv(base.PASTA / "tabelas" / "composicao_riscos.csv", riscos)
    log("composição: " + "; ".join(f"{x['grupo']} {x['produtos']} produtos, AF {x['fracao_compras_AF']:.3f}" for x in linhas))
    return linhas
