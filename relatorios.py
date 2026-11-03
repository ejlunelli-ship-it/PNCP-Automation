"""Organiza o zip "Todos os relatórios e termos" de cada compra do Compras.gov.br.

Antes, procura os termos no PNCP (pncp_arquivos.py): se o órgão os publicou lá para todos os
itens, a compra é baixada sem navegador nem captcha. Senão (ou se faltarem itens):
abre cada compra no navegador padrão (sem automação, então sem captcha extra).
Você clica em Downloads > "Todos os relatórios e termos"; o script detecta o zip
na pasta Downloads, move para a pasta da compra, extrai e abre a próxima.
Só um relatório por item é mantido (o termo de homologação ou, sem ele, o de julgamento
da última sessão); o zip e os demais relatórios são apagados.
"""
import argparse
import csv
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


PARCIAL = ".pncp_parcial"  # marca a pasta cujos termos do PNCP não cobrem todos os itens


def tentar_pncp(registro, destino, outros=None, irmas=True):
    """Baixa o que houver no PNCP. Devolve ('completo', 'parcial' ou None, Busca)."""
    from pncp_arquivos import baixar_do_pncp, quantidade_itens
    busca = baixar_do_pncp(registro, destino, outros, irmas)
    cobertos = busca.cobertos
    if not cobertos:
        return None, busca
    manter_selecionados(destino)  # julgamento sai quando o item tem termo de homologação
    total = quantidade_itens(registro)
    if total is not None and len(cobertos) < total:
        print(f"  PNCP cobre {len(cobertos)} de {total} itens; o resto precisa do zip (navegador)")
        (destino / PARCIAL).write_text(f"{len(cobertos)}/{total}\n", encoding="utf-8")
        return "parcial", busca
    (destino / PARCIAL).unlink(missing_ok=True)
    return "completo", busca


COLUNAS_PENDENTES = ["idCompra", "numeroControlePNCP", "numeroCompra", "anoCompraPncp",
                     "orgaoEntidadeRazaoSocial", "unidadeOrgaoCodigoUnidade", "unidadeOrgaoUfSigla",
                     "modoDisputaNomePncp", "motivo", "itens_no_pncp", "link_compra", "objetoCompra"]


def salvar_pendentes(pendentes, arquivo):
    """Grava (ou apaga, se vazia) a lista das compras sem relatório completo nesta rodada."""
    if not pendentes:
        arquivo.unlink(missing_ok=True)
        return
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    with open(arquivo, "w", newline="", encoding="utf-8-sig") as f:  # BOM: abre direto no Excel
        w = csv.DictWriter(f, fieldnames=COLUNAS_PENDENTES, extrasaction="ignore")
        w.writeheader()
        w.writerows(pendentes)


def baixar_relatorios(registros, pasta_base, usar_pncp=True, so_pncp=False):
    """Baixa os relatórios das compras e grava <pasta>/pendentes.csv com as que ficaram sem eles."""
    pasta_base = Path(pasta_base)
    if not so_pncp:
        print(f"Vigiando downloads em: {DOWNLOADS}")
    ok = 0
    pendentes = []

    def pendente(r, destino, motivo):
        marca = destino / PARCIAL
        pendentes.append({**r, "motivo": motivo,
                          "itens_no_pncp": marca.read_text(encoding="utf-8").strip() if marca.exists() else "",
                          "link_compra": URL_COMPRA.format(r["idCompra"])})

    for i, r in enumerate(registros, 1):
        destino = pasta_da_compra(r, pasta_base)
        print(f"[{i}/{len(registros)}] {r['idCompra']} - {r['objetoCompra'][:60]}")
        parcial = (destino / PARCIAL).exists()
        if (destino.exists() and not parcial
                and (selecionar(list(destino.rglob("*.pdf"))) or any(destino.glob("*.zip")))):
            print("  já baixado, pulando")
            manter_selecionados(destino)
            ok += 1
            continue
        # sem resultado homologado o site não oferece "Todos os relatórios e termos"
        if not r.get("existeResultado") and not r.get("valorTotalHomologado"):
            print("  ainda não homologada (sem relatórios), pulando")
            pendente(r, destino, "ainda não homologada")
            continue

        situacao, busca = ("parcial" if parcial else None), None
        if (usar_pncp or so_pncp) and not parcial:
            situacao, busca = tentar_pncp(r, destino, pasta_base.parent / "outros_formatos")
            if situacao == "completo":
                print(f"  baixado do PNCP -> {destino}")
                ok += 1
                continue
        motivo = ("PNCP não consultado" if not (usar_pncp or so_pncp)
                  else "termos incompletos no PNCP" if situacao == "parcial"
                  else busca.motivo)
        if so_pncp:
            print(f"  {motivo}; falta o zip")
            pendente(r, destino, motivo)
            continue

        antes = zips_em_downloads(r["idCompra"])
        webbrowser.open(URL_COMPRA.format(r["idCompra"]))
        print("  no navegador: Downloads > 'Todos os relatórios e termos' "
              f"(aguardando até {ESPERA // 60} min; se não tiver a opção, só esperar)")

        arq = esperar_novo_zip(r["idCompra"], antes)
        if not arq:
            print("  nenhum zip recebido, pulando")
            pendente(r, destino, f"{motivo}; zip não recebido no navegador")
            continue

        destino.mkdir(parents=True, exist_ok=True)
        # nome limpo, sem o " (n)" que o navegador adiciona em downloads repetidos
        shutil.move(str(arq), destino / f"relatorios-compra-{r['idCompra']}.zip")
        manter_selecionados(destino)
        (destino / PARCIAL).unlink(missing_ok=True)
        print(f"  {arq.name} -> {destino}")
        ok += 1

    arquivo = pasta_base.parent / "pendentes.csv"
    salvar_pendentes(pendentes, arquivo)
    print(f"Relatórios organizados: {ok}/{len(registros)}")
    if pendentes:
        print(f"Pendentes: {len(pendentes)} -> {arquivo}"
              + (" (rode sem --so-pncp para pedir os zips no navegador)" if so_pncp else ""))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Baixa os relatórios de cada compra: do PNCP quando houver, senão pelo navegador.")
    ap.add_argument("origens", nargs="*", type=Path, metavar="contratacoes_<pasta>.json",
                    help="sem argumento: dados/filtrados/pregao_*/contratacoes_*.json")
    grupo = ap.add_mutually_exclusive_group()
    grupo.add_argument("--so-pncp", action="store_true", help="só baixa do PNCP, sem abrir o navegador")
    grupo.add_argument("--sem-pncp", action="store_true", help="não consulta o PNCP (só navegador, como antes)")
    args = ap.parse_args()
    origens = args.origens or sorted((DADOS / "filtrados").glob("pregao_*/contratacoes_*.json"))
    for origem in origens:
        print(f"== {origem.parent.name}")
        with open(origem, encoding="utf-8") as f:
            registros = json.load(f)
        baixar_relatorios(registros, origem.parent / "relatorios",
                          usar_pncp=not args.sem_pncp, so_pncp=args.so_pncp)
