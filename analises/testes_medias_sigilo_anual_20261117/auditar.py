"""Audita classificação de sigilo, preços, estimados e observações influentes."""
from pathlib import Path
import sys,json,sqlite3,hashlib
import numpy as np
import pandas as pd
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];ANT=OUT.parent/'testes_medias_20261117'
sys.path.insert(0,str(OUT))
from estatistica import suporte,teste
def main():
    selected=[];tops=[];influence=[];diag=[];donor_cases=[]
    donors=pd.read_pickle(OUT/'doadores_anuais.pkl')
    for sig in [0,1]:
        for code,y in [('A','logp'),('B','desconto'),('C','relativo')]:
            path=OUT/f'amostra_principal_s{sig}_{code}.pkl'
            if not path.exists():continue
            d=pd.read_pickle(path);assert d.sigilo.eq(sig).all()
            assert d.groupby('estrato')[['produto','ano','uf']].nunique().eq(1).all().all()
            selected.append(d.sample(min(50,len(d)),random_state=20261117))
            if code=='B':
                assert np.isfinite(d.r).all() and d.r.gt(0).all();assert np.allclose(d.desconto,1-d.p/d.r)
                selected.extend([d.nsmallest(8,'desconto'),d.nlargest(8,'desconto')])
                for mode,h in d.groupby('modo'):
                    diag.append({'sigilo':sig,'modo':mode,'itens':len(h),'fracao_estimado_igual_homologado':float(np.isclose(h.r,h.p,rtol=0,atol=1e-8).mean()),'fracao_desconto_negativo':float(h.desconto.lt(0).mean()),'desconto_min':float(h.desconto.min()),'desconto_max':float(h.desconto.max())})
            if code=='C':
                top=d.nlargest(12,'relativo');selected.append(top);tops.append(top)
                for row in top.head(3).itertuples():
                    z=suporte(d[d.id!=row.id],['produto','ano','uf'],'relativo');r,_=teste(z,'relativo')
                    influence.append({'sigilo':sig,'id_excluido':row.id,'indice':row.relativo,'diferenca_sem_item':r['diferenca'],'itens':len(z),'estratos':r['estratos'],'nota':'Diagnóstico de influência posterior; benchmark fixado; não substitui principal'})
                for row in top.head(2).itertuples():
                    h=donors[(donors.celula_mercado==row.celula_mercado)&(donors.orgao!=row.orgao)].copy();h['id_alvo']=row.id;h['sigilo_alvo']=sig;donor_cases.append(h)
    selected=pd.concat(selected).drop_duplicates('id');ids=selected.id.astype(int).tolist()
    db=ROOT/'PNCP-Automation/dados/pncp.db';con=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True);con.execute('PRAGMA query_only=ON')
    query='''SELECT i.id,i.numero_controle_pncp,i.numero_item,i.cod_item_catalogo,i.unidade_medida,
      i.descricao_resumida,i.orcamento_sigiloso,i.quantidade,i.quantidade_resultado,
      i.valor_unitario_resultado,i.valor_unitario_estimado,i.valor_total_resultado,
      i.situacao_item,i.homologado,i.material_ou_servico,i.registro_principal,i.numero_grupo,
      c.fonte,c.modalidade_nome,c.modo_disputa,c.orgao_cnpj,c.uasg,c.uf,c.data_abertura_proposta,
      i.data_resultado FROM itens i JOIN compras c ON c.numero_controle_pncp=i.numero_controle_pncp
      WHERE i.id IN ('''+','.join('?' for _ in ids)+')'
    raw=pd.read_sql_query(query,con,params=ids);con.close()
    check=selected[['id','p','q','r','modo','sigilo','codigo']].merge(raw,on='id',validate='one_to_one');assert len(check)==len(selected)
    for a,b in [('p','valor_unitario_resultado'),('r','valor_unitario_estimado'),('q','quantidade'),('sigilo','orcamento_sigiloso')]:assert np.allclose(check[a],check[b],equal_nan=True)
    assert (check.codigo==check.cod_item_catalogo).all()
    assert (check.modo_disputa.map({'Aberto':0,'Aberto-Fechado':1})==check.modo).all()
    assert check.homologado.eq(1).all() and check.situacao_item.eq('Homologado').all() and check.material_ou_servico.eq('M').all()
    assert check.registro_principal.eq(1).all() and check.fonte.eq('dados_abertos').all() and check.modalidade_nome.str.contains('Eletr',case=False).all()
    check.to_csv(OUT/'conferencia_SQLite.csv',index=False,encoding='utf-8-sig')
    top=pd.concat(tops)[['id','sigilo','modo','mediana','relativo','peso_padronizado','pregoes_doadores','orgaos_doadores']].merge(raw,on='id',validate='one_to_one')
    top['contribuicao_diferenca']=(2*top.modo-1)*top.peso_padronizado*top.relativo
    top.to_csv(OUT/'auditoria_extremos_indice.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame(influence).to_csv(OUT/'influencia_extremos.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame(diag).to_csv(OUT/'diagnostico_estimados.csv',index=False,encoding='utf-8-sig')
    z=pd.concat(donor_cases);mapas=json.loads((ANT/'fonte/mapas.json').read_text(encoding='utf-8'))
    for col in ['compra','orgao']:z[col]=z[col].map({v:k for k,v in mapas[col].items()})
    z.to_csv(OUT/'doadores_extremos.csv',index=False,encoding='utf-8-sig')
    record=json.loads((OUT/'registro_inicio.json').read_text(encoding='utf-8'))
    for f,h in record['hashes_scripts'].items():assert hashlib.sha256((OUT/f).read_bytes()).hexdigest()==h
    assert db.stat().st_size==record['bytes'] and db.stat().st_mtime_ns==record['mtime_ns']
    result={'itens_SQLite':len(check),'sigilo_0':int(check.sigilo.eq(0).sum()),'sigilo_1':int(check.sigilo.eq(1).sum()),'sigilo_precos_estimados_status_identidades_coincidem':True,'ano_estratos_verificado':True,'banco_preservado':True,'hashes_scripts_preservados':True}
    (OUT/'validacao_final.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(result)
if __name__=='__main__':main()
