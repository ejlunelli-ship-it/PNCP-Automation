"""Gráficos de diagnóstico (SVG) dos testes de robustez, lidos das tabelas CSV (a versão em tabela de cada gráfico).

Paleta de referência validada (azul, laranja, aqua; modos claro e escuro pelo `prefers-color-scheme`); marcas finas,
grade em traço fino, dica nativa (<title>) em cada marca. Uso: chamado por executar_todos.py, ou
    python analises/robustez_dispersao_20261123/graficos.py
"""
import sys
from pathlib import Path
from xml.sax.saxutils import escape

sys.dont_write_bytecode = True
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

AQUI = Path(__file__).resolve().parent
FONTE = 'system-ui, -apple-system, "Segoe UI", sans-serif'
CSS = f"""
svg {{ --surface:#fcfcfb; --ink:#0b0b0b; --ink2:#52514e; --muted:#898781; --grid:#e1e0d9; --axis:#c3c2b7;
       --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; font-family:{FONTE}; }}
@media (prefers-color-scheme: dark) {{
  svg {{ --surface:#1a1a19; --ink:#f0efec; --ink2:#c3c2b7; --muted:#898781; --grid:#2c2c2a; --axis:#383835;
         --s1:#3987e5; --s2:#d95926; --s3:#199e70; }}
}}
.bg {{ fill:var(--surface); }}
.t1 {{ fill:var(--ink); font-size:15px; font-weight:600; }}
.t2 {{ fill:var(--ink2); font-size:12px; }}
.lab {{ fill:var(--ink); font-size:12px; }}
.val {{ fill:var(--ink2); font-size:11px; font-variant-numeric:tabular-nums; }}
.tick {{ fill:var(--muted); font-size:11px; font-variant-numeric:tabular-nums; }}
.nota {{ fill:var(--muted); font-size:10.5px; }}
.grid {{ stroke:var(--grid); stroke-width:1; }}
.axis {{ stroke:var(--axis); stroke-width:1; }}
.ref {{ stroke:var(--ink2); stroke-width:1; }}
.ci1 {{ stroke:var(--s1); stroke-width:2; stroke-linecap:round; }}
.ci2 {{ stroke:var(--s2); stroke-width:2; stroke-linecap:round; }}
.ci3 {{ stroke:var(--s3); stroke-width:2; stroke-linecap:round; }}
.d1 {{ fill:var(--s1); stroke:var(--surface); stroke-width:2; }}
.d2 {{ fill:var(--s2); stroke:var(--surface); stroke-width:2; }}
.d3 {{ fill:var(--s3); stroke:var(--surface); stroke-width:2; }}
.bar1 {{ fill:var(--s1); }}
.est {{ stroke:var(--ink); stroke-width:2; stroke-linecap:round; }}
.hit {{ fill:transparent; }}
g.m:hover .d1, g.m:hover .d2, g.m:hover .d3 {{ stroke:var(--ink); }}
g.m:hover .bar1 {{ opacity:.8; }}
"""


def br(x, nd=2):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "—"
    s = f"{x:.{nd}f}".replace(".", ",")
    return s.replace("-", "−")


def svg(w, h, titulo, desc, corpo):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" '
            f'aria-labelledby="tt dd"><title id="tt">{escape(titulo)}</title><desc id="dd">{escape(desc)}</desc>'
            f'<style>{CSS}</style><rect class="bg" x="0" y="0" width="{w}" height="{h}"/>' + "".join(corpo) + "</svg>")


def escala(lo, hi, a, b):
    return lambda v: a + (v - lo) / (hi - lo) * (b - a)


def ticks(lo, hi, passo):
    return list(np.arange(np.ceil(lo / passo) * passo, hi + 1e-9, passo))


def ic_de(r):
    lo, hi = r.get("ic95_wcr_inf"), r.get("ic95_wcr_sup")
    if lo is None or not np.isfinite(lo):
        lo, hi = r.get("ic95_t_inf"), r.get("ic95_t_sup")
    return lo, hi


