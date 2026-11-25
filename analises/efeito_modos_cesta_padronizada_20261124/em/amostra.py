"""Etapas 1–3: validar produtos aprovados, construir e auditar a amostra de preços, regime de modo por UASG.

Fontes (só leitura): a cesta congelada (CSVs + banco de trabalho da cesta, para o mapeamento item → produto) e o
pncp_v2.db (preços, modo, datas, SRP, sigilo). Nenhuma das duas é alterada.
"""
import csv
import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import comum
from .comum import ErroEstrutural

COLS = ["chave", "numero_item", "produto", "id_candidato", "classe_tecnica", "catmat", "unidade_norm",
        "uasg", "orgao_cnpj", "modo_disputa", "criterio_julgamento", "situacao_item", "homologado",
        "quantidade", "p_est", "p_hom", "orcamento_sigiloso", "srp", "data_publicacao", "data_abertura",
        "uf", "esfera", "poder", "id_compra"]


def _ler_csv(p):
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def validar_cesta(cam, reg, saidas):
    """Etapa 1: conjunto efetivamente aprovado e interseções reais dos conjuntos da cesta."""
    cp = cam["cesta_pasta"] / "saidas"
    cong = json.loads((cp / "congelamento_cesta.json").read_text(encoding="utf-8"))
    h = comum.sha256_arquivo(cp / "cesta_candidata.csv")
    if h != cong["sha256_cesta_candidata"]:
        raise ErroEstrutural("cesta_candidata.csv difere do congelamento da cesta")
    cand = _ler_csv(cp / "cesta_candidata.csv")
    valid = _ler_csv(cp / "cesta_validada.csv")
    form = _ler_csv(cp / "formulario_revisao.csv")
    pert = _ler_csv(cp / "sensibilidade_pertinencia.csv")
    rec = {r["produto"]: r for r in _ler_csv(cp / "recorrencia_temporal.csv")}
    familia = lambda p: p.split("#")[0]
    A = {c["produto"] for c in cand if c["classe_tecnica"] == "A"}
    B = {c["produto"] for c in cand if c["classe_tecnica"] == "B"}
    rig_fam = {r["familia"] for r in pert if r.get("rigoroso") == "1"}
    rig_prod = {c["produto"] for c in cand if familia(c["produto"]) in rig_fam}
    aprovados = {v["produto"] for v in valid}
    decisoes = sum(1 for f in form if (f.get("decisao (aprovar/rejeitar/dividir)") or "").strip())
    res = {
        "sha256_cesta_candidata": h, "cesta_congelada_em": cong["congelado_em"],
        "candidatos": len(cand), "classe_A": len(A), "classe_B": len(B),
        "familias_rigoroso": len(rig_fam), "produtos_candidatos_em_familias_rigoroso": len(rig_prod),
        "familias_rigoroso_fora_da_cesta": len(rig_fam - {familia(p) for p in A | B}),
        "A_e_rigoroso": len(A & rig_prod), "B_e_rigoroso": len(B & rig_prod), "A_fora_rigoroso": len(A - rig_prod),
        "produtos_aprovados": len(aprovados), "formulario_linhas": len(form), "formulario_com_decisao": decisoes,
        "recorrencia_todas_janelas": sum(1 for p in A | B if rec.get(p, {}).get("presente_todas_janelas") == "1"),
        "analise_principal_viavel": len(aprovados) > 0,
    }
    if not aprovados:
        reg.aviso("nenhum produto aprovado (cesta_validada.csv vazia): a análise principal NÃO é executável; "
                  "todas as estimativas são EXPLORATÓRIAS sobre a cesta candidata")
    comum.escrever_json(saidas / "tabelas" / "validacao_cesta.json", res)
    conj = pd.DataFrame({"produto": [c["produto"] for c in cand], "classe_tecnica": [c["classe_tecnica"] for c in cand]})
    conj["rigoroso"] = conj.produto.map(lambda p: int(familia(p) in rig_fam))
    conj["aprovado"] = conj.produto.isin(aprovados).astype(int)
    conj["recorrente"] = conj.produto.map(lambda p: int(rec.get(p, {}).get("presente_todas_janelas") == "1"))
    alertas = {c["produto"]: c["alertas_especificacao"] or "" for c in cand}
    # inconsistência técnica: alertas que não são categorias de cautela (assinaturas, embalagem, indicadores, PDM, unidade)
    def inconsistente(a):
        partes = [x for x in a.split(" | ") if x]
        return int(any(not x.startswith("cautela:") for x in partes))
    conj["inconsistencia_tecnica"] = conj.produto.map(lambda p: inconsistente(alertas[p]))
    return res, conj


