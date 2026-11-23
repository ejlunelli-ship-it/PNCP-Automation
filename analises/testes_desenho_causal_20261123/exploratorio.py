"""Verificações EXPLORATÓRIAS, feitas depois de ver os resultados (desvio registrado no relatório, §10):
concentração dos pesos por CNPJ e estimativa principal sem cada um dos 5 CNPJs de maior peso.

Uso (da pasta PNCP-Automation): python analises/testes_desenho_causal_20261123/exploratorio.py
Lê eventos_did.csv e poder.json; grava exploratorio.json.
"""
import json

import numpy as np
import pandas as pd

import comum as C

esp = json.loads((C.AQUI / "especificacao.json").read_text(encoding="utf-8"))
V = json.loads((C.AQUI / "poder.json").read_text(encoding="utf-8"))[f"W{esp['W']}_cmin{esp['cmin']}"]["var_modelo"]
d = pd.read_csv(C.AQUI / "eventos_did.csv", dtype={"cnpj": str})
d["w"] = 1 / np.maximum(V["a"] + V["b"] * d.h, 1e-6)
out = {"concentracao": {}}
for nome, z in [("todos", d)] + list(d.groupby("tipo")):
    s = z.groupby("cnpj").w.sum() / z.w.sum()
    s2 = z.groupby("cnpj").size() / len(z)
    out["concentracao"][nome] = {"cnpjs": int(len(s)), "maior_peso": float(s.max()), "cinco_maiores": float(s.nlargest(5).sum()),
                                 "cnpjs_efetivos": float(1 / (s ** 2).sum()), "cnpjs_efetivos_pesos_iguais": float(1 / (s2 ** 2).sum())}
ordem = d.groupby("cnpj").w.sum().sort_values(ascending=False).index[:5]
out["sem_cnpj"] = {}
for k, c in enumerate(ordem, 1):
    z = d[d.cnpj != c]
    out["sem_cnpj"][f"{k}º maior peso"] = float(np.average(z.sinal * z.did, weights=z.w))
out["efeito_AF"] = float(np.average(d.sinal * d.did, weights=d.w))
(C.AQUI / "exploratorio.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=1))
