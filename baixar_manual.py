"""Download manual dos zips "Todos os relatórios e termos", do mês mais recente para o mais antigo.

Pega as mesmas compras do baixar_api.py (Aberto-Fechado com item homologado, pelo mês do resultado) e
pode rodar junto com ele, que anda no sentido contrário. O que já foi feito fica anotado:
- termos na pasta da compra (dados/filtrados/aberto-fechado_<mês>/relatorios/<compra>/), sem a marca
  de parcial: compra resolvida, por qualquer um dos dois;
- dados/filtrados/aberto-fechado_<mês>/manual.csv: uma linha por compra tentada aqui, no formato do
  motivos.csv (passada 'manual'), lida pelo inventario_pdfs.py e pelo baixar_api.py.

Não consulta o PNCP (o automático já faz isso, e os dois juntos estourariam o limite de requisições)
nem grava no pncp.db. Só abre a página da compra no navegador: você clica em Downloads >
"Todos os relatórios e termos", e o script pega o zip na pasta Downloads.

Enquanto espera o zip: [p] pula a compra (sem a opção no site), [s] encerra.
Compras puladas ou sem zip não são reabertas, salvo com --repetir.

Uso: python baixar_manual.py [--de 2026-10] [--ate 2025-11] [--repetir]
"""
import argparse
import csv
import shutil
import sys
import time
import webbrowser

from config import DADOS
from baixar_api import COLUNAS, compras_do_mes
from extrator_homologacao.selecao import selecionar
from inventario_pdfs import ler_motivos
from relatorios import DOWNLOADS, ESPERA, PARCIAL, URL_COMPRA, manter_selecionados, pasta_da_compra, \
    zips_em_downloads

try:
    import msvcrt  # Windows: tecla sem Enter
except ImportError:
    msvcrt = None


def meses_decrescentes(de, ate):
    ano, mes = map(int, de.split("-"))
    while f"{ano}-{mes:02d}" >= ate:
        yield f"{ano}-{mes:02d}"
        ano, mes = (ano, mes - 1) if mes > 1 else (ano - 1, 12)


def resolvida(destino):
    """A pasta da compra já tem termos de todos os itens (do PNCP completo ou de um zip)."""
    return destino.exists() and not (destino / PARCIAL).exists() and bool(selecionar(list(destino.rglob("*.pdf"))))


def tecla():
    if msvcrt and msvcrt.kbhit():
        return msvcrt.getwch().lower()
    return None


def esperar_zip(id_compra, antes):
    """(zip, None) quando chega; (None, 'p'/'s') se o usuário pular/encerrar; (None, None) no tempo-limite."""
    limite = time.time() + ESPERA
    while time.time() < limite:
        t = tecla()
        if t in ("p", "s"):
            return None, t
        for arq in zips_em_downloads(id_compra) - antes:
            tamanho = arq.stat().st_size
            time.sleep(1)
            if tamanho > 0 and arq.exists() and arq.stat().st_size == tamanho:
                return arq, None
        time.sleep(1)
    return None, None


def main():
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--de", default="2026-10", help="primeiro mês (o mais recente)")
    p.add_argument("--ate", default="2025-11", help="último mês (o mais antigo)")
    p.add_argument("--repetir", action="store_true", help="reabre compras puladas ou sem zip em rodadas anteriores")
    args = p.parse_args()
    print(f"Vigiando downloads em: {DOWNLOADS}. Durante a espera: [p] pula, [s] encerra.")

    for mes in meses_decrescentes(args.de, args.ate):
        pasta = DADOS / "filtrados" / f"aberto-fechado_{mes}"
        compras = list(reversed(compras_do_mes(mes)))
        print(f"== {mes}: {len(compras)} compra(s)")
        for i, c in enumerate(compras, 1):
            # relido a cada compra: o automático pode ter acabado de completar esta
            historico = ler_motivos()
            if any(l["numeroControlePNCP"] == c["numeroControlePNCP"] and (
                    l["situacao"] == "completo" or (l["passada"] == "manual" and not args.repetir))
                   for l in historico):
                continue
            destino = pasta_da_compra(c, pasta / "relatorios")
            if resolvida(destino):
                continue

            print(f"[{mes} {i}/{len(compras)}] {c['idCompra']} - {(c['objetoCompra'] or '')[:60]}")
            antes = zips_em_downloads(c["idCompra"])
            webbrowser.open(URL_COMPRA.format(c["idCompra"]))
            arq, comando = esperar_zip(c["idCompra"], antes)
            if comando == "s":
                print("Encerrado.")
                return
            linha = {"numeroControlePNCP": c["numeroControlePNCP"], "idCompra": c["idCompra"], "passada": "manual",
                     "situacao": "", "itens_cobertos": 0, "publicados": "", "candidatos": "",
                     "outros_guardados": 0, "erros": ""}
            if arq:
                destino.mkdir(parents=True, exist_ok=True)
                shutil.move(str(arq), destino / f"relatorios-compra-{c['idCompra']}.zip")
                manter_selecionados(destino)
                (destino / PARCIAL).unlink(missing_ok=True)
                termos = selecionar(list(destino.rglob("*.pdf")))
                linha.update(situacao="completo" if termos else "", itens_cobertos=len(termos),
                             motivo="zip baixado à mão" if termos else "zip sem termos")
                print(f"  {len(termos)} termo(s) -> {destino}")
            else:
                linha["motivo"] = "pulada no site" if comando == "p" else "zip não recebido"
                print(f"  {linha['motivo']}")
            pasta.mkdir(parents=True, exist_ok=True)
            arquivo = pasta / "manual.csv"
            novo = not arquivo.exists()
            with open(arquivo, "a", newline="", encoding="utf-8-sig" if novo else "utf-8") as f:
                w = csv.DictWriter(f, fieldnames=COLUNAS)
                if novo:
                    w.writeheader()
                w.writerow(linha)


if __name__ == "__main__":
    main()
