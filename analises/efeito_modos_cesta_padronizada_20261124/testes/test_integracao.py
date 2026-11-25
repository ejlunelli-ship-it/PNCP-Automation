"""Integração: pipeline completo (sem HonestDiD/R) em mundo sintético com efeito AF conhecido (testes/sintetico.py)."""
import csv
import hashlib
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
sys.path.insert(0, str(AQUI))

import executar  # noqa: E402
import sintetico  # noqa: E402
from em import comum  # noqa: E402

ETAPAS = "validar,amostra,cobertura,referencias,descritivas,efeitos_fixos,eventos"


def ler(p):
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rodar(c, etapas=ETAPAS):
    c["saidas"].mkdir(parents=True, exist_ok=True)
    (c["saidas"] / "honestdid.R").write_text("", encoding="utf-8")
    with redirect_stdout(io.StringIO()):
        executar.principal(["--etapas", etapas, "--config", str(c["config"]), "--saidas", str(c["saidas"])])


class Pipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.c = sintetico.construir(Path(cls.tmp.name) / "w")
        cls.h_v2, cls.h_cesta = sha(cls.c["v2"]), sha(cls.c["cesta_trabalho"])
        rodar(cls.c)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_fontes_somente_leitura(self):
        self.assertEqual(sha(self.c["v2"]), self.h_v2)
        self.assertEqual(sha(self.c["cesta_trabalho"]), self.h_cesta)

    def test_identificacao_produtos_e_funil(self):
        f = {r["etapa"]: r for r in ler(self.c["saidas"] / "funil_amostra.csv")}
        self.assertEqual(int(f["0_cesta_candidata"]["produtos"]), 4)
        self.assertEqual(int(f["0_cesta_candidata"]["itens"]), 40 * 4 * 12 * 2)
        self.assertEqual(int(f["7_produto_aprovado"]["itens"]), 0, "sem aprovação a amostra principal é vazia")
        self.assertEqual(int(f["0_cesta_candidata"]["uasgs"]), 40)

    def test_chaves_e_juncoes(self):
        import pickle
        with open(Path(self.tmp.name) / "w" / "trabalho" / "amostra.pkl", "rb") as f:
            df = pickle.load(f)
        self.assertFalse(df.duplicated(["chave", "numero_item"]).any())
        self.assertEqual(df.chave.nunique(), 40 * 4 * 12)
        self.assertTrue((df.uasg.str.len() == 6).all())

    def test_eventos_identificados(self):
        ev = ler(self.c["saidas"] / "tabelas" / "eventos_unidades.csv")
        d = {}
        for r in ev:
            d[r["tipo"]] = d.get(r["tipo"], 0) + 1
        self.assertEqual(d.get("troca"), 14)          # 8 adoções + 6 abandonos
        self.assertEqual(d.get("irregular"), 2)

    def test_efeito_recuperado(self):
        es = {(r["especificacao"], r["grupo"], r["l"]): r for r in ler(self.c["saidas"] / "estudo_eventos.csv")}
        for g in ("agregado", "adocao", "abandono"):
            b = float(es[("dcdh_6m_item_celula", g, "media")]["beta_lp"])
            self.assertAlmostEqual(b, sintetico.TAU, delta=1.0, msg=g)
        fe = {r["especificacao"]: r for r in ler(self.c["saidas"] / "efeitos_fixos.csv")}
        self.assertAlmostEqual(float(fe["E3"]["beta_lp"]), sintetico.TAU, delta=1.0)
        self.assertAlmostEqual(float(fe["E3"]["pct_exato"]), float(comum.pct_exato(float(fe["E3"]["beta_lp"]))), 9)

    def test_reproducao_integral(self):
        c2 = sintetico.construir(Path(self.tmp.name) / "w2")
        rodar(c2)
        for arq in ("funil_amostra.csv", "descritivas.csv", "efeitos_fixos.csv", "estudo_eventos.csv",
                    "tabelas/referencias_resumo.csv", "tabelas/eventos_unidades.csv"):
            self.assertEqual((self.c["saidas"] / arq).read_bytes(), (c2["saidas"] / arq).read_bytes(), arq)

    def test_amostra_principal_com_aprovacao(self):
        c3 = sintetico.construir(Path(self.tmp.name) / "w3")
        cesta = Path(self.tmp.name) / "w3" / "cesta" / "saidas" / "cesta_validada.csv"
        cesta.write_text("﻿id_candidato,produto\nCP0001,100|UNIDADE\n", encoding="utf-8")
        rodar(c3, "validar,amostra")
        f = {r["etapa"]: r for r in ler(c3["saidas"] / "funil_amostra.csv")}
        self.assertGreater(int(f["7_produto_aprovado"]["itens"]), 0)
        self.assertEqual(int(f["7_produto_aprovado"]["produtos"]), 1)


if __name__ == "__main__":
    unittest.main()
