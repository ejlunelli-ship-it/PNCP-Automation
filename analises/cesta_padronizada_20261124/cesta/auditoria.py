"""Controle de qualidade e integridade dos dados (seção 11). Nenhum registro é eliminado em silêncio:
cada verificação informa afetados, percentual, critério, quantos foram excluídos, exemplos e o impacto
sobre os candidatos."""


def _um(dst, sql, p=()):
    return dst.execute(sql, p).fetchone()[0]


def _exemplos(dst, sql, n):
    cur = dst.execute(sql + f" LIMIT {int(n)}")
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def verificar(dst, par, reg, candidatos_tab="cesta_candidata_tab"):
    """Lista de verificações. Supõe as tabelas do banco de trabalho já criadas (universo, cesta)."""
    ex = par["saida"]["exemplos_auditoria"]
    n_itens = _um(dst, "SELECT COUNT(*) FROM itens")
    n_linhas = _um(dst, "SELECT COUNT(*) FROM itens_linhas")
    n_compras = _um(dst, "SELECT COUNT(*) FROM compras_base")
    mod = par["universo"]["modalidade"]
    import time
    tem_cand = _um(dst, f"SELECT COUNT(*) FROM sqlite_master WHERE name = '{candidatos_tab}'") > 0

    def impacto(sub):
        """Produtos candidatos com algum item no subconjunto `sub` (colunas chave, numero_item), por junção indexada."""
        if not tem_cand:
            return None
        dst.executescript("DROP TABLE IF EXISTS _imp; CREATE TEMP TABLE _imp (chave TEXT, numero_item INTEGER, "
                          "PRIMARY KEY (chave, numero_item)) WITHOUT ROWID;")
        dst.execute(f"INSERT OR IGNORE INTO _imp SELECT chave, numero_item FROM ({sub})")
        return _um(dst, f"SELECT COUNT(DISTINCT u.produto) FROM _imp m JOIN universo_produto u "
                        f"ON u.chave = m.chave AND u.numero_item = m.numero_item JOIN {candidatos_tab} k USING (produto)")

    v = []
    relogio = [time.time()]

    def add(nome, afetados, base, criterio, excluidos, exemplos, impacto_cand=None, base_nome="itens", obs=""):
        if reg.verboso:
            print(f"    auditoria: {nome} ({time.time() - relogio[0]:.1f} s)", flush=True)
        relogio[0] = time.time()
        v.append({"verificacao": nome, "afetados": afetados, "base": base, "base_nome": base_nome,
                  "pct": round(100 * afetados / base, 4) if base else None, "criterio": criterio,
                  "excluidos": excluidos, "impacto_produtos_candidatos": impacto_cand, "observacao": obs,
                  "exemplos": exemplos})

    # 1. chaves de compra duplicadas
    add("chaves de compra duplicadas", _um(dst, "SELECT COUNT(*) - COUNT(DISTINCT chave) FROM compras_base"), n_compras,
        "numero_controle_pncp é chave primária no banco; conferido de novo na extração (erro se > 0)", 0, [],
        base_nome="compras")
    # 2. chaves de item duplicadas (registros repetidos)
    rep = _um(dst, "SELECT COUNT(*) FROM itens_conflitos")
    add("itens com mais de um registro (mesma chave composta)", rep, n_itens,
        "colapsados em um item pela chave (numero_controle_pncp, numero_item); não se usa registro_principal",
        0, _exemplos(dst, "SELECT * FROM itens_conflitos ORDER BY registros DESC, chave", ex),
        obs=f"{_um(dst, 'SELECT COALESCE(SUM(registros),0) FROM itens_conflitos')} registros nesses itens")
    conf = "SELECT chave, numero_item FROM itens WHERE atributos_conflitantes"
    add("itens cujos registros divergem em CATMAT, natureza ou unidade", _um(dst, f"SELECT COUNT(*) FROM ({conf})"), n_itens,
        "excluídos do universo (etapa 4 do funil): o produto do item não é identificável", _um(dst, f"SELECT COUNT(*) FROM ({conf})"),
        _exemplos(dst, "SELECT l.chave, l.numero_item, l.catmat, l.material_ou_servico, l.unidade_original, l.situacao "
                       "FROM itens_linhas l JOIN itens i USING (chave, numero_item) WHERE i.atributos_conflitantes "
                       "ORDER BY l.chave, l.numero_item", ex))
    # 3. junções
    lig = dict(dst.execute("SELECT tipo, COUNT(*) FROM ligacao_divergencias GROUP BY 1").fetchall())
    add("junção item -> compra (N:1)", 0, n_itens, "cada item tem exatamente uma compra; erro explícito se não", 0, [])
    add("junção banco -> brutos (descrição detalhada)", sum(lig.values()), n_itens,
        "mesmo número de registros por item, mesmo CATMAT; divergência de cardinalidade/CATMAT interrompe a execução; "
        "divergência só de unidade é auditada", 0,
        _exemplos(dst, "SELECT * FROM ligacao_divergencias ORDER BY tipo, chave", ex), obs=str(lig))
    # só itens com mais de um registro podem ter descrições diferentes: restringe pela tabela itens_conflitos
    md_sql = ("SELECT b.chave, b.numero_item, b.registros_brutos, b.descricao_detalhada, b.descricao_detalhada_max "
              "FROM itens_conflitos c JOIN brutos_por_item b USING (chave, numero_item) WHERE b.n_descricoes > 1")
    md = _um(dst, f"SELECT COUNT(*) FROM ({md_sql})")
    add("itens com descrições detalhadas diferentes entre registros", md, n_itens,
        "mantida a menor (ordem lexicográfica); todas as variantes ficam em brutos_itens", 0,
        _exemplos(dst, md_sql + " ORDER BY b.chave", ex),
        impacto(f"SELECT chave, numero_item FROM ({md_sql})"))
    # 4. itens sem compra / compras sem itens
    add("itens sem compra correspondente (banco inteiro)", reg.contagens.get("itens_sem_compra_total", 0) or 0, n_linhas,
        "contados na varredura do banco de origem; não entram no universo", 0, [], base_nome="linhas de item")
    sem_itens = "SELECT c.chave, c.uasg, c.modalidade, c.data_publicacao FROM compras_base c WHERE NOT EXISTS (SELECT 1 FROM itens i WHERE i.chave = c.chave)"
    add("compras sem itens (fonte do universo)", _um(dst, f"SELECT COUNT(*) FROM ({sem_itens})"), n_compras,
        "não geram itens; ficam fora naturalmente", 0, _exemplos(dst, sem_itens, ex), base_nome="compras")
    # 5. CATMAT
    pe = f"FROM itens i JOIN compras_base c USING (chave) WHERE c.modalidade = '{mod}' AND i.material_ou_servico = 'M'"
    n_pe_m = _um(dst, f"SELECT COUNT(*) {pe}")
    add("CATMAT nulo em item de material (pregão eletrônico)", _um(dst, f"SELECT COUNT(*) {pe} AND i.catmat IS NULL"), n_pe_m,
        "excluídos (etapa 3): sem código não há família", _um(dst, f"SELECT COUNT(*) {pe} AND i.catmat IS NULL"),
        _exemplos(dst, f"SELECT i.chave, i.numero_item, i.catmat_original, i.unidade_original, i.descricao_resumida {pe} AND i.catmat IS NULL", ex))
    inval = _um(dst, f"SELECT COUNT(*) {pe} AND i.catmat IS NULL AND i.catmat_original IS NOT NULL")
    add("CATMAT presente mas inválido (não numérico/zero)", inval, n_pe_m, "excluídos com os nulos", inval,
        _exemplos(dst, f"SELECT i.chave, i.numero_item, i.catmat_original {pe} AND i.catmat IS NULL AND i.catmat_original IS NOT NULL", ex))
    # 6. unidade / descrição / UASG / datas
    add("unidade de fornecimento ausente", _um(dst, f"SELECT COUNT(*) {pe} AND (i.unidade_original IS NULL OR TRIM(i.unidade_original) = '')"),
        n_pe_m, "excluídos (etapa 7)", _um(dst, f"SELECT COUNT(*) {pe} AND (i.unidade_original IS NULL OR TRIM(i.unidade_original) = '')"), [])
    alert_un = dst.execute("SELECT alerta, SUM(itens), COUNT(*) FROM unidades WHERE alerta <> '' GROUP BY 1").fetchall()
    for al, n, formas in alert_un:
        add(f"unidade com alerta '{al}'", n, n_itens, "mantidos como família própria, sem fusão; alerta na classificação",
            0, _exemplos(dst, f"SELECT unidade_original, unidade_norm, itens FROM unidades WHERE alerta = '{al}' ORDER BY itens DESC", ex),
            impacto(f"SELECT i.chave, i.numero_item FROM itens i JOIN unidades u ON u.unidade_original = COALESCE(i.unidade_original,'') WHERE u.alerta = '{al}'"),
            obs=f"{formas} formas originais")
    dst.executescript("DROP TABLE IF EXISTS _desc_vazia; CREATE TEMP TABLE _desc_vazia AS "
                      "SELECT rowid AS id FROM descricoes WHERE TRIM(descricao_original) = '';")
    sem_desc = ("SELECT u.chave, u.numero_item FROM universo u WHERE u.desc_id IS NULL "
                "OR u.desc_id IN (SELECT id FROM _desc_vazia)")
    n_univ = _um(dst, "SELECT COUNT(*) FROM universo")
    add("descrição detalhada ausente (universo)", _um(dst, f"SELECT COUNT(*) FROM ({sem_desc})"), n_univ,
        "mantidos; reduzem share_desc_completa da família", 0, _exemplos(dst, sem_desc, ex), impacto(sem_desc))
    so_pdm = "SELECT chave, numero_item FROM universo WHERE desc_completa = 0"
    add("descrição sem atributos além do nome do PDM (universo)", _um(dst, f"SELECT COUNT(*) FROM ({so_pdm})"), n_univ,
        "mantidos; contam como descrição incompleta", 0,
        _exemplos(dst, "SELECT u.familia, d.descricao_original, u.nome_pdm FROM universo u LEFT JOIN descricoes d "
                       "ON d.rowid = u.desc_id WHERE u.desc_completa = 0", ex), impacto(so_pdm))
    add("UASG da compra ausente ou inválida", _um(dst, "SELECT COUNT(*) FROM compras_base WHERE uasg IS NULL"), n_compras,
        "excluídas (etapa 5)", _um(dst, "SELECT COUNT(*) FROM compras_base WHERE uasg IS NULL"),
        _exemplos(dst, "SELECT chave, uasg_original FROM compras_base WHERE uasg IS NULL", ex), base_nome="compras")
    add("data de publicação inválida", _um(dst, "SELECT COUNT(*) FROM compras_base WHERE data_publicacao IS NULL"), n_compras,
        "excluídas (etapa 6)", _um(dst, "SELECT COUNT(*) FROM compras_base WHERE data_publicacao IS NULL"),
        _exemplos(dst, "SELECT chave, data_publicacao_original FROM compras_base WHERE data_publicacao IS NULL", ex), base_nome="compras")
    fora = ("SELECT chave, data_publicacao, data_abertura FROM compras_base WHERE data_abertura IS NOT NULL AND "
            "(julianday(data_abertura) - julianday(data_publicacao) > 365 OR julianday(data_abertura) < julianday(data_publicacao) - 30)")
    add("data de abertura incoerente com a publicação (> 1 ano depois ou > 30 dias antes)", _um(dst, f"SELECT COUNT(*) FROM ({fora})"),
        n_compras, "mantidas; a referência temporal é a data de publicação", 0, _exemplos(dst, fora, ex), base_nome="compras")
    ab_inv = _um(dst, "SELECT COUNT(*) FROM compras_base WHERE data_abertura_original IS NOT NULL AND data_abertura IS NULL")
    add("data de abertura inválida", ab_inv, n_compras, "mantidas (campo não usado na seleção)", 0, [], base_nome="compras")
    # 7. quantidades
    qn = "SELECT chave, numero_item, quantidade_min FROM universo WHERE quantidade_min IS NULL OR quantidade_min <= 0"
    add("quantidade nula, zero ou negativa (universo)", _um(dst, f"SELECT COUNT(*) FROM ({qn})"), n_univ,
        "mantidos: a seleção conta compras, não quantidades", 0, _exemplos(dst, qn, ex), impacto(qn))
    qi = "SELECT chave, numero_item FROM itens WHERE quantidade_min <> quantidade_max"
    add("quantidade diferente entre registros do mesmo item", _um(dst, f"SELECT COUNT(*) FROM ({qi})"), n_itens,
        "mantidos (quantidade não entra na seleção)", 0, _exemplos(dst, qi, ex))
    # 8. registros idênticos
    ident = ("SELECT l.chave, l.numero_item, COUNT(*) n FROM itens_conflitos c JOIN itens_linhas l USING (chave, numero_item) "
             "GROUP BY l.chave, l.numero_item, l.id_compra_item, l.catmat, l.unidade_original, l.situacao, l.quantidade, "
             "l.data_atualizacao HAVING COUNT(*) > 1")
    add("registros de item idênticos (todos os campos não monetários)", _um(dst, f"SELECT COUNT(*) FROM ({ident})"), n_itens,
        "colapsados pela chave composta", 0, _exemplos(dst, ident, ex))
    # 9. mudanças de codificação no tempo (formas de unidade por ano)
    cod = ("SELECT catmat, COUNT(DISTINCT unidade_original) formas_orig, COUNT(DISTINCT unidade_norm) formas_norm "
           "FROM universo GROUP BY catmat HAVING COUNT(DISTINCT unidade_original) > COUNT(DISTINCT unidade_norm)")
    add("CATMAT com grafias diferentes da mesma unidade normalizada", _um(dst, f"SELECT COUNT(*) FROM ({cod})"),
        _um(dst, "SELECT COUNT(DISTINCT catmat) FROM universo"), "unificadas pela normalização textual/aliases (sem conversão)",
        0, _exemplos(dst, cod + " ORDER BY formas_orig DESC", ex), base_nome="CATMATs")
    zero = ("SELECT catmat FROM universo GROUP BY catmat HAVING SUM(alerta_unidade = 'conteudo_zero') > 0 "
            "AND SUM(unidade_norm = 'UNIDADE') > 0")
    add("CATMAT com 'UNIDADE 0' e 'UNIDADE' (provável mudança de codificação)", _um(dst, f"SELECT COUNT(*) FROM ({zero})"),
        _um(dst, "SELECT COUNT(DISTINCT catmat) FROM universo"), "NÃO fundidas; famílias separadas e alerta", 0,
        _exemplos(dst, zero, ex), base_nome="CATMATs")
    desc_ano = ("SELECT u.catmat, COUNT(DISTINCT u.ano) anos, COUNT(DISTINCT d.chave_textual) descricoes FROM universo u "
                "LEFT JOIN descricoes d ON d.rowid = u.desc_id GROUP BY u.catmat HAVING COUNT(DISTINCT d.chave_textual) > 1")
    add("CATMAT com mais de uma descrição textual distinta", _um(dst, f"SELECT COUNT(*) FROM ({desc_ano})"),
        _um(dst, "SELECT COUNT(DISTINCT catmat) FROM universo"),
        "auditadas uma a uma nas famílias triadas (descricoes_variantes.csv)", 0,
        _exemplos(dst, desc_ano + " ORDER BY descricoes DESC", ex), base_nome="CATMATs")
    # 10. unidades aparentemente iguais mas comercialmente diferentes
    emb = ("SELECT catmat, embalagem, COUNT(DISTINCT unidade_norm) n, GROUP_CONCAT(DISTINCT unidade_norm) formas FROM universo "
           "WHERE conteudo IS NOT NULL GROUP BY catmat, embalagem HAVING COUNT(DISTINCT unidade_norm) > 1")
    add("mesmo CATMAT e mesma embalagem com conteúdos diferentes (ex.: CAIXA 50 × CAIXA 100)",
        _um(dst, f"SELECT COUNT(*) FROM ({emb})"), _um(dst, "SELECT COUNT(DISTINCT catmat) FROM universo"),
        "mantidas como famílias distintas; nenhuma conversão", 0, _exemplos(dst, emb + " ORDER BY n DESC", ex), base_nome="CATMATs")
    # 11. bens × serviços
    ms = ("SELECT catmat, GROUP_CONCAT(DISTINCT material_ou_servico) tipos, COUNT(*) itens FROM itens WHERE catmat IS NOT NULL "
          "GROUP BY catmat HAVING COUNT(DISTINCT material_ou_servico) > 1")
    add("mesmo código de catálogo como material e como serviço", _um(dst, f"SELECT COUNT(*) FROM ({ms})"),
        _um(dst, "SELECT COUNT(DISTINCT catmat) FROM itens WHERE catmat IS NOT NULL"),
        "regra: só material_ou_servico = 'M' entra; códigos coincidentes de CATSER ficam fora", 0,
        _exemplos(dst, ms + " ORDER BY itens DESC", ex), base_nome="códigos")
    # 12. informação institucional contraditória
    ua = "SELECT chave, numero_item, uasg_item FROM universo WHERE uasg_item IS NOT NULL AND uasg_item <> uasg"
    add("UASG do item diferente da UASG da compra (universo)", _um(dst, f"SELECT COUNT(*) FROM ({ua})"), n_univ,
        "mantidos; vale a UASG da compra (unidade que realizou o pregão)", 0,
        _exemplos(dst, "SELECT u.chave, u.numero_item, u.uasg, u.uasg_item FROM universo u WHERE uasg_item IS NOT NULL AND uasg_item <> uasg", ex),
        impacto(ua))
    ucn = "SELECT uasg, COUNT(DISTINCT orgao_cnpj) n FROM compras_base WHERE uasg IS NOT NULL GROUP BY uasg HAVING COUNT(DISTINCT orgao_cnpj) > 1"
    add("UASG associada a mais de um CNPJ", _um(dst, f"SELECT COUNT(*) FROM ({ucn})"),
        _um(dst, "SELECT COUNT(DISTINCT uasg) FROM compras_base"), "mantidas; a UASG é a unidade de diversidade", 0,
        _exemplos(dst, ucn + " ORDER BY n DESC", ex), base_nome="UASGs")
    cnu = "SELECT orgao_cnpj, COUNT(DISTINCT uasg) n, MIN(orgao_nome) nome FROM compras_base WHERE uasg IS NOT NULL GROUP BY orgao_cnpj HAVING COUNT(DISTINCT uasg) > 1"
    add("CNPJ compartilhado por mais de uma UASG", _um(dst, f"SELECT COUNT(*) FROM ({cnu})"),
        _um(dst, "SELECT COUNT(DISTINCT orgao_cnpj) FROM compras_base"),
        "esperado (ex.: Justiça Eleitoral); UASGs preservadas como unidades distintas", 0,
        _exemplos(dst, cnu + " ORDER BY n DESC", ex), base_nome="CNPJs")
    idc = ("SELECT id_compra, COUNT(*) n, COUNT(DISTINCT uasg) uasgs FROM compras_base WHERE id_compra IS NOT NULL "
           "GROUP BY id_compra HAVING COUNT(*) > 1")
    add("id_compra repetido em mais de um numero_controle_pncp", _um(dst, f"SELECT COUNT(*) FROM ({idc})"), n_compras,
        "NÃO agrupadas: a compra é o numero_controle_pncp (chave completa); ver contagem de itens idênticos", 0,
        _exemplos(dst, idc + " ORDER BY n DESC", ex), base_nome="compras")
    # irmãs com o mesmo conjunto de itens (possível publicação duplicada do mesmo pregão)
    # tabelas temporárias materializadas (uma CTE sem índice aqui era reavaliada por compra: custo quadrático)
    dst.executescript("""
        DROP TABLE IF EXISTS _dup; DROP TABLE IF EXISTS _sig;
        CREATE TEMP TABLE _dup AS SELECT id_compra FROM compras_base WHERE id_compra IS NOT NULL
            GROUP BY id_compra HAVING COUNT(*) > 1;
        CREATE TEMP TABLE _sig AS SELECT c.id_compra, c.chave,
            (SELECT GROUP_CONCAT(x, ',') FROM (SELECT i.numero_item || ':' || COALESCE(i.catmat, '') || ':' ||
                 COALESCE(i.unidade_original, '') AS x FROM itens i WHERE i.chave = c.chave ORDER BY i.numero_item)) AS sig
            FROM compras_base c WHERE c.id_compra IN (SELECT id_compra FROM _dup);""")
    irm = ("SELECT id_compra, COUNT(*) AS compras, MIN(chave) AS chave_1, MAX(chave) AS chave_2 FROM _sig "
           "GROUP BY id_compra HAVING COUNT(DISTINCT COALESCE(sig, '')) = 1")
    n_irm = _um(dst, f"SELECT COUNT(*) FROM ({irm})")
    add("id_compra repetido com conjunto de itens idêntico (possível publicação duplicada)", n_irm, n_compras,
        "NÃO deduplicadas (falta prova de que são o mesmo pregão; numero_controle_pncp distintos); impacto conferido",
        0, _exemplos(dst, irm, ex),
        impacto(f"SELECT i.chave, i.numero_item FROM _sig g JOIN itens i ON i.chave = g.chave WHERE g.id_compra IN "
                f"(SELECT id_compra FROM ({irm}))"),
        base_nome="compras")
    return v
