"""Banco SQLite unificado da base nacional: dados/pncp.db, a partir de dados/brutos/<ano>/.

Tabelas: compras (uma linha por numeroControlePNCP) e itens (uma linha por registro da API).
View: analise_itens (só registro_principal = 1), com os descontos em % e o filtro `elegivel`.

Um item pode ter mais de um registro na API (idCompraItem duplicado ou mais de um resultado).
`registro_principal` marca um por item: homologado, com valor de resultado, atualização mais recente.

As colunas de lance por etapa (melhor_lance_*, etc.) nascem vazias e vêm dos PDFs. Como recriar o
banco apaga o que estiver nelas, o script só sobrescreve um banco existente com --recriar.

A tabela resultados vem de coleta_resultados.py. Depois da coleta, --resultados a carrega no banco
existente, sem mexer nas outras tabelas.

As compras das demais plataformas vêm do PNCP (coleta_pncp.py), com compras.fonte = 'pncp'. Os brutos
ficam em dados/brutos_pncp/ e são recarregados por --recriar; --pncp carrega os meses que faltam.

Uso: python banco_unificado.py [--recriar | --resultados | --pncp]
"""
import argparse
import glob
import gzip
import json
import os
import re
import sqlite3
import sys
import zlib
from datetime import datetime

import pandas as pd

from config import DADOS

BRUTOS = DADOS / "brutos"
BRUTOS_PNCP = DADOS / "brutos_pncp"
DESTINO = DADOS / "pncp.db"
sys.stdout.reconfigure(encoding="utf-8")

# coluna do banco -> campo da API
COMPRAS = {
    "numero_controle_pncp": "numeroControlePNCP", "id_compra": "idCompra", "uasg": "unidadeOrgaoCodigoUnidade",
    "numero_compra": "numeroCompra", "ano_compra": "anoCompraPncp", "orgao_cnpj": "orgaoEntidadeCnpj",
    "orgao_nome": "orgaoEntidadeRazaoSocial", "esfera": "orgaoEntidadeEsferaId", "poder": "orgaoEntidadePoderId",
    "uf": "unidadeOrgaoUfSigla", "municipio": "unidadeOrgaoMunicipioNome", "codigo_ibge": "unidadeOrgaoCodigoIbge",
    "modalidade_nome": "modalidadeNome", "modo_disputa": "modoDisputaNomePncp", "srp": "srp",
    "existe_resultado": "existeResultado", "valor_total_estimado": "valorTotalEstimado",
    "valor_total_homologado": "valorTotalHomologado", "data_publicacao": "dataPublicacaoPncp",
    "data_abertura_proposta": "dataAberturaPropostaPncp", "objeto_compra": "objetoCompra",
}
ITENS = {
    "numero_controle_pncp": "numeroControlePNCPCompra", "numero_item": "numeroItemPncp",
    "id_compra_item": "idCompraItem", "uasg_item": "unidadeOrgaoCodigoUnidade",
    "cod_item_catalogo": "codItemCatalogo", "material_ou_servico": "materialOuServico",
    "codigo_classe": "codigoClasse", "codigo_grupo": "codigoGrupo", "codigo_pdm": "codigoPdm",
    "unidade_medida": "unidadeMedida", "descricao_resumida": "descricaoResumida",
    "criterio_julgamento": "criterioJulgamentoNome", "tipo_beneficio": "tipoBeneficioNome",
    "numero_grupo": "numeroGrupo", "orcamento_sigiloso": "orcamentoSigiloso",
    "situacao_item": "situacaoCompraItemNome", "quantidade": "quantidade",
    "valor_unitario_estimado": "valorUnitarioEstimado", "tem_resultado": "temResultado",
    "quantidade_resultado": "quantidadeResultado", "valor_unitario_resultado": "valorUnitarioResultado",
    "valor_total_resultado": "valorTotalResultado", "data_resultado": "dataResultado",
    "data_atualizacao": "dataAtualizacaoPncp", "cod_fornecedor": "codFornecedor",
    "nome_fornecedor": "nomeFornecedor",
}
INTEIROS = ["numero_item", "cod_item_catalogo", "codigo_classe", "codigo_grupo", "codigo_pdm", "numero_grupo"]
NUMEROS = ["quantidade", "valor_unitario_estimado", "quantidade_resultado", "valor_unitario_resultado",
           "valor_total_resultado"]
