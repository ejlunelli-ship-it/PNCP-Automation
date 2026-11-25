"""Etapa 'selecionar': universo, métricas, triagem, auditoria de descrições, classificação,
subtipos, cesta candidata (congelada), formulário de revisão e auditoria de qualidade.

Lê somente o banco de trabalho (que não contém preços nem modo de disputa)."""
import gzip
import csv
import hashlib
import json
import time
from pathlib import Path

from . import VERSAO, auditoria, classificacao, comum, metricas
from .classificacao import VERSAO_REGRAS

COLS_METRICAS = ["familia", "catmat", "unidade_norm", "classe", "pdm", "itens", "compras", "uasgs", "orgaos",
                 "trimestres", "anos", "primeira", "ultima", "itens_homologados", "compras_homologadas",
                 "share_uasg_dominante", "hhi", "n_efetivo_uasgs", "share_top5", "compras_uasg_max",
                 "share_desc_completa", "n_descricoes_originais", "n_descricoes_distintas", "itens_por_compra",
                 "compras_por_trimestre", "compras_por_ano", "distribuicao_uasg"]


def _linhas(dst, sql, p=()):
    cur = dst.execute(sql, p)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _r(x, n=4):
    return round(x, n) if isinstance(x, float) else x


def _csv_gz(caminho, linhas, colunas):
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(caminho, "wt", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(colunas)
        for x in linhas:
            w.writerow(["" if x.get(c) is None else _r(x.get(c)) for c in colunas])


def _meta(dst, chave):
    try:
        r = dst.execute("SELECT valor FROM meta WHERE chave = ?", (chave,)).fetchone()
    except Exception:
        return None
    return json.loads(r[0]) if r else None


def qualidade_cadastral(m, unidade, par):
    q = par["qualidade_cadastral"]
    falhas = []
    if q["exigir_unidade_valida"] and unidade["alerta"] in ("unidade_ausente", "formato_nao_reconhecido"):
        falhas.append(f"unidade {unidade['alerta']}")
    if m["share_desc_completa"] is None or m["share_desc_completa"] < q["share_descricao_completa_min"]:
        falhas.append(f"descrição completa em {m['share_desc_completa']:.1%} < {q['share_descricao_completa_min']:.0%}")
    return falhas


def _executar(ctx, dst):
    metricas.registrar_funcoes(dst)
    par, reg, saidas = ctx["par"], ctx["reg"], ctx["saidas"]
    lim = par["triagem_inicial"]
    cautela = classificacao.carregar_cautela(Path(ctx["parametros_arquivo"]).parent / "cautela.json")

    with reg.etapa("funil do universo"):
        fun = metricas.funil(dst, par)
        comum.escrever_csv(saidas / "funil_selecao.csv", fun, list(fun[-1].keys()))
    with reg.etapa("tabela do universo"):
        sql = metricas.sql_universo(par)
        assinatura = hashlib.sha256((sql + "|" + json.dumps(_meta(dst, "normalizacao"), sort_keys=True)).encode()).hexdigest()
        existe = dst.execute("SELECT COUNT(*) FROM sqlite_master WHERE name = 'universo'").fetchone()[0]
        if existe and _meta(dst, "assinatura_universo") == assinatura:
            reg.aviso("universo reaproveitado: mesma consulta e mesma normalização (assinatura conferida)")
        else:
            metricas.criar_universo(dst, par)
            dst.execute("CREATE TABLE IF NOT EXISTS meta (chave TEXT PRIMARY KEY, valor TEXT)")
            dst.execute("INSERT OR REPLACE INTO meta VALUES ('assinatura_universo', ?)", (json.dumps(assinatura),))
        reg.consulta("universo", sql)
        reg.contar("universo_itens", dst.execute("SELECT COUNT(*) FROM universo").fetchone()[0])
    with reg.etapa("cobertura temporal"):
        cob = dst.execute("SELECT MIN(data_publicacao), MAX(data_publicacao), COUNT(DISTINCT trimestre), "
                          "COUNT(DISTINCT ano) FROM universo").fetchone()
        meses = [r[0] for r in dst.execute("SELECT DISTINCT substr(data_publicacao, 1, 7) FROM universo ORDER BY 1")]
        tri_meses = {}
        for m in meses:
            t = f"{m[:4]}T{(int(m[5:7]) - 1) // 3 + 1}"
            tri_meses.setdefault(t, []).append(m)
        anos_meses = {}
        for m in meses:
            anos_meses.setdefault(m[:4], []).append(m)
        temporal = {"data_minima": cob[0], "data_maxima": cob[1], "trimestres": cob[2], "anos": cob[3],
                    "meses_observados": meses,
                    "trimestres_parciais": {t: ms for t, ms in tri_meses.items() if len(ms) < 3},
                    "anos_parciais": {a: len(ms) for a, ms in anos_meses.items() if len(ms) < 12},
                    "nota": "Trimestre/ano parcial = menos meses com publicações do que o calendário. O último mês "
                            "pode estar incompleto mesmo listado (coleta até o dia da carga)."}
        comum.escrever_json(saidas / "cobertura_temporal.json", temporal)

    with reg.etapa("métricas por família (licitados e homologados)"):
        n_fam = metricas.metricas_familias(dst, "fam_metricas")
        metricas.metricas_familias(dst, "fam_metricas_hom", filtro="homologado = 1")
        reg.contar("familias_universo", n_fam)
        fams = _linhas(dst, "SELECT * FROM fam_metricas ORDER BY compras DESC, familia")
        _csv_gz(saidas / "familias_metricas.csv.gz", fams, COLS_METRICAS)
        hom = {r["familia"]: r for r in _linhas(dst, "SELECT familia, compras, uasgs, trimestres, anos, "
                                                     "share_uasg_dominante, hhi FROM fam_metricas_hom")}
    unidades = {r["unidade_norm"]: r for r in _linhas(
        dst, "SELECT unidade_norm, MIN(conteudo) conteudo, MIN(alerta) alerta FROM unidades GROUP BY unidade_norm")}

    # ------------------------------------------------------------------ triagem quantitativa + cadastral
    with reg.etapa("triagem das famílias"):
        # triagem ampla = cenário mais brando da grade de sensibilidade (classificação técnica para todas);
        # a cesta principal usa os limiares iniciais
        sens = par["sensibilidade"]
        lim_amplo = {d: (min(sens[d]) if d.endswith("_min") else max(sens[d])) for d in lim}
        triadas, falhas_quant, falhas_cad, n_inicial = [], 0, 0, 0
        for m in fams:
            ok, falhas = metricas.aplica_limiares(m, lim_amplo)
            if not ok:
                continue
            m["passa_inicial"], m["falhas_limiares"] = metricas.aplica_limiares(m, lim)
            if not m["passa_inicial"]:
                falhas_quant += 1
            else:
                n_inicial += 1
            un = unidades.get(m["unidade_norm"], {"conteudo": None, "alerta": ""})
            fc = qualidade_cadastral(m, un, par)
            m["falhas_cadastrais"] = fc
            if fc and m["passa_inicial"]:
                falhas_cad += 1
            triadas.append(m)
        reg.contar("limiares_triagem_ampla", lim_amplo)
        reg.contar("familias_triagem_ampla", len(triadas))
        reg.contar("familias_passam_limiares_iniciais", n_inicial)
        reg.contar("familias_ampla_falham_limiares_iniciais", falhas_quant)
        reg.contar("familias_iniciais_falham_qualidade_cadastral", falhas_cad)
        dst.executescript("DROP TABLE IF EXISTS triadas; CREATE TABLE triadas (familia TEXT PRIMARY KEY);")
        dst.executemany("INSERT INTO triadas VALUES (?)", [(m["familia"],) for m in triadas])

    # ------------------------------------------------------------------ auditoria de descrições (100%)
    with reg.etapa("auditoria das descrições (todas as variantes das famílias triadas)"):
        dst.executescript("""
            DROP TABLE IF EXISTS variantes;
            CREATE TABLE variantes AS
            SELECT u.familia, COALESCE(u.desc_id, 0) AS desc_id, COALESCE(MIN(d.descricao_original), '') AS descricao_original,
                   MIN(d.descricao_norm) AS descricao_norm, MIN(d.chave_textual) AS chave_textual,
                   COUNT(*) AS itens, COUNT(DISTINCT u.chave) AS compras,
                   COUNT(DISTINCT u.uasg) AS uasgs, GROUP_CONCAT(DISTINCT u.uasg) AS lista_uasgs,
                   MIN(u.data_publicacao) AS primeira, MAX(u.data_publicacao) AS ultima, MIN(u.nome_pdm) AS nome_pdm,
                   GROUP_CONCAT(DISTINCT u.ano) AS anos
            FROM universo u JOIN triadas t USING (familia) LEFT JOIN descricoes d ON d.rowid = u.desc_id
            GROUP BY u.familia, COALESCE(u.desc_id, 0);
            CREATE INDEX ix_var_fam ON variantes (familia);
        """)
        por_fam = {}
        for v in _linhas(dst, "SELECT * FROM variantes ORDER BY familia, itens DESC, descricao_original"):
            v["descricao_norm"] = v["descricao_norm"] or ""
            por_fam.setdefault(v["familia"], []).append(v)
        classes, linhas_var = {}, []
        for m in triadas:
            vs = classificacao.variantes_da_familia(por_fam.get(m["familia"], []))
            un = unidades.get(m["unidade_norm"], {"unidade_norm": m["unidade_norm"], "conteudo": None, "alerta": ""})
            un = {"unidade_norm": m["unidade_norm"], "conteudo": un.get("conteudo"), "alerta": un.get("alerta") or ""}
            c = classificacao.classificar_familia(m["familia"], vs, m, un, par["homogeneidade"], cautela)
            if m["falhas_cadastrais"]:
                c["pendencias"].insert(0, "qualidade cadastral insuficiente: " + "; ".join(m["falhas_cadastrais"]))
            classes[m["familia"]] = c
            tot = sum(v["itens"] for v in vs) or 1
            acum = 0
            for v in vs:
                acum += v["itens"]
                unidades_fis = sorted({x for k in ("volume", "peso", "medida_linear", "dimensoes", "gramatura")
                                       for x in v["atributos"].get(k, ())})
                emb = v["atributos"].get("unidades_por_embalagem", ())
                linhas_var.append({
                    "familia": m["familia"], "catmat": m["catmat"], "unidade_norm": m["unidade_norm"],
                    "descricao_original": v["descricao_original"], "descricao_normalizada": v["descricao_norm"],
                    "chave_textual": v["chave_textual"], "itens": v["itens"], "compras": v["compras"],
                    "uasgs": v["uasgs"], "lista_uasgs": v["lista_uasgs"], "primeira": v["primeira"], "ultima": v["ultima"],
                    "anos": v["anos"], "share_itens": v["itens"] / tot, "share_acumulada": acum / tot,
                    "expressoes_numericas": v["assinatura"], "unidades_fisicas": " | ".join(unidades_fis),
                    "embalagem_na_descricao": " | ".join(emb),
                    "embalagem_divergente": int(classificacao.at.embalagem_divergente(v["atributos"], un["unidade_norm"], un["conteudo"])),
                    "indicadores": ",".join(sorted(v["indicadores"])), "so_nome_pdm": int(bool(v["so_pdm"])),
                    "descricao_ausente": int(not v["descricao_original"]),
                    "difere_assinatura_dominante": int(v["assinatura"] != c["assinatura_dominante"]),
                    "classe_familia": c["classe"], "familia_passa_limiares_iniciais": int(m["passa_inicial"]),
                    "nome_pdm": v["nome_pdm"],
                })
        dst.executescript("DROP TABLE IF EXISTS familia_classe; CREATE TABLE familia_classe (familia TEXT PRIMARY KEY, "
                          "classe_tecnica TEXT, cadastral_ok INTEGER, passa_inicial INTEGER, motivos TEXT, alertas TEXT);")
        dst.executemany("INSERT INTO familia_classe VALUES (?,?,?,?,?,?)",
                        [(m["familia"], classes[m["familia"]]["classe"], int(not m["falhas_cadastrais"]), int(m["passa_inicial"]),
                          " | ".join(classes[m["familia"]]["motivos"]), " | ".join(classes[m["familia"]]["alertas"])) for m in triadas])
        cols_var = list(linhas_var[0].keys()) if linhas_var else ["familia"]
        comum.escrever_csv(saidas / "descricoes_variantes.csv",
                           [{k: _r(x[k]) for k in cols_var} for x in linhas_var], cols_var)
        reg.contar("variantes_auditadas", len(linhas_var))

    # ------------------------------------------------------------------ produtos (subtipos identificáveis)
    triadas_por_fam_ini = {m["familia"]: m["passa_inicial"] for m in triadas}
    with reg.etapa("produtos candidatos e subtipos"):
        dst.executescript("DROP TABLE IF EXISTS produto_map; CREATE TABLE produto_map (familia TEXT, desc_id INTEGER, "
                          "produto TEXT, assinatura TEXT, PRIMARY KEY (familia, desc_id));")
        mapa, subtipos_info = [], {}
        for fam, c in classes.items():
            if not triadas_por_fam_ini.get(fam):
                continue
            for v in por_fam.get(fam, []):
                if c["subtipos"]:
                    prod = f"{fam}#{c['subtipos'][v['assinatura']]}"
                    subtipos_info.setdefault(prod, {"familia": fam, "assinatura": v["assinatura"]})
                else:
                    prod = fam
                mapa.append((fam, v["desc_id"], prod, v["assinatura"]))
        dst.executemany("INSERT INTO produto_map VALUES (?,?,?,?)", mapa)
        dst.executescript("""
            DROP TABLE IF EXISTS universo_produto;
            CREATE TABLE universo_produto AS
            SELECT u.*, p.produto FROM universo u JOIN produto_map p
              ON p.familia = u.familia AND p.desc_id = COALESCE(u.desc_id, 0);
            CREATE INDEX ix_up_prod ON universo_produto (produto);
            CREATE INDEX ix_up_item ON universo_produto (chave, numero_item);
        """)
        metricas.metricas_familias(dst, "prod_metricas", chave_familia="produto", origem="universo_produto")
        prods = _linhas(dst, "SELECT * FROM prod_metricas ORDER BY compras DESC, familia")
        candidatos, descartados = [], []
        triadas_por_fam = {x["familia"]: x for x in triadas}
        for p in prods:
            fam = p["familia"].split("#")[0]
            c = classes[fam]
            m_fam = triadas_por_fam[fam]
            if not m_fam["passa_inicial"]:
                continue
            ok, falhas = metricas.aplica_limiares(p, lim)
            sub = subtipos_info.get(p["familia"])
            classe = c["classe"]
            motivos = list(c["motivos"])
            pend = list(c["pendencias"])
            if sub:
                if classe == "A":
                    classe = "B"
                motivos = [f"subtipo separado automaticamente pela assinatura '{sub['assinatura']}'"] + \
                          ([] if c["classe"] != "C" else motivos)
                if c["classe"] == "C":
                    classe = "C"
                pend.append("confirmar que o subtipo corresponde a uma apresentação inequívoca")
            if m_fam["falhas_cadastrais"]:
                ok = False
                falhas = falhas + m_fam["falhas_cadastrais"]
            reg_p = {**p, "produto": p["familia"], "familia_base": fam, "classe_tecnica": classe,
                     "risco_heterogeneidade": {"A": "baixo", "B": "moderado", "C": "alto"}[classe],
                     "motivos_classificacao": motivos, "alertas": c["alertas"], "pendencias": pend,
                     "descricao_representativa": c["descricao_dominante"] if not sub else
                     next((v["descricao_original"] for v in por_fam[fam] if v["assinatura"] == sub["assinatura"]), None),
                     "assinatura": sub["assinatura"] if sub else c["assinatura_dominante"],
                     "share_descricao_dominante": c["share_descricao_dominante"], "n_assinaturas_familia": c["n_assinaturas"],
                     "cautela": c["cautela"], "falhas_triagem": falhas}
            hm = hom.get(fam)
            reg_p["compras_homologadas_familia"] = hm["compras"] if hm else 0
            if ok and classe in ("A", "B"):
                candidatos.append(reg_p)
            else:
                reg_p["motivo_descarte"] = ("; ".join(falhas) if not ok else f"classe {classe}: " + "; ".join(motivos))
                descartados.append(reg_p)
        reg.contar("produtos_avaliados", len(prods))
        reg.contar("produtos_candidatos", len(candidatos))
        reg.contar("produtos_candidatos_por_classe",
                   {k: sum(1 for x in candidatos if x["classe_tecnica"] == k) for k in "AB"})
        reg.contar("produtos_descartados", len(descartados))

    # ------------------------------------------------------------------ cesta candidata (congelada)
    with reg.etapa("cesta candidata e formulário de revisão"):
        candidatos.sort(key=lambda x: (x["classe_tecnica"], -x["compras"], x["produto"]))
        for k, x in enumerate(candidatos, 1):
            x["id_candidato"] = f"CP{k:04d}"
        cols_c = ["id_candidato", "produto", "catmat", "unidade_norm", "descricao_representativa", "compras", "itens",
                  "uasgs", "orgaos", "anos", "trimestres", "primeira", "ultima", "hhi", "share_uasg_dominante",
                  "n_efetivo_uasgs", "share_top5", "n_descricoes_originais", "n_descricoes_distintas",
                  "share_descricao_dominante", "classe_tecnica", "risco_heterogeneidade", "alertas_especificacao",
                  "motivos_inclusao", "pendencias_validacao", "compras_homologadas", "itens_homologados", "classe", "pdm",
                  "cautela", "assinatura_atributos"]
        lin_c = []
        for x in candidatos:
            lin_c.append({**x, "alertas_especificacao": " | ".join(x["alertas"]),
                          "motivos_inclusao": (f"compras {x['compras']} ≥ {lim['compras_min']}; UASGs {x['uasgs']} ≥ {lim['uasgs_min']}; "
                                               f"trimestres {x['trimestres']} ≥ {lim['trimestres_min']}; anos {x['anos']} ≥ {lim['anos_min']}; "
                                               f"UASG dominante {x['share_uasg_dominante']:.1%} ≤ {lim['share_uasg_dominante_max']:.0%}; "
                                               f"HHI {x['hhi']:.4f} ≤ {lim['hhi_max']}; classe {x['classe_tecnica']}: "
                                               + "; ".join(x["motivos_classificacao"])),
                          "pendencias_validacao": " | ".join(x["pendencias"] + ["aprovação humana não registrada"]),
                          "cautela": ",".join(x["cautela"]), "assinatura_atributos": x["assinatura"]})
        arq_c = comum.escrever_csv(saidas / "cesta_candidata.csv", [{k: _r(v) for k, v in l.items()} for l in lin_c], cols_c)
        cols_d = ["produto", "catmat", "unidade_norm", "compras", "uasgs", "trimestres", "anos", "hhi",
                  "share_uasg_dominante", "classe_tecnica", "motivo_descarte", "alertas"]
        comum.escrever_csv(saidas / "familias_triadas_descartadas.csv",
                           [{**{k: _r(x.get(k)) for k in cols_d}, "alertas": " | ".join(x["alertas"])} for x in descartados], cols_d)
        dst.executescript("DROP TABLE IF EXISTS cesta_candidata_tab; CREATE TABLE cesta_candidata_tab "
                          "(id_candidato TEXT, produto TEXT PRIMARY KEY, classe_tecnica TEXT);")
        dst.executemany("INSERT INTO cesta_candidata_tab VALUES (?,?,?)",
                        [(x["id_candidato"], x["produto"], x["classe_tecnica"]) for x in candidatos])
        # formulário de revisão: campos de aprovação em branco (não se inventa aprovação)
        cols_f = ["id_candidato", "produto", "catmat", "unidade_norm", "classe_tecnica", "descricao_representativa",
                  "atributos_extraidos", "n_descricoes_distintas", "alertas_especificacao", "pendencias_validacao",
                  "decisao (aprovar/rejeitar/dividir)", "especificacao_canonica_aprovada", "atributos_essenciais",
                  "criterios_equivalencia", "criterios_exclusao", "revisor", "data_revisao", "justificativa",
                  "versao_regra_classificacao"]
        comum.escrever_csv(saidas / "formulario_revisao.csv",
                           [{"id_candidato": x["id_candidato"], "produto": x["produto"], "catmat": x["catmat"],
                             "unidade_norm": x["unidade_norm"], "classe_tecnica": x["classe_tecnica"],
                             "descricao_representativa": x["descricao_representativa"], "atributos_extraidos": x["assinatura"],
                             "n_descricoes_distintas": x["n_descricoes_distintas"],
                             "alertas_especificacao": " | ".join(x["alertas"]),
                             "pendencias_validacao": " | ".join(x["pendencias"]),
                             "versao_regra_classificacao": VERSAO_REGRAS} for x in candidatos], cols_f)
        cols_v = ["id_candidato", "produto", "catmat", "unidade_norm", "especificacao_canonica_aprovada",
                  "atributos_essenciais", "criterios_equivalencia", "criterios_exclusao", "revisor", "data_revisao",
                  "justificativa", "versao_regra_classificacao"]
        comum.escrever_csv(saidas / "cesta_validada.csv", [], cols_v)
        congel = {"congelado_em": time.strftime("%Y-%m-%dT%H:%M:%S"), "versao_codigo": VERSAO, "versao_regras": VERSAO_REGRAS,
                  "sha256_cesta_candidata": comum.sha256_arquivo(arq_c), "produtos": len(candidatos),
                  "parametros": par, "situacao_cesta_validada": "PENDENTE: nenhuma revisão humana registrada",
                  "nota": "Congelado antes de qualquer leitura do modo de disputa (etapa diagnostico)."}
        comum.escrever_json(saidas / "congelamento_cesta.json", congel)

    dst.close()


def executar(ctx):
    dst = comum.conectar_trabalho(ctx["trabalho_db"])
    try:
        _executar(ctx, dst)
    finally:
        try:
            dst.close()
        except Exception:
            pass


def _auditar(ctx, dst):
    """Etapa 'auditar': auditoria de qualidade e cobertura da cesta já congelada (não altera a cesta)."""
    par, reg, saidas = ctx["par"], ctx["reg"], ctx["saidas"]
    metricas.registrar_funcoes(dst)
    import csv as _csv
    with open(saidas / "funil_selecao.csv", encoding="utf-8-sig", newline="") as f:
        fun = [{k: (int(v) if k in ("itens", "compras", "uasgs") and v else v) for k, v in r.items()}
               for r in _csv.DictReader(f)]
    # ------------------------------------------------------------------ auditoria de qualidade
    with reg.etapa("auditoria de qualidade e integridade"):
        aud = auditoria.verificar(dst, par, reg)
        comum.escrever_json(saidas / "auditoria_qualidade.json", aud)
        comum.escrever_csv(saidas / "auditoria_qualidade.csv",
                           [{**a, "exemplos": json.dumps(a["exemplos"][:3], ensure_ascii=False, default=str)} for a in aud],
                           ["verificacao", "afetados", "base", "base_nome", "pct", "criterio", "excluidos",
                            "impacto_produtos_candidatos", "observacao", "exemplos"])

    # ------------------------------------------------------------------ cobertura da cesta (seção 13)
    with reg.etapa("cobertura da cesta candidata"):
        from . import cobertura
        cob = cobertura.calcular(dst, saidas, fun)
        comum.escrever_json(saidas / "cobertura_cesta.json", cob)


def auditar(ctx):
    dst = comum.conectar_trabalho(ctx["trabalho_db"])
    try:
        _auditar(ctx, dst)
    finally:
        dst.close()
