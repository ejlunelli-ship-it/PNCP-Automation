"""Carga das entradas com lista BRANCA de colunas: só as colunas de config/validacao_automatica.json chegam aos
extratores e classificadores. Registra o que foi lido. Confere a integridade da rodada P1 congelada."""
import csv
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))

import comum  # noqa: E402
from comum import ErroEstrutural  # noqa: E402


class Leitor:
    def __init__(self, cfg_auto):
        self.permitidas = cfg_auto["colunas_permitidas"]
        self.lidas = {}

    def csv(self, caminho, nome=None):
        nome = nome or Path(caminho).name
        perm = self.permitidas[nome]
        cab = comum.cabecalho_csv(caminho)
        falta = [c for c in perm if c not in cab]
        if falta:
            raise ErroEstrutural(f"{nome}: colunas esperadas ausentes {falta}")
        self.lidas[nome] = {"arquivo": str(caminho), "colunas_lidas": perm, "colunas_descartadas": [c for c in cab if c not in perm]}
        out = []
        with open(caminho, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                out.append({c: r[c] for c in perm})
        return out

    def sql(self, con, tabela, where="", params=(), alias=None):
        perm = self.permitidas[tabela]
        reais = [r[1] for r in con.execute(f"PRAGMA {alias + '.' if alias else ''}table_info({tabela})")]
        falta = [c for c in perm if c not in reais]
        if falta:
            raise ErroEstrutural(f"{tabela}: colunas esperadas ausentes {falta}")
        self.lidas[tabela] = {"tabela": tabela, "colunas_lidas": perm, "colunas_descartadas": [c for c in reais if c not in perm]}
        nome = f"{alias}.{tabela}" if alias else tabela
        return con.execute(f"SELECT {', '.join(perm)} FROM {nome} {where}", params)


def conferir_rodada(pasta, versao_esperada):
    """A rodada de origem precisa estar íntegra e na versão de auditoria esperada (nada é regerado)."""
    man = comum.carregar_json(pasta / "manifesto.json")
    if man["versao_auditoria"] != versao_esperada:
        raise ErroEstrutural(f"versão da auditoria de origem {man['versao_auditoria']} ≠ {versao_esperada}")
    dif = [k for k, h in man["hashes_base"].items() if comum.sha256_arquivo(pasta / k) != h]
    if dif:
        raise ErroEstrutural(f"arquivos-base da rodada {man['rodada']} alterados: {dif}")
    return man


def carregar_base(cfg_auto, pasta_origem, leitor):
    man = conferir_rodada(pasta_origem, cfg_auto["versao_auditoria_origem"])
    prods = leitor.csv(pasta_origem / "base_produtos.csv")
    vars_ = leitor.csv(pasta_origem / "base_variantes.csv")
    origs = leitor.csv(pasta_origem / "descricoes_originais.csv")
    ids = [p["id_registro"] for p in prods]
    if len(ids) != len(set(ids)):
        raise ErroEstrutural("base_produtos: id_registro duplicado")
    vid = [v["id_variante"] for v in vars_]
    if len(vid) != len(set(vid)):
        raise ErroEstrutural("base_variantes: id_variante duplicado")
    return man, prods, vars_, origs