BOOLEANOS = ["orcamento_sigiloso", "tem_resultado"]

ESQUEMA = """
-- valores em REAL, não NUMERIC: NUMERIC guarda 80.0 como inteiro e 80 / 100 vira divisão inteira (0)
CREATE TABLE compras (
    numero_controle_pncp TEXT PRIMARY KEY, id_compra TEXT, uasg TEXT, numero_compra TEXT, ano_compra INTEGER,
    orgao_cnpj TEXT, orgao_nome TEXT, esfera TEXT, poder TEXT, uf TEXT, municipio TEXT, codigo_ibge INTEGER,
    modalidade_nome TEXT, modo_disputa TEXT, srp INTEGER, existe_resultado INTEGER,
    valor_total_estimado REAL, valor_total_homologado REAL,
    data_publicacao TEXT, data_abertura_proposta TEXT, ano_publicacao INTEGER, objeto_compra TEXT
);
CREATE TABLE itens (
    id INTEGER PRIMARY KEY,
    numero_controle_pncp TEXT NOT NULL REFERENCES compras, numero_item INTEGER NOT NULL, id_compra_item TEXT,
    registro_principal INTEGER NOT NULL DEFAULT 0, uasg_item TEXT,
    cod_item_catalogo INTEGER, material_ou_servico TEXT, codigo_classe INTEGER, codigo_grupo INTEGER,
    codigo_pdm INTEGER, unidade_medida TEXT, descricao_resumida TEXT,
    criterio_julgamento TEXT, tipo_beneficio TEXT, numero_grupo INTEGER, orcamento_sigiloso INTEGER,
    situacao_item TEXT, homologado INTEGER NOT NULL,
    quantidade REAL, valor_unitario_estimado REAL, tem_resultado INTEGER, quantidade_resultado REAL,
    valor_unitario_resultado REAL, valor_total_resultado REAL, data_resultado TEXT, data_atualizacao TEXT,
    cod_fornecedor TEXT, nome_fornecedor TEXT,
    -- vindas dos PDFs (extrator_homologacao); vazias até a carga
    melhor_lance_modo_aberto REAL, melhor_lance_modo_fechado REAL, melhor_lance_desempate REAL,
    lance_aceito REAL, valor_negociado_aceito REAL, valor_estimado_pdf REAL,
    quantidade_fornecedores INTEGER, status_extracao TEXT, erros_extracao TEXT, versao_parser TEXT,
    arquivo_origem TEXT
);
"""

POS_CARGA = """
UPDATE itens SET registro_principal = 1 WHERE id IN (
    SELECT id FROM (
        SELECT id, ROW_NUMBER() OVER (
            PARTITION BY numero_controle_pncp, numero_item
            ORDER BY homologado DESC, COALESCE(valor_unitario_resultado > 0, 0) DESC, data_atualizacao DESC,
                     COALESCE(quantidade_resultado, 0) DESC, valor_unitario_resultado, id) AS ordem
        FROM itens)
    WHERE ordem = 1);
CREATE INDEX ix_itens_compra ON itens (numero_controle_pncp, numero_item);
CREATE INDEX ix_itens_pareamento ON itens (uasg_item, cod_item_catalogo);
CREATE INDEX ix_compras_id_compra ON compras (id_compra);
CREATE INDEX ix_compras_pdf ON compras (uasg, numero_compra, ano_compra);
"""

