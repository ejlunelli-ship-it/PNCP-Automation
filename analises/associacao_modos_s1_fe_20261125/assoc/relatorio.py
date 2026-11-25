"""Relatório, gráficos e manifesto."""
from pathlib import Path

import numpy as np
import pandas as pd

from . import comum
from .comum import GRA, PASTA, RES, TAB

MODELOS = ["M1", "M2", "M3", "M4", "M5"]


def f(v, d=2):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "—"
    if not np.isfinite(v):
        return "—"
    return f"{v:.{d}f}".replace(".", ",").replace("-", "−")


def n(v):
    try:
        return f"{int(v):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "—"


def pval(p):
    try:
        p = float(p)
    except (TypeError, ValueError):
        return "—"
    if not np.isfinite(p):
        return "—"
    return "< 0,001" if p < 0.001 else f(p, 3)


def ic(a, b):
    return "—" if not (np.isfinite(float(a)) and np.isfinite(float(b))) else f"[{f(a)}; {f(b)}]"


def robusta(r, regra_G=20):
    g = r.G_css_rho1 if np.isfinite(r.G_css_rho1) else r.G_css_rho0
    ok = (r.p_cr1 < 0.05) and (r.p_wcr_webb < 0.05) and g >= regra_G
    motivo = []
    if not r.p_cr1 < 0.05:
        motivo.append("CR1 não rejeita")
    if not r.p_wcr_webb < 0.05:
        motivo.append("WCR não rejeita")
    if g < regra_G:
        motivo.append(f"G* = {f(g, 1)} < {regra_G}")
    return ("sim" if ok else "não"), "; ".join(motivo) or "—"


def graficos(R, loo):
    from em.svg import coeficientes
    vs = ["principal", "sem_lnq", "peso_igual_por_compra", "sem_trimestres_incompletos"]
    ser = []
    for v in vs:
        s = []
        for M in MODELOS:
            r = R[(R.modelo == M) & (R.variante == v)]
            s.append((r.beta_lp.iat[0], r.ic95_inf.iat[0], r.ic95_sup.iat[0]) if len(r) else None)
        ser.append((v.replace("_", " "), s))
    coeficientes(GRA / "coeficientes_M1_M5.svg", "Coeficiente AF (lp, IC95 CR1 por CNPJ) — M1 a M5", MODELOS, ser,
                 nota="associação condicional; amostras próprias de cada modelo")
    ser = []
    for v in ("principal", "amostra_comum_M3", "amostra_comum_M5"):
        s = []
        for M in MODELOS:
            r = R[(R.modelo == M) & (R.variante == v)]
            s.append((r.beta_lp.iat[0], r.ic95_inf.iat[0], r.ic95_sup.iat[0]) if len(r) else None)
        ser.append((v.replace("_", " "), s))
    coeficientes(GRA / "amostras_comuns.svg", "Coeficiente AF em amostras próprias e comuns (lp, IC95)", MODELOS, ser,
                 nota="amostra comum M5 = obs. identificáveis em UASG × produto × trimestre")
    if len(loo):
        s = [(loo[loo.modelo == M].beta_sem.median(), loo[loo.modelo == M].beta_sem.min(), loo[loo.modelo == M].beta_sem.max()) for M in MODELOS]
        b = [(R[(R.modelo == M) & (R.variante == "principal")].beta_lp.iat[0], np.nan, np.nan) for M in MODELOS]
        coeficientes(GRA / "exclusao_top10_cnpj.svg", "Exclusão de cada um dos 10 CNPJs mais influentes (mín.–máx.)", MODELOS,
                     [("sem um CNPJ (mediana, mín., máx.)", s), ("estimativa completa", b)], nota="reestimação integral a cada exclusão")


