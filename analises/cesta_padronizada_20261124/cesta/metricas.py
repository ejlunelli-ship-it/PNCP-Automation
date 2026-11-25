"""Universo da cesta, funil de seleção e métricas de frequência/diversidade por família.

Regra fundamental: a frequência é contada em COMPRAS DISTINTAS (chave numero_controle_pncp). Várias
linhas do mesmo produto na mesma compra contam uma compra (o número de itens é preservado à parte).
"""
import json
import math

from .normalizacao import normalizar_texto

# Etapas do funil, aplicadas cumulativamente. Cada uma é uma condição SQL sobre a junção
# itens (i) × compras_base (c) × unidades (u) × brutos_por_item (b).
FUNIL = [
    ("0_fonte_dados_abertos", "1", "Itens de compras da fonte dados_abertos (Compras.gov.br), todas as modalidades"),
    ("1_pregao_eletronico", "c.modalidade = :modalidade", "Modalidade Pregão Eletrônico (qualquer modo de disputa)"),
    ("2_material", "i.material_ou_servico = :ms", "Item de material (M); serviços CATSER ficam de fora"),
    ("3_catmat_valido", "i.catmat IS NOT NULL", "Código de catálogo presente e numérico"),
    ("4_atributos_constantes", "i.atributos_conflitantes = 0",
     "Registros repetidos do item com o mesmo CATMAT, natureza e unidade"),
    ("5_uasg_valida", "c.uasg IS NOT NULL", "UASG da compra presente e numérica (até 6 dígitos)"),
    ("6_data_valida", "c.data_publicacao IS NOT NULL", "Data de publicação válida"),
    ("7_unidade_presente", "u.unidade_norm IS NOT NULL", "Unidade de fornecimento presente"),
]

DDL_UNIVERSO = """
DROP TABLE IF EXISTS universo;
CREATE TABLE universo AS
SELECT i.chave, i.numero_item, i.catmat, i.classe, i.pdm, i.homologado, i.situacoes, i.registros,
       i.unidade_original, u.unidade_norm, u.embalagem, u.conteudo, u.unidade_conteudo, u.alerta AS alerta_unidade,
       b.n_descricoes AS n_descricoes_item, b.nome_pdm,
       d.rowid AS desc_id, desc_completa(b.descricao_detalhada, b.nome_pdm) AS desc_completa,
       c.uasg, c.orgao_cnpj, c.data_publicacao, c.ano, c.trimestre, i.uasg_item, i.quantidade_min,
       CAST(i.catmat AS TEXT) || '|' || u.unidade_norm AS familia
FROM itens i
JOIN compras_base c USING (chave)
LEFT JOIN unidades u ON u.unidade_original = COALESCE(i.unidade_original, '')
LEFT JOIN brutos_por_item b USING (chave, numero_item)
LEFT JOIN descricoes d ON d.descricao_original = b.descricao_detalhada
WHERE {condicao};
CREATE INDEX ix_univ_fam ON universo (familia);
CREATE INDEX ix_univ_chave ON universo (chave);
"""


def _condicao(ate):
    return " AND ".join(f"({c})" for _, c, _ in FUNIL[: ate + 1])


def funil(dst, par):
    """Contagem de itens, compras, UASGs e famílias em cada etapa do funil (cumulativo)."""
    p = {"modalidade": par["universo"]["modalidade"], "ms": par["universo"]["material_ou_servico"]}
    base = ("FROM itens i JOIN compras_base c USING (chave) "
            "LEFT JOIN unidades u ON u.unidade_original = COALESCE(i.unidade_original, '') WHERE ")
    linhas, anterior = [], None
    for k, (nome, _, desc) in enumerate(FUNIL):
        r = dst.execute(f"SELECT COUNT(*), COUNT(DISTINCT i.chave), COUNT(DISTINCT c.uasg), SUM(i.homologado) "
                        f"{base} {_condicao(k)}", p).fetchone()
        linha = {"etapa": nome, "criterio": desc, "itens": r[0], "compras": r[1], "uasgs": r[2], "itens_homologados": r[3]}
        if anterior:
            linha["itens_perdidos"] = anterior["itens"] - r[0]
            linha["pct_itens_perdidos_etapa"] = round(100 * (anterior["itens"] - r[0]) / anterior["itens"], 4) if anterior["itens"] else None
            linha["compras_perdidas"] = anterior["compras"] - r[1]
        linhas.append(linha)
        anterior = linha
    return linhas


