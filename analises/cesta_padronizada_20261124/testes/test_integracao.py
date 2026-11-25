"""Testes de integração com bancos SQLite sintéticos (pipeline completo, todas as etapas)."""
import csv
import hashlib
import io
import re
import sqlite3
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

AQUI = Path(__file__).resolve().parent
PASTA = AQUI.parent
sys.path.insert(0, str(PASTA))
sys.path.insert(0, str(AQUI))

import executar  # noqa: E402
import sintetico  # noqa: E402
from cesta import comum, diagnostico, esquema  # noqa: E402
from cesta.comum import ErroEstrutural  # noqa: E402


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ler(p):
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def rodar(c, etapas=None):
    with redirect_stdout(io.StringIO()):
        return executar.principal(sintetico.argv(c, etapas) if etapas else sintetico.argv(c))


class PipelineSintetico(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.c = sintetico.construir(Path(cls.tmp.name) / "w1")
        cls.hash_db_antes = sha(cls.c["db"])
        cls.mtime_antes = cls.c["db"].stat().st_mtime_ns
        rodar(cls.c)
        cls.trab = sqlite3.connect(cls.c["trabalho"] / "trabalho.db")
        cls.fam = {r[0]: dict(zip([d[0] for d in cls.trab.execute("SELECT * FROM fam_metricas").description], r))
                   for r in cls.trab.execute("SELECT * FROM fam_metricas")}

    @classmethod
    def tearDownClass(cls):
        cls.trab.close()
        cls.tmp.cleanup()

    # Teste 1 — frequência correta
    def test_1_varios_itens_mesma_compra_contam_uma_compra(self):
        f = self.fam["111|UNIDADE"]
        # 16 compras principais (a 1ª com 3 itens) + 1 com registro repetido + 2 com id_compra repetido
        self.assertEqual(f["compras"], 19)
        self.assertEqual(f["itens"], 21, "os 3 itens da 1ª compra são preservados como itens")
        self.assertGreater(f["itens"], f["compras"])

    # Teste 2 — identificadores institucionais
    def test_2_uasgs_com_mesmo_cnpj_continuam_distintas(self):
        f = self.fam["111|UNIDADE"]
        self.assertEqual(f["uasgs"], 8)
        self.assertEqual(f["orgaos"], 7, "000001 e 000002 compartilham CNPJ")
        n = self.trab.execute("SELECT COUNT(DISTINCT uasg) FROM compras_base WHERE orgao_cnpj = '11111111000111'").fetchone()[0]
        self.assertEqual(n, 2)

    # Teste 3 — chaves compostas
    def test_3_id_compra_repetido_nao_agrupa_compras(self):
        n = self.trab.execute("SELECT COUNT(*) FROM compras_base WHERE id_compra = 'DUPLICADO'").fetchone()[0]
        self.assertEqual(n, 2)
        n = self.trab.execute("SELECT COUNT(DISTINCT chave) FROM universo WHERE chave IN "
                              "(SELECT chave FROM compras_base WHERE id_compra = 'DUPLICADO')").fetchone()[0]
        self.assertEqual(n, 2)

    def test_3b_registro_repetido_vira_um_item(self):
        r = self.trab.execute("SELECT registros FROM itens i JOIN compras_base c USING (chave) "
                              "WHERE c.uasg = '000003' AND i.numero_item = 1 AND i.catmat = 111 "
                              "ORDER BY registros DESC LIMIT 1").fetchone()
        self.assertEqual(r[0], 2)

    # Teste 4 — unidades não fundidas
    def test_4_embalagens_distintas_sao_familias_distintas(self):
        luvas = sorted(k for k in self.fam if k.startswith("222|"))
        self.assertEqual(luvas, ["222|CAIXA 100 UNIDADE", "222|CAIXA 500 UNIDADE", "222|UNIDADE"])

    # Teste 5 — especificações incompatíveis
    def test_5_gramaturas_diferentes_nao_formam_um_produto(self):
        cand = ler(self.c["saidas"] / "cesta_candidata.csv")
        papeis = [c for c in cand if c["catmat"] == "333"]
        self.assertEqual(len(papeis), 2, "separados em subtipos pela assinatura")
        self.assertTrue(all(c["classe_tecnica"] == "B" for c in papeis), "subtipo automático no máximo B")
        self.assertEqual({("75 G/M2" in c["assinatura_atributos"], "90 G/M2" in c["assinatura_atributos"]) for c in papeis},
                         {(True, False), (False, True)})

    def test_5b_descricao_generica_fica_fora(self):
        cand = ler(self.c["saidas"] / "cesta_candidata.csv")
        self.assertFalse([c for c in cand if c["catmat"] == "555"])
        desc = ler(self.c["saidas"] / "familias_triadas_descartadas.csv")
        self.assertTrue([d for d in desc if d["catmat"] == "555"])

    # Teste 6 — bens × serviços
    def test_6_servico_fora_do_universo(self):
        n = self.trab.execute("SELECT COUNT(*) FROM universo WHERE catmat = 444").fetchone()[0]
        self.assertEqual(n, 0)

    # Teste 7 — somente leitura
    def test_7_banco_de_origem_inalterado(self):
        self.assertEqual(sha(self.c["db"]), self.hash_db_antes)
        self.assertEqual(self.c["db"].stat().st_mtime_ns, self.mtime_antes)
        self.assertFalse(Path(str(self.c["db"]) + "-journal").exists())

    def test_7b_conexao_ro_recusa_escrita(self):
        con = comum.conectar_ro(self.c["db"])
        with self.assertRaises(sqlite3.OperationalError):
            con.execute("CREATE TABLE x (a)")
        with self.assertRaises(sqlite3.OperationalError):
            con.execute("DELETE FROM compras")
        con.close()

    # Teste 8 — exclusões explícitas e contadas
    def test_8_funil_e_auditoria_registram_exclusoes(self):
        fun = {f["etapa"]: f for f in ler(self.c["saidas"] / "funil_selecao.csv")}
        self.assertEqual(int(fun["1_pregao_eletronico"]["compras_perdidas"]), 1)
        self.assertEqual(int(fun["5_uasg_valida"]["compras_perdidas"]), 1)
        self.assertEqual(int(fun["6_data_valida"]["compras_perdidas"]), 1)
        aud = {a["verificacao"]: a for a in ler(self.c["saidas"] / "auditoria_qualidade.csv")}
        self.assertEqual(int(aud["data de publicação inválida"]["afetados"]), 1)
        self.assertEqual(int(aud["CNPJ compartilhado por mais de uma UASG"]["afetados"]), 1)
        self.assertEqual(int(aud["id_compra repetido em mais de um numero_controle_pncp"]["afetados"]), 1)

    # Teste 9 — cesta validada não é inventada
    def test_9_cesta_validada_vazia_sem_revisao(self):
        self.assertEqual(ler(self.c["saidas"] / "cesta_validada.csv"), [])
        form = ler(self.c["saidas"] / "formulario_revisao.csv")
        self.assertTrue(form)
        self.assertTrue(all(not r["revisor"] and not r["decisao (aprovar/rejeitar/dividir)"] for r in form))

    # Teste 10 — 100% das variantes preservadas
    def test_10_todas_as_variantes_no_arquivo(self):
        var = ler(self.c["saidas"] / "descricoes_variantes.csv")
        caneta = {v["descricao_original"] for v in var if v["familia"] == "111|UNIDADE"}
        self.assertEqual(caneta, set(sintetico.PRODUTOS["caneta"][6]))
        tot = sum(int(v["itens"]) for v in var if v["familia"] == "111|UNIDADE")
        self.assertEqual(tot, self.fam["111|UNIDADE"]["itens"])

    # Teste 11 — diagnóstico só depois do congelamento e sem alterar a cesta
    def test_11_diagnostico_exige_congelamento(self):
        with tempfile.TemporaryDirectory() as t:
            ctx = {"cam": {"db": self.c["db"]}, "reg": comum.Registro(False), "saidas": Path(t),
                   "trabalho_db": self.c["trabalho"] / "trabalho.db", "par": comum.carregar_parametros(self.c["parametros"])}
            with self.assertRaises(ErroEstrutural):
                diagnostico.executar(ctx)

    def test_11b_diagnostico_produzido(self):
        self.assertTrue((self.c["saidas"] / "diagnostico_viabilidade.json").exists())
        self.assertTrue((self.c["saidas"] / "relatorio.md").exists())


class Independencia(unittest.TestCase):
    """Teste metamórfico: trocar SÓ preços e modo de disputa não pode mudar a cesta."""

    def test_precos_e_modos_nao_alteram_a_cesta(self):
        with tempfile.TemporaryDirectory() as t:
            a = sintetico.construir(Path(t) / "a", fator_preco=1.0, inverter_modo=False)
            b = sintetico.construir(Path(t) / "b", fator_preco=37.5, inverter_modo=True)
            etapas = "extrair,brutos,normalizar,selecionar,sensibilidade"
            rodar(a, etapas)
            rodar(b, etapas)
            for arq in ("cesta_candidata.csv", "descricoes_variantes.csv", "funil_selecao.csv",
                        "sensibilidade_grade.csv", "familias_triadas_descartadas.csv"):
                self.assertEqual((a["saidas"] / arq).read_bytes(), (b["saidas"] / arq).read_bytes(), arq)

    def test_codigo_de_selecao_nao_le_colunas_proibidas(self):
        modulos = ["selecao", "metricas", "classificacao", "atributos", "extracao", "brutos", "cobertura",
                   "sensibilidade", "normalizacao", "auditoria"]
        for m in modulos:
            txt = (PASTA / "cesta" / f"{m}.py").read_text(encoding="utf-8")
            for col in esquema.COLUNAS_PROIBIDAS_SELECAO:
                self.assertIsNone(re.search(rf"\b{col}\b", txt), f"{m}.py menciona {col}")


class Estrutural(unittest.TestCase):
    def test_cardinalidade_brutos_quebrada_interrompe(self):
        with tempfile.TemporaryDirectory() as t:
            c = sintetico.construir(Path(t) / "w")
            arq = c["brutos"] / "2024" / "itens_pregao_2024-01.csv"
            linhas = arq.read_text(encoding="utf-8-sig").splitlines()
            arq.write_text("\n".join(linhas[:-1]) + "\n", encoding="utf-8-sig")   # remove um item dos brutos
            with self.assertRaises(ErroEstrutural):
                rodar(c, "extrair,brutos")

    def test_campo_obrigatorio_ausente_interrompe(self):
        with tempfile.TemporaryDirectory() as t:
            db = Path(t) / "x.db"
            con = sqlite3.connect(db)
            con.execute("CREATE TABLE compras (numero_controle_pncp TEXT PRIMARY KEY)")
            con.execute("CREATE TABLE itens (id INTEGER PRIMARY KEY)")
            con.close()
            ro = comum.conectar_ro(db)
            with self.assertRaises(ErroEstrutural):
                esquema.mapear(ro)
            ro.close()


if __name__ == "__main__":
    unittest.main()
