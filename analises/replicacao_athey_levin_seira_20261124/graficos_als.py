"""Gráficos (SVG) da replicação adaptada de Athey, Levin e Seira (2011), lidos das tabelas desta pasta.

Reaproveita as funções e a paleta validada de ../robustez_dispersao_20261123/graficos.py (marcas finas, grade em traço fino,
dica nativa em cada marca, modo escuro pelo prefers-color-scheme). Chamado por executar.py, ou:
    python analises/replicacao_athey_levin_seira_20261124/graficos_als.py
"""
import sys
from pathlib import Path
from xml.sax.saxutils import escape

sys.dont_write_bytecode = True
AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent / "robustez_dispersao_20261123"))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from graficos import br, escala, svg, ticks  # noqa: E402

NOTA = "Exploratório: associações ajustadas, não efeitos causais. lp = 100 × diferença em log. Tabelas em tabelas/."
REFS = [(-1.91, "estudo de eventos −1,91"), (-3.76, "filtrado −3,76"), (100 * np.log(1 - .045), "painel 16/11 −4,6")]


def legenda(c, x, y, itens):
    for cls, nome in itens:
        if cls == "ref":
            c.append(f'<line class="ref" x1="{x}" x2="{x + 16}" y1="{y}" y2="{y}"/>')
        elif cls.startswith("bar"):
            c.append(f'<rect class="bar1" x="{x}" y="{y - 5}" width="16" height="10" fill-opacity="{cls[3:] or "1"}"/>')
        else:
            c.append(f'<line class="ci{cls}" x1="{x}" x2="{x + 16}" y1="{y}" y2="{y}"/><circle class="d{cls}" cx="{x + 8}" cy="{y}" r="4"/>')
        c.append(f'<text class="lab" x="{x + 22}" y="{y + 4}">{escape(nome)}</text>')
        x += 30 + 7.2 * len(nome)


# --------------------------------------------------------------------------------------------- 1. escore
def g_escore(tab, out):
    h = pd.read_csv(tab / "escore_distribuicao.csv")
    h = h[h.escore == "PS2"]
    W, H, x0, larg, topo, base = 980, 470, 80, 840, 110, 390
    tot = h.groupby("modo").compras.sum()
    h = h.assign(frac=h.compras / h.modo.map(tot))
    ymax = float(np.ceil(h.frac.max() * 100 / 5) * 5) / 100
    x = escala(0, 1, x0, x0 + larg)
    y = escala(0, ymax, base, topo)
    c = ['<text class="t1" x="20" y="28">Escore de propensão ao AF (PS2) por modo: distribuição das compras</text>',
         '<text class="t2" x="20" y="47">Logit na compra: período, região, esfera, tamanho (decis), objeto, quantidade, competição '
         'esperada e histórico AF da UASG (12 meses).</text>',
         '<text class="t2" x="20" y="63">Barras = fração das compras de cada modo por faixa de 0,025 do escore. Linhas tracejadas: '
         'suporte do artigo [0,075; 0,925].</text>']
    legenda(c, 20, 86, [("1", f"AF ({int(tot.get('AF', 0)):,} compras)".replace(",", ".")),
                        ("2", f"Aberto ({int(tot.get('A', 0)):,} compras)".replace(",", ".")), ("ref", "limites do suporte")])
    for v in ticks(0, ymax, 0.05 if ymax > .2 else 0.02):
        c.append(f'<line class="grid" x1="{x0}" x2="{x0 + larg}" y1="{y(v):.1f}" y2="{y(v):.1f}"/>')
        c.append(f'<text class="tick" x="{x0 - 8}" y="{y(v) + 4:.1f}" text-anchor="end">{br(100 * v, 0)}%</text>')
    c.append(f'<line class="axis" x1="{x0}" x2="{x0 + larg}" y1="{base}" y2="{base}"/>')
    for v in np.arange(0, 1.01, .1):
        c.append(f'<text class="tick" x="{x(v):.1f}" y="{base + 18}" text-anchor="middle">{br(v, 1)}</text>')
    for v in (.075, .925):
        c.append(f'<line class="ref" x1="{x(v):.1f}" x2="{x(v):.1f}" y1="{topo}" y2="{base}"/>')
    larg_b = (x(.025) - x(0)) / 2 - 1
    for (_, r) in h.iterrows():
        for modo, cl, dx in (("AF", "1", 0), ("A", "2", 1)):
            if r.modo != modo:
                continue
            xx = x(r.lim_inf) + dx * (larg_b + 1) + 0.5
            dica = f"{modo}: escore {br(r.lim_inf, 3)}–{br(r.lim_sup, 3)}: {int(r.compras)} compras ({br(100 * r.frac, 1)}%)"
            cor = "bar1" if modo == "AF" else "bar2"
            c.append(f'<g class="m"><title>{escape(dica)}</title><rect class="{cor}" x="{xx:.1f}" y="{y(r.frac):.1f}" '
                     f'width="{larg_b:.1f}" height="{max(base - y(r.frac), 0):.1f}" rx="1"/></g>')
    c.append(f'<text class="tick" x="{x0 + larg / 2:.1f}" y="{base + 40}" text-anchor="middle">escore previsto de AF</text>')
    c.append(f'<text class="nota" x="20" y="{H - 12}">{escape(NOTA)} Tabela: escore_distribuicao.csv.</text>')
    texto = svg(W, H, "Escore de propensão", "distribuição por modo", c)
    texto = texto.replace(".bar1 {", ".bar2 { fill:var(--s2); }\n.bar1 {", 1)
    (out / "g1_escore_por_modo.svg").write_text(texto, encoding="utf-8", newline="\n")


