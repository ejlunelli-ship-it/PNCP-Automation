"""Varre o PNCP atrás dos relatórios dos pregões Aberto-Fechado com item homologado em um mês.

Só usa a API pública: não abre navegador nem toca no captcha do Compras.gov.br. As compras vêm de
dados/pncp.db, pela data de resultado do item. Para cada uma, olha a própria contratação e as irmãs,
achadas no índice mensal de publicações (dados/pncp_publicadas/). Na primeira vez, montar o índice dos
meses de publicação leva mais tempo; depois ele é reaproveitado.

Cada compra entra em dados/filtrados/aberto-fechado_<mês>/motivos.csv assim que termina, então a
rodada pode ser interrompida e retomada. Compra já buscada em qualquer mês não é buscada de novo. No
fim, o inventário atualiza relatorios_pdf, busca_pdf e dados/pendentes_manual.csv.

Uso: python baixar_api.py 2026-01 [--sem-irmas] [--cnpj CNPJ] [--amostra-orgaos N] [--limite N]
"""
import argparse
import csv
import random
import re
import sqlite3
import sys
import time

from config import DADOS
from inventario_pdfs import atualizar as atualizar_inventario
from inventario_pdfs import ler_motivos
from pncp_arquivos import IndicePublicadas
from relatorios import pasta_da_compra, tentar_pncp

SEMENTE_AMOSTRA = 20260103  # fixa, para a amostra de órgãos ser reproduzível
COLUNAS = ["numeroControlePNCP", "idCompra", "passada", "situacao", "motivo", "itens_cobertos", "publicados",
           "candidatos", "outros_guardados", "erros"]
SELECAO = """
SELECT DISTINCT c.numero_controle_pncp AS numeroControlePNCP, c.id_compra AS idCompra,
       c.numero_compra AS numeroCompra, c.ano_compra AS anoCompraPncp, c.objeto_compra AS objetoCompra,
       c.data_publicacao AS dataPublicacaoPncp, c.data_abertura_proposta AS dataAberturaPropostaPncp,
       c.orgao_cnpj AS orgaoEntidadeCnpj
FROM compras c JOIN itens i USING (numero_controle_pncp)
WHERE i.registro_principal = 1 AND i.homologado = 1 AND c.modo_disputa = 'Aberto-Fechado'
  AND c.id_compra IS NOT NULL AND i.data_resultado LIKE ?
ORDER BY 1
"""


def compras_do_mes(mes):
    con = sqlite3.connect(f"file:{(DADOS / 'pncp.db').as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return [dict(r) for r in con.execute(SELECAO, (f"{mes}%",))]


def meses_ao_redor(ano_mes):
    """O mês e os vizinhos: a irmã costuma ser publicada perto da contratação."""
    ano, mes = map(int, ano_mes.split("-"))
    return [f"{ano + (mes + d - 1) // 12}-{(mes + d - 1) % 12 + 1:02d}" for d in (-1, 0, 1)]


def main():
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)  # progresso aparece mesmo em arquivo
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mes", help="mês do resultado, ex.: 2026-01")
    p.add_argument("--sem-irmas", action="store_true", help="olha só a própria contratação")
    p.add_argument("--cnpj", help="só as compras deste órgão")
    p.add_argument("--amostra-orgaos", type=int, metavar="N", help="só as compras de N órgãos sorteados (semente fixa)")
    p.add_argument("--limite", type=int, help="processa só as N primeiras compras pendentes")
    args = p.parse_args()
    if not re.fullmatch(r"\d{4}-\d{2}", args.mes):
        p.error("mês no formato AAAA-MM")

    pasta = DADOS / "filtrados" / f"aberto-fechado_{args.mes}"
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = pasta / "motivos.csv"
    passada = "propria" if args.sem_irmas else "irmas"
    # vale o histórico de todos os meses: compra já buscada não é buscada de novo
    historico = ler_motivos()
    feitas = {l["numeroControlePNCP"] for l in historico if l["motivo"] != "erro na API"
              and (l["passada"] == "irmas" or l["passada"] == passada or l["situacao"] == "completo")}

    compras = compras_do_mes(args.mes)
    total_mes = len(compras)
    if args.cnpj:
        compras = [c for c in compras if c["orgaoEntidadeCnpj"] == args.cnpj]
    if args.amostra_orgaos:
        orgaos = sorted({c["orgaoEntidadeCnpj"] for c in compras})
        sorteados = set(random.Random(SEMENTE_AMOSTRA).sample(orgaos, min(args.amostra_orgaos, len(orgaos))))
        compras = [c for c in compras if c["orgaoEntidadeCnpj"] in sorteados]
        print(f"Amostra: {len(sorteados)} de {len(orgaos)} órgãos, {len(compras)} compras")
    compras = [c for c in compras if c["numeroControlePNCP"] not in feitas]
    if args.limite:
        compras = compras[:args.limite]
    print(f"{args.mes}: {total_mes} compra(s) no mês, {len(compras)} a buscar (passada '{passada}')")

    indice = None
    if not args.sem_irmas:
        indice = IndicePublicadas()
        meses = sorted({m for c in compras for m in meses_ao_redor(c["dataPublicacaoPncp"][:7])})
        print(f"Índice de publicações: {len(meses)} mês(es)")
        for m in meses:
            indice.carregar(m)

    inicio = time.time()
    contagem = {}
    novo = not arquivo.exists()
    with open(arquivo, "a", newline="", encoding="utf-8-sig" if novo else "utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS)
        if novo:
            w.writeheader()
        for i, c in enumerate(compras, 1):
            situacao, busca = tentar_pncp(c, pasta_da_compra(c, pasta / "relatorios"), pasta / "outros_formatos",
                                          irmas=not args.sem_irmas, indice=indice)
            w.writerow({"numeroControlePNCP": c["numeroControlePNCP"], "idCompra": c["idCompra"], "passada": passada,
                        "situacao": situacao or "", "motivo": busca.motivo, "itens_cobertos": len(busca.cobertos),
                        "publicados": busca.publicados, "candidatos": busca.candidatos,
                        "outros_guardados": busca.guardados, "erros": " | ".join(busca.erros)})
            f.flush()
            contagem[busca.motivo] = contagem.get(busca.motivo, 0) + 1
            print(f"[{i}/{len(compras)}] {c['idCompra']} {busca.motivo} ({time.time() - inicio:.0f}s)")
    print("Resumo:", dict(sorted(contagem.items(), key=lambda x: -x[1])))
    atualizar_inventario()


if __name__ == "__main__":
    main()