def desc_completa(descricao, nome_pdm):
    """1 se a descrição detalhada existe e traz algo além do nome do PDM (atributos); senão 0."""
    d = normalizar_texto(descricao)
    if not d:
        return 0
    n = normalizar_texto(nome_pdm)
    return 0 if (n and d == n) else 1


def registrar_funcoes(dst):
    dst.create_function("desc_completa", 2, desc_completa, deterministic=True)


def sql_universo(par):
    p = {"modalidade": par["universo"]["modalidade"], "ms": par["universo"]["material_ou_servico"]}
    sql = DDL_UNIVERSO.format(condicao=_condicao(len(FUNIL) - 1))
    # executescript não aceita parâmetros: os valores são substituídos com escape de aspas
    for k, v in p.items():
        sql = sql.replace(":" + k, "'" + str(v).replace("'", "''") + "'")
    return sql


def criar_universo(dst, par):
    registrar_funcoes(dst)
    sql = sql_universo(par)
    dst.executescript(sql)
    return sql


def hhi(contagens):
    """HHI (0-1) da distribuição de compras entre UASGs; 1/HHI = número efetivo de UASGs."""
    t = sum(contagens)
    if t == 0:
        return None
    return sum((x / t) ** 2 for x in contagens)


def metricas_familias(dst, tabela_saida, filtro="1", periodo=None, chave_familia="familia", origem="universo"):
    """Métricas por família (ou por produto, se chave_familia for outra coluna).

    filtro: condição SQL adicional (ex.: 'homologado = 1'); periodo: (ini, fim) ISO para uma cesta com
    período de formação explícito (não aplicado na cesta descritiva)."""
    cond = filtro
    if periodo:
        cond += f" AND data_publicacao BETWEEN '{periodo[0]}' AND '{periodo[1]}'"
    dst.executescript(f"""
        DROP TABLE IF EXISTS _fu;
        CREATE TEMP TABLE _fu AS
        SELECT {chave_familia} AS fam, uasg, COUNT(DISTINCT chave) AS compras
        FROM {origem} WHERE {cond} GROUP BY 1, 2;
        DROP TABLE IF EXISTS _fa;
        CREATE TEMP TABLE _fa AS
        SELECT {chave_familia} AS fam, COUNT(*) AS itens, COUNT(DISTINCT chave) AS compras,
               COUNT(DISTINCT uasg) AS uasgs, COUNT(DISTINCT orgao_cnpj) AS orgaos,
               COUNT(DISTINCT trimestre) AS trimestres, COUNT(DISTINCT ano) AS anos,
               MIN(data_publicacao) AS primeira, MAX(data_publicacao) AS ultima,
               SUM(homologado) AS itens_homologados,
               COUNT(DISTINCT CASE WHEN homologado = 1 THEN chave END) AS compras_homologadas,
               AVG(desc_completa * 1.0) AS share_desc_completa,
               COUNT(DISTINCT desc_id) AS n_descricoes_originais,
               COUNT(DISTINCT chave_textual) AS n_descricoes_distintas,
               MIN(catmat) AS catmat, MIN(unidade_norm) AS unidade_norm, MIN(classe) AS classe, MIN(pdm) AS pdm
        FROM {origem} o LEFT JOIN descricoes d ON d.rowid = o.desc_id WHERE {cond} GROUP BY 1;
    """)
    # concentração institucional calculada sobre compras por UASG
    conc = {}
    atual, vals = None, []
    for fam, c in dst.execute("SELECT fam, compras FROM _fu ORDER BY fam, compras DESC"):
        if fam != atual:
            if atual is not None:
                conc[atual] = vals
            atual, vals = fam, []
        vals.append(c)
    if atual is not None:
        conc[atual] = vals
    por_tri = {}
    for fam, t, n in dst.execute(f"SELECT {chave_familia}, trimestre, COUNT(DISTINCT chave) FROM {origem} "
                                 f"WHERE {cond} GROUP BY 1, 2 ORDER BY 1, 2"):
        por_tri.setdefault(fam, {})[t] = n
    por_ano = {}
    for fam, a, n in dst.execute(f"SELECT {chave_familia}, ano, COUNT(DISTINCT chave) FROM {origem} "
                                 f"WHERE {cond} GROUP BY 1, 2 ORDER BY 1, 2"):
        por_ano.setdefault(fam, {})[str(a)] = n
    dst.executescript(f"""
        DROP TABLE IF EXISTS {tabela_saida};
        CREATE TABLE {tabela_saida} (familia TEXT PRIMARY KEY, catmat INTEGER, unidade_norm TEXT, classe INTEGER,
            pdm INTEGER, itens INTEGER, compras INTEGER, uasgs INTEGER, orgaos INTEGER, trimestres INTEGER,
            anos INTEGER, primeira TEXT, ultima TEXT, itens_homologados INTEGER, compras_homologadas INTEGER,
            share_uasg_dominante REAL, hhi REAL, n_efetivo_uasgs REAL, share_top5 REAL, compras_uasg_max INTEGER,
            share_desc_completa REAL, n_descricoes_originais INTEGER, n_descricoes_distintas INTEGER,
            itens_por_compra REAL, compras_por_trimestre TEXT, compras_por_ano TEXT, distribuicao_uasg TEXT);
    """)
    linhas = []
    for r in dst.execute("SELECT * FROM _fa ORDER BY fam").fetchall():
        (fam, itens, compras, uasgs, orgaos, tri, anos, pri, ult, ih, ch, sdc, ndo, ndd, cat, un, cl, pdm) = r
        v = conc.get(fam, [])
        h = hhi(v)
        tot = sum(v)
        # distribuição resumida: quantas UASGs com 1, 2-4, 5-9, 10+ compras
        faixas = {"1": 0, "2-4": 0, "5-9": 0, "10+": 0}
        for x in v:
            faixas["1" if x == 1 else "2-4" if x < 5 else "5-9" if x < 10 else "10+"] += 1
        linhas.append((fam, cat, un, cl, pdm, itens, compras, uasgs, orgaos, tri, anos, pri, ult, ih, ch,
                       (v[0] / tot) if tot else None, h, (1 / h) if h else None,
                       (sum(v[:5]) / tot) if tot else None, v[0] if v else None,
                       sdc, ndo, ndd, itens / compras if compras else None,
                       json.dumps(por_tri.get(fam, {}), sort_keys=True), json.dumps(por_ano.get(fam, {}), sort_keys=True),
                       json.dumps(faixas)))
    dst.executemany(f"INSERT INTO {tabela_saida} VALUES ({','.join('?' * 27)})", linhas)
    dst.executescript("DROP TABLE IF EXISTS _fu; DROP TABLE IF EXISTS _fa;")
    return len(linhas)


