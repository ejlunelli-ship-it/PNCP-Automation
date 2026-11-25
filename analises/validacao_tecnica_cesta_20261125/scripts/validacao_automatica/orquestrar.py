"""Orquestração das etapas automáticas com retomada segura: uma etapa é pulada quando o checkpoint registra as
mesmas entradas (hashes) e as saídas ainda conferem."""
import comum

from .auditar_decisoes import auditar
from .gerar_cesta import validar
from .pipeline import Contexto, documentos, preparar


def _valido_preparar(ctx):
    a = ctx.arq_estado("auto-preparar")
    if not a.exists() or not (ctx.estado / "itens.db").exists():
        return False
    e = comum.carregar_json(a)
    man = comum.carregar_json(ctx.origem / "manifesto.json")
    return (e.get("hash_config") == ctx.hash_config() and e.get("hashes_base_origem") == man["hashes_base"]
            and comum.sha256_arquivo(ctx.estado / "itens.db") == e.get("sha256_itens_db"))


def _valido_validar(ctx):
    a = ctx.arq_estado("auto-validar")
    if not a.exists():
        return False
    e = comum.carregar_json(a)
    docs = ctx.estado / "documentos.jsonl"
    if e.get("hash_config") != ctx.hash_config():
        return False
    if e.get("sha256_snapshot_catalogo") != comum.sha256_arquivo(ctx.estado / "snapshot_catalogo.json"):
        return False
    if e.get("sha256_documentos") != (comum.sha256_arquivo(docs) if docs.exists() else None):
        return False
    return all((ctx.saida / n).exists() and comum.sha256_arquivo(ctx.saida / n) == h for n, h in e.get("saidas", {}).items())


def executar_auto(cfg, reg, comando, atualizar=False, limite_compras=None, refazer=False, ctx=None):
    ctx = ctx or Contexto(cfg)
    testes_arq = comum.resolver(cfg["parametros"]["saidas"]) / "resultado_testes.json"
    testes = comum.carregar_json(testes_arq) if testes_arq.exists() else None
    if comando in ("auto-preparar", "auto-executar"):
        if comando == "auto-preparar" or refazer or not _valido_preparar(ctx):
            preparar(ctx, reg)
        else:
            reg.log("auto-preparar: checkpoint válido, etapa pulada")
    if comando in ("auto-documentos", "auto-executar"):
        documentos(ctx, reg, atualizar=atualizar, limite_compras=limite_compras)   # incremental: só o que falta
    if comando in ("auto-validar", "auto-executar"):
        if comando == "auto-validar" or refazer or atualizar or not _valido_validar(ctx):
            validar(ctx, reg)
        else:
            reg.log("auto-validar: checkpoint válido, etapa pulada")
    if comando in ("auto-auditar", "auto-executar"):
        auditar(ctx, reg, testes)
    return ctx
