"""Descoberta do esquema real do banco e mapeamento explícito campo lógico -> (tabela, coluna).

Nenhum nome é presumido sem conferência: cada campo lógico tem uma lista de candidatos, e o
mapeamento só é aceito se a coluna existir. Campos obrigatórios ausentes interrompem a execução.
"""
from .comum import ErroEstrutural

# campo lógico -> (tabela, [candidatos em ordem de preferência], obrigatório, observação)
CAMPOS = {
    "compra.chave":            ("compras", ["numero_controle_pncp"], True, "Chave primária da compra (numeroControlePNCP)."),
    "compra.id_compra":        ("compras", ["id_compra"], False, "idCompra do Compras.gov.br; NÃO é único (contratações irmãs)."),
    "compra.uasg":             ("compras", ["uasg", "codigo_uasg"], True, "UASG da compra (unidadeOrgaoCodigoUnidade)."),
    "compra.orgao_cnpj":       ("compras", ["orgao_cnpj", "cnpj"], True, "CNPJ do órgão; pode ser compartilhado por várias UASGs."),
    "compra.orgao_nome":       ("compras", ["orgao_nome"], False, ""),
    "compra.numero_compra":    ("compras", ["numero_compra"], False, ""),
    "compra.ano_compra":       ("compras", ["ano_compra"], False, ""),
    "compra.data_publicacao":  ("compras", ["data_publicacao"], True, "dataPublicacaoPncp; data de referência da recorrência."),
    "compra.data_abertura":    ("compras", ["data_abertura_proposta"], False, "dataAberturaPropostaPncp."),
    "compra.modalidade":       ("compras", ["modalidade_nome"], True, "Modalidade (Pregão Eletrônico/Presencial)."),
    "compra.modo_disputa":     ("compras", ["modo_disputa"], True, "Lido SOMENTE no diagnóstico posterior ao congelamento."),
    "compra.fonte":            ("compras", ["fonte"], True, "dados_abertos (Compras.gov.br) ou pncp (outras plataformas)."),
    "compra.situacao":         ("compras", ["situacao_compra"], False, "Só preenchida em fonte=pncp."),
    "compra.uf":               ("compras", ["uf"], False, ""),
    "compra.esfera":           ("compras", ["esfera"], False, ""),
    "compra.poder":            ("compras", ["poder"], False, ""),
    "item.id":                 ("itens", ["id"], True, "Chave técnica de linha (um registro da API)."),
    "item.chave_compra":       ("itens", ["numero_controle_pncp"], True, "Liga o item à compra."),
    "item.numero":             ("itens", ["numero_item"], True, "Com a chave da compra, identifica o item."),
    "item.id_compra_item":     ("itens", ["id_compra_item"], False, "idCompraItem; não é único."),
    "item.registro_principal": ("itens", ["registro_principal"], False, "Marca uma linha por item; NÃO usada (prioriza valor do resultado)."),
    "item.uasg":               ("itens", ["uasg_item"], False, "UASG informada no item; auditada contra a da compra."),
    "item.catmat":             ("itens", ["cod_item_catalogo", "codigo_catmat"], True, "codItemCatalogo (CATMAT se material, CATSER se serviço)."),
    "item.material_servico":   ("itens", ["material_ou_servico"], True, "M = material (CATMAT), S = serviço (CATSER)."),
    "item.classe":             ("itens", ["codigo_classe"], False, "Classe do catálogo."),
    "item.grupo":              ("itens", ["codigo_grupo"], False, "Grupo do catálogo (muitas vezes vazio)."),
    "item.pdm":                ("itens", ["codigo_pdm"], False, "Padrão descritivo de material."),
    "item.unidade":            ("itens", ["unidade_medida"], True, "Unidade de fornecimento."),
    "item.descricao_resumida": ("itens", ["descricao_resumida"], True, "No dados_abertos é o nome do item no catálogo (nível PDM)."),
    "item.quantidade":         ("itens", ["quantidade"], True, ""),
    "item.situacao":           ("itens", ["situacao_item"], True, "Situação do item (Homologado, Deserto, ...)."),
    "item.homologado":         ("itens", ["homologado"], False, "Derivada de situacao_item."),
    "item.criterio":           ("itens", ["criterio_julgamento"], False, "Critério de julgamento (≠ modalidade)."),
    "item.data_atualizacao":   ("itens", ["data_atualizacao"], False, ""),
}

