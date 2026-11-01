"""Lista os órgãos que publicaram pregões (Lei 14.133) no Compras.gov.br no período.

Consulta a mesma API do get.py sem filtrar CNPJ, mês a mês, e agrega por órgão. Gera
dados/orgaos/orgaos.txt (um CNPJ por linha, pronto para `get.py --orgaos dados/orgaos/orgaos.txt`)
e orgaos.csv com os detalhes; só entram órgãos com pelo menos MINIMO pregões. Cada mês concluído
fica em orgaos.parcial.json, então uma execução interrompida continua de onde parou.
"""
import argparse
import csv
import json
import sys
import time
from collections import Counter
from datetime import date, timedelta

from config import DADOS
from get import DIAS_PADRAO, MODALIDADES, TAMANHO, get_json

MINIMO = 5  # pregões no período para o órgão entrar na lista
PASTA = DADOS / "orgaos"

sys.stdout.reconfigure(encoding="utf-8")


def meses(inicio, fim):
    """Intervalos [início, fim] de cada mês civil dentro do período."""
    atual = inicio
    while atual <= fim:
        proximo = (atual.replace(day=1) + timedelta(days=32)).replace(day=1)
        yield atual, min(fim, proximo - timedelta(days=1))
        atual = proximo


def buscar_periodo(cod, inicio, fim):
    """Contratações de todo o país na modalidade/período; None se alguma página falhar."""
    registros, pagina = {}, 1
    while True:
        j = get_json({
            "pagina": pagina,
            "tamanhoPagina": TAMANHO,
            "dataPublicacaoPncpInicial": inicio.isoformat(),
            "dataPublicacaoPncpFinal": fim.isoformat(),
            "codigoModalidade": cod,
        })
        if j is None:
            return None
        resultado = j.get("resultado") or []
        for r in resultado:
            registros[r["numeroControlePNCP"]] = r  # idCompra se repete entre contratações distintas
        print(f"  pág {pagina}/{j.get('totalPaginas')}: {len(registros)}/{j.get('totalRegistros')}")
        if not resultado or j.get("paginasRestantes", 0) == 0 or pagina >= j.get("totalPaginas", pagina):
            return list(registros.values())
        pagina += 1
        time.sleep(0.3)


def resumir(registros):
    """Só o necessário por contratação, para o checkpoint não crescer demais."""
    return {r["numeroControlePNCP"]: {
        "cnpj": r.get("orgaoEntidadeCnpj"),
        "nome": r.get("orgaoEntidadeRazaoSocial"),
        "esfera": r.get("orgaoEntidadeEsferaId"),
        "poder": r.get("orgaoEntidadePoderId"),
        "uf": r.get("unidadeOrgaoUfSigla"),
        "municipio": r.get("unidadeOrgaoMunicipioNome"),
        "modo": r.get("modoDisputaNomePncp") or "Não se aplica",
        "homologada": bool(r.get("existeResultado") or r.get("valorTotalHomologado")),
    } for r in registros}


def agregar(contratacoes):
    orgaos = {}
    for c in contratacoes.values():
        o = orgaos.setdefault(c["cnpj"], {
            "cnpj": c["cnpj"], "nome": c["nome"], "esfera": c["esfera"], "poder": c["poder"],
            "ufs": Counter(), "municipios": Counter(), "modos": Counter(), "contratacoes": 0, "homologadas": 0,
        })
        o["contratacoes"] += 1
        o["homologadas"] += c["homologada"]
        o["ufs"][c["uf"]] += 1
        o["municipios"][f"{c['municipio']}/{c['uf']}"] += 1
        o["modos"][c["modo"]] += 1
    return sorted(orgaos.values(), key=lambda o: (-o["contratacoes"], o["nome"] or ""))


def salvar(orgaos, inicio, fim, modalidades, minimo):
    modos = sorted({m for o in orgaos for m in o["modos"]})
    with open(PASTA / "orgaos.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["cnpj", "nome", "esfera", "poder", "uf", "municipio", "contratacoes", "homologadas"]
                   + [f"modo: {m}" for m in modos])
        for o in orgaos:
            w.writerow([o["cnpj"], o["nome"], o["esfera"], o["poder"],
                        o["ufs"].most_common(1)[0][0], o["municipios"].most_common(1)[0][0],
                        o["contratacoes"], o["homologadas"]] + [o["modos"][m] for m in modos])
    with open(PASTA / "orgaos.txt", "w", encoding="utf-8") as f:
        f.write(f"# órgãos com {minimo}+ pregões | modalidades {modalidades} | {inicio} a {fim}\n")
        f.write("# CNPJ  # contratações | homologadas | município | nome\n")
        for o in orgaos:
            f.write(f"{o['cnpj']}  # {o['contratacoes']} | {o['homologadas']} | "
                    f"{o['municipios'].most_common(1)[0][0]} | {o['nome']}\n")


def main():
    ap = argparse.ArgumentParser(description=f"Lista os órgãos com {MINIMO}+ pregões no período (Brasil todo).")
    ap.add_argument("--inicio", type=date.fromisoformat, help=f"data inicial AAAA-MM-DD (padrão: hoje - {DIAS_PADRAO} dias)")
    ap.add_argument("--fim", type=date.fromisoformat, default=date.today(), help="data final AAAA-MM-DD (padrão: hoje)")
    args = ap.parse_args()
    args.inicio = args.inicio or args.fim - timedelta(days=DIAS_PADRAO)
    if args.inicio > args.fim:
        ap.error("--inicio maior que --fim")

    PASTA.mkdir(parents=True, exist_ok=True)
    parcial = PASTA / "orgaos.parcial.json"
    feitos = json.loads(parcial.read_text(encoding="utf-8")) if parcial.exists() else {}

    falhas = []
    for cod in MODALIDADES:
        for ini, fim in meses(args.inicio, args.fim):
            chave = f"{cod}|{ini}|{fim}"
            if chave in feitos:
                continue
            print(f"== modalidade {cod} | {ini} a {fim}")
            registros = buscar_periodo(cod, ini, fim)
            if registros is None:
                print("  falhou; rode de novo para tentar este mês")
                falhas.append(chave)
                continue
            feitos[chave] = resumir(registros)
            parcial.write_text(json.dumps(feitos, ensure_ascii=False), encoding="utf-8")

    contratacoes = {}
    for cod in MODALIDADES:
        for ini, fim in meses(args.inicio, args.fim):
            contratacoes.update(feitos.get(f"{cod}|{ini}|{fim}", {}))
    todos = agregar(contratacoes)
    orgaos = [o for o in todos if o["contratacoes"] >= MINIMO]
    salvar(orgaos, args.inicio, args.fim, MODALIDADES, MINIMO)

    print(f"{len(contratacoes)} contratações, {len(todos)} órgãos; {len(orgaos)} com {MINIMO}+ "
          f"-> {PASTA / 'orgaos.txt'}")
    if falhas:
        print(f"ATENÇÃO: {len(falhas)} mês(es) falharam, lista incompleta: {', '.join(falhas)}")


if __name__ == "__main__":
    main()
