"""Associação condicional A × AF na cesta S1 com efeitos fixos (M1–M5). Uso:
    python executar.py                       # todas as etapas
    python executar.py --etapas modelos,loo  # etapas escolhidas
Etapas: amostra, modelos, loo, verificacao, testes, relatorio; viabilidade (diagnóstico CNPJ × trimestre, avulso). Intermediários em D:/associacao_modos_s1_trabalho.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from assoc import comum, pipeline  # noqa: E402

ORDEM = ["amostra", "modelos", "loo", "verificacao", "testes", "relatorio"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--etapas", default=",".join(ORDEM))
    a = ap.parse_args()
    c = comum.cfg()
    log = comum.Log(comum.trabalho(c, "log_execucao.txt"))
    for et in [x for x in a.etapas.split(",") if x]:
        log(f"etapa {et}: início")
        if et == "amostra":
            pipeline.etapa_amostra(c, log)
        elif et == "modelos":
            pipeline.etapa_modelos(c, log)
        elif et == "loo":
            pipeline.etapa_loo(c, log)
        elif et == "viabilidade":
            from assoc import viabilidade_cnpj
            viabilidade_cnpj.executar(c, log)
        elif et == "verificacao":
            pipeline.etapa_verificacao(c, log)
        elif et == "testes":
            import io
            import unittest
            buf = io.StringIO()
            r = unittest.TextTestRunner(stream=buf, verbosity=2).run(
                unittest.defaultTestLoader.discover(str(comum.PASTA / "testes"), top_level_dir=str(comum.PASTA / "testes")))
            comum.escrever_json(comum.RES / "resultado_testes.json", {"executado_em": comum.agora(), "testes": r.testsRun,
                                                                      "falhas": len(r.failures), "erros": len(r.errors),
                                                                      "ok": r.wasSuccessful(), "saida": buf.getvalue().splitlines()[-40:]})
            log(f"testes: {r.testsRun}, falhas {len(r.failures)}, erros {len(r.errors)}")
        elif et == "relatorio":
            from assoc import relatorio
            relatorio.gerar(c, log)
        log(f"etapa {et}: concluída")


if __name__ == "__main__":
    main()
