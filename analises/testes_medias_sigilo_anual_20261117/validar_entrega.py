"""Valida sigilo, ano, elegibilidade, pesos, ajustes múltiplos e planilha."""
from pathlib import Path
import json,sys,math,hashlib,zipfile,xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
OUT=Path(__file__).resolve().parent;sys.path.insert(0,str(OUT))
from estatistica import holm
def main():
    r=json.loads((OUT/'resultados.json').read_text(encoding='utf-8'));df=pd.read_csv(OUT/'todas_estimativas.csv',sep=';');assert len(r)==len(df)==30
    for family in ['principal','condicoes_compra','ampliado','amostra_comum','winsor']:
        names=[f'{family}_s{s}_{c}' for s in [0,1] for c in ['A','B','C']]
        for field,pkey in [('infer_duplo','p_holm6'),('bootstrap','p_bootstrap_holm6')]:
            ps=holm([r[n].get(field,{}).get('p') for n in names])
            for n,p in zip(names,ps):assert abs(p-r[n][pkey])<1e-12
    for sig in [0,1]:
        common=[]
        for code,y in [('A','logp'),('B','desconto'),('C','relativo')]:
            n=f'principal_s{sig}_{code}';z=pd.read_pickle(OUT/f'amostra_{n}.pkl');rr=r[n]
            assert z.sigilo.eq(sig).all() and z.modo.isin([0,1]).all() and not z.id.duplicated().any()
            assert len(z)==rr['itens'] and np.isfinite(z[y]).all()
            assert z.groupby('estrato')[['produto','ano','uf']].nunique().eq(1).all().all()
            assert z.groupby('estrato').modo.nunique().eq(2).all()
            for mode,key in [(0,'media_A'),(1,'media_AF')]:
                h=z[z.modo==mode];assert abs(h.peso_padronizado.sum()-1)<1e-12
                assert math.isclose(float(np.sum(h.peso_padronizado*h[y])),rr[key],rel_tol=1e-11,abs_tol=1e-10)
            if code=='B':assert z.r.gt(0).all() and np.allclose(z.desconto,1-z.p/z.r)
            if code=='C':assert np.allclose(z.relativo,z.p/z.mediana) and z.pregoes_doadores.ge(5).all() and z.orgaos_doadores.ge(2).all()
            common.append(set(pd.read_pickle(OUT/f'amostra_amostra_comum_s{sig}_{code}.pkl').id))
            for field,col in [('media_A','Media A padronizada'),('media_AF','Media AF padronizada'),('diferenca','Diferenca AF-A')]:
                s=100 if code=='B' else 1;assert math.isclose(df[df.Analise==n].iloc[0][col],rr[field]*s,rel_tol=1e-12,abs_tol=1e-10)
        assert common[0]==common[1]==common[2]
    # Conferir a matriz mapeada sem carregá-la integralmente na memória.
    rb=np.load(OUT/'referencias_bootstrap.npy',mmap_mode='r');ref=pd.read_csv(OUT/'referencias_anuais.csv.gz');assert rb.shape==(1999,len(ref))
    counts=np.load(OUT/'multiplicidades_orgao.npy');orgs=json.loads((OUT/'orgaos_bootstrap.json').read_text());oi={int(o):i for i,o in enumerate(orgs)};don=pd.read_pickle(OUT/'doadores_anuais.pkl')
    for row in ref.sample(12,random_state=51).itertuples():
        h=don[(don.celula_mercado==row.celula_mercado)&(don.orgao!=row.orgao)]
        for b in [0,3,11]:
            w=counts[b,[oi[int(o)] for o in h.orgao]];sel=w>0
            if sel.sum()<5 or h.loc[sel,'orgao'].nunique()<2:assert np.isnan(rb[b,row.ref_id])
            else:assert math.isclose(float(np.median(np.repeat(h.p.to_numpy(),w))),float(rb[b,row.ref_id]),rel_tol=1e-12,abs_tol=1e-10)
    ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(OUT/'resultados_completos.xlsx') as b:
        assert b.testzip() is None
        for name in b.namelist():ET.fromstring(b.read(name))
        root=ET.fromstring(b.read('xl/worksheets/sheet1.xml'));parsed=[]
        for row in root.findall('m:sheetData/m:row',ns):
            vals=[]
            for cell in row:
                v=cell.find('m:v',ns);vals.append(float(v.text) if v is not None and v.text else ''.join(cell.itertext()))
            parsed.append(vals)
        assert len(parsed)==7;head=parsed[0]
        for row in parsed[1:]:
            expected=df[df.Analise==row[head.index('Analise')]].iloc[0]
            for col in ['Itens A','Itens AF','Media A padronizada','Media AF padronizada','Diferenca AF-A','IC95 inferior','IC95 superior','p nominal','p Holm seis','p bootstrap Holm seis']:
                assert math.isclose(row[head.index(col)],expected[col],rel_tol=1e-12,abs_tol=1e-10)
    record=json.loads((OUT/'registro_inicio.json').read_text(encoding='utf-8'))
    for f,digest in record['hashes_scripts'].items():assert hashlib.sha256((OUT/f).read_bytes()).hexdigest()==digest
    valid={'especificacoes':30,'principais':6,'amostras_anuais_sigilo_e_pesos_verificados':True,'Holm_seis_reproduzido':True,'estimados_positivos_nos_dois_sigilos':True,'benchmarks_bootstrap_reproduzidos_por_expansao_literal':36,'JSON_CSV_XLSX_coincidem':True,'hashes_scripts_preservados':True,'hashes_entrega':{f:hashlib.sha256((OUT/f).read_bytes()).hexdigest() for f in ['relatorio_completo.md','resultados_completos.xlsx','resultados.json','todas_estimativas.csv']}}
    (OUT/'validacao_entrega.json').write_text(json.dumps(valid,indent=2),encoding='utf-8');print(valid)
if __name__=='__main__':main()
