"""Traz do PNCP, mês a mês, os pregões que a API Dados Abertos não tem (as demais plataformas).

Para cada mês de publicação: lista os pregões (Eletrônico e Presencial, todos os modos), descarta os
que já estão em dados/pncp.db e as contratações irmãs, baixa itens e resultados dos demais e carrega
tudo no banco numa única transação. Compra fica com compras.fonte = 'pncp'.

Os brutos ficam em dados/brutos_pncp/<ano>/, sem CSV, para `banco_unificado.py --recriar` não perder a
coleta. Pode ser interrompido: compras já baixadas não são baixadas de novo, e mês já carregado é
pulado. A lista do mês seguinte é baixada enquanto o mês atual busca os itens.

Uso: python coleta_pncp.py 2022-11 [2026-10] [--threads 3]
"""
import argparse
import calendar
import gzip
import json
import os
import shutil
import sqlite3
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import requests

from banco_unificado import (BRUTOS_PNCP, DESTINO, arquivos_pncp, carregar_mes_pncp, ler_jsonl_gz, preparar_pncp,
                             separar_novas)
from pncp_arquivos import API, MODALIDADES_PNCP, FalhaAPI, IndicePublicadas

LOTE = 200               # compras por bloco gravado no bruto
TAMANHO_ITENS = 500
MAX_FALHAS_ACEITAS = 50  # acima disso o problema é a API, e o mês não é carregado
ESPACO_MINIMO = 8 * 2**30

_local = threading.local()
_pausa = {"ate": 0.0}


