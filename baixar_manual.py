"""Download manual dos zips "Todos os relatórios e termos", do mês mais recente para o mais antigo.

Pega as mesmas compras do baixar_api.py (Aberto-Fechado com item homologado, pelo mês do resultado) e
pode rodar junto com ele, que anda no sentido contrário. O que já foi feito fica anotado:
- termos na pasta da compra (dados/filtrados/aberto-fechado_<mês>/relatorios/<compra>/), sem a marca
  de parcial: compra resolvida, por qualquer um dos dois;
- registro compartilhado (registro/aberto-fechado_<mês>/<usuario>_manual.csv, ver registro.py): uma
  linha por compra tentada aqui (passada 'manual'), lida pelo inventario_pdfs.py e pelo baixar_api.py
  de todos os usuários depois do `git pull`. Com mais de uma pessoa, usem --parte k/n.

Não consulta o PNCP (o automático já faz isso, e os dois juntos estourariam o limite de requisições)
nem grava no pncp.db. Só abre a página da compra no navegador: você clica em Downloads >
"Todos os relatórios e termos", e o script pega o zip na pasta Downloads.

Enquanto espera o zip: [p] pula a compra (sem a opção no site), [s] encerra.
Compras puladas ou sem zip não são reabertas, salvo com --repetir.

Uso: python baixar_manual.py [--de 2026-10] [--ate 2025-11] [--parte k/n] [--repetir]
"""
import argparse
import shutil
import sys
import time
import webbrowser

from config import DADOS
from extrator_homologacao.selecao import selecionar
from inventario_pdfs import ler_motivos
from registro import anotar, compras_do_mes, na_parte, parte, termos
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
    p.add_argument("--parte", type=parte, metavar="k/n", help="só a parte k de n das compras (divisão entre usuários)")
    p.add_argument("--repetir", action="store_true", help="reabre compras puladas ou sem zip em rodadas anteriores")
    args = p.parse_args()
    print(f"Vigiando downloads em: {DOWNLOADS}. Durante a espera: [p] pula, [s] encerra.")

    for mes in meses_decrescentes(args.de, args.ate):
        pasta = DADOS / "filtrados" / f"aberto-fechado_{mes}"
        compras = [c for c in reversed(compras_do_mes(mes)) if na_parte(c["numeroControlePNCP"], args.parte)]
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
                     "situacao": "", "itens_cobertos": 0, "outros_guardados": 0}
            if arq:
                destino.mkdir(parents=True, exist_ok=True)
                shutil.move(str(arq), destino / f"relatorios-compra-{c['idCompra']}.zip")
                manter_selecionados(destino)
                (destino / PARCIAL).unlink(missing_ok=True)
                escolhidos = selecionar(list(destino.rglob("*.pdf")))
                itens, sha = termos(escolhidos)
                linha.update(situacao="completo" if escolhidos else "", itens_cobertos=len(escolhidos),
                             itens=itens, sha256=sha, motivo="zip baixado à mão" if escolhidos else "zip sem termos")
                print(f"  {len(escolhidos)} termo(s) -> {destino}")
            else:
                linha["motivo"] = "pulada no site" if comando == "p" else "zip não recebido"
                print(f"  {linha['motivo']}")
            anotar(mes, "manual", linha)


if __name__ == "__main__":
    main()
