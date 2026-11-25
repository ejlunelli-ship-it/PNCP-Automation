"""Etapa 19: gráficos (SVG sem dependências), relatório e manifesto."""
from html import escape
from pathlib import Path

import numpy as np
import pandas as pd

from . import comum
from .comum import PASTA

TAB, RES, GRA = PASTA / "tabelas", PASTA / "resultados", PASTA / "graficos"
FASE_I = ["desenho.py", "construir_risk_sets.py", "construir_covariaveis.py", "estimar_propensao.py", "realizar_matching.py",
          "diagnosticar_balanceamento.py", "executar_placebos.py", "estimar_did.py", "inferencia.py", "pipeline.py",
          "construir_painel.py", "identificar_eventos.py", "verificar_fontes.py", "comum.py", "config.json"]
COR = ["#2b6cb0", "#c05621", "#2f855a", "#6b46c1", "#b7791f"]


def _svg(w, h, corpo, titulo):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" font-family="Segoe UI, Arial" font-size="12">'
            f'<rect width="100%" height="100%" fill="white"/><text x="{w / 2}" y="22" text-anchor="middle" font-size="15" '
            f'font-weight="600">{escape(titulo)}</text>' + "".join(corpo) + "</svg>")


def barras_h(caminho, titulo, rotulos, valores, nota=""):
    w, lh, m_esq = 860, 22, 430
    h = 60 + lh * len(rotulos) + 20
    vmax = max(max(valores), 1)
    W = w - m_esq - 60
    c = []
    for i, (r, v) in enumerate(zip(rotulos, valores)):
        y = 40 + i * lh
        c.append(f'<text x="{m_esq - 6}" y="{y + 14}" text-anchor="end">{escape(str(r))}</text>')
        c.append(f'<rect x="{m_esq}" y="{y + 3}" width="{W * v / vmax:.1f}" height="{lh - 6}" fill="{COR[0]}"/>')
        c.append(f'<text x="{m_esq + W * v / vmax + 4:.1f}" y="{y + 14}">{v:g}</text>')
    if nota:
        c.append(f'<text x="{w - 10}" y="{h - 6}" text-anchor="end" font-size="10" fill="#666">{escape(nota)}</text>')
    Path(caminho).write_text(_svg(w, h, c, titulo), encoding="utf-8")


def love_plot(caminho, titulo, b):
    b = b.dropna(subset=["smd_antes"]).reset_index(drop=True)
    w, lh, m_esq = 760, 16, 210
    h = 70 + lh * len(b) + 30
    lim = max(1.0, float(np.nanmax(np.abs(b[["smd_antes", "smd_depois"]].to_numpy()))))
    W = w - m_esq - 40
    x = lambda v: m_esq + W * (v + lim) / (2 * lim)
    c = [f'<line x1="{x(0):.1f}" x2="{x(0):.1f}" y1="40" y2="{h - 30}" stroke="#888"/>']
    for v in (-0.1, 0.1):
        c.append(f'<line x1="{x(v):.1f}" x2="{x(v):.1f}" y1="40" y2="{h - 30}" stroke="#bbb" stroke-dasharray="3 3"/>')
    for i, r in b.iterrows():
        y = 48 + i * lh
        c.append(f'<text x="{m_esq - 6}" y="{y + 4}" text-anchor="end" font-size="10">{escape(r.covariavel)}</text>')
        c.append(f'<circle cx="{x(r.smd_antes):.1f}" cy="{y}" r="3.5" fill="none" stroke="{COR[1]}"/>')
        if r.smd_depois == r.smd_depois:
            c.append(f'<circle cx="{x(r.smd_depois):.1f}" cy="{y}" r="3.5" fill="{COR[0]}"/>')
    c.append(f'<text x="{m_esq}" y="{h - 10}" font-size="11">○ antes (tratadas × candidatas)   ● depois (tratadas × controles pareados)   '
             f'tracejado: |SMD| = 0,10   eixo: ±{lim:.2f}</text>')
    Path(caminho).write_text(_svg(w, h, c, titulo), encoding="utf-8")


