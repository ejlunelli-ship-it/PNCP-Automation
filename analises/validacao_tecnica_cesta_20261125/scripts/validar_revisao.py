"""Etapa concluir: lê os formulários efetivamente preenchidos, confere a integridade contra os arquivos-base e
emite o resultado. Falha de forma conservadora: na dúvida documental, não aprova.

Erros de integridade (arquivo-base alterado, ID duplicado/ausente/novo, campo imutável alterado, decisão inválida,
versão diferente) interrompem a conclusão sem gerar cesta. Falhas de documentação bloqueiam só o registro afetado.
"""
import datetime as dt
import json
import re
import shutil
from collections import defaultdict
from pathlib import Path

import comum
from auditar_homogeneidade import CHAVE_INVALIDA, CONFLITO, INSUFICIENTE
from comum import ErroEstrutural
from extrair_atributos import Extrator
from inspecionar_entradas import caminhos
from normalizar_especificacoes import chave_compacta, normalizar, sem_acentos
from preparar_revisao import COLS_REV_PROD, COLS_REV_VAR, EDIT_PROD, EDIT_VAR, IMUT_PROD, IMUT_VAR

VALIDADO, REJEITADO, DESMEMBRADO, PENDENTE, BLOQUEADO = "VALIDADO", "REJEITADO", "DESMEMBRADO", "PENDENTE", "BLOQUEADO"
RX_PNCP = re.compile(r"^\d{14}-\d-\d{1,6}/\d{4}$")
RX_URL = re.compile(r"^https?://[^\s/]+\.[^\s]+$", re.I)
RX_NORMA = re.compile(r"^(?:ABNT\s*)?(?:NBR|ISO|IEC|NR|RDC|ASTM|EN|IN|PORTARIA)\b[\w\-\.:/ ]*\d", re.I)
COLS_RESULTADO = ["id_registro", "tipo_registro", "id_candidato", "produto", "id_especificacao_atomica", "decisao_registrada",
                  "status_final", "n_variantes", "variantes_revisadas", "variantes_equivalentes", "motivos_bloqueio",
                  "pendencias", "revisor", "revisores_variantes", "data_revisao", "revisao_dupla", "versao_auditoria"]
COLS_CESTA = ["id_candidato", "produto", "catmat", "unidade_norm", "tipo_registro", "id_especificacao_atomica",
              "especificacao_canonica", "regras_equivalencia", "revisor_produto", "revisores_variantes", "data_revisao_produto",
              "datas_revisao_variantes", "fontes_documentais", "status_validacao", "versao_auditoria", "hash_registro", "rodada"]
COLS_CESTA_ORIGINAL = ["id_candidato", "produto", "catmat", "unidade_norm", "especificacao_canonica_aprovada", "atributos_essenciais",
                       "criterios_equivalencia", "criterios_exclusao", "revisor", "data_revisao", "justificativa",
                       "versao_regra_classificacao"]


# ------------------------------------------------------------------------------------------------ verificações de campo
def _limpo(s):
    return re.sub(r"[^A-Z0-9 ]", "", sem_acentos(s or "").upper()).strip()


def checar_fundamentacao(txt, par):
    t = (txt or "").strip()
    if not t:
        return "fundamentação ausente"
    if len(t) < par["fundamentacao_min_caracteres"]:
        return f"fundamentação curta (< {par['fundamentacao_min_caracteres']} caracteres)"
    if _limpo(t) in {_limpo(g) for g in par["frases_genericas"]}:
        return "fundamentação genérica"
    return None


