"""Decisão automática por família (catálogo) e por item (contratação). Regras explícitas, cumulativas e
conservadoras: na falta de demonstração, AUTO_INCONCLUSIVO. Nenhum escore de similaridade supera um conflito."""
from . import (AUTO_DESMEMBRAR, AUTO_DIVERGENTE, AUTO_ERRO_DADOS, AUTO_INCONCLUSIVO, AUTO_VALIDADO_CATALOGO,
               AUTO_VALIDADO_CATALOGO_RESSALVA, AUTO_VALIDADO_ITEM, ITEM_SEM_CLASSIFICACAO, ITEM_SEM_VALIDACAO_DOCUMENTAL)
from .avaliar_evidencias import avaliar_perfis, perfis_do_produto, unidade_reconhecida
from .comparar_especificacoes import (CONFORME_TIPOGRAFICA, CONFORMES, DIVERGENCIA_TEXTUAL, DIVERGENTE, PARCIAL,
                                      SEM_DESCRICAO, comparar_variante, contradicoes_oficiais)
from .consultar_catalogo import OK, VAZIO
from .identificar_subprodutos import grupos
from .normalizar_texto import normalizar

VALIDADOS = {AUTO_VALIDADO_CATALOGO, AUTO_VALIDADO_CATALOGO_RESSALVA}
CRITERIOS = ["c01_identificacao_inequivoca", "c02_catmat_valido", "c03_unidade_interpretavel", "c04_especificacao_suficiente",
             "c05_atributos_essenciais_categoria", "c06_evidencias_verificaveis", "c07_cobertura_variantes",
             "c08_sem_conflito_material", "c09_sem_ambiguidade_critica", "c10_regras_versionadas", "c11_rastreabilidade",
             "c12_fontes_preservadas"]


def _avaliar_grupo(comps, base_ok, ressalvas_base):
    """Status de catálogo para um conjunto de variantes (família inteira ou subproduto conforme)."""
    st = [c["status"] for c in comps]
    res = list(ressalvas_base)
    if SEM_DESCRICAO in st:
        res.append(f"{st.count(SEM_DESCRICAO)} variante(s) sem descrição: itens ligados só pelo código CATMAT")
    if CONFORME_TIPOGRAFICA in st:
        res.append("equivalência com correção tipográfica (espaço dentro de número)")
    if not base_ok:
        return None, res
    return (AUTO_VALIDADO_CATALOGO_RESSALVA if res else AUTO_VALIDADO_CATALOGO), res


