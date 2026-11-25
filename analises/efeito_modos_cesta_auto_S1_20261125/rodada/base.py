"""Infraestrutura da rodada: caminhos, congelamento (antes de qualquer acesso a preços ou modos) e amostras.

O estudo anterior é reutilizado SEM modificação: seu pacote `em` é importado a partir da pasta original e suas etapas
rodam com `--trabalho` e `--saidas` apontando para pastas novas.
"""
import csv
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
PASTA = AQUI.parent
REPO = PASTA.parents[1]


class ErroRodada(RuntimeError):
    pass


def resolver(p):
    p = Path(p)
    return p if p.is_absolute() else REPO / p


def cfg():
    with open(PASTA / "config.json", encoding="utf-8") as f:
        return json.load(f)


def sha(p, bloco=1 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(bloco), b""):
            h.update(b)
    return h.hexdigest()


def agora():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def escrever_json(p, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o)) + "\n",
                   encoding="utf-8")
    tmp.replace(p)


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
            w.writerow(["" if x.get(c) is None else (repr(float(round(float(x[c]), 10))) if isinstance(x.get(c), float) else x.get(c)) for c in colunas])
    return p


def ler_csv(p, colunas=None):
    with open(p, encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        return [({c: x[c] for c in colunas} if colunas else dict(x)) for x in r]


def estudo_anterior(c=None):
    c = c or cfg()
    p = resolver(c["estudo_anterior"])
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
    return p


# ------------------------------------------------------------------------------------------------ conjuntos
def conjuntos(c=None):
    """Listas de produtos por amostra, lidas SÓ das saídas técnicas (nenhuma coluna de preço ou modo)."""
    c = c or cfg()
    auto = resolver(c["validacao_automatica"])
    sens = ler_csv(auto / "resultados_sensibilidade.csv", ["id_candidato", "produto", "status_automatico"])
    cesta = ler_csv(resolver(c["estudo_anterior"]).parent / "cesta_padronizada_20261124" / "saidas" / "cesta_candidata.csv",
                    ["id_candidato", "produto"])
    st = {r["produto"]: r["status_automatico"] for r in sens}
    out = {}
    for nome, d in c["amostras"].items():
        if nome.startswith("_"):
            continue
        if d["status"] == "todos_P1":
            out[nome] = sorted(st)
        elif d["status"] == "cesta_candidata":
            out[nome] = sorted(r["produto"] for r in cesta)
        else:
            out[nome] = sorted(p for p, s in st.items() if s in d["status"])
    return out, st, {r["produto"]: r["id_candidato"] for r in cesta}


def congelar(c=None, forcar=False):
    """Registra hashes, identificadores e regras da validação automática e do estudo anterior. Roda ANTES de
    qualquer leitura de preço ou modo de disputa e não lê nenhum desses campos."""
    c = c or cfg()
    auto = resolver(c["validacao_automatica"])
    man = json.loads((auto / "manifesto.json").read_text(encoding="utf-8"))
    if man["versao_validador"] != c["versao_validador_esperada"]:
        raise ErroRodada(f"validador {man['versao_validador']} ≠ {c['versao_validador_esperada']}")
    dif = [n for n, h in man["saidas"].items() if sha(auto / n) != h]
    if dif:
        raise ErroRodada(f"saídas da validação automática diferem do manifesto: {dif}")
    conj, st, ids = conjuntos(c)
    ant = resolver(c["estudo_anterior"])
    dados = Path(c["dados_base"])
    linhas = [{"produto": p, "id_candidato": ids.get(p, ""), "status_automatico": st.get(p, ""),
               **{n: int(p in set(v)) for n, v in conj.items()}} for p in conj["cesta"]]
    escrever_csv(PASTA / "tabelas" / "conjuntos_amostras.csv", linhas)
    out = {
        "congelado_em": agora(), "antes_de_acessar_precos_e_modos": True,
        "validacao_automatica": {"pasta": str(auto), "id_execucao": man["id_execucao"], "versao_validador": man["versao_validador"],
                                 "versao_regras": man["versao_regras_automaticas"], "versao_auditoria_origem": man["versao_auditoria_origem"],
                                 "sha256_manifesto": sha(auto / "manifesto.json"), "saidas": man["saidas"],
                                 "config": {p.name: sha(p) for p in sorted(resolver(c["validacao_config"]).glob("*.json"))},
                                 "codigo": {p.name: sha(p) for p in sorted(resolver(c["validacao_codigo"]).glob("*.py"))}},
        "conjuntos": {n: {"produtos": len(v), "sha256_lista": hashlib.sha256("\n".join(v).encode()).hexdigest()} for n, v in conj.items()},
        "sha256_conjuntos_amostras": sha(PASTA / "tabelas" / "conjuntos_amostras.csv"),
        "estudo_anterior": {"pasta": str(ant), "config": sha(ant / "config.json"), "executar": sha(ant / "executar.py"),
                            "honestdid_R": sha(ant / "honestdid.R"), "codigo": {p.name: sha(p) for p in sorted((ant / "em").glob("*.py"))},
                            "saidas": {n: sha(ant / n) for n in ("efeitos_fixos.csv", "estudo_eventos.csv", "honestdid.csv",
                                                                   "referencias_alternativas.csv", "funil_amostra.csv", "robustez.csv")}},
        "dados_base": {n: sha(dados / n) for n in ("amostra.pkl", "regime_compras.pkl", "conjuntos.pkl")},
        "config_rodada": sha(PASTA / "config.json"),
    }
    arq = PASTA / "congelamento.json"
    if arq.exists() and not forcar:
        velho = json.loads(arq.read_text(encoding="utf-8"))
        chaves = ("validacao_automatica", "conjuntos", "estudo_anterior", "dados_base", "config_rodada")
        if any(velho[k] != out[k] for k in chaves):
            raise ErroRodada("o congelamento existente difere do estado atual (validação, conjuntos, estudo ou dados mudaram)")
        return velho
    escrever_json(arq, out)
    return out


def verificar_congelamento(c=None):
    c = c or cfg()
    arq = PASTA / "congelamento.json"
    if not arq.exists():
        raise ErroRodada("rodada não congelada: rode `executar.py congelar` antes de acessar preços")
    return congelar(c)          # recalcula e compara; erro se algo mudou


# ------------------------------------------------------------------------------------------------ amostras
def preparar_amostras(c=None, nomes=None, log=print):
    """Filtra a amostra analítica do estudo anterior pelos produtos de cada conjunto e calcula o funil (com a etapa 7
    redefinida como 'produto no conjunto'). Copia o regime de modo por UASG (independente dos produtos)."""
    import pandas as pd
    c = c or cfg()
    verificar_congelamento(c)
    ant = estudo_anterior(c)
    from em import amostra as em_amostra
    from em import comum as em_comum
    cfg_ant = em_comum.carregar_config(ant / "config.json")
    conj, _, _ = conjuntos(c)
    dados = Path(c["dados_base"])
    df = pd.read_pickle(dados / "amostra.pkl")
    reg_c = pd.read_pickle(dados / "regime_compras.pkl")
    cj = pd.read_pickle(dados / "conjuntos.pkl")
    funis = {}
    for nome in (nomes or [n for n in conj if n != "cesta"]):
        alvo = set(conj[nome])
        cj2 = cj.copy()
        cj2["aprovado"] = cj2.produto.isin(alvo).astype(int)
        linhas, masks = em_amostra.funil(df, cfg_ant, cj2)
        linhas[-1]["etapa"] = f"7_produto_no_conjunto_{nome}"
        linhas[-1]["criterio"] = f"Produto no conjunto {nome} (validação AUTOMÁTICA de catálogo; não é aprovação humana)"
        funis[nome] = linhas
        sub = df.loc[df.produto.isin(alvo)].copy()
        destino = Path(c["trabalho"]) / nome
        destino.mkdir(parents=True, exist_ok=True)
        sub.to_pickle(destino / "amostra.pkl")
        shutil.copy2(dados / "regime_compras.pkl", destino / "regime_compras.pkl")
        cj2.loc[cj2.produto.isin(alvo)].to_pickle(destino / "conjuntos.pkl")
        escrever_csv(PASTA / "amostras" / nome / "funil_amostra.csv", linhas)
        log(f"{nome}: {len(alvo)} produtos, {len(sub)} itens na amostra analítica; funil etapa 6 → 7: "
            f"{linhas[6]['itens']} → {linhas[7]['itens']}")
    return funis


def estimar(c=None, nome="S1", log=print, bootstrap=None):
    """Roda as etapas do estudo anterior (código intacto) sobre a amostra `nome`, em pastas novas."""
    c = c or cfg()
    verificar_congelamento(c)
    ant = resolver(c["estudo_anterior"])
    saida = PASTA / "amostras" / nome
    saida.mkdir(parents=True, exist_ok=True)
    preparar_saida(c, saida)
    cmd = [sys.executable, "-u", str(ant / "executar.py"), "--etapas", ",".join(c["etapas_estudo_anterior"]),
           "--config", str(ant / "config.json"), "--trabalho", str(Path(c["trabalho"]) / nome), "--saidas", str(saida)]
    if bootstrap:
        cmd += ["--bootstrap", str(bootstrap)]
    log(f"{nome}: {' '.join(cmd[2:5])} …")
    with open(saida / "log_estimacao.txt", "w", encoding="utf-8") as f:
        r = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
    if r.returncode != 0:
        raise ErroRodada(f"estimação de {nome} falhou (ver {saida / 'log_estimacao.txt'})")
    return saida


def preparar_saida(c, saida):
    """O módulo HonestDiD do estudo anterior executa `<saidas>/honestdid.R`: copia o script original (hash conferido
    com o congelamento) para a pasta de saída da amostra."""
    ant = resolver(c["estudo_anterior"])
    cong = json.loads((PASTA / "congelamento.json").read_text(encoding="utf-8"))
    if sha(ant / "honestdid.R") != cong["estudo_anterior"]["honestdid_R"]:
        raise ErroRodada("honestdid.R do estudo anterior mudou depois do congelamento")
    shutil.copy2(ant / "honestdid.R", Path(saida) / "honestdid.R")


def reexecutar_etapas(c, nome, etapas, log=print):
    """Reexecuta etapas específicas do estudo anterior para uma amostra (mesmo código, mesmos dados)."""
    verificar_congelamento(c)
    ant = resolver(c["estudo_anterior"])
    saida = PASTA / "amostras" / nome
    preparar_saida(c, saida)
    cmd = [sys.executable, "-u", str(ant / "executar.py"), "--etapas", ",".join(etapas), "--config", str(ant / "config.json"),
           "--trabalho", str(Path(c["trabalho"]) / nome), "--saidas", str(saida)]
    with open(saida / f"log_{'_'.join(etapas)}.txt", "w", encoding="utf-8") as f:
        r = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
    if r.returncode != 0:
        raise ErroRodada(f"{nome}: etapas {etapas} falharam")
    log(f"{nome}: etapas {etapas} reexecutadas")