# colunas cuja LEITURA é proibida nas etapas de seleção (verificado também por teste estático)
COLUNAS_PROIBIDAS_SELECAO = [
    "valor_unitario_estimado", "valor_unitario_resultado", "valor_total_resultado",
    "valor_total_estimado", "valor_total_homologado", "valor_unitario_homologado",
    "melhor_lance_modo_aberto", "melhor_lance_modo_fechado", "melhor_lance_desempate",
    "lance_aceito", "valor_negociado_aceito", "valor_estimado_pdf", "modo_disputa", "desconto",
]


def tabelas(con):
    return [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]


def colunas(con, tabela):
    return [{"cid": r[0], "nome": r[1], "tipo": r[2], "notnull": r[3], "pk": r[5]}
            for r in con.execute(f"PRAGMA table_info({tabela})")]


def inspecionar(con, amostra=3):
    """Esquema completo: tabelas, colunas, índices, chaves estrangeiras e amostra de linhas."""
    saida = {"tabelas": {}, "views": [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")]}
    for t in tabelas(con):
        idx = []
        for r in con.execute(f"PRAGMA index_list({t})"):
            cols = [c[2] for c in con.execute(f"PRAGMA index_info({r[1]})")]
            idx.append({"nome": r[1], "unico": bool(r[2]), "origem": r[3], "colunas": cols})
        fks = [{"coluna": r[3], "tabela": r[2], "para": r[4]} for r in con.execute(f"PRAGMA foreign_key_list({t})")]
        cols = colunas(con, t)
        linhas = con.execute(f"SELECT * FROM {t} LIMIT {int(amostra)}").fetchall()
        saida["tabelas"][t] = {
            "colunas": cols, "indices": idx, "chaves_estrangeiras": fks,
            "chave_primaria": [c["nome"] for c in sorted(cols, key=lambda c: c["pk"]) if c["pk"]],
            "amostra": [dict(zip([c["nome"] for c in cols], [str(v)[:120] if v is not None else None for v in l]))
                        for l in linhas],
        }
    return saida


def mapear(con):
    """Mapeamento explícito campo lógico -> coluna real. Erro se faltar campo obrigatório."""
    existentes = {t: {c["nome"] for c in colunas(con, t)} for t in tabelas(con)}
    mapa, faltando = {}, []
    for campo, (tab, candidatos, obrig, obs) in CAMPOS.items():
        presentes = [c for c in candidatos if c in existentes.get(tab, set())]
        if not presentes:
            if obrig:
                faltando.append(f"{campo} ({tab}: {candidatos})")
            mapa[campo] = {"tabela": tab, "coluna": None, "obrigatorio": obrig, "observacao": obs}
            continue
        mapa[campo] = {"tabela": tab, "coluna": presentes[0], "obrigatorio": obrig, "observacao": obs,
                       "alternativas_presentes": presentes[1:]}
    if faltando:
        raise ErroEstrutural("campos obrigatórios ausentes no banco: " + "; ".join(faltando))
    return mapa


def conferir_chaves(con, mapa):
    """Confere a chave primária declarada de compras e o índice do item. Barato (só metadados)."""
    info = {}
    pk = [c["nome"] for c in colunas(con, "compras") if c["pk"]]
    if pk != [mapa["compra.chave"]["coluna"]]:
        raise ErroEstrutural(f"chave primária de compras inesperada: {pk}")
    info["compras_pk_declarada"] = pk
    idx_itens = []
    for r in con.execute("PRAGMA index_list(itens)"):
        idx_itens.append([c[2] for c in con.execute(f"PRAGMA index_info({r[1]})")])
    alvo = [mapa["item.chave_compra"]["coluna"], mapa["item.numero"]["coluna"]]
    info["itens_indice_chave_item"] = alvo in idx_itens
    info["itens_indices"] = idx_itens
    info["itens_pk_declarada"] = [c["nome"] for c in colunas(con, "itens") if c["pk"]]
    return info
