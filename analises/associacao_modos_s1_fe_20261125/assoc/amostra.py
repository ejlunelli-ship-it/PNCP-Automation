"""Amostra compra × produto S1 (anterior ao filtro de referência externa A1).

Itens da amostra S1 da rodada `efeito_modos_cesta_auto_S1_20261125` (708.964 itens ligados 1:1 ao pncp_v2.db),
conferidos de novo contra a tabela `compras` do banco (somente leitura): fonte Compras.gov.br (dados abertos),
Pregão Eletrônico, modo, UASG, CNPJ e UF. Filtros: modo A/AF, menor preço, data de abertura válida, homologado,
preço unitário positivo, produto S1. NÃO se exige referência externa (A1) nem se aplica a máscara |Y| ≤ ln 10.
Agregação: itens da mesma compra e produto → um registro, preço unitário médio ponderado pela quantidade.
"""
import hashlib

import numpy as np
import pandas as pd

from . import comum
from .comum import ErroDesenho

COLS_COMPRA = "numero_controle_pncp, fonte, modalidade_nome, modo_disputa, uasg, orgao_cnpj, orgao_nome, uf, esfera, data_abertura_proposta"


def localizar_banco(c):
    from em.comum import impressao_digital
    esp = c["fontes"]["pncp_v2_impressao_esperada"]
    for cand in c["fontes"]["pncp_v2_caminhos_candidatos"]:
        p = comum.resolver(cand)
        if p.exists():
            imp = impressao_digital(p)
            if imp["tamanho_bytes"] == esp["tamanho_bytes"] and imp["sha256_inicio_fim"] == esp["sha256_inicio_fim"]:
                return imp
    raise ErroDesenho("pncp_v2.db com a impressão esperada não encontrado")


def lista_S1(c):
    rod = comum.resolver(c["fontes"]["rodada_S1"])
    cong = comum.ler_json(rod / "congelamento.json")
    p = rod / "tabelas" / "conjuntos_amostras.csv"
    if comum.sha(p) != cong["sha256_conjuntos_amostras"]:
        raise ErroDesenho("conjuntos_amostras.csv da rodada S1 difere do congelamento")
    linhas = comum.ler_csv(p)
    s1 = sorted(r["produto"] for r in linhas if r["S1"] == "1")
    s2 = sorted(r["produto"] for r in linhas if r["S1S2"] == "1" and r["S1"] == "0")
    if hashlib.sha256("\n".join(s1).encode()).hexdigest() != cong["conjuntos"]["S1"]["sha256_lista"]:
        raise ErroDesenho("lista S1 não confere")
    return s1, s2


def compras_do_banco(banco, chaves):
    from em.comum import conectar_ro
    con = conectar_ro(banco)
    partes = []
    ch = sorted(chaves)
    for i in range(0, len(ch), 900):
        bloco = ch[i:i + 900]
        partes.append(pd.read_sql_query(f"SELECT {COLS_COMPRA} FROM compras WHERE numero_controle_pncp IN ({','.join('?' * len(bloco))})",
                                        con, params=bloco))
    con.close()
    return pd.concat(partes, ignore_index=True)


def agregar(it):
    """Itens → compra × produto. Preço = Σ p·q / Σ q se todas as q > 0; senão média simples (sinalizado)."""
    it = it.copy()
    it["q_ok"] = it.quantidade.gt(0) & it.quantidade.notna()
    it["pq"] = it.p_hom * it.quantidade.where(it.q_ok, 0)
    it["qpos"] = it.quantidade.where(it.q_ok, 0)
    g = it.groupby(["chave", "produto"], observed=True)
    a = g.agg(n_itens=("p_hom", "size"), p_media_simples=("p_hom", "mean"), soma_pq=("pq", "sum"),
              soma_q=("qpos", "sum"), q_todas_ok=("q_ok", "all"),
              modo=("modo_disputa", "first"), n_modos=("modo_disputa", "nunique"),
              uasg=("uasg", "first"), n_uasg=("uasg", "nunique"), cnpj=("orgao_cnpj", "first"),
              n_cnpj=("orgao_cnpj", "nunique"), uf=("uf", "first"), n_uf=("uf", "nunique"),
              tri=("tri", "first"), n_tri=("tri", "nunique")).reset_index()
    for k in ("n_modos", "n_uasg", "n_cnpj", "n_uf", "n_tri"):
        if (a[k] > 1).any():
            raise ErroDesenho(f"atributo de compra inconsistente dentro de compra × produto: {k}")
    a["preco"] = np.where(a.q_todas_ok, a.soma_pq / a.soma_q.where(a.soma_q > 0), a.p_media_simples)
    a["ponderado_por_quantidade"] = a.q_todas_ok
    a["quantidade"] = np.where(a.q_todas_ok, a.soma_q, np.nan)
    a["y"] = 100 * np.log(a.preco)
    a["lnq"] = np.log(a.quantidade)
    a["af"] = (a.modo == "Aberto-Fechado").astype(np.int8)
    # modo é atributo da compra: um único modo por compra (todas as linhas)
    mc = a.groupby("chave").modo.nunique()
    if (mc > 1).any():
        raise ErroDesenho(f"{int((mc > 1).sum())} compras com mais de um modo")
    if a.duplicated(["chave", "produto"]).any():
        raise ErroDesenho("compra × produto duplicado após agregação")
    return a.drop(columns=["soma_pq", "q_todas_ok", "n_modos", "n_uasg", "n_cnpj", "n_uf", "n_tri"])