def decidir_familia(prod, variantes, ficha, canon, extrator, contexto, cfg_auto, parse_unidade, fontes_preservadas):
    """Devolve o registro completo da decisão (status, nível, motivos, ressalvas, critérios, comparações, subprodutos)."""
    d = {"id_candidato": prod["id_candidato"], "produto": prod["produto"], "status": None, "nivel": "", "motivos": [],
         "ressalvas": [], "criterios": {c: None for c in CRITERIOS}, "comparacoes": {}, "subprodutos": [], "perfis": [],
         "unidade": "", "contradicoes_oficiais": []}
    cr = d["criterios"]
    cr["c10_regras_versionadas"] = True
    chave_ok = bool(prod["catmat"].strip()) and bool(prod["unidade_norm"].strip()) and prod["status_auditoria"] != "CHAVE_INVALIDA" and bool(variantes)
    cr["c01_identificacao_inequivoca"] = chave_ok
    if not chave_ok:
        d["status"] = AUTO_ERRO_DADOS
        d["motivos"].append("chave do produto inválida (CATMAT/unidade ausente) ou sem variantes")
        return d
    st_item = ficha.get("status_item")
    cr["c02_catmat_valido"] = st_item == OK
    if st_item == VAZIO:
        d["status"] = AUTO_ERRO_DADOS
        d["motivos"].append("CATMAT não encontrado no catálogo oficial")
        return d
    if st_item != OK:
        d["status"] = AUTO_INCONCLUSIVO
        d["motivos"].append(f"catálogo oficial indisponível ou resposta inválida ({st_item})")
        return d
    ressalvas = []
    if not ficha["item"]["ativo"]:
        ressalvas.append("item inativo no catálogo oficial")
    if ficha["item"].get("codigo_pdm") is not None and str(ficha["item"]["codigo_pdm"]) != str(prod["pdm"]):
        ressalvas.append(f"PDM do catálogo ({ficha['item']['codigo_pdm']}) ≠ PDM da cesta ({prod['pdm']})")
    # unidade
    interp, recon, det = unidade_reconhecida(prod["unidade_norm"], parse_unidade, ficha, cfg_auto["siglas_unidade"])
    d["unidade"] = det
    cr["c03_unidade_interpretavel"] = interp
    if interp and not recon:
        ressalvas.append(det)
    # especificação canônica
    if canon is None:
        cr["c04_especificacao_suficiente"] = False
        d["motivos"].append("catálogo oficial sem características estruturadas" if ficha.get("status_caracteristicas") == VAZIO
                            else f"características oficiais indisponíveis ({ficha.get('status_caracteristicas')})")
    else:
        d["contradicoes_oficiais"] = contradicoes_oficiais(canon)
        if d["contradicoes_oficiais"]:
            d["motivos"].append("fontes oficiais contraditórias (característica ausente da descrição oficial): " + "; ".join(d["contradicoes_oficiais"]))
        inativas = [c["nome"] for c in canon["caracteristicas"] if not c["ativo"]]
        if inativas:
            ressalvas.append("característica/valor inativo no catálogo: " + "; ".join(inativas))
        d["perfis"] = perfis_do_produto(prod["requer_especialista"])
        emb = normalizar((parse_unidade or {}).get("embalagem") or prod["unidade_norm"])
        un_apres = emb if (recon and emb in {normalizar(x) for x in cfg_auto["perfis"].get("unidades_apresentacao_farmaceutica", [])}) else None
        faltas, _ = avaliar_perfis(canon, d["perfis"], cfg_auto["perfis"], un_apres)
        cr["c05_atributos_essenciais_categoria"] = not faltas
        d["motivos"] += faltas
        cr["c04_especificacao_suficiente"] = not d["contradicoes_oficiais"] and not any(f.startswith("geral:") for f in faltas)
    cr["c06_evidencias_verificaveis"] = canon is not None and all(ficha["fontes"][k]["sha256"] for k in ("catmat_item", "catmat_caracteristicas"))
    cr["c12_fontes_preservadas"] = bool(fontes_preservadas)
    if not interp:
        d["motivos"].append(det)
    if canon is None:
        cr["c07_cobertura_variantes"] = cr["c08_sem_conflito_material"] = cr["c09_sem_ambiguidade_critica"] = False
        d["status"] = AUTO_INCONCLUSIVO
        cr["c11_rastreabilidade"] = True
        return d
    # comparação de 100% das variantes
    for v in variantes:
        d["comparacoes"][v["id_variante"]] = comparar_variante(v, canon, extrator, contexto)
    st = [c["status"] for c in d["comparacoes"].values()]
    cr["c07_cobertura_variantes"] = len(d["comparacoes"]) == len(variantes) and all(s in CONFORMES or s == SEM_DESCRICAO for s in st)
    cr["c08_sem_conflito_material"] = DIVERGENTE not in st and prod["status_auditoria"] != "CONFLITO_OBJETIVO_EXIGE_DESMEMBRAMENTO"
    amb = int(prod["itens_ambiguos"] or 0)
    if amb:
        ressalvas.append(f"{amb} item(ns) com mais de uma descrição bruta")
    cr["c09_sem_ambiguidade_critica"] = PARCIAL not in st and DIVERGENCIA_TEXTUAL not in st
    cr["c11_rastreabilidade"] = True
    base_ok = all(cr[c] for c in ("c01_identificacao_inequivoca", "c02_catmat_valido", "c03_unidade_interpretavel", "c04_especificacao_suficiente",
                                   "c05_atributos_essenciais_categoria", "c06_evidencias_verificaveis", "c10_regras_versionadas",
                                   "c11_rastreabilidade", "c12_fontes_preservadas"))
    if DIVERGENTE in st:
        gs = grupos(prod["id_candidato"], d["comparacoes"], prod["catmat"])
        if gs:
            d["status"] = AUTO_DESMEMBRAR
            d["motivos"].append("variantes conformes e variantes divergentes do catálogo oficial, separáveis pela própria descrição")
            for g in gs:
                if g["tipo"] == "CONFORME_CATALOGO":
                    sts, res = _avaliar_grupo([d["comparacoes"][v] for v in g["variantes"]], base_ok, ressalvas)
                    g["status"] = sts or AUTO_INCONCLUSIVO
                    g["ressalvas"] = res
                    g["motivos"] = [] if sts else ["critérios de catálogo não atendidos: " + "; ".join(d["motivos"][:-1]) or "—"]
                else:
                    g["status"] = AUTO_INCONCLUSIVO
                    g["ressalvas"] = []
                    g["motivos"] = ["diverge da especificação oficial; sem documentação independente que a sustente"]
                g["nivel"] = "S1" if g["status"] == AUTO_VALIDADO_CATALOGO else ("S2" if g["status"] == AUTO_VALIDADO_CATALOGO_RESSALVA else "")
            d["subprodutos"] = gs
            outros = [v for v, c in d["comparacoes"].items() if c["status"] not in CONFORMES and c["status"] != DIVERGENTE]
            if outros:
                d["ressalvas"].append(f"{len(outros)} variante(s) sem classificação (parcial, divergência textual ou sem descrição)")
        else:
            divs = {tuple(sorted(c["divergencias_materiais"])) for c in d["comparacoes"].values() if c["status"] == DIVERGENTE}
            if len(divs) >= 2:
                d["status"] = AUTO_DIVERGENTE
                d["motivos"].append("variantes materialmente incompatíveis entre si e com o catálogo oficial")
            else:
                d["status"] = AUTO_INCONCLUSIVO
                d["motivos"].append("todas as variantes com texto divergem do catálogo oficial (dados × catálogo contraditórios)")
        d["ressalvas"] += ressalvas
        return d
    if prod["status_auditoria"] == "CONFLITO_OBJETIVO_EXIGE_DESMEMBRAMENTO":
        d["status"] = AUTO_DIVERGENTE
        d["motivos"].append("conflito objetivo entre variantes (auditoria 1.2.0) não resolvido pelo catálogo oficial")
        return d
    if not cr["c09_sem_ambiguidade_critica"]:
        n_p, n_t = st.count(PARCIAL), st.count(DIVERGENCIA_TEXTUAL)
        d["motivos"].append(f"equivalência não demonstrável: {n_p} variante(s) sem todos os valores oficiais, {n_t} com divergência textual de atributo")
    if not (base_ok and cr["c09_sem_ambiguidade_critica"] and cr["c07_cobertura_variantes"]):
        d["status"] = AUTO_INCONCLUSIVO
        d["ressalvas"] = ressalvas
        return d
    sts, res = _avaliar_grupo(list(d["comparacoes"].values()), True, ressalvas)
    d["status"], d["ressalvas"] = sts, res
    d["nivel"] = "S1" if sts == AUTO_VALIDADO_CATALOGO else "S2"
    return d