def aplica_limiares(m, lim):
    """m: dict/row com as métricas; lim: dict de limiares. Devolve (passa, motivos_de_falha)."""
    falhas = []
    if m["compras"] < lim["compras_min"]:
        falhas.append(f"compras {m['compras']} < {lim['compras_min']}")
    if m["uasgs"] < lim["uasgs_min"]:
        falhas.append(f"UASGs {m['uasgs']} < {lim['uasgs_min']}")
    if m["trimestres"] < lim["trimestres_min"]:
        falhas.append(f"trimestres {m['trimestres']} < {lim['trimestres_min']}")
    if m["anos"] < lim["anos_min"]:
        falhas.append(f"anos {m['anos']} < {lim['anos_min']}")
    if m["share_uasg_dominante"] is None or m["share_uasg_dominante"] > lim["share_uasg_dominante_max"] + 1e-12:
        falhas.append(f"UASG dominante {m['share_uasg_dominante']:.3f} > {lim['share_uasg_dominante_max']}")
    if m["hhi"] is None or m["hhi"] > lim["hhi_max"] + 1e-12:
        falhas.append(f"HHI {m['hhi']:.4f} > {lim['hhi_max']}")
    return (not falhas), falhas


def isfinite(x):
    return x is not None and not (isinstance(x, float) and math.isnan(x))
