import argparse
import json
import re
import time
import unicodedata
from datetime import date, timedelta
from pathlib import Path

import requests

from config import DADOS

URL = "https://dadosabertos.compras.gov.br/modulo-contratacoes/1_consultarContratacoes_PNCP_14133"
TAMANHO = 500

# padrões da linha de comando
ORGAOS_PADRAO = ["08778326000156"]  # Prefeitura Municipal de João Pessoa
DIAS_PADRAO = 365                  # período: último ano até hoje
MODALIDADES = [5]  # só Pregão (Eletrônico e Presencial); nessa API 6 é Dispensa e 7 Inexigibilidade

# pastas de saída
PASTA_BRUTOS = DADOS / "brutos"
PASTA_FILTRADOS = DADOS / "filtrados"

session = requests.Session()
session.headers.update({"Accept": "application/json"})


def get_json(params, tentativas=5, url=URL):
    """GET com retry para erros temporários (429, 5xx, timeout)."""
    for i in range(tentativas):
        try:
            r = session.get(url, params=params, timeout=90)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(2 ** i)
                continue
            # 4xx (ex.: 400 por parâmetro inválido): não adianta repetir
            print(f"  HTTP {r.status_code}: {r.text[:200]}")
            return None
        except (requests.Timeout, requests.ConnectionError) as e:
            print(f"  erro de rede ({e}), tentativa {i + 1}/{tentativas}")
            time.sleep(2 ** i)
    return None


def buscar_modalidade(cnpj, cod, inicio, fim):
    registros, vistos = [], set()
    pagina = 1
    while True:
        params = {
            "pagina": pagina,
            "tamanhoPagina": TAMANHO,
            "orgaoEntidadeCnpj": cnpj,
            "dataPublicacaoPncpInicial": inicio.isoformat(),
            "dataPublicacaoPncpFinal": fim.isoformat(),
            "codigoModalidade": cod,
        }
        j = get_json(params)
        if not j:
            break

        resultado = j.get("resultado") or []
        if not resultado:
            break

        # só conta o que ainda não foi visto; se nada novo, a paginação parou de mudar.
        # Chave é o numeroControlePNCP: o idCompra se repete entre contratações distintas.
        novos = [x for x in resultado if x.get("numeroControlePNCP") not in vistos]
        if not novos:
            break
        for x in novos:
            vistos.add(x.get("numeroControlePNCP"))
            registros.append(x)

        print(f"  modalidade {cod} | pág {pagina}: +{len(novos)} "
              f"(total {len(registros)}/{j.get('totalRegistros')})")

        # fim declarado pela própria API
        if j.get("paginasRestantes", 0) == 0 or pagina >= j.get("totalPaginas", pagina):
            break

        pagina += 1
        time.sleep(0.3)
    return registros


def normalizar(texto):
    """Minúsculas e sem acento, para comparar 'Pregão' com 'pregao'."""
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    return "".join(c for c in texto if not unicodedata.combining(c)).lower().strip()


def slug(texto):
    return "-".join(normalizar(texto).replace("/", " ").split())


def grupo(registro):
    """Pasta da contratação: <modalidade>_<modo de disputa>, ex.: 'pregao_aberto-fechado'.

    A modalidade usa só a parte antes de ' - ' ('Pregão - Eletrônico' -> 'pregao'); modo
    'Não se aplica' é omitido ('dispensa', 'inexigibilidade').
    """
    modalidade = slug(str(registro.get("modalidadeNome") or "sem modalidade").split(" - ")[0])
    modo = slug(registro.get("modoDisputaNomePncp") or "")
    modo = modo.removeprefix(modalidade + "-")  # 'Dispensa Com Disputa' -> 'com-disputa'
    if not modo or modo == "nao-se-aplica":
        return modalidade
    return f"{modalidade}_{modo}"


def agrupar(registros):
    grupos = {}
    for r in registros:
        grupos.setdefault(grupo(r), []).append(r)
    return dict(sorted(grupos.items()))


def salvar(registros, pasta, nome):
    pasta.mkdir(parents=True, exist_ok=True)
    with open(pasta / f"{nome}.json", "w", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False, indent=2)

    try:
        import pandas as pd
        pd.DataFrame(registros).to_csv(pasta / f"{nome}.csv", index=False, encoding="utf-8-sig")
    except ImportError:
        print("pandas não instalado, só o JSON foi salvo.")


