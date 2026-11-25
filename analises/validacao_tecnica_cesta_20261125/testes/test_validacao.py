"""Testes da validação técnica (mundo sintético; nenhum dado real é alterado).

Numeração 1–25 = lista obrigatória do pedido; os demais (R*) são regressões das correções de regra e
verificações extras de integridade.
"""
import datetime as dt
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mundo_sintetico as ms  # noqa: E402

import comum  # noqa: E402
from auditar_homogeneidade import CHAVE_INVALIDA, CONFLITO  # noqa: E402
from comum import ErroEstrutural  # noqa: E402
from extrair_atributos import Extrator  # noqa: E402
from inspecionar_entradas import inspecionar  # noqa: E402
from normalizar_especificacoes import normalizar  # noqa: E402
from preparar_revisao import preparar  # noqa: E402
from validar_revisao import concluir  # noqa: E402

HOJE = dt.date.today().isoformat()
FONTE = "CATMAT:{catmat} | DOCUMENTO_COMPRA:00394452000103-1-000123/2024"
FUND = "Conferido no termo de referência da compra citada e no catálogo CATMAT: mesmas características técnicas."


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.tmp = Path(self._tmp.name)
        self.cfg = ms.criar(self.tmp)
        self.reg = comum.Registro(verboso=False)
        self.pasta = self.tmp / "saidas" / "P1"
        self.man = preparar(self.cfg, self.reg, "P1", saida=self.pasta)

    def tearDown(self):
        self._tmp.cleanup()

    # ------------------------------------------------------------------ utilidades
    def prods(self):
        return ms.ler(self.pasta / "revisao_produtos.csv")

    def vars(self):
        return ms.ler(self.pasta / "revisao_variantes.csv")

    def base(self, idr):
        return next(p for p in ms.ler(self.pasta / "base_produtos.csv") if p["id_registro"] == idr)

    def preencher(self, idr, decisao="APROVAR", rev_prod="R1", rev_var="R2", var_decisao="EQUIVALENTE", fonte=None,
                  data=HOJE, omitir_variante=False, especificacao=None, variantes_de=None):
        P, V = self.prods(), self.vars()
        b = self.base(idr)
        for p in P:
            if p["id_registro"] == idr:
                p.update({"decisao_produto": decisao, "fundamentacao": FUND, "revisor": rev_prod, "data_revisao": data,
                          "fonte_evidencia": FONTE.format(catmat=b["catmat"]) if fonte is None else fonte,
                          "resolucao_alertas": "Alertas examinados no termo de referência: não alteram a especificação técnica.",
                          "especificacao_canonica": especificacao if especificacao is not None else
                          f"{b['descricao_representativa'].split(',')[0]} | DESCRICAO: {b['descricao_representativa']}"})
        alvo = variantes_de or idr
        primeira = True
        for v in V:
            if v["id_candidato"] == alvo or v["id_especificacao_atomica"] == alvo:
                if omitir_variante and primeira:
                    primeira = False
                    continue
                v.update({"decisao_variante": var_decisao, "fundamentacao": FUND, "revisor": rev_var, "data_revisao": HOJE,
                          "fonte_evidencia": FONTE.format(catmat=b["catmat"])})
        ms.gravar(self.pasta / "revisao_produtos.csv", P)
        ms.gravar(self.pasta / "revisao_variantes.csv", V)

    def concluir(self, dupla=False):
        return concluir(self.cfg, self.reg, self.pasta, exigir_dupla=dupla)

    def status(self, idr):
        return next(r for r in ms.ler(self.pasta / "resultado_revisao.csv") if r["id_registro"] == idr)


