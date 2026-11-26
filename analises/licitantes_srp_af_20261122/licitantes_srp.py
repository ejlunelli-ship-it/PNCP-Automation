"""Número de licitantes no Aberto-Fechado: SRP × não SRP (protocolo.md).

Lê os bancos de extração dos PDFs (dados/extracao/) e dados/pncp.db, ambos somente para leitura.
Usa o estimador de analises/controles_modos_20261122/controles_modos.py.

    python analises/licitantes_srp_af_20261122/licitantes_srp.py
"""
import importlib.util
import json
import os
import sqlite3
import time
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
DADOS = Path(os.environ.get('PNCP_DADOS', RAIZ / 'dados'))
EXTR = ['aberto-fechado_2024-11_a_2024-12.db', 'junho2025.db', 'aberto-fechado_2025-12_a_2026-07.db',
        'aberto-fechado_2026-03_04_08.db', 'aberto-fechado_2026-09_a_2026-10.db']
spec = importlib.util.spec_from_file_location('cm', AQUI.parent / 'controles_modos_20261122' / 'controles_modos.py')
cm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cm)

SQL = """
SELECT c.id_compra, c.numero_controle_pncp AS compra, c.orgao_cnpj AS cnpj, COALESCE(i.uasg_item, c.uasg) AS uasg,
       substr(c.data_publicacao, 1, 7) AS mes, c.srp, i.numero_item AS item, i.material_ou_servico AS ms,
       i.cod_item_catalogo AS cat, i.orcamento_sigiloso AS sig, i.tipo_beneficio AS benef,
       i.quantidade AS q, i.valor_unitario_estimado AS r
FROM itens i JOIN compras c ON c.numero_controle_pncp = i.numero_controle_pncp
WHERE c.fonte = 'dados_abertos' AND c.modo_disputa = 'Aberto-Fechado' AND i.registro_principal = 1
  AND c.id_compra IS NOT NULL
"""
LOG = []


def log(*a):
    s = ' '.join(map(str, a))
    LOG.append(s)
    print(s.encode('ascii', 'replace').decode(), flush=True)


def carregar():
    partes = []
    for f in EXTR:
        con = sqlite3.connect(f"file:{DADOS / 'extracao' / f}?mode=ro", uri=True)
        x = pd.read_sql_query("""SELECT pasta, item, quantidade_fornecedores AS lic, status_extracao AS st,
                                        versao_parser AS v, arquivo_origem AS arq FROM itens""", con)
        con.close()
        x['banco'] = f
        partes.append(x)
    e = pd.concat(partes, ignore_index=True)
    log('extracao: itens', len(e), 'por banco', e.banco.value_counts().to_dict())
    e['mes_pasta'] = e.arq.str.extract(r'aberto-fechado_(\d{4}-\d{2})')[0]
    e = e[(e.st == 'OK') & (e.lic >= 1)].copy()
    e['id_compra'] = e.pasta.str.split('_').str[-1]
    n0 = len(e)
    e = e.drop_duplicates(['id_compra', 'item'])
    log('OK com licitantes >= 1', n0, 'sem repetidos', len(e), 'meses', sorted(e.mes_pasta.dropna().unique()))

    con = sqlite3.connect(f"file:{DADOS / 'pncp.db'}?mode=ro", uri=True)
    p = pd.read_sql_query(SQL, con)
    con.close()
    dup = p.groupby('id_compra').compra.nunique()
    p = p[p.id_compra.isin(dup[dup == 1].index)]
    d = e.merge(p, on=['id_compra', 'item'], how='inner')
    log('ligados ao pncp.db', len(d), f'({100 * len(d) / len(e):.1f}%)', 'compras', d.compra.nunique(), 'id_compra repetidos fora', int((dup > 1).sum()))
    n = pd.read_pickle(DADOS / 'analise_uso_modos' / 'compras.pkl')[['compra', 'n_itens']]
    d = d.merge(n, on='compra', how='left')
    return d


def preparar(d):
    d = d[d.sig.notna() & d.srp.notna()].copy()
    d['srp'] = d.srp.astype(float)
    d['licitantes'] = d.lic.astype(float)
    d['ln_lic'] = 100 * np.log(d.licitantes)
    d['sigiloso'] = d.sig.astype(float)
    d['servico'] = (d.ms == 'S').astype(float)
    b = d.benef.astype(str)
    d['exclusiva'] = b.str.startswith('Participa').astype(float)
    d['cota'] = b.str.startswith('Cota').astype(float)
    v = d.q.astype(float) * d.r.astype(float)
    d['sem_valor'] = (~(v > 0)).astype(float)
    d['log_valor'] = np.where(v > 0, np.log(v.where(v > 0, 1)), 0.0)
    d['log_n'] = np.log(d.n_itens.fillna(1).clip(lower=1).astype(float))
    d['ano'] = d.mes.str[:4]
    cod = lambda *cols: pd.MultiIndex.from_arrays([d[k].astype(str) for k in cols]).factorize()[0]
    d['mes_ms'] = cod('mes', 'ms')
    d['cel'] = np.where(d.cat.isna(), -1, cod('uasg', 'cat', 'ano'))
    cc = pd.factorize(d.compra)[0]
    ct = pd.factorize(d.cat)[0]
    d['cl_cat'] = np.where(ct < 0, ct.max() + 1 + cc, ct)
    for k in ['cnpj', 'uasg', 'mes']:
        d[k] = pd.factorize(d[k])[0]
    return d


