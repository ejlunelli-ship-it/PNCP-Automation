"""Extrai homologados de materiais para painel; SQLite estritamente em leitura."""
from pathlib import Path
import sqlite3,json,time,hashlib
import pandas as pd
import numpy as np

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
DB=ROOT/'dados/pncp.db'
MAPAS={}
T0=time.time()
def log(s):print(f'[{time.time()-T0:.1f}s] {s}',flush=True)
def texto(s):return s.fillna('').astype(str).str.strip()
def ident(s,n):
    s=texto(s).str.replace(r'\.0$','',regex=True)
    return s.where(s.str.fullmatch(r'\d+'),'').map(lambda x:x.zfill(n) if x else '')
def cod(s,nome):
    mapa=MAPAS.setdefault(nome,{})
    for v in s.unique():
        if v not in mapa:mapa[v]=len(mapa)
    return s.map(mapa).astype('int32')
def dia(s):
    dt=pd.to_datetime(s,format='mixed',errors='coerce',utc=True)
    return ((dt.dt.floor('D')-pd.Timestamp('1970-01-01',tz='UTC'))/pd.Timedelta(days=1)).fillna(-1).astype('int32')
def main():
    st=DB.stat();meta={'banco':str(DB),'bytes':st.st_size,'mtime_ns':st.st_mtime_ns,'execucao':time.strftime('%Y-%m-%dT%H:%M:%S')}
    con=sqlite3.connect(DB.as_uri()+'?mode=ro',uri=True);con.execute('PRAGMA query_only=ON');con.execute('BEGIN')
    q='''SELECT i.id,i.numero_controle_pncp compra,i.numero_item item,c.id_compra,
      c.modo_disputa modo,i.uasg_item uasg,c.uasg uasg_compra,c.orgao_cnpj orgao,c.uf,c.esfera,
      i.cod_item_catalogo codigo,i.codigo_pdm pdm,i.codigo_classe classe,
      i.unidade_medida unidade,i.descricao_resumida descricao,i.criterio_julgamento criterio,
      i.quantidade q,i.valor_unitario_estimado r,i.valor_unitario_resultado p,
      i.orcamento_sigiloso sigilo,c.srp,i.tipo_beneficio beneficio,i.numero_grupo grupo,
      c.data_abertura_proposta abertura,i.data_resultado resultado,i.data_atualizacao atualizado
      FROM compras c CROSS JOIN itens i ON i.numero_controle_pncp=c.numero_controle_pncp
      WHERE c.fonte='dados_abertos' AND c.modalidade_nome LIKE 'Preg%Eletr%'
      AND c.modo_disputa IN ('Aberto','Aberto-Fechado','Fechado-Aberto')
      AND i.registro_principal=1 AND i.material_ou_servico='M'
      AND i.homologado=1 AND i.situacao_item='Homologado' '''
    (OUT/'consulta.sql').write_text(q,encoding='utf-8')
    partes=[];counts={}
    for d in pd.read_sql_query(q,con,chunksize=150000):
        for (m,k),n in d.groupby(['modo','criterio'],dropna=False).size().items():
            tag=f'{m}|{k}';counts[tag]=counts.get(tag,0)+int(n)
        d=d[d.criterio.eq('Menor preço')].copy();d.drop(columns='criterio',inplace=True)
        d['modo']=d.modo.map({'Aberto':0,'Aberto-Fechado':1,'Fechado-Aberto':2}).astype('int8')
        d['orgao']=cod(ident(d.orgao,14),'orgao')
        for col in ['uasg','uasg_compra']:d[col]=cod(ident(d[col],6),'uasg')
        for col in ['compra','id_compra','uf','esfera','beneficio']:d[col]=cod(texto(d[col]),col)
        for col in ['unidade','descricao']:d[col]=cod(texto(d[col]).str.upper().str.replace(r'\s+',' ',regex=True),col)
        for col in ['abertura','resultado','atualizado']:d[col]=dia(d[col])
        for col in ['codigo','pdm','classe','sigilo','srp','grupo']:d[col]=pd.to_numeric(d[col],errors='coerce').fillna(-1).astype('int32')
        partes.append(d);log(f'Homologados Menor preço extraídos: {sum(len(x) for x in partes):,}')
    d=pd.concat(partes,ignore_index=True)
    assert not d.id.duplicated().any()
    meta['criterios_modos']=counts;meta['linhas']=len(d);meta['compras']=d.compra.nunique()
    meta['duplicatas_compra_item']=int(d.duplicated(['compra','item'],keep=False).sum())
    meta['codigo_positivo_por_modo']=d[d.codigo>0].modo.value_counts().to_dict()
    meta['pdm_classe_validos']=int((d.pdm.gt(0)&d.classe.gt(0)).sum())
    con.rollback();con.close()
    assert DB.stat().st_size==st.st_size and DB.stat().st_mtime_ns==st.st_mtime_ns
    d.to_pickle(OUT/'homologados.pkl')
    (OUT/'mapas.json').write_text(json.dumps(MAPAS,ensure_ascii=False),encoding='utf-8')
    (OUT/'extracao.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    resumo=d.groupby('classe').agg(itens=('id','size'),produtos=('codigo','nunique')).sort_values('itens',ascending=False)
    resumo.to_csv(OUT/'classes_extraidas.csv')
    log(f'Concluído: {len(d):,} itens; descrições {d.descricao.nunique():,}; produtos CATMAT {d.codigo.nunique():,}')
if __name__=='__main__':main()
