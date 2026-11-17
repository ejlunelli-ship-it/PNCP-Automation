"""Verifica o arquivo versionado ou reproduz os testes no workspace local."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys,importlib
HERE=Path(__file__).resolve().parent;REPO=HERE.parent;WORK=REPO.parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--verificar',action='store_true');g.add_argument('--executar',action='store_true');p.add_argument('--somente-anual',action='store_true');a=p.parse_args()
    manifest=json.loads((HERE/'manifesto.json').read_text(encoding='utf-8'))
    for f,h in manifest['sha256'].items():
        if sha(HERE/f)!=h:raise SystemExit('Arquivo diverge do manifesto: '+f)
    for package in ['numpy','pandas','scipy']:importlib.import_module(package)
    if REPO.name!='PNCP-Automation':raise SystemExit('Os scripts históricos esperam o repositório nomeado PNCP-Automation.')
    db=REPO/'dados/pncp.db';record=json.loads((HERE/'testes_medias_sigilo_anual_20261117/registro_inicio.json').read_text(encoding='utf-8'))
    if not db.exists():
        if a.verificar:
            print(f'Manifesto verificado: {len(manifest["sha256"])} arquivos. Dependências disponíveis. Banco ausente; execução depende do snapshot local.',flush=True)
            return
        raise SystemExit('Banco necessário para executar: '+str(db))
    st=db.stat()
    if st.st_size!=record['bytes'] or st.st_mtime_ns!=record['mtime_ns']:raise SystemExit('O banco difere dos metadados do snapshot registrado; confira a origem antes de reproduzir.')
    print(f'Manifesto verificado: {len(manifest["sha256"])} arquivos. Banco e dependências disponíveis.',flush=True)
    if a.verificar:return
    folders=['painel_efeitos_fixos_20261116','testes_medias_20261117','testes_medias_sigilo_anual_20261117']
    for folder in folders:
        dst=WORK/'analise'/folder;dst.mkdir(parents=True,exist_ok=True)
        for src in (HERE/folder).iterdir():
            if src.suffix!='.py' and src.name not in ['protocolo.md','emenda_antes_estimacao.md']:continue
            target=dst/src.name
            if target.exists() and target.read_bytes()!=src.read_bytes():raise SystemExit(f'Fonte local diferente, preservada: {target}')
            if not target.exists():target.write_bytes(src.read_bytes())
    sequences=[]
    if not a.somente_anual:sequences.append(('testes_medias_20261117',['preparar.py','validar_calculo.py','executar.py','auditar.py','relatar.py','validar_entrega.py']))
    sequences.append(('testes_medias_sigilo_anual_20261117',['validar_calculo.py','executar.py','auditar.py','relatar.py','validar_entrega.py']))
    for folder,scripts in sequences:
        for script in scripts:subprocess.run([sys.executable,str(WORK/'analise'/folder/script)],cwd=WORK,check=True)
if __name__=='__main__':main()
