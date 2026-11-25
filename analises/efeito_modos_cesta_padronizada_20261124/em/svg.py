"""Gráficos SVG mínimos (sem matplotlib): coeficientes com IC95, uma série por cor, linha do zero."""
from html import escape
from pathlib import Path

CORES = ["#2b6cb0", "#c05621", "#2f855a", "#6b46c1"]


def coeficientes(caminho, titulo, rotulos, series, eixo_y="log-pontos", nota="", largura=760, altura=380):
    """rotulos: lista de categorias no eixo x; series: lista de (nome, [(beta, lo, hi) ou None])."""
    vals = [v for _, s in series for t in s if t for v in t if v == v]
    if not vals:
        return None
    lo, hi = min(vals + [0]), max(vals + [0])
    pad = (hi - lo) * 0.08 or 1
    lo, hi = lo - pad, hi + pad
    m_esq, m_dir, m_sup, m_inf = 70, 20, 48, 70
    W, H = largura - m_esq - m_dir, altura - m_sup - m_inf
    y = lambda v: m_sup + H * (hi - v) / (hi - lo)
    nx = len(rotulos)
    x = lambda i, k: m_esq + W * (i + 0.5) / nx + (k - (len(series) - 1) / 2) * min(14, W / nx / (len(series) + 1))
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{largura}" height="{altura}" font-family="Segoe UI, Arial" font-size="12">',
         '<rect width="100%" height="100%" fill="white"/>',
         f'<text x="{largura / 2}" y="22" text-anchor="middle" font-size="15" font-weight="600">{escape(titulo)}</text>',
         f'<line x1="{m_esq}" x2="{m_esq + W}" y1="{y(0):.1f}" y2="{y(0):.1f}" stroke="#888" stroke-dasharray="4 3"/>',
         f'<line x1="{m_esq}" x2="{m_esq}" y1="{m_sup}" y2="{m_sup + H}" stroke="#333"/>']
    for k in range(6):
        v = lo + (hi - lo) * k / 5
        p.append(f'<text x="{m_esq - 6}" y="{y(v) + 4:.1f}" text-anchor="end" fill="#444">{v:.1f}</text>')
        p.append(f'<line x1="{m_esq - 3}" x2="{m_esq}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="#333"/>')
    p.append(f'<text x="18" y="{m_sup + H / 2}" transform="rotate(-90 18 {m_sup + H / 2})" text-anchor="middle">{escape(eixo_y)}</text>')
    for i, r in enumerate(rotulos):
        p.append(f'<text x="{x(i, (len(series) - 1) / 2):.1f}" y="{m_sup + H + 18}" text-anchor="middle" fill="#333">{escape(str(r))}</text>')
    for k, (nome, s) in enumerate(series):
        c = CORES[k % len(CORES)]
        for i, t in enumerate(s):
            if not t or t[0] != t[0]:
                continue
            b, l, h = t
            if l == l and h == h:
                p.append(f'<line x1="{x(i, k):.1f}" x2="{x(i, k):.1f}" y1="{y(l):.1f}" y2="{y(h):.1f}" stroke="{c}" stroke-width="2"/>')
            p.append(f'<circle cx="{x(i, k):.1f}" cy="{y(b):.1f}" r="4" fill="{c}"/>')
        p.append(f'<rect x="{m_esq + 10 + 150 * k}" y="{altura - 26}" width="12" height="12" fill="{c}"/>'
                 f'<text x="{m_esq + 28 + 150 * k}" y="{altura - 16}">{escape(nome)}</text>')
    if nota:
        p.append(f'<text x="{largura - m_dir}" y="{altura - 4}" text-anchor="end" font-size="10" fill="#666">{escape(nota)}</text>')
    p.append("</svg>")
    Path(caminho).parent.mkdir(parents=True, exist_ok=True)
    Path(caminho).write_text("\n".join(p), encoding="utf-8")
    return caminho
