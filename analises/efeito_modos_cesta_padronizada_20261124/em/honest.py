"""Etapa 9: entradas do HonestDiD a partir dos draws do bootstrap de CADA especificação, execução do R e tabela.

Coeficientes no tempo de evento (referência e = −1, isto é, F−1): pré = placebos l = −Lpre..−1 (e = −1−k),
pós = DID_l, l = 1..L (e = l−1). Alvo: média dos efeitos pós com os pesos da própria estimativa agregada.
"""
import glob
import os
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from . import comum


def montar(draws_all, especs, grupos):
    man, bet, sig = [], [], []
    for nome in especs:
        if nome not in draws_all:
            continue
        chaves, draws, ponto = draws_all[nome]
        for g in grupos:
            pre = sorted([k for k in chaves if k[0] == g and isinstance(k[1], int) and k[1] < 0], key=lambda k: k[1])
            pos = sorted([k for k in chaves if k[0] == g and isinstance(k[1], int) and k[1] > 0], key=lambda k: k[1])
            if not pre or not pos:
                continue
            ks = pre + pos
            j = [chaves.index(k) for k in ks]
            D = draws[:, j]
            D = D[np.isfinite(D).all(1)]
            if D.shape[0] < 50:
                continue
            S = np.cov(D, rowvar=False)
            b = np.array([ponto[k] for k in ks])
            if not np.isfinite(b).all():
                continue
            ident = f"{nome}|{g}"
            l_vec = np.ones(len(pos)) / len(pos)
            man.append({"id": ident, "numPre": len(pre), "numPost": len(pos), "l_vec": ";".join(str(float(x)) for x in l_vec),
                        "draws_validos": int(D.shape[0])})
            bet += [{"id": ident, "ordem": i + 1, "beta": float(v), "evento": (k[1] - 0) if k[1] > 0 else k[1]}
                    for i, (k, v) in enumerate(zip(ks, b))]
            sig += [{"id": ident, "i": a + 1, "j": c + 1, "valor": float(S[a, c])} for a in range(len(ks)) for c in range(len(ks))]
    return man, bet, sig


def rscript():
    cands = sorted(glob.glob(r"C:\Program Files\R\R-*\bin\Rscript.exe"))
    return cands[-1] if cands else "Rscript"


def executar(ctx, abrir):
    cfg, reg, saidas = ctx["cfg"], ctx["reg"], ctx["saidas"]
    h = cfg["honestdid"]
    draws_all = abrir(ctx, "eventos_draws")
    especs = [f"dcdh_{j}_item_celula" for j in cfg["eventos"]["janelas_trimestres"]]
    man, bet, sig = montar(draws_all, especs, ["agregado", "adocao", "abandono"])
    pasta = ctx["dados"] / "honestdid"
    ent = pasta / "entradas"
    ent.mkdir(parents=True, exist_ok=True)
    for m in man:
        m["mbar"] = ";".join(map(str, h["Mbar_RM"]))
        m["msd"] = ";".join(map(str, h["M_SD_lp"]))
    pd.DataFrame(man).to_csv(ent / "manifesto.csv", index=False)
    pd.DataFrame(bet).to_csv(ent / "beta.csv", index=False)
    pd.DataFrame(sig).to_csv(ent / "sigma.csv", index=False)
    if not man:
        reg.aviso("HonestDiD: nenhuma especificação com pré e pós-períodos e covariância válida")
        comum.escrever_csv(saidas / "honestdid.csv", [{"situacao": "não calculado: sem especificação elegível"}])
        return
    with reg.etapa(f"HonestDiD (R) em {len(man)} especificações"):
        r = subprocess.run([rscript(), str(ctx["saidas"] / "honestdid.R"), str(pasta)], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode != 0:
            reg.aviso("HonestDiD falhou: " + r.stderr[-800:])
            comum.escrever_csv(saidas / "honestdid.csv", [{"situacao": "falha do R", "erro": r.stderr[-800:]}])
            return
    out = pd.read_csv(pasta / "honestdid_r.csv")
    amb = pd.read_csv(pasta / "honestdid_r_ambiente.csv")
    out["inclui_zero"] = (out.lb <= 0) & (out.ub >= 0)
    out["classificacao"] = "exploratório"
    out.to_csv(saidas / "honestdid.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(man).to_csv(saidas / "tabelas" / "honestdid_manifesto.csv", index=False, encoding="utf-8-sig")
    reg.contar("honestdid", {"especificacoes": len(man), "r": amb.to_dict("records")})
