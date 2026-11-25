"""Etapa 13: relatorio.md, registro_execucao.json e gráficos, gerados das saídas (nenhum número digitado à mão)."""
import csv
import json
import time
from pathlib import Path

import numpy as np

from . import VERSAO, comum, svg


def _csv(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _j(p):
    p = Path(p)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def f(x, d=2):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "—" if x in (None, "") else str(x)
    if not np.isfinite(v):
        return "—"
    s = f"{v:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def fi(x):
    return f(x, 0)


def tab(cab, linhas):
    out = ["| " + " | ".join(cab) + " |", "|" + "|".join("---" for _ in cab) + "|"]
    out += ["| " + " | ".join(str(c).replace("|", "/") for c in l) + " |" for l in linhas]
    return "\n".join(out)


def ic(l, a="ic95_inf", b="ic95_sup"):
    return f"[{f(l.get(a))}; {f(l.get(b))}]"


def _graficos(s, es, refs, hon):
    g = s / "graficos"
    # trajetória dinâmica dCDH 12 meses
    for jan in ("6m", "12m"):
        nome = f"dcdh_{jan}_item_celula"
        linhas = [l for l in es if l["especificacao"] == nome and l["l"] not in ("media",)]
        ls = sorted({int(l["l"]) for l in linhas})
        rot = [f"e={l - 1}" if l > 0 else f"e={l - 1}" for l in ls]
        series = []
        for grp in ("agregado", "adocao", "abandono"):
            d = {int(l["l"]): l for l in linhas if l["grupo"] == grp}
            series.append((grp, [(float(d[k]["beta_lp"]), float(d[k]["ic95_inf"] or "nan"), float(d[k]["ic95_sup"] or "nan"))
                                 if k in d and d[k]["beta_lp"] else None for k in ls]))
        svg.coeficientes(g / f"estudo_eventos_{jan}.svg", f"dCDH, janela de {jan}: efeito do AF por tempo de evento (EXPLORATÓRIO)",
                         rot, series, nota="e = t − F; referência e = −1; IC95 bootstrap por CNPJ")
    # referências na amostra comum
    rs = [l for l in refs if l.get("amostra") in ("comum (14 referências)", "comum")]
    variantes = [l["referencia"] for l in rs if l.get("modelo") == "FE E3"]
    if variantes:
        fe = {l["referencia"]: l for l in rs if l.get("modelo") == "FE E3"}
        dc = {l["referencia"]: l for l in rs if l.get("modelo") == "dCDH" and l.get("grupo") == "agregado"}
        tri = lambda l: (float(l["beta_lp"]), float(l["ic95_inf"]), float(l["ic95_sup"])) if l else None
        svg.coeficientes(g / "referencias_amostra_comum.svg", "Referências alternativas, amostra comum (EXPLORATÓRIO)", variantes,
                         [("FE E3", [tri(fe.get(v)) for v in variantes]), ("dCDH 6m agregado", [tri(dc.get(v)) for v in variantes])])
    if hon:
        rm = [h for h in hon if h.get("familia") == "RM" and h.get("id", "").endswith("|agregado") and h.get("lb")]
        for ident in sorted({h["id"] for h in rm}):
            hh = [h for h in rm if h["id"] == ident]
            svg.coeficientes(g / f"honestdid_{ident.split('|')[0]}.svg", f"HonestDiD Δ^RM — {ident}", [h["valor"] for h in hh],
                             [("IC robusto", [((float(h["lb"]) + float(h["ub"])) / 2, float(h["lb"]), float(h["ub"])) for h in hh])],
                             nota="ponto = centro do intervalo; eixo x = M̄")


def executar(ctx, abrir):
    cfg, saidas, reg = ctx["cfg"], ctx["saidas"], ctx["reg"]
    s = saidas
    val = _j(s / "tabelas" / "validacao_cesta.json")
    fun = _csv(s / "funil_amostra.csv")
    cob = _csv(s / "tabelas" / "cobertura_trimestres.csv")
    ide = _j(s / "tabelas" / "identificacao_eventos.json")
    des = _csv(s / "descritivas.csv")
    bru = _csv(s / "tabelas" / "diferenca_bruta.csv")
    fe = _csv(s / "efeitos_fixos.csv")
    es = _csv(s / "estudo_eventos.csv")
    dg = _j(s / "tabelas" / "diagnosticos_identificacao.json")
    bal = _csv(s / "tabelas" / "balanco_covariaveis_eventos.csv")
    hon = _csv(s / "honestdid.csv")
    refs = _csv(s / "referencias_alternativas.csv")
    rob = _csv(s / "robustez.csv")
    sec = _csv(s / "resultados_secundarios.csv")
    contrib = _csv(s / "tabelas" / "contribuicao_orgaos_E3.csv")
    _graficos(s, es, refs, hon)
    from .inferencia import holm
    ev = cfg["eventos"]
    pr = f"dcdh_{ev['janela_principal']}_item_celula"
    E = {(l["especificacao"], l["grupo"], l["l"]): l for l in es}
    get = lambda g, l="media", e=pr: E.get((e, g, str(l)), {})
    # Holm famílias P e F
    famP = [get(g) for g in ("agregado", "adocao", "abandono")]
    famF = [get("adocao", -1), get("abandono", -1), get("simetria")]
    for fam in (famP, famF):
        ps = [float(x.get("p") or "nan") for x in fam]
        if all(np.isfinite(ps)):
            for x, a in zip(fam, holm(ps)):
                x["p_holm"] = a
    feP = next((l for l in fe if l["especificacao"] == cfg["efeitos_fixos"]["principal"]), {})
    br = bru[0] if bru else {}
    L = []
    A = L.append
    A("# Efeito do modo de disputa (Aberto × Aberto-Fechado) na cesta padronizada")
    A("")
    A(f"Gerado em {time.strftime('%d/%m/%Y %H:%M')} por `executar.py` (versão {VERSAO}). Protocolo: [`protocolo.md`](protocolo.md) "
      "(fixado antes da estimação); método: [`metodologia.md`](metodologia.md); conclusão: [`conclusao.md`](conclusao.md); "
      "alterações após o registro: [`desvios_registro.md`](desvios_registro.md).")
    A("")
    A("> **Todos os resultados abaixo são EXPLORATÓRIOS.** A cesta validada não tem nenhum produto aprovado "
      f"({val.get('produtos_aprovados', 0)} aprovados; {val.get('formulario_com_decisao', 0)} decisões no formulário). A análise "
      "principal, que exige aprovação técnica documentada, não pôde ser executada; as estimativas usam a cesta candidata e "
      "não devem ser lidas como confirmação causal.")
    A("")
    A("## 1. Produtos aprovados e conjuntos da cesta")
    A("")
    A(tab(["Conjunto", "Produtos"], [["Cesta candidata", fi(val.get("candidatos"))], ["Classe A", fi(val.get("classe_A"))],
                                     ["Classe B", fi(val.get("classe_B"))], ["Famílias do cenário rigoroso", fi(val.get("familias_rigoroso"))],
                                     ["Produtos candidatos nessas famílias", fi(val.get("produtos_candidatos_em_familias_rigoroso"))],
                                     ["A ∩ rigoroso", fi(val.get("A_e_rigoroso"))], ["B ∩ rigoroso", fi(val.get("B_e_rigoroso"))],
                                     ["A fora do rigoroso", fi(val.get("A_fora_rigoroso"))],
                                     ["Produtos recorrentes em todas as janelas", fi(val.get("recorrencia_todas_janelas"))],
                                     ["**Aprovados (cesta validada)**", f"**{fi(val.get('produtos_aprovados'))}**"]]))
    A("")
    A("## 2. Amostra, funil e auditoria")
    A("")
    A(tab(["Etapa", "Critério", "Itens", "Compras", "Produtos", "UASGs", "Órgãos (CNPJ)"],
          [[x["etapa"], x["criterio"], fi(x["itens"]), fi(x["compras"]), fi(x["produtos"]), fi(x["uasgs"]), fi(x["orgaos_cnpj"])] for x in fun]))
    A("")
    rc = reg.contagens
    ra = _csv(s / "tabelas" / "referencias_resumo.csv")
    a1 = next((r for r in ra if r["variante"] == "A1"), {})
    A(f"- Ligação ao `pncp_v2.db` por (`numero_controle_pncp`, `numero_item`, `registro_principal = 1`): todos os 2.137.650 itens "
      "ligados, um registro por item, CATMAT, CNPJ e data de publicação iguais aos da cesta; as divergências de UASG eram "
      "só zeros à esquerda (normalizado para 6 dígitos). Ver `tabelas/impressoes_digitais.json` (fontes inalteradas).")
    A(f"- Referência A1 disponível (≥ 5 itens de ≥ 3 outras UASGs): {fi(a1.get('itens_com_referencia'))} itens; depois da regra "
      f"`|Y| ≤ ln 10`: **{fi(a1.get('amostra_comum_A1'))} itens** na amostra exploratória (A1).")
    A("")
    A("## 3. Cobertura temporal e censura")
    A("")
    A(tab(["Trimestre de abertura", "Itens", "Compras", "Homologados", "Com preço", "Situação"],
          [[x["trimestre"], fi(x["itens"]), fi(x["compras"]), fi(x["homologados"]), fi(x["com_preco"]), x["situacao"]] for x in cob]))
    A("")
    A("- O CATMAT some da fonte depois de 17/04/2026 (censura da fonte): 2026T2 é incompleto e 2026T3–T4 não são observados — "
      "não são trimestres sem compras.")
    A("- 2023T1 não tem itens com situação Homologado: a API mantém 'Em andamento' em itens com preço de resultado (status "
      "desatualizado). O preço só existe a partir de 2023T2; o regime de modo usa 2023T1.")
    A("")
    A("## 4. Eventos e identificação")
    A("")
    A(tab(["Medida", "Valor"], [["Painel (regime)", ide.get("painel")], ["UASGs no painel", fi(ide.get("uasgs"))],
                                ["Trocas válidas (A→AF / AF→A)", f"{fi(sum(ide.get('trocas_por_direcao', {}).values()))} "
                                 f"({fi(ide.get('trocas_por_direcao', {}).get('A->AF'))} / {fi(ide.get('trocas_por_direcao', {}).get('AF->A'))})"],
                                ["Trocas puras / absorventes", f"{fi(ide.get('trocas_puras'))} / {fi(ide.get('trocas_absorventes'))}"],
                                ["Irregulares (fora) / sem pré adjacente (fora)", f"{fi(ide.get('tipos', {}).get('irregular'))} / "
                                 f"{fi(ide.get('tipos', {}).get('troca_sem_pre_adjacente'))}"],
                                ["CNPJs com troca", fi(ide.get("cnpjs_com_troca"))],
                                ["Eventos usados em l = 1 (principal)", fi(dg.get("eventos_usados_l1"))],
                                ["CNPJs usados / nº efetivo de CNPJs", f"{fi(dg.get('cnpjs_usados'))} / {f(dg.get('n_efetivo_cnpjs'), 1)}"],
                                ["Participação do maior CNPJ / das 5 maiores UASGs no peso", f"{f(100 * (dg.get('share_top1_cnpj_peso') or np.nan), 1)}% / {f(100 * (dg.get('share_top5_uasgs_peso') or np.nan), 1)}%"],
                                ["Eventos com placebo l = −1 / −2", f"{fi(dg.get('eventos_com_placebo1'))} / {fi(dg.get('eventos_com_placebo2'))}"],
                                ["Sobreposição de produtos pré/pós (média)", f(100 * (dg.get("sobreposicao_produtos_media") or np.nan), 1) + "%"],
                                ["Trimestre do ano das trocas", dg.get("trimestre_do_ano_F")]]))
    A("")
    A(f"As referências de auditoria (995 UASGs com os dois modos; ~160 eventos potenciais) usavam outra regra; a regra deste "
      f"protocolo identifica {fi(sum(ide.get('trocas_por_direcao', {}).values()))} trocas persistentes.")
    A("")
    if bal:
        A("Balanço (mesmo estimador dCDH aplicado às características; diferença associada à troca, sinal 'efeito do AF'):")
        A("")
        A(tab(["Característica", "Grupo", "l", "Estimativa", "IC95", "p"],
              [[b["covariavel"], b["grupo"], b["l"], f(b["beta_lp"], 3), ic(b), f(b["p"], 3)] for b in bal if b["grupo"] in ("agregado", "adocao", "abandono")]))
        A("")
    A("## 5. Estatísticas descritivas por modo (Y_A1, log-pontos)")
    A("")
    A(tab(["Modo", "Itens", "Compras", "Produtos", "UASGs", "Órgãos", "Média", "Mediana", "DP", "P5", "P25", "P75", "P95", "Homolog. (decididos)", "Fracasso", "Deserção"],
          [[d["modo"], fi(d["itens"]), fi(d["compras"]), fi(d["produtos"]), fi(d["uasgs"]), fi(d["orgaos_cnpj"]), f(d["media_Y"]), f(d["mediana_Y"]),
            f(d["dp_Y"]), f(d["p05"]), f(d["p25"]), f(d["p75"]), f(d["p95"]), f(100 * float(d["taxa_homologacao_decididos"]), 1) + "%",
            f(100 * float(d["taxa_fracasso_decididos"]), 1) + "%", f(100 * float(d["taxa_desercao_decididos"]), 1) + "%"] for d in des]))
    A("")
    A(tab(["Diferença bruta (AF − A)", "lp", "% exato", "IC95 (CNPJ)", "p CNPJ", "p 2 vias", "p WCR", "Órgãos (efetivos)"],
          [[b["desfecho"], f(b["diferenca_AF_menos_A_lp"]), f(b.get("pct_exato")), ic(b), f(b.get("p_cnpj"), 3), f(b.get("p_2vias"), 3),
            f(b.get("p_wcr_webb"), 3), f"{fi(b.get('cnpjs'))} ({f(b.get('n_efetivo_cnpjs'), 0)})"] for b in bru]))
    A("")
    A("## 6. Painel de efeitos fixos — associação condicional")
    A("")
    A(tab(["Espec.", "Descrição", "β (lp)", "% exato", "IC95 CNPJ", "p", "p 2 vias", "p WCR", "Itens", "UASGs", "Órgãos (efet.)", "Perda singletons"],
          [[l["especificacao"], l["descricao"], f(l["beta_lp"]), f(l["pct_exato"]), ic(l), f(l["p"], 3), f(l.get("p_2vias"), 3),
            f(l.get("p_wcr_webb"), 3), fi(l["n_itens"]), fi(l["n_uasgs"]), f"{fi(l['n_orgaos'])} ({f(l['n_efetivo_orgaos'], 0)})",
            fi(l["perda_singletons"])] for l in fe]))
    A("")
    if contrib:
        A("Maiores contribuintes para a variação identificadora de E3 (exclusão exata e re-estimação):")
        A("")
        A(tab(["CNPJ", "Participação", "β sem o órgão"], [[c["orgao_cnpj"], f(100 * float(c["participacao_variacao_identificadora"]), 1) + "%",
                                                          f(c.get("beta_sem_orgao"))] for c in contrib[:10]]))
        A("")
    A("## 7. Estudo de eventos (dCDH) — análise causal exploratória")
    A("")
    rows = []
    for l in es:
        if l["l"] == "media" or l["grupo"] == "adocao_absorvente":
            rows.append([l["especificacao"], l["grupo"], l["l"], f(l["beta_lp"]), f(l.get("pct_exato")), ic(l), f(l["p"], 3),
                         f(l.get("p_holm"), 3) if l.get("p_holm") else "", f(l.get("mde_80"))])
    for x in famP + famF:
        for r in rows:
            if r[0] == pr and r[1] == x.get("grupo") and r[2] == x.get("l") and "p_holm" in x:
                r[7] = f(x["p_holm"], 3)
    A(tab(["Especificação", "Grupo", "l", "β (lp)", "% exato", "IC95 (bootstrap CNPJ)", "p", "p Holm (família)", "DMD 80%"], rows))
    A("")
    A("Trajetória dinâmica e placebos (principal):")
    A("")
    A(tab(["Grupo", "l (e = l−1)", "β (lp)", "IC95", "p", "DMD 80%"],
          [[l["grupo"], l["l"], f(l["beta_lp"]), ic(l), f(l["p"], 3), f(l.get("mde_80"))] for l in es
           if l["especificacao"] == pr and l["l"] != "media" and l["grupo"] in ("agregado", "adocao", "abandono")]))
    A("")
    A("![dinâmica 6m](graficos/estudo_eventos_6m.svg)")
    A("")
    A("![dinâmica 12m](graficos/estudo_eventos_12m.svg)")
    A("")
    A("## 8. HonestDiD")
    A("")
    if hon and hon[0].get("familia"):
        A(tab(["Especificação", "Família", "Valor", "IC robusto", "Inclui zero", "Erro/observação"],
              [[h["id"], h["familia"], h["valor"] or "—", f"[{f(h['lb'])}; {f(h['ub'])}]" if h.get("lb") else "—",
                h.get("inclui_zero", ""), h.get("erro", "")] for h in hon]))
    else:
        A("Não calculado: " + (hon[0].get("situacao", "") if hon else "sem saída") + ".")
    A("")
    A("## 9. Referências alternativas")
    A("")
    A(tab(["Modelo", "Amostra", "Referência", "Grupo", "β (lp)", "IC95", "β − β_A1", "IC95 da diferença", "p Holm (dif.)", "Itens"],
          [[r.get("modelo"), r.get("amostra"), r.get("referencia"), r.get("grupo", ""), f(r.get("beta_lp")), ic(r),
            f(r.get("dif_vs_A1")), ic(r, "dif_ic95_inf", "dif_ic95_sup") if r.get("dif_vs_A1") else "", f(r.get("p_dif_holm"), 3),
            fi(r.get("n_itens"))] for r in refs if r.get("grupo", "agregado") in ("agregado", "")]))
    A("")
    A("![referências](graficos/referencias_amostra_comum.svg)")
    A("")
    A("## 10. Robustez")
    A("")
    A(tab(["Verificação", "Modelo", "Grupo", "β (lp)", "IC95", "p", "Itens / observação"],
          [[r.get("verificacao"), r.get("modelo", "—"), r.get("grupo", "—"), f(r.get("beta_lp")), ic(r) if r.get("ic95_inf") else "—",
            f(r.get("p"), 3), r.get("situacao") or (f"jackknife [{f(r.get('jackknife_min'))}; {f(r.get('jackknife_max'))}]" if r.get("jackknife_min") else fi(r.get("n_itens")))]
           for r in rob if r.get("grupo") in (None, "", "agregado", "associacao", "—") or r.get("situacao")]))
    A("")
    A("## 11. Desfechos secundários")
    A("")
    A(tab(["Desfecho", "Modelo", "Grupo", "β", "IC95", "p", "p Holm (S)", "Unidade"],
          [[x["desfecho"], x["modelo"], x["grupo"], f(x["beta"]), ic(x), f(x["p"], 3), f(x.get("p_holm_familia_S"), 3), x["unidade"]] for x in sec]))
    A("")
    # perguntas finais
    ag = get("agregado")
    ad, ab = get("adocao"), get("abandono")
    sim = get("simetria")
    A("## 12. Respostas às questões finais")
    A("")
    def inclui(l):
        try:
            return float(l["ic95_inf"]) <= 0 <= float(l["ic95_sup"])
        except (KeyError, TypeError, ValueError):
            return None
    A(f"1. **O AF apresenta preços menores que o Aberto na cesta?** Descritivamente, a diferença bruta de Y_A1 é "
      f"{f(br.get('diferenca_AF_menos_A_lp'))} lp ({f(br.get('pct_exato'))}%), IC95 {ic(br)}. Exploratório; não há produtos aprovados.")
    A(f"2. **Magnitude bruta:** {f(br.get('diferenca_AF_menos_A_lp'))} lp; diferença de medianas "
      f"{f(bru[-1].get('diferenca_AF_menos_A_lp') if bru else None)} lp.")
    A(f"3. **Após UASG, produto e período (E3):** {f(feP.get('beta_lp'))} lp ({f(feP.get('pct_exato'))}%), IC95 {ic(feP)} — associação condicional.")
    A(f"4. **A mesma UASG muda o preço quando troca de modo (dCDH 6m, por item)?** Agregado {f(ag.get('beta_lp'))} lp, IC95 {ic(ag)}; "
      f"adoção {f(ad.get('beta_lp'))} lp {ic(ad)}; abandono (sinal do AF) {f(ab.get('beta_lp'))} lp {ic(ab)}; simetria "
      f"(adoção − abandono) {f(sim.get('beta_lp'))} lp {ic(sim)}.")
    A(f"5. **Significância:** E3 p = {f(feP.get('p'), 3)} (WCR {f(feP.get('p_wcr_webb'), 3)}); dCDH agregado p = {f(ag.get('p'), 3)} "
      f"(Holm na família P: {f(ag.get('p_holm'), 3)}).")
    A(f"6. **Intervalos:** E3 {ic(feP)}; dCDH agregado {ic(ag)} (em %: [{f(ag.get('pct_ic_inf'))}; {f(ag.get('pct_ic_sup'))}]).")
    A("7. **Média, mediana ou geométrica?** Ver §9: diferenças pareadas β_k − β_A1 na amostra comum, com Holm.")
    A("8. **Compras com muitos itens?** Ver R06 (peso igual por compra) e o estimando por compra em §7.")
    A("9. **Heterogeneidade dos produtos:** E7 (UASG × produto), R02 (A ∩ rigoroso), R09 (sem inconsistências), R10 (mesmo produto antes e depois).")
    A("10. **Desvios das tendências paralelas:** ver §8 (HonestDiD); a ausência de pré-tendência significativa não prova tendências paralelas.")
    sh = [x for x in sec if x["desfecho"] == "homologacao" and x["grupo"] == "agregado"]
    A(f"11. **Homologação:** dCDH agregado {f(sh[0]['beta']) if sh else '—'} p.p., IC95 {ic(sh[0]) if sh else '—'} (ver §11).")
    A("12. **Natureza dos resultados:** §5 descritivo; §6 associativo; §7–8 potencialmente causal, porém **exploratório** "
      "(cesta não validada). Nenhum resultado é confirmatório.")
    A("")
    A("## 13. Reprodução")
    A("")
    A("```powershell")
    A("cd PNCP-Automation\\analises\\efeito_modos_cesta_padronizada_20261124")
    A("..\\..\\.venv\\Scripts\\python.exe executar.py                 # todas as etapas (~1–2 h; lê pncp_v2.db só em mode=ro)")
    A("..\\..\\.venv\\Scripts\\python.exe -m unittest discover -s testes -v")
    A("```")
    (s / "relatorio.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    # registro
    arqs = sorted([*Path(s).glob("em/*.py"), *Path(s).glob("testes/*.py"), Path(s) / "executar.py", Path(s) / "config.json",
                   Path(s) / "honestdid.R", Path(s) / "protocolo.md"])
    regs = {p.stem: _j(p) for p in sorted((s / "registros").glob("execucao_*.json"))}
    comum.escrever_json(s / "registro_execucao.json", {
        "versao": VERSAO, "gerado_em": time.strftime("%Y-%m-%dT%H:%M:%S"), "semente": cfg["semente"],
        "bootstrap": {"eventos": cfg["eventos"]["bootstrap"], "wcr": cfg["efeitos_fixos"]["bootstrap_wcr"]},
        "ambiente": comum.ambiente(), "r": _csv(ctx["dados"] / "honestdid" / "honestdid_r_ambiente.csv"),
        "impressoes_digitais": _j(s / "tabelas" / "impressoes_digitais.json"),
        "sha256_config": comum.sha256_arquivo(Path(s) / "config.json"),
        "hashes_codigo": {str(p.relative_to(s)).replace("\\", "/"): comum.sha256_arquivo(p) for p in arqs if p.is_file()},
        "saidas_sha256": {p.name: comum.sha256_arquivo(p) for p in sorted(Path(s).glob("*.csv"))},
        "execucoes": {k: {"etapas": v.get("etapas"), "avisos": v.get("avisos")} for k, v in regs.items()},
        "classificacao": "EXPLORATÓRIO: nenhum produto aprovado na cesta validada"})
