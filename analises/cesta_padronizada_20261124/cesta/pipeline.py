"""Orquestração das etapas. Cada etapa lê/grava o banco de trabalho e as saídas em `saidas/`."""
import json
import time

from . import VERSAO, brutos, comum, esquema, extracao
from .normalizacao import aliases_padrao, carregar_aliases


def _meta_gravar(dst, chave, valor):
    dst.execute("CREATE TABLE IF NOT EXISTS meta (chave TEXT PRIMARY KEY, valor TEXT)")
    dst.execute("INSERT OR REPLACE INTO meta VALUES (?, ?)", (chave, json.dumps(valor, ensure_ascii=False, default=str)))


def _meta_ler(dst, chave, padrao=None):
    try:
        r = dst.execute("SELECT valor FROM meta WHERE chave = ?", (chave,)).fetchone()
    except Exception:
        return padrao
    return json.loads(r[0]) if r else padrao


def etapa_extrair(ctx):
    par, cam, reg, saidas = ctx["par"], ctx["cam"], ctx["reg"], ctx["saidas"]
    with reg.etapa("impressão digital do banco de origem"):
        antes = comum.impressao_digital(cam["db"])
    src = comum.conectar_ro(cam["db"])
    comum.abrir_snapshot(src)
    try:
        with reg.etapa("esquema: inspeção e mapeamento"):
            insp = esquema.inspecionar(src)
            mapa = esquema.mapear(src)
            chaves = esquema.conferir_chaves(src, mapa)
            pragma = {"journal_mode": src.execute("PRAGMA journal_mode").fetchone()[0],
                      "data_version": src.execute("PRAGMA data_version").fetchone()[0],
                      "page_size": src.execute("PRAGMA page_size").fetchone()[0],
                      "page_count": src.execute("PRAGMA page_count").fetchone()[0]}
            comum.escrever_json(saidas / "esquema" / "esquema_inspecionado.json", insp)
            comum.escrever_json(saidas / "esquema" / "mapeamento_colunas.json",
                                {"mapeamento": mapa, "chaves": chaves, "pragma": pragma,
                                 "colunas_proibidas_na_selecao": esquema.COLUNAS_PROIBIDAS_SELECAO})
        if ctx["trabalho_db"].exists():
            ctx["trabalho_db"].unlink()
        dst = comum.conectar_trabalho(ctx["trabalho_db"])
        ctx["_dst"] = dst
        if ctx.get("sem_universo_total"):
            extracao.contar_universo_total = lambda *a, **k: None  # noqa: E731 (só em testes)
        extracao.extrair(src, dst, mapa, par, reg)
    except BaseException:
        if ctx.get("_dst"):
            ctx.pop("_dst").close()
        raise
    finally:
        comum.fechar_snapshot(src)
        src.close()
    ctx.pop("_dst", None)
    depois = comum.conferir_inalterado(antes, cam["db"])
    snap = {"antes": antes, "depois": depois, "sqlite_pragma": pragma, "extraido_em": time.strftime("%Y-%m-%dT%H:%M:%S")}
    ctx["snapshot"] = snap
    extracao.deduplicar_itens(dst, reg)
    _meta_gravar(dst, "snapshot", snap)
    _meta_gravar(dst, "mapeamento", mapa)
    _meta_gravar(dst, "versao_extracao", VERSAO)
    dst.close()


def etapa_brutos(ctx):
    cam, reg = ctx["cam"], ctx["reg"]
    dst = comum.conectar_trabalho(ctx["trabalho_db"])
    try:
        brutos.carregar(dst, cam["brutos"], reg)
        brutos.ligar(dst, reg)
        _meta_gravar(dst, "brutos", {"pasta": str(cam["brutos"]), "lido_em": time.strftime("%Y-%m-%dT%H:%M:%S")})
    finally:
        dst.close()


def etapa_normalizar(ctx):
    """Unidades e descrições normalizadas. Refazível sem reler o pncp.db nem os brutos."""
    reg = ctx["reg"]
    aliases_arq = ctx["parametros_arquivo"].parent / "aliases_unidades.csv"
    aliases = carregar_aliases(aliases_arq) if aliases_arq.exists() else aliases_padrao()
    dst = comum.conectar_trabalho(ctx["trabalho_db"])
    extracao.normalizar_unidades(dst, aliases, reg)
    brutos.chaves_descricao(dst, reg)
    _meta_gravar(dst, "normalizacao", {"aliases": str(aliases_arq), "sha256_aliases": comum.sha256_arquivo(aliases_arq),
                                       "feito_em": time.strftime("%Y-%m-%dT%H:%M:%S")})
    dst.close()


def etapa_selecionar(ctx):
    from . import selecao
    selecao.executar(ctx)


def etapa_auditar(ctx):
    from . import selecao
    selecao.auditar(ctx)


def etapa_sensibilidade(ctx):
    from . import sensibilidade
    sensibilidade.executar(ctx)


def etapa_diagnostico(ctx):
    from . import diagnostico
    diagnostico.executar(ctx)


def etapa_relatorio(ctx):
    from . import relatorio
    relatorio.executar(ctx)