class Obrigatorios(Base):
    def test_01_embalagens_100_e_500_bloqueio(self):
        b = self.base("CP0002")
        self.assertEqual(b["status_auditoria"], CONFLITO)
        self.assertIn("quantidade_embalagem", b["conflitos"])
        self.preencher("CP0002")
        self.concluir()
        r = self.status("CP0002")
        self.assertEqual(r["status_final"], "BLOQUEADO")
        self.assertIn("conflito objetivo", r["motivos_bloqueio"])

    def test_02_descricoes_equivalentes_e_documentacao_completa_aprovacao_possivel(self):
        self.preencher("CP0001")
        out = self.concluir(dupla=True)
        self.assertEqual(self.status("CP0001")["status_final"], "VALIDADO", self.status("CP0001")["motivos_bloqueio"])
        self.assertEqual(out["produtos_aprovados"], 1)
        cesta = ms.ler(self.pasta / "cesta_validada.csv")
        self.assertEqual([c["produto"] for c in cesta], ["100001|PAR"])
        self.assertEqual(cesta[0]["status_validacao"], "VALIDADO")
        self.assertEqual(cesta[0]["versao_auditoria"], self.man["versao_auditoria"])
        self.assertTrue((self.pasta / "integracao_econometria" / "saidas" / "cesta_validada.csv").is_file())

    def test_03_variante_sem_revisao_bloqueio(self):
        self.preencher("CP0007", omitir_variante=True)
        self.concluir()
        r = self.status("CP0007")
        self.assertEqual(r["status_final"], "BLOQUEADO")
        self.assertIn("sem revisão", r["motivos_bloqueio"])

    def test_04_variante_divergente_bloqueio(self):
        self.preencher("CP0007", var_decisao="DIVERGENTE")
        self.concluir()
        self.assertIn("DIVERGENTE", self.status("CP0007")["motivos_bloqueio"])
        self.assertEqual(self.status("CP0007")["status_final"], "BLOQUEADO")

    def test_05_variante_indeterminada_bloqueio(self):
        self.preencher("CP0007", var_decisao="INDETERMINADA")
        self.concluir()
        self.assertEqual(self.status("CP0007")["status_final"], "BLOQUEADO")

    def test_06_conflito_de_concentracao_bloqueio(self):
        b = self.base("CP0003")
        self.assertEqual(b["status_auditoria"], CONFLITO)
        self.assertIn("concentracao_pct: 70% ", b["conflitos"])
        self.preencher("CP0003")
        self.concluir()
        self.assertEqual(self.status("CP0003")["status_final"], "BLOQUEADO")

    def test_07_conflito_de_gramatura_bloqueio(self):
        b = self.base("CP0004")
        self.assertEqual(b["status_auditoria"], CONFLITO)
        self.assertIn("gramatura: 75 G/M2", b["conflitos"])
        self.preencher("CP0004")
        self.concluir()
        self.assertEqual(self.status("CP0004")["status_final"], "BLOQUEADO")

    def test_08_conversao_inequivoca_litros_mililitros(self):
        e = Extrator(self.cfg["regras"])
        self.assertEqual(set(e.extrair(normalizar("ÁGUA 0,5 L"))["volume"]), {"500 ML"})
        self.assertEqual(set(e.extrair(normalizar("ÁGUA 500ML"))["volume"]), {"500 ML"})
        self.assertNotEqual(set(e.extrair(normalizar("ÁGUA 1 LITRO"))["volume"]), {"500 ML"})
        b = self.base("CP0007")
        self.assertNotEqual(b["status_auditoria"], CONFLITO)
        self.assertNotIn("volume", b["conflitos"])
        self.assertEqual(json.loads(b["atributos_consenso"])["volume"], "500 ML")

    def test_09_decimal_com_virgula(self):
        self.assertEqual(normalizar("Frasco 1,5 L"), "FRASCO 1.5 L")
        e = Extrator(self.cfg["regras"])
        self.assertEqual(set(e.extrair(normalizar("FRASCO 1,5 LITROS"))["volume"]), {"1500 ML"})
        self.assertEqual(set(e.extrair(normalizar("TEOR 2,5%"))["concentracao_pct"]), {"2.5%"})
        self.assertEqual(set(e.extrair(normalizar("RESMA 1.000 FOLHAS"))["numero_folhas"]), {"1000 FOLHAS"})

    def test_10_catmat_e_unidade_ausentes_bloqueio(self):
        self.assertEqual(self.base("CP0006")["status_auditoria"], CHAVE_INVALIDA)
        self.preencher("CP0006")
        self.concluir()
        r = self.status("CP0006")
        self.assertEqual(r["status_final"], "BLOQUEADO")
        self.assertIn("CATMAT ou unidade ausente", r["motivos_bloqueio"])

    def test_11_descricao_rara_incompativel_preservada_e_alertada(self):
        vs = [v for v in ms.ler(self.pasta / "base_variantes.csv") if v["id_candidato"] == "CP0005"]
        rara = [v for v in vs if "VERMELHA" in v["descricao_normalizada"]]
        self.assertEqual(len(rara), 1)
        self.assertEqual(rara[0]["itens"], "1")
        self.assertIn("descrição rara", rara[0]["alertas"])
        self.assertIn("conflito objetivo", rara[0]["alertas"])
        self.assertEqual(self.base("CP0005")["status_auditoria"], CONFLITO)

    def test_12_id_duplicado_erro(self):
        P = self.prods()
        ms.gravar(self.pasta / "revisao_produtos.csv", P + [P[0]])
        with self.assertRaisesRegex(ErroEstrutural, "duplicados"):
            self.concluir()

    def test_13_alteracao_de_campo_imutavel_erro(self):
        P = self.prods()
        P[0]["status_auditoria"] = "SEM_DIVERGENCIA_DETECTADA" if P[0]["status_auditoria"] != "SEM_DIVERGENCIA_DETECTADA" else "X"
        ms.gravar(self.pasta / "revisao_produtos.csv", P)
        with self.assertRaisesRegex(ErroEstrutural, "não editáveis"):
            self.concluir()

    def test_14_alteracao_de_arquivo_base_apos_preparacao_erro(self):
        V = ms.ler(self.pasta / "base_variantes.csv")
        V[0]["descricao_normalizada"] += " X"
        ms.gravar(self.pasta / "base_variantes.csv", V)
        with self.assertRaisesRegex(ErroEstrutural, "arquivo-base alterado"):
            self.concluir()

    def test_15_decisao_sem_fonte_documental_bloqueio(self):
        self.preencher("CP0001", fonte="")
        self.concluir()
        r = self.status("CP0001")
        self.assertEqual(r["status_final"], "BLOQUEADO")
        self.assertIn("fonte documental ausente", r["motivos_bloqueio"])
        self.preencher("CP0001", fonte="SITE:qualquer coisa")
        self.concluir()
        self.assertEqual(self.status("CP0001")["status_final"], "BLOQUEADO")

    def test_16_decisao_sem_revisor_bloqueio(self):
        self.preencher("CP0001", rev_prod="")
        self.concluir()
        self.assertIn("revisor não identificado", self.status("CP0001")["motivos_bloqueio"])
        self.preencher("CP0001", rev_prod="R9")                      # fora do cadastro
        self.concluir()
        self.assertIn("não consta do cadastro", self.status("CP0001")["motivos_bloqueio"])

    def test_17_data_invalida_bloqueio(self):
        for d in ("2026-13-40", "25/11/2026", (dt.date.today() + dt.timedelta(days=3)).isoformat(), "2020-01-01"):
            self.preencher("CP0001", data=d)
            self.concluir()
            self.assertEqual(self.status("CP0001")["status_final"], "BLOQUEADO", d)

    def test_18_revisor_final_igual_ao_de_variantes_com_dupla_revisao_bloqueio(self):
        self.preencher("CP0001", rev_prod="R2", rev_var="R2")
        self.concluir(dupla=True)
        self.assertIn("dupla revisão", self.status("CP0001")["motivos_bloqueio"])
        self.concluir(dupla=False)
        self.assertEqual(self.status("CP0001")["status_final"], "VALIDADO")
        self.assertEqual(self.status("CP0001")["revisao_dupla"], "0")

    def test_19_invariancia_a_precos_e_modos(self):
        arqs = ["base_produtos.csv", "base_variantes.csv", "descricoes_originais.csv", "auditoria_atributos.csv",
                "auditoria_conflitos.csv", "revisao_produtos.csv", "revisao_variantes.csv"]
        h0 = {a: sha(self.pasta / a) for a in arqs}
        shutil.rmtree(self.tmp / "entradas")
        cfg2 = ms.criar(self.tmp, preco_fator=7.3, modo="Aberto-Fechado")      # só preço, valor e modo mudam
        self.assertNotEqual(self.man["entradas"]["cesta_candidata"]["sha256"],
                            comum.sha256_arquivo(self.tmp / "entradas" / "cesta_candidata.csv"))
        p2 = self.tmp / "saidas" / "P1_precos_alterados"
        m2 = preparar(cfg2, self.reg, "P1", saida=p2)
        self.assertEqual(h0, {a: sha(p2 / a) for a in arqs})
        self.assertEqual(m2["versao_auditoria"], self.man["versao_auditoria"])

    def test_20_duas_execucoes_identicas(self):
        p2 = self.tmp / "saidas" / "P1_repeticao"
        m2 = preparar(self.cfg, self.reg, "P1", saida=p2)
        self.assertEqual(self.man["hashes_base"], m2["hashes_base"])
        self.assertEqual(self.man["hashes_formularios_iniciais"], m2["hashes_formularios_iniciais"])
        self.assertEqual([p["id_registro"] for p in self.prods()], [p["id_registro"] for p in ms.ler(p2 / "revisao_produtos.csv")])

    def test_21_nenhuma_modificacao_ao_banco_de_origem(self):
        e = self.tmp / "entradas"
        antes = {n: sha(e / n) for n in ("cesta.db", "pncp.db", "cesta_candidata.csv", "descricoes_variantes.csv", "formulario_revisao.csv")}
        preparar(self.cfg, self.reg, "P1", saida=self.tmp / "saidas" / "outra")
        self.preencher("CP0001")
        self.concluir()
        self.assertEqual(antes, {n: sha(e / n) for n in antes})
        self.assertTrue(self.man["bancos"]["inalterados"])

    def test_22_nenhum_produto_aprovado_automaticamente(self):
        self.assertTrue(all(p["decisao_produto"] == "PENDENTE" for p in self.prods()))
        self.assertTrue(all(v["decisao_variante"] == "" for v in self.vars()))
        out = self.concluir(dupla=True)
        self.assertEqual(out["produtos_aprovados"], 0)
        self.assertEqual(out["subprodutos_aprovados"], 0)
        self.assertFalse((self.pasta / "cesta_validada.csv").exists())
        self.assertIn("NÃO foi criada", out["aviso"])
        self.assertEqual(self.man["contagens"]["aprovados_automaticamente"], 0)
        self.assertEqual(self.base("CP0001")["classe_tecnica"], "A")                 # classe A não aprova sozinha

    def test_23_familia_desmembrada_nao_aprovada_antes_dos_subprodutos(self):
        b = self.base("CP0002")
        self.assertEqual(b["desmembravel"], "1")
        subs = b["subprodutos"].split(";")
        self.assertEqual(len(subs), 2)
        self.preencher("CP0002", decisao="DESMEMBRAR")
        self.concluir()
        self.assertEqual(self.status("CP0002")["status_final"], "DESMEMBRADO")
        self.assertTrue(all(self.status(s)["status_final"] == "PENDENTE" for s in subs))
        self.assertFalse((self.pasta / "cesta_validada.csv").exists())
        self.preencher(subs[0], variantes_de=subs[0])
        self.concluir(dupla=True)
        self.assertEqual(self.status(subs[0])["status_final"], "VALIDADO", self.status(subs[0])["motivos_bloqueio"])
        self.assertEqual(self.status(subs[1])["status_final"], "PENDENTE")
        cesta = ms.ler(self.pasta / "cesta_validada.csv")
        self.assertEqual([(c["tipo_registro"], c["id_especificacao_atomica"]) for c in cesta], [("SUBPRODUTO", subs[0])])
        self.assertTrue((self.pasta / "integracao_econometria" / "ligacao_itens_especificacoes.csv").is_file())

    def test_24_preservacao_integral_das_descricoes_originais(self):
        ent = {(r["familia"], r["descricao_original"]) for r in ms.ler(self.tmp / "entradas" / "descricoes_variantes.csv")
               if r["familia"] != "100008|UNIDADE"}
        sai = {(r["familia"], r["descricao_original"]) for r in ms.ler(self.pasta / "descricoes_originais.csv")}
        self.assertEqual(ent, sai)
        for r in ms.ler(self.pasta / "descricoes_originais.csv"):
            self.assertEqual(r["sha256_descricao"], comum.sha256_texto(r["descricao_original"]))
        self.assertTrue(any(r["descricao_original"].endswith(" ") for r in ms.ler(self.pasta / "descricoes_originais.csv")))

    def test_25_nao_duplicacao_de_frequencias(self):
        V = ms.ler(self.pasta / "base_variantes.csv")
        for p in ms.ler(self.pasta / "base_produtos.csv"):
            if p["tipo_registro"] == "PRODUTO":
                self.assertEqual(sum(int(v["itens"]) for v in V if v["id_candidato"] == p["id_candidato"]), int(p["itens"]))
        luva = [v for v in V if v["id_candidato"] == "CP0001"]
        self.assertEqual(len(luva), 1)                         # dois formatos (com e sem ':') -> uma variante normalizada
        self.assertEqual(luva[0]["n_descricoes_originais"], "2")
        self.assertEqual(luva[0]["itens"], "65")
        self.assertEqual(luva[0]["compras"], str(20 + 13))       # compras distintas contadas item a item


