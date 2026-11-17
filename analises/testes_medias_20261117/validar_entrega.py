"""Confere amostras, resultados e representação numérica da planilha entregue."""
from pathlib import Path
import json,zipfile,xml.etree.ElementTree as ET,hashlib,math,sys
import numpy as np
import pandas as pd
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT))
from estatistica import holm
def main():
    r=json.loads((OUT/'resultados.json').read_text(encoding='utf-8'))
    df=pd.read_csv(OUT/'todas_estimativas.csv',sep=';');assert len(r)==len(df)==15
    for fam in ['principal','condicoes_compra','ampliado','amostra_comum','winsor']:
        ps=holm([r[fam+'_'+c]['infer_duplo']['p'] for c in ['A','B','C']])
        for c,p in zip(['A','B','C'],ps):assert abs(p-r[fam+'_'+c]['p_holm'])<1e-12
    for c,y in [('A','logp'),('B','desconto'),('C','relativo')]:
        z=pd.read_pickle(OUT/f'amostra_principal_{c}.pkl');rr=r['principal_'+c]
        assert len(z)==rr['itens'] and z.modo.isin([0,1]).all() and not z.id.duplicated().any()
        assert np.isfinite(z[y]).all() and z.p.gt(0).all()
        assert z.groupby('estrato').modo.nunique().eq(2).all()
        assert z.groupby('estrato')[['produto','mes','uf']].nunique().eq(1).all().all()
        for mode,key in [(0,'media_A'),(1,'media_AF')]:
            h=z[z.modo==mode];assert abs(h.peso_padronizado.sum()-1)<1e-12
            assert abs(float(np.sum(h.peso_padronizado*h[y]))-rr[key])<1e-9
        if c=='B':assert z.r.gt(0).all() and z.sigilo.eq(0).all() and np.allclose(z.desconto,1-z.p/z.r)
        if c=='C':assert np.allclose(z.relativo,z.p/z.mediana) and z.pregoes_doadores.ge(5).all() and z.orgaos_doadores.ge(2).all()
        for col in ['media_A','media_AF','diferenca']:
            dest={'media_A':'Media A padronizada','media_AF':'Media AF padronizada','diferenca':'Diferenca AF-A'}[col];v=df[df.Analise=='principal_'+c].iloc[0][dest];scale=100 if c=='B' else 1
            assert abs(v-rr[col]*scale)<1e-9
    sets=[set(pd.read_pickle(OUT/f'amostra_amostra_comum_{c}.pkl').id) for c in ['A','B','C']]
    assert sets[0]==sets[1]==sets[2]
    ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(OUT/'resultados_completos.xlsx') as book:
        assert book.testzip() is None
        for name in book.namelist():ET.fromstring(book.read(name))
        root=ET.fromstring(book.read('xl/worksheets/sheet1.xml'));rows=root.findall('m:sheetData/m:row',ns)
        parsed=[]
        for row in rows:
            vals=[]
            for cell in row:
                value=cell.find('m:v',ns)
                vals.append(float(value.text) if value is not None and value.text else ''.join(cell.itertext()))
            parsed.append(vals)
        assert len(parsed)==4
        header=parsed[0]
        for row in parsed[1:]:
            name=row[header.index('Analise')];expected=df[df.Analise==name].iloc[0]
            for col in ['Itens A','Itens AF','Diferenca AF-A','IC95 inferior','IC95 superior','p duplo','p Holm trio']:
                assert math.isclose(row[header.index(col)],expected[col],rel_tol=1e-12,abs_tol=1e-12)
    record=json.loads((OUT/'registro_inicio_testes.json').read_text(encoding='utf-8'))
    for fn,digest in record['hashes'].items():assert hashlib.sha256((OUT/fn).read_bytes()).hexdigest()==digest
    result={'especificacoes':len(r),'principal_testes':3,'amostras_pesos_elegibilidade_verificados':True,'amostra_comum_mesmos_itens':True,'Holm_reproduzido':True,'JSON_CSV_XLSX_coincidem':True,'arquivos_entrada_preservados':True,'hashes_entrega':{fn:hashlib.sha256((OUT/fn).read_bytes()).hexdigest() for fn in ['relatorio_completo.md','resultados_completos.xlsx','resultados.json','todas_estimativas.csv','validacao_final.json']}}
    (OUT/'validacao_entrega.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(result)
if __name__=='__main__':main()
