"""Infraestrutura comum: caminhos, conexão somente leitura com snapshot, impressão digital do banco,
registro de etapas e escrita determinística de CSV. Sem efeito colateral ao importar."""
import csv
import hashlib
import json
import os
import platform
import sqlite3
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent            # .../cesta
PASTA = AQUI.parent                                # .../cesta_padronizada_20261124
REPO = PASTA.parents[1]                            # .../PNCP-Automation
WORKSPACE = REPO.parent                            # .../PNCP(arquivos)


class ErroEstrutural(RuntimeError):
    """Inconsistência que impede junção ou contagem confiável: a execução deve parar."""


def carregar_parametros(caminho=None):
    caminho = Path(caminho or PASTA / "config" / "parametros.json")
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def resolver_caminhos(par, db=None, brutos=None, trabalho=None):
    c = par["caminhos"]
    def r(valor, env, padrao):
        v = valor or os.environ.get(env) or padrao
        p = Path(v)
        return p if p.is_absolute() else (WORKSPACE / p)
    return {"db": r(db, "PNCP_DB", c["db"]).resolve(),
            "brutos": r(brutos, "PNCP_BRUTOS", c["brutos"]).resolve(),
            "trabalho": r(trabalho, "CESTA_TRABALHO", c["trabalho"]).resolve()}


# ------------------------------------------------------------------------------------- banco de origem

def conectar_ro(caminho):
    """Conexão SQLite estritamente somente leitura (mode=ro). Recusa arquivo inexistente."""
    caminho = Path(caminho)
    if not caminho.is_file():
        raise FileNotFoundError(f"banco não encontrado: {caminho}")
    con = sqlite3.connect(f"{caminho.resolve().as_uri()}?mode=ro", uri=True, isolation_level=None)
    con.execute("PRAGMA query_only = 1")
    return con


def abrir_snapshot(con):
    """Inicia uma transação de leitura e adquire o bloqueio compartilhado imediatamente, de modo que
    todas as leituras seguintes vejam o mesmo estado do banco (snapshot)."""
    con.execute("BEGIN")
    con.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()


def fechar_snapshot(con):
    try:
        con.execute("COMMIT")
    except sqlite3.OperationalError:
        pass


def impressao_digital(caminho, mb_amostra=64):
    """Identificador do snapshot sem ler os 16 GB: tamanho, mtime, contador de alterações do cabeçalho
    SQLite (bytes 24-27), versão do esquema (40-43) e SHA-256 do início e do fim do arquivo."""
    caminho = Path(caminho)
    st = caminho.stat()
    n = mb_amostra * 1024 * 1024
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        cab = f.read(100)
        f.seek(0)
        h.update(f.read(n))
        if st.st_size > n:
            f.seek(max(st.st_size - n, n))
            h.update(f.read(n))
    return {
        "caminho": str(caminho),
        "tamanho_bytes": st.st_size,
        "mtime_ns": st.st_mtime_ns,
        "mtime_iso": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(st.st_mtime)),
        "sqlite_contador_alteracoes": int.from_bytes(cab[24:28], "big") if len(cab) >= 28 else None,
        "sqlite_cookie_esquema": int.from_bytes(cab[40:44], "big") if len(cab) >= 44 else None,
        "sha256_inicio_fim": h.hexdigest(),
        "amostra_mb": mb_amostra,
    }


def conferir_inalterado(antes, caminho):
    depois = impressao_digital(caminho, antes["amostra_mb"])
    chaves = ["tamanho_bytes", "mtime_ns", "sqlite_contador_alteracoes", "sha256_inicio_fim"]
    dif = {k: (antes[k], depois[k]) for k in chaves if antes[k] != depois[k]}
    if dif:
        raise ErroEstrutural(f"o banco de origem mudou durante a execução: {dif}")
    return depois


def sha256_arquivo(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def ambiente():
    return {"python": sys.version, "sqlite": sqlite3.sqlite_version, "plataforma": platform.platform(),
            "executavel": sys.executable}


# ------------------------------------------------------------------------------------- banco de trabalho

def conectar_trabalho(caminho):
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(caminho, isolation_level=None)
    con.execute("PRAGMA journal_mode = OFF")
    con.execute("PRAGMA synchronous = OFF")
    # Ordenações temporárias em ARQUIVO (não em RAM): os GROUP BY/COUNT(DISTINCT) sobre milhões de linhas
    # esgotavam a memória da máquina (7,9 GB). Os temporários ficam na pasta do banco de trabalho.
    con.execute("PRAGMA temp_store = FILE")
    try:
        con.execute(f"PRAGMA temp_store_directory = '{caminho.parent.resolve().as_posix()}'")
    except sqlite3.DatabaseError:
        pass
    con.execute("PRAGMA cache_size = -100000")
    return con


# ------------------------------------------------------------------------------------- registro

class Registro:
    """Registro das etapas: tempos, contagens intermediárias e consultas principais."""

    def __init__(self, verboso=True):
        self.etapas, self.contagens, self.consultas, self.avisos = [], {}, {}, []
        self.verboso = verboso
        self._t0 = time.time()

    def etapa(self, nome):
        reg = self

        class _Ctx:
            def __enter__(self_):
                self_.t = time.time()
                if reg.verboso:
                    print(f"[{time.strftime('%H:%M:%S')}] {nome} ...", flush=True)
                return self_

            def __exit__(self_, *exc):
                dt = time.time() - self_.t
                reg.etapas.append({"etapa": nome, "segundos": round(dt, 2), "ok": exc[0] is None})
                if reg.verboso:
                    print(f"[{time.strftime('%H:%M:%S')}]   {nome}: {dt:.1f} s", flush=True)
                return False
        return _Ctx()

    def contar(self, chave, valor):
        self.contagens[chave] = valor

    def consulta(self, nome, sql):
        self.consultas[nome] = " ".join(sql.split())

    def aviso(self, texto):
        self.avisos.append(texto)
        if self.verboso:
            print("  AVISO:", texto, flush=True)

    def total(self):
        return round(time.time() - self._t0, 2)


# ------------------------------------------------------------------------------------- saídas

def escrever_csv(caminho, linhas, colunas):
    """CSV UTF-8 (com BOM, para abrir no Excel), separador vírgula, ordem das linhas preservada."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(colunas)
        for x in linhas:
            w.writerow(["" if x.get(c) is None else x.get(c) for c in colunas] if isinstance(x, dict)
                       else ["" if v is None else v for v in x])
    return caminho


def escrever_json(caminho, obj):
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, default=str)
    return caminho


def consulta_csv(con, sql, caminho, params=(), lote=50000):
    """Exporta o resultado de uma consulta para CSV em lotes (sem carregar tudo em memória)."""
    cur = con.execute(sql, params)
    colunas = [d[0] for d in cur.description]
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(caminho, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(colunas)
        while True:
            bloco = cur.fetchmany(lote)
            if not bloco:
                break
            w.writerows([["" if v is None else v for v in r] for r in bloco])
            n += len(bloco)
    return n