VIEW = """
DROP VIEW IF EXISTS analise_itens;
-- Descontos em %. Por etapa, só Menor preço: em Maior desconto o lance do PDF pode ser percentual.
CREATE VIEW analise_itens AS
SELECT b.*,
    CASE WHEN tem_resultado = 1 AND orcamento_sigiloso = 0 AND valor_unitario_estimado > 0
              AND valor_unitario_resultado > 0 AND desconto_final BETWEEN -100 AND 99 THEN 1 ELSE 0 END AS elegivel,
    CASE WHEN por_preco AND valor_unitario_estimado > 0 AND melhor_lance_modo_aberto > 0
         THEN 100.0 * (1 - melhor_lance_modo_aberto / valor_unitario_estimado) END AS desconto_aberto,
    CASE WHEN por_preco AND valor_unitario_estimado > 0 AND melhor_lance_modo_fechado > 0
         THEN 100.0 * (1 - melhor_lance_modo_fechado / valor_unitario_estimado) END AS desconto_fechado,
    CASE WHEN por_preco AND modo_disputa = 'Aberto-Fechado'
         THEN MIN(COALESCE(melhor_lance_modo_aberto, melhor_lance_modo_fechado),
                  COALESCE(melhor_lance_modo_fechado, melhor_lance_modo_aberto)) END AS melhor_lance_apos_fechada,
    CASE WHEN por_preco AND modo_disputa = 'Aberto-Fechado' AND valor_unitario_estimado > 0
              AND melhor_lance_modo_aberto > 0
         THEN 100.0 * (melhor_lance_modo_aberto
                       - MIN(melhor_lance_modo_aberto, COALESCE(melhor_lance_modo_fechado, melhor_lance_modo_aberto)))
              / valor_unitario_estimado END AS ganho_fechada
FROM (
    SELECT i.*, c.id_compra, c.uasg, c.numero_compra, c.ano_compra, c.orgao_cnpj, c.orgao_nome, c.esfera, c.poder,
           c.uf, c.municipio, c.codigo_ibge, c.modalidade_nome, c.modo_disputa, c.srp, c.existe_resultado,
           c.data_publicacao, c.data_abertura_proposta, c.ano_publicacao,
           c.fonte, c.usuario_nome, c.situacao_compra,
           i.criterio_julgamento = 'Menor preço' AS por_preco,
           CASE WHEN i.valor_unitario_estimado > 0 AND i.valor_unitario_resultado > 0
                THEN 100.0 * (1 - i.valor_unitario_resultado / i.valor_unitario_estimado) END AS desconto_final
    FROM itens i JOIN compras c USING (numero_controle_pncp)
    WHERE i.registro_principal = 1
) b;
"""


def inserir(con, tabela, df):
    linhas = df.astype(object).where(df.notna(), None).values.tolist()
    con.executemany(f"INSERT INTO {tabela} ({', '.join(df.columns)}) VALUES ({', '.join('?' * df.shape[1])})", linhas)


def carregar_compras(con):
    total = 0
    for f in sorted(glob.glob(str(BRUTOS / "20*" / "contratacoes_pregao_*.json"))):
        registros = json.load(open(f, encoding="utf-8"))
        df = pd.DataFrame([{c: x.get(campo) for c, campo in COMPRAS.items()} for x in registros])
        df["ano_publicacao"] = df.data_publicacao.str[:4].astype("Int64")
        inserir(con, "compras", df)
        total += len(df)
    print(f"compras: {total:,}", flush=True)


def carregar_itens(con):
    total = 0
    for f in sorted(glob.glob(str(BRUTOS / "20*" / "itens_pregao_*.csv"))):
        # keep_default_na=False: "NA" e "None" são textos válidos em descrição e unidade de medida
        df = pd.read_csv(f, usecols=list(ITENS.values()), dtype=str, encoding="utf-8-sig",
                         keep_default_na=False, na_values=[""])
        df = df.rename(columns={v: k for k, v in ITENS.items()})[list(ITENS)]
        for c in INTEIROS:
            df[c] = pd.to_numeric(df[c]).astype("Int64")
        for c in NUMEROS:
            df[c] = pd.to_numeric(df[c])
        for c in BOOLEANOS:
            df[c] = df[c].str.lower().map({"true": 1, "false": 0}).astype("Int64")
        df["homologado"] = (df.situacao_item == "Homologado").astype(int)
        inserir(con, "itens", df)
        con.commit()
        total += len(df)
        print(f"{os.path.basename(f)}: {len(df):,} (acumulado {total:,})", flush=True)


