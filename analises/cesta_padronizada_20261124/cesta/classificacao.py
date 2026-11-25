"""Auditoria de homogeneidade das descrições e classificação técnica A/B/C.

Regras determinísticas (sem modelo probabilístico). A categoria A indica apenas maior viabilidade de
auditoria; não é aprovação. A categoria final exige revisão humana registrada (formulário).
"""
import hashlib
import json

from . import atributos as at
from .normalizacao import normalizar_texto

VERSAO_REGRAS = "1.0.0"


def carregar_cautela(caminho):
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)["categorias"]


def categorias_cautela(classe, textos, cautela):
    grupo = (classe // 100) if isinstance(classe, int) and classe >= 1000 else None
    achadas = []
    alvo = " " + " ".join(t for t in textos if t) + " "
    for nome, c in cautela.items():
        if (grupo is not None and grupo in c["grupos"]) or any((" " + p) in alvo for p in c["palavras"]):
            achadas.append(nome)
    return achadas


def _hash(s):
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:8]


def variantes_da_familia(linhas):
    """linhas: dicts com descricao_original, descricao_norm, chave_textual, itens, compras, nome_pdm.
    Acrescenta atributos, assinatura, indicadores e segmentos a cada variante."""
    for v in linhas:
        a = at.extrair(v["descricao_norm"])
        v["atributos"] = a
        v["assinatura"] = at.assinatura(a)
        v["indicadores"] = at.indicadores(v["descricao_norm"])
        pdm = normalizar_texto(v.get("nome_pdm"))
        v["segmentos"] = at.segmentos(v["descricao_norm"], pdm)
        v["so_pdm"] = bool(v["descricao_norm"]) and (v["descricao_norm"] == pdm or not v["segmentos"])
    return linhas


