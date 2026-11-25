"""Extração do universo do pncp.db (somente leitura) para o banco de trabalho.

Só são copiadas colunas não monetárias e sem o modo de disputa. A deduplicação dos registros de
item não usa `registro_principal` (que prioriza o valor do resultado): o item é a chave composta
(numero_controle_pncp, numero_item), e seus atributos de produto precisam ser constantes entre os
registros; caso contrário o item é marcado e auditado.
"""
from .comum import ErroEstrutural
from .normalizacao import (normalizar_catmat, normalizar_cnpj, normalizar_data, normalizar_texto,
                           normalizar_uasg, normalizar_unidade, trimestre)

LOTE = 100_000

DDL = """
DROP TABLE IF EXISTS universo_compras;
CREATE TABLE universo_compras (fonte TEXT, modalidade TEXT, situacao TEXT, compras INTEGER,
    data_min TEXT, data_max TEXT);
DROP TABLE IF EXISTS universo_itens;
CREATE TABLE universo_itens (fonte TEXT, modalidade TEXT, material_ou_servico TEXT, tem_catalogo INTEGER,
    linhas INTEGER, itens INTEGER);
DROP TABLE IF EXISTS compras_base;
CREATE TABLE compras_base (
    chave TEXT PRIMARY KEY, id_compra TEXT, uasg_original TEXT, uasg TEXT, orgao_cnpj_original TEXT,
    orgao_cnpj TEXT, orgao_nome TEXT, numero_compra TEXT, ano_compra INTEGER, modalidade TEXT,
    data_publicacao_original TEXT, data_publicacao TEXT, data_abertura_original TEXT, data_abertura TEXT,
    ano INTEGER, trimestre TEXT, uf TEXT, esfera TEXT, poder TEXT);
DROP TABLE IF EXISTS itens_linhas;
CREATE TABLE itens_linhas (
    id INTEGER PRIMARY KEY, chave TEXT NOT NULL, numero_item INTEGER, id_compra_item TEXT,
    registro_principal INTEGER, uasg_item_original TEXT, uasg_item TEXT, catmat_original TEXT, catmat INTEGER,
    material_ou_servico TEXT, classe INTEGER, grupo INTEGER, pdm INTEGER, unidade_original TEXT,
    descricao_resumida TEXT, quantidade REAL, situacao TEXT, homologado INTEGER, criterio TEXT,
    data_atualizacao TEXT);
"""


def _sql_universo_compras(m):
    c = lambda k: m[k]["coluna"]
    sit = c("compra.situacao") or "NULL"
    return (f"SELECT {c('compra.fonte')}, {c('compra.modalidade')}, {sit}, COUNT(*), "
            f"MIN({c('compra.data_publicacao')}), MAX({c('compra.data_publicacao')}) "
            f"FROM compras GROUP BY 1, 2, 3 ORDER BY 1, 2, 3")


def _sql_universo_itens(m):
    c = lambda k: m[k]["coluna"]
    return (f"SELECT co.{c('compra.fonte')}, co.{c('compra.modalidade')}, i.{c('item.material_servico')}, "
            f"i.{c('item.catmat')} IS NOT NULL, COUNT(*), "
            f"COUNT(DISTINCT i.{c('item.chave_compra')} || '#' || i.{c('item.numero')}) "
            f"FROM itens i JOIN compras co ON co.{c('compra.chave')} = i.{c('item.chave_compra')} "
            f"GROUP BY 1, 2, 3, 4 ORDER BY 1, 2, 3, 4")


def contar_universo_total(src, dst, mapa, reg):
    """Contagem descritiva do universo total do PNCP (todas as fontes e modalidades)."""
    with reg.etapa("universo total: compras"):
        sql = _sql_universo_compras(mapa)
        reg.consulta("universo_compras", sql)
        dst.executemany("INSERT INTO universo_compras VALUES (?,?,?,?,?,?)", src.execute(sql).fetchall())
    with reg.etapa("universo total: itens (varredura completa)"):
        sql = _sql_universo_itens(mapa)
        reg.consulta("universo_itens", sql)
        dst.executemany("INSERT INTO universo_itens VALUES (?,?,?,?,?,?)", src.execute(sql).fetchall())
    orfaos_sql = (f"SELECT COUNT(*) FROM itens i WHERE NOT EXISTS (SELECT 1 FROM compras c WHERE "
                  f"c.{mapa['compra.chave']['coluna']} = i.{mapa['item.chave_compra']['coluna']})")
    with reg.etapa("universo total: itens sem compra"):
        reg.consulta("itens_orfaos", orfaos_sql)
        reg.contar("itens_sem_compra_total", src.execute(orfaos_sql).fetchone()[0])