def status_item(dec, id_variante, ambiguo, doc):
    """(status_item, id_subproduto, motivo). doc = resultado documental da compra (ou None)."""
    fam_ok = dec["status"] in VALIDADOS
    sub = ""
    if dec["status"] == AUTO_DESMEMBRAR:
        g = next((g for g in dec["subprodutos"] if id_variante in g["variantes"]), None)
        if g is None:
            return ITEM_SEM_CLASSIFICACAO, "", "variante sem classificação no desmembramento"
        sub = g["id_subproduto"]
        fam_ok = g["status"] in VALIDADOS
    if not fam_ok:
        return "ITEM_NAO_ELEGIVEL", sub, f"família/subproduto {dec['status'] if not sub else g['status']}"
    if ambiguo:
        return ITEM_SEM_CLASSIFICACAO, sub, "item com mais de uma descrição bruta"
    comp = dec["comparacoes"].get(id_variante)
    if comp is None or comp["status"] == SEM_DESCRICAO:
        base = "item sem descrição própria (ligado só pelo CATMAT)"
    else:
        base = ""
    if doc and doc.get("resultado") == "COMPATIVEL" and not base:
        return AUTO_VALIDADO_ITEM, sub, "especificação do item no documento da contratação compatível com a canônica oficial"
    if doc:
        return ITEM_SEM_VALIDACAO_DOCUMENTAL, sub, f"documento da compra: {doc.get('resultado')}" + (f"; {base}" if base else "")
    return ITEM_SEM_VALIDACAO_DOCUMENTAL, sub, base or "sem documento da contratação examinado"
