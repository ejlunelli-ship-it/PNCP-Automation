"""Uso dos modos Aberto-Fechado e Fechado-Aberto: tendência e associações (protocolo.md).

Lê a extração de extracao.py (dados/analise_uso_modos/) e, para a parte em nível de item, a base da
análise de desfecho (dados/analise_desfecho/base_itens.pkl). Grava os resultados nesta pasta.

    python analises/uso_modos_20261121/extracao.py   # uma vez (~20 min)
    python analises/uso_modos_20261121/uso_modos.py
"""
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
DADOS = Path(os.environ.get('PNCP_DADOS', RAIZ / 'dados'))
BASE = DADOS / 'analise_uso_modos'
ITENS = DADOS / 'analise_desfecho' / 'base_itens.pkl'

REGIAO = {**{u: 'Norte' for u in 'AC AP AM PA RO RR TO'.split()},
          **{u: 'Nordeste' for u in 'AL BA CE MA PB PE PI RN SE'.split()},
          **{u: 'Centro-Oeste' for u in 'DF GO MT MS'.split()},
          **{u: 'Sudeste' for u in 'ES MG RJ SP'.split()},
          **{u: 'Sul' for u in 'PR RS SC'.split()}}
CTRL = ['srp', 'log_valor', 'sem_valor', 'log_n', 'f_mat', 'f_desc', 'f_excl', 'f_cota', 'f_sig']
NOMES = {'t': 'Tendência (p.p. por ano)', 'srp': 'Registro de preços', 'log_valor': 'Log do valor estimado',
         'sem_valor': 'Sem valor estimado', 'log_n': 'Log do nº de itens', 'f_mat': 'Parcela de itens de material',
         'f_desc': 'Parcela com critério Maior desconto', 'f_excl': 'Parcela exclusiva ME/EPP',
         'f_cota': 'Parcela com cota ME/EPP', 'f_sig': 'Parcela com orçamento sigiloso',
         'esf_F': 'Esfera federal', 'esf_E': 'Esfera estadual', 'esf_D': 'Distrito Federal', 'esf_N': 'Esfera não informada/outra',
         'jud': 'Poder Judiciário', 'leg': 'Poder Legislativo'}
LOG = []


def log(*a):
    s = ' '.join(map(str, a))
    LOG.append(s)
    print(s.encode('ascii', 'replace').decode(), flush=True)


# ---------------------------------------------------------------- estimação

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


def estimar(df, y, xs, fes, cluster='cnpj'):
    """MQO com efeitos fixos absorvidos e erro-padrão agrupado em uma via. Devolve todos os coeficientes."""
    if fes:
        df = sem_singletons(df, fes)
    grupos = [codigos(df[f]) for f in fes]
    M = demean(df[[y] + xs].to_numpy(float), grupos)
    Y, X = M[:, 0], M[:, 1:]
    ok = X.std(axis=0) > 1e-10
    X = X[:, ok]
    nomes = [x for x, k in zip(xs, ok) if k]
    XtX_inv = np.linalg.pinv(X.T @ X)
    b = XtX_inv @ X.T @ Y
    u = Y - X @ b
    cl = codigos(df[cluster])
    G = cl.max() + 1
    S = X * u[:, None]
    Sg = np.column_stack([np.bincount(cl, weights=S[:, j], minlength=G) for j in range(S.shape[1])])
    n, k = X.shape
    V = (G / (G - 1)) * ((n - 1) / (n - k)) * XtX_inv @ (Sg.T @ Sg) @ XtX_inv
    se = np.sqrt(np.clip(np.diag(V), 0, None))
    tc = stats.t.ppf(.975, G - 1)
    linhas = []
    for j, nome in enumerate(nomes):
        t = b[j] / se[j] if se[j] > 0 else np.nan
        linhas.append({'termo': nome, 'coef_pp': 100 * b[j], 'ep_pp': 100 * se[j], 't': t,
                       'p': 2 * stats.t.sf(abs(t), G - 1), 'ic95_inf_pp': 100 * (b[j] - tc * se[j]),
                       'ic95_sup_pp': 100 * (b[j] + tc * se[j])})
    meta = {'n': int(n), 'grupos_cnpj': int(G), 'media_y_pct': 100 * float(df[y].mean())}
    return pd.DataFrame(linhas).assign(**meta)