# --------------------------------------------------------------------------------------------- 2. equilíbrio
def g_equilibrio(tab, out):
    e = pd.read_csv(tab / "equilibrio_matching.csv")
    e = e[e.variante == "(a) só o escore"]
    W, esq, larg, topo, alt = 980, 260, 560, 120, 24
    H = topo + alt * len(e) + 70
    lo, hi = -1.0, 1.0
    vals = np.r_[e.dif_padronizada_amostra_completa, e.dif_padronizada_suporte_antes, e.dif_padronizada_depois]
    lo = min(lo, np.floor(np.nanmin(vals) * 2) / 2); hi = max(hi, np.ceil(np.nanmax(vals) * 2) / 2)
    x = escala(lo, hi, esq, esq + larg)
    c = ['<text class="t1" x="20" y="28">Equilíbrio das covariáveis: diferença padronizada AF − Aberto</text>',
         '<text class="t2" x="20" y="47">Amostra completa, suporte [0,075; 0,925] antes do matching e depois do matching (a) pelo '
         'escore (pesos do casamento).</text>',
         '<text class="t2" x="20" y="63">Faixa ±0,1 = equilíbrio convencional. Equilíbrio observado não é evidência de validade causal.</text>']
    legenda(c, 20, 86, [("3", "amostra completa"), ("2", "suporte, antes"), ("1", "depois do matching")])
    c.append(f'<rect class="bar1" x="{x(-.1):.1f}" y="{topo - 8}" width="{x(.1) - x(-.1):.1f}" height="{alt * len(e) + 8}" fill-opacity=".12"/>')
    for v in ticks(lo, hi, 0.5):
        c.append(f'<line class="grid" x1="{x(v):.1f}" x2="{x(v):.1f}" y1="{topo - 8}" y2="{topo + alt * len(e)}"/>')
        c.append(f'<text class="tick" x="{x(v):.1f}" y="{topo + alt * len(e) + 16}" text-anchor="middle">{br(v, 1)}</text>')
    c.append(f'<line class="axis" x1="{x(0):.1f}" x2="{x(0):.1f}" y1="{topo - 8}" y2="{topo + alt * len(e)}"/>')
    for j, (_, r) in enumerate(e.iterrows()):
        yy = topo + alt * j + alt / 2
        c.append(f'<text class="lab" x="{esq - 12}" y="{yy + 4:.1f}" text-anchor="end">{escape(r.covariavel)}</text>')
        for k, (col, cl) in enumerate((("dif_padronizada_amostra_completa", "3"), ("dif_padronizada_suporte_antes", "2"),
                                      ("dif_padronizada_depois", "1"))):
            v = r[col]
            if not np.isfinite(v):
                continue
            dica = f"{r.covariavel}: {br(v, 3)}"
            c.append(f'<g class="m"><title>{escape(dica)}</title><circle class="d{cl}" cx="{x(min(max(v, lo), hi)):.1f}" '
                     f'cy="{yy + (k - 1) * 5:.1f}" r="4"/></g>')
    c.append(f'<text class="nota" x="20" y="{H - 16}">{escape(NOTA)} Tabelas: equilibrio_suporte.csv e equilibrio_matching.csv.</text>')
    (out / "g2_equilibrio.svg").write_text(svg(W, H, "Equilíbrio", "diferenças padronizadas", c), encoding="utf-8", newline="\n")


