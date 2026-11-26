"""Orçamento sigiloso e material × serviço: desconto e preço/mediana nos três modos (protocolo.md).

Lê dados/pncp.db somente para leitura e grava a base em dados/analise_controles/ (fora do git). O nº de
itens da compra vem da extração da análise de uso (dados/analise_uso_modos/compras.pkl).

    python analises/controles_modos_20261122/controles_modos.py extrair
    python analises/controles_modos_20261122/controles_modos.py desc
    python analises/controles_modos_20261122/controles_modos.py est D     # desconto
    python analises/controles_modos_20261122/controles_modos.py est L     # preço/mediana
    python analises/controles_modos_20261122/controles_modos.py holm
"""
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
DADOS = Path(os.environ.get('PNCP_DADOS', RAIZ / 'dados'))
BASE = DADOS / 'analise_controles'
COMPRAS_USO = DADOS / 'analise_uso_modos' / 'compras.pkl'
MODOS = {'Aberto': 'A', 'Aberto-Fechado': 'AF', 'Fechado-Aberto': 'FA'}

SQL = """
SELECT c.numero_controle_pncp AS compra, c.orgao_cnpj AS cnpj, COALESCE(i.uasg_item, c.uasg) AS uasg, c.uf,
       substr(c.data_publicacao, 1, 7) AS mes, c.modo_disputa AS modo, c.srp,
       i.material_ou_servico AS ms, i.cod_item_catalogo AS cat, upper(trim(i.unidade_medida)) AS unid,
       i.orcamento_sigiloso AS sig, i.tipo_beneficio AS benef, i.quantidade AS q,
       i.valor_unitario_estimado AS r, i.valor_unitario_resultado AS p
FROM itens i JOIN compras c ON c.numero_controle_pncp = i.numero_controle_pncp
WHERE c.fonte = 'dados_abertos' AND c.modalidade_nome LIKE 'Preg%Eletr%'
  AND c.modo_disputa IN ('Aberto', 'Aberto-Fechado', 'Fechado-Aberto')
  AND i.registro_principal = 1 AND i.situacao_item = 'Homologado'
  AND i.criterio_julgamento LIKE 'Menor pre%'
  AND i.valor_unitario_resultado > 0
  AND substr(c.data_publicacao, 1, 7) BETWEEN '2023-01' AND '2026-06'
"""
LOG = []


def log(*a):
    s = ' '.join(map(str, a))
    LOG.append(s)
    print(s.encode('ascii', 'replace').decode(), flush=True)


# ------------------------------------------------------------------ dados

def extrair():
    BASE.mkdir(parents=True, exist_ok=True)
    t = time.time()
    con = sqlite3.connect(f"file:{DADOS / 'pncp.db'}?mode=ro", uri=True)
    d = pd.read_sql_query(SQL, con)
    con.close()
    log('extraidos', len(d), f'{time.time() - t:.0f}s')
    n = pd.read_pickle(COMPRAS_USO)[['compra', 'n_itens']]
    d = d.merge(n, on='compra', how='left')
    log('sem n_itens', int(d.n_itens.isna().sum()))
    for k in ['compra', 'cnpj', 'uasg', 'uf', 'mes', 'modo', 'ms', 'unid', 'benef']:
        d[k] = d[k].astype('category')
    d.to_pickle(BASE / 'itens.pkl')
    mediana_comparaveis(d)


