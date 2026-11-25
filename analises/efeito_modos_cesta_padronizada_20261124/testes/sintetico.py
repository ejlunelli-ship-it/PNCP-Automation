"""Mundo sintético para os testes de integração: cesta congelada + banco da cesta + pncp_v2 com efeito AF conhecido.

40 UASGs (2 por CNPJ), 4 produtos, 2023T1–2025T4. Regimes: 16 sempre A, 8 sempre AF, 8 adotam AF em 2024T2,
6 abandonam AF em 2024T3, 2 irregulares (um trimestre isolado em AF). Cada UASG compra cada produto em todo
trimestre (1 compra por produto, 2 itens). ln P = μ_produto + α_UASG + λ_trimestre + τ·AF + ruído pequeno.
"""
import csv
import hashlib
import json
import sqlite3
from pathlib import Path

import numpy as np

TAU = -5.0          # efeito do AF em log-pontos
PRODUTOS = ["100|UNIDADE", "200|QUILOGRAMA", "300|CAIXA 12 UNIDADE", "400|LITRO"]


def _regime(k, t):
    """t = índice do trimestre (0 = 2023T1). Retorna 1 se AF."""
    if k < 16:
        return 0
    if k < 24:
        return 1
    if k < 32:
        return int(t >= 5)          # adota em 2024T2
    if k < 38:
        return int(t < 6)           # abandona em 2024T3
    return int(t == 4)              # irregular: só 2024T1 em AF