RESULTADOS = {
    "numero_controle_pncp": "numeroControlePNCPCompra", "numero_item": "numeroItemPncp",
    "sequencial_resultado": "sequencialResultado", "id_compra_item": "idCompraItem",
    "situacao_resultado": "situacaoCompraItemResultadoNome", "motivo_cancelamento": "motivoCancelamento",
    "ni_fornecedor": "niFornecedor", "nome_fornecedor": "nomeRazaoSocialFornecedor",
    "porte_fornecedor": "porteFornecedorNome", "quantidade_homologada": "quantidadeHomologada",
    "valor_unitario_homologado": "valorUnitarioHomologado", "valor_total_homologado": "valorTotalHomologado",
    "data_resultado": "dataResultadoPncp", "data_atualizacao": "dataAtualizacaoPncp",
    "data_cancelamento": "dataCancelamentoPncp",
}


def carregar_resultados(con):
    """Refaz os resultados da API Dados Abertos, sem tocar nos do PNCP. Um resultado pode aparecer em
    mais de um mês: vale o mais recente."""
    preparar_pncp(con)
    con.execute("DELETE FROM resultados WHERE numero_controle_pncp NOT IN "
                "(SELECT numero_controle_pncp FROM compras WHERE fonte = 'pncp')")
    colunas = ", ".join(RESULTADOS)
    atualizar = ", ".join(f"{c} = excluded.{c}" for c in RESULTADOS if c not in list(RESULTADOS)[:3])
    sql = (f"INSERT INTO resultados ({colunas}) VALUES ({', '.join('?' * len(RESULTADOS))}) "
           f"ON CONFLICT DO UPDATE SET {atualizar} WHERE excluded.data_atualizacao >= resultados.data_atualizacao")
    total = 0
    for f in sorted(glob.glob(str(BRUTOS / "20*" / "resultados_pregao_*.json"))):
        registros = json.load(open(f, encoding="utf-8"))
        con.executemany(sql, [[x.get(c) for c in RESULTADOS.values()] for x in registros])
        total += len(registros)
    con.commit()
    print(f"resultados: {total:,} lidos, {con.execute('SELECT COUNT(*) FROM resultados').fetchone()[0]:,} na tabela")


# --- Compras do PNCP fora da API Dados Abertos (coleta_pncp.py) ---

TABELAS_PNCP = """
CREATE TABLE IF NOT EXISTS resultados (
    numero_controle_pncp TEXT NOT NULL, numero_item INTEGER NOT NULL, sequencial_resultado INTEGER NOT NULL,
    id_compra_item TEXT, situacao_resultado TEXT, motivo_cancelamento TEXT, ni_fornecedor TEXT,
    nome_fornecedor TEXT, porte_fornecedor TEXT, quantidade_homologada REAL, valor_unitario_homologado REAL,
    valor_total_homologado REAL, data_resultado TEXT, data_atualizacao TEXT, data_cancelamento TEXT,
    PRIMARY KEY (numero_controle_pncp, numero_item, sequencial_resultado));
CREATE TABLE IF NOT EXISTS compras_duplicadas (
    numero_controle_pncp TEXT PRIMARY KEY, duplicata_de TEXT NOT NULL, usuario_nome TEXT, mes TEXT);
CREATE TABLE IF NOT EXISTS coleta_pncp_meses (
    mes TEXT PRIMARY KEY, publicadas INTEGER, ja_na_base INTEGER, duplicadas INTEGER, novas INTEGER,
    itens INTEGER, resultados INTEGER, sem_itens INTEGER, carregado_em TEXT);
"""
COLUNAS_PNCP = {"fonte": "TEXT NOT NULL DEFAULT 'dados_abertos'", "usuario_nome": "TEXT", "codigo_unidade": "TEXT",
                "nome_unidade": "TEXT", "situacao_compra": "TEXT"}