def mediana_comparaveis(d):
    """M por item: mediana das medianas por pregão do produto × ano × UF, sem o próprio CNPJ."""
    t = time.time()
    x = d[d.cat.notna() & d.unid.notna()][['compra', 'cnpj', 'uf', 'mes', 'cat', 'unid', 'p']].copy()
    x['cel'] = pd.MultiIndex.from_arrays([x.cat.astype(str), x.unid.astype(str), x.mes.astype(str).str[:4], x.uf.astype(str)]).factorize()[0]
    pg = x.groupby(['cel', 'compra'], observed=True).agg(cnpj=('cnpj', 'first'), med=('p', 'median')).reset_index()
    pg['cnpj'] = pg.cnpj.astype(str)
    st = pg.groupby('cel').agg(np_=('med', 'size'), nc=('cnpj', 'nunique'))
    ok = st[(st.np_ >= 6) & (st.nc >= 3)].index
    pg = pg[pg.cel.isin(ok)].sort_values(['cel', 'med'])
    saida = []
    for cel, g in pg.groupby('cel', sort=False):
        meds = g.med.to_numpy()
        cn = g.cnpj.to_numpy()
        for c in np.unique(cn):
            m = cn != c
            if m.sum() >= 5 and len(np.unique(cn[m])) >= 2:
                saida.append((cel, c, float(np.median(meds[m]))))
    ref = pd.DataFrame(saida, columns=['cel', 'cnpj', 'M'])
    x['cnpj_s'] = x.cnpj.astype(str)
    x = x.reset_index().merge(ref, left_on=['cel', 'cnpj_s'], right_on=['cel', 'cnpj'], how='left', suffixes=('', '_r'))
    m = pd.Series(x.M.to_numpy(), index=x['index'])
    out = pd.DataFrame({'M': m}).reindex(d.index)
    out['cel_ref'] = pd.Series(x.cel.to_numpy(), index=x['index']).reindex(d.index)
    out.to_pickle(BASE / 'mediana.pkl')
    log('mediana: celulas', len(st), 'elegiveis', len(ok), 'itens com M', int(out.M.notna().sum()), f'{time.time() - t:.0f}s')


def preparar():
    d = pd.read_pickle(BASE / 'itens.pkl')
    d = d.join(pd.read_pickle(BASE / 'mediana.pkl'))
    d = d[d.sig.notna()].copy()
    d['modo_c'] = d.modo.astype(str).map(MODOS)
    d['af'] = (d.modo_c == 'AF').astype(float)
    d['fa'] = (d.modo_c == 'FA').astype(float)
    d['sigiloso'] = d.sig.astype(float)
    d['servico'] = (d.ms.astype(str) == 'S').astype(float)
    d['srp'] = d.srp.fillna(0).astype(float)
    b = d.benef.astype(str)
    d['exclusiva'] = b.str.startswith('Participa').astype(float)
    d['cota'] = b.str.startswith('Cota').astype(float)
    q = d.q.astype(float)
    d['sem_q'] = (~(q > 0)).astype(float)
    d['log_q'] = np.where(q > 0, np.log(q.where(q > 0, 1)), 0.0)
    d['log_n'] = np.log(d.n_itens.fillna(1).clip(lower=1).astype(float))
    r, p = d.r.astype(float), d.p.astype(float)
    d['D'] = np.where(r > 0, 100 * (1 - p / r.where(r > 0, np.nan)), np.nan)
    d.loc[~d.D.between(-100, 99), 'D'] = np.nan
    d['L'] = np.where(d.M > 0, 100 * np.log(p / d.M.where(d.M > 0, np.nan)), np.nan)
    d['ano'] = d.mes.astype(str).str[:4]
    cod = lambda *cols: pd.MultiIndex.from_arrays([d[k].astype(str) for k in cols]).factorize()[0]
    d['prod_ano'] = np.where(d.cat.isna(), -1, cod('cat', 'unid', 'ano'))
    # grupo de CATMAT para o erro-padrão: sem código, agrupa pela compra
    cc = pd.factorize(d.compra)[0]
    ct = pd.factorize(d.cat)[0]
    d['cl_cat'] = np.where(ct < 0, ct.max() + 1 + cc, ct)
    d['sig_af'] = d.sigiloso * d.af
    d['sig_fa'] = d.sigiloso * d.fa
    d['serv_af'] = d.servico * d.af
    d['serv_fa'] = d.servico * d.fa
    for k in ['cnpj', 'uasg', 'mes']:
        d[k] = pd.factorize(d[k])[0]
    return d


# ------------------------------------------------------------------ estimação

def codigos(s):
    return pd.factorize(s, sort=False)[0]


def sem_singletons(df, fes):
    keep = np.ones(len(df), bool)
    arr = [codigos(df[f]) for f in fes]
    while True:
        mudou = False
        for a in arr:
            cnt = np.bincount(a[keep], minlength=a.max() + 1)
            fora = keep & (cnt[a] == 1)
            if fora.any():
                keep &= ~fora
                mudou = True
        if not mudou:
            return df[keep]


