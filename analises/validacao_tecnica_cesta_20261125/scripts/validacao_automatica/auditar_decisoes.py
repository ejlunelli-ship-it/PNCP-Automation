"""Etapa auto-auditar: integridade (fontes, base, bancos, histórico), auditoria das decisões, diagnósticos de
cobertura (sem preços nem modos), integração separada para o estudo econométrico, manifesto e relatório."""
import csv
import gzip
import json
import platform
import shutil
import sqlite3
import sys
import uuid
from collections import Counter, defaultdict
from pathlib import Path

import comum
from comum import ErroEstrutural

from . import (AUTO_DESMEMBRAR, AUTO_DIVERGENTE, AUTO_ERRO_DADOS, AUTO_INCONCLUSIVO, AUTO_VALIDADO_CATALOGO,
               AUTO_VALIDADO_CATALOGO_RESSALVA, VERSAO_VALIDADOR)
from .pipeline import carregar_documentos, snapshot_entradas


def _ler(p):
    p = Path(p)
    op = gzip.open if p.suffix == ".gz" else open
    with op(p, "rt", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _n(x):
    return f"{int(x):,}".replace(",", ".")


def _pct(a, b):
    return (f"{100 * a / b:.1f}%".replace(".", ",")) if b else "—"


def _tab(cab, linhas):
    out = ["| " + " | ".join(cab) + " |", "|" + "|".join("---" for _ in cab) + "|"]
    out += ["| " + " | ".join(str(c).replace("|", "/") for c in l) + " |" for l in linhas]
    return "\n".join(out)


def integridade(ctx):
    """Verificações que interrompem: base P1, fontes do snapshot, bancos, formulários e cestas históricas."""
    r = {}
    man = comum.carregar_json(ctx.origem / "manifesto.json")
    r["base_P1_intacta"] = all(comum.sha256_arquivo(ctx.origem / k) == h for k, h in man["hashes_base"].items())
    r["formularios_humanos_intocados"] = {}
    for rod in ("piloto_P1_100", "P1"):
        p = ctx.origem.parent / rod
        if (p / "manifesto.json").exists():
            m = comum.carregar_json(p / "manifesto.json")
            r["formularios_humanos_intocados"][rod] = all(comum.sha256_arquivo(p / k) == h for k, h in m["hashes_formularios_iniciais"].items())
    snap = snapshot_entradas(ctx)
    ruins = []
    for u, e in snap.items():
        if e.get("ok"):
            arq = ctx.cache.pasta / e["arquivo"]
            if not arq.exists() or comum.sha256_arquivo(arq) != e["sha256"]:
                ruins.append(u)
    r["fontes_catalogo_integras"] = not ruins
    r["fontes_catalogo_corrompidas"] = ruins[:20]
    prep = comum.carregar_json(ctx.arq_estado("auto-preparar"))
    agora = comum.impressao_digital(ctx.banco)
    r["banco_cesta_inalterado"] = all(prep["banco_cesta"]["antes"].get(k) == agora.get(k)
                                      for k in ("tamanho_bytes", "mtime_ns", "sqlite_contador_alteracoes", "sha256_inicio_fim"))
    cv = ctx.cfg["parametros"]["entradas"].get("cesta_validada_original")
    if cv:
        p = comum.resolver(cv)
        r["cesta_validada_original_linhas"] = sum(1 for _ in comum.ler_csv(p)) if p.exists() else None
    r["cesta_validada_humana_nao_criada_pelo_modo_automatico"] = not (ctx.saida / "cesta_validada.csv").exists()
    falhas = [k for k, v in r.items() if v is False or (isinstance(v, dict) and not all(v.values()))]
    if falhas:
        raise ErroEstrutural(f"auditoria de integridade falhou: {falhas}")
    return r


def cobertura(ctx, sens):
    """Cobertura por conjunto (S1, S2, S4, S3) — produtos, compras, itens, UASGs — e por classe, ano, trimestre, UF."""
    con = sqlite3.connect(ctx.estado / "itens.db")
    base = {p["produto"]: p for p in comum.ler_csv(ctx.origem / "base_produtos.csv") if p["tipo_registro"] == "PRODUTO"}
    subs = _ler(ctx.saida / "subprodutos_identificados.csv")
    desm = {x["produto"] for x in subs}
    # nível por item: família inteira S1/S2, ou (famílias desmembradas) só as variantes do subproduto S1/S2
    con.execute("CREATE TEMP TABLE g (produto TEXT PRIMARY KEY, s1 INT, s2 INT, classe TEXT, desm INT)")
    con.executemany("INSERT INTO g VALUES (?,?,?,?,?)", [(x["produto"], int(x["S1_alta_seguranca"]), int(x["S2_seguranca_intermediaria"]),
                                                         base[x["produto"]]["classe_catalogo"], int(x["produto"] in desm)) for x in sens])
    con.execute("CREATE TEMP TABLE dv (produto TEXT, desc_id INT, nivel TEXT, PRIMARY KEY (produto, desc_id))")
    var_nivel = {}
    for x in subs:
        for v in x["variantes"].split(";"):
            var_nivel[v] = x["nivel"]
    con.executemany("INSERT OR IGNORE INTO dv VALUES (?,?,?)", [(o["produto"], int(o["desc_id"]), var_nivel[o["id_variante"]])
                                                              for o in comum.ler_csv(ctx.origem / "descricoes_originais.csv")
                                                              if o["id_variante"] in var_nivel])
    con.execute("CREATE TEMP TABLE n AS SELECT i.rowid AS rid, CASE WHEN g.desm = 0 THEN (CASE WHEN g.s1 = 1 THEN 'S1' WHEN g.s2 = 1 THEN 'S2' ELSE '' END) "
                "ELSE COALESCE((SELECT dv.nivel FROM dv WHERE dv.produto = i.produto AND dv.desc_id = COALESCE(i.desc_id, 0)), '') END AS nivel "
                "FROM itens i JOIN g ON g.produto = i.produto")
    con.execute("CREATE INDEX ix_n ON n (rid)")
    val = _ler(ctx.saida / "itens_validados_automaticamente.csv")
    con.execute("CREATE TEMP TABLE v (chave TEXT, numero_item INT, PRIMARY KEY (chave, numero_item))")
    con.executemany("INSERT OR IGNORE INTO v VALUES (?,?)", [(x["numero_controle_pncp"], int(x["numero_item"])) for x in val])
    tot = {}
    defs = {"S3_candidato_P1": "1=1", "S1_catalogo_alta_seguranca": "n.nivel = 'S1'", "S2_catalogo_intermediaria": "n.nivel = 'S2'",
            "S4_itens_verificados": "EXISTS (SELECT 1 FROM v WHERE v.chave = i.chave AND v.numero_item = i.numero_item)"}
    for nome, cond in defs.items():
        r = con.execute(f"SELECT COUNT(DISTINCT i.produto), COUNT(DISTINCT i.chave), COUNT(*), COUNT(DISTINCT i.uasg) "
                        f"FROM itens i JOIN g ON g.produto = i.produto JOIN n ON n.rid = i.rowid WHERE {cond}").fetchone()
        tot[nome] = {"produtos": r[0], "compras": r[1], "itens": r[2], "uasgs": r[3]}
    dims = {}
    for nome, expr in (("classe_catalogo", "g.classe"), ("ano", "i.ano"), ("trimestre", "i.trimestre"), ("uf", "COALESCE(i.uf, '(sem UF)')")):
        linhas = []
        for k, it, it1, it4, co, co1 in con.execute(
                f"SELECT {expr}, COUNT(*), SUM(n.nivel = 'S1'), SUM(EXISTS (SELECT 1 FROM v WHERE v.chave = i.chave AND v.numero_item = i.numero_item)), "
                f"COUNT(DISTINCT i.chave), COUNT(DISTINCT CASE WHEN n.nivel = 'S1' THEN i.chave END) FROM itens i JOIN g ON g.produto = i.produto "
                f"JOIN n ON n.rid = i.rowid "
                f"GROUP BY 1 ORDER BY 1"):
            linhas.append({nome: k, "itens_P1": it, "itens_S1": it1 or 0, "itens_S4": it4 or 0, "compras_P1": co, "compras_S1": co1 or 0,
                           "pct_itens_S1": round(100 * (it1 or 0) / it, 2) if it else 0})
        dims[nome] = linhas
        comum.escrever_csv(ctx.saida / f"cobertura_por_{nome}.csv", linhas, list(linhas[0].keys()) if linhas else [nome])
    con.close()
    return tot, dims


def integrar(ctx, man_origem):
    """Integração SEPARADA (`integracao_econometria_automatica/`): congela a cesta automática com os identificadores
    originais. Não cria `cesta_validada.csv` (o leitor atual do estudo exige revisão humana e deve ser adaptado por
    configuração própria; esta pasta não passa produtos automáticos por esse requisito)."""
    dest = ctx.saida / "integracao_econometria_automatica"
    dest.mkdir(exist_ok=True)
    arqs = ["cesta_catalogo_validada_automaticamente.csv", "itens_validados_automaticamente.csv", "subprodutos_identificados.csv",
            "resultados_sensibilidade.csv"]
    for a in arqs:
        shutil.copy2(ctx.saida / a, dest / a)
    mapa = []
    for x in _ler(ctx.saida / "comparacao_variantes.csv"):
        if x["id_subproduto"]:
            mapa.append({"id_candidato": x["id_candidato"], "produto": x["produto"], "id_variante": x["id_variante"], "id_subproduto": x["id_subproduto"]})
    comum.escrever_csv(dest / "mapa_variante_subproduto.csv", mapa, ["id_candidato", "produto", "id_variante", "id_subproduto"])
    m = {"criado_em": comum.agora(), "modalidade": "VALIDACAO_AUTOMATICA", "nao_e_revisao_humana": True,
         "versao_validador": VERSAO_VALIDADOR, "versao_regras": ctx.auto["versao_regras_automaticas"],
         "versao_auditoria_origem": man_origem["versao_auditoria"], "chave": "produto (catmat|unidade_norm, com #hash nos subtipos da cesta) e id_candidato",
         "niveis": {"cesta_catalogo_validada_automaticamente.csv": "AUTO_VALIDADO_CATALOGO (S1): homogeneidade de catálogo; NÃO comprova cada contratação",
                    "itens_validados_automaticamente.csv": "AUTO_VALIDADO_ITEM (S4): compatibilidade demonstrada pelo documento da própria contratação"},
         "subprodutos": "itens ligados ao subproduto pela própria descrição (desc_id → id_variante → id_subproduto); ver mapa_variante_subproduto.csv",
         "uso_no_estudo": ("o estudo econométrico precisa de configuração PRÓPRIA para esta modalidade (ex.: 'modalidade_validacao': "
                           "'automatica_catalogo' ou 'automatica_item'); o leitor atual (cesta_validada.csv com revisão humana) não deve "
                           "aceitar estes arquivos sem essa mudança explícita. Nenhuma regressão foi executada nesta tarefa."),
         "analise_anterior": "permanece exploratória; não se torna confirmatória retroativamente",
         "hashes": {a: comum.sha256_arquivo(dest / a) for a in arqs + ["mapa_variante_subproduto.csv"]}}
    comum.escrever_json(dest / "manifesto_integracao.json", m)
    return m


CATEGORIAS_143 = {
    "SEM_DESCRICAO": "descrição ausente",
    "espacamento": "palavra concatenada / espaçamento (resolvida pelo texto oficial)",
    "numero_quebrado": "número quebrado por quebra de linha (correção tipográfica, S2)",
    "CONFORME_ATRIBUTOS": "divergência lexical sem diferença material (todos os valores oficiais presentes)",
    "PARCIAL": "atributo ausente na variante",
    "DIVERGENTE": "potencial conflito técnico (diverge do catálogo oficial)",
    "DIVERGENCIA_TEXTUAL": "divergência textual de atributo não demonstrada como equivalente",
    "SEM_FONTE": "fonte documental insuficiente (catálogo sem características ou indisponível)",
}


def analise_pendencias(ctx):
    """Os 143 produtos 'DIVERGENCIA_A_EXAMINAR' da auditoria 1.2.0: tipo de problema por variante, à luz do catálogo
    oficial. 'Falha de extração' = a auditoria apontou divergência entre variantes, mas todas são o texto oficial."""
    base = {p["id_candidato"]: p for p in comum.ler_csv(ctx.origem / "base_produtos.csv") if p["tipo_registro"] == "PRODUTO"}
    alvo = {k for k, p in base.items() if p["status_auditoria"] == "DIVERGENCIA_A_EXAMINAR"}
    comp = defaultdict(list)
    for c in _ler(ctx.saida / "comparacao_variantes.csv"):
        if c["id_candidato"] in alvo:
            comp[c["id_candidato"]].append(c)
    st = {a["id_candidato"]: a["status_automatico"] for a in _ler(ctx.saida / "auditoria_decisoes.csv") if a["tipo_registro"] == "PRODUTO"}
    linhas, cont = [], Counter()
    for k in sorted(alvo):
        cats = set()
        for c in comp[k]:
            s = c["status_variante"]
            if s.startswith("NAO_COMPARADA"):
                cats.add("SEM_FONTE")
            elif s == "CONFORME_TEXTO_OFICIAL":
                cats.add("espacamento" if c["tipo_igualdade_texto_oficial"] == "espacamento" else "identico")
            elif s == "CONFORME_COM_CORRECAO_TIPOGRAFICA":
                cats.add("numero_quebrado")
            else:
                cats.add(s)
        conformes = all(c["status_variante"] in ("CONFORME_TEXTO_OFICIAL", "CONFORME_COM_CORRECAO_TIPOGRAFICA", "CONFORME_ATRIBUTOS", "SEM_DESCRICAO")
                        for c in comp[k])
        if conformes and base[k]["conflitos"]:
            cats.add("FALHA_EXTRACAO")
        cats.discard("identico")
        for x in cats:
            cont[x] += 1
        linhas.append({"id_candidato": k, "produto": base[k]["produto"], "alertas_auditoria": base[k]["alertas"],
                       "divergencias_auditoria": base[k]["conflitos"], "problemas": ";".join(sorted(cats)),
                       "status_automatico": st.get(k, "")})
    comum.escrever_csv(ctx.saida / "pendencias_143_classificadas.csv", linhas,
                       ["id_candidato", "produto", "alertas_auditoria", "divergencias_auditoria", "problemas", "status_automatico"])
    return len(alvo), cont, Counter(l["status_automatico"] for l in linhas)


def caso(ctx, id_candidato):
    """Evidências de um caso específico (CP1860): catálogo oficial, variantes, itens por descrição, decisão."""
    esp = next((e for e in _ler(ctx.saida / "especificacoes_canonicas.csv") if e["id_candidato"] == id_candidato), None)
    if not esp:
        return None
    comp = [c for c in _ler(ctx.saida / "comparacao_variantes.csv") if c["id_candidato"] == id_candidato]
    aud = [a for a in _ler(ctx.saida / "auditoria_decisoes.csv") if a["id_candidato"] == id_candidato]
    origs = [o for o in comum.ler_csv(ctx.origem / "descricoes_originais.csv") if o["id_candidato"] == id_candidato]
    return {"esp": esp, "comp": comp, "aud": aud, "origs": origs}


def auditar(ctx, reg, testes=None):
    integ = integridade(ctx)
    reg.log("integridade conferida")
    man_o = comum.carregar_json(ctx.origem / "manifesto.json")
    sens = _ler(ctx.saida / "resultados_sensibilidade.csv")
    aud = _ler(ctx.saida / "auditoria_decisoes.csv")
    if len({a["id_registro"] for a in aud}) != len(aud):
        raise ErroEstrutural("auditoria_decisoes: registro duplicado")
    P = [a for a in aud if a["tipo_registro"] == "PRODUTO"]
    if len(P) != int(man_o["contagens"]["produtos"]):
        raise ErroEstrutural("nem todos os produtos P1 receberam classificação automática")
    comp = _ler(ctx.saida / "comparacao_variantes.csv")
    if len(comp) != int(man_o["contagens"]["variantes_normalizadas"]):
        raise ErroEstrutural("nem todas as variantes foram processadas")
    tot, dims = cobertura(ctx, sens)
    pend = analise_pendencias(ctx)
    cp = caso(ctx, "CP1860")
    integ_m = integrar(ctx, man_o)
    est_v = comum.carregar_json(ctx.arq_estado("auto-validar"))
    est_d = comum.carregar_json(ctx.arq_estado("auto-documentos"))
    docs = _ler(ctx.saida / "documentos_localizados.csv")
    indisp = _ler(ctx.saida / "documentos_indisponiveis.csv")
    fontes = _ler(ctx.saida / "catalogo_fontes.csv")
    subs = _ler(ctx.saida / "subprodutos_identificados.csv")
    st = Counter(a["status_automatico"] for a in P)
    motivos = Counter()
    for a in P:
        if a["status_automatico"] in (AUTO_INCONCLUSIVO, AUTO_ERRO_DADOS):
            for m in [x for x in a["motivos"].split(" | ") if x]:
                motivos[m.split(":")[0][:90]] += 1
    ress = Counter()
    for a in P:
        if a["status_automatico"] == AUTO_VALIDADO_CATALOGO_RESSALVA:
            for m in [x for x in a["ressalvas"].split(" | ") if x]:
                ress[m.split(":")[0][:90]] += 1
    st_var = Counter(c["status_variante"] for c in comp)
    res_compras = Counter(r["resultado"] for r in carregar_documentos(ctx).values())
    execucao = str(uuid.uuid5(uuid.NAMESPACE_URL, json.dumps([est_v["saidas"], est_v["sha256_snapshot_catalogo"]], sort_keys=True)))
    import pymupdf
    manifesto = {
        "id_execucao": execucao, "gerado_em": comum.agora(), "modalidade": "VALIDACAO_AUTOMATICA (não é revisão humana)",
        "versao_validador": VERSAO_VALIDADOR, "versao_regras_automaticas": ctx.auto["versao_regras_automaticas"],
        "versoes_regras_extracao": man_o["versoes"], "versao_auditoria_origem": man_o["versao_auditoria"],
        "hashes_base_origem": man_o["hashes_base"], "hash_cesta_original": man_o["entradas"]["cesta_candidata"]["sha256"],
        "hash_variantes": man_o["hashes_base"]["base_variantes.csv"], "hash_config_automatica": ctx.hash_config(),
        "hashes_config_regras": {n: comum.sha256_arquivo(ctx.cfg["pasta_config"] / n) for n in ("regras_atributos.json", "mapa_colunas.json", "parametros.json")},
        "hash_snapshot_catalogo": est_v["sha256_snapshot_catalogo"], "hash_documentos_contratacao": est_v["sha256_documentos"],
        "consulta_documental": {"inicio": min((f["consultado_em"] for f in fontes if f["consultado_em"]), default=None),
                                "fim": max((f["consultado_em"] for f in fontes if f["consultado_em"]), default=None)},
        "bibliotecas": {"python": sys.version.split()[0], "sqlite": sqlite3.sqlite_version, "pymupdf": pymupdf.VersionBind, "plataforma": platform.platform()},
        "modelo_de_linguagem": "nenhum (extração só por regras determinísticas)",
        "contagens": {"candidatos_examinados": len(P), "variantes_processadas": len(comp), "status_familias": dict(sorted(st.items())),
                      "subprodutos": len(subs), "itens": est_v["status_itens"], "itens_validados_individualmente": est_v["itens_validados"],
                      "fontes_catalogo_consultadas": len(fontes), "fontes_catalogo_ok": sum(1 for f in fontes if f["ok"] == "1"),
                      "documentos_contratacao_localizados": len(docs), "documentos_com_texto": sum(1 for d in docs if d["texto_extraido"] == "1"),
                      "registros_indisponiveis": len(indisp), "atributos_extraidos": sum(1 for _ in comum.ler_csv(ctx.saida / "atributos_extraidos.csv")),
                      "compras_amostra_documental": est_d["compras_amostra"], "resultado_compras_amostra": dict(sorted(res_compras.items()))},
        "cobertura": tot, "integridade": integ, "integracao": integ_m["hashes"], "testes": testes,
        "colunas_lidas": comum.carregar_json(ctx.saida / "colunas_lidas.json"),
        "saidas": {p.name: comum.sha256_arquivo(p) for p in sorted(ctx.saida.glob("*.csv*"))},
    }
    comum.escrever_json(ctx.saida / "manifesto.json", manifesto)
    manifesto["pendencias_143"] = {"produtos": pend[0], "problemas": dict(pend[1]), "status": dict(pend[2])}
    comum.escrever_json(ctx.saida / "manifesto.json", manifesto)
    relatorio(ctx, manifesto, st, motivos, ress, st_var, res_compras, dims, docs, indisp, subs, testes, pend, cp)
    reg.log(f"auto-auditar: manifesto e relatório gravados em {ctx.saida}")
    comum.escrever_json(ctx.arq_estado("auto-auditar"), {"etapa": "auto-auditar", "concluido_em": comum.agora(), "id_execucao": execucao,
                                                         "sha256_manifesto": comum.sha256_arquivo(ctx.saida / "manifesto.json")})
    return manifesto


def relatorio(ctx, m, st, motivos, ress, st_var, res_compras, dims, docs, indisp, subs, testes, pend=None, cp=None):
    c = m["contagens"]
    n = c["candidatos_examinados"]
    tot = m["cobertura"]
    L = ["# Validação técnica automática — cesta P1\n",
         f"Gerado em {m['gerado_em']} (execução `{m['id_execucao']}`), validador {m['versao_validador']}, regras automáticas "
         f"{m['versao_regras_automaticas']}, sobre a auditoria congelada `{m['versao_auditoria_origem']}`. **Modalidade automática: "
         "não é revisão humana**; nenhum formulário de revisor foi preenchido e nenhuma assinatura foi criada.\n",
         "> Aprovação só quando a equivalência técnica é demonstrável por atributos objetivos e evidência verificável "
         "(catálogo oficial CATMAT). A ausência de conflito, sozinha, não aprova nada. AUTO_VALIDADO_CATALOGO valida a "
         "família de catálogo, **não** cada contratação; itens só são AUTO_VALIDADO_ITEM com documento da própria compra.\n",
         "## Resultados gerais\n",
         _tab(["Status automático da família", "Produtos", "%"], [[k, _n(v), _pct(v, n)] for k, v in sorted(st.items(), key=lambda kv: -kv[1])]),
         "\n" + _tab(["Conjunto", "Produtos", "Compras", "Itens", "UASGs"], [[k, _n(v["produtos"]), _n(v["compras"]), _n(v["itens"]), _n(v["uasgs"])] for k, v in tot.items()]),
         f"\n- Subprodutos identificados: {_n(len(subs))} "
         f"({_n(sum(1 for s in subs if s['nivel'] == 'S1'))} S1, {_n(sum(1 for s in subs if s['status_automatico'] == AUTO_INCONCLUSIVO))} inconclusivos).",
         f"- Itens: " + "; ".join(f"{k} {_n(v)}" for k, v in sorted(c["itens"].items())) + ".",
         "- S1 = catálogo com atributos essenciais completos e equivalência demonstrada (validação automática rigorosa); "
         "S2 = catálogo consistente com ressalva documental não crítica (**não** é validação sem qualificação); S3 = os 4.122 "
         "candidatos, sem validação presumida; S4 = itens com compatibilidade demonstrada pelo documento da contratação.\n",
         "## Qualidade da documentação\n",
         f"- **Catálogo oficial (nível 1):** API pública de dados abertos do Compras.gov.br — `4_consultarItemMaterial`, "
         f"`7_consultarMaterialCaracteristicas`, `6_consultarMaterialUnidadeFornecimento` (endpoints conferidos na documentação "
         f"OpenAPI). {_n(c['fontes_catalogo_ok'])} de {_n(c['fontes_catalogo_consultadas'])} consultas com resposta; período "
         f"{m['consulta_documental']['inicio']} a {m['consulta_documental']['fim']}. Respostas guardadas com SHA-256 (`catalogo_fontes.csv`).",
         f"- **Contratações (nível 2):** API pública do PNCP (`/compras/{{ano}}/{{seq}}/arquivos`), amostra documental de "
         f"{_n(c['compras_amostra_documental'])} compras (uma por família, sorteio por SHA-256, independente da classificação). "
         f"{_n(c['documentos_contratacao_localizados'])} documentos (TR/edital) localizados, {_n(c['documentos_com_texto'])} com texto. "
         "Resultado por compra: " + "; ".join(f"{k} {_n(v)}" for k, v in sorted(res_compras.items(), key=lambda kv: -kv[1])) + ".",
         f"- **Nível 3 (normas, fabricantes):** não consultado automaticamente — nenhuma fonte desse tipo foi usada como prova.",
         f"- **Indisponibilidades registradas:** {_n(len(indisp))} (`documentos_indisponiveis.csv`).\n",
         "## Qualidade da classificação\n",
         _tab(["Status da variante × catálogo oficial", "Variantes"], [[k, _n(v)] for k, v in sorted(st_var.items(), key=lambda kv: -kv[1])]),
         "\n**Motivos das decisões inconclusivas** (um produto pode ter mais de um):\n",
         _tab(["Motivo", "Produtos"], [[k, _n(v)] for k, v in motivos.most_common(15)]) if motivos else "Nenhum.",
         "\n**Ressalvas de S2:**\n",
         _tab(["Ressalva", "Produtos"], [[k, _n(v)] for k, v in ress.most_common(10)]) if ress else "Nenhuma.",
         "\nRegras aplicadas (todas em `metodologia_automatica.md`): especificação canônica = características oficiais do "
         "CATMAT; variante conforme só se for o texto oficial a menos de espaços ou contiver todos os valores oficiais sem "
         "divergência de grandeza; '1/2' nunca casa com '12'; espaço dentro de número só é aceito quando o número oficial é "
         "contíguo, com ressalva S2; perfis por categoria de risco exigem atributos críticos no catálogo; unidade conferida "
         "com as unidades oficiais do PDM.\n",
         *secao_pendencias(pend), *secao_caso(cp),
         "## Reprodutibilidade\n",
         f"- Testes: {testes['testes_executados']} executados, {testes['aprovados']} aprovados, {testes['falhas']} falhas, {testes['erros']} erros "
         f"({testes['executado_em']})." if testes else "- Testes: ver `saidas/resultado_testes.json`.",
         f"- Hash da cesta original `{m['hash_cesta_original'][:16]}…`; variantes `{m['hash_variantes'][:16]}…`; snapshot do catálogo "
         f"`{(m['hash_snapshot_catalogo'] or '')[:16]}…`; documentos `{(m['hash_documentos_contratacao'] or '')[:16]}…`; configuração "
         f"`{m['hash_config_automatica'][:16]}…`. Hashes completos em `manifesto.json`.",
         "- Reprodução: `..\\..\\.venv\\Scripts\\python.exe scripts\\executar.py auto-executar --prioridade P1` (reutiliza o cache; "
         "etapas com hashes válidos não são refeitas).\n",
         "## Limitações\n",
         "- Validação automática não garante ausência absoluta de erro.\n- Equivalência textual não prova equivalência material.\n"
         "- Equivalência de catálogo não prova conformidade individual das contratações; para isso só os itens S4.\n"
         "- Ausência de documentação impede a aprovação (inconclusivo, nunca aprovação presumida).\n"
         "- A amostra documental cobre poucas compras; PDFs sem camada de texto não são lidos (sem OCR).\n"
         "- A seleção da cesta não resolve a endogeneidade na escolha do modo de disputa.\n"
         "- A validação não elimina as falhas de pré-tendência identificadas no estudo econométrico, que permanece exploratório.\n"]
    (ctx.saida / "relatorio.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def secao_pendencias(pend):
    if not pend:
        return []
    n, cont, st = pend
    nomes = dict(CATEGORIAS_143, FALHA_EXTRACAO="falha de extração da auditoria 1.2.0 (todas as variantes conformes ao texto oficial)")
    return ["## Os 143 casos pendentes da auditoria 1.2.0\n",
            f"Os {n} produtos com divergência a examinar foram reexaminados contra o catálogo oficial "
            "(`pendencias_143_classificadas.csv`); um produto pode ter mais de um problema:\n",
            _tab(["Problema", "Produtos"], [[nomes.get(k, k), _n(v)] for k, v in cont.most_common()]),
            "\nStatus automático resultante: " + "; ".join(f"{k} {_n(v)}" for k, v in st.most_common()) + ". Nenhuma regra foi "
            "ajustada para aprová-los; as únicas correções são as inequívocas (espaçamento conferido no texto oficial).\n"]


def secao_caso(cp):
    if not cp:
        return []
    e, a = cp["esp"], cp["aud"]
    prod = next(x for x in a if x["tipo_registro"] == "PRODUTO")
    L = ["## Caso CP1860 (parafusadeira: mandril 12″ × 1/2″)\n",
         f"- Catálogo oficial do CATMAT {e['catmat']} (consultado em {e['consultado_em']}, SHA-256 "
         f"`{(e['fonte_caracteristicas_sha256'] or '')[:16]}…`): «{e['descricao_oficial'].strip()}».",
         "- Descrições originais preservadas (itens por descrição):"]
    for o in sorted(cp["origs"], key=lambda o: -int(o["itens"])):
        L.append(f"  - {o['itens']} itens — «{o['descricao_original'][:170]}»")
    for c in cp["comp"]:
        L.append(f"- Variante `{c['id_variante']}` ({c['itens']} itens): **{c['status_variante']}**"
                 + (f" — {c['divergencias_materiais']}" if c["divergencias_materiais"] else "")
                 + (f" → subproduto `{c['id_subproduto']}`" if c["id_subproduto"] else ""))
    L.append(f"- Decisão da família: **{prod['status_automatico']}**. {prod['motivos']}")
    for x in a:
        if x["tipo_registro"] == "SUBPRODUTO":
            L.append(f"  - subproduto `{x['id_registro']}`: {x['status_automatico']} {x['nivel']} — {x['motivos'] or x['ressalvas'] or x['evidencias']}")
    div = [c for c in cp["comp"] if c["status_variante"] == "DIVERGENTE"]
    if div:
        L.append(f"- A(s) descrição(ões) divergente(s) ({sum(int(c['itens']) for c in div)} itens) não são tratadas como erro de digitação: "
                 "divergem da especificação oficial e, sem documentação independente que as sustente, ficam inconclusivas; a família "
                 "inteira não é aprovada.\n")
    else:
        L.append("- Sem especificação oficial comparável, nenhuma das descrições foi confirmada ou descartada; a família não é aprovada.\n")
    return L
