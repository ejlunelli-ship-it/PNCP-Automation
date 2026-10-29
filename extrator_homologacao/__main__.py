"""CLI: python -m extrator_homologacao [pasta] [--saida arquivo.xlsx] ..."""

import argparse
import logging
import sys
from pathlib import Path

from config import DADOS

from . import VERSAO_PARSER
from .excel import gerar_excel
from .lote import descobrir_pdfs, processar_lote
from .selecao import selecionar
from .sqlite import gravar_sqlite

PASTA_PADRAO = DADOS / "filtrados"
SAIDA_PADRAO = DADOS / "extracao" / "homologacoes.xlsx"


def configurar_log(arquivo):
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    formato = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    raiz = logging.getLogger()
    raiz.setLevel(logging.INFO)
    em_arquivo = logging.FileHandler(arquivo, encoding="utf-8")
    em_arquivo.setFormatter(formato)
    no_console = logging.StreamHandler()
    no_console.setLevel(logging.WARNING)
    no_console.setFormatter(formato)
    raiz.addHandler(em_arquivo)
    raiz.addHandler(no_console)


def pasta_de(pdf, raiz):
    """Primeira subpasta abaixo da raiz (ex.: 'pregao_aberto-fechado'); None se o PDF estiver na raiz."""
    partes = Path(pdf).relative_to(raiz).parts
    return partes[0] if len(partes) > 1 else None


def main(argv=None):
    ap = argparse.ArgumentParser(description="Extrai campos dos relatórios de julgamento/homologação para Excel.")
    ap.add_argument("pasta", nargs="?", default=PASTA_PADRAO, type=Path, help=f"pasta com os PDFs (padrão: {PASTA_PADRAO})")
    ap.add_argument("--saida", default=SAIDA_PADRAO, type=Path, help=f"arquivo Excel (padrão: {SAIDA_PADRAO})")
    ap.add_argument("--padrao", default="*.pdf", help='glob dos arquivos, ex.: "relatorio-termo-homologacao-*.pdf"')
    ap.add_argument("--todos", action="store_true",
                    help="processa todos os PDFs; sem ela, um relatório por item (homologação ou, sem ela, "
                         "o julgamento da última sessão)")
    ap.add_argument("--reprocessar", action="store_true", help="ignora o cache e extrai todos os PDFs novamente")
    ap.add_argument("--sem-ocr", action="store_true", help="não tenta OCR em PDFs sem camada de texto")
    ap.add_argument("--workers", type=int, default=1, help="processos paralelos (padrão: 1)")
    ap.add_argument("--sem-separar", action="store_true",
                    help="gera só o Excel consolidado, sem um Excel por subpasta")
    ap.add_argument("--db", type=Path,
                    help="banco SQLite, uma linha por item (padrão: --saida com extensão .db)")
    args = ap.parse_args(argv)

    configurar_log(args.saida.with_suffix(".log"))
    log = logging.getLogger("extrator_homologacao")
    log.info("início - versão do parser %s - pasta %s", VERSAO_PARSER, args.pasta)

    pdfs = descobrir_pdfs(args.pasta, args.padrao)
    if not args.todos:
        pdfs = selecionar(pdfs)
    if not pdfs:
        print(f"Nenhum PDF encontrado em {args.pasta} ({args.padrao})")
        return 1

    registros = processar_lote(
        pdfs,
        cache_path=args.saida.with_name(args.saida.stem + ".cache.json"),
        reprocessar=args.reprocessar,
        ocr=not args.sem_ocr,
        workers=args.workers,
    )
    registros = [r.model_copy(update={"pasta": pasta_de(p, args.pasta)}) for r, p in zip(registros, pdfs)]
    gerar_excel(registros, args.saida)

    # o banco tem uma linha por item; com --todos haveria vários relatórios por item
    db = args.db or args.saida.with_suffix(".db")
    if args.todos:
        print(f"--todos: SQLite não atualizado ({db})")
    else:
        gravados, ignorados = gravar_sqlite(registros, db)
        sem_chave = f", {ignorados} sem uasg/compra/item ignorado(s)" if ignorados else ""
        log.info("sqlite - %d item(ns) gravado(s)%s - %s", gravados, sem_chave, db)
        print(f"SQLite: {gravados} item(ns) gravado(s){sem_chave} -> {db}")

    # um Excel por subpasta (ex.: dados/extracao/pregao_aberto-fechado.xlsx)
    if not args.sem_separar:
        por_pasta = {}
        for r in registros:
            if r.pasta:
                por_pasta.setdefault(r.pasta, []).append(r)
        for nome, regs in sorted(por_pasta.items()):
            destino = gerar_excel(regs, args.saida.with_name(f"{nome}.xlsx"))
            print(f"  {nome}: {len(regs)} PDF(s) -> {destino}")

    contagem = {}
    for r in registros:
        contagem[r.status_extracao] = contagem.get(r.status_extracao, 0) + 1
    resumo = ", ".join(f"{s}: {n}" for s, n in sorted(contagem.items()))
    log.info("fim - %d PDF(s) - %s - %s", len(registros), resumo, args.saida)
    print(f"{len(registros)} PDF(s) processados ({resumo}) -> {args.saida}")
    print(f"Log: {args.saida.with_suffix('.log')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
