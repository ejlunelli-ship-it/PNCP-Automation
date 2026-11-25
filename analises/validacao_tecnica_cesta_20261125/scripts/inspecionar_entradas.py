"""Etapa inspect: lê os cabeçalhos reais, confere o mapeamento de colunas, a unicidade das chaves e a ligação
cesta ↔ variantes ↔ banco de trabalho da cesta. Interrompe (ErroEstrutural) em qualquer ambiguidade não resolvida.

Nunca abre os arquivos proibidos (diagnóstico por modo, estudo econométrico) e nunca lê colunas econômicas.
"""
from collections import Counter, defaultdict
from pathlib import Path

import comum
from comum import ErroEstrutural


def caminhos(cfg):
    e = cfg["parametros"]["entradas"]
    return {k: comum.resolver(v) for k, v in e.items() if not k.startswith("_")}


def conferir_mapeamento(cfg, cam, reg):
    """Cabeçalhos reais × mapa_colunas.json. Devolve o relatório por arquivo."""
    mapa = cfg["mapa"]
    proib = mapa["padroes_proibidos"]
    rel = {}
    for nome in ("cesta_candidata", "variantes", "pertinencia", "formulario_original"):
        arq = cam[nome]
        if not arq.is_file():
            raise ErroEstrutural(f"arquivo de entrada não encontrado: {arq}")
        cab = comum.cabecalho_csv(arq)
        usar = list(mapa[nome]["usar"])
        falta = [c for c in usar if c not in cab]
        if falta:
            raise ErroEstrutural(f"{arq.name}: colunas do mapeamento ausentes no arquivo real: {falta}")
        dup = [c for c, n in Counter(cab).items() if n > 1]
        if dup:
            raise ErroEstrutural(f"{arq.name}: cabeçalho com colunas repetidas {dup}")
        ruins = [c for c in usar if comum.proibida(c, proib)]
        if ruins:
            raise ErroEstrutural(f"{arq.name}: o mapeamento usa colunas com informação econômica {ruins}")
        rel[nome] = {"arquivo": str(arq), "sha256": comum.sha256_arquivo(arq), "colunas_reais": cab, "colunas_usadas": usar,
                     "colunas_ignoradas": [c for c in cab if c not in usar],
                     "colunas_ignoradas_por_conterem_informacao_economica": [c for c in cab if c not in usar and comum.proibida(c, proib)]}
        reg.log(f"{arq.name}: {len(cab)} colunas reais, {len(usar)} usadas")
    for p in mapa["arquivos_proibidos"]:
        rel.setdefault("arquivos_proibidos_nao_lidos", []).append(str(comum.resolver(p)))
    return rel


def carregar_candidatos(cfg, cam):
    usar = list(cfg["mapa"]["cesta_candidata"]["usar"])
    cand = list(comum.ler_csv(cam["cesta_candidata"], usar))
    return cand


def familia_de(produto):
    return produto.split("#")[0]


def detectar_ids(cand):
    """Cardinalidade de cada coluna da cesta: candidatas a identificador são as de cardinalidade = nº de linhas."""
    n = len(cand)
    out = {}
    for c in cand[0]:
        if c == "__linha":
            continue
        k = len({x[c] for x in cand})
        out[c] = {"distintos": k, "unico": k == n}
    return out


