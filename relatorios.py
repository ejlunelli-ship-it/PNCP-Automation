"""Organiza o zip "Todos os relatórios e termos" de cada compra do Compras.gov.br.

Abre cada compra no navegador padrão (sem automação, então sem captcha extra).
Você clica em Downloads > "Todos os relatórios e termos"; o script detecta o zip
na pasta Downloads, move para a pasta da compra, extrai e abre a próxima.
Só um relatório por item é mantido (o termo de homologação ou, sem ele, o de julgamento
da última sessão); o zip e os demais relatórios são apagados.
"""
import json
import shutil
import sys
import time
import webbrowser
import zipfile
from pathlib import Path

from config import DADOS
from extrator_homologacao.selecao import selecionar

URL_COMPRA = ("https://cnetmobile.estaleiro.serpro.gov.br/comprasnet-web/public/compras/"
              "acompanhamento-compra/item/1?compra={}")
DOWNLOADS = Path.home() / "Downloads"
ESPERA = 5 * 60  # segundos aguardando o download antes de pular a compra

sys.stdout.reconfigure(encoding="utf-8")


def pasta_da_compra(registro, pasta_base):
    nome = f"{registro['numeroCompra']}-{registro['anoCompraPncp']}_{registro['idCompra']}"
    return pasta_base / nome


def zips_em_downloads(id_compra):
    # o site nomeia o arquivo como relatorios-compra-<idCompra>[ (n)].zip
    return set(DOWNLOADS.glob(f"*{id_compra}*.zip"))


def esperar_novo_zip(id_compra, antes):
    """Espera aparecer um .zip novo e completo desta compra na pasta Downloads."""
    limite = time.time() + ESPERA
    while time.time() < limite:
        novos = zips_em_downloads(id_compra) - antes
        for arq in novos:
            # tamanho estável = navegador terminou de gravar
            tamanho = arq.stat().st_size
            time.sleep(1)
            if tamanho > 0 and arq.exists() and arq.stat().st_size == tamanho:
                return arq
        time.sleep(1)
    return None


def manter_selecionados(destino):
    """Deixa na pasta da compra só o relatório escolhido para cada item (ver extrator_homologacao.selecao).

    Extrai do zip os escolhidos que faltam e apaga o resto (zip incluído). Se nenhum relatório
    se encaixar na regra, não apaga nada.
    """
    no_zip = {}  # nome -> (zip, membro)
    for zp in destino.glob("*.zip"):
        if zipfile.is_zipfile(zp):
            with zipfile.ZipFile(zp) as z:
                for membro in z.namelist():
                    no_zip.setdefault(Path(membro).name, (zp, membro))
    extraidos = {p.name: p for p in destino.rglob("*.pdf")}
    manter = set(selecionar(sorted(no_zip.keys() | extraidos.keys())))
    if not manter:
        print("  nenhum termo de homologação ou julgamento; arquivos mantidos")
        return
    for nome in manter - extraidos.keys():
        zp, membro = no_zip[nome]
        with zipfile.ZipFile(zp) as z, z.open(membro) as origem, open(destino / nome, "wb") as saida:
            shutil.copyfileobj(origem, saida)
    for arq in sorted(destino.rglob("*"), reverse=True):  # arquivos antes das pastas
        if arq.is_file() and arq.name not in manter:
            arq.unlink()
        elif arq.is_dir() and not any(arq.iterdir()):
            arq.rmdir()


def baixar_relatorios(registros, pasta_base):
    pasta_base = Path(pasta_base)
    print(f"Vigiando downloads em: {DOWNLOADS}")
    ok = 0
    for i, r in enumerate(registros, 1):
        destino = pasta_da_compra(r, pasta_base)
        print(f"[{i}/{len(registros)}] {r['idCompra']} - {r['objetoCompra'][:60]}")
        if destino.exists() and (selecionar(list(destino.rglob("*.pdf"))) or any(destino.glob("*.zip"))):
            print("  já baixado, pulando")
            manter_selecionados(destino)
            ok += 1
            continue
        # sem resultado homologado o site não oferece "Todos os relatórios e termos"
        if not r.get("existeResultado") and not r.get("valorTotalHomologado"):
            print("  ainda não homologada (sem relatórios), pulando")
            continue

        antes = zips_em_downloads(r["idCompra"])
        webbrowser.open(URL_COMPRA.format(r["idCompra"]))
        print("  no navegador: Downloads > 'Todos os relatórios e termos' "
              f"(aguardando até {ESPERA // 60} min; se não tiver a opção, só esperar)")

        arq = esperar_novo_zip(r["idCompra"], antes)
        if not arq:
            print("  nenhum zip recebido, pulando")
            continue

        destino.mkdir(parents=True, exist_ok=True)
        # nome limpo, sem o " (n)" que o navegador adiciona em downloads repetidos
        shutil.move(str(arq), destino / f"relatorios-compra-{r['idCompra']}.zip")
        manter_selecionados(destino)
        print(f"  {arq.name} -> {destino}")
        ok += 1

    print(f"Relatórios organizados: {ok}/{len(registros)}")


if __name__ == "__main__":
    # sem argumento: as pastas de pregão geradas pelo get.py (dados/filtrados/pregao_<modo>/contratacoes_*.json)
    if len(sys.argv) > 1:
        origens = [Path(a) for a in sys.argv[1:]]
    else:
        origens = sorted((DADOS / "filtrados").glob("pregao_*/contratacoes_*.json"))
    for origem in origens:
        print(f"== {origem.parent.name}")
        with open(origem, encoding="utf-8") as f:
            registros = json.load(f)
        baixar_relatorios(registros, origem.parent / "relatorios")
