"""Diferenças padronizadas e inferência por agrupamentos, sem dependência de statsmodels."""
import numpy as np
import pandas as pd
from scipy import stats, sparse

def codigos(d,cols):return pd.factorize(pd.MultiIndex.from_frame(d[cols]),sort=True)[0]

def suporte(d,cols,y):
    x=d[np.isfinite(d[y])].copy()
    if not len(x):return x
    x['estrato']=codigos(x,cols)
    grupos=x.groupby('estrato').modo.nunique()
    x=x[x.estrato.isin(grupos[grupos==2].index)].copy()
    if len(x):x['estrato']=pd.factorize(x.estrato,sort=True)[0]
    return x.reset_index(drop=True)

def medias(d,y):
    s=d.estrato.to_numpy();t=d.modo.to_numpy();v=d[y].to_numpy(float)
    S=int(s.max())+1;arm=2*s+t
    n=np.bincount(arm,minlength=2*S);soma=np.bincount(arm,weights=v,minlength=2*S)
    m=soma/n;delta=float(np.mean(m[1::2]-m[0::2]))
    return float(np.mean(m[0::2])),float(np.mean(m[1::2])),delta,n,m

def teste(d,y):
    ma,mf,delta,n,m=medias(d,y);s=d.estrato.to_numpy();t=d.modo.to_numpy();S=len(n)//2;N=len(d)
    sinais=2*t-1;arm=2*s+t;v=d[y].to_numpy(float)
    resid=v-(m[2*s]+m[2*s+1])/2-delta*sinais/2
    score=sinais*resid/(S*n[arm])
    def variancia(cols):
        codes=codigos(d,cols);G=int(codes.max())+1
        u=np.bincount(codes,weights=score,minlength=G)
        return float(np.dot(u,u)*G/(G-1)*(N-1)/(N-S-1)) if G>1 and N>S+1 else np.nan,G,u
    vo,go,uo=variancia(['orgao']);vp,gp,up=variancia(['codigo']);vi,gi,_=variancia(['orgao','codigo'])
    v2=vo+vp-vi;df=min(go,gp)-1
    def infer(var,df):
        if not np.isfinite(var) or var<=0 or df<1:return {'ep':None,'t':None,'gl':df,'p':None,'ic95':None}
        se=float(np.sqrt(var));stat=delta/se;c=float(stats.t.ppf(.975,df))
        return {'ep':se,'t':stat,'gl':df,'p':float(2*stats.t.sf(abs(stat),df)),'ic95':[delta-c*se,delta+c*se]}
    pesos=1/(S*n[arm]);desc={};conc={}
    for k in [0,1]:
        z=d[t==k];a=z[y].to_numpy(float);w=pesos[t==k]
        desc[str(k)]={'itens':len(z),'pregoes':z.compra.nunique(),'orgaos':z.orgao.nunique(),'produtos':z.produto.nunique(),'media_bruta':float(np.mean(a)),'dp':float(np.std(a,ddof=1)),'mediana':float(np.median(a)),'min':float(np.min(a)),'max':float(np.max(a)),'q01':float(np.quantile(a,.01)),'q25':float(np.quantile(a,.25)),'q75':float(np.quantile(a,.75)),'q99':float(np.quantile(a,.99)),'assimetria':float(stats.skew(a,bias=False)),'curtose_excesso':float(stats.kurtosis(a,bias=False)),'media_padronizada':ma if k==0 else mf,'media_logq_padronizada':float(np.sum(w*np.log(z.q))),'srp_padronizado':float(np.sum(w*z.srp))}
        c=pd.Series(w,index=z.orgao).groupby(level=0).sum().sort_values(ascending=False)
        conc[str(k)]={'maior_orgao':int(c.index[0]),'peso_maior':float(c.iloc[0]),'peso_top10':float(c.iloc[:10].sum()),'orgaos_equivalentes_concentracao':float(1/np.sum(c*c))}
    d['peso_padronizado']=pesos
    d['influencia_regressao']=score
    info=(uo*uo)/np.dot(uo,uo) if np.dot(uo,uo)>0 else uo
    return {'estimavel':True,'itens':N,'pregoes':d.compra.nunique(),'orgaos':go,'catmats':gp,'produtos':d.produto.nunique(),'estratos':S,'media_A':ma,'media_AF':mf,'diferenca':delta,'infer_duplo':infer(v2,df),'infer_orgao':infer(vo,go-1),'variancias':{'orgao':vo,'catmat':vp,'intersecao':vi,'duplo':v2},'descritivas':desc,'concentracao':conc,'fracao_estratos_um_item_cada':float(np.mean((n[0::2]==1)&(n[1::2]==1))),'concentracao_score_quadrado_max':float(np.max(info))},d