def gerar(c, log):
    GRA.mkdir(exist_ok=True)
    R = pd.read_csv(TAB / "modelos.csv", dtype={"top1_cnpj": str})
    cel = pd.read_csv(TAB / "celulas_dois_modos.csv", dtype={"top1_cnpj_celulas": str})
    cc = pd.read_csv(TAB / "contribuicao_cnpj.csv", dtype={"cnpj": str})
    cu = pd.read_csv(TAB / "contribuicao_uf.csv")
    loo = pd.read_csv(TAB / "loo_top10_cnpj.csv", dtype={"cnpj_excluido": str}) if (TAB / "loo_top10_cnpj.csv").exists() else pd.DataFrame()
    ver = pd.read_csv(TAB / "verificacao_convergencia.csv") if (TAB / "verificacao_convergencia.csv").exists() else pd.DataFrame()
    fun = pd.read_csv(TAB / "funil_amostra.csv")
    cob = pd.read_csv(TAB / "cobertura_trimestres.csv")
    ag = comum.ler_json(RES / "amostra_resumo.json")
    te = comum.ler_json(RES / "resultado_testes.json") if (RES / "resultado_testes.json").exists() else {}
    graficos(R, loo)
    P = R[R.variante == "principal"].set_index("modelo")
    L = []
    a = L.append
    a("# Associação entre os modos Aberto e Aberto-Fechado e o preço homologado — cesta S1, efeitos fixos M1–M5\n")
    a(f"Gerado em {comum.agora()} por `python executar.py`. **Todas as estimativas são associações condicionais**; nenhuma "
      "tem interpretação causal automática (a escolha do modo é endógena). "
      f"Testes automatizados: {te.get('testes', '?')} executados, {te.get('falhas', '?')} falhas, {te.get('erros', '?')} erros.\n")
    a("## 1. Dados e amostra\n")
    b = ag["banco"]
    a(f"- **Banco:** `{b['caminho']}`, aberto só para leitura; a impressão digital confere com a registrada pelo estudo original.")
    a("- **Itens:** vêm da amostra S1 da rodada `efeito_modos_cesta_auto_S1_20261125`. Foram reconferidos compra a compra contra "
      "a tabela `compras` do banco:")
    a("  - 74.167 compras, todas de Compras.gov.br e Pregão Eletrônico;")
    a("  - 0 divergências de modo, UASG, CNPJ e UF.")
    a("- **Referência externa:** a amostra é **anterior** ao filtro A1 (sem exigência de referência e sem a máscara |Y| ≤ ln 10).")
    a(f"- **UF:** {ag['uf']} **Limitação:** a dimensão geográfica é a da unidade compradora, não a do local de entrega.")
    a(f"- **Unidade de observação:** compra × produto S1, com {n(ag['observacoes'])} observações.")
    a(f"  - {n(ag['com_itens_duplicados'])} observações reúnem {n(ag['itens_em_duplicados'])} itens duplicados da mesma compra e "
      "produto, agregados por preço unitário médio ponderado pela quantidade.")
    a(f"  - Média simples por falta de quantidade: {n(ag['media_simples_por_quantidade_ausente'])}.")
    a("- **Modo:** é atributo da compra; um único modo por compra, verificado.")
    a("- **Período:** todo o período com preço (2023T2–2026T3), sem corte arbitrário. 2026T2 (CATMAT só até 17/04/2026) e 2026T3 "
      f"(residual) são incompletos, com {n(ag['obs_em_trimestres_incompletos'])} observações; ficam na principal e saem numa sensibilidade.\n")
    a("| Etapa | Critério | Itens | Compras | Produtos | UASGs | CNPJs | UFs |\n|---|---|---:|---:|---:|---:|---:|---:|")
    for r in fun.itertuples():
        a(f"| {r.etapa} | {r.criterio} | {n(r.itens)} | {n(r.compras)} | {n(r.produtos)} | {n(r.uasgs)} | {n(r.cnpjs)} | {n(r.ufs)} |")
    a("\n## 2. Controlar por CNPJ não é comparar só compras do mesmo CNPJ\n")
    a("- **M1** (UF × produto × trimestre + CNPJ) usa **todas** as observações elegíveis.")
    a("  - Compara cada compra com as demais do mesmo produto, na mesma UF e no mesmo trimestre, **de qualquer órgão**, depois "
      "de remover o nível médio de preço de cada CNPJ, estimado com todas as compras do órgão (todos os produtos e trimestres).")
    a("  - Uma compra AF do órgão g pode ser comparada com uma compra A do órgão h. Basta que o efeito fixo de g e o de h estejam "
      "identificados por outras compras, o que vale mesmo em células sem os dois modos. Não restringimos a amostra a células mistas.")
    a("  - A hipótese é aditiva: as diferenças de nível entre órgãos são as mesmas em todos os produtos e trimestres.")
    a("- **M2** troca o nível do órgão pelo nível do órgão **em cada produto** (CNPJ × produto).")
    a("- **M3** (CNPJ × produto × trimestre) compara **apenas** compras do mesmo órgão, do mesmo produto e no mesmo trimestre, ou "
      "seja, UASGs diferentes do mesmo órgão ou a mesma UASG em compras distintas. Só identificam as células com os dois modos.")
    a("- **M4** acrescenta UASG. A variação passa a ser dentro do órgão e líquida do nível de cada UASG.")
    a("- **M5** (UASG × produto × trimestre) compara compras da **mesma UASG**, do mesmo produto e trimestre.\n")
    a("## 3. Resultados principais (com ln q, peso por observação, amostra própria)\n")
    a("| Modelo | Efeitos fixos | β (lp) | % exata | IC95 CR1 CNPJ | p CR1 | p WCR (Webb) | IC95 WCU | EP CGM CNPJ+produto | EP CR1 UF | γ ln q |\n"
      "|---|---|---:|---:|---|---:|---:|---|---:|---:|---:|")
    for M in MODELOS:
        r = P.loc[M]
        a(f"| {M} | {r.descricao} | **{f(r.beta_lp)}** | {f(r.pct_exato)}% | {ic(r.ic95_inf, r.ic95_sup)} | {pval(r.p_cr1)} | {pval(r.p_wcr_webb)} | "
          f"{ic(r.ic_wcu_inf, r.ic_wcu_sup)} | {f(r.ep_cgm_cnpj_produto)} | {f(r.ep_cr1_uf)} | {f(r.gamma_lnq)} |")
    a("\n| Modelo | Obs. | Singletons removidos | Compras | Produtos | UASGs | CNPJs | UFs | Var. identificadora (% da var. de AF) | Nº ef. CNPJs (G*, ρ=0) | G* ρ=1 | Nº ef. UFs | CNPJ mais influente | UF mais influente |\n"
      "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|")
    for M in MODELOS:
        r = P.loc[M]
        a(f"| {M} | {n(r.obs)} | {n(r.singletons_removidos)} | {n(r.compras)} | {n(r.produtos)} | {n(r.uasgs)} | {n(r.cnpjs)} | {n(r.ufs)} | "
          f"{f(100 * r.variancia_identificadora_relativa, 1)}% | {f(r.n_efetivo_cnpjs, 1)} | {f(r.G_css_rho1, 1)} | {f(r.n_efetivo_ufs, 1)} | "
          f"{r.nome_top1_cnpj} ({f(100 * r.share_top1_cnpj, 1)}%) | {r.top1_uf} ({f(100 * r.share_top1_uf, 1)}%) |")
    a("\nG* ρ = 1 não é definido quando o efeito fixo está aninhado no CNPJ (M3 e M4): o choque comum do órgão é absorvido.\n")
    a("## 4. Variantes\n")
    a("| Modelo | principal | sem ln q | peso igual por compra | sem trimestres incompletos |\n|---|---|---|---|---|")
    for M in MODELOS:
        cel_ = []
        for v in ("principal", "sem_lnq", "peso_igual_por_compra", "sem_trimestres_incompletos"):
            r = R[(R.modelo == M) & (R.variante == v)].iloc[0]
            cel_.append(f"{f(r.beta_lp)} {ic(r.ic95_inf, r.ic95_sup)} (n = {n(r.obs)})")
        a(f"| {M} | " + " | ".join(cel_) + " |")
    a("\n## 5. Amostras comuns\n")
    a("- A amostra de M5 (observações identificáveis em UASG × produto × trimestre) está contida na de todos os outros modelos.")
    a("- A amostra de M3 está contida nas de M1, M2 e M4.")
    a("- Cada modelo é reestimado nessas amostras, com ln q.\n")
    a("| Modelo | própria | comum M3 | comum M5 |\n|---|---|---|---|")
    for M in MODELOS:
        cel_ = []
        for v in ("principal", "amostra_comum_M3", "amostra_comum_M5"):
            r = R[(R.modelo == M) & (R.variante == v)]
            cel_.append("—" if not len(r) else f"{f(r.beta_lp.iat[0])} {ic(r.ic95_inf.iat[0], r.ic95_sup.iat[0])} (n = {n(r.obs.iat[0])}; G* = {f(r.n_efetivo_cnpjs.iat[0], 1)})")
        a(f"| {M} | " + " | ".join(cel_) + " |")
    a("\n## 6. Células com os dois modos e suporte de M3, M4 e M5\n")
    a("| Modelo | Célula | Células | Com A e AF | Obs. nelas | Compras nelas | Obs. em células de um só modo | Compras só em células de um modo | CNPJs com células mistas | Nº ef. CNPJs (células) | Maior CNPJ (células) |\n"
      "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    nomes = comum.ler_pkl(comum.trabalho(c, "amostra_compra_produto.pkl.gz"))["nomes"]
    for r in cel.itertuples():
        a(f"| {r.modelo} | {r.celula} | {n(r.celulas)} | {n(r.celulas_com_A_e_AF)} | {n(r.obs_em_celulas_com_A_e_AF)} | {n(r.compras_em_celulas_com_A_e_AF)} | "
          f"{n(r.obs_em_celulas_de_um_so_modo)} | {n(r.compras_so_em_celulas_de_um_so_modo)} | {n(r.cnpjs_com_celulas_mistas)} | {f(r.n_efetivo_cnpjs_celulas, 1)} | "
          f"{f(100 * r.share_top1_cnpj_celulas, 1)}% ({str(nomes.get(str(r.top1_cnpj_celulas), ''))[:28]}) |")
    base_obs = ag["observacoes"]
    a("\n**Perdas até a célula identificadora** (das " + n(base_obs) + " observações e " + n(fun.compras.iloc[-1]) + " compras da amostra):\n")
    a("| Modelo | Obs. após singletons | Obs. em células com A e AF | % da amostra | Compras em células com A e AF | % das compras |\n|---|---:|---:|---:|---:|---:|")
    for M, celn in (("M3", "cnpj_prod_tri"), ("M4", "cnpj_prod_tri"), ("M5", "uasg_prod_tri")):
        r = cel[(cel.modelo == M) & (cel.celula == celn)].iloc[0]
        a(f"| {M} | {n(P.loc[M].obs)} | {n(r.obs_em_celulas_com_A_e_AF)} | {f(100 * r.obs_em_celulas_com_A_e_AF / base_obs, 1)}% | "
          f"{n(r.compras_em_celulas_com_A_e_AF)} | {f(100 * r.compras_em_celulas_com_A_e_AF / fun.compras.iloc[-1], 1)}% |")
    a("\n## 7. Contribuição à variação identificadora\n")
    a("Participação de cada CNPJ em Σ x̃², onde x̃ é AF residualizado nos efeitos fixos e em ln q:\n")
    a("| Modelo | 1º | 2º | 3º | 4º | 5º | top 5 | top 10 |\n|---|---|---|---|---|---|---:|---:|")
    for M in MODELOS:
        s = cc[cc.modelo == M].sort_values("ordem")
        top = [f"{str(x.orgao)[:26]} {f(100 * x.participacao, 1)}%" for x in s.head(5).itertuples()]
        a(f"| {M} | " + " | ".join(top) + f" | {f(100 * s.head(5).participacao.sum(), 1)}% | {f(100 * s.head(10).participacao.sum(), 1)}% |")
    a("\n| Modelo | UFs mais influentes |\n|---|---|")
    for M in MODELOS:
        s = cu[cu.modelo == M].sort_values("ordem").head(5)
        a(f"| {M} | " + ", ".join(f"{x.uf} {f(100 * x.participacao, 1)}%" for x in s.itertuples()) + " |")
    if len(loo):
        a("\n## 8. Exclusão de cada um dos 10 CNPJs mais influentes (reestimação integral)\n")
        a("| Modelo | β completo | β mín. sem 1 CNPJ | β máx. sem 1 CNPJ | CNPJ cuja exclusão mais muda β | mudança |\n|---|---:|---:|---:|---|---:|")
        for M in MODELOS:
            s = loo[loo.modelo == M]
            k = s.loc[s.mudanca.abs().idxmax()]
            a(f"| {M} | {f(s.beta_base.iat[0])} | {f(s.beta_sem.min())} | {f(s.beta_sem.max())} | {str(k.orgao)[:40]} | {f(k.mudanca)} |")
        a("\nTabela completa: `tabelas/loo_top10_cnpj.csv`.\n")
    a("## 9. Inferência\n")
    a(f"- **Regra predefinida (config.json):** {c['inferencia']['regra']}.")
    a("- **CR1 por CNPJ:** agrupa todas as compras e UASGs do mesmo órgão. É apresentado como referência, não como definitivo.")
    a("- **WCR:** bootstrap selvagem restrito por CNPJ (Webb, 9.999 réplicas), com IC WCU percentil-t.")
    a("- **CGM:** variância bidirecional CNPJ + produto. Também há CR1 por UF (27 clusters).")
    a("- **Número efetivo de clusters:** de Carter, Schnepel e Steigerwald (2017).")
    a("- **Limites do bootstrap:** quando poucos órgãos concentram a variação, o WCR também pode ter tamanho incorreto "
      "(MacKinnon e Webb, 2017). Por isso as exclusões de CNPJ entram na avaliação.\n")
    a("| Modelo | p CR1 | p WCR | G* usado | Significância robusta pela regra? | Motivo |\n|---|---:|---:|---:|---|---|")
    for M in MODELOS:
        r = P.loc[M]
        g = r.G_css_rho1 if np.isfinite(r.G_css_rho1) else r.G_css_rho0
        s, mot = robusta(r)
        a(f"| {M} | {pval(r.p_cr1)} | {pval(r.p_wcr_webb)} | {f(g, 1)} | {s} | {mot} |")
    if len(ver):
        a("\n## 10. Convergência numérica\n")
        a("- Efeitos fixos múltiplos: LSMR esparso seguido de projeções alternadas até a variação máxima ficar abaixo de 10⁻⁹. "
          "Verificação: maior média ponderada residual em qualquer grupo de qualquer efeito fixo.")
        a("- Conferência independente por projeções alternadas puras:\n")
        a("| Modelo | β LSMR+MAP | β MAP | diferença | iterações MAP | média residual máx. (LSMR / MAP) |\n|---|---:|---:|---:|---:|---|")
        for r in ver.itertuples():
            a(f"| {r.modelo} | {r.beta_lsmr_map:.6f} | {r.beta_map:.6f} | {r.diferenca:.2e} | {n(r.iteracoes_map)} | {r.max_media_residual_lsmr:.1e} / {r.max_media_residual_map:.1e} |")
    a("\n## 11. Leitura\n")
    a("Ver `conclusao.md`. Gráficos em `graficos/`; tabelas completas em `tabelas/`.\n")
    (PASTA / "relatorio.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    arqs = {}
    for pasta in ("assoc", "tabelas", "resultados", "graficos", "testes"):
        for p in sorted((PASTA / pasta).glob("*")):
            if p.is_file() and p.suffix != ".pyc":
                arqs[f"{pasta}/{p.name}"] = comum.sha(p)
    for nm in ("config.json", "executar.py", "README.md", "relatorio.md", "conclusao.md", "metodologia.md"):
        if (PASTA / nm).exists():
            arqs[nm] = comum.sha(PASTA / nm)
    trab = {p.name: comum.sha(p) for p in sorted(Path(c["trabalho"]).glob("*.pkl.gz"))}
    comum.escrever_json(PASTA / "manifesto.json", {"gerado_em": comum.agora(), "arquivos": arqs, "trabalho_D": trab})
    log("relatório e manifesto gerados")