def inspecionar(cfg, reg, escrever=True):
    cam = caminhos(cfg)
    rel = {"versao": comum.VERSAO, "executado_em": comum.agora(), "mapeamento": conferir_mapeamento(cfg, cam, reg)}
    rel["bancos_antes"] = {k: comum.impressao_digital(cam[k]) for k in ("banco_cesta", "banco_pncp")}

    # ------------------------------------------------------------------ cesta candidata
    cand = carregar_candidatos(cfg, cam)
    card = detectar_ids(cand)
    rel["cardinalidade_cesta"] = card
    for c in ("id_candidato", "produto"):
        if not card[c]["unico"]:
            raise ErroEstrutural(f"cesta_candidata.csv: {c} não é único")
    sem_chave = [x["id_candidato"] for x in cand if not x["catmat"].strip() or not x["unidade_norm"].strip()]
    divergentes = [x["produto"] for x in cand if familia_de(x["produto"]) != f"{x['catmat']}|{x['unidade_norm']}"]
    if divergentes:
        raise ErroEstrutural(f"produto ≠ catmat|unidade_norm em {len(divergentes)} candidatos: {divergentes[:5]}")
    subtipos = sorted(x["produto"] for x in cand if "#" in x["produto"])
    classes = Counter(x["classe_tecnica"] for x in cand)
    # ------------------------------------------------------------------ cenário rigoroso
    rig = {r["familia"] for r in comum.ler_csv(cam["pertinencia"], ["familia", "rigoroso"]) if r["rigoroso"] == "1"}
    em_rig = [x for x in cand if familia_de(x["produto"]) in rig]
    rel["cesta"] = {
        "candidatos": len(cand), "classe_A": classes.get("A", 0), "classe_B": classes.get("B", 0),
        "outras_classes": {k: v for k, v in classes.items() if k not in ("A", "B")},
        "familias_rigoroso": len(rig), "candidatos_em_familias_rigoroso": len(em_rig),
        "A_e_rigoroso": sum(1 for x in em_rig if x["classe_tecnica"] == "A"),
        "B_e_rigoroso": sum(1 for x in em_rig if x["classe_tecnica"] == "B"),
        "produtos_com_subtipo_#": subtipos, "candidatos_sem_catmat_ou_unidade": sem_chave,
        "chave_produto": "produto (= catmat|unidade_norm, com sufixo #hash quando a cesta separou subtipos)",
        "id_produto": "id_candidato",
        "relacao_com_variantes": "familia(variantes) = produto sem o sufixo #; descrição → produto pelo produto_map (familia, desc_id) do banco da cesta",
    }
    reg.log(f"cesta: {len(cand)} candidatos; A∩rigoroso = {rel['cesta']['A_e_rigoroso']}")

    # ------------------------------------------------------------------ variantes (CSV) e banco da cesta
    fams = {familia_de(x["produto"]) for x in cand}
    prods = {x["produto"] for x in cand}
    usar_v = list(cfg["mapa"]["variantes"]["usar"])
    csv_var = {}
    linhas_csv = 0
    for r in comum.ler_csv(cam["variantes"], usar_v):
        linhas_csv += 1
        if r["familia"] not in fams:
            continue
        k = (r["familia"], r["descricao_original"])
        if k in csv_var:
            raise ErroEstrutural(f"descricoes_variantes.csv: (familia, descricao_original) repetido na linha {r['__linha']}")
        csv_var[k] = r
    con = comum.conectar_ro(cam["banco_cesta"])
    try:
        db_var = defaultdict(list)
        for fam, did, desc, it in con.execute("SELECT familia, desc_id, descricao_original, itens FROM variantes"):
            if fam in fams:
                db_var[(fam, desc or "")].append((did, it))
        pmap = defaultdict(list)
        for fam, did, prod in con.execute("SELECT familia, desc_id, produto FROM produto_map"):
            if fam in fams:
                pmap[(fam, did)].append(prod)
    finally:
        con.close()
    so_csv = [k for k in csv_var if k not in db_var]
    so_db = [k for k in db_var if k not in csv_var]
    multi = [k for k, v in db_var.items() if len(v) != 1]
    if so_csv or so_db or multi:
        raise ErroEstrutural(f"variantes CSV × banco: {len(so_csv)} só no CSV, {len(so_db)} só no banco, {len(multi)} ambíguas")
    itens_dif = [k for k, r in csv_var.items() if int(r["itens"]) != db_var[k][0][1]]
    if itens_dif:
        raise ErroEstrutural(f"frequência de itens difere entre CSV e banco em {len(itens_dif)} variantes")
    sem_prod, multi_prod = [], []
    itens_por_prod = Counter()
    var_por_prod = Counter()
    for k, r in csv_var.items():
        did = db_var[k][0][0]
        ps = [p for p in pmap.get((k[0], did), []) if p in prods]
        if len(ps) == 0:
            sem_prod.append(k)
            continue
        if len(ps) > 1:
            multi_prod.append(k)
            continue
        itens_por_prod[ps[0]] += int(r["itens"])
        var_por_prod[ps[0]] += 1
    if multi_prod:
        raise ErroEstrutural(f"{len(multi_prod)} descrições atribuídas a mais de um produto candidato")
    sem_var = sorted(prods - set(var_por_prod))
    if sem_var:
        raise ErroEstrutural(f"{len(sem_var)} produtos candidatos sem nenhuma variante: {sem_var[:5]}")
    itens_cesta = {x["produto"]: int(x["itens"]) for x in cand}
    dif_itens = [p for p in prods if itens_por_prod[p] != itens_cesta[p]]
    if dif_itens:
        raise ErroEstrutural(f"soma dos itens das variantes ≠ itens da cesta em {len(dif_itens)} produtos: {dif_itens[:5]}")
    rel["variantes"] = {
        "linhas_csv": linhas_csv, "variantes_das_familias_candidatas": len(csv_var),
        "variantes_fora_dos_produtos_candidatos": len(sem_prod),
        "_nota_fora": "descrições de famílias com subtipo cujo subtipo não entrou na cesta (ficam fora da revisão)",
        "descricoes_ausentes": sum(1 for k in csv_var if not k[1]),
        "variantes_por_produto_max": max(var_por_prod.values()), "produtos_com_uma_variante": sum(1 for v in var_por_prod.values() if v == 1),
        "soma_itens_confere_com_cesta": True, "chave_variante": "(familia, descricao_original) ↔ desc_id do banco da cesta",
    }
    # ------------------------------------------------------------------ formulário e cesta validada originais (só contagem)
    dec_col = "decisao (aprovar/rejeitar/dividir)"
    form = list(comum.ler_csv(cam["formulario_original"], ["id_candidato", dec_col]))
    rel["formulario_original"] = {"linhas": len(form), "com_decisao": sum(1 for f in form if f[dec_col].strip()),
                                  "sha256": comum.sha256_arquivo(cam["formulario_original"])}
    cv = cam["cesta_validada_original"]
    rel["cesta_validada_original"] = {"linhas": sum(1 for _ in comum.ler_csv(cv)) if cv.is_file() else None,
                                      "sha256": comum.sha256_arquivo(cv) if cv.is_file() else None}
    rel["bancos_depois"] = {k: comum.impressao_digital(cam[k]) for k in ("banco_cesta", "banco_pncp")}
    for k in rel["bancos_antes"]:
        comum.conferir_inalterado(rel["bancos_antes"][k], rel["bancos_depois"][k])
    rel["conclusao"] = "mapeamento confirmado; nenhuma ambiguidade não resolvida"
    if escrever:
        saidas = comum.resolver(cfg["parametros"]["saidas"])
        comum.escrever_json(saidas / "inspecao_entradas.json", rel)
        reg.log(f"inspeção gravada em {saidas / 'inspecao_entradas.json'}")
    return rel
