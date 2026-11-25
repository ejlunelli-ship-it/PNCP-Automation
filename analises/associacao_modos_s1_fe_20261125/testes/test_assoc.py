"""Testes do estudo associativo (sintéticos + integração com os arquivos reais, somente leitura)."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AQUI))

from assoc import amostra, comum, estimar  # noqa: E402
from assoc.comum import ErroDesenho  # noqa: E402

C = comum.cfg()


def itens_sinteticos():
    return pd.DataFrame({"chave": ["c1", "c1", "c1", "c2"], "produto": ["p", "p", "q", "p"], "p_hom": [10.0, 20.0, 5.0, 8.0],
                         "quantidade": [1.0, 3.0, 2.0, np.nan], "modo_disputa": ["Aberto"] * 3 + ["Aberto-Fechado"],
                         "uasg": ["u1"] * 3 + ["u2"], "orgao_cnpj": ["g1"] * 3 + ["g2"], "uf": ["SP"] * 3 + ["RJ"], "tri": [8100] * 4})


def painel_fe(seed=0, beta=-5.0, gamma=-10.0, n_cnpj=60, n_prod=30, n_tri=6, n_uf=5):
    rng = np.random.default_rng(seed)
    n = 12000
    d = pd.DataFrame({"cnpj": rng.integers(0, n_cnpj, n).astype(str), "produto": rng.integers(0, n_prod, n).astype(str),
                      "tri": rng.integers(8095, 8095 + n_tri, n)})
    d["uf"] = (d.cnpj.astype(int) % n_uf).astype(str)
    d["uasg"] = d.cnpj + "_" + rng.integers(0, 3, n).astype(str)
    d["chave"] = [f"k{i // 2}" for i in range(n)]
    a_c = rng.normal(0, 10, n_cnpj)
    pa = d.cnpj.astype(int).map(lambda x: 0.2 + 0.6 * (x % 2))
    d["af"] = (rng.random(n) < pa).astype(np.int8)
    d["af"] = d.groupby("chave").af.transform("first")
    d["lnq"] = rng.normal(3, 1, n) + 0.5 * d.af
    cel = d.groupby(["uf", "produto", "tri"]).ngroup()
    dlt = rng.normal(0, 20, cel.max() + 1)
    d["y"] = beta * d.af + a_c[d.cnpj.astype(int)] + dlt[cel] + gamma * d.lnq + rng.normal(0, 2, n)
    return d


class Amostra(unittest.TestCase):
    def test_01_agregacao_ponderada(self):
        a = amostra.agregar(itens_sinteticos()).set_index(["chave", "produto"])
        self.assertAlmostEqual(a.loc[("c1", "p"), "preco"], (10 * 1 + 20 * 3) / 4)
        self.assertEqual(a.loc[("c1", "p"), "n_itens"], 2)
        self.assertAlmostEqual(a.loc[("c1", "p"), "y"], 100 * np.log(17.5))

    def test_02_media_simples_sem_quantidade(self):
        a = amostra.agregar(itens_sinteticos()).set_index(["chave", "produto"])
        self.assertFalse(a.loc[("c2", "p"), "ponderado_por_quantidade"])
        self.assertTrue(np.isnan(a.loc[("c2", "p"), "lnq"]))

    def test_03_modo_e_atributo_da_compra(self):
        it = itens_sinteticos()
        it.loc[2, "modo_disputa"] = "Aberto-Fechado"
        with self.assertRaises(ErroDesenho):
            amostra.agregar(it)

    def test_04_sem_duplicacao(self):
        a = amostra.agregar(itens_sinteticos())
        self.assertFalse(a.duplicated(["chave", "produto"]).any())
        self.assertEqual(a.n_itens.sum(), 4)

    def test_05_peso_por_compra(self):
        a = amostra.agregar(itens_sinteticos())
        w = estimar.peso_por_compra(a)
        np.testing.assert_allclose(pd.Series(w).groupby(a.chave.to_numpy()).sum(), 1.0)


class Estimacao(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = painel_fe()

    def test_06_um_fe_exato(self):
        f = estimar.codificar(self.d.cnpj.to_numpy())
        M, info = estimar.absorver(self.d[["y"]].to_numpy(), [f], np.ones(len(self.d)))
        g = self.d.groupby("cnpj").y.transform("mean").to_numpy()
        np.testing.assert_allclose(M[:, 0], self.d.y - g, atol=1e-9)
        self.assertTrue(info["convergiu"])

    def test_07_dois_fe_igual_dummies(self):
        d = self.d.iloc[:1500]
        r = estimar.estimar(d, ["uf_prod_tri", "cnpj"], diagnosticos=False)
        sub = d.iloc[r["_sub_idx"]]
        X = pd.get_dummies(sub[["cnpj"]].astype(str), drop_first=False).astype(float)
        X2 = pd.get_dummies((sub.uf + "|" + sub.produto + "|" + sub.tri.astype(str)), drop_first=True).astype(float)
        Z = np.column_stack([sub.af, sub.lnq, X, X2])
        b = np.linalg.lstsq(Z, sub.y.to_numpy(), rcond=None)[0]
        self.assertAlmostEqual(r["beta_lp"], b[0], 6)
        self.assertLess(r["conv_max_media_residual_grupos"], 1e-6)

    def test_08_map_e_lsmr_coincidem(self):
        f = [estimar.codificar(self.d.uf.to_numpy(), self.d.produto.to_numpy(), self.d.tri.to_numpy()),
             estimar.codificar(self.d.cnpj.to_numpy())]
        M = self.d[["y", "af"]].to_numpy(float)
        a, _ = estimar.absorver(M, f, np.ones(len(M)))
        b, _ = estimar.absorver_map(M, f, np.ones(len(M)), 1e-11, 100000)
        np.testing.assert_allclose(a, b, atol=1e-6)

    def test_09_recupera_beta(self):
        r = estimar.estimar(self.d, ["uf_prod_tri", "cnpj"], B=199, semente=1)
        self.assertAlmostEqual(r["beta_lp"], -5.0, delta=4 * r["ep_cr1_cnpj"])
        self.assertAlmostEqual(r["gamma_lnq"], -10.0, delta=0.5)

    def test_10_singletons(self):
        d = self.d.copy()
        d.loc[0, "cnpj"] = "unico"
        r = estimar.estimar(d, ["cnpj"], diagnosticos=False)
        self.assertGreaterEqual(r["singletons_removidos"], 1)
        self.assertNotIn(0, set(r["_sub_idx"]))

    def test_11_m3_dentro_da_celula(self):
        d = self.d.copy()
        r = estimar.estimar(d, ["cnpj_prod_tri"], com_q=False, diagnosticos=False)
        sub = d.iloc[r["_sub_idx"]]
        g = sub.groupby(["cnpj", "produto", "tri"])
        yd, xd = sub.y - g.y.transform("mean"), sub.af - g.af.transform("mean")
        self.assertAlmostEqual(r["beta_lp"], float((xd * yd).sum() / (xd ** 2).sum()), 8)

    def test_12_contribuicoes_e_numero_efetivo(self):
        r = estimar.estimar(self.d, ["uf_prod_tri", "cnpj"])
        self.assertAlmostEqual(float(r["_contrib_cnpj"].sum()), 1.0, 10)
        self.assertAlmostEqual(float(r["_contrib_uf"].sum()), 1.0, 10)
        self.assertAlmostEqual(r["n_efetivo_cnpjs"], 1 / np.sum(r["_contrib_cnpj"].to_numpy() ** 2), 8)
        self.assertLessEqual(r["n_efetivo_cnpjs"], r["cnpjs"])

    def test_13_css_aninhado(self):
        r = estimar.estimar(self.d, ["cnpj_prod_tri"])
        self.assertTrue(np.isnan(r["G_css_rho1"]))      # FE aninhado no cluster: ρ = 1 indefinido
        self.assertAlmostEqual(r["G_css_rho0"], r["n_efetivo_cnpjs"], 10)

    def test_14_celulas_dois_modos(self):
        sub = pd.DataFrame({"cnpj": ["a", "a", "a", "b", "b"], "produto": ["p"] * 5, "tri": [1, 1, 2, 1, 1],
                            "af": [0, 1, 1, 0, 0], "chave": list("vwxyz")})
        r = estimar.celulas_dois_modos(sub, "cnpj_prod_tri")
        self.assertEqual((r["celulas"], r["celulas_com_A_e_AF"], r["compras_em_celulas_com_A_e_AF"]), (3, 1, 2))

    def test_15_wcr_mesma_semente(self):
        a = estimar.estimar(self.d, ["cnpj_prod_tri"], B=499, semente=7)
        b = estimar.estimar(self.d, ["cnpj_prod_tri"], B=499, semente=7)
        self.assertEqual(a["p_wcr_webb"], b["p_wcr_webb"])

    def test_16_exclusao_completa_cnpj(self):
        g = self.d.cnpj.iat[0]
        r = estimar.estimar(self.d, ["uf_prod_tri", "cnpj"], mascara=(self.d.cnpj != g).to_numpy(), diagnosticos=False)
        self.assertFalse((self.d.iloc[r["_sub_idx"]].cnpj == g).any())

    def test_17_pct_exato_e_peso(self):
        w = np.ones(len(self.d))
        r = estimar.estimar(self.d, ["cnpj_prod_tri"], peso=w)
        r0 = estimar.estimar(self.d, ["cnpj_prod_tri"])
        self.assertAlmostEqual(r["beta_lp"], r0["beta_lp"], 10)
        self.assertAlmostEqual(r["pct_exato"], 100 * np.expm1(r["beta_lp"] / 100), 10)


class Viabilidade(unittest.TestCase):
    def test_23_sequencia_e_eventos(self):
        from assoc import viabilidade_cnpj as vc
        self.assertEqual(vc.maior_sequencia({1, 2, 3, 5, 6}), 3)
        sh = pd.DataFrame({10: [0.0, 0.0], 11: [0.0, 1.0], 12: [1.0, 1.0], 13: [1.0, 0.0]}, index=["g", "h"])
        n = sh * 0 + 5
        ev = vc.eventos(sh, n, 10, 13, 0.5, 3).set_index("cnpj")
        self.assertEqual(int(ev.loc["g", "t0"]), 12)
        self.assertTrue(ev.loc["g", "persistente"])
        self.assertNotIn("h", ev.index)          # 0→1→1→0: média pré 0,5, pós 0,5

    def test_24_decomposicao_soma(self):
        from assoc import viabilidade_cnpj as vc
        uq = pd.DataFrame({"cnpj": ["g"] * 6, "uasg": ["a", "b", "a", "b", "a", "c"], "tri": [8, 8, 9, 10, 11, 11],
                           "n": [4, 2, 4, 4, 2, 6], "n_af": [0, 1, 0, 4, 2, 6]})
        ev = pd.DataFrame({"cnpj": ["g"], "t0": [10]})
        d = vc.decomposicao(ev, uq).iloc[0]
        self.assertAlmostEqual(d.dentro_uasgs + d.composicao_uasgs + d.entrada_saida_uasgs, d.delta, 12)


class Reais(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p = comum.trabalho(C, "amostra_compra_produto.pkl.gz")
        cls.A = comum.ler_pkl(p) if p.exists() else None

    def setUp(self):
        if self.A is None:
            self.skipTest("amostra real não construída")

    def test_18_amostra_S1_e_filtros(self):
        d = self.A["d"]
        s1, s2 = amostra.lista_S1(C)
        self.assertTrue(set(d.produto) <= set(s1))
        self.assertFalse(set(d.produto) & set(s2))
        self.assertTrue((d.preco > 0).all() and d.af.isin([0, 1]).all())
        self.assertTrue(set(d.modo) <= {"Aberto", "Aberto-Fechado"})
        self.assertEqual(int(d.n_itens.sum()), int(self.A["funil"].query("etapa == '7_produto_S1'").itens.iat[0]))

    def test_19_chaves_consistentes(self):
        d = self.A["d"]
        self.assertFalse(d.duplicated(["chave", "produto"]).any())
        for k in ("modo", "uasg", "cnpj", "uf", "tri"):
            self.assertTrue((d.groupby("chave")[k].nunique() == 1).all(), k)
        conf = self.A["agreg"]["conferencia_banco"]
        self.assertTrue(all(v == 0 for v in conf.values()), conf)

    def test_20_banco_inalterado(self):
        from em.comum import impressao_digital
        b = self.A["agreg"]["banco"]
        atual = impressao_digital(b["caminho"])
        for k in ("tamanho_bytes", "mtime_ns", "sha256_inicio_fim", "sqlite_contador_alteracoes"):
            self.assertEqual(atual[k], b[k], k)

    def test_21_resultados_anteriores_intactos(self):
        rod = comum.resolver(C["fontes"]["rodada_S1"])
        cong = comum.ler_json(rod / "congelamento.json")
        self.assertEqual(comum.sha(rod / "tabelas" / "conjuntos_amostras.csv"), cong["sha256_conjuntos_amostras"])
        rs = comum.RISK / "resultados"
        prot = comum.ler_json(rs / "protocolo_congelado.json")
        self.assertEqual(comum.hash_df(pd.read_parquet(rs / "pares_congelados.parquet")), prot["pares_sha256_conteudo"])

    def test_22_reproducao_M3(self):
        m = comum.TAB / "modelos.csv"
        if not m.exists():
            self.skipTest("modelos não estimados")
        R = pd.read_csv(m)
        r0 = R[(R.modelo == "M3") & (R.variante == "principal")].iloc[0]
        r = estimar.estimar(self.A["d"], C["modelos"]["M3"]["fe"], diagnosticos=False)
        self.assertAlmostEqual(r["beta_lp"], r0.beta_lp, 8)
        self.assertEqual(r["obs"], r0.obs)


if __name__ == "__main__":
    unittest.main()