def extrair(src, dst, mapa, par, reg):
    """Copia compras e linhas de item da fonte do universo (todas as modalidades, para o funil)."""
    c = lambda k: mapa[k]["coluna"]
    dst.executescript(DDL)
    contar_universo_total(src, dst, mapa, reg)
    fonte = par["universo"]["fonte"]

    sql_c = (f"SELECT {c('compra.chave')}, {c('compra.id_compra')}, {c('compra.uasg')}, {c('compra.orgao_cnpj')}, "
             f"{c('compra.orgao_nome')}, {c('compra.numero_compra')}, {c('compra.ano_compra')}, "
             f"{c('compra.modalidade')}, {c('compra.data_publicacao')}, {c('compra.data_abertura')}, "
             f"{c('compra.uf')}, {c('compra.esfera')}, {c('compra.poder')} "
             f"FROM compras WHERE {c('compra.fonte')} = ? ORDER BY {c('compra.chave')}")
    reg.consulta("compras_base", sql_c)
    with reg.etapa("extração: compras"):
        cur = src.execute(sql_c, (fonte,))
        n = 0
        while True:
            bloco = cur.fetchmany(LOTE)
            if not bloco:
                break
            linhas = []
            for (ch, idc, uasg, cnpj, nome, num, ano_c, mod, dpub, dab, uf, esf, pod) in bloco:
                dp = normalizar_data(dpub)
                linhas.append((ch, idc, uasg, normalizar_uasg(uasg), cnpj, normalizar_cnpj(cnpj), nome, num, ano_c,
                               mod, dpub, dp, dab, normalizar_data(dab), int(dp[:4]) if dp else None,
                               trimestre(dp), uf, esf, pod))
            dst.executemany("INSERT INTO compras_base VALUES (" + ",".join("?" * 19) + ")", linhas)
            n += len(bloco)
        reg.contar("compras_base", n)

    sql_i = (f"SELECT i.{c('item.id')}, i.{c('item.chave_compra')}, i.{c('item.numero')}, i.{c('item.id_compra_item')}, "
             f"i.{c('item.registro_principal')}, i.{c('item.uasg')}, i.{c('item.catmat')}, i.{c('item.material_servico')}, "
             f"i.{c('item.classe')}, i.{c('item.grupo')}, i.{c('item.pdm')}, i.{c('item.unidade')}, "
             f"i.{c('item.descricao_resumida')}, i.{c('item.quantidade')}, i.{c('item.situacao')}, "
             f"i.{c('item.homologado')}, i.{c('item.criterio')}, i.{c('item.data_atualizacao')} "
             f"FROM compras co JOIN itens i ON i.{c('item.chave_compra')} = co.{c('compra.chave')} "
             f"WHERE co.{c('compra.fonte')} = ? ORDER BY i.{c('item.id')}")
    reg.consulta("itens_linhas", sql_i)
    with reg.etapa("extração: linhas de item"):
        cur = src.execute(sql_i, (fonte,))
        n = 0
        while True:
            bloco = cur.fetchmany(LOTE)
            if not bloco:
                break
            linhas = [(i, ch, ni, idci, rp, ua, None if cm is None else str(cm), normalizar_catmat(cm), ms, cl, gr, pdm,
                       un, desc, q, sit, hom, crit, dat)
                      for (i, ch, ni, idci, rp, ua, cm, ms, cl, gr, pdm, un, desc, q, sit, hom, crit, dat) in bloco]
            # uasg_item normalizada inserida depois (coluna 7) para manter a tupla legível
            linhas = [l[:6] + (normalizar_uasg(l[5]),) + l[6:] for l in linhas]
            dst.executemany("INSERT INTO itens_linhas VALUES (" + ",".join("?" * 20) + ")", linhas)
            n += len(bloco)
            if n % 1_000_000 < LOTE:
                print(f"    {n:,} linhas", flush=True)
        reg.contar("itens_linhas", n)
    with reg.etapa("índices do banco de trabalho"):
        dst.execute("CREATE INDEX ix_il_item ON itens_linhas (chave, numero_item)")


