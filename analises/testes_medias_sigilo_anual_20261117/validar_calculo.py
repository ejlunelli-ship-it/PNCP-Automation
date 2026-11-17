"""Validação independente: WLS explícita e expansão literal de doadores sorteados."""
from pathlib import Path
import json,sys
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parent))
from estatistica import suporte,teste,referencias,medianas_bootstrap,bootstrap
OUT=Path(__file__).resolve().parent

def comparar_wls(d,y):
    r,z=teste(d.copy(),y);s=z.estrato.to_numpy(int);t=z.modo.to_numpy(int);S=r['estratos'];N=len(z)
    X=np.column_stack([np.eye(S)[s],t]);n=np.bincount(2*s+t,minlength=2*S);w=1/n[2*s+t]
    bread=np.linalg.inv(X.T@(w[:,None]*X));beta=bread@(X.T@(w*z[y].to_numpy()))
    assert abs(beta[-1]-r['diferenca'])<1e-9
    resid=z[y].to_numpy()-X@beta
    def cov(cols):
        code=pd.factorize(pd.MultiIndex.from_frame(z[cols]))[0];G=code.max()+1
        U=np.zeros((G,S+1));np.add.at(U,code,X*(w*resid)[:,None]);V=bread@(U.T@U)@bread
        return V[-1,-1]*G/(G-1)*(N-1)/(N-S-1)
    va=cov(['orgao'])+cov(['codigo'])-cov(['orgao','codigo'])
    assert abs(va-r['variancias']['duplo'])<1e-9
    return {'itens':N,'estratos':S,'erro_coeficiente':float(abs(beta[-1]-r['diferenca'])),'erro_variancia':float(abs(va-r['variancias']['duplo']))}

def main():
    rng=np.random.default_rng(41);rows=[]
    for s in range(12):
        for modo in [0,1]:
            for j in range(1+s%4):
                rows.append({'id':len(rows),'estrato':s,'modo':modo,'orgao':(s+j+modo)%7,'codigo':s%5,'produto':s%5,'compra':len(rows),'q':10+s,'srp':s%2,'y':s+.5*modo+rng.normal(),'p':1.,'ref_id':-1})
    syn=comparar_wls(pd.DataFrame(rows),'y')
    real=pd.read_pickle(OUT.parent/'testes_medias_20261117/base_principal.pkl');real['ref_id']=-1
    real=suporte(real[real.sigilo.eq(1)],['produto','ano','uf'],'logp');ids=real.estrato.drop_duplicates().sample(35,random_state=123)
    real=real[real.estrato.isin(ids)].copy();real['estrato']=pd.factorize(real.estrato)[0];rr=comparar_wls(real,'logp')
    dd=pd.DataFrame([{'celula_mercado':0,'compra':j,'orgao':j//2,'p':float(j+1)} for j in range(8)])
    ref,don,blocks=referencias(dd);counts=np.array([[1,1,1,1],[2,1,0,2],[1,1,1,2],[0,1,1,1]])
    rb=medianas_bootstrap(blocks,counts,{i:i for i in range(4)},len(ref))
    for row in ref.itertuples():
        h=don[don.orgao!=row.orgao]
        for b,c in enumerate(counts):
            keep=c[h.orgao.to_numpy()]>0
            values=np.repeat(h.p.to_numpy(),c[h.orgao.to_numpy()])
            if keep.sum()<5 or h.loc[keep,'orgao'].nunique()<2:assert np.isnan(rb[b,row.ref_id])
            else:assert abs(rb[b,row.ref_id]-np.median(values))<1e-12
    # Bootstrap sem sorteio deve reproduzir as médias originais, incluindo o índice recalculado.
    x=pd.DataFrame(rows);x['estrato']=x.estrato.astype(int);x['ref_id']=-1
    rep,frac=bootstrap(x,'y',np.ones((1,7),int),{i:i for i in range(7)})
    r,_=teste(x,'y');assert abs(rep[0]-r['diferenca'])<1e-12 and frac[0]==1
    out={'wls_sintetico':syn,'wls_dados_reais':rr,'medianas_bootstrap_expansao_literal':len(ref)*len(counts),'bootstrap_unitario_reproduz_original':True}
    (OUT/'validacao_calculo.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(out,flush=True)
if __name__=='__main__':main()