def extrair(cam, cfg, reg, trabalho_db):
    """Etapa 2: amostra de preços ligada 1:1 ao pncp_v2.db; regime de modo por UASG × trimestre."""
    with reg.etapa("impressão digital do pncp_v2.db"):
        antes = comum.impressao_digital(cam["pncp_v2"])
        antes_cesta = comum.impressao_digital(cam["cesta_trabalho"])
    if trabalho_db.exists():
        trabalho_db.unlink()
    dst = comum.conectar_trabalho(trabalho_db)
    try:
        comum.anexar_ro(dst, cam["cesta_trabalho"], "cesta")
        comum.anexar_ro(dst, cam["pncp_v2"], "v2")
        dst.execute("BEGIN")
        with reg.etapa("chaves dos itens da cesta candidata (mapeamento congelado)"):
            dst.execute("""CREATE TABLE chaves AS
                SELECT u.chave, u.numero_item, u.produto, k.id_candidato, k.classe_tecnica, u.catmat, u.unidade_norm,
                       u.uasg AS uasg_cesta, u.orgao_cnpj AS cnpj_cesta, u.data_publicacao AS pub_cesta, u.homologado AS hom_cesta
                FROM cesta.universo_produto u JOIN cesta.cesta_candidata_tab k USING (produto)""")
            dst.execute("CREATE UNIQUE INDEX ix_ch ON chaves (chave, numero_item)")
            reg.contar("itens_cesta", dst.execute("SELECT COUNT(*) FROM chaves").fetchone()[0])
        with reg.etapa("ligação ao pncp_v2.db (registro_principal = 1)"):
            n_multi = dst.execute("""SELECT COUNT(*) FROM (SELECT ch.chave, ch.numero_item, COUNT(i.id) n FROM chaves ch
                JOIN v2.itens i ON i.numero_controle_pncp = ch.chave AND i.numero_item = ch.numero_item AND i.registro_principal = 1
                GROUP BY 1, 2 HAVING n > 1)""").fetchone()[0]
            if n_multi:
                raise ErroEstrutural(f"{n_multi} itens com mais de um registro_principal no pncp_v2.db")
            dst.execute("""CREATE TABLE amostra AS
                SELECT ch.chave, ch.numero_item, ch.produto, ch.id_candidato, ch.classe_tecnica, ch.catmat, ch.unidade_norm,
                       ch.uasg_cesta, ch.cnpj_cesta, ch.pub_cesta, ch.hom_cesta,
                       i.cod_item_catalogo AS catmat_v2, i.criterio_julgamento, i.situacao_item, i.homologado, i.quantidade,
                       i.valor_unitario_estimado AS p_est, i.valor_unitario_resultado AS p_hom, i.orcamento_sigiloso,
                       c.modo_disputa, c.srp, c.data_abertura_proposta AS data_abertura, c.data_publicacao, c.uf, c.esfera,
                       c.poder, c.uasg, c.orgao_cnpj, c.modalidade_nome, c.fonte, c.id_compra,
                       (i.id IS NOT NULL) AS ligou_item, (c.numero_controle_pncp IS NOT NULL) AS ligou_compra
                FROM chaves ch
                LEFT JOIN v2.itens i ON i.numero_controle_pncp = ch.chave AND i.numero_item = ch.numero_item AND i.registro_principal = 1
                LEFT JOIN v2.compras c ON c.numero_controle_pncp = ch.chave""")
            aud = dict(zip(["linhas", "sem_item", "sem_compra", "catmat_diverge", "uasg_diverge", "cnpj_diverge",
                            "publicacao_diverge", "homologado_diverge", "fonte_diverge", "modalidade_diverge"],
                           dst.execute("""SELECT COUNT(*), SUM(NOT ligou_item), SUM(NOT ligou_compra),
                SUM(catmat_v2 IS NOT catmat), SUM(uasg IS NOT uasg_cesta), SUM(orgao_cnpj IS NOT cnpj_cesta),
                SUM(substr(data_publicacao, 1, 10) IS NOT pub_cesta), SUM(homologado IS NOT hom_cesta),
                SUM(fonte IS NOT 'dados_abertos'), SUM(modalidade_nome IS NOT 'Pregão - Eletrônico') FROM amostra""").fetchone()))
            reg.contar("auditoria_ligacao", aud)
            if aud["linhas"] != reg.contagens["itens_cesta"] or aud["sem_item"] or aud["sem_compra"] or aud["catmat_diverge"]:
                raise ErroEstrutural(f"ligação cesta × pncp_v2 não confiável: {aud}")
        with reg.etapa("regime de modo por UASG × trimestre (todas as compras A/AF da fonte)"):
            dst.execute("""CREATE TABLE regime_compras AS
                SELECT numero_controle_pncp AS chave, uasg, orgao_cnpj, modo_disputa, data_abertura_proposta AS data_abertura,
                       data_publicacao
                FROM v2.compras WHERE fonte = 'dados_abertos' AND modalidade_nome = 'Pregão - Eletrônico'
                  AND modo_disputa IN ('Aberto', 'Aberto-Fechado') AND uasg IS NOT NULL""")
            reg.contar("compras_regime", dst.execute("SELECT COUNT(*) FROM regime_compras").fetchone()[0])
        dst.execute("COMMIT")
    finally:
        dst.close()
    comum.conferir_inalterado(antes, cam["pncp_v2"])
    comum.conferir_inalterado(antes_cesta, cam["cesta_trabalho"])
    return {"pncp_v2": antes, "cesta_trabalho": antes_cesta}