PLATAFORMA_UASG = "Compras.gov.br"  # só nela o codigoUnidade é UASG; nas outras pode ser "1", em vários órgãos


def preparar_pncp(con):
    """Acrescenta ao banco o que a carga do PNCP usa. Pode rodar mais de uma vez."""
    existentes = {x[1] for x in con.execute("PRAGMA table_info(compras)")}
    for coluna, tipo in COLUNAS_PNCP.items():
        if coluna not in existentes:
            con.execute(f"ALTER TABLE compras ADD COLUMN {coluna} {tipo}")
    con.executescript(TABELAS_PNCP + VIEW)


def chave_pregao(cnpj, ano, numero, abertura):
    """Identifica o pregão entre contratações irmãs; None se faltar número ou abertura."""
    numero = re.sub(r"\D", "", str(numero or "").split("/")[0]).lstrip("0")
    return (cnpj, int(ano), numero, abertura) if numero and abertura else None


def separar_novas(con, registros):
    """(novas, duplicadas, quantas já na base). duplicadas: pares (registro, numeroControlePNCP da irmã)."""
    presentes, chaves = set(), {}
    for controle, cnpj, ano, numero, abertura in con.execute(
            "SELECT numero_controle_pncp, orgao_cnpj, ano_compra, numero_compra, data_abertura_proposta FROM compras"):
        presentes.add(controle)
        chaves[chave_pregao(cnpj, ano, numero, abertura)] = controle
    chaves.pop(None, None)
    novas, duplicadas, na_base = [], [], 0
    for x in sorted(registros, key=lambda r: r["numeroControlePNCP"]):
        if x["numeroControlePNCP"] in presentes:
            na_base += 1
            continue
        chave = chave_pregao(x["orgaoEntidade"]["cnpj"], x["anoCompra"], x["numeroCompra"], x["dataAberturaProposta"])
        if chave in chaves:
            duplicadas.append((x, chaves[chave]))
            continue
        if chave:
            chaves[chave] = x["numeroControlePNCP"]
        novas.append(x)
    return novas, duplicadas, na_base


def ler_jsonl_gz(arquivo):
    """Linhas JSON do arquivo. Para na primeira linha cortada, de uma gravação interrompida."""
    try:
        with gzip.open(arquivo, "rt", encoding="utf-8") as f:
            for linha in f:
                yield json.loads(linha)
    except (EOFError, gzip.BadGzipFile, zlib.error, json.JSONDecodeError):
        return


def resultado_principal(resultados):
    """O resultado ativo que representa o item, pela ordem de registro_principal; None se não houver."""
    ativos = [r for r in resultados if r.get("situacaoCompraItemResultadoNome") != "Cancelado"
              and not r.get("dataCancelamento")]
    ativos.sort(key=lambda r: r.get("valorUnitarioHomologado") or 0)
    ativos.sort(key=lambda r: r.get("quantidadeHomologada") or 0, reverse=True)
    ativos.sort(key=lambda r: r.get("dataAtualizacao") or "", reverse=True)
    ativos.sort(key=lambda r: (r.get("valorUnitarioHomologado") or 0) > 0, reverse=True)
    return ativos[0] if ativos else None