def demean(M, grupos, tol=1e-8, maxit=500):
    M = M.astype(float).copy()
    if not grupos:
        return M - M.mean(axis=0)
    cont = [np.bincount(g).astype(float) for g in grupos]
    for _ in range(maxit):
        mx = 0.0
        for g, n in zip(grupos, cont):
            med = np.column_stack([np.bincount(g, weights=M[:, j]) / n for j in range(M.shape[1])])
            M -= med[g]
            mx = max(mx, np.abs(med).max())
        if len(grupos) == 1 or mx < tol:
            break
    return M


def estimar(df, y, xs, fes, termos, clusters=('cnpj', 'cl_cat')):
    df = df[df[y].notna()]
    if fes:
        df = sem_singletons(df, fes)
    if len(df) < 50:
        return []
    grupos = [codigos(df[f]) for f in fes]
    M = demean(df[[y] + xs].to_numpy(float), grupos)
    Y, X = M[:, 0], M[:, 1:]
    ok = X.std(axis=0) > 1e-10
    X = X[:, ok]
    nomes = [x for x, k in zip(xs, ok) if k]
    XtX_inv = np.linalg.pinv(X.T @ X)
    b = XtX_inv @ X.T @ Y
    u = Y - X @ b
    S = X * u[:, None]
    n, k = X.shape
    cls = [codigos(df[c]) for c in clusters]
    inter = pd.MultiIndex.from_arrays(cls).factorize()[0]
    V = np.zeros((k, k))
    Gs = []
    for cl, sinal in [(cls[0], 1), (cls[1], 1), (inter, -1)]:
        G = cl.max() + 1
        Sg = np.column_stack([np.bincount(cl, weights=S[:, j], minlength=G) for j in range(k)])
        V += sinal * (G / (G - 1)) * ((n - 1) / (n - k)) * (XtX_inv @ (Sg.T @ Sg) @ XtX_inv)
        Gs.append(G)
    gl = min(Gs[:2]) - 1
    se = np.sqrt(np.clip(np.diag(V), 0, None))
    tc = stats.t.ppf(.975, gl)
    out = []
    for j, nome in enumerate(nomes):
        if nome not in termos:
            continue
        t = b[j] / se[j] if se[j] > 0 else np.nan
        out.append({'termo': nome, 'coef': b[j], 'ep': se[j], 't': t, 'p': 2 * stats.t.sf(abs(t), gl),
                    'ic95_inf': b[j] - tc * se[j], 'ic95_sup': b[j] + tc * se[j], 'n': int(n),
                    'g_cnpj': int(Gs[0]), 'g_cat': int(Gs[1]), 'media_y': float(df[y].mean())})
    return out


COV = ['srp', 'log_q', 'sem_q', 'log_n', 'exclusiva', 'cota']
SPECS = {'E1': ([], ['mes']), 'E2': (COV, ['mes', 'uasg']), 'E3': (COV, ['mes', 'uasg', 'prod_ano'])}


def winsor(s):
    lo, hi = s.quantile([.01, .99])
    return s.clip(lo, hi)


def est(y):
    d = preparar()
    log('itens', len(d), y, 'com desfecho', int(d[y].notna().sum()))
    linhas = []

    def reg(base, yy, xs, fes, termos, **meta):
        t = time.time()
        r = estimar(base, yy, xs, fes, termos)
        for x in r:
            linhas.append({'desfecho': y, **meta, **x})
        log(y, meta, {x['termo']: round(x['coef'], 2) for x in r}, f'{time.time() - t:.0f}s')

    for e, (cov, fes) in SPECS.items():
        base = d[d.prod_ano >= 0] if e == 'E3' else d
        # (a) efeito em cada modo
        for m in ['A', 'AF', 'FA']:
            reg(base[base.modo_c == m], y, ['sigiloso', 'servico'] + cov, fes, ['sigiloso', 'servico'], espec=e, modelo='a_por_modo', modo=m)
        # (b) interações
        xs = ['af', 'fa', 'sigiloso', 'servico', 'sig_af', 'sig_fa', 'serv_af', 'serv_fa'] + cov
        reg(base, y, xs, fes, ['af', 'fa', 'sigiloso', 'servico', 'sig_af', 'sig_fa', 'serv_af', 'serv_fa'], espec=e, modelo='b_interacao', modo='todos')
        # (c) modos sem e com os controles
        reg(base, y, ['af', 'fa'] + cov, fes, ['af', 'fa'], espec=e, modelo='c_sem_controles', modo='todos')
        reg(base, y, ['af', 'fa', 'sigiloso', 'servico'] + cov, fes, ['af', 'fa', 'sigiloso', 'servico'], espec=e, modelo='c_com_controles', modo='todos')
    # sensibilidade: E2 com desfecho winsorizado
    w = d[d[y].notna()].copy()
    w['yw'] = winsor(w[y])
    cov, fes = SPECS['E2']
    for m in ['A', 'AF', 'FA']:
        reg(w[w.modo_c == m], 'yw', ['sigiloso', 'servico'] + cov, fes, ['sigiloso', 'servico'], espec='E2-winsor', modelo='a_por_modo', modo=m)
    reg(w, 'yw', ['af', 'fa', 'sigiloso', 'servico', 'sig_af', 'sig_fa', 'serv_af', 'serv_fa'] + cov, fes,
        ['af', 'fa', 'sigiloso', 'servico', 'sig_af', 'sig_fa', 'serv_af', 'serv_fa'], espec='E2-winsor', modelo='b_interacao', modo='todos')
    pd.DataFrame(linhas).to_csv(AQUI / f'resultados_{y}.csv', index=False, encoding='utf-8')


