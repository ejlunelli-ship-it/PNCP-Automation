"""Etapa auto-validar: classifica famílias, subprodutos e itens a partir do snapshot documental e grava as saídas.

Separação central: `cesta_catalogo_validada_automaticamente.csv` (homogeneidade do CATÁLOGO, só S1) ≠
`itens_validados_automaticamente.csv` (itens com compatibilidade demonstrada por documento da própria contratação).
Tabelas vazias são gravadas com cabeçalho; nada é preenchido por suposição.
"""
import csv
import gzip
import io
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

import comum

from . import (AUTO_DESMEMBRAR, AUTO_DIVERGENTE, AUTO_ERRO_DADOS, AUTO_INCONCLUSIVO, AUTO_VALIDADO_CATALOGO,
               AUTO_VALIDADO_CATALOGO_RESSALVA, AUTO_VALIDADO_ITEM, ITEM_SEM_CLASSIFICACAO, ITEM_SEM_VALIDACAO_DOCUMENTAL,
               VERSAO_VALIDADOR)
from .consultar_catalogo import ficha_oficial
from .decidir_validacao import CRITERIOS, VALIDADOS, decidir_familia, status_item
from .detectar_conflitos import linhas as linhas_conflitos
from .extrair_atributos import especificacao_canonica, linhas_atributos, novo_extrator
from .pipeline import _base, carregar_documentos, contexto_produto, snapshot_entradas


