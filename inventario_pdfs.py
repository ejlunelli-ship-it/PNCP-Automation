"""Registro do que já foi achado, para não buscar de novo.

- tabela relatorios_pdf (pncp.db) e dados/inventario_pdfs.csv: os arquivos em disco, de
  dados/filtrados/*/relatorios (termos, um arquivo por item) e */outros_formatos;
- tabela busca_pdf (pncp.db): a última busca de cada compra, a partir dos motivos.csv das rodadas;
- dados/pendentes_manual.csv: compras buscadas e ainda sem todos os termos. **É a lista a usar no
  download manual**; quem não está nela já foi resolvido ou ainda não foi buscado.

Tudo é refeito a partir do disco, então pode rodar a qualquer momento; o baixar_api.py chama no fim de
cada rodada. Depois de `banco_unificado.py --recriar`, rode de novo.

Uso: python inventario_pdfs.py
"""
import csv
import hashlib
import re
import sqlite3
import sys

from config import DADOS

RE_TERMO = re.compile(r"^relatorio-(termo-homologacao|julg-hab)-(\d+)(?:-s\d+)?-item-(\d+)\.pdf$", re.I)
RE_PASTA = re.compile(r"_(\d+)$")
COLUNAS = ["id_compra", "numero_controle_pncp", "item", "tipo", "arquivo", "tamanho", "sha256", "pasta"]
COLUNAS_BUSCA = ["numero_controle_pncp", "id_compra", "mes", "passada", "situacao", "motivo", "itens_cobertos",
                 "outros_guardados"]
LINK = ("https://cnetmobile.estaleiro.serpro.gov.br/comprasnet-web/public/compras/"
        "acompanhamento-compra/item/1?compra={}")


def sha256(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def ler_motivos():
    """Linhas de todos os motivos.csv, em ordem cronológica de rodada, com o mês em `mes`."""
    linhas = []
    for arquivo in sorted((DADOS / "filtrados").glob("aberto-fechado_*/motivos.csv")):
        with open(arquivo, newline="", encoding="utf-8-sig") as f:
            linhas += [{**l, "mes": arquivo.parent.name.split("_")[-1]} for l in csv.DictReader(f)]
    return linhas


def varrer():
    linhas = []
    for pasta in sorted(p for p in (DADOS / "filtrados").iterdir() if p.is_dir()):
        for sub in ("relatorios", "outros_formatos"):
            for arq in sorted((pasta / sub).rglob("*")):
                if not arq.is_file() or arq.name == "manifesto.csv" or arq.name.startswith("."):
                    continue
                m = RE_TERMO.match(arq.name)
                compra = RE_PASTA.search(arq.parent.name)
                linhas.append({
                    "id_compra": m.group(2) if m else (compra.group(1) if compra else None),
                    "numero_controle_pncp": None,
                    "item": int(m.group(3)) if m else None,
                    "tipo": {"termo-homologacao": "termo de homologação", "julg-hab": "termo de julgamento"}[m.group(1).lower()]
                            if m else "outro formato",
                    "arquivo": arq.relative_to(DADOS).as_posix(),
                    "tamanho": arq.stat().st_size,
                    "sha256": sha256(arq),
                    "pasta": pasta.name,
                })
    return linhas


def buscas():
    """Melhor registro de cada compra: completo vale sobre os demais; senão, a busca mais recente."""
    por_compra = {}
    for l in ler_motivos():
        atual = por_compra.get(l["numeroControlePNCP"])
        if atual is None or atual["situacao"] != "completo":
            por_compra[l["numeroControlePNCP"]] = l
    return [{"numero_controle_pncp": l["numeroControlePNCP"], "id_compra": l["idCompra"], "mes": l["mes"],
             "passada": l["passada"], "situacao": l["situacao"], "motivo": l["motivo"],
             "itens_cobertos": int(l["itens_cobertos"] or 0), "outros_guardados": int(l["outros_guardados"] or 0)}
            for l in por_compra.values()]


def atualizar():
    linhas = varrer()
    busca = buscas()
    con = sqlite3.connect(DADOS / "pncp.db")
    # id_compra se repete entre contratações: só preenche quando aponta para uma única
    unicos = dict(con.execute("SELECT id_compra, MIN(numero_controle_pncp) FROM compras GROUP BY 1 HAVING COUNT(*) = 1"))
    for l in linhas:
        l["numero_controle_pncp"] = unicos.get(l["id_compra"])
    with con:
        con.execute("DROP TABLE IF EXISTS relatorios_pdf")
        con.execute("""CREATE TABLE relatorios_pdf (
            id_compra TEXT, numero_controle_pncp TEXT, item INTEGER, tipo TEXT, arquivo TEXT PRIMARY KEY,
            tamanho INTEGER, sha256 TEXT, pasta TEXT)""")
        con.executemany(f"INSERT INTO relatorios_pdf VALUES ({', '.join('?' * len(COLUNAS))})",
                        [[l[c] for c in COLUNAS] for l in linhas])
        con.execute("CREATE INDEX ix_relatorios_pdf_compra ON relatorios_pdf (numero_controle_pncp, item)")
        con.execute("DROP TABLE IF EXISTS busca_pdf")
        con.execute("""CREATE TABLE busca_pdf (
            numero_controle_pncp TEXT PRIMARY KEY, id_compra TEXT, mes TEXT, passada TEXT, situacao TEXT, motivo TEXT,
            itens_cobertos INTEGER, outros_guardados INTEGER)""")
        con.executemany(f"INSERT INTO busca_pdf VALUES ({', '.join('?' * len(COLUNAS_BUSCA))})",
                        [[l[c] for c in COLUNAS_BUSCA] for l in busca])
    con.close()
    with open(DADOS / "inventario_pdfs.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS)
        w.writeheader()
        w.writerows(linhas)
    pendentes = [{**l, "link_compra": LINK.format(l["id_compra"])} for l in busca if l["situacao"] != "completo"]
    with open(DADOS / "pendentes_manual.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS_BUSCA + ["link_compra"])
        w.writeheader()
        w.writerows(pendentes)
    termos = [l for l in linhas if l["tipo"] != "outro formato"]
    print(f"Inventário: {len(termos)} termo(s) por item de {len({l['id_compra'] for l in termos})} compra(s), "
          f"{len(linhas) - len(termos)} arquivo(s) em outros formatos, {len(busca)} compra(s) buscada(s), "
          f"{len(pendentes)} pendente(s) para o manual")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    atualizar()
