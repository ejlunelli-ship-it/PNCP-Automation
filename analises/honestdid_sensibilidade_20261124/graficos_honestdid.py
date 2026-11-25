"""Gráficos (SVG) da sensibilidade HonestDiD, lidos das tabelas desta pasta.

Reaproveita as funções e a paleta validada de ../robustez_dispersao_20261123/graficos.py (marcas finas, grade em traço fino,
dica nativa em cada marca, modo escuro pelo prefers-color-scheme). Chamado por executar.py, ou:
    python analises/honestdid_sensibilidade_20261124/graficos_honestdid.py
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

REF = -1.91
NOTA = "lp = 100 × diferença em log. Exploratório. Tabelas: tabelas/honestdid_resultados.csv e coeficientes_dinamicos.csv."
ROT_PAR = {"a": "(a) 1º trimestre pós", "b": "(b) média dos trimestres pós", "antecipacao": "trimestre −1 (antecipação)"}


def passo_de(lo, hi):
    for p in (2, 5, 10, 20, 25, 50):
        if (hi - lo) / p <= 10:
            return p
    return 100


def legenda(c, x, y, itens):
    for cls, nome in itens:
        if cls == "faixa":
            c.append(f'<rect class="bar1" x="{x}" y="{y - 5}" width="16" height="10" fill-opacity=".35"/>')
        elif cls == "ref":
            c.append(f'<line class="ref" x1="{x}" x2="{x + 16}" y1="{y}" y2="{y}"/>')
        else:
            c.append(f'<line class="ci{cls}" x1="{x}" x2="{x + 16}" y1="{y}" y2="{y}"/>'
                     f'<circle class="d{cls}" cx="{x + 8}" cy="{y}" r="4"/>')
        c.append(f'<text class="lab" x="{x + 22}" y="{y + 4}">{escape(nome)}</text>')
        x += 30 + 7.2 * len(nome)


def eixo_y(c, y, lo, hi, x0, x1, passo):
    for v in ticks(lo, hi, passo):
        c.append(f'<line class="grid" x1="{x0}" x2="{x1}" y1="{y(v):.1f}" y2="{y(v):.1f}"/>')
        c.append(f'<text class="tick" x="{x0 - 8}" y="{y(v) + 4:.1f}" text-anchor="end">{br(v, 0)}</text>')
    c.append(f'<line class="axis" x1="{x0}" x2="{x1}" y1="{y(0):.1f}" y2="{y(0):.1f}"/>')


def corta(v, lo, hi):
    return min(max(v, lo), hi)


def intervalo_v(c, x, y, lo, hi, l_, u_, cls, dica, ponto=None, faixa=None):
    """Traço vertical de l_ a u_ (cortado no eixo, com triângulo na ponta cortada), ponto opcional e faixa opcional."""
    m = []
    if faixa is not None and np.all(np.isfinite(faixa)):
        a, b = corta(faixa[0], lo, hi), corta(faixa[1], lo, hi)
        m.append(f'<rect class="bar1" x="{x - 5:.1f}" y="{y(b):.1f}" width="10" height="{max(y(a) - y(b), 1.5):.1f}" fill-opacity=".35"/>')
    if np.isfinite(l_) and np.isfinite(u_):
        m.append(f'<line class="ci{cls}" x1="{x:.1f}" x2="{x:.1f}" y1="{y(corta(u_, lo, hi)):.1f}" y2="{y(corta(l_, lo, hi)):.1f}"/>')
        if l_ < lo:
            m.append(f'<path class="bar1" d="M{x:.1f},{y(lo):.1f} l-4,-7 l8,0 z"/>')
        if u_ > hi:
            m.append(f'<path class="bar1" d="M{x:.1f},{y(hi):.1f} l-4,7 l8,0 z"/>')
    if ponto is not None and np.isfinite(ponto):
        m.append(f'<circle class="d{cls}" cx="{x:.1f}" cy="{y(corta(ponto, lo, hi)):.1f}" r="4.5"/>')
    c.append(f'<g class="m"><title>{escape(dica)}</title><rect class="hit" x="{x - 12:.1f}" y="{y(hi):.1f}" width="24" '
             f'height="{y(lo) - y(hi):.1f}"/>' + "".join(m) + "</g>")


# --------------------------------------------------------------------------------------------- 1. perfil
def g_perfil(coef, out):
    paineis = [("P1", "Janela de 6 meses (principal)", [-2, -1, 0, 1]),
               ("J12_pre3_pos4", "Janela de 12 meses (sensibilidade; 78 eventos)", [-4, -3, -2, -1, 0, 1, 2, 3])]
    W, H, topo, base = 980, 470, 120, 380
    zs = [coef[coef.espec == e] for e, _, _ in paineis]
    lo = min(min(z.ic95_normal_inf.min() for z in zs), -5)
    hi = max(max(z.ic95_normal_sup.max() for z in zs), 5)
    lo, hi = np.floor(lo / 5) * 5, np.ceil(hi / 5) * 5
    y = escala(lo, hi, base, topo)
    c = ['<text class="t1" x="20" y="28">Coeficientes dinâmicos do estudo de eventos, efeito do AF (lp, IC95 normal da matriz CR1)</text>',
         '<text class="t2" x="20" y="47">Exploratório. Base = trimestre −1 (zero por construção); a troca ocorre entre −1 e 0. '
         'Sinal: efeito do AF (A → AF e AF → A combinados).</text>',
         '<text class="t2" x="20" y="63">Abaixo de cada ponto: eventos que contribuem. Pré-período: trimestres anteriores a −1.</text>']
    larguras = [300, 520]
    x0 = 80
    for (e, nome, qs), z, larg in zip(paineis, zs, larguras):
        x = escala(qs[0] - .6, qs[-1] + .6, x0, x0 + larg)
        c.append(f'<text class="lab" x="{x0}" y="{topo - 22}" font-weight="600">{escape(nome)}</text>')
        eixo_y(c, y, lo, hi, x0, x0 + larg, passo_de(lo, hi))
        c.append(f'<line class="ref" x1="{x(-0.5):.1f}" x2="{x(-0.5):.1f}" y1="{topo}" y2="{base}"/>')
        c.append(f'<text class="val" x="{x(-0.5) + 4:.1f}" y="{topo + 12}">troca</text>')
        for q in qs:
            c.append(f'<text class="tick" x="{x(q):.1f}" y="{base + 18}" text-anchor="middle">{"−" if q < 0 else ""}{abs(q)}</text>')
            r = z[z.trimestre == q]
            if q == -1:
                c.append(f'<circle class="d2" cx="{x(q):.1f}" cy="{y(0):.1f}" r="4.5"/>')
                c.append(f'<text class="val" x="{x(q):.1f}" y="{base + 34}" text-anchor="middle">base</text>')
                continue
            if not len(r):
                continue
            r = r.iloc[0]
            dica = (f"trimestre {q}: {br(r.coef_lp)} lp, IC95 [{br(r.ic95_normal_inf)}; {br(r.ic95_normal_sup)}], "
                    f"EP {br(r.ep_lp)}, p WCR {br(r.p_wcr, 3)}, {int(r.eventos)} eventos, {int(r.orgaos)} órgãos")
            intervalo_v(c, x(q), y, lo, hi, r.ic95_normal_inf, r.ic95_normal_sup, 1, dica, ponto=r.coef_lp)
            c.append(f'<text class="val" x="{x(q):.1f}" y="{base + 34}" text-anchor="middle">{int(r.eventos)}</text>')
        c.append(f'<text class="tick" x="{x0 + larg / 2:.1f}" y="{base + 56}" text-anchor="middle">trimestre relativo à troca</text>')
        x0 += larg + 80
    c.append(f'<text class="nota" x="20" y="{H - 12}">{escape(NOTA)}</text>')
    (out / "g1_coeficientes_dinamicos.svg").write_text(svg(W, H, "Coeficientes dinâmicos", "perfil por trimestre", c),
                                                       encoding="utf-8", newline="\n")


# --------------------------------------------------------------------------------------------- 2. sensibilidade P1
def g_sensibilidade(res, out, familia, arquivo, titulo, rot_valor):
    z = res[(res.espec == "P1") & (res.grade == "completa")]
    pars = ["a", "b"]
    W, H, topo, base = 980, 500, 130, 400
    sel = z[z.familia.isin([familia, "original"])]
    lo = min(sel.lb.min(), -10); hi = max(sel.ub.max(), 5)
    lo, hi = np.floor(lo / 5) * 5, np.ceil(hi / 5) * 5
    y = escala(lo, hi, base, topo)
    c = [f'<text class="t1" x="20" y="28">{escape(titulo)}</text>',
         '<text class="t2" x="20" y="47">Exploratório. Especificação principal (janela de 6 meses, 141 eventos com trimestre −1, '
         '68 órgãos). Pacote HonestDiD 0.2.8.</text>',
         '<text class="t2" x="20" y="63">Traço = conjunto de confiança robusto de 95%; barra clara e ponto = conjunto identificado '
         'no ponto estimado (sem erro amostral).</text>']
    legenda(c, 20, 86, [("2", "IC original do pacote (normal)"), ("1", "IC robusto 95%"), ("faixa", "conjunto identificado"),
                        ("ref", "M0: −1,91 lp")])
    larg, x0 = 400, 80
    for p in pars:
        zp = z[z.parametro == p]
        vals = sorted(zp[zp.familia == familia].valor.dropna().unique())
        cats = ["orig."] + [br(v, 2).rstrip("0").rstrip(",") for v in vals]
        x = escala(-0.7, len(cats) - 0.3, x0, x0 + larg)
        c.append(f'<text class="lab" x="{x0}" y="{topo - 14}" font-weight="600">{escape(ROT_PAR[p])}</text>')
        eixo_y(c, y, lo, hi, x0, x0 + larg, passo_de(lo, hi))
        c.append(f'<line class="ref" x1="{x0}" x2="{x0 + larg}" y1="{y(REF):.1f}" y2="{y(REF):.1f}"/>')
        o = zp[zp.familia == "original"].iloc[0]
        intervalo_v(c, x(0), y, lo, hi, o.lb, o.ub, 2,
                    f"IC original: [{br(o.lb)}; {br(o.ub)}], estimativa {br(o.estimativa_lp)} lp", ponto=o.estimativa_lp)
        for j, v in enumerate(vals, 1):
            r = zp[(zp.familia == familia) & (zp.valor == v)].iloc[0]
            dica = (f"{rot_valor} = {br(v)}: IC robusto [{br(r.lb)}; {br(r.ub)}]; conjunto identificado "
                    f"[{br(r.id_lb)}; {br(r.id_ub)}]; {'inclui' if r.inclui_zero else 'exclui'} zero")
            intervalo_v(c, x(j), y, lo, hi, r.lb, r.ub, 1, dica, ponto=(r.id_lb + r.id_ub) / 2, faixa=(r.id_lb, r.id_ub))
        for j, t in enumerate(cats):
            c.append(f'<text class="tick" x="{x(j):.1f}" y="{base + 18}" text-anchor="middle">{t}</text>')
        c.append(f'<text class="tick" x="{x0 + larg / 2:.1f}" y="{base + 40}" text-anchor="middle">{escape(rot_valor)}</text>')
        x0 += larg + 90
    c.append(f'<text class="nota" x="20" y="{H - 12}">{escape(NOTA)}</text>')
    (out / arquivo).write_text(svg(W, H, titulo, "sensibilidade", c), encoding="utf-8", newline="\n")


# --------------------------------------------------------------------------------------------- 3. direções
def g_direcoes(res, out):
    z = res[(res.grade == "completa") & (res.parametro == "b") & res.espec.isin(["P1", "D_AAF", "D_AFA"])]
    series = [("P1", "1", "combinado (e)"), ("D_AAF", "2", "A → AF (c)"), ("D_AFA", "3", "AF → A, sinal do AF (d)")]
    W, H, topo, base = 980, 500, 130, 400
    lo = max(min(z.lb.min(), -10), -60); hi = min(max(z.ub.max(), 5), 60)
    lo, hi = np.floor(lo / 10) * 10, np.ceil(hi / 10) * 10
    y = escala(lo, hi, base, topo)
    c = ['<text class="t1" x="20" y="28">Sensibilidade por direção da troca, parâmetro (b): média dos trimestres pós (lp)</text>',
         '<text class="t2" x="20" y="47">Exploratório. Conjuntos de confiança robustos de 95% (HonestDiD). Direções estimadas '
         'separadamente; AF → A com o sinal do efeito do AF.</text>',
         f'<text class="t2" x="20" y="63">Eixo cortado em [{br(lo, 0)}; {br(hi, 0)}]; triângulo = intervalo que passa do eixo '
         '(valores na dica).</text>']
    legenda(c, 20, 86, [(cl, nm) for _, cl, nm in series])
    larg, x0 = 400, 80
    for fam, nome_fam, rot in (("RM", "Magnitudes relativas, Δ^RM(M̄)", "M̄"), ("SD", "Suavidade, Δ^SD(M), M em lp", "M")):
        vals = sorted(z[z.familia == fam].valor.dropna().unique())
        cats = ["orig."] + [br(v, 2).rstrip("0").rstrip(",") for v in vals]
        x = escala(-0.7, len(cats) - 0.3, x0, x0 + larg)
        c.append(f'<text class="lab" x="{x0}" y="{topo - 14}" font-weight="600">{escape(nome_fam)}</text>')
        eixo_y(c, y, lo, hi, x0, x0 + larg, passo_de(lo, hi))
        for s, (e, cl, nm) in enumerate(series):
            off = (s - 1) * 0.22
            ze = z[z.espec == e]
            o = ze[ze.familia == "original"]
            if len(o):
                o = o.iloc[0]
                intervalo_v(c, x(off), y, lo, hi, o.lb, o.ub, cl, f"{nm}, IC original: [{br(o.lb)}; {br(o.ub)}]",
                            ponto=o.estimativa_lp)
            for j, v in enumerate(vals, 1):
                r = ze[(ze.familia == fam) & (ze.valor == v)]
                if len(r):
                    r = r.iloc[0]
                    intervalo_v(c, x(j + off), y, lo, hi, r.lb, r.ub, cl,
                                f"{nm}, {rot} = {br(v)}: [{br(r.lb)}; {br(r.ub)}]", ponto=(r.id_lb + r.id_ub) / 2)
        for j, t in enumerate(cats):
            c.append(f'<text class="tick" x="{x(j):.1f}" y="{base + 18}" text-anchor="middle">{t}</text>')
        c.append(f'<text class="tick" x="{x0 + larg / 2:.1f}" y="{base + 40}" text-anchor="middle">{rot}</text>')
        x0 += larg + 90
    c.append(f'<text class="nota" x="20" y="{H - 12}">{escape(NOTA)}</text>')
    (out / "g4_direcoes.svg").write_text(svg(W, H, "Direções", "sensibilidade por direção", c), encoding="utf-8", newline="\n")


# --------------------------------------------------------------------------------------------- 4. sensibilidades (floresta)
ROT_ESP = {"P1": "principal (CR1)", "P1_JACK": "principal, matriz jackknife", "P1_BOOT": "principal, matriz bootstrap",
           "S_IGUAIS": "pesos iguais por evento", "S_BAL": "painel balanceado (87 eventos)", "D_AAF": "só A → AF",
           "D_AFA": "só AF → A (sinal do AF)", "F1": "filtrado, dispersão ≤ 0,80",
           "J12_pre1_pos2": "janela 12: 1 pré, 2 pós", "J12_pre2_pos2": "janela 12: 2 pré, 2 pós",
           "J12_pre3_pos2": "janela 12: 3 pré, 2 pós", "J12_pre1_pos4": "janela 12: 1 pré, 4 pós",
           "J12_pre2_pos4": "janela 12: 2 pré, 4 pós", "J12_pre3_pos4": "janela 12: 3 pré, 4 pós",
           "ANT12": "antecipação: janela 12, ref. −2"}


def g_floresta(res, out, parametro, arquivo):
    z = res[(res.grade == "completa") & (res.parametro == parametro)]
    ordem = [e for e in ROT_ESP if e in set(z.espec)]
    W, esq, larg, topo, alt = 980, 300, 470, 120, 34
    H = topo + alt * len(ordem) + 70
    lo_e, hi_e = -40.0, 40.0
    x = escala(lo_e, hi_e, esq, esq + larg)
    c = [f'<text class="t1" x="20" y="28">Sensibilidades em M̄ = 1 e M = 1 lp: {escape(ROT_PAR[parametro])} (lp)</text>',
         '<text class="t2" x="20" y="47">Exploratório. Cada especificação muda a amostra ou o estimando (ver relatório). '
         'Eixo cortado em ±40; triângulo = intervalo além do eixo.</text>',
         '<text class="t2" x="20" y="63">Ponto: estimativa (IC original) ou centro do conjunto identificado (robustos).</text>']
    legenda(c, 20, 86, [("3", "IC original"), ("1", "Δ^RM, M̄ = 1"), ("2", "Δ^SD, M = 1")])
    for v in ticks(lo_e, hi_e, 10):
        c.append(f'<line class="grid" x1="{x(v):.1f}" x2="{x(v):.1f}" y1="{topo - 8}" y2="{topo + alt * len(ordem)}"/>')
        c.append(f'<text class="tick" x="{x(v):.1f}" y="{topo + alt * len(ordem) + 16}" text-anchor="middle">{br(v, 0)}</text>')
    c.append(f'<line class="axis" x1="{x(0):.1f}" x2="{x(0):.1f}" y1="{topo - 8}" y2="{topo + alt * len(ordem)}"/>')
    c.append(f'<line class="ref" x1="{x(REF):.1f}" x2="{x(REF):.1f}" y1="{topo - 8}" y2="{topo + alt * len(ordem)}"/>')
    c.append(f'<text class="val" x="{x(REF) - 4:.1f}" y="{topo - 12}" text-anchor="end">M0 −1,91</text>')
    for j, e in enumerate(ordem):
        yc = topo + alt * j + alt / 2
        c.append(f'<text class="lab" x="{esq - 14}" y="{yc + 4:.1f}" text-anchor="end">{escape(ROT_ESP[e])}</text>')
        ze = z[z.espec == e]
        for k, (fam, val, cl) in enumerate((("original", None, "3"), ("RM", 1.0, "1"), ("SD", 1.0, "2"))):
            r = ze[(ze.familia == fam) & ((ze.valor == val) if val is not None else True)]
            if not len(r):
                continue
            r = r.iloc[0]
            yy = yc + (k - 1) * 8
            pt = r.estimativa_lp if fam == "original" else (r.id_lb + r.id_ub) / 2
            l_, u_ = r.lb, r.ub
            m = []
            if np.isfinite(l_) and np.isfinite(u_):
                m.append(f'<line class="ci{cl}" x1="{x(corta(l_, lo_e, hi_e)):.1f}" x2="{x(corta(u_, lo_e, hi_e)):.1f}" '
                         f'y1="{yy:.1f}" y2="{yy:.1f}"/>')
                if l_ < lo_e:
                    m.append(f'<path class="bar1" d="M{x(lo_e):.1f},{yy:.1f} l7,-4 l0,8 z"/>')
                if u_ > hi_e:
                    m.append(f'<path class="bar1" d="M{x(hi_e):.1f},{yy:.1f} l-7,-4 l0,8 z"/>')
            if np.isfinite(pt):
                m.append(f'<circle class="d{cl}" cx="{x(corta(pt, lo_e, hi_e)):.1f}" cy="{yy:.1f}" r="4"/>')
            nome = {"original": "IC original", "RM": "Δ^RM, M̄ = 1", "SD": "Δ^SD, M = 1"}[fam]
            c.append(f'<g class="m"><title>{escape(f"{ROT_ESP[e]} · {nome}: [{br(l_)}; {br(u_)}]")}</title>'
                     f'<rect class="hit" x="0" y="{yy - 4:.1f}" width="{W}" height="8"/>' + "".join(m) + "</g>")
        o = ze[ze.familia == "RM"]
        o = o[o.valor == 1.0]
        if len(o):
            o = o.iloc[0]
            c.append(f'<text class="val" x="{esq + larg + 16}" y="{yc + 4:.1f}">M̄ = 1: [{br(o.lb, 1)}; {br(o.ub, 1)}]</text>')
    c.append(f'<text class="nota" x="20" y="{H - 16}">{escape(NOTA)}</text>')
    (out / arquivo).write_text(svg(W, H, "Sensibilidades", "floresta", c), encoding="utf-8", newline="\n")


# --------------------------------------------------------------------------------------------- 5. influência
def g_influencia(res, infl, out):
    z = res[(res.grade == "loo") & (res.parametro == "b")]
    full = res[(res.espec == "P1") & (res.parametro == "b") & (res.grade == "completa")]
    W, H, topo, base, x0, larg = 980, 470, 120, 380, 80, 860
    paineis = [("RM", 1.0, "1", "Δ^RM, M̄ = 1"), ("SD", 1.0, "2", "Δ^SD, M = 1")]
    lo = min(z[z.familia.isin(["RM", "SD"])].lb.min(), -20); hi = max(z[z.familia.isin(["RM", "SD"])].ub.max(), 10)
    lo, hi = np.floor(lo / 5) * 5, np.ceil(hi / 5) * 5
    y = escala(lo, hi, base, topo)
    zz = z[(z.familia == "RM") & (z.valor == 1.0)].merge(infl[["id", "orgao_retirado", "eventos_retirados", "peso_do_orgao"]],
                                                          left_on="espec", right_on="id", suffixes=("", "_i"))
    zz = zz.sort_values("lb").reset_index(drop=True)
    ordem = list(zz.espec)
    x = escala(-1, len(ordem), x0, x0 + larg)
    c = ['<text class="t1" x="20" y="28">Influência: retirando um órgão por vez, parâmetro (b) (lp)</text>',
         f'<text class="t2" x="20" y="47">Exploratório. Cada par de traços = conjuntos robustos de 95% sem os eventos de um órgão '
         f'({len(ordem)} órgãos), ordenados pelo limite inferior de Δ^RM.</text>',
         '<text class="t2" x="20" y="63">Linhas horizontais tracejadas: limites da amostra completa em Δ^RM, M̄ = 1.</text>']
    legenda(c, 20, 86, [(cl, nm) for _, _, cl, nm in paineis])
    eixo_y(c, y, lo, hi, x0, x0 + larg, passo_de(lo, hi))
    f = full[(full.familia == "RM") & (full.valor == 1.0)]
    if len(f):
        f = f.iloc[0]
        for v in (f.lb, f.ub):
            c.append(f'<line class="ref" x1="{x0}" x2="{x0 + larg}" y1="{y(v):.1f}" y2="{y(v):.1f}"/>')
    for j, e in enumerate(ordem):
        info = zz[zz.espec == e].iloc[0]
        for k, (fam, val, cl, nm) in enumerate(paineis):
            r = z[(z.espec == e) & (z.familia == fam) & (z.valor == val)]
            if not len(r):
                continue
            r = r.iloc[0]
            xx = x(j) + (k - 0.5) * 4
            c.append(f'<g class="m"><title>{escape(f"sem o órgão {info.orgao_retirado} ({int(info.eventos_retirados)} eventos, peso {br(100 * info.peso_do_orgao, 1)}%): {nm} [{br(r.lb)}; {br(r.ub)}]")}</title>'
                     f'<rect class="hit" x="{xx - 3:.1f}" y="{topo}" width="6" height="{base - topo}"/>'
                     f'<line class="ci{cl}" x1="{xx:.1f}" x2="{xx:.1f}" y1="{y(corta(r.ub, lo, hi)):.1f}" y2="{y(corta(r.lb, lo, hi)):.1f}"/></g>')
    c.append(f'<text class="tick" x="{x0 + larg / 2:.1f}" y="{base + 22}" text-anchor="middle">órgão retirado (ordenado)</text>')
    c.append(f'<text class="nota" x="20" y="{H - 12}">{escape(NOTA)} Influência: tabelas/honestdid_influencia_orgaos.csv.</text>')
    (out / "g6_influencia_orgaos.svg").write_text(svg(W, H, "Influência", "retirando um órgão", c), encoding="utf-8",
                                                  newline="\n")


def main(saida=AQUI):
    tab, out = Path(saida) / "tabelas", Path(saida) / "graficos"
    out.mkdir(parents=True, exist_ok=True)
    feitos = []
    coef = pd.read_csv(tab / "coeficientes_dinamicos.csv")
    g_perfil(coef, out); feitos.append("g1_coeficientes_dinamicos.svg")
    arq = tab / "honestdid_resultados.csv"
    if arq.exists():
        res = pd.read_csv(arq)
        g_sensibilidade(res, out, "RM", "g2_magnitudes_relativas.svg",
                        "Magnitudes relativas Δ^RM(M̄): conjuntos robustos de 95% do efeito do AF (lp)", "M̄")
        g_sensibilidade(res, out, "SD", "g3_suavidade.svg",
                        "Suavidade Δ^SD(M): conjuntos robustos de 95% do efeito do AF (lp; M em lp por trimestre)", "M")
        feitos += ["g2_magnitudes_relativas.svg", "g3_suavidade.svg"]
        if res.espec.isin(["D_AAF", "D_AFA"]).any():
            g_direcoes(res, out); feitos.append("g4_direcoes.svg")
        if res.espec.nunique() > 1:
            g_floresta(res, out, "b", "g5_sensibilidades_media.svg")
            g_floresta(res, out, "a", "g5_sensibilidades_primeiro.svg")
            feitos += ["g5_sensibilidades_media.svg", "g5_sensibilidades_primeiro.svg"]
        infl = tab / "influencia_orgaos_coeficientes.csv"
        if (res.grade == "loo").any() and infl.exists():
            g_influencia(res, pd.read_csv(infl), out); feitos.append("g6_influencia_orgaos.svg")
    return {"status": "ok", "graficos": feitos}


if __name__ == "__main__":
    print(main())
