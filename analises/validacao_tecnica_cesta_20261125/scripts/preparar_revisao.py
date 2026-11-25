"""Etapa preparar: arquivos-base imutáveis, auditoria automática integral e formulários de revisão de uma rodada.

Rodada = conjunto de produtos de uma prioridade (P1…P5 ou 'todas'), opcionalmente limitado aos N primeiros na ordem
de revisão (compras distintas desc, id_candidato asc). A ordem é de REVISÃO; não seleciona amostra causal.
Nenhuma decisão é preenchida: todo produto sai PENDENTE e toda variante sai sem decisão.
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

import comum
from auditar_homogeneidade import (CONFLITO, VERSAO_AUDITORIA, auditar_produto, resumo_conflitos, riscos_do_produto)
from comum import ErroEstrutural
from extrair_atributos import VERSAO_EXTRACAO, Extrator, Vocabulario, chaves_com_dois_pontos
from inspecionar_entradas import caminhos, familia_de, inspecionar
from normalizar_especificacoes import VERSAO_NORMALIZACAO, chave_compacta, normalizar

PRIORIDADES = ("P1", "P2", "P3", "P4", "P5")

# ------------------------------------------------------------------------------------------------ colunas
COLS_BASE_PROD = ["id_registro", "tipo_registro", "id_candidato", "produto", "id_especificacao_atomica", "catmat",
                  "unidade_norm", "pdm", "classe_catalogo", "classe_tecnica", "cenario_rigoroso", "prioridade",
                  "ordem_revisao", "compras", "itens", "uasgs", "orgaos", "n_variantes", "n_descricoes_originais",
                  "itens_ambiguos", "status_auditoria", "n_conflitos_objetivos", "n_divergencias_a_examinar", "conflitos",
                  "atributos_consenso", "alertas", "requer_especialista", "consulta_edital", "desmembravel",
                  "motivo_nao_desmembravel", "subprodutos", "descricao_representativa", "alertas_cesta",
                  "pendencias_cesta", "hash_registro"]
COLS_BASE_VAR = ["id_variante", "id_candidato", "produto", "id_especificacao_atomica", "descricao_normalizada",
                 "chave_compacta", "descricao_original_mais_frequente", "n_descricoes_originais", "ids_descricoes",
                 "itens", "compras", "uasgs", "itens_ambiguos", "primeira", "ultima", "descricao_ausente", "nome_item",
                 "atributos", "atributos_declarados", "n_atributos", "alertas", "divergencias", "atributos_ausentes",
                 "fonte", "hash_registro"]
COLS_ORIG = ["id_descricao", "id_variante", "id_candidato", "produto", "familia", "desc_id", "descricao_original",
             "sha256_descricao", "itens", "compras", "uasgs", "primeira", "ultima", "nome_pdm", "fonte_arquivo", "fonte_linha"]
COLS_ATTR = ["id_candidato", "produto", "id_variante", "atributo", "origem", "valor", "trechos"]
COLS_CONF = ["id_candidato", "produto", "atributo", "origem", "gravidade", "relacao", "valor", "itens_com_valor",
             "variantes_com_valor", "variantes_sem_valor", "desmembravel"]

IMUT_PROD = ["versao_auditoria", "hash_registro", "id_registro", "tipo_registro", "id_candidato", "produto",
             "id_especificacao_atomica", "catmat", "unidade_norm", "classe_tecnica", "cenario_rigoroso", "prioridade",
             "ordem_revisao", "compras", "uasgs", "n_variantes", "status_auditoria", "conflitos", "alertas",
             "atributos_consenso", "requer_especialista", "consulta_edital", "descricao_representativa"]
EDIT_PROD = ["decisao_produto", "especificacao_canonica", "fundamentacao", "fonte_evidencia", "resolucao_alertas",
             "revisor", "data_revisao"]
IMUT_VAR = ["versao_auditoria", "hash_registro", "id_variante", "id_candidato", "produto", "id_especificacao_atomica",
            "descricao_normalizada", "descricao_original_mais_frequente", "n_descricoes_originais", "itens", "compras",
            "uasgs", "atributos", "divergencias", "alertas"]
EDIT_VAR = ["decisao_variante", "fundamentacao", "fonte_evidencia", "revisor", "data_revisao"]
COLS_REV_PROD = IMUT_PROD + EDIT_PROD
COLS_REV_VAR = IMUT_VAR + EDIT_VAR


def _id(prefixo, *partes):
    return prefixo + comum.sha256_texto("\x1f".join(partes))[:16]


def _rel(p):
    try:
        return Path(p).resolve().relative_to(comum.REPO.resolve()).as_posix()
    except ValueError:
        return Path(p).as_posix()


def _j(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True)


# ------------------------------------------------------------------------------------------------ priorização
def priorizar(cand, rig):
    regras = {("A", 1): "P1", ("A", 0): "P2", ("B", 1): "P3", ("B", 0): "P4"}
    for x in cand:
        x["cenario_rigoroso"] = int(familia_de(x["produto"]) in rig)
        x["prioridade"] = regras.get((x["classe_tecnica"], x["cenario_rigoroso"]), "P5")
    ordem = sorted(cand, key=lambda x: (x["prioridade"], -int(x["compras"]), x["id_candidato"]))
    por_pri = Counter()
    for i, x in enumerate(ordem, 1):
        por_pri[x["prioridade"]] += 1
        x["ordem_global"] = i
        x["ordem_revisao"] = por_pri[x["prioridade"]]
    return ordem


def nome_rodada(prioridade, limite):
    return f"piloto_{prioridade}_{limite}" if limite else prioridade


def _formularios_preenchidos(pasta):
    """True se algum campo editável dos formulários da pasta já foi preenchido (proteção contra sobrescrita)."""
    for arq, edit in (("revisao_produtos.csv", EDIT_PROD), ("revisao_variantes.csv", EDIT_VAR)):
        p = pasta / arq
        if not p.is_file():
            continue
        for r in comum.ler_csv(p):
            for c in edit:
                v = (r.get(c) or "").strip()
                if v and not (c == "decisao_produto" and v == "PENDENTE"):
                    return True
    return False


# ------------------------------------------------------------------------------------------------ preparo
def preparar(cfg, reg, prioridade="P1", limite=None, saida=None, trabalho=None, executar_inspecao=True):
    par = cfg["parametros"]
    cam = caminhos(cfg)
    rodada = nome_rodada(prioridade, limite)
    pasta = Path(saida) if saida else comum.resolver(par["saidas"]) / rodada
    if pasta.exists() and _formularios_preenchidos(pasta):
        raise ErroEstrutural(f"{pasta} já tem revisões preenchidas: não sobrescrevo. Use outra pasta (--saida) para uma nova versão.")
    insp = inspecionar(cfg, reg, escrever=executar_inspecao)
    antes = insp["bancos_antes"]

    # ------------------------------------------------------------------ candidatos e prioridades
    cand = [{k: v for k, v in x.items() if k != "__linha"} for x in comum.ler_csv(cam["cesta_candidata"], list(cfg["mapa"]["cesta_candidata"]["usar"]))]
    rig = {r["familia"] for r in comum.ler_csv(cam["pertinencia"], ["familia", "rigoroso"]) if r["rigoroso"] == "1"}
    ordem = priorizar(cand, rig)
    if prioridade != "todas" and prioridade not in PRIORIDADES:
        raise ErroEstrutural(f"prioridade inválida: {prioridade}")
    sel = [x for x in ordem if prioridade == "todas" or x["prioridade"] == prioridade]
    if limite:
        sel = sel[:int(limite)]
    if not sel:
        raise ErroEstrutural(f"nenhum candidato na prioridade {prioridade}")
    reg.log(f"rodada {rodada}: {len(sel)} produtos")
    por_prod = {x["produto"]: x for x in sel}
    fams_rodada = {familia_de(p) for p in por_prod}
    fams_todas = {familia_de(x["produto"]) for x in cand}

    # ------------------------------------------------------------------ variantes (CSV, leitura incremental) + vocabulário
    usar_v = list(cfg["mapa"]["variantes"]["usar"])
    var_csv = {}
    textos_vocab = []
    arq_var = cam["variantes"]
    for r in comum.ler_csv(arq_var, usar_v):
        if r["familia"] not in fams_todas:
            continue
        if r["descricao_original"]:
            textos_vocab.append(r["descricao_original"])
        if r["familia"] in fams_rodada:
            var_csv[(r["familia"], r["descricao_original"])] = r
    reg_v = cfg["regras"]
    vocab = Vocabulario.de_textos(textos_vocab, reg_v["chave_declarada_min_ocorrencias"], reg_v["chave_declarada_max_palavras"])
    del textos_vocab
    reg.log(f"vocabulário de chaves declaradas: {len(vocab.globais)} chaves")

    # ------------------------------------------------------------------ banco de trabalho: desc_id, produto, itens
    trab = Path(trabalho) if trabalho else comum.resolver(par["trabalho"])
    con = comum.conectar_trabalho(trab)
    try:
        comum.anexar_ro(con, cam["banco_cesta"], "cesta")
        con.executescript("""
            DROP TABLE IF EXISTS r_fam; CREATE TABLE r_fam (familia TEXT PRIMARY KEY);
            DROP TABLE IF EXISTS r_prod; CREATE TABLE r_prod (produto TEXT PRIMARY KEY);
            DROP TABLE IF EXISTS r_map; CREATE TABLE r_map (produto TEXT, desc_id INTEGER, id_variante TEXT, id_espec TEXT,
                                                            PRIMARY KEY (produto, desc_id));
        """)
        con.executemany("INSERT INTO r_fam VALUES (?)", [(f,) for f in sorted(fams_rodada)])
        con.executemany("INSERT INTO r_prod VALUES (?)", [(p,) for p in sorted(por_prod)])
        db = {}
        for fam, did, desc in con.execute("SELECT v.familia, v.desc_id, v.descricao_original FROM cesta.variantes v "
                                          "JOIN r_fam f ON f.familia = v.familia"):
            db[(fam, desc or "")] = did
        pmap = {}
        for fam, did, prod in con.execute("SELECT m.familia, m.desc_id, m.produto FROM cesta.produto_map m "
                                          "JOIN r_fam f ON f.familia = m.familia"):
            if prod in por_prod:
                pmap[(fam, did)] = prod
        if set(db) != set(var_csv):
            raise ErroEstrutural("variantes do CSV ≠ variantes do banco da cesta nesta rodada")

        # ---------------------------------------------------------------- descrições originais -> variantes normalizadas
        originais = defaultdict(list)            # produto -> [registro original]
        for (fam, desc), r in var_csv.items():
            did = db[(fam, desc)]
            prod = pmap.get((fam, did))
            if prod is None:
                continue                         # descrição de um subtipo que não está nesta rodada
            originais[prod].append({
                "id_descricao": _id("D", prod, desc), "familia": fam, "desc_id": did, "descricao_original": desc,
                "sha256_descricao": comum.sha256_texto(desc), "itens": int(r["itens"]), "compras": int(r["compras"]),
                "uasgs": int(r["uasgs"]), "primeira": r["primeira"], "ultima": r["ultima"], "nome_pdm": r["nome_pdm"],
                "fonte_arquivo": _rel(arq_var), "fonte_linha": r["__linha"], "normalizada": normalizar(desc)})
        falta = sorted(set(por_prod) - set(originais))
        if falta:
            raise ErroEstrutural(f"produtos sem descrições: {falta[:5]}")
        variantes = {}                           # produto -> {normalizada: variante}
        for prod, lst in originais.items():
            vs = {}
            for o in sorted(lst, key=lambda o: (-o["itens"], o["descricao_original"])):
                n = o["normalizada"]
                v = vs.get(n)
                if v is None:
                    v = vs[n] = {"id_variante": _id("V", prod, n), "descricao_normalizada": n, "originais": [],
                                 "descricao_ausente": int(n == "")}
                o["id_variante"] = v["id_variante"]
                v["originais"].append(o)
            variantes[prod] = vs
        con.executemany("INSERT INTO r_map (produto, desc_id, id_variante) VALUES (?,?,?)",
                        [(p, o["desc_id"], o["id_variante"]) for p, lst in originais.items() for o in lst])

        # ---------------------------------------------------------------- frequências exatas (item a item)
        reg.log("frequências por variante a partir dos itens (banco da cesta, mode=ro) ...")
        freq_v = {}
        for vid, it, co, ua, amb, pri, ult in con.execute("""
                SELECT m.id_variante, COUNT(*), COUNT(DISTINCT u.chave), COUNT(DISTINCT u.uasg), SUM(u.n_descricoes_item > 1),
                       MIN(u.data_publicacao), MAX(u.data_publicacao)
                FROM r_prod r JOIN cesta.universo_produto u ON u.produto = r.produto
                LEFT JOIN r_map m ON m.produto = u.produto AND m.desc_id = COALESCE(u.desc_id, 0)
                GROUP BY m.id_variante"""):
            if vid is None:
                raise ErroEstrutural(f"{it} itens da rodada sem descrição mapeada (ligação item × descrição incompleta)")
            freq_v[vid] = {"itens": it, "compras": co, "uasgs": ua, "itens_ambiguos": amb or 0, "primeira": pri, "ultima": ult}
        freq_p = {}
        for prod, it, co, ua, amb in con.execute("""
                SELECT u.produto, COUNT(*), COUNT(DISTINCT u.chave), COUNT(DISTINCT u.uasg), SUM(u.n_descricoes_item > 1)
                FROM r_prod r JOIN cesta.universo_produto u ON u.produto = r.produto GROUP BY u.produto"""):
            freq_p[prod] = {"itens": it, "compras": co, "uasgs": ua, "itens_ambiguos": amb or 0}
        for prod, x in por_prod.items():
            fp = freq_p.get(prod)
            if not fp or fp["itens"] != int(x["itens"]) or fp["compras"] != int(x["compras"]) or fp["uasgs"] != int(x["uasgs"]):
                raise ErroEstrutural(f"frequências do banco ≠ cesta candidata em {prod}: {fp} × itens {x['itens']}, compras {x['compras']}")
            soma = sum(freq_v[v["id_variante"]]["itens"] for v in variantes[prod].values())
            if soma != fp["itens"]:
                raise ErroEstrutural(f"soma dos itens das variantes ≠ itens do produto em {prod} (duplicação de frequência)")

        # ---------------------------------------------------------------- extração e auditoria
        ext = Extrator(reg_v)
        ext.definir_chaves(vocab.globais)
        prod_out, var_out, orig_out, attr_out, conf_out = [], [], [], [], []
        sub_maps = {}
        reg.log("extração de atributos e auditoria de homogeneidade ...")
        for prod in [x["produto"] for x in sel]:
            x = por_prod[prod]
            vs = list(variantes[prod].values())
            info = {"id_candidato": x["id_candidato"], "produto": prod, "catmat": x["catmat"], "unidade_norm": x["unidade_norm"],
                    "cautela": x["cautela"], "classe_catalogo": x["classe"], "ambiguos": freq_p[prod]["itens_ambiguos"]}
            info["riscos"] = riscos_do_produto([v["descricao_normalizada"] for v in vs], info, reg_v)
            ctx = {"medicamento": "medicamento" in info["riscos"],
                   "originalidade": bool({"toner_cartucho", "peca_reposicao", "equipamento_eletronico"} & set(info["riscos"]))}
            chaves_prod = sorted({k for v in vs for o in v["originais"] for k in chaves_com_dois_pontos(o["descricao_original"])}
                                 & set(vocab.globais))
            for v in vs:
                n = v["descricao_normalizada"]
                v["atributos_det"] = ext.extrair(n, ctx) if n else {}
                v["atributos"] = {a: sorted(d) for a, d in v["atributos_det"].items()}
                nome, pares = vocab.pares(n, chaves_prod) if n else ("", [])
                decl = defaultdict(set)
                for k, val, _ in pares:
                    decl[k].add(val)
                v["declarados"] = {k: sorted(s) for k, s in decl.items()}
                v["pares"] = pares
                v["nome"] = nome
                v["chave_compacta"] = chave_compacta(n)
                v["notas"] = ext.notas_catalogo(n)
                v.update(freq_v[v["id_variante"]])
            aud = auditar_produto(info, vs, reg_v)
            # divergências e ausências por variante
            div_v, aus_v = defaultdict(list), defaultdict(list)
            for c in aud["conflitos"]:
                for val, d in c["valores"].items():
                    for vid in d["variantes"]:
                        div_v[vid].append(f"{c['atributo']}={val} [{c['gravidade']}]")
                for vid in c["variantes_sem_valor"]:
                    div_v[vid].append(f"{c['atributo']}=(sem valor) [{c['gravidade']}]")
            for a in aud["ausentes"]:
                for vid in a["variantes_sem_atributo"]:
                    aus_v[vid].append(a["atributo"])
            sub = aud["subprodutos"]
            if sub:
                sub_maps[prod] = sub
            # variantes e originais
            for v in sorted(vs, key=lambda v: (-v["itens"], v["descricao_normalizada"])):
                alert_v = []
                if v["descricao_ausente"]:
                    alert_v.append("descrição ausente")
                if v["itens"] <= 1:
                    alert_v.append("descrição rara (1 item)")
                if v["notas"]:
                    alert_v.append("nota de catálogo: " + "; ".join(v["notas"]))
                if v["itens_ambiguos"]:
                    alert_v.append(f"{v['itens_ambiguos']} item(ns) com mais de uma descrição bruta")
                if any("[OBJETIVO]" in d for d in div_v[v["id_variante"]]):
                    alert_v.append("participa de conflito objetivo")
                o0 = v["originais"][0]
                var_out.append({
                    "id_variante": v["id_variante"], "id_candidato": x["id_candidato"], "produto": prod,
                    "id_especificacao_atomica": (sub or {}).get(v["id_variante"], ""),
                    "descricao_normalizada": v["descricao_normalizada"] or "(DESCRIÇÃO AUSENTE)", "chave_compacta": v["chave_compacta"],
                    "descricao_original_mais_frequente": o0["descricao_original"], "n_descricoes_originais": len(v["originais"]),
                    "ids_descricoes": ";".join(o["id_descricao"] for o in v["originais"]),
                    "itens": v["itens"], "compras": v["compras"], "uasgs": v["uasgs"], "itens_ambiguos": v["itens_ambiguos"],
                    "primeira": v["primeira"], "ultima": v["ultima"], "descricao_ausente": v["descricao_ausente"], "nome_item": v["nome"],
                    "atributos": _j(v["atributos"]), "atributos_declarados": _j(v["declarados"]),
                    "n_atributos": len(v["atributos"]) + len(v["declarados"]), "alertas": " | ".join(alert_v),
                    "divergencias": " | ".join(sorted(div_v[v["id_variante"]])), "atributos_ausentes": ";".join(sorted(aus_v[v["id_variante"]])),
                    "fonte": f"{arq_var.name}: linhas " + ",".join(str(o["fonte_linha"]) for o in v["originais"])})
                for o in v["originais"]:
                    orig_out.append({**{k: o[k] for k in COLS_ORIG if k in o}, "id_variante": v["id_variante"],
                                     "id_candidato": x["id_candidato"], "produto": prod})
                for a, d in sorted(v["atributos_det"].items()):
                    for val, trechos in sorted(d.items()):
                        attr_out.append({"id_candidato": x["id_candidato"], "produto": prod, "id_variante": v["id_variante"],
                                         "atributo": a, "origem": "extraido", "valor": val, "trechos": " | ".join(trechos)})
                for k, val, trecho in v["pares"]:
                    attr_out.append({"id_candidato": x["id_candidato"], "produto": prod, "id_variante": v["id_variante"],
                                     "atributo": f"declarado:{k}", "origem": "declarado", "valor": val, "trechos": trecho})
            for c in aud["conflitos"]:
                for val, d in sorted(c["valores"].items()):
                    conf_out.append({"id_candidato": x["id_candidato"], "produto": prod, "atributo": c["atributo"], "origem": c["origem"],
                                     "gravidade": c["gravidade"], "relacao": c["relacao"], "valor": val, "itens_com_valor": d["itens"],
                                     "variantes_com_valor": ";".join(d["variantes"]), "variantes_sem_valor": ";".join(c["variantes_sem_valor"]),
                                     "desmembravel": int(bool(sub))})
            prod_out.append({
                "id_registro": x["id_candidato"], "tipo_registro": "PRODUTO", "id_candidato": x["id_candidato"], "produto": prod,
                "id_especificacao_atomica": "", "catmat": x["catmat"], "unidade_norm": x["unidade_norm"], "pdm": x["pdm"],
                "classe_catalogo": x["classe"], "classe_tecnica": x["classe_tecnica"], "cenario_rigoroso": x["cenario_rigoroso"],
                "prioridade": x["prioridade"], "ordem_revisao": x["ordem_revisao"], "compras": int(x["compras"]), "itens": int(x["itens"]),
                "uasgs": int(x["uasgs"]), "orgaos": int(x["orgaos"]), "n_variantes": len(vs),
                "n_descricoes_originais": sum(len(v["originais"]) for v in vs), "itens_ambiguos": freq_p[prod]["itens_ambiguos"],
                "status_auditoria": aud["status"], "n_conflitos_objetivos": aud["n_conflitos_objetivos"],
                "n_divergencias_a_examinar": aud["n_divergencias_a_examinar"], "conflitos": resumo_conflitos(aud["conflitos"]),
                "atributos_consenso": _j(aud["consenso"]), "alertas": " | ".join(aud["alertas"]),
                "requer_especialista": ";".join(aud["requer_especialista"]),
                "consulta_edital": " | ".join(aud["consulta_edital"]), "desmembravel": int(bool(sub)) if aud["status"] == CONFLITO else "",
                "motivo_nao_desmembravel": aud["motivo_nao_desmembravel"],
                "subprodutos": ";".join(sorted(set(sub.values()))) if sub else "",
                "descricao_representativa": x["descricao_representativa"], "alertas_cesta": x["alertas_especificacao"],
                "pendencias_cesta": x["pendencias_validacao"], "_aud": aud, "_vs": vs, "_info": info})

        # ---------------------------------------------------------------- subprodutos (especificações atômicas)
        if sub_maps:
            con.executemany("UPDATE r_map SET id_espec = ? WHERE produto = ? AND id_variante = ?",
                            [(e, p, vid) for p, m in sub_maps.items() for vid, e in m.items()])
            freq_s = {e: (it, co, ua) for e, it, co, ua in con.execute("""
                SELECT m.id_espec, COUNT(*), COUNT(DISTINCT u.chave), COUNT(DISTINCT u.uasg)
                FROM r_map m JOIN cesta.universo_produto u ON u.produto = m.produto AND COALESCE(u.desc_id, 0) = m.desc_id
                WHERE m.id_espec IS NOT NULL GROUP BY m.id_espec""")}
            novos = []
            for p in prod_out:
                sub = sub_maps.get(p["produto"])
                if not sub:
                    continue
                grupos = defaultdict(list)
                for v in p["_vs"]:
                    if v["id_variante"] in sub:
                        grupos[sub[v["id_variante"]]].append(v)
                for e in sorted(grupos):
                    gv = grupos[e]
                    aud_s = auditar_produto({**p["_info"], "id_candidato": e}, gv, reg_v)
                    it, co, ua = freq_s[e]
                    dif = {}
                    for c in p["_aud"]["conflitos"]:
                        if c["gravidade"] == "OBJETIVO":
                            dif[c["atributo"]] = sorted({val for val, d in c["valores"].items() if set(d["variantes"]) & {v["id_variante"] for v in gv}})
                    novos.append({**{k: p[k] for k in ("id_candidato", "produto", "catmat", "unidade_norm", "pdm", "classe_catalogo",
                                                       "classe_tecnica", "cenario_rigoroso", "prioridade", "ordem_revisao", "orgaos",
                                                       "alertas_cesta", "pendencias_cesta")},
                                  "id_registro": e, "tipo_registro": "SUBPRODUTO", "id_especificacao_atomica": e,
                                  "compras": co, "itens": it, "uasgs": ua, "orgaos": "", "n_variantes": len(gv),
                                  "n_descricoes_originais": sum(len(v["originais"]) for v in gv), "itens_ambiguos": 0,
                                  "status_auditoria": aud_s["status"], "n_conflitos_objetivos": aud_s["n_conflitos_objetivos"],
                                  "n_divergencias_a_examinar": aud_s["n_divergencias_a_examinar"],
                                  "conflitos": resumo_conflitos(aud_s["conflitos"]),
                                  "atributos_consenso": _j({**aud_s["consenso"], **{k: v[0] for k, v in dif.items() if len(v) == 1}}),
                                  "alertas": " | ".join(["subproduto proposto pelos atributos " + ", ".join(f"{k}={'/'.join(v)}" for k, v in sorted(dif.items()))] + aud_s["alertas"]),
                                  "requer_especialista": p["requer_especialista"], "consulta_edital": " | ".join(aud_s["consulta_edital"]),
                                  "desmembravel": "", "motivo_nao_desmembravel": "", "subprodutos": "",
                                  "descricao_representativa": max(gv, key=lambda v: (v["itens"], v["descricao_normalizada"]))["originais"][0]["descricao_original"]})
            prod_out += novos
    finally:
        con.close()

    # ------------------------------------------------------------------ hashes de registro e gravação
    var_por_reg = defaultdict(list)
    var_hash = {}
    for v in var_out:
        v["hash_registro"] = comum.sha256_json({k: v[k] for k in COLS_BASE_VAR if k != "hash_registro"})
        var_hash[v["id_variante"]] = v["hash_registro"]
        var_por_reg[v["id_candidato"]].append(v["id_variante"])
        if v["id_especificacao_atomica"]:
            var_por_reg[v["id_especificacao_atomica"]].append(v["id_variante"])
    for p in prod_out:
        for k in ("_aud", "_vs", "_info"):
            p.pop(k, None)
        base = {k: p[k] for k in COLS_BASE_PROD if k != "hash_registro"}
        base["_variantes"] = sorted(var_hash[v] for v in var_por_reg[p["id_registro"]])
        p["hash_registro"] = comum.sha256_json(base)
    ordem_tipo = {"PRODUTO": 0, "SUBPRODUTO": 1}
    og = {x["id_candidato"]: x["ordem_global"] for x in sel}
    prod_out.sort(key=lambda p: (og[p["id_candidato"]], ordem_tipo[p["tipo_registro"]], p["id_registro"]))
    orig_out.sort(key=lambda o: (o["id_candidato"], o["id_variante"], -o["itens"], o["descricao_original"]))
    attr_out.sort(key=lambda a: (a["id_candidato"], a["id_variante"], a["origem"], a["atributo"], a["valor"]))
    conf_out.sort(key=lambda c: (c["id_candidato"], c["gravidade"], c["atributo"], c["valor"]))

    pasta.mkdir(parents=True, exist_ok=True)
    arquivos_base = {"base_produtos.csv": (prod_out, COLS_BASE_PROD), "base_variantes.csv": (var_out, COLS_BASE_VAR),
                     "descricoes_originais.csv": (orig_out, COLS_ORIG), "auditoria_atributos.csv": (attr_out, COLS_ATTR),
                     "auditoria_conflitos.csv": (conf_out, COLS_CONF)}
    for nome, (linhas, cols) in arquivos_base.items():
        comum.escrever_csv(pasta / nome, linhas, cols)
    comum.escrever_json(pasta / "vocabulario_chaves_declaradas.json", vocab.globais)
    hashes_base = {n: comum.sha256_arquivo(pasta / n) for n in list(arquivos_base) + ["vocabulario_chaves_declaradas.json"]}
    hashes_config = {n: comum.sha256_arquivo(cfg["pasta_config"] / n) for n in ("parametros.json", "mapa_colunas.json", "regras_atributos.json")}
    codigo = {p.name: comum.sha256_arquivo(p) for p in sorted(comum.AQUI.glob("*.py"))}
    versao_auditoria = comum.sha256_json({"base": hashes_base, "config": hashes_config})[:16]

    rev_prod = [{**{k: p.get(k, "") for k in IMUT_PROD if k != "versao_auditoria"}, "versao_auditoria": versao_auditoria,
                 "decisao_produto": "PENDENTE", **{k: "" for k in EDIT_PROD if k != "decisao_produto"}} for p in prod_out]
    rev_var = [{**{k: v.get(k, "") for k in IMUT_VAR if k != "versao_auditoria"}, "versao_auditoria": versao_auditoria,
                **{k: "" for k in EDIT_VAR}} for v in var_out]
    comum.escrever_csv(pasta / "revisao_produtos.csv", rev_prod, COLS_REV_PROD)
    comum.escrever_csv(pasta / "revisao_variantes.csv", rev_var, COLS_REV_VAR)
    for velho in ("resultado_revisao.csv", "resultado_validacao.json", "cesta_validada.csv"):
        if (pasta / velho).exists():
            (pasta / velho).unlink()                 # resultados de uma versão anterior sem revisões (nunca reutilizados)

    depois = {k: comum.impressao_digital(cam[k]) for k in ("banco_cesta", "banco_pncp")}
    for k in antes:
        comum.conferir_inalterado(antes[k], depois[k])
    status = Counter(p["status_auditoria"] for p in prod_out if p["tipo_registro"] == "PRODUTO")
    tipos_conf = Counter(a for a, _ in {(c["atributo"], c["id_candidato"]) for c in conf_out if c["gravidade"] == "OBJETIVO"})
    manifesto = {
        "rodada": rodada, "prioridade": prioridade, "limite": limite, "preparado_em": comum.agora(), "data_preparacao": comum.hoje(),
        "versao_auditoria": versao_auditoria,
        "versoes": {"codigo": comum.VERSAO, "normalizacao": VERSAO_NORMALIZACAO, "extracao": VERSAO_EXTRACAO,
                    "auditoria": VERSAO_AUDITORIA, "regras": cfg["regras"]["versao"], "mapa": cfg["mapa"]["versao"]},
        "entradas": {k: {"caminho": str(cam[k]), "sha256": comum.sha256_arquivo(cam[k])}
                     for k in ("cesta_candidata", "variantes", "pertinencia", "formulario_original")},
        "bancos": {"antes": antes, "depois": depois, "inalterados": True},
        "hashes_config": hashes_config, "hashes_codigo": codigo, "hashes_base": hashes_base,
        "hashes_formularios_iniciais": {n: comum.sha256_arquivo(pasta / n) for n in ("revisao_produtos.csv", "revisao_variantes.csv")},
        "colunas_imutaveis": {"revisao_produtos.csv": IMUT_PROD, "revisao_variantes.csv": IMUT_VAR},
        "colunas_editaveis": {"revisao_produtos.csv": EDIT_PROD, "revisao_variantes.csv": EDIT_VAR},
        "contagens": {
            "produtos": sum(1 for p in prod_out if p["tipo_registro"] == "PRODUTO"),
            "subprodutos_propostos": sum(1 for p in prod_out if p["tipo_registro"] == "SUBPRODUTO"),
            "variantes_normalizadas": len(var_out), "descricoes_originais": len(orig_out),
            "itens": sum(int(p["itens"]) for p in prod_out if p["tipo_registro"] == "PRODUTO"),
            "status_auditoria": dict(sorted(status.items())), "conflitos_objetivos_por_atributo": dict(sorted(tipos_conf.items(), key=lambda kv: (-kv[1], kv[0]))),
            "produtos_com_conflito_objetivo": status.get(CONFLITO, 0),
            "produtos_desmembraveis": sum(1 for p in prod_out if p["tipo_registro"] == "PRODUTO" and p["desmembravel"] == 1),
            "produtos_requer_especialista": sum(1 for p in prod_out if p["tipo_registro"] == "PRODUTO" and p["requer_especialista"]),
            "produtos_consulta_edital": sum(1 for p in prod_out if p["tipo_registro"] == "PRODUTO" and p["consulta_edital"]),
            "aprovados_automaticamente": 0,
        },
        "priorizacao_total": dict(sorted(Counter(x["prioridade"] for x in cand).items())),
        "independencia": "nenhuma coluna de preço, valor, desconto, modo de disputa, licitantes ou resultado econométrico foi lida",
    }
    comum.escrever_json(pasta / "manifesto.json", manifesto)
    # relação integral dos candidatos e da ordem de revisão (todas as prioridades)
    comum.escrever_csv(comum.resolver(par["saidas"]) / "priorizacao_candidatos.csv", ordem,
                       ["ordem_global", "prioridade", "ordem_revisao", "id_candidato", "produto", "catmat", "unidade_norm",
                        "classe_tecnica", "cenario_rigoroso", "compras", "uasgs"])
    reg.log(f"rodada {rodada} preparada em {pasta}: {manifesto['contagens']}")
    return manifesto