class Extras(Base):
    def test_R_decisao_invalida_erro(self):
        P = self.prods()
        P[0]["decisao_produto"] = "APROVADO"
        ms.gravar(self.pasta / "revisao_produtos.csv", P)
        with self.assertRaisesRegex(ErroEstrutural, "decisões inválidas"):
            self.concluir()

    def test_R_preparar_nao_sobrescreve_revisoes(self):
        self.preencher("CP0001")
        with self.assertRaisesRegex(ErroEstrutural, "não sobrescrevo"):
            preparar(self.cfg, self.reg, "P1", saida=self.pasta)

    def test_R_mudanca_de_entrada_exige_nova_versao(self):
        arq = self.tmp / "entradas" / "cesta_candidata.csv"
        arq.write_text(arq.read_text(encoding="utf-8-sig") + "\n", encoding="utf-8-sig")
        with self.assertRaisesRegex(ErroEstrutural, "nova versão"):
            self.concluir()

    def test_R_mapeamento_com_coluna_economica_erro(self):
        self.cfg["mapa"]["cesta_candidata"]["usar"]["preco_medio"] = "preço"
        with self.assertRaisesRegex(ErroEstrutural, "informação econômica"):
            inspecionar(self.cfg, self.reg, escrever=False)

    def test_R_codigo_nao_referencia_campos_economicos(self):
        proib = ["valor_unit", "modo_disputa", "desconto_", "n_licitantes", "preco_", "valor_estimado", "compras_af", "honestdid"]
        for p in ms.SCRIPTS.glob("*.py"):
            t = p.read_text(encoding="utf-8").lower()
            for x in proib:
                self.assertNotIn(x, t, f"{p.name} menciona {x}")

    def test_R_rejeicao_documentada(self):
        self.preencher("CP0003", decisao="REJEITAR")
        self.concluir()
        self.assertEqual(self.status("CP0003")["status_final"], "REJEITADO")

    def test_R_subproduto_nao_aceita_desmembrar(self):
        sub = self.base("CP0002")["subprodutos"].split(";")[0]
        P = self.prods()
        for p in P:
            if p["id_registro"] == sub:
                p["decisao_produto"] = "DESMEMBRAR"
        ms.gravar(self.pasta / "revisao_produtos.csv", P)
        with self.assertRaises(ErroEstrutural):
            self.concluir()

    def test_R_especificacao_sem_atributo_essencial_bloqueio(self):
        self.preencher("CP0001", especificacao="LUVA PARA PROCEDIMENTO | MATERIAL: LATEX")      # falta TAMANHO 7
        self.concluir()
        self.assertIn("atributos essenciais", self.status("CP0001")["motivos_bloqueio"])


