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

--auto: o clique fica com o userscript navegador/compras_auto.user.js (Tampermonkey), que age só nas
abas abertas por este script. O hCaptcha não é contornado: o site gera o token como num clique à mão,
e um desafio, se aparecer, é resolvido por você na aba. Entre uma compra e outra há um intervalo
aleatório (--intervalo); depois de --max-falhas compras seguidas sem zip, o script pausa.

Enquanto espera o zip: [p] pula a compra (sem a opção no site), [s] encerra.
Compras puladas ou sem zip não são reabertas, salvo com --repetir.

Uso: python baixar_manual.py [--de 2026-10] [--ate 2025-11] [--parte k/n] [--repetir]
                             [--auto [--intervalo 20-60] [--max-falhas 3]]
"""
import argparse
import random
import re
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

# avisos que o userscript baixa quando a compra não tem zip: pncp-auto-<idCompra>-<motivo>.txt
MOTIVOS_AUTO = {
    "sem-opcao": "sem a opção no site",
    "sem-botao": "sem botão de downloads no site",
    "acesso-nao-autorizado": "acesso não autorizado no site",
    "compra-nao-encontrada": "compra não encontrada no site",
    "erro-download": "erro do site no download",
}
ID_COMPRA = re.compile(r"\d{17}")  # UASG (6) + modalidade (2) + número (5) + ano (4)
AVISO_DESAFIO = 60  # segundos sem zip no --auto antes de lembrar de olhar a aba (desafio do captcha)


def meses_decrescentes(de, ate):
    ano, mes = map(int, de.split("-"))
    while f"{ano}-{mes:02d}" >= ate:
        yield f"{ano}-{mes:02d}"
        ano, mes = (ano, mes - 1) if mes > 1 else (ano - 1, 12)


def intervalo(texto):
    """'20-60' -> (20.0, 60.0); '30' -> (30.0, 30.0)."""
    try:
        minimo, _, maximo = texto.partition("-")
        minimo, maximo = float(minimo), float(maximo or minimo)
    except ValueError:
        raise argparse.ArgumentTypeError("use segundos como 20-60 ou 30")
    if minimo < 0 or maximo < minimo:
        raise argparse.ArgumentTypeError("use segundos como 20-60 ou 30")
    return minimo, maximo


def resolvida(destino):
    """A pasta da compra já tem termos de todos os itens (do PNCP completo ou de um zip)."""
    return destino.exists() and not (destino / PARCIAL).exists() and bool(selecionar(list(destino.rglob("*.pdf"))))


def tecla():
    if msvcrt and msvcrt.kbhit():
        return msvcrt.getwch().lower()
    return None


def avisos_em_downloads(id_compra):
    # o navegador pode acrescentar " (n)" ao nome
    return set(DOWNLOADS.glob(f"pncp-auto-{id_compra}-*.txt"))


def motivo_do_aviso(arq):
    nome = arq.stem.split(" (")[0]
    for codigo, motivo in MOTIVOS_AUTO.items():
        if nome.endswith("-" + codigo):
            return motivo
    return "aviso desconhecido do userscript"


def guardar_aviso(aviso):
    """Move o aviso (com o diagnóstico da página) para dados/avisos_auto/, fora da pasta Downloads."""
    pasta = DADOS / "avisos_auto"
    pasta.mkdir(parents=True, exist_ok=True)
    shutil.move(str(aviso), pasta / aviso.name.replace(" ", ""))


def esperar_zip(id_compra, antes, auto=False):
    """(zip, None) quando chega; (None, 'p'/'s') se o usuário pular/encerrar; (None, None) no tempo-limite;
    no --auto, (None, motivo) quando o userscript avisa que a compra não tem zip."""
    limite = time.time() + ESPERA
    lembrete = time.time() + AVISO_DESAFIO
    while time.time() < limite:
        t = tecla()
        if t in ("p", "s"):
            return None, t
        for arq in zips_em_downloads(id_compra) - antes:
            tamanho = arq.stat().st_size
            time.sleep(1)
            if tamanho > 0 and arq.exists() and arq.stat().st_size == tamanho:
                return arq, None
        if auto:
            for aviso in avisos_em_downloads(id_compra):
                # o Firefox cria o arquivo vazio e só depois grava: espera o tamanho firmar
                tamanho = aviso.stat().st_size
                time.sleep(1)
                if tamanho == 0 or not aviso.exists() or aviso.stat().st_size != tamanho:
                    continue
                motivo = motivo_do_aviso(aviso)
                guardar_aviso(aviso)
                return None, motivo
            if lembrete and time.time() > lembrete:
                print(f"  sem zip há {AVISO_DESAFIO} s: veja se a aba pede o captcha ([p] pula, [s] encerra)")
                lembrete = None
        time.sleep(1)
    return None, None


def pausar(segundos):
    """Espera entre compras; devolve 's' se o usuário encerrar."""
    fim = time.time() + segundos
    while time.time() < fim:
        if tecla() == "s":
            return "s"
        time.sleep(0.2)
    return None


def confirmar_continuacao(falhas):
    print(f"  {falhas} compras seguidas sem zip: pode ser bloqueio ou desafio do captcha. "
          "Confira o navegador. [c] continua, [s] encerra")
    while True:
        t = tecla() if msvcrt else input("> ").strip().lower()
        if t in ("c", "s"):
            return t
        time.sleep(0.2)


def main():
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--de", default="2026-10", help="primeiro mês (o mais recente)")
    p.add_argument("--ate", default="2025-11", help="último mês (o mais antigo)")
    p.add_argument("--parte", type=parte, metavar="k/n", help="só a parte k de n das compras (divisão entre usuários)")
    p.add_argument("--repetir", action="store_true", help="reabre compras puladas ou sem zip em rodadas anteriores")
    p.add_argument("--auto", action="store_true",
                   help="o userscript navegador/compras_auto.user.js clica no download (instale no Tampermonkey)")
    p.add_argument("--intervalo", type=intervalo, default=(20.0, 60.0), metavar="MIN-MAX",
                   help="no --auto, segundos de espera aleatória entre compras (padrão 20-60)")
    p.add_argument("--max-falhas", type=int, default=3, metavar="N",
                   help="no --auto, pausa depois de N compras seguidas sem zip (padrão 3; 0 desliga)")
    args = p.parse_args()
    print(f"Vigiando downloads em: {DOWNLOADS}. Durante a espera: [p] pula, [s] encerra.")
    if args.auto:
        print("Modo --auto: o userscript navegador/compras_auto.user.js precisa estar ativo no navegador padrão, "
              "e o navegador não pode perguntar onde salvar cada arquivo.")

    abertas = 0
    falhas = 0
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

            linha = {"numeroControlePNCP": c["numeroControlePNCP"], "idCompra": c["idCompra"], "passada": "manual",
                     "situacao": "", "itens_cobertos": 0, "outros_guardados": 0}
            if not ID_COMPRA.fullmatch(c["idCompra"] or ""):
                # o site responde "compra não encontrada"; não vale abrir
                print(f"[{mes} {i}/{len(compras)}] {c['idCompra']!r}: idCompra inválido, pulando")
                anotar(mes, "manual", {**linha, "motivo": "idCompra inválido"})
                continue

            if args.auto and abertas:
                espera = random.uniform(*args.intervalo)
                if espera and pausar(espera) == "s":
                    print("Encerrado.")
                    return
            print(f"[{mes} {i}/{len(compras)}] {c['idCompra']} - {(c['objetoCompra'] or '')[:60]}")
            antes = zips_em_downloads(c["idCompra"])
            url = URL_COMPRA.format(c["idCompra"])
            if args.auto:
                for velho in avisos_em_downloads(c["idCompra"]):  # de uma rodada anterior
                    velho.unlink(missing_ok=True)
                url += "&pncpauto=1"
            webbrowser.open(url)
            abertas += 1
            arq, comando = esperar_zip(c["idCompra"], antes, args.auto)
            if comando == "s":
                print("Encerrado.")
                return
            if arq:
                destino.mkdir(parents=True, exist_ok=True)
                shutil.move(str(arq), destino / f"relatorios-compra-{c['idCompra']}.zip")
                manter_selecionados(destino)
                (destino / PARCIAL).unlink(missing_ok=True)
                escolhidos = selecionar(list(destino.rglob("*.pdf")))
                itens, sha = termos(escolhidos)
                baixado = "zip baixado (auto)" if args.auto else "zip baixado à mão"
                linha.update(situacao="completo" if escolhidos else "", itens_cobertos=len(escolhidos),
                             itens=itens, sha256=sha, motivo=baixado if escolhidos else "zip sem termos")
                print(f"  {len(escolhidos)} termo(s) -> {destino}")
                falhas = 0
            else:
                linha["motivo"] = ("pulada no site" if comando == "p"
                                   else comando if comando else "zip não recebido")
                print(f"  {linha['motivo']}")
                # sem a opção no site é resposta normal; o resto pode indicar bloqueio
                if comando in (None, MOTIVOS_AUTO["sem-botao"], MOTIVOS_AUTO["erro-download"],
                               MOTIVOS_AUTO["acesso-nao-autorizado"]):
                    falhas += 1
                else:
                    falhas = 0
            anotar(mes, "manual", linha)
            if args.auto and args.max_falhas and falhas >= args.max_falhas:
                if confirmar_continuacao(falhas) == "s":
                    print("Encerrado.")
                    return
                falhas = 0


if __name__ == "__main__":
    main()