def r2(df, y, fes):
    grupos = [codigos(df[f]) for f in fes]
    e = demean(df[[y]].to_numpy(float), grupos)[:, 0]
    yy = df[y].to_numpy(float)
    sst = ((yy - yy.mean()) ** 2).sum()
    n = len(yy)
    k = sum(g.max() + 1 for g in grupos) - max(0, len(grupos) - 1)
    r = 1 - (e ** 2).sum() / sst
    return r, 1 - (1 - r) * (n - 1) / max(1, n - k), k


def holm(ps):
    ps = np.asarray(ps, float)
    ordem = np.argsort(ps)
    m = len(ps)
    adj = np.empty(m)
    acc = 0.0
    for r, i in enumerate(ordem):
        acc = max(acc, (m - r) * ps[i])
        adj[i] = min(1.0, acc)
    return adj


# ---------------------------------------------------------------- dados

def preparar():
    c = pd.read_pickle(BASE / 'compras.pkl')
    cat = pd.read_pickle(BASE / 'categorias.pkl')
    c['af'] = (c.modo == 'Aberto-Fechado').astype(float)
    c['fa'] = (c.modo == 'Fechado-Aberto').astype(float)
    da = c.fonte == 'dados_abertos'
    c['unidade'] = np.where(da, 'D' + c.uasg.astype(str), 'P' + c.cnpj.astype(str) + '|' + c.codigo_unidade.astype(str))
    c['nome_un'] = np.where(da, c.orgao_nome, c.nome_unidade.fillna(c.orgao_nome))
    m = c.mes.str[:4].astype(int) * 12 + c.mes.str[5:7].astype(int)
    c['t'] = (m - (2022 * 12 + 11)) / 12
    c['moy'] = c.mes.str[5:7]
    c['ano'] = c.mes.str[:4]
    c['semestre'] = c.ano + '-S' + np.where(c.mes.str[5:7].astype(int) <= 6, '1', '2')
    c['srp'] = c.srp.fillna(0).astype(float)
    c['sem_valor'] = ~(c.valor > 0)
    c['log_valor'] = np.where(c.sem_valor, 0.0, np.log(c.valor.where(c.valor > 0, 1)))
    c['sem_valor'] = c.sem_valor.astype(float)
    c['log_n'] = np.log(c.n_itens.clip(lower=1).astype(float))
    for k in ['f_mat', 'f_desc', 'f_excl', 'f_cota', 'f_sig']:
        c[k] = c[k].fillna(0).astype(float)
    for e in ['F', 'E', 'D']:
        c[f'esf_{e}'] = (c.esfera == e).astype(float)
    c['esf_N'] = (~c.esfera.isin(['F', 'E', 'D', 'M'])).astype(float)
    c['jud'] = (c.poder == 'J').astype(float)
    c['leg'] = (c.poder == 'L').astype(float)
    c['regiao'] = c.uf.map(REGIAO).fillna('Sem UF')
    for r in ['Norte', 'Nordeste', 'Centro-Oeste', 'Sul']:
        c[f'reg_{r}'] = (c.regiao == r).astype(float)
        NOMES[f'reg_{r}'] = f'Região {r}'
    top = c[~da].plat.value_counts().index[:12]
    c['plataforma'] = np.where(da, 'Compras.gov.br', np.where(c.plat.isin(top), c.plat, 'Outras plataformas (demais)'))
    plats = [p for p in c.plataforma.value_counts().index if p != 'Compras.gov.br']
    for j, p in enumerate(plats):
        c[f'plat_{j}'] = (c.plataforma == p).astype(float)
        NOMES[f'plat_{j}'] = f'Plataforma: {p}'
    # categoria predominante (Compras.gov.br)
    cat = cat.sort_values(['compra', 'n', 'cat'], ascending=[True, False, True]).drop_duplicates('compra')
    c = c.merge(cat[['compra', 'cat']], on='compra', how='left')
    c['ucat'] = np.where(c.cat.notna(), c.unidade + '#' + c.cat.astype(str), None)
    return c, plats


