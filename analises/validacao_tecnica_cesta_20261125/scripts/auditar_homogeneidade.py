"""Auditoria de homogeneidade de cada produto: compara 100% das variantes normalizadas, aponta conflitos objetivos,
divergências a examinar, atributos ausentes, riscos e a possibilidade de desmembramento reproduzível.

Só usa texto, atributos extraídos, frequências (itens/compras/UASGs) e metadados técnicos do catálogo.
O resultado é evidência para a revisão humana: o status automático NUNCA é aprovação.
"""
import hashlib
import json
import re

from normalizar_especificacoes import chave_compacta, numeros

VERSAO_AUDITORIA = "1.2.0"

# status automáticos (ordem de precedência)
CHAVE_INVALIDA = "CHAVE_INVALIDA"
CONFLITO = "CONFLITO_OBJETIVO_EXIGE_DESMEMBRAMENTO"
INSUFICIENTE = "ATRIBUTOS_INSUFICIENTES"
A_EXAMINAR = "DIVERGENCIA_A_EXAMINAR"
SEM_DIVERGENCIA = "SEM_DIVERGENCIA_DETECTADA"

ATRIBUTOS_NAO_OBJETIVOS = {"certificacao", "norma_tecnica"}   # diferença vira 'a examinar', não conflito objetivo
RISCOS_EDITAL = {"toner_cartucho", "peca_reposicao", "compatibilidade", "equipamento_eletronico"}


def riscos_do_produto(textos, info, regras):
    """Categorias de risco que pedem avaliação especializada (palavras do texto, cautela da cesta, classe do catálogo)."""
    cautela = {c.strip() for c in (info.get("cautela") or "").split(",") if c.strip()}
    classe = (info.get("classe_catalogo") or "").strip()
    tudo = " , ".join(textos)
    out = {}
    for nome, r in regras["riscos"].items():
        if nome.startswith("_"):
            continue
        ev = []
        for p in r.get("palavras", []):
            # palavra inteira (plural S/ES aceito); 'X*' = prefixo de palavra (regra 1.2.0)
            fim = r"" if p.endswith("*") else r"(?:S|ES)?(?![A-Z0-9])"
            if re.search(rf"(?<![A-Z0-9]){re.escape(p.rstrip('*'))}{fim}", tudo):
                ev.append(f"palavra '{p}'")
        ev += [f"cautela da cesta '{c}'" for c in r.get("cautela", []) if c in cautela]
        if classe and classe in r.get("classes_catalogo", []):
            ev.append(f"classe do catálogo {classe}")
        if ev:
            out[nome] = ev
    return out


def _relacao(conjuntos):
    """Compara conjuntos não vazios de valores entre variantes: 'igual', 'subconjunto' (informação parcial) ou 'disjunto'."""
    distintos = {frozenset(s) for s in conjuntos if s}
    if len(distintos) <= 1:
        return "igual"
    lista = sorted(distintos, key=lambda s: (len(s), sorted(s)))
    for i, a in enumerate(lista):
        for b in lista[i + 1:]:
            if not (a <= b or b <= a):
                return "disjunto"
    return "subconjunto"


def _valores_por_variante(variantes, campo):
    """{atributo: {id_variante: set(valores)}}"""
    out = {}
    for v in variantes:
        for a, vals in v[campo].items():
            out.setdefault(a, {})[v["id_variante"]] = set(vals)
    return out


