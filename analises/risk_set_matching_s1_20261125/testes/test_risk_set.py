"""40 testes do risk-set matching + DiD (sintéticos e de integração com os arquivos reais congelados)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AQUI))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import sintetico as S  # noqa: E402
from scripts import comum  # noqa: E402
from scripts import construir_covariaveis as cv  # noqa: E402
from scripts import desenho as ds  # noqa: E402
from scripts import diagnosticar_balanceamento as bal  # noqa: E402
from scripts import inferencia as inf  # noqa: E402
from scripts import realizar_matching as rm  # noqa: E402
from scripts import testar_composicao as tc  # noqa: E402
from scripts.construir_painel import A, AF, MISTO  # noqa: E402
from scripts.estimar_did import PainelPos, abrir_pos, montar_linhas  # noqa: E402
from scripts.executar_placebos import placebo  # noqa: E402

C = S.cfg()
REAIS = (AQUI / "resultados" / "protocolo_congelado.json").exists()


def rodar(P, metodos=(("M0", None), ("M1", None), ("PS", None), ("PSM", None))):
    ev = S.anotar(C, P)
    return ds.executar(C, P, ev, "sint", False, list(metodos)), ev


class Mundo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.P, cls.t0 = S.mundo_base()
        cls.s, cls.ev = rodar(cls.P)
        cls.pares = cls.s["pares"]
        cls.u = {n: i for i, n in enumerate(cls.P.unidades)}

    def ide(self, u, t=None):
        return f"{self.P.unidades[u]}_{comum.nome_tri(t or self.t0)}"

    def controles(self, u, metodo="M0"):
        p = self.pares[(self.pares.metodo == metodo) & (self.pares.id_evento == self.ide(u))]
        return set(p.u_controle)

    # 1–6 conjuntos de risco
    def test_01_risco_adocao(self):
        cand = set(self.s["cand"][self.ide(0)])
        self.assertTrue(cand)
        st = self.P.arr["status"]
        j = self.P.j(self.t0)
        self.assertTrue(all(st[v, j] == A and st[v, j - 1] == A for v in cand))

    def test_02_risco_abandono(self):
        cand = set(self.s["cand"][self.ide(20)])
        st = self.P.arr["status"]
        j = self.P.j(self.t0)
        self.assertTrue(cand and all(st[v, j] == AF and st[v, j - 1] == AF for v in cand))

    def test_03_mesmo_trimestre(self):
        self.assertTrue((self.pares.t0 == self.pares.id_evento.str.split("_").str[1].map(comum.tri)).all())

    def test_04_mesma_origem(self):
        pop = self.s["pop"]["A->AF"]
        self.assertTrue((pop[pop.candidata].trimestres_no_regime >= 1).all())
        self.assertFalse(set(self.s["cand"][self.ide(0)]) & set(range(20, 38)))

    def test_05_exclui_propria(self):
        self.assertTrue(all(self.pares.u_controle != self.pares.u_tratada))

    def test_06_exclui_mesmo_cnpj(self):
        self.assertNotIn(1, self.s["cand"][self.ide(0)])
        self.assertTrue((self.pares.cnpj_controle != self.pares.cnpj_tratada).all())

    # 7–9 sem dados futuros/reservados; PS de mudança
    def test_07_sem_precos_futuros_no_pareamento(self):
        P2, _ = S.mundo_base()
        j = P2.j(self.t0)
        P2.arr["Yc"][:, j:] += np.random.default_rng(7).normal(0, 50, P2.arr["Yc"][:, j:].shape)
        s2, _ = rodar(P2)
        cols = ["metodo", "id_evento", "u_controle", "peso"]
        pd.testing.assert_frame_equal(self.pares[cols].reset_index(drop=True), s2["pares"][cols].reset_index(drop=True))

    def test_08_sem_precos_reservados_no_pareamento(self):
        """Perturba t0−2 e t0−1 dos eventos de t0 = 2025T1 e compara os pares desses eventos (os de t0 = 2025T2
        usariam legitimamente 2024T4 como t−3, trimestre de formação em M1)."""
        P2, _ = S.mundo_base()
        j = P2.j(self.t0)
        P2.arr["Yc"][:, j - 2:j] += np.random.default_rng(8).normal(0, 50, P2.arr["Yc"][:, j - 2:j].shape)
        s2, _ = rodar(P2, (("M0", None), ("M1", None)))
        cols = ["metodo", "id_evento", "u_controle"]
        a = self.pares[self.pares.metodo.isin(["M0", "M1"]) & (self.pares.t0 == self.t0)][cols].reset_index(drop=True)
        b = s2["pares"][s2["pares"].t0 == self.t0][cols].reset_index(drop=True)
        self.assertGreater(len(a), 0)
        pd.testing.assert_frame_equal(a, b)

    def test_09_ps_de_mudanca(self):
        r = self.s["pop"]["A->AF"]
        risco = r[r.completo & (r.candidata | r.evento_elegivel)]
        st = self.P.arr["status"]
        self.assertTrue(all(st[int(u), self.P.j(t) - 1] == A for u, t in zip(risco.u, risco.t0)))
        ev = self.s["eventos"]
        esperado = set(ev[(ev.direcao == "A->AF") & ev.historico_suficiente].u)
        self.assertEqual(set(risco[risco.y == 1].u), esperado)
        self.assertFalse(set(risco[risco.y == 1].u) & set(range(20, 38)))   # não é a probabilidade de "estar em AF"
        self.assertIn("logit_ps", risco)

    # 10–12 trajetórias
    def test_10_controle_muda_depois(self):
        self.assertIn(6, self.s["cand"][self.ide(0)])          # continua no risco de t0
        p = self.pares[(self.pares.metodo == "M0") & (self.pares.id_evento == self.ide(0))]
        if 6 not in set(p.u_controle):
            p = pd.concat([p.iloc[:1].assign(u_controle=6, uasg_controle=self.P.unidades[6], cnpj_controle="C003"), p])
        L = montar_linhas(lambda t: PainelPos(self.P), p, 1, -1, censura_ate=1, status=PainelPos(self.P))
        self.assertNotIn(6, set(L[L.papel == "C"].u))           # censurado em h = 1
        L0 = montar_linhas(lambda t: PainelPos(self.P), p, 0, -1)
        self.assertIn(6, set(L0[L0.papel == "C"].u))

    def test_11_controle_reutilizado(self):
        c0, c2 = self.controles(0, "PS"), self.controles(2, "PS")
        self.assertTrue(c0 & c2)
        conc = bal.concentracao(self.pares[self.pares.metodo == "PS"])
        self.assertGreaterEqual(conc["reuso_max"], 2)

    def test_12_evento_repetido(self):
        e4 = self.ev[self.ev.u == 4].sort_values("t0")
        self.assertEqual(list(e4.episodio), [1, 2])
        self.assertEqual(list(e4.direcao), ["A->AF", "AF->A"])
        self.assertFalse(e4.iloc[1].historico_modo_compativel)
        self.assertEqual(e4.iloc[0]["persistencia_t0+1"], "persistente")

    # 13–15 regimes e suporte
    def test_13_trimestre_misto(self):
        self.assertEqual(self.P.arr["status"][8, self.P.j(comum.tri("2024T3"))], MISTO)
        self.assertTrue(self.ev[self.ev.u == 8].empty)

    def test_14_historico_insuficiente(self):
        e = self.s["eventos"].set_index("id_evento").loc[self.ide(10)]
        self.assertFalse(e.historico_suficiente)

    def test_15_sem_controle(self):
        e = self.s["eventos"].set_index("id_evento").loc[self.ide(38)]
        self.assertFalse(e.com_controles)
        self.assertNotIn(self.ide(38), set(self.pares.id_evento))

    # 16–19 calipers, k, pesos
    def test_16_caliper(self):
        p = self.pares[self.pares.metodo == "PS"]
        cal = C["matching"]["caliper_ps_dp_logit"] * self.s["ps"]["A->AF"]["diag"]["dp_logit_populacao"]
        pa = p[p.direcao == "A->AF"]
        self.assertTrue((pa.dif_logit_ps <= cal + 1e-12).all())
        u = rm.parear_evento(0, [1, 2], {0: np.zeros(2), 1: np.array([10.0, 0]), 2: np.array([0.1, 0])}, np.eye(2), 5, 3.0,
                             uasg={0: "a", 1: "b", 2: "c"})
        self.assertEqual([v for v, *_ in u[0]], [2])
        self.assertEqual(u[1]["fora_caliper_mahalanobis"], 1)

    def test_17_k_max(self):
        self.assertTrue((self.pares.groupby(["metodo", "id_evento"]).size() <= C["matching"]["k_max"]).all())
        s1, _ = rodar(self.P, (("M0_k1", 1),))
        self.assertTrue((s1["pares"].groupby("id_evento").size() == 1).all())

    def test_18_pesos_somam_1(self):
        np.testing.assert_allclose(self.pares.groupby(["metodo", "id_evento"]).peso.sum(), 1.0)

    def test_19_peso_igual_por_evento(self):
        L = montar_linhas(lambda t: PainelPos(self.P), self.pares[self.pares.metodo == "M0"], 0, -1)
        e = inf.eventos_tau(L)
        r = inf.contraste(L, None, B=0, margem=None)
        self.assertAlmostEqual(r["beta_lp"], e.tau.mean(), 10)

    # 20–21 sinal e DiD
    def _pares_forcados(self, u, k=5):
        """Pares diretamente do conjunto de risco (sem PS), para testar o cálculo do DiD em qualquer direção."""
        e = self.ev.set_index("id_evento").loc[self.ide(u)]
        cand = sorted(self.s["cand"][self.ide(u)])[:k]
        return pd.DataFrame([{"id_evento": self.ide(u), "t0": int(e.t0), "direcao": e.direcao, "sinal_af": int(e.sinal_af),
                              "u_tratada": u, "uasg_tratada": self.P.unidades[u], "cnpj_tratada": e.cnpj, "u_controle": v,
                              "uasg_controle": self.P.unidades[v], "cnpj_controle": self.P.attr["cnpj"][v], "peso": 1 / len(cand)}
                             for v in cand])

    def test_20_sinal_abandono(self):
        pm = pd.concat([self._pares_forcados(0), self._pares_forcados(20)])
        L = montar_linhas(lambda t: PainelPos(self.P), pm, 0, -1)
        e = inf.eventos_tau(L)
        self.assertAlmostEqual(e.loc[self.ide(0), "tau"], -8, delta=2.5)
        self.assertAlmostEqual(e.loc[self.ide(20), "tau"], -8, delta=2.5)   # abandono na escala AF − A
        r = inf.contraste(L, "abandono", B=0, margem=None)
        self.assertLess(r["beta_lp"], 0)

    def test_21_calculo_did(self):
        p = self.pares[(self.pares.metodo == "M0") & (self.pares.id_evento == self.ide(0))]
        Y = self.P.arr["Yc"]
        j = self.P.j(self.t0)
        dT = Y[0, j] - Y[0, j - 1]
        dC = np.mean([Y[v, j] - Y[v, j - 1] for v in p.u_controle])
        L = montar_linhas(lambda t: PainelPos(self.P), p, 0, -1)
        self.assertAlmostEqual(inf.eventos_tau(L).tau.iat[0], dT - dC, 10)

    # 22–24 balanceamento e suporte
    def test_22_smd(self):
        xt, xc = np.array([1.0, 2, 3]), np.array([2.0, 4, 6, 8])
        sd = np.sqrt((np.var(xt) + np.var(xc)) / 2)
        self.assertAlmostEqual(bal.smd(xt, np.ones(3), xc, np.ones(4), sd), (2 - 5) / sd, 12)

    def test_23_constantes_e_singular(self):
        df = pd.DataFrame({"a": [1.0, 1, 1, 1], "b": [1.0, 2, 3, 4], "c": [2.0, 4, 6, 8]})
        Z, usadas = rm.padronizar(df, ["a", "b", "c"])
        self.assertEqual(usadas, ["b", "c"])
        Sinv, cond = rm.inversa_regularizada(Z, 0.01)
        self.assertTrue(np.isfinite(Sinv).all())

    def test_24_sem_suporte_comum(self):
        sel, mot = rm.parear_evento(0, [1, 2], {0: np.zeros(1), 1: np.zeros(1), 2: np.zeros(1)}, np.eye(1), 5, None,
                                    logit={0: 5.0, 1: -3.0, 2: -2.0}, caliper_ps=0.2, usar_ps_distancia=True,
                                    uasg={0: "a", 1: "b", 2: "c"})
        self.assertEqual(sel, [])
        self.assertEqual(mot["fora_caliper_ps"], 2)
        ev = self.s["eventos"]
        self.assertTrue(set(self.pares.id_evento) <= set(ev[ev.suporte_comum].id_evento))

    # 25–28 placebo, RTM, composição
    def test_25_placebo_independente(self):
        P2, _ = S.mundo_base()
        j = P2.j(self.t0)
        P2.arr["Yc"][0, j - 1] += 30
        s2, _ = rodar(P2, (("M0", None),))
        pm = self.pares[self.pares.metodo == "M0"]
        pd.testing.assert_frame_equal(pm[["id_evento", "u_controle"]].reset_index(drop=True),
                                      s2["pares"][["id_evento", "u_controle"]].reset_index(drop=True))
        _, o1 = placebo(self.P, pm, B=0)
        _, o2 = placebo(P2, s2["pares"], B=0)
        self.assertNotAlmostEqual(o1[0]["beta_lp"], o2[0]["beta_lp"], 3)

    def test_26_reversao_media_simulacao(self):
        """Efeito verdadeiro ZERO; as UASGs trocam depois de um choque transitório alto em t−1 (seleção). O DiD fica
        negativo e o placebo reservado positivo: o estimador NÃO é confiável sob esse tipo de seleção, e o placebo o
        denuncia. Também com seleção por tendência (variação de nível persistente antes da troca)."""
        rng = np.random.default_rng(26)
        U, T = 160, S.T_FIM - S.T_INI + 1
        t0 = comum.tri("2025T1")
        j0 = t0 - S.T_INI
        Y = rng.normal(0, 3, U)[:, None] + rng.normal(0, 8, (U, T))
        st = np.full((U, T), A)
        trat = np.argsort(-Y[:, j0 - 1])[:24]
        st[trat, j0:] = AF
        P = S.painel(st, Y, cnpj=[f"K{i:03d}" for i in range(U)], seed=26)
        s, _ = rodar(P, (("M0", None),))
        pm = s["pares"][s["pares"].balanceado]
        _, pl = placebo(P, pm, B=0)
        L = montar_linhas(lambda t: PainelPos(P), pm, 0, -1)
        r = inf.contraste(L, None, B=0, margem=None)
        self.assertGreater(pl[0]["beta_lp"], 0)
        self.assertLess(pl[0]["p_t"], 0.05)
        self.assertLess(r["beta_lp"], 0)
        self.assertLess(r["p_t"], 0.05)
        # seleção por tendência: tratadas com trajetória crescente antes de t0; efeito verdadeiro zero
        Y2 = rng.normal(0, 1, (U, T))
        trat2 = np.arange(24)
        Y2[trat2] += 4.0 * np.arange(T)[None, :]
        st2 = np.full((U, T), A)
        st2[trat2, j0:] = AF
        P2 = S.painel(st2, Y2, cnpj=[f"K{i:03d}" for i in range(U)], seed=27)
        s2, _ = rodar(P2, (("M0", None),))
        _, pl2 = placebo(P2, s2["pares"][s2["pares"].balanceado], B=0)
        self.assertGreater(pl2[0]["beta_lp"], 2)

    def test_27_cesta_muda_no_pos(self):
        P2, _ = S.mundo_base()
        it = P2.longo["itens_y"]
        j = self.t0
        it.loc[(it.u == 0) & (it.t >= j), "produto"] = "NOVO"
        pm = self.pares[(self.pares.metodo == "M0") & (self.pares.id_evento == self.ide(0))]
        d, n = tc.delta_c3(it.groupby(["u", "t", "produto"]).y_A1.mean(), 0, self.t0, 0)
        self.assertTrue(np.isnan(d) and n == 0)
        L, perdas = tc.montar_linhas_comp(P2, pm, 0, "C3")
        self.assertEqual(perdas["tratada_sem_suporte"], 1)
        self.assertEqual(len(montar_linhas(lambda t: PainelPos(P2), pm, 0, -1)) > 0, True)   # C1 continua estimável

    def test_28_sem_imputacao(self):
        P2, _ = S.mundo_base()
        j = P2.j(self.t0)
        pm = self.pares[(self.pares.metodo == "M0") & (self.pares.id_evento == self.ide(0))]
        v = int(pm.u_controle.iat[0])
        P2.arr["Yc"][v, j] = np.nan
        L = montar_linhas(lambda t: PainelPos(P2), pm, 0, -1)
        self.assertNotIn(v, set(L[L.papel == "C"].u))
        P2.arr["Yc"][0, j] = np.nan
        self.assertEqual(len(montar_linhas(lambda t: PainelPos(P2), pm, 0, -1)), 0)

    # 31–35 janelas e inferência
    def test_31_janelas_incompletas(self):
        ev = self.ev
        cedo = ev[ev.t0 < comum.tri("2023T2") + 6]
        self.assertFalse(cedo.janela_principal_calendario.any() if len(cedo) else False)
        t_tarde = comum.tri("2026T2")
        self.assertFalse(((ev.t0 > comum.tri("2026T1")) & ev.janela_principal_calendario).any())
        pre = self.P.ate(self.t0)
        with self.assertRaises(comum.ErroDesenho):
            pre.col("Yc", self.t0)
        self.assertEqual(t_tarde, comum.tri("2026T2"))

    def _linhas_manual(self):
        return pd.DataFrame([
            {"id_evento": "e1", "papel": "T", "u": 1, "uasg": "u1", "cnpj": "G1", "z": 5.0, "w": 1, "a": 1, "grupo": "adocao", "celula": "c"},
            {"id_evento": "e1", "papel": "C", "u": 9, "uasg": "u9", "cnpj": "G9", "z": 1.0, "w": 1, "a": np.nan, "grupo": "adocao", "celula": "c"},
            {"id_evento": "e2", "papel": "T", "u": 2, "uasg": "u2", "cnpj": "G1", "z": 3.0, "w": 1, "a": 1, "grupo": "adocao", "celula": "c"},
            {"id_evento": "e2", "papel": "C", "u": 9, "uasg": "u9", "cnpj": "G9", "z": 1.0, "w": 1, "a": np.nan, "grupo": "adocao", "celula": "c"},
            {"id_evento": "e3", "papel": "T", "u": 3, "uasg": "u3", "cnpj": "G3", "z": -1.0, "w": 1, "a": 1, "grupo": "adocao", "celula": "c"},
            {"id_evento": "e3", "papel": "C", "u": 8, "uasg": "u8", "cnpj": "G8", "z": 0.0, "w": 1, "a": np.nan, "grupo": "adocao", "celula": "c"}])

    def _V_manual(self, L, tau):
        mu = L[L.papel == "C"].z.mean()
        E = L.id_evento.nunique()
        c = np.where(L.papel == "T", 1 / E, -1 / E)
        e = L.z - mu - tau * (L.papel == "T")
        S = pd.Series(c * e).groupby(L.cnpj.to_numpy()).sum()
        G = len(S)
        return G / (G - 1) * np.sum(S ** 2)

    def test_32_agrupamento_eventos_repetidos(self):
        L = self._linhas_manual()
        r = inf.contraste(L, None, B=0, margem=None)
        self.assertAlmostEqual(r["beta_lp"], (4 + 2 - 1) / 3, 12)
        self.assertAlmostEqual(r["ep"] ** 2, self._V_manual(L, r["beta_lp"]), 10)
        self.assertEqual(r["clusters"], 4)                      # G1 (2 eventos), G9, G3, G8
        # dois eventos do mesmo CNPJ G1 entram no MESMO escore

    def test_33_reuso_controle_na_inferencia(self):
        L = self._linhas_manual()
        l, tau = inf.coeficientes(L, inf.eventos_tau(L))
        self.assertAlmostEqual(l[(l.cnpj == "G9")].c.sum(), -2 / 3, 12)   # controle u9 em e1 e e2: um só cluster

    def test_34_exclusao_completa_orgao(self):
        L = self._linhas_manual()
        L2 = inf.remover_cluster(L, "cnpj", "G9")
        self.assertEqual(set(L2.id_evento), {"e3"})
        self.assertFalse((L2.cnpj == "G9").any())

    def test_35_mesma_semente(self):
        L = montar_linhas(lambda t: PainelPos(self.P), self.pares[self.pares.metodo == "M0"], 0, -1)
        a = inf.contraste(L, None, B=999, semente=5)
        b = inf.contraste(L, None, B=999, semente=5)
        self.assertEqual(a["p_wcr_webb"], b["p_wcr_webb"])

    # 36–38 congelamento
    def test_36_congelamento_dos_pares(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            pr = self.pares.drop(columns=[c for c in self.pares.columns if self.pares[c].dtype == object and c not in
                                          ("id_evento", "direcao", "uasg_tratada", "uasg_controle")]).reset_index(drop=True)
            comum.escrever_parquet(d / "p.parquet", pr)
            comum.escrever_json(d / "prot.json", {"pares_sha256_conteudo": comum.hash_df(pr), "config_sha256": comum.sha(AQUI / "config.json")})
            abrir_pos(self.P, d / "prot.json", d / "p.parquet")
            pr.loc[0, "peso"] = 0.123
            comum.escrever_parquet(d / "p.parquet", pr)
            with self.assertRaises(comum.ErroDesenho):
                abrir_pos(self.P, d / "prot.json", d / "p.parquet")

    @unittest.skipUnless(REAIS, "protocolo real ainda não congelado")
    def test_37_integridade_hashes(self):
        prot = comum.ler_json(AQUI / "resultados" / "protocolo_congelado.json")
        man = comum.ler_json(AQUI / "resultados" / "manifesto_matching.json")
        pr = pd.read_parquet(AQUI / "resultados" / "pares_congelados.parquet")
        self.assertEqual(comum.hash_df(pr), prot["pares_sha256_conteudo"])
        self.assertEqual(comum.sha(AQUI / "resultados" / "pares_congelados.parquet"), man["pares_congelados.parquet"])
        for n, h in man["tabelas_fase_I"].items():
            self.assertEqual(comum.sha(AQUI / "tabelas" / n), h, n)

    def test_38_invariancia_precos_pos(self):
        P2, _ = S.mundo_base()
        j = P2.j(self.t0)
        P2.arr["Yc"][:, j:] = -P2.arr["Yc"][:, j:] * 3 + 100
        P2.longo["itens_y"].loc[P2.longo["itens_y"].t >= self.t0, "y_A1"] = 999.0
        s2, _ = rodar(P2)
        cols = ["metodo", "id_evento", "u_controle", "peso", "dif_logit_ps"]
        pd.testing.assert_frame_equal(self.pares[cols].reset_index(drop=True), s2["pares"][cols].reset_index(drop=True))


class Reais(unittest.TestCase):
    """Integração com os arquivos reais (somente leitura)."""

    @classmethod
    def setUpClass(cls):
        cls.c = C
        cls.fontes = comum.ler_json(AQUI / "resultados" / "fontes.json") if (AQUI / "resultados" / "fontes.json").exists() else None

    def _painel(self):
        p = comum.trabalho(self.c, "painel_S1.pkl.gz")
        if not p.exists():
            self.skipTest("painel não construído")
        return comum.ler_pkl(p)

    def test_29_conformidade_cesta_S1(self):
        from scripts.verificar_fontes import conjunto_S1
        s1, s2, _ = conjunto_S1(self.c)
        P = self._painel()
        self.assertTrue(set(P.longo["itens_y"].produto) <= set(s1))
        self.assertEqual(len(s1), 3065)

    def test_30_sem_S2_na_principal(self):
        from scripts.verificar_fontes import conjunto_S1
        s1, s2, _ = conjunto_S1(self.c)
        P = self._painel()
        self.assertFalse(set(P.longo["itens_y"].produto) & set(s2))
        self.assertFalse(set(P.longo["produtos_licitados"].produto) & set(s2))

    def test_39_banco_inalterado(self):
        if not self.fontes:
            self.skipTest("fontes não verificadas")
        from em.comum import impressao_digital
        b = self.fontes["pncp_v2"]
        atual = impressao_digital(b["caminho"])
        for k in ("tamanho_bytes", "mtime_ns", "sha256_inicio_fim", "sqlite_contador_alteracoes"):
            self.assertEqual(atual[k], b[k], k)
        from em.comum import conectar_ro
        con = conectar_ro(b["caminho"])
        with self.assertRaises(Exception):
            con.execute("CREATE TABLE _teste_escrita (x)")
        con.close()

    @unittest.skipUnless(REAIS, "protocolo real ainda não congelado")
    def test_40_reproducao_integral(self):
        """Refaz a Fase I do desenho principal a partir do painel e dos eventos e compara com os pares congelados;
        refaz R1 a partir dos pares congelados e compara com tabelas/efeitos.csv."""
        P = self._painel()
        ev = comum.ler_pkl(comum.trabalho(self.c, "eventos.pkl.gz"))
        s = ds.executar(self.c, P, ev, "principal", False, ds.METODOS_PRINCIPAL)
        pr = pd.read_parquet(AQUI / "resultados" / "pares_congelados.parquet")
        a = pr[pr.desenho == "principal"].sort_values(["metodo", "id_evento", "ordem"])[["metodo", "id_evento", "u_controle", "peso"]]
        b = s["pares"].sort_values(["metodo", "id_evento", "ordem"])[["metodo", "id_evento", "u_controle", "peso"]]
        pd.testing.assert_frame_equal(a.reset_index(drop=True), b.reset_index(drop=True))
        ef = AQUI / "tabelas" / "efeitos.csv"
        if ef.exists():
            R = pd.read_csv(ef)
            r1 = R[(R.spec == "R1") & (R.grupo == "agregado")].iloc[0]
            pm = pr[(pr.desenho == "principal") & (pr.metodo == "M0") & pr.balanceado]
            L = montar_linhas(lambda t: PainelPos(P), pm, 0, -1)
            if len(L):
                self.assertAlmostEqual(inf.contraste(L, None, B=0, margem=None)["beta_lp"], r1.beta_lp, 8)


if __name__ == "__main__":
    unittest.main()
