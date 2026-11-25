"""Gerador de um workspace sintético (pncp.db + brutos CSV + config) com o mesmo esquema do real.

Cenários embutidos (ver testes):
  CATMAT 111 'UNIDADE'  caneta, descrições só com variação de formatação; uma compra com 3 itens dela;
                        UASGs 000001 e 000002 compartilham o mesmo CNPJ
  CATMAT 222            mesmo código em 'Caixa 100,00 UN', 'Caixa 500,00 UN' e 'Unidade'
  CATMAT 333 'Resma'    papel A4 com 75 G/M2 e 90 G/M2 (atributos incompatíveis)
  CATMAT 555 'Unidade'  descrição só com o nome do PDM (genérica)
  CATSER 444            serviço com código coincidente em faixa de material (deve ficar fora)
  compras com UASG ausente, data inválida, Pregão Presencial e id_compra repetido
"""
import csv
import json
import random
import shutil
import sqlite3
from pathlib import Path

AQUI = Path(__file__).resolve().parent
CONFIG_REAL = AQUI.parent / "config"

ESQUEMA = """
CREATE TABLE compras (
    numero_controle_pncp TEXT PRIMARY KEY, id_compra TEXT, uasg TEXT, numero_compra TEXT, ano_compra INTEGER,
    orgao_cnpj TEXT, orgao_nome TEXT, esfera TEXT, poder TEXT, uf TEXT, municipio TEXT, codigo_ibge INTEGER,
    modalidade_nome TEXT, modo_disputa TEXT, srp INTEGER, existe_resultado INTEGER,
    valor_total_estimado REAL, valor_total_homologado REAL,
    data_publicacao TEXT, data_abertura_proposta TEXT, ano_publicacao INTEGER, objeto_compra TEXT,
    fonte TEXT NOT NULL DEFAULT 'dados_abertos', usuario_nome TEXT, codigo_unidade TEXT, nome_unidade TEXT, situacao_compra TEXT);
CREATE TABLE itens (
    id INTEGER PRIMARY KEY, numero_controle_pncp TEXT NOT NULL REFERENCES compras, numero_item INTEGER NOT NULL,
    id_compra_item TEXT, registro_principal INTEGER NOT NULL DEFAULT 0, uasg_item TEXT,
    cod_item_catalogo INTEGER, material_ou_servico TEXT, codigo_classe INTEGER, codigo_grupo INTEGER,
    codigo_pdm INTEGER, unidade_medida TEXT, descricao_resumida TEXT,
    criterio_julgamento TEXT, tipo_beneficio TEXT, numero_grupo INTEGER, orcamento_sigiloso INTEGER,
    situacao_item TEXT, homologado INTEGER NOT NULL,
    quantidade REAL, valor_unitario_estimado REAL, tem_resultado INTEGER, quantidade_resultado REAL,
    valor_unitario_resultado REAL, valor_total_resultado REAL, data_resultado TEXT, data_atualizacao TEXT,
    cod_fornecedor TEXT, nome_fornecedor TEXT);
CREATE INDEX ix_itens_compra ON itens (numero_controle_pncp, numero_item);
"""

PRODUTOS = {
    "caneta": (111, "M", 7510, "Unidade", "Caneta esferográfica", "CANETA ESFEROGRÁFICA",
               ["CANETA ESFEROGRÁFICA, MATERIAL PLÁSTICO, COR AZUL, ESPESSURA PONTA 1,0 MM",
                "CANETA ESFEROGRÁFICA, MATERIAL: PLÁSTICO , COR: AZUL , ESPESSURA PONTA: 1,0 MM "]),
    "luva100": (222, "M", 6515, "Caixa 100,00 UN", "Luva", "LUVA PARA PROCEDIMENTO",
                ["LUVA PARA PROCEDIMENTO, MATERIAL LÁTEX, TAMANHO MÉDIO, TIPO NÃO ESTÉRIL"]),
    "luva500": (222, "M", 6515, "Caixa 500,00 UN", "Luva", "LUVA PARA PROCEDIMENTO",
                ["LUVA PARA PROCEDIMENTO, MATERIAL LÁTEX, TAMANHO MÉDIO, TIPO NÃO ESTÉRIL"]),
    "luvaun": (222, "M", 6515, "Unidade", "Luva", "LUVA PARA PROCEDIMENTO",
               ["LUVA PARA PROCEDIMENTO, MATERIAL LÁTEX, TAMANHO MÉDIO, TIPO NÃO ESTÉRIL"]),
    "papel75": (333, "M", 7530, "Resma", "Papel A4", "PAPEL A4",
                ["PAPEL A4, MATERIAL CELULOSE, GRAMATURA 75 G/M², 500 FOLHAS"]),
    "papel90": (333, "M", 7530, "Resma", "Papel A4", "PAPEL A4",
                ["PAPEL A4, MATERIAL CELULOSE, GRAMATURA 90 G/M², 500 FOLHAS"]),
    "peca": (555, "M", 2590, "Unidade", "Peça veículo", "PEÇA MECÂNICA / ELÉTRICA - VEÍCULO AUTOMOTIVO",
             ["PEÇA MECÂNICA / ELÉTRICA - VEÍCULO AUTOMOTIVO"]),
    "servico": (444, "S", 0, "Unidade", "Serviço de limpeza", "", ["SERVIÇO DE LIMPEZA"]),
}

