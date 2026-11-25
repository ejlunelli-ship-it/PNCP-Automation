"""Etapa 1: localizar e conferir as fontes (somente leitura) e registrar hashes.

- Banco PNCP: procura o pncp_v2.db nos caminhos candidatos e confere a impressão digital registrada pelo estudo
  original (tamanho + SHA-256 do início e do fim). Não assume o local original.
- Cesta S1: lista de produtos da rodada S1 (conjuntos_amostras.csv) conferida contra o congelamento dessa rodada;
  amostra S1 (708.964 itens) conferida contra as contagens esperadas, sem nenhum produto fora de S1 (nem S2).
"""
import hashlib

import pandas as pd

from . import comum
from .comum import ErroDesenho


def localizar_banco(c):
    from em.comum import impressao_digital
    esp = c["fontes"]["pncp_v2_impressao_esperada"]
    achados = []
    for cand in c["fontes"]["pncp_v2_caminhos_candidatos"]:
        p = comum.resolver(cand)
        if not p.exists():
            achados.append({"caminho": str(p), "existe": False})
            continue
        imp = impressao_digital(p)
        ok = imp["tamanho_bytes"] == esp["tamanho_bytes"] and imp["sha256_inicio_fim"] == esp["sha256_inicio_fim"]
        achados.append({"caminho": str(p), "existe": True, "confere": ok, **imp})
    validos = [a for a in achados if a.get("confere")]
    if not validos:
        raise ErroDesenho(f"nenhum pncp_v2.db confere com a impressão esperada: {achados}")
    return validos[0], achados


def conjunto_S1(c):
    rod = comum.resolver(c["fontes"]["rodada_S1"])
    cong = comum.ler_json(rod / "congelamento.json")
    p = rod / "tabelas" / "conjuntos_amostras.csv"
    h = comum.sha(p)
    if h != cong["sha256_conjuntos_amostras"]:
        raise ErroDesenho("conjuntos_amostras.csv da rodada S1 difere do congelamento")
    linhas = comum.ler_csv(p)
    s1 = sorted(r["produto"] for r in linhas if r["S1"] == "1")
    s2 = sorted(r["produto"] for r in linhas if r["S1S2"] == "1" and r["S1"] == "0")
    if not all(r["status_automatico"] == "AUTO_VALIDADO_CATALOGO" for r in linhas if r["S1"] == "1"):
        raise ErroDesenho("produto S1 sem status AUTO_VALIDADO_CATALOGO")
    hl = hashlib.sha256("\n".join(s1).encode()).hexdigest()
    if hl != cong["conjuntos"]["S1"]["sha256_lista"]:
        raise ErroDesenho("lista S1 não confere com o congelamento da rodada S1")
    return s1, s2, {"conjuntos_amostras_sha256": h, "S1_sha256_lista": hl, "congelamento_rodada_S1": cong["congelado_em"],
                    "validador": cong["validacao_automatica"]["versao_validador"],
                    "sha256_manifesto_validacao": cong["validacao_automatica"]["sha256_manifesto"]}


def executar(c, log):
    banco, achados = localizar_banco(c)
    log(f"pncp_v2.db conferido em {banco['caminho']}")
    s1, s2, meta = conjunto_S1(c)
    dS1 = comum.resolver(c["fontes"]["dados_S1"])
    arquivos = {}
    for n in ("amostra.pkl", "indices.pkl", "regime_compras.pkl", "eventos_info.pkl", "unidades.pkl", "dcdh_principal.pkl"):
        arquivos[f"S1/{n}"] = comum.sha(dS1 / n)
    dS12 = comum.resolver(c["fontes"]["dados_S1S2"])
    for n in ("amostra.pkl", "indices.pkl"):
        arquivos[f"S1S2/{n}"] = comum.sha(dS12 / n)
    dce = comum.resolver(c["fontes"]["dados_cesta"])
    arquivos["cesta/indices.pkl"] = comum.sha(dce / "indices.pkl")
    arquivos["cesta/amostra.pkl"] = comum.sha(dce / "amostra.pkl")
    a = pd.read_pickle(dS1 / "amostra.pkl")[["chave", "produto", "uasg"]]
    cont = {"produtos": int(a.produto.nunique()), "compras": int(a.chave.nunique()), "itens": int(len(a)),
            "uasgs": int(a.uasg.nunique())}
    esp = c["fontes"]["contagens_S1_esperadas"]
    prods = set(a.produto.astype(str))
    fora = prods - set(s1)
    com_s2 = prods & set(s2)
    if cont != esp or fora or com_s2:
        raise ErroDesenho(f"amostra S1 inconsistente: {cont} (esperado {esp}); fora de S1 = {len(fora)}; S2 = {len(com_s2)}")
    # a rodada S1 congelou também os resultados que serão usados na comparação (dCDH, E3, E7)
    rod = comum.resolver(c["fontes"]["rodada_S1"])
    man = comum.ler_json(rod / "manifesto.json")
    res_S1 = {}
    for n in ("amostras/S1/estudo_eventos.csv", "amostras/S1/efeitos_fixos.csv",
              "amostras/S1/tabelas/diagnosticos_identificacao.json", "amostras/S1/tabelas/populacao_eventos_pesos.csv"):
        res_S1[n] = comum.sha(rod / n)
    out = {"verificado_em": comum.agora(), "pncp_v2": banco, "pncp_v2_candidatos": achados, "S1": meta,
           "contagens_S1": cont, "produtos_S1": len(s1), "produtos_S2_excluidos": len(s2),
           "arquivos_trabalho_sha256": arquivos, "resultados_rodada_S1_sha256": res_S1,
           "manifesto_rodada_S1_chaves": sorted(man)[:20]}
    comum.escrever_json(comum.PASTA / "resultados" / "fontes.json", out)
    return out
