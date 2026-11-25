"""Etapas da validação automática, com checkpoints e retomada segura.

  auto-preparar   base P1 congelada (lista branca de colunas), unidades e itens (banco da cesta em mode=ro)
  auto-documentos catálogo oficial (CATMAT/PDM) e documentos de contratação da amostra documental (PNCP)
  auto-validar    classificação AUTO_* de famílias, subprodutos e itens, a partir do snapshot documental
  auto-auditar    integridade, auditoria das decisões, cobertura, sensibilidade, integração, relatório

Cada etapa grava `estado/<etapa>.json` com os hashes das entradas e das saídas; `auto-executar` pula a etapa quando
os hashes registrados conferem. Nenhuma etapa lê preço, valor, desconto, modo de disputa, licitantes ou resultado
econométrico.
"""
import json
import sqlite3
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import comum  # noqa: E402
from comum import ErroEstrutural  # noqa: E402

from . import VERSAO_VALIDADOR  # noqa: E402
from .acesso_fontes import Cache  # noqa: E402
from .carregar_dados import Leitor, carregar_base  # noqa: E402
from .consultar_catalogo import coletar, ficha_oficial, urls  # noqa: E402
from .extrair_atributos import especificacao_canonica, novo_extrator  # noqa: E402
from .extrair_documentos import avaliar_ancoras, extrair_texto, localizar_item  # noqa: E402
from .localizar_documentos import amostrar_compras, escolher, listar_documentos  # noqa: E402

ETAPAS = ("auto-preparar", "auto-documentos", "auto-validar", "auto-auditar")


class Contexto:
    def __init__(self, cfg, saida=None, cache=None, estado=None, origem=None, banco=None, buscador=None):
        self.cfg = cfg
        self.auto = comum.carregar_json(cfg["pasta_config"] / "validacao_automatica.json")
        self.saida = Path(saida) if saida else comum.resolver(self.auto["saida"])
        self.estado = Path(estado) if estado else Path(self.auto["estado"])
        self.origem = Path(origem) if origem else comum.resolver(cfg["parametros"]["saidas"]) / self.auto["rodada_origem"]
        self.banco = Path(banco) if banco else Path(self.auto["banco_cesta"])
        self.cache = Cache(Path(cache) if cache else Path(self.auto["cache"]), self.auto["fontes"], buscador)
        self.saida.mkdir(parents=True, exist_ok=True)
        self.estado.mkdir(parents=True, exist_ok=True)
        self.leitor = Leitor(self.auto)

    def arq_estado(self, etapa):
        return self.estado / f"{etapa}.json"

    def hash_config(self):
        return comum.sha256_arquivo(self.cfg["pasta_config"] / "validacao_automatica.json")


def contexto_produto(prod):
    req = set((prod["requer_especialista"] or "").split(";"))
    return {"medicamento": "medicamento" in req,
            "originalidade": bool({"toner_cartucho", "peca_reposicao", "equipamento_eletronico"} & req)}