def checar_fontes(txt, par, registro):
    """Devolve (fontes_validas, problemas). Fonte = TIPO:identificador; várias separadas por '|'."""
    t = (txt or "").strip()
    if not t:
        return [], ["fonte documental ausente"]
    tipos = {k: v for k, v in par["fontes"].items() if not k.startswith("_")}
    ok, prob = [], []
    for parte in [p.strip() for p in t.split("|") if p.strip()]:
        if ":" not in parte:
            prob.append(f"fonte sem tipo: '{parte}'")
            continue
        tipo, ident = (x.strip() for x in parte.split(":", 1))
        tipo = tipo.upper()
        regra = tipos.get(tipo)
        if regra is None:
            prob.append(f"tipo de fonte desconhecido: '{tipo}'")
            continue
        if regra == "numero_controle_pncp_ou_url":
            valido = bool(RX_PNCP.match(ident) or RX_URL.match(ident))
        elif regra == "codigo_catmat_do_produto":
            valido = ident == (registro.get("catmat") or "")
        elif regra == "codigo_pdm_do_produto":
            valido = bool(registro.get("pdm")) and ident == registro.get("pdm")
        elif regra == "norma_tecnica":
            valido = bool(RX_NORMA.match(ident))
        elif regra == "url":
            valido = bool(RX_URL.match(ident))
        else:
            valido = False
        (ok if valido else prob).append(f"{tipo}:{ident}" if valido else f"fonte não verificável: '{parte}'")
    if not ok and not prob:
        prob.append("fonte documental ausente")
    return ok, prob


def checar_revisor(rev, revisores, par):
    r = (rev or "").strip()
    if not r:
        return "revisor não identificado"
    if _limpo(r) in {_limpo(x) for x in par["revisores_proibidos"]}:
        return f"identificação de revisor inválida: '{r}'"
    if r not in revisores:
        return f"revisor '{r}' não consta do cadastro de revisores (config/revisores.csv)"
    return None


def checar_data(txt, data_preparacao, hoje=None):
    t = (txt or "").strip()
    if not t:
        return "data da revisão ausente"
    try:
        d = dt.date.fromisoformat(t)
    except ValueError:
        return f"data inválida: '{t}' (use AAAA-MM-DD)"
    if len(t) != 10:
        return f"data inválida: '{t}' (use AAAA-MM-DD)"
    hoje = hoje or dt.date.today()
    if d > hoje:
        return f"data no futuro: {t}"
    if d < dt.date.fromisoformat(data_preparacao):
        return f"data anterior à preparação da auditoria ({data_preparacao}): {t}"
    return None


def checar_especificacao(txt, consenso, extrator, ctx, par, minimo=None):
    """Formato 'NOME | ATRIBUTO: VALOR | ...'; exige os atributos essenciais (consenso das variantes)."""
    t = (txt or "").strip()
    if not t:
        return ["especificação canônica ausente"]
    partes = [p.strip() for p in t.split("|") if p.strip()]
    pares = [p for p in partes[1:] if ":" in p and all(x.strip() for x in p.split(":", 1))]
    prob = []
    minimo = minimo or par["especificacao_min_atributos"]
    if len(pares) < minimo:
        prob.append(f"especificação canônica com {len(pares)} atributo(s) 'ATRIBUTO: VALOR' (mínimo {minimo})")
    norm = normalizar(t.replace("|", ","))
    estrito = re.sub(r"[^A-Z0-9]", "", chave_compacta(norm))
    ext = extrator.extrair(norm, ctx)
    falta = []
    for a, v in sorted(consenso.items()):
        if a.startswith("declarado:"):
            if v and re.sub(r"[^A-Z0-9]", "", v) not in estrito:
                falta.append(f"{a}={v}")
        elif v not in ext.get(a, {}):
            falta.append(f"{a}={v}")
    if falta:
        prob.append("especificação canônica sem atributos essenciais: " + "; ".join(falta))
    return prob


# ------------------------------------------------------------------------------------------------ integridade
def _ler_form(caminho, colunas, chave):
    if not caminho.is_file():
        raise ErroEstrutural(f"formulário ausente: {caminho}")
    cab = comum.cabecalho_csv(caminho)
    if cab != colunas:
        raise ErroEstrutural(f"{caminho.name}: cabeçalho alterado (colunas adicionadas, removidas ou reordenadas)")
    linhas, vistos, dup = [], set(), []
    for r in comum.ler_csv(caminho):
        if r[chave] in vistos:
            dup.append(r[chave])
        vistos.add(r[chave])
        linhas.append(r)
    if dup:
        raise ErroEstrutural(f"{caminho.name}: identificadores duplicados {sorted(set(dup))[:5]}")
    return {r[chave]: r for r in linhas}


