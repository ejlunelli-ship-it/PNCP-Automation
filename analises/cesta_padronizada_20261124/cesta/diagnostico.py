"""Diagnóstico de viabilidade causal (seção 13, parte final). NÃO SELETIVO.

Executado só depois do congelamento da cesta candidata: confere o hash de cesta_candidata.csv antes e
depois e recusa rodar se a cesta não estiver congelada. É o único módulo que lê o modo de disputa
(direto do pncp.db, somente leitura). Não lê preços e não estima regressões. Nada aqui altera a cesta.
"""
import json
from collections import Counter, defaultdict

from . import comum
from .comum import ErroEstrutural

MODOS = {"Aberto": "A", "Aberto-Fechado": "AF", "Fechado-Aberto": "FA"}
EVENTO_MIN_ANTES, EVENTO_MIN_DEPOIS, REF_MIN_OUTRAS_UASGS = 3, 3, 3


def _conferir_congelamento(saidas):
    arq = saidas / "congelamento_cesta.json"
    if not arq.exists():
        raise ErroEstrutural("cesta não congelada: rode a etapa 'selecionar' antes do diagnóstico")
    cong = json.loads(arq.read_text(encoding="utf-8"))
    h = comum.sha256_arquivo(saidas / "cesta_candidata.csv")
    if h != cong["sha256_cesta_candidata"]:
        raise ErroEstrutural("cesta_candidata.csv difere do congelamento registrado")
    return cong, h