def _obter(url, params=None):
    """Resposta 200/204, ou None se a contratação não existir. Um 429 pausa todas as threads."""
    if not hasattr(_local, "sessao"):
        _local.sessao = requests.Session()
        _local.sessao.headers.update({"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    for i in range(7):
        time.sleep(max(0, _pausa["ate"] - time.time()))
        try:
            r = _local.sessao.get(url, params=params, timeout=90)
            if r.status_code in (200, 204):
                return r
            if r.status_code == 404:
                return None
            if r.status_code == 429:
                espera = int(r.headers.get("Retry-After") or 30)
                _pausa["ate"] = max(_pausa["ate"], time.time() + espera)
                print(f"  PNCP pediu para esperar ({espera}s)", flush=True)
                continue
            if r.status_code not in (500, 502, 503, 504):
                return None
        except (requests.Timeout, requests.ConnectionError):
            pass
        time.sleep(2 ** i)
    raise FalhaAPI(url)


def _lista(r):
    return r.json() if r is not None and r.status_code == 200 and r.content else []


def detalhar(x):
    """Itens da compra, cada um com a lista dos seus resultados."""
    base = f"{API}/orgaos/{x['orgaoEntidade']['cnpj']}/compras/{x['anoCompra']}/{x['sequencialCompra']}"
    itens, pagina = [], 1
    while True:
        bloco = _lista(_obter(f"{base}/itens", {"pagina": pagina, "tamanhoPagina": TAMANHO_ITENS}))
        itens += bloco
        if len(bloco) < TAMANHO_ITENS:
            break
        pagina += 1
    for i in itens:
        if i.get("temResultado"):
            i["resultados"] = _lista(_obter(f"{base}/itens/{i['numeroItem']}/resultados"))
    return {"numeroControlePNCP": x["numeroControlePNCP"], "itens": itens}


def listar_mes(mes):
    """Grava a lista do mês, consultada dia a dia: o PNCP demora mais quanto mais funda a página (0,5 s na
    5ª, 3,8 s na 600ª), e um dia cabe em poucas dezenas de páginas. Repete o dia uma vez se vier menos
    que o totalRegistros."""
    arquivo, _ = arquivos_pncp(mes)
    if arquivo.exists():
        return
    ano, m = map(int, mes.split("-"))
    fim = calendar.monthrange(ano, m)[1]
    indice, registros, paginas = IndicePublicadas(), {}, 0
    for modalidade in MODALIDADES_PNCP:
        for dia in range(1, fim + 1):
            data = f"{ano}{m:02d}{dia:02d}"
            for _passada in range(2):
                pagina, total, recebidos = 1, 0, set()
                while True:
                    r = indice._pagina({"dataInicial": data, "dataFinal": data, "codigoModalidadeContratacao": modalidade,
                                        "pagina": pagina, "tamanhoPagina": 50})
                    paginas += 1
                    if paginas % 100 == 0:
                        print(f"  lista {mes}: {paginas} páginas, modalidade {modalidade}, dia {dia}/{fim}", flush=True)
                    time.sleep(indice.ESPERA_PAGINA)
                    if r.status_code == 204 or not r.content:
                        break
                    j = r.json()
                    total = j.get("totalRegistros") or 0
                    for x in j.get("data") or []:
                        registros[x["numeroControlePNCP"]] = x
                        recebidos.add(x["numeroControlePNCP"])
                    if pagina >= (j.get("totalPaginas") or 1):
                        break
                    pagina += 1
                if len(recebidos) >= total:
                    break
                print(f"  lista {mes}: modalidade {modalidade}, dia {dia} veio com {len(recebidos)} de {total}", flush=True)
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    temporario = arquivo.with_suffix(".tmp")
    with gzip.open(temporario, "wt", encoding="utf-8") as f:
        json.dump(list(registros.values()), f, ensure_ascii=False)
    os.replace(temporario, arquivo)


def _ja_baixadas(detalhes):
    """Compras do bruto. Se a última gravação foi cortada, refaz o arquivo só com as linhas boas."""
    if not detalhes.exists():
        return set()
    linhas = list(ler_jsonl_gz(detalhes))
    temporario = detalhes.with_suffix(".tmp")
    with gzip.open(temporario, "wt", encoding="utf-8") as f:
        for d in linhas:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    os.replace(temporario, detalhes)
    return {d["numeroControlePNCP"] for d in linhas}


def _gravar(detalhes, linhas):
    texto = "".join(json.dumps(d, ensure_ascii=False) + "\n" for d in linhas)
    detalhes.parent.mkdir(parents=True, exist_ok=True)
    with open(detalhes, "ab") as f:  # cada bloco é um membro gzip completo
        f.write(gzip.compress(texto.encode("utf-8")))


def _tentar(x):
    try:
        return x, detalhar(x)
    except FalhaAPI:
        return x, None


def baixar_detalhes(con, mes, threads):
    contratacoes, detalhes = arquivos_pncp(mes)
    with gzip.open(contratacoes, "rt", encoding="utf-8") as f:
        registros = json.load(f)
    novas, duplicadas, na_base = separar_novas(con, registros)
    feitas = _ja_baixadas(detalhes)
    pendentes = [x for x in novas if x["numeroControlePNCP"] not in feitas]
    print(f"{mes}: {len(registros)} no PNCP, {na_base} já na base, {len(duplicadas)} irmãs, {len(novas)} novas, "
          f"{len(pendentes)} a baixar", flush=True)
    inicio, total = time.time(), len(pendentes)
    with ThreadPoolExecutor(threads) as ex:
        for _tentativa in range(3):
            falhas = []
            for i in range(0, len(pendentes), LOTE):
                if shutil.disk_usage(contratacoes.parent).free < ESPACO_MINIMO:
                    sys.exit("Menos de 8 GB livres em disco: coleta interrompida; rode de novo para retomar.")
                resultado = list(ex.map(_tentar, pendentes[i:i + LOTE]))
                _gravar(detalhes, [d for _, d in resultado if d])
                falhas += [x for x, d in resultado if d is None]
                if (i // LOTE) % 10 == 9:
                    print(f"  {mes}: {i + LOTE}/{len(pendentes)} ({time.time() - inicio:.0f}s)", flush=True)
            pendentes = falhas
            if not pendentes:
                break
            print(f"  {mes}: {len(pendentes)} compra(s) falharam; nova tentativa", flush=True)
            time.sleep(60)
    if len(pendentes) > MAX_FALHAS_ACEITAS:
        sys.exit(f"{mes}: {len(pendentes)} compras falharam; mês não carregado. Rode de novo para retomar.")
    if total:
        print(f"  {mes}: {total} compras em {time.time() - inicio:.0f}s; sem itens por falha: {len(pendentes)}", flush=True)
    detalhes.with_name(f"itens_{mes}.completo").touch()


def meses_entre(inicio, fim):
    ano, mes = map(int, inicio.split("-"))
    while f"{ano}-{mes:02d}" <= fim:
        yield f"{ano}-{mes:02d}"
        ano, mes = ano + mes // 12, mes % 12 + 1


def main():
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("inicio", help="primeiro mês de publicação, ex.: 2022-11")
    p.add_argument("fim", nargs="?", help="último mês; sem ele, só o primeiro")
    p.add_argument("--threads", type=int, default=3)
    args = p.parse_args()

    BRUTOS_PNCP.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DESTINO, timeout=300)
    preparar_pncp(con)
    feitos = {x[0] for x in con.execute("SELECT mes FROM coleta_pncp_meses")}
    meses = [m for m in meses_entre(args.inicio, args.fim or args.inicio) if m not in feitos]
    print(f"{len(meses)} mês(es) a coletar", flush=True)
    with ThreadPoolExecutor(1) as listagem:
        proxima = listagem.submit(listar_mes, meses[0]) if meses else None
        for i, mes in enumerate(meses):
            proxima.result()
            if i + 1 < len(meses):
                proxima = listagem.submit(listar_mes, meses[i + 1])
            baixar_detalhes(con, mes, args.threads)
            print(carregar_mes_pncp(con, mes), flush=True)
    con.close()


if __name__ == "__main__":
    main()
