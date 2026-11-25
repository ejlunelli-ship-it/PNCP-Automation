"""Gráficos de efeitos e IC95 (SVG) da investigação de composição, lidos de tabelas/todas_estimativas.csv.

Reaproveita as funções e a paleta validada de ../robustez_dispersao_20261123/graficos.py (marcas finas, grade em traço
fino, dica nativa em cada marca, modo escuro pelo prefers-color-scheme). Chamado por executar.py, ou:
    python analises/composicao_precos_medicamentos_20261123/graficos_composicao.py
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


def floresta(linhas, arquivo, titulo, sub1, sub2, refs, nota, lo_eixo=-15.0, hi_eixo=15.0):
    """linhas: (rótulo, coef, ic_inf, ic_sup, p, eventos). IC além do eixo ganha um triângulo na ponta cortada."""
    W, esq, larg = 900, 330, 330
    topo, alt = 110, 26
    H = topo + alt * len(linhas) + 70
    lo = max(min(min(l[2] for l in linhas), -6) - 1, lo_eixo)
    hi = min(max(max(l[3] for l in linhas), 3) + 1, hi_eixo)
    x = escala(lo, hi, esq, esq + larg)
    c = [f'<text class="t1" x="20" y="28">{escape(titulo)}</text>',
         f'<text class="t2" x="20" y="47">{escape(sub1)}</text>', f'<text class="t2" x="20" y="63">{escape(sub2)}</text>']
    passo = 2 if hi - lo <= 24 else 5
    for v in ticks(lo, hi, passo):
        c.append(f'<line class="grid" x1="{x(v):.1f}" x2="{x(v):.1f}" y1="{topo - 8}" y2="{topo + alt * len(linhas)}"/>')
        c.append(f'<text class="tick" x="{x(v):.1f}" y="{topo + alt * len(linhas) + 16}" text-anchor="middle">{br(v, 0)}</text>')
    c.append(f'<line class="axis" x1="{x(0):.1f}" x2="{x(0):.1f}" y1="{topo - 8}" y2="{topo + alt * len(linhas)}"/>')
    for v, nome, anc, dx in refs:
        if lo < v < hi:
            c.append(f'<line class="ref" x1="{x(v):.1f}" x2="{x(v):.1f}" y1="{topo - 14}" y2="{topo + alt * len(linhas)}"/>')
            c.append(f'<text class="val" x="{x(v) + dx:.1f}" y="{topo - 18}" text-anchor="{anc}">{nome}</text>')
    c.append(f'<text class="val" x="{esq + larg + 16}" y="{topo - 18}">coef. [IC95] · p · eventos</text>')
    for j, (rot, b, l_, h_, p, n) in enumerate(linhas):
        y = topo + alt * j + alt / 2
        dica = f"{rot}: {br(b)} lp, IC95 [{br(l_)}; {br(h_)}], p = {br(p, 3)}, {int(n)} eventos"
        marcas = ""
        if l_ < lo:
            marcas += f'<path class="bar1" d="M{x(lo):.1f},{y:.1f} l7,-4 l0,8 z"/>'
        if h_ > hi:
            marcas += f'<path class="bar1" d="M{x(hi):.1f},{y:.1f} l-7,-4 l0,8 z"/>'
        c.append(f'<g class="m"><title>{escape(dica)}</title>'
                 f'<rect class="hit" x="0" y="{y - alt / 2:.1f}" width="{W}" height="{alt}"/>'
                 f'<text class="lab" x="{esq - 14}" y="{y + 4:.1f}" text-anchor="end">{escape(rot)}</text>'
                 f'<line class="ci1" x1="{x(max(l_, lo)):.1f}" x2="{x(min(h_, hi)):.1f}" y1="{y:.1f}" y2="{y:.1f}"/>' + marcas +
                 f'<circle class="d1" cx="{x(min(max(b, lo), hi)):.1f}" cy="{y:.1f}" r="5"/>'
                 f'<text class="val" x="{esq + larg + 16}" y="{y + 4:.1f}">{br(b)} [{br(l_)}; {br(h_)}] · {br(p, 3)} · {int(n)}</text></g>')
    c.append(f'<text class="nota" x="20" y="{H - 16}">{escape(nota)}</text>')
    arquivo.write_text(svg(W, H, titulo, sub1, c), encoding="utf-8", newline="\n")


REFS = [(-1.91, "M0 −1,91", "start", 4), (-3.76, "M1 −3,76", "end", -4)]
NOTA = "Tabela: tabelas/todas_estimativas.csv. lp = 100 × diferença em log. Triângulo = IC que passa do eixo (valores à direita)."


def pega(t, teste, contem, pesos=None):
    z = t[(t.teste.astype(str) == teste) & t.modelo.str.contains(contem, regex=False)]
    if pesos is not None:
        z = z[z.pesos.astype(str) == pesos]
    return z.iloc[0] if len(z) else None


def linha_de(r, rot):
    return (rot, r.coef_lp, r.ic95_inf, r.ic95_sup, r.p_wcr, r.n_eventos)


def main(saida=AQUI):
    tab, out = Path(saida) / "tabelas", Path(saida) / "graficos"
    out.mkdir(parents=True, exist_ok=True)
    t = pd.read_csv(tab / "todas_estimativas.csv")
    t = t[t.coef_lp.notna()]
    feitos = []
    # 1. grupos
    L = []
    for sig in ("A", "G"):
        for grupo in ("todos", "medicamentos", "demais materiais"):
            r = pega(t[t.modelo.str.contains(f"| {grupo} | controles do modelo base", regex=False)], "1", f"{sig} (", "precisão (h do grupo)")
            if r is not None:
                L.append(linha_de(r, f"{sig} · {grupo}"))
        for grupo in ("medicamentos", "demais materiais"):
            r = pega(t[t.modelo.str.contains(f"| {grupo} | controles selecionados de novo", regex=False)], "1", f"{sig} (")
            if r is not None:
                L.append(linha_de(r, f"{sig} · {grupo}, controles novos"))
    if L:
        floresta(L, out / "g1_grupos.svg", "Efeito do AF por grupo de produtos (lp, IC95)",
                 "Exploratório. A = referência original; G = referência G com dispersão ≤ 0,80. Pesos de precisão do grupo.",
                 "Controles e janelas do modelo base; nas linhas \"controles novos\", controles selecionados para o grupo.", REFS, NOTA)
        feitos.append("g1_grupos.svg")
    # 2. interação
    L = []
    for sig in ("A", "G"):
        for pn in ("precisão da diferença", "iguais"):
            r = pega(t, "2", f"{sig} (", pn)
            if r is not None:
                L.append(linha_de(r, f"{sig} · medicamentos − demais · pesos {pn.replace('precisão da diferença', 'de precisão')}"))
    if L:
        floresta(L, out / "g2_interacao.svg", "Interação AF × medicamentos: diferença de efeitos (lp, IC95)",
                 "Exploratório. Diferença pareada por evento entre o efeito em medicamentos e nos demais materiais.",
                 "Zero = efeitos iguais. IC por bootstrap selvagem por órgão.", [], NOTA, -30, 30)
        feitos.append("g2_interacao.svg")
    # 3. composição fixa
    L = []
    for sig in ("A", "G"):
        for chave, rot in (("principal | índice original", "índice original"), ("principal | A: preço", "composição fixa (A)"),
                           ("principal | índice fixo com produtos que somem", "fixa, sumidos = 0")):
            for pn in ("pesos do modelo base", "iguais"):
                r = pega(t[t.modelo.str.contains(chave, regex=False)], "3/4", f"{sig} (", pn)
                if r is not None:
                    L.append(linha_de(r, f"{sig} · {rot} · {'pesos base' if pn != 'iguais' else 'pesos iguais'}"))
    if L:
        floresta(L, out / "g3_composicao_fixa.svg", "Índice original × índice de composição fixa (lp, IC95)",
                 "Exploratório. Mesmos eventos e controles. Composição fixa: produtos continuados, pesos da pré-janela.",
                 "Pesos base = precisão do modelo base, congelados; pesos iguais = cada evento pesa igual.", REFS, NOTA)
        feitos.append("g3_composicao_fixa.svg")
    # 4. decomposição
    L = []
    for sig in ("A", "G"):
        for chave, rot in (("principal | ΔĒ", "total, média por item"), ("principal | A: preço", "A: preço, comparáveis"),
                           ("principal | B1", "B1: recomposição"), ("principal | B2", "B2: entrada e saída")):
            r = pega(t[t.modelo.str.contains(chave, regex=False)], "3/4", f"{sig} (", "pesos do modelo base")
            if r is not None:
                L.append(linha_de(r, f"{sig} · {rot}"))
    if L:
        floresta(L, out / "g4_decomposicao.svg", "Decomposição: preço de comparáveis × composição (lp, IC95)",
                 "Exploratório. ΔĒ = A + B1 + B2 por unidade e evento (identidade exata). Pesos do modelo base.",
                 "Componentes B1 e B2 refletem escolhas de compra; não têm leitura causal isolada.", [], NOTA)
        feitos.append("g4_decomposicao.svg")
    # 5. pré-tendência na pseudojanela
    L = []
    for sig in ("A", "G"):
        for chave, rot in (("índice original", "índice original"), ("ΔĒ", "total, média por item"), ("A: preço", "A: preço, comparáveis"),
                           ("B1", "B1: recomposição"), ("B2", "B2: entrada e saída")):
            z = t[(t.teste.astype(str) == "5") & t.modelo.str.contains("pseudojanela", regex=False) &
                  t.modelo.str.contains(chave, regex=False) & t.modelo.str.startswith(f"{sig} (") & (t.pesos == "pesos do modelo base")]
            if len(z):
                L.append(linha_de(z.iloc[0], f"{sig} · {rot}"))
    if L:
        floresta(L, out / "g5_pre_tendencia.svg", "Pré-tendência: as mesmas medidas antes da troca (lp, IC95)",
                 "Exploratório. Pseudojanela [m−6, m−3) contra [m−3, m), mesmos eventos e controles. Esperado: zero.",
                 "Pesos do modelo base.", [], NOTA)
        feitos.append("g5_pre_tendencia.svg")
    return {"status": "ok", "graficos": feitos}


if __name__ == "__main__":
    print(main())
