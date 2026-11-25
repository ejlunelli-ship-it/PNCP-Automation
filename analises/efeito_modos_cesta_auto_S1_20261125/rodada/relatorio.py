"""Tabela comparativa, gráficos, relatório e manifesto da rodada (números lidos das saídas; nada digitado à mão)."""
import json
from pathlib import Path

import numpy as np

from . import base
from .analises import _saida

ORDEM = ["S1", "S1S2", "P1", "cesta"]


def _f(x, d=2):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "—"
    if not np.isfinite(v):
        return "—"
    return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _n(x):
    try:
        return f"{int(float(x)):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "—"


def _tab(cab, linhas):
    out = ["| " + " | ".join(cab) + " |", "|" + "|".join("---" for _ in cab) + "|"]
    out += ["| " + " | ".join(str(c).replace("|", "/") for c in l) + " |" for l in linhas]
    return "\n".join(out)


def _ic(r):
    return f"{_f(r.get('beta_lp'))} [{_f(r.get('ic95_inf'))}; {_f(r.get('ic95_sup'))}]" if r else "—"


def metricas(c, nome):
    base.estudo_anterior(c)
    from em.inferencia import holm
    p = _saida(c, nome)
    fe = {r["especificacao"]: r for r in base.ler_csv(p / "efeitos_fixos.csv")}
    ev = base.ler_csv(p / "estudo_eventos.csv")
    spec = c["principal"]["dcdh"]

    def g(grupo, l, s=spec):
        return next((r for r in ev if r["especificacao"] == s and r["grupo"] == grupo and r["l"] == str(l)), None)
    agg, ado, aba, sim = g("agregado", "media"), g("adocao", "media"), g("abandono", "media"), g("simetria", "media")
    ps = [float(x["p"]) if x and x["p"] else np.nan for x in (agg, ado, aba)]
    hP = holm([x if np.isfinite(x) else 1.0 for x in ps])
    pl = {k: g(k, -1) for k in ("agregado", "adocao", "abandono")}
    pf = [float(x["p"]) if x and x["p"] else 1.0 for x in (pl["adocao"], pl["abandono"], sim)]
    hF = holm(pf)
    hon = base.ler_csv(p / "honestdid.csv") if (p / "honestdid.csv").exists() else []

    def h(ident, fam, val):
        r = next((x for x in hon if x["id"] == ident and x["familia"] == fam and (fam == "original" or abs(float(x["valor"] or "nan") - val) < 1e-9)), None)
        return f"[{_f(r['lb'])}; {_f(r['ub'])}]" + (" inclui 0" if r["inclui_zero"] == "True" else " exclui 0") if r else "—"
    diag = json.loads((p / "tabelas" / "diagnosticos_identificacao.json").read_text(encoding="utf-8"))
    ide = json.loads((p / "tabelas" / "identificacao_eventos.json").read_text(encoding="utf-8"))
    contrib = base.ler_csv(p / "tabelas" / "contribuicao_orgaos_E3.csv")
    refs = [r for r in base.ler_csv(p / "referencias_alternativas.csv") if r["modelo"] == "FE E3" and r["amostra"].startswith("comum")] \
        if (p / "referencias_alternativas.csv").exists() else []      # P1: etapa de robustez interrompida (memória)
    betas = [float(r["beta_lp"]) for r in refs if r["beta_lp"]]
    pdh = [float(r["p_dif_holm"]) for r in refs if r.get("p_dif_holm")]
    return {"amostra": nome, "rotulo": c["amostras"][nome]["rotulo"], "E1": fe.get("E1"), "E3": fe.get("E3"), "E7": fe.get("E7"),
            "agregado": agg, "adocao": ado, "abandono": aba, "simetria": sim, "holm_P": dict(zip(("agregado", "adocao", "abandono"), hP)),
            "placebo": pl, "holm_F": dict(zip(("placebo1_adocao", "placebo1_abandono", "simetria"), hF)),
            "hon_RM05_agregado": h(f"{spec}|agregado", "RM", 0.5), "hon_RM0_agregado": h(f"{spec}|agregado", "RM", 0.0),
            "hon_SD0_agregado": h(f"{spec}|agregado", "SD", 0.0), "hon_SD0_abandono": h(f"{spec}|abandono", "SD", 0.0),
            "diag": diag, "ident": ide, "top_cnpj_E3": contrib[0] if contrib else None,
            "refs_min": min(betas) if betas else np.nan, "refs_max": max(betas) if betas else np.nan,
            "refs_holm_min": min(pdh) if pdh else np.nan, "variantes": {r["especificacao"]: r for r in ev if r["l"] == "media" and r["grupo"] == "agregado"}}


