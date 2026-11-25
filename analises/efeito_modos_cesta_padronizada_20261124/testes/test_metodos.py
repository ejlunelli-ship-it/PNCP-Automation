"""Testes unitários dos métodos: referências LOO, transformação exata, eventos, dCDH, inferência agrupada, Holm."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from em import comum  # noqa: E402
from em.eventos import DCDH, IRREGULAR, NUNCA, SEM_PRE, TROCA, bjs, bootstrap, classificar_unidades  # noqa: E402
from em.inferencia import codificar, demean, holm, ols_fe, remover_singletons, vcov_cluster  # noqa: E402
from em.referencias import VARIANTES, calcular  # noqa: E402


def _pool(n=300, semente=1):
    rng = np.random.default_rng(semente)
    return pd.DataFrame({"produto": rng.choice(["p1", "p2"], n), "tri": rng.choice([1, 2], n),
                         "uasg": rng.choice([f"u{i}" for i in range(7)], n), "logp": rng.normal(2, .5, n)})


class Referencias(unittest.TestCase):
    def test_forca_bruta_todas_as_variantes(self):
        pool = _pool()
        r = calcular(pool)
        for i in range(0, len(pool), 11):
            c = pool.iloc[i]
            o = pool[(pool.produto == c.produto) & (pool.tri == c.tri) & (pool.uasg != c.uasg)]
            lp = np.sort(o.logp.to_numpy())
            g = o.groupby("uasg").logp
            self.assertAlmostEqual(r.ref_A1.iat[i], lp.mean(), 12)
            self.assertAlmostEqual(r.ref_A3.iat[i], np.median(lp), 12)
            self.assertAlmostEqual(r.ref_B5.iat[i], g.mean().mean(), 12)
            self.assertAlmostEqual(r.ref_B9.iat[i], np.median(g.median()), 12)

    def test_uasg_focal_completamente_excluida(self):
        pool = _pool()
        r0 = calcular(pool)
        p2 = pool.copy()
        foco = p2.uasg == "u3"
        p2.loc[foco, "logp"] += 50.0                      # preços absurdos da focal não mexem na sua referência
        r1 = calcular(p2)
        for k in VARIANTES:
            np.testing.assert_allclose(r0.loc[foco, f"ref_{k}"], r1.loc[foco, f"ref_{k}"], atol=1e-12)

    def test_minimos_e_amostra_comum(self):
        pool = _pool(60)
        r = calcular(pool, min_itens=5, min_uasgs=3)
        ok = r.ref_ok.to_numpy()
        self.assertTrue(((r.n_outros >= 5) & (r.k_outros >= 3)).to_numpy()[ok].all())
        for k in VARIANTES:                               # todas definidas exatamente onde os mínimos valem
            np.testing.assert_array_equal(r[f"ref_{k}"].notna().to_numpy(), ok)


class Gravacao(unittest.TestCase):
    def test_csv_linhas_heterogeneas_nao_perdem_colunas(self):
        import csv, tempfile
        with tempfile.TemporaryDirectory() as t:
            arq = comum.escrever_csv(Path(t) / "x.csv", [{"a": 1}, {"a": 2, "b": 3}, {"c": 4}])
            with open(arq, encoding="utf-8-sig") as f:
                linhas = list(csv.DictReader(f))
            self.assertEqual(list(linhas[0].keys()), ["a", "b", "c"])
            self.assertEqual(linhas[1]["b"], "3")
            self.assertEqual(linhas[2]["c"], "4")


class Transformacao(unittest.TestCase):
    def test_log_pontos_para_percentual_exato(self):
        self.assertAlmostEqual(float(comum.pct_exato(-5.0)), 100 * (np.exp(-0.05) - 1), 12)
        self.assertAlmostEqual(float(comum.pct_exato(0.0)), 0.0)
        self.assertNotAlmostEqual(float(comum.pct_exato(-20.0)), -20.0, 2)


def _reg(seqs):
    linhas = []
    for u, s in seqs.items():
        for t, d in enumerate(s):
            if d is not None:
                linhas.append({"uasg": u, "tri": t, "D": d, "puro": 1})
    return pd.DataFrame(linhas)


class Eventos(unittest.TestCase):
    def test_regras_de_classificacao(self):
        info = classificar_unidades(_reg({
            "troca": [0, 0, 1, 1, 1], "flip": [0, 0, 1, 0, 0], "gap": [0, None, 1, 1, 1],
            "nunca": [1, 1, 1, 1, 1], "volta": [1, 1, 0, 0, 1]}), 0, 4).set_index("uasg")
        self.assertEqual(info.loc["troca", "tipo"], TROCA)
        self.assertEqual(info.loc["troca", "F"], 2)
        self.assertEqual(info.loc["troca", "direcao"], "A->AF")
        self.assertEqual(info.loc["flip", "tipo"], IRREGULAR)
        self.assertEqual(info.loc["gap", "tipo"], SEM_PRE)
        self.assertEqual(info.loc["nunca", "tipo"], NUNCA)
        self.assertEqual(info.loc["volta", "direcao"], "AF->A")

    def _mundo(self, tau_in=10.0, tau_out=4.0, U=60, T=8):
        rng = np.random.default_rng(0)
        a = rng.normal(0, 5, U)
        lam = np.linspace(0, 3, T)
        tipos, d0, F = [], [], []
        Y = np.zeros((U, T))
        for u in range(U):
            if u < 20:
                tipos.append(NUNCA); d0.append(0); F.append(np.nan); D = np.zeros(T); tau = 0
            elif u < 35:
                tipos.append(NUNCA); d0.append(1); F.append(np.nan); D = np.ones(T); tau = tau_out
            elif u < 48:
                tipos.append(TROCA); d0.append(0); F.append(4); D = (np.arange(T) >= 4).astype(float); tau = tau_in
            else:
                tipos.append(TROCA); d0.append(1); F.append(5); D = (np.arange(T) < 5).astype(float); tau = tau_out
            Y[u] = a[u] + lam + tau * D
        info = pd.DataFrame({"tipo": tipos, "d0": d0, "F": F, "absorvente": [t == TROCA and d == 0 for t, d in zip(tipos, d0)]})
        return Y, np.ones((U, T)), info

    def test_adocao_e_abandono_separados(self):
        Y, N, info = self._mundo()
        e, _ = DCDH(Y, N, info, 2, 2).estimar()
        self.assertAlmostEqual(e[("adocao", "media")], 10.0, 9)
        self.assertAlmostEqual(e[("abandono", "media")], 4.0, 9)      # sinal normalizado: efeito do AF
        self.assertAlmostEqual(e[("simetria", "media")], 6.0, 9)
        self.assertAlmostEqual(e[("adocao", -1)], 0.0, 9)             # placebo sem pré-tendência

    def test_controles_sem_observacoes_futuras(self):
        Y, N, info = self._mundo()
        est = DCDH(Y, N, info, 2, 1)
        for b in est.blocos:
            ult = b["F"] - 1 + abs(b["l"])
            Fc = info.F.to_numpy(dtype=float)[b["c"]]
            self.assertTrue(np.all(np.isnan(Fc) | (Fc > ult)), "controle já tinha trocado")
        # mudar Y dos controles DEPOIS do último período usado não altera a estimativa
        e0, _ = est.estimar()
        Y2 = Y.copy()
        Y2[:35, 7] += 100.0
        e1, _ = DCDH(Y2, N, info, 2, 1).estimar()
        self.assertAlmostEqual(e0[("adocao", 1)], e1[("adocao", 1)], 9)

    def test_bjs_absorvente(self):
        Y, N, info = self._mundo()
        r = bjs(Y, N, info, 2)
        self.assertAlmostEqual(r["media"][0], 10.0, 6)

    def test_bootstrap_reprodutivel(self):
        Y, N, info = self._mundo()
        est = DCDH(Y + np.random.default_rng(1).normal(0, 1, Y.shape), N, info, 2, 1)
        cl = np.arange(len(info)) // 2
        a = bootstrap(est, cl, 30, 7)[3]
        b = bootstrap(est, cl, 30, 7)[3]
        np.testing.assert_array_equal(a, b)


class Inferencia(unittest.TestCase):
    def test_fe_igual_a_dummies(self):
        rng = np.random.default_rng(2)
        n = 400
        g1, g2 = rng.integers(0, 15, n), rng.integers(0, 9, n)
        x = rng.normal(size=n) + 0.3 * g1
        y = 2.0 * x + g1 * 0.5 - g2 * 0.2 + rng.normal(size=n)
        r = ols_fe(y, x, [codificar(g1), codificar(g2)], codificar(rng.integers(0, 20, n)), tol=1e-12)
        D = np.column_stack([x, np.eye(15)[g1], np.eye(9)[g2][:, 1:]])
        b = np.linalg.lstsq(D, y, rcond=None)[0]
        self.assertAlmostEqual(r["beta"][0], b[0], 8)

    def test_cr1_formula_manual(self):
        rng = np.random.default_rng(3)
        n, G = 300, 25
        cl = rng.integers(0, G, n)
        X = np.column_stack([np.ones(n), rng.normal(size=n)])
        e = rng.normal(size=n)
        V, g = vcov_cluster(X, e, cl)
        inv = np.linalg.inv(X.T @ X)
        meat = sum(np.outer(X[cl == k].T @ e[cl == k], X[cl == k].T @ e[cl == k]) for k in range(G))
        c = G / (G - 1) * (n - 1) / (n - 2)
        np.testing.assert_allclose(V, c * inv @ meat @ inv, rtol=1e-10)

    def test_duas_vias_e_wcr(self):
        rng = np.random.default_rng(4)
        n = 500
        c1, c2 = rng.integers(0, 30, n), rng.integers(0, 12, n)
        x = rng.normal(size=n)
        y = rng.normal(size=n) + rng.normal(size=30)[c1]
        r = ols_fe(y, x, [], c1, cluster2=c2, wcr=199, semente=5)
        r2 = ols_fe(y, x, [], c1, cluster2=c2, wcr=199, semente=5)
        self.assertTrue(0 <= r["p_wcr"] <= 1)
        self.assertEqual(r["p_wcr"], r2["p_wcr"])                     # reprodutível com a mesma semente
        self.assertGreater(r["se_2vias"][0], 0)

    def test_singletons(self):
        f = np.array([0, 0, 1, 2, 2, 3])
        np.testing.assert_array_equal(remover_singletons([f]), [1, 1, 0, 1, 1, 0])

    def test_holm(self):
        np.testing.assert_allclose(holm([0.01, 0.04, 0.03]), [0.03, 0.06, 0.06])


if __name__ == "__main__":
    unittest.main()