# --------------------------------------------------------------------------------------------- 1. coeficientes
ESCOLHA = [("00", "M0 original (A, todas as células)", "M0 original: ref. A, todas as células"),
           ("00", "M1 filtrado (G, dispersão ≤ 0,80)", "M1 filtrado: ref. G, dispersão ≤ 0,80"),
           ("01", "M0 nos eventos comuns", "01 · M0 nos eventos comuns"),
           ("01", "M1 nos eventos comuns", "01 · M1 nos eventos comuns"),
           ("02", "A, ≤ 0,80 — pesos congelados de M0", "02 · ref. A, ≤ 0,80, pesos de M0"),
           ("02", "G, ≤ 0,80 — pesos congelados de M0", "02 · ref. G, ≤ 0,80, pesos de M0"),
           ("02", "G, ≤ 0,80 — pesos iguais", "02 · ref. G, ≤ 0,80, pesos iguais"),
           ("03", "ref. A: só células ≤ 0,80, mesmos controles, janelas e pesos", "03 · ref. A, ≤ 0,80, controles de M0"),
           ("03", "ref. G: só células ≤ 0,80, mesmos controles, janelas e pesos", "03 · ref. G, ≤ 0,80, controles de G"),
           ("04", "G, dispersão pré-tratamento ≤ 0,80", "04 · dispersão pré-tratamento ≤ 0,80"),
           ("07", "ponderação contínua 1/D̃², D̃ ∈ [0,20; 1,50]", "07 · ponderação contínua pela dispersão"),
           ("08", "H1: apresentação padronizada", "08 · H1, apresentação padronizada"),
           ("08", "H2: H1 ∩ medicamentos (6505)", "08 · H2, medicamentos"),
           ("14", "caminho 1: S4 troca o método (empilhado → BJS), pesos iguais", "14 · BJS, ≤ 0,80, pesos iguais"),
           ("14", "caminho 1: S4b BJS com pesos de precisão", "14 · BJS, ≤ 0,80, pesos de precisão")]


