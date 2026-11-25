"""Sensibilidade da seleção (seções 7, 14 e 15). Usa só métricas de frequência, diversidade e
qualidade (banco de trabalho, sem preços nem modo). A grade é pré-especificada em parametros.json;
nenhum cenário é escolhido por maximizar observações.

A sensibilidade opera no nível da FAMÍLIA (CATMAT × unidade), com a classificação técnica feita para
toda a triagem ampla (famílias que passam o cenário mais brando da grade). A divisão automática em
subtipos só existe na cesta principal; isso é indicado nas saídas.
"""
import itertools
import json

import numpy as np

from . import comum
from .metricas import hhi

DIMENSOES = ["compras_min", "uasgs_min", "trimestres_min", "anos_min", "share_uasg_dominante_max", "hhi_max"]


def _passa(F, lim):
    return ((F["compras"] >= lim["compras_min"]) & (F["uasgs"] >= lim["uasgs_min"])
            & (F["trimestres"] >= lim["trimestres_min"]) & (F["anos"] >= lim["anos_min"])
            & (F["share_uasg_dominante"] <= lim["share_uasg_dominante_max"] + 1e-12)
            & (F["hhi"] <= lim["hhi_max"] + 1e-12))


def _carregar_familias(dst, tabela):
    rows = dst.execute(f"SELECT m.familia, m.compras, m.uasgs, m.trimestres, m.anos, m.share_uasg_dominante, m.hhi, "
                       f"COALESCE(k.classe_tecnica, ''), COALESCE(k.cadastral_ok, 0) FROM {tabela} m "
                       f"LEFT JOIN familia_classe k USING (familia) ORDER BY m.familia").fetchall()
    fam = [r[0] for r in rows]
    F = {c: np.array([r[i + 1] if r[i + 1] is not None else np.nan for r in rows], dtype=float)
         for i, c in enumerate(["compras", "uasgs", "trimestres", "anos", "share_uasg_dominante", "hhi"])}
    F["classe"] = np.array([r[7] for r in rows])
    F["cadastral_ok"] = np.array([r[8] for r in rows], dtype=bool)
    return fam, F


class Cobertura:
    """Itens (família, compra, UASG, ano, trimestre) das famílias da triagem ampla, em arrays inteiros."""

    def __init__(self, dst, familias, filtro="1", lote=200_000):
        """Lê em lotes e guarda só códigos inteiros (memória ~ 40 bytes por item)."""
        from array import array
        self.idx = {f: i for i, f in enumerate(familias)}
        dst.executescript("DROP TABLE IF EXISTS _amp; CREATE TEMP TABLE _amp (familia TEXT PRIMARY KEY);")
        dst.executemany("INSERT INTO _amp VALUES (?)", [(f,) for f in familias])
        cc, cu, ct = {}, {}, {}
        fam, compra, uasg, ano, tri = (array("q") for _ in range(5))
        cur = dst.execute(f"SELECT u.familia, u.chave, u.uasg, u.ano, u.trimestre FROM universo u JOIN _amp USING (familia) "
                          f"WHERE {filtro}")
        while True:
            bloco = cur.fetchmany(lote)
            if not bloco:
                break
            for f, ch, ua, a, t in bloco:
                fam.append(self.idx[f])
                compra.append(cc.setdefault(ch, len(cc)))
                uasg.append(cu.setdefault(ua, len(cu)))
                ano.append(a)
                tri.append(ct.setdefault(t, len(ct)))
        self.fam, self.compra, self.uasg = (np.frombuffer(x, dtype=np.int64) for x in (fam, compra, uasg))
        self.ano, self.tri = np.frombuffer(ano, dtype=np.int64), np.frombuffer(tri, dtype=np.int64)
        self.tri_nomes = {i: t for t, i in ct.items()}
        n = len(cc)
        del cc
        # compra -> (uasg, ano, trimestre): uma compra pertence a uma UASG e a um trimestre
        self.compra_uasg = np.zeros(n, dtype=np.int64)
        self.compra_uasg[self.compra] = self.uasg
        self.compra_ano = np.zeros(n, dtype=np.int64)
        self.compra_ano[self.compra] = self.ano
        self.compra_tri = np.zeros(n, dtype=np.int64)
        self.compra_tri[self.compra] = self.tri

    def medir(self, mascara_fam):
        sel = mascara_fam[self.fam]
        compras = np.unique(self.compra[sel])
        if compras.size == 0:
            return {"compras": 0, "itens": 0, "uasgs": 0, "hhi_institucional": None, "n_efetivo_uasgs": None,
                    "compras_por_ano": {}, "compras_por_trimestre": {}}
        cu = np.bincount(self.compra_uasg[compras])
        h = hhi(cu[cu > 0].tolist())
        anos, na = np.unique(self.compra_ano[compras], return_counts=True)
        tris, nt = np.unique(self.compra_tri[compras], return_counts=True)
        return {"compras": int(compras.size), "itens": int(sel.sum()), "uasgs": int((cu > 0).sum()),
                "hhi_institucional": round(h, 6), "n_efetivo_uasgs": round(1 / h, 1),
                "compras_por_ano": {str(int(a)): int(n) for a, n in zip(anos, na)},
                "compras_por_trimestre": {self.tri_nomes[int(t)]: int(n) for t, n in zip(tris, nt)}}


