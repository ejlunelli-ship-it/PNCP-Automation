"""Testes de diferença de desfecho (fracassado, deserto, não homologado) entre modos de disputa.

Segue analises/desfecho_modos_20261121/protocolo.md. Lê dados/pncp.db (somente leitura), grava a base
extraída em dados/analise_desfecho/ (fora do git) e os resultados nesta pasta.

    python analises/desfecho_modos_20261121/testes_desfecho.py [--reextrair]
"""
import json
import os
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
DADOS = Path(os.environ.get('PNCP_DADOS', RAIZ / 'dados'))
CACHE = DADOS / 'analise_desfecho'
MODOS = ['Aberto', 'Aberto-Fechado', 'Fechado-Aberto']

SQL = """
SELECT c.numero_controle_pncp AS compra, c.orgao_cnpj AS cnpj, COALESCE(i.uasg_item, c.uasg) AS uasg,
       substr(c.data_publicacao, 1, 7) AS mes, c.modo_disputa AS modo, c.srp AS srp,
       i.situacao_item AS sit, i.material_ou_servico AS ms, i.cod_item_catalogo AS cat,
       i.criterio_julgamento AS crit, i.tipo_beneficio AS benef, i.orcamento_sigiloso AS sig,
       i.quantidade AS q, i.valor_unitario_estimado AS vu
FROM itens i JOIN compras c ON c.numero_controle_pncp = i.numero_controle_pncp
WHERE c.fonte = 'dados_abertos' AND c.modalidade_nome LIKE 'Preg%Eletr%'
  AND c.modo_disputa IN ('Aberto', 'Aberto-Fechado', 'Fechado-Aberto')
  AND i.registro_principal = 1
  AND substr(c.data_publicacao, 1, 7) BETWEEN '2023-01' AND '2026-06'
"""


def extrair(reextrair=False):
    CACHE.mkdir(parents=True, exist_ok=True)
    arq = CACHE / 'base_itens.pkl'
    if arq.exists() and not reextrair:
        return pd.read_pickle(arq)
    con = sqlite3.connect(f"file:{DADOS / 'pncp.db'}?mode=ro", uri=True)
    df = pd.read_sql_query(SQL, con)
    con.close()
    for c in ['compra', 'cnpj', 'uasg', 'mes', 'modo', 'sit', 'ms', 'cat', 'crit', 'benef']:
        df[c] = df[c].astype('category')
    df.to_pickle(arq)
    return df


def preparar(df):
    """Variáveis de item e base de compras."""
    d = df.copy()
    d['n_itens_compra'] = d.groupby('compra', observed=True).compra.transform('size')
    d = d[d.sit.isin(['Homologado', 'Fracassado', 'Deserto'])].copy()
    d['fracassado'] = (d.sit == 'Fracassado').astype(float)
    d['deserto'] = (d.sit == 'Deserto').astype(float)
    d['nao_homologado'] = d.fracassado + d.deserto
    d['af'] = (d.modo == 'Aberto-Fechado').astype(float)
    d['fa'] = (d.modo == 'Fechado-Aberto').astype(float)
    d['srp'] = d.srp.fillna(0).astype(float)
    d['sig'] = d.sig.fillna(0).astype(float)
    d['maior_desc'] = (d.crit.astype(str) == 'Maior desconto').astype(float)
    b = d.benef.astype(str)
    d['exclusiva'] = b.str.startswith('Participa').astype(float)
    d['cota'] = b.str.startswith('Cota').astype(float)
    v = d.q.astype(float) * d.vu.astype(float)
    d['sem_valor'] = ~(v > 0)
    d['log_valor'] = np.where(d.sem_valor, 0.0, np.log(v.where(v > 0, 1)))
    d['sem_valor'] = d.sem_valor.astype(float)
    d['log_n_itens'] = np.log(d.n_itens_compra.astype(float))
    d['material'] = (d.ms.astype(str) == 'M').astype(float)
    d['ano'] = d.mes.astype(str).str[:4]
    cod = lambda *cols: pd.MultiIndex.from_arrays([d[k] for k in cols]).factorize()[0] if len(cols) > 1 else pd.factorize(d[cols[0]])[0]
    d['mes_ms'] = cod('mes', 'ms')
    d['cel'] = np.where(d.cat.isna(), -1, cod('uasg', 'cat', 'ano'))
    # CATMAT para agrupamento: sem código, agrupa pelos itens da mesma compra
    cc = pd.factorize(d.compra)[0]
    ct = pd.factorize(d.cat)[0]
    d['cl_cat'] = np.where(ct < 0, ct.max() + 1 + cc, ct)
    d['valor_pos'] = np.where(v > 0, v, 0.0)

    g = d.groupby('compra', observed=True)
    c = pd.DataFrame({
        'cnpj': g.cnpj.first(), 'uasg': g.uasg.first(), 'mes': g.mes.first(), 'mes_txt': g.mes.first().astype(str), 'modo': g.modo.first(),
        'srp': g.srp.first(), 'n_dec': g.size(), 'n_nao': g.nao_homologado.sum(),
        'valor': g.valor_pos.sum(), 'material': g.material.mean(), 'sig': g.sig.mean(), 'exclusiva': g.exclusiva.mean(),
    }).reset_index()
    c['n_hom'] = c.n_dec - c.n_nao
    c['compra_sem_hom'] = (c.n_hom == 0).astype(float)
    c['compra_toda_hom'] = (c.n_hom == c.n_dec).astype(float)
    c['af'] = (c.modo == 'Aberto-Fechado').astype(float)
    c['fa'] = (c.modo == 'Fechado-Aberto').astype(float)
    c['sem_valor'] = (c.valor <= 0).astype(float)
    c['log_valor'] = np.where(c.valor > 0, np.log(c.valor.where(c.valor > 0, 1)), 0.0)
    c['log_n_dec'] = np.log(c.n_dec.astype(float))
    for k in ['cnpj', 'uasg', 'mes']:
        c[k] = pd.factorize(c[k])[0]
    for k in ['cnpj', 'uasg']:
        d[k] = pd.factorize(d[k])[0]
    return d, c