# ------------------------------------------------------------------------------------------------ auto-preparar
def preparar(ctx, reg):
    man, prods, vars_, origs = carregar_base(ctx.auto, ctx.origem, ctx.leitor)
    P = [p for p in prods if p["tipo_registro"] == "PRODUTO"]
    reg.log(f"base P1 congelada (versão {man['versao_auditoria']}): {len(P)} produtos, {len(vars_)} variantes, {len(origs)} descrições originais")
    antes = comum.impressao_digital(ctx.banco)
    db = ctx.estado / "itens.db"
    tmp = ctx.estado / "itens.db.tmp"
    if tmp.exists():
        tmp.unlink()
    con = sqlite3.connect(tmp.resolve().as_uri(), uri=True)
    con.execute("ATTACH DATABASE ? AS cesta", (f"{ctx.banco.resolve().as_uri()}?mode=ro",))
    try:
        cols_u = ctx.auto["colunas_permitidas"]["universo_produto"]
        cols_c = ctx.auto["colunas_permitidas"]["compras_base"]
        cols_n = ctx.auto["colunas_permitidas"]["unidades"]
        for t, cols in (("universo_produto", cols_u), ("compras_base", cols_c), ("unidades", cols_n)):
            reais = [r[1] for r in con.execute(f"PRAGMA cesta.table_info({t})")]
            falta = [c for c in cols if c not in reais]
            if falta:
                raise ErroEstrutural(f"{t}: colunas ausentes {falta}")
            ctx.leitor.lidas[t] = {"tabela": t, "colunas_lidas": cols, "colunas_descartadas": [c for c in reais if c not in cols]}
        con.executescript("CREATE TABLE p (produto TEXT PRIMARY KEY);")
        con.executemany("INSERT INTO p VALUES (?)", [(x["produto"],) for x in P])
        con.execute(f"CREATE TABLE itens AS SELECT {', '.join('u.' + c for c in cols_u)}, c.uf AS uf FROM p "
                    f"JOIN cesta.universo_produto u ON u.produto = p.produto LEFT JOIN cesta.compras_base c ON c.chave = u.chave")
        con.execute("CREATE INDEX ix_it_prod ON itens (produto)")
        con.executescript("CREATE TABLE pu (unidade_norm TEXT PRIMARY KEY);")
        con.executemany("INSERT OR IGNORE INTO pu VALUES (?)", [(x["unidade_norm"],) for x in P])
        con.execute(f"CREATE TABLE unidades AS SELECT DISTINCT {', '.join('n.' + c for c in cols_n)} FROM cesta.unidades n "
                    f"JOIN pu ON pu.unidade_norm = n.unidade_norm")
        con.commit()
        n_itens = con.execute("SELECT COUNT(*) FROM itens").fetchone()[0]
    finally:
        con.close()
    tmp.replace(db)
    depois = comum.impressao_digital(ctx.banco)
    comum.conferir_inalterado(antes, depois)
    esperado = sum(int(p["itens"]) for p in P)
    if n_itens != esperado:
        raise ErroEstrutural(f"itens carregados ({n_itens}) ≠ itens da base P1 ({esperado})")
    est = {"etapa": "auto-preparar", "concluido_em": comum.agora(), "versao_validador": VERSAO_VALIDADOR,
           "versao_auditoria_origem": man["versao_auditoria"], "hashes_base_origem": man["hashes_base"],
           "hash_config": ctx.hash_config(), "itens": n_itens, "produtos": len(P), "banco_cesta": {"antes": antes, "depois": depois},
           "colunas_lidas": ctx.leitor.lidas, "sha256_itens_db": comum.sha256_arquivo(db)}
    comum.escrever_json(ctx.arq_estado("auto-preparar"), est)
    comum.escrever_json(ctx.saida / "colunas_lidas.json", ctx.leitor.lidas)
    reg.log(f"auto-preparar: {n_itens} itens; banco da cesta inalterado")
    return est


def _base(ctx):
    man, prods, vars_, origs = carregar_base(ctx.auto, ctx.origem, ctx.leitor)
    P = [p for p in prods if p["tipo_registro"] == "PRODUTO"]
    V = defaultdict(list)
    for v in vars_:
        V[v["id_candidato"]].append(v)
    return man, P, V, origs