def carregar(trabalho_db, cfg):
    """Amostra em pandas com tipos compactos e variáveis derivadas (sem decidir elegibilidade ainda)."""
    con = comum.conectar_trabalho(trabalho_db)
    df = pd.read_sql_query("SELECT chave, numero_item, produto, id_candidato, classe_tecnica, catmat, unidade_norm, uasg, "
                           "orgao_cnpj, modo_disputa, criterio_julgamento, situacao_item, homologado, quantidade, p_est, "
                           "p_hom, orcamento_sigiloso, srp, data_publicacao, data_abertura, uf, esfera, poder, id_compra "
                           "FROM amostra", con)
    reg_c = pd.read_sql_query("SELECT chave, uasg, orgao_cnpj, modo_disputa, data_abertura FROM regime_compras", con)
    con.close()
    # UASG com 6 dígitos (o pncp_v2 guarda '2300' e '002300'; a cesta usa a forma normalizada) — só preenchimento
    for t in (df, reg_c):
        t["uasg"] = t["uasg"].astype(str).str.strip().str.zfill(6)
    for c in ["produto", "id_candidato", "classe_tecnica", "unidade_norm", "uasg", "orgao_cnpj", "modo_disputa",
              "criterio_julgamento", "situacao_item", "uf", "esfera", "poder"]:
        df[c] = df[c].astype("category")
    df["data_abertura"] = df["data_abertura"].str[:10]
    df["data_publicacao"] = df["data_publicacao"].str[:10]
    a = pd.to_datetime(df["data_abertura"], errors="coerce", format="%Y-%m-%d")
    df["tri"] = (a.dt.year * 4 + (a.dt.month - 1) // 3).astype("Int64")
    df["mes"] = (a.dt.year * 12 + a.dt.month - 1).astype("Int64")
    df["ano"] = a.dt.year.astype("Int64")
    df["af"] = (df["modo_disputa"] == "Aberto-Fechado").astype("int8")
    with np.errstate(divide="ignore", invalid="ignore"):
        df["logp"] = np.where(df["p_hom"] > 0, np.log(df["p_hom"].where(df["p_hom"] > 0)), np.nan)
        df["logq"] = np.where(df["quantidade"] > 0, np.log(df["quantidade"].where(df["quantidade"] > 0)), np.nan)
    reg_c["data_abertura"] = reg_c["data_abertura"].str[:10]
    ra = pd.to_datetime(reg_c["data_abertura"], errors="coerce", format="%Y-%m-%d")
    reg_c["tri"] = (ra.dt.year * 4 + (ra.dt.month - 1) // 3).astype("Int64")
    reg_c["af"] = (reg_c["modo_disputa"] == "Aberto-Fechado").astype("int8")
    return df, reg_c


def funil(df, cfg, conj):
    """Funil de elegibilidade (cumulativo) com itens, compras, produtos, UASGs e órgãos (CNPJ)."""
    a = cfg["amostra"]
    passos = [
        ("0_cesta_candidata", pd.Series(True, index=df.index), "Itens licitados dos produtos da cesta candidata"),
        ("1_compras_gov_pregao_eletronico", pd.Series(True, index=df.index), "Compras.gov.br, Pregão Eletrônico (já garantido pela cesta; conferido na ligação)"),
        ("2_modo_A_ou_AF", df.modo_disputa.isin(a["modos"]), "Modo Aberto ou Aberto-Fechado"),
        ("3_menor_preco", df.criterio_julgamento == a["criterio"], "Critério de julgamento Menor preço"),
        ("4_data_abertura_valida", df.tri.notna(), "Data de abertura válida (define o trimestre)"),
        ("5_homologado", df.situacao_item == a["situacao_homologado"], "Item homologado"),
        ("6_preco_positivo", df.p_hom > 0, "Preço unitário homologado positivo"),
    ]
    aprovados = set(conj.loc[conj.aprovado == 1, "produto"])
    passos.append(("7_produto_aprovado", df.produto.isin(aprovados), "Produto com aprovação técnica documentada (cesta validada)"))
    linhas, m = [], pd.Series(True, index=df.index)
    masks = {}
    for nome, cond, desc in passos:
        m = m & cond
        masks[nome] = m.copy()
        s = df[m]
        linhas.append({"etapa": nome, "criterio": desc, "itens": int(m.sum()), "compras": int(s.chave.nunique()),
                       "produtos": int(s.produto.nunique()), "uasgs": int(s.uasg.nunique()), "orgaos_cnpj": int(s.orgao_cnpj.nunique())})
    return linhas, masks