def executar(ctx):
    cam, reg, saidas = ctx["cam"], ctx["reg"], ctx["saidas"]
    cong, h0 = _conferir_congelamento(saidas)
    dst = comum.conectar_trabalho(ctx["trabalho_db"])
    with reg.etapa("diagnóstico: itens da cesta congelada"):
        sql_itens = ("SELECT u.chave, u.uasg, k.id_candidato, u.trimestre, u.data_publicacao "
                     "FROM universo_produto u JOIN cesta_candidata_tab k USING (produto)")

        def itens_cesta():
            cur = dst.execute(sql_itens)
            while True:
                bloco = cur.fetchmany(200_000)
                if not bloco:
                    return
                yield from bloco
        chaves = {r[0] for r in itens_cesta()}
    with reg.etapa("diagnóstico: modo de disputa (pncp.db, somente leitura)"):
        antes = comum.impressao_digital(cam["db"])
        r = dst.execute("SELECT valor FROM meta WHERE chave = 'snapshot'").fetchone()
        snap = json.loads(r[0]) if r else None
        if snap and snap["antes"]["sha256_inicio_fim"] != antes["sha256_inicio_fim"]:
            raise ErroEstrutural("o pncp.db mudou desde a extração; o modo seria lido de outro estado do banco")
        src = comum.conectar_ro(cam["db"])
        comum.abrir_snapshot(src)
        sql = "SELECT numero_controle_pncp, modo_disputa FROM compras WHERE fonte = ?"
        reg.consulta("diagnostico_modo", sql)
        modo = {ch: m for ch, m in src.execute(sql, (ctx["par"]["universo"]["fonte"],)) if ch in chaves}
        comum.fechar_snapshot(src)
        src.close()
        comum.conferir_inalterado(antes, cam["db"])
    with reg.etapa("diagnóstico: indicadores"):
        compras_modo = Counter(MODOS.get(modo.get(ch), "outro/ausente") for ch in chaves)
        por_prod = defaultdict(lambda: defaultdict(set))       # produto -> modo -> compras
        por_uasg = defaultdict(dict)                           # uasg -> compra -> (data, modo)
        cel = defaultdict(lambda: defaultdict(set))            # (produto, trimestre) -> modo -> uasgs
        cel_uasgs = defaultdict(set)
        n_itens = 0
        cod_ch = {ch: i for i, ch in enumerate(sorted(chaves))}
        for ch, ua, prod, tri, data in itens_cesta():
            n_itens += 1
            m = MODOS.get(modo.get(ch), "outro")
            ch = cod_ch[ch]
            por_prod[prod][m].add(ch)
            por_uasg[ua][ch] = (data, m)
            cel[(prod, tri)][m].add(ua)
            cel_uasgs[(prod, tri)].add(ua)
        uasgs_ambos = [u for u, cs in por_uasg.items() if {"A", "AF"} <= {m for _, m in cs.values()}]
        prods_ambos = [p for p, d in por_prod.items() if d.get("A") and d.get("AF")]
        prods_ambos_5 = [p for p, d in por_prod.items() if len(d.get("A", ())) >= 5 and len(d.get("AF", ())) >= 5]
        cel_ambas = [k for k, d in cel.items() if d.get("A") and d.get("AF")]
        cel_ambas_uasgs_dif = [k for k, d in cel.items() if d.get("A") and d.get("AF") and (d["A"] | d["AF"]) and
                               len(d["A"] | d["AF"]) >= 2]
        # trocas de modo dentro da UASG (sequência temporal das compras da cesta, só A/AF)
        trocas, uasgs_com_troca, eventos, eventos_ano = 0, 0, 0, Counter()
        for u, cs in por_uasg.items():
            seq = [m for _, m in sorted(cs.values()) if m in ("A", "AF")]
            t = sum(1 for a, b in zip(seq, seq[1:]) if a != b)
            trocas += t
            uasgs_com_troca += t > 0
            if "AF" in seq:
                k = seq.index("AF")
                if k >= EVENTO_MIN_ANTES and all(x == "A" for x in seq[:k]) and seq[k:].count("AF") >= EVENTO_MIN_DEPOIS:
                    eventos += 1
                    datas = sorted(d for d, m in cs.values() if m == "AF")
                    eventos_ano[datas[0][:4]] += 1
        # referência interna: compras da cesta com >= 3 OUTRAS UASGs comprando o mesmo produto no trimestre
        com_ref = sum(1 for ch, ua, prod, tri, _ in itens_cesta() if len(cel_uasgs[(prod, tri)] - {ua}) >= REF_MIN_OUTRAS_UASGS)
        res = {
            "nota": "Diagnóstico descritivo e não seletivo; não altera a cesta e não usa preços.",
            "cesta_sha256": h0, "compras_cesta": len(chaves), "compras_por_modo": dict(compras_modo),
            "uasgs_cesta": len(por_uasg), "uasgs_usaram_A_e_AF": len(uasgs_ambos),
            "produtos": len(por_prod), "produtos_comprados_nos_dois_modos": len(prods_ambos),
            "produtos_com_5_ou_mais_compras_em_cada_modo": len(prods_ambos_5),
            "celulas_produto_trimestre": len(cel), "celulas_com_A_e_AF": len(cel_ambas),
            "celulas_com_A_e_AF_e_2_ou_mais_uasgs": len(cel_ambas_uasgs_dif),
            "trocas_de_modo_dentro_da_uasg": trocas, "uasgs_com_alguma_troca": uasgs_com_troca,
            "eventos_potenciais": {"definicao": f">= {EVENTO_MIN_ANTES} compras da cesta só em A antes da primeira AF e "
                                                f">= {EVENTO_MIN_DEPOIS} compras AF a partir dela", "uasgs": eventos,
                                   "por_ano_da_primeira_AF": dict(sorted(eventos_ano.items()))},
            "referencia_interna": {"definicao": f"item da cesta com >= {REF_MIN_OUTRAS_UASGS} outras UASGs comprando o mesmo "
                                                f"produto no mesmo trimestre", "itens": com_ref, "itens_total": n_itens,
                                   "pct": round(100 * com_ref / n_itens, 2) if n_itens else None},
            "referencia_externa": "Não há fonte externa de preços no pncp.db (ex.: Painel de Preços); cobertura não avaliável aqui.",
        }
        comum.escrever_json(saidas / "diagnostico_viabilidade.json", res)
        lin = [{"id_candidato": p, "compras_A": len(d.get("A", ())), "compras_AF": len(d.get("AF", ())),
                "compras_FA": len(d.get("FA", ())), "compras_outro": len(d.get("outro", ()))} for p, d in sorted(por_prod.items())]
        comum.escrever_csv(saidas / "diagnostico_por_produto.csv", lin,
                           ["id_candidato", "compras_A", "compras_AF", "compras_FA", "compras_outro"])
    dst.close()
    if comum.sha256_arquivo(saidas / "cesta_candidata.csv") != h0:
        raise ErroEstrutural("a cesta mudou durante o diagnóstico")
    reg.contar("diagnostico", {k: v for k, v in res.items() if not isinstance(v, str)})
