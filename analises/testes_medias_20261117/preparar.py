"""Nova leitura do SQLite e construção da população antes de testar desfechos."""
from pathlib import Path
import importlib.util, json, re, sqlite3, hashlib, time
import pandas as pd
import numpy as np

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
DB=ROOT/'PNCP-Automation/dados/pncp.db'
FONTE=OUT/'fonte'
FONTE.mkdir(exist_ok=True)
FLUXO=[]
def salvar(nome,obj):
    (OUT/nome).write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=lambda v:v.item() if isinstance(v,np.generic) else str(v)),encoding='utf-8')
def etapa(nome,d):
    row={'etapa':nome,'itens':len(d),'pregoes':d.compra.nunique(),'orgaos':d.orgao.nunique()}
    row.update({nome:int(d.modo.eq(k).sum()) for k,nome in [(0,'Aberto'),(1,'Aberto-Fechado'),(2,'Fechado-Aberto')]})
    FLUXO.append(row);print(row,flush=True)
    return d
def dia(s):return int((pd.Timestamp(s)-pd.Timestamp('1970-01-01')).days)
def main():
    st=DB.stat()
    salvar('registro_antes_estimacao.json',{'data':time.strftime('%Y-%m-%dT%H:%M:%S'),'protocolo_sha256':hashlib.sha256((OUT/'protocolo.md').read_bytes()).hexdigest(),'banco':str(DB),'bytes':st.st_size,'mtime_ns':st.st_mtime_ns})
    spec=importlib.util.spec_from_file_location('extrator_anterior',ROOT/'analise/painel_efeitos_fixos_20261116/extrair.py')
    ex=importlib.util.module_from_spec(spec);spec.loader.exec_module(ex)
    (OUT/'extrator_base_registrado.py').write_bytes(Path(spec.origin).read_bytes())
    ex.OUT=FONTE;ex.DB=DB;ex.main()
    mapas=json.loads((FONTE/'mapas.json').read_text(encoding='utf-8'))
    d=etapa('01_homologados_materiais',pd.read_pickle(FONTE/'homologados.pkl'))
    d=etapa('02_somente_A_AF',d[d.modo.isin([0,1])].copy())
    con=sqlite3.connect(DB.as_uri()+'?mode=ro',uri=True);con.execute('PRAGMA query_only=ON')
    ids=[r[0] for r in con.execute("SELECT id_compra FROM compras WHERE fonte='dados_abertos' AND id_compra IS NOT NULL AND id_compra<>'' GROUP BY id_compra HAVING COUNT(*)>1")];con.close()
    amb=[mapas['id_compra'][x] for x in ids if x in mapas['id_compra']]
    invalid_org=[v for k,v in mapas['orgao'].items() if not re.fullmatch(r'\d{14}',k)]
    invalid_uasg=[v for k,v in mapas['uasg'].items() if not re.fullmatch(r'\d{6}',k)]
    vazio=lambda c:mapas[c].get('',-9999)
    dupl=d.duplicated(['compra','item'],keep=False)
    d=etapa('03_identidades',d[~dupl&~d.orgao.isin(invalid_org)&~d.uasg.isin(invalid_uasg)&d.uasg.eq(d.uasg_compra)&d.id_compra.ne(vazio('id_compra'))&~d.id_compra.isin(amb)].copy())
    d=etapa('04_coorte_preco_quantidade',d[d.abertura.between(dia('2022-11-01'),dia('2026-04-30'))&d.resultado.ge(d.abertura)&d.resultado.le(dia('2026-11-10'))&np.isfinite(d.p)&d.p.gt(0)&np.isfinite(d.q)&d.q.gt(0)&d.srp.isin([0,1])&d.grupo.le(0)].copy())
    ident=d[d.codigo.gt(0)].groupby('codigo').agg(classes=('classe',lambda x:x[x>0].nunique()),pdms=('pdm',lambda x:x[x>0].nunique()))
    ruins=ident[(ident.classes>1)|(ident.pdms>1)].index
    unidades_zero=[v for k,v in mapas['unidade'].items() if re.search(r'(?<![\d.,])0(?:[,.]0+)?\s*(?:UN|ML|KG|G|L|SAC|COM|CAP)\b',k)]
    ufs=['AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO']
    uf_ok=[v for k,v in mapas['uf'].items() if k in ufs]
    d=etapa('05_produto_UF_validos',d[d.codigo.gt(0)&d.pdm.gt(0)&d.classe.gt(0)&~d.codigo.isin(ruins)&d.unidade.ne(vazio('unidade'))&~d.unidade.isin(unidades_zero)&d.descricao.ne(vazio('descricao'))&d.uf.isin(uf_ok)].copy())
    datas=pd.to_datetime(d.abertura,unit='D');d['mes']=(datas.dt.year*12+datas.dt.month-1).astype('int32');d['ano']=datas.dt.year.astype('int16')
    d['produto']=pd.factorize(pd.MultiIndex.from_frame(d[['codigo','unidade','pdm','descricao']]),sort=True)[0]
    prod=d.groupby('produto').agg(pregoes=('compra','nunique'),orgaos=('orgao','nunique'),meses=('mes','nunique'))
    ok=prod[(prod.pregoes>=5)&(prod.orgaos>=3)&(prod.meses>=3)].index
    d=etapa('06_produtos_recorrentes',d[d.produto.isin(ok)].copy())
    pares=d.groupby(['orgao','produto']).agg(pregoes=('compra','nunique'),meses=('mes','nunique'));bons=pares[(pares.pregoes>=2)&(pares.meses>=2)].index
    d=etapa('07_pares_recorrentes',d[pd.MultiIndex.from_frame(d[['orgao','produto']]).isin(bons)].copy())
    d['logp']=np.log(d.p);d['logq']=np.log(d.q);d['faixa_q']=np.floor(np.log2(d.q)).astype('int32')
    d['desconto']=np.where(np.isfinite(d.r)&d.r.gt(0)&d.sigilo.eq(0),1-d.p/d.r,np.nan)
    d['celula_mercado']=pd.factorize(pd.MultiIndex.from_frame(d[['produto','mes','uf']]),sort=True)[0]
    d.reset_index(drop=True).to_pickle(OUT/'base_ampliada.pkl')
    pri=etapa('08_classes_prioritarias',d[d.classe.isin([6505,7510,7530,7930,8540])].copy())
    pri.reset_index(drop=True).to_pickle(OUT/'base_principal.pkl')
    pd.DataFrame(FLUXO).to_csv(OUT/'fluxo.csv',index=False,encoding='utf-8-sig')
    salvar('preparacao.json',{'id_compra_ambiguos':len(amb),'catmats_inconsistentes':len(ruins),'ufs_validas':ufs,'banco_preservado':DB.stat().st_size==st.st_size and DB.stat().st_mtime_ns==st.st_mtime_ns})
    assert DB.stat().st_size==st.st_size and DB.stat().st_mtime_ns==st.st_mtime_ns
if __name__=='__main__':main()
