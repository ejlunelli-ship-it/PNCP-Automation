"""Infraestrutura: caminhos, conexões somente leitura, impressão digital, registro e escrita."""
import csv
import gzip
import hashlib
import json
import os
import platform
import sqlite3
import sys
import time
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
PASTA = AQUI.parent
REPO = PASTA.parents[1]                       # PNCP-Automation
CESTA_PASTA = REPO / "analises" / "cesta_padronizada_20261124"
sys.path.insert(0, str(CESTA_PASTA))
from cesta.comum import ErroEstrutural, impressao_digital, conferir_inalterado, sha256_arquivo  # noqa: E402,F401


def carregar_config(caminho=None):
    with open(caminho or PASTA / "config.json", encoding="utf-8") as f:
        return json.load(f)


def resolver(cfg, **sobre):
    c = dict(cfg["caminhos"])
    c.update({k: v for k, v in sobre.items() if v})
    out = {}
    for k, v in c.items():
        if k.startswith("_"):
            continue
        p = Path(v)
        out[k] = (p if p.is_absolute() else REPO / p).resolve()
    return out


def conectar_ro(caminho):
    caminho = Path(caminho)
    if not caminho.is_file():
        raise FileNotFoundError(f"banco não encontrado: {caminho}")
    con = sqlite3.connect(f"{caminho.resolve().as_uri()}?mode=ro", uri=True, isolation_level=None)
    con.execute("PRAGMA query_only = 1")
    return con


def conectar_trabalho(caminho):
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    # aberta em modo URI para permitir ATTACH ... ?mode=ro das fontes
    con = sqlite3.connect(caminho.resolve().as_uri(), isolation_level=None, uri=True)
    for p in ("journal_mode = OFF", "synchronous = OFF", "temp_store = FILE", "cache_size = -100000"):
        con.execute(f"PRAGMA {p}")
    try:
        con.execute(f"PRAGMA temp_store_directory = '{caminho.parent.resolve().as_posix()}'")
    except sqlite3.DatabaseError:
        pass
    return con


def anexar_ro(con, caminho, alias):
    """ATTACH somente leitura (URI mode=ro) num banco de trabalho."""
    uri = f"{Path(caminho).resolve().as_uri()}?mode=ro"
    con.execute(f"ATTACH DATABASE ? AS {alias}", (uri,))


def ambiente():
    import scipy
    import pandas
    return {"python": sys.version, "sqlite": sqlite3.sqlite_version, "numpy": np.__version__,
            "pandas": pandas.__version__, "scipy": scipy.__version__, "plataforma": platform.platform()}


class Registro:
    def __init__(self, verboso=True):
        self.etapas, self.contagens, self.avisos, self.consultas = [], {}, [], {}
        self.verboso, self.t0 = verboso, time.time()

    def etapa(self, nome):
        reg = self

        class _C:
            def __enter__(s):
                s.t = time.time()
                if reg.verboso:
                    print(f"[{time.strftime('%H:%M:%S')}] {nome} ...", flush=True)

            def __exit__(s, *e):
                dt = time.time() - s.t
                reg.etapas.append({"etapa": nome, "segundos": round(dt, 1), "ok": e[0] is None})
                if reg.verboso:
                    print(f"[{time.strftime('%H:%M:%S')}]   {nome}: {dt:.1f} s", flush=True)
                return False
        return _C()

    def contar(self, k, v):
        self.contagens[k] = v

    def aviso(self, t):
        self.avisos.append(t)
        if self.verboso:
            print("  AVISO:", t, flush=True)


def escrever_csv(caminho, linhas, colunas=None):
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    linhas = list(linhas)
    if colunas is None:
        # união das chaves de TODAS as linhas, na ordem em que aparecem (linhas heterogêneas não perdem colunas)
        colunas = []
        vistos = set()
        for x in linhas:
            for k in x.keys():
                if k not in vistos:
                    vistos.add(k)
                    colunas.append(k)
    with open(caminho, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(colunas)
        for x in linhas:
            w.writerow([_fmt(x.get(c)) for c in colunas])
    return caminho


def _fmt(v):
    if v is None:
        return ""
    if isinstance(v, (float, np.floating)):
        if not np.isfinite(v):
            return ""
        return repr(round(float(v), 10))
    if isinstance(v, (np.integer,)):
        return int(v)
    return v


def escrever_json(caminho, obj):
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    return caminho


def pct_exato(beta_lp):
    """Log-pontos (100·Δln) -> diferença percentual exata 100(exp(β/100) − 1)."""
    return 100.0 * (np.exp(np.asarray(beta_lp, dtype=float) / 100.0) - 1.0)


def trimestre_de(data_iso):
    """'AAAA-MM-DD' -> índice inteiro de trimestre (ano*4 + q-1); None se inválida."""
    if not data_iso or len(data_iso) < 7:
        return None
    try:
        a, m = int(data_iso[:4]), int(data_iso[5:7])
    except ValueError:
        return None
    if not (1 <= m <= 12):
        return None
    return a * 4 + (m - 1) // 3


def nome_trimestre(t):
    return f"{t // 4}T{t % 4 + 1}"


def mes_de(data_iso):
    try:
        return int(data_iso[:4]) * 12 + int(data_iso[5:7]) - 1
    except (TypeError, ValueError):
        return None