CSV_COLS = ["idCompra", "idCompraItem", "unidadeOrgaoCodigoUnidade", "orgaoEntidadeCnpj", "numeroItemPncp",
            "numeroItemCompra", "descricaoResumida", "materialOuServico", "codigoClasse", "codItemCatalogo",
            "descricaodetalhada", "unidadeMedida", "situacaoCompraItemNome", "quantidade", "valorUnitarioEstimado",
            "numeroControlePNCPCompra", "codigoPdm", "nomePdm"]

UASGS = [f"{i:06d}" for i in range(1, 9)]
CNPJ = {u: ("11111111000111" if u in ("000001", "000002") else f"{int(u):014d}") for u in UASGS}


def _datas():
    """24 trimestres-datas de 2023 a 2026 (publicação)."""
    return [f"{a}-{m:02d}-15T10:00:00" for a in (2023, 2024, 2025, 2026) for m in (1, 4, 7, 10)]


def construir(raiz, semente=7, fator_preco=1.0, inverter_modo=False, parametros=None):
    """Cria raiz/dados/pncp.db, raiz/dados/brutos/2024/itens_pregao_2024-01.csv e raiz/config/.
    fator_preco e inverter_modo alteram SÓ preços e modo de disputa (teste de independência)."""
    raiz = Path(raiz)
    (raiz / "dados" / "brutos" / "2024").mkdir(parents=True, exist_ok=True)
    rnd = random.Random(semente)
    db = raiz / "dados" / "pncp.db"
    con = sqlite3.connect(db)
    con.executescript(ESQUEMA)
    datas = _datas()
    compras, itens, csv_linhas = [], [], []
    seq, item_id = 0, 0

    def compra(uasg, data, modalidade="Pregão - Eletrônico", id_compra=None, uasg_campo="__"):
        nonlocal seq
        seq += 1
        chave = f"{CNPJ[uasg]}-1-{seq:06d}/{data[:4]}"
        modo = ["Aberto", "Aberto-Fechado"][(seq + (1 if inverter_modo else 0)) % 2]
        compras.append((chave, id_compra or f"{uasg}05{seq:05d}{data[:4]}", uasg if uasg_campo == "__" else uasg_campo,
                        f"{seq:05d}", int(data[:4]), CNPJ[uasg], f"ORGAO {uasg}", "F", "E", "PB", "X", 1, modalidade, modo,
                        0, 1, 1000.0 * fator_preco, 900.0 * fator_preco, data, data, int(data[:4]), "obj", "dados_abertos",
                        None, None, None, None))
        return chave

    def item(chave, n, prod, uasg, desc_idx=0, situacao="Homologado", repetir=1):
        nonlocal item_id
        cat, ms, classe, un, resumida, pdm, descs = PRODUTOS[prod]
        desc = descs[desc_idx % len(descs)]
        for r in range(repetir):
            item_id += 1
            preco = round(rnd.uniform(1, 100) * fator_preco, 2)
            itens.append((item_id, chave, n, f"{chave}-{n}", int(r == 0), uasg, cat, ms, classe or None, None, 1,
                          un, resumida, "Menor preço", "Não se aplica", 0, 0, situacao, int(situacao == "Homologado"),
                          10.0, preco, 1, 10.0, preco * 0.9, preco * 9, "2024-01-01", "2024-02-01", "1", "F"))
            csv_linhas.append({"idCompra": "x", "idCompraItem": f"{chave}-{n}", "unidadeOrgaoCodigoUnidade": uasg,
                               "orgaoEntidadeCnpj": CNPJ[uasg], "numeroItemPncp": str(n), "numeroItemCompra": str(n),
                               "descricaoResumida": resumida, "materialOuServico": ms, "codigoClasse": str(classe),
                               "codItemCatalogo": f"{cat}.0", "descricaodetalhada": desc, "unidadeMedida": un,
                               "situacaoCompraItemNome": situacao, "quantidade": "10", "valorUnitarioEstimado": str(preco),
                               "numeroControlePNCPCompra": chave, "codigoPdm": "1", "nomePdm": pdm})

    # caneta: 16 compras em 8 UASGs, 16 trimestres; a 1ª compra tem 3 itens da caneta
    for k in range(16):
        u = UASGS[k % 8]
        ch = compra(u, datas[k])
        if k == 0:
            for n in (1, 2, 3):
                item(ch, n, "caneta", u, desc_idx=n)
        else:
            item(ch, 1, "caneta", u, desc_idx=k)
        # luvas: três unidades diferentes do mesmo CATMAT
        item(ch, 10, ["luva100", "luva500", "luvaun"][k % 3], u)
        item(ch, 20, "papel75" if k % 2 else "papel90", u)
        item(ch, 30, "peca", u)
        item(ch, 40, "servico", u)
    # registro repetido do mesmo item (2 linhas, mesma chave composta)
    ch = compra("000003", datas[3])
    item(ch, 1, "caneta", "000003", repetir=2)
    # compras problemáticas
    ch = compra("000004", datas[5], uasg_campo=None)          # UASG ausente
    item(ch, 1, "caneta", "000004")
    ch = compra("000005", "2024-13-40T00:00:00")              # data inválida
    item(ch, 1, "caneta", "000005")
    ch = compra("000006", datas[6], modalidade="Pregão - Presencial")
    item(ch, 1, "caneta", "000006")
    ch1 = compra("000007", datas[7], id_compra="DUPLICADO")   # id_compra repetido
    item(ch1, 1, "caneta", "000007")
    ch2 = compra("000007", datas[7], id_compra="DUPLICADO")
    item(ch2, 1, "caneta", "000007")

    con.executemany(f"INSERT INTO compras VALUES ({','.join('?' * 27)})", compras)
    con.executemany(f"INSERT INTO itens VALUES ({','.join('?' * 29)})", itens)
    con.commit()
    con.close()
    with open(raiz / "dados" / "brutos" / "2024" / "itens_pregao_2024-01.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, CSV_COLS, lineterminator="\n")
        w.writeheader()
        w.writerows(csv_linhas)
    cfg = raiz / "config"
    cfg.mkdir(exist_ok=True)
    for n in ("aliases_unidades.csv", "cautela.json"):
        shutil.copy(CONFIG_REAL / n, cfg / n)
    par = json.loads((CONFIG_REAL / "parametros.json").read_text(encoding="utf-8"))
    par["triagem_inicial"] = {"compras_min": 4, "uasgs_min": 3, "trimestres_min": 3, "anos_min": 2,
                              "share_uasg_dominante_max": 0.5, "hhi_max": 0.5}
    par["sensibilidade"].update({"compras_min": [3, 4, 6], "uasgs_min": [3], "trimestres_min": [3], "anos_min": [2],
                                 "share_uasg_dominante_max": [0.5], "hhi_max": [0.5]})
    par["sensibilidade"]["cenarios_nomeados"] = {
        "brando": {**par["triagem_inicial"], "compras_min": 3},
        "inicial": dict(par["triagem_inicial"]),
        "rigoroso": {**par["triagem_inicial"], "compras_min": 6},
        "inicial_homologados": {**par["triagem_inicial"], "base": "homologados"}}
    par["temporal"]["janelas_recorrencia"] = [["2023-01-01", "2023-12-31"], ["2024-01-01", "2026-12-31"]]
    if parametros:
        parametros(par)
    (cfg / "parametros.json").write_text(json.dumps(par, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"db": db, "brutos": raiz / "dados" / "brutos", "trabalho": raiz / "trabalho", "saidas": raiz / "saidas",
            "parametros": cfg / "parametros.json"}


def argv(c, etapas="extrair,brutos,normalizar,selecionar,auditar,sensibilidade,diagnostico,relatorio"):
    return ["--etapas", etapas, "--db", str(c["db"]), "--brutos", str(c["brutos"]), "--trabalho", str(c["trabalho"]),
            "--saidas", str(c["saidas"]), "--parametros", str(c["parametros"])]