def codigos(s):
    return pd.factorize(s, sort=False)[0]


def sem_singletons(df, fes):
    keep = np.ones(len(df), bool)
    arr = [df[f].to_numpy() for f in fes]
    while True:
        mudou = False
        for a in arr:
            cnt = np.bincount(a[keep])
            fora = keep & (cnt[np.where(keep, a, 0)] == 1)
            if fora.any():
                keep &= ~fora
                mudou = True
        if not mudou:
            return df[keep]


def demean(M, grupos, tol=1e-9, maxit=1000):
    M = M.copy()
    if not grupos:
        return M - M.mean(axis=0)
    cont = [np.bincount(g).astype(float) for g in grupos]
    for it in range(maxit):
        mx = 0.0
        for g, n in zip(grupos, cont):
            med = np.column_stack([np.bincount(g, weights=M[:, j]) / n for j in range(M.shape[1])])
            M -= med[g]
            mx = max(mx, np.abs(med).max())
        if len(grupos) == 1 or mx < tol:
            break
    return M


def meat(S, cl):
    G = cl.max() + 1
    Sg = np.column_stack([np.bincount(cl, weights=S[:, j], minlength=G) for j in range(S.shape[1])])
    return Sg.T @ Sg, G


def estimar(df, y, xs, fes, clusters):
    if fes:
        df = sem_singletons(df, fes)
    grupos = [codigos(df[f]) for f in fes]
    M = demean(df[[y] + xs].to_numpy(float), grupos)
    Y, X = M[:, 0], M[:, 1:]
    # remove colunas sem variação depois de absorver os efeitos fixos
    ok = X.std(axis=0) > 1e-10
    ok[:2] = True
    X = X[:, ok]
    nomes = [x for x, k in zip(xs, ok) if k]
    XtX_inv = np.linalg.inv(X.T @ X)
    b = XtX_inv @ X.T @ Y
    u = Y - X @ b
    S = X * u[:, None]
    n, k = X.shape
    cls = [codigos(df[c]) for c in clusters]
    if len(cls) == 2:
        inter = pd.MultiIndex.from_arrays([cls[0], cls[1]]).factorize()[0]
        partes = [(cls[0], 1), (cls[1], 1), (inter, -1)]
    else:
        partes = [(cls[0], 1)]
    V = np.zeros((k, k))
    Gs = []
    for cl, sinal in partes:
        m, G = meat(S, cl)
        Gs.append(G)
        V += sinal * (G / (G - 1)) * ((n - 1) / (n - k)) * (XtX_inv @ m @ XtX_inv)
    Gmin = min(Gs[:len(cls)])
    se = np.sqrt(np.clip(np.diag(V), 0, None))
    out = {}
    for j, nome in enumerate(nomes[:2]):
        t = b[j] / se[j]
        out[nome] = {'coef_pp': 100 * b[j], 'ep_pp': 100 * se[j], 't': t,
                     'p': 2 * stats.t.sf(abs(t), Gmin - 1),
                     'ic95_pp': [100 * (b[j] - stats.t.ppf(.975, Gmin - 1) * se[j]),
                                 100 * (b[j] + stats.t.ppf(.975, Gmin - 1) * se[j])]}
    meta = {'n': int(n), 'grupos': {c: int(g) for c, g in zip(clusters, Gs)},
            'n_af': int(df.af.sum()), 'n_fa': int(df.fa.sum()), 'n_a': int(n - df.af.sum() - df.fa.sum()),
            'media_a_pct': 100 * float(df.loc[(df.af == 0) & (df.fa == 0), y].mean())}
    return out, meta