def referencias(d):
    donors=d.groupby(['celula_mercado','compra','orgao'],sort=True).p.median().reset_index()
    eleg=donors.groupby('celula_mercado').agg(n=('compra','size'),g=('orgao','nunique'))
    ids=eleg[(eleg.n>=6)&(eleg.g>=3)].index
    rows=[];blocos=[]
    for cell,h in donors[donors.celula_mercado.isin(ids)].groupby('celula_mercado',sort=True):
        if len(h)<6 or h.orgao.nunique()<3:continue
        h=h.sort_values('p');p=h.p.to_numpy(float);org=h.orgao.to_numpy(int)
        refs=[]
        for o in np.unique(org):
            other=org!=o
            if other.sum()>=5 and len(np.unique(org[other]))>=2:
                idx=len(rows);rows.append((idx,cell,o,float(np.median(p[other])),int(other.sum()),len(np.unique(org[other]))));refs.append((idx,o))
        if refs:blocos.append((cell,p,org,refs))
    r=pd.DataFrame(rows,columns=['ref_id','celula_mercado','orgao','mediana','pregoes_doadores','orgaos_doadores'])
    return r,donors,blocos

def medianas_bootstrap(blocos,counts,orgindex,nrefs,callback=None,destino=None):
    B=len(counts)
    if destino is None:out=np.full((B,nrefs),np.nan)
    else:
        out=np.lib.format.open_memmap(destino,mode='w+',dtype='float64',shape=(B,nrefs))
        out[:]=np.nan
    for j,(cell,p,org,refs) in enumerate(blocos):
        w0=counts[:,[orgindex[int(o)] for o in org]]
        for rid,o in refs:
            keep=org!=o;w=w0[:,keep];pp=p[keep]
            total=w.sum(axis=1);nc=(w>0).sum(axis=1)
            oo=np.unique(org[keep]);ng=(counts[:,[orgindex[int(z)] for z in oo]]>0).sum(axis=1)
            good=(nc>=5)&(ng>=2)&(total>0)
            cum=np.cumsum(w,axis=1);lo=(total-1)//2;hi=total//2
            il=(cum>lo[:,None]).argmax(axis=1);ih=(cum>hi[:,None]).argmax(axis=1)
            out[good,rid]=(pp[il[good]]+pp[ih[good]])/2
        if callback and j%200==0:callback(f'Referencias bootstrap: {j}/{len(blocos)} mercados')
    if destino is not None:out.flush()
    return out

def bootstrap(d,y,counts,orgindex,refboot=None):
    S=d.estrato.nunique();B=len(counts);G=counts.shape[1]
    g=d.groupby(['estrato','modo','orgao'],sort=True).agg(n=('id','size'),sy=(y,'sum'),sp=('p','sum'),ref_id=('ref_id','first')).reset_index()
    arm=(2*g.estrato+g.modo).to_numpy(int);oc=np.array([orgindex[int(o)] for o in g.orgao]);n=g.n.to_numpy(float)
    vals=np.full(B,np.nan);fra=np.zeros(B);mapa=sparse.csr_matrix((np.ones(len(g)),(np.arange(len(g)),arm)),shape=(len(g),2*S))
    if refboot is None:
        cnt=sparse.csr_matrix((n,(oc,arm)),shape=(G,2*S));som=sparse.csr_matrix((g.sy.to_numpy(),(oc,arm)),shape=(G,2*S))
    else:rid=g.ref_id.to_numpy(int);sp=g.sp.to_numpy(float)
    for a in range(0,B,80):
        b=min(B,a+80);c=counts[a:b].astype(float)
        if refboot is None:num=c@som;den=c@cnt
        else:
            mm=refboot[a:b][:,rid];ww=c[:,oc];ok=np.isfinite(mm)
            num=(np.divide(ww*sp,mm,out=np.zeros_like(mm),where=ok))@mapa
            den=(ww*n*ok)@mapa
        avg=np.divide(num,den,out=np.full_like(num,np.nan),where=den>0)
        dif=avg[:,1::2]-avg[:,0::2];valid=np.isfinite(dif);q=valid.sum(axis=1)
        vals[a:b]=np.divide(np.nansum(dif,axis=1),q,out=np.full(b-a,np.nan),where=q>0);fra[a:b]=q/S
    return vals,fra

def resumo_boot(delta,rep,fracao):
    a=rep[np.isfinite(rep)];B=len(a)
    if B<20:return {'replicacoes_validas':B,'ic_basico':None,'p':None}
    q=np.quantile(a,[.025,.975]);e=a-delta
    p=min(1.,2*min((1+np.sum(e>=delta))/(B+1),(1+np.sum(e<=delta))/(B+1)))
    return {'replicacoes_validas':B,'ic_basico':[float(2*delta-q[1]),float(2*delta-q[0])],'ic_percentil':q.tolist(),'p':float(p),'dp':float(np.std(a,ddof=1)),'media':float(np.mean(a)),'fracao_media_estratos_retidos':float(np.mean(fracao)),'fracao_min_estratos_retidos':float(np.min(fracao))}

def holm(ps):
    p=np.array([v if v is not None and np.isfinite(v) else 1. for v in ps]);order=np.argsort(p);out=np.empty(len(p));out[order]=np.minimum(1,np.maximum.accumulate(p[order]*(len(p)-np.arange(len(p)))))
    return out.tolist()
