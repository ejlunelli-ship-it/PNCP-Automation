"""Acesso controlado a fontes externas: cache imutável, controle de taxa, tentativas limitadas, hosts permitidos.

Cada consulta vira uma ENTRADA imutável (url, data, HTTP, SHA-256 do conteúdo, arquivo). O conteúdo fica em
`conteudo/<sha256>` (deduplicado); o índice `indice/<sha256(url)>.json` guarda o histórico de entradas da URL.
Uma URL já consultada com sucesso é reutilizada (não se baixa de novo); uma atualização explícita cria entrada nova,
sem apagar a antiga. Conteúdo externo é dado não confiável: só é lido como bytes/texto, nunca executado.
"""
import hashlib
import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def _agora():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


class LimitadorTaxa:
    def __init__(self, intervalo):
        self.intervalo, self.ultimo, self.trava = intervalo, 0.0, threading.Lock()

    def esperar(self):
        with self.trava:
            agora = time.monotonic()
            espera = self.ultimo + self.intervalo - agora
            if espera > 0:
                time.sleep(espera)
            self.ultimo = time.monotonic()


def baixar_http(url, cfg_fontes, limitador, max_bytes):
    """Busca real (urllib). Devolve (status_http, bytes|None, erro|None, cabecalhos)."""
    host = urllib.parse.urlparse(url).hostname or ""
    if not any(host == h or host.endswith("." + h) for h in cfg_fontes["hosts_permitidos"]):
        return None, None, f"host não permitido: {host}", {}
    ultimo_erro, status = None, None
    for t in range(cfg_fontes["tentativas"]):
        limitador.esperar()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": cfg_fontes["user_agent"], "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=cfg_fontes["timeout_segundos"]) as r:
                dados = r.read(max_bytes + 1)
                if len(dados) > max_bytes:
                    return r.status, None, f"conteúdo maior que {max_bytes} bytes (não baixado)", dict(r.headers)
                return r.status, dados, None, dict(r.headers)
        except urllib.error.HTTPError as e:
            status, ultimo_erro = e.code, f"HTTP {e.code}"
            if e.code in (400, 401, 403, 404, 410):
                try:
                    return e.code, e.read(65536), ultimo_erro, dict(e.headers or {})
                except Exception:
                    return e.code, None, ultimo_erro, {}
            ra = (e.headers or {}).get("Retry-After")
            time.sleep(min(60, float(ra)) if ra and str(ra).isdigit() else 2 ** t)
        except Exception as e:                       # timeout, conexão, DNS
            ultimo_erro = f"{type(e).__name__}: {e}"[:300]
            time.sleep(2 ** t)
    return status, None, ultimo_erro or "falha", {}


class Cache:
    def __init__(self, pasta, cfg_fontes, buscador=None):
        self.pasta = Path(pasta)
        (self.pasta / "conteudo").mkdir(parents=True, exist_ok=True)
        (self.pasta / "indice").mkdir(parents=True, exist_ok=True)
        self.cfg = cfg_fontes
        self.limitador = LimitadorTaxa(cfg_fontes["intervalo_minimo_segundos"])
        self.buscador = buscador or (lambda url, mx: baixar_http(url, self.cfg, self.limitador, mx))
        self.trava = threading.Lock()

    def _ind(self, url):
        return self.pasta / "indice" / (hashlib.sha256(url.encode("utf-8")).hexdigest() + ".json")

    def historico(self, url):
        p = self._ind(url)
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []

    def ultima(self, url):
        h = self.historico(url)
        return h[-1] if h else None

    def obter(self, url, atualizar=False, max_bytes=None, aceitar_404=True):
        """Entrada da URL: reutiliza a última bem-sucedida (ou 404 definitivo) salvo `atualizar`."""
        ult = self.ultima(url)
        if ult and not atualizar and (ult["ok"] or (aceitar_404 and ult.get("status_http") == 404)):
            return ult
        max_bytes = max_bytes or int(self.cfg.get("tamanho_maximo_documento_mb", 30) * 1024 * 1024)
        status, dados, erro, cab = self.buscador(url, max_bytes)
        ent = {"url": url, "consultado_em": _agora(), "status_http": status, "ok": dados is not None and erro is None and status == 200,
               "erro": erro, "sha256": None, "arquivo": None, "bytes": None,
               "content_type": (cab or {}).get("Content-Type") or (cab or {}).get("content-type"),
               "content_disposition": (cab or {}).get("Content-Disposition") or (cab or {}).get("content-disposition")}
        if dados is not None:
            sha = hashlib.sha256(dados).hexdigest()
            arq = self.pasta / "conteudo" / sha
            if not arq.exists():
                tmp = arq.with_suffix(".tmp")
                tmp.write_bytes(dados)
                os.replace(tmp, arq)
            ent.update({"sha256": sha, "arquivo": f"conteudo/{sha}", "bytes": len(dados)})
        with self.trava:
            h = self.historico(url)
            if ult and ult.get("sha256") and ent.get("sha256") and ult["sha256"] != ent["sha256"]:
                ent["substitui_versao"] = ult["sha256"]          # fonte mudou: nova versão registrada, antiga preservada
            h.append(ent)
            tmp = self._ind(url).with_suffix(".tmp")
            tmp.write_text(json.dumps(h, ensure_ascii=False, indent=1), encoding="utf-8")
            os.replace(tmp, self._ind(url))
        return ent

    def conteudo(self, ent):
        if not ent or not ent.get("arquivo"):
            return None
        dados = (self.pasta / ent["arquivo"]).read_bytes()
        if hashlib.sha256(dados).hexdigest() != ent["sha256"]:
            raise RuntimeError(f"conteúdo em cache corrompido: {ent['arquivo']}")
        return dados

    def json(self, ent):
        d = self.conteudo(ent)
        if d is None:
            return None
        try:
            return json.loads(d.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