# ---------------------------------------------------------------- partes

FONTES = {'Compras.gov.br': lambda c: c.fonte == 'dados_abertos', 'Outras plataformas': lambda c: c.fonte == 'pncp',
          'Todas': lambda c: np.ones(len(c), bool)}
MODOS = {'af': 'Aberto-Fechado', 'fa': 'Fechado-Aberto'}


def descritivas(c):
    g = c.groupby(['mes', 'fonte'])
    m = pd.DataFrame({'compras': g.size(), 'af': g.af.sum(), 'fa': g.fa.sum()}).reset_index()
    t = c.groupby('mes').agg(compras=('af', 'size'), af=('af', 'sum'), fa=('fa', 'sum')).reset_index().assign(fonte='todas')
    m = pd.concat([m, t])
    m['pct_af'] = 100 * m.af / m.compras
    m['pct_fa'] = 100 * m.fa / m.compras
    m.to_csv(AQUI / 'mensal_modos.csv', index=False, encoding='utf-8')
    for dim in ['ano', 'esfera', 'regiao', 'plataforma']:
        d = c.groupby(['fonte', dim] if dim != 'plataforma' else [dim]).agg(compras=('af', 'size'), pct_af=('af', 'mean'), pct_fa=('fa', 'mean'))
        d[['pct_af', 'pct_fa']] *= 100
        d.round(3).reset_index().to_csv(AQUI / f'perfil_{dim}.csv', index=False, encoding='utf-8')
    # parcela por ano e plataforma
    d = c.groupby(['plataforma', 'ano']).agg(compras=('af', 'size'), pct_af=('af', 'mean'), pct_fa=('fa', 'mean'))
    d[['pct_af', 'pct_fa']] *= 100
    d.round(3).reset_index().to_csv(AQUI / 'perfil_plataforma_ano.csv', index=False, encoding='utf-8')