def g1(tab, out):
    t = pd.read_csv(tab / "todas_estimativas.csv", dtype={"teste": str})
    t["teste"] = t.teste.str.zfill(2)
    linhas = []
    for te, mod, rot in ESCOLHA:
        z = t[(t.teste == te) & (t.modelo == mod)]
        if len(z) and pd.notna(z.coef_lp.iloc[0]):
            r = z.iloc[0].to_dict()
            lo, hi = ic_de(r)
            linhas.append((rot, r["coef_lp"], lo, hi, r.get("p_wcr"), r.get("n_eventos"), r.get("orgaos")))
    W, esq, larg, dirc = 900, 300, 360, 240
    topo, alt = 110, 26
    H = topo + alt * len(linhas) + 70
    LO_EIXO = -12.0                                  # eixo cortado em −12; IC além disso ganha marca de truncagem
    lo = max(min(min(l[2] for l in linhas), -8) - 1, LO_EIXO)
    hi = max(max(l[3] for l in linhas), 3) + 1
    x = escala(lo, hi, esq, esq + larg)
    c = [f'<text class="t1" x="20" y="28">Efeito do AF no preço: estimativas dos testes de robustez (lp, IC95)</text>',
         f'<text class="t2" x="20" y="47">Exploratório. Ponto = coeficiente; traço = IC95 (bootstrap selvagem por órgão).</text>',
         f'<text class="t2" x="20" y="63">Linhas verticais: zero e as referências −1,91 (M0) e −3,76 (M1).</text>']
    for v in ticks(lo, hi, 2):
        c.append(f'<line class="grid" x1="{x(v):.1f}" x2="{x(v):.1f}" y1="{topo - 8}" y2="{topo + alt * len(linhas)}"/>')
        c.append(f'<text class="tick" x="{x(v):.1f}" y="{topo + alt * len(linhas) + 16}" text-anchor="middle">{br(v, 0)}</text>')
    c.append(f'<line class="axis" x1="{x(0):.1f}" x2="{x(0):.1f}" y1="{topo - 8}" y2="{topo + alt * len(linhas)}"/>')
    for v, nome, anc, dx in ((-1.91, "M0 −1,91", "start", 4), (-3.76, "M1 −3,76", "end", -4)):
        c.append(f'<line class="ref" x1="{x(v):.1f}" x2="{x(v):.1f}" y1="{topo - 14}" y2="{topo + alt * len(linhas)}"/>')
        c.append(f'<text class="val" x="{x(v) + dx:.1f}" y="{topo - 18}" text-anchor="{anc}">{nome}</text>')
    c.append(f'<text class="val" x="{esq + larg + 16}" y="{topo - 18}">coef. [IC95] · p · eventos</text>')
    for j, (rot, b, l_, h_, p, n, o) in enumerate(linhas):
        y = topo + alt * j + alt / 2
        dica = f"{rot}: {br(b)} lp, IC95 [{br(l_)}; {br(h_)}], p = {br(p, 3)}, {int(n)} eventos, {int(o)} órgãos"
        c.append(f'<g class="m"><title>{escape(dica)}</title>'
                 f'<rect class="hit" x="0" y="{y - alt / 2:.1f}" width="{W}" height="{alt}"/>'
                 f'<text class="lab" x="{esq - 14}" y="{y + 4:.1f}" text-anchor="end">{escape(rot)}</text>'
                 f'<line class="ci1" x1="{x(max(l_, lo)):.1f}" x2="{x(h_):.1f}" y1="{y:.1f}" y2="{y:.1f}"/>'
                 + (f'<path class="bar1" d="M{x(lo):.1f},{y:.1f} l7,-4 l0,8 z"/>' if l_ < lo else "") +
                 f'<circle class="d1" cx="{x(max(b, lo)):.1f}" cy="{y:.1f}" r="5"/>'
                 f'<text class="val" x="{esq + larg + 16}" y="{y + 4:.1f}">{br(b)} [{br(l_)}; {br(h_)}] · {br(p, 3)} · {int(n)}</text></g>')
    c.append(f'<text class="nota" x="20" y="{H - 16}">Tabela: tabelas/todas_estimativas.csv. lp = 100 × diferença em log. '
             f'Eixo cortado em −12 lp: o triângulo marca IC que passa desse ponto (valores na coluna à direita).</text>')
    (out / "g1_coeficientes.svg").write_text(svg(W, H, "Estimativas dos testes de robustez",
                                                 "Coeficiente e IC95 de cada especificação", c), encoding="utf-8")


