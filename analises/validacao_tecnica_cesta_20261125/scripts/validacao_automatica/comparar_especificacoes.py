"""Comparação, atributo por atributo, de cada variante com a especificação canônica oficial.

Similaridade textual não aprova nada: a variante só é CONFORME se (a) for o texto oficial a menos de espaços, ou
(b) contiver TODOS os valores das características oficiais e nenhum atributo materialmente divergente.
"""
import json

from normalizar_especificacoes import numeros
from .normalizar_texto import compacto, contem, contem_tolerante, igual_ao_oficial, normalizar

CONFORME_TEXTO = "CONFORME_TEXTO_OFICIAL"
CONFORME_ATRIBUTOS = "CONFORME_ATRIBUTOS"
CONFORME_TIPOGRAFICA = "CONFORME_COM_CORRECAO_TIPOGRAFICA"
PARCIAL = "PARCIAL"
DIVERGENCIA_TEXTUAL = "DIVERGENCIA_TEXTUAL"
DIVERGENTE = "DIVERGENTE"
SEM_DESCRICAO = "SEM_DESCRICAO"
CONFORMES = {CONFORME_TEXTO, CONFORME_ATRIBUTOS, CONFORME_TIPOGRAFICA}


def contradicoes_oficiais(canon):
    """Características oficiais cujo valor NÃO aparece na descrição oficial do mesmo item (fontes contraditórias)."""
    dc = compacto(canon["descricao_oficial"])
    return [c["nome"] for c in canon["caracteristicas"] if c["valor_compacto"] and not contem_tolerante(c["valor"], dc)[0]]


def comparar_variante(v, canon, extrator, contexto):
    """v: linha de base_variantes. Devolve dict com status, presentes, ausentes, divergências e tipo de correção."""
    r = {"id_variante": v["id_variante"], "presentes": [], "ausentes": [], "tolerados": [], "divergencias_materiais": [],
         "divergencias_textuais": [], "tipo_igualdade": "", "status": None}
    if v["descricao_ausente"] == "1":
        r["status"] = SEM_DESCRICAO
        return r
    texto = v["descricao_original_mais_frequente"]
    igual, tipo = igual_ao_oficial(texto, canon["descricao_oficial"])
    if igual:
        r["tipo_igualdade"] = tipo
        r["presentes"] = [c["nome"] for c in canon["caracteristicas"]]
        r["status"] = CONFORME_TIPOGRAFICA if tipo == "numero_quebrado" else CONFORME_TEXTO
        return r
    nv = normalizar(texto)
    tc = compacto(texto)
    tv = {a: set(d) for a, d in extrator.extrair(nv, contexto).items()}
    r["equivalencias_grandeza"] = []
    for c in canon["caracteristicas"]:
        numericos = {a: vals for a, vals in c["atributos_tipados"].items() if any(ch.isdigit() for x in vals for ch in x)}
        if numericos:
            # característica com grandeza: o número solto não basta ('500' de 500 ML ≠ '500 G'); exige a MESMA grandeza com
            # o mesmo valor canônico (conversão exata: oficial 500 ML = variante 0,5 L)
            if all(a in tv and set(vals) & tv[a] for a, vals in numericos.items()):
                r["presentes"].append(c["nome"])
                if not contem(c["valor"], tc):
                    r["equivalencias_grandeza"].append(f"{c['nome']}: " + "; ".join(f"{a}={'/'.join(v)}" for a, v in numericos.items()))
            else:
                r["ausentes"].append(c["nome"])
            continue
        achou, tol = contem_tolerante(c["valor"], tc)
        if achou:
            (r["tolerados"] if tol else r["presentes"]).append(c["nome"])
        else:
            r["ausentes"].append(c["nome"])
    # grandezas: conjuntos disjuntos para o mesmo atributo = divergência material
    for a, oficiais in canon["atributos_tipados"].items():
        if a in tv and tv[a] and not (set(oficiais) & tv[a]):
            r["divergencias_materiais"].append(f"{a}: oficial {'/'.join(oficiais)} × variante {'/'.join(sorted(tv[a]))}")
    # atributos declarados com a mesma chave da característica oficial
    decl = json.loads(v["atributos_declarados"] or "{}")
    nomes = {compacto(c["nome"]): c for c in canon["caracteristicas"]}
    for k, vals in decl.items():
        c = nomes.get(compacto(k))
        if not c or c["nome"] not in r["ausentes"]:
            continue
        for val in vals:
            if numeros(val.replace("|", " ")) != numeros(c["valor_compacto"].replace("|", " ")):
                r["divergencias_materiais"].append(f"{c['nome']}: oficial «{c['valor']}» × variante «{val}»")
            else:
                r["divergencias_textuais"].append(f"{c['nome']}: oficial «{c['valor']}» × variante «{val}»")
    if r["divergencias_materiais"]:
        r["status"] = DIVERGENTE
    elif r["divergencias_textuais"]:
        r["status"] = DIVERGENCIA_TEXTUAL
    elif r["ausentes"]:
        r["status"] = PARCIAL
    elif r["tolerados"]:
        r["status"] = CONFORME_TIPOGRAFICA
    else:
        r["status"] = CONFORME_ATRIBUTOS
    return r