def tendencia(c):
    linhas = []
    for fnome, f in FONTES.items():
        d = c[f(c)]
        for y in ['af', 'fa']:
            specs = {'T1': (['t'], ['moy']), 'T2': (['t'], ['moy', 'unidade']),
                     'T3': (['t'] + CTRL, ['moy', 'unidade', 'plataforma'])}
            # sensibilidade posterior ao protocolo: só a partir de 2024-01 (2023 foi a transição para a Lei 14.133)
            specs.update({'T1-2024': (['t'], ['moy']), 'T2-2024': (['t'], ['moy', 'unidade'])})
            for e, (xs, fes) in specs.items():
                r = estimar(d[d.ano >= '2024'] if e.endswith('2024') else d, y, xs, fes)
                r = r[r.termo == 't'].assign(fonte=fnome, modo=MODOS[y], espec=e)
                linhas.append(r)
                log('tendencia', fnome, y, e, round(r.coef_pp.iloc[0], 3), 'p', round(r.p.iloc[0], 4))
    res = pd.concat(linhas, ignore_index=True)
    fam = (res.espec == 'T2') & res.fonte.isin(['Compras.gov.br', 'Outras plataformas'])
    res['p_holm'] = np.nan
    res.loc[fam, 'p_holm'] = holm(res.loc[fam, 'p'])
    res.to_csv(AQUI / 'tendencia.csv', index=False, encoding='utf-8')

    # semestres, dentro da unidade (ref. 2023-S1)
    sems = sorted(c.semestre.unique())
    sl = []
    for fnome in ['Compras.gov.br', 'Outras plataformas']:
        d = c[FONTES[fnome](c)].copy()
        xs = []
        for s in sems:
            if s != '2023-S1':
                d[f's_{s}'] = (d.semestre == s).astype(float)
                xs.append(f's_{s}')
        for y in ['af', 'fa']:
            bruto = d.groupby('semestre')[y].mean() * 100
            r = estimar(d, y, xs, ['unidade'])
            r['semestre'] = r.termo.str[2:]
            ref = pd.DataFrame([{'semestre': '2023-S1', 'coef_pp': 0.0, 'ic95_inf_pp': 0.0, 'ic95_sup_pp': 0.0}])
            r = pd.concat([r, ref], ignore_index=True)
            r['pct_observado'] = r.semestre.map(bruto)
            r['fonte'], r['modo'] = fnome, MODOS[y]
            sl.append(r)
    pd.concat(sl, ignore_index=True).sort_values(['fonte', 'modo', 'semestre']).to_csv(AQUI / 'tendencia_semestres.csv', index=False, encoding='utf-8')

    # decomposição 2023 -> 2025
    dl = []
    for fnome in ['Compras.gov.br', 'Outras plataformas', 'Todas']:
        d = c[FONTES[fnome](c)]
        for y in ['af', 'fa']:
            a = {}
            for ano in ['2023', '2025']:
                g = d[d.ano == ano].groupby('unidade')[y].agg(['size', 'mean'])
                g['s'] = g['size'] / g['size'].sum()
                a[ano] = g
            g0, g1 = a['2023'], a['2025']
            P0, P1 = (g0.s * g0['mean']).sum(), (g1.s * g1['mean']).sum()
            cont = g0.index.intersection(g1.index)
            s0, s1, p0, p1 = g0.s[cont], g1.s[cont], g0['mean'][cont], g1['mean'][cont]
            ent = g1.drop(cont)
            sai = g0.drop(cont)
            comp = {'dentro': (s0 * (p1 - p0)).sum(), 'entre': ((s1 - s0) * (p0 - P0)).sum(),
                    'cruzado': ((s1 - s0) * (p1 - p0)).sum(), 'entrada': (ent.s * (ent['mean'] - P0)).sum(),
                    'saida': -(sai.s * (sai['mean'] - P0)).sum()}
            dl.append({'fonte': fnome, 'modo': MODOS[y], 'pct_2023': 100 * P0, 'pct_2025': 100 * P1, 'variacao_pp': 100 * (P1 - P0),
                       **{f'{k}_pp': 100 * v for k, v in comp.items()},
                       'unidades_2023': len(g0), 'unidades_2025': len(g1), 'unidades_nos_dois': len(cont),
                       'pct_compras_2025_de_unidades_novas': 100 * ent.s.sum()})
    pd.DataFrame(dl).to_csv(AQUI / 'tendencia_decomposicao.csv', index=False, encoding='utf-8')
    # adoção: unidades que usaram o modo ao menos uma vez, por ano
    ad = []
    for fnome in ['Compras.gov.br', 'Outras plataformas']:
        d = c[FONTES[fnome](c)]
        g = d.groupby(['ano', 'unidade']).agg(af=('af', 'max'), fa=('fa', 'max'), n=('af', 'size')).reset_index()
        g = g[g.n >= 5]
        r = g.groupby('ano').agg(unidades=('unidade', 'size'), pct_usou_af=('af', 'mean'), pct_usou_fa=('fa', 'mean')).reset_index()
        r[['pct_usou_af', 'pct_usou_fa']] *= 100
        ad.append(r.assign(fonte=fnome))
    pd.concat(ad).to_csv(AQUI / 'adocao_unidades.csv', index=False, encoding='utf-8')
    return res