def histogramas(caminho, titulo, a, b, rot_a, rot_b, bins=30):
    w, h, m = 760, 360, 50
    lo, hi = float(np.nanmin(np.concatenate([a, b]))), float(np.nanmax(np.concatenate([a, b])))
    e = np.linspace(lo, hi, bins + 1)
    ha = np.histogram(a, e)[0] / max(len(a), 1)
    hb = np.histogram(b, e)[0] / max(len(b), 1)
    ym = max(ha.max(), hb.max(), 1e-9)
    W, H = w - 2 * m, h - 2 * m - 20
    c = []
    for k in range(bins):
        x0 = m + W * k / bins
        bw = W / bins
        c.append(f'<rect x="{x0:.1f}" y="{m + H - H * ha[k] / ym:.1f}" width="{bw:.1f}" height="{H * ha[k] / ym:.1f}" fill="{COR[1]}" fill-opacity="0.45"/>')
        c.append(f'<rect x="{x0:.1f}" y="{m + H - H * hb[k] / ym:.1f}" width="{bw:.1f}" height="{H * hb[k] / ym:.1f}" fill="{COR[0]}" fill-opacity="0.6"/>')
    for k in range(6):
        v = lo + (hi - lo) * k / 5
        c.append(f'<text x="{m + W * k / 5:.1f}" y="{m + H + 16}" text-anchor="middle">{v:.1f}</text>')
    c.append(f'<text x="{m}" y="{h - 12}">laranja: {escape(rot_a)} (n = {len(a)})   azul: {escape(rot_b)} (n = {len(b)})   eixo x: logit do PS</text>')
    Path(caminho).write_text(_svg(w, h, c, titulo), encoding="utf-8")


def trajetorias(caminho, titulo, P, pares, rels=range(-6, 2)):
    from .estimar_did import PainelPos
    V = PainelPos(P)
    T, Cc = {r: [] for r in rels}, {r: [] for r in rels}
    for ide, g in pares.groupby("id_evento"):
        t0, u, s = int(g.t0.iat[0]), int(g.u_tratada.iat[0]), int(g.sinal_af.iat[0])
        for r in rels:
            y = V.col("Yc", t0 + r)
            if np.isfinite(y[u]):
                T[r].append(y[u])
            yc = y[g.u_controle.to_numpy()]
            ok = np.isfinite(yc)
            if ok.any():
                Cc[r].append(float(np.mean(yc[ok])))
    from em.svg import coeficientes
    ser = [("tratadas", [(np.mean(T[r]), np.nan, np.nan) if T[r] else None for r in rels]),
           ("controles pareados (média do evento)", [(np.mean(Cc[r]), np.nan, np.nan) if Cc[r] else None for r in rels])]
    coeficientes(caminho, titulo, [f"t{r:+d}" if r else "t0" for r in rels], ser, eixo_y="índice A1 (log-pontos)",
                 nota="médias simples entre eventos com índice observado no período; t−6..t−3 formação, t−2..t−1 reservados")
    return {r: (len(T[r]), len(Cc[r])) for r in rels}


def _f(v, d=2):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "—"
    return "—" if not np.isfinite(v) else f"{v:.{d}f}".replace(".", ",").replace("-", "−")


def _ic(a, b):
    return "—" if not (np.isfinite(float(a)) and np.isfinite(float(b))) else f"[{_f(a)}; {_f(b)}]"


def _n(x):
    return f"{int(x):,}".replace(",", ".")