# --------------------------------------------------------------------------------------------- 2. dinâmica
def g2(tab, out):
    t = pd.read_csv(tab / "t12_dinamica.csv")
    t = t[pd.to_numeric(t.trimestre, errors="coerce").notna()].copy()
    t["trimestre"] = t.trimestre.astype(int)
    paineis = [("6 meses", ["M0", "M1", "T4"], [-2, 0, 1]), ("12 meses", ["M0", "M1"], [-4, -3, -2, 0, 1, 2, 3])]
    nomes = {"M0": "M0 original", "M1": "M1 filtrado", "T4": "teste 04 (dispersão pré)"}
    cls = {"M0": "1", "M1": "2", "T4": "3"}
    lo = float(np.nanmin(t.ic95_t_inf)); hi = float(np.nanmax(t.ic95_t_sup))
    lo, hi = min(lo, -5) - 1, max(hi, 5) + 1
    W, H = 900, 430
    topo, base_y = 110, 360
    y = escala(lo, hi, base_y, topo)
    c = [f'<text class="t1" x="20" y="28">Dinâmica do efeito do AF por trimestre relativo à troca (lp, IC95)</text>',
         f'<text class="t2" x="20" y="47">Exploratório. Base = trimestre −1 (fixado em zero). A troca ocorre entre −1 e 0. '
         f'IC95 por t(G − 1) com EP agrupado por órgão.</text>']
    lx = 20
    for s in ("M0", "M1", "T4"):
        c.append(f'<line class="ci{cls[s]}" x1="{lx}" x2="{lx + 18}" y1="70" y2="70"/><circle class="d{cls[s]}" cx="{lx + 9}" cy="70" r="4"/>'
                 f'<text class="lab" x="{lx + 26}" y="74">{nomes[s]}</text>')
        lx += 210
    largura = (W - 120) / 2
    for ip, (jan, series, qs) in enumerate(paineis):
        x0 = 70 + ip * (largura + 30)
        todas = list(range(min(qs), max(qs) + 1))
        x = escala(min(todas) - 0.6, max(todas) + 0.6, x0, x0 + largura)
        c.append(f'<text class="lab" x="{x0}" y="{topo - 14}" font-weight="600">Janela de {jan}</text>')
        for v in ticks(lo, hi, 5):
            c.append(f'<line class="grid" x1="{x0}" x2="{x0 + largura}" y1="{y(v):.1f}" y2="{y(v):.1f}"/>')
            if ip == 0:
                c.append(f'<text class="tick" x="{x0 - 8}" y="{y(v) + 4:.1f}" text-anchor="end">{br(v, 0)}</text>')
        c.append(f'<line class="axis" x1="{x0}" x2="{x0 + largura}" y1="{y(0):.1f}" y2="{y(0):.1f}"/>')
        c.append(f'<line class="ref" x1="{x(-0.5):.1f}" x2="{x(-0.5):.1f}" y1="{topo}" y2="{base_y}"/>')
        c.append(f'<text class="val" x="{x(-0.5) + 4:.1f}" y="{topo + 12}">troca</text>')
        for q in todas:
            c.append(f'<text class="tick" x="{x(q):.1f}" y="{base_y + 18}" text-anchor="middle">{"−" if q < 0 else ""}{abs(q)}</text>')
        for js, s in enumerate(series):
            off = (js - (len(series) - 1) / 2) * 0.2
            z = t[(t.modelo == s) & (t.janela == jan)]
            for _, r in z.iterrows():
                q = r.trimestre
                dica = f"{nomes[s]}, janela de {jan}, trimestre {q}: {br(r.coef_lp)} lp [{br(r.ic95_t_inf)}; {br(r.ic95_t_sup)}], {int(r.n_eventos)} eventos"
                c.append(f'<g class="m"><title>{escape(dica)}</title>'
                         f'<rect class="hit" x="{x(q + off) - 12:.1f}" y="{topo}" width="24" height="{base_y - topo}"/>'
                         f'<line class="ci{cls[s]}" x1="{x(q + off):.1f}" x2="{x(q + off):.1f}" y1="{y(r.ic95_t_inf):.1f}" y2="{y(r.ic95_t_sup):.1f}"/>'
                         f'<circle class="d{cls[s]}" cx="{x(q + off):.1f}" cy="{y(r.coef_lp):.1f}" r="4.5"/></g>')
        c.append(f'<text class="tick" x="{x0 + largura / 2:.1f}" y="{base_y + 36}" text-anchor="middle">trimestre relativo à troca</text>')
    c.append(f'<text class="nota" x="20" y="{H - 12}">Tabela: tabelas/t12_dinamica.csv (inclui os testes conjuntos de pré e pós).</text>')
    (out / "g2_dinamica.svg").write_text(svg(W, H, "Dinâmica do efeito do AF", "Efeito por trimestre relativo à troca", c),
                                         encoding="utf-8")