def classificar_familia(fam, variantes, metricas, unidade, par_h, cautela):
    """Devolve dict com classe (A/B/C), risco, motivos, alertas, pendências e possíveis subtipos.

    fam: id da família; variantes: lista de variantes (com atributos); metricas: dict da família;
    unidade: dict com unidade_norm, conteudo, alerta."""
    tot = sum(v["itens"] for v in variantes) or 1
    com_desc = [v for v in variantes if v["descricao_norm"]]
    # dominância por chave textual (variantes de formatação somadas)
    por_chave = {}
    for v in com_desc:
        por_chave[v["chave_textual"]] = por_chave.get(v["chave_textual"], 0) + v["itens"]
    share_dom = (max(por_chave.values()) / tot) if por_chave else 0.0
    dom_chave = max(por_chave, key=lambda k: (por_chave[k], k)) if por_chave else None
    dominante = max((v for v in com_desc if v["chave_textual"] == dom_chave), key=lambda v: (v["itens"], v["descricao_original"]),
                    default=None)
    # assinaturas de atributos
    por_ass = {}
    for v in com_desc:
        por_ass[v["assinatura"]] = por_ass.get(v["assinatura"], 0) + v["itens"]
    n_ass = len(por_ass)
    share_ass_dom = (max(por_ass.values()) / tot) if por_ass else 0.0
    ass_dom = max(por_ass, key=lambda k: (por_ass[k], k)) if por_ass else ""

    motivos, alertas, pend = [], [], []
    ind = {}
    for v in com_desc:
        for k in v["indicadores"]:
            ind[k] = ind.get(k, 0) + v["itens"]
    emb_div = sum(v["itens"] for v in com_desc
                  if at.embalagem_divergente(v["atributos"], unidade["unidade_norm"], unidade["conteudo"]))
    so_pdm = sum(v["itens"] for v in variantes if v.get("so_pdm") or not v["descricao_norm"])
    n_seg_dom = len(dominante["segmentos"]) if dominante else 0
    textos = [dominante["descricao_norm"] if dominante else "", normalizar_texto(variantes[0].get("nome_pdm")) or ""]
    caut = categorias_cautela(metricas.get("classe"), textos, cautela)

    if unidade["alerta"]:
        alertas.append(f"unidade: {unidade['alerta']}")
    if n_ass > 1:
        alertas.append(f"{n_ass} assinaturas de atributos distintas (dominante {share_ass_dom:.1%})")
    if emb_div:
        alertas.append(f"embalagem na descrição diverge da unidade em {emb_div / tot:.1%} dos itens")
    for k, n in sorted(ind.items()):
        alertas.append(f"indicador '{k}' em {n / tot:.1%} dos itens")
    if so_pdm:
        alertas.append(f"descrição só com o nome do PDM (sem atributos) em {so_pdm / tot:.1%} dos itens")
    for c in caut:
        alertas.append(f"cautela: {c} ({cautela[c]['risco']})")
        pend.append(f"revisão especializada ({c})")

    # ---------------------------------------------------------------- regras C
    c_motivos = []
    if metricas["share_desc_completa"] < 0.5:
        c_motivos.append(f"descrição completa em só {metricas['share_desc_completa']:.1%} dos itens")
    if unidade["alerta"] in ("unidade_ausente", "formato_nao_reconhecido"):
        c_motivos.append(f"unidade {unidade['alerta']}")
    if dominante is None or n_seg_dom == 0:
        c_motivos.append("descrição dominante sem atributos além do nome do PDM (genérica)")
    if ind.get("generico", 0) / tot >= 0.5:
        c_motivos.append("descrição genérica (DIVERSOS/CONFORME EDITAL/...) na maioria dos itens")
    if share_ass_dom < par_h["share_descricao_dominante_min_B"]:
        c_motivos.append(f"nenhuma assinatura de atributos majoritária ({share_ass_dom:.1%})")
    if (ind.get("aplicacao_variavel", 0) + ind.get("marca_modelo", 0)) / tot >= 0.5 and "pecas_referencia_determinante" in caut:
        c_motivos.append("peça cuja aplicação/referência define o objeto")

    # ---------------------------------------------------------------- regras A
    a_falhas = []
    if share_dom < par_h["share_descricao_dominante_min_A"]:
        a_falhas.append(f"descrição dominante em {share_dom:.1%} < {par_h['share_descricao_dominante_min_A']:.0%}")
    if n_ass > par_h["max_assinaturas_atributos_A"]:
        a_falhas.append(f"{n_ass} assinaturas de atributos")
    if n_seg_dom < par_h["min_atributos_especificos_A"]:
        a_falhas.append(f"só {n_seg_dom} atributo(s) declarados na descrição dominante")
    if metricas["share_desc_completa"] < 0.95:
        a_falhas.append(f"descrição completa em {metricas['share_desc_completa']:.1%} < 95%")
    if emb_div:
        a_falhas.append("indício de embalagem distinta")
    for k in ("marca_modelo", "compatibilidade", "aplicacao_variavel", "generico"):
        if ind.get(k):
            a_falhas.append(f"indicador {k}")
    if unidade["alerta"]:
        a_falhas.append(f"unidade {unidade['alerta']}")

    if c_motivos:
        classe, risco, motivos = "C", "alto", c_motivos
    elif not a_falhas:
        classe, risco = "A", "baixo"
        motivos = [f"descrição dominante em {share_dom:.1%} dos itens; 1 assinatura de atributos; "
                   f"{n_seg_dom} atributos declarados"]
        pend.append("confirmar a especificação canônica e a ausência de exigências extras no termo de referência")
    else:
        classe, risco, motivos = "B", "moderado", a_falhas
        pend.append("revisão especializada da equivalência entre as variantes")

    # subtipos identificáveis: todas as variantes com assinatura não vazia e o MESMO conjunto de chaves
    subtipos = None
    if n_ass > 1 and all(v["assinatura"] for v in com_desc) and len(com_desc) == len(variantes):
        chaves = {tuple(sorted(v["atributos"])) for v in com_desc}
        ambigua = any(len(vals) > 1 for v in com_desc for vals in v["atributos"].values())
        if len(chaves) == 1 and not ambigua:
            subtipos = {a: _hash(a) for a in por_ass}
    return {
        "familia": fam, "classe": classe, "risco_heterogeneidade": risco, "motivos": motivos, "alertas": alertas,
        "pendencias": pend, "share_descricao_dominante": share_dom, "n_assinaturas": n_ass,
        "share_assinatura_dominante": share_ass_dom, "assinatura_dominante": ass_dom,
        "descricao_dominante": dominante["descricao_original"] if dominante else None,
        "n_atributos_dominante": n_seg_dom, "cautela": caut, "subtipos": subtipos,
        "share_embalagem_divergente": emb_div / tot, "indicadores": {k: n / tot for k, n in ind.items()},
        "versao_regras": VERSAO_REGRAS,
    }
