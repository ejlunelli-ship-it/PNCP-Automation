"""Testes da nova rodada (sobre os arquivos reais congelados; nada é alterado)."""
import json
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AQUI))

from rodada import base  # noqa: E402

C = base.cfg()


class Conjuntos(unittest.TestCase):
    def test_tamanhos_e_aninhamento(self):
        conj, st, _ = base.conjuntos(C)
        self.assertEqual({k: len(v) for k, v in conj.items()}, {"S1": 3065, "S1S2": 3172, "P1": 4122, "cesta": 16248})
        s1, s12, p1, ce = (set(conj[k]) for k in ("S1", "S1S2", "P1", "cesta"))
        self.assertTrue(s1 < s12 < p1 < ce)
        self.assertTrue(all(st[p] == "AUTO_VALIDADO_CATALOGO" for p in s1))
        self.assertTrue(all(st[p] == "AUTO_VALIDADO_CATALOGO_COM_RESSALVA" for p in s12 - s1))

    def test_s1_nao_mistura_itens_s4(self):
        """A amostra é definida por PRODUTO (catálogo); itens S4 não entram como critério."""
        linhas = base.ler_csv(AQUI / "tabelas" / "conjuntos_amostras.csv")
        self.assertEqual(set(linhas[0]), {"produto", "id_candidato", "status_automatico", "S1", "S1S2", "P1", "cesta"})

    def test_congelamento_confere(self):
        c = base.verificar_congelamento(C)
        self.assertTrue(c["antes_de_acessar_precos_e_modos"])

    def test_congelamento_anterior_a_amostra(self):
        import datetime as dt
        cong = json.loads((AQUI / "congelamento.json").read_text(encoding="utf-8"))
        t_cong = dt.datetime.fromisoformat(cong["congelado_em"]).timestamp()
        t_amostra = (Path(C["trabalho"]) / "S1" / "amostra.pkl").stat().st_mtime
        self.assertLess(t_cong, t_amostra)


class Amostras(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conj, _, _ = base.conjuntos(C)

    def test_amostra_so_com_produtos_do_conjunto(self):
        for n in ("S1", "S1S2", "P1"):
            d = pd.read_pickle(Path(C["trabalho"]) / n / "amostra.pkl", )[["produto"]]
            self.assertTrue(set(d.produto.astype(str)) <= set(self.conj[n]), n)

    def test_funil_monotono_e_coerente(self):
        for n in ("S1", "S1S2", "P1"):
            f = base.ler_csv(AQUI / "amostras" / n / "funil_amostra.csv")
            itens = [int(r["itens"]) for r in f]
            self.assertEqual(itens, sorted(itens, reverse=True), n)
            self.assertTrue(f[-1]["etapa"].startswith("7_produto_no_conjunto"))
            self.assertLessEqual(int(f[-1]["produtos"]), len(self.conj[n]))

    def test_regime_de_modo_identico_em_todas_as_amostras(self):
        hs = {base.sha(Path(C["trabalho"]) / n / "regime_compras.pkl") for n in ("S1", "S1S2", "P1")}
        self.assertEqual(hs, {base.sha(Path(C["dados_base"]) / "regime_compras.pkl")})


class Resultados(unittest.TestCase):
    def test_especificacoes_iguais_as_do_estudo_anterior(self):
        for n in ("S1", "S1S2", "P1"):
            p = AQUI / "amostras" / n
            if not (p / "efeitos_fixos.csv").exists():
                self.skipTest("estimação ainda não executada")
            fe = {r["especificacao"] for r in base.ler_csv(p / "efeitos_fixos.csv")}
            ant = {r["especificacao"] for r in base.ler_csv(base.resolver(C["estudo_anterior"]) / "efeitos_fixos.csv")}
            self.assertEqual(fe, ant)
            ev = {r["especificacao"] for r in base.ler_csv(p / "estudo_eventos.csv")}
            ev_ant = {r["especificacao"] for r in base.ler_csv(base.resolver(C["estudo_anterior"]) / "estudo_eventos.csv")}
            self.assertEqual(ev, ev_ant)

    def test_holm_da_familia_principal(self):
        base.estudo_anterior(C)
        from em.inferencia import holm
        np.testing.assert_allclose(holm([0.049, 0.172, 0.108]), [0.147, 0.216, 0.216])

    def test_decomposicao_reproduz_estimativa_propria(self):
        """dCDH com os switchers restritos a TODOS os switchers da própria amostra = estimativa própria."""
        p = AQUI / "amostras" / "S1" / "tabelas" / "populacao_eventos_pesos.csv"
        if not p.exists():
            self.skipTest("estimação ainda não executada")
        from rodada.analises import dcdh_restrito, switchers_com_peso
        a, _ = dcdh_restrito(C, "S1", None, 3, 1, 2, lambda m: None)
        b, _ = dcdh_restrito(C, "S1", switchers_com_peso(C, "S1"), 3, 1, 2, lambda m: None)
        ga = next(r for r in a if r["grupo"] == "agregado" and r["l"] == "media")["beta_lp"]
        gb = next(r for r in b if r["grupo"] == "agregado" and r["l"] == "media")["beta_lp"]
        self.assertAlmostEqual(ga, gb, 9)
        ev = next(r for r in base.ler_csv(AQUI / "amostras" / "S1" / "estudo_eventos.csv")
                  if r["especificacao"] == "dcdh_6m_item_celula" and r["grupo"] == "agregado" and r["l"] == "media")
        self.assertAlmostEqual(ga, float(ev["beta_lp"]), 6)

    def test_estudo_anterior_intacto(self):
        cong = json.loads((AQUI / "congelamento.json").read_text(encoding="utf-8"))
        ant = base.resolver(C["estudo_anterior"])
        for n, h in cong["estudo_anterior"]["saidas"].items():
            self.assertEqual(base.sha(ant / n), h, n)
        for n, h in cong["estudo_anterior"]["codigo"].items():
            self.assertEqual(base.sha(ant / "em" / n), h, n)


if __name__ == "__main__":
    unittest.main()