def conferir_integridade(pasta, man, cfg):
    erros = []
    for nome, h in man["hashes_base"].items():
        p = pasta / nome
        if not p.is_file() or comum.sha256_arquivo(p) != h:
            erros.append(f"arquivo-base alterado ou ausente após a preparação: {nome}")
    for k, e in man["entradas"].items():
        p = Path(e["caminho"])
        if not p.is_file() or comum.sha256_arquivo(p) != e["sha256"]:
            erros.append(f"entrada mudou depois da preparação ({k}): é preciso uma nova versão da auditoria")
    for nome, h in man["hashes_config"].items():
        if comum.sha256_arquivo(cfg["pasta_config"] / nome) != h:
            erros.append(f"configuração mudou depois da preparação ({nome}): é preciso uma nova versão da auditoria")
    if erros:
        raise ErroEstrutural("; ".join(erros))
    base_p = {r["id_registro"]: r for r in comum.ler_csv(pasta / "base_produtos.csv")}
    base_v = {r["id_variante"]: r for r in comum.ler_csv(pasta / "base_variantes.csv")}
    fp = _ler_form(pasta / "revisao_produtos.csv", COLS_REV_PROD, "id_registro")
    fv = _ler_form(pasta / "revisao_variantes.csv", COLS_REV_VAR, "id_variante")
    for nome, form, base in (("revisao_produtos.csv", fp, base_p), ("revisao_variantes.csv", fv, base_v)):
        falta, novos = sorted(set(base) - set(form)), sorted(set(form) - set(base))
        if falta or novos:
            raise ErroEstrutural(f"{nome}: registros-base ausentes {falta[:5]} ou novos {novos[:5]} (IDs alterados?)")
    for nome, form, base, imut in (("revisao_produtos.csv", fp, base_p, IMUT_PROD), ("revisao_variantes.csv", fv, base_v, IMUT_VAR)):
        alterados = []
        for k, r in form.items():
            for c in imut:
                esperado = man["versao_auditoria"] if c == "versao_auditoria" else base[k].get(c, "")
                if r[c] != esperado:
                    alterados.append(f"{k}.{c}")
        if alterados:
            raise ErroEstrutural(f"{nome}: campos não editáveis alterados: {alterados[:8]} (total {len(alterados)})")
    return base_p, base_v, fp, fv


# ------------------------------------------------------------------------------------------------ conclusão
def ler_revisores(caminho):
    p = Path(caminho)
    if not p.is_file():
        return {}
    return {r["id_revisor"].strip(): r for r in comum.ler_csv(p) if (r.get("id_revisor") or "").strip()}


