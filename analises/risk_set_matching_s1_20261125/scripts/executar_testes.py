"""Etapa 18: executa a bateria de testes e registra o resultado em resultados/resultado_testes.json."""
import io
import unittest

from . import comum
from .comum import PASTA


def executar(c, log):
    buf = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(PASTA / "testes"), top_level_dir=str(PASTA / "testes"))
    r = unittest.TextTestRunner(stream=buf, verbosity=2).run(suite)
    out = {"executado_em": comum.agora(), "testes": r.testsRun, "falhas": len(r.failures), "erros": len(r.errors),
           "pulados": len(r.skipped), "ok": r.wasSuccessful(),
           "detalhe": [l for l in buf.getvalue().splitlines() if l.endswith(("ok", "FAIL", "ERROR")) or "skipped" in l]}
    comum.escrever_json(PASTA / "resultados" / "resultado_testes.json", out)
    log(f"testes: {out['testes']} executados, {out['falhas']} falhas, {out['erros']} erros, {out['pulados']} pulados")
    return out
