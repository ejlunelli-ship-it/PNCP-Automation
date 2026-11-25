"""Desmembramento automático: só com atributos discriminantes confiáveis e atribuição reproduzível de cada item.

Grupos: (a) variantes conformes ao catálogo oficial; (b) variantes divergentes, agrupadas pelos valores em que
divergem. Itens são atribuídos pela PRÓPRIA descrição (desc_id → variante). Variantes parciais, com divergência só
textual ou sem descrição, e itens com mais de uma descrição bruta, ficam sem classificação — nunca vão para o
subtipo mais frequente.
"""
import hashlib
import json

from .comparar_especificacoes import CONFORMES, DIVERGENTE


def id_subproduto(id_candidato, assinatura):
    return f"{id_candidato}.A{hashlib.sha256(json.dumps([id_candidato, assinatura], ensure_ascii=False).encode()).hexdigest()[:8]}"


def grupos(id_candidato, comparacoes, catmat):
    """comparacoes: {id_variante: resultado de comparar_variante}. Devolve lista de grupos ou []."""
    conf = sorted(v for v, c in comparacoes.items() if c["status"] in CONFORMES)
    div = {}
    for v, c in comparacoes.items():
        if c["status"] == DIVERGENTE:
            div.setdefault(tuple(sorted(c["divergencias_materiais"])), []).append(v)
    if not (conf and div):
        return []
    out = [{"id_subproduto": id_subproduto(id_candidato, ["CATALOGO_OFICIAL", catmat]), "tipo": "CONFORME_CATALOGO",
            "variantes": conf, "regra": "variantes conformes à especificação oficial do CATMAT",
            "atributos_diferenciadores": "especificação oficial"}]
    for assin, vs in sorted(div.items()):
        out.append({"id_subproduto": id_subproduto(id_candidato, list(assin)), "tipo": "DIVERGENTE_DO_CATALOGO", "variantes": sorted(vs),
                    "regra": "variantes com os mesmos valores divergentes do catálogo oficial",
                    "atributos_diferenciadores": " | ".join(assin)})
    return out
