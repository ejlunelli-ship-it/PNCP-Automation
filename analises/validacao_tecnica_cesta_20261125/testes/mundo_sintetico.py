"""Mundo sintético para os testes: cesta, variantes, pertinência, formulário, banco da cesta e banco PNCP
fictícios, com colunas econômicas (preço, modo) presentes de propósito para provar que não são lidas."""
import csv
import json
import shutil
import sqlite3
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SCRIPTS = AQUI.parent / "scripts"
CONFIG = AQUI.parent / "config"
sys.path.insert(0, str(SCRIPTS))

import comum  # noqa: E402

# (id, catmat, unidade, classe A/B, rigoroso, [(descrição original, itens)])
PRODUTOS = [
    ("CP0001", "100001", "PAR", "A", 1, [("LUVA PARA PROCEDIMENTO, MATERIAL: LÁTEX , TAMANHO: 7 ", 40),
                                          ("LUVA PARA PROCEDIMENTO, MATERIAL LÁTEX, TAMANHO 7", 25)]),
    ("CP0002", "100002", "PACOTE", "A", 1, [("COPO DESCARTÁVEL, MATERIAL POLIPROPILENO, PACOTE COM 100 UNIDADES", 30),
                                           ("COPO DESCARTÁVEL, MATERIAL POLIPROPILENO, PACOTE COM 500 UNIDADES", 12)]),
    ("CP0003", "100003", "FRASCO 1 LITRO", "A", 1, [("ÁLCOOL ETÍLICO, CONCENTRAÇÃO: 70% , APRESENTAÇÃO: LÍQUIDO", 20),
                                                    ("ÁLCOOL ETÍLICO, CONCENTRAÇÃO: 96% , APRESENTAÇÃO: LÍQUIDO", 9)]),
    ("CP0004", "100004", "PACOTE 500 FOLHA", "A", 1, [("PAPEL SULFITE, FORMATO A4, GRAMATURA 75 G/M²", 18),
                                                      ("PAPEL SULFITE, FORMATO A4, GRAMATURA 90 G/M²", 6)]),
    ("CP0005", "100005", "UNIDADE", "A", 1, [("CANETA ESFEROGRÁFICA, COR: AZUL , MATERIAL CORPO: PLÁSTICO", 50),
                                             ("CANETA ESFEROGRÁFICA, COR: VERMELHA , MATERIAL CORPO: PLÁSTICO", 1)]),
    ("CP0006", "100006", "", "A", 1, [("ÁGUA SANITÁRIA, TEOR CLORO 2,5%", 10)]),
    ("CP0007", "100007", "UNIDADE", "A", 1, [("ÁGUA MINERAL SEM GÁS, VOLUME 0,5 L", 15), ("ÁGUA MINERAL SEM GÁS, VOLUME 500 ML", 7)]),
    ("CP0008", "100008", "UNIDADE", "B", 0, [("GRAMPEADOR, MATERIAL METAL, CAPACIDADE 20 FOLHAS", 8)]),
]


def chave_pncp(pid, k, i):
    """Número de controle no formato do PNCP (CNPJ-1-sequencial/ano), único por (produto, variante, par de itens)."""
    return f"{int(pid[2:]):014d}-1-{k * 100 + i // 2 + 1:06d}/2024"


def _unidade(un):
    import re
    m = re.match(r"^(.*?)\s+(\d+(?:\.\d+)?)\s+(\S+)$", un or "")
    return (m.group(1), m.group(2), m.group(3)) if m else (un, "", "")


def _w(caminho, cab, linhas):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(cab)
        w.writerows(linhas)