def auditar_produto(info, variantes, regras):
    """info: dados do produto (id_candidato, produto, catmat, unidade_norm, ambiguos, ...).
    variantes: lista de dicts com id_variante, descricao_normalizada, chave_compacta, nome, atributos {a: [valores]},
    declarados {chave: [valores_compactos]}, itens, descricao_ausente, notas."""
    objetivas_decl = {chave_compacta(k) for k in regras["chaves_declaradas_categoricas_objetivas"]}
    conflitos, ausentes, alertas = [], [], []
    ids = [v["id_variante"] for v in variantes]
    itens_v = {v["id_variante"]: v["itens"] for v in variantes}
    com_texto = [v for v in variantes if not v["descricao_ausente"]]

    def registrar(atributo, origem, por_var, relacao, objetivo):
        valores = {}
        for vid, s in por_var.items():
            for x in sorted(s):
                d = valores.setdefault(x, {"itens": 0, "variantes": []})
                d["itens"] += itens_v[vid]
                d["variantes"].append(vid)
        conflitos.append({"atributo": atributo, "origem": origem, "relacao": relacao,
                          "gravidade": "OBJETIVO" if objetivo else "A_EXAMINAR",
                          "valores": valores, "variantes_sem_valor": sorted(set(ids) - set(por_var))})

    # ---------------------------------------------------------------------- atributos tipados
    tip = _valores_por_variante(com_texto, "atributos")
    for a in sorted(tip):
        por_var = tip[a]
        rel = _relacao(por_var.values())
        if rel != "igual":
            registrar(a, "extraido", por_var, rel, objetivo=(rel == "disjunto" and a not in ATRIBUTOS_NAO_OBJETIVOS))
        faltam = sorted(v["id_variante"] for v in com_texto if v["id_variante"] not in por_var)
        if faltam:
            ausentes.append({"atributo": a, "origem": "extraido", "variantes_sem_atributo": faltam})
    # ---------------------------------------------------------------------- atributos declarados (catálogo)
    dec = _valores_por_variante(com_texto, "declarados")
    for k in sorted(dec):
        por_var = dec[k]
        rel = _relacao(por_var.values())
        if rel != "igual":
            nums = {frozenset(n for x in s for n in numeros(x)) for s in por_var.values()}
            objetivo = rel == "disjunto" and (len(nums) > 1 or chave_compacta(k) in objetivas_decl)
            # só espaço dentro de um número ('45~5 0' × '45~50'): provável quebra de linha da fonte -> a examinar (regra 1.1.0)
            estrito = {frozenset(re.sub(r"[^A-Z0-9]", "", x) for x in s) for s in por_var.values()}
            if len(estrito) == 1:
                rel, objetivo = "so_espacamento", False
            registrar(f"declarado:{k}", "declarado", por_var, rel, objetivo)
        faltam = sorted(v["id_variante"] for v in com_texto if v["id_variante"] not in por_var)
        if faltam:
            ausentes.append({"atributo": f"declarado:{k}", "origem": "declarado", "variantes_sem_atributo": faltam})
    # ---------------------------------------------------------------------- números do texto não explicados
    nums_var = {v["id_variante"]: frozenset(numeros(v["descricao_normalizada"])) for v in com_texto}
    if len(set(nums_var.values())) > 1:
        registrar("numeros_no_texto", "texto", {k: set(s) for k, s in nums_var.items()}, _relacao(nums_var.values()), objetivo=False)
    # ---------------------------------------------------------------------- nome do item e notas
    nomes = {chave_compacta(v["nome"]) for v in com_texto}
    if len(nomes) > 1:
        alertas.append("nome do item (primeiro segmento) difere entre variantes")
    notas = sorted({n for v in variantes for n in v["notas"]})
    if notas:
        alertas.append("nota de catálogo: " + "; ".join(notas))
    sem_texto = [v["id_variante"] for v in variantes if v["descricao_ausente"]]
    if sem_texto:
        alertas.append(f"{len(sem_texto)} variante(s) sem descrição: equivalência só pelo código CATMAT ({sum(itens_v[x] for x in sem_texto)} itens)")
    if info.get("ambiguos"):
        alertas.append(f"{info['ambiguos']} item(ns) com mais de uma descrição bruta (associação item × descrição ambígua)")
    textual = len({v["chave_compacta"] for v in com_texto}) > 1
    if textual:
        alertas.append("texto difere entre variantes além de espaços e pontuação")

    n_attr = {v["id_variante"]: len(v["atributos"]) + len(v["declarados"]) for v in variantes}
    insuficiente = not com_texto or max(n_attr[v["id_variante"]] for v in com_texto) == 0
    objetivos = [c for c in conflitos if c["gravidade"] == "OBJETIVO"]

    if not (info.get("catmat") or "").strip() or not (info.get("unidade_norm") or "").strip():
        status = CHAVE_INVALIDA
    elif objetivos:
        status = CONFLITO
    elif insuficiente:
        status = INSUFICIENTE
    elif conflitos or textual or sem_texto or notas or info.get("ambiguos") or len(nomes) > 1:
        status = A_EXAMINAR
    else:
        status = SEM_DIVERGENCIA

    # ---------------------------------------------------------------------- consenso / atributos essenciais
    consenso = {}
    for campo, por in (("atributos", tip), ("declarados", dec)):
        for a, por_var in por.items():
            vals = {frozenset(s) for s in por_var.values()}
            if len(vals) == 1:
                (s,) = vals
                if len(s) == 1:
                    consenso[a if campo == "atributos" else f"declarado:{a}"] = next(iter(s))

    # ---------------------------------------------------------------------- desmembramento reproduzível
    sub, motivo_sub = None, ""
    if objetivos:
        attrs = sorted(c["atributo"] for c in objetivos)
        problemas = []
        if sem_texto:
            problemas.append("há variantes sem descrição (não classificáveis)")
        if info.get("ambiguos"):
            problemas.append("há itens com mais de uma descrição bruta")
        chaves = {}
        for v in variantes:
            if v["descricao_ausente"]:
                continue
            tupla = []
            for a in attrs:
                fonte = v["declarados"].get(a[len("declarado:"):]) if a.startswith("declarado:") else v["atributos"].get(a)
                s = set(fonte or ())
                if len(s) != 1:
                    problemas.append(f"variante {v['id_variante']} tem {len(s)} valor(es) para {a}")
                    break
                tupla.append((a, next(iter(s))))
            else:
                chaves[v["id_variante"]] = tuple(tupla)
        if not problemas and len(set(chaves.values())) >= 2:
            sub = {vid: id_especificacao(info["id_candidato"], t) for vid, t in chaves.items()}
        else:
            motivo_sub = "; ".join(dict.fromkeys(problemas)) or "um único grupo de valores"

    requer_esp = sorted(info.get("riscos", {}))
    edital = []
    if status == INSUFICIENTE:
        edital.append("atributos técnicos insuficientes na descrição")
    if RISCOS_EDITAL & set(requer_esp):
        edital.append("risco: " + ", ".join(sorted(RISCOS_EDITAL & set(requer_esp))))
    if sem_texto:
        edital.append("variantes sem descrição")
    if "medicamento" in requer_esp and not any(a.startswith(("concentracao", "dosagem")) for a in tip):
        edital.append("medicamento sem concentração/dosagem identificada")
    if any(c["gravidade"] == "A_EXAMINAR" and c["atributo"] == "numeros_no_texto" for c in conflitos):
        edital.append("números divergentes no texto")
    return {"status": status, "conflitos": conflitos, "ausentes": ausentes, "alertas": alertas,
            "consenso": consenso, "subprodutos": sub, "motivo_nao_desmembravel": motivo_sub,
            "requer_especialista": requer_esp, "consulta_edital": edital,
            "n_conflitos_objetivos": len(objetivos), "n_divergencias_a_examinar": len(conflitos) - len(objetivos)}


def id_especificacao(id_candidato, tupla):
    """Identificador estável da especificação atômica: depende só do produto e dos valores diferenciadores."""
    h = hashlib.sha256(json.dumps([id_candidato, list(tupla)], ensure_ascii=False).encode("utf-8")).hexdigest()[:8]
    return f"{id_candidato}.{h}"


def resumo_conflitos(conflitos, so_objetivos=False):
    out = []
    for c in conflitos:
        if so_objetivos and c["gravidade"] != "OBJETIVO":
            continue
        vals = " vs ".join(f"{v} ({d['itens']} itens)" for v, d in sorted(c["valores"].items()))
        out.append(f"[{c['gravidade']}] {c['atributo']}: {vals}")
    return " | ".join(out)