def main():
    t0 = time.time()
    d = preparar(carregar())
    log('amostra', len(d), 'itens', d.compra.nunique(), 'compras', d.cnpj.nunique(), 'CNPJs', d.uasg.nunique(), 'UASGs')
    # descritivas
    g = d.groupby('srp')
    desc = pd.DataFrame({'itens': g.size(), 'compras': g.compra.nunique(), 'cnpjs': g.cnpj.nunique(),
                         'media': g.licitantes.mean(), 'dp': g.licitantes.std(), 'mediana': g.licitantes.median(),
                         'p25': g.licitantes.quantile(.25), 'p75': g.licitantes.quantile(.75),
                         'pct_1_licitante': g.licitantes.apply(lambda s: 100 * (s == 1).mean()),
                         'pct_servico': 100 * g.servico.mean(), 'pct_sigiloso': 100 * g.sigiloso.mean()}).reset_index()
    desc.round(3).to_csv(AQUI / 'descritivas.csv', index=False, encoding='utf-8')
    log(desc.round(2).to_string())
    pm = d.groupby(['ano', 'srp']).licitantes.agg(['size', 'mean', 'median']).reset_index()
    pm.round(3).to_csv(AQUI / 'descritivas_ano.csv', index=False, encoding='utf-8')

    cov = ['sigiloso', 'log_valor', 'sem_valor', 'log_n', 'exclusiva', 'cota']
    specs = {'S1': ([], []), 'S2': (cov, ['mes_ms']), 'S3': (cov, ['mes_ms', 'uasg']), 'S4': (cov, ['cel', 'mes_ms'])}
    linhas = []
    for y in ['licitantes', 'ln_lic']:
        for e, (xs, fes) in specs.items():
            base = d[d.cel >= 0] if e == 'S4' else d
            r = cm.estimar(base, y, ['srp'] + xs, fes, ['srp'])
            for x in r:
                linhas.append({'nivel': 'item', 'desfecho': y, 'espec': e, **x})
                log(y, e, round(x['coef'], 3), 'IC', round(x['ic95_inf'], 3), round(x['ic95_sup'], 3), 'p', round(x['p'], 4), 'n', x['n'])
    # por compra
    gc = d.groupby('compra')
    c = pd.DataFrame({'cnpj': gc.cnpj.first(), 'uasg': gc.uasg.first(), 'mes': gc.mes.first(), 'srp': gc.srp.first(),
                      'licitantes': gc.licitantes.mean(), 'ln_lic': gc.ln_lic.mean(), 'sigiloso': gc.sigiloso.mean(),
                      'servico': gc.servico.mean(), 'log_n': gc.log_n.first(), 'exclusiva': gc.exclusiva.mean(),
                      'cota': gc.cota.mean(), 'valor': gc.log_valor.mean()}).reset_index()
    c['cl'] = c.cnpj
    for y in ['licitantes', 'ln_lic']:
        r = cm.estimar(c, y, ['srp', 'sigiloso', 'servico', 'log_n', 'exclusiva', 'cota', 'valor'], ['mes', 'uasg'], ['srp'], clusters=('cnpj', 'cl'))
        for x in r:
            linhas.append({'nivel': 'compra', 'desfecho': y, 'espec': 'S3', **x})
            log('compra', y, round(x['coef'], 3), 'p', round(x['p'], 4), 'n', x['n'])
    res = pd.DataFrame(linhas)
    principal = (res.nivel == 'item') & (res.espec == 'S3')
    res['p_holm'] = np.nan
    res.loc[principal, 'p_holm'] = cm.holm_ps(res.loc[principal, 'p'])
    res.to_csv(AQUI / 'resultados.csv', index=False, encoding='utf-8')
    log(res[['nivel', 'desfecho', 'espec', 'coef', 'ic95_inf', 'ic95_sup', 'p', 'p_holm', 'n', 'g_cnpj', 'g_cat', 'media_y']].round(4).to_string())
    log(f'fim em {time.time() - t0:.0f}s')
    (AQUI / 'log_execucao.txt').write_text('\n'.join(LOG) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