def holm(ps):
    ordem = np.argsort(ps)
    m = len(ps)
    adj = np.empty(m)
    acc = 0.0
    for r, i in enumerate(ordem):
        acc = max(acc, (m - r) * ps[i])
        adj[i] = min(1.0, acc)
    return adj


def main():
    df = extrair('--reextrair' in sys.argv)
    d, c = preparar(df)
    del df
    print('itens decididos', len(d), 'compras', len(c), flush=True)

    xi = ['af', 'fa', 'srp', 'sig', 'maior_desc', 'exclusiva', 'cota', 'log_valor', 'sem_valor', 'log_n_itens']
    xc = ['af', 'fa', 'srp', 'log_valor', 'sem_valor', 'log_n_dec', 'material', 'sig', 'exclusiva']
    specs_item = {
        'E1': (['af', 'fa'], []),
        'E2': (xi, ['mes_ms']),
        'E3': (xi, ['mes_ms', 'uasg']),
        'E4': (xi, ['cel', 'mes_ms']),
    }
    specs_compra = {
        'E1': (['af', 'fa'], []),
        'E2': (xc, ['mes']),
        'E3': (xc, ['mes', 'uasg']),
    }
    linhas = []
    for y in ['fracassado', 'deserto', 'nao_homologado']:
        for e, (xs, fes) in specs_item.items():
            base = d[d.cel >= 0] if e == 'E4' else d
            r, meta = estimar(base, y, xs, fes, ['cnpj', 'cl_cat'])
            for ctr, nome in [('af', 'AF − A'), ('fa', 'FA − A')]:
                linhas.append({'nivel': 'item', 'desfecho': y, 'espec': e, 'contraste': nome, **r[ctr], **meta})
            print(y, e, {k: round(v['coef_pp'], 2) for k, v in r.items()}, flush=True)
    for y in ['compra_sem_hom', 'compra_toda_hom']:
        for e, (xs, fes) in specs_compra.items():
            r, meta = estimar(c, y, xs, fes, ['cnpj'])
            for ctr, nome in [('af', 'AF − A'), ('fa', 'FA − A')]:
                linhas.append({'nivel': 'compra', 'desfecho': y, 'espec': e, 'contraste': nome, **r[ctr], **meta})
            print(y, e, {k: round(v['coef_pp'], 2) for k, v in r.items()}, flush=True)

    res = pd.DataFrame(linhas)
    principal = res.espec == 'E3'
    res['p_holm'] = np.nan
    res.loc[principal, 'p_holm'] = holm(res.loc[principal, 'p'].to_numpy())
    res['ic95_inf_pp'] = res.ic95_pp.str[0]
    res['ic95_sup_pp'] = res.ic95_pp.str[1]
    res['grupos'] = res.grupos.apply(json.dumps)
    res = res.drop(columns='ic95_pp')
    res.to_csv(AQUI / 'resultados.csv', index=False, encoding='utf-8')

    # descritivas: taxas por modo e ano
    desc = d.groupby(['ano', 'modo'], observed=True)[['fracassado', 'deserto', 'nao_homologado']].mean().mul(100).round(2)
    desc['itens'] = d.groupby(['ano', 'modo'], observed=True).size()
    desc.reset_index().to_csv(AQUI / 'descritivas_itens.csv', index=False, encoding='utf-8')
    c['ano'] = c.mes_txt.str[:4]
    dc = c.groupby(['ano', 'modo'], observed=True)[['compra_sem_hom', 'compra_toda_hom']].mean().mul(100).round(2)
    dc['compras'] = c.groupby(['ano', 'modo'], observed=True).size()
    dc.reset_index().to_csv(AQUI / 'descritivas_compras.csv', index=False, encoding='utf-8')
    print(res.to_string().encode("ascii", "replace").decode())


if __name__ == '__main__':
    main()