def md_tabela(df, cols, nomes=None):
    nomes = nomes or cols
    l = ["| " + " | ".join(nomes) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        cel = []
        for c in cols:
            v = r[c]
            if isinstance(v, str) and v.startswith("["):
                v = v.replace(".", ",").replace("-", "−")
            cel.append(_f(v) if isinstance(v, (float, np.floating)) else ("—" if v is None or v != v else str(v)))
        l.append("| " + " | ".join(cel) + " |")
    return "\n".join(l)


def executar(c, log):
    from em.svg import coeficientes
    GRA.mkdir(exist_ok=True)
    prot = comum.ler_json(RES / "protocolo_congelado.json")
    atual = comum.hashes_codigo()
    integ = [{"arquivo": n, "hash_no_congelamento": prot["codigo_sha256"].get(n), "hash_atual": atual.get(n),
              "igual": prot["codigo_sha256"].get(n) == atual.get(n)} for n in FASE_I]
    comum.escrever_csv(TAB / "integridade_codigo_fase_I.csv", integ)
    fontes = comum.ler_json(RES / "fontes.json")
    painel = comum.ler_json(RES / "painel_resumo.json")["S1"]
    evr = comum.ler_json(RES / "eventos_resumo.json")
    diag = comum.ler_json(RES / "diagnostico_desenho.json")
    f2 = comum.ler_json(RES / "fase2_resumo.json")
    testes = comum.ler_json(RES / "resultado_testes.json") if (RES / "resultado_testes.json").exists() else {}
    funil = pd.read_csv(TAB / "funil_suporte.csv")
    viab = pd.read_csv(TAB / "viabilidade_regras_alternativas.csv")
    plc = pd.read_csv(TAB / "placebos_reservados.csv")
    efe = pd.read_csv(TAB / "efeitos.csv")
    comp = pd.read_csv(TAB / "comparacao_desenhos.csv")
    bal = pd.read_csv(TAB / "balanceamento.csv")
    conc = pd.read_csv(TAB / "concentracao_controles.csv")
    psd = pd.read_csv(TAB / "propensao_diagnosticos.csv")
    aud = pd.read_csv(TAB / "composicao_auditoria.csv")
    rtm = pd.read_csv(TAB / "regressao_media.csv")
    desc = pd.read_csv(TAB / "eventos_descartados_e_mantidos.csv")
    cens = pd.read_csv(TAB / "censura_controles_t0+1.csv")
    cob = pd.read_csv(TAB / "cobertura_indice_trimestres.csv")
    # gráficos
    fp = funil[(funil.desenho == "principal") & (funil.metodo == "M0") & (funil.direcao == "todas")]
    barras_h(GRA / "funil_suporte_principal.svg", "Funil de suporte — desenho principal (M0)", fp.etapa.tolist(), fp.eventos.tolist(),
             "eventos inequívocos A↔AF com t0 entre 2024T4 e 2026T1")
    barras_h(GRA / "viabilidade_regras.svg", "Eventos que sobreviveriam sob regras alternativas (diagnóstico, sem estimação)",
             [f"{r.regime[:10]}: {r.regra[:48]}" for r in viab.itertuples()], viab.eventos.tolist(), "t0 entre 2024T4 e 2026T1")
    b = bal[(bal.desenho == "principal") & (bal.metodo == "M0") & (bal.direcao == "A->AF")]
    love_plot(GRA / "balanceamento_M0_adocao.svg", "Balanceamento M0 — adoções (diferenças padronizadas)", b)
    sc = pd.read_csv(TAB / "propensao_scores_principal_A_AF.csv")
    histogramas(GRA / "propensao_A_AF.svg", "Logit do propensity score de mudança A→AF (população de risco)",
                sc[sc.y == 0].logit_ps.to_numpy(), sc[sc.y == 1].logit_ps.to_numpy(), "candidatas", "tratadas")
    pa = plc[(plc.placebo == "reservado_t-2_t-1") & (plc.grupo == "agregado")]
    rot = [f"{r.desenho}/{r.metodo}" for r in pa.itertuples()]
    dc = comp.iloc[0]
    coeficientes(GRA / "placebos_reservados.svg", "Placebo reservado t−2→t−1 (escala AF − A, lp, IC95)", rot + ["dCDH S1 (l = −1)"],
                 [("placebo", [(r.beta_lp, r.ic95_inf, r.ic95_sup) for r in pa.itertuples()] +
                   [(dc.placebo_lp, *[float(x) for x in str(dc.placebo_ic95).strip("[]").split(";")])])],
                 nota="populações diferentes: não é o mesmo parâmetro")
    ser = []
    for r in comp.itertuples():
        if r.efeito_af_lp != r.efeito_af_lp or not isinstance(r.ic95, str):
            ser.append(None)
            continue
        lo, hi = [float(x) for x in r.ic95.strip("[]").split(";")]
        ser.append((r.efeito_af_lp, lo, hi))
    coeficientes(GRA / "comparacao_desenhos.svg", "Efeito/associação do AF por desenho (lp, IC95)",
                 [str(d)[:22] for d in comp.desenho], [("estimativa", ser)], nota="populações e estimandos diferentes")
    P = comum.ler_pkl(comum.trabalho(c, "painel_S1.pkl.gz"))
    pr = pd.read_parquet(RES / "pares_congelados.parquet")
    pm = pr[(pr.desenho == "principal") & (pr.metodo == "M0") & pr.balanceado]
    ntraj = trajetorias(GRA / "trajetorias_M0.svg", "Trajetória do índice — tratadas × controles M0 (4 eventos)", P, pm) if len(pm) else {}
    # relatório
    r1 = efe[(efe.spec == "R1") & (efe.grupo == "agregado")].iloc[0]
    pl0 = pa[(pa.desenho == "principal") & (pa.metodo == "M0")].iloc[0]
    L = []
    a = L.append
    a("# Risk-set matching + DiD na cesta S1 — relatório\n")
    a(f"Gerado em {comum.agora()} por `python executar.py`. Protocolo congelado em {prot['congelado_em']} "
      f"(pares: SHA-256 de conteúdo `{prot['pares_sha256_conteudo'][:16]}…`). **{prot['declaracao']}.**\n")
    a(f"Integridade do código da Fase I depois do congelamento: "
      f"{'todos os arquivos iguais' if all(x['igual'] for x in integ) else 'HÁ ARQUIVOS ALTERADOS — ver tabelas/integridade_codigo_fase_I.csv'}. "
      f"Testes: {testes.get('testes', '?')} executados, {testes.get('falhas', '?')} falhas, {testes.get('erros', '?')} erros.\n")
    a("## A. Amostra\n")
    a(f"- Banco: `{fontes['pncp_v2']['caminho']}` (somente leitura; impressão digital idêntica à registrada pelo estudo original e à da cópia em `D:/pncp_v2.db`).")
    cs = fontes["contagens_S1"]
    a(f"- Cesta S1 (validação automática de catálogo, validador {fontes['S1']['validador']}): {_n(cs['produtos'])} produtos, "
      f"{_n(cs['compras'])} compras, {_n(cs['itens'])} itens, {_n(cs['uasgs'])} UASGs antes dos filtros. Nenhum produto S2 entra. "
      "S1 não equivale a conferência documental de cada item (S4: só 36 itens).")
    a(f"- Itens com índice A1 (máscara do estudo original, 2023T2–2026T1): {_n(painel['itens_com_indice'])}; compras {_n(painel['compras_com_indice'])}; "
      f"produtos {_n(painel['produtos_com_indice'])}; UASGs {_n(painel['uasgs_com_indice'])}; CNPJs {_n(painel['cnpjs_com_indice'])}.")
    a(f"- Regime: {_n(evr['uasg_trimestres_observados'])} UASG-trimestres com compras A/AF (2023T1–2026T4); "
      f"{_n(evr['uasg_trimestres_mistos'])} mistos ({_f(100 * evr['fracao_mistos'], 1)}%), com {_n(evr['compras_em_trimestres_mistos'])} das "
      f"{_n(evr['compras_total'])} compras. Só {_f(100 * diag['densidade_indice']['fracao_com_indice'], 1)}% dos UASG-trimestres com compras "
      "(2023T2–2026T1) têm índice S1.")
    a(f"- Eventos inequívocos (A→AF ou AF→A entre trimestres inequívocos consecutivos): {evr['eventos_inequivocos_todos']} "
      f"(A→AF {evr['por_direcao'].get('A->AF')}, AF→A {evr['por_direcao'].get('AF->A')}); {evr['uasgs_com_mais_de_um_evento']} UASGs com mais de um evento. "
      f"Situação em t0+1: " + ", ".join(f"{k} {v}" for k, v in evr['por_persistencia'].items()) + ".")
    ra = evr["comparacao_regra_anterior"]
    a(f"- Regra do estudo anterior (fração AF ≥ 0,5, persistência 2, painel {ra['painel_regra_anterior']}): {ra['trocas_regra_anterior']} trocas; "
      f"só {ra['tambem_eventos_inequivocos']} são eventos inequívocos, {ra['motivos'].get('trimestre misto em t0-1 ou t0', 0)} envolvem trimestre misto.\n")
    a("Cobertura do índice por trimestre:\n")
    a(md_tabela(cob, ["trimestre", "itens", "compras", "uasgs", "orgaos", "itens_estl"], ["trimestre", "itens", "compras", "UASGs", "CNPJs", "itens c/ ref. estáveis local"]))
    a("\n## B. Conjuntos de risco\n")
    a("Regras (as mesmas para tratadas e controles): regime inequívoco de origem em t0−1; sem trimestre misto ou no destino de t0−6 a t0−2; "
      "índice em t0−1 e t0−2 e em ≥ 2 dos 4 trimestres de formação; controles observados e inequívocos na origem em t0; mesma esfera; CNPJ diferente.\n")
    ff = funil[(funil.desenho == "principal") & (funil.metodo == "M0") & (funil.t0 == "todos")]
    a(md_tabela(ff, ["etapa", "direcao", "eventos", "uasgs_tratadas", "cnpjs_tratados", "n_efetivo_cnpjs_tratados", "uasgs_controle", "cnpjs_controle"],
                ["etapa", "direção", "eventos", "UASGs trat.", "CNPJs trat.", "CNPJs efetivos", "UASGs controle", "CNPJs controle"]))
    md = desc[desc.desenho == "principal"].motivo.value_counts().reset_index()
    md.columns = ["motivo", "eventos"]
    a("\nMotivos de descarte (desenho principal, M0):\n")
    a(md_tabela(md, ["motivo", "eventos"]))
    a("\n**Diagnóstico de inviabilidade (só contagens, nada estimado):**\n")
    a(md_tabela(viab, ["regime", "regra", "eventos", "cnpjs", "adocoes", "abandonos"]))
    a("\n## C. Matching\n")
    a(md_tabela(psd, ["desenho", "direcao", "linhas", "tratadas", "auc_diagnostico", "dp_logit_populacao", "caliper_logit", "tratadas_fora_do_suporte"],
                ["desenho", "direção", "linhas", "tratadas", "AUC (diag.)", "dp logit", "caliper", "fora do suporte"]))
    a("\nAUC ≈ 1 com tão poucas tratadas indica separação quase perfeita: o PS não oferece suporte comum confiável.\n")
    a(md_tabela(conc, ["desenho", "metodo", "eventos", "pares", "controles_distintos", "reuso_max", "n_efetivo_controles", "n_efetivo_cnpjs_tratados"],
                ["desenho", "método", "eventos", "pares", "controles", "reuso máx.", "nº ef. controles", "nº ef. CNPJs trat."]))
    bm = b[b.covariavel.isin(["log_compras", "log_itens", "freq_trimestral", "log_valor_medio_compra", "var_log_itens", "recorrencia_s1",
                              "srp", "sigilo", "homologacao", "fracasso", "y_nivel", "y_tendencia", "y_dp"])]
    a("\nBalanceamento (adoções, M0; y_* são preços de formação, não usados em M0):\n")
    a(md_tabela(bm, ["covariavel", "smd_antes", "smd_depois", "razao_var_depois", "ks_depois"], ["covariável", "SMD antes", "SMD depois", "razão var.", "KS depois"]))
    a(f"\nCovariáveis M0 com |SMD| ≥ 0,10 depois do pareamento: {', '.join(diag['covariaveis_M0_com_smd_depois_maior_0_10'])}. "
      f"Máximo |SMD| = {_f(diag['smd_abs_max_depois_M0'])}. O balanceamento NÃO é satisfatório.\n")
    a("## D. Placebos (Fase I, períodos reservados)\n")
    pp = plc[plc.grupo == "agregado"].copy()
    pp["ic95"] = [_ic(x, y) for x, y in zip(pp.ic95_inf, pp.ic95_sup)]
    a(md_tabela(pp, ["desenho", "metodo", "placebo", "beta_lp", "ic95", "p_t", "p_wcr_webb", "p_tost", "mde_80", "poder_contra_margem", "eventos", "clusters"],
                ["desenho", "método", "placebo", "lp", "IC95", "p (t)", "p (WCR)", "p TOST ±5", "MDE 80%", "poder vs ±5", "eventos", "clusters"]))
    a(f"\nNo dCDH reestimado na S1 (população e janela diferentes: maioria ≥ 0,5, pesos por item), o placebo l = −1 é {_f(dc.placebo_lp)} lp {str(dc.placebo_ic95).replace('.', ',')}.\n")
    a(md_tabela(rtm, ["metodo", "eventos", "media_desvio_t2_tratada", "media_desvio_t1_tratada", "media_gap_formacao", "corr_gap_formacao_placebo"],
                ["método", "eventos", "desvio t−2 (trat.)", "desvio t−1 (trat.)", "gap formação", "corr(gap, placebo)"]))
    a("\n## E. Efeitos (Fase II — descritivos)\n")
    ee = efe[efe.spec.isin(["R1", "R2", "R3", "R4"])].copy()
    ee["ic95"] = [_ic(x, y) for x, y in zip(ee.ic95_inf, ee.ic95_sup)]
    a(md_tabela(ee, ["spec", "grupo", "beta_lp", "ic95", "p_t", "p_wcr_webb", "eventos", "clusters"], ["spec", "grupo", "lp", "IC95", "p (t)", "p (WCR)", "eventos", "clusters"]))
    a(f"\nR1 (principal): {_f(r1.beta_lp)} lp, IC95 {_ic(r1.ic95_inf, r1.ic95_sup)}, com {int(r1.eventos)} eventos (dos 4 pareados, 2 têm índice em t0 "
      f"para a tratada e para ao menos um controle). Nenhum abandono sobreviveu; o segundo horizonte não é estimável. "
      f"{f2['controles_censurados_t0+1']} dos {f2['pares_M0']} pares saem do regime de origem (ou ficam mistos/sem compras) em t0+1.\n")
    a("Inferência: CR1 por CNPJ somando todas as participações (tratada e controle) e t(G−1); bootstrap selvagem por CNPJ (Webb, "
      f"{c['inferencia']['wcr_B']} réplicas, nulidade imposta), condicional aos pares. O pareamento não é refeito: o bootstrap ingênuo de "
      "matching com k fixo é inconsistente (Abadie e Imbens, 2008). Com 2 eventos, nenhum desses procedimentos é confiável.\n")
    a("## F. Composição\n")
    a(md_tabela(aud, [c_ for c_ in aud.columns if c_ in ("id_evento", "sobreposicao_itens_pos_com_produto_pre_tratada", "jaccard_produtos_tratada",
                                                         "jaccard_produtos_controles", "produtos_comuns_tratada", "tvd_classes_tratada",
                                                         "tvd_classes_controles", "c3_produto_comum_t0_tratada")]))
    a(f"\nC2 e C3 não são estimáveis: {f2['perdas_composicao']}.\n")
    a("## G. Robustez\n")
    rr = efe[efe.grupo == "agregado"].copy()
    rr["ic95"] = [_ic(x, y) for x, y in zip(rr.ic95_inf, rr.ic95_sup)]
    a(md_tabela(rr, ["spec", "descricao", "beta_lp", "ic95", "eventos", "clusters"], ["spec", "descrição", "lp", "IC95", "eventos", "clusters"]))
    a("\n## Comparação com o estudo anterior na S1\n")
    a(md_tabela(comp, ["desenho", "eventos", "orgaos_efetivos", "placebo_lp", "efeito_af_lp", "ic95", "populacao"],
                ["desenho", "eventos", "órgãos efetivos", "placebo", "efeito AF", "IC95", "população"]))
    a(f"\nEventos comuns entre o dCDH e o risk-set estimável: {len(f2['eventos_comuns_dcdh'])}. Sem amostra comum, as diferenças não podem ser "
      "atribuídas ao estimador.\n")
    a("## H. Identificação causal\n")
    a("Ver `conclusao.md`. Gráficos: `graficos/`. Tabelas completas: `tabelas/`. Pares e protocolo: `resultados/`.\n")
    (PASTA / "relatorio.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    # manifesto
    arqs = {}
    for pasta in ("tabelas", "resultados", "graficos", "scripts", "testes"):
        for p in sorted((PASTA / pasta).glob("*")):
            if p.is_file() and p.suffix != ".pyc":
                arqs[f"{pasta}/{p.name}"] = comum.sha(p)
    for n in ("config.json", "executar.py", "README.md", "protocolo.md", "metodologia.md", "relatorio.md", "conclusao.md"):
        if (PASTA / n).exists():
            arqs[n] = comum.sha(PASTA / n)
    trab = {p.name: comum.sha(p) for p in sorted(Path(c["trabalho"]).glob("*.pkl.gz"))}
    comum.escrever_json(PASTA / "manifesto.json", {"gerado_em": comum.agora(), "protocolo_congelado_em": prot["congelado_em"],
                                                   "arquivos": arqs, "trabalho_D": trab, "trajetorias_n": ntraj})
    log("relatório e manifesto gerados")
    return [PASTA / "relatorio.md", PASTA / "manifesto.json"]
