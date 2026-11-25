"""Infraestrutura comum: caminhos, hashes, E/S, trimestres e checkpoints."""
import csv
import gzip
import hashlib
import io
import json
import pickle
import sys
import time
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
PASTA = AQUI.parent
REPO = PASTA.parents[1]
ORIGINAL = REPO / "analises" / "efeito_modos_cesta_padronizada_20261124"
if str(ORIGINAL) not in sys.path:
    sys.path.insert(0, str(ORIGINAL))


class ErroDesenho(RuntimeError):
    pass


def cfg(caminho=None):
    with open(caminho or PASTA / "config.json", encoding="utf-8") as f:
        return json.load(f)


def resolver(p):
    p = Path(p)
    return p if p.is_absolute() else REPO / p


def trabalho(c, *partes):
    p = Path(c["trabalho"]).joinpath(*partes)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def sha(p, bloco=1 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(bloco), b""):
            h.update(b)
    return h.hexdigest()


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def agora():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def tri(nome):
    """'2024T3' -> 2024*4+2."""
    return int(nome[:4]) * 4 + int(nome[-1]) - 1


def nome_tri(t):
    t = int(t)
    return f"{t // 4}T{t % 4 + 1}"


def _conv(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (set, frozenset)):
        return sorted(o)
    if isinstance(o, Path):
        return str(o)
    return str(o)


def _limpar(o):
    if isinstance(o, float) and not np.isfinite(o):
        return None
    if isinstance(o, dict):
        return {str(k): _limpar(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_limpar(v) for v in o]
    if isinstance(o, np.floating):
        return _limpar(float(o))
    return o


def escrever_json(p, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(_limpar(obj), ensure_ascii=False, indent=2, default=_conv) + "\n", encoding="utf-8")
    tmp.replace(p)
    return p


def ler_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _fmt(v):
    if v is None:
        return ""
    if isinstance(v, (bool, np.bool_)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        v = float(v)
        return "" if not np.isfinite(v) else repr(round(v, 10))
    if isinstance(v, np.integer):
        return int(v)
    return v


def escrever_csv(p, linhas, colunas=None):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    linhas = list(linhas)
    if colunas is None:
        colunas = []
        for x in linhas:
            for k in x:
                if k not in colunas:
                    colunas.append(k)
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(colunas)
        for x in linhas:
            w.writerow([_fmt(x.get(c)) for c in colunas])
    return p


def ler_csv(p):
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def salvar_pkl(p, obj):
    """Pickle comprimido determinístico (gzip com mtime = 0)."""
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with open(tmp, "wb") as fb, gzip.GzipFile(fileobj=fb, mode="wb", mtime=0, compresslevel=5) as g:
        pickle.dump(obj, g, protocol=5)
    tmp.replace(p)
    return p


def ler_pkl(p):
    with gzip.open(p, "rb") as g:
        return pickle.load(g)


def escrever_parquet(p, df):
    """Parquet (pyarrow) sem metadados variáveis; o conteúdo lógico é conferido por hash de CSV canônico."""
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(p, index=False, compression="zstd")
    return p


def hash_df(df):
    """Hash do conteúdo lógico (CSV canônico ordenado pelas colunas na ordem dada)."""
    buf = io.StringIO()
    df.to_csv(buf, index=False, float_format="%.10g", lineterminator="\n")
    return sha_bytes(buf.getvalue().encode("utf-8"))


class Log:
    def __init__(self, arquivo=None, verboso=True):
        self.arquivo, self.verboso = arquivo, verboso

    def __call__(self, msg):
        linha = f"[{agora()}] {msg}"
        if self.verboso:
            print(linha, flush=True)
        if self.arquivo:
            Path(self.arquivo).parent.mkdir(parents=True, exist_ok=True)
            with open(self.arquivo, "a", encoding="utf-8") as f:
                f.write(linha + "\n")


def hashes_codigo():
    return {p.name: sha(p) for p in sorted(AQUI.glob("*.py"))} | {"config.json": sha(PASTA / "config.json"),
                                                                  "executar.py": sha(PASTA / "executar.py")}