def gerar(c, nomes, log=print):
    base.verificar_congelamento(c)
    base.estudo_anterior(c)
    from em import svg
    amostras = [n for n in ORDEM if n in nomes + ["cesta"]]
    M = {n: metricas(c, n) for n in amostras}
    # ------------------------------------------------------------------ tabela comparativa
    linhas = []
    for n in amostras:
        m = M[n]
        e1, e3, e7 = m["E1"], m["E3"], m["E7"]
        linhas.append({
            "amostra": n, "produtos": e1["n_produtos"], "itens": e1["n_itens"], "compras": e1["n_compras"], "uasgs": e1["n_uasgs"],
            "orgaos_efetivos_E3": e3["n_efetivo_orgaos"], "eventos_validos": m["ident"]["trocas_por_direcao"],
            "trocas_validas": m["diag"]["eventos_validos"], "eventos_usados_l1": m["diag"]["eventos_usados_l1"],
            "n_efetivo_cnpjs_dcdh": m["diag"]["n_efetivo_cnpjs"],
            "E3_beta": e3["beta_lp"], "E3_ic_inf": e3["ic95_inf"], "E3_ic_sup": e3["ic95_sup"], "E3_p_wcr": e3["p_wcr_webb"],
            "E7_beta": e7["beta_lp"], "E7_ic_inf": e7["ic95_inf"], "E7_ic_sup": e7["ic95_sup"], "E7_p_wcr": e7["p_wcr_webb"],
            "E3_menos_E7": float(e3["beta_lp"]) - float(e7["beta_lp"]),
            "dcdh_beta": m["agregado"]["beta_lp"], "dcdh_ic_inf": m["agregado"]["ic95_inf"], "dcdh_ic_sup": m["agregado"]["ic95_sup"],
            "dcdh_p": m["agregado"]["p"], "dcdh_p_holm": m["holm_P"]["agregado"],
            "adocao_beta": m["adocao"]["beta_lp"], "adocao_p_holm": m["holm_P"]["adocao"],
            "abandono_beta": m["abandono"]["beta_lp"], "abandono_p_holm": m["holm_P"]["abandono"],
            **{f"placebo_{k}_beta": (m["placebo"][k] or {}).get("beta_lp") for k in ("agregado", "adocao", "abandono")},
            **{f"placebo_{k}_ic_inf": (m["placebo"][k] or {}).get("ic95_inf") for k in ("agregado", "adocao", "abandono")},
            **{f"placebo_{k}_ic_sup": (m["placebo"][k] or {}).get("ic95_sup") for k in ("agregado", "adocao", "abandono")},
            **{f"placebo_{k}_p": (m["placebo"][k] or {}).get("p") for k in ("agregado", "adocao", "abandono")},
            "placebo1_abandono_p_holm_F": m["holm_F"]["placebo1_abandono"], "placebo1_adocao_p_holm_F": m["holm_F"]["placebo1_adocao"],
            "honestdid_RM_Mbar0.5_agregado": m["hon_RM05_agregado"], "honestdid_SD_M0_agregado": m["hon_SD0_agregado"],
            "honestdid_SD_M0_abandono": m["hon_SD0_abandono"],
            "sobreposicao_produtos_pre_pos": m["diag"]["sobreposicao_produtos_media"],
            "peso_maior_cnpj_dcdh": m["diag"]["share_top1_cnpj_peso"],
            "maior_cnpj_E3": (m["top_cnpj_E3"] or {}).get("orgao_cnpj"), "participacao_maior_cnpj_E3": (m["top_cnpj_E3"] or {}).get("participacao_variacao_identificadora"),
            "E3_sem_maior_cnpj": (m["top_cnpj_E3"] or {}).get("beta_sem_orgao"),
            "E3_14_referencias_min": m["refs_min"], "E3_14_referencias_max": m["refs_max"], "E3_refs_menor_p_holm_dif": m["refs_holm_min"],
            "dcdh_peso_evento": (m["variantes"].get("dcdh_6m_item_evento") or {}).get("beta_lp"),
            "dcdh_por_compra": (m["variantes"].get("dcdh_6m_compra_celula") or {}).get("beta_lp"),
            "dcdh_12m": (m["variantes"].get("dcdh_12m_item_celula") or {}).get("beta_lp")})
    base.escrever_csv(base.PASTA / "tabelas" / "comparacao_amostras.csv", linhas)
    # ------------------------------------------------------------------ gráficos
    def tri(r):
        return (float(r["beta_lp"]), float(r["ic95_inf"]), float(r["ic95_sup"])) if r and r.get("beta_lp") else None
    cat = ["E3", "E7", "dCDH agregado", "dCDH adoção", "dCDH abandono", "placebo −1 agregado", "placebo −1 abandono"]
    series = [(n, [tri(M[n]["E3"]), tri(M[n]["E7"]), tri(M[n]["agregado"]), tri(M[n]["adocao"]), tri(M[n]["abandono"]),
                   tri(M[n]["placebo"]["agregado"]), tri(M[n]["placebo"]["abandono"])]) for n in amostras]
    (base.PASTA / "graficos").mkdir(exist_ok=True)
    svg.coeficientes(base.PASTA / "graficos" / "comparacao_amostras.svg", "AF − Aberto por amostra (EXPLORATÓRIO)", cat, series,
                     nota="log-pontos; IC95 (CR1 por CNPJ nos efeitos fixos; bootstrap por CNPJ no dCDH)", largura=980)
    dec = base.ler_csv(base.PASTA / "tabelas" / "decomposicao_dcdh.csv") if (base.PASTA / "tabelas" / "decomposicao_dcdh.csv").exists() else []
    decd = base.ler_csv(base.PASTA / "tabelas" / "decomposicao_eventos_orgaos.csv") if (base.PASTA / "tabelas" / "decomposicao_eventos_orgaos.csv").exists() else []
    if dec:
        rot = [f"{r['amostra']}|{r['populacao_eventos']}" for r in decd]
        ser = [("agregado", [tri(next((x for x in dec if x["amostra"] == a.split("|")[0] and x["populacao_eventos"] == a.split("|")[1]
                                        and x["grupo"] == "agregado" and x["l"] == "media"), None)) for a in rot])]
        svg.coeficientes(base.PASTA / "graficos" / "decomposicao_dcdh.svg", "dCDH agregado: amostra própria × eventos da S1", rot, ser,
                         nota="mesmos switchers da S1 (controles inalterados)", largura=980)
    relatorio_md(c, M, linhas, dec, decd, amostras)
    manifesto(c, amostras)
    log("comparação, gráficos, relatório e manifesto gravados")


