"""Resultados dos itens de pregão: dados/brutos/<ano>/resultados_pregao_<ano>-<mês>.json.

Usa 3_consultarResultadoItensContratacoes_PNCP_14133, dia a dia pela data de resultado (nesta
consulta a data final é INCLUSIVA) e mantém só as compras de dados/pncp.db. Traz um registro por
sequencialResultado, com a situação (Informado ou Cancelado), o que a consulta de itens não separa.

A API repete linhas idênticas e o totalRegistros conta as repetições, então a conferência é pelas
linhas recebidas. Mês com falha não é gravado e é refeito na próxima execução; meses gravados são
pulados, exceto o corrente. 3 meses em paralelo.

Depois da coleta, carregue no banco: python banco_unificado.py --resultados
"""
import json
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import get
from config import DADOS

URL = "https://dadosabertos.compras.gov.br/modulo-contratacoes/3_consultarResultadoItensContratacoes_PNCP_14133"
INICIO = date(2022, 11, 1)
hoje = date.today()
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

con = sqlite3.connect(f"file:{(DADOS / 'pncp.db').as_posix()}?mode=ro", uri=True)
pregoes = {x[0] for x in con.execute("SELECT numero_controle_pncp FROM compras")}
con.close()
print(f"{len(pregoes)} pregões de referência")


def buscar_dia(dia):
    """(registros do dia sem repetição, total da API, consulta completa?)."""
    for tentativa in range(5):
        regs, total, linhas, pagina = {}, None, 0, 1
        while True:
            j = get.get_json({"pagina": pagina, "tamanhoPagina": get.TAMANHO, "dataResultadoPncpInicial": dia.isoformat(),
                              "dataResultadoPncpFinal": dia.isoformat()}, url=URL)
            if j is None:
                break
            total = j.get("totalRegistros")
            linhas += len(j.get("resultado") or [])
            for x in j.get("resultado") or []:
                regs[(x.get("numeroControlePNCPCompra"), x.get("numeroItemPncp"), x.get("sequencialResultado"))] = x
            if not j.get("resultado") or j.get("paginasRestantes", 0) == 0:
                break
            pagina += 1
            time.sleep(0.2)
        if total is not None and linhas >= total:
            return list(regs.values()), total, True
        time.sleep(10 * (tentativa + 1))
    return list(regs.values()), total, False


def mes(ini):
    prox = date(ini.year + (ini.month == 12), ini.month % 12 + 1, 1)
    pasta, nome = get.PASTA_BRUTOS / str(ini.year), f"resultados_pregao_{ini:%Y-%m}"
    if (pasta / f"{nome}.json").exists() and prox <= hoje:
        return f"{nome}: já existe, pulando"
    resultados, todos, falhas, dia = [], 0, [], ini
    while dia < min(prox, hoje + timedelta(days=1)):
        regs, total, ok = buscar_dia(dia)
        todos += len(regs)
        resultados += [x for x in regs if x.get("numeroControlePNCPCompra") in pregoes]
        if not ok:
            falhas.append(f"{dia} ({len(regs)} registros, total {total})")
        dia += timedelta(days=1)
    if falhas:
        return f"{nome}: NÃO GRAVADO, refazer: {', '.join(falhas)}"
    pasta.mkdir(parents=True, exist_ok=True)
    with open(pasta / f"{nome}.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False)
    return f"{nome}: {len(resultados)} resultados de pregão (de {todos} no mês)"


meses = []
m = INICIO
while m <= hoje:
    meses.append(m)
    m = date(m.year + (m.month == 12), m.month % 12 + 1, 1)

with ThreadPoolExecutor(3) as ex:
    for linha in ex.map(mes, reversed(meses)):
        print(linha, flush=True)
