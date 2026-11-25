"""Testes unitários: normalização, unidades, atributos, HHI, classificação e validação da revisão."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cesta import atributos as at  # noqa: E402
from cesta import classificacao, metricas  # noqa: E402
from cesta.normalizacao import (aliases_padrao, chave_textual, normalizar_catmat, normalizar_data,  # noqa: E402
                                normalizar_texto, normalizar_uasg, normalizar_unidade, trimestre)
import validar_revisao  # noqa: E402


class Normalizacao(unittest.TestCase):
    def test_texto(self):
        self.assertEqual(normalizar_texto("  Água   mineral,  TIPO: sem gás ; "), "AGUA MINERAL, TIPO SEM GAS")
        self.assertEqual(normalizar_texto("75 g/m²"), "75 G/M2")
        self.assertEqual(normalizar_texto("ponta 1,0 mm"), "PONTA 1,0 MM", "vírgula decimal não pode ganhar espaço")
        self.assertIsNone(normalizar_texto(None))

    def test_chave_textual_agrupa_so_formatacao(self):
        a = chave_textual("CANETA, MATERIAL: METAL , PONTA 1,0 MM")
        b = chave_textual("Caneta, material metal, ponta 1,0mm")
        c = chave_textual("CANETA, MATERIAL METAL, PONTA 10 MM")
        self.assertEqual(a, b)
        self.assertNotEqual(a, c, "1,0 MM e 10 MM não podem colapsar")

    def test_codigos(self):
        for v in ("445485", "445485.0", 445485, 445485.0, " 445485 "):
            self.assertEqual(normalizar_catmat(v), 445485)
        for v in (None, "", "abc", 0, "0", -1, 1.5, True):
            self.assertIsNone(normalizar_catmat(v))
        self.assertEqual(normalizar_uasg("70006"), "070006")
        self.assertEqual(normalizar_uasg("070006"), "070006")
        for v in (None, "", "0", "1234567", "ab12"):
            self.assertIsNone(normalizar_uasg(v))

    def test_datas(self):
        self.assertEqual(normalizar_data("2024-05-03T10:00:00"), "2024-05-03")
        self.assertEqual(normalizar_data("2024-05-03 00:00:00.0000000"), "2024-05-03")
        for v in ("2024-13-01", "2023-02-29", "2024-04-31", "lixo", None, "1900-01-01"):
            self.assertIsNone(normalizar_data(v))
        self.assertEqual(normalizar_data("2024-02-29"), "2024-02-29")
        self.assertEqual(trimestre("2026-10-31"), "2026T4")


class Unidades(unittest.TestCase):
    al = aliases_padrao()

    def n(self, u):
        return normalizar_unidade(u, self.al)["unidade_norm"]

    def test_aliases_de_grafia(self):
        self.assertEqual(self.n("UN"), "UNIDADE")
        self.assertEqual(self.n("Unidade "), "UNIDADE")
        self.assertEqual(self.n("UNID."), "UNIDADE")
        self.assertEqual(self.n("Caixa 100,00 UN"), self.n("CAIXA 100 UNIDADE"))

    def test_nao_funde_embalagens(self):
        formas = {self.n(u) for u in ("Unidade", "Caixa 100,00 UN", "Caixa 500,00 UN", "Pacote 100,00 UN", "Resma",
                                      "Litro", "Quilograma", "Caixa")}
        self.assertEqual(len(formas), 8, formas)

    def test_sem_conversao_fisica(self):
        self.assertNotEqual(self.n("Frasco 1000,00 ML"), self.n("Frasco 1,00 L"))
        self.assertNotEqual(self.n("Litro"), self.n("Mililitro"))

    def test_conteudo_zero_nao_fundido(self):
        r = normalizar_unidade("UNIDADE 0,00 ", self.al)
        self.assertEqual(r["unidade_norm"], "UNIDADE 0")
        self.assertEqual(r["alerta"], "conteudo_zero")
        self.assertNotEqual(r["unidade_norm"], self.n("Unidade"))

    def test_ausente(self):
        self.assertEqual(normalizar_unidade(None, self.al)["alerta"], "unidade_ausente")
        self.assertEqual(normalizar_unidade("  ", self.al)["alerta"], "unidade_ausente")


class Atributos(unittest.TestCase):
    def ex(self, t):
        return at.extrair(normalizar_texto(t))

    def test_exemplos_do_protocolo(self):
        a = self.ex("PAPEL A4, 75 G/M², 500 FOLHAS")
        self.assertEqual(a["formato_papel"], ("A4",))
        self.assertEqual(a["gramatura"], ("75 G/M2",))
        self.assertEqual(a["folhas"], ("500 FOLHAS",))
        self.assertEqual(self.ex("ÁLCOOL ETÍLICO 70%, FRASCO 1 L")["concentracao_pct"], ("70%",))
        self.assertEqual(self.ex("ÁLCOOL ETÍLICO 70%, FRASCO 1 L")["volume"], ("1 L",))
        self.assertEqual(self.ex("DETERGENTE 500 ML")["volume"], ("500 ML",))
        self.assertEqual(self.ex("LAPISEIRA 0,7 MM")["medida_linear"], ("0.7 MM",))
        self.assertEqual(self.ex("CLIPE, CAIXA COM 12")["unidades_por_embalagem"], ("CAIXA 12",))
        self.assertEqual(self.ex("ENVELOPE, PACOTE COM 100 UNIDADES")["unidades_por_embalagem"], ("PACOTE 100",))
        self.assertEqual(self.ex("DIPIRONA 500 MG")["dosagem"], ("500 MG",))
        self.assertEqual(self.ex("AMOXICILINA 250 MG/5 ML")["concentracao_razao"], ("250 MG/5 ML",))

    def test_assinatura_distingue_especificacoes(self):
        s75 = at.assinatura(self.ex("PAPEL A4, 75 G/M2, 500 FOLHAS"))
        s90 = at.assinatura(self.ex("PAPEL A4, 90 G/M2, 500 FOLHAS"))
        self.assertNotEqual(s75, s90)
        self.assertEqual(s75, at.assinatura(self.ex("Papel A4 , 75 g/m², 500 folhas")))

    def test_embalagem_divergente(self):
        a = self.ex("LUVA, CAIXA COM 100")
        self.assertFalse(at.embalagem_divergente(a, "CAIXA 100 UNIDADE", "100"))
        self.assertTrue(at.embalagem_divergente(a, "CAIXA 500 UNIDADE", "500"))
        self.assertTrue(at.embalagem_divergente(a, "UNIDADE", None))


class Concentracao(unittest.TestCase):
    def test_hhi(self):
        self.assertAlmostEqual(metricas.hhi([1, 1, 1, 1]), 0.25)
        self.assertAlmostEqual(metricas.hhi([10]), 1.0)
        self.assertAlmostEqual(metricas.hhi([3, 1]), 0.625)
        self.assertIsNone(metricas.hhi([]))

    def test_limiares(self):
        lim = {"compras_min": 40, "uasgs_min": 15, "trimestres_min": 6, "anos_min": 2,
               "share_uasg_dominante_max": 0.25, "hhi_max": 0.12}
        m = {"compras": 40, "uasgs": 15, "trimestres": 6, "anos": 2, "share_uasg_dominante": 0.25, "hhi": 0.12}
        self.assertTrue(metricas.aplica_limiares(m, lim)[0], "limiares são inclusivos")
        ok, falhas = metricas.aplica_limiares({**m, "compras": 39, "hhi": 0.2}, lim)
        self.assertFalse(ok)
        self.assertEqual(len(falhas), 2)


class Classificacao(unittest.TestCase):
    cautela = classificacao.carregar_cautela(Path(__file__).resolve().parents[1] / "config" / "cautela.json")
    par_h = {"share_descricao_dominante_min_A": 0.90, "max_assinaturas_atributos_A": 1,
             "min_atributos_especificos_A": 2, "share_descricao_dominante_min_B": 0.50}

    def fam(self, descs, unidade="UNIDADE", conteudo=None, classe=7510, pdm="CANETA ESFEROGRAFICA", completa=1.0):
        vs = [{"descricao_original": d, "descricao_norm": normalizar_texto(d) or "", "chave_textual": chave_textual(d),
               "itens": n, "compras": n, "nome_pdm": pdm} for d, n in descs]
        vs = classificacao.variantes_da_familia(vs)
        return classificacao.classificar_familia("f", vs, {"classe": classe, "share_desc_completa": completa},
                                                 {"unidade_norm": unidade, "conteudo": conteudo, "alerta": ""},
                                                 self.par_h, self.cautela)

    def test_A_formatacao_apenas(self):
        c = self.fam([("CANETA ESFEROGRAFICA, MATERIAL PLASTICO, COR AZUL, PONTA 1,0 MM", 80),
                      ("CANETA ESFEROGRÁFICA, MATERIAL: PLÁSTICO , COR: AZUL , PONTA: 1,0 MM", 20)])
        self.assertEqual(c["classe"], "A", c)

    def test_incompativeis_nao_sao_A(self):
        c = self.fam([("PAPEL A4, MATERIAL CELULOSE, 75 G/M2, 500 FOLHAS", 50),
                      ("PAPEL A4, MATERIAL CELULOSE, 90 G/M2, 500 FOLHAS", 50)], pdm="PAPEL A4", classe=7530)
        self.assertNotEqual(c["classe"], "A")
        self.assertIsNotNone(c["subtipos"], "atributos inequívocos permitem subtipos")
        self.assertEqual(len(set(c["subtipos"].values())), 2)

    def test_generica_C(self):
        c = self.fam([("PEÇA MECÂNICA / ELÉTRICA - VEÍCULO AUTOMOTIVO", 100)],
                     pdm="PEÇA MECÂNICA / ELÉTRICA - VEÍCULO AUTOMOTIVO", classe=2590)
        self.assertEqual(c["classe"], "C")

    def test_embalagem_distinta_impede_A(self):
        c = self.fam([("LUVA PARA PROCEDIMENTO, MATERIAL LATEX, TAMANHO M, CAIXA COM 100", 100)],
                     unidade="CAIXA 500 UNIDADE", conteudo="500", classe=6515, pdm="LUVA PARA PROCEDIMENTO")
        self.assertNotEqual(c["classe"], "A")

    def test_cautela_nao_exclui(self):
        c = self.fam([("DIPIRONA SODICA, CONCENTRACAO 500 MG, FORMA FARMACEUTICA COMPRIMIDO", 100)],
                     unidade="COMPRIMIDO", classe=6505, pdm="DIPIRONA SODICA")
        self.assertIn("medicamentos_materiais_medicos", c["cautela"])
        self.assertIn(c["classe"], ("A", "B"))
        self.assertTrue(any("revisão especializada" in p for p in c["pendencias"]))


class Revisao(unittest.TestCase):
    def test_sem_aprovacao_cesta_vazia(self):
        apr, rec = validar_revisao.validar([{"id_candidato": "CP0001", validar_revisao.DECISAO: ""}])
        self.assertEqual(apr, [])

    def test_aprovacao_incompleta_recusada(self):
        apr, rec = validar_revisao.validar([{"id_candidato": "CP0001", validar_revisao.DECISAO: "aprovar",
                                             "revisor": "Fulano"}])
        self.assertEqual(apr, [])
        self.assertIn("campos ausentes", rec[0]["motivo"])

    def test_aprovacao_completa(self):
        r = {"id_candidato": "CP0001", validar_revisao.DECISAO: "aprovar", "data_revisao": "2026-12-01",
             **{c: "x" for c in validar_revisao.OBRIGATORIOS if c != "data_revisao"}}
        apr, rec = validar_revisao.validar([r])
        self.assertEqual(len(apr), 1)
        self.assertEqual(rec, [])


if __name__ == "__main__":
    unittest.main()