# --------------------------------------------------------------------------------------------- 3. efeitos (floresta)
def floresta(linhas, arquivo, titulo, sub1, sub2, out, refs=REFS):
    W, esq, larg, topo, alt = 1060, 450, 360, 120, 26
    H = topo + alt * len(linhas) + 70
    vals = [v for l_ in linhas for v in (l_[2], l_[3]) if np.isfinite(v)]
    lo = max(min(min(vals), -8) - 1, -25); hi = min(max(max(vals), 3) + 1, 25)
    x = escala(lo, hi, esq, esq + larg)
    c = [f'<text class="t1" x="20" y="28">{escape(titulo)}</text>', f'<text class="t2" x="20" y="47">{escape(sub1)}</text>',
         f'<text class="t2" x="20" y="63">{escape(sub2)}</text>']
    passo = 2 if hi - lo <= 24 else 5
    for v in ticks(lo, hi, passo):
        c.append(f'<line class="grid" x1="{x(v):.1f}" x2="{x(v):.1f}" y1="{topo - 8}" y2="{topo + alt * len(linhas)}"/>')
        c.append(f'<text class="tick" x="{x(v):.1f}" y="{topo + alt * len(linhas) + 16}" text-anchor="middle">{br(v, 0)}</text>')
    c.append(f'<line class="axis" x1="{x(0):.1f}" x2="{x(0):.1f}" y1="{topo - 8}" y2="{topo + alt * len(linhas)}"/>')
    for k, (v, nome) in enumerate(refs):
        if lo < v < hi:
            c.append(f'<line class="ref" x1="{x(v):.1f}" x2="{x(v):.1f}" y1="{topo - 12 - 12 * k}" y2="{topo + alt * len(linhas)}"/>')
            c.append(f'<text class="val" x="{x(v) + 4:.1f}" y="{topo - 14 - 12 * k}">{escape(nome)}</text>')
    c.append(f'<text class="val" x="{esq + larg + 14}" y="{topo - 14}">coef. [IC95] · p · compras</text>')
    for j, (rot, b, l_, h_, p, n, cl) in enumerate(linhas):
        yy = topo + alt * j + alt / 2
        m = []
        if np.isfinite(l_) and np.isfinite(h_):
            m.append(f'<line class="ci{cl}" x1="{x(max(l_, lo)):.1f}" x2="{x(min(h_, hi)):.1f}" y1="{yy:.1f}" y2="{yy:.1f}"/>')
            if l_ < lo:
                m.append(f'<path class="bar1" d="M{x(lo):.1f},{yy:.1f} l7,-4 l0,8 z"/>')
            if h_ > hi:
                m.append(f'<path class="bar1" d="M{x(hi):.1f},{yy:.1f} l-7,-4 l0,8 z"/>')
        if np.isfinite(b):
            m.append(f'<circle class="d{cl}" cx="{x(min(max(b, lo), hi)):.1f}" cy="{yy:.1f}" r="4.5"/>')
        dica = f"{rot}: {br(b)} [{br(l_)}; {br(h_)}], p = {br(p, 3)}, {n} compras"
        c.append(f'<g class="m"><title>{escape(dica)}</title><rect class="hit" x="0" y="{yy - alt / 2:.1f}" width="{W}" height="{alt}"/>'
                 f'<text class="lab" x="{esq - 12}" y="{yy + 4:.1f}" text-anchor="end">{escape(rot)}</text>' + "".join(m) +
                 f'<text class="val" x="{esq + larg + 14}" y="{yy + 4:.1f}">{br(b)} [{br(l_)}; {br(h_)}] · {br(p, 3)} · {n}</text></g>')
    c.append(f'<text class="nota" x="20" y="{H - 16}">{escape(NOTA)}</text>')
    (out / arquivo).write_text(svg(W, H, titulo, sub1, c), encoding="utf-8", newline="\n")


def fmt_n(v):
    return f"{int(v):,}".replace(",", ".") if np.isfinite(v) else "—"


def g_efeitos(tab, out):
    o = pd.read_csv(tab / "ols.csv")
    L = []
    for am, rot_am in (("completa", "completa"), ("suporte", "suporte")):
        for esp in ("OLS 1", "OLS 2", "OLS 3", "OLS 4"):
            for pesos, cl in (("item", "1"), ("compra", "2")):
                r = o[(o.amostra == am) & (o.especificacao == esp) & (o.pesos == pesos)]
                if len(r):
                    r = r.iloc[0]
                    L.append((f"{esp} · {rot_am} · peso por {pesos}", r.coef_lp, r.ic95_inf, r.ic95_sup, r.p, fmt_n(r.compras), cl))
    fi = tab / "interacoes.csv"
    if fi.exists():
        it = pd.read_csv(fi)
        for am in ("completa", "suporte"):
            r = it[(it.amostra == am) & (it.base == "OLS 2") & (it.pesos == "item") & (it.dimensao == "conjunto (5 dimensões)")]
            if len(r):
                r = r.iloc[0]
                L.append((f"interações (OLS 2) · {am} · efeito médio", r.efeito_medio_ajustado_lp, r.ic95_inf, r.ic95_sup, r.p,
                          fmt_n(r.compras), "3"))
    fm = tab / "matching.csv"
    if fm.exists():
        mt = pd.read_csv(fm)
        for var in mt.variante.unique():
            r = mt[(mt.variante == var) & (mt.pesos == "compra") & (mt.estimando == "efeito_medio_eq7")]
            if len(r):
                r = r.iloc[0]
                L.append((f"matching {var} · eq. 7 · EP agrupado", r.coef_lp, r.ic95_inf_agrupado, r.ic95_sup_agrupado, r.p_agrupado,
                          fmt_n(r.compras_no_estimando), "3"))
    fq = tab / "regressao_mediana.csv"
    if fq.exists():
        q = pd.read_csv(fq)
        for _, r in q.iterrows():
            L.append((f"mediana (compra) · {r.amostra} · {r.especificacao}", r.coef_lp, r.ic95_percentil_inf, r.ic95_percentil_sup,
                      r.p_normal, fmt_n(r.compras), "3"))
    floresta(L, "g3_efeitos.svg", "Diferença ajustada AF − Aberto no índice de preço (lp, IC95)",
             "OLS 1–4 (item; EP agrupado por CNPJ), interações (efeito médio), matching pelo escore (eq. 7) e regressão mediana.",
             "Azul = peso por item; laranja = peso igual por compra; aqua = outros estimadores. Suporte = escore PS2 em [0,075; 0,925].",
             out)


