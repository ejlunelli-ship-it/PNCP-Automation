"""Descrição detalhada dos itens a partir dos CSVs brutos da API Dados Abertos (somente leitura).

O pncp.db guarda em `descricao_resumida` apenas o nome do item no catálogo (nível PDM) para a fonte
dados_abertos; a descrição completa (`descricaodetalhada`) e o nome do PDM (`nomePdm`) só existem nos
arquivos `dados/brutos/<ano>/itens_pregao_*.csv`, que são a origem da carga do banco
(banco_unificado.py). A ligação é feita pela chave composta do item e conferida em cardinalidade:
cada item do banco deve ter exatamente o mesmo número de registros nos brutos.
"""
import glob
import hashlib
import io
from pathlib import Path

import pandas as pd

from .comum import ErroEstrutural
from .normalizacao import chave_textual, normalizar_catmat, normalizar_texto

COLUNAS = {"numeroControlePNCPCompra": "chave", "numeroItemPncp": "numero_item", "idCompraItem": "id_compra_item",
           "codItemCatalogo": "catmat_bruto", "materialOuServico": "ms_bruto", "unidadeMedida": "unidade_bruta",
           "descricaodetalhada": "descricao_detalhada", "nomePdm": "nome_pdm", "codigoPdm": "pdm_bruto"}

DDL = """
DROP TABLE IF EXISTS brutos_arquivos;
CREATE TABLE brutos_arquivos (arquivo TEXT PRIMARY KEY, tamanho INTEGER, sha256 TEXT, linhas INTEGER,
    colunas_ausentes TEXT);
DROP TABLE IF EXISTS brutos_itens;
CREATE TABLE brutos_itens (chave TEXT, numero_item INTEGER, id_compra_item TEXT, catmat INTEGER, ms TEXT,
    unidade_bruta TEXT, descricao_detalhada TEXT, nome_pdm TEXT, arquivo TEXT);
"""


def arquivos(pasta_brutos):
    """Mesma ordem e padrão de banco_unificado.carregar_itens."""
    return sorted(glob.glob(str(Path(pasta_brutos) / "20*" / "itens_pregao_*.csv")))


def carregar(dst, pasta_brutos, reg, tamanho_lote=200_000):
    dst.executescript(DDL)
    fs = arquivos(pasta_brutos)
    if not fs:
        raise ErroEstrutural(f"nenhum itens_pregao_*.csv em {pasta_brutos}")
    total = 0
    with reg.etapa(f"brutos: leitura de {len(fs)} arquivos de itens"):
        for f in fs:
            dados = Path(f).read_bytes()
            sha = hashlib.sha256(dados).hexdigest()
            cab = pd.read_csv(io.BytesIO(dados), nrows=0, encoding="utf-8-sig").columns
            ausentes = [c for c in COLUNAS if c not in cab]
            if any(c in ausentes for c in ["numeroControlePNCPCompra", "numeroItemPncp", "descricaodetalhada"]):
                raise ErroEstrutural(f"{f}: colunas essenciais ausentes {ausentes}")
            n = 0
            leitor = pd.read_csv(io.BytesIO(dados), usecols=lambda c: c in COLUNAS, dtype=str,
                                 encoding="utf-8-sig", keep_default_na=False, na_values=[""],
                                 chunksize=tamanho_lote)
            rel = str(Path(f).relative_to(Path(pasta_brutos)))
            for df in leitor:
                df = df.rename(columns=COLUNAS)
                for c in COLUNAS.values():
                    if c not in df:
                        df[c] = None
                df = df.astype(object).where(df.notna(), None)
                linhas = [(r.chave, int(float(r.numero_item)) if r.numero_item is not None else None, r.id_compra_item,
                           normalizar_catmat(r.catmat_bruto), r.ms_bruto, r.unidade_bruta, r.descricao_detalhada,
                           r.nome_pdm, rel) for r in df.itertuples(index=False)]
                dst.executemany("INSERT INTO brutos_itens VALUES (?,?,?,?,?,?,?,?,?)", linhas)
                n += len(linhas)
            dst.execute("INSERT INTO brutos_arquivos VALUES (?,?,?,?,?)",
                        (rel, len(dados), sha, n, ",".join(ausentes)))
            total += n
            del dados
        reg.contar("brutos_linhas", total)
    with reg.etapa("brutos: índice"):
        dst.execute("CREATE INDEX ix_bi_item ON brutos_itens (chave, numero_item)")


