"""Executa todos os contrastes pré-especificados, registra amostras e incerteza."""
from pathlib import Path
import json, hashlib, time, sys
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parent))
from estatistica import suporte,teste,referencias,medianas_bootstrap,bootstrap,resumo_boot,holm

OUT=Path(__file__).resolve().parent
T0=time.time();RES={}
def log(s):print(f'[{time.time()-T0:.1f}s] {s}',flush=True)
def salvar(nome,obj):
    (OUT/nome).write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=lambda x:x.item() if isinstance(x,np.generic) else str(x)),encoding='utf-8')
def main():
    arquivos=['protocolo.md','emenda_antes_estimacao.md','preparar.py','estatistica.py','executar.py','base_principal.pkl','base_ampliada.pkl']
    salvar('registro_inicio_testes.json',{'data':time.strftime('%Y-%m-%dT%H:%M:%S'),'hashes':{f:hashlib.sha256((OUT/f).read_bytes()).hexdigest() for f in arquivos},'replicacoes':1999,'seed':20261117})
    d=pd.read_pickle(OUT/'base_ampliada.pkl');log(f'Base ampliada: {len(d):,} itens')
    refs,donors,blocos=referencias(d)
    refs.to_csv(OUT/'referencias.csv.gz',index=False,compression='gzip');donors.to_pickle(OUT/'doadores.pkl')
    d=d.merge(refs,on=['celula_mercado','orgao'],how='left',validate='many_to_one');d['ref_id']=d.ref_id.fillna(-1).astype(int);d['relativo']=d.p/d.mediana
    log(f'{len(refs):,} referencias; {d.relativo.notna().sum():,} itens com referencia')
    pri=d[d.classe.isin([6505,7510,7530,7930,8540])].copy();pri.to_pickle(OUT/'principal_com_referencia.pkl')
    # Validação independente das medianas, fora do algoritmo de bootstrap.
    import statistics
    checks=refs.sample(min(50,len(refs)),random_state=20261117)
    for r in checks.itertuples():
        h=donors[(donors.celula_mercado==r.celula_mercado)&(donors.orgao!=r.orgao)]
        assert len(h)==r.pregoes_doadores and h.orgao.nunique()==r.orgaos_doadores
        assert abs(statistics.median(h.p)-r.mediana)<1e-10
    salvar('validacao_referencias.json',{'referencias_reproduzidas':len(checks),'exclusao_cnpj_alvo':True})
    families=[('principal',pri,['produto','mes','uf']),('condicoes_compra',pri,['produto','mes','uf','srp','beneficio','faixa_q']),('ampliado',d,['produto','mes','uf']),('amostra_comum',pri[np.isfinite(pri.desconto)&np.isfinite(pri.relativo)].copy(),['produto','mes','uf'])]
    amostras={};lista=[]
    for family,base,cols in families:
        for code,y in [('A','logp'),('B','desconto'),('C','relativo')]:
            nome=family+'_'+code;x=suporte(base,cols,y);amostras[nome]=(x,y)
            lista.append({'analise':nome,'elegiveis':int(np.isfinite(base[y]).sum()),'itens':len(x),'A':int(x.modo.eq(0).sum()),'AF':int(x.modo.eq(1).sum()),'estratos':x.estrato.nunique() if len(x) else 0,'orgaos':x.orgao.nunique()})
    for code,y in [('A','logp'),('B','desconto'),('C','relativo')]:
        base=pri[np.isfinite(pri[y])].copy();g=base.groupby('produto')[y];lo=g.transform(lambda v:v.quantile(.01));hi=g.transform(lambda v:v.quantile(.99));base['y_win']=base[y].clip(lo,hi)
        x=suporte(base,['produto','mes','uf'],'y_win');amostras['winsor_'+code]=(x,'y_win')
        lista.append({'analise':'winsor_'+code,'elegiveis':len(base),'itens':len(x),'A':int(x.modo.eq(0).sum()),'AF':int(x.modo.eq(1).sum()),'estratos':x.estrato.nunique() if len(x) else 0,'orgaos':x.orgao.nunique(),'fracao_alterada':float((base[y]!=base.y_win).mean())})
    pd.DataFrame(lista).to_csv(OUT/'amostras_preestimacao.csv',index=False,encoding='utf-8-sig')
    log('Suporte das 15 análises registrado antes dos testes')
    for nome,(x,y) in amostras.items():
        if not len(x):RES[nome]={'estimavel':False};continue
        r,x=teste(x,y);r.update({'analise':nome,'desfecho':y,'familia':nome.rsplit('_',1)[0],'codigo':nome[-1]});RES[nome]=r;amostras[nome]=(x,y)
        if nome.startswith(('principal_','amostra_comum_')):x.to_pickle(OUT/f'amostra_{nome}.pkl')
        log(f'{nome}: N={len(x):,}; G={r["orgaos"]}; S={r["estratos"]}; delta={r["diferenca"]:.6g}; p_duplo={r["infer_duplo"]["p"]}')
        salvar('resultados.json',RES)
    orgs=np.sort(d.orgao.unique());orgindex={int(o):i for i,o in enumerate(orgs)}
    rng=np.random.default_rng(20261117);counts=rng.multinomial(len(orgs),np.ones(len(orgs))/len(orgs),size=1999).astype('int16')
    np.save(OUT/'multiplicidades_orgao.npy',counts);salvar('orgaos_bootstrap.json',orgs.tolist())
    refboot=medianas_bootstrap(blocos,counts,orgindex,len(refs),callback=log);np.save(OUT/'referencias_bootstrap.npy',refboot)
    for nome,(x,y) in amostras.items():
        if not len(x):continue
        # A winsorização é diagnóstico condicional aos limites e ao benchmark originais.
        rb=refboot if nome.endswith('_C') and not nome.startswith('winsor_') else None
        rep,fracao=bootstrap(x,y,counts,orgindex,refboot=rb)
        RES[nome]['bootstrap']=resumo_boot(RES[nome]['diferenca'],rep,fracao)
        RES[nome]['bootstrap_recalcula_referencia']=rb is not None
        np.savez_compressed(OUT/f'bootstrap_{nome}.npz',estimativas=rep,fracao_estratos=fracao)
        log(f'Bootstrap {nome}: {RES[nome]["bootstrap"]}')
        salvar('resultados.json',RES)
    for f in ['principal','condicoes_compra','ampliado','amostra_comum','winsor']:
        names=[f+'_'+c for c in ['A','B','C']]
        pp=holm([RES[n].get('infer_duplo',{}).get('p') for n in names]);pb=holm([RES[n].get('bootstrap',{}).get('p') for n in names])
        for n,p,b in zip(names,pp,pb):RES[n]['p_holm']=p;RES[n]['p_bootstrap_holm']=b
    salvar('resultados.json',RES)
    # Auditoria de influência: omitir cada um dos dez órgãos com maior peso AF e refazer suporte.
    influence=[]
    for code,y in [('A','logp'),('B','desconto'),('C','relativo')]:
        x,_=amostras['principal_'+code]
        if not len(x):continue
        weights=x[x.modo.eq(1)].groupby('orgao').peso_padronizado.sum().sort_values(ascending=False)
        for o in weights.head(10).index:
            z=suporte(x[x.orgao!=o],['produto','mes','uf'],y)
            if len(z):
                r,_=teste(z,y);influence.append({'desfecho':code,'orgao_excluido':o,'peso_AF':weights.loc[o],'itens':len(z),'estratos':r['estratos'],'diferenca':r['diferenca'],'nota':'Diagnóstico posterior; benchmark observado fixado'})
    pd.DataFrame(influence).to_csv(OUT/'influencia_orgaos.csv',index=False,encoding='utf-8-sig')
    # Exportar amostras com identificadores legíveis para verificação externa.
    mapas=json.loads((OUT/'fonte/mapas.json').read_text(encoding='utf-8'))
    for code in ['A','B','C']:
        x,_=amostras['principal_'+code];z=x.copy()
        for col in ['compra','orgao','uasg','unidade','descricao','uf','beneficio']:
            z[col]=z[col].map({v:k for k,v in mapas[col].items()})
        for col in ['abertura','resultado']:z[col]=pd.to_datetime(z[col],unit='D').dt.strftime('%Y-%m-%d')
        z.to_csv(OUT/f'amostra_principal_{code}.csv.gz',index=False,compression='gzip')
    salvar('fim_execucao.json',{'data':time.strftime('%Y-%m-%dT%H:%M:%S'),'segundos':time.time()-T0,'analises':len(RES),'referencias':len(refs),'doadores_pregao_produto':len(donors),'orgaos_sorteio':len(orgs)})
    log('Testes e sensibilidades concluídos')
if __name__=='__main__':main()
