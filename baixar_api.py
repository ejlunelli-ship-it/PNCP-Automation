"""Baixa pelo PNCP os relatórios dos pregões Aberto-Fechado com item homologado em um mês.

Só usa a API pública: não abre navegador nem toca no captcha do Compras.gov.br. As compras vêm de
dados/pncp.db, pela data de resultado do item, e cada uma entra em
dados/filtrados/aberto-fechado_<mês>/motivos.csv assim que termina, então a rodada pode ser
interrompida e retomada.

A 1ª passada olha só a própria contratação, que é rápida. Com --irmas, a 2ª passada busca as
contratações irmãs das compras ainda sem termos; é bem mais lenta, pois lista os pregões do órgão.

Uso: python baixar_api.py 2026-01 [--irmas] [--limite N]
"""
import argparse
import csv
import re
import sqlite3
import sys
import time

from config import DADOS
from relatorios import pasta_da_compra, tentar_pncp

COLUNAS = ["numeroControlePNCP", "idCompra", "passada", "situacao", "motivo", "itens_cobertos", "publicados",
           "candidatos", "outros_guardados", "erros"]
SELECAO = """
SELECT DISTINCT c.numero_controle_pncp AS numeroControlePNCP, c.id_compra AS idCompra,
       c.numero_compra AS numeroCompra, c.ano_compra AS anoCompraPncp, c.objeto_compra AS objetoCompra,
       c.data_publicacao AS dataPublicacaoPncp, c.data_abertura_proposta AS dataAberturaPropostaPncp
FROM compras c JOIN itens i USING (numero_controle_pncp)
WHERE i.registro_principal = 1 AND i.homologado = 1 AND c.modo_disputa = 'Aberto-Fechado'
  AND i.data_resultado LIKE ?
ORDER BY 1
"""


def compras_do_mes(mes):
    con = sqlite3.connect(f"file:{(DADOS / 'pncp.db').as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return [dict(r) for r in con.execute(SELECAO, (f"{mes}%",))]


def ler_motivos(arquivo):
    if not arquivo.exists():
        return []
    with open(arquivo, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main():
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)  # progresso aparece mesmo em arquivo
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mes", help="mês do resultado, ex.: 2026-01")
    p.add_argument("--irmas", action="store_true", help="2ª passada: busca as irmãs das compras ainda sem termos")
    p.add_argument("--limite", type=int, help="processa só as N primeiras compras pendentes")
    args = p.parse_args()
    if not re.fullmatch(r"\d{4}-\d{2}", args.mes):
        p.error("mês no formato AAAA-MM")

    pasta = DADOS / "filtrados" / f"aberto-fechado_{args.mes}"
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = pasta / "motivos.csv"
    passada = "irmas" if args.irmas else "propria"
    historico = ler_motivos(arquivo)
    # o último registro de cada compra vale; erro na API é refeito ao retomar
    ultimo = {l["numeroControlePNCP"]: l for l in historico}
    feitas = {l["numeroControlePNCP"] for l in historico if l["passada"] == passada and l["motivo"] != "erro na API"}

    compras = [c for c in compras_do_mes(args.mes) if c["numeroControlePNCP"] not in feitas]
    if args.irmas:
        compras = [c for c in compras if ultimo.get(c["numeroControlePNCP"], {}).get("situacao") != "completo"]
    if args.limite:
        compras = compras[:args.limite]
    print(f"{len(compras)} compra(s) a processar na passada '{passada}'")

    inicio = time.time()
    contagem = {}
    with open(arquivo, "a", newline="", encoding="utf-8-sig" if not historico else "utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS)
        if not historico:
            w.writeheader()
        for i, c in enumerate(compras, 1):
            situacao, busca = tentar_pncp(c, pasta_da_compra(c, pasta / "relatorios"), pasta / "outros_formatos",
                                          irmas=args.irmas)
            w.writerow({"numeroControlePNCP": c["numeroControlePNCP"], "idCompra": c["idCompra"], "passada": passada,
                        "situacao": situacao or "", "motivo": busca.motivo, "itens_cobertos": len(busca.cobertos),
                        "publicados": busca.publicados, "candidatos": busca.candidatos,
                        "outros_guardados": busca.guardados, "erros": " | ".join(busca.erros)})
            f.flush()
            contagem[busca.motivo] = contagem.get(busca.motivo, 0) + 1
            print(f"[{i}/{len(compras)}] {c['idCompra']} {busca.motivo} ({time.time() - inicio:.0f}s)")
    print("Resumo:", dict(sorted(contagem.items(), key=lambda x: -x[1])))


if __name__ == "__main__":
    main()
