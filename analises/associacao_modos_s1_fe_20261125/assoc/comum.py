"""Caminhos, hashes e E/S (reaproveita, sem modificar, utilidades do estudo risk-set e do estudo original)."""
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
PASTA = AQUI.parent
REPO = PASTA.parents[1]
ORIGINAL = REPO / "analises" / "efeito_modos_cesta_padronizada_20261124"
RISK = REPO / "analises" / "risk_set_matching_s1_20261125"
for p in (ORIGINAL, RISK):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from scripts.comum import (ErroDesenho, Log, agora, escrever_csv, escrever_json, hash_df, ler_csv, ler_json,  # noqa: E402,F401
                           ler_pkl, nome_tri, resolver, salvar_pkl, sha, tri)
import json  # noqa: E402

TAB, RES, GRA = PASTA / "tabelas", PASTA / "resultados", PASTA / "graficos"


def cfg():
    return json.loads((PASTA / "config.json").read_text(encoding="utf-8"))


def trabalho(c, nome):
    p = Path(c["trabalho"]) / nome
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def hashes_codigo():
    return {p.name: sha(p) for p in sorted(AQUI.glob("*.py"))} | {"config.json": sha(PASTA / "config.json")}