DDL_ITENS = """
DROP TABLE IF EXISTS itens_conflitos;
CREATE TABLE itens_conflitos AS
SELECT chave, numero_item, COUNT(*) AS registros,
       COUNT(DISTINCT COALESCE(catmat, -1)) AS n_catmat,
       COUNT(DISTINCT COALESCE(material_ou_servico, '?')) AS n_ms,
       COUNT(DISTINCT COALESCE(unidade_original, '?')) AS n_unidade,
       COUNT(DISTINCT COALESCE(uasg_item, '?')) AS n_uasg_item
FROM itens_linhas GROUP BY chave, numero_item HAVING COUNT(*) > 1;

DROP TABLE IF EXISTS itens;
CREATE TABLE itens AS
SELECT l.chave, l.numero_item,
       COUNT(*) AS registros,
       MIN(l.id) AS id_min,
       MIN(l.catmat) AS catmat, MIN(l.catmat_original) AS catmat_original,
       MIN(l.material_ou_servico) AS material_ou_servico,
       MIN(l.classe) AS classe, MIN(l.grupo) AS grupo, MIN(l.pdm) AS pdm,
       MIN(l.unidade_original) AS unidade_original,
       MIN(l.descricao_resumida) AS descricao_resumida,
       MIN(l.uasg_item) AS uasg_item, MIN(l.uasg_item_original) AS uasg_item_original,
       MAX(l.homologado) AS homologado,
       GROUP_CONCAT(DISTINCT l.situacao) AS situacoes,
       MIN(l.quantidade) AS quantidade_min, MAX(l.quantidade) AS quantidade_max,
       MIN(l.criterio) AS criterio,
       (COUNT(DISTINCT COALESCE(l.catmat, -1)) > 1 OR COUNT(DISTINCT COALESCE(l.material_ou_servico, '?')) > 1
        OR COUNT(DISTINCT COALESCE(l.unidade_original, '?')) > 1) AS atributos_conflitantes
FROM itens_linhas l GROUP BY l.chave, l.numero_item;
CREATE UNIQUE INDEX ix_itens_chave ON itens (chave, numero_item);
"""


def deduplicar_itens(dst, reg):
    """Um registro por item (chave composta). Atributos de produto devem ser constantes."""
    with reg.etapa("deduplicação dos itens (chave composta)"):
        dst.executescript(DDL_ITENS)
        n_itens = dst.execute("SELECT COUNT(*) FROM itens").fetchone()[0]
        n_rep = dst.execute("SELECT COUNT(*), COALESCE(SUM(registros), 0) FROM itens_conflitos").fetchone()
        n_conf = dst.execute("SELECT COUNT(*) FROM itens WHERE atributos_conflitantes").fetchone()[0]
        reg.contar("itens_distintos", n_itens)
        reg.contar("itens_com_registros_repetidos", n_rep[0])
        reg.contar("registros_em_itens_repetidos", n_rep[1])
        reg.contar("itens_atributos_conflitantes", n_conf)
        # cardinalidade da junção item -> compra: cada item deve ter exatamente uma compra
        orf = dst.execute("SELECT COUNT(*) FROM itens i LEFT JOIN compras_base c USING (chave) "
                          "WHERE c.chave IS NULL").fetchone()[0]
        if orf:
            raise ErroEstrutural(f"{orf} itens extraídos sem compra correspondente na fonte do universo")
        dup_c = dst.execute("SELECT COUNT(*) - COUNT(DISTINCT chave) FROM compras_base").fetchone()[0]
        if dup_c:
            raise ErroEstrutural(f"{dup_c} chaves de compra duplicadas em compras_base")


def normalizar_unidades(dst, aliases, reg):
    """Tabela de correspondência unidade original -> normalizada (todas as formas observadas)."""
    with reg.etapa("normalização das unidades"):
        dst.executescript("""
            DROP TABLE IF EXISTS unidades;
            CREATE TABLE unidades (unidade_original TEXT PRIMARY KEY, unidade_texto TEXT, unidade_norm TEXT,
                embalagem TEXT, conteudo TEXT, unidade_conteudo TEXT, alerta TEXT, itens INTEGER);""")
        linhas = []
        for (u, n) in dst.execute("SELECT unidade_original, COUNT(*) FROM itens GROUP BY 1").fetchall():
            r = normalizar_unidade(u, aliases)
            linhas.append((u if u is not None else "", normalizar_texto(u), r["unidade_norm"], r["embalagem"],
                           r["conteudo"], r["unidade_conteudo"], r["alerta"], n))
        dst.executemany("INSERT INTO unidades VALUES (?,?,?,?,?,?,?,?)", linhas)
        reg.contar("unidades_formas_originais", len(linhas))
        reg.contar("unidades_formas_normalizadas",
                   dst.execute("SELECT COUNT(DISTINCT unidade_norm) FROM unidades").fetchone()[0])
