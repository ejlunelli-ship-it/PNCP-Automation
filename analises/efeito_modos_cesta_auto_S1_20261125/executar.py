"""Nova rodada EXPLORATÓRIA do estudo A × AF sobre a cesta P1 validada automaticamente (S1).

    python executar.py congelar        # 1. hashes, identificadores e regras — ANTES de acessar preços ou modos
    python executar.py amostras        # 2-3. amostras S1, S1S2, P1 e funis (a cesta original reutiliza o estudo anterior)
    python executar.py estimar         # 4-7, 12-13. E3/E7, dCDH, placebos, HonestDiD, referências, Holm (código do estudo anterior, intacto)
    python executar.py decompor        # 8-9, 11. amostras comuns de eventos, ponderação, órgãos efetivos, sobreposição
    python executar.py composicao      # 10. composição da S1 × demais
    python executar.py comparar        # tabela comparativa, gráficos, relatório, manifesto
    python executar.py tudo            # todas as etapas, na ordem
    python executar.py testes          # testes desta rodada

Opções: --amostras S1,S1S2,P1   --bootstrap N (só para testes)
"""
import argparse
import sys
import time
import unittest
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

from rodada import base  # noqa: E402

ETAPAS = ["congelar", "amostras", "estimar", "decompor", "composicao", "comparar"]


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("comando", choices=ETAPAS + ["tudo", "testes"])
    ap.add_argument("--amostras", default="S1,S1S2,P1")
    ap.add_argument("--bootstrap", type=int)
    a = ap.parse_args(argv)
    c = base.cfg()
    nomes = [x for x in a.amostras.split(",") if x]
    try:
        if a.comando == "testes":
            s = unittest.defaultTestLoader.discover(str(AQUI / "testes"), top_level_dir=str(AQUI))
            r = unittest.TextTestRunner(verbosity=2).run(s)
            base.escrever_json(AQUI / "resultado_testes.json", {"executado_em": base.agora(), "testes": r.testsRun, "falhas": len(r.failures),
                                                                "erros": len(r.errors), "sucesso": r.wasSuccessful()})
            return 0 if r.wasSuccessful() else 1
        etapas = ETAPAS if a.comando == "tudo" else [a.comando]
        for e in etapas:
            t0 = time.time()
            if e == "congelar":
                base.congelar(c)
            elif e == "amostras":
                base.preparar_amostras(c, nomes, log)
            elif e == "estimar":
                for n in nomes:
                    base.estimar(c, n, log, a.bootstrap)
            elif e == "decompor":
                from rodada import analises
                analises.decompor(c, nomes, log, a.bootstrap)
            elif e == "composicao":
                from rodada import analises
                analises.composicao(c, log)
            elif e == "comparar":
                from rodada import relatorio
                relatorio.gerar(c, nomes, log)
            log(f"{e} concluído em {time.time() - t0:.0f} s")
    except base.ErroRodada as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
