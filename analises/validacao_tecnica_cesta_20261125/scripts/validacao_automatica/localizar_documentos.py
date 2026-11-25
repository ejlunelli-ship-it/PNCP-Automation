"""Nível 2 — documentos de contratação no PNCP (API pública `.../compras/{ano}/{seq}/arquivos`).

Amostra documental reproduzível e INDEPENDENTE da classificação e de qualquer variável econômica: famílias ordenadas
por SHA-256(semente|produto), uma compra por família escolhida por SHA-256(semente|produto|compra). Só documentos do
tipo Termo de Referência ou Edital, ativos, até N por compra. Nunca se consulta o endpoint de itens/resultados.
"""
import hashlib
import re

from .normalizar_texto import normalizar

RX_CONTROLE = re.compile(r"^(\d{14})-(\d)-(\d{1,6})/(\d{4})$")


def h(*partes):
    return hashlib.sha256("|".join(str(p) for p in partes).encode("utf-8")).hexdigest()


def separar_controle(chave):
    m = RX_CONTROLE.match(chave or "")
    if not m:
        return None
    return {"cnpj": m.group(1), "sequencial": int(m.group(3)), "ano": int(m.group(4))}


def amostrar_compras(produtos, compras_por_produto, cfg_doc):
    """produtos: lista ordenada de chaves de produto; compras_por_produto: {produto: set(chave)}.
    Devolve [(produto, chave)] — uma compra por família, para as N primeiras famílias na ordem do hash."""
    s = cfg_doc["semente"]
    fam = sorted(produtos, key=lambda p: (h(s, p), p))[:cfg_doc["familias"]]
    out = []
    for p in fam:
        cs = sorted((c for c in compras_por_produto.get(p, ()) if separar_controle(c)), key=lambda c: (h(s, p, c), c))
        if cs:
            out.append((p, cs[0]))
    return out


def listar_documentos(cache, cfg_fontes, chave):
    """Entrada do cache + lista de documentos (dicts da API) da compra, ou (entrada, None) se indisponível."""
    sc = separar_controle(chave)
    url = cfg_fontes["pncp_arquivos"].format(**sc)
    ent = cache.obter(url, max_bytes=4 * 1024 * 1024)
    if not ent["ok"]:
        return url, ent, None
    d = cache.json(ent)
    return url, ent, (d if isinstance(d, list) else None)


def escolher(docs, cfg_doc):
    aceitos = [normalizar(t) for t in cfg_doc["tipos_aceitos"]]
    sel = []
    for d in docs or []:
        tipo = normalizar(d.get("tipoDocumentoNome") or d.get("tipoDocumentoDescricao") or "")
        if d.get("statusAtivo") is False or tipo not in aceitos or not d.get("url"):
            continue
        sel.append((aceitos.index(tipo), d.get("sequencialDocumento") or 0, d))
    # Termo de Referência antes de Edital; desempate pelo sequencial do documento
    ordem = {normalizar("TERMO DE REFERENCIA"): 0}
    sel.sort(key=lambda x: (ordem.get(aceitos[x[0]], 1), x[1]))
    return [d for _, _, d in sel[:cfg_doc["documentos_por_compra"]]]