# --------------------------------------------------------------------------------------------- 3. órgãos
def g3(tab, out):
    resumo = pd.read_csv(tab / "t09_influencia_orgaos.csv").set_index("modelo")
    mods = [m for m in ("M0", "M1", "T4") if (tab / f"t09_loo_{m}.csv").exists()]
    nomes = {"M0": "M0 original", "M1": "M1 filtrado", "T4": "teste 04 (dispersão pré)"}
    dados = {m: pd.read_csv(tab / f"t09_loo_{m}.csv") for m in mods}
    lo = min(d.coef_sem_orgao_lp.min() for d in dados.values()) - 0.5
    hi = max(d.coef_sem_orgao_lp.max() for d in dados.values()) + 0.5
    lo, hi = min(lo, -4.5), max(hi, -1)
    W, esq, larg = 900, 220, 600
    topo, alt = 106, 70
    H = topo + alt * len(mods) + 60
    x = escala(lo, hi, esq, esq + larg)
    c = [f'<text class="t1" x="20" y="28">Retirando um órgão de cada vez: distribuição do efeito do AF (lp)</text>',
         f'<text class="t2" x="20" y="47">Exploratório. Cada ponto = estimativa sem os eventos de um órgão; traço escuro = '
         f'estimativa com todos.</text>',
         f'<text class="t2" x="20" y="63">Linhas verticais: referências −1,91 (M0) e −3,76 (M1).</text>']
    for v in ticks(lo, hi, 1):
        c.append(f'<line class="grid" x1="{x(v):.1f}" x2="{x(v):.1f}" y1="{topo - 6}" y2="{topo + alt * len(mods)}"/>')
        c.append(f'<text class="tick" x="{x(v):.1f}" y="{topo + alt * len(mods) + 16}" text-anchor="middle">{br(v, 0)}</text>')
    for v, nome in ((-1.91, "M0 −1,91"), (-3.76, "M1 −3,76")):
        if lo < v < hi:
            c.append(f'<line class="ref" x1="{x(v):.1f}" x2="{x(v):.1f}" y1="{topo - 12}" y2="{topo + alt * len(mods)}"/>')
            c.append(f'<text class="val" x="{x(v):.1f}" y="{topo - 16}" text-anchor="middle">{nome}</text>')
    for j, m in enumerate(mods):
        yc = topo + alt * j + alt / 2
        d = dados[m].sort_values("coef_sem_orgao_lp").reset_index(drop=True)
        est = resumo.loc[m, "coef_lp"]
        c.append(f'<text class="lab" x="{esq - 14}" y="{yc - 2:.1f}" text-anchor="end">{nomes[m]}</text>')
        c.append(f'<text class="val" x="{esq - 14}" y="{yc + 13:.1f}" text-anchor="end">{int(resumo.loc[m, "orgaos"])} órgãos, '
                 f'{br(resumo.loc[m, "orgaos_efetivos"], 1)} efetivos</text>')
        for i, r in d.iterrows():
            jit = ((i * 7919) % 21 - 10) * 1.6
            dica = f"{nomes[m]} sem o órgão {r.cnpj}: {br(r.coef_sem_orgao_lp)} lp (peso {br(100 * r.peso, 1)}%, {int(r.eventos)} eventos)"
            c.append(f'<g class="m"><title>{escape(dica)}</title><rect class="hit" x="{x(r.coef_sem_orgao_lp) - 12:.1f}" '
                     f'y="{yc + jit - 12:.1f}" width="24" height="24"/><circle class="d1" cx="{x(r.coef_sem_orgao_lp):.1f}" '
                     f'cy="{yc + jit:.1f}" r="4"/></g>')
        c.append(f'<line class="est" x1="{x(est):.1f}" x2="{x(est):.1f}" y1="{yc - 24:.1f}" y2="{yc + 24:.1f}"/>')
    c.append(f'<text class="nota" x="20" y="{H - 14}">Tabelas: tabelas/t09_loo_*.csv e t09_influencia_orgaos.csv.</text>')
    (out / "g3_orgaos.svg").write_text(svg(W, H, "Influência dos órgãos", "Estimativas sem um órgão de cada vez", c),
                                       encoding="utf-8")