def ligar(dst, reg):
    """Agrega a descrição detalhada por item e confere a cardinalidade contra o banco."""
    with reg.etapa("brutos: ligação e conferência de cardinalidade"):
        dst.executescript("""
            DROP TABLE IF EXISTS brutos_por_item;
            CREATE TABLE brutos_por_item AS
            SELECT chave, numero_item, COUNT(*) AS registros_brutos,
                   COUNT(DISTINCT COALESCE(descricao_detalhada, '')) AS n_descricoes,
                   MIN(descricao_detalhada) AS descricao_detalhada, MAX(descricao_detalhada) AS descricao_detalhada_max,
                   MIN(nome_pdm) AS nome_pdm, MIN(catmat) AS catmat_bruto, MIN(unidade_bruta) AS unidade_bruta,
                   COUNT(DISTINCT COALESCE(catmat, -1)) AS n_catmat_bruto
            FROM brutos_itens GROUP BY chave, numero_item;
            CREATE UNIQUE INDEX ix_bpi ON brutos_por_item (chave, numero_item);
            DROP TABLE IF EXISTS ligacao_divergencias;
            CREATE TABLE ligacao_divergencias AS
            SELECT i.chave, i.numero_item, i.registros, b.registros_brutos, i.catmat, b.catmat_bruto,
                   i.unidade_original, b.unidade_bruta,
                   CASE WHEN b.chave IS NULL THEN 'sem_bruto'
                        WHEN b.registros_brutos <> i.registros THEN 'cardinalidade'
                        WHEN COALESCE(b.catmat_bruto, -1) <> COALESCE(i.catmat, -1) THEN 'catmat_diverge'
                        WHEN COALESCE(b.unidade_bruta, '') <> COALESCE(i.unidade_original, '') THEN 'unidade_diverge'
                   END AS tipo
            FROM itens i LEFT JOIN brutos_por_item b USING (chave, numero_item)
            WHERE b.chave IS NULL OR b.registros_brutos <> i.registros
               OR COALESCE(b.catmat_bruto, -1) <> COALESCE(i.catmat, -1)
               OR COALESCE(b.unidade_bruta, '') <> COALESCE(i.unidade_original, '');
        """)
        n_brutos_itens = dst.execute("SELECT COUNT(*) FROM brutos_por_item").fetchone()[0]
        sem_banco = dst.execute("SELECT COUNT(*) FROM brutos_por_item b LEFT JOIN itens i USING (chave, numero_item) "
                                "WHERE i.chave IS NULL").fetchone()[0]
        tipos = dict(dst.execute("SELECT tipo, COUNT(*) FROM ligacao_divergencias GROUP BY 1").fetchall())
        reg.contar("brutos_itens_distintos", n_brutos_itens)
        reg.contar("brutos_itens_sem_banco", sem_banco)
        reg.contar("ligacao_divergencias", tipos)
        reg.contar("itens_com_mais_de_uma_descricao_detalhada",
                   dst.execute("SELECT COUNT(*) FROM brutos_por_item WHERE n_descricoes > 1").fetchone()[0])
        if tipos.get("sem_bruto", 0) or tipos.get("cardinalidade", 0) or tipos.get("catmat_diverge", 0):
            raise ErroEstrutural(f"ligação banco × brutos não confiável: {tipos} (ver tabela ligacao_divergencias)")
        if tipos.get("unidade_diverge", 0):
            reg.aviso(f"{tipos['unidade_diverge']} itens com unidade diferente entre banco e bruto (ver ligacao_divergencias)")


def chaves_descricao(dst, reg):
    """Descrições distintas (original exata) com normalizações; base da auditoria de homogeneidade."""
    with reg.etapa("descrições: normalização das variantes distintas"):
        dst.executescript("""
            DROP TABLE IF EXISTS descricoes;
            CREATE TABLE descricoes (descricao_original TEXT PRIMARY KEY, descricao_norm TEXT, chave_textual TEXT);""")
        cur = dst.execute("SELECT DISTINCT descricao_detalhada FROM brutos_por_item WHERE descricao_detalhada IS NOT NULL")
        n = 0
        while True:
            bloco = cur.fetchmany(100_000)
            if not bloco:
                break
            dst.executemany("INSERT INTO descricoes VALUES (?,?,?)",
                            [(d, normalizar_texto(d), chave_textual(d)) for (d,) in bloco])
            n += len(bloco)
        reg.contar("descricoes_originais_distintas", n)
