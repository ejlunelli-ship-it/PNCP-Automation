"""Gravação no SQLite: tabela `itens`, uma linha por item (uasg, numero_compra, item).

Cada execução atualiza os itens processados (INSERT OR REPLACE) e mantém os demais, então o banco
acumula execuções feitas em pastas ou períodos diferentes. Colunas novas do modelo são adicionadas
a um banco já existente.
"""

import sqlite3
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from .validacao import COLUNAS, RegistroExtracao

TABELA = "itens"
CHAVE = ("uasg", "numero_compra", "item")


def _tipo(campo):
    anotacao = str(RegistroExtracao.model_fields[campo].annotation)
    if "Decimal" in anotacao:
        return "NUMERIC"
    if "int" in anotacao or "bool" in anotacao:
        return "INTEGER"
    return "TEXT"


def _valor(v):
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, datetime):
        return v.isoformat(sep=" ")
    if isinstance(v, bool):
        return int(v)
    return v


def gravar_sqlite(registros, destino):
    """Grava os registros com chave completa; devolve (gravados, ignorados sem chave)."""
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    linhas = [r.model_dump() for r in registros]
    com_chave = [l for l in linhas if all(l.get(c) is not None for c in CHAVE)]

    with sqlite3.connect(destino) as con:
        definicoes = ", ".join(f"{c} {_tipo(c)}" for c in COLUNAS)
        con.execute(f"CREATE TABLE IF NOT EXISTS {TABELA} ({definicoes}, PRIMARY KEY ({', '.join(CHAVE)}))")
        existentes = {linha[1] for linha in con.execute(f"PRAGMA table_info({TABELA})")}
        for c in COLUNAS:
            if c not in existentes:
                con.execute(f"ALTER TABLE {TABELA} ADD COLUMN {c} {_tipo(c)}")
        con.executemany(
            f"INSERT OR REPLACE INTO {TABELA} ({', '.join(COLUNAS)}) VALUES ({', '.join('?' * len(COLUNAS))})",
            [[_valor(l[c]) for c in COLUNAS] for l in com_chave],
        )
    return len(com_chave), len(linhas) - len(com_chave)