def criar(tmp, produtos=PRODUTOS, preco_fator=1.0, modo="Aberto"):
    """Cria o mundo em `tmp` e devolve a configuração carregada. preco_fator/modo alteram SÓ campos econômicos."""
    tmp = Path(tmp)
    ent = tmp / "entradas"
    ent.mkdir(parents=True, exist_ok=True)
    cand, var, pert, form, diag = [], [], [], [], []
    db = sqlite3.connect(ent / "cesta.db")
    db.executescript("""
        CREATE TABLE variantes (familia, desc_id, descricao_original, descricao_norm, chave_textual, itens, compras, uasgs,
                                lista_uasgs, primeira, ultima, nome_pdm, anos);
        CREATE TABLE produto_map (familia TEXT, desc_id INTEGER, produto TEXT, assinatura TEXT, PRIMARY KEY (familia, desc_id));
        CREATE TABLE universo_produto (chave TEXT, numero_item INT, catmat, classe, pdm, homologado, situacoes, registros,
            unidade_original, unidade_norm TEXT, embalagem TEXT, conteudo TEXT, unidade_conteudo TEXT, alerta_unidade TEXT,
            n_descricoes_item, nome_pdm, desc_id INT, desc_completa, uasg, orgao_cnpj, data_publicacao, ano, trimestre,
            uasg_item, quantidade_min, familia, produto, valor_unitario_homologado REAL, modo_disputa TEXT);
        CREATE INDEX ix_up_prod ON universo_produto (produto);
        CREATE TABLE compras_base (chave TEXT PRIMARY KEY, id_compra TEXT, uasg TEXT, uf TEXT, modalidade TEXT, modo_disputa TEXT);
        CREATE TABLE unidades (unidade_original TEXT PRIMARY KEY, unidade_texto TEXT, unidade_norm TEXT, embalagem TEXT, conteudo TEXT,
                               unidade_conteudo TEXT, alerta TEXT, itens INTEGER);
    """)
    did = 0
    for pid, cat, un, classe, rig, vs in produtos:
        fam = f"{cat}|{un}"
        prod = fam
        compras_p, uasgs_p, itens_p = set(), set(), 0
        for k, (desc, n) in enumerate(vs):
            did += 1
            chaves = {chave_pncp(pid, k, i) for i in range(n)}
            uas = {f"{i % 5:06d}" for i in range(n)}
            for i in range(n):
                db.execute("INSERT INTO universo_produto (chave, numero_item, catmat, n_descricoes_item, desc_id, uasg, data_publicacao, "
                           "familia, produto, valor_unitario_homologado, modo_disputa) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                           (chave_pncp(pid, k, i), i % 2 + 1, cat, 1, did, f"{i % 5:06d}", "2024-05-01", fam, prod,
                            (10.0 + k) * preco_fator * (1 + i % 3), modo if i % 2 else "Aberto-Fechado"))
            db.execute("INSERT INTO variantes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       (fam, did, desc, "", "", n, len(chaves), len(uas), ",".join(sorted(uas)), "2024-05-01", "2024-05-01", "PDM", "2024"))
            db.execute("INSERT INTO produto_map VALUES (?,?,?,?)", (fam, did, prod, ""))
            var.append([fam, cat, un, desc, n, len(chaves), len(uas), "2024-05-01", "2024-05-01", "PDM", round(17.3 * preco_fator, 2)])
            for c in chaves:
                db.execute("INSERT OR IGNORE INTO compras_base VALUES (?,?,?,?,?,?)", (c, c, "000001", "PB", "Pregão Eletrônico", modo))
            compras_p |= chaves
            uasgs_p |= uas
            itens_p += n
        emb, cont, ucont = _unidade(un)
        db.execute("INSERT OR IGNORE INTO unidades VALUES (?,?,?,?,?,?,?,?)", (un or "(vazia)", un, un, emb, cont, ucont, "" if un else "vazia", 1))
        cand.append([pid, prod, cat, un, max(vs, key=lambda x: x[1])[0], len(compras_p), itens_p, len(uasgs_p), len(uasgs_p), 1, 1,
                     classe, "6515", "123", "", "", "", 1, len(vs), round(12.5 * preco_fator, 2), modo, int(len(compras_p) * 0.8)])
        pert.append([fam, 1, 1, rig, 1])
        form.append([pid, ""])
        diag.append([pid, len(compras_p) if modo == "Aberto" else 0, 0 if modo == "Aberto" else len(compras_p)])
    db.commit()
    db.close()
    _w(ent / "cesta_candidata.csv", ["id_candidato", "produto", "catmat", "unidade_norm", "descricao_representativa", "compras", "itens",
                                     "uasgs", "orgaos", "anos", "trimestres", "classe_tecnica", "classe", "pdm", "alertas_especificacao",
                                     "pendencias_validacao", "cautela", "n_descricoes_originais", "n_descricoes_distintas",
                                     "preco_medio", "modo_disputa_dominante", "compras_homologadas"], cand)
    _w(ent / "descricoes_variantes.csv", ["familia", "catmat", "unidade_norm", "descricao_original", "itens", "compras", "uasgs",
                                          "primeira", "ultima", "nome_pdm", "valor_medio"], var)
    _w(ent / "sensibilidade_pertinencia.csv", ["familia", "brando", "inicial", "rigoroso", "inicial_homologados"], pert)
    _w(ent / "formulario_revisao.csv", ["id_candidato", "decisao (aprovar/rejeitar/dividir)"], form)
    _w(ent / "cesta_validada.csv", ["id_candidato", "produto"], [])
    _w(ent / "diagnostico_por_produto.csv", ["id_candidato", "compras_A", "compras_AF"], diag)
    (ent / "congelamento_cesta.json").write_text("{}", encoding="utf-8")
    pn = sqlite3.connect(ent / "pncp.db")
    pn.execute("CREATE TABLE IF NOT EXISTS compras (x)")
    pn.commit()
    pn.close()
    return configurar(tmp)


def configurar(tmp):
    tmp = Path(tmp)
    ent = tmp / "entradas"
    pc = tmp / "config"
    if not pc.exists():
        shutil.copytree(CONFIG, pc)
        par = json.loads((pc / "parametros.json").read_text(encoding="utf-8"))
        par["entradas"] = {"pasta_cesta": str(ent), "cesta_candidata": str(ent / "cesta_candidata.csv"),
                           "variantes": str(ent / "descricoes_variantes.csv"), "pertinencia": str(ent / "sensibilidade_pertinencia.csv"),
                           "formulario_original": str(ent / "formulario_revisao.csv"), "cesta_validada_original": str(ent / "cesta_validada.csv"),
                           "congelamento": str(ent / "congelamento_cesta.json"), "banco_cesta": str(ent / "cesta.db"),
                           "banco_pncp": str(ent / "pncp.db")}
        par["trabalho"] = str(tmp / "trabalho" / "trabalho.db")
        par["saidas"] = str(tmp / "saidas")
        par["revisores"] = str(pc / "revisores.csv")
        (pc / "parametros.json").write_text(json.dumps(par, ensure_ascii=False, indent=1), encoding="utf-8")
        reg = json.loads((pc / "regras_atributos.json").read_text(encoding="utf-8"))
        reg["chave_declarada_min_ocorrencias"] = 1
        (pc / "regras_atributos.json").write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
        _w(pc / "revisores.csv", ["id_revisor", "nome", "qualificacao", "funcoes", "observacao"],
           [["R1", "Revisora Um", "engenheira de materiais", "produto", ""], ["R2", "Revisor Dois", "farmacêutico", "variantes", ""],
            ["R3", "Revisora Três", "catalogadora", "variantes", ""]])
    return comum.carregar_config(pc)


def ler(caminho):
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def gravar(caminho, linhas):
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        cab = next(csv.reader(f))
    with open(caminho, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cab, lineterminator="\n")
        w.writeheader()
        for r in linhas:
            w.writerow({k: r.get(k, "") for k in cab})