class Regras(unittest.TestCase):
    """Regressões das correções de regra feitas após o piloto (metodologia_validacao.md, §Registro de alterações)."""

    @classmethod
    def setUpClass(cls):
        cls.e = Extrator(comum.carregar_json(ms.CONFIG / "regras_atributos.json"))
        cls.e.definir_chaves(["FORMA FARMACEUTICA"])

    def test_R1_cx_nao_vira_caixa(self):
        self.assertEqual(normalizar("TAMANHO (CX L) 297 X 210 MM").replace(" ", ""), "TAMANHO(CXL)297X210MM")
        self.assertNotIn("CAIXA", normalizar("TAMANHO (CX L) 297 X 210 MM"))

    def test_R2_milhar_antes_de_virgula(self):
        self.assertEqual(normalizar("DOSAGEM 2% +1:100.000, APRESENTAÇÃO"), "DOSAGEM 2% +1 100000, APRESENTACAO")
        self.assertEqual(normalizar("ABNT/NBR 14.865, COR"), "ABNT/NBR 14865, COR")
        self.assertEqual(normalizar("1.000,5 KG"), "1000.5 KG")

    def test_R3_fracao_de_polegada(self):
        self.assertEqual(set(self.e.extrair(normalizar('MANDRIL DE 1/2"'))["medida_linear"]), {"12.7 MM"})
        self.assertEqual(set(self.e.extrair(normalizar("DIÂMETRO 1 1/2 POL"))["diametro"]), {"38.1 MM"})
        self.assertEqual(set(self.e.extrair(normalizar("MANDRIL DE 12 POL"))["medida_linear"]), {"304.8 MM"})

    def test_R4_forma_farmaceutica_colada_e_generica(self):
        a = self.e.extrair(normalizar("X, FORMA FARMACÊUTICASUSPENSÃO INJETÁVEL"), {"medicamento": True})["forma_farmaceutica"]
        b = self.e.extrair(normalizar("X, FORMA FARMACÊUTICA SUSPENSÃO INJETÁVEL"), {"medicamento": True})["forma_farmaceutica"]
        self.assertEqual(set(a), set(b))
        c = self.e.extrair(normalizar("COMPRIMIDO"), {"medicamento": True})["forma_farmaceutica"]
        self.assertTrue(set(c).isdisjoint({"SUSPENSAO_INJETAVEL"}))
        g = set(self.e.extrair(normalizar("X, APRESENTAÇÃO INJETÁVEL"), {"medicamento": True})["forma_farmaceutica"])
        self.assertTrue(g < set(b))                              # genérico ⊂ específico: 'a examinar', não conflito

    def test_R5_espacamento_dentro_de_numero_e_a_examinar(self):
        from auditar_homogeneidade import auditar_produto
        regras = comum.carregar_json(ms.CONFIG / "regras_atributos.json")
        vs = [{"id_variante": f"V{i}", "descricao_normalizada": d, "chave_compacta": d, "nome": "CAMERA", "atributos": {},
               "declarados": {"CARACTERISTICAS ADICIONAIS": [val]}, "itens": 10, "descricao_ausente": 0, "notas": []}
              for i, (d, val) in enumerate([("CAMERA, ... 45~5 0", "VERTICAL45|5|0"), ("CAMERA, ... 45~50", "VERTICAL45|50")])]
        aud = auditar_produto({"id_candidato": "X", "catmat": "1", "unidade_norm": "UN"}, vs, regras)
        self.assertNotEqual(aud["status"], CONFLITO)
        self.assertEqual(aud["conflitos"][0]["relacao"], "so_espacamento")

    def test_R6_concentracoes_sem_conversao_entre_grandezas(self):
        x = self.e.extrair(normalizar("FOSFATO, CONCENTRAÇÃO 2 MEQ/ML"), {"medicamento": True})
        self.assertEqual(set(x["concentracao_outras"]), {"2 MEQ/ML"})
        y = self.e.extrair(normalizar("ÁLCOOL 70%, FRASCO 1 L"))
        self.assertEqual(set(y["concentracao_pct"]), {"70%"})
        self.assertEqual(set(y["volume"]), {"1000 ML"})
        z = self.e.extrair(normalizar("DIPIRONA 500 MG/ML"), {"medicamento": True})
        self.assertNotIn("massa", z)
        self.assertNotIn("dosagem", z)


if __name__ == "__main__":
    unittest.main()