def concluir(cfg, reg, pasta, exigir_dupla=False, hoje=None, revisores_csv=None):
    pasta = Path(pasta)
    par = cfg["parametros"]
    prev = par["revisao"]
    if not (pasta / "manifesto.json").is_file():
        raise ErroEstrutural(f"rodada não preparada: {pasta / 'manifesto.json'} não existe")
    man = comum.carregar_json(pasta / "manifesto.json")
    base_p, base_v, fp, fv = conferir_integridade(pasta, man, cfg)
    reg.log(f"integridade conferida: {len(fp)} registros de produto, {len(fv)} variantes")
    # decisões válidas (valor inválido = erro, não bloqueio silencioso)
    inval = [f"{k}: '{r['decisao_produto']}'" for k, r in fp.items()
             if (r["decisao_produto"] or "PENDENTE").strip() not in prev["decisoes_produto"]
             or (r["tipo_registro"] == "SUBPRODUTO" and r["decisao_produto"].strip() == "DESMEMBRAR")]
    inval += [f"{k}: '{r['decisao_variante']}'" for k, r in fv.items()
              if r["decisao_variante"].strip() and r["decisao_variante"].strip() not in prev["decisoes_variante"]]
    if inval:
        raise ErroEstrutural(f"decisões inválidas: {inval[:8]} (total {len(inval)})")
    revisores = ler_revisores(revisores_csv or comum.resolver(par["revisores"]))
    extrator = Extrator(cfg["regras"])
    data_prep = man["data_preparacao"]

    # variantes: documentação de cada decisão
    var_doc = {}
    for k, r in fv.items():
        d = r["decisao_variante"].strip()
        prob = []
        if d:
            for p in (checar_fundamentacao(r["fundamentacao"], prev), checar_revisor(r["revisor"], revisores, prev),
                      checar_data(r["data_revisao"], data_prep, hoje)):
                if p:
                    prob.append(p)
            _, pf = checar_fontes(r["fonte_evidencia"], prev, base_p.get(r["id_candidato"], {}))
            prob += pf
        var_doc[k] = {"decisao": d, "problemas": prob, "revisor": r["revisor"].strip(), "data": r["data_revisao"].strip()}
    vars_de = defaultdict(list)
    for k, b in base_v.items():
        vars_de[b["id_candidato"]].append(k)
        if b["id_especificacao_atomica"]:
            vars_de[b["id_especificacao_atomica"]].append(k)

    def avaliar(k):
        r, b = fp[k], base_p[k]
        d = (r["decisao_produto"] or "PENDENTE").strip()
        vs = sorted(vars_de[k])
        rev = [var_doc[v] for v in vs]
        revisadas = [x for x in rev if x["decisao"]]
        motivos, pend = [], []
        doc = [p for p in (checar_fundamentacao(r["fundamentacao"], prev), checar_revisor(r["revisor"], revisores, prev),
                           checar_data(r["data_revisao"], data_prep, hoje)) if p]
        sem = len(vs) - len(revisadas)
        if sem:
            pend.append(f"{sem} variante(s) sem revisão")
        if d == "PENDENTE":
            return PENDENTE, motivos, pend
        if d == "REJEITAR":
            return (REJEITADO, [], pend) if not doc else (PENDENTE, ["rejeição sem documentação: " + "; ".join(doc)], pend)
        if d == "DESMEMBRAR":
            if b["status_auditoria"] != CONFLITO or b["desmembravel"] != "1" or not b["subprodutos"]:
                motivos.append("desmembramento sem subprodutos reproduzíveis propostos pela auditoria (exige nova versão das regras)")
            motivos += doc
            return (DESMEMBRADO, [], pend) if not motivos else (BLOQUEADO, motivos, pend)
        # ---------------------------------------------------------------- APROVAR
        motivos += doc
        fontes, pf = checar_fontes(r["fonte_evidencia"], prev, b)
        motivos += pf
        consenso = comum_json(b["atributos_consenso"])
        ctx = {"medicamento": "medicamento" in b["requer_especialista"],
               "originalidade": any(x in b["requer_especialista"] for x in ("toner_cartucho", "peca_reposicao", "equipamento_eletronico"))}
        minimo = None
        if b["status_auditoria"] == INSUFICIENTE:
            minimo = max(2, prev["especificacao_min_atributos"])
            if not any(f.split(":")[0] in ("TERMO_REFERENCIA", "EDITAL", "DOCUMENTO_COMPRA", "NORMA", "FABRICANTE", "CATALOGO") for f in fontes):
                motivos.append("atributos insuficientes na descrição: exige fonte além do CATMAT/PDM (edital, termo de referência, norma, fabricante)")
        motivos += checar_especificacao(r["especificacao_canonica"], consenso, extrator, ctx, prev, minimo)
        if b["status_auditoria"] == CHAVE_INVALIDA:
            motivos.append("CATMAT ou unidade ausente")
        if b["tipo_registro"] == "PRODUTO" and b["status_auditoria"] == CONFLITO:
            motivos.append("conflito objetivo não resolvido: a família não pode ser aprovada como especificação única (use DESMEMBRAR)")
        if b["tipo_registro"] == "SUBPRODUTO":
            pai = fp.get(b["id_candidato"])
            if not pai or (pai["decisao_produto"] or "").strip() != "DESMEMBRAR":
                motivos.append("subproduto sem decisão DESMEMBRAR documentada no produto de origem")
        if (b["alertas"] or b["requer_especialista"] or b["consulta_edital"]) and \
                len((r["resolucao_alertas"] or "").strip()) < prev["fundamentacao_min_caracteres"]:
            motivos.append("alertas, riscos ou consulta a edital sem resolução documentada")
        if b["consulta_edital"] and not any(f.split(":")[0] in ("TERMO_REFERENCIA", "EDITAL", "DOCUMENTO_COMPRA") for f in fontes):
            motivos.append("consulta a edital indicada pela auditoria sem edital/termo de referência/documento de compra entre as fontes")
        if not vs:
            motivos.append("nenhuma variante associada")
        if sem:
            motivos.append(f"{sem} variante(s) sem revisão")
        nao_eq = [x for x in revisadas if x["decisao"] != "EQUIVALENTE"]
        if nao_eq:
            motivos.append(f"{sum(1 for x in nao_eq if x['decisao'] == 'DIVERGENTE')} variante(s) DIVERGENTE e "
                           f"{sum(1 for x in nao_eq if x['decisao'] == 'INDETERMINADA')} INDETERMINADA")
        mal = [v for v, x in zip(vs, rev) if x["decisao"] and x["problemas"]]
        if mal:
            motivos.append(f"{len(mal)} decisão(ões) de variante sem fundamentação, fonte, revisor ou data válidos")
        if exigir_dupla:
            rv = {x["revisor"] for x in revisadas}
            if r["revisor"].strip() and r["revisor"].strip() in rv:
                motivos.append("dupla revisão exigida: o aprovador final também decidiu variantes")
        return (VALIDADO, [], pend) if not motivos else (BLOQUEADO, motivos, pend)

    # produtos primeiro (o subproduto depende da decisão do produto de origem)
    ordem = sorted(fp, key=lambda k: (fp[k]["tipo_registro"] != "PRODUTO", k))
    res, status = [], {}
    for k in ordem:
        st, mot, pend = avaliar(k)
        if fp[k]["tipo_registro"] == "SUBPRODUTO" and st == VALIDADO and status.get(fp[k]["id_candidato"]) != DESMEMBRADO:
            st, mot = BLOQUEADO, ["produto de origem não está DESMEMBRADO"]
        status[k] = st
        vs = sorted(vars_de[k])
        rv = sorted({var_doc[v]["revisor"] for v in vs if var_doc[v]["decisao"] and var_doc[v]["revisor"]})
        rp = fp[k]["revisor"].strip()
        res.append({"id_registro": k, "tipo_registro": fp[k]["tipo_registro"], "id_candidato": fp[k]["id_candidato"],
                    "produto": fp[k]["produto"], "id_especificacao_atomica": fp[k]["id_especificacao_atomica"],
                    "decisao_registrada": (fp[k]["decisao_produto"] or "PENDENTE").strip(), "status_final": st,
                    "n_variantes": len(vs), "variantes_revisadas": sum(1 for v in vs if var_doc[v]["decisao"]),
                    "variantes_equivalentes": sum(1 for v in vs if var_doc[v]["decisao"] == "EQUIVALENTE"),
                    "motivos_bloqueio": " | ".join(mot), "pendencias": " | ".join(pend), "revisor": rp,
                    "revisores_variantes": ";".join(rv), "data_revisao": fp[k]["data_revisao"].strip(),
                    "revisao_dupla": int(bool(rp) and bool(rv) and rp not in rv), "versao_auditoria": man["versao_auditoria"]})
    pos = {k: i for i, k in enumerate(base_p)}
    res.sort(key=lambda x: pos[x["id_registro"]])
    comum.escrever_csv(pasta / "resultado_revisao.csv", res, COLS_RESULTADO)

    validos = [x for x in res if x["status_final"] == VALIDADO]
    cesta = pasta / "cesta_validada.csv"
    hist = pasta / "historico"
    if cesta.exists():
        hist.mkdir(exist_ok=True)
        shutil.move(str(cesta), hist / f"cesta_validada_{dt.datetime.now():%Y%m%d_%H%M%S}.csv")
    linhas_cesta = []
    for x in validos:
        k = x["id_registro"]
        r, b = fp[k], base_p[k]
        vs = sorted(vars_de[k])
        linhas_cesta.append({
            "id_candidato": b["id_candidato"], "produto": b["produto"], "catmat": b["catmat"], "unidade_norm": b["unidade_norm"],
            "tipo_registro": b["tipo_registro"], "id_especificacao_atomica": b["id_especificacao_atomica"],
            "especificacao_canonica": r["especificacao_canonica"].strip(),
            "regras_equivalencia": "variantes EQUIVALENTE: " + "; ".join(f"{v} «{base_v[v]['descricao_normalizada']}»" for v in vs),
            "revisor_produto": r["revisor"].strip(), "revisores_variantes": x["revisores_variantes"],
            "data_revisao_produto": r["data_revisao"].strip(),
            "datas_revisao_variantes": ";".join(sorted({var_doc[v]["data"] for v in vs})),
            "fontes_documentais": " | ".join(sorted({r["fonte_evidencia"].strip()} | {fv[v]["fonte_evidencia"].strip() for v in vs})),
            "status_validacao": VALIDADO, "versao_auditoria": man["versao_auditoria"], "hash_registro": b["hash_registro"],
            "rodada": man["rodada"]})
    if linhas_cesta:
        comum.escrever_csv(cesta, linhas_cesta, COLS_CESTA)
        integrar_econometria(cfg, pasta, linhas_cesta, man)
    cont = defaultdict(int)
    for x in res:
        cont[(x["tipo_registro"], x["status_final"])] += 1
    prods = [x for x in res if x["tipo_registro"] == "PRODUTO"]
    out = {
        "rodada": man["rodada"], "versao_auditoria": man["versao_auditoria"], "concluido_em": comum.agora(),
        "versao_codigo": comum.VERSAO, "exigir_dupla_revisao": bool(exigir_dupla),
        "candidatos_examinados": len(prods),
        "produtos_aprovados": sum(1 for x in prods if x["status_final"] == VALIDADO),
        "subprodutos_aprovados": cont[("SUBPRODUTO", VALIDADO)],
        "produtos_rejeitados": sum(1 for x in prods if x["status_final"] == REJEITADO),
        "produtos_pendentes": sum(1 for x in prods if x["status_final"] == PENDENTE),
        "produtos_bloqueados": sum(1 for x in prods if x["status_final"] == BLOQUEADO),
        "produtos_desmembrados": sum(1 for x in prods if x["status_final"] == DESMEMBRADO),
        "produtos_que_exigem_desmembramento": sum(1 for b in base_p.values() if b["tipo_registro"] == "PRODUTO" and b["status_auditoria"] == CONFLITO),
        "variantes_avaliadas": sum(1 for x in var_doc.values() if x["decisao"]), "variantes_total": len(var_doc),
        "conflitos_objetivos": sum(int(b["n_conflitos_objetivos"] or 0) for b in base_p.values() if b["tipo_registro"] == "PRODUTO"),
        "produtos_com_revisao_dupla": sum(1 for x in prods if x["revisao_dupla"]),
        "revisores_cadastrados": len(revisores),
        "hashes_formularios": {n: comum.sha256_arquivo(pasta / n) for n in ("revisao_produtos.csv", "revisao_variantes.csv")},
        "hashes_formularios_iniciais": man["hashes_formularios_iniciais"],
        "formularios_alterados_desde_a_preparacao": {n: comum.sha256_arquivo(pasta / n) != h for n, h in man["hashes_formularios_iniciais"].items()},
        "cesta_validada": str(cesta) if linhas_cesta else None,
        "aviso": None if linhas_cesta else "nenhum registro VALIDADO: cesta_validada.csv NÃO foi criada",
    }
    comum.escrever_json(pasta / "resultado_validacao.json", out)
    reg.log(f"conclusão: {out['produtos_aprovados']} aprovados, {out['produtos_pendentes']} pendentes, "
            f"{out['produtos_bloqueados']} bloqueados; cesta_validada.csv {'criada' if linhas_cesta else 'NÃO criada'}")
    return out


