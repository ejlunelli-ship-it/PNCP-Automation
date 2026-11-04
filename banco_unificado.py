"""Banco SQLite unificado da base nacional: dados/pncp.db, a partir de dados/brutos/<ano>/.

Tabelas: compras (uma linha por numeroControlePNCP) e itens (uma linha por registro da API).
View: analise_itens (só registro_principal = 1), com os descontos em % e o filtro `elegivel`.

Um item pode ter mais de um registro na API (idCompraItem duplicado ou mais de um resultado).
`registro_principal` marca um por item: homologado, com valor de resultado, atualização mais recente.

As colunas de lance por etapa (melhor_lance_*, etc.) nascem vazias e vêm dos PDFs. Como recriar o
banco apaga o que estiver nelas, o script só sobrescreve um banco existente com --recriar.

A tabela resultados vem de coleta_resultados.py. Depois da coleta, --resultados a carrega no banco
existente, sem mexer nas outras tabelas.

Uso: python banco_unificado.py [--recriar | --resultados]
"""
import argparse
import glob
import json
import os
import sqlite3
import sys

import pandas as pd

from config import DADOS

BRUTOS = DADOS / "brutos"
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
    """Refaz a tabela resultados. Um resultado pode aparecer em mais de um mês: vale o mais recente."""
    con.executescript("""
        DROP TABLE IF EXISTS resultados;
        CREATE TABLE resultados (
            numero_controle_pncp TEXT NOT NULL, numero_item INTEGER NOT NULL, sequencial_resultado INTEGER NOT NULL,
            id_compra_item TEXT, situacao_resultado TEXT, motivo_cancelamento TEXT, ni_fornecedor TEXT,
            nome_fornecedor TEXT, porte_fornecedor TEXT, quantidade_homologada REAL, valor_unitario_homologado REAL,
            valor_total_homologado REAL, data_resultado TEXT, data_atualizacao TEXT, data_cancelamento TEXT,
            PRIMARY KEY (numero_controle_pncp, numero_item, sequencial_resultado));
    """)
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


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--recriar", action="store_true", help="sobrescreve o banco existente, inclusive as colunas de lance")
    p.add_argument("--resultados", action="store_true", help="só recarrega a tabela resultados no banco existente")
    args = p.parse_args()
    if args.resultados:
        con = sqlite3.connect(DESTINO)
        carregar_resultados(con)
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
    con.close()
    os.replace(temporario, DESTINO)
    print(f"pronto: {DESTINO} ({DESTINO.stat().st_size / 2**30:.2f} GiB)")


if __name__ == "__main__":
    main()