def perfil(c, plats):
    """A1 (todas as fontes, sem efeito fixo de unidade) e A2 (dentro da unidade, por fonte)."""
    xs1 = ['esf_F', 'esf_E', 'esf_D', 'esf_N', 'jud', 'leg', 'reg_Norte', 'reg_Nordeste', 'reg_Centro-Oeste', 'reg_Sul'] + \
          [f'plat_{j}' for j in range(len(plats))] + CTRL
    out = []
    for y in ['af', 'fa']:
        r = estimar(c[c.regiao != 'Sem UF'], y, xs1, ['mes'])
        r['p_holm'] = holm(r.p)
        out.append(r.assign(modelo='A1', fonte='Todas', modo=MODOS[y]))
        log('A1', y, 'n', r.n.iloc[0])
        for fnome in ['Compras.gov.br', 'Outras plataformas']:
            r = estimar(c[FONTES[fnome](c)], y, CTRL, ['unidade', 'mes'])
            r['p_holm'] = holm(r.p)
            out.append(r.assign(modelo='A2', fonte=fnome, modo=MODOS[y]))
            log('A2', fnome, y, 'n', r.n.iloc[0])
    res = pd.concat(out, ignore_index=True)
    res['termo_nome'] = res.termo.map(NOMES).fillna(res.termo)
    res.to_csv(AQUI / 'associacao_perfil.csv', index=False, encoding='utf-8')


def decomposicao_r2(c):
    linhas = []
    da = c[(c.fonte == 'dados_abertos') & c.cat.notna()]
    da = sem_singletons(da, ['ucat'])  # mesma amostra em todas as combinações
    combos = {'mês': ['mes'], 'categoria': ['cat'], 'unidade': ['unidade'], 'órgão (CNPJ)': ['cnpj'],
              'mês + categoria': ['mes', 'cat'], 'mês + unidade': ['mes', 'unidade'],
              'mês + unidade + categoria': ['mes', 'unidade', 'cat'], 'mês + unidade × categoria': ['mes', 'ucat']}
    for y in ['af', 'fa']:
        for nome, fes in combos.items():
            r, ra, k = r2(da, y, fes)
            linhas.append({'base': 'Compras.gov.br, compras', 'modo': MODOS[y], 'efeitos_fixos': nome, 'r2': r, 'r2_ajustado': ra, 'parametros': k, 'n': len(da)})
            log('R2 da', y, nome, round(r, 3), round(ra, 3))
    pn = c[c.fonte == 'pncp']
    pn = sem_singletons(pn, ['unidade'])
    combos = {'mês': ['mes'], 'plataforma': ['plataforma'], 'órgão (CNPJ)': ['cnpj'], 'unidade': ['unidade'],
              'mês + plataforma': ['mes', 'plataforma'], 'mês + unidade': ['mes', 'unidade']}
    for y in ['af', 'fa']:
        for nome, fes in combos.items():
            r, ra, k = r2(pn, y, fes)
            linhas.append({'base': 'Outras plataformas, compras', 'modo': MODOS[y], 'efeitos_fixos': nome, 'r2': r, 'r2_ajustado': ra, 'parametros': k, 'n': len(pn)})
            log('R2 pncp', y, nome, round(r, 3), round(ra, 3))
    # nível de item (CATMAT/CATSER)
    if ITENS.exists():
        it = pd.read_pickle(ITENS)[['compra', 'uasg', 'mes', 'modo', 'cat']]
        it = it[it.cat.notna()].copy()
        it['af'] = (it.modo == 'Aberto-Fechado').astype(float)
        it['fa'] = (it.modo == 'Fechado-Aberto').astype(float)
        it['cel'] = pd.MultiIndex.from_arrays([it.uasg, it.cat]).factorize()[0]
        it = sem_singletons(it, ['cel'])
        combos = {'mês': ['mes'], 'item de catálogo': ['cat'], 'UASG': ['uasg'], 'mês + item de catálogo': ['mes', 'cat'],
                  'mês + UASG': ['mes', 'uasg'], 'mês + UASG + item de catálogo': ['mes', 'uasg', 'cat'],
                  'mês + UASG × item de catálogo': ['mes', 'cel']}
        for y in ['af', 'fa']:
            for nome, fes in combos.items():
                r, ra, k = r2(it, y, fes)
                linhas.append({'base': 'Compras.gov.br, itens (2023-01 a 2026-06)', 'modo': MODOS[y], 'efeitos_fixos': nome, 'r2': r, 'r2_ajustado': ra, 'parametros': k, 'n': len(it)})
                log('R2 itens', y, nome, round(r, 3), round(ra, 3))
        del it
    pd.DataFrame(linhas).to_csv(AQUI / 'associacao_r2.csv', index=False, encoding='utf-8')