def comum_json(txt):
    return json.loads(txt) if txt else {}


def integrar_econometria(cfg, pasta, linhas, man):
    """Pasta compatível com o estudo econométrico (sem alterá-lo): cópia dos arquivos congelados da cesta + uma
    cesta_validada.csv no formato original, só com produtos INTEIROS validados (subprodutos exigem ligação item ×
    especificação atômica, gravada à parte)."""
    cam = caminhos(cfg)
    dest = pasta / "integracao_econometria" / "saidas"
    dest.mkdir(parents=True, exist_ok=True)
    origem = {"cesta_candidata.csv": cam["cesta_candidata"], "congelamento_cesta.json": cam["congelamento"],
              "formulario_revisao.csv": cam["formulario_original"], "sensibilidade_pertinencia.csv": cam["pertinencia"],
              "recorrencia_temporal.csv": cam["cesta_candidata"].parent / "recorrencia_temporal.csv"}
    faltam = []
    for n, src in origem.items():
        if Path(src).is_file():
            shutil.copy2(src, dest / n)
        else:
            faltam.append(n)
    (pasta / "integracao_econometria" / "LEIA-ME.txt").write_text(
        "Cópia dos arquivos congelados da cesta + cesta_validada.csv no formato original (só produtos INTEIROS validados).\n"
        "Para reexecutar o estudo econométrico sem alterá-lo, use um config.json com caminhos.cesta_pasta apontando para\n"
        f"{pasta / 'integracao_econometria'}\n"
        "Subprodutos (especificações atômicas) exigem adaptar a ligação item × especificação: ver ligacao_itens_especificacoes.csv.\n"
        + (f"Arquivos ausentes na origem: {faltam}\n" if faltam else ""), encoding="utf-8")
    inteiros = [x for x in linhas if x["tipo_registro"] == "PRODUTO"]
    comum.escrever_csv(dest / "cesta_validada.csv", [{
        "id_candidato": x["id_candidato"], "produto": x["produto"], "catmat": x["catmat"], "unidade_norm": x["unidade_norm"],
        "especificacao_canonica_aprovada": x["especificacao_canonica"], "atributos_essenciais": "",
        "criterios_equivalencia": x["regras_equivalencia"], "criterios_exclusao": "variantes não listadas",
        "revisor": x["revisor_produto"], "data_revisao": x["data_revisao_produto"], "justificativa": x["fontes_documentais"],
        "versao_regra_classificacao": man["versao_auditoria"]} for x in inteiros], COLS_CESTA_ORIGINAL)
    subs = [x for x in linhas if x["tipo_registro"] == "SUBPRODUTO"]
    if subs:
        # ligação item × especificação atômica (desc_id de cada variante equivalente)
        desc = defaultdict(set)
        for o in comum.ler_csv(pasta / "descricoes_originais.csv"):
            desc[o["id_variante"]].add((o["produto"], int(o["desc_id"])))
        base_v = {r["id_variante"]: r for r in comum.ler_csv(pasta / "base_variantes.csv")}
        alvo = [(p, d, x["id_especificacao_atomica"]) for x in subs for v, b in base_v.items()
                if b["id_especificacao_atomica"] == x["id_especificacao_atomica"] for p, d in desc[v]]
        con = comum.conectar_ro(cam["banco_cesta"])
        try:
            linhas_lig = []
            for p, d, e in alvo:
                for chave, item in con.execute("SELECT chave, numero_item FROM universo_produto WHERE produto = ? AND COALESCE(desc_id, 0) = ?", (p, d)):
                    linhas_lig.append({"numero_controle_pncp": chave, "numero_item": item, "produto": p, "id_especificacao_atomica": e})
        finally:
            con.close()
        comum.escrever_csv(pasta / "integracao_econometria" / "ligacao_itens_especificacoes.csv", linhas_lig,
                           ["numero_controle_pncp", "numero_item", "produto", "id_especificacao_atomica"])