def linha_compra(x, itens):
    unidade, orgao = x.get("unidadeOrgao") or {}, x.get("orgaoEntidade") or {}
    usuario, codigo = x.get("usuarioNome"), unidade.get("codigoUnidade")
    ibge = unidade.get("codigoIbge")
    return {
        "numero_controle_pncp": x["numeroControlePNCP"], "uasg": codigo if usuario == PLATAFORMA_UASG else None,
        "numero_compra": x.get("numeroCompra"), "ano_compra": x.get("anoCompra"), "orgao_cnpj": orgao.get("cnpj"),
        "orgao_nome": orgao.get("razaoSocial"), "esfera": orgao.get("esferaId"), "poder": orgao.get("poderId"),
        "uf": unidade.get("ufSigla"), "municipio": unidade.get("municipioNome"),
        "codigo_ibge": int(ibge) if str(ibge or "").isdigit() else None, "modalidade_nome": x.get("modalidadeNome"),
        "modo_disputa": x.get("modoDisputaNome"), "srp": int(bool(x.get("srp"))),
        "existe_resultado": int(any(resultado_principal(i.get("resultados") or []) for i in itens)),
        "valor_total_estimado": x.get("valorTotalEstimado"), "valor_total_homologado": x.get("valorTotalHomologado"),
        "data_publicacao": x.get("dataPublicacaoPncp"), "data_abertura_proposta": x.get("dataAberturaProposta"),
        "ano_publicacao": int(x["dataPublicacaoPncp"][:4]), "objeto_compra": x.get("objetoCompra"), "fonte": "pncp",
        "usuario_nome": usuario, "codigo_unidade": codigo, "nome_unidade": unidade.get("nomeUnidade"),
        "situacao_compra": x.get("situacaoCompraNome"),
    }


def linha_item(controle, uasg, i):
    """Uma linha por item, já como registro principal; os demais resultados ficam em `resultados`."""
    r = resultado_principal(i.get("resultados") or []) or {}
    situacao = i.get("situacaoCompraItemNome")
    return {
        "numero_controle_pncp": controle, "numero_item": i["numeroItem"], "registro_principal": 1, "uasg_item": uasg,
        "material_ou_servico": i.get("materialOuServico"), "unidade_medida": i.get("unidadeMedida"),
        "descricao_resumida": i.get("descricao"), "criterio_julgamento": i.get("criterioJulgamentoNome"),
        "tipo_beneficio": i.get("tipoBeneficioNome"), "orcamento_sigiloso": int(bool(i.get("orcamentoSigiloso"))),
        "situacao_item": situacao, "homologado": int(situacao == "Homologado"), "quantidade": i.get("quantidade"),
        "valor_unitario_estimado": i.get("valorUnitarioEstimado"), "tem_resultado": 1 if r else None,
        "quantidade_resultado": r.get("quantidadeHomologada"), "valor_unitario_resultado": r.get("valorUnitarioHomologado"),
        "valor_total_resultado": r.get("valorTotalHomologado"), "data_resultado": r.get("dataResultado"),
        "data_atualizacao": i.get("dataAtualizacao"), "cod_fornecedor": r.get("niFornecedor"),
        "nome_fornecedor": r.get("nomeRazaoSocialFornecedor"),
    }


def linha_resultado(controle, r):
    return [controle, r.get("numeroItem"), r.get("sequencialResultado"), None, r.get("situacaoCompraItemResultadoNome"),
            r.get("motivoCancelamento"), r.get("niFornecedor"), r.get("nomeRazaoSocialFornecedor"),
            r.get("porteFornecedorNome"), r.get("quantidadeHomologada"), r.get("valorUnitarioHomologado"),
            r.get("valorTotalHomologado"), r.get("dataResultado"), r.get("dataAtualizacao"), r.get("dataCancelamento")]


def _inserir_dict(con, tabela, linhas):
    if linhas:
        colunas = list(linhas[0])
        con.executemany(f"INSERT INTO {tabela} ({', '.join(colunas)}) VALUES ({', '.join('?' * len(colunas))})",
                        [[l[c] for c in colunas] for l in linhas])


def arquivos_pncp(mes):
    pasta = BRUTOS_PNCP / mes[:4]
    return pasta / f"contratacoes_{mes}.json.gz", pasta / f"itens_{mes}.jsonl.gz"