def ler_orgaos(valores):
    """CNPJs informados diretamente e/ou em arquivos (um por linha; '#' inicia comentário)."""
    cnpjs = []
    for v in valores:
        caminho = Path(v)
        if caminho.is_file():
            linhas = caminho.read_text(encoding="utf-8").splitlines()
            itens = [l.split("#")[0] for l in linhas]
        else:
            itens = v.split(",")
        for item in itens:
            digitos = re.sub(r"\D", "", item)
            if not digitos:
                continue
            if len(digitos) != 14:
                raise SystemExit(f"CNPJ inválido: {item.strip()!r}")
            if digitos not in cnpjs:
                cnpjs.append(digitos)
    return cnpjs


def filtrar_modos(registros, modos):
    """Mantém só os modos de disputa pedidos (comparação sem acento/maiúsculas, ex.: 'aberto-fechado')."""
    if not modos:
        return registros
    pedidos = {slug(m) for m in modos}
    return [r for r in registros if slug(r.get("modoDisputaNomePncp") or "nao se aplica") in pedidos]


def argumentos():
    ap = argparse.ArgumentParser(description="Coleta os pregões (Lei 14.133) no Compras.gov.br e separa por modo de disputa.")
    ap.add_argument("--orgaos", nargs="+", default=ORGAOS_PADRAO, metavar="CNPJ|ARQUIVO",
                    help="CNPJs dos órgãos (separados por espaço/vírgula) ou arquivo com um CNPJ por linha "
                         "(padrão: Prefeitura de João Pessoa)")
    ap.add_argument("--inicio", type=date.fromisoformat, help=f"data inicial AAAA-MM-DD (padrão: hoje - {DIAS_PADRAO} dias)")
    ap.add_argument("--fim", type=date.fromisoformat, default=date.today(), help="data final AAAA-MM-DD (padrão: hoje)")
    ap.add_argument("--modos", nargs="+", metavar="MODO",
                    help="modos de disputa a manter, ex.: aberto-fechado aberto fechado-aberto (padrão: todos)")
    ap.add_argument("--relatorios", action="store_true", help="em seguida, abre o navegador para baixar os relatórios")
    args = ap.parse_args()
    args.inicio = args.inicio or args.fim - timedelta(days=DIAS_PADRAO)
    if args.inicio > args.fim:
        ap.error("--inicio maior que --fim")
    args.orgaos = ler_orgaos(args.orgaos)
    return args


def main():
    args = argumentos()
    print(f"Período: {args.inicio} a {args.fim} | órgãos: {', '.join(args.orgaos)}")
    todos = []
    for cnpj in args.orgaos:
        print(f"== órgão {cnpj}")
        for cod in MODALIDADES:
            print(f"codigoModalidade={cod}")
            regs = buscar_modalidade(cnpj, cod, args.inicio, args.fim)
            print(f"  -> {len(regs)} registros")
            todos.extend(regs)

    # dedup global por numeroControlePNCP (idCompra não é único)
    unicos = {r["numeroControlePNCP"]: r for r in todos}
    todos = list(unicos.values())

    salvar(todos, PASTA_BRUTOS, "contratacoes")
    print(f"Total final: {len(todos)} contratações -> {PASTA_BRUTOS}")

    selecionados = filtrar_modos(todos, args.modos)
    if args.modos:
        print(f"Modos {args.modos}: {len(selecionados)} contratações")

    grupos = agrupar(selecionados)
    for nome, registros in grupos.items():
        salvar(registros, PASTA_FILTRADOS / nome, f"contratacoes_{nome}")
        print(f"  {nome}: {len(registros)} -> {PASTA_FILTRADOS / nome}")

    # opcional: abre o navegador para baixar os zips de relatórios das contratações selecionadas
    if args.relatorios:
        from relatorios import baixar_relatorios
        for nome, registros in grupos.items():
            print(f"== {nome}")
            baixar_relatorios(registros, PASTA_FILTRADOS / nome / "relatorios")


if __name__ == "__main__":
    main()
