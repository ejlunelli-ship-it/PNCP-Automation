"""Conflitos objetivos preservados: (a) entre variantes (auditoria 1.2.0, campo `conflitos` da base congelada) e
(b) variante × especificação oficial (comparação automática), além de contradições entre fontes oficiais."""
from .comparar_especificacoes import DIVERGENCIA_TEXTUAL, DIVERGENTE


def linhas(prod, dec):
    out = []
    for parte in [p for p in (prod["conflitos"] or "").split(" | ") if p.startswith("[OBJETIVO]")]:
        out.append({"id_candidato": prod["id_candidato"], "produto": prod["produto"], "origem": "entre_variantes (auditoria 1.2.0)",
                    "id_variante": "", "descricao": parte, "gravidade": "MATERIAL", "fonte": "saidas/P1/base_produtos.csv"})
    for vid, c in sorted(dec["comparacoes"].items()):
        if c["status"] == DIVERGENTE:
            for x in c["divergencias_materiais"]:
                out.append({"id_candidato": prod["id_candidato"], "produto": prod["produto"], "origem": "variante × catálogo oficial",
                            "id_variante": vid, "descricao": x, "gravidade": "MATERIAL", "fonte": "catálogo CATMAT (API dados abertos)"})
        elif c["status"] == DIVERGENCIA_TEXTUAL:
            for x in c["divergencias_textuais"]:
                out.append({"id_candidato": prod["id_candidato"], "produto": prod["produto"], "origem": "variante × catálogo oficial",
                            "id_variante": vid, "descricao": x, "gravidade": "TEXTUAL (não demonstrada como equivalente)",
                            "fonte": "catálogo CATMAT (API dados abertos)"})
    for n in dec.get("contradicoes_oficiais", []):
        out.append({"id_candidato": prod["id_candidato"], "produto": prod["produto"], "origem": "item oficial × características oficiais",
                    "id_variante": "", "descricao": f"valor da característica '{n}' ausente da descrição oficial do item",
                    "gravidade": "FONTE CONTRADITÓRIA", "fonte": "catálogo CATMAT (API dados abertos)"})
    return out