def construir(c, log):
    banco = localizar_banco(c)
    s1, s2 = lista_S1(c)
    d1 = comum.resolver(c["fontes"]["dados_S1"])
    am = pd.read_pickle(d1 / "amostra.pkl")
    esp = c["fontes"]["contagens_S1_esperadas"]
    cont = {"produtos": int(am.produto.nunique()), "compras": int(am.chave.nunique()), "itens": int(len(am)), "uasgs": int(am.uasg.nunique())}
    if cont != esp:
        raise ErroDesenho(f"amostra S1 difere do esperado: {cont}")
    for k in ("uasg", "orgao_cnpj", "uf", "produto", "modo_disputa", "criterio_julgamento", "situacao_item"):
        am[k] = am[k].astype(str)
    log(f"amostra S1: {cont}; conferindo {am.chave.nunique():,} compras no pncp_v2.db (somente leitura)")
    co = compras_do_banco(banco["caminho"], set(am.chave))
    if co.numero_controle_pncp.duplicated().any():
        raise ErroDesenho("compra duplicada na tabela compras")
    co["uasg_n"] = co.uasg.astype(str).str.strip().str.zfill(6)
    m = am.merge(co.rename(columns={"numero_controle_pncp": "chave"}), on="chave", how="left", suffixes=("", "_db"), indicator=True)
    if len(m) != len(am):
        raise ErroDesenho("a ligação com compras duplicou itens")
    a = c["amostra"]
    conf = {"itens_sem_compra_no_banco": int((m._merge != "both").sum()),
            "modo_item_difere_do_banco": int((m.modo_disputa != m.modo_disputa_db).sum()),
            "uasg_difere": int((m.uasg.str.zfill(6) != m.uasg_n).sum()),
            "cnpj_difere": int((m.orgao_cnpj != m.orgao_cnpj_db.astype(str)).sum()),
            "uf_difere": int((m.uf != m.uf_db.astype(str)).sum()),
            "fonte_diferente": int((m.fonte != a["fonte"]).sum()), "modalidade_diferente": int((m.modalidade_nome != a["modalidade"]).sum())}
    log(f"conferência com o banco: {conf}")
    m["uasg"] = m.uasg.str.zfill(6)
    passos = [("0_itens_S1", pd.Series(True, index=m.index), "itens licitados dos 3.065 produtos S1"),
              ("1_compras_gov_pregao_eletronico", (m.fonte == a["fonte"]) & (m.modalidade_nome == a["modalidade"]), "Compras.gov.br (dados abertos), Pregão Eletrônico — conferido no banco"),
              ("2_modo_A_ou_AF", m.modo_disputa.isin(a["modos"]) & (m.modo_disputa == m.modo_disputa_db), "modo Aberto ou Aberto-Fechado (igual ao da compra no banco)"),
              ("3_menor_preco", m.criterio_julgamento == a["criterio"], "critério menor preço"),
              ("4_data_abertura_valida", m.tri.notna(), "data de abertura válida (trimestre)"),
              ("5_homologado", m.situacao_item == a["situacao"], "item homologado"),
              ("6_preco_positivo", m.p_hom > 0, "preço unitário homologado positivo"),
              ("7_produto_S1", m.produto.isin(set(s1)) & ~m.produto.isin(set(s2)), "produto S1 (nenhum S2)")]
    mask = pd.Series(True, index=m.index)
    funil = []
    for nome, cond, desc in passos:
        mask &= cond.fillna(False).astype(bool)
        s = m[mask]
        funil.append({"etapa": nome, "criterio": desc, "itens": int(mask.sum()), "compras": int(s.chave.nunique()),
                      "produtos": int(s.produto.nunique()), "uasgs": int(s.uasg.nunique()), "cnpjs": int(s.orgao_cnpj.nunique()),
                      "ufs": int(s.uf.nunique())})
    it = m[mask].copy()
    it["tri"] = it.tri.astype(int)
    d = agregar(it[["chave", "produto", "p_hom", "quantidade", "modo_disputa", "uasg", "orgao_cnpj", "uf", "tri"]])
    nomes = co.assign(cnpj=co.orgao_cnpj.astype(str)).groupby("cnpj").orgao_nome.agg(lambda s: s.mode().iat[0] if s.notna().any() else "")
    d["trimestre"] = d.tri.map(comum.nome_tri)
    inc = {comum.tri(x) for x in a["trimestres_incompletos"]}
    d["trimestre_incompleto"] = d.tri.isin(inc)
    funil.append({"etapa": "8_compra_x_produto", "criterio": "agregação compra × produto (itens duplicados ponderados pela quantidade)",
                  "itens": int(d.n_itens.sum()), "observacoes": int(len(d)), "compras": int(d.chave.nunique()),
                  "produtos": int(d.produto.nunique()), "uasgs": int(d.uasg.nunique()), "cnpjs": int(d.cnpj.nunique()), "ufs": int(d.uf.nunique())})
    agreg = {"observacoes": int(len(d)), "com_itens_duplicados": int((d.n_itens > 1).sum()),
             "itens_em_duplicados": int(d.loc[d.n_itens > 1, "n_itens"].sum()),
             "media_simples_por_quantidade_ausente": int((~d.ponderado_por_quantidade).sum()),
             "sem_lnq": int(d.lnq.isna().sum()), "conferencia_banco": conf, "banco": banco,
             "uf": a["uf"], "trimestres": d.groupby("trimestre").size().to_dict(),
             "obs_em_trimestres_incompletos": int(d.trimestre_incompleto.sum())}
    return d, pd.DataFrame(funil), agreg, nomes
