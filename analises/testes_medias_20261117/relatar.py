"""Gera relatório e planilha dos testes, preservando todas as especificações."""
from pathlib import Path
import json,sys,math
import pandas as pd
import numpy as np
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
sys.path.insert(0,str(ROOT/'analise/painel_efeitos_fixos_20261116'))
from planilha import xlsx

def num(v,n=2):
    if v is None or not np.isfinite(v):return '—'
    return f'{v:,.{n}f}'.replace(',','X').replace('.',',').replace('X','.')
def pval(v):return '—' if v is None else ('<0,0001' if v<.0001 else num(v,4))
def intervalo(a,n=2):return '—' if a is None else '['+num(a[0],n)+'; '+num(a[1],n)+']'
def table(rows):return '\n'.join(['| '+' | '.join(map(str,rows[0]))+' |','|'+'|'.join(['---']*len(rows[0]))+'|']+['| '+' | '.join(map(str,r))+' |' for r in rows[1:]])
def norm_rows(df):
    return [list(df.columns)]+[[None if pd.isna(v) else v.item() if isinstance(v,np.generic) else v for v in row] for row in df.itertuples(index=False,name=None)]
def main():
    res=json.loads((OUT/'resultados.json').read_text(encoding='utf-8'));samples=pd.read_csv(OUT/'amostras_preestimacao.csv');flow=pd.read_csv(OUT/'fluxo.csv');valid=json.loads((OUT/'validacao_final.json').read_text(encoding='utf-8'))
    rows=[];descr=[];conc=[]
    nomes={'A':'Logaritmo do preço','B':'Desconto (%)','C':'Preço/mediana pública'}
    for nome,r in res.items():
        if not r.get('estimavel'):rows.append({'Analise':nome,'Estimavel':False});continue
        c=r['codigo'];scale=100 if c=='B' else 1.;inf=r['infer_duplo'];ci=inf['ic95'];boot=r['bootstrap'];bi=boot.get('ic_basico');D=r['diferenca'];a=r['descritivas']['0'];b=r['descritivas']['1']
        row={'Analise':nome,'Desfecho':nomes[c],'Estimavel':True,'Itens A':a['itens'],'Itens AF':b['itens'],'Itens total':r['itens'],'Pregoes':r['pregoes'],'Orgaos':r['orgaos'],'Orgaos A':a['orgaos'],'Orgaos AF':b['orgaos'],'CATMAT':r['catmats'],'Produtos':r['produtos'],'Estratos':r['estratos'],'Media A padronizada':r['media_A']*scale,'Media AF padronizada':r['media_AF']*scale,'Diferenca AF-A':D*scale,'EP duplo':None if inf['ep'] is None else inf['ep']*scale,'IC95 inferior':None if ci is None else ci[0]*scale,'IC95 superior':None if ci is None else ci[1]*scale,'Unidade diferenca':'p.p.' if c=='B' else 'log' if c=='A' else 'unidades do indice','t':inf['t'],'gl':inf['gl'],'p duplo':inf['p'],'p Holm trio':r['p_holm'],'Significativo 5% Holm':r['p_holm']<.05,'p orgao':r['infer_orgao']['p'],'p bootstrap':boot.get('p'),'p bootstrap Holm':r['p_bootstrap_holm'],'Bootstrap IC basico inferior':None if bi is None else bi[0]*scale,'Bootstrap IC basico superior':None if bi is None else bi[1]*scale,'Bootstrap fracao estratos retidos':boot.get('fracao_media_estratos_retidos'),'Bootstrap recalcula referencia':r['bootstrap_recalcula_referencia']}
        if c=='A':row.update({'Diferenca geometrica %':100*np.expm1(D),'IC95 geometrico inferior %':None if ci is None else 100*np.expm1(ci[0]),'IC95 geometrico superior %':None if ci is None else 100*np.expm1(ci[1]),'Media geometrica A':np.exp(r['media_A']),'Media geometrica AF':np.exp(r['media_AF'])})
        if c=='C':row['Variacao relativa das medias % descritiva']=100*(r['media_AF']/r['media_A']-1)
        rows.append(row)
        for k,name in [('0','Aberto'),('1','Aberto-Fechado')]:
            s=r['descritivas'][k];v={'Analise':nome,'Modo':name}
            for field in ['itens','pregoes','orgaos','produtos','media_bruta','media_padronizada','dp','mediana','min','q01','q25','q75','q99','max','assimetria','curtose_excesso','media_logq_padronizada','srp_padronizado']:v[field]=s[field]
            v['Escala']='proporcao' if c=='B' else 'log' if c=='A' else 'razao';descr.append(v)
            conc.append({'Analise':nome,'Modo':name,**r['concentracao'][k]})
    df=pd.DataFrame(rows);de=pd.DataFrame(descr);co=pd.DataFrame(conc)
    for fn,z in [('todas_estimativas.csv',df),('descritivas.csv',de),('concentracao.csv',co)]:z.to_csv(OUT/fn,index=False,sep=';',encoding='utf-8-sig')
    principal=df[df.Analise.str.startswith('principal_')]
    metodologia=[['Campo','Definição'],['Fonte','PNCP-Automation/dados/pncp.db; nova leitura somente leitura; Dados Abertos/Compras.gov.br'],['População','Pregão eletrônico; material; homologado; Menor preço; produtos e compradores recorrentes; classes prioritárias 6505/7510/7530/7930/8540'],['Comparação','Mesmo produto, mês e UF; pesos iguais por estrato e por modo no estrato'],['Hipótese','H0: diferença de médias padronizadas=0; bilateral; alfa 5%'],['Teste principal','t da diferença padronizada; variância robusta com agrupamentos CNPJ e CATMAT; Holm nos três desfechos'],['Bootstrap','1999 sorteios de CNPJs; recálculo das referências em C; somente complementar devido à perda de suporte'],['Referência','Mediana de medianas por pregão; mesmo produto/mês/UF; excluir todo o CNPJ-alvo; mínimo 5 pregões de 2 outros órgãos'],['Desconto','(1-P/R); R positivo e sigilo falso; tabelas de resultados em % e diferença em p.p.'],['Razão','P/M em nível, sem substituir pelo log; inferência principal condicional ao benchmark observado'],['Limites','Associação observacional; comparabilidade técnica aproximada; seleção de homologados; preços ativos não certificados; índice sensível a valores extremos'],['Winsorização','Quantis 1/99 por produto; diagnóstico secundário, sem exclusão dos valores originais; não necessariamente 2% dos registros alterados'],['Significância','Holm separado por trio; ICs individuais. Valores-p de sensibilidades são exploratórios.']]
    abas={'Principal':norm_rows(principal),'Todas estimativas':norm_rows(df),'Descritivas':norm_rows(de),'Amostras':norm_rows(samples),'Fluxo':norm_rows(flow),'Concentracao':norm_rows(co),'Extremos indice':norm_rows(pd.read_csv(OUT/'auditoria_extremos_indice.csv')),'Influencia orgaos':norm_rows(pd.read_csv(OUT/'influencia_orgaos.csv')),'Metodologia':metodologia}
    xlsx(OUT/'resultados_completos.xlsx',abas)
    rA=res['principal_A'];rB=res['principal_B'];rC=res['principal_C'];a=df.set_index('Analise')
    txt=[]
    txt.append('**Diferenças de médias — Aberto versus Aberto-Fechado — 17/11/2026**\n')
    txt.append('**Resultado:** o teste principal encontra média de log do preço menor em Aberto-Fechado, com diferença geométrica de '+num(a.loc['principal_A','Diferenca geometrica %'])+'% e p ajustado de '+pval(rA['p_holm'])+'. Desconto e preço relativo não apresentam diferença significativa a 5% na amostra principal. A significância do log do preço não se mantém após Holm no bootstrap complementar (p='+pval(rA['p_bootstrap_holm'])+'), que perde muitos estratos. O índice P/M em nível está dominado por registros extremos e não sustenta interpretação econômica da diferença de médias. São associações entre grupos, não efeitos causais da troca de modo.\n')
    txt.append('**Fonte e amostra.** Nova consulta ao banco indicado pelo usuário, `PNCP-Automation/dados/pncp.db`, aberto somente para leitura. Snapshot 10/11/2026. Aberturas de 01/11/2022 a 30/04/2026; elegibilidade detalhada no protocolo. Fonte Dados Abertos/Compras.gov.br, não todas as plataformas do PNCP. A análise principal mantém as classes prioritárias de bens potencialmente padronizáveis dos estudos anteriores; todas as classes entram na sensibilidade ampliada. Excluídos serviços, outras modalidades, Fechado-Aberto, não homologados e critérios diferentes de Menor preço. Recorrência foi novamente verificada usando somente A/AF. Não foram removidos singletons de modelos de painel: este é um novo teste de médias.\n')
    txt.append('**Médias comparáveis.** Produto=CATMAT+apresentação/unidade+PDM+descrição resumida. Somente estratos produto×mês×UF contendo ambos os modos. Cada estrato recebe peso igual, e cada modo tem peso total igual dentro dele. A média padronizada é a média das médias dos estratos. As médias brutas, DP, medianas e quantis também estão disponíveis, mas não devem ser confundidos com as médias padronizadas da tabela.\n')
    hdr=['Desfecho','Média A','Média AF','Diferença AF−A','IC95%','p nominal','p Holm','Signif. 5%']
    body=[hdr]
    for c in ['A','B','C']:
        z=a.loc['principal_'+c];dec=4 if c=='A' else 2
        body.append([nomes[c],num(z['Media A padronizada'],dec),num(z['Media AF padronizada'],dec),num(z['Diferenca AF-A'],dec)+' '+z['Unidade diferenca'],intervalo([z['IC95 inferior'],z['IC95 superior']],dec),pval(z['p duplo']),pval(z['p Holm trio']),'Sim' if z['Significativo 5% Holm'] else 'Não'])
    txt.append(table(body)+'\n')
    txt.append('Para A, Δlog='+num(rA['diferenca'],5)+', EP='+num(rA['infer_duplo']['ep'],5)+', t='+num(rA['infer_duplo']['t'],3)+', gl='+str(rA['infer_duplo']['gl'])+'. A transformação 100×[exp(Δ)−1] resulta em '+num(a.loc['principal_A','Diferenca geometrica %'])+'%, IC95% '+intervalo([a.loc['principal_A','IC95 geometrico inferior %'],a.loc['principal_A','IC95 geometrico superior %']])+'. Médias geométricas de produtos com unidades diferentes são índices de composição fixa, não preço de uma cesta física ou gasto médio.\n')
    txt.append('Para B, a diferença é em pontos percentuais; as médias são descontos percentuais. Para C, 1 representa preço igual ao benchmark; a diferença está em unidades da razão, não em pontos percentuais. O valor descritivo da variação relativa das médias de C é exportado à planilha, mas sua interpretação é comprometida pelas caudas. Não foi calculado IC específico para esse quociente de médias.\n')
    rr=[['Desfecho','Itens A','Itens AF','Total','Pregões','Órgãos A/AF','Órgãos distintos','Produtos','Estratos']]
    for c in ['A','B','C']:
        z=a.loc['principal_'+c];rr.append([c,*[num(z[k],0) for k in ['Itens A','Itens AF','Itens total','Pregoes']],str(z['Orgaos A'])+'/'+str(z['Orgaos AF']),num(z['Orgaos'],0),num(z['Produtos'],0),num(z['Estratos'],0)])
    txt.append(table(rr)+'\n')
    txt.append('Os órgãos podem aparecer nos dois modos; as contagens por modo não são somadas para obter órgãos distintos. As elegibilidades diferem: B exige estimado válido e sigilo falso; C exige benchmark. A interseção comum foi estimada separadamente.\n')
    txt.append('**Distribuição e escolha do teste.** O teste é bilateral de diferença de médias padronizadas, equivalente a WLS com interceptos de estrato, indicador AF e pesos 1/n_estrato_modo. O sandwich aceita heteroscedasticidade e dependência dentro do CNPJ e do CATMAT; usa t e correções finitas especificadas. Não pressupõe normalidade dos itens ou variâncias iguais, mas sua aproximação requer informação suficiente entre grupos. Welch isolado não resolve a dependência entre itens. Mann–Whitney testa uma hipótese de distribuição e não genericamente igualdade de médias; não foi usado como substituto. Não houve escolha de teste por Shapiro ou pelo resultado mais significativo. Referências: [agrupamentos múltiplos](https://www.nber.org/papers/t0327), [Welch](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.ttest_ind.html), [Mann–Whitney](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.mannwhitneyu.html).\n')
    rr=[['Desfecho/modo','Média bruta','DP','Mediana','P99','Máximo','Assimetria','Curtose excesso']]
    for c in ['A','B','C']:
        for k,label in [('0','A'),('1','AF')]:
            z=res['principal_'+c]['descritivas'][k];sc=100 if c=='B' else 1
            rr.append([c+'/'+label,*[num(z[v]*sc) for v in ['media_bruta','dp','mediana','q99','max']],num(z['assimetria']),num(z['curtose_excesso'])])
    txt.append(table(rr)+'\n')
    txt.append('**Auditoria do preço relativo.** A referência é a mediana contemporânea de compras públicas de outros órgãos, com ≥5 pregões e ≥2 CNPJs; uma mediana por pregão, mesmo produto/mês/UF. Não é um preço externo do mercado privado. Foram reproduzidas 50 referências por algoritmo independente. O teste principal de C é condicional às referências observadas; o bootstrap complementar as recalcula.\n')
    txt.append('A maior razão é '+num(valid['maior_razao'])+': preço registrado de R$ '+num(valid['maior_preco'])+' dividido pela mediana R$ '+num(valid['mediana_doadora_maior_razao'],3)+'. O registro tem CATMAT 268493, apresentação registrada COMPRIMIDO e quantidade prevista 1. Esses valores foram confirmados no SQLite; confirmar o registro não comprova equivalência física. Não foi possível certificar se há embalagem/globalização/erro ou outra causa. Os maiores casos e seus doadores estão em `auditoria_extremos_indice.csv` e `doadores_tres_extremos.csv`. Não houve correção conjectural ou exclusão por magnitude.\n')
    txt.append('As medianas brutas das razões são próximas de 1 nos dois modos, enquanto as médias são muito maiores. Isso não autoriza trocar média por mediana e manter a mesma hipótese. A winsorização registrada foi mostrada separadamente; em produtos com poucos itens, os quantis interpolados podem modificar mais de 2% dos registros.\n')
    txt.append('**Bootstrap complementar e concentração.** Foram feitas 1.999 replicações por CNPJ, mantendo juntos os itens de cada órgão. Referências de C foram recalculadas com multiplicidade dos doadores, exclusão do órgão-alvo e mínimos de suporte. Estratos sem ambos os modos ou sem referência válida ficam ausentes na replicação. Essa perda altera a composição; os números abaixo não são uma segunda certificação da inferência principal.\n')
    rr=[['Desfecho','IC95 básico (escala original)','p bootstrap','p Holm bootstrap','Estratos retidos em média']]
    for c in ['A','B','C']:
        z=res['principal_'+c];b=z['bootstrap'];sc=100 if c=='B' else 1
        rr.append([c,intervalo([v*sc for v in b['ic_basico']],4 if c=='A' else 2),pval(b['p']),pval(z['p_bootstrap_holm']),num(100*b['fracao_media_estratos_retidos'])+'%'])
    txt.append(table(rr)+'\n')
    txt.append('Para log do preço, a correção Holm é significativa no teste principal, mas não no bootstrap. Para desconto e índice, os dois procedimentos permanecem sem rejeição após Holm. A forte perda de suporte, sobretudo em C, impede usar o bootstrap como solução definitiva para a distribuição irregular. ICs percentis e inferência somente por órgão também estão no JSON/planilha. Não rejeição não demonstra equivalência.\n')
    txt.append('**Sensibilidades registradas.** “Condições de compra” exige também SRP, benefício e faixa de quantidade fator dois iguais. Não exige mesmo comprador. “Ampliado” usa todas as classes; “Amostra comum” usa os mesmos itens elegíveis para os três desfechos; “Winsor” altera o desfecho pelos quantis 1/99 de cada produto. Populações/variáveis mudam, e nenhum resultado substitui o principal. Holm é aplicado separadamente por trio exploratório.\n')
    rr=[['Análise','Itens A/AF','Órgãos','Diferença','IC95%','p Holm']]
    for nome,z in a.iterrows():
        c=nome[-1]
        if c=='A':estimate=z['Diferenca geometrica %'];ci=[z['IC95 geometrico inferior %'],z['IC95 geometrico superior %']];un='% geom.'
        else:estimate=z['Diferenca AF-A'];ci=[z['IC95 inferior'],z['IC95 superior']];un=z['Unidade diferenca']
        rr.append([nome,str(z['Itens A'])+'/'+str(z['Itens AF']),num(z['Orgaos'],0),num(estimate)+' '+un,intervalo(ci),pval(z['p Holm trio'])])
    txt.append(table(rr)+'\n')
    z=a.loc['condicoes_compra_A'];txt.append('Na comparação adicional com condições de compra semelhantes, o log do preço corresponde a '+num(z['Diferenca geometrica %'])+'%, IC95% '+intervalo([z['IC95 geometrico inferior %'],z['IC95 geometrico superior %']])+', p Holm='+pval(z['p Holm trio'])+'; bootstrap Holm='+pval(z['p bootstrap Holm'])+'. Esse resultado reforça a associação negativa nessa população específica, sem remover confundimento entre compradores. Para C, a mesma restrição reduz a amostra a 209 itens e aproxima as médias de 1, mas a diferença permanece não significativa.\n')
    txt.append('**Limites.** A análise compara compras homologadas e recorrentes, selecionadas e não aleatórias. Catálogo/apresentação não certificam equivalência técnica integral. Quantidade/SRP no snapshot não garantem versões anteriores à decisão do modo. Referências usam preços públicos contemporâneos, inclusive dos dois modos; podem refletir a composição institucional e efeitos compartilhados. O benchmark não deve ser chamado de preço verdadeiro de mercado. Campos de lote e resultados ativos continuam incompletos. A análise não mede execução, entrega ou economia fiscal. As diferenças em relação ao painel e matching anteriores decorrem também de outro alvo (peso igual por produto/mês/UF), recortes e ajustes; não são três estimativas intercambiáveis do mesmo efeito.\n')
    txt.append('**Integridade e reprodução.** '+str(valid['itens_conferidos_SQLite'])+' itens conferidos diretamente no SQLite, incluindo extremos; valores, quantidades, status e identificadores coincidiram. Coeficiente e variância comparados a WLS com dummies explícitas em dados sintéticos e 101 itens reais. Medianas bootstrap comparadas à expansão literal de doadores. Banco preservado em tamanho/mtime. Protocolo e emenda computacional antes da estimação, hashes, extração, amostras, sorteios e scripts preservados. A emenda de inferência durante a extração é transparente; não se reivindica pré-registro público.\n')
    txt.append('Arquivos: `resultados_completos.xlsx`, `todas_estimativas.csv`, `descritivas.csv`, `resultados.json`, `amostra_principal_A/B/C.csv.gz`, `protocolo.md`, `emenda_antes_estimacao.md`. Reprodução: `preparar.py`, `validar_calculo.py`, `executar.py`, `auditar.py`, `relatar.py`, `validar_entrega.py`, usando o Python portátil do workspace.\n')
    (OUT/'relatorio_completo.md').write_text('\n'.join(txt),encoding='utf-8')
    print(principal[['Analise','Itens A','Itens AF','Media A padronizada','Media AF padronizada','Diferenca AF-A','IC95 inferior','IC95 superior','p duplo','p Holm trio']].to_string(index=False))
if __name__=='__main__':main()
