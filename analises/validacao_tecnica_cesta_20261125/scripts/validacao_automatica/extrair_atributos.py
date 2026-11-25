"""Especificação canônica a partir das características OFICIAIS do catálogo (não da descrição mais frequente).

Cada característica oficial vira um atributo com evidência (código da característica e do valor, URL e SHA-256 da
resposta). Grandezas são extraídas pelo mesmo Extrator 1.2.0 (conversão só dentro da mesma grandeza), preservando
valor original, unidade original, valor normalizado, unidade canônica e regra de conversão.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extrair_atributos import Extrator  # noqa: E402
from .normalizar_texto import compacto, normalizar  # noqa: E402

_RX_NUM_UN = re.compile(r"(\d+(?:\.\d+)?(?:\s*/\s*\d+(?:\.\d+)?)?)\s*([A-Z%/0-9]*)\s*$")


def regra_conversao(atributo, valor_can, trecho):
    """Descreve a conversão aplicada (ou 'sem conversão')."""
    t = normalizar(trecho)
    m = _RX_NUM_UN.search(t) or re.search(r"(\d+(?:\.\d+)?)\s*([A-Z%/]+)", t)
    un_orig = m.group(2) if m else ""
    partes = valor_can.split(" ", 1)
    un_can = partes[1] if len(partes) == 2 else ""
    if un_orig and un_can and un_orig != un_can and not un_can.startswith("(") and un_orig not in ("X",):
        return un_orig, un_can, f"{atributo}: {un_orig} -> {un_can} (fator exato da mesma grandeza)"
    return un_orig, un_can, "sem conversão"


def especificacao_canonica(ficha, extrator, contexto):
    """Estrutura canônica oficial. Devolve dict com tipo, características (com atributos tipados) e atributos tipados
    agregados; `None` se não houver características oficiais."""
    if ficha.get("status_item") != "OK" or ficha.get("status_caracteristicas") != "OK":
        return None
    item = ficha["item"]
    cars = []
    tip = {}
    for c in ficha["caracteristicas"]:
        texto = f"{c['nome']} {c['valor']} {c['unidade']}".strip()
        n = normalizar(texto)
        t = {a: sorted(v) for a, v in extrator.extrair(n, contexto).items()}
        cars.append({**c, "texto_normalizado": n, "valor_compacto": compacto(c["valor"]), "atributos_tipados": t})
        for a, vals in t.items():
            tip.setdefault(a, set()).update(vals)
    return {"tipo": item["nome_pdm"], "catmat": ficha["catmat"], "descricao_oficial": item["descricao"], "item_ativo": item["ativo"],
            "codigo_pdm": item["codigo_pdm"], "classe": item["codigo_classe"], "atualizado_em": item["atualizado_em"],
            "caracteristicas": cars, "atributos_tipados": {a: sorted(v) for a, v in sorted(tip.items())}}


def linhas_atributos(id_candidato, canon, ficha, extrator, contexto):
    """Linhas de atributos_extraidos.csv para o catálogo oficial (com evidência rastreável)."""
    out = []
    f_car = ficha["fontes"]["catmat_caracteristicas"]
    for c in canon["caracteristicas"]:
        out.append({"id_candidato": id_candidato, "origem": "catalogo_oficial", "id_variante": "", "atributo": f"caracteristica:{c['nome']}",
                    "valor_original": c["valor"], "unidade_original": c["unidade"], "valor_normalizado": c["valor_compacto"],
                    "unidade_canonica": "", "regra": "valor oficial (chave compacta)", "evidencia": f"{c['codigo']}={c['codigo_valor']}",
                    "fonte_url": f_car["url"], "fonte_sha256": f_car["sha256"], "consultado_em": f_car["consultado_em"]})
        det = extrator.extrair(c["texto_normalizado"], contexto)
        for a, vals in sorted(det.items()):
            for v, trechos in sorted(vals.items()):
                uo, uc, regra = regra_conversao(a, v, trechos[0])
                out.append({"id_candidato": id_candidato, "origem": "catalogo_oficial", "id_variante": "", "atributo": a,
                            "valor_original": trechos[0], "unidade_original": uo, "valor_normalizado": v, "unidade_canonica": uc,
                            "regra": regra, "evidencia": f"característica {c['codigo']} ({c['nome']})",
                            "fonte_url": f_car["url"], "fonte_sha256": f_car["sha256"], "consultado_em": f_car["consultado_em"]})
    return out


def novo_extrator(regras, vocabulario):
    e = Extrator(regras)
    e.definir_chaves(vocabulario)
    return e
