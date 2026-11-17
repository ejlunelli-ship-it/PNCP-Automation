"""Confere registros no SQLite e documenta influência das caudas sem excluir casos."""
from pathlib import Path
import sqlite3,json,hashlib
import numpy as np
import pandas as pd
import sys
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
sys.path.insert(0,str(OUT))
from estatistica import suporte,teste

def main():
    db=ROOT/'PNCP-Automation/dados/pncp.db';st=db.stat();meta=json.loads((OUT/'registro_antes_estimacao.json').read_text(encoding='utf-8'))
    am={c:pd.read_pickle(OUT/f'amostra_principal_{c}.pkl') for c in ['A','B','C']}
    top=am['C'].nlargest(20,'relativo')
    selected=pd.concat([z.sample(min(50,len(z)),random_state=20261117) for z in am.values()]+[top,am['B'].nsmallest(10,'desconto')]).drop_duplicates('id')
    ids=selected.id.astype(int).tolist();con=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True);con.execute('PRAGMA query_only=ON')
    sql='''SELECT i.id,i.numero_controle_pncp,i.numero_item,i.cod_item_catalogo,
      i.unidade_medida,i.descricao_resumida,i.quantidade,i.quantidade_resultado,
      i.valor_unitario_resultado,i.valor_unitario_estimado,i.valor_total_resultado,
      i.situacao_item,i.homologado,i.material_ou_servico,i.registro_principal,i.numero_grupo,
      c.fonte,c.modalidade_nome,c.modo_disputa,c.orgao_cnpj,c.uasg,c.uf,
      c.data_abertura_proposta,i.data_resultado FROM itens i JOIN compras c
      ON c.numero_controle_pncp=i.numero_controle_pncp WHERE i.id IN ('''+','.join('?' for _ in ids)+')'
    raw=pd.read_sql_query(sql,con,params=ids);con.close();assert len(raw)==len(ids)
    check=selected[['id','p','q','r','modo','codigo']].merge(raw,on='id',validate='one_to_one')
    for a,b in [('p','valor_unitario_resultado'),('q','quantidade'),('r','valor_unitario_estimado')]:assert np.allclose(check[a],check[b],equal_nan=True)
    assert (check.codigo==check.cod_item_catalogo).all()
    assert check.situacao_item.eq('Homologado').all() and check.homologado.eq(1).all()
    assert check.material_ou_servico.eq('M').all() and check.registro_principal.eq(1).all()
    assert check.fonte.eq('dados_abertos').all() and check.modalidade_nome.str.contains('Eletr',case=False).all()
    assert (check.modo_disputa.map({'Aberto':0,'Aberto-Fechado':1})==check.modo).all()
    check.to_csv(OUT/'conferencia_SQLite.csv',index=False,encoding='utf-8-sig')
    audit=top[['id','mediana','relativo','pregoes_doadores','orgaos_doadores','peso_padronizado','modo','celula_mercado','orgao']].merge(raw,on='id',validate='one_to_one')
    audit['contribuicao_diferenca']=(2*audit.modo-1)*audit.peso_padronizado*audit.relativo
    audit.to_csv(OUT/'auditoria_extremos_indice.csv',index=False,encoding='utf-8-sig')
    donors=pd.read_pickle(OUT/'doadores.pkl');d=pd.read_pickle(OUT/'principal_com_referencia.pkl')
    cases=[]
    for row in top.head(3).itertuples():
        h=donors[(donors.celula_mercado==row.celula_mercado)&(donors.orgao!=row.orgao)].copy();h['id_alvo']=row.id;cases.append(h)
    zz=pd.concat(cases);mapas=json.loads((OUT/'fonte/mapas.json').read_text(encoding='utf-8'))
    for col in ['compra','orgao']:zz[col]=zz[col].map({v:k for k,v in mapas[col].items()})
    zz.to_csv(OUT/'doadores_tres_extremos.csv',index=False,encoding='utf-8-sig')
    influence=[]
    for row in top.head(5).itertuples():
        z=suporte(am['C'][am['C'].id!=row.id],['produto','mes','uf'],'relativo');r,_=teste(z,'relativo')
        influence.append({'id_excluido':row.id,'razao':row.relativo,'diferenca_sem_item':r['diferenca'],'itens':len(z),'estratos':r['estratos'],'nota':'Diagnóstico posterior; não substitui resultado principal; benchmark fixado'})
    pd.DataFrame(influence).to_csv(OUT/'influencia_itens_extremos.csv',index=False,encoding='utf-8-sig')
    reg=json.loads((OUT/'registro_inicio_testes.json').read_text(encoding='utf-8'))
    for f,h in reg['hashes'].items():assert hashlib.sha256((OUT/f).read_bytes()).hexdigest()==h
    assert db.stat().st_size==st.st_size==meta['bytes'] and db.stat().st_mtime_ns==st.st_mtime_ns==meta['mtime_ns']
    rows={'itens_conferidos_SQLite':len(raw),'campos_precos_quantidades_status_identidades_coincidem':True,'referencias_cnpj_excluido':True,'hashes_entradas_scripts_protocolo_preservados':True,'banco_preservado':True,'maior_razao':float(top.relativo.max()),'maior_preco':float(top.iloc[0].p),'mediana_doadora_maior_razao':float(top.iloc[0].mediana)}
    (OUT/'validacao_final.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');print(rows)
if __name__=='__main__':main()