def holm_ps(ps):
    ps = np.asarray(ps, float)
    ordem = np.argsort(ps)
    m = len(ps)
    adj = np.empty(m)
    acc = 0.0
    for r, i in enumerate(ordem):
        acc = max(acc, (m - r) * ps[i])
        adj[i] = min(1.0, acc)
    return adj


def holm():
    r = pd.concat([pd.read_csv(AQUI / f'resultados_{y}.csv') for y in ['D', 'L']], ignore_index=True)
    r['familia'] = ''
    f1 = (r.espec == 'E2') & (r.modelo == 'a_por_modo') & r.termo.isin(['sigiloso', 'servico'])
    f2 = (r.espec == 'E2') & (r.modelo == 'b_interacao') & r.termo.isin(['sig_af', 'sig_fa', 'serv_af', 'serv_fa'])
    r.loc[f1, 'familia'] = 'F1'
    r.loc[f2, 'familia'] = 'F2'
    r['p_holm'] = np.nan
    for f, m in [('F1', f1), ('F2', f2)]:
        log(f, 'testes', int(m.sum()))
        r.loc[m, 'p_holm'] = holm_ps(r.loc[m, 'p'])
    r.to_csv(AQUI / 'resultados.csv', index=False, encoding='utf-8')


def desc():
    d = preparar()
    g = d.groupby(['modo_c', 'servico', 'sigiloso'])
    t = pd.DataFrame({'itens': g.size(), 'com_R': g.D.count(), 'D_media': g.D.mean(), 'D_mediana': g.D.median(),
                      'com_M': g.L.count(), 'L_media': g.L.mean(), 'L_mediana': g.L.median(),
                      'compras': g.compra.nunique()}).reset_index()
    t['pct_com_R'] = 100 * t.com_R / t.itens
    t['pct_com_M'] = 100 * t.com_M / t.itens
    t.round(3).to_csv(AQUI / 'descritivas.csv', index=False, encoding='utf-8')
    g2 = d.groupby('modo_c')
    t2 = pd.DataFrame({'itens': g2.size(), 'pct_sigiloso': 100 * g2.sigiloso.mean(), 'pct_servico': 100 * g2.servico.mean(),
                       'D_media': g2.D.mean(), 'L_media': g2.L.mean(), 'compras': g2.compra.nunique(), 'cnpjs': g2.cnpj.nunique()}).reset_index()
    t2.round(3).to_csv(AQUI / 'descritivas_modo.csv', index=False, encoding='utf-8')
    log(t2.round(2).to_string())


def main():
    t0 = time.time()
    a = sys.argv[1:]
    if a[0] == 'extrair':
        extrair()
    elif a[0] == 'mediana':
        mediana_comparaveis(pd.read_pickle(BASE / 'itens.pkl'))
    elif a[0] == 'desc':
        desc()
    elif a[0] == 'est':
        est(a[1])
    elif a[0] == 'holm':
        holm()
    log(f'{a} fim em {time.time() - t0:.0f}s')
    with (AQUI / 'log_execucao.txt').open('a', encoding='utf-8') as f:
        f.write('\n'.join(LOG) + '\n')


if __name__ == '__main__':
    main()