def _executar(ctx, dst):
    par, reg, saidas = ctx["par"], ctx["reg"], ctx["saidas"]
    sens = par["sensibilidade"]
    inicial = par["triagem_inicial"]
    with reg.etapa("sensibilidade: grade fatorial"):
        fam, F = _carregar_familias(dst, "fam_metricas")
        brando = {d: (min(sens[d]) if d.endswith("_min") else max(sens[d])) for d in DIMENSOES}
        amplo = _passa(F, brando)
        fam_amplo = [f for f, ok in zip(fam, amplo) if ok]
        cob = Cobertura(dst, fam_amplo)
        # máscara no espaço da triagem ampla
        sub = {k: (v[amplo] if isinstance(v, np.ndarray) else v) for k, v in F.items()}
        linhas = []
        for combo in itertools.product(*[sens[d] for d in DIMENSOES]):
            lim = dict(zip(DIMENSOES, combo))
            m = _passa(sub, lim)
            cand = m & sub["cadastral_ok"] & np.isin(sub["classe"], ["A", "B"])
            medida = cob.medir(cand)
            dif = [d for d in DIMENSOES if lim[d] != inicial[d]]
            linhas.append({**lim, "dimensoes_alteradas": "+".join(dif) if dif else "(inicial)",
                           "uma_dimensao": int(len(dif) <= 1), "familias_elegiveis": int(m.sum()),
                           "familias_qualidade_cadastral": int((m & sub["cadastral_ok"]).sum()),
                           "produtos_candidatos_familia": int(cand.sum()),
                           "classe_A": int((cand & (sub["classe"] == "A")).sum()),
                           "classe_B": int((cand & (sub["classe"] == "B")).sum()),
                           "classe_C": int((m & (sub["classe"] == "C")).sum()),
                           "compras_cobertas": medida["compras"], "itens_cobertos": medida["itens"],
                           "uasgs_cobertas": medida["uasgs"], "hhi_institucional": medida["hhi_institucional"],
                           "n_efetivo_uasgs": medida["n_efetivo_uasgs"],
                           "trimestres_medios_por_produto": round(float(sub["trimestres"][cand].mean()), 2) if cand.any() else None,
                           "compras_por_ano": json.dumps(medida["compras_por_ano"]),
                           "compras_por_trimestre": json.dumps(medida["compras_por_trimestre"])})
        cols = list(linhas[0].keys())
        comum.escrever_csv(saidas / "sensibilidade_grade.csv", linhas, cols)
        comum.escrever_csv(saidas / "sensibilidade_uma_dimensao.csv", [l for l in linhas if l["uma_dimensao"]], cols)
        reg.contar("sensibilidade_cenarios_grade", len(linhas))
        reg.contar("sensibilidade_familias_triagem_ampla", len(fam_amplo))

    with reg.etapa("sensibilidade: cenários nomeados e interseções"):
        fam_h, F_h = _carregar_familias(dst, "fam_metricas_hom")
        conjuntos, resumo = {}, []
        for nome, lim in sens["cenarios_nomeados"].items():
            base = lim.get("base", "licitados")
            ff, FF = (fam_h, F_h) if base == "homologados" else (fam, F)
            m = _passa(FF, lim) & FF["cadastral_ok"] & np.isin(FF["classe"], ["A", "B"])
            conj = {f for f, ok in zip(ff, m) if ok}
            conjuntos[nome] = conj
            mask = np.array([f in conj for f in fam_amplo], dtype=bool)
            fora = len(conj - set(fam_amplo))
            medida = cob.medir(mask)
            pos = {f: i for i, f in enumerate(fam)}
            tri = [F["trimestres"][pos[f]] for f in conj if f in pos] if conj else []
            resumo.append({"cenario": nome, "base": base, **{d: lim[d] for d in DIMENSOES}, "produtos_familia": len(conj),
                           "fora_da_triagem_ampla": fora, **{k: v for k, v in medida.items() if not k.startswith("compras_por")},
                           "trimestres_medios": round(float(np.mean(tri)), 2) if tri else None,
                           "compras_por_ano": json.dumps(medida["compras_por_ano"])})
        comum.escrever_csv(saidas / "sensibilidade_cenarios.csv", resumo, list(resumo[0].keys()))
        inter = []
        nomes = list(conjuntos)
        for a, b in itertools.combinations(nomes, 2):
            A, B = conjuntos[a], conjuntos[b]
            inter.append({"cenario_a": a, "cenario_b": b, "produtos_a": len(A), "produtos_b": len(B),
                          "comuns": len(A & B), "exclusivos_a": len(A - B), "exclusivos_b": len(B - A),
                          "jaccard": round(len(A & B) / len(A | B), 4) if (A | B) else None})
        comum.escrever_csv(saidas / "sensibilidade_intersecoes.csv", inter, list(inter[0].keys()))
        pertenca = sorted(set().union(*conjuntos.values()))
        comum.escrever_csv(saidas / "sensibilidade_pertinencia.csv",
                           [{"familia": f, **{n: int(f in conjuntos[n]) for n in nomes}} for f in pertenca], ["familia"] + nomes)

    with reg.etapa("recorrência temporal da cesta candidata (seção 15)"):
        janelas = par["temporal"]["janelas_recorrencia"]
        cur = dst.execute("""SELECT k.id_candidato, k.produto, u.data_publicacao, u.chave, u.uasg
                             FROM universo_produto u JOIN cesta_candidata_tab k USING (produto)""")
        por, cod = {}, {}

        def linhas():
            while True:
                bloco = cur.fetchmany(200_000)
                if not bloco:
                    return
                for idc, prod, data, ch, ua in bloco:
                    yield idc, prod, data, cod.setdefault(ch, len(cod)), cod.setdefault("U" + ua, len(cod))
        for idc, prod, data, ch, ua in linhas():
            d = por.setdefault((idc, prod), {"jan": [[set(), set()] for _ in janelas], "primeira": data})
            d["primeira"] = min(d["primeira"], data)
            for j, (ini, fim) in enumerate(janelas):
                if ini <= data <= fim:
                    d["jan"][j][0].add(ch)
                    d["jan"][j][1].add(ua)
        pre = par["temporal"].get("recorrencia_pre", {"compras_min": 10, "uasgs_min": 5})
        lin = []
        for (idc, prod), d in sorted(por.items()):
            l = {"id_candidato": idc, "produto": prod, "primeira_compra": d["primeira"]}
            for j, (ini, fim) in enumerate(janelas):
                l[f"compras_{ini[:7]}_{fim[:7]}"] = len(d["jan"][j][0])
                l[f"uasgs_{ini[:7]}_{fim[:7]}"] = len(d["jan"][j][1])
            l["comum_primeira_janela"] = int(len(d["jan"][0][0]) >= pre["compras_min"] and len(d["jan"][0][1]) >= pre["uasgs_min"])
            l["presente_todas_janelas"] = int(all(len(x[0]) > 0 for x in d["jan"]))
            lin.append(l)
        if lin:
            comum.escrever_csv(saidas / "recorrencia_temporal.csv", lin, list(lin[0].keys()))
        reg.contar("recorrencia", {"produtos": len(lin), "comum_primeira_janela": sum(l["comum_primeira_janela"] for l in lin),
                                   "presente_todas_janelas": sum(l["presente_todas_janelas"] for l in lin),
                                   "criterio_comum_primeira_janela": pre})
    dst.close()


def cesta_periodo_formacao(dst, ini, fim, lim, tabela="fam_metricas_formacao"):
    """Estrutura para uma futura cesta com período de formação explícito (NÃO aplicada aqui).
    Recalcula as métricas só com compras publicadas em [ini, fim] e aplica os mesmos limiares."""
    from .metricas import metricas_familias, aplica_limiares
    metricas_familias(dst, tabela, periodo=(ini, fim))
    cur = dst.execute(f"SELECT * FROM {tabela}")
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r))["familia"] for r in cur.fetchall() if aplica_limiares(dict(zip(cols, r)), lim)[0]]


def executar(ctx):
    dst = comum.conectar_trabalho(ctx["trabalho_db"])
    try:
        _executar(ctx, dst)
    finally:
        try:
            dst.close()
        except Exception:
            pass
