"""Organiza o zip "Todos os relatórios e termos" de cada compra do Compras.gov.br.

Abre cada compra no navegador padrão (sem automação, então sem captcha extra).
Você clica em Downloads > "Todos os relatórios e termos"; o script detecta o zip
na pasta Downloads, move para a pasta da compra, extrai e abre a próxima.
"""
import json
import shutil
import sys
import time
import webbrowser
import zipfile
from pathlib import Path

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


def baixar_relatorios(registros, pasta_base):
    pasta_base = Path(pasta_base)
    print(f"Vigiando downloads em: {DOWNLOADS}")
    ok = 0
    for i, r in enumerate(registros, 1):
        destino = pasta_da_compra(r, pasta_base)
        print(f"[{i}/{len(registros)}] {r['idCompra']} - {r['objetoCompra'][:60]}")
        if destino.exists() and any(destino.glob("*.zip")):
            print("  já baixado, pulando")
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
        final = Path(shutil.move(str(arq), destino / f"relatorios-compra-{r['idCompra']}.zip"))
        if zipfile.is_zipfile(final):
            with zipfile.ZipFile(final) as z:
                z.extractall(destino)
        print(f"  {arq.name} -> {destino}")
        ok += 1

    print(f"Relatórios organizados: {ok}/{len(registros)}")


if __name__ == "__main__":
    # sem argumento: todas as pastas geradas pelo get.py (dados/filtrados/<grupo>/contratacoes_<grupo>.json)
    if len(sys.argv) > 1:
        origens = [Path(a) for a in sys.argv[1:]]
    else:
        origens = sorted((Path(__file__).parent / "dados" / "filtrados").glob("*/contratacoes_*.json"))
    for origem in origens:
        print(f"== {origem.parent.name}")
        with open(origem, encoding="utf-8") as f:
            registros = json.load(f)
        baixar_relatorios(registros, origem.parent / "relatorios")
