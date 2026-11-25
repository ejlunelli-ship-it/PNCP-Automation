"""Risk-set matching + DiD na cesta S1 — comando único: python executar.py

Etapas (retomada segura; cada etapa é pulada quando o código e os arquivos produzidos conferem):
  1 fontes   2 painel   3 eventos   4–12 desenho (Fase I: risco, covariáveis, M0, M1, PS, balanceamento, placebos,
  suporte, congelamento)   13–17 estimacao (Fase II: DiD, inferência, composição, robustez, comparação com o dCDH)
  18 testes   19 relatorio
Uso: python executar.py [--etapas fontes,painel,...] [--refazer etapa1,etapa2]
"""
import argparse
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

from scripts import comum, pipeline  # noqa: E402

ORDEM = ["fontes", "painel", "eventos", "desenho", "estimacao", "diagnosticos", "testes", "relatorio"]
DEPS = {"fontes": ["verificar_fontes.py", "comum.py"],
        "painel": ["construir_painel.py", "executar_placebos.py", "comum.py"],
        "eventos": ["identificar_eventos.py", "construir_painel.py"],
        "desenho": ["desenho.py", "construir_risk_sets.py", "construir_covariaveis.py", "estimar_propensao.py",
                    "realizar_matching.py", "diagnosticar_balanceamento.py", "executar_placebos.py", "estimar_did.py",
                    "inferencia.py", "pipeline.py"],
        "estimacao": ["fase2.py", "estimar_did.py", "inferencia.py", "testar_composicao.py", "robustez.py", "pipeline.py"],
        "diagnosticos": ["diagnosticos_suporte.py"],
        "testes": ["executar_testes.py"],
        "relatorio": ["gerar_relatorio.py"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--etapas", default=",".join(ORDEM))
    ap.add_argument("--refazer", default="")
    a = ap.parse_args()
    c = comum.cfg()
    log = comum.Log(comum.trabalho(c, "log_execucao.txt"))
    E = pipeline.Etapas(c, log, [x for x in a.refazer.split(",") if x])
    funcs = {"fontes": lambda: pipeline.etapa_fontes(c, log), "painel": lambda: pipeline.etapa_painel(c, log),
             "eventos": lambda: pipeline.etapa_eventos(c, log), "desenho": lambda: pipeline.etapa_desenho(c, log)}
    try:
        from scripts import fase2
        funcs["estimacao"] = lambda: fase2.executar(c, log)
    except ImportError:
        pass
    try:
        from scripts import gerar_relatorio
        funcs["relatorio"] = lambda: gerar_relatorio.executar(c, log)
    except ImportError:
        pass
    from scripts import diagnosticos_suporte
    funcs["diagnosticos"] = lambda: diagnosticos_suporte.executar(c, log)
    from scripts import executar_testes
    funcs["testes"] = lambda: executar_testes.executar(c, log)
    for et in [x for x in a.etapas.split(",") if x]:
        if et == "testes":
            funcs[et]()          # sempre executa (registra o resultado)
            continue
        E.rodar(et, DEPS[et], funcs[et])


if __name__ == "__main__":
    main()
