"""Inventário dos relatórios já baixados: tabela relatorios_pdf em dados/pncp.db e dados/inventario_pdfs.csv.

Varre dados/filtrados/*/relatorios (termos, um arquivo por item) e dados/filtrados/*/outros_formatos
(o que o extrator ainda não lê). O inventário é sempre refeito a partir do disco, então pode ser
rodado a qualquer momento; o baixar_api.py o atualiza no fim de cada rodada. Depois de
`banco_unificado.py --recriar`, rode de novo.

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


def sha256(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


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


def atualizar():
    linhas = varrer()
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
    con.close()
    with open(DADOS / "inventario_pdfs.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS)
        w.writeheader()
        w.writerows(linhas)
    termos = [l for l in linhas if l["tipo"] != "outro formato"]
    print(f"Inventário: {len(termos)} termo(s) por item de {len({l['id_compra'] for l in termos})} compra(s), "
          f"{len(linhas) - len(termos)} arquivo(s) em outros formatos")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    atualizar()