def _csv(caminho, linhas, cols, gz=False):
    caminho = Path(caminho)
    if gz:
        tmp = caminho.with_suffix(caminho.suffix + ".tmp")
        n = 0
        with io.TextIOWrapper(gzip.GzipFile(tmp, "wb", mtime=0), encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(cols)
            for x in linhas:
                w.writerow([comum._fmt(x.get(c)) for c in cols])
                n += 1
        tmp.replace(caminho)
        return n
    return comum.escrever_csv(caminho, linhas, cols)


def _j(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True)


def validar(ctx, reg):
    man, P, V, origs = _base(ctx)
    entradas = snapshot_entradas(ctx)
    f = ctx.auto["fontes"]
    voc = comum.carregar_json(ctx.origem / "vocabulario_chaves_declaradas.json")
    ext = novo_extrator(ctx.cfg["regras"], voc)
    con = sqlite3.connect(ctx.estado / "itens.db")
    unid = {}
    for un, emb, cont, ucont, alerta in con.execute("SELECT unidade_norm, embalagem, conteudo, unidade_conteudo, alerta FROM unidades "
                                                  "ORDER BY unidade_norm, embalagem, conteudo, unidade_conteudo, alerta"):
        x = {"embalagem": emb, "conteudo": cont, "unidade_conteudo": ucont, "alerta": alerta}
        if un in unid and (unid[un]["embalagem"], unid[un]["conteudo"], unid[un]["unidade_conteudo"]) != (emb, cont, ucont):
            unid[un]["alerta"] = (unid[un].get("alerta") or "") + " leituras divergentes da unidade"
        unid.setdefault(un, x)
    dec, canons, fichas = {}, {}, {}
    l_esp, l_attr, l_comp, l_conf, l_aud = [], [], [], [], []
    reg.log("classificando famílias ...")
    for p in sorted(P, key=lambda p: (int(p["ordem_revisao"]), p["id_candidato"])):
        ficha = ficha_oficial(ctx.cache, f, p["catmat"], p["pdm"], entradas)
        cx = contexto_produto(p)
        canon = especificacao_canonica(ficha, ext, cx)
        preserv = all((ctx.cache.pasta / (entradas.get(u) or {}).get("arquivo", "x")).exists()
                      for u in (ficha["fontes"]["catmat_item"]["url"], ficha["fontes"]["catmat_caracteristicas"]["url"])
                      if (entradas.get(u) or {}).get("ok"))
        d = decidir_familia(p, V[p["id_candidato"]], ficha, canon, ext, cx, ctx.auto, unid.get(p["unidade_norm"]), preserv)
        dec[p["id_candidato"]], canons[p["id_candidato"]], fichas[p["id_candidato"]] = d, canon, ficha
        fi, fc = ficha["fontes"]["catmat_item"], ficha["fontes"]["catmat_caracteristicas"]
        l_esp.append({"id_candidato": p["id_candidato"], "produto": p["produto"], "catmat": p["catmat"], "unidade_norm": p["unidade_norm"],
                      "status_catalogo": ficha["status_item"], "status_caracteristicas": ficha["status_caracteristicas"],
                      "tipo": (canon or {}).get("tipo", ""), "descricao_oficial": (canon or {}).get("descricao_oficial", ""),
                      "item_ativo": (canon or {}).get("item_ativo", ""), "n_caracteristicas": len((canon or {}).get("caracteristicas", [])),
                      "especificacao_canonica": _j({"tipo": canon["tipo"], "caracteristicas": [{k: c[k] for k in ("nome", "valor", "unidade", "codigo", "codigo_valor")} for c in canon["caracteristicas"]],
                                                    "atributos_tipados": canon["atributos_tipados"]}) if canon else "",
                      "perfis": ";".join(d["perfis"]), "unidade_avaliacao": d["unidade"],
                      "fonte_item_url": fi["url"], "fonte_item_sha256": fi["sha256"], "fonte_caracteristicas_url": fc["url"],
                      "fonte_caracteristicas_sha256": fc["sha256"], "consultado_em": fc["consultado_em"],
                      "atualizado_no_catalogo_em": (canon or {}).get("atualizado_em", "")})
        if canon:
            l_attr += linhas_atributos(p["id_candidato"], canon, ficha, ext, cx)
        for v in V[p["id_candidato"]]:
            c = d["comparacoes"].get(v["id_variante"])
            g = next((g["id_subproduto"] for g in d["subprodutos"] if v["id_variante"] in g["variantes"]), "")
            l_comp.append({"id_variante": v["id_variante"], "id_candidato": p["id_candidato"], "produto": p["produto"],
                           "status_variante": c["status"] if c else "NAO_COMPARADA (sem especificação oficial)",
                           "tipo_igualdade_texto_oficial": (c or {}).get("tipo_igualdade", ""),
                           "caracteristicas_presentes": ";".join((c or {}).get("presentes", [])),
                           "caracteristicas_ausentes": ";".join((c or {}).get("ausentes", [])),
                           "caracteristicas_com_correcao_tipografica": ";".join((c or {}).get("tolerados", [])),
                           "divergencias_materiais": " | ".join((c or {}).get("divergencias_materiais", [])),
                           "divergencias_textuais": " | ".join((c or {}).get("divergencias_textuais", [])),
                           "id_subproduto": g, "itens": v["itens"], "descricao_ausente": v["descricao_ausente"],
                           "descricao_normalizada": v["descricao_normalizada"], "fonte_comparacao": fc["url"] if canon else ""})
        l_conf += linhas_conflitos(p, d)
        l_aud.append({"id_registro": p["id_candidato"], "tipo_registro": "PRODUTO", "id_candidato": p["id_candidato"], "produto": p["produto"],
                      "status_automatico": d["status"], "nivel": d["nivel"], **{c: d["criterios"][c] for c in CRITERIOS},
                      "motivos": " | ".join(d["motivos"]), "ressalvas": " | ".join(d["ressalvas"]),
                      "evidencias": f"{fi['url']} (sha256 {fi['sha256']}); {fc['url']} (sha256 {fc['sha256']})",
                      "versao_validador": VERSAO_VALIDADOR, "versao_regras": ctx.auto["versao_regras_automaticas"],
                      "versao_auditoria_origem": man["versao_auditoria"], "hash_registro_origem": p["hash_registro"],
                      "tipo_validacao": "automatica (não é revisão humana)"})
        for g in d["subprodutos"]:
            l_aud.append({"id_registro": g["id_subproduto"], "tipo_registro": "SUBPRODUTO", "id_candidato": p["id_candidato"], "produto": p["produto"],
                          "status_automatico": g["status"], "nivel": g["nivel"], **{c: "" for c in CRITERIOS},
                          "motivos": " | ".join(g.get("motivos", [])), "ressalvas": " | ".join(g.get("ressalvas", [])),
                          "evidencias": g["regra"], "versao_validador": VERSAO_VALIDADOR, "versao_regras": ctx.auto["versao_regras_automaticas"],
                          "versao_auditoria_origem": man["versao_auditoria"], "hash_registro_origem": p["hash_registro"],
                          "tipo_validacao": "automatica (não é revisão humana)"})

    # ---------------------------------------------------------------------------------------- itens
    reg.log("classificando itens ...")
    var_de = {(o["produto"], int(o["desc_id"])): o["id_variante"] for o in origs}
    docs = carregar_documentos(ctx)
    doc_por = {k: v for k, v in docs.items()}
    porp = {p["produto"]: p for p in P}
    cont = Counter()
    sub_itens = Counter()
    sub_nao = Counter()
    s = ctx.saida
    cols_it = ["numero_controle_pncp", "numero_item", "id_candidato", "produto", "id_variante", "id_subproduto", "uasg", "data_publicacao",
               "ano", "trimestre", "uf", "status_familia", "status_item", "motivo"]
    validados = []
    gz = {}
    for nome in ("itens_sem_validacao_documental.csv.gz", "itens_sem_classificacao.csv.gz"):
        fh = io.TextIOWrapper(gzip.GzipFile(s / (nome + ".tmp"), "wb", mtime=0), encoding="utf-8", newline="")
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(cols_it)
        gz[nome] = (fh, w)
    n_gz = Counter()
    cur = con.execute("SELECT chave, numero_item, produto, desc_id, uasg, data_publicacao, ano, trimestre, n_descricoes_item, uf FROM itens "
                      "ORDER BY produto, chave, numero_item")
    for chave, item, prod, did, uasg, data, ano, tri, ndesc, uf in cur:
        p = porp[prod]
        d = dec[p["id_candidato"]]
        vid = var_de.get((prod, int(did or 0)), "")
        docr = doc_por.get((prod, chave))
        st, sub, mot = status_item(d, vid, (ndesc or 1) > 1, docr)
        cont[st] += 1
        linha = {"numero_controle_pncp": chave, "numero_item": item, "id_candidato": p["id_candidato"], "produto": prod, "id_variante": vid,
                 "id_subproduto": sub, "uasg": uasg, "data_publicacao": data, "ano": ano, "trimestre": tri, "uf": uf,
                 "status_familia": d["status"], "status_item": st, "motivo": mot}
        if d["status"] == AUTO_DESMEMBRAR:
            if sub:
                sub_itens[sub] += 1
            else:
                sub_nao[p["id_candidato"]] += 1
        if st == AUTO_VALIDADO_ITEM:
            a = docr["ancora"]
            linha.update({"documento_url": a["documento_url"], "documento_sha256": a["documento_sha256"], "pagina": a["pagina"],
                          "trecho": a["trecho"], "caracteristicas_confirmadas": ";".join(a["presentes"] + a["tolerados"])})
            validados.append(linha)
        elif st in (ITEM_SEM_VALIDACAO_DOCUMENTAL, ITEM_SEM_CLASSIFICACAO):
            nome = "itens_sem_validacao_documental.csv.gz" if st == ITEM_SEM_VALIDACAO_DOCUMENTAL else "itens_sem_classificacao.csv.gz"
            gz[nome][1].writerow([comum._fmt(linha.get(c)) for c in cols_it])
            n_gz[nome] += 1
    con.close()
    for nome, (fh, _) in gz.items():
        fh.close()
        (s / (nome + ".tmp")).replace(s / nome)
    _csv(s / "itens_validados_automaticamente.csv", validados, cols_it + ["documento_url", "documento_sha256", "pagina", "trecho", "caracteristicas_confirmadas"])

    # ---------------------------------------------------------------------------------------- famílias e cestas
    def fam(p, d):
        return {"id_candidato": p["id_candidato"], "produto": p["produto"], "catmat": p["catmat"], "unidade_norm": p["unidade_norm"],
                "status_automatico": d["status"], "nivel": d["nivel"], "motivos": " | ".join(d["motivos"]), "ressalvas": " | ".join(d["ressalvas"]),
                "perfis": ";".join(d["perfis"]), "compras": p["compras"], "itens": p["itens"], "uasgs": p["uasgs"]}
    cols_f = ["id_candidato", "produto", "catmat", "unidade_norm", "status_automatico", "nivel", "motivos", "ressalvas", "perfis", "compras", "itens", "uasgs"]
    _csv(s / "familias_inconclusivas.csv", [fam(p, dec[p["id_candidato"]]) for p in P if dec[p["id_candidato"]]["status"] in (AUTO_INCONCLUSIVO, AUTO_ERRO_DADOS)], cols_f)
    _csv(s / "familias_divergentes.csv", [fam(p, dec[p["id_candidato"]]) for p in P if dec[p["id_candidato"]]["status"] == AUTO_DIVERGENTE], cols_f)
    _csv(s / "familias_desmembradas.csv", [fam(p, dec[p["id_candidato"]]) for p in P if dec[p["id_candidato"]]["status"] == AUTO_DESMEMBRAR], cols_f)
    l_sub = []
    for p in P:
        for g in dec[p["id_candidato"]]["subprodutos"]:
            l_sub.append({"id_candidato": p["id_candidato"], "produto": p["produto"], "id_subproduto": g["id_subproduto"], "tipo": g["tipo"],
                          "status_automatico": g["status"], "nivel": g["nivel"], "atributos_diferenciadores": g["atributos_diferenciadores"],
                          "regra_separacao": g["regra"], "variantes": ";".join(g["variantes"]), "itens_atribuidos": sub_itens[g["id_subproduto"]],
                          "itens_nao_classificaveis_da_familia": sub_nao[p["id_candidato"]], "motivos": " | ".join(g.get("motivos", [])),
                          "ressalvas": " | ".join(g.get("ressalvas", [])), "versao_validador": VERSAO_VALIDADOR})
    _csv(s / "subprodutos_identificados.csv", l_sub, ["id_candidato", "produto", "id_subproduto", "tipo", "status_automatico", "nivel",
                                                     "atributos_diferenciadores", "regra_separacao", "variantes", "itens_atribuidos",
                                                     "itens_nao_classificaveis_da_familia", "motivos", "ressalvas", "versao_validador"])
    cesta = []
    for p in P:
        d = dec[p["id_candidato"]]
        regs = [(p["id_candidato"], "PRODUTO", d["nivel"], d["status"])] if d["status"] == AUTO_VALIDADO_CATALOGO else []
        regs += [(g["id_subproduto"], "SUBPRODUTO", g["nivel"], g["status"]) for g in d["subprodutos"] if g["status"] == AUTO_VALIDADO_CATALOGO]
        for idr, tipo, nivel, st in regs:
            e = next(x for x in l_esp if x["id_candidato"] == p["id_candidato"])
            cesta.append({"id_registro": idr, "tipo_registro": tipo, "id_candidato": p["id_candidato"], "produto": p["produto"],
                          "catmat": p["catmat"], "unidade_norm": p["unidade_norm"], "status_validacao": st, "nivel_seguranca": nivel,
                          "modalidade": "AUTOMATICA_CATALOGO (homogeneidade de catálogo; não comprova conformidade de cada contratação)",
                          "especificacao_canonica": e["especificacao_canonica"], "fonte_item_url": e["fonte_item_url"],
                          "fonte_item_sha256": e["fonte_item_sha256"], "fonte_caracteristicas_url": e["fonte_caracteristicas_url"],
                          "fonte_caracteristicas_sha256": e["fonte_caracteristicas_sha256"], "consultado_em": e["consultado_em"],
                          "versao_validador": VERSAO_VALIDADOR, "versao_regras": ctx.auto["versao_regras_automaticas"],
                          "versao_auditoria_origem": man["versao_auditoria"], "hash_registro_origem": p["hash_registro"]})
    cols_c = ["id_registro", "tipo_registro", "id_candidato", "produto", "catmat", "unidade_norm", "status_validacao", "nivel_seguranca",
              "modalidade", "especificacao_canonica", "fonte_item_url", "fonte_item_sha256", "fonte_caracteristicas_url",
              "fonte_caracteristicas_sha256", "consultado_em", "versao_validador", "versao_regras", "versao_auditoria_origem", "hash_registro_origem"]
    _csv(s / "cesta_catalogo_validada_automaticamente.csv", cesta, cols_c)
    itens_s4 = Counter(x["id_candidato"] for x in validados)
    sens = []
    for p in P:
        d = dec[p["id_candidato"]]
        s1 = d["status"] == AUTO_VALIDADO_CATALOGO or any(g["status"] == AUTO_VALIDADO_CATALOGO for g in d["subprodutos"])
        s2 = d["status"] == AUTO_VALIDADO_CATALOGO_RESSALVA or any(g["status"] == AUTO_VALIDADO_CATALOGO_RESSALVA for g in d["subprodutos"])
        sens.append({"id_candidato": p["id_candidato"], "produto": p["produto"], "status_automatico": d["status"],
                     "S1_alta_seguranca": int(s1), "S2_seguranca_intermediaria": int(s2 and not s1), "S3_candidato_original": 1,
                     "S4_itens_verificados": itens_s4.get(p["id_candidato"], 0), "ressalvas_S2": " | ".join(d["ressalvas"]) if (s2 and not s1) else ""})
    _csv(s / "resultados_sensibilidade.csv", sens, list(sens[0].keys()))
    _csv(s / "especificacoes_canonicas.csv", l_esp, list(l_esp[0].keys()))
    _csv(s / "atributos_extraidos.csv", l_attr, ["id_candidato", "origem", "id_variante", "atributo", "valor_original", "unidade_original",
                                                "valor_normalizado", "unidade_canonica", "regra", "evidencia", "fonte_url", "fonte_sha256", "consultado_em"])
    _csv(s / "comparacao_variantes.csv", l_comp, list(l_comp[0].keys()))
    _csv(s / "conflitos_objetivos.csv", l_conf, ["id_candidato", "produto", "origem", "id_variante", "descricao", "gravidade", "fonte"])
    _csv(s / "auditoria_decisoes.csv", l_aud, list(l_aud[0].keys()))
    # ---------------------------------------------------------------------------------------- fontes
    produtos_de = defaultdict(list)
    for p in P:
        for k, u in fichas[p["id_candidato"]]["fontes"].items():
            produtos_de[u["url"]].append(p["id_candidato"])
    l_fontes, l_indisp = [], []
    for u, e in sorted(entradas.items()):
        tipo = "CATMAT_ITEM" if "4_consultarItemMaterial" in u else "CATMAT_CARACTERISTICAS" if "7_consultar" in u else "PDM_UNIDADES"
        l_fontes.append({"tipo": tipo, "identificador": u.rsplit("=", 1)[-1], "url": u, "ok": int(bool(e["ok"])), "status_http": e["status_http"],
                         "consultado_em": e["consultado_em"], "sha256": e["sha256"], "bytes": e["bytes"], "arquivo_cache": e["arquivo"],
                         "produtos": ";".join(sorted(set(produtos_de.get(u, []))))})
        if not e["ok"]:
            l_indisp.append({"nivel": "1_catalogo", "tipo": tipo, "url": u, "status_http": e["status_http"], "erro": e["erro"] or
                             ("registro inexistente (404)" if e["status_http"] == 404 else ""), "consultado_em": e["consultado_em"],
                             "produtos": ";".join(sorted(set(produtos_de.get(u, []))))})
    _csv(s / "catalogo_fontes.csv", l_fontes, ["tipo", "identificador", "url", "ok", "status_http", "consultado_em", "sha256", "bytes", "arquivo_cache", "produtos"])
    l_docs, vistos = [], {}
    for (prod, chave), r in sorted(docs.items()):
        if r["resultado"] in ("LISTA_INDISPONIVEL",):
            l_indisp.append({"nivel": "2_contratacao", "tipo": "PNCP_LISTA_ARQUIVOS", "url": r["url_lista"], "status_http": r["lista_status_http"],
                             "erro": r["resultado"], "consultado_em": r["processado_em"], "produtos": r["id_candidato"]})
        for d in r["documentos"]:
            dup = vistos.get(d["sha256"]) if d["sha256"] else None
            if d["sha256"] and not dup:
                vistos[d["sha256"]] = d["url"]
            l_docs.append({"id_candidato": r["id_candidato"], "produto": prod, "numero_controle_pncp": chave, "tipo_documento": d["tipo"],
                           "titulo": d["titulo"], "url": d["url"], "data_publicacao": d["data_publicacao"], "status_http": d["status_http"],
                           "sha256": d["sha256"], "bytes": d["bytes"], "formato": d["formato"], "paginas": d["paginas"], "texto_extraido": int(bool(d["texto"])),
                           "ancoras_catmat": d["ancoras"], "duplicado_de": dup or "", "resultado_compra": r["resultado"]})
            if not d["sha256"] or not d["texto"]:
                l_indisp.append({"nivel": "2_contratacao", "tipo": f"PNCP_DOCUMENTO ({d['tipo']})", "url": d["url"], "status_http": d["status_http"],
                                 "erro": d.get("erro") or d.get("erro_extracao") or "sem texto extraível (PDF sem camada de texto?)",
                                 "consultado_em": r["processado_em"], "produtos": r["id_candidato"]})
    _csv(s / "documentos_localizados.csv", l_docs, ["id_candidato", "produto", "numero_controle_pncp", "tipo_documento", "titulo", "url",
                                                  "data_publicacao", "status_http", "sha256", "bytes", "formato", "paginas", "texto_extraido",
                                                  "ancoras_catmat", "duplicado_de", "resultado_compra"])
    _csv(s / "documentos_indisponiveis.csv", l_indisp, ["nivel", "tipo", "url", "status_http", "erro", "consultado_em", "produtos"])
    st = Counter(d["status"] for d in dec.values())
    est = {"etapa": "auto-validar", "concluido_em": comum.agora(), "versao_validador": VERSAO_VALIDADOR, "hash_config": ctx.hash_config(),
           "sha256_snapshot_catalogo": comum.sha256_arquivo(ctx.estado / "snapshot_catalogo.json"),
           "sha256_documentos": comum.sha256_arquivo(ctx.estado / "documentos.jsonl") if (ctx.estado / "documentos.jsonl").exists() else None,
           "status_familias": dict(sorted(st.items())), "status_itens": dict(sorted(cont.items())),
           "subprodutos": len(l_sub), "cesta_catalogo_S1": len(cesta), "itens_validados": len(validados), "linhas_gz": dict(n_gz),
           "saidas": {p.name: comum.sha256_arquivo(p) for p in sorted(s.glob("*.csv*"))}}
    comum.escrever_json(ctx.arq_estado("auto-validar"), est)
    reg.log(f"auto-validar: famílias {dict(st)}; itens {dict(cont)}")
    return est
