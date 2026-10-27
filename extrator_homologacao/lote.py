"""Processamento em lote: descoberta dos PDFs, hash SHA-256, cache por hash e versão do parser."""

import hashlib
import json
import logging
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from pydantic import ValidationError

from . import VERSAO_PARSER
from .extracao import RelatorioNaoSuportado, extrair_documento
from .texto import extrair_paginas
from .validacao import ERRO, OK, REVISAR, RegistroExtracao, validar

log = logging.getLogger(__name__)


def descobrir_pdfs(pasta, padrao="*.pdf"):
    """PDFs da pasta e subpastas, em ordem estável."""
    return sorted(p for p in Path(pasta).rglob(padrao) if p.is_file() and p.suffix.lower() == ".pdf")


def sha256(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def processar_pdf(caminho, ocr=True):
    """Extrai um PDF e devolve o RegistroExtracao. Nunca lança exceção: erros viram status ERRO."""
    caminho = Path(caminho)
    base = {
        "arquivo_origem": str(caminho),
        "versao_parser": VERSAO_PARSER,
        "processado_em": datetime.now().replace(microsecond=0),
    }
    try:
        base["hash_arquivo"] = sha256(caminho)
        paginas, usou_ocr = extrair_paginas(caminho, ocr=ocr)
        base["usou_ocr"] = usou_ocr
        r = extrair_documento(paginas, caminho.name)
        problemas = r.problemas + validar(r.dados)
        mensagens = problemas + [f"[aviso] {a}" for a in r.avisos]
        return RegistroExtracao(
            **base,
            **r.dados,
            fontes_extracao="; ".join(r.fontes) or None,
            status_extracao=REVISAR if problemas else OK,
            erros_extracao=" | ".join(mensagens) or None,
        )
    except RelatorioNaoSuportado as e:
        log.warning("%s: %s", caminho, e)
        return RegistroExtracao(**base, status_extracao=ERRO, erros_extracao=str(e))
    except ValidationError as e:
        log.exception("validação do modelo falhou em %s", caminho)
        return RegistroExtracao(**base, status_extracao=ERRO, erros_extracao=f"modelo inválido: {e}")
    except Exception as e:  # um PDF com problema não interrompe o lote
        log.exception("erro ao processar %s", caminho)
        return RegistroExtracao(**base, status_extracao=ERRO, erros_extracao=f"{type(e).__name__}: {e}")


# --------------------------------------------------------------------------- cache

def _json_padrao(v):
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, datetime):
        return v.isoformat()
    raise TypeError(type(v))


def carregar_cache(caminho):
    """{hash: registro_em_json} somente da versão atual do parser (mudou a versão, reprocessa)."""
    caminho = Path(caminho)
    if not caminho.exists():
        return {}
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        log.warning("cache ilegível em %s; ignorando", caminho)
        return {}
    return {h: r for h, r in dados.items() if r.get("versao_parser") == VERSAO_PARSER}


def salvar_cache(caminho, cache):
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tmp = caminho.with_suffix(".tmp")
    tmp.write_text(json.dumps(cache, ensure_ascii=False, indent=1, default=_json_padrao), encoding="utf-8")
    tmp.replace(caminho)


def processar_lote(pdfs, cache_path=None, reprocessar=False, ocr=True, workers=1):
    """Processa os PDFs e retorna a lista de RegistroExtracao, um por PDF, na ordem recebida.

    Arquivos idênticos (mesmo SHA-256) já extraídos pela versão atual do parser são reaproveitados
    do cache, inclusive cópias com outro nome; erros (status ERRO) não entram no cache para que o
    arquivo seja tentado novamente na próxima execução.
    """
    cache = {} if (reprocessar or not cache_path) else carregar_cache(cache_path)
    registros = [None] * len(pdfs)
    pendentes = {}  # hash -> índices
    for i, pdf in enumerate(pdfs):
        try:
            h = sha256(pdf)
        except OSError as e:
            registros[i] = RegistroExtracao(arquivo_origem=str(pdf), versao_parser=VERSAO_PARSER,
                                            status_extracao=ERRO, erros_extracao=f"leitura: {e}")
            continue
        if h in cache:
            registros[i] = RegistroExtracao(**{**cache[h], "arquivo_origem": str(pdf)})
            continue
        pendentes.setdefault(h, []).append(i)

    log.info("%d PDF(s): %d do cache, %d a processar (%d distintos)", len(pdfs),
             sum(r is not None for r in registros), sum(map(len, pendentes.values())), len(pendentes))

    unicos = [(h, pdfs[idx[0]]) for h, idx in pendentes.items()]
    if workers > 1 and len(unicos) > 1:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            resultados = list(ex.map(processar_pdf, [p for _, p in unicos], [ocr] * len(unicos), chunksize=4))
    else:
        resultados = [processar_pdf(p, ocr) for _, p in unicos]

    for (h, _), reg in zip(unicos, resultados):
        log.info("%s: %s%s", reg.arquivo_origem, reg.status_extracao,
                 f" - {reg.erros_extracao}" if reg.status_extracao != OK and reg.erros_extracao else "")
        if reg.status_extracao != ERRO:
            cache[h] = reg.model_dump()
        for i in pendentes[h]:
            registros[i] = reg.model_copy(update={"arquivo_origem": str(pdfs[i])})

    if cache_path:
        salvar_cache(cache_path, cache)
    return registros