# ------------------------------------------------------------------------------------------------ auto-documentos
def documentos(ctx, reg, atualizar=False, limite_compras=None):
    man, P, V, _ = _base(ctx)
    f = ctx.auto["fontes"]
    entradas = coletar(ctx.cache, f, {p["catmat"] for p in P if p["catmat"]}, {p["pdm"] for p in P if p["pdm"]}, reg, atualizar)
    snapshot = {u: {k: e.get(k) for k in ("url", "consultado_em", "status_http", "ok", "erro", "sha256", "arquivo", "bytes")}
                for u, e in sorted(entradas.items())}
    comum.escrever_json(ctx.estado / "snapshot_catalogo.json", snapshot)
    reg.log(f"catálogo: {len(snapshot)} URLs, {sum(1 for e in snapshot.values() if e['ok'])} ok")
    # amostra documental de contratações (independente da classificação)
    con = sqlite3.connect(ctx.estado / "itens.db")
    comp = defaultdict(set)
    for prod, chave in con.execute("SELECT DISTINCT produto, chave FROM itens"):
        comp[prod].add(chave)
    con.close()
    cd = ctx.auto["documentos_contratacao"]
    alvo = amostrar_compras(sorted(p["produto"] for p in P), comp, cd)
    if limite_compras:
        alvo = alvo[:limite_compras]
    porp = {p["produto"]: p for p in P}
    regras = ctx.cfg["regras"]
    voc = comum.carregar_json(ctx.origem / "vocabulario_chaves_declaradas.json")
    ext = novo_extrator(regras, voc)
    feitos_arq = ctx.estado / "documentos.jsonl"
    feitos = {}
    if feitos_arq.exists():
        for l in feitos_arq.read_text(encoding="utf-8").splitlines():
            if l.strip():
                r = json.loads(l)
                feitos[(r["produto"], r["chave"])] = r
    textos = ctx.estado / "textos"
    textos.mkdir(exist_ok=True)
    novos = 0
    with open(feitos_arq, "a", encoding="utf-8") as out:
        for i, (prod, chave) in enumerate(alvo, 1):
            if (prod, chave) in feitos and not atualizar:
                continue
            p = porp[prod]
            ficha = ficha_oficial(ctx.cache, f, p["catmat"], p["pdm"], entradas)
            canon = especificacao_canonica(ficha, ext, contexto_produto(p))
            r = {"produto": prod, "id_candidato": p["id_candidato"], "chave": chave, "processado_em": comum.agora(), "documentos": [],
                 "resultado": None, "ancora": None}
            url_l, ent_l, docs = listar_documentos(ctx.cache, f, chave)
            r["url_lista"], r["lista_status_http"], r["lista_sha256"] = url_l, ent_l.get("status_http"), ent_l.get("sha256")
            if docs is None:
                r["resultado"] = "LISTA_INDISPONIVEL" if ent_l.get("status_http") != 404 else "COMPRA_SEM_ARQUIVOS"
            else:
                sel = escolher(docs, cd)
                if not sel:
                    r["resultado"] = "SEM_TR_OU_EDITAL"
                ancoras = []
                for d in sel:
                    ent = ctx.cache.obter(d["url"])
                    info = {"tipo": d.get("tipoDocumentoNome"), "titulo": d.get("titulo"), "url": d["url"],
                            "data_publicacao": d.get("dataPublicacaoPncp"), "status_http": ent.get("status_http"), "sha256": ent.get("sha256"),
                            "bytes": ent.get("bytes"), "erro": ent.get("erro"), "formato": None, "paginas": 0, "texto": False, "ancoras": 0}
                    if ent["ok"]:
                        tx = textos / f"{ent['sha256']}.json"
                        if tx.exists():
                            t = json.loads(tx.read_text(encoding="utf-8"))
                        else:
                            fmt, pags, err = extrair_texto(ctx.cache.conteudo(ent))
                            t = {"formato": fmt, "paginas": pags, "erro": err}
                            tx.write_text(json.dumps(t, ensure_ascii=False), encoding="utf-8")
                        info.update({"formato": t["formato"], "paginas": len(t["paginas"]), "erro_extracao": t["erro"],
                                     "texto": any(x.strip() for x in t["paginas"])})
                        if canon is not None and info["texto"]:
                            a = localizar_item(t["paginas"], p["catmat"], canon, ext, contexto_produto(p), cd["janela_caracteres"],
                                               cd["janela_conflito_caracteres"])
                            for x in a:
                                x["documento_sha256"] = ent["sha256"]
                                x["documento_url"] = d["url"]
                            info["ancoras"] = len(a)
                            ancoras += a
                    r["documentos"].append(info)
                if sel and r["resultado"] is None:
                    if canon is None:
                        r["resultado"] = "SEM_ESPECIFICACAO_OFICIAL"
                    elif not any(x["texto"] for x in r["documentos"]):
                        r["resultado"] = "DOCUMENTO_SEM_TEXTO_OU_INDISPONIVEL"
                    else:
                        r["resultado"], r["ancora"] = avaliar_ancoras(ancoras)
            out.write(json.dumps(r, ensure_ascii=False) + "\n")
            out.flush()
            feitos[(prod, chave)] = r
            novos += 1
            if novos % 25 == 0:
                reg.log(f"documentos: {i}/{len(alvo)} compras")
    est = {"etapa": "auto-documentos", "concluido_em": comum.agora(), "hash_config": ctx.hash_config(),
           "sha256_snapshot_catalogo": comum.sha256_arquivo(ctx.estado / "snapshot_catalogo.json"),
           "compras_amostra": len(alvo), "compras_processadas": len(feitos),
           "sha256_documentos": comum.sha256_arquivo(feitos_arq) if feitos_arq.exists() else None}
    comum.escrever_json(ctx.arq_estado("auto-documentos"), est)
    reg.log(f"auto-documentos: {len(feitos)} compras examinadas ({novos} novas nesta execução)")
    return est


def carregar_documentos(ctx):
    arq = ctx.estado / "documentos.jsonl"
    out = {}
    if arq.exists():
        for l in arq.read_text(encoding="utf-8").splitlines():
            if l.strip():
                r = json.loads(l)
                out[(r["produto"], r["chave"])] = r            # a última linha da mesma compra prevalece
    return out


def snapshot_entradas(ctx):
    s = comum.carregar_json(ctx.estado / "snapshot_catalogo.json")
    return {u: e for u, e in s.items()}
