"""Nível 1 — catálogo oficial (CATMAT/PDM do Compras.gov.br, API pública de dados abertos).

Para cada CATMAT: item (descrição oficial, situação, PDM, classe) e características estruturadas (nome, valor,
unidade de medida, códigos). Para cada PDM: unidades de fornecimento oficiais. Tudo via `acesso_fontes.Cache`.
"""
from concurrent.futures import ThreadPoolExecutor

OK, VAZIO, INDISPONIVEL, INVALIDO = "OK", "VAZIO", "INDISPONIVEL", "RESPOSTA_INVALIDA"


def _avaliar(cache, ent):
    if ent is None:
        return INDISPONIVEL, None
    if not ent["ok"]:
        return (VAZIO if ent.get("status_http") == 404 else INDISPONIVEL), None
    d = cache.json(ent)
    if not isinstance(d, dict) or not isinstance(d.get("resultado"), list):
        return INVALIDO, None
    if d.get("paginasRestantes"):
        return INVALIDO, d                                   # resposta truncada: não usar como completa
    return (OK if d["resultado"] else VAZIO), d


def urls(cfg_fontes, catmat=None, pdm=None):
    out = {}
    if catmat:
        out["catmat_item"] = cfg_fontes["catmat_item"].format(catmat=catmat)
        out["catmat_caracteristicas"] = cfg_fontes["catmat_caracteristicas"].format(catmat=catmat)
    if pdm:
        out["pdm_unidades"] = cfg_fontes["pdm_unidades"].format(pdm=pdm)
    return out


def coletar(cache, cfg_fontes, catmats, pdms, reg=None, atualizar=False):
    """Busca (ou reutiliza do cache) todas as URLs; devolve {url: entrada}. Paralelismo limitado e taxa controlada."""
    alvo = []
    for c in sorted(catmats):
        alvo += list(urls(cfg_fontes, catmat=c).values())
    for p in sorted(pdms):
        alvo += list(urls(cfg_fontes, pdm=p).values())
    feitos, total = 0, len(alvo)
    res = {}

    def um(u):
        return u, cache.obter(u, atualizar=atualizar, max_bytes=8 * 1024 * 1024)

    with ThreadPoolExecutor(max_workers=cfg_fontes["conexoes_simultaneas"]) as ex:
        for u, ent in ex.map(um, alvo):
            res[u] = ent
            feitos += 1
            if reg and feitos % 500 == 0:
                reg.log(f"catálogo: {feitos}/{total} consultas")
    return res


def ficha_oficial(cache, cfg_fontes, catmat, pdm, entradas):
    """Estrutura a evidência oficial de um CATMAT (e das unidades do PDM)."""
    u = urls(cfg_fontes, catmat=catmat, pdm=pdm)
    st_i, di = _avaliar(cache, entradas.get(u["catmat_item"]))
    st_c, dc = _avaliar(cache, entradas.get(u["catmat_caracteristicas"]))
    st_u, du = _avaliar(cache, entradas.get(u["pdm_unidades"])) if pdm else (INDISPONIVEL, None)
    f = {"catmat": catmat, "status_item": st_i, "status_caracteristicas": st_c, "status_unidades": st_u,
         "fontes": {k: {"url": v, "sha256": (entradas.get(v) or {}).get("sha256"), "consultado_em": (entradas.get(v) or {}).get("consultado_em"),
                        "status_http": (entradas.get(v) or {}).get("status_http")} for k, v in u.items()}}
    if st_i == OK:
        it = [r for r in di["resultado"] if str(r.get("codigoItem")) == str(catmat)]
        if len(it) != 1:
            f["status_item"] = INVALIDO
        else:
            it = it[0]
            f["item"] = {"descricao": it.get("descricaoItem") or "", "ativo": bool(it.get("statusItem")), "codigo_pdm": it.get("codigoPdm"),
                         "nome_pdm": it.get("nomePdm") or "", "codigo_classe": it.get("codigoClasse"), "nome_classe": it.get("nomeClasse"),
                         "atualizado_em": it.get("dataHoraAtualizacao")}
    if st_c == OK:
        cars = []
        for r in sorted(dc["resultado"], key=lambda r: (r.get("numeroCaracteristica") or 0, r.get("codigoCaracteristica") or "")):
            if str(r.get("codigoItem")) != str(catmat):
                continue
            cars.append({"nome": r.get("nomeCaracteristica") or "", "valor": r.get("nomeValorCaracteristica") or "",
                         "unidade": r.get("siglaUnidadeMedida") or "", "codigo": r.get("codigoCaracteristica"),
                         "codigo_valor": r.get("codigoValorCaracteristica"), "numero": r.get("numeroCaracteristica"),
                         "ativo": bool(r.get("statusCaracteristica")) and bool(r.get("statusValorCaracteristica"))})
        f["caracteristicas"] = cars
    if st_u == OK:
        f["unidades"] = [{"sigla": r.get("siglaUnidadeFornecimento") or "", "nome": r.get("nomeUnidadeFornecimento") or "",
                          "capacidade": r.get("capacidadeUnidadeFornecimento"), "unidade_medida": r.get("siglaUnidadeMedida") or "",
                          "ativo": bool(r.get("statusUnidadeFornecimentoPdm")) and bool(r.get("statusUnidadeFornecimento"))}
                         for r in du["resultado"]]
    return f
