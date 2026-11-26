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
                             [--auto [--intervalo 20-60] [--max-falhas 3]] [--navegador chrome|edge|firefox]
                             [--modo aberto-fechado|fechado-aberto|aberto] [--crescente]

--modo fechado-aberto: baixa os pregões Fechado-Aberto (mesma seleção), com registro em
registro/fechado-aberto_<mês>/, lista em registro/compras_fechado-aberto/ e PDFs em
dados/filtrados/fechado-aberto_<mês>/relatorios/. O padrão é aberto-fechado.
--modo aberto: idem para os pregões Aberto, só Pregão Eletrônico (pastas aberto_<mês>).
--crescente: do mês mais antigo (--de) ao mais recente (--ate), ex.: --de 2022-11 --ate 2026-10.

Meses em paralelo: um terminal por mês, cada um com --navegador diferente (e o userscript instalado em
cada navegador). Todos vigiam a pasta Downloads, mas cada um só pega os arquivos das próprias compras.
Dois navegadores no mesmo mês: um com --parte 1/2, outro com --parte 2/2.

Ritmo: o registro é lido inteiro uma vez e depois só nas linhas novas; a pasta Downloads é olhada a cada
0,25 s; o zip recebido é aberto e anotado em segundo plano, enquanto a próxima compra já carrega.
"""
import argparse
import csv
import io
import os
import random
import re
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from config import DADOS
from extrator_homologacao.selecao import selecionar
import registro
from registro import MODOS, REGISTRO, _legados, anotar, compras_do_mes, na_parte, parte, termos, usar_modo
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
    "compra-anulada": "compra anulada no site",
    "compra-revogada": "compra revogada no site",
    "compra-cancelada": "compra cancelada no site",
    "sem-propostas": "compra sem propostas no site",
}
# situação da compra no texto da página (o aviso traz o texto): sem zip por definição, passa à próxima
SITUACAO_SEM_ZIP = [
    (re.compile(r"\bcompra anulada\b"), "compra-anulada"),
    (re.compile(r"\bcompra revogada\b"), "compra-revogada"),
    (re.compile(r"\bcompra cancelada\b"), "compra-cancelada"),
    (re.compile(r"não houve registro de proposta"), "sem-propostas"),
]
# --navegador: onde cada um costuma ficar no Windows (o primeiro que existir)
NAVEGADORES = {
    "chrome": [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
               r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
               r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"],
    "edge": [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
             r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"],
    "firefox": [r"C:\Program Files\Mozilla Firefox\firefox.exe",
                r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe"],
}
ID_COMPRA = re.compile(r"\d{17}")  # UASG (6) + modalidade (2) + número (5) + ano (4)
AVISO_DESAFIO = 60  # segundos sem zip no --auto antes de lembrar de olhar a aba (desafio do captcha)
PASSO = 0.25  # segundos entre olhadas na pasta Downloads
FIRME = 0.3  # segundos com o tamanho parado para dar o arquivo por gravado
ESCALONA = 1.0  # com --abas > 1, segundos mínimos entre abrir uma aba e a seguinte
ESPERA_AUTO = 2 * 60  # no --auto, segundos à espera do zip (no manual, ESPERA); o resto vai para --repetir


class Historico:
    """O registro compartilhado (registro.ler), lido aos poucos.

    Os arquivos do registro só crescem: na primeira vez cada um é lido inteiro, depois só os bytes
    novos, até a última linha completa (outro processo pode estar no meio de uma escrita). Reler tudo
    antes de cada compra custava ~1 s com 30 mil linhas, e crescia a cada mês.
    """

    def __init__(self):
        self.lido = {}  # arquivo -> (bytes já lidos, cabeçalho)
        self.completas = set()  # numeroControlePNCP com alguma linha 'completo'
        self.manuais = set()  # ... com alguma linha da passada 'manual'
        self.ultimo_motivo = {}  # ... -> motivo da linha mais recente lida

    def atualizar(self):
        for arquivo in sorted(REGISTRO.glob(f"{registro.MODO}_*/*.csv")) + _legados():
            pos, cabecalho = self.lido.get(arquivo, (0, None))
            try:
                if arquivo.stat().st_size <= pos:
                    continue
                with open(arquivo, "rb") as f:
                    f.seek(pos)
                    bruto = f.read()
            except OSError:
                continue
            fim = bruto.rfind(b"\n") + 1
            if not fim:
                continue
            texto = bruto[:fim].decode("utf-8", errors="replace")
            if pos == 0:
                texto = texto.lstrip("﻿")
            leitor = csv.reader(io.StringIO(texto))
            if cabecalho is None:
                cabecalho = next(leitor, None)
            for valores in leitor:
                l = dict(zip(cabecalho, valores))
                controle = l.get("numeroControlePNCP")
                if not controle:
                    continue  # linha quebrada
                if l.get("situacao") == "completo":
                    self.completas.add(controle)
                if l.get("passada") == "manual":
                    self.manuais.add(controle)
                self.ultimo_motivo[controle] = l.get("motivo", "")
            self.lido[arquivo] = (pos + fim, cabecalho)
        return self


def meses_decrescentes(de, ate):
    ano, mes = map(int, de.split("-"))
    while f"{ano}-{mes:02d}" >= ate:
        yield f"{ano}-{mes:02d}"
        ano, mes = (ano, mes - 1) if mes > 1 else (ano - 1, 12)


def meses_crescentes(de, ate):
    """De --de (o mais antigo) até --ate (o mais recente)."""
    ano, mes = map(int, de.split("-"))
    while f"{ano}-{mes:02d}" <= ate:
        yield f"{ano}-{mes:02d}"
        ano, mes = (ano, mes + 1) if mes < 12 else (ano + 1, 1)


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


def abridor(nome):
    """Função que abre uma URL: no navegador padrão ('padrao') ou no executável de --navegador."""
    if nome == "padrao":
        return webbrowser.open
    for caminho in NAVEGADORES[nome]:
        exe = Path(os.path.expandvars(caminho))
        if exe.exists():
            return lambda url: subprocess.Popen([str(exe), url])
    sys.exit(f"{nome} não encontrado em: {', '.join(NAVEGADORES[nome])}")


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
            if codigo == "sem-botao":  # userscript < 1.4: a situação só aparece no texto da página
                try:
                    texto = arq.read_text(encoding="utf-8", errors="replace").split("texto da página:", 1)[-1]
                except OSError:
                    texto = ""
                for padrao, situacao in SITUACAO_SEM_ZIP:
                    if padrao.search(texto.lower()):
                        return MOTIVOS_AUTO[situacao]
            return motivo
    return "aviso desconhecido do userscript"


def guardar_aviso(aviso):
    """Move o aviso (com o diagnóstico da página) para dados/avisos_auto/, fora da pasta Downloads."""
    pasta = DADOS / "avisos_auto"
    pasta.mkdir(parents=True, exist_ok=True)
    shutil.move(str(aviso), pasta / aviso.name.replace(" ", ""))


def gravado(arq, zip_=False):
    """O navegador terminou de gravar o arquivo? Chrome e Edge só dão o nome final no fim (antes é
    .crdownload); o Firefox cria o arquivo vazio e grava aos poucos, com um .part ao lado. Tamanho
    parado por FIRME segundos e, no zip, o diretório central legível (fica no fim do arquivo)."""
    try:
        tamanho = arq.stat().st_size
        if tamanho == 0 or Path(f"{arq}.part").exists():
            return False
        time.sleep(FIRME)
        return arq.stat().st_size == tamanho and (not zip_ or zipfile.is_zipfile(arq))
    except OSError:
        return False


def zip_atrasado(id_compra):
    """Zip desta compra que já está completo na pasta Downloads antes de abrir a página: no --auto, o
    tempo-limite (ESPERA_AUTO) anota "zip não recebido", mas o site às vezes entrega o zip minutos depois,
    e ele ficava esquecido lá. Arquivos vazios (o Firefox cria o nome antes de gravar) não contam."""
    for arq in sorted(zips_em_downloads(id_compra)):
        if gravado(arq, zip_=True):
            return arq
    return None


class Voo:
    """Compra com a aba aberta, à espera do zip ou do aviso do userscript."""

    def __init__(self, mes, i, n, c, destino, linha, espera):
        self.mes, self.i, self.n, self.c, self.destino, self.linha = mes, i, n, c, destino, linha
        self.id = c["idCompra"]
        self.antes = zips_em_downloads(self.id)
        self.limite = time.time() + espera
        self.lembrete = time.time() + AVISO_DESAFIO


def chegou(voo, auto):
    """(zip, None) quando o zip chega; no --auto, (None, motivo) quando o userscript avisa que a compra
    não tem zip; None enquanto nada chegou."""
    for arq in zips_em_downloads(voo.id) - voo.antes:
        if gravado(arq, zip_=True):
            return arq, None
    if auto:
        for aviso in avisos_em_downloads(voo.id):
            if gravado(aviso):
                motivo = motivo_do_aviso(aviso)
                guardar_aviso(aviso)
                return None, motivo
    return None


_trava = threading.Lock()  # o laço e o processamento em segundo plano escrevem no mesmo arquivo


def anotar_manual(mes, linha):
    with _trava:
        anotar(mes, "manual", linha)


def processar_zip(mes, destino, linha, auto):
    """Abre o zip já movido para a pasta da compra, guarda os termos escolhidos e anota (em segundo plano)."""
    try:
        manter_selecionados(destino)
        (destino / PARCIAL).unlink(missing_ok=True)
        escolhidos = selecionar(list(destino.rglob("*.pdf")))
        itens, sha = termos(escolhidos)
        baixado = "zip baixado (auto)" if auto else "zip baixado à mão"
        linha.update(situacao="completo" if escolhidos else "", itens_cobertos=len(escolhidos),
                     itens=itens, sha256=sha, motivo=baixado if escolhidos else "zip sem termos")
        anotar_manual(mes, linha)
        print(f"  {linha['idCompra']}: {len(escolhidos)} termo(s) -> {destino}")
    except Exception as e:  # sem anotar: a compra volta numa próxima rodada; o zip fica na pasta
        print(f"  {linha['idCompra']}: erro ao abrir o zip ({e!r}); ficou em {destino}")


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
    p.add_argument("--de", default="2026-10", help="primeiro mês (o mais recente; com --crescente, o mais antigo)")
    p.add_argument("--ate", default="2025-11", help="último mês (o mais antigo; com --crescente, o mais recente)")
    p.add_argument("--crescente", action="store_true",
                   help="anda do mês mais antigo (--de) para o mais recente (--ate), e na ordem crescente das compras")
    p.add_argument("--parte", type=parte, metavar="k/n", help="só a parte k de n das compras (divisão entre usuários)")
    p.add_argument("--repetir", action="store_true", help="reabre compras puladas ou sem zip em rodadas anteriores")
    p.add_argument("--motivo", metavar="TEXTO",
                   help='com --repetir, só reabre as compras cujo último motivo é este (ex.: "zip não recebido")')
    p.add_argument("--auto", action="store_true",
                   help="o userscript navegador/compras_auto.user.js clica no download (instale no Tampermonkey)")
    p.add_argument("--intervalo", type=intervalo, default=(20.0, 60.0), metavar="MIN-MAX",
                   help="no --auto, segundos de espera aleatória entre compras (padrão 20-60)")
    p.add_argument("--max-falhas", type=int, default=3, metavar="N",
                   help="no --auto, pausa depois de N compras seguidas sem zip (padrão 3; 0 desliga)")
    p.add_argument("--navegador", choices=["padrao", *NAVEGADORES], default="padrao",
                   help="navegador que abre as compras (padrão: o do sistema); permite rodar meses em paralelo, "
                        "um navegador por mês, todos baixando na pasta Downloads")
    p.add_argument("--abas", type=int, default=1, metavar="N",
                   help="no --auto, quantas compras ficam abertas ao mesmo tempo neste navegador (padrão 1)")
    p.add_argument("--modo", choices=list(MODOS), default="aberto-fechado",
                   help="modo de disputa das compras (padrão aberto-fechado); muda as pastas do registro e dos PDFs")
    args = p.parse_args()
    usar_modo(args.modo)
    if (args.de > args.ate) if args.crescente else (args.de < args.ate):
        p.error("com --crescente, --de é o mês mais antigo; sem ele, o mais recente")
    if args.motivo and not args.repetir:
        p.error("--motivo só vale junto com --repetir")
    if args.abas < 1 or (args.abas > 1 and not args.auto):
        p.error("--abas N precisa de N >= 1, e mais de uma aba só com --auto")
    abrir = abridor(args.navegador)
    print(f"Modo de disputa: {MODOS[args.modo]}. Vigiando downloads em: {DOWNLOADS}. "
          "Durante a espera: [p] pula, [s] encerra.")
    if args.auto:
        print("Modo --auto: o userscript navegador/compras_auto.user.js precisa estar ativo no navegador padrão, "
              "e o navegador não pode perguntar onde salvar cada arquivo.")

    # um só processamento de zip por vez em segundo plano: mantém a ordem das anotações e não disputa
    # a CPU com o navegador; ao sair (fim, [s] ou erro), o with espera os que faltam
    with ThreadPoolExecutor(max_workers=1) as fila:
        baixar(args, abrir, fila)


def pendentes(args, historico):
    """(mês, i, total, compra) na ordem do download: meses do mais recente ao mais antigo (ou o contrário,
    com --crescente)."""
    meses = meses_crescentes(args.de, args.ate) if args.crescente else meses_decrescentes(args.de, args.ate)
    for mes in meses:
        todas = compras_do_mes(mes)
        compras = [c for c in (todas if args.crescente else reversed(todas))
                   if na_parte(c["numeroControlePNCP"], args.parte)]
        if args.motivo:
            ultimo = historico.atualizar().ultimo_motivo
            compras = [c for c in compras if ultimo.get(c["numeroControlePNCP"]) == args.motivo]
        print(f"== {mes}: {len(compras)} compra(s)")
        for i, c in enumerate(compras, 1):
            yield mes, i, len(compras), c


def baixar(args, abrir, fila):
    """Mantém até --abas compras abertas ao mesmo tempo e recolhe o que chega na pasta Downloads.

    Com --abas 1 é o laço de sempre: abre, espera o zip, anota, abre a próxima."""
    historico = Historico()
    fonte = pendentes(args, historico)
    voando = []  # em ordem de abertura
    esgotou = False
    falhas = 0
    proxima = 0.0  # hora em que a próxima aba pode abrir
    while True:
        while not esgotou and len(voando) < args.abas and time.time() >= proxima:
            item = next(fonte, None)
            if item is None:
                esgotou = True
                break
            mes, i, n, c = item
            # atualizado a cada compra: o automático ou outro processo pode ter acabado de fazer esta
            historico.atualizar()
            controle = c["numeroControlePNCP"]
            if controle in historico.completas:
                continue
            destino = pasta_da_compra(c, DADOS / "filtrados" / f"{registro.MODO}_{mes}" / "relatorios")
            if resolvida(destino):
                continue
            linha = {"numeroControlePNCP": controle, "idCompra": c["idCompra"], "passada": "manual",
                     "situacao": "", "itens_cobertos": 0, "outros_guardados": 0}
            atrasado = ID_COMPRA.fullmatch(c["idCompra"] or "") and zip_atrasado(c["idCompra"])
            if atrasado:
                # chegou depois do tempo-limite numa rodada anterior ("zip não recebido"): usa sem reabrir
                print(f"[{mes} {i}/{n}] {c['idCompra']}: zip atrasado já em Downloads, sem abrir o site")
                destino.mkdir(parents=True, exist_ok=True)
                shutil.move(str(atrasado), destino / f"relatorios-compra-{c['idCompra']}.zip")
                fila.submit(processar_zip, mes, destino, linha, args.auto)
                continue
            if controle in historico.manuais and not args.repetir:
                continue
            if args.motivo and historico.ultimo_motivo.get(controle) != args.motivo:
                continue
            if not ID_COMPRA.fullmatch(c["idCompra"] or ""):
                # o site responde "compra não encontrada"; não vale abrir
                print(f"[{mes} {i}/{n}] {c['idCompra']!r}: idCompra inválido, pulando")
                anotar_manual(mes, {**linha, "motivo": "idCompra inválido"})
                continue
            print(f"[{mes} {i}/{n}] {c['idCompra']} - {(c['objetoCompra'] or '')[:60]}")
            url = URL_COMPRA.format(c["idCompra"])
            if args.auto:
                for velho in avisos_em_downloads(c["idCompra"]):  # de uma rodada anterior
                    velho.unlink(missing_ok=True)
                url += "&pncpauto=1"
            voando.append(Voo(mes, i, n, c, destino, linha, ESPERA_AUTO if args.auto else ESPERA))
            abrir(url)
            # entre uma aba e a seguinte: --intervalo; com várias abas, ao menos ESCALONA s
            proxima = time.time() + max(random.uniform(*args.intervalo) if args.auto else 0,
                                        ESCALONA if args.abas > 1 else 0)
        if esgotou and not voando:
            return

        t = tecla()
        if t == "s":
            print("Encerrado.")
            return
        resolvidos = []
        for voo in voando:
            r = chegou(voo, args.auto)
            if r is None and t == "p" and voo is voando[0]:
                r = (None, "p")  # [p] pula a mais antiga das abertas
            if r is None and time.time() > voo.limite:
                r = (None, None)
            if r is None:
                if args.auto and voo.lembrete and time.time() > voo.lembrete:
                    print(f"  {voo.id}: sem zip há {AVISO_DESAFIO} s: veja se a aba pede o captcha "
                          "([p] pula a mais antiga, [s] encerra)")
                    voo.lembrete = None
                continue
            resolvidos.append(voo)
            arq, comando = r
            if arq:
                voo.destino.mkdir(parents=True, exist_ok=True)
                shutil.move(str(arq), voo.destino / f"relatorios-compra-{voo.id}.zip")
                fila.submit(processar_zip, voo.mes, voo.destino, voo.linha, args.auto)  # anota quando terminar
                falhas = 0
                continue
            voo.linha["motivo"] = ("pulada no site" if comando == "p"
                                   else comando if comando else "zip não recebido")
            print(f"  {voo.id}: {voo.linha['motivo']}")
            # sem a opção no site é resposta normal; o resto pode indicar bloqueio
            if comando in (None, MOTIVOS_AUTO["sem-botao"], MOTIVOS_AUTO["erro-download"],
                           MOTIVOS_AUTO["acesso-nao-autorizado"]):
                falhas += 1
            else:
                falhas = 0
            anotar_manual(voo.mes, voo.linha)
        voando = [v for v in voando if v not in resolvidos]
        if args.auto and args.max_falhas and falhas >= args.max_falhas:
            if confirmar_continuacao(falhas) == "s":
                print("Encerrado.")
                return
            falhas = 0
        time.sleep(PASSO)


if __name__ == "__main__":
    main()