# --------------------------------------------------------------------------------------------- 4. dispersão
def g4(tab, out):
    h = pd.read_csv(tab / "t04_histograma_dispersao.csv")
    W, H = 900, 536
    c = [f'<text class="t1" x="20" y="28">Dispersão de preço entre as outras UASGs, nos itens das tratadas</text>',
         f'<text class="t2" x="20" y="47">Exploratório. Desvio-padrão, entre as outras UASGs, do log do preço médio por UASG.</text>',
         f'<text class="t2" x="20" y="63">Em cima: no mesmo trimestre (M1). Embaixo: nos 4 trimestres anteriores à janela (teste 04).</text>']
    paineis = [("contemporanea", "No mesmo trimestre (contemporânea)"), ("historica", "Antes da janela (pré-tratamento)")]
    esq, larg = 90, 760
    n = len(h)
    slot = larg / n
    bw = min(24, slot - 2)
    lim = 0.8033
    for ip, (col, nome) in enumerate(paineis):
        topo = 96 + ip * 215
        base = topo + 160
        tot = h[col].sum()
        sh = 100 * h[col] / tot if tot else h[col] * 0
        ymax = max(5, float(np.ceil(sh.max() / 5) * 5))
        y = escala(0, ymax, base, topo + 10)
        c.append(f'<text class="lab" x="{esq}" y="{topo}" font-weight="600">{nome}</text>')
        c.append(f'<text class="val" x="{esq + larg}" y="{topo}" text-anchor="end">{int(tot):,} itens'.replace(",", ".") + '</text>')
        for v in ticks(0, ymax, 5):
            c.append(f'<line class="grid" x1="{esq}" x2="{esq + larg}" y1="{y(v):.1f}" y2="{y(v):.1f}"/>')
            c.append(f'<text class="tick" x="{esq - 8}" y="{y(v) + 4:.1f}" text-anchor="end">{br(v, 0)}%</text>')
        for i, r in h.iterrows():
            xc = esq + slot * i + slot / 2
            yt = y(sh[i])
            hh = base - yt
            rr = min(4, hh)
            fim = "+" if not np.isfinite(r.faixa_fim) else f"–{br(r.faixa_fim, 1)}"
            dica = f"{nome}: dispersão {br(r.faixa_ini, 1)}{fim}: {br(sh[i], 1)}% dos itens ({int(r[col]):,})".replace(",", ".")
            if hh > 0.5:
                path = (f"M{xc - bw / 2:.1f},{base:.1f} L{xc - bw / 2:.1f},{yt + rr:.1f} Q{xc - bw / 2:.1f},{yt:.1f} "
                        f"{xc - bw / 2 + rr:.1f},{yt:.1f} L{xc + bw / 2 - rr:.1f},{yt:.1f} Q{xc + bw / 2:.1f},{yt:.1f} "
                        f"{xc + bw / 2:.1f},{yt + rr:.1f} L{xc + bw / 2:.1f},{base:.1f} Z")
                c.append(f'<g class="m"><title>{escape(dica)}</title><rect class="hit" x="{xc - slot / 2:.1f}" y="{topo}" '
                         f'width="{slot:.1f}" height="{base - topo:.1f}"/><path class="bar1" d="{path}"/></g>')
        c.append(f'<line class="axis" x1="{esq}" x2="{esq + larg}" y1="{base}" y2="{base}"/>')
        xl = esq + slot * (lim / 0.1)
        c.append(f'<line class="ref" x1="{xl:.1f}" x2="{xl:.1f}" y1="{topo + 6}" y2="{base}"/>')
        c.append(f'<text class="val" x="{xl + 4:.1f}" y="{topo + 18}">limite 0,80</text>')
        for i in range(0, n - 1, 5):
            c.append(f'<text class="tick" x="{esq + slot * i:.1f}" y="{base + 16}" text-anchor="middle">{br(h.faixa_ini[i], 1)}</text>')
        c.append(f'<text class="tick" x="{esq + slot * (n - 0.5):.1f}" y="{base + 16}" text-anchor="middle">2,5+</text>')
    c.append(f'<text class="nota" x="20" y="{H - 14}">Tabela: tabelas/t04_histograma_dispersao.csv (contagens por faixa de 0,1).</text>')
    (out / "g4_dispersao.svg").write_text(svg(W, H, "Distribuição da dispersão de preço",
                                              "Histogramas da dispersão contemporânea e pré-tratamento", c), encoding="utf-8")


