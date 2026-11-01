"""Coleta todos os pregões (codigoModalidade=5) de todos os órgãos, mês a mês, em dados/brutos/<ano>/.

Deduplica por numeroControlePNCP: idCompra se repete entre contratações distintas.
"""
import time
from datetime import date

import get

INICIO = date(2022, 11, 1)  # antes disso a API não tem pregões
hoje = date.today()


def buscar_mes(ini, prox):
    regs, total, pagina = {}, None, 1
    while True:
        j = get.get_json({
            "pagina": pagina, "tamanhoPagina": get.TAMANHO, "codigoModalidade": 5,
            "dataPublicacaoPncpInicial": ini.isoformat(), "dataPublicacaoPncpFinal": prox.isoformat(),
        })
        if j is None:
            raise RuntimeError(f"falha na página {pagina}")
        total = j.get("totalRegistros")
        for x in j.get("resultado") or []:
            regs[x["numeroControlePNCP"]] = x
        if not j.get("resultado") or j.get("paginasRestantes", 0) == 0:
            break
        pagina += 1
        time.sleep(0.3)
    return list(regs.values()), total


ini = INICIO
while ini <= hoje:
    prox = date(ini.year + (ini.month == 12), ini.month % 12 + 1, 1)  # data final da API é exclusiva
    nome = f"contratacoes_pregao_{ini:%Y-%m}"
    for tentativa in range(3):
        regs, total = buscar_mes(ini, prox)
        if len(regs) >= total:
            break
    if regs:
        get.salvar(regs, get.PASTA_BRUTOS / str(ini.year), nome)
    print(f"{nome}: salvo {len(regs)} | api {total}{'' if len(regs) >= total else '  <-- INCOMPLETO'}", flush=True)
    ini = prox
