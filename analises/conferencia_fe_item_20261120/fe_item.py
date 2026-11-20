"""Confere: painel empilhado (2 obs./item) com FE de item (within) = primeira diferença do analise_etapas.py.
Rodar da raiz do projeto: python analises/conferencia_fe_item_20261120/fe_item.py (lê a base dos 31 meses e ../dados/pncp.db)."""
import sys, numpy as np, pandas as pd
from scipy import stats
sys.path.insert(0, ".")
import analise_etapas as ae

df = ae.ligar_pncp(ae.ler_bancos(["dados/extracao/aberto-fechado_2025-03_a_2026-10.db"], None), "../dados/pncp.db")
df, _ = ae.preparar(df)
s = df[df.na_amostra].copy(); v = s[s.validos_ok].copy()

def fe_item(d, suf):
    ab = d.melhor_lance_modo_aberto if suf == "" else d.melhor_lance_modo_aberto_validos
    ap = d.melhor_apos if suf == "" else d.apos_v
    r = d[d.quantidade_fornecedores.notna() & (d.quantidade_fornecedores > 0) & (d.valor_estimado_total > 0)]
    r = r[r.material_ou_servico.isin(["M", "S"]) & r.orcamento_sigiloso.isin([0, 1])]
    ab, ap = ab.loc[r.index], ap.loc[r.index]
    Z = [np.log(r.quantidade_fornecedores.astype(float)), r.orcamento_sigiloso.astype(float),
         (r.material_ou_servico == "S").astype(float), np.log(r.valor_estimado_total.astype(float))]
    Z += [(r.mes == m).astype(float) for m in sorted(r.mes.unique())[1:]]
    Z = np.column_stack(Z); Z = Z - Z.mean(axis=0)
    n = len(r)
    # empilha: linha 0 = etapa aberta (F=0), linha 1 = após a fechada (F=1)
    y = np.r_[100 * np.log(ab.to_numpy()), 100 * np.log(ap.to_numpy())]
    F = np.r_[np.zeros(n), np.ones(n)]
    X = np.column_stack([F, F[:, None] * np.vstack([Z, Z])])
    item = np.r_[np.arange(n), np.arange(n)]
    # within: subtrai a média do item (cada item tem 2 obs.)
    def dm(a):
        m = (a[:n] + a[n:]) / 2
        return a - np.concatenate([m, m])
    yw, Xw = dm(y), dm(X)
    A = np.linalg.inv(Xw.T @ Xw); b = A @ Xw.T @ yw; u = yw - Xw @ b
    g = np.r_[r.uasg.to_numpy(), r.uasg.to_numpy()]
    _, idx = np.unique(g, return_inverse=True); G = idx.max() + 1; N, k = Xw.shape
    S = np.zeros((G, k)); np.add.at(S, idx, Xw * u[:, None])
    # gl: N obs. − n efeitos de item − k
    V = A @ (S.T @ S) @ A * (G / (G - 1)) * ((N - 1) / (N - n - k)); se = np.sqrt(np.diag(V))
    return b[:4], se[:4], n, G

for nome, suf, d in [("todos os fornecedores", "", s), ("só fornecedores válidos", "_v", v)]:
    fd = pd.DataFrame(ae.regressao(d, suf, nome, True)).set_index("regressor")
    b, se, n, G = fe_item(d, suf)
    print(f"\n{nome}: n itens {n}, UASGs {G}")
    for i, rg in enumerate(["F (etapa fechada)", "F_x_ln_lic", "F_x_sigiloso", "F_x_servico"]):
        print(f"  {rg:18s} PD {fd.loc[rg,'coef']:8.3f} ({fd.loc[rg,'ep']:.3f})   FE item {b[i]:8.3f} ({se[i]:.3f})   dif {abs(b[i]-fd.loc[rg,'coef']):.1e}")