def efeitos_categoria(c):
    rot = pd.read_pickle(BASE / 'rotulos.pkl').set_index('cat').descricoes
    d = c[(c.fonte == 'dados_abertos') & c.cat.notna()].copy()
    d = sem_singletons(d, ['unidade', 'mes', 'cat'])
    gu, gm, gc = codigos(d.unidade), codigos(d.mes), codigos(d.cat)
    nu, nm, nc = [np.bincount(g).astype(float) for g in (gu, gm, gc)]
    cl = codigos(d.cnpj)
    G = cl.max() + 1
    out = []
    for y in ['af', 'fa']:
        Y = d[y].to_numpy(float)
        a, m, g = np.zeros(len(nu)), np.zeros(len(nm)), np.zeros(len(nc))
        mu = Y.mean()
        for it in range(2000):
            a_n = np.bincount(gu, Y - mu - m[gm] - g[gc]) / nu
            m_n = np.bincount(gm, Y - mu - a_n[gu] - g[gc]) / nm
            g_n = np.bincount(gc, Y - mu - a_n[gu] - m_n[gm]) / nc
            dif = max(np.abs(a_n - a).max(), np.abs(m_n - m).max(), np.abs(g_n - g).max())
            a, m, g = a_n, m_n, g_n
            if dif < 1e-9:
                break
        e = Y - mu - a[gu] - m[gm] - g[gc]
        gbar = (nc * g).sum() / nc.sum()
        # erro-padrão agrupado por CNPJ da média dos resíduos na categoria
        chave = gc.astype(np.int64) * G + cl
        s = pd.Series(e).groupby(chave).sum()
        var = (s ** 2).groupby(s.index // G).sum().reindex(range(len(nc)), fill_value=0).to_numpy() * G / (G - 1)
        se = np.sqrt(var) / nc
        tab = pd.DataFrame({'cat': pd.unique(d.cat), 'n_compras': nc})
        tab['efeito_pp'] = 100 * (g - gbar)
        tab['ep_pp'] = 100 * se
        tab['pct_observado'] = 100 * pd.Series(Y).groupby(gc).mean().to_numpy()
        tab['unidades'] = d.groupby(gc).unidade.nunique().to_numpy()
        tab['modo'] = MODOS[y]
        tab['convergiu_iter'] = it
        ele = (tab.n_compras >= 300) & (tab.unidades >= 30)
        tab['elegivel'] = ele
        tab['t'] = tab.efeito_pp / tab.ep_pp
        tab['p'] = 2 * stats.t.sf(tab.t.abs(), G - 1)
        tab['p_holm'] = np.nan
        tab.loc[ele, 'p_holm'] = holm(tab.loc[ele, 'p'])
        tab['tipo'] = np.where(tab.cat.str[0] == 'M', 'Material (classe CATMAT)', 'Serviço (grupo CATSER)')
        tab['descricoes'] = tab.cat.map(rot)
        out.append(tab)
        log('categorias', y, 'elegiveis', int(ele.sum()), 'holm<0.05', int((tab.p_holm < .05).sum()), 'iter', it)
    pd.concat(out, ignore_index=True).sort_values(['modo', 'efeito_pp'], ascending=[True, False]).to_csv(
        AQUI / 'associacao_categorias.csv', index=False, encoding='utf-8')


def concentracao(c):
    g = c.groupby('unidade').agg(fonte=('fonte', 'first'), nome=('nome_un', 'first'), orgao=('orgao_nome', 'first'), uf=('uf', 'first'),
                                 plataforma=('plataforma', lambda s: s.mode().iloc[0]), compras=('af', 'size'),
                                 af=('af', 'sum'), fa=('fa', 'sum')).reset_index()
    g['pct_af'] = 100 * g.af / g.compras
    g['pct_fa'] = 100 * g.fa / g.compras
    linhas = []
    for fnome, f in [('Compras.gov.br', g.fonte == 'dados_abertos'), ('Outras plataformas', g.fonte == 'pncp'), ('Todas', np.ones(len(g), bool))]:
        h = g[f & (g.compras >= 20)]
        for y, col in [('Aberto-Fechado', 'pct_af'), ('Fechado-Aberto', 'pct_fa')]:
            v = h[col]
            tot = g[f][col[4:]].sum()
            srt = g[f][col[4:]].sort_values(ascending=False)
            linhas.append({'fonte': fnome, 'modo': y, 'unidades_20mais': len(h),
                           'pct_unid_nunca': 100 * (v == 0).mean(), 'pct_unid_menos5': 100 * (v < 5).mean(),
                           'pct_unid_5a95': 100 * ((v >= 5) & (v <= 95)).mean(), 'pct_unid_mais95': 100 * (v > 95).mean(),
                           'mediana_pct': v.median(), 'compras_modo': int(tot),
                           'pct_compras_top10_unid': 100 * srt.iloc[:10].sum() / tot if tot else np.nan,
                           'pct_compras_top50_unid': 100 * srt.iloc[:50].sum() / tot if tot else np.nan,
                           'pct_compras_top1pct_unid': 100 * srt.iloc[:max(1, len(srt) // 100)].sum() / tot if tot else np.nan})
    pd.DataFrame(linhas).to_csv(AQUI / 'concentracao_unidades.csv', index=False, encoding='utf-8')
    # histogramas da parcela por unidade
    hl = []
    for fonte in ['dados_abertos', 'pncp']:
        h = g[(g.fonte == fonte) & (g.compras >= 20)]
        for col in ['pct_af', 'pct_fa']:
            b = pd.cut(h[col], [-0.1, 0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 99.999, 100], labels=['0', '0-10', '10-20', '20-30', '30-40', '40-50', '50-60', '60-70', '70-80', '80-90', '90-<100', '100'])
            hl.append(b.value_counts(sort=False).rename('unidades').reset_index().rename(columns={col: 'faixa'}).assign(fonte=fonte, modo=col))
    pd.concat(hl).to_csv(AQUI / 'distribuicao_unidades.csv', index=False, encoding='utf-8')
    top = pd.concat([g.sort_values('af', ascending=False).head(30).assign(lista='mais compras AF'),
                     g.sort_values('fa', ascending=False).head(30).assign(lista='mais compras FA')])
    top.to_csv(AQUI / 'unidades_top.csv', index=False, encoding='utf-8')


def main():
    t0 = time.time()
    c, plats = preparar()
    log('compras', len(c), 'unidades', c.unidade.nunique(), 'af', int(c.af.sum()), 'fa', int(c.fa.sum()))
    partes = sys.argv[1:] or ['desc', 'tend', 'perfil', 'r2', 'cat', 'conc']
    if 'desc' in partes: descritivas(c)
    if 'tend' in partes: tendencia(c)
    if 'perfil' in partes: perfil(c, plats)
    if 'cat' in partes: efeitos_categoria(c)
    if 'conc' in partes: concentracao(c)
    if 'r2' in partes: decomposicao_r2(c)
    log(f'fim em {time.time() - t0:.0f}s')
    (AQUI / 'log_execucao.txt').open('a', encoding='utf-8').write('\n'.join(LOG) + '\n')


if __name__ == '__main__':
    main()