def relatorio_md(c, M, linhas, dec, decd, amostras):
    cong = json.loads((base.PASTA / "congelamento.json").read_text(encoding="utf-8"))
    comp = base.ler_csv(base.PASTA / "tabelas" / "composicao_conjuntos.csv") if (base.PASTA / "tabelas" / "composicao_conjuntos.csv").exists() else []
    L = ["# Nova rodada exploratória A × AF — cesta P1 validada automaticamente (S1)\n",
         f"Gerado em {base.agora()} por `executar.py comparar`. Protocolo: [`protocolo.md`](protocolo.md); congelamento antes de "
         f"acessar preços: `congelamento.json` ({cong['congelado_em']}); conclusão: [`conclusao.md`](conclusao.md).\n",
         "> **Exploratório.** Esta rodada NÃO é a execução confirmatória do protocolo anterior (que exigia aprovação técnica humana; "
         "a cesta validada humana continua vazia). A população principal é a S1 da validação **automática** de catálogo "
         f"(validador {cong['validacao_automatica']['versao_validador']}, execução `{cong['validacao_automatica']['id_execucao']}`), "
         "que não equivale a validação documental individual. Especificações, janelas, pesos, referências e inferência são "
         "exatamente os do estudo anterior (código reutilizado sem modificação).\n",
         "## 1. Funil (itens homologados, preço positivo, referência A1 válida)\n"]
    fl = []
    for n in amostras:
        f = base.ler_csv((base.PASTA / "amostras" / n / "funil_amostra.csv") if n != "cesta" else base.resolver(c["estudo_anterior"]) / "funil_amostra.csv")
        e1 = M[n]["E1"]
        for r in f:
            fl.append([n, r["etapa"], _n(r["itens"]), _n(r["compras"]), _n(r["produtos"]), _n(r["uasgs"]), _n(r["orgaos_cnpj"])])
        fl.append([n, "8_referencia_A1_valida (amostra analítica)", _n(e1["n_itens"]), _n(e1["n_compras"]), _n(e1["n_produtos"]),
                   _n(e1["n_uasgs"]), _n(e1["n_orgaos"])])
    L.append(_tab(["Amostra", "Etapa", "Itens", "Compras", "Produtos", "UASGs", "CNPJs"], fl))
    L.append("\nNa cesta, a etapa 7 do estudo anterior exigia aprovação humana (0 itens); a amostra analítica dele foi a cesta "
             "candidata (etapa 6 + referência A1). Nas novas amostras, a etapa 7 é a pertença ao conjunto.\n")
    L.append("## 2. Tabela comparativa (amostras próprias)\n")
    t = []
    for r in linhas:
        m = M[r["amostra"]]
        t.append([r["amostra"], _n(r["produtos"]), f"{_n(r['itens'])} / {_n(r['compras'])}", _n(r["uasgs"]), _f(r["orgaos_efetivos_E3"], 1),
                  f"{_n(r['trocas_validas'])} ({_n(r['eventos_usados_l1'])} em l=1)",
                  _ic(m["E3"]), _ic(m["E7"]), _ic(m["agregado"]), _f(r["dcdh_p_holm"], 3),
                  _ic(m["placebo"]["agregado"]), r["honestdid_RM_Mbar0.5_agregado"],
                  _f(100 * float(r["sobreposicao_produtos_pre_pos"]), 1) + "%", _f(100 * float(r["peso_maior_cnpj_dcdh"]), 1) + "%"])
    L.append(_tab(["Amostra", "Produtos", "Itens / compras", "UASGs", "Órgãos efetivos (E3)", "Trocas válidas", "E3 (IC95)", "E7 (IC95)",
                   "dCDH agregado (IC95)", "p Holm (P)", "Placebo −1 agregado (IC95)", "HonestDiD RM M̄=0,5", "Sobreposição pré/pós",
                   "Peso maior CNPJ (dCDH)"], t))
    L.append("\nlp = log-pontos (100·Δln); % exato = 100(e^{β/100} − 1). Detalhes em `tabelas/comparacao_amostras.csv`.\n")
    L.append("### Adoção × abandono e placebos\n")
    t2 = []
    for r in linhas:
        m = M[r["amostra"]]
        t2.append([r["amostra"], _ic(m["adocao"]), _f(r["adocao_p_holm"], 3), _ic(m["abandono"]), _f(r["abandono_p_holm"], 3),
                   _ic(m["placebo"]["adocao"]), _f(r["placebo1_adocao_p_holm_F"], 3), _ic(m["placebo"]["abandono"]),
                   _f(r["placebo1_abandono_p_holm_F"], 3), r["honestdid_SD_M0_abandono"]])
    L.append(_tab(["Amostra", "Adoção", "Holm P", "Abandono", "Holm P", "Placebo −1 adoção", "Holm F", "Placebo −1 abandono", "Holm F",
                   "HonestDiD SD M=0 (abandono)"], t2))
    L.append("\n### Ponderação, janela, órgão dominante e referências\n")
    t3 = [[r["amostra"], _f(r["dcdh_beta"]), _f(r["dcdh_peso_evento"]), _f(r["dcdh_por_compra"]), _f(r["dcdh_12m"]),
           f"{r['maior_cnpj_E3']} ({_f(100 * float(r['participacao_maior_cnpj_E3'] or 'nan'), 1)}%)", _f(r["E3_sem_maior_cnpj"]),
           _f(r["n_efetivo_cnpjs_dcdh"], 1), f"{_f(r['E3_14_referencias_min'])} a {_f(r['E3_14_referencias_max'])}",
           _f(r["E3_refs_menor_p_holm_dif"], 3)] for r in linhas]
    L.append(_tab(["Amostra", "dCDH célula", "dCDH peso por evento", "dCDH por compra", "dCDH 12m", "Maior CNPJ na variação de E3",
                   "E3 sem ele", "CNPJs efetivos (dCDH)", "E3 nas 14 referências (comum)", "menor p Holm das diferenças"], t3))
    if dec:
        L.append("\n## 3. Decomposição: eventos comuns, seleção de produtos e órgãos\n")
        td = []
        for d in decd:
            x = next((r for r in dec if r["amostra"] == d["amostra"] and r["populacao_eventos"] == d["populacao_eventos"]
                      and r["grupo"] == "agregado" and r["l"] == "media"), None)
            pl = next((r for r in dec if r["amostra"] == d["amostra"] and r["populacao_eventos"] == d["populacao_eventos"]
                       and r["grupo"] == "agregado" and r["l"] == "-1"), None)
            td.append([d["amostra"], d["populacao_eventos"], _ic(x), _ic(pl), _n(d["eventos_l1"]), _n(d["cnpjs"]), _f(d["n_efetivo_cnpjs"], 1),
                       _f(100 * float(d["peso_maior_cnpj"]), 1) + "%", _n(d["itens_amostra"])])
        L.append(_tab(["Amostra", "Eventos", "dCDH agregado (IC95)", "Placebo −1 (IC95)", "Eventos l=1", "CNPJs", "CNPJs efetivos",
                       "Peso maior CNPJ", "Itens"], td))
        L.append("\n'eventos_S1' = mesmos switchers (UASGs) com peso na S1; controles inalterados. A diferença cesta → S1 se decompõe "
                 "em redução de eventos (cesta|eventos_S1 − cesta|propria) e seleção de produtos dentro dos mesmos eventos "
                 "(S1|propria − cesta|eventos_S1).\n")
    if comp:
        L.append("## 4. Composição dos conjuntos (diagnóstico; não altera a classificação)\n")
        L.append(_tab(["Grupo", "Produtos", "Itens", "Compras", "UASGs", "Compras/produto (mediana)", "Quantidade (mediana)",
                       "Órgãos efetivos", "Maior órgão", "Fração de compras AF", "Classe mais frequente"],
                      [[x["grupo"], _n(x["produtos"]), _n(x["itens"]), _n(x["compras"]), _n(x["uasgs"]), _f(x["compras_por_produto_mediana"], 0),
                        _f(x["quantidade_mediana"], 0), _f(x["n_efetivo_orgaos"], 1), _f(100 * float(x["participacao_maior_orgao"]), 1) + "%",
                        _f(100 * float(x["fracao_compras_AF"]), 1) + "%", x["classe_catalogo_mais_frequente"]] for x in comp]))
        L.append("\nClasses, anos e categorias de risco por grupo: `tabelas/composicao_classes.csv`, `composicao_anos.csv`, "
                 "`composicao_riscos.csv`.\n")
    L.append("## 5. Arquivos\n")
    L.append("- `amostras/<amostra>/`: saídas completas do código do estudo anterior para cada amostra (efeitos_fixos.csv, "
             "estudo_eventos.csv, honestdid.csv, referencias_alternativas.csv, robustez.csv, descritivas.csv, tabelas/, funil).\n"
             "- `tabelas/`: comparação, decomposição, composição, conjuntos. `graficos/`: comparação e decomposição.\n"
             "- Reprodução: `..\\..\\.venv\\Scripts\\python.exe executar.py tudo` (≈ horas; usa a amostra analítica do estudo anterior, "
             "congelada por SHA-256).\n")
    (base.PASTA / "relatorio.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def manifesto(c, amostras):
    cong = json.loads((base.PASTA / "congelamento.json").read_text(encoding="utf-8"))
    out = {"gerado_em": base.agora(), "versao": c["versao"], "caracter": "EXPLORATÓRIO — não é execução confirmatória do protocolo anterior",
           "populacao_principal": "S1 (AUTO_VALIDADO_CATALOGO, validação automática de catálogo)", "congelamento": cong,
           "codigo": {p.name: base.sha(p) for p in sorted((base.PASTA / "rodada").glob("*.py"))} | {"executar.py": base.sha(base.PASTA / "executar.py")},
           "amostras": {}}
    for n in amostras:
        p = _saida(c, n)
        out["amostras"][n] = {"pasta": str(p), "saidas": {f.name: base.sha(f) for f in sorted(p.glob("*.csv"))},
                              "registros": sorted(x.name for x in (p / "registros").glob("*.json")) if (p / "registros").exists() else []}
    out["tabelas"] = {f.name: base.sha(f) for f in sorted((base.PASTA / "tabelas").glob("*.csv"))}
    if (base.PASTA / "resultado_testes.json").exists():
        out["testes"] = json.loads((base.PASTA / "resultado_testes.json").read_text(encoding="utf-8"))
    base.escrever_json(base.PASTA / "manifesto.json", out)