def carregar_mes_pncp(con, mes):
    """Carrega um mês de dados/brutos_pncp/ numa única transação; devolve o resumo gravado."""
    contratacoes, detalhes = arquivos_pncp(mes)
    with gzip.open(contratacoes, "rt", encoding="utf-8") as f:
        registros = json.load(f)
    novas, duplicadas, na_base = separar_novas(con, registros)
    pendentes = {x["numeroControlePNCP"]: x for x in novas}
    itens = resultados = sem_itens = 0
    with con:
        con.executemany("INSERT OR REPLACE INTO compras_duplicadas VALUES (?, ?, ?, ?)",
                        [(x["numeroControlePNCP"], irma, x.get("usuarioNome"), mes) for x, irma in duplicadas])
        for d in ler_jsonl_gz(detalhes):
            x = pendentes.pop(d["numeroControlePNCP"], None)
            if x is None:
                continue
            compra = linha_compra(x, d["itens"])
            _inserir_dict(con, "compras", [compra])
            _inserir_dict(con, "itens", [linha_item(compra["numero_controle_pncp"], compra["uasg"], i) for i in d["itens"]])
            linhas = [linha_resultado(compra["numero_controle_pncp"], r) for i in d["itens"] for r in i.get("resultados") or []]
            con.executemany(f"INSERT OR REPLACE INTO resultados VALUES ({', '.join('?' * len(RESULTADOS))})", linhas)
            itens += len(d["itens"])
            resultados += len(linhas)
            sem_itens += not d["itens"]
        _inserir_dict(con, "compras", [linha_compra(x, []) for x in pendentes.values()])
        sem_itens += len(pendentes)
        resumo = {"mes": mes, "publicadas": len(registros), "ja_na_base": na_base, "duplicadas": len(duplicadas),
                  "novas": len(novas), "itens": itens, "resultados": resultados, "sem_itens": sem_itens,
                  "carregado_em": datetime.now().isoformat(timespec="seconds")}
        con.execute("DELETE FROM coleta_pncp_meses WHERE mes = ?", (mes,))
        _inserir_dict(con, "coleta_pncp_meses", [resumo])
    return resumo


def carregar_pncp(con):
    """Carrega os meses completos de dados/brutos_pncp/ que ainda não estão no banco."""
    preparar_pncp(con)
    feitos = {x[0] for x in con.execute("SELECT mes FROM coleta_pncp_meses")}
    for f in sorted(BRUTOS_PNCP.glob("20*/itens_*.completo")):
        mes = f.name[len("itens_"):-len(".completo")]
        if mes not in feitos:
            print(carregar_mes_pncp(con, mes), flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--recriar", action="store_true", help="sobrescreve o banco existente, inclusive as colunas de lance")
    p.add_argument("--resultados", action="store_true", help="só recarrega a tabela resultados no banco existente")
    p.add_argument("--pncp", action="store_true", help="só carrega no banco existente os meses do PNCP que faltam")
    args = p.parse_args()
    if args.resultados or args.pncp:
        con = sqlite3.connect(DESTINO)
        (carregar_resultados if args.resultados else carregar_pncp)(con)
        con.close()
        return
    if DESTINO.exists() and not args.recriar:
        sys.exit(f"{DESTINO} já existe. Use --recriar para sobrescrever (apaga as colunas de lance já carregadas).")

    temporario = DESTINO.with_suffix(".db.tmp")
    temporario.unlink(missing_ok=True)
    con = sqlite3.connect(temporario)
    con.execute("PRAGMA journal_mode = OFF")
    con.execute("PRAGMA synchronous = OFF")
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(ESQUEMA)
    carregar_compras(con)
    con.commit()
    carregar_itens(con)
    print("marcando registros principais e criando índices...", flush=True)
    con.executescript(POS_CARGA)
    con.commit()
    carregar_resultados(con)
    carregar_pncp(con)
    con.close()
    os.replace(temporario, DESTINO)
    print(f"pronto: {DESTINO} ({DESTINO.stat().st_size / 2**30:.2f} GiB)")


if __name__ == "__main__":
    main()