# --------------------------------------------------------------------------------------------- 5. faixas
def g5(tab, out):
    t = pd.read_csv(tab / "t05_heterogeneidade.csv")
    z = t[t.modelo.str.startswith("faixa")].reset_index(drop=True)
    W, H = 900, 400
    esq, larg, topo, base = 90, 760, 90, 300
    lo = min(float(z.ic95_wcr_inf.min()), -5) - 1
    hi = max(float(z.ic95_wcr_sup.max()), 5) + 1
    y = escala(lo, hi, base, topo)
    slot = larg / len(z)
    c = [f'<text class="t1" x="20" y="28">Efeito do AF por faixa de dispersão pré-tratamento do produto (lp, IC95)</text>',
         f'<text class="t2" x="20" y="47">Exploratório. Cada faixa estimada em separado, com os eventos que têm itens nela. '
         f'IC95 por bootstrap selvagem por órgão.</text>']
    for v in ticks(lo, hi, 5):
        c.append(f'<line class="grid" x1="{esq}" x2="{esq + larg}" y1="{y(v):.1f}" y2="{y(v):.1f}"/>')
        c.append(f'<text class="tick" x="{esq - 8}" y="{y(v) + 4:.1f}" text-anchor="end">{br(v, 0)}</text>')
    c.append(f'<line class="axis" x1="{esq}" x2="{esq + larg}" y1="{y(0):.1f}" y2="{y(0):.1f}"/>')
    for i, r in z.iterrows():
        xc = esq + slot * i + slot / 2
        rot = r.modelo.replace("faixa ", "").replace(" (pesos de precisão próprios)", "")
        dica = f"{rot}: {br(r.coef_lp)} lp [{br(r.ic95_wcr_inf)}; {br(r.ic95_wcr_sup)}], p = {br(r.p_wcr, 3)}, {int(r.n_eventos)} eventos, {int(r.orgaos)} órgãos"
        c.append(f'<g class="m"><title>{escape(dica)}</title><rect class="hit" x="{xc - 20:.1f}" y="{topo}" width="40" '
                 f'height="{base - topo}"/><line class="ci1" x1="{xc:.1f}" x2="{xc:.1f}" y1="{y(r.ic95_wcr_inf):.1f}" '
                 f'y2="{y(r.ic95_wcr_sup):.1f}"/><circle class="d1" cx="{xc:.1f}" cy="{y(r.coef_lp):.1f}" r="5"/></g>')
        c.append(f'<text class="lab" x="{xc:.1f}" y="{base + 22}" text-anchor="middle">{escape(rot)}</text>')
        c.append(f'<text class="val" x="{xc:.1f}" y="{base + 40}" text-anchor="middle">{br(r.coef_lp)} [{br(r.ic95_wcr_inf)}; {br(r.ic95_wcr_sup)}]</text>')
        c.append(f'<text class="val" x="{xc:.1f}" y="{base + 56}" text-anchor="middle">{int(r.n_eventos)} eventos · {int(r.orgaos)} órgãos</text>')
    c.append(f'<text class="nota" x="20" y="{H - 12}">Tabela: tabelas/t05_heterogeneidade.csv.</text>')
    (out / "g5_faixas.svg").write_text(svg(W, H, "Efeito por faixa de dispersão", "Efeito do AF por faixa de dispersão", c),
                                       encoding="utf-8")


def main(saida=AQUI):
    tab, out = Path(saida) / "tabelas", Path(saida) / "graficos"
    out.mkdir(parents=True, exist_ok=True)
    feitos, erros = [], {}
    for nome, fn in (("g1", g1), ("g2", g2), ("g3", g3), ("g4", g4), ("g5", g5)):
        try:
            fn(tab, out)
            feitos.append(nome)
        except Exception as e:  # cada gráfico é independente
            erros[nome] = repr(e)
    if erros:
        raise RuntimeError(f"gráficos com erro: {erros}; gerados: {feitos}")
    return feitos


if __name__ == "__main__":
    print(main())