def construir(raiz, semente=3, tau=TAU, ruido=0.5):
    raiz = Path(raiz)
    rng = np.random.default_rng(semente)
    cesta = raiz / "cesta"
    (cesta / "saidas").mkdir(parents=True, exist_ok=True)
    # --- cesta (CSVs)
    cand_cols = ["id_candidato", "produto", "catmat", "unidade_norm", "classe_tecnica", "alertas_especificacao"]
    with open(cesta / "saidas" / "cesta_candidata.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(cand_cols)
        for i, p in enumerate(PRODUTOS):
            w.writerow([f"CP{i + 1:04d}", p, p.split("|")[0], p.split("|")[1], "A" if i < 3 else "B",
                        "indicador 'marca_modelo' em 10% dos itens" if i == 3 else ""])
    h = hashlib.sha256((cesta / "saidas" / "cesta_candidata.csv").read_bytes()).hexdigest()
    (cesta / "saidas" / "congelamento_cesta.json").write_text(json.dumps({"sha256_cesta_candidata": h, "congelado_em": "x"}),
                                                              encoding="utf-8")
    for nome, cols in (("cesta_validada.csv", ["id_candidato", "produto"]),
                       ("formulario_revisao.csv", ["id_candidato", "produto", "decisao (aprovar/rejeitar/dividir)"])):
        with open(cesta / "saidas" / nome, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(cols)
            if nome == "formulario_revisao.csv":
                for i, p in enumerate(PRODUTOS):
                    w.writerow([f"CP{i + 1:04d}", p, ""])
    with open(cesta / "saidas" / "sensibilidade_pertinencia.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["familia", "rigoroso"])
        for i, p in enumerate(PRODUTOS):
            w.writerow([p, int(i < 2)])
    with open(cesta / "saidas" / "recorrencia_temporal.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["id_candidato", "produto", "presente_todas_janelas"])
        for i, p in enumerate(PRODUTOS):
            w.writerow([f"CP{i + 1:04d}", p, int(i != 2)])
    # --- bancos
    ct = sqlite3.connect(raiz / "cesta_trabalho.db")
    ct.executescript("""CREATE TABLE universo_produto (chave TEXT, numero_item INTEGER, produto TEXT, catmat INTEGER,
        unidade_norm TEXT, uasg TEXT, orgao_cnpj TEXT, data_publicacao TEXT, homologado INTEGER);
        CREATE TABLE cesta_candidata_tab (id_candidato TEXT, produto TEXT PRIMARY KEY, classe_tecnica TEXT);""")
    ct.executemany("INSERT INTO cesta_candidata_tab VALUES (?,?,?)",
                   [(f"CP{i + 1:04d}", p, "A" if i < 3 else "B") for i, p in enumerate(PRODUTOS)])
    v2 = sqlite3.connect(raiz / "pncp_v2.db")
    v2.executescript("""CREATE TABLE compras (numero_controle_pncp TEXT PRIMARY KEY, id_compra TEXT, uasg TEXT,
        orgao_cnpj TEXT, uf TEXT, esfera TEXT, poder TEXT, modalidade_nome TEXT, modo_disputa TEXT, srp INTEGER,
        data_publicacao TEXT, data_abertura_proposta TEXT, fonte TEXT);
        CREATE TABLE itens (id INTEGER PRIMARY KEY, numero_controle_pncp TEXT, numero_item INTEGER, registro_principal INTEGER,
        cod_item_catalogo INTEGER, criterio_julgamento TEXT, situacao_item TEXT, homologado INTEGER, quantidade REAL,
        valor_unitario_estimado REAL, valor_unitario_resultado REAL, orcamento_sigiloso INTEGER);
        CREATE INDEX ix_itens_compra ON itens (numero_controle_pncp, numero_item);""")
    mu = {p: rng.normal(3, 1) for p in PRODUTOS}
    alfa = rng.normal(0, 0.1, 40)
    lam = np.linspace(0, 0.08, 12)
    seq, iid = 0, 0
    compras, itens, univ = [], [], []
    for t in range(12):
        ano, q = 2023 + t // 4, t % 4
        data = f"{ano}-{3 * q + 2:02d}-15"
        for k in range(40):
            uasg = f"{k + 1:06d}"
            cnpj = f"{k // 2 + 1:014d}"
            af = _regime(k, t)
            for j, p in enumerate(PRODUTOS):
                seq += 1
                chave = f"{cnpj}-1-{seq:06d}/{ano}"
                compras.append((chave, f"I{seq}", uasg, cnpj, "PB", "F", "E", "Pregão - Eletrônico",
                                "Aberto-Fechado" if af else "Aberto", 0, data + "T10:00:00", data + "T10:00:00", "dados_abertos"))
                for n in (1, 2):
                    iid += 1
                    lp = mu[p] + alfa[k] + lam[t] + tau / 100 * af + rng.normal(0, ruido / 100)
                    sit = "Homologado" if rng.random() > 0.1 else "Fracassado"
                    itens.append((iid, chave, n, 1, int(p.split("|")[0]), "Menor preço", sit, int(sit == "Homologado"),
                                  float(rng.integers(1, 100)), float(np.exp(lp) * 1.3), float(np.exp(lp)) if sit == "Homologado" else None, 0))
                    univ.append((chave, n, p, int(p.split("|")[0]), p.split("|")[1], uasg, cnpj, data, int(sit == "Homologado")))
    v2.executemany("INSERT INTO compras VALUES (" + ",".join("?" * 13) + ")", compras)
    v2.executemany("INSERT INTO itens VALUES (" + ",".join("?" * 12) + ")", itens)
    ct.executemany("INSERT INTO universo_produto VALUES (?,?,?,?,?,?,?,?,?)", univ)
    for c in (ct, v2):
        c.commit()
        c.close()
    cfg = json.loads((Path(__file__).resolve().parents[1] / "config.json").read_text(encoding="utf-8"))
    cfg["caminhos"] = {"pncp_v2": str(raiz / "pncp_v2.db"), "cesta_pasta": str(cesta),
                       "cesta_trabalho": str(raiz / "cesta_trabalho.db"), "trabalho": str(raiz / "trabalho")}
    cfg["amostra"]["trimestres_incompletos"] = []
    cfg["referencia"]["unidades_estaveis"]["min_compras"] = 10
    cfg["eventos"]["bootstrap"] = 49
    cfg["efeitos_fixos"]["bootstrap_wcr"] = 49
    cfg["efeitos_fixos"]["loo_orgaos_top"] = 2
    (raiz / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"config": raiz / "config.json", "saidas": raiz / "saidas", "v2": raiz / "pncp_v2.db",
            "cesta_trabalho": raiz / "cesta_trabalho.db"}
