"""Testes anuais separados por sigilo; população preservada e referências recalculadas."""
from pathlib import Path
import json,hashlib,time,sys,gc,statistics
import numpy as np
import pandas as pd
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];ANT=OUT.parent/'testes_medias_20261117'
sys.path.insert(0,str(OUT))
from estatistica import codigos,suporte,teste,referencias,medianas_bootstrap,bootstrap,resumo_boot,holm
T0=time.time();RES={};SAMPLES=[]
def log(s):print(f'[{time.time()-T0:.1f}s] {s}',flush=True)
def salvar(nome,obj):
    (OUT/nome).write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=lambda x:x.item() if isinstance(x,np.generic) else str(x)),encoding='utf-8')
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def main():
    db=ROOT/'PNCP-Automation/dados/pncp.db';st=db.stat();old=json.loads((ANT/'registro_antes_estimacao.json').read_text(encoding='utf-8'))
    assert st.st_size==old['bytes'] and st.st_mtime_ns==old['mtime_ns'],'Banco alterado: reextrair antes de prosseguir'
    hashes=json.loads((ANT/'registro_inicio_testes.json').read_text(encoding='utf-8'))['hashes']
    for f in ['base_ampliada.pkl','base_principal.pkl']:assert sha(ANT/f)==hashes[f]
    salvar('registro_inicio.json',{'data':time.strftime('%Y-%m-%dT%H:%M:%S'),'banco':str(db),'bytes':st.st_size,'mtime_ns':st.st_mtime_ns,'origem_extracao':str(ANT),'hashes_bases':{f:hashes[f] for f in ['base_ampliada.pkl','base_principal.pkl']},'hashes_scripts':{f:sha(OUT/f) for f in ['protocolo.md','estatistica.py','executar.py']},'replicacoes':1999,'seed':20261117})
    d=pd.read_pickle(ANT/'base_ampliada.pkl');d['R_valido']=np.isfinite(d.r)&d.r.gt(0)
    cov=[]
    for label,z in [('ampliado',d),('prioritario',d[d.classe.isin([6505,7510,7530,7930,8540])])]:
        c=z.groupby(['sigilo','modo']).agg(itens=('id','size'),pregoes=('compra','nunique'),orgaos=('orgao','nunique'),estimado_valido=('R_valido','sum')).reset_index();c['populacao']=label;c['cobertura_estimado']=c.estimado_valido/c.itens;cov.append(c)
    pd.concat(cov).to_csv(OUT/'cobertura_estimado.csv',index=False,encoding='utf-8-sig')
    unknown=int((~d.sigilo.isin([0,1])).sum());d=d[d.sigilo.isin([0,1])].copy()
    # Mudança importante: estimados válidos também entram quando o orçamento é sigiloso.
    d['desconto']=np.where(d.R_valido,1-d.p/d.r,np.nan)
    d['celula_mercado']=codigos(d,['produto','ano','uf']);d['ref_id']=-1
    log(f'Base anual: {len(d):,} itens; sigilo desconhecido: {unknown}')
    d.groupby(['sigilo','modo','ano']).agg(itens=('id','size'),pregoes=('compra','nunique'),orgaos=('orgao','nunique')).to_csv(OUT/'composicao_ano.csv',encoding='utf-8-sig')
    mixed=d.groupby('compra').sigilo.nunique();salvar('classificacao.json',{'desconhecidos_excluidos':unknown,'pregoes_com_ambos_sigilos_no_recorte':int((mixed==2).sum()),'benchmark_doadores_ambos_sigilos':True,'ano_2026_parcial_ate':'2026-04-30'})
    refs,donors,blocos=referencias(d);refs.to_csv(OUT/'referencias_anuais.csv.gz',index=False,compression='gzip');donors.to_pickle(OUT/'doadores_anuais.pkl')
    d.drop(columns='ref_id',inplace=True);d=d.merge(refs,on=['celula_mercado','orgao'],how='left',validate='many_to_one');d['ref_id']=d.ref_id.fillna(-1).astype(int);d['relativo']=d.p/d.mediana
    d.to_pickle(OUT/'base_anual_com_referencia.pkl')
    pri=d[d.classe.isin([6505,7510,7530,7930,8540])].copy()
    checks=refs.sample(min(60,len(refs)),random_state=20261117)
    for r in checks.itertuples():
        h=donors[(donors.celula_mercado==r.celula_mercado)&(donors.orgao!=r.orgao)]
        assert len(h)==r.pregoes_doadores and h.orgao.nunique()==r.orgaos_doadores and abs(statistics.median(h.p)-r.mediana)<1e-10
    salvar('validacao_referencias.json',{'referencias_reproduzidas':len(checks),'exclusao_CNPJ_alvo':True,'periodo':'ano','doadores_ambos_sigilos':True})
    log(f'{len(refs):,} referências anuais; {len(blocos):,} mercados')
    for family in ['principal','condicoes_compra','ampliado','amostra_comum','winsor']:
        for sig in [0,1]:
            base=(d if family=='ampliado' else pri);base=base[base.sigilo.eq(sig)].copy()
            if family=='amostra_comum':base=base[np.isfinite(base.desconto)&np.isfinite(base.relativo)].copy()
            cols=['produto','ano','uf']+(['srp','beneficio','faixa_q'] if family=='condicoes_compra' else [])
            for code,y0 in [('A','logp'),('B','desconto'),('C','relativo')]:
                nome=f'{family}_s{sig}_{code}';y=y0;tmp=base
                if family=='winsor':
                    tmp=base[np.isfinite(base[y0])].copy();g=tmp.groupby('produto')[y0]
                    lo=g.transform(lambda v:v.quantile(.01));hi=g.transform(lambda v:v.quantile(.99));tmp['y_win']=tmp[y0].clip(lo,hi);y='y_win'
                x=suporte(tmp,cols,y)
                SAMPLES.append({'analise':nome,'familia':family,'sigilo':sig,'desfecho':code,'elegiveis':int(np.isfinite(tmp[y]).sum()),'itens':len(x),'A':int(x.modo.eq(0).sum()),'AF':int(x.modo.eq(1).sum()),'pregoes':x.compra.nunique(),'orgaos':x.orgao.nunique(),'estratos':x.estrato.nunique() if len(x) else 0})
                r={'estimavel':False,'analise':nome,'familia':family,'sigilo':sig,'codigo':code,'desfecho':y}
                if len(x):
                    est,x=teste(x,y);r.update(est);x.to_pickle(OUT/f'amostra_{nome}.pkl')
                    log(f'{nome}: N={len(x):,}; G={r["orgaos"]}; S={r["estratos"]}; delta={r["diferenca"]:.6g}; p={r["infer_duplo"]["p"]}')
                else:log(f'{nome}: sem suporte')
                RES[nome]=r;salvar('resultados.json',RES);del x
            del base
    pd.DataFrame(SAMPLES).to_csv(OUT/'amostras.csv',index=False,encoding='utf-8-sig')
    orgs=np.sort(d.orgao.unique());orgindex={int(o):i for i,o in enumerate(orgs)}
    counts=np.random.default_rng(20261117).multinomial(len(orgs),np.ones(len(orgs))/len(orgs),size=1999).astype('int16')
    np.save(OUT/'multiplicidades_orgao.npy',counts);salvar('orgaos_bootstrap.json',orgs.tolist())
    del d,pri,donors,tmp;gc.collect()
    refboot=medianas_bootstrap(blocos,counts,orgindex,len(refs),callback=log,destino=OUT/'referencias_bootstrap.npy')
    for nome,r in RES.items():
        if not r['estimavel']:continue
        x=pd.read_pickle(OUT/f'amostra_{nome}.pkl');rb=refboot if r['codigo']=='C' and r['familia']!='winsor' else None
        rep,fra=bootstrap(x,r['desfecho'],counts,orgindex,refboot=rb);r['bootstrap']=resumo_boot(r['diferenca'],rep,fra);r['bootstrap_recalcula_referencia']=rb is not None
        np.savez_compressed(OUT/f'bootstrap_{nome}.npz',estimativas=rep,fracao_estratos=fra)
        log(f'Bootstrap {nome}: p={r["bootstrap"].get("p")}; suporte={r["bootstrap"].get("fracao_media_estratos_retidos")}');salvar('resultados.json',RES);del x
    for family in ['principal','condicoes_compra','ampliado','amostra_comum','winsor']:
        names=[f'{family}_s{s}_{c}' for s in [0,1] for c in ['A','B','C']]
        for field,dest in [('infer_duplo','p_holm6'),('bootstrap','p_bootstrap_holm6')]:
            ps=holm([RES[n].get(field,{}).get('p') for n in names])
            for n,p in zip(names,ps):RES[n][dest]=p
            for sig in [0,1]:
                ns=[f'{family}_s{sig}_{c}' for c in ['A','B','C']];ps=holm([RES[n].get(field,{}).get('p') for n in ns])
                for n,p in zip(ns,ps):RES[n][dest.replace('6','3')]=p
    salvar('resultados.json',RES)
    mapas=json.loads((ANT/'fonte/mapas.json').read_text(encoding='utf-8'))
    for sig in [0,1]:
        for code in ['A','B','C']:
            nome=f'principal_s{sig}_{code}'
            if not RES[nome]['estimavel']:continue
            z=pd.read_pickle(OUT/f'amostra_{nome}.pkl')
            for col in ['compra','orgao','uasg','unidade','descricao','uf','beneficio']:z[col]=z[col].map({v:k for k,v in mapas[col].items()})
            for col in ['abertura','resultado']:z[col]=pd.to_datetime(z[col],unit='D').dt.strftime('%Y-%m-%d')
            z.to_csv(OUT/f'amostra_{nome}.csv.gz',index=False,compression='gzip')
    assert db.stat().st_size==st.st_size and db.stat().st_mtime_ns==st.st_mtime_ns
    salvar('fim_execucao.json',{'data':time.strftime('%Y-%m-%dT%H:%M:%S'),'segundos':time.time()-T0,'analises':len(RES),'referencias':len(refs),'banco_preservado':True});log('Execução concluída')
if __name__=='__main__':main()
