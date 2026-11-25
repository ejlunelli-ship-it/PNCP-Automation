"""Comando único da cesta padronizada de produtos (ver protocolo.md e README.md).

    python executar.py                      # todas as etapas
    python executar.py --etapas extrair     # só uma ou mais etapas (separadas por vírgula)
    python executar.py --db <pncp.db> --brutos <pasta> --trabalho <pasta>

Etapas, em ordem:
  extrair      esquema real + extração somente leitura do pncp.db para o banco de trabalho
  brutos       descrição detalhada dos CSVs brutos, ligada e conferida em cardinalidade
  normalizar   unidades (tabela de aliases) e descrições normalizadas (refazível sem reler as fontes)
  selecionar   métricas das famílias, auditoria de descrições, classificação, cesta candidata (CONGELADA)
  auditar      auditoria de qualidade/integridade e cobertura da cesta congelada
  sensibilidade grade de limiares, interseções, recorrência temporal
  diagnostico  diagnóstico de viabilidade causal (lê o modo de disputa; só depois do congelamento)
  relatorio    relatorio.md e registro_execucao.json

O pncp.db é aberto com mode=ro e query_only; a impressão digital do arquivo é conferida no início e
no fim de cada etapa que o lê. Nenhuma etapa de seleção lê preços ou o modo de disputa.
"""
import argparse
import json
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

from cesta import VERSAO  # noqa: E402
from cesta import comum  # noqa: E402

ETAPAS = ["extrair", "brutos", "normalizar", "selecionar", "auditar", "sensibilidade", "diagnostico", "relatorio"]


def principal(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--etapas", default=",".join(ETAPAS))
    ap.add_argument("--db")
    ap.add_argument("--brutos")
    ap.add_argument("--trabalho")
    ap.add_argument("--saidas", default=str(AQUI / "saidas"))
    ap.add_argument("--parametros", default=str(AQUI / "config" / "parametros.json"))
    ap.add_argument("--sem-universo-total", action="store_true",
                    help="pula a varredura descritiva de todas as fontes (testes)")
    a = ap.parse_args(argv)
    etapas = [e.strip() for e in a.etapas.split(",") if e.strip()]
    for e in etapas:
        if e not in ETAPAS:
            ap.error(f"etapa desconhecida: {e}")

    par = comum.carregar_parametros(a.parametros)
    cam = comum.resolver_caminhos(par, a.db, a.brutos, a.trabalho)
    saidas = Path(a.saidas)
    saidas.mkdir(parents=True, exist_ok=True)
    trabalho_db = cam["trabalho"] / "trabalho.db"
    reg = comum.Registro()
    ctx = {"par": par, "cam": cam, "saidas": saidas, "trabalho_db": trabalho_db, "reg": reg,
           "parametros_arquivo": Path(a.parametros), "sem_universo_total": a.sem_universo_total}

    from cesta import pipeline
    inicio = time.strftime("%Y-%m-%dT%H:%M:%S")
    for e in ETAPAS:
        if e in etapas:
            getattr(pipeline, "etapa_" + e)(ctx)
    # registro parcial de cada execução (o completo é gerado na etapa relatorio)
    reg_arq = saidas / "registros" / f"execucao_{'-'.join(etapas)}.json"
    comum.escrever_json(reg_arq, {"versao": VERSAO, "inicio": inicio, "fim": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                  "etapas_pedidas": etapas, "etapas": reg.etapas, "contagens": reg.contagens,
                                  "avisos": reg.avisos, "consultas": reg.consultas,
                                  "segundos_total": reg.total(), "caminhos": {k: str(v) for k, v in cam.items()},
                                  **({"snapshot": ctx["snapshot"]} if "snapshot" in ctx else {})})
    print(f"concluído em {reg.total():.0f} s; registro em {reg_arq}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
