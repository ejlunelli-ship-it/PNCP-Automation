import json
import sys
import time
import unicodedata
from datetime import date, timedelta
from pathlib import Path

import requests

URL = "https://dadosabertos.compras.gov.br/modulo-contratacoes/1_consultarContratacoes_PNCP_14133"
CNPJ = "08778326000156"
TAMANHO = 500

# período: último ano até hoje
DATA_FINAL = date.today()
DATA_INICIAL = DATA_FINAL - timedelta(days=365)

# pastas de saída
BASE = Path(__file__).parent / "dados"
PASTA_BRUTOS = BASE / "brutos"
PASTA_FILTRADOS = BASE / "filtrados" / "pregao_aberto-fechado"

session = requests.Session()
session.headers.update({"Accept": "application/json"})


def get_json(params, tentativas=5):
    """GET com retry para erros temporários (429, 5xx, timeout)."""
    for i in range(tentativas):
        try:
            r = session.get(URL, params=params, timeout=90)
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


def buscar_modalidade(cod):
    registros, vistos = [], set()
    pagina = 1
    while True:
        params = {
            "pagina": pagina,
            "tamanhoPagina": TAMANHO,
            "orgaoEntidadeCnpj": CNPJ,
            "dataPublicacaoPncpInicial": DATA_INICIAL.isoformat(),
            "dataPublicacaoPncpFinal": DATA_FINAL.isoformat(),
            "codigoModalidade": cod,
        }
        j = get_json(params)
        if not j:
            break

        resultado = j.get("resultado") or []
        if not resultado:
            break

        # só conta o que ainda não foi visto; se nada novo, a paginação parou de mudar
        novos = [x for x in resultado if x.get("idCompra") not in vistos]
        if not novos:
            break
        for x in novos:
            vistos.add(x.get("idCompra"))
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


def filtrar(registros):
    return [
        r for r in registros
        if "pregao" in normalizar(r.get("amparoLegalDescricao"))
        and normalizar(r.get("modoDisputaNomePncp")) == "aberto-fechado"
    ]


def salvar(registros, pasta, nome):
    pasta.mkdir(parents=True, exist_ok=True)
    with open(pasta / f"{nome}.json", "w", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False, indent=2)

    try:
        import pandas as pd
        pd.DataFrame(registros).to_csv(pasta / f"{nome}.csv", index=False, encoding="utf-8-sig")
    except ImportError:
        print("pandas não instalado, só o JSON foi salvo.")


def main():
    print(f"Período: {DATA_INICIAL} a {DATA_FINAL}")
    todos = []
    for cod in range(1, 20):
        print(f"codigoModalidade={cod}")
        regs = buscar_modalidade(cod)
        print(f"  -> {len(regs)} registros")
        todos.extend(regs)

    # dedup global por idCompra
    unicos = {r["idCompra"]: r for r in todos}
    todos = list(unicos.values())

    salvar(todos, PASTA_BRUTOS, "contratacoes_joao_pessoa")
    print(f"Total final: {len(todos)} contratações -> {PASTA_BRUTOS}")

    filtrados = filtrar(todos)
    salvar(filtrados, PASTA_FILTRADOS, "contratacoes_pregao_aberto-fechado")
    print(f"Filtrados (pregão + Aberto-Fechado): {len(filtrados)} -> {PASTA_FILTRADOS}")

    # opcional: abre o navegador para baixar os zips de relatórios dos filtrados
    if "--relatorios" in sys.argv:
        from relatorios import baixar_relatorios
        baixar_relatorios(filtrados, PASTA_FILTRADOS / "relatorios")


if __name__ == "__main__":
    main()
