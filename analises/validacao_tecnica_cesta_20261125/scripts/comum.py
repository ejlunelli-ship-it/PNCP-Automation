"""Infraestrutura comum (só biblioteca-padrão): caminhos, configuração, hashes, CSV, SQLite somente leitura."""
import csv
import datetime as dt
import hashlib
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
PASTA = AQUI.parent                                   # analises/validacao_tecnica_cesta_20261125
REPO = PASTA.parents[1]                               # PNCP-Automation
VERSAO = "1.0.0"
CODIF = "utf-8-sig"

csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))


class ErroEstrutural(RuntimeError):
    """Erro que interrompe a execução: chave ambígua, arquivo alterado, formulário adulterado etc."""


# ----------------------------------------------------------------------------------------------- configuração
def carregar_json(caminho):
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def carregar_config(pasta_config=None):
    pc = Path(pasta_config) if pasta_config else PASTA / "config"
    return {"parametros": carregar_json(pc / "parametros.json"), "mapa": carregar_json(pc / "mapa_colunas.json"),
            "regras": carregar_json(pc / "regras_atributos.json"), "pasta_config": pc}


def resolver(caminho, base=None):
    p = Path(caminho)
    return p if p.is_absolute() else ((Path(base) if base else REPO) / p)


# ----------------------------------------------------------------------------------------------- hashes
def sha256_arquivo(caminho, bloco=1 << 20):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for b in iter(lambda: f.read(bloco), b""):
            h.update(b)
    return h.hexdigest()


def sha256_texto(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def sha256_json(obj):
    return sha256_texto(json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")))


def impressao_digital(caminho, amostra_mb=64):
    """Impressão digital barata de um banco grande: tamanho, mtime, contador de alterações do cabeçalho SQLite
    e SHA-256 do primeiro e do último bloco. Não abre o arquivo para escrita."""
    p = Path(caminho)
    if not p.is_file():
        return {"caminho": str(p), "existe": False}
    st = p.stat()
    n = amostra_mb << 20
    h = hashlib.sha256()
    with open(p, "rb") as f:
        cab = f.read(100)
        f.seek(0)
        h.update(f.read(n))
        if st.st_size > n:
            f.seek(max(st.st_size - n, n))
            h.update(f.read(n))
    contador = int.from_bytes(cab[24:28], "big") if cab[:16] == b"SQLite format 3\x00" else None
    return {"caminho": str(p), "existe": True, "tamanho_bytes": st.st_size, "mtime_ns": st.st_mtime_ns,
            "sqlite_contador_alteracoes": contador, "sha256_inicio_fim": h.hexdigest(), "amostra_mb": amostra_mb}


def conferir_inalterado(antes, depois):
    chaves = ("existe", "tamanho_bytes", "mtime_ns", "sqlite_contador_alteracoes", "sha256_inicio_fim")
    dif = [k for k in chaves if antes.get(k) != depois.get(k)]
    if dif:
        raise ErroEstrutural(f"banco de origem alterado durante a execução ({antes.get('caminho')}): {dif}")
    return True


# ----------------------------------------------------------------------------------------------- SQLite
def conectar_ro(caminho):
    p = Path(caminho)
    if not p.is_file():
        raise ErroEstrutural(f"banco não encontrado: {p}")
    con = sqlite3.connect(f"{p.resolve().as_uri()}?mode=ro", uri=True, isolation_level=None)
    con.execute("PRAGMA query_only = 1")
    return con


def conectar_trabalho(caminho):
    p = Path(caminho)
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(p.resolve().as_uri(), uri=True, isolation_level=None)
    for pr in ("journal_mode = OFF", "synchronous = OFF", "temp_store = FILE", "cache_size = -200000"):
        con.execute(f"PRAGMA {pr}")
    return con


def anexar_ro(con, caminho, alias):
    p = Path(caminho)
    if not p.is_file():
        raise ErroEstrutural(f"banco não encontrado: {p}")
    con.execute(f"ATTACH DATABASE ? AS {alias}", (f"{p.resolve().as_uri()}?mode=ro",))


# ----------------------------------------------------------------------------------------------- CSV
def cabecalho_csv(caminho):
    with open(caminho, encoding=CODIF, newline="") as f:
        return next(csv.reader(f))


def ler_csv(caminho, colunas=None, lote=None):
    """Itera linhas como dict; com `colunas`, devolve só essas (erro se faltar alguma). Leitura incremental."""
    with open(caminho, encoding=CODIF, newline="") as f:
        r = csv.DictReader(f)
        if colunas is not None:
            falta = [c for c in colunas if c not in (r.fieldnames or [])]
            if falta:
                raise ErroEstrutural(f"{Path(caminho).name}: colunas ausentes {falta}")
        for i, linha in enumerate(r, start=2):            # linha 1 = cabeçalho
            if colunas is not None:
                linha = {c: linha[c] for c in colunas}
            linha["__linha"] = i
            yield linha


def escrever_csv(caminho, linhas, colunas):
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tmp = caminho.with_suffix(caminho.suffix + ".tmp")
    n = 0
    with open(tmp, "w", encoding=CODIF, newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(colunas)
        for x in linhas:
            w.writerow([_fmt(x.get(c)) for c in colunas])
            n += 1
    os.replace(tmp, caminho)
    return n


def _fmt(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, float):
        return repr(round(v, 10)) if v == v else ""
    if isinstance(v, (list, tuple, dict)):
        return json.dumps(v, ensure_ascii=False, sort_keys=isinstance(v, dict))
    return v


def escrever_json(caminho, obj):
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tmp = caminho.with_suffix(caminho.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=False)
        f.write("\n")
    os.replace(tmp, caminho)
    return caminho


# ----------------------------------------------------------------------------------------------- diversos
def agora():
    return dt.datetime.now().replace(microsecond=0).isoformat()


def hoje():
    return dt.date.today().isoformat()


def proibida(coluna, padroes):
    c = coluna.lower()
    return any(re.search(p, c) for p in padroes)


class Registro:
    """Log simples de etapas e contagens (vai para manifesto/registro)."""

    def __init__(self, verboso=True):
        self.eventos, self.contagens, self.avisos, self.verboso = [], {}, [], verboso

    def log(self, msg):
        self.eventos.append({"em": agora(), "msg": msg})
        if self.verboso:
            print(f"[{dt.datetime.now():%H:%M:%S}] {msg}", flush=True)

    def contar(self, k, v):
        self.contagens[k] = v

    def aviso(self, msg):
        self.avisos.append(msg)
        if self.verboso:
            print("  AVISO:", msg, flush=True)