def g_robustez(tab, out):
    r = pd.read_csv(tab / "robustez.csv")
    L = []
    for _, x in r.iterrows():
        if x.teste.startswith("9."):
            continue
        if not np.isfinite(x.get("coef_lp", np.nan)):
            continue
        l_, h_ = x.get("ic95_inf", np.nan), x.get("ic95_sup", np.nan)
        rot = f"{x.especificacao} · {x.amostra}" + (f" · {x.pesos}" if str(x.get("pesos")) == "compra" else "")
        L.append((rot[:62], x.coef_lp, l_, h_, x.get("p", np.nan), fmt_n(x.get("compras", np.nan)), "1"))
    if L:
        floresta(L, "g4_robustez.svg", "Testes de robustez: diferença AF − Aberto no índice (lp, IC95)",
                 "Cada linha muda a amostra, o escore, o estimador ou o tratamento do índice (ver relatório).",
                 "OLS com EP agrupado por CNPJ; matching com EP agrupado (adaptação). Nenhuma variante foi escolhida pelo valor-p.", out)


def g_comparacao(tab, out):
    cp = pd.read_csv(tab / "comparacao_estudos_anteriores.csv")
    o = pd.read_csv(tab / "ols.csv")
    L = [("painel de 16/11 (publicado): −4,5% em %", 100 * np.log(1 - .045), 100 * np.log(1 - .069), 100 * np.log(1 - .021),
          np.nan, "—", "2"),
         ("estudo de eventos (publicado)", -1.91, -5.67, 1.93, .32, "152 eventos", "2"),
         ("filtrado, dispersão ≤ 0,80 (publicado)", -3.76, -6.67, -0.89, np.nan, "150 eventos", "2")]
    for _, x in cp.iterrows():
        L.append((f"{x.especificacao[:46]} · {x.amostra[:18]} · {x.pesos}", x.coef_lp, x.ic95_inf, x.ic95_sup, x.p,
                  fmt_n(x.compras), "1"))
    for esp in ("OLS 3", "OLS 4"):
        r = o[(o.amostra == "suporte") & (o.especificacao == esp) & (o.pesos == "item")]
        if len(r):
            r = r.iloc[0]
            L.append((f"esta replicação: {esp} · suporte · item", r.coef_lp, r.ic95_inf, r.ic95_sup, r.p, fmt_n(r.compras), "3"))
    floresta(L, "g5_comparacao.svg", "Comparação com os estudos anteriores (lp, IC95)",
             "Laranja = resultados publicados (amostras e parâmetros próprios); azul = mesma especificação ou mesma amostra nesta base.",
             "Amostras e parâmetros distintos não são diretamente equivalentes (ver relatório, seção 10).", out, refs=[])


def main(saida=AQUI):
    tab, out = Path(saida) / "tabelas", Path(saida) / "graficos"
    out.mkdir(parents=True, exist_ok=True)
    feitos = []
    for nome, f, arq in (("g1_escore_por_modo.svg", g_escore, "escore_distribuicao.csv"),
                         ("g2_equilibrio.svg", g_equilibrio, "equilibrio_matching.csv"), ("g3_efeitos.svg", g_efeitos, "ols.csv"),
                         ("g4_robustez.svg", g_robustez, "robustez.csv"),
                         ("g5_comparacao.svg", g_comparacao, "comparacao_estudos_anteriores.csv")):
        if (tab / arq).exists():
            f(tab, out)
            feitos.append(nome)
    return {"status": "ok", "graficos": feitos}


if __name__ == "__main__":
    print(main())
