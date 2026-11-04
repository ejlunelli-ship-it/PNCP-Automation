"""Itens dos pregões já coletados (dados/brutos/<ano>/contratacoes_pregao_*.json).

Usa a consulta por período (2_consultarItensContratacoes_PNCP_14133, data de inclusão do item,
data final exclusiva), dia a dia, e mantém só os itens cuja compra está nos pregões coletados.
Grava por mês de inclusão do item em dados/brutos/<ano>/itens_pregao_<ano>-<mês>.json/.csv.
Meses já gravados são pulados (exceto o mês corrente). 3 meses em paralelo.
"""
import glob
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import get

URL = "https://dadosabertos.compras.gov.br/modulo-contratacoes/2_consultarItensContratacoes_PNCP_14133"
INICIO = date(2022, 11, 1)
hoje = date.today()

pregoes = set()
for f in glob.glob(str(get.PASTA_BRUTOS / "20*" / "contratacoes_pregao_*.json")):
    pregoes.update(x["numeroControlePNCP"] for x in json.load(open(f, encoding="utf-8")))
print(f"{len(pregoes)} pregões de referência", flush=True)


def buscar_dia(dia):
    """Todos os itens incluídos no dia (todas as modalidades).

    A API repete linhas idênticas e o totalRegistros conta as repetições, então a conferência
    é pelas linhas recebidas (antes de deduplicar); falta de linhas = página que falhou.
    """
    for tentativa in range(5):
        itens, total, linhas, pagina = {}, None, 0, 1
        while True:
            j = get.get_json({"pagina": pagina, "tamanhoPagina": get.TAMANHO,
                              "dataInclusaoPncpInicial": dia.isoformat(),
                              "dataInclusaoPncpFinal": (dia + timedelta(days=1)).isoformat()}, url=URL)
            if j is None:
                break
            total = j.get("totalRegistros")
            linhas += len(j.get("resultado") or [])
            for x in j.get("resultado") or []:
                # fornecedor e valor na chave: um item pode ter mais de um resultado
                itens[(x.get("numeroControlePNCPCompra"), x.get("numeroItemPncp"), x.get("idCompraItem"),
                       x.get("codFornecedor"), x.get("valorUnitarioResultado"))] = x
            if not j.get("resultado") or j.get("paginasRestantes", 0) == 0:
                break
            pagina += 1
            time.sleep(0.2)
        if total is not None and linhas >= total:
            return list(itens.values()), total, True
        time.sleep(10 * (tentativa + 1))
    return list(itens.values()), total, False


def salvar(registros, pasta, nome):
    pasta.mkdir(parents=True, exist_ok=True)
    with open(pasta / f"{nome}.json", "w", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False)
    import pandas as pd
    pd.DataFrame(registros).to_csv(pasta / f"{nome}.csv", index=False, encoding="utf-8-sig")


def mes(ini):
    prox = date(ini.year + (ini.month == 12), ini.month % 12 + 1, 1)
    pasta, nome = get.PASTA_BRUTOS / str(ini.year), f"itens_pregao_{ini:%Y-%m}"
    if (pasta / f"{nome}.json").exists() and prox <= hoje:
        return f"{nome}: já existe, pulando"
    itens, todos, falhas, dia = [], 0, [], ini
    while dia < min(prox, hoje + timedelta(days=1)):
        regs, total, ok = buscar_dia(dia)
        todos += len(regs)
        itens += [x for x in regs if x.get("numeroControlePNCPCompra") in pregoes]
        if not ok:
            falhas.append(f"{dia} ({len(regs)} itens, total {total})")
        dia += timedelta(days=1)
    if itens:
        salvar(itens, pasta, nome)
    aviso = f"  <-- INCOMPLETO: {', '.join(falhas)}" if falhas else ""
    return f"{nome}: {len(itens)} itens de pregão (de {todos} itens no mês){aviso}"


meses = []
m = INICIO
while m <= hoje:
    meses.append(m)
    m = date(m.year + (m.month == 12), m.month % 12 + 1, 1)

with ThreadPoolExecutor(3) as ex:
    for linha in ex.map(mes, meses):
        print(linha, flush=True)
